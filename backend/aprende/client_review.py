"""Client review of attorney-approved documents (T6-06)."""
import os
import uuid

import yaml
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import app as backend_app
import db
from aprende import journey, legacy, content
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
    j, open_ = _client_journey(authorization, "may_see_documents")
    if not open_:
        return _gate_fail()
    is_en = (lang == "en")
    live = content.live_entries("summary")
    docs = []
    for d in _current_approved_docs(j):
        kind = NAME_TO_KIND.get(d.get("name"))
        summary = []
        if kind in _SUMMARIES:
            for art in _SUMMARIES[kind]:
                eid = f"summary:{kind}.{art['article']}"
                body = live.get(eid, {"es": art["es"], "en": art["en"]})
                text = body["en" if is_en else "es"]
                summary.append({"article": art["article"], "text": text})
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
    j, open_ = _client_journey(authorization, "may_see_documents")
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
        db.execute("INSERT INTO client_reviews (id, document_id, journey_id, decision, change_type, note, at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (str(uuid.uuid4()), doc_id, j["id"], "change", ct, note, journey._now_iso()))
        email = _user_email(j["user_id"])
        backend_app.record_change_request({"matter_id": j["matter_id"], "requested_by": email, "change_type": ct,
                                           "affected_documents": d["name"], "required_attorney_decision": True,
                                           "impact": "Revisión: 2 días hábiles", "status": "Open", "note": note}, email)
        journey.apply(j["id"], "changes_requested", {}, actor="system")
        legacy.set_stage(journey.get_journey(j["id"]), "5 Review Queue")
    else:
        db.execute("INSERT INTO client_reviews (id, document_id, journey_id, decision, change_type, note, at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (str(uuid.uuid4()), doc_id, j["id"], "ok", None, None, journey._now_iso()))
        # check all ok
        current = _current_approved_docs(journey.get_journey(j["id"]))
        all_ok = all(_latest_decision(dd["id"], j["id"]) == "ok" for dd in current) and len(current) > 0
        if all_ok:
            journey.apply(j["id"], "client_confirmed", {}, actor="system")
            legacy.set_stage(journey.get_journey(j["id"]), "7 Signing Preparation")
    return {"ok": True}
