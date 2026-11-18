
import sys, os, tempfile, datetime, subprocess
import pytest

sys.path.insert(0, "backend")

@pytest.fixture(scope="module")
def client():
    import app as backend_app
    from app import users, hash_pw
    globals()["backend_app"] = backend_app
    globals()["users"] = users
    globals()["hash_pw"] = hash_pw
    import uuid
    if "staff@example.com" not in users:
        users["staff@example.com"] = {
            "id": str(uuid.uuid4()), "name": "Test Staff", "email": "staff@example.com",
            "role": "paralegal", "password_hash": hash_pw("staff-test-password"),
            "created_at": datetime.datetime.utcnow().isoformat(),
        }
    from fastapi.testclient import TestClient
    return TestClient(backend_app.app)


def test_aprende_signup_requires_adult(client):
    r = client.post("/auth/signup", json={
        "name": "A", "email": "adult-missing@example.com",
        "password": "long-secure-password", "source": "aprende",
    })
    assert r.status_code == 400
    assert r.json()["detail"] == "adult confirmation required"


def test_aprende_signup_with_adult(client):
    r = client.post("/auth/signup", json={
        "name": "A", "email": "adult-ok@example.com",
        "password": "long-secure-password", "source": "aprende", "adult": True,
    })
    assert r.status_code == 200
    u = users["adult-ok@example.com"]
    assert "adult_confirmed_at" in u


def test_portal_signup_unchanged(client):
    r = client.post("/auth/signup", json={
        "name": "P", "email": "portal@example.com", "password": "long-secure-password",
    })
    assert r.status_code == 200


def test_client_session_30_days(client):
    r = client.post("/auth/signup", json={
        "name": "C", "email": "client-sess@example.com",
        "password": "long-secure-password", "source": "aprende", "adult": True,
    })
    assert r.status_code == 200
    token = r.json()["token"]
    exp = backend_app.sessions[token]["expires"]
    delta = datetime.datetime.fromisoformat(exp) - datetime.datetime.utcnow()
    assert 29 <= delta.days <= 30


def test_staff_session_24h(client):
    r = client.post("/auth/login", json={"email": "staff@example.com", "password": "staff-test-password"})
    assert r.status_code == 200
    token = r.json()["token"]
    exp = backend_app.sessions[token]["expires"]
    delta = datetime.datetime.fromisoformat(exp) - datetime.datetime.utcnow()
    assert 23 <= delta.total_seconds() / 3600 <= 24


def test_client_session_slides(client):
    r = client.post("/auth/signup", json={
        "name": "C2", "email": "client-slide@example.com",
        "password": "long-secure-password", "source": "aprende", "adult": True,
    })
    token = r.json()["token"]
    backend_app.sessions[token]["expires"] = (datetime.datetime.utcnow() + datetime.timedelta(days=2)).isoformat()
    rr = client.get("/auth/me", headers={"Authorization": "Bearer " + token})
    assert rr.status_code == 200
    new_exp = backend_app.sessions[token]["expires"]
    delta = datetime.datetime.fromisoformat(new_exp) - datetime.datetime.utcnow()
    assert delta.days >= 29


def test_staff_session_does_not_slide(client):
    r = client.post("/auth/login", json={"email": "staff@example.com", "password": "staff-test-password"})
    token = r.json()["token"]
    original = backend_app.sessions[token]["expires"]
    rr = client.get("/auth/me", headers={"Authorization": "Bearer " + token})
    assert rr.status_code == 200
    assert backend_app.sessions[token]["expires"] == original


def test_cors_in_subprocess():
    db = tempfile.mktemp(suffix=".db")
    code = (
        "import os, sys\n"
        "os.environ['DATABASE_URL'] = ''\n"
        "os.environ['CARBON_DB_PATH'] = " + repr(db) + "\n"
        "os.environ['APRENDE_EXTENSION_ORIGIN'] = 'chrome-extension://abc'\n"
        "sys.path.insert(0, 'backend')\n"
        "import migrate; migrate.run()\n"
        "from fastapi.testclient import TestClient\n"
        "import app as backend_app\n"
        "c = TestClient(backend_app.app)\n"
        "r = c.options('/auth/signup', headers={'Origin': 'chrome-extension://abc', 'Access-Control-Request-Method': 'POST'})\n"
        "assert r.status_code == 200, r.status_code\n"
        "assert r.headers.get('access-control-allow-origin') == 'chrome-extension://abc'\n"
        "r = c.options('/auth/signup', headers={'Origin': 'chrome-extension://other', 'Access-Control-Request-Method': 'POST'})\n"
        "assert r.headers.get('access-control-allow-origin') is None\n"
        "for method in ('PUT', 'DELETE'):\n"
        "    r = c.options('/auth/signup', headers={'Origin': 'chrome-extension://abc', 'Access-Control-Request-Method': method})\n"
        "    allow = r.headers.get('access-control-allow-methods') or ''\n"
        "    assert method in allow, (method, allow)\n"
        "print('cors ok')\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         env={**os.environ, "APRENDE_EXTENSION_ORIGIN": "chrome-extension://abc",
                              "CARBON_DB_PATH": db, "DATABASE_URL": ""})
    assert out.returncode == 0, out.stderr
