"""Retention sweep for unpaid journeys' personal data (T7-05)."""
import datetime
import json
from zoneinfo import ZoneInfo

import app as backend_app
import db
from aprende import jobs
from aprende import firm

LA = ZoneInfo("America/Los_Angeles")


def _threshold_days():
    try:
        return int(firm.get()["retention"]["unpaid_personal_data_days"])
    except Exception:
        return 365


def _is_paid(jid):
    rows = db.query("SELECT 1 FROM journey_events WHERE journey_id = ? AND type = 'paid' LIMIT 1", (jid,))
    return bool(rows)


def _last_activity(jid):
    row = db.query(
        "SELECT MAX(v) FROM ("
        "  SELECT started_at AS v FROM journeys WHERE id = ? "
        "  UNION ALL "
        "  SELECT created_at AS v FROM journey_events WHERE journey_id = ? "
        "  UNION ALL "
        "  SELECT updated_at AS v FROM datos_answers WHERE journey_id = ? "
        "  UNION ALL "
        "  SELECT created_at AS v FROM item_attempts WHERE journey_id = ? "
        ")", (jid, jid, jid, jid))
    if row and row[0] and row[0][0]:
        return row[0][0]
    rows = db.query("SELECT started_at FROM journeys WHERE id = ?", (jid,))
    return rows[0][0] if rows else None


def _to_naive(value):
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        v = value
    else:
        v = datetime.datetime.fromisoformat(str(value))
    if v.tzinfo is not None:
        v = v.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return v


def sweep(now):
    if not isinstance(now, datetime.datetime):
        now = datetime.datetime.fromisoformat(str(now))
    now = _to_naive(now)
    days = _threshold_days()
    cutoff = now - datetime.timedelta(days=days)
    jids = [r[0] for r in db.query("SELECT id FROM journeys")]
    swept = 0
    for jid in jids:
        if _is_paid(jid):
            continue
        la = _last_activity(jid)
        dt = _to_naive(la)
        if dt is None or dt > cutoff:
            continue
        counts = {
            "datos_answers": db.query("SELECT COUNT(*) FROM datos_answers WHERE journey_id = ?", (jid,))[0][0],
            "datos_audit": db.query("SELECT COUNT(*) FROM datos_audit WHERE journey_id = ?", (jid,))[0][0],
            "attorney_questions": db.query("SELECT COUNT(*) FROM attorney_questions WHERE journey_id = ?", (jid,))[0][0],
        }
        if sum(counts.values()) == 0:
            continue
        with db.transaction():
            db.execute("DELETE FROM datos_answers WHERE journey_id = ?", (jid,))
            db.execute("DELETE FROM datos_audit WHERE journey_id = ?", (jid,))
            db.execute("DELETE FROM attorney_questions WHERE journey_id = ?", (jid,))
        backend_app.log_audit("retention", "retention_sweep", "journey", jid, json.dumps(counts))
        swept += 1
    return {"journeys": swept}


def schedule(at):
    jobs.enqueue("retention_sweep", f"retention_sweep:{at:%Y-%m-%d}", run_after=at)


def _job(job):
    sweep(datetime.datetime.now(datetime.timezone.utc))
    tomorrow = (datetime.datetime.now(LA) + datetime.timedelta(days=1)).replace(hour=3, minute=0, second=0, microsecond=0)
    # ensure future
    now_la = datetime.datetime.now(LA)
    if tomorrow <= now_la:
        tomorrow = tomorrow + datetime.timedelta(days=1)
    schedule(tomorrow.astimezone(datetime.timezone.utc))


jobs.register("retention_sweep", _job)
