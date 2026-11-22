"""A possible conflict stops consultation booking too: the firm must not meet a possibly adverse party (brief s.6).

Found by the guardrail audit (~/work/cl-reports/audit-guardrails.md). Fictional people only. (Opus)"""
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
import db
import migrate
from aprende import conflicts, journey

migrate.run()
c = TestClient(backend.app)
PASSWORD = "audit-fix-password"
ATTORNEY = "audit-fix-attorney@example.com"
backend.users[ATTORNEY] = {"id": str(uuid.uuid4()), "name": "Audit Attorney", "email": ATTORNEY, "role": "attorney",
                           "password_hash": backend.hash_pw(PASSWORD), "created_at": datetime.datetime.utcnow().isoformat()}


def login(email):
    return {"Authorization": "Bearer " + c.post("/auth/login", json={"email": email, "password": PASSWORD}).json()["token"]}


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


def consented(h, names=("Ana Torres",)):
    send(h, "ai_disclosed"); send(h, "consent", answer="yes")
    r = send(h, "names_submitted", names=list(names))
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture
def firm_list():
    """The firm's conflict list for one test; the list in force before is put back afterwards."""
    before = conflicts.get_list()
    yield lambda *names: conflicts.replace_list("name\n" + "\n".join(names) + "\n") if names else conflicts.delete_list()
    conflicts.replace_list("name\n" + "\n".join(before) + "\n") if before else conflicts.delete_list()


def lessons_done(jid):
    for d in ("will", "trust", "ahcd", "poa"):
        journey.apply(jid, f"lesson_completed:{d}", {}, actor="system")


def test_a_possible_conflict_also_stops_booking_a_consultation(firm_list):
    """A consultation is a meeting with the attorney: under a possible conflict the firm must not take one (brief s.6)."""
    firm_list("Luis Torres")
    h = client()
    jid = consented(h, ["Luis Torres"])
    lessons_done(jid)
    assert state(h)["conflict"] == "hold"
    assert c.get("/booking/slots?kind=consultation&from=2026-12-01", headers=h).status_code == 409
    r = c.post("/booking", json={"kind": "consultation", "start": "2026-12-01T17:00:00Z"}, headers=h)
    assert r.status_code == 409 and db.query("SELECT COUNT(*) FROM bookings WHERE journey_id = ?", (jid,))[0][0] == 0


def test_a_cleared_client_can_still_book_a_consultation_after_the_lessons(firm_list):
    firm_list()
    h = client()
    jid = consented(h)
    journey.apply(jid, "conflict_auto", {"result": "clear"}, actor="system")
    lessons_done(jid)
    assert c.get("/booking/slots?kind=consultation&from=2026-12-01", headers=h).status_code == 200
