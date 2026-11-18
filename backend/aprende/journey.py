"""Journey state machine for Aprende y Planea (spec section 5)."""
import os, sys, json, uuid, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import db

CLIENT_EVENTS = {"ai_disclosed", "consent", "names_submitted", "documents_tentative", "documents_confirmed"}
SERVER_EVENTS = {
    "conflict_auto", "conflict_firm", "scope_approved", "engagement_signed",
    "paid", "drafts_ready", "attorney_approved", "signed", "intake_completed",
}
ALL_EVENTS = CLIENT_EVENTS | SERVER_EVENTS

REQUIRED_GATE = {
    "ai_disclosed": "may_disclose",
    "consent": "may_consent",
    "names_submitted": "may_name",
    "documents_tentative": "may_collect_details",
    "documents_confirmed": "may_collect_details",
}


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()


def gates(facts):
    facts = facts or {}
    auto = facts.get("conflict_auto_result")
    firm = facts.get("conflict_firm_result")
    if auto in ("possible", "no_list") or firm == "flagged":
        conflict = "hold"
    elif auto == "clear" and firm != "flagged":
        conflict = "clear"
    else:
        conflict = "pending"
    conflict_clear = conflict == "clear"
    ai = "ai_disclosed" in facts
    consent_yes = ("consent" in facts) and (facts.get("consent_answer") == "yes")
    names = "names_submitted" in facts
    scope = "scope_approved" in facts
    engagement = "engagement_signed" in facts
    paid = "paid" in facts
    drafts = "drafts_ready" in facts
    attorney = "attorney_approved" in facts
    return {
        "may_disclose": True,
        "may_consent": ai,
        "may_name": consent_yes,
        "may_collect_details": consent_yes and names and conflict_clear,
        "may_chat": consent_yes and names and conflict_clear,
        "may_sign_engagement": consent_yes and names and conflict_clear and scope,
        "may_pay": engagement,
        "may_see_documents": paid and drafts and attorney,
        "may_book_signing": engagement,
        "may_take_final_lesson": paid and drafts and attorney,
    }


def conflict_status(facts):
    facts = facts or {}
    auto = facts.get("conflict_auto_result")
    firm = facts.get("conflict_firm_result")
    if auto in ("possible", "no_list") or firm == "flagged":
        return "hold"
    if auto == "clear" and firm != "flagged":
        return "clear"
    return "pending"


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
        if typ == "consent" and "consent_answer" not in facts and isinstance(payload, dict) and "answer" in payload:
            facts["consent_answer"] = payload["answer"]
        if typ == "conflict_auto" and "conflict_auto_result" not in facts and isinstance(payload, dict) and "result" in payload:
            facts["conflict_auto_result"] = payload["result"]
        if typ == "conflict_firm" and "conflict_firm_result" not in facts and isinstance(payload, dict) and "result" in payload:
            facts["conflict_firm_result"] = payload["result"]
    return facts


def _row_to_journey(row, events_rows):
    jid, user_id, tz, started_at, matter_id = row[0], row[1], row[2], row[3], row[4]
    facts_internal = _reconstruct_facts(events_rows)
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
        if typ == "documents_tentative" and isinstance(payload, dict):
            if "codes" in payload:
                tentative = list(payload["codes"])
            elif "documents" in payload:
                tentative = list(payload["documents"])
        if typ == "documents_confirmed" and isinstance(payload, dict):
            if "codes" in payload:
                confirmed = list(payload["codes"])
            elif "documents" in payload:
                confirmed = list(payload["documents"])
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
    if hasattr(journey_id, "id"):
        journey_id = journey_id.id
    rows = db.query("SELECT id, user_id, tz, started_at, matter_id FROM journeys WHERE id = ?", (journey_id,))
    if not rows:
        return None
    ev = db.query("SELECT type, payload_json, actor, created_at FROM journey_events WHERE journey_id = ? ORDER BY created_at", (journey_id,))
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


def _insert_event(journey_id, type_, payload, actor, dedupe_key=""):
    eid = str(uuid.uuid4())
    try:
        db.execute(
            "INSERT INTO journey_events (id, journey_id, type, payload_json, actor, dedupe_key) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (eid, journey_id, type_, json.dumps(payload if payload is not None else {}), actor, dedupe_key),
        )
        return True
    except Exception:
        return False


def apply(journey_id, event_type, payload=None, actor="system"):
    if isinstance(journey_id, dict):
        journey_id = journey_id.get("id") or journey_id.get("journey_id")
    if hasattr(journey_id, "id"):
        journey_id = journey_id.id
    if isinstance(event_type, dict):
        payload = event_type.get("payload", payload)
        actor = event_type.get("actor", actor)
        event_type = event_type.get("type") or event_type.get("event")
    j = get_journey(journey_id)
    if j is None:
        raise ValueError("journey not found")
    inserted = _insert_event(j["id"], event_type, payload or {}, actor)
    if not inserted:
        return get_journey(j["id"])
    if event_type == "names_submitted":
        try:
            import legacy
            mid = legacy.ensure_matter(get_journey(j["id"]))
            if mid:
                db.execute("UPDATE journeys SET matter_id = ? WHERE id = ?", (mid, j["id"]))
        except Exception:
            pass
    return get_journey(j["id"])
