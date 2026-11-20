"""Analytics without client content (spec 12). One writer for the `events` table."""
import contextvars
import json
import re
import uuid

import db
from aprende import journey

TARGET = contextvars.ContextVar("analytics_target", default="web")

EVENTS = {
    "lesson_started": {"lesson_id"}, "item_answered": {"item_id", "correct", "attempt"},
    "lesson_completed": {"lesson_id"}, "datos_question_answered": {"question_id", "skipped"},
    "datos_completed": set(), "consent": {"answer"}, "conflict_auto": {"result"},
    "documents_tentative": {"codes"}, "engagement_signed": set(), "checkout_started": set(),
    "paid": set(), "drafts_ready": set(), "attorney_approved": set(), "client_confirmed": set(),
    "changes_requested": set(), "signing_booked": set(), "signed": set(),
    "final_lesson_completed": set(), "step_late": {"step"},
}

_ANALYTICS_MAP = {
    "consent": ("consent", lambda p: {"answer": p.get("answer")} if "answer" in p else {}),
    "conflict_auto": ("conflict_auto", lambda p: {"result": p.get("result")} if "result" in p else {}),
    "documents_tentative": ("documents_tentative", lambda p: {"codes": p.get("codes")} if "codes" in p else {}),
    "engagement_signed": ("engagement_signed", lambda p: {}),
    "paid": ("paid", lambda p: {}),
    "drafts_ready": ("drafts_ready", lambda p: {}),
    "attorney_approved": ("attorney_approved", lambda p: {}),
    "client_confirmed": ("client_confirmed", lambda p: {}),
    "changes_requested": ("changes_requested", lambda p: {}),
    "signing_booked": ("signing_booked", lambda p: {}),
    "signed": ("signed", lambda p: {}),
    "final_lesson_completed": ("final_lesson_completed", lambda p: {}),
    "intake_completed": ("datos_completed", lambda p: {}),
}
JOURNEY_ANALYTICS_MAP = _ANALYTICS_MAP


_VALUE_RE = re.compile(r"^[a-z0-9_.:-]*$")


def _valid_value(v):
    if isinstance(v, bool):
        return True
    if isinstance(v, int):
        return True
    if isinstance(v, str):
        return len(v) <= 40 and bool(_VALUE_RE.match(v))
    if isinstance(v, list):
        return all(isinstance(x, str) and len(x) <= 40 and bool(_VALUE_RE.match(x)) for x in v)
    return False


def record(journey_id, type_, props=None, *, conn=None):
    if type_ not in EVENTS:
        raise ValueError(f"unknown event type: {type_}")
    allowed = EVENTS[type_]
    props = dict(props or {})
    if not set(props).issubset(allowed):
        raise ValueError(f"disallowed prop keys: {set(props) - allowed}")
    for k, v in props.items():
        if not _valid_value(v):
            raise ValueError(f"invalid value for {k}")
    j = journey.get_journey(journey_id)
    if j is None:
        raise ValueError("journey not found")
    row_props = dict(props)
    row_props["day"] = j["day"]
    target = TARGET.get()
    eid = str(uuid.uuid4())
    sql = ("INSERT INTO events (id, journey_id, type, props_json, target, created_at) "
           "VALUES (?, ?, ?, ?, ?, ?)")
    params = (eid, journey_id, type_, json.dumps(row_props), target, journey._now_iso())
    if conn is None:
        db.execute(sql, params)
    else:
        conn.execute(sql, params)


def from_journey_event(journey_id, event_type, payload=None, conn=None):
    mapping = _ANALYTICS_MAP.get(event_type)
    if not mapping:
        return None
    ev_type, prop_fn = mapping
    return record(journey_id, ev_type, prop_fn(payload or {}), conn=conn)


def record_once(journey_id, type_, props=None, *, conn=None):
    """Record only if no prior event of this type/lesson exists (one query check)."""
    props = dict(props or {})
    lesson_id = props.get("lesson_id")
    if lesson_id is not None:
        sql = "SELECT 1 FROM events WHERE journey_id = ? AND type = ? AND props_json LIKE ? LIMIT 1"
        param = (journey_id, type_, f'%{lesson_id}%')
    else:
        sql = "SELECT 1 FROM events WHERE journey_id = ? AND type = ? LIMIT 1"
        param = (journey_id, type_)
    if conn is None:
        rows = db.query(sql, param)
        exists = bool(rows)
    else:
        exists = conn.execute(sql, param).fetchone() is not None
    if exists:
        return None
    return record(journey_id, type_, props, conn=conn)


def dashboard(since=None):
    if since:
        jids = [r[0] for r in db.query("SELECT id FROM journeys WHERE started_at >= ?", (since,))]
    else:
        jids = [r[0] for r in db.query("SELECT id FROM journeys")]
    jset = set(jids)

    events_by_j = {jid: [] for jid in jids}
    if jids:
        if since:
            sql = "SELECT journey_id, type, props_json, created_at, id FROM events WHERE journey_id IN (SELECT id FROM journeys WHERE started_at >= ?) ORDER BY created_at, id"
            param = (since,)
        else:
            sql = "SELECT journey_id, type, props_json, created_at, id FROM events WHERE journey_id IN (SELECT id FROM journeys) ORDER BY created_at, id"
            param = ()
        for jid_, t, pj, ca, eid in db.query(sql, param):
            props = json.loads(pj) if pj else {}
            if jid_ in events_by_j:
                events_by_j[jid_].append((t, props, eid))

    item_lesson = {}
    item_order = []
    for iid, lid in db.query("SELECT i.id, i.lesson_id FROM content_items i JOIN content_steps s ON s.id = i.step_id ORDER BY s.position, i.position"):
        item_lesson[iid] = lid
        item_order.append(iid)

    lesson_order = [r[0] for r in db.query("SELECT id FROM content_lessons ORDER BY position, id")]

    lesson_started = {l: set() for l in lesson_order}
    lesson_completed = {l: set() for l in lesson_order}
    for jid in jids:
        for t, props, eid in events_by_j[jid]:
            if t == "lesson_started":
                lid = props.get("lesson_id")
                if lid in lesson_started:
                    lesson_started[lid].add(jid)
            elif t == "lesson_completed":
                lid = props.get("lesson_id")
                if lid in lesson_completed:
                    lesson_completed[lid].add(jid)

    item_answered_j = {iid: set() for iid in item_lesson}
    item_first_correct = {iid: 0 for iid in item_lesson}
    for jid in jids:
        for t, props, eid in events_by_j[jid]:
            if t == "item_answered" and props.get("attempt") == 1:
                iid = props.get("item_id")
                if iid in item_answered_j:
                    item_answered_j[iid].add(jid)
                    if props.get("correct") is True:
                        item_first_correct[iid] += 1

    journey_latest_item_in_lesson = {}
    for jid in jids:
        last_by_lesson = {}
        for t, props, eid in events_by_j[jid]:
            if t == "item_answered":
                iid = props.get("item_id")
                lid = item_lesson.get(iid)
                if lid is None:
                    continue
                last_by_lesson[lid] = iid
        journey_latest_item_in_lesson[jid] = last_by_lesson

    item_dropoff = {iid: 0 for iid in item_lesson}
    for jid in jids:
        for lid in lesson_order:
            if jid in lesson_started.get(lid, set()) and jid not in lesson_completed.get(lid, set()):
                latest = journey_latest_item_in_lesson[jid].get(lid)
                if latest in item_dropoff:
                    item_dropoff[latest] += 1

    lesson_dropped_before = {}
    for lid in lesson_order:
        n = 0
        for jid in jids:
            if jid in lesson_started.get(lid, set()) and jid not in lesson_completed.get(lid, set()):
                if not journey_latest_item_in_lesson[jid].get(lid):
                    n += 1
        lesson_dropped_before[lid] = n

    lessons_out = []
    for lid in lesson_order:
        started = len(lesson_started.get(lid, set()))
        completed = len(lesson_completed.get(lid, set()))
        if started == 0 and completed == 0:
            continue
        rate = round(completed / started, 3) if started else None
        lessons_out.append({
            "lesson_id": lid,
            "started": started,
            "completed": completed,
            "completion_rate": rate,
            "dropped_before_first_item": lesson_dropped_before.get(lid, 0),
        })

    items_out = []
    for iid in item_order:
        lid = item_lesson[iid]
        answered = len(item_answered_j.get(iid, set()))
        if answered == 0 and item_dropoff.get(iid, 0) == 0:
            continue
        fc = item_first_correct.get(iid, 0)
        acc = round(fc / answered, 3) if answered else None
        items_out.append({
            "item_id": iid,
            "lesson_id": lid,
            "answered": answered,
            "first_try_correct": fc,
            "accuracy": acc,
            "drop_off": item_dropoff.get(iid, 0),
        })

    paid_jids = set()
    for jid in jids:
        for t, props, eid in events_by_j[jid]:
            if t == "paid":
                paid_jids.add(jid)
    conversion_rate = round(len(paid_jids) / len(jids), 3) if jids else None
    conversion = {"journeys": len(jids), "paid": len(paid_jids), "rate": conversion_rate}

    finished_jids = set()
    for jid in jids:
        for t, props, eid in events_by_j[jid]:
            if t == "final_lesson_completed":
                finished_jids.add(jid)
    alert_jids = set(r[0] for r in db.query("SELECT DISTINCT journey_id FROM timeline_alerts"))
    # restrict to selected journeys
    alert_jids = alert_jids & set(jids)
    on_time_jids = {jid for jid in finished_jids if jid not in alert_jids}
    on_time_rate = round(len(on_time_jids) / len(finished_jids), 3) if finished_jids else None
    on_time = {"finished": len(finished_jids), "on_time": len(on_time_jids), "rate": on_time_rate}

    return {"lessons": lessons_out, "items": items_out, "conversion": conversion, "on_time": on_time}
