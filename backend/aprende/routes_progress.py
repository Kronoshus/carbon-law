"""Routes for progress / motivation (T4-06) + push (T8-03)."""
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, HttpUrl

import app as backend_app
from aprende import auth, journey, motivation, push

router = APIRouter()


class ReminderBody(BaseModel):
    enabled: bool
    local_time: str


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class PushBody(BaseModel):
    endpoint: str
    keys: PushKeys
    lang: str = "es"


@router.get("/progress")
def get_progress(j: dict = Depends(auth.client_journey)):
    return motivation.progress(j)


@router.put("/progress/reminders")
def put_reminders(body: ReminderBody, j: dict = Depends(auth.client_journey)):
    try:
        res = motivation.set_reminder(j["id"], body.enabled, body.local_time)
    except ValueError as error:
        raise HTTPException(422, str(error))
    if not body.enabled:
        push.unsubscribe(j["id"])
    return res


@router.get("/progress/push-key")
def get_push_key(j: dict = Depends(auth.client_journey)):
    return {"public_key": push.public_key()}


@router.put("/progress/push")
def put_push(body: PushBody, j: dict = Depends(auth.client_journey)):
    if not motivation.get_reminder(j["id"]).get("enabled"):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=409, content={"error": "reminders_off"})
    # validation
    from urllib.parse import urlparse
    u = urlparse(body.endpoint)
    if u.scheme != "https" or len(body.endpoint) > 500:
        raise HTTPException(422, "bad endpoint")
    if body.lang not in ("es", "en"):
        raise HTTPException(422, "bad lang")
    if len(body.keys.p256dh) < 10 or len(body.keys.auth) < 10:
        raise HTTPException(422, "bad keys")
    push.subscribe(j["id"], body.endpoint, body.keys.p256dh, body.keys.auth, body.lang)
    return {"ok": True}


@router.delete("/progress/push")
def delete_push(j: dict = Depends(auth.client_journey)):
    return {"removed": push.unsubscribe(j["id"])}
