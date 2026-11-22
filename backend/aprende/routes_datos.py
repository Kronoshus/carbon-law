"""Routes for Tus datos (T5-05)."""
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from aprende import datos
from aprende import auth, datos, journey

router = APIRouter()


class Answer(BaseModel):
    answer: str | None = None
    skipped: bool = False


def _journey(j):
    if not j["gates"].get("may_collect_details", False):
        raise HTTPException(409, {"error": "gate", "missing": ["may_collect_details"]})
    return j


@router.get("/datos")
def get_datos(lang: str = "es", j: dict = Depends(auth.client_journey)):
    try:
        return datos.get_datos(_journey(j), "en" if lang == "en" else "es")
    except HTTPException as e:
        if e.status_code == 409:
            return JSONResponse(status_code=409, content=e.detail)
        raise


@router.put("/datos/{question_id}")
def put_datos(question_id: str, body: Answer, j: dict = Depends(auth.client_journey)):
    try:
        j = _journey(j)
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
