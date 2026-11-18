"""Routes for Tus datos (T5-05)."""
from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import app as backend_app
from aprende import datos, journey

router = APIRouter()


class DatosBody(BaseModel):
    answer: str | None = None
    skipped: bool | None = None


def _journey(authorization):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    user, _ = backend_app.require_auth(authorization)
    if user.get("role") != "client":
        raise HTTPException(403, "staff have no journey")
    if "adult_confirmed_at" not in user:
        raise HTTPException(403, "adult confirmation required")
    j = journey.get_or_create_for_user(user["id"])
    if not j["gates"].get("may_collect_details"):
        return None, JSONResponse(status_code=409, content={"error": "gate", "missing": ["may_collect_details"]})
    return j, None


@router.get("/datos")
def get_datos(lang: str = Query("es"), authorization: str = Header(None)):
    j, err = _journey(authorization)
    if err is not None:
        return err
    l = "en" if lang == "en" else "es"
    return datos.get_datos(j, l)


@router.put("/datos/{question_id}")
def put_datos(question_id: str, body: DatosBody, authorization: str = Header(None)):
    j, err = _journey(authorization)
    if err is not None:
        return err
    q = datos.by_id(question_id)
    if q is None:
        raise HTTPException(404, "unknown question")
    try:
        if body.skipped is True:
            datos.put_datos(j, question_id, {"skipped": True})
        else:
            datos.put_datos(j, question_id, {"answer": body.answer if body.answer is not None else ""})
    except ValueError as e:
        raise HTTPException(422, str(e))
    except KeyError:
        raise HTTPException(404, "unknown question")
    return {"ok": True}
