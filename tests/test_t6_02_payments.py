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
import hmac
import time

from aprende import jobs, payments

SECRET = "whsec_test_secret"


class FakeStripe:
    def __init__(self):
        self.sessions = []

    def create_checkout_session(self, *, amount_cents, currency, description, metadata, success_url, cancel_url, idempotency_key):
        sid = f"cs_test_{uuid.uuid4().hex}"                       # Stripe's ids are unique; the test database is shared
        self.sessions.append(dict(id=sid, amount_cents=amount_cents, currency=currency, metadata=metadata, idempotency_key=idempotency_key))
        return {"id": sid, "url": f"https://checkout.stripe.test/{len(self.sessions)}"}


@pytest.fixture
def stripe(monkeypatch):
    fake = FakeStripe()
    monkeypatch.setattr(payments, "stripe_client", lambda: fake)
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", SECRET)
    monkeypatch.delenv("STRIPE_MODE", raising=False)
    return fake


def may_pay(docs=("will",)):
    h = client()
    send(h, "ai_disclosed"); send(h, "consent", answer="yes")
    jid = send(h, "names_submitted", names=["Ana Torres"]).json()["id"]
    journey.apply(jid, "conflict_auto", {"result": "clear"}, actor="system")
    journey.apply(jid, "conflict_firm", {"result": "cleared"}, actor="staff@example.com")
    send(h, "documents_confirmed", codes=list(docs))
    for ev in ("scope_approved", "engagement_signed", "engagement_countersigned"):
        journey.apply(jid, ev, {}, actor="system")
    assert state(h)["gates"]["may_pay"] is True
    return h, jid


def signed(payload: bytes, secret=SECRET, t=None):
    t = int(t or time.time())
    sig = hmac.new(secret.encode(), f"{t}.".encode() + payload, hashlib.sha256).hexdigest()
    return {"Stripe-Signature": f"t={t},v1={sig}", "Content-Type": "application/json"}


def completed(jid, session_id=None, event_id="evt_1", amount=None):
    return json.dumps({"id": event_id, "type": "checkout.session.completed",
                       "data": {"object": {"id": session_id or f"cs_test_{jid}_{event_id}", "payment_status": "paid", "amount_total": amount,
                                           "metadata": {"journey_id": jid}}}}).encode()


# --- checkout (T6-02) ---

def test_checkout_is_refused_until_may_pay(stripe):
    h = client()
    r = c.post("/payments/checkout", headers=h)
    assert r.status_code == 409 and r.json()["missing"] == ["may_pay"] and stripe.sessions == []


def test_the_amount_is_the_servers_quote_never_the_clients(stripe):
    h, jid = may_pay(("will", "ahcd"))
    total = c.get("/payments/quote?codes=will,ahcd", headers=h).json()["total"]
    r = c.post("/payments/checkout", json={"amount_cents": 1, "codes": ["will"]}, headers=h)
    assert r.status_code == 200, r.text
    assert stripe.sessions[-1]["amount_cents"] == total and stripe.sessions[-1]["currency"] == "usd"
    assert stripe.sessions[-1]["metadata"] == {"journey_id": jid}
    assert r.json()["url"].startswith("https://checkout.stripe.test/") and r.json()["mode"] == "test"


def test_asking_twice_reuses_the_same_payment(stripe):
    h, _ = may_pay()
    c.post("/payments/checkout", headers=h); c.post("/payments/checkout", headers=h)
    keys = {s["idempotency_key"] for s in stripe.sessions}
    assert len(keys) == 1                                         # Stripe returns the same session for the same key


def test_live_mode_needs_the_firms_approval(stripe, monkeypatch):
    monkeypatch.setenv("STRIPE_MODE", "live")
    h, _ = may_pay()
    r = c.post("/payments/checkout", headers=h)
    assert r.status_code == 503 and stripe.sessions == []
    admin_email = "admin-p6@example.com"
    backend.users[admin_email] = {"id": str(uuid.uuid4()), "name": "Admin", "email": admin_email, "role": "admin",
                                  "password_hash": backend.hash_pw("admin-password-p6"), "created_at": datetime.datetime.utcnow().isoformat()}
    adm = {"Authorization": "Bearer " + c.post("/auth/login", json={"email": admin_email, "password": "admin-password-p6"}).json()["token"]}
    assert c.put("/staff/payments/live-approval", json={"approved": True}, headers=staff()).status_code == 403
    assert c.put("/staff/payments/live-approval", json={"approved": True}, headers=adm).status_code == 200
    r = c.post("/payments/checkout", headers=h)
    assert r.status_code == 200 and r.json()["mode"] == "live"
    c.put("/staff/payments/live-approval", json={"approved": False}, headers=adm)


# --- webhook (T6-03) ---

def test_a_bad_signature_records_nothing(stripe):
    h, jid = may_pay()
    body = completed(jid)
    assert c.post("/payments/webhook", content=body, headers=signed(body, secret="whsec_wrong")).status_code == 400
    assert c.post("/payments/webhook", content=body, headers={"Content-Type": "application/json"}).status_code == 400
    old = signed(body, t=time.time() - 3600)                      # a replay an hour later
    assert c.post("/payments/webhook", content=body, headers=old).status_code == 400
    assert "paid" not in state(h)["facts"]


def test_a_completed_checkout_records_one_payment_and_one_drafting_job_even_when_retried(stripe):
    h, jid = may_pay()
    c.post("/payments/checkout", headers=h)
    total = c.get("/payments/quote?codes=will", headers=h).json()["total"]
    body = completed(jid, amount=total)
    for _ in range(3):
        assert c.post("/payments/webhook", content=body, headers=signed(body)).status_code == 200
    assert db.query("SELECT COUNT(*) FROM journey_events WHERE journey_id = ? AND type = 'paid'", (jid,))[0][0] == 1
    assert db.query("SELECT COUNT(*) FROM jobs WHERE kind = 'draft_documents' AND key LIKE ?", (f"%{jid}%",))[0][0] == 1
    assert state(h)["gates"]["may_pay"] is False or "paid" in state(h)["facts"]


def test_an_amount_that_differs_from_the_quote_alerts_staff_and_is_not_paid(stripe, monkeypatch):
    alerts = []
    monkeypatch.setattr(payments, "notify_staff", lambda title, message: alerts.append(message))
    h, jid = may_pay()
    body = completed(jid, event_id="evt_short", amount=100)
    assert c.post("/payments/webhook", content=body, headers=signed(body)).status_code == 200
    assert "paid" not in state(h)["facts"] and len(alerts) == 1


def test_other_event_types_are_acknowledged_and_ignored(stripe):
    h, jid = may_pay()
    body = json.dumps({"id": "evt_x", "type": "customer.created", "data": {"object": {}}}).encode()
    assert c.post("/payments/webhook", content=body, headers=signed(body)).status_code == 200
    assert "paid" not in state(h)["facts"]


def test_the_success_redirect_alone_never_marks_paid(stripe):
    h, jid = may_pay()
    r = c.get("/payments/return?session_id=cs_test_1", headers=h)
    assert r.status_code == 200 and r.json()["paid"] is False
    assert "paid" not in state(h)["facts"]


def test_refunds_are_admin_only_and_appear_on_the_receipt(stripe):
    h, jid = may_pay()
    total = c.get("/payments/quote?codes=will", headers=h).json()["total"]
    body = completed(jid, event_id="evt_r", amount=total)
    c.post("/payments/webhook", content=body, headers=signed(body))
    assert c.post(f"/staff/journeys/{jid}/refunds", json={"amount_cents": 50000, "reason": "Cliente canceló el fideicomiso"},
                  headers=staff()).status_code == 403
    admin_email = "admin-p6r@example.com"
    backend.users[admin_email] = {"id": str(uuid.uuid4()), "name": "Admin", "email": admin_email, "role": "admin",
                                  "password_hash": backend.hash_pw("admin-password-p6"), "created_at": datetime.datetime.utcnow().isoformat()}
    adm = {"Authorization": "Bearer " + c.post("/auth/login", json={"email": admin_email, "password": "admin-password-p6"}).json()["token"]}
    assert c.post(f"/staff/journeys/{jid}/refunds", json={"amount_cents": 50000, "reason": "Cliente canceló"}, headers=adm).status_code == 200
    receipt = c.get("/payments/receipt", headers=h).json()
    assert receipt["paid_cents"] == total and receipt["refunds"][0]["amount_cents"] == 50000
    assert receipt["balance_cents"] == total - 50000


def test_concurrent_deliveries_of_one_payment_record_it_once(stripe):
    import threading
    h, jid = may_pay()
    c.post("/payments/checkout", headers=h)
    total = c.get("/payments/quote?codes=will", headers=h).json()["total"]
    body = completed(jid, session_id=stripe.sessions[-1]["id"], event_id="evt_conc", amount=total)
    ts = [threading.Thread(target=lambda: c.post("/payments/webhook", content=body, headers=signed(body))) for _ in range(5)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert db.query("SELECT COUNT(*) FROM journey_events WHERE journey_id = ? AND type = 'paid'", (jid,))[0][0] == 1


def test_a_discount_earned_after_checkout_does_not_reject_the_payment(stripe):
    h, jid = may_pay()
    c.post("/payments/checkout", headers=h)
    asked = stripe.sessions[-1]["amount_cents"]
    journey.apply(jid, "intake_completed", {}, actor="system")                 # one more $100 off after Stripe opened
    body = completed(jid, session_id=stripe.sessions[-1]["id"], event_id="evt_late_discount", amount=asked)
    c.post("/payments/webhook", content=body, headers=signed(body))
    assert "paid" in state(h)["facts"]
