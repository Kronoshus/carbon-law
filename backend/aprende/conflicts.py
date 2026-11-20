"""Conflict-of-interest queue for Aprende y Planea (T5-03).

Staff-only: the firm's uploaded conflict list and per-journey checks.
Client-facing data never includes names or matches.
"""
import csv
import io
import json
import uuid
import datetime

import db
from aprende import clock
from carbon_intake.conflicts import conflict_hits
from aprende.notify import notify_staff

__all__ = ["notify_staff", "conflict_hits"]


def _now_iso():
    return clock.now_iso()


def get_list():
    rows = db.query("SELECT name FROM conflict_names")
    return [r[0] for r in rows]


def replace_list(csv_text):
    reader = csv.reader(io.StringIO(csv_text or ""))
    rows = list(reader)
    if rows and rows[0] and (rows[0][0] or "").strip().lower() == "name":
        rows = rows[1:]
    names = list(dict.fromkeys(v for v in ((r[0] or "").strip() for r in rows if r) if v))   # in order, no repeats
    with db.transaction() as conn:                       # the old list stays in force until the new one is complete
        conn.execute("DELETE FROM conflict_names")
        for n in names:
            conn.execute("INSERT INTO conflict_names (name) VALUES (?)", (n,))
    return {"count": len(names)}


def delete_list():
    db.execute("DELETE FROM conflict_names")
    return {"ok": True}


def _run_for(journey_id, names):
    firm = get_list()
    if not firm:
        result = "no_list"
        matches = []
    else:
        # each submitted name on its own, so words from two different people never combine into a match
        matches = list(dict.fromkeys(m for n in names or [] for m in conflict_hits(n, firm)))
        result = "possible" if matches else "clear"
    db.execute(
        "INSERT INTO conflict_checks (id, journey_id, names_json, matches_json, result, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), journey_id, json.dumps(names or []), json.dumps(matches), result, _now_iso()),
    )
    if result == "possible":
        notify_staff("Possible conflict", f"A possible conflict needs review. Journey: {journey_id}")
    return result, matches


def run_check(journey_id, names):
    result, matches = _run_for(journey_id, names)
    # record the server-side event (names/matches never enter the event payload)
    from aprende import journey
    journey.apply(journey_id, "conflict_auto", {"result": result}, actor="system")
    return result


def queue():
    rows = db.query(
        "SELECT journey_id, names_json, matches_json, result, decision FROM conflict_checks ORDER BY created_at, id"
    )
    out = []
    for r in rows:
        out.append({
            "journey_id": r[0],
            "names": json.loads(r[1] or "[]"),
            "matches": json.loads(r[2] or "[]"),
            "result": r[3],
            "decision": r[4],
        })
    return out


def get_check(journey_id):
    rows = db.query(
        "SELECT id, names_json, matches_json, result, decision FROM conflict_checks WHERE journey_id = ? ORDER BY created_at DESC, id DESC LIMIT 1",
        (journey_id,),
    )
    if not rows:
        return None
    r = rows[0]
    return {"id": r[0], "names": json.loads(r[1] or "[]"), "matches": json.loads(r[2] or "[]"),
            "result": r[3], "decision": r[4]}


def decide(journey_id, result, staff_email):
    if result not in ("cleared", "flagged"):
        raise ValueError("invalid result")
    from aprende import journey
    j = journey.get_journey(journey_id)
    if j is None:
        raise KeyError("unknown journey")
    # update latest check
    chk = get_check(journey_id)
    if chk is not None:
        db.execute(
            "UPDATE conflict_checks SET decision = ?, decided_by = ?, decided_at = ? WHERE id = ?",
            (result, staff_email, _now_iso(), chk["id"]),
        )
    journey.apply(journey_id, "conflict_firm", {"result": result}, actor=staff_email)
    return {"ok": True}
