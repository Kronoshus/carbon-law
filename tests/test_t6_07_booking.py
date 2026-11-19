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

import threading
from zoneinfo import ZoneInfo

from aprende import booking

LA = ZoneInfo("America/Los_Angeles")
ALL_DAY = {d: [["00:00", "05:00"], ["09:00", "17:00"]] for d in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")}


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    now = {"t": datetime.datetime(2027, 3, 10, 12, 0, tzinfo=datetime.timezone.utc)}
    monkeypatch.setattr(booking, "now", lambda: now["t"])
    return now


@pytest.fixture
def sent(monkeypatch):
    out = {"staff": [], "client": []}
    monkeypatch.setattr(booking, "notify_staff", lambda title, message: out["staff"].append(message))
    monkeypatch.setattr(booking, "send_confirmation", lambda to, subject, body: out["client"].append((to, subject, body)))
    return out


def setup(holidays=()):
    r = c.put("/staff/availability", json={"hours": ALL_DAY, "slot_minutes": {"signing": 60, "consultation": 30}}, headers=staff())
    assert r.status_code == 200, r.text
    assert c.put("/staff/holidays", json={"dates": list(holidays)}, headers=staff()).status_code == 200


def lessons_done():
    h = client()
    jid = state(h)["id"]
    for doc in ("will", "trust", "ahcd", "poa"):
        journey.apply(jid, f"lesson_completed:{doc}", {}, actor="system")
    return h, jid


def slots(h, kind, day, days=1):
    r = c.get(f"/booking/slots?kind={kind}&from={day}&days={days}", headers=h)
    assert r.status_code == 200, r.text
    return r.json()["slots"]


def local_times(ss):
    return [s["local"][11:16] for s in ss]


def utc(y, m, d, hh, mm=0):
    return datetime.datetime(y, m, d, hh, mm, tzinfo=LA).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_staff_set_the_hours_clients_cannot():
    h = client()
    assert c.put("/staff/availability", json={"hours": ALL_DAY, "slot_minutes": {"signing": 60, "consultation": 30}}, headers=h).status_code == 403
    assert c.put("/staff/availability", json={"hours": {"mon": [["17:00", "09:00"]]}, "slot_minutes": {"signing": 60, "consultation": 30}},
                 headers=staff()).status_code == 422


def test_the_spring_forward_gap_is_never_offered():
    setup()
    h, _ = lessons_done()
    times = local_times(slots(h, "consultation", "2027-03-14"))          # clocks jump from 2:00 to 3:00 that night
    assert times[:8] == ["00:00", "00:30", "01:00", "01:30", "03:00", "03:30", "04:00", "04:30"]
    assert "02:00" not in times and "02:30" not in times


def test_times_are_stored_in_utc_and_shown_in_los_angeles():
    setup()
    h, _ = lessons_done()
    s = slots(h, "consultation", "2027-03-16")[0]
    assert s["local"].startswith("2027-03-16T00:00") and s["start"] == utc(2027, 3, 16, 0)


def test_a_firm_holiday_has_no_slots():
    setup(holidays=["2027-03-16"])
    h, _ = lessons_done()
    assert slots(h, "consultation", "2027-03-16") == []
    assert slots(h, "consultation", "2027-03-17") != []


def test_past_times_are_not_offered(clock):
    setup()
    clock["t"] = datetime.datetime.fromisoformat(utc(2027, 3, 16, 10).replace("Z", "+00:00"))
    h, _ = lessons_done()
    assert all(t >= "10:30" for t in local_times(slots(h, "consultation", "2027-03-16")))


def test_a_consultation_needs_the_four_core_lessons(sent):
    setup()
    h = client()
    r = c.post("/booking", json={"kind": "consultation", "start": utc(2027, 3, 16, 9)}, headers=h)
    assert r.status_code == 409 and r.json()["missing"] == ["core_lessons"]
    h2, _ = lessons_done()
    assert c.post("/booking", json={"kind": "consultation", "start": utc(2027, 3, 16, 9)}, headers=h2).status_code == 200


def test_signing_needs_the_client_to_have_confirmed_the_documents(sent):
    setup()
    h, jid = lessons_done()
    r = c.post("/booking", json={"kind": "signing", "start": utc(2027, 3, 16, 11)}, headers=h)
    assert r.status_code == 409 and r.json()["missing"] == ["may_book_signing"]
    for ev, p in (("ai_disclosed", {}), ("consent", {"answer": "yes"}), ("names_submitted", {"names": ["Ana Torres"]}),
                  ("conflict_auto", {"result": "clear"}), ("conflict_firm", {"result": "cleared"}), ("scope_approved", {}),
                  ("engagement_signed", {}), ("paid", {}), ("drafts_ready", {}),
                  ("attorney_approved", {}), ("client_confirmed", {})):
        journey.apply(jid, ev, p, actor="system")
    r = c.post("/booking", json={"kind": "signing", "start": utc(2027, 3, 16, 11)}, headers=h)    # 9:00 is taken above
    assert r.status_code == 200, r.text
    assert "signing_booked" in state(h)["facts"]


def test_a_start_that_is_not_an_offered_slot_is_refused(sent):
    setup()
    h, _ = lessons_done()
    assert c.post("/booking", json={"kind": "consultation", "start": utc(2027, 3, 16, 9, 10)}, headers=h).status_code == 422
    assert c.post("/booking", json={"kind": "consultation", "start": utc(2027, 3, 16, 7)}, headers=h).status_code == 422


def test_no_double_booking_under_concurrent_requests(sent):
    setup()
    clients = [lessons_done()[0] for _ in range(6)]
    codes = []
    def book(h):
        codes.append(c.post("/booking", json={"kind": "consultation", "start": utc(2027, 3, 17, 9)}, headers=h).status_code)
    threads = [threading.Thread(target=book, args=(h,)) for h in clients]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert sorted(codes) == [200] + [409] * 5


def test_overlapping_lengths_cannot_share_time(sent):
    setup()
    h, _ = lessons_done()
    assert c.post("/booking", json={"kind": "consultation", "start": utc(2027, 3, 18, 9, 30)}, headers=h).status_code == 200
    h2, _ = lessons_done()
    starts = [s["start"] for s in slots(h2, "consultation", "2027-03-18")]
    assert utc(2027, 3, 18, 9, 30) not in starts and utc(2027, 3, 18, 9) in starts


def test_cancel_frees_the_slot_and_only_the_owner_may_cancel(sent):
    setup()
    h, _ = lessons_done()
    b = c.post("/booking", json={"kind": "consultation", "start": utc(2027, 3, 19, 9)}, headers=h).json()
    other, _ = lessons_done()
    assert c.delete(f"/booking/{b['id']}", headers=other).status_code == 404
    assert c.delete(f"/booking/{b['id']}", headers=h).status_code == 200
    assert utc(2027, 3, 19, 9) in [s["start"] for s in slots(other, "consultation", "2027-03-19")]


def test_no_changes_within_24_hours(sent, clock):
    setup()
    h, _ = lessons_done()
    b = c.post("/booking", json={"kind": "consultation", "start": utc(2027, 3, 11, 9)}, headers=h).json()
    clock["t"] = datetime.datetime.fromisoformat(utc(2027, 3, 10, 10).replace("Z", "+00:00"))     # 23 hours before
    assert c.delete(f"/booking/{b['id']}", headers=h).status_code == 409
    assert c.patch(f"/booking/{b['id']}", json={"start": utc(2027, 3, 12, 9)}, headers=h).status_code == 409


def test_reschedule_is_all_or_nothing(sent):
    setup()
    h, _ = lessons_done()
    other, _ = lessons_done()
    mine = c.post("/booking", json={"kind": "consultation", "start": utc(2027, 3, 22, 9)}, headers=h).json()
    c.post("/booking", json={"kind": "consultation", "start": utc(2027, 3, 22, 10)}, headers=other)
    assert c.patch(f"/booking/{mine['id']}", json={"start": utc(2027, 3, 22, 10)}, headers=h).status_code == 409
    assert [b["start"] for b in c.get("/booking", headers=h).json()] == [utc(2027, 3, 22, 9)]       # the old one is kept
    assert c.patch(f"/booking/{mine['id']}", json={"start": utc(2027, 3, 22, 11)}, headers=h).status_code == 200
    assert [b["start"] for b in c.get("/booking", headers=h).json()] == [utc(2027, 3, 22, 11)]
    assert utc(2027, 3, 22, 9) in [s["start"] for s in slots(other, "consultation", "2027-03-22")]


def test_confirmations_go_out_once_and_staff_alerts_carry_no_name(sent):
    setup()
    h, _ = lessons_done()
    email = c.get("/auth/me", headers=h).json()["email"]
    c.post("/booking", json={"kind": "consultation", "start": utc(2027, 3, 23, 9)}, headers=h)
    assert len(sent["client"]) == 1 and sent["client"][0][0] == email
    assert "9:00" in sent["client"][0][2] and "2027" in sent["client"][0][2]
    assert len(sent["staff"]) == 1 and "Ana" not in sent["staff"][0]


def test_staff_see_every_booking():
    setup()
    h, _ = lessons_done()
    c.post("/booking", json={"kind": "consultation", "start": utc(2027, 3, 24, 9)}, headers=h)
    rows = c.get("/staff/bookings?from=2027-03-24&days=1", headers=staff()).json()
    assert any(r["start"] == utc(2027, 3, 24, 9) and r["client_name"] == "Ana Torres" for r in rows)
    assert c.get("/staff/bookings?from=2027-03-24&days=1", headers=h).status_code == 403


def test_slots_say_why_a_kind_is_locked():
    setup()
    h = client()
    r = c.get("/booking/slots?kind=signing&from=2027-03-16&days=1", headers=h)
    assert r.status_code == 409 and r.json()["missing"] == ["may_book_signing"]
    r = c.get("/booking/slots?kind=consultation&from=2027-03-16&days=1", headers=h)
    assert r.status_code == 409 and r.json()["missing"] == ["core_lessons"]


def test_changing_the_hours_keeps_existing_bookings(sent):
    setup()
    h, _ = lessons_done()
    c.post("/booking", json={"kind": "consultation", "start": utc(2027, 3, 25, 9)}, headers=h)
    setup()
    assert [b["start"] for b in c.get("/booking", headers=h).json()] == [utc(2027, 3, 25, 9)]
