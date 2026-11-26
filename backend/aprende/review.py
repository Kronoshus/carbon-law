"""Attorney review queue (T6-05): drafts waiting, view, revise, approve or request changes."""
import base64
import datetime
import re

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

import app as backend_app
import db
from aprende import auth, clock, journey, legacy, timeline
from carbon_intake import docx as make_docx, unverified_cites

router = APIRouter()


TODO = re.compile(r"\[ATTORNEY TO COMPLETE[^\]]+\]")


class Version(BaseModel):
    content: str


class Decision(BaseModel):
    decision: str
    note: str | None = None


def _auth(authorization, roles=None):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    return backend_app.require_auth(authorization, roles)


def _current_drafts(jid):
    out = []
    for d in list(backend_app.documents.values()):
        if d.get("journey_id") != jid:
            continue
        if d.get("attorney_only") is not True:
            continue
        if d.get("status") == "Superseded":
            continue
        out.append(d)
    return out


def _change_requested(jid):
    """Approved documents whose client's latest decision is a change request: the attorney revises them."""
    out = []
    for d in list(backend_app.documents.values()):
        if d.get("journey_id") != jid or d.get("status") != "Attorney Approved":
            continue
        last = db.query("SELECT decision FROM client_reviews WHERE document_id = ? AND journey_id = ? ORDER BY at DESC, id DESC LIMIT 1",
                        (d["id"], jid))
        if last and last[0][0] == "change":
            out.append(d)
    return out


@router.get("/staff/review-queue")
def review_queue(authorization: str = Header(None)):
    _auth(authorization, {"paralegal", "attorney", "admin"})
    now = clock.now()
    rows = []
    for (jid,) in db.query("SELECT id FROM journeys"):
        j = journey.get_journey(jid)
        if not j or not j.get("matter_id"):
            continue
        drafts = _current_drafts(jid)
        asked = [] if drafts else _change_requested(jid)          # spec 6.1 day 10: a client's change goes to the attorney
        if not drafts and not asked:
            continue
        mid = j.get("matter_id")
        steps = timeline.for_journey(j, now)
        ar = next((s for s in steps if s["step"] == ("changes" if asked else "attorney_review")), None)
        due = (ar or {}).get("due") or (ar or {}).get("date")
        late = bool(ar and ar.get("status") == "late")
        matter = backend_app.matters.get(mid, {})
        rows.append({
            "journey_id": jid,
            "client_name": legacy._user_name(j["user_id"]),
            "due": due,
            "late": late,
            "note": matter.get("review_note"),
            "documents": [{"id": d["id"], "name": d["name"], "version": d["version"]} for d in drafts or asked],
        })
    return rows


@router.get("/staff/drafts/{doc_id}")
def get_draft(doc_id: str, authorization: str = Header(None)):
    _auth(authorization, {"attorney", "admin"})
    if doc_id not in backend_app.documents:
        raise HTTPException(404, "document not found")
    d = backend_app.documents[doc_id]
    return {"id": d["id"], "name": d["name"], "version": d["version"], "content": d.get("content")}


@router.get("/staff/drafts/{doc_id}/docx")
def get_draft_docx(doc_id: str, user: dict = Depends(auth.staff("attorney", "admin"))):
    if doc_id not in backend_app.documents:
        raise HTTPException(404, "document not found")
    d = backend_app.documents[doc_id]
    raw = base64.b64decode(d["docx_b64"])
    return Response(content=raw, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@router.post("/staff/drafts/{doc_id}/versions")
def new_version(doc_id: str, body: Version, user: dict = Depends(auth.staff("attorney", "admin"))):
    u = user
    if doc_id not in backend_app.documents:
        raise HTTPException(404, "document not found")
    old = backend_app.documents[doc_id]
    content = body.content
    j = journey.get_journey(old["journey_id"])
    mid = (j or {}).get("matter_id") or old.get("matter_id")
    rec = legacy.add_document_version(mid, old["journey_id"], old["name"], {
        "status": "Attorney Review", "attorney_only": True, "content": content,
        "docx_b64": base64.b64encode(make_docx(content, old["name"])).decode(),
    })
    if old.get("status") != "Attorney Approved":
        with backend_app._request_lock:
            backend_app.documents[doc_id]["status"] = "Superseded"
            backend_app.save_data()
    backend_app.log_audit(u["email"], "create", "document", rec["id"], "new version")
    return {"id": rec["id"], "name": rec["name"], "version": rec["version"]}


@router.post("/staff/journeys/{jid}/review")
def review_journey(jid: str, body: Decision, user: dict = Depends(auth.staff("attorney", "admin"))):
    u = user
    j = journey.get_journey(jid)
    if not j:
        raise HTTPException(404, "journey not found")
    mid = j.get("matter_id")
    matter = backend_app.matters.get(mid, {})
    assigned = matter.get("attorney_reviewer")
    if u["role"] != "admin" and assigned != u["id"]:
        raise HTTPException(403, "not assigned attorney")
    decision, note = body.decision, (body.note or "").strip()
    if decision == "changes":
        if not note:
            raise HTTPException(422, "note required")
        with backend_app._request_lock:
            backend_app.matters[mid]["review_note"] = note
            backend_app.save_data()
        backend_app.log_audit(u["email"], "review", "journey", jid, "changes")
        return {"ok": True}
    if decision != "approve":
        raise HTTPException(422, "invalid decision")
    drafts = _current_drafts(jid)
    if not drafts:
        raise HTTPException(409, "nothing to approve")
    # an open item has text inside the brackets; the notice at the top of every draft names the bare "[ATTORNEY TO COMPLETE]"
    if any(TODO.search(d["content"]) for d in drafts):
        raise HTTPException(409, "a draft still contains [ATTORNEY TO COMPLETE …]")
    unverified = sorted({s for d in drafts for s in unverified_cites(d["content"])})
    if unverified:
        raise HTTPException(409, "a draft cites sections not on the verified list: " + ", ".join(unverified))
    with backend_app._request_lock:
        for d in drafts:
            backend_app.documents[d["id"]]["status"] = "Attorney Approved"
            backend_app.documents[d["id"]]["attorney_only"] = False
        for d in drafts:
            for other in list(backend_app.documents.values()):
                if other.get("journey_id") == jid and other.get("name") == d["name"] \
                        and other["id"] != d["id"] and other.get("status") == "Attorney Approved":
                    other["status"] = "Superseded"
        backend_app.matters[mid]["review_note"] = None
        backend_app.save_data()
    journey.apply(jid, "attorney_approved", {}, actor="system")
    legacy.set_stage(journey.get_journey(jid), "6 Client Review")
    backend_app.log_audit(u["email"], "review", "journey", jid, "approve")
    return {"ok": True}
