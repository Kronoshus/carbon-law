"""Retention sweep for unpaid journeys' personal data (T7-05)."""
import datetime
import json

import db
from aprende import jobs
from aprende import firm

try:
    from app import log_audit
except Exception:
    def log_audit(*a, **k):
        pass


def _threshold_days():
    try:
        return int(firm.get()["retention"]["unpaid_personal_data_days"])
    except Exception:
        return 365


def _is_paid(jid):
    rows = db.query("SELECT 1 FROM journey_events WHERE journey_id = ? AND type = 'paid' LIMIT 1", (jid,))
    return bool(rows)


def _last_activity(jid):
    rows = db.query("SELECT MAX(created_at) FROM journey_events WHERE journey_id = ?", (jid,))
    if rows and rows[0] and rows[0][0]:
        return rows[0][0]
    rows = db.query("SELECT started_at FROM journeys WHERE id = ?", (jid,))
    return rows[0][0] if rows else None


def _to_naive(dt, value):
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        v = value
    else:
        v = datetime.datetime.fromisoformat(str(value))
    if v.tzinfo is not None:
        v = v.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return v


def sweep(now=None):
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)
    now = _to_naive(now, now)
    days = _threshold_days()
    cutoff = now - datetime.timedelta(days=days)
    jids = [r[0] for r in db.query("SELECT id FROM journeys")]
    swept = 0
    for jid in jids:
        if _is_paid(jid):
            continue
        la = _last_activity(jid)
        dt = _to_naive(None, la) if False else None
        try:
            dt = datetime.datetime.fromisoformat(str(la)) if la is not None else None
            if dt is not None and dt.tzinfo is not None:
                dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        except (ValueError, TypeError):
            dt = None
        if dt is None or dt > cutoff:
            continue
        existing = db.query("SELECT COUNT(*) FROM datos_answers WHERE journey_id = ?", (jid,))[0][0]
        existing += db.query("SELECT COUNT(*) FROM datos_audit WHERE journey_id = ?", (jid,))[0][0]
        existing += db.query("SELECT COUNT(*) FROM attorney_questions WHERE journey_id = ?", (jid,))[0][0]
        if existing == 0:
            continue
        with db.transaction() as conn:
            conn.execute("DELETE FROM datos_answers WHERE journey_id = ?", (jid,))
            conn.execute("DELETE FROM datos_audit WHERE journey_id = ?", (jid,))
            conn.execute("DELETE FROM attorney_questions WHERE journey_id = ?", (jid,))
        try:
            log_audit("retention", "retention_sweep", "journey", jid, "")
        except Exception:
            pass
        swept += 1
    jobs.enqueue("retention_sweep", "retention_sweep", run_after=now + datetime.timedelta(days=1))
    return {"journeys": swept}


def schedule(at):
    jobs.enqueue("retention_sweep", "retention_sweep", run_after=at)


def _handler(job):
    sweep()


jobs.register("retention_sweep", _handler)
