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

sys.path.insert(0, BACKEND)
import worker

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


def test_fail_retry_flow_with_patched_clock(monkeypatch):
    base = jobs._now()
    monkeypatch.setattr(jobs, "_now", lambda: base)
    jid = jobs.enqueue("email", "retry-key", {})
    job = jobs.claim()
    assert job is not None
    jobs.fail(job, "boom1")
    # backoff 60s not passed
    monkeypatch.setattr(jobs, "_now", lambda: base)
    assert jobs.claim() is None
    # advance past backoff
    monkeypatch.setattr(jobs, "_now", lambda: base.__class__.fromtimestamp(base.timestamp() + 61))
    job2 = jobs.claim()
    assert job2 is not None and job2["id"] == jid
    jobs.fail(job2, "boom2")
    monkeypatch.setattr(jobs, "_now", lambda: base.__class__.fromtimestamp(base.timestamp() + 61 + 301))
    job3 = jobs.claim()
    assert job3 is not None
    jobs.fail(job3, "boom3")
    rows = db.query("SELECT status, last_error FROM jobs WHERE id=?", (jid,))
    assert rows[0][0] == "failed"
    assert rows[0][1] == "boom3"


def test_future_run_after_not_claimed():
    future = jobs._now()  # placeholder
    from datetime import timedelta
    future_dt = jobs._now() + timedelta(hours=1)
    jobs.enqueue("email", "future-key", {}, run_after=future_dt)
    assert jobs.claim() is None


def test_no_handler_marks_failed():
    jobs.enqueue("unknown_kind", "nohandler-key", {})
    job = jobs.claim()
    worker.run_one("w")  # job already claimed; run_one claims none
    # instead use worker flow: reset to pending then run_forever? simple: fail via worker if no handler by claiming fresh
    # Re-enqueue and let run_one handle claim+fail
    db.execute("DELETE FROM jobs")
    jobs.enqueue("unknown_kind", "nohandler-key2", {})
    # call run_one which claims and fails due to no handler
    worker.run_one("w")
    rows = db.query("SELECT status, last_error FROM jobs WHERE key=?", ("nohandler-key2",))
    assert rows[0][0] == "failed"
    assert "no handler" in (rows[0][1] or "")


def test_run_forever_stops():
    import threading
    ev = threading.Event()
    t = threading.Thread(target=worker.run_forever, args=(ev,), daemon=True)
    t.start()
    time.sleep(0.3)
    ev.set()
    t.join(timeout=2)
    assert not t.is_alive()


def test_postgres_skip_locked_real():
    pg_url = os.environ.get("APRENDE_TEST_PG_URL")
    if not pg_url:
        pytest.skip("APRENDE_TEST_PG_URL not set")
    import psycopg
    code = (
        "import os, sys, time, threading\n"
        "os.environ['DATABASE_URL'] = " + repr(pg_url) + "\n"
        "backend = " + repr(BACKEND) + "\n"
        "sys.path.insert(0, backend)\n"
        "import db, migrate, aprende.jobs as jobs\n"
        "import psycopg\n"
        "c = psycopg.connect(" + repr(pg_url) + ", autocommit=True)\n"
        "c.execute('DROP SCHEMA public CASCADE')\n"
        "c.execute('CREATE SCHEMA public')\n"
        "c.close()\n"
        "migrate.run()\n"
        "for i in range(20): jobs.enqueue('email', 'k'+str(i), {'i': i})\n"
        "claimed = []\n"
        "lock = threading.Lock()\n"
        "def claimer():\n"
        "    conn = psycopg.connect(" + repr(pg_url) + ")\n"
        "    while True:\n"
        "        j = jobs.claim(conn=conn)\n"
        "        if j is None: \n"
        "            break\n"
        "        with lock: claimed.append(j['id'])\n"
        "    conn.close()\n"
        "ts = [threading.Thread(target=claimer) for _ in range(4)]\n"
        "for t in ts: t.start()\n"
        "for t in ts: t.join()\n"
        "assert len(claimed) == 20, len(claimed)\n"
        "assert len(set(claimed)) == 20\n"
        "print('pg skip locked real ok')\n"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=180)
    print(r.stdout)
    print(r.stderr)
    assert r.returncode == 0, r.stderr
