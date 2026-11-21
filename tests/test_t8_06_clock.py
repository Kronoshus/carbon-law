"""T8-06: the one server clock. Off in production; in the Playwright backend tests may move it forward. (Opus)"""
import datetime
import os
import subprocess
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
import db
from aprende import clock, jobs, journey

migrate.run()
c = TestClient(backend.app)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAYS = datetime.timedelta(days=1)


def backend_with(tmp_path, code, **env):
    """Run `code` in a fresh backend process with the given environment."""
    full = {**os.environ, "CARBON_DB_PATH": str(tmp_path / "clock.db"), "DATABASE_URL": "", **env}
    full.pop("RENDER", None) if "RENDER" not in env else None
    return subprocess.run([sys.executable, "-c", "import app\n" + code], cwd=os.path.join(ROOT, "backend"), env=full,
                          capture_output=True, text=True, timeout=120)


def test_without_the_flag_the_clock_route_does_not_exist():
    assert not clock.ENABLED
    assert c.get("/e2e/clock").status_code == 404
    assert c.post("/e2e/clock", json={"now": "2030-01-01T00:00:00+00:00"}).status_code == 404
    with pytest.raises(RuntimeError):
        clock.set_now(clock.now() + DAYS)


@pytest.mark.parametrize("env", [{"RENDER": "true"}, {"STRIPE_MODE": "live"}])
def test_the_backend_refuses_to_start_with_the_flag_in_production(tmp_path, env):
    r = backend_with(tmp_path, "", APRENDE_E2E_CLOCK="1", **env)
    assert r.returncode != 0 and "APRENDE_E2E_CLOCK is for the test backend only" in r.stderr


def test_with_the_flag_the_route_moves_the_clock_forward_only(tmp_path):
    r = backend_with(tmp_path, "\n".join([
        "from fastapi.testclient import TestClient", "c = TestClient(app.app)",
        "print(c.get('/e2e/clock').status_code)",
        "print(c.post('/e2e/clock', json={'now': '2099-02-04T18:00:00+00:00'}).json()['now'][:16])",
        "print(c.post('/e2e/clock', json={'now': '2099-02-01T18:00:00+00:00'}).status_code)",
        "print(c.post('/e2e/clock', json={'now': '2099-02-05T18:00:00'}).status_code)"]), APRENDE_E2E_CLOCK="1")
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["200", "2099-02-04T18:00", "409", "422"]


@pytest.fixture
def moved(monkeypatch):
    monkeypatch.setattr(clock, "ENABLED", True)
    monkeypatch.setattr(clock, "_offset", clock._offset)                       # put the real time back afterwards
    return lambda delta: clock.set_now(clock.now() + delta)


def test_a_moved_clock_moves_the_day_the_lessons_and_the_jobs(moved):
    body = {"name": "Ana Torres", "email": f"ana-{uuid.uuid4().hex[:8]}@example.com", "password": "long-secure-password",
            "source": "aprende", "adult": True}
    h = {"Authorization": "Bearer " + c.post("/auth/signup", json=body).json()["token"]}
    assert c.get("/journey", headers=h).json()["day"] == 1
    key = f"clock-test:{uuid.uuid4().hex}"
    jobs.enqueue("clock_test", key, run_after=clock.now() + 2 * DAYS)
    while (job := jobs.claim("clock-test")) is not None:                       # drain what is due now
        jobs.done(job)
    assert db.query("SELECT status FROM jobs WHERE key = ?", (key,))[0][0] == "pending"
    moved(3 * DAYS)
    assert c.get("/journey", headers=h).json()["day"] == 4
    claimed = []
    while (job := jobs.claim("clock-test")) is not None:
        claimed.append(job["key"]); jobs.done(job)
    assert key in claimed
    with pytest.raises(ValueError):
        clock.set_now(clock.now() - DAYS)
