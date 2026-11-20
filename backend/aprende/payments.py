"""Payments: Stripe checkout (test mode), webhook, refunds, config."""
import hashlib
import hmac
import json
import os
import time
import uuid

import httpx
from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

import app as backend_app
import db
from aprende import journey, jobs, legacy, pricing
from aprende import analytics
from aprende.notify import notify_staff

router = APIRouter()


def _auth(authorization):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    u, _ = backend_app.require_auth(authorization)
    return u


def _adult_check(u):
    if u.get("role") != "client":
        raise HTTPException(403, "staff have no journey")
    if "adult_confirmed_at" not in u:
        raise HTTPException(403, "adult confirmation required")


def _staff(authorization, roles):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    return backend_app.require_auth(authorization, roles)[0]


def _approved():
    rows = db.query("SELECT value_json FROM settings WHERE key = ?", ("payments_live_approved",))
    if not rows:
        return False
    try:
        return bool(json.loads(rows[0][0]))
    except (ValueError, TypeError):
        return False


def mode():
    m = os.environ.get("STRIPE_MODE", "test").lower()
    if m == "live" and _approved():
        return "live"
    return "test"


class StripeClient:
    def __init__(self, secret_key=None):
        self.secret_key = secret_key if secret_key is not None else os.environ.get("STRIPE_SECRET_KEY", "")

    def create_checkout_session(self, *, amount_cents, currency, description, metadata, success_url, cancel_url, idempotency_key):
        data = {
            "mode": "payment",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "line_items[0][price_data][currency]": currency,
            "line_items[0][price_data][product_data][name]": description or "Aprende y Planea",
            "line_items[0][price_data][unit_amount]": int(amount_cents),
            "line_items[0][quantity]": 1,
        }
        for k, v in (metadata or {}).items():
            data[f"metadata[{k}]"] = v
        r = httpx.post(
            "https://api.stripe.com/v1/checkout/sessions",
            data=data,
            headers={"Authorization": f"Bearer {self.secret_key}", "Idempotency-Key": idempotency_key},
            timeout=30,
        )
        r.raise_for_status()
        j = r.json()
        return {"id": j["id"], "url": j["url"]}


def stripe_client():
    return StripeClient()


def _earned(jid):
    return {(d, e): c for d, e, c in db.query("SELECT document, event, amount_cents FROM discounts WHERE journey_id = ?", (jid,))}


def _total(j):
    """The server's price for the confirmed documents: the only amount ever charged."""
    return int(pricing.quote(pricing.load_settings("pricing") or {}, j["facts"], j["documents"]["confirmed"], earned=_earned(j["id"]))["total"])


def _verify_signature(raw, sig_header, secret):
    if not sig_header or not secret:
        return False
    t = None
    v1 = None
    for part in sig_header.split(","):
        part = part.strip()
        if part.startswith("t="):
            t = part[2:]
        elif part.startswith("v1="):
            v1 = part[3:]
    if not t or not v1:
        return False
    try:
        t_int = int(t)
    except ValueError:
        return False
    if abs(time.time() - t_int) > 300:
        return False
    mac = hmac.new(secret.encode(), (str(t) + ".").encode() + raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, v1)


@router.get("/payments/quote")
def get_quote(codes: str = Query(...), authorization: str = Header(None)):
    """The price card: any documents the client is looking at, with the discounts she has earned."""
    u = _auth(authorization)
    _adult_check(u)
    j = journey.get_or_create_for_user(u["id"])
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if any(c not in pricing.DOC_CODES for c in code_list):
        raise HTTPException(422, "invalid codes")
    if not code_list:
        raise HTTPException(422, "codes required")
    earned = _earned(j["id"])
    return pricing.quote(pricing.load_settings("pricing") or {}, j["facts"], code_list, earned=earned)


@router.get("/payments/config")
def get_config(authorization: str = Header(None)):
    _auth(authorization)
    return {"mode": mode()}


@router.post("/payments/checkout")
def checkout(authorization: str = Header(None)):
    u = _auth(authorization)
    _adult_check(u)
    j = journey.get_or_create_for_user(u["id"])
    if not j["gates"].get("may_pay"):
        return JSONResponse(status_code=409, content={"error": "gate", "missing": ["may_pay"]})
    m = os.environ.get("STRIPE_MODE", "test").lower()
    if m == "live" and not _approved():
        raise HTTPException(503, "live payments not approved")
    amount = _total(j)
    app_origin = os.environ.get("APP_ORIGIN", "http://127.0.0.1:5173")
    success_url = f"{app_origin}/#/pago/listo?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{app_origin}/#/pago"
    idempotency_key = hashlib.sha256((j["id"] + str(amount)).encode()).hexdigest()
    client = stripe_client()
    session = client.create_checkout_session(
        amount_cents=amount,
        currency="usd",
        description="Aprende y Planea",
        metadata={"journey_id": j["id"]},
        success_url=success_url,
        cancel_url=cancel_url,
        idempotency_key=idempotency_key,
    )
    db.execute("INSERT INTO checkout_sessions (id, journey_id, amount_cents, created_at) VALUES (?, ?, ?, ?) ON CONFLICT (id) DO NOTHING",
               (session["id"], j["id"], amount, journey._now_iso()))
    analytics.record(j["id"], "checkout_started")
    return {"url": session["url"], "mode": mode()}


@router.post("/payments/webhook")
async def webhook(request: Request):
    raw = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not _verify_signature(raw, sig_header, secret):
        return Response(status_code=400)
    try:
        event = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return Response(status_code=400)
    if event.get("type") != "checkout.session.completed":
        return Response(status_code=200)
    obj = (event.get("data") or {}).get("object") or {}
    jid = (obj.get("metadata") or {}).get("journey_id")
    j = journey.get_journey(jid) if jid else None
    if obj.get("payment_status") != "paid" or j is None:
        return Response(status_code=200)
    # The amount must be what we asked Stripe for: the session's amount, or (for a session we don't know) today's quote.
    asked = db.query("SELECT amount_cents FROM checkout_sessions WHERE id = ? AND journey_id = ?", (obj.get("id"), jid))
    if obj.get("amount_total") not in ({asked[0][0]} if asked else set()) | {_total(j)}:
        notify_staff("Pago con monto distinto", f"Expediente {jid}: Stripe cobró {obj.get('amount_total')} centavos; revise antes de continuar.")
        return Response(status_code=200)
    # Stripe retries until it gets a 200, sometimes concurrently: the unique session id makes recording happen once.
    new = db.execute("INSERT INTO payments (id, journey_id, session_id, amount_cents, paid_at) VALUES (?, ?, ?, ?, ?) "
                     "ON CONFLICT (session_id) DO NOTHING",
                     (str(uuid.uuid4()), jid, obj.get("id"), int(obj["amount_total"]), journey._now_iso()))
    if new:
        journey.apply(jid, "paid", {}, actor="stripe")
        jobs.enqueue("draft_documents", f"draft_documents:{jid}", {"journey_id": jid})
        legacy.set_stage(journey.get_journey(jid), "4 Drafting")
    return Response(status_code=200)


@router.get("/payments/return")
def return_payment(session_id: str = Query(...), authorization: str = Header(None)):
    u = _auth(authorization)
    _adult_check(u)
    j = journey.get_or_create_for_user(u["id"])
    return {"paid": "paid" in (j.get("facts") or {})}


class LiveApproval(BaseModel):
    approved: bool


class RefundBody(BaseModel):
    amount_cents: int
    reason: str


@router.post("/staff/journeys/{jid}/refunds")
def create_refund(jid: str, body: RefundBody, authorization: str = Header(None)):
    _staff(authorization, {"admin"})
    if journey.get_journey(jid) is None:
        raise HTTPException(404, "journey not found")
    db.execute(
        "INSERT INTO refunds (id, journey_id, amount_cents, reason, created_at) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), jid, int(body.amount_cents), body.reason, journey._now_iso()),
    )
    return {"ok": True}


@router.get("/payments/receipt")
def receipt(authorization: str = Header(None)):
    u = _auth(authorization)
    _adult_check(u)
    j = journey.get_or_create_for_user(u["id"])
    jid = j["id"]
    rows = db.query("SELECT amount_cents FROM payments WHERE journey_id = ?", (jid,))
    paid_cents = int(sum(r[0] for r in rows)) if rows else 0
    rrows = db.query("SELECT amount_cents, reason, created_at FROM refunds WHERE journey_id = ? ORDER BY created_at", (jid,))
    refunds = [{"amount_cents": r[0], "reason": r[1], "at": r[2]} for r in rrows]
    balance = paid_cents - sum(r["amount_cents"] for r in refunds)
    return {"paid_cents": paid_cents, "refunds": refunds, "balance_cents": balance}


@router.put("/staff/payments/live-approval")
def live_approval(body: LiveApproval, authorization: str = Header(None)):
    u = _staff(authorization, {"admin"})
    approved = body.approved
    now = journey._now_iso()
    db.execute(
        "INSERT INTO settings (key, value_json, updated_by, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT (key) DO UPDATE SET value_json = excluded.value_json, updated_by = excluded.updated_by, updated_at = excluded.updated_at",
        ("payments_live_approved", json.dumps(approved), u["email"], now),
    )
    return {"ok": True}
