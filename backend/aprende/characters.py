"""Character registry for Aprende y Planea (T3-06, T7-03)."""
import json

import db

UNITS = ("will", "trust", "ahcd", "poa", "final", "bonus", "games", "sensitive", "intake")


def _rows():
    return db.query("SELECT id, enabled, units_json, voice_es, voice_en, persona_learn_id, persona_intake_id FROM characters")


def list_all():
    out = []
    for r in _rows():
        out.append({
            "id": r[0],
            "enabled": bool(r[1]),
            "units": json.loads(r[2]) if r[2] else [],
            "voice_es": r[3],
            "voice_en": r[4],
            "persona_learn_id": r[5],
            "persona_intake_id": r[6],
        })
    return out


def list_enabled():
    return [c for c in list_all() if c["enabled"]]


def get(char_id):
    for c in list_all():
        if c["id"] == char_id:
            return c
    return None


def lesson_character(unit, authored):
    for c in list_enabled():
        if unit in (c["units"] or []):
            return c["id"]
    if authored is not None and any(c["id"] == authored and c["enabled"] for c in list_all()):
        return authored
    return "calavera"


def item_character(authored, host):
    if authored is None:
        return None
    if any(c["id"] == authored and c["enabled"] for c in list_all()):
        return authored
    return host


def update(char_id, fields):
    existing = get(char_id)
    if existing is None:
        return None
    if char_id == "calavera" and fields.get("enabled") is False:
        raise ValueError("calavera cannot be disabled")
    with db.transaction() as conn:
        sets = []
        params = []
        if "enabled" in fields and fields["enabled"] is not None:
            sets.append("enabled = ?")
            params.append(1 if fields["enabled"] else 0)
        new_units = None
        if "units" in fields and fields["units"] is not None:
            new_units = list(fields["units"])
            sets.append("units_json = ?")
            params.append(json.dumps(new_units))
        if "voice_es" in fields:
            sets.append("voice_es = ?")
            params.append(fields["voice_es"])
        if "voice_en" in fields:
            sets.append("voice_en = ?")
            params.append(fields["voice_en"])
        if sets:
            p = list(params) + [char_id]
            conn.execute("UPDATE characters SET " + ", ".join(sets) + " WHERE id = ?", tuple(p))
        if new_units is not None:
            for other in list_all():
                if other["id"] == char_id:
                    continue
                other_units = [u for u in (other["units"] or []) if u not in new_units]
                if other_units != (other["units"] or []):
                    conn.execute("UPDATE characters SET units_json = ? WHERE id = ?", (json.dumps(other_units), other["id"]))
    return get(char_id)


def character_for(unit):
    return lesson_character(unit, None)
