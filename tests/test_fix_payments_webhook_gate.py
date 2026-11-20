"""The payment webhook records a payment only when the attorney has countersigned (Bus. & Prof. Code s. 6148(a)).

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

from aprende import notify, payments


@pytest.fixture
def alerts(monkeypatch):
    """Staff phone alerts as ntfy would receive them (title header and body), through the shared notify helper."""
    sent = []
    monkeypatch.setenv("APRENDE_STAFF_NTFY_TOPIC", "audit-topic")
    monkeypatch.setattr(notify.httpx, "post", lambda url, content=b"", headers=None, **kw: sent.append(
        {"url": url, "title": (headers or {}).get("Title", ""), "body": content.decode()}))
    return sent


import hashlib
import hmac
import time

WEBHOOK_SECRET = "whsec_audit_guardrails"


class FakeStripe:
    def __init__(self):
        self.sessions = []

    def create_checkout_session(self, **kw):
        self.sessions.append(kw)
        return {"id": f"cs_test_{uuid.uuid4().hex}", "url": "https://checkout.stripe.test/audit"}


@pytest.fixture
def stripe(monkeypatch):
    fake = FakeStripe()
    monkeypatch.setattr(payments, "stripe_client", lambda: fake)
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.delenv("STRIPE_MODE", raising=False)
    return fake


def webhook(jid, amount):
    body = json.dumps({"id": f"evt_{uuid.uuid4().hex}", "type": "checkout.session.completed",
                       "data": {"object": {"id": f"cs_test_{uuid.uuid4().hex}", "payment_status": "paid",
                                           "amount_total": amount, "metadata": {"journey_id": jid}}}}).encode()
    t = int(time.time())
    sig = hmac.new(WEBHOOK_SECRET.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    return c.post("/payments/webhook", content=body, headers={"Stripe-Signature": f"t={t},v1={sig}",
                                                              "Content-Type": "application/json"})


def cleared_with_letter(h):
    jid = consented(h)
    journey.apply(jid, "conflict_auto", {"result": "clear"}, actor="system")
    journey.apply(jid, "conflict_firm", {"result": "cleared"}, actor="staff@example.com")
    send(h, "documents_confirmed", codes=["will"])
    return jid


def test_a_paid_webhook_before_the_countersignature_records_no_payment_and_starts_no_drafts(stripe, firm_list, alerts):
    """Stripe can report a payment the app did not open (a link made in the dashboard, an old session after the letter
    changed): without the countersignature it is not the client's payment for drafting, and staff are told to refund."""
    firm_list()
    h = client()
    jid = cleared_with_letter(h)
    journey.apply(jid, "scope_approved", {}, actor="system")
    journey.apply(jid, "engagement_signed", {}, actor="system")
    assert state(h)["gates"]["may_pay"] is False
    assert webhook(jid, payments._total(journey.get_journey(jid))).status_code == 200
    assert "paid" not in state(h)["facts"]
    assert db.query("SELECT COUNT(*) FROM payments WHERE journey_id = ?", (jid,))[0][0] == 0
    assert db.query("SELECT COUNT(*) FROM jobs WHERE kind = 'draft_documents' AND key LIKE ?", (f"%{jid}%",))[0][0] == 0
    assert len(alerts) == 1 and jid in alerts[0]["body"] and "Torres" not in alerts[0]["body"]


def test_after_the_countersignature_the_same_webhook_records_the_payment(stripe, firm_list, alerts):
    firm_list()
    h = client()
    jid = cleared_with_letter(h)
    for ev in ("scope_approved", "engagement_signed", "engagement_countersigned"):
        journey.apply(jid, ev, {}, actor="system")
    assert webhook(jid, payments._total(journey.get_journey(jid))).status_code == 200
    assert "paid" in state(h)["facts"] and alerts == []
