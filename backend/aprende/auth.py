"""Shared auth dependencies for the Aprende routes.

FastAPI resolves these before it validates query parameters and request bodies, so a
missing/insufficient credential answers 401/403 before any 422.
"""
from fastapi import Depends, Header, HTTPException

import app as backend_app
from aprende import journey


def client_user(authorization: str = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(401, "not authenticated")
    user, _ = backend_app.require_auth(authorization)
    if user.get("role") != "client":
        raise HTTPException(403, "staff have no journey")
    if "adult_confirmed_at" not in user:
        raise HTTPException(403, "adult confirmation required")
    return user


def client_journey(user: dict = Depends(client_user)) -> dict:
    return journey.get_or_create_for_user(user["id"])


def signed_in(authorization: str = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(401, "not authenticated")
    user, _ = backend_app.require_auth(authorization)
    return user


def staff(*roles):
    allowed = set(roles) if roles else {"paralegal", "attorney", "admin"}

    def dep(authorization: str = Header(None)) -> dict:
        if not authorization:
            raise HTTPException(401, "not authenticated")
        return backend_app.require_auth(authorization, allowed)[0]

    return dep
