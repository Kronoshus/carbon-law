"""Routes for signing, executed documents, and funding (T6-08)."""
import base64
import datetime
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

import app as backend_app
from aprende import jobs, journey, legacy, signing

router = APIRouter()


def _staff(authorization, roles):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    return backend_app.require_auth(authorization, roles)[0]


def _client(authorization):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    user, _ = backend_app.require_auth(authorization)
    if user.get("role") != "client":
        raise HTTPException(403, "staff have no journey")
    if "adult_confirmed_at" not in user:
        raise HTTPException(403, "adult confirmation required")
    return user, journey.get_or_create_for_user(user["id"])


class ExecutedDoc(BaseModel):
    name: str
    filename: str
    content_b64: str


class ExecutedBody(BaseModel):
    documents: list[ExecutedDoc]


@router.post("/staff/journeys/{jid}/executed")
def upload_executed(jid: str, body: ExecutedBody, authorization: str = Header(None)):
    u = _staff(authorization, {"paralegal", "attorney", "admin"})
    j = journey.get_journey(jid)
    if j is None:
        raise HTTPException(404, "journey not found")
    if "client_confirmed" not in (j.get("facts") or {}):
        raise HTTPException(409, "client has not confirmed")
    for d in body.documents:
        try:
            base64.b64decode(d.content_b64, validate=True)
        except ValueError:
            raise HTTPException(422, f"{d.filename} is not valid base64")
    signing.store_executed(jid, [d.model_dump() for d in body.documents], u["email"])
    j = journey.apply(jid, "signed", {}, actor=u["email"])
    legacy.set_stage(j, "8 Execution")
    legacy.set_stage(j, "9 Funding Follow-Up")
    signed_at = datetime.datetime.fromisoformat(j["facts"]["signed"])
    for week, days in ((2, 14), (6, 42), (12, 84)):
        jobs.enqueue("funding_checkin", f"funding_checkin:{jid}:{week}",
                     payload={"journey_id": jid, "week": week},
                     run_after=signed_at + datetime.timedelta(days=days))
    return {"ok": True}


@router.get("/signed-documents")
def list_signed(authorization: str = Header(None)):
    user, j = _client(authorization)
    return signing.list_for_journey(j["id"])


@router.get("/signed-documents/{did}")
def get_signed(did: str, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    user, _ = backend_app.require_auth(authorization)
    doc = signing.get_document(did)
    if doc is None:
        raise HTTPException(404, "not found")
    j = journey.get_journey(doc["journey_id"])
    if j is None or j["user_id"] != user["id"]:
        raise HTTPException(404, "not found")
    content = base64.b64decode(doc["content_b64"])
    return Response(content=content, media_type=signing.content_type(doc["filename"]),
                    headers={"Content-Disposition": f'attachment; filename="{doc["filename"]}"'})


@router.get("/funding-checklist")
def get_checklist(authorization: str = Header(None)):
    user, j = _client(authorization)
    try:
        text = signing.funding_checklist_text(j)
    except ValueError:
        raise HTTPException(409, "not signed")
    except LookupError:
        raise HTTPException(404, "no trust document")
    return Response(content=text, media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="funding-checklist.md"'})


@router.post("/staff/journeys/{jid}/funding-done")
def funding_done(jid: str, authorization: str = Header(None)):
    u = _staff(authorization, {"paralegal", "attorney", "admin"})
    j = journey.get_journey(jid)
    if j is None:
        raise HTTPException(404, "journey not found")
    legacy.set_stage(journey.apply(jid, "funding_done", {}, actor=u["email"]), "10 Closed")
    return {"ok": True}
