"""Motivation: petals (XP), candle (streak), seals, reminders, progress (T4-06)."""
import datetime
import json
import uuid

import db
from aprende import journey as journeys
from aprende import learn

LEVELS_KEY = "levels"
DEFAULT_LEVELS = {"Aprendiz": 0, "Conocedor": 300, "Planeador": 800, "Guardián": 1500}

PETAL_ITEM = 10
PETAL_LESSON = 50
PETAL_INTAKE = 100


def _levels():
    rows = db.query("SELECT value_json FROM settings WHERE key = ?", (LEVELS_KEY,))
    if not rows:
        return DEFAULT_LEVELS
    try:
        return json.loads(rows[0][0])
    except (ValueError, TypeError):
        return DEFAULT_LEVELS


def award_petal_tx(conn, journey_id, reason, ref, amount, created_at=None):
    """Insert a petal award inside an existing transaction. Returns amount if newly awarded else 0."""
    if created_at is None:
        created_at = learn.now().isoformat() if hasattr(learn, "now") else datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO petal_awards (id, journey_id, reason, ref, amount, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (journey_id, reason, ref) DO NOTHING",
        (str(uuid.uuid4()), journey_id, reason, ref, amount, created_at))
    return amount if (cur.rowcount or 0) > 0 else 0


def award_petal(journey_id, reason, ref, amount, created_at=None):
    with db.transaction() as conn:
        return award_petal_tx(conn, journey_id, reason, ref, amount, created_at)


def total_petals(journey_id):
    rows = db.query("SELECT COALESCE(SUM(amount),0) FROM petal_awards WHERE journey_id = ?", (journey_id,))
    return int(rows[0][0]) if rows else 0


def level_for(petals):
    levels = _levels()
    ordered = sorted(levels.items(), key=lambda kv: kv[1])
    name = ordered[0][0]
    next_at = None
    for i, (n, t) in enumerate(ordered):
        if petals >= t:
            name = n
        else:
            next_at = t
            break
    # if max level, next_at None
    if petals >= ordered[-1][1]:
        next_at = None
    return {"name_key": name, "next_at": next_at}


def streak(days, today):
    dayset = set(days)
    if not dayset:
        return {"count": 0, "rested_this_week": False}
    used_weeks = set()
    count = 0
    if today in dayset:
        cur = today
    else:
        cur = today - datetime.timedelta(days=1)
    lower_bound = min(dayset)
    while cur >= lower_bound:
        if cur in dayset:
            count += 1
        else:
            iso = cur.isocalendar()
            week_key = (iso.year, iso.week)
            if week_key in used_weeks:
                break
            used_weeks.add(week_key)
        cur = cur - datetime.timedelta(days=1)
    this_week = (today.isocalendar().year, today.isocalendar().week)
    rested_this_week = this_week in used_weeks
    return {"count": count, "rested_this_week": rested_this_week}


def _completed_lesson_ids(journey_id):
    return [r[0] for r in db.query("SELECT lesson_id FROM lesson_completions WHERE journey_id = ?", (journey_id,))]


def _units_completed(journey_id):
    units = set()
    for lid in _completed_lesson_ids(journey_id):
        rows = db.query("SELECT unit FROM content_lessons WHERE id = ?", (lid,))
        if rows:
            units.add(rows[0][0])
    return units


def seals_for(journey):
    facts = journey.get("facts") or {}
    units = _units_completed(journey["id"])
    out = []
    for code in ("will", "trust", "ahcd", "poa"):
        out.append({"id": code, "earned": code in units})
    out.append({"id": "datos", "earned": "intake_completed" in facts})
    out.append({"id": "firmado", "earned": "signed" in facts})
    out.append({"id": "plan_completo", "earned": "final_lesson_completed" in facts})
    return out


def get_reminder(journey_id):
    rows = db.query("SELECT enabled, local_time FROM reminders WHERE journey_id = ?", (journey_id,))
    if not rows:
        return {"enabled": False, "local_time": "09:00"}
    return {"enabled": bool(rows[0][0]), "local_time": rows[0][1] or "09:00"}


def set_reminder(journey_id, enabled, local_time):
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    db.execute(
        "INSERT INTO reminders (journey_id, enabled, local_time, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT (journey_id) DO UPDATE SET enabled=excluded.enabled, local_time=excluded.local_time, updated_at=excluded.updated_at",
        (journey_id, 1 if enabled else 0, local_time, now_iso))
    return get_reminder(journey_id)


def _parse_time(s):
    h, m = s.split(":")
    return int(h), int(m)


def reminder_due(now):
    """Return journey ids whose reminder is due as of `now` (a datetime)."""
    out = []
    for jid, tz in db.query("SELECT id, tz FROM journeys"):
        rem = None
        rrows = db.query("SELECT enabled, local_time, last_sent_on FROM reminders WHERE journey_id = ?", (jid,))
        if not rrows or not rrows[0][0]:
            continue
        enabled, local_time, last_sent_on = rrows[0][0], rrows[0][1], rrows[0][2]
        if not enabled:
            continue
        zone_name = tz or "America/Los_Angeles"
        try:
            from zoneinfo import ZoneInfo
            zone = ZoneInfo(zone_name)
        except Exception:
            zone = datetime.timezone.utc
        if now.tzinfo is None:
            now = now.replace(tzinfo=datetime.timezone.utc)
        local_now = now.astimezone(zone)
        today_str = local_now.date().isoformat()
        if last_sent_on == today_str:
            continue
        lh, lm = _parse_time(local_time or "09:00")
        due_time = datetime.time(lh, lm)
        if local_now.timetuple().tm_hour * 60 + local_now.timetuple().tm_min < lh * 60 + lm:
            continue
        # no lesson completed today
        completed_today = False
        for lid, cat in db.query("SELECT lesson_id, completed_at FROM lesson_completions WHERE journey_id = ?", (jid,)):
            try:
                cat_dt = datetime.datetime.fromisoformat(str(cat).replace("Z", "+00:00"))
                if cat_dt.tzinfo is None:
                    cat_dt = cat_dt.replace(tzinfo=datetime.timezone.utc)
                if cat_dt.astimezone(zone).date() == local_now.date():
                    completed_today = True
                    break
            except (ValueError, TypeError):
                pass
        if completed_today:
            continue
        out.append(jid)
    return out


def mark_reminded(journey_id, on_date=None):
    if on_date is None:
        # use today UTC date? caller should pass; default now date in UTC
        on_date = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    db.execute("UPDATE reminders SET last_sent_on = ? WHERE journey_id = ?", (on_date, journey_id))


# aliases
record_reminder_sent = mark_reminded
set_last_sent = mark_reminded


def progress(journey):
    jid = journey["id"]
    tz_name = journey.get("tz") or "America/Los_Angeles"
    try:
        from zoneinfo import ZoneInfo
        zone = ZoneInfo(tz_name)
    except Exception:
        zone = datetime.timezone.utc
    days = []
    for lid, cat in db.query("SELECT lesson_id, completed_at FROM lesson_completions WHERE journey_id = ?", (jid,)):
        try:
            cat_dt = datetime.datetime.fromisoformat(str(cat).replace("Z", "+00:00"))
            if cat_dt.tzinfo is None:
                cat_dt = cat_dt.replace(tzinfo=datetime.timezone.utc)
            days.append(cat_dt.astimezone(zone).date())
        except (ValueError, TypeError):
            pass
    today_local = learn.now().astimezone(zone).date() if hasattr(learn.now(), "astimezone") else datetime.datetime.now(zone).date()
    # learn.now() returns aware UTC datetime per learn module
    try:
        today_local = learn.now().astimezone(zone).date()
    except Exception:
        today_local = datetime.datetime.now(zone).date()
    petals = total_petals(jid)
    return {
        "petals": petals,
        "level": level_for(petals),
        "streak": streak(days, today_local),
        "seals": seals_for(journey),
        "reminders": get_reminder(jid),
    }
