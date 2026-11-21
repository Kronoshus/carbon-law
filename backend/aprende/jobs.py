"""Jobs queue. All stored times are naive UTC ISO strings.
"""
import os, sys, uuid, json
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

import db
from aprende import clock

BACKOFF_SECONDS = (60, 300, 1800)
MAX_ATTEMPTS = 3
LOCK_STALE_MINUTES = 10

HANDLERS = {}


def register(kind, handler):
    HANDLERS[kind] = handler


def _now():
    return clock.now().replace(tzinfo=None)


def _iso(dt):
    return dt.isoformat()


def _normalize_run_after(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value.isoformat()
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
    db.execute(
        "INSERT INTO jobs (id, kind, key, payload_json, status, attempts, run_after) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT (key) DO NOTHING",
        (job_id, kind, key, payload_json, "pending", 0, run_after_iso),
    )
    rows = db.query("SELECT id FROM jobs WHERE key = ?", (key,))
    return rows[0][0] if rows else job_id


def _is_pg_conn(conn):
    return "psycopg" in type(conn).__module__


def _translate_sql(sql, pg):
    return sql.replace("?", "%s") if pg else sql


def _claim_core(conn, pg, worker_id, now_iso, cutoff_iso):
    if pg:
        rows = conn.execute(
            _translate_sql(
                "SELECT id FROM jobs "
                "WHERE (status = ? OR (status = ? AND locked_at < ?)) "
                "  AND (run_after IS NULL OR run_after <= ?) "
                "ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED", pg),
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
        _translate_sql(
            "UPDATE jobs SET status = ?, locked_by = ?, locked_at = ?, attempts = attempts + 1 "
            "WHERE id = ? AND (status = ? OR (status = ? AND locked_at < ?))", pg),
        ("running", worker_id, now_iso, job_id, "pending", "running", cutoff_iso),
    )
    if getattr(cur, "rowcount", 1) == 0:
        return None
    row = conn.execute(
        _translate_sql(
            "SELECT id, kind, key, payload_json, status, attempts, run_after, locked_by, locked_at, last_error "
            "FROM jobs WHERE id = ?", pg),
        (job_id,),
    ).fetchone()
    return _row_to_job(row)


def claim(worker_id=None, conn=None):
    if worker_id is None:
        worker_id = "worker-{}-{}".format(os.getpid(), uuid.uuid4().hex[:8])
    now = _now()
    now_iso = _iso(now)
    cutoff_iso = _iso(now - timedelta(minutes=LOCK_STALE_MINUTES))
    if conn is None:
        with db.transaction() as c:
            return _claim_core(c, db.POSTGRES, worker_id, now_iso, cutoff_iso)
    pg = _is_pg_conn(conn)
    try:
        if pg:
            conn.autocommit = False
        else:
            conn.execute("BEGIN")
        result = _claim_core(conn, pg, worker_id, now_iso, cutoff_iso)
        conn.commit()
        return result
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        if pg:
            try:
                conn.autocommit = True
            except Exception:
                pass


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
