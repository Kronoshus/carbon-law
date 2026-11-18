"""FastAPI routes for Aprende payments (quote only in T4-08)."""
from fastapi import APIRouter, Header, HTTPException, Query

import app as backend_app
from aprende import journey, pricing

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


@router.get("/payments/quote")
def get_quote(codes: str = Query(...), authorization: str = Header(None)):
    u = _auth(authorization)
    _adult_check(u)
    j = journey.get_or_create_for_user(u["id"])
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    settings = pricing.load_settings("pricing")
    if settings is None:
        settings = {}
    rows = db_query_discounts(j["id"]) if False else None
    import db
    drows = db.query("SELECT document, event, amount_cents FROM discounts WHERE journey_id = ?", (j["id"],))
    earned = [{"document": r[0], "event": r[1], "amount_cents": r[2]} for r in drows]
    q = pricing.quote(settings, j["facts"], code_list, discounts=earned)
    return q
