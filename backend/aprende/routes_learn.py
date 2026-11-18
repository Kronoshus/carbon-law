"""Routes for learning (T4-03); the contract is in tests/test_learn.py."""
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

import app as backend_app
from aprende import journey, learn

router = APIRouter()


class Attempt(BaseModel):
    item_id: str
    answer: Any
    lang: str = "es"


def _journey(authorization):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    user, _ = backend_app.require_auth(authorization)
    if user.get("role") != "client":
        raise HTTPException(403, "staff have no journey")
    if "adult_confirmed_at" not in user:
        raise HTTPException(403, "adult confirmation required")
    return journey.get_or_create_for_user(user["id"])


def _call(fn, *args):
    try:
        return fn(*args)
    except KeyError:
        raise HTTPException(404, "not found")
    except PermissionError:
        raise HTTPException(409, "locked")
    except ValueError as error:
        raise HTTPException(422, str(error))


@router.get("/learn/map")
def get_map(authorization: str = Header(None)):
    return learn.get_map(_journey(authorization))


@router.get("/learn/lessons/{lesson_id}")
def get_lesson(lesson_id: str, lang: str = Query("es", pattern="^(es|en)$"), authorization: str = Header(None)):
    return _call(learn.get_lesson, _journey(authorization), lesson_id, lang)


@router.post("/learn/attempts")
def post_attempt(body: Attempt, authorization: str = Header(None)):
    return _call(learn.submit_attempt, _journey(authorization), body.item_id, body.answer, "en" if body.lang == "en" else "es")


@router.post("/learn/lessons/{lesson_id}/complete")
def complete(lesson_id: str, authorization: str = Header(None)):
    return _call(learn.complete_lesson, _journey(authorization), lesson_id)
