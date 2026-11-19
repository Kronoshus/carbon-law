"""Routes for Tus datos (T5-05)."""
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from aprende import datos
from aprende.chat import _client_journey

router = APIRouter()


class Answer(BaseModel):
    answer: str | None = None
    skipped: bool = False


def _journey(authorization):
    j, open_ = _client_journey(authorization, "may_collect_details")
    if not open_:
        raise HTTPException(409, {"error": "gate", "missing": ["may_collect_details"]})
    return j


@router.get("/datos")
def get_datos(lang: str = "es", authorization: str = Header(None)):
    try:
        return datos.get_datos(_journey(authorization), "en" if lang == "en" else "es")
    except HTTPException as e:
        if e.status_code == 409:
            return JSONResponse(status_code=409, content=e.detail)
        raise


@router.put("/datos/{question_id}")
def put_datos(question_id: str, body: Answer, authorization: str = Header(None)):
    try:
        j = _journey(authorization)
    except HTTPException as e:
        if e.status_code == 409:
            return JSONResponse(status_code=409, content=e.detail)
        raise
    if question_id not in datos.BY_ID:
        raise HTTPException(404, "unknown question")
    if not body.skipped and not (body.answer or "").strip():
        raise HTTPException(422, "answer or skipped required")
    datos.save(j, question_id, answer=None if body.skipped else body.answer.strip())
    return {"ok": True}
