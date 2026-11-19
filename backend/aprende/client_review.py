"""Client review of attorney-approved documents (T6-06)."""
import base64
import datetime
import json
import os
import uuid

import yaml
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import app as backend_app
import db
from aprende import journey, legacy
from aprende.chat import _client_journey

router = APIRouter()

SUMMARIES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                              "aprende", "content", "summaries.yaml")
with open(SUMMARIES_PATH, encoding="utf-8") as _f:
    _SUMMARIES = yaml.safe_load(_f)

NAME_TO_KIND = {
    "Last will and testament": "will",
    "Pour-over will": "will",
    "Revocable living trust": "trust",
    "Financial power of attorney": "poa",
    "Advance health care directive": "ahcd",
}

CHANGE_TYPES = [
    "Beneficiary change", "Fiduciary change", "Asset change", "Guardian change",
    "Distribution age change", "Title change", "Contact or address change",
    "Appointment change", "Document scope change",
]


class ReviewDecision(BaseModel):
    decision: str
    change_type: str | None = None
    note: str | None = None


def _user_email(user_id):
    for u in backend_app.users.values():
        if u.get("id") == user_id:
            return u.get("email")
    return None


def _latest_decision(document_id, journey_id):
    rows = db.query(
        "SELECT decision FROM client_reviews WHERE document_id = ? AND journey_id = ? ORDER BY at DESC, id DESC LIMIT 1",
        (document_id, journey_id))
    return rows[0][0] if rows else None


def _current_approved_docs(j):
    mid = j.get("matter_id")
    out = []
    for d in backend_app.documents.values():
        if d.get("matter_id") != mid:
            continue
        if d.get("status") != "Attorney Approved":
            continue
        if d.get("journey_id") != j["id"]:
            continue
        out.append(d)
    return out


def _gate_fail():
    return JSONResponse(status_code=409, content={"error": "gate", "missing": ["may_see_documents"]})


@router.get("/review/documents")
def get_review_documents(lang: str = "es", authorization: str = Header(None)):
    try:
        j, open_ = _client_journey(authorization, "may_see_documents")
    except HTTPException as e:
        if e.status_code in (401, 403):
            raise
        raise
    if not open_:
        return _gate_fail()
    is_en = (lang == "en")
    docs = []
    for d in _current_approved_docs(j):
        kind = NAME_TO_KIND.get(d.get("name"))
        summary = []
        if kind in _SUMMARIES:
            for art in _SUMMARIES[kind]:
                summary.append({"article": art["article"],
                                "text": (art["en"] if is_en else art["es"])})
        docs.append({
            "id": d["id"],
            "name": d["name"],
            "version": d.get("version"),
            "content": d.get("content"),
            "decision": _latest_decision(d["id"], j["id"]),
            "summary": summary,
        })
    return {"documents": docs}


@router.post("/review/documents/{doc_id}")
def post_review_document(doc_id: str, body: ReviewDecision, authorization: str = Header(None)):
    try:
        j, open_ = _client_journey(authorization, "may_see_documents")
    except HTTPException as e:
        if e.status_code in (401, 403):
            raise
        raise
    if not open_:
        return _gate_fail()
    if doc_id not in backend_app.documents:
        raise HTTPException(404, "document not found")
    d = backend_app.documents[doc_id]
    if d.get("status") != "Attorney Approved" or d.get("journey_id") != j["id"]:
        raise HTTPException(404, "document not found")
    if body.decision not in ("ok", "change"):
        raise HTTPException(422, "invalid decision")
    if body.decision == "change":
        ct = (body.change_type or "").strip()
        note = (body.note or "").strip()
        if not ct or ct not in CHANGE_TYPES:
            raise HTTPException(422, "invalid change_type")
        if not note:
            raise HTTPException(422, "note required")
        # store decision
        with backend_app._request_lock:
            db.execute(
                "INSERT INTO client_reviews (id, document_id, journey_id, decision, change_type, note, at) VALUES (?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), doc_id, j["id"], "change", ct, note, backend_app.now_iso()))
            backend_app.save_data()
        # create legacy change request
        mid = j.get("matter_id")
        cr = {
            "matter_id": mid,
            "requested_by": _user_email(j["user_id"]),
            "change_type": ct,
            "affected_documents": d["name"],
            "required_attorney_decision": True,
            "impact": "Revisión: 2 días hábiles",
            "status": "Open",
            "note": note,
        }
        # replicate POST /change-requests logic
        rec = dict(cr)
        rec["id"] = str(uuid.uuid4())
        rec["created_at"] = backend_app.now_iso()
        tid = str(uuid.uuid4())
        backend_app.tasks[tid] = {"id": tid, "matter_id": mid, "title": f"Review change: {ct}",
                                 "owner": backend_app.matters[mid].get("owner", "Unassigned"), "due_date": None,
                                 "status": "Open", "blocker": "None", "created_at": backend_app.now_iso()}
        rec["task_id"] = tid
        backend_app.changes.append(rec)
        backend_app.log_audit(rec["requested_by"], "create", "change_request", rec["id"], ct)
        backend_app.save_data()
        journey.apply(j["id"], "changes_requested", {}, actor="system")
        legacy.set_stage(journey.get_journey(j["id"]), "5 Review Queue")
    else:
        with backend_app._request_lock:
            db.execute(
                "INSERT INTO client_reviews (id, document_id, journey_id, decision, change_type, note, at) VALUES (?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), doc_id, j["id"], "ok", None, None, backend_app.now_iso()))
            backend_app.save_data()
        # check all ok
        current = _current_approved_docs(journey.get_journey(j["id"]))
        all_ok = all(_latest_decision(dd["id"], j["id"]) == "ok" for dd in current) and len(current) > 0
        if all_ok:
            journey.apply(j["id"], "client_confirmed", {}, actor="system")
            legacy.set_stage(journey.get_journey(j["id"]), "7 Signing Preparation")
    return {"ok": True}
