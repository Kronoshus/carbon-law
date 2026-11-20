"""Routes for progress / motivation (T4-06)."""
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

import app as backend_app
from aprende import auth, journey, motivation

router = APIRouter()


class ReminderBody(BaseModel):
    enabled: bool
    local_time: str




@router.get("/progress")
def get_progress(j: dict = Depends(auth.client_journey)):
    return motivation.progress(j)


@router.put("/progress/reminders")
def put_reminders(body: ReminderBody, j: dict = Depends(auth.client_journey)):
    try:
        return motivation.set_reminder(j["id"], body.enabled, body.local_time)
    except ValueError as error:
        raise HTTPException(422, str(error))
