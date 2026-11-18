"""Motivation (T4-06): petals (XP), the candle (daily streak), levels, seals, reminders. The UI comes with the map (T4-07).
Petals are award rows (idempotent per reason and reference); the streak is computed from lesson completions."""
import datetime
import json
import re
import uuid
from zoneinfo import ZoneInfo

import db
from aprende import learn

PETAL_ITEM, PETAL_LESSON, PETAL_INTAKE = 10, 50, 100


def award_petal_tx(conn, journey_id, reason, ref, amount, created_at):
    """Award inside the caller's transaction; returns the amount if new, 0 if already awarded."""
    cur = conn.execute("INSERT INTO petal_awards (id, journey_id, reason, ref, amount, created_at) VALUES (?, ?, ?, ?, ?, ?) "
                       "ON CONFLICT (journey_id, reason, ref) DO NOTHING",
                       (str(uuid.uuid4()), journey_id, reason, ref, amount, created_at))
    return amount if cur.rowcount > 0 else 0


def total_petals(journey_id):
    return int(db.query("SELECT COALESCE(SUM(amount), 0) FROM petal_awards WHERE journey_id = ?", (journey_id,))[0][0])


def level_for(petals):
    """-> {"name_key", "next_at"}: the highest level reached and the petals needed for the next one (None at the top)."""
    levels = sorted(json.loads(db.query("SELECT value_json FROM settings WHERE key = 'levels'")[0][0]).items(), key=lambda kv: kv[1])
    reached = [name for name, at in levels if petals >= at]
    above = [at for _, at in levels if petals < at]
    return {"name_key": f"level.{reached[-1]}", "next_at": above[0] if above else None}


def streak(days, today):
    """Consecutive days with a completed lesson, ending today or yesterday. One missed day per ISO week is forgiven
    ("su vela descansó"); a second missed day in the same week ends the streak. Today not done yet is not a miss."""
    done = set(days)
    cur = today if today in done else today - datetime.timedelta(days=1)
    counted, rests = [], []
    while True:
        if cur in done:
            counted.append(cur)
        else:
            week = cur.isocalendar()[:2]
            if not any(d < cur for d in done) or any(r.isocalendar()[:2] == week for r in rests):
                break
            rests.append(cur)
        cur -= datetime.timedelta(days=1)
    used = [r for r in rests if any(d < r for d in counted)]       # a rest only counts if the streak went on past it
    return {"count": len(counted), "rested_this_week": any(r.isocalendar()[:2] == today.isocalendar()[:2] for r in used)}


def _local_days(journey_id, zone):
    return [datetime.datetime.fromisoformat(at).astimezone(zone).date()
            for (at,) in db.query("SELECT completed_at FROM lesson_completions WHERE journey_id = ?", (journey_id,))]


def seals_for(journey):
    units = {u for (u,) in db.query("SELECT l.unit FROM lesson_completions c JOIN content_lessons l ON l.id = c.lesson_id "
                                    "WHERE c.journey_id = ?", (journey["id"],))}
    facts = journey["facts"]
    return ([{"id": u, "earned": u in units} for u in ("will", "trust", "ahcd", "poa")] +
            [{"id": "datos", "earned": "intake_completed" in facts}, {"id": "firmado", "earned": "signed" in facts},
             {"id": "plan_completo", "earned": "final_lesson_completed" in facts}])


def get_reminder(journey_id):
    rows = db.query("SELECT enabled, local_time FROM reminders WHERE journey_id = ?", (journey_id,))
    return {"enabled": bool(rows[0][0]), "local_time": rows[0][1]} if rows else {"enabled": False, "local_time": None}


def set_reminder(journey_id, enabled, local_time):
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", local_time or ""):
        raise ValueError("local_time must be HH:MM")
    db.execute("INSERT INTO reminders (journey_id, enabled, local_time, updated_at) VALUES (?, ?, ?, ?) "
               "ON CONFLICT (journey_id) DO UPDATE SET enabled = excluded.enabled, local_time = excluded.local_time, "
               "updated_at = excluded.updated_at", (journey_id, 1 if enabled else 0, local_time, learn.now().isoformat()))
    return get_reminder(journey_id)


def reminders_due(now):
    """Journeys whose reminder time has passed today (their time zone), not yet reminded today, and with no lesson
    completed today: at most one reminder a day."""
    due = []
    for jid, tz, local_time, last_sent_on in db.query(
            "SELECT j.id, j.tz, r.local_time, r.last_sent_on FROM reminders r JOIN journeys j ON j.id = r.journey_id "
            "WHERE r.enabled = 1"):
        zone = ZoneInfo(tz or "America/Los_Angeles")
        local = now.astimezone(zone)
        if last_sent_on == local.date().isoformat() or local.strftime("%H:%M") < local_time:
            continue
        if local.date() in _local_days(jid, zone):
            continue
        due.append(jid)
    return due


def mark_reminded(journey_id, now):
    tz = db.query("SELECT tz FROM journeys WHERE id = ?", (journey_id,))[0][0]
    db.execute("UPDATE reminders SET last_sent_on = ? WHERE journey_id = ?",
               (now.astimezone(ZoneInfo(tz or "America/Los_Angeles")).date().isoformat(), journey_id))


def progress(journey):
    zone = ZoneInfo(journey.get("tz") or "America/Los_Angeles")
    petals = total_petals(journey["id"])
    return {"petals": petals, "level": level_for(petals),
            "streak": streak(_local_days(journey["id"], zone), learn.now().astimezone(zone).date()),
            "seals": seals_for(journey), "reminders": get_reminder(journey["id"])}
