"""FastAPI routes for Aprende characters (T3-06)."""
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

import app as backend_app
from aprende import auth, characters

router = APIRouter()


class CharacterPatch(BaseModel):
    enabled: bool | None = None
    units: list[str] | None = None
    voice_es: str | None = None
    voice_en: str | None = None


def _auth(authorization, roles=None):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    u, _ = backend_app.require_auth(authorization, roles)
    return u


@router.get("/characters")
def get_characters(user: dict = Depends(auth.signed_in)):
    out = []
    for c in characters.list_enabled():
        out.append({
            "id": c["id"],
            "name_key": f"character.{c['id']}.name",
            "units": c["units"],
            "voice_es": c["voice_es"],
            "voice_en": c["voice_en"],
        })
    return out


@router.patch("/characters/{char_id}")
def patch_character(char_id: str, body: CharacterPatch, authorization: str = Header(None)):
    u = _auth(authorization, {"paralegal", "attorney", "admin"})
    existing = characters.get(char_id)
    if existing is None:
        raise HTTPException(404, "unknown character")
    fields = body.model_dump(exclude_unset=True)
    try:
        updated = characters.update(char_id, fields)
    except ValueError as e:
        raise HTTPException(409, str(e))
    backend_app.log_audit(u.get("email") or "staff", "character_update", "character", char_id, str(fields))
    return {
        "id": updated["id"],
        "name_key": f"character.{updated['id']}.name",
        "enabled": updated["enabled"],
        "units": updated["units"],
        "voice_es": updated["voice_es"],
        "voice_en": updated["voice_en"],
    }
