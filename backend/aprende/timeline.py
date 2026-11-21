"""Timeline engine (spec 6.3): when each step of a client's journey falls on the calendar, and which firm steps are late.

`plan` is pure. Days 1-4 are calendar days from the start in the client's time zone; firm steps count business days in
America/Los_Angeles with the firm's holiday list; every later step chains from what actually happened before it."""
import datetime
import json
import uuid
from zoneinfo import ZoneInfo

import db
from aprende import analytics, clock, jobs
from aprende.notify import notify_staff

LA = ZoneInfo("America/Los_Angeles")
UTC = datetime.timezone.utc
DAY = datetime.timedelta(days=1)
DEFAULT_TURNAROUND = {"conflict_bd": 2, "scope_bd": 2, "scope_change_bd": 1, "review_bd": 3, "revise_bd": 2}
NOMINAL = {"lesson_will": 1, "lesson_trust": 2, "lesson_ahcd": 3, "lesson_poa": 4, "pay": 5, "attorney_review": 8,
           "client_review": 9, "changes": 10, "signing": 13, "final_lesson": 14}
DONE_BY = {"lesson_will": "lesson_completed:will", "lesson_trust": "lesson_completed:trust",
           "lesson_ahcd": "lesson_completed:ahcd", "lesson_poa": "lesson_completed:poa", "pay": "paid",
           "attorney_review": "attorney_approved", "client_review": "client_confirmed", "changes": "changes_requested",
           "signing": "signed", "final_lesson": "final_lesson_completed"}


def _local(iso):
    t = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    return (t if t.tzinfo else t.replace(tzinfo=UTC)).astimezone(LA).date()


class _Calendar:
    """Business days. `weekends=False` and no holidays give the plain-calendar baseline used to explain shifts."""
    def __init__(self, holidays=(), weekends=True):
        self.holidays, self.weekends = set(holidays), weekends

    def business(self, d):
        return (d.weekday() < 5 or not self.weekends) and d.isoformat() not in self.holidays

    def add(self, d, n):
        """The n-th business day after d (d itself not counted)."""
        while n:
            d += DAY
            n -= self.business(d)
        return d

    def next_business(self, d):
        while not self.business(d):
            d += DAY
        return d


def _dates(facts, turnaround, cal, changes):
    """{step: (date, due)} — `due` only for the firm's steps."""
    t = {**DEFAULT_TURNAROUND, **(turnaround or {})}
    start = _local(facts["started_at"])
    on = lambda key, fallback: _local(facts[key]) if key in facts else fallback
    out = {}
    for step, doc in (("lesson_will", "will"), ("lesson_trust", "trust"), ("lesson_ahcd", "ahcd"), ("lesson_poa", "poa")):
        out[step] = (on(f"lesson_completed:{doc}", start + (NOMINAL[step] - 1) * DAY), None)
    reopened = facts.get("scope_reopened_latest", facts.get("scope_reopened"))
    if reopened:                                       # a changed choice restarts the attorney's scope review (spec 6.2)
        scope_done = cal.add(_local(reopened), t["scope_change_bd"])
    else:
        scope_done = cal.add(on("documents_tentative", start + DAY) - DAY, t["scope_bd"])
    conflict_done = cal.add(on("names_submitted", start) - DAY, t["conflict_bd"])
    pay = on("paid", max(start + 4 * DAY, scope_done + DAY, conflict_done + DAY))
    out["pay"] = (pay, None)
    review_due = cal.add(pay, t["review_bd"])
    released = on("attorney_approved", review_due)
    out["attorney_review"] = (released, review_due)
    review = on("client_confirmed", released + DAY) if not changes else released + DAY
    out["client_review"] = (review, None)
    confirm = review
    if changes:
        asked = on("changes_requested", review)
        revise_due = cal.add(asked, t["revise_bd"])
        confirm = on("client_confirmed", revise_due + DAY)
        out["changes"] = (confirm, revise_due)
    signing = on("signed", cal.next_business(max(confirm + DAY, review + 3 * DAY)))
    out["signing"] = (signing, None)
    out["final_lesson"] = (on("final_lesson_completed", signing + DAY), None)
    return out


def plan(facts, settings, holidays, now, *, changes=False):
    changes = changes or "changes_requested" in facts
    turnaround = (settings or {}).get("turnaround")
    real = _dates(facts, turnaround, _Calendar(holidays), changes)
    no_holidays = _dates(facts, turnaround, _Calendar(), changes)
    plain = _dates(facts, turnaround, _Calendar(weekends=False), changes)
    start, today = _local(facts["started_at"]), now.astimezone(LA).date()
    steps, found_next = [], False
    for step, (date, due) in real.items():
        day = (date - start).days + 1
        reason = None
        if day != NOMINAL[step]:
            reason = "holiday" if date != no_holidays[step][0] else "weekend" if date != plain[step][0] else None
        if DONE_BY[step] in facts and not (step == "client_review" and changes and "changes_requested" in facts
                                           and "client_confirmed" not in facts):
            status = "done"
        elif due and today > due and (step != "attorney_review" or "paid" in facts) \
                and (step != "changes" or "changes_requested" in facts):
            status = "late"
        elif date == today:
            status = "today"
        elif date > today and not found_next:
            status, found_next = "next", True
        else:
            status = "waiting"
        steps.append({"step": step, "day": day, "date": date.isoformat(), "due": due.isoformat() if due else None,
                      "status": status, "shifted_days": day - NOMINAL[step], "reason_key": reason})
    return steps


def _setting(key, default):
    rows = db.query("SELECT value_json FROM settings WHERE key = ?", (key,))
    return json.loads(rows[0][0]) if rows else default


def for_journey(j, now):
    """The client-facing timeline of a journey as `journey.get_journey` returns it."""
    facts = {**j["facts"], "started_at": j["started_at"]}
    return plan(facts, {"turnaround": _setting("turnaround", DEFAULT_TURNAROUND)}, _setting("holidays", []), now)


def _firm_clocks(facts, turnaround, holidays):
    """The firm's background clocks that are not steps on the client's map: (name, due) for each still open."""
    t, cal, out = {**DEFAULT_TURNAROUND, **(turnaround or {})}, _Calendar(holidays), []
    if "names_submitted" in facts and "conflict_firm" not in facts:
        out.append(("conflict_review", cal.add(_local(facts["names_submitted"]) - DAY, t["conflict_bd"])))
    if "documents_tentative" in facts and "scope_approved" not in facts:
        out.append(("scope_review", cal.add(_local(facts["documents_tentative"]) - DAY, t["scope_bd"])))
    return out


def tick(now):
    """Record each newly late firm step once (the dashboard flag) and alert staff once for it."""
    from aprende import journey
    turnaround, holidays = _setting("turnaround", DEFAULT_TURNAROUND), _setting("holidays", [])
    today = now.astimezone(LA).date()
    for (jid,) in db.query("SELECT id FROM journeys"):
        j = journey.get_journey(jid)
        facts = {**j["facts"], "started_at": j["started_at"]}
        late = [(s["step"], s["due"]) for s in plan(facts, {"turnaround": turnaround}, holidays, now) if s["status"] == "late"]
        late += [(name, due.isoformat()) for name, due in _firm_clocks(facts, turnaround, holidays) if today > due]
        for step, due in late:
            new = db.execute("INSERT INTO timeline_alerts (id, journey_id, step, due, created_at) VALUES (?, ?, ?, ?, ?) "
                             "ON CONFLICT (journey_id, step, due) DO NOTHING",
                             (str(uuid.uuid4()), jid, step, due, now.astimezone(UTC).replace(tzinfo=None).isoformat()))
            if new:
                analytics.record(jid, "step_late", {"step": step})
                notify_staff("Paso atrasado", f"{step} venció el {due}. Expediente: /dashboard#journey={jid}")


def _tick_job(job):
    """Hourly: run the tick, then queue the next hour's (the job key makes each hour's job unique)."""
    now = clock.now()
    tick(now)
    schedule(now + datetime.timedelta(hours=1))


def schedule(at):
    jobs.enqueue("timeline_tick", f"timeline_tick:{at:%Y-%m-%dT%H}", run_after=at.replace(minute=0, second=0, microsecond=0))


jobs.register("timeline_tick", _tick_job)
