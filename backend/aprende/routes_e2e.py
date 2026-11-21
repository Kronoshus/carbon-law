"""Test backend only: move the server clock (aprende.clock). app.py registers this router only when the clock is enabled."""
import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aprende import clock

router = APIRouter()


class Moment(BaseModel):
    now: datetime.datetime


@router.get("/e2e/clock")
def get_clock():
    return {"now": clock.now().isoformat()}


@router.post("/e2e/clock")
def set_clock(body: Moment):
    if body.now.tzinfo is None:
        raise HTTPException(422, "a time zone offset is required")
    try:
        clock.set_now(body.now)
    except ValueError:
        raise HTTPException(409, "the clock only moves forward")
    return {"now": clock.now().isoformat()}
