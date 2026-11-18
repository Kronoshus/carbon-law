"""FastAPI routes for the Aprende journey."""
import os, sys, json
from fastapi import APIRouter, Header, HTTPException, Body
from fastapi.responses import JSONResponse

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

import app as backend_app
from aprende import journey

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


@router.get("/journey")
def get_journey(authorization: str = Header(None)):
    u = _auth(authorization)
    _adult_check(u)
    j = journey.get_or_create_for_user(u["id"])
    return j


class EventBody:
    pass


@router.post("/journey/events")
def post_event(body: dict = Body(...), authorization: str = Header(None)):
    u = _auth(authorization)
    _adult_check(u)
    j = journey.get_or_create_for_user(u["id"])
    etype = body.get("type")
    payload = body.get("payload", {}) or {}
    if etype not in journey.ALL_EVENTS:
        raise HTTPException(422, "unknown event type")
    if etype not in journey.CLIENT_EVENTS:
        raise HTTPException(403, "server-only event")
    # validation
    if etype == "consent":
        if not isinstance(payload, dict) or payload.get("answer") not in ("yes", "no"):
            raise HTTPException(422, "answer must be yes or no")
    if etype == "names_submitted":
        names = payload.get("names") if isinstance(payload, dict) else None
        if not isinstance(names, list) or len(names) == 0 or len(names) > 20:
            raise HTTPException(422, "invalid names")
        for n in names:
            if not isinstance(n, str) or len(n) == 0 or len(n) > 120:
                raise HTTPException(422, "invalid name")
    # gate check
    g = journey.gates(j["facts"])
    required = journey.REQUIRED_GATE.get(etype, "may_disclose")
    if not g.get(required, False):
        return JSONResponse(status_code=409, content={"error": "gate", "missing": [required]})
    # apply
    updated = journey.apply(j["id"], etype, payload, actor=u.get("email") or "client")
    return updated
