"""Staff views of Aprende journeys (spec 11)."""
import datetime

from fastapi import APIRouter, Header, HTTPException

import app as backend_app
import db
from aprende import journey, legacy, timeline

router = APIRouter()


@router.get("/staff/journeys")
def list_journeys(authorization: str = Header(None)):
    """Every journey with its late firm steps, the most late first (T6-09)."""
    if not authorization:
        raise HTTPException(401, "not authenticated")
    backend_app.require_auth(authorization, {"paralegal", "attorney", "admin"})
    now = datetime.datetime.now(datetime.timezone.utc)
    rows = []
    for (jid,) in db.query("SELECT id FROM journeys"):
        j = journey.get_journey(jid)
        steps = timeline.for_journey(j, now)
        late = [s for s in steps if s["status"] == "late"]
        upcoming = next((s for s in steps if s["status"] != "done"), steps[-1])
        rows.append({"journey_id": jid, "client_name": legacy._user_name(j["user_id"]), "day": j["day"],
                     "next_step": upcoming["step"], "late": [s["step"] for s in late],
                     "due": min(s["due"] for s in late) if late else upcoming["due"] or upcoming["date"]})
    return sorted(rows, key=lambda r: (-len(r["late"]), r["due"] if r["late"] else "9999"))


import json

@router.get("/staff/analytics")
def staff_analytics(since: str = None, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    backend_app.require_auth(authorization, {"paralegal", "attorney", "admin"})
    if since:
        jids = [r[0] for r in db.query("SELECT id FROM journeys WHERE started_at >= ?", (since,))]
    else:
        jids = [r[0] for r in db.query("SELECT id FROM journeys")]
    jset = set(jids)

    events_by_j = {jid: [] for jid in jids}
    for jid in jids:
        rows = db.query("SELECT type, props_json, created_at, id FROM events WHERE journey_id = ?", (jid,))
        rows = sorted(rows, key=lambda r: (r[2] or "", r[3] or ""))
        for t, pj, ca, eid in rows:
            try:
                props = json.loads(pj) if pj else {}
            except (ValueError, TypeError):
                props = {}
            events_by_j[jid].append((t, props, eid))

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
    on_time_jids = {jid for jid in finished_jids if jid not in alert_jids}
    on_time_rate = round(len(on_time_jids) / len(finished_jids), 3) if finished_jids else None
    on_time = {"finished": len(finished_jids), "on_time": len(on_time_jids), "rate": on_time_rate}

    return {"lessons": lessons_out, "items": items_out, "conversion": conversion, "on_time": on_time}
