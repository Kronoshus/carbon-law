"""Routes for learning (T4-03); the contract is in tests/test_learn.py."""
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel

import app as backend_app
from aprende import auth, journey, learn

router = APIRouter()


class Attempt(BaseModel):
    item_id: str
    answer: Any
    lang: str = "es"




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
def get_map(j: dict = Depends(auth.client_journey)):
    return learn.get_map(j)


@router.get("/learn/lessons/{lesson_id}")
def get_lesson(lesson_id: str, lang: str = Query("es", pattern="^(es|en)$"), j: dict = Depends(auth.client_journey)):
    return _call(learn.get_lesson, j, lesson_id, lang)


@router.post("/learn/attempts")
def post_attempt(body: Attempt, j: dict = Depends(auth.client_journey)):
    return _call(learn.submit_attempt, j, body.item_id, body.answer, "en" if body.lang == "en" else "es")


@router.post("/learn/lessons/{lesson_id}/complete")
def complete(lesson_id: str, j: dict = Depends(auth.client_journey)):
    return _call(learn.complete_lesson, j, lesson_id)
