"""Routes for progress / motivation (T4-06)."""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

import app as backend_app
from aprende import journey, progress as P

router = APIRouter()


class ReminderBody(BaseModel):
    enabled: bool
    local_time: str


def _journey(authorization):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    user, _ = backend_app.require_auth(authorization)
    if user.get("role") != "client":
        raise HTTPException(403, "staff have no journey")
    if "adult_confirmed_at" not in user:
        raise HTTPException(403, "adult confirmation required")
    return journey.get_or_create_for_user(user["id"])


@router.get("/progress")
def get_progress(authorization: str = Header(None)):
    j = _journey(authorization)
    return P.progress(j)


@router.put("/progress/reminders")
def put_reminders(body: ReminderBody, authorization: str = Header(None)):
    j = _journey(authorization)
    return P.set_reminder(j["id"], body.enabled, body.local_time)
