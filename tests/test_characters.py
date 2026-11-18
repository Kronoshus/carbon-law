"""T3-06 acceptance tests."""
import datetime
import json
import os
import sys
import tempfile
import uuid

os.environ.setdefault("DATABASE_URL", "")
os.environ.setdefault("CARBON_DB_PATH", tempfile.mktemp(suffix=".db"))
sys.path.insert(0, "backend")

import pytest
from fastapi.testclient import TestClient

import app as backend
import migrate
from aprende import characters

migrate.run()
c = TestClient(backend.app)

STAFF_EMAIL = "char-staff@example.com"
backend.users[STAFF_EMAIL] = {"id": str(uuid.uuid4()), "name": "Char Staff", "email": STAFF_EMAIL, "role": "paralegal",
                              "password_hash": backend.hash_pw("char-staff-password"),
                              "created_at": datetime.datetime.utcnow().isoformat()}


def staff():
    token = c.post("/auth/login", json={"email": STAFF_EMAIL, "password": "char-staff-password"}).json()["token"]
    return {"Authorization": "Bearer " + token}


def client():
    email = f"ana-{uuid.uuid4().hex[:8]}@example.com"
    body = {"name": "Ana Torres", "email": email, "password": "long-secure-password", "source": "aprende", "adult": True}
    r = c.post("/auth/signup", json=body)
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_get_characters_returns_only_enabled():
    # disable pinata via staff
    r = c.patch("/characters/pinata", json={"enabled": False}, headers=staff())
    assert r.status_code == 200
    r = c.get("/characters", headers=client())
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()]
    assert "pinata" not in ids
    assert "calavera" in ids
    assert "oso" in ids
    # re-enable
    c.patch("/characters/pinata", json={"enabled": True}, headers=staff())


def test_patch_staff_only():
    r = c.patch("/characters/oso", json={"enabled": False}, headers=client())
    assert r.status_code == 403


def test_calavera_cannot_be_disabled():
    r = c.patch("/characters/calavera", json={"enabled": False}, headers=staff())
    assert r.status_code == 409


def test_character_for_fallback():
    # disable... calavera can't be disabled; test fallback when unit unknown
    assert characters.character_for("nonexistent-unit") == "calavera"
    # assigned unit returns owner
    assert characters.character_for("games") == "pinata"


def test_disabled_falls_back_to_calavera_in_character_for():
    # temporarily disable pinata
    characters.update("pinata", {"enabled": False})
    assert characters.character_for("games") == "calavera"
    characters.update("pinata", {"enabled": True})
