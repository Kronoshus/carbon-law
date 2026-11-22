"""T8-03 acceptance (Opus, p8-tests): push subscriptions only after the client turns reminders on; the daily lesson
nudge; the appointment reminder 24 hours before; the yearly review reminder after funding. Staff alerts carry no names.
Delivery to the push service is stubbed (`push._deliver`); email is stubbed (`reminders.send_email`)."""
import base64
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
from zoneinfo import ZoneInfo

import app as backend
import migrate
import db
from aprende import journey, jobs

migrate.run()
c = TestClient(backend.app)

from aprende import booking   # noqa: E402

push = reminders = None          # new in T8-03; imported per test so this file collects before they exist

LA = ZoneInfo("America/Los_Angeles")
UTC = datetime.timezone.utc
STAFF_EMAIL = "p8-staff@example.com"
backend.users[STAFF_EMAIL] = {"id": str(uuid.uuid4()), "name": "P8 Staff", "email": STAFF_EMAIL, "role": "paralegal",
                              "password_hash": backend.hash_pw("p8-staff-password"),
                              "created_at": datetime.datetime.utcnow().isoformat()}
ALL_DAY = {d: [["09:00", "17:00"]] for d in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")}
SUB = {"endpoint": "https://fcm.googleapis.com/fcm/send/ana-device-1", "keys": {"p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM", "auth": "tBHItJI5svbpez7KI4CCXg"}, "lang": "es"}


def staff():
    token = c.post("/auth/login", json={"email": STAFF_EMAIL, "password": "p8-staff-password"}).json()["token"]
    return {"Authorization": "Bearer " + token}


def client(name="Ana Torres"):
    body = {"name": name, "email": f"ana-{uuid.uuid4().hex[:8]}@example.com", "password": "long-secure-password",
            "source": "aprende", "adult": True}
    r = c.post("/auth/signup", json=body)
    assert r.status_code == 200, r.text
    h = {"Authorization": "Bearer " + r.json()["token"]}
    return h, c.get("/journey", headers=h).json()["id"]


def utc(y, m, d, hh, mm=0):
    return datetime.datetime(y, m, d, hh, mm, tzinfo=LA).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def at(iso):
    t = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=UTC)                          # journey facts are naive UTC


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    global push, reminders
    from aprende import push, reminders      # noqa: F811  (reminders registers its jobs on import)
    now = {"t": datetime.datetime(2027, 3, 10, 12, 0, tzinfo=UTC)}
    monkeypatch.setattr(booking, "now", lambda: now["t"])
    monkeypatch.setattr(reminders, "now", lambda: now["t"])
    return now


@pytest.fixture
def out(monkeypatch):
    """Everything that would leave the server: push deliveries, client emails, staff alerts."""
    o = {"push": [], "email": [], "staff": [], "status": 201}
    monkeypatch.setattr(push, "_deliver", lambda sub, data: (o["push"].append((sub["endpoint"], json.loads(data))), o["status"])[1])
    monkeypatch.setattr(reminders, "send_email", lambda to, subject, body: o["email"].append((to, subject, body)))
    monkeypatch.setattr(reminders, "notify_staff", lambda title, message: o["staff"].append(title + " " + message))
    monkeypatch.setattr(booking, "send_confirmation", lambda *a, **k: True)
    monkeypatch.setattr(booking, "notify_staff", lambda *a, **k: None)
    return o


def reminders_on(h, local_time="18:30"):
    r = c.put("/progress/reminders", json={"enabled": True, "local_time": local_time}, headers=h)
    assert r.status_code == 200, r.text


def subscribe(h, endpoint=SUB["endpoint"], lang="es"):
    return c.put("/progress/push", json={**SUB, "endpoint": endpoint, "lang": lang}, headers=h)


def subs(jid):
    return [r[0] for r in db.query("SELECT endpoint FROM push_subscriptions WHERE journey_id = ?", (jid,))]


def run(kind, key_like):
    """Run the queued jobs of one kind whose key matches, the way the worker does."""
    rows = db.query("SELECT id, payload_json FROM jobs WHERE kind = ? AND key LIKE ? AND status = 'pending'", (kind, key_like))
    for jid_, payload in rows:
        jobs.HANDLERS[kind]({"id": jid_, "payload": json.loads(payload) if payload else None})
        jobs.done(jid_)
    return len(rows)


# ---------------------------------------------------------------- push subscriptions

def test_a_push_subscription_is_refused_until_reminders_are_on(out):
    h, jid = client()
    r = subscribe(h)
    assert r.status_code == 409 and r.json() == {"error": "reminders_off"}
    assert subs(jid) == []
    reminders_on(h)
    assert subscribe(h).status_code == 200
    assert subscribe(h).status_code == 200                                    # the same device again: still one row
    assert subs(jid) == [SUB["endpoint"]]


def test_turning_reminders_off_removes_every_subscription(out):
    h, jid = client()
    reminders_on(h)
    subscribe(h, "https://fcm.googleapis.com/fcm/send/ana-phone")
    subscribe(h, "https://updates.push.services.mozilla.com/wpush/v2/ana-laptop")
    assert len(subs(jid)) == 2
    assert c.put("/progress/reminders", json={"enabled": False, "local_time": "18:30"}, headers=h).status_code == 200
    assert subs(jid) == []


def test_unsubscribe_and_bad_subscriptions(out):
    h, jid = client()
    reminders_on(h)
    for bad in ({**SUB, "endpoint": "http://fcm.googleapis.com/x"}, {**SUB, "endpoint": "https://x/" + "a" * 600},
                {**SUB, "keys": {"p256dh": "BN"}}, {**SUB, "lang": "fr"}):
        assert c.put("/progress/push", json=bad, headers=h).status_code == 422, bad
    subscribe(h)
    r = c.delete("/progress/push", headers=h)
    assert r.status_code == 200 and r.json() == {"removed": 1}
    assert subs(jid) == []


def test_one_client_cannot_touch_another_clients_subscription(out):
    h, jid = client()
    other, ojid = client("Luis Torres")
    reminders_on(h); reminders_on(other)
    subscribe(h)
    assert subscribe(other).status_code == 200                                # the same endpoint now belongs to Luis's journey
    assert subs(jid) == [] and subs(ojid) == [SUB["endpoint"]]
    c.delete("/progress/push", headers=h)
    assert subs(ojid) == [SUB["endpoint"]]


def test_the_push_key_is_public_config(monkeypatch, out):
    h, _ = client()
    monkeypatch.setenv("APRENDE_VAPID_PUBLIC_KEY", "BPublicKeyForTests")
    assert c.get("/progress/push-key", headers=h).json() == {"public_key": "BPublicKeyForTests"}
    monkeypatch.delenv("APRENDE_VAPID_PUBLIC_KEY")
    assert c.get("/progress/push-key", headers=h).json() == {"public_key": None}   # push not set up: the app hides it


def test_a_gone_subscription_is_dropped(out):
    h, jid = client()
    reminders_on(h); subscribe(h)
    out["status"] = 410                                                       # the browser unsubscribed on its side
    assert push.send(jid, {"es": {"title": "t", "body": "b"}, "en": {"title": "t", "body": "b"}}, "#/aprender") == 0
    assert subs(jid) == []


# ---------------------------------------------------------------- the daily lesson nudge

def test_the_daily_nudge_is_one_push_a_day_in_her_language(out, clock):
    h, jid = client()
    reminders_on(h, "18:30")
    subscribe(h, lang="en")
    plain, pjid = client("Luis Torres")
    reminders_on(plain, "18:30")                                              # reminders on, but no device: nothing to send
    clock["t"] = datetime.datetime(2027, 3, 10, 18, 31, tzinfo=LA).astimezone(UTC)
    reminders.daily_tick(clock["t"])
    reminders.daily_tick(clock["t"] + datetime.timedelta(hours=2))
    mine = [p for e, p in out["push"] if e == SUB["endpoint"]]
    assert len(mine) == 1
    assert mine[0]["url"] == "#/aprender" and mine[0]["title"] and mine[0]["body"]
    assert "Ana" not in json.dumps(mine[0]) and "Torres" not in json.dumps(mine[0])
    assert mine[0]["body"] != reminders.TEXT["daily"]["es"]["body"]                  # English, as she chose
    assert out["email"] == []                                                 # the daily nudge is push only
    clock["t"] += datetime.timedelta(days=1)
    reminders.daily_tick(clock["t"])
    assert len([p for e, p in out["push"] if e == SUB["endpoint"]]) == 2      # tomorrow again


def test_the_daily_tick_is_a_registered_job_that_queues_the_next(out, clock):
    assert "daily_reminders" in jobs.HANDLERS
    reminders.schedule_daily(clock["t"])
    assert run("daily_reminders", "daily_reminders:%") >= 1
    later = db.query("SELECT run_after FROM jobs WHERE kind = 'daily_reminders' AND status = 'pending'")
    assert later and min(datetime.datetime.fromisoformat(r[0]).replace(tzinfo=UTC) for r in later) > clock["t"]


# ---------------------------------------------------------------- the appointment reminder

def setup_hours():                                                           # afternoon slots: test_t6_07 books the mornings in the same database
    assert c.put("/staff/availability", json={"hours": ALL_DAY, "slot_minutes": {"signing": 60, "consultation": 30}},
                 headers=staff()).status_code == 200
    assert c.put("/staff/holidays", json={"dates": []}, headers=staff()).status_code == 200


def lessons_done(name="Ana Torres"):
    h, jid = client(name)
    for doc in ("will", "trust", "ahcd", "poa"):
        journey.apply(jid, f"lesson_completed:{doc}", {}, actor="system")
    return h, jid


def book(h, start):
    r = c.post("/booking", json={"kind": "consultation", "start": start}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_an_appointment_reminder_goes_out_24_hours_before_by_email_and_push(out):
    setup_hours()
    h, jid = lessons_done()
    reminders_on(h); subscribe(h)
    email = c.get("/auth/me", headers=h).json()["email"]
    start = utc(2027, 3, 16, 14)
    bid = book(h, start)
    rows = db.query("SELECT run_after FROM jobs WHERE kind = 'appointment_reminder' AND key LIKE ?", (f"%{bid}%",))
    assert len(rows) == 1
    assert datetime.datetime.fromisoformat(rows[0][0]).replace(tzinfo=UTC) == at(start) - datetime.timedelta(hours=24)
    assert run("appointment_reminder", f"%{bid}%") == 1
    assert len(out["email"]) == 1
    to, subject, body = out["email"][0]
    assert to == email and subject == "Recordatorio de su cita / Appointment reminder"
    assert "2:00 p. m." in body and "2:00 p.m." in body and "16 de marzo" in body and "March 16" in body
    assert "hora de California" in body and "California time" in body
    assert [e for e, _ in out["push"]] == [SUB["endpoint"]] and out["push"][0][1]["url"] == "#/cita"
    assert all("Ana" not in s and "Torres" not in s for s in out["staff"])


def test_without_reminders_on_the_appointment_reminder_is_email_only(out):
    setup_hours()
    h, _ = lessons_done()
    bid = book(h, utc(2027, 3, 17, 14))
    run("appointment_reminder", f"%{bid}%")
    assert len(out["email"]) == 1 and out["push"] == []


def test_a_rescheduled_or_cancelled_appointment_reminds_only_for_the_live_time(out):
    setup_hours()
    h, _ = lessons_done()
    bid = book(h, utc(2027, 3, 18, 14))
    assert c.patch(f"/booking/{bid}", json={"start": utc(2027, 3, 19, 15)}, headers=h).status_code == 200
    assert run("appointment_reminder", f"%{bid}%") == 2                       # the old job and the new one
    assert len(out["email"]) == 1 and "3:00 p. m." in out["email"][0][2] and "19 de marzo" in out["email"][0][2]
    bid2 = book(h, utc(2027, 3, 22, 14))
    assert c.delete(f"/booking/{bid2}", headers=h).status_code == 200
    run("appointment_reminder", f"%{bid2}%")
    assert len(out["email"]) == 1                                             # nothing for a cancelled appointment


def test_an_appointment_booked_less_than_a_day_ahead_gets_only_its_confirmation(out):
    setup_hours()
    h, _ = lessons_done()
    bid = book(h, utc(2027, 3, 10, 14))                                        # 10 hours after the clock's now
    assert db.query("SELECT id FROM jobs WHERE kind = 'appointment_reminder' AND key LIKE ?", (f"%{bid}%",)) == []


# ---------------------------------------------------------------- the yearly review after funding

def funded():
    h, jid = client()
    c.post("/journey/events", json={"type": "ai_disclosed", "payload": {}}, headers=h)
    c.post("/journey/events", json={"type": "consent", "payload": {"answer": "yes"}}, headers=h)
    c.post("/journey/events", json={"type": "names_submitted", "payload": {"names": ["Ana Torres"]}}, headers=h)
    for ev, p in (("conflict_auto", {"result": "clear"}), ("conflict_firm", {"result": "cleared"})):
        journey.apply(jid, ev, p, actor="system")
    c.post("/journey/events", json={"type": "documents_confirmed", "payload": {"codes": ["will", "trust"]}}, headers=h)
    for ev in ("scope_approved", "engagement_signed", "engagement_countersigned", "paid", "drafts_ready", "attorney_approved",
               "client_confirmed", "signing_booked"):
        journey.apply(jid, ev, {}, actor="system")
    files = [{"name": "Testamento", "filename": "will.pdf", "content_b64": base64.b64encode(b"%PDF-1.4 t803").decode()}]
    assert c.post(f"/staff/journeys/{jid}/executed", json={"documents": files}, headers=staff()).status_code == 200
    assert c.post(f"/staff/journeys/{jid}/funding-done", headers=staff()).status_code == 200
    return h, jid


def test_the_yearly_review_reminder_comes_a_year_after_funding_and_every_year_after(out, monkeypatch):
    monkeypatch.setattr("aprende.signing.send_email", lambda *a, **k: True)
    monkeypatch.setattr("aprende.signing.notify_staff", lambda *a, **k: None)
    h, jid = funded()
    reminders_on(h); subscribe(h)
    done_at = at(journey.get_journey(jid)["facts"]["funding_done"])
    first = db.query("SELECT run_after FROM jobs WHERE kind = 'annual_review' AND key LIKE ?", (f"%{jid}%",))
    assert len(first) == 1
    due = datetime.datetime.fromisoformat(first[0][0]).replace(tzinfo=UTC)
    assert abs(due - (done_at + datetime.timedelta(days=365))) < datetime.timedelta(minutes=1)
    assert run("annual_review", f"%{jid}%") == 1
    assert len(out["email"]) == 1 and out["email"][0][1] == "Revisión anual de su plan / Yearly review of your plan"
    assert out["push"] and out["push"][0][1]["url"] == "#/plan"
    assert len(out["staff"]) == 1 and "Ana" not in out["staff"][0] and "Torres" not in out["staff"][0] and jid in out["staff"][0]
    nxt = db.query("SELECT run_after FROM jobs WHERE kind = 'annual_review' AND key LIKE ? AND status = 'pending'", (f"%{jid}%",))
    assert len(nxt) == 1
    gap = datetime.datetime.fromisoformat(nxt[0][0]) - datetime.datetime.fromisoformat(first[0][0])
    assert gap == datetime.timedelta(days=365)


def test_no_yearly_review_before_funding_is_done(out):
    h, jid = client()
    assert db.query("SELECT id FROM jobs WHERE kind = 'annual_review' AND key LIKE ?", (f"%{jid}%",)) == []


def test_the_reminder_wording_is_bilingual_and_marked_for_the_attorney():
    for kind in ("daily", "appointment", "annual"):
        for lang in ("es", "en"):
            assert reminders.TEXT[kind][lang]["title"] and reminders.TEXT[kind][lang]["body"], (kind, lang)
    src = open(reminders.__file__, encoding="utf-8").read()
    assert "attorney approval" in src                                         # legal care: the wording waits for Pankaj (#50)
