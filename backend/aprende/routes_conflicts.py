"""FastAPI routes for Aprende conflicts (staff-only, T5-03)."""
from pydantic import BaseModel, Field

from fastapi import APIRouter, Header, HTTPException

import app as backend_app
from aprende import conflicts, journey

router = APIRouter()


def _staff(authorization):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    u, _ = backend_app.require_auth(authorization, {"paralegal", "attorney", "admin"})
    return u


class ListBody(BaseModel):
    csv: str = Field(default="")


class DecisionBody(BaseModel):
    result: str


@router.post("/conflicts/list")
def upload_list(body: ListBody, authorization: str = Header(None)):
    _staff(authorization)
    return conflicts.replace_list(body.csv)


@router.delete("/conflicts/list")
def delete_list(authorization: str = Header(None)):
    _staff(authorization)
    conflicts.delete_list()
    return {"ok": True}


@router.get("/conflicts/queue")
def get_queue(authorization: str = Header(None)):
    _staff(authorization)
    return conflicts.queue()


@router.post("/conflicts/{journey_id}/decision")
def decide(journey_id: str, body: DecisionBody, authorization: str = Header(None)):
    u = _staff(authorization)
    if body.result not in ("cleared", "flagged"):
        raise HTTPException(422, "result must be cleared or flagged")
    try:
        conflicts.decide(journey_id, body.result, u.get("email") or "staff")
    except KeyError:
        raise HTTPException(404, "unknown journey")
    except ValueError:
        raise HTTPException(422, "invalid result")
    return {"ok": True}
