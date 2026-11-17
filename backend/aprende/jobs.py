import os, sys, uuid, json
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

import db

BACKOFF_SECONDS = (2, 4, 8)
MAX_ATTEMPTS = 3
LOCK_STALE_MINUTES = 10

HANDLERS = {}


def register(kind, handler):
    HANDLERS[kind] = handler


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _iso(dt):
    return dt.isoformat()


def _normalize_run_after(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return (value.replace(tzinfo=None) if value.tzinfo else value).isoformat()
    return str(value)


def _row_to_job(row):
    if row is None:
        return None
    cols = ["id", "kind", "key", "payload_json", "status", "attempts",
            "run_after", "locked_by", "locked_at", "last_error"]
    job = dict(zip(cols, row))
    raw = job.get("payload_json")
    try:
        job["payload"] = json.loads(raw) if raw is not None else None
    except (ValueError, TypeError):
        job["payload"] = None
    return job


def enqueue(kind, key, payload=None, run_after=None):
    job_id = str(uuid.uuid4())
    payload_json = None if payload is None else json.dumps(payload)
    run_after_iso = _normalize_run_after(run_after)
    try:
        db.execute(
            "INSERT INTO jobs (id, kind, key, payload_json, status, attempts, run_after) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (job_id, kind, key, payload_json, "pending", 0, run_after_iso),
        )
        return job_id
    except Exception:
        rows = db.query("SELECT id FROM jobs WHERE key = ?", (key,))
        if rows:
            return rows[0][0]
        raise


def claim(worker_id=None):
    if worker_id is None:
        worker_id = "worker-{}-{}".format(os.getpid(), uuid.uuid4().hex[:8])
    now = _now()
    now_iso = _iso(now)
    cutoff_iso = _iso(now - timedelta(minutes=LOCK_STALE_MINUTES))
    with db.transaction() as conn:
        if db.POSTGRES:
            rows = conn.execute(
                "SELECT id FROM jobs "
                "WHERE (status = ? OR (status = ? AND locked_at < ?)) "
                "  AND (run_after IS NULL OR run_after <= ?) "
                "ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED",
                ("pending", "running", cutoff_iso, now_iso),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id FROM jobs "
                "WHERE (status = ? OR (status = ? AND locked_at < ?)) "
                "  AND (run_after IS NULL OR run_after <= ?) "
                "ORDER BY id LIMIT 1",
                ("pending", "running", cutoff_iso, now_iso),
            ).fetchall()
        if not rows:
            return None
        job_id = rows[0][0]
        cur = conn.execute(
            "UPDATE jobs SET status = ?, locked_by = ?, locked_at = ?, attempts = attempts + 1 "
            "WHERE id = ? AND (status = ? OR (status = ? AND locked_at < ?))",
            ("running", worker_id, now_iso, job_id, "pending", "running", cutoff_iso),
        )
        if getattr(cur, "rowcount", 1) == 0:
            return None
        row = conn.execute(
            "SELECT id, kind, key, payload_json, status, attempts, run_after, locked_by, locked_at, last_error "
            "FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
    return _row_to_job(row)


def _job_id(job):
    if isinstance(job, dict):
        return job["id"]
    return job


def done(job):
    job_id = _job_id(job)
    db.execute(
        "UPDATE jobs SET status = ?, locked_by = NULL, locked_at = NULL, last_error = NULL "
        "WHERE id = ?", ("done", job_id)
    )


def fail(job, error=None):
    job_id = _job_id(job)
    rows = db.query("SELECT attempts FROM jobs WHERE id = ?", (job_id,))
    attempts = rows[0][0] if rows else 0
    if attempts >= MAX_ATTEMPTS:
        db.execute(
            "UPDATE jobs SET status = ?, locked_by = NULL, locked_at = NULL, last_error = ? "
            "WHERE id = ?", ("failed", (str(error) if error is not None else None), job_id)
        )
    else:
        idx = attempts - 1 if attempts > 0 else 0
        backoff = BACKOFF_SECONDS[min(idx, len(BACKOFF_SECONDS) - 1)]
        run_after = _iso(_now() + timedelta(seconds=backoff))
        db.execute(
            "UPDATE jobs SET status = ?, locked_by = NULL, locked_at = NULL, "
            "run_after = ?, last_error = ? WHERE id = ?",
            ("pending", run_after, (str(error) if error is not None else None), job_id),
        )
