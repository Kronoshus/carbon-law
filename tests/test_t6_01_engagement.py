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

import hashlib
import re

from pypdf import PdfReader
import io

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ES = open(os.path.join(ROOT, "aprende", "content", "engagement", "es.md"), encoding="utf-8").read()
EN = open(os.path.join(ROOT, "aprende", "content", "engagement", "en.md"), encoding="utf-8").read()

ATTORNEY_EMAIL = "raval-p6@example.com"
backend.users[ATTORNEY_EMAIL] = {"id": str(uuid.uuid4()), "name": "Pankaj Raval", "email": ATTORNEY_EMAIL, "role": "attorney",
                                 "password_hash": backend.hash_pw("attorney-password-p6"),
                                 "created_at": datetime.datetime.utcnow().isoformat()}
PROFILE = {"bar_number": "000000", "costs_line": {"es": "Sin costos adicionales.", "en": "No additional costs."},
           "refund_policy": {"es": "Política de reembolso de prueba.", "en": "Test refund policy."},
           "data_promise": {"es": "Promesa de datos de prueba.", "en": "Test data promise."}}


def attorney():
    t = c.post("/auth/login", json={"email": ATTORNEY_EMAIL, "password": "attorney-password-p6"}).json()["token"]
    return {"Authorization": "Bearer " + t}


def approved_template():
    r = c.post("/staff/engagement-templates", json={"es": ES, "en": EN}, headers=attorney())
    assert r.status_code == 200, r.text
    tid = r.json()["id"]
    assert c.post(f"/staff/engagement-templates/{tid}/approve", headers=attorney()).status_code == 200
    assert c.put("/staff/firm-profile", json=PROFILE, headers=attorney()).status_code == 200
    return tid


def ready_to_sign(docs=("will",)):
    """A client with consent, an automatic and a firm clearance, confirmed documents and the attorney's scope approval."""
    h = client()
    send(h, "ai_disclosed"); send(h, "consent", answer="yes")
    jid = send(h, "names_submitted", names=["Ana Torres"]).json()["id"]
    journey.apply(jid, "conflict_auto", {"result": "clear"}, actor="system")
    journey.apply(jid, "conflict_firm", {"result": "cleared"}, actor="staff@example.com")
    send(h, "documents_confirmed", codes=list(docs))
    assert c.post(f"/staff/journeys/{jid}/scope-approval", headers=attorney()).status_code == 200
    return h, jid


def letter(h, lang="es"):
    return c.get(f"/engagement?lang={lang}", headers=h)


def sign(h, sha, name="Ana Torres", accept=True):
    return c.post("/engagement/sign", json={"name": name, "accept": accept, "sha256": sha}, headers=h)


# --- templates ---

def test_only_the_attorney_approves_a_template():
    r = c.post("/staff/engagement-templates", json={"es": ES, "en": EN}, headers=attorney())
    tid = r.json()["id"]
    assert c.post(f"/staff/engagement-templates/{tid}/approve", headers=staff()).status_code == 403
    assert c.post(f"/staff/engagement-templates/{tid}/approve", headers=client()).status_code == 403
    assert c.post("/staff/engagement-templates", json={"es": ES, "en": EN}, headers=client()).status_code == 403


def test_a_letter_needs_an_approved_template_and_the_firm_profile():
    db.execute("DELETE FROM settings WHERE key = 'firm_profile'")
    db.execute("UPDATE engagement_templates SET approved_by = NULL, approved_at = NULL")
    h, _ = ready_to_sign()
    r = letter(h)
    assert r.status_code == 409 and set(r.json()["missing"]) == {"approved_template", "firm_profile"}
    approved_template()
    assert letter(h).status_code == 200


def test_a_new_unapproved_version_does_not_replace_the_approved_one():
    approved_template()
    h, _ = ready_to_sign()
    before = letter(h).json()
    c.post("/staff/engagement-templates", json={"es": ES.replace("Fecha", "FECHA NUEVA"), "en": EN}, headers=attorney())
    after = letter(h).json()
    assert after["version"] == before["version"] and "FECHA NUEVA" not in after["text"]


# --- scope approval and gates ---

def test_scope_approval_is_the_attorneys_and_opens_signing():
    approved_template()
    h = client()
    send(h, "ai_disclosed"); send(h, "consent", answer="yes")
    jid = send(h, "names_submitted", names=["Ana Torres"]).json()["id"]
    journey.apply(jid, "conflict_auto", {"result": "clear"}, actor="system")
    send(h, "documents_confirmed", codes=["will"])
    assert c.post(f"/staff/journeys/{jid}/scope-approval", headers=staff()).status_code == 403
    assert c.post(f"/staff/journeys/{jid}/scope-approval", headers=attorney()).status_code == 200
    r = letter(h)
    assert r.status_code == 409 and r.json()["missing"] == ["may_sign_engagement"]   # the firm's own clearance is missing
    journey.apply(jid, "conflict_firm", {"result": "cleared"}, actor="staff@example.com")
    assert letter(h).status_code == 200


def test_scope_needs_confirmed_documents():
    h = client()
    send(h, "ai_disclosed"); send(h, "consent", answer="yes")
    jid = send(h, "names_submitted", names=["Ana Torres"]).json()["id"]
    r = c.post(f"/staff/journeys/{jid}/scope-approval", headers=attorney())
    assert r.status_code == 409


# --- the letter ---

def test_the_letter_names_the_client_documents_and_the_quoted_total():
    approved_template()
    h, _ = ready_to_sign(("will", "ahcd"))
    body = letter(h).json()
    text = body["text"]
    assert "Ana Torres" in text and "000000" in text and "Promesa de datos de prueba." in text
    assert "Testamento" in text and "Directiva" in text
    quote = c.get("/payments/quote?codes=will,ahcd", headers=h).json()
    total = quote["total"]
    assert f"${total // 100:,}" in text                                          # the same total the price screen shows
    assert not re.search(r"\{[a-z_]+\}", text)                                  # every placeholder filled
    assert body["sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
    en = letter(h, "en").json()
    assert "Legal services and fee agreement" in en["text"] and en["sha256"] != body["sha256"]


def test_the_clients_name_is_text_not_markup():
    approved_template()
    r = c.post("/auth/signup", json={"name": "<b>Ana</b> {total}", "email": f"x-{uuid.uuid4().hex[:8]}@example.com",
                                     "password": "long-secure-password", "source": "aprende", "adult": True})
    h = {"Authorization": "Bearer " + r.json()["token"]}
    send(h, "ai_disclosed"); send(h, "consent", answer="yes")
    jid = send(h, "names_submitted", names=["Ana Torres"]).json()["id"]
    journey.apply(jid, "conflict_auto", {"result": "clear"}, actor="system")
    journey.apply(jid, "conflict_firm", {"result": "cleared"}, actor="s@example.com")
    send(h, "documents_confirmed", codes=["will"])
    c.post(f"/staff/journeys/{jid}/scope-approval", headers=attorney())
    text = letter(h).json()["text"]
    assert "<b>Ana</b> {total}" in text                                            # kept exactly as typed: not markup, not a placeholder


# --- signing ---

def test_signing_needs_the_text_that_was_shown():
    approved_template()
    h, _ = ready_to_sign()
    sha = letter(h).json()["sha256"]
    assert sign(h, "0" * 64).status_code == 409                                 # the text changed (or was never seen)
    assert sign(h, sha, accept=False).status_code == 422
    assert sign(h, sha, name="  ").status_code == 422
    assert sign(h, sha).status_code == 200
    assert "engagement_signed" in state(h)["facts"]


def test_signing_twice_is_a_no_op():
    approved_template()
    h, jid = ready_to_sign()
    sha = letter(h).json()["sha256"]
    sign(h, sha); sign(h, sha)
    assert db.query("SELECT COUNT(*) FROM engagement_signatures WHERE journey_id = ?", (jid,))[0][0] == 1
    assert db.query("SELECT COUNT(*) FROM journey_events WHERE journey_id = ? AND type = 'engagement_signed'", (jid,))[0][0] == 1


def test_the_stored_hash_is_the_hash_of_the_stored_text():
    approved_template()
    h, jid = ready_to_sign()
    shown = letter(h).json()
    sign(h, shown["sha256"])
    text, sha, name = db.query("SELECT text, sha256, client_name FROM engagement_signatures WHERE journey_id = ?", (jid,))[0]
    assert text == shown["text"] and sha == hashlib.sha256(text.encode("utf-8")).hexdigest() and name == "Ana Torres"


def test_payment_waits_for_both_signatures():
    """Bus. & Prof. Code § 6148(a): the client gets a copy signed by both the attorney and the client."""
    approved_template()
    h, jid = ready_to_sign()
    sign(h, letter(h).json()["sha256"])
    assert state(h)["gates"]["may_pay"] is False
    assert c.post(f"/staff/journeys/{jid}/engagement/countersign", headers=staff()).status_code == 403
    assert c.post(f"/staff/journeys/{jid}/engagement/countersign", headers=attorney()).status_code == 200
    assert state(h)["gates"]["may_pay"] is True
    assert letter(h).json()["attorney_signed_at"]


def test_the_attorney_cannot_countersign_before_the_client():
    approved_template()
    h, jid = ready_to_sign()
    assert c.post(f"/staff/journeys/{jid}/engagement/countersign", headers=attorney()).status_code == 409


def test_a_later_template_change_does_not_touch_a_signed_letter():
    approved_template()
    h, jid = ready_to_sign()
    shown = letter(h).json()
    sign(h, shown["sha256"])
    approved_template()                                                          # a new approved version
    assert letter(h).json()["text"] == shown["text"]                             # the signed letter is what she sees


# --- the copy ---

def test_the_signed_copy_is_a_pdf_for_the_client_and_staff_only():
    approved_template()
    h, jid = ready_to_sign()
    sha = letter(h).json()["sha256"]
    assert c.get("/engagement/pdf", headers=h).status_code == 409               # nothing signed yet
    sign(h, sha)
    c.post(f"/staff/journeys/{jid}/engagement/countersign", headers=attorney())
    r = c.get("/engagement/pdf", headers=h)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    text = " ".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
    assert sha in text.replace("\n", "").replace(" ", "")
    assert "Ana Torres" in text and "Pankaj Raval" in text
    assert c.get(f"/staff/journeys/{jid}/engagement/pdf", headers=staff()).status_code == 200
    assert c.get("/engagement/pdf").status_code == 401
    assert c.get(f"/staff/journeys/{jid}/engagement/pdf", headers=client()).status_code == 403
