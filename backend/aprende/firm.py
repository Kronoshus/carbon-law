"""Firm controls enforced server-side (T7-05)."""
import datetime
import json

import app as backend_app
import db
from aprende import clock

SWITCHES = ("voice_recording", "ai_chat", "extension")
DEFAULTS = {
    "switches": {"voice_recording": True, "ai_chat": True, "extension": True},
    "retention": {"unpaid_personal_data_days": 365},
    "lessons_per_day": 1,
}


class FirmSettingsError(ValueError):
    pass


def _now_iso():
    return clock.now_iso()


def _load(key, default):
    rows = db.query("SELECT value_json FROM settings WHERE key = ?", (key,))
    if not rows:
        return default
    try:
        return json.loads(rows[0][0])
    except Exception:
        return default


def _save_setting(key, value, actor=None):
    existing = db.query("SELECT key FROM settings WHERE key = ?", (key,))
    now = _now_iso()
    if existing:
        db.execute("UPDATE settings SET value_json = ?, updated_at = ?, updated_by = ? WHERE key = ?",
                   (json.dumps(value), now, actor, key))
    else:
        db.execute("INSERT INTO settings (key, value_json, updated_at, updated_by) VALUES (?, ?, ?, ?)",
                   (key, json.dumps(value), now, actor))


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
        return list(json.loads(rows[0][0]) or [])
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
        raise FirmSettingsError("changes must be object")
    allowed = {"switches", "retention", "lessons_per_day"}
    for k in changes:
        if k not in allowed:
            raise FirmSettingsError("unknown key %s" % k)

    # validate everything first
    new_switches = None
    if "switches" in changes:
        val = changes["switches"]
        if not isinstance(val, dict):
            raise FirmSettingsError("switches must be object")
        cur = dict(get()["switches"])
        for name, v in val.items():
            if name not in SWITCHES:
                raise FirmSettingsError("unknown switch %s" % name)
            if type(v) is not bool:
                raise FirmSettingsError("switch value must be bool")
            cur[name] = v
        new_switches = cur

    new_retention = None
    if "retention" in changes:
        val = changes["retention"]
        if not isinstance(val, dict):
            raise FirmSettingsError("retention must be object")
        cur = dict(get()["retention"])
        for k, v in val.items():
            if k not in ("unpaid_personal_data_days",):
                raise FirmSettingsError("unknown retention key %s" % k)
            if type(v) is not int or isinstance(v, bool):
                raise FirmSettingsError("retention value must be int")
            if v < 30:
                raise FirmSettingsError("retention days must be >= 30")
            cur[k] = v
        new_retention = cur

    new_lpd = None
    if "lessons_per_day" in changes:
        v = changes["lessons_per_day"]
        if type(v) is not int or isinstance(v, bool):
            raise FirmSettingsError("lessons_per_day must be int")
        if v < 1 or v > 4:
            raise FirmSettingsError("lessons_per_day must be 1-4")
        new_lpd = v

    # write all in one transaction
    with db.transaction():
        if new_switches is not None:
            _save_setting("switches", new_switches, actor)
        if new_retention is not None:
            _save_setting("retention", new_retention, actor)
        if new_lpd is not None:
            _save_setting("lessons_per_day", new_lpd, actor)

    if new_switches is not None:
        backend_app.log_audit(actor, "firm_settings", "settings", "switches", json.dumps(new_switches))
    if new_retention is not None:
        backend_app.log_audit(actor, "firm_settings", "settings", "retention", json.dumps(new_retention))
    if new_lpd is not None:
        backend_app.log_audit(actor, "firm_settings", "settings", "lessons_per_day", json.dumps(new_lpd))
    return get()
