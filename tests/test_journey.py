"""T2-06 acceptance tests, written by Opus before the code (ticket ★). The journey is the server-enforced order of
the legal steps: AI disclosure -> consent -> names-only conflict check -> details. These tests are the contract; do not
weaken them. Server-only facts are applied in tests with `aprende.journey.apply(journey_id, type, payload, actor)`."""
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
from aprende import journey

migrate.run()
c = TestClient(backend.app)

STAFF_EMAIL = "journey-staff@example.com"
backend.users[STAFF_EMAIL] = {"id": str(uuid.uuid4()), "name": "Journey Staff", "email": STAFF_EMAIL, "role": "paralegal",
                              "password_hash": backend.hash_pw("journey-staff-password"),
                              "created_at": datetime.datetime.utcnow().isoformat()}


def staff():
    token = c.post("/auth/login", json={"email": STAFF_EMAIL, "password": "journey-staff-password"}).json()["token"]
    return {"Authorization": "Bearer " + token}


def client(adult=True):
    email = f"ana-{uuid.uuid4().hex[:8]}@example.com"
    body = {"name": "Ana Torres", "email": email, "password": "long-secure-password"}
    if adult:
        body.update(source="aprende", adult=True)
    r = c.post("/auth/signup", json=body)
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def send(h, type_, **payload):
    return c.post("/journey/events", json={"type": type_, "payload": payload}, headers=h)


def state(h):
    r = c.get("/journey", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def to_names(h):
    assert send(h, "ai_disclosed").status_code == 200
    assert send(h, "consent", answer="yes").status_code == 200
    r = send(h, "names_submitted", names=["Ana Torres", "Luis Torres", "Sofía Torres"])
    assert r.status_code == 200, r.text
    return r.json()


def test_new_journey_starts_at_disclosure():
    j = state(client())
    assert j["gates"]["may_disclose"] is True
    assert j["gates"]["may_consent"] is False
    assert j["gates"]["may_collect_details"] is False
    assert j["conflict"] == "pending"
    assert j["day"] == 1


def test_journey_requires_adult_confirmation():
    r = c.get("/journey", headers=client(adult=False))
    assert r.status_code == 403
    assert "adult" in r.json()["detail"]


def test_order_is_enforced_with_the_missing_gate_named():
    h = client()
    r = send(h, "consent", answer="yes")
    assert r.status_code == 409 and "may_consent" in r.json()["missing"]
    assert send(h, "ai_disclosed").status_code == 200
    r = send(h, "names_submitted", names=["Ana Torres"])
    assert r.status_code == 409 and "may_name" in r.json()["missing"]


def test_consent_no_is_learning_only():
    h = client()
    send(h, "ai_disclosed")
    assert send(h, "consent", answer="no").status_code == 200
    j = state(h)
    assert j["gates"]["may_name"] is False
    assert j["gates"]["may_collect_details"] is False and j["gates"]["may_chat"] is False
    assert send(h, "names_submitted", names=["Ana Torres"]).status_code == 409


def test_consent_answer_must_be_yes_or_no():
    h = client()
    send(h, "ai_disclosed")
    assert send(h, "consent", answer="maybe").status_code == 422


def test_names_are_validated():
    h = client()
    send(h, "ai_disclosed"); send(h, "consent", answer="yes")
    assert send(h, "names_submitted", names=[]).status_code == 422
    assert send(h, "names_submitted", names=["x" * 121]).status_code == 422
    assert send(h, "names_submitted", names=["Ana"] * 21).status_code == 422


def test_names_create_exactly_one_matter_for_staff():
    h = client()
    to_names(h)
    assert send(h, "names_submitted", names=["Ana Torres"]).status_code == 200      # a resend is a no-op
    j = state(h)
    matters = [m for m in c.get("/matters", headers=staff()).json() if m.get("id") == j["matter_id"]]
    assert len(matters) == 1 and matters[0]["stage"] == "1 Intake"


def test_details_wait_for_an_automatic_clear():
    h = client()
    j = to_names(h)
    assert j["gates"]["may_collect_details"] is False
    journey.apply(j["id"], "conflict_auto", {"result": "clear"}, actor="system")
    j = state(h)
    assert j["conflict"] == "clear"
    assert j["gates"]["may_collect_details"] is True and j["gates"]["may_chat"] is True
    assert j["gates"]["may_sign_engagement"] is False and j["gates"]["may_pay"] is False


def test_possible_conflict_stops_and_says_nothing_more():
    h = client()
    j = to_names(h)
    journey.apply(j["id"], "conflict_auto", {"result": "possible", "matches": ["Roberto Méndez"]}, actor="system")
    raw = c.get("/journey", headers=h).text
    j = json.loads(raw)
    assert j["conflict"] == "hold"
    assert not any(j["gates"][g] for g in ("may_collect_details", "may_chat", "may_sign_engagement", "may_pay"))
    assert "Méndez" not in raw and "Mendez" not in raw and "matches" not in raw and "possible" not in raw


def test_firm_flag_overrides_an_automatic_clear():
    h = client()
    j = to_names(h)
    journey.apply(j["id"], "conflict_auto", {"result": "clear"}, actor="system")
    journey.apply(j["id"], "conflict_firm", {"result": "flagged"}, actor="staff@example.com")
    j = state(h)
    assert j["conflict"] == "hold" and j["gates"]["may_collect_details"] is False


def test_payment_needs_firm_clearance_scope_and_signed_letter():
    h = client()
    j = to_names(h)
    jid = j["id"]
    journey.apply(jid, "conflict_auto", {"result": "clear"}, actor="system")
    journey.apply(jid, "conflict_firm", {"result": "cleared"}, actor="staff@example.com")
    assert state(h)["gates"]["may_sign_engagement"] is False
    journey.apply(jid, "scope_approved", {}, actor="attorney@example.com")
    assert state(h)["gates"]["may_sign_engagement"] is True
    assert state(h)["gates"]["may_pay"] is False
    journey.apply(jid, "engagement_signed", {}, actor="client")
    assert state(h)["gates"]["may_pay"] is True


def test_documents_visible_only_after_attorney_approval():
    h = client()
    jid = to_names(h)["id"]
    for t in ("paid", "drafts_ready"):
        journey.apply(jid, t, {}, actor="system")
    assert state(h)["gates"]["may_see_documents"] is False
    journey.apply(jid, "attorney_approved", {}, actor="attorney@example.com")
    assert state(h)["gates"]["may_see_documents"] is True


def test_client_cannot_send_server_only_events():
    h = client()
    for t in ("conflict_auto", "conflict_firm", "scope_approved", "paid", "attorney_approved", "signed", "intake_completed"):
        assert send(h, t, result="clear").status_code == 403, t


def test_unknown_event_type_is_rejected():
    assert send(client(), "make_me_rich").status_code == 422


def test_facts_are_append_only():
    h = client()
    send(h, "ai_disclosed")
    first = state(h)["facts"]["ai_disclosed"]
    assert send(h, "ai_disclosed").status_code == 200
    assert state(h)["facts"]["ai_disclosed"] == first


def test_one_journey_per_client_and_staff_have_none():
    h = client()
    assert state(h)["id"] == state(h)["id"]
    assert c.get("/journey", headers=staff()).status_code == 403
    assert c.get("/journey").status_code == 401


def test_gates_is_a_pure_function_of_facts():
    facts = {"ai_disclosed": "t", "consent": "t", "consent_answer": "yes", "names_submitted": "t", "conflict_auto": "t",
             "conflict_auto_result": "clear"}
    g = journey.gates(facts)
    assert g["may_collect_details"] is True and g["may_pay"] is False
    assert journey.gates({})["may_disclose"] is True
