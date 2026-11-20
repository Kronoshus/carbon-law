"""Routes for the engagement letter (T6-01)."""
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

import app as backend_app
from aprende import auth, engagement, journey

router = APIRouter()


def _gate(j):
    if not j["gates"]["may_sign_engagement"] and not engagement.signature(j["id"]):
        return JSONResponse(status_code=409, content={"error": "gate", "missing": ["may_sign_engagement"]})
    if engagement.missing():
        return JSONResponse(status_code=409, content={"error": "not_ready", "missing": engagement.missing()})
    return None


class Template(BaseModel):
    es: str
    en: str


class Profile(BaseModel):
    bar_number: str
    costs_line: dict[str, str]
    refund_policy: dict[str, str]
    data_promise: dict[str, str]


class Signature(BaseModel):
    name: str
    accept: bool
    sha256: str


@router.post("/staff/engagement-templates")
def create_template(body: Template, user: dict = Depends(auth.staff("attorney", "admin"))):
    u = user
    return engagement.create_template(body.es, body.en, u["email"])


@router.post("/staff/engagement-templates/{tid}/approve")
def approve_template(tid: str, user: dict = Depends(auth.staff("attorney"))):
    u = user
    if not engagement.approve_template(tid, u["email"]):
        raise HTTPException(404, "template not found")
    return {"ok": True}


@router.put("/staff/firm-profile")
def put_profile(body: Profile, user: dict = Depends(auth.staff("attorney", "admin"))):
    u = user
    engagement.set_firm_profile(body.model_dump(), u["email"])
    return {"ok": True}


@router.post("/staff/journeys/{jid}/scope-approval")
def approve_scope(jid: str, user: dict = Depends(auth.staff("attorney"))):
    u = user
    j = journey.get_journey(jid)
    if j is None:
        raise HTTPException(404, "journey not found")
    if not j["documents"]["confirmed"]:
        raise HTTPException(409, "the client has not confirmed documents")
    journey.apply(jid, "scope_approved", {}, actor=u["email"])
    return {"ok": True}


@router.post("/staff/journeys/{jid}/engagement/countersign")
def countersign(jid: str, user: dict = Depends(auth.staff("attorney"))):
    u = user
    if not engagement.signature(jid):
        raise HTTPException(409, "the client has not signed")
    engagement.countersign(jid, u.get("name") or u["email"])
    return {"ok": True}


@router.get("/staff/journeys/{jid}/engagement/pdf")
def staff_pdf(jid: str, user: dict = Depends(auth.staff())):
    sig = engagement.signature(jid)
    if not sig:
        raise HTTPException(409, "not signed")
    return Response(engagement.pdf(sig), media_type="application/pdf")


@router.get("/engagement")
def get_letter(lang: str = "es", user: dict = Depends(auth.client_user), j: dict = Depends(auth.client_journey)):
    blocked = _gate(j)
    if blocked:
        return blocked
    sig = engagement.signature(j["id"])
    if sig:                                                      # once signed, the client sees exactly what she signed
        return {k: sig[k] for k in ("template_id", "version", "lang", "text", "sha256", "client_signed_at", "attorney_signed_at")}
    return {**engagement.render(j, "en" if lang == "en" else "es"), "client_signed_at": None, "attorney_signed_at": None}


@router.post("/engagement/sign")
def sign(body: Signature, request: Request, user: dict = Depends(auth.client_user), j: dict = Depends(auth.client_journey)):

    if not body.accept or not body.name.strip():
        raise HTTPException(422, "type your name and accept")
    blocked = _gate(j)
    if blocked:
        return blocked
    try:
        engagement.sign(j, body.name.strip(), body.sha256, request.client.host if request.client else None)
    except LookupError:
        return JSONResponse(status_code=409, content={"error": "text_changed"})
    return {"ok": True}


@router.get("/engagement/pdf")
def client_pdf(user: dict = Depends(auth.client_user), j: dict = Depends(auth.client_journey)):
    sig = engagement.signature(j["id"])
    if not sig:
        return JSONResponse(status_code=409, content={"error": "not_signed"})
    return Response(engagement.pdf(sig), media_type="application/pdf")
