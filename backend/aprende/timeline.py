"""Timeline engine for Aprende y Planea (pure projection)."""
import datetime
import json
import os
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from zoneinfo import ZoneInfo

import db
from aprende.notify import notify_staff

LA = ZoneInfo("America/Los_Angeles")
UTC = datetime.timezone.utc

DEFAULT_TURNAROUND = {"conflict_bd": 2, "scope_bd": 2, "review_bd": 3, "revise_bd": 2}


def load_settings(key):
    rows = db.query("SELECT value_json FROM settings WHERE key = ?", (key,))
    if not rows:
        return None
    try:
        return json.loads(rows[0][0])
    except (ValueError, TypeError):
        return None


def _parse_dt(value):
    if isinstance(value, datetime.datetime):
        dt = value
    else:
        dt = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _local_date(value):
    return _parse_dt(value).astimezone(LA).date()


def _is_biz(d, holidays):
    return d.weekday() < 5 and d.isoformat() not in holidays


def bd_add(d, n, holidays):
    cur = d
    count = 0
    while count < n:
        cur = cur + datetime.timedelta(days=1)
        if _is_biz(cur, holidays):
            count += 1
    return cur


def _build(facts, settings, holidays, now, changes):
    facts = facts or {}
    turnaround = (settings or {}).get("turnaround") or DEFAULT_TURNAROUND
    conflict_bd = int(turnaround.get("conflict_bd", 2))
    scope_bd = int(turnaround.get("scope_bd", 2))
    review_bd = int(turnaround.get("review_bd", 3))
    revise_bd = int(turnaround.get("revise_bd", 2))
    holidays_set = set(holidays or [])

    started_at = facts.get("started_at")
    start_date = _local_date(started_at)
    now_local = _parse_dt(now).astimezone(LA).date()

    changes_flag = bool(changes) or ("changes_requested" in facts)

    nominal_days = {
        "lesson_will": 1, "lesson_trust": 2, "lesson_ahcd": 3, "lesson_poa": 4,
        "pay": 5, "attorney_review": 8, "client_review": 9, "changes": 10,
        "signing": 13, "final_lesson": 14,
    }

    dates = {}

    lesson_map = {"lesson_will": "will", "lesson_trust": "trust", "lesson_ahcd": "ahcd", "lesson_poa": "poa"}
    for step, doc in lesson_map.items():
        key = "lesson_completed:" + doc
        if key in facts:
            dates[step] = _local_date(facts[key])
        else:
            dates[step] = start_date + datetime.timedelta(days=nominal_days[step] - 1)

    if "documents_tentative" in facts:
        scope_base = _local_date(facts["documents_tentative"]) - datetime.timedelta(days=1)
    else:
        scope_base = start_date
    if "names_submitted" in facts:
        conflict_base = _local_date(facts["names_submitted"]) - datetime.timedelta(days=1)
    else:
        conflict_base = start_date - datetime.timedelta(days=1)

    if "paid" in facts:
        pay_date = _local_date(facts["paid"])
    else:
        scope_done = bd_add(scope_base, scope_bd, holidays_set)
        conflict_done = bd_add(conflict_base, conflict_bd, holidays_set)
        pay_date = max(
            start_date + datetime.timedelta(days=4),
            scope_done + datetime.timedelta(days=1),
            conflict_done + datetime.timedelta(days=1),
        )
    dates["pay"] = pay_date

    if "attorney_approved" in facts:
        released_date = _local_date(facts["attorney_approved"])
    else:
        released_date = bd_add(pay_date, review_bd, holidays_set)
    dates["attorney_review"] = released_date

    review_date = released_date + datetime.timedelta(days=1)

    if "client_confirmed" in facts:
        client_review_date = _local_date(facts["client_confirmed"])
        confirm_date = client_review_date
        review_date = client_review_date
    else:
        if changes_flag:
            confirm_date = bd_add(review_date, revise_bd, holidays_set) + datetime.timedelta(days=1)
        else:
            confirm_date = review_date

    dates["client_review"] = review_date

    if changes_flag:
        if "changes_requested" in facts:
            changes_date = _local_date(facts["changes_requested"])
        else:
            changes_date = confirm_date
        dates["changes"] = changes_date

    if "signed" in facts:
        signing_date = _local_date(facts["signed"])
    else:
        cand1 = confirm_date + datetime.timedelta(days=1)
        cand2 = review_date + datetime.timedelta(days=3)
        signing_date = max(cand1, cand2)
        while not _is_biz(signing_date, holidays_set):
            signing_date = signing_date + datetime.timedelta(days=1)
        # a firm holiday that shifted the review clock also pushes signing when
        # the calendar math would otherwise land on the same day
        if holidays_set:
            nohol_released = bd_add(pay_date, review_bd, set())
            if nohol_released != released_date:
                signing_date = signing_date + datetime.timedelta(days=1)
                while not _is_biz(signing_date, holidays_set):
                    signing_date = signing_date + datetime.timedelta(days=1)
    dates["signing"] = signing_date

    if "final_lesson_completed" in facts:
        final_date = _local_date(facts["final_lesson_completed"])
    else:
        final_date = signing_date + datetime.timedelta(days=1)
    dates["final_lesson"] = final_date

    order = ["lesson_will", "lesson_trust", "lesson_ahcd", "lesson_poa", "pay",
             "attorney_review", "client_review"]
    if changes_flag:
        order.append("changes")
    order += ["signing", "final_lesson"]

    fact_for_step = {
        "lesson_will": "lesson_completed:will",
        "lesson_trust": "lesson_completed:trust",
        "lesson_ahcd": "lesson_completed:ahcd",
        "lesson_poa": "lesson_completed:poa",
        "pay": "paid",
        "attorney_review": "attorney_approved",
        "client_review": "client_confirmed",
        "changes": "changes_requested",
        "signing": "signed",
        "final_lesson": "final_lesson_completed",
    }

    steps_list = []
    for step in order:
        d = dates[step]
        day = (d - start_date).days + 1
        shifted = day - nominal_days[step]
        steps_list.append({
            "step": step,
            "day": day,
            "date": d.isoformat(),
            "due": d.isoformat(),
            "status": None,
            "shifted_days": shifted,
            "reason_key": None,
        })

    for s in steps_list:
        step = s["step"]
        fk = fact_for_step.get(step)
        if fk is not None and fk in facts:
            s["status"] = "done"
        elif s["date"] == now_local.isoformat():
            s["status"] = "today"
        elif datetime.date.fromisoformat(s["date"]) > now_local:
            s["status"] = "future"
        else:
            s["status"] = "past"

    next_set = False
    for s in steps_list:
        if s["status"] == "future" and not next_set:
            s["status"] = "next"
            next_set = True

    firm_steps = {"attorney_review", "changes"}
    for s in steps_list:
        if s["status"] == "past":
            if s["step"] in firm_steps:
                cond = False
                if s["step"] == "attorney_review" and "paid" in facts:
                    cond = True
                if s["step"] == "changes" and "changes_requested" in facts:
                    cond = True
                if cond and datetime.date.fromisoformat(s["due"]) < now_local:
                    s["status"] = "late"
                else:
                    s["status"] = "waiting"
            else:
                s["status"] = "waiting"

    if holidays_set:
        nohol = _build(facts, settings, [], now, changes)
        nohol_dates = {s["step"]: s["date"] for s in nohol}
        for s in steps_list:
            if s["shifted_days"] == 0:
                s["reason_key"] = None
            elif nohol_dates.get(s["step"]) != s["date"]:
                s["reason_key"] = "holiday"
            else:
                s["reason_key"] = "weekend"
    else:
        for s in steps_list:
            if s["shifted_days"] != 0:
                s["reason_key"] = "weekend"
            else:
                s["reason_key"] = None

    return steps_list


def plan(facts, settings, holidays, now, *, changes=False):
    return _build(facts, settings, holidays, now, changes)


def tick(now):
    import aprende.journey as journey

    turnaround = load_settings("turnaround")
    if turnaround is None:
        turnaround = DEFAULT_TURNAROUND
    holidays = load_settings("holidays")
    if holidays is None:
        holidays = []
    settings = {"turnaround": turnaround}

    now_dt = now
    if getattr(now_dt, "tzinfo", None) is None:
        now_dt = now_dt.replace(tzinfo=UTC)

    rows = db.query("SELECT id FROM journeys")
    for (jid,) in rows:
        j = journey.get_journey(jid)
        if not j:
            continue
        facts = dict(j.get("facts") or {})
        facts["started_at"] = j.get("started_at")
        tl = plan(facts, settings, holidays, now_dt)
        firm_steps = {"attorney_review", "changes"}
        for s in tl:
            if s["step"] not in firm_steps:
                continue
            if s["status"] != "late":
                continue
            due = s["due"]
            try:
                rc = db.execute(
                    "INSERT INTO timeline_alerts (id, journey_id, step, due, created_at) VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), jid, s["step"], due, now_dt.replace(tzinfo=None).isoformat()),
                )
            except Exception:
                rc = 0
            if rc and rc > 0:
                notify_staff("Timeline alert", f"Journey {jid}: {s['step']} is late (due {due}). Dashboard: /journey/{jid}")


try:
    import aprende.jobs as _jobs

    def _timeline_tick_handler(job):
        tick(datetime.datetime.now(UTC))

    _jobs.register("timeline_tick", _timeline_tick_handler)
except Exception:
    pass
