"""Firm settings routes (T7-05)."""
import json

from fastapi import APIRouter, Header, HTTPException

import app as backend_app
from aprende import firm

router = APIRouter()


def _staff(authorization):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    u, _ = backend_app.require_auth(authorization, {"paralegal", "attorney", "admin"})
    return u


def _attorney_or_admin(authorization):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    u, _ = backend_app.require_auth(authorization, {"attorney", "admin"})
    return u


@router.get("/staff/firm-settings")
def get_firm_settings(authorization: str = Header(None)):
    _staff(authorization)
    return firm.get()


@router.put("/staff/firm-settings")
def put_firm_settings(body: dict, authorization: str = Header(None)):
    u = _attorney_or_admin(authorization)
    return firm.update(body, u["email"])


@router.get("/settings/public")
def public_settings():
    return {"switches": firm.get()["switches"]}
