"""Character registry for Aprende y Planea (T3-06)."""
import json

import db


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


def character_for(unit):
    """Enabled character assigned to `unit`, falling back to calavera."""
    for c in list_enabled():
        if unit in (c["units"] or []):
            return c["id"]
    return "calavera"


def update(char_id, fields):
    existing = get(char_id)
    if existing is None:
        return None
    if char_id == "calavera" and fields.get("enabled") is False:
        raise ValueError("calavera cannot be disabled")
    sets = []
    params = []
    if "enabled" in fields and fields["enabled"] is not None:
        sets.append("enabled = ?")
        params.append(1 if fields["enabled"] else 0)
    if "units" in fields and fields["units"] is not None:
        sets.append("units_json = ?")
        params.append(json.dumps(fields["units"]))
    if "voice_es" in fields:
        sets.append("voice_es = ?")
        params.append(fields["voice_es"])
    if "voice_en" in fields:
        sets.append("voice_en = ?")
        params.append(fields["voice_en"])
    if not sets:
        return get(char_id)
    params.append(char_id)
    db.execute("UPDATE characters SET " + ", ".join(sets) + " WHERE id = ?", tuple(params))
    return get(char_id)
