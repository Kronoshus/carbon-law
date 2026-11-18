import os, sys, tempfile, datetime

os.environ["DATABASE_URL"] = ""
os.environ["CARBON_DB_PATH"] = tempfile.mktemp(suffix=".db")
os.environ["APRENDE_EXTENSION_ORIGIN"] = "chrome-extension://abc"

sys.path.insert(0, "backend")
import migrate
import importlib
import app as backend_app
importlib.reload(backend_app)
migrate.run()

from fastapi.testclient import TestClient
from app import users, hash_pw
backend_app = sys.modules["app"]

c = TestClient(backend_app.app)

_STAFF_ID = None


def _seed_staff():
    global _STAFF_ID
    import uuid
    _STAFF_ID = str(uuid.uuid4())
    users["staff@example.com"] = {
        "id": _STAFF_ID, "name": "Test Staff", "email": "staff@example.com",
        "role": "paralegal", "password_hash": hash_pw("staff-test-password"),
        "created_at": datetime.datetime.utcnow().isoformat(),
    }


_seed_staff()


def test_aprende_signup_requires_adult():
    r = c.post("/auth/signup", json={
        "name": "A", "email": "adult-missing@example.com",
        "password": "long-secure-password", "source": "aprende",
    })
    assert r.status_code == 400
    assert r.json()["detail"] == "adult confirmation required"


def test_aprende_signup_with_adult():
    r = c.post("/auth/signup", json={
        "name": "A", "email": "adult-ok@example.com",
        "password": "long-secure-password", "source": "aprende", "adult": True,
    })
    assert r.status_code == 200
    u = backend_app.users["adult-ok@example.com"]
    assert "adult_confirmed_at" in u


def test_portal_signup_unchanged():
    r = c.post("/auth/signup", json={
        "name": "P", "email": "portal@example.com", "password": "long-secure-password",
    })
    assert r.status_code == 200


def test_client_session_30_days():
    r = c.post("/auth/signup", json={
        "name": "C", "email": "client-sess@example.com",
        "password": "long-secure-password", "source": "aprende", "adult": True,
    })
    assert r.status_code == 200
    token = r.json()["token"]
    exp = backend_app.sessions[token]["expires"]
    delta = datetime.datetime.fromisoformat(exp) - datetime.datetime.utcnow()
    assert 29 <= delta.days <= 30


def test_staff_session_24h():
    r = c.post("/auth/login", json={"email": "staff@example.com", "password": "staff-test-password"})
    assert r.status_code == 200
    token = r.json()["token"]
    exp = backend_app.sessions[token]["expires"]
    delta = datetime.datetime.fromisoformat(exp) - datetime.datetime.utcnow()
    assert 23 <= delta.total_seconds() / 3600 <= 24


def test_client_session_slides():
    r = c.post("/auth/signup", json={
        "name": "C2", "email": "client-slide@example.com",
        "password": "long-secure-password", "source": "aprende", "adult": True,
    })
    token = r.json()["token"]
    # force < 29 days remaining to trigger slide
    backend_app.sessions[token]["expires"] = (datetime.datetime.utcnow() + datetime.timedelta(days=2)).isoformat()
    backend_app.save_data() if hasattr(backend_app, "save_data") else None
    rr = c.get("/auth/me", headers={"Authorization": "Bearer " + token})
    assert rr.status_code == 200
    new_exp = backend_app.sessions[token]["expires"]
    delta = datetime.datetime.fromisoformat(new_exp) - datetime.datetime.utcnow()
    assert delta.days >= 29


def test_staff_session_does_not_slide():
    r = c.post("/auth/login", json={"email": "staff@example.com", "password": "staff-test-password"})
    token = r.json()["token"]
    original = backend_app.sessions[token]["expires"]
    rr = c.get("/auth/me", headers={"Authorization": "Bearer " + token})
    assert rr.status_code == 200
    assert backend_app.sessions[token]["expires"] == original


def test_cors_preflight_allowed():
    r = c.options("/auth/signup", headers={
        "Origin": "chrome-extension://abc",
        "Access-Control-Request-Method": "POST",
    })
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "chrome-extension://abc"


def test_cors_preflight_refused():
    r = c.options("/auth/signup", headers={
        "Origin": "chrome-extension://other",
        "Access-Control-Request-Method": "POST",
    })
    assert r.headers.get("access-control-allow-origin") is None


def test_cors_put_delete_allowed():
    for method in ("PUT", "DELETE"):
        r = c.options("/auth/signup", headers={
            "Origin": "chrome-extension://abc",
            "Access-Control-Request-Method": method,
        })
        allow = r.headers.get("access-control-allow-methods") or ""
        assert method in allow
