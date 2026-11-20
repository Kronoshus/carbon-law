"""FastAPI routes for Aprende conflicts (staff-only, T5-03)."""
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, Header, HTTPException

import app as backend_app
from aprende import auth, conflicts, journey

router = APIRouter()


class ListBody(BaseModel):
    csv: str = Field(default="")


class DecisionBody(BaseModel):
    result: str


@router.post("/conflicts/list")
def upload_list(body: ListBody, user: dict = Depends(auth.staff())):
    return conflicts.replace_list(body.csv)


@router.delete("/conflicts/list")
def delete_list(user: dict = Depends(auth.staff())):
    conflicts.delete_list()
    return {"ok": True}


@router.get("/conflicts/queue")
def get_queue(user: dict = Depends(auth.staff())):
    return conflicts.queue()


@router.post("/conflicts/{journey_id}/decision")
def decide(journey_id: str, body: DecisionBody, user: dict = Depends(auth.staff())):
    u = user
    if body.result not in ("cleared", "flagged"):
        raise HTTPException(422, "result must be cleared or flagged")
    try:
        conflicts.decide(journey_id, body.result, u.get("email") or "staff")
    except KeyError:
        raise HTTPException(404, "unknown journey")
    except ValueError:
        raise HTTPException(422, "invalid result")
    return {"ok": True}
