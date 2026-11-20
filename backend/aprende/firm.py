"""Firm controls enforced server-side (T7-05)."""
import datetime
import json

import app as backend_app
import db
from fastapi import HTTPException

SWITCHES = ("voice_recording", "ai_chat", "extension")
DEFAULTS = {
    "switches": {"voice_recording": True, "ai_chat": True, "extension": True},
    "retention": {"unpaid_personal_data_days": 365},
    "lessons_per_day": 1,
}


def _load(key, default):
    rows = db.query("SELECT value_json FROM settings WHERE key = ?", (key,))
    if not rows:
        return default
    try:
        return json.loads(rows[0][0])
    except Exception:
        return default


def _save(key, value):
    existing = db.query("SELECT key FROM settings WHERE key = ?", (key,))
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()
    if existing:
        db.execute("UPDATE settings SET value_json = ?, updated_at = ? WHERE key = ?", (json.dumps(value), now, key))
    else:
        db.execute("INSERT INTO settings (key, value_json, updated_at) VALUES (?, ?, ?)", (key, json.dumps(value), now))


def _load_availability():
    rows = db.query("SELECT value_json FROM settings WHERE key = ?", ("availability",))
    if not rows:
        return None
    try:
        return json.loads(rows[0][0])
    except Exception:
        return None


def _load_holidays():
    rows = db.query("SELECT value_json FROM settings WHERE key = ?", ("holidays",))
    if not rows:
        return []
    try:
        return json.loads(rows[0][0]) or []
    except Exception:
        return []


def get():
    switches = _load("switches", DEFAULTS["switches"])
    retention = _load("retention", DEFAULTS["retention"])
    lpd = _load("lessons_per_day", DEFAULTS["lessons_per_day"])
    return {
        "availability": _load_availability(),
        "holidays": _load_holidays(),
        "retention": retention,
        "switches": switches,
        "lessons_per_day": int(lpd),
    }


def switch(name):
    s = get()["switches"]
    return bool(s.get(name, DEFAULTS["switches"].get(name, False)))


def update(changes, actor):
    if not isinstance(changes, dict):
        raise HTTPException(422, "changes must be object")
    allowed = {"switches", "retention", "lessons_per_day"}
    for k in changes:
        if k not in allowed:
            raise HTTPException(422, "unknown key %s" % k)
    new_switches = None
    if "switches" in changes:
        val = changes["switches"]
        if not isinstance(val, dict):
            raise HTTPException(422, "switches must be object")
        cur = dict(get()["switches"])
        for name, v in val.items():
            if name not in SWITCHES:
                raise HTTPException(422, "unknown switch %s" % name)
            if type(v) is not bool:
                raise HTTPException(422, "switch value must be bool")
            cur[name] = v
        new_switches = cur
    new_retention = None
    if "retention" in changes:
        val = changes["retention"]
        if not isinstance(val, dict):
            raise HTTPException(422, "retention must be object")
        cur = dict(get()["retention"])
        for k, v in val.items():
            if k not in ("unpaid_personal_data_days",):
                raise HTTPException(422, "unknown retention key %s" % k)
            if type(v) is not int or isinstance(v, bool):
                raise HTTPException(422, "retention value must be int")
            if v < 30:
                raise HTTPException(422, "retention days must be >= 30")
            cur[k] = v
        new_retention = cur
    new_lpd = None
    if "lessons_per_day" in changes:
        v = changes["lessons_per_day"]
        if type(v) is not int or isinstance(v, bool):
            raise HTTPException(422, "lessons_per_day must be int")
        if v < 1 or v > 4:
            raise HTTPException(422, "lessons_per_day must be 1-4")
        new_lpd = v

    if new_switches is not None:
        _save("switches", new_switches)
        backend_app.log_audit(actor, "firm_settings", "settings", "switches", json.dumps(new_switches))
    if new_retention is not None:
        _save("retention", new_retention)
        backend_app.log_audit(actor, "firm_settings", "settings", "retention", json.dumps(new_retention))
    if new_lpd is not None:
        _save("lessons_per_day", new_lpd)
        backend_app.log_audit(actor, "firm_settings", "settings", "lessons_per_day", json.dumps(new_lpd))
    return get()
