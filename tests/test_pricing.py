"""T4-08 acceptance tests."""
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
from aprende import journey, pricing

migrate.run()
c = TestClient(backend.app)

STAFF_EMAIL = "pricing-staff@example.com"
backend.users[STAFF_EMAIL] = {"id": str(uuid.uuid4()), "name": "Pricing Staff", "email": STAFF_EMAIL, "role": "paralegal",
                              "password_hash": backend.hash_pw("pricing-staff-password"),
                              "created_at": datetime.datetime.utcnow().isoformat()}


def staff():
    token = c.post("/auth/login", json={"email": STAFF_EMAIL, "password": "pricing-staff-password"}).json()["token"]
    return {"Authorization": "Bearer " + token}


def client():
    email = f"ana-{uuid.uuid4().hex[:8]}@example.com"
    r = c.post("/auth/signup", json={"name": "Ana Torres", "email": email, "password": "long-secure-password",
                                    "source": "aprende", "adult": True})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}, r.json()


def quote(h, codes="will"):
    return c.get(f"/payments/quote?codes={codes}", headers=h)


def test_fresh_journey_will_300000():
    h, _ = client()
    r = quote(h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["items"][0]["code"] == "will"
    assert d["items"][0]["base"] == 300000
    assert d["items"][0]["price"] == 300000
    assert d["total"] == 300000
    assert d["items"][0]["discounts"] == []


def test_four_lessons_then_intake():
    h, u = client()
    j = journey.get_or_create_for_user(u["id"] if "id" in u else None) if False else None
    # get journey id via API
    jr = c.get("/journey", headers=h).json()
    jid = jr["id"]
    events = ["lesson_completed:will", "lesson_completed:trust", "lesson_completed:ahcd", "lesson_completed:poa"]
    for i, ev in enumerate(events, 1):
        journey.apply(jid, ev, {}, actor="system")
        r = quote(h).json()
        assert r["items"][0]["price"] == 300000 - 10000 * i
        assert len(r["items"][0]["discounts"]) == i
    journey.apply(jid, "intake_completed", {}, actor="system")
    r = quote(h).json()
    assert r["items"][0]["price"] == 250000
    # discounts list names each event
    names = [d["event"] for d in r["items"][0]["discounts"]]
    assert "intake_completed" in names
    # plural sum line possibility: total discount 50000
    assert sum(d["amount"] for d in r["items"][0]["discounts"]) == 50000


def test_sixth_event_floor():
    settings = {
        "base": {"will": 300000},
        "packages": {},
        "discounts": {"will": {"amount": 10000, "events": [f"e{i}" for i in range(6)], "floor": 250000}},
        "placeholder_codes": [],
    }
    facts = {f"e{i}": "t" for i in range(6)}
    q = pricing.quote(settings, facts, ["will"])
    assert q["items"][0]["price"] == 250000


def test_settings_change_keeps_earned():
    h, u = client()
    jr = c.get("/journey", headers=h).json()
    jid = jr["id"]
    journey.apply(jid, "lesson_completed:will", {}, actor="system")
    journey.apply(jid, "lesson_completed:trust", {}, actor="system")
    # change amount
    import db, json
    new_settings = pricing.load_settings("pricing")
    new_settings["discounts"]["will"]["amount"] = 20000
    db.execute("UPDATE settings SET value_json = ? WHERE key = ?", (json.dumps(new_settings), "pricing"))
    journey.apply(jid, "lesson_completed:ahcd", {}, actor="system")
    r = quote(h).json()
    discounts = r["items"][0]["discounts"]
    amounts = {d["event"]: d["amount"] for d in discounts}
    assert amounts["lesson_completed:will"] == 10000
    assert amounts["lesson_completed:trust"] == 10000
    assert amounts["lesson_completed:ahcd"] == 20000
    # restore
    orig = pricing.load_settings("pricing") if False else None
    import json as _j
    original = {"base": {"will": 300000, "trust": 500000, "poa": 200000, "ahcd": 200000}, "packages": {}, "discounts": {"will": {"amount": 10000, "events": ["lesson_completed:will", "lesson_completed:trust", "lesson_completed:ahcd", "lesson_completed:poa", "intake_completed"], "floor": 250000}}, "placeholder_codes": ["trust", "poa", "ahcd"]}
    db.execute("UPDATE settings SET value_json = ? WHERE key = ?", (json.dumps(original), "pricing"))


def test_duplicate_event_one_discount():
    h, u = client()
    jr = c.get("/journey", headers=h).json()
    jid = jr["id"]
    journey.apply(jid, "lesson_completed:will", {}, actor="system")
    journey.apply(jid, "lesson_completed:will", {}, actor="system")
    rows = __import__("db").query("SELECT COUNT(*) FROM discounts WHERE journey_id = ?", (jid,))
    assert rows[0][0] == 1


def test_unknown_code_422():
    h, _ = client()
    r = quote(h, "foo")
    assert r.status_code == 422


def test_staff_403():
    r = quote(staff())
    assert r.status_code == 403


def test_isolation():
    h1, _ = client()
    h2, u2 = client()
    jr2 = c.get("/journey", headers=h2).json()
    journey.apply(jr2["id"], "lesson_completed:will", {}, actor="system")
    # client1 has no discounts
    r1 = quote(h1).json()
    assert r1["items"][0]["discounts"] == []
    r2 = quote(h2).json()
    assert len(r2["items"][0]["discounts"]) == 1


def test_placeholders():
    h, _ = client()
    r = quote(h, "will,trust,poa,ahcd").json()
    by = {i["code"]: i for i in r["items"]}
    assert by["will"]["placeholder"] is False
    assert by["trust"]["placeholder"] is True
    assert by["poa"]["placeholder"] is True
    assert by["ahcd"]["placeholder"] is True


def test_unit_quote_basic():
    settings = {"base": {"will": 300000}, "packages": {}, "discounts": {"will": {"amount": 10000, "events": ["a", "b"], "floor": 250000}}, "placeholder_codes": []}
    facts = {"a": "t"}
    q = pricing.quote(settings, facts, ["will"])
    assert q["items"][0]["price"] == 290000
    assert q["items"][0]["discounts"][0]["event"] == "a"


def test_unit_earned_locked():
    settings = {"base": {"will": 300000}, "packages": {}, "discounts": {"will": {"amount": 20000, "events": ["a"], "floor": 250000}}, "placeholder_codes": []}
    facts = {"a": "t"}
    earned = {("will", "a"): 10000}
    q = pricing.quote(settings, facts, ["will"], earned=earned)
    assert q["items"][0]["discounts"][0]["amount"] == 10000


def test_package_exact_set():
    settings = {"base": {"will": 300000, "poa": 200000}, "packages": {frozenset({"will", "poa"}): {"price": 450000}}, "discounts": {}, "placeholder_codes": []}
    # packages key as string comma
    settings2 = {"base": {"will": 300000, "poa": 200000}, "packages": {"will,poa": {"price": 450000}}, "discounts": {}, "placeholder_codes": []}
    q = pricing.quote(settings2, {}, ["will", "poa"])
    assert q["total"] == 450000
