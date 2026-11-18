"""Journey state machine for Aprende y Planea (spec section 5)."""
import datetime
import json
import uuid

import db
from aprende import legacy

CLIENT_EVENTS = {"ai_disclosed", "consent", "names_submitted", "documents_tentative", "documents_confirmed"}
SERVER_EVENTS = {
    "conflict_auto", "conflict_firm", "scope_approved", "engagement_signed",
    "paid", "drafts_ready", "attorney_approved", "signed", "intake_completed",
    "client_confirmed", "changes_requested", "signing_booked", "final_lesson_completed",
    "funding_done",
    "lesson_completed:will", "lesson_completed:trust", "lesson_completed:ahcd", "lesson_completed:poa",
}
ALL_EVENTS = CLIENT_EVENTS | SERVER_EVENTS

REQUIRED_GATE = {
    "ai_disclosed": "may_disclose",
    "consent": "may_consent",
    "names_submitted": "may_name",
    "documents_tentative": "may_collect_details",
    "documents_confirmed": "may_collect_details",
}

DOC_CODES = {"will", "trust", "poa", "ahcd"}


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()


def conflict_status(facts):
    facts = facts or {}
    auto = facts.get("conflict_auto_result")
    firm = facts.get("conflict_firm_result")
    if auto in ("possible", "no_list") or firm == "flagged":
        return "hold"
    if auto == "clear" and firm != "flagged":
        return "clear"
    return "pending"


def gates(facts):
    facts = facts or {}
    conflict = conflict_status(facts)
    conflict_clear = conflict == "clear"
    ai = "ai_disclosed" in facts
    consent_yes = ("consent" in facts) and (facts.get("consent_answer") == "yes")
    names = "names_submitted" in facts
    scope = "scope_approved" in facts
    firm_cleared = facts.get("conflict_firm_result") == "cleared"
    engagement = "engagement_signed" in facts
    paid = "paid" in facts
    drafts = "drafts_ready" in facts
    attorney = "attorney_approved" in facts
    client_confirmed = "client_confirmed" in facts
    signed = "signed" in facts
    may_disclose = True
    may_consent = ai
    may_name = consent_yes
    base_open = consent_yes and names and conflict_clear
    may_collect_details = base_open
    may_chat = base_open
    may_sign_engagement = base_open and firm_cleared and scope
    may_pay = may_sign_engagement and engagement
    may_see_documents = paid and drafts and attorney
    may_book_signing = may_see_documents and client_confirmed
    may_take_final_lesson = signed
    # hold closes everything after may_name
    if conflict == "hold":
        may_collect_details = False
        may_chat = False
        may_sign_engagement = False
        may_pay = False
        may_see_documents = False
        may_book_signing = False
        may_take_final_lesson = False
    return {
        "may_disclose": may_disclose,
        "may_consent": may_consent,
        "may_name": may_name,
        "may_collect_details": may_collect_details,
        "may_chat": may_chat,
        "may_sign_engagement": may_sign_engagement,
        "may_pay": may_pay,
        "may_see_documents": may_see_documents,
        "may_book_signing": may_book_signing,
        "may_take_final_lesson": may_take_final_lesson,
    }


def compute_day(started_at, tz="America/Los_Angeles"):
    try:
        from zoneinfo import ZoneInfo
        zone = ZoneInfo(tz)
    except Exception:
        zone = datetime.timezone.utc
    start = datetime.datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
    if start.tzinfo is None:
        start = start.replace(tzinfo=datetime.timezone.utc)
    now = datetime.datetime.now(zone)
    start_local = start.astimezone(zone)
    delta = (now.date() - start_local.date()).days
    if delta < 0:
        delta = 0
    return 1 + delta


def _reconstruct_facts(rows):
    facts = {}
    for r in rows:
        typ = r[0]
        payload_raw = r[1]
        created_at = r[3]
        try:
            payload = json.loads(payload_raw) if payload_raw else {}
        except (ValueError, TypeError):
            payload = {}
        if typ not in facts:
            facts[typ] = created_at
        if typ == "consent" and isinstance(payload, dict) and "answer" in payload:
            facts["consent_answer"] = payload["answer"]
        if typ == "conflict_auto" and isinstance(payload, dict) and "result" in payload:
            facts["conflict_auto_result"] = payload["result"]
        if typ == "conflict_firm" and isinstance(payload, dict) and "result" in payload:
            facts["conflict_firm_result"] = payload["result"]
    return facts


def _row_to_journey(row, events_rows):
    jid, user_id, tz, started_at, matter_id = row[0], row[1], row[2], row[3], row[4]
    facts_internal = _reconstruct_facts(events_rows)
    # client-facing facts hide conflict results (confidential)
    facts = {k: v for k, v in facts_internal.items()
             if k not in ("conflict_auto_result", "conflict_firm_result")}
    tentative = []
    confirmed = []
    for r in events_rows:
        typ = r[0]
        try:
            payload = json.loads(r[1]) if r[1] else {}
        except (ValueError, TypeError):
            payload = {}
        if typ == "documents_tentative" and isinstance(payload, dict) and "codes" in payload:
            tentative = list(payload["codes"])
        if typ == "documents_confirmed" and isinstance(payload, dict) and "codes" in payload:
            confirmed = list(payload["codes"])
    return {
        "id": jid,
        "user_id": user_id,
        "started_at": started_at,
        "tz": tz,
        "day": compute_day(started_at, tz or "America/Los_Angeles"),
        "facts": facts,
        "gates": gates(facts_internal),
        "conflict": conflict_status(facts_internal),
        "documents": {"tentative": tentative, "confirmed": confirmed},
        "timeline": [],
        "matter_id": matter_id,
    }


def get_journey(journey_id):
    rows = db.query("SELECT id, user_id, tz, started_at, matter_id FROM journeys WHERE id = ?", (journey_id,))
    if not rows:
        return None
    ev = db.query("SELECT type, payload_json, actor, created_at, id FROM journey_events WHERE journey_id = ? ORDER BY created_at, id", (journey_id,))
    return _row_to_journey(rows[0], ev)


def get_journey_by_user(user_id):
    rows = db.query("SELECT id FROM journeys WHERE user_id = ?", (user_id,))
    if not rows:
        return None
    return get_journey(rows[0][0])


def create_journey(user_id, tz="America/Los_Angeles"):
    jid = str(uuid.uuid4())
    db.execute(
        "INSERT INTO journeys (id, user_id, tz, started_at) VALUES (?, ?, ?, ?)",
        (jid, user_id, tz, _now_iso()),
    )
    return get_journey(jid)


def get_or_create_for_user(user_id):
    j = get_journey_by_user(user_id)
    if j is None:
        j = create_journey(user_id)
    return j


def _insert_event(journey_id, event_type, payload, actor, created_at):
    """Record an event unless it repeats the latest one of its type (a resend is a no-op). For consent and the conflict
    results only an unchanged answer is a repeat, so a changed decision is always recorded. Read and insert happen in one
    transaction, so concurrent requests cannot both insert. Earned discounts are recorded in the same transaction."""
    with db.transaction() as conn:
        row = conn.execute(
            "SELECT payload_json FROM journey_events WHERE journey_id = ? AND type = ? ORDER BY created_at DESC, id DESC LIMIT 1",
            (journey_id, event_type)).fetchone()
        if row is not None:
            if event_type not in ("consent", "conflict_auto", "conflict_firm"):
                return False
            last = json.loads(row[0] or "{}")
            key = "answer" if event_type == "consent" else "result"
            if last.get(key) == payload.get(key):
                return False
        conn.execute(
            "INSERT INTO journey_events (id, journey_id, type, payload_json, actor, created_at, dedupe_key) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), journey_id, event_type, json.dumps(payload), actor, created_at, uuid.uuid4().hex))
        r = conn.execute("SELECT value_json FROM settings WHERE key = ?", ("pricing",)).fetchone()
        settings = json.loads(r[0]) if r else {}
        for doc, cfg in (settings.get("discounts") or {}).items():
            if event_type in (cfg.get("events") or []):
                conn.execute(
                    "INSERT INTO discounts (id, journey_id, document, event, amount_cents, earned_at) "
                    "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (journey_id, document, event) DO NOTHING",
                    (str(uuid.uuid4()), journey_id, doc, event_type, int(cfg["amount"]), created_at))
    return True


def apply(journey_id, event_type, payload=None, actor="system"):
    if event_type not in ALL_EVENTS:
        raise ValueError("unknown event type")
    j = get_journey(journey_id)
    if j is None:
        raise ValueError("journey not found")
    inserted = _insert_event(j["id"], event_type, payload or {}, actor, _now_iso())
    if not inserted:
        return get_journey(j["id"])
    if event_type == "names_submitted":
        mid = legacy.ensure_matter(get_journey(j["id"]))
        if mid:
            db.execute("UPDATE journeys SET matter_id = ? WHERE id = ?", (mid, j["id"]))
    return get_journey(j["id"])
