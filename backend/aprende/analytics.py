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
