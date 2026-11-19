"""FastAPI routes for engagement letter (T6-01)."""
import hashlib
import json
from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import Response, JSONResponse

import app as backend_app
from aprende import engagement, journey

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


def _staff(authorization, roles=None):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    roles = roles or {"paralegal", "attorney", "admin"}
    u, _ = backend_app.require_auth(authorization, roles)
    return u


def _attorney(authorization):
    return _staff(authorization, {"attorney"})


def _admin_or_attorney(authorization):
    return _staff(authorization, {"attorney", "admin"})


# --- staff template management ---

class TemplateBody:
    pass


from pydantic import BaseModel, Field


class TplBody(BaseModel):
    es: str
    en: str


@router.post("/staff/engagement-templates")
def create_tpl(body: TplBody, authorization: str = Header(None)):
    u = _admin_or_attorney(authorization)
    res = engagement.create_template(body.es, body.en, u.get("email") or "staff")
    return {"id": res["id"], "version": res["version"]}


@router.post("/staff/engagement-templates/{tid}/approve")
def approve_tpl(tid: str, authorization: str = Header(None)):
    u = _attorney(authorization)
    engagement.approve_template(tid, u.get("email") or "attorney")
    return {"ok": True}


# fix approve to record email
# monkey: rebind below not needed; update function call properly by overriding


class ProfileBody(BaseModel):
    bar_number: str = ""
    costs_line: dict = Field(default_factory=dict)
    refund_policy: dict = Field(default_factory=dict)
    data_promise: dict = Field(default_factory=dict)


@router.put("/staff/firm-profile")
def put_profile(body: ProfileBody, authorization: str = Header(None)):
    u = _admin_or_attorney(authorization)
    engagement.set_firm_profile(body.model_dump(), u.get("email") or "staff")
    return {"ok": True}


@router.post("/staff/journeys/{jid}/scope-approval")
def scope_approval(jid: str, authorization: str = Header(None)):
    u = _attorney(authorization)
    # 409 if client has no confirmed documents
    j = journey.get_journey(jid)
    if j is None:
        raise HTTPException(404, "journey not found")
    confirmed = (j.get("documents") or {}).get("confirmed") or []
    if not confirmed:
        raise HTTPException(409, "no confirmed documents")
    try:
        journey.apply(jid, "scope_approved", {}, actor=u.get("email") or "attorney")
    except ValueError:
        raise HTTPException(404, "journey not found")
    return {"ok": True}


# --- client engagement ---

@router.get("/engagement")
def get_engagement(lang: str = Query("es"), authorization: str = Header(None)):
    u = _auth(authorization)
    _adult_check(u)
    j = journey.get_or_create_for_user(u["id"])
    # gate
    if not j["gates"].get("may_sign_engagement", False):
        return JSONResponse(status_code=409, content={"error": "gate", "missing": ["may_sign_engagement"]})
    template = engagement.get_approved_template()
    profile = engagement.get_firm_profile()
    missing = []
    if template is None:
        missing.append("approved_template")
    if profile is None:
        missing.append("firm_profile")
    if missing:
        return JSONResponse(status_code=409, content={"error": "not_ready", "missing": missing})
    # signed?
    sig = engagement.get_signature(j["id"])
    if sig is not None:
        # return signed text
        text = sig["text"]
        sha = sig["sha256"]
        client_signed_at = sig["client_signed_at"]
        attorney_signed_at = sig["attorney_signed_at"]
        return {
            "template_id": sig["template_id"],
            "version": sig["version"],
            "lang": sig["lang"],
            "text": text,
            "sha256": sha,
            "client_signed_at": client_signed_at,
            "attorney_signed_at": attorney_signed_at,
        }
    text, sha = engagement.render_current(j, lang)
    return {
        "template_id": template["id"],
        "version": template["version"],
        "lang": lang,
        "text": text,
        "sha256": sha,
        "client_signed_at": None,
        "attorney_signed_at": None,
    }


class SignBody(BaseModel):
    name: str = ""
    accept: bool = False
    sha256: str = ""


@router.post("/engagement/sign")
def sign_engagement(body: SignBody, request: Request, authorization: str = Header(None)):
    u = _auth(authorization)
    _adult_check(u)
    j = journey.get_or_create_for_user(u["id"])
    if not body.accept or not (body.name or "").strip():
        raise HTTPException(422, "invalid")
    ip = request.client.host if request.client else None
    try:
        res = engagement.sign(j["id"], body.name, body.accept, body.sha256, ip)
    except ValueError as e:
        msg = str(e)
        if msg == "text_changed":
            return JSONResponse(status_code=409, content={"error": "text_changed"})
        if msg == "invalid":
            raise HTTPException(422, "invalid")
        raise HTTPException(409, msg)
    if res == "noop":
        return {"ok": True}
    return {"ok": True}


@router.get("/engagement/pdf")
def engagement_pdf(authorization: str = Header(None)):
    u = _auth(authorization)
    _adult_check(u)
    j = journey.get_or_create_for_user(u["id"])
    sig = engagement.get_signature(j["id"])
    if sig is None:
        return JSONResponse(status_code=409, content={"error": "not_signed"})
    pdf = engagement.make_pdf(sig, for_staff=False)
    return Response(content=pdf, media_type="application/pdf")


@router.post("/staff/journeys/{jid}/engagement/countersign")
def countersign(jid: str, authorization: str = Header(None)):
    u = _attorney(authorization)
    sig = engagement.get_signature(jid)
    if sig is None:
        return JSONResponse(status_code=409, content={"error": "not_signed"})
    try:
        engagement.countersign(jid, u.get("name") or u.get("email") or "attorney")
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {"ok": True}


@router.get("/staff/journeys/{jid}/engagement/pdf")
def staff_engagement_pdf(jid: str, authorization: str = Header(None)):
    _staff(authorization)
    sig = engagement.get_signature(jid)
    if sig is None:
        return JSONResponse(status_code=409, content={"error": "not_signed"})
    pdf = engagement.make_pdf(sig, for_staff=True)
    return Response(content=pdf, media_type="application/pdf")
