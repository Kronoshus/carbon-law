"""Firm settings routes (T7-05)."""
import json

from fastapi import APIRouter, Header, HTTPException

import app as backend_app
from aprende import firm

router = APIRouter()


def _staff(authorization, roles):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    u, _ = backend_app.require_auth(authorization, roles)
    return u


@router.get("/staff/firm-settings")
def get_firm_settings(authorization: str = Header(None)):
    _staff(authorization, {"paralegal", "attorney", "admin"})
    return firm.get()


@router.put("/staff/firm-settings")
def put_firm_settings(body: dict, authorization: str = Header(None)):
    u = _staff(authorization, {"attorney", "admin"})
    try:
        return firm.update(body, u["email"])
    except firm.FirmSettingsError as e:
        raise HTTPException(422, str(e))


@router.get("/settings/public")
def public_settings():
    return {"switches": firm.get()["switches"]}
