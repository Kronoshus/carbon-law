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

from aprende import timeline
from zoneinfo import ZoneInfo

LA = ZoneInfo("America/Los_Angeles")


def ready(h):
    send(h, "ai_disclosed"); send(h, "consent", answer="yes")
    j = send(h, "names_submitted", names=["Ana Torres"]).json()
    journey.apply(j["id"], "conflict_auto", {"result": "clear"}, actor="system")
    journey.apply(j["id"], "conflict_firm", {"result": "cleared"}, actor="staff@example.com")
    return j["id"]


def test_no_se_todavia_is_all_four_documents():
    h = client()
    ready(h)
    assert send(h, "documents_tentative", codes=["will", "trust", "poa", "ahcd"]).status_code == 200
    assert sorted(state(h)["documents"]["tentative"]) == ["ahcd", "poa", "trust", "will"]


def test_changing_documents_after_scope_approval_reopens_the_scope_review():
    h = client()
    jid = ready(h)
    send(h, "documents_confirmed", codes=["will"])
    journey.apply(jid, "scope_approved", {}, actor="attorney@example.com")
    assert state(h)["gates"]["may_sign_engagement"] is True
    send(h, "documents_confirmed", codes=["will"])                              # the same choice again: nothing reopens
    assert state(h)["gates"]["may_sign_engagement"] is True
    assert send(h, "documents_confirmed", codes=["will", "trust"]).status_code == 200
    j = state(h)
    assert j["gates"]["may_sign_engagement"] is False and "scope_reopened" in j["facts"]
    journey.apply(jid, "scope_approved", {}, actor="attorney@example.com")       # the attorney approves the new scope
    assert state(h)["gates"]["may_sign_engagement"] is True


def test_a_reopened_scope_gets_one_business_day_on_the_timeline():
    start = datetime.datetime(2026, 12, 2, 10, tzinfo=LA).astimezone(datetime.timezone.utc).replace(tzinfo=None).isoformat()
    reopened = datetime.datetime(2026, 12, 4, 10, tzinfo=LA).astimezone(datetime.timezone.utc).replace(tzinfo=None).isoformat()
    now = datetime.datetime(2026, 12, 4, 12, tzinfo=datetime.timezone.utc)
    plain = {s["step"]: s for s in timeline.plan({"started_at": start}, {}, [], now)}
    moved = {s["step"]: s for s in timeline.plan({"started_at": start, "scope_reopened": reopened}, {}, [], now)}
    assert plain["pay"]["date"] == "2026-12-06"
    assert moved["pay"]["date"] == "2026-12-08"           # reopened Friday → reviewed Monday → pay Tuesday


def test_approving_twice_records_one_approval():
    h = client()
    jid = ready(h)
    send(h, "documents_confirmed", codes=["will"])
    journey.apply(jid, "scope_approved", {}, actor="attorney@example.com")
    journey.apply(jid, "scope_approved", {}, actor="attorney@example.com")
    assert db.query("SELECT COUNT(*) FROM journey_events WHERE journey_id = ? AND type = 'scope_approved'", (jid,))[0][0] == 1


def test_changing_the_tentative_choice_is_recorded():
    h = client()
    ready(h)
    send(h, "documents_tentative", codes=["will"])
    send(h, "documents_tentative", codes=["will", "trust"])
    assert state(h)["documents"]["tentative"] == ["will", "trust"]
