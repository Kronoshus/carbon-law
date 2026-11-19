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

LA = ZoneInfo("America/Los_Angeles")


def at(days_ago, hour=10):
    t = datetime.datetime.now(LA).replace(hour=hour, minute=0, second=0, microsecond=0) - datetime.timedelta(days=days_ago)
    return t.astimezone(datetime.timezone.utc).replace(tzinfo=None).isoformat()


def journey_with(monkeypatch, name, start_days_ago, paid_days_ago=None):
    clock = {"now": at(start_days_ago)}
    monkeypatch.setattr(journey, "_now_iso", lambda: clock["now"])
    r = c.post("/auth/signup", json={"name": name, "email": f"p-{uuid.uuid4().hex[:8]}@example.com", "password": "long-secure-password",
                                     "source": "aprende", "adult": True})
    h = {"Authorization": "Bearer " + r.json()["token"]}
    jid = state(h)["id"]
    db.execute("UPDATE journeys SET started_at = ? WHERE id = ?", (clock["now"], jid))
    if paid_days_ago is not None:
        clock["now"] = at(paid_days_ago)
        journey.apply(jid, "paid", {}, actor="stripe")
    monkeypatch.undo()
    return h, jid


def test_the_client_sees_every_step_with_its_date(monkeypatch):
    h, _ = journey_with(monkeypatch, "Ana Torres", 0)
    tl = state(h)["timeline"]
    assert [s["step"] for s in tl] == ["lesson_will", "lesson_trust", "lesson_ahcd", "lesson_poa", "pay",
                                       "attorney_review", "client_review", "signing", "final_lesson"]
    assert all(s["date"] for s in tl)


def test_staff_list_puts_the_most_late_first(monkeypatch):
    _, on_time = journey_with(monkeypatch, "Luis Torres", 1)
    _, late = journey_with(monkeypatch, "Rosa Late", 30, paid_days_ago=25)                 # the review was due weeks ago
    rows = c.get("/staff/journeys", headers=staff()).json()
    ids = [r["journey_id"] for r in rows]
    assert ids.index(late) < ids.index(on_time)
    row = next(r for r in rows if r["journey_id"] == late)
    assert row["client_name"] == "Rosa Late" and row["late"] == ["attorney_review"]
    assert {"journey_id", "client_name", "day", "next_step", "late"} <= set(row)
    assert next(r for r in rows if r["journey_id"] == on_time)["late"] == []


def test_the_staff_list_is_staff_only():
    assert c.get("/staff/journeys", headers=client()).status_code == 403
    assert c.get("/staff/journeys").status_code == 401
