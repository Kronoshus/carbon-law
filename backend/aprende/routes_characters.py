"""FastAPI routes for Aprende characters (T3-06, T7-03)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import app as backend_app
from aprende import auth, characters

router = APIRouter()


class CharacterPatch(BaseModel):
    enabled: bool | None = None
    units: list[str] | None = None
    voice_es: str | None = None
    voice_en: str | None = None


def _public(c: dict) -> dict:
    return {"id": c["id"], "name_key": f"character.{c['id']}.name", "units": c["units"],
            "voice_es": c["voice_es"], "voice_en": c["voice_en"]}


@router.get("/staff/characters")
def staff_characters(user: dict = Depends(auth.staff())):
    return [{**_public(c), "enabled": c["enabled"]} for c in characters.list_all()]


@router.get("/characters")
def get_characters(user: dict = Depends(auth.signed_in)):
    return [_public(c) for c in characters.list_enabled()]


@router.patch("/characters/{char_id}")
def patch_character(char_id: str, body: CharacterPatch, u: dict = Depends(auth.staff())):
    if characters.get(char_id) is None:
        raise HTTPException(404, "unknown character")
    fields = body.model_dump(exclude_unset=True)
    try:
        updated = characters.update(char_id, fields)
    except ValueError as e:
        raise HTTPException(422 if "unknown unit" in str(e) else 409, str(e))
    backend_app.log_audit(u.get("email") or "staff", "character_update", "character", char_id, str(fields))
    return {**_public(updated), "enabled": updated["enabled"]}
