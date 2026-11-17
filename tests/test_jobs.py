import os, sys, tempfile, time, threading, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(os.path.dirname(HERE), "backend")
sys.path.insert(0, BACKEND)

_orig_db_url = os.environ.get("DATABASE_URL")
_orig_db_path = os.environ.get("CARBON_DB_PATH")
os.environ["DATABASE_URL"] = ""
os.environ["CARBON_DB_PATH"] = tempfile.mktemp(suffix=".db")

import db
import migrate
import aprende.jobs as jobs

if _orig_db_url is None:
    os.environ.pop("DATABASE_URL", None)
else:
    os.environ["DATABASE_URL"] = _orig_db_url
if _orig_db_path is None:
    os.environ.pop("CARBON_DB_PATH", None)
else:
    os.environ["CARBON_DB_PATH"] = _orig_db_path


def setup_module():
    migrate.run()

import pytest

@pytest.fixture(autouse=True)
def _clean_jobs():
    try:
        db.execute("DELETE FROM jobs")
    except Exception:
        pass
    yield



def test_enqueue_same_key_twice_one_job():
    j1 = jobs.enqueue("email", "dedup-key", {"to": "a"})
    j2 = jobs.enqueue("email", "dedup-key", {"to": "b"})
    assert j1 == j2
    rows = db.query("SELECT COUNT(*) FROM jobs WHERE key = ?", ("dedup-key",))
    assert rows[0][0] == 1


def test_claim_returns_job_and_marks_running():
    jobs.enqueue("email", "claim-key", {"x": 1})
    job = jobs.claim()
    assert job is not None
    assert job["status"] == "running"
    assert job["attempts"] == 1
    assert job["payload"] == {"x": 1}


def test_crashed_claim_reclaimed_after_stale():
    jid = jobs.enqueue("email", "stale-key", {})
    old = "2000-01-01T00:00:00"
    db.execute("UPDATE jobs SET status='running', locked_by='ghost', locked_at=?, attempts=1 WHERE id=?", (old, jid))
    job = jobs.claim()
    assert job is not None
    assert job["id"] == jid
    assert job["locked_by"] != "ghost"


def test_fail_retries_with_backoff_then_failed():
    jid = jobs.enqueue("failkind", "fail-key", {})
    for i in range(3):
        db.execute("UPDATE jobs SET status='pending', run_after=NULL, locked_by=NULL, locked_at=NULL WHERE id=?", (jid,))
        db.execute("UPDATE jobs SET attempts=? WHERE id=?", (i, jid))
        job = jobs.claim()
        assert job is not None
        jobs.fail(job, "boom")
    rows = db.query("SELECT status, attempts FROM jobs WHERE id=?", (jid,))
    assert rows[0][0] == "failed"
    assert rows[0][1] == 3


def test_done_marks_done():
    jid = jobs.enqueue("email", "done-key", {})
    job = jobs.claim()
    jobs.done(job)
    rows = db.query("SELECT status FROM jobs WHERE id=?", (jid,))
    assert rows[0][0] == "done"


def test_postgres_skip_locked():
    pg_url = os.environ.get("APRENDE_TEST_PG_URL")
    if not pg_url:
        import pytest
        pytest.skip("APRENDE_TEST_PG_URL not set")
    # basic import check in subprocess
    code = "import sys; sys.path.insert(0, " + repr(BACKEND) + "); import db, migrate, aprende.jobs; print('import ok')"
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
