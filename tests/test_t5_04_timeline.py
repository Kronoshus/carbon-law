import datetime
import json
import os
import sys
import tempfile
import uuid

os.environ.setdefault("DATABASE_URL", "")
os.environ.setdefault("CARBON_DB_PATH", tempfile.mktemp(suffix=".db"))
sys.path.insert(0, "backend")

import pytest
from fastapi.testclient import TestClient

import app as backend
import migrate
import db
from aprende import journey

migrate.run()
c = TestClient(backend.app)

STAFF_EMAIL = "p5-staff@example.com"
backend.users[STAFF_EMAIL] = {"id": str(uuid.uuid4()), "name": "P5 Staff", "email": STAFF_EMAIL, "role": "paralegal",
                              "password_hash": backend.hash_pw("p5-staff-password"),
                              "created_at": datetime.datetime.utcnow().isoformat()}


def staff():
    token = c.post("/auth/login", json={"email": STAFF_EMAIL, "password": "p5-staff-password"}).json()["token"]
    return {"Authorization": "Bearer " + token}


def client():
    body = {"name": "Ana Torres", "email": f"ana-{uuid.uuid4().hex[:8]}@example.com", "password": "long-secure-password",
            "source": "aprende", "adult": True}
    r = c.post("/auth/signup", json=body)
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def send(h, type_, **payload):
    return c.post("/journey/events", json={"type": type_, "payload": payload}, headers=h)


def state(h):
    r = c.get("/journey", headers=h)
    assert r.status_code == 200, r.text
    return r.json()

from zoneinfo import ZoneInfo

from aprende import timeline

LA = ZoneInfo("America/Los_Angeles")
SETTINGS = {"turnaround": {"conflict_bd": 2, "scope_bd": 2, "review_bd": 3, "revise_bd": 2}}
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def at(y, m, d, hh=10, mm=0):
    """A local Los Angeles time, as the UTC ISO string the journey stores."""
    t = datetime.datetime(y, m, d, hh, mm, tzinfo=LA).astimezone(datetime.timezone.utc)
    return t.replace(tzinfo=None).isoformat()


def utc(iso):
    return datetime.datetime.fromisoformat(iso).replace(tzinfo=datetime.timezone.utc)


def steps(facts, now, holidays=(), changes=False):
    out = timeline.plan(facts, SETTINGS, list(holidays), utc(now), changes=changes)
    return {s["step"]: s for s in out}


def wd(iso_date):
    return WEEKDAYS[datetime.date.fromisoformat(iso_date).weekday()]


def total(s, start):
    return (datetime.date.fromisoformat(s["final_lesson"]["date"]) - start).days + 1


# spec 6.3: client starts on | pays on | drafts released | total days, no changes | total days, with changes
TABLE = [("Mon", "Fri", "Wed", 16, 18), ("Tue", "Sat", "Wed", 15, 17), ("Wed", "Sun", "Wed", 14, 16),
         ("Thu", "Tue", "Fri", 14, 16), ("Fri", "Wed", "Mon", 16, 19), ("Sat", "Wed", "Mon", 15, 18),
         ("Sun", "Thu", "Tue", 17, 17)]


@pytest.mark.parametrize("offset,row", list(enumerate(TABLE)))
def test_the_spec_table_for_every_start_weekday(offset, row):
    start = datetime.date(2026, 11, 30) + datetime.timedelta(days=offset)      # Monday 30 Nov 2026 + offset
    assert WEEKDAYS[start.weekday()] == row[0]
    now = at(start.year, start.month, start.day)
    plain = steps({"started_at": now}, now)
    assert wd(plain["pay"]["date"]) == row[1]
    assert wd(plain["attorney_review"]["date"]) == row[2]
    assert total(plain, start) == row[3]
    assert total(steps({"started_at": now}, now, changes=True), start) == row[4]


def test_the_steps_in_order_with_their_nominal_days():
    now = at(2026, 12, 2)
    s = timeline.plan({"started_at": now}, SETTINGS, [], utc(now))
    assert [x["step"] for x in s] == ["lesson_will", "lesson_trust", "lesson_ahcd", "lesson_poa", "pay",
                                      "attorney_review", "client_review", "signing", "final_lesson"]
    assert [x["day"] for x in s] == [1, 2, 3, 4, 5, 8, 9, 13, 14]           # a Wednesday start is the on-time case
    assert all(x["shifted_days"] == 0 and x["reason_key"] is None for x in s)
    with_changes = timeline.plan({"started_at": now}, SETTINGS, [], utc(now), changes=True)
    assert "changes" in [x["step"] for x in with_changes]


def test_a_weekend_that_moves_a_date_says_so():
    now = at(2026, 11, 30)                                                     # Monday
    s = steps({"started_at": now}, now)
    assert s["pay"]["date"] == "2026-12-04" and s["pay"]["shifted_days"] == 0
    assert s["attorney_review"]["date"] == "2026-12-09" and s["attorney_review"]["day"] == 10
    assert s["attorney_review"]["shifted_days"] == 2 and s["attorney_review"]["reason_key"] == "weekend"
    assert s["client_review"]["date"] == "2026-12-10" and s["client_review"]["shifted_days"] == 2
    assert s["signing"]["date"] == "2026-12-14" and s["signing"]["reason_key"] == "weekend"


def test_a_firm_holiday_shifts_only_the_steps_after_it():
    now = at(2026, 12, 2)                                                      # Wednesday: on time without the holiday
    s = steps({"started_at": now}, now, holidays=["2026-12-08"])
    assert s["pay"]["date"] == "2026-12-06" and s["pay"]["shifted_days"] == 0
    assert s["attorney_review"]["date"] == "2026-12-10"
    assert s["attorney_review"]["shifted_days"] == 1 and s["attorney_review"]["reason_key"] == "holiday"
    assert s["client_review"]["date"] == "2026-12-11" and s["client_review"]["reason_key"] == "holiday"
    assert s["signing"]["date"] == "2026-12-14"          # the weekend before signing absorbs the holiday's day


def test_later_days_follow_what_actually_happened():
    start = at(2026, 12, 2)
    facts = {"started_at": start, "paid": at(2026, 12, 6, 11), "attorney_approved": at(2026, 12, 7, 15)}
    s = steps(facts, at(2026, 12, 7, 16))
    assert s["pay"]["status"] == "done" and s["attorney_review"]["status"] == "done"
    assert s["attorney_review"]["date"] == "2026-12-07"                        # early: released Monday
    assert s["client_review"]["date"] == "2026-12-08"


def test_a_firm_step_past_its_due_date_is_late():
    start = at(2026, 12, 2)
    facts = {"started_at": start, "paid": at(2026, 12, 6, 11)}
    s = steps(facts, at(2026, 12, 11))
    assert s["attorney_review"]["due"] == "2026-12-09"
    assert s["attorney_review"]["status"] == "late"


def test_the_clients_own_steps_are_never_late():
    start = at(2026, 12, 2)
    s = steps({"started_at": start}, at(2026, 12, 20))                         # nothing done for weeks
    for key in ("lesson_will", "lesson_trust", "lesson_ahcd", "lesson_poa", "pay", "client_review"):
        assert s[key]["status"] != "late", key


@pytest.mark.parametrize("dst_sat,plain_sat", [((2026, 10, 31), (2026, 11, 7)),   # clocks go back Sunday 1 Nov
                                               ((2026, 3, 7), (2026, 3, 14))])     # clocks go forward Sunday 8 Mar
def test_dst_weeks_do_not_shift_dates(dst_sat, plain_sat):
    a_now, b_now = at(*dst_sat, 23, 30), at(*plain_sat, 23, 30)                # late evening: UTC is already Sunday
    a, b = steps({"started_at": a_now}, a_now), steps({"started_at": b_now}, b_now)
    assert a["lesson_will"]["date"] == "%04d-%02d-%02d" % dst_sat
    for key in a:
        shift = (datetime.date.fromisoformat(b[key]["date"]) - datetime.date.fromisoformat(a[key]["date"])).days
        assert shift == 7, key


@pytest.fixture
def alerts(monkeypatch):
    sent = []
    monkeypatch.setattr(timeline, "notify_staff", lambda title, message: sent.append((title, message)))
    return sent


def paid_journey(monkeypatch):
    clock = {"now": at(2026, 12, 2)}
    monkeypatch.setattr(journey, "_now_iso", lambda: clock["now"])
    h = client()
    j = state(h)
    send(h, "ai_disclosed"); send(h, "consent", answer="yes"); send(h, "names_submitted", names=["Ana Torres"])
    for ev, payload in (("conflict_auto", {"result": "clear"}), ("conflict_firm", {"result": "cleared"}),
                        ("scope_approved", {}), ("engagement_signed", {})):
        journey.apply(j["id"], ev, payload, actor="system")
    clock["now"] = at(2026, 12, 6, 11)
    journey.apply(j["id"], "paid", {}, actor="stripe")
    return h, j["id"]


def test_a_late_review_raises_one_alert_and_one_flag(monkeypatch, alerts):
    h, jid = paid_journey(monkeypatch)
    mine = lambda: [a for a in alerts if jid in a[1]]                           # the alert links to the journey
    timeline.tick(utc(at(2026, 12, 9, 12)))                                    # due today: not late yet
    assert mine() == []
    timeline.tick(utc(at(2026, 12, 10, 9)))
    timeline.tick(utc(at(2026, 12, 10, 10)))
    timeline.tick(utc(at(2026, 12, 11, 9)))
    assert len(mine()) == 1 and "Ana Torres" not in mine()[0][1]
    assert db.query("SELECT COUNT(*) FROM timeline_alerts WHERE journey_id = ?", (jid,))[0][0] == 1


def test_the_client_journey_carries_the_timeline(monkeypatch, alerts):
    h, jid = paid_journey(monkeypatch)
    tl = state(h)["timeline"]
    assert [s["step"] for s in tl][:5] == ["lesson_will", "lesson_trust", "lesson_ahcd", "lesson_poa", "pay"]
    assert all({"step", "day", "date", "due", "status", "shifted_days", "reason_key"} <= set(s) for s in tl)


def test_status_is_one_of_the_five_and_there_is_one_next():
    start = at(2026, 12, 2)
    for now in (start, at(2026, 12, 4), at(2026, 12, 20)):
        s = timeline.plan({"started_at": start}, SETTINGS, [], utc(now))
        assert {x["status"] for x in s} <= {"done", "today", "next", "waiting", "late"}
        assert [x["status"] for x in s].count("next") <= 1


def test_a_client_delay_is_not_called_a_weekend():
    start = at(2026, 12, 2)                                                    # Wednesday
    s = steps({"started_at": start, "lesson_completed:will": at(2026, 12, 4)}, at(2026, 12, 4, 12))
    assert s["lesson_will"]["shifted_days"] == 2 and s["lesson_will"]["reason_key"] is None


def test_only_firm_steps_have_a_due_date():
    start = at(2026, 12, 2)
    s = steps({"started_at": start, "paid": at(2026, 12, 6, 11), "attorney_approved": at(2026, 12, 7, 15)}, at(2026, 12, 7, 16))
    assert s["attorney_review"]["due"] == "2026-12-09"                         # the deadline, not the early release
    assert all(s[k]["due"] is None for k in ("lesson_will", "pay", "client_review", "signing", "final_lesson"))


def test_an_open_conflict_review_past_its_due_date_alerts_once(monkeypatch, alerts):
    clock = {"now": at(2026, 12, 2)}
    monkeypatch.setattr(journey, "_now_iso", lambda: clock["now"])
    h = client()
    jid = state(h)["id"]
    send(h, "ai_disclosed"); send(h, "consent", answer="yes"); send(h, "names_submitted", names=["Ana Torres"])
    mine = lambda: [a for a in alerts if jid in a[1]]
    timeline.tick(utc(at(2026, 12, 3, 17)))                                    # due Thursday 3 Dec: not late that day
    assert mine() == []
    timeline.tick(utc(at(2026, 12, 4, 9)))
    timeline.tick(utc(at(2026, 12, 7, 9)))
    assert len(mine()) == 1 and "conflict_review" in mine()[0][1]


ATTORNEY_EMAIL = "t5-04-attorney@example.com"
backend.users[ATTORNEY_EMAIL] = {"id": str(uuid.uuid4()), "name": "Pankaj Raval", "email": ATTORNEY_EMAIL, "role": "attorney",
                                 "password_hash": backend.hash_pw("t5-04-attorney-password"),
                                 "created_at": datetime.datetime.utcnow().isoformat()}


def attorney():
    token = c.post("/auth/login", json={"email": ATTORNEY_EMAIL, "password": "t5-04-attorney-password"}).json()["token"]
    return {"Authorization": "Bearer " + token}


def test_an_on_time_wednesday_journey_raises_no_scope_alert(monkeypatch, alerts):
    """Spec 6.1 day 2: the tentative choice "starts the attorney's scope review now, so the engagement letter is ready on
    day 5"; 6.2: "Day 2 gives the attorney days 2-4". A Wednesday client chooses on Thursday, the review is due Friday,
    and the attorney approves on Friday, before she confirms the same documents on Saturday (day 4)."""
    clock = {"now": at(2026, 12, 2)}                                             # Wednesday, day 1
    monkeypatch.setattr(journey, "_now_iso", lambda: clock["now"])
    h = client()
    jid = state(h)["id"]
    send(h, "ai_disclosed"); send(h, "consent", answer="yes"); send(h, "names_submitted", names=["Ana Torres"])
    journey.apply(jid, "conflict_auto", {"result": "clear"}, actor="system")
    clock["now"] = at(2026, 12, 3)                                               # Thursday, day 2
    send(h, "documents_tentative", codes=["will", "trust"])
    journey.apply(jid, "conflict_firm", {"result": "cleared"}, actor="staff@example.com")
    clock["now"] = at(2026, 12, 4)                                               # Friday, day 3: the scope review's due date
    assert steps({**state(h)["facts"], "started_at": state(h)["started_at"]}, clock["now"])["pay"]["date"] == "2026-12-06"
    assert c.post(f"/staff/journeys/{jid}/scope-approval", headers=attorney()).status_code == 200
    clock["now"] = at(2026, 12, 5)                                               # Saturday, day 4: she confirms the same two
    send(h, "documents_confirmed", codes=["trust", "will"])
    for day in (3, 4, 5, 6, 7):
        timeline.tick(utc(at(2026, 12, day, 9)))
    assert [a for a in alerts if jid in a[1]] == []
    clock["now"] = at(2026, 12, 6)                                               # Sunday, day 5: the letter is ready
    j = state(h)
    assert j["gates"]["may_sign_engagement"] is True and "scope_reopened" not in j["facts"]
