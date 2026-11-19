"""Staff-only routes for the Aprende journey: the "Mi plan" late list."""
import datetime
from fastapi import APIRouter, Header, HTTPException

import app as backend_app
import db
from aprende import journey, timeline

router = APIRouter()

STAFF_ROLES = {"paralegal", "attorney", "admin"}


def _auth(authorization):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    u, _ = backend_app.require_auth(authorization)
    return u


@router.get("/staff/journeys")
def list_journeys(authorization: str = Header(None)):
    u = _auth(authorization)
    if u.get("role") not in STAFF_ROLES:
        raise HTTPException(403, "staff only")
    now = datetime.datetime.now(datetime.timezone.utc)
    out = []
    for (jid,) in db.query("SELECT id FROM journeys"):
        j = journey.get_journey(jid)
        if j is None:
            continue
        j["timeline"] = timeline.for_journey(j, now)
        late = [s["step"] for s in j["timeline"] if s["status"] == "late"]
        late_dues = [s["due"] for s in j["timeline"] if s["status"] == "late" and s.get("due")]
        earliest_late_due = min(late_dues) if late_dues else None
        next_step = None
        for s in j["timeline"]:
            if s["status"] in ("today", "next"):
                next_step = s["step"]
                break
        if next_step is None:
            for s in j["timeline"]:
                if s["status"] not in ("done",):
                    next_step = s["step"]
                    break
        if next_step is None and j["timeline"]:
            next_step = j["timeline"][-1]["step"]
        if earliest_late_due is not None:
            due = earliest_late_due
        else:
            ns = None
            for s in j["timeline"]:
                if s["step"] == next_step:
                    ns = s
                    break
            due = (ns.get("due") or ns.get("date")) if ns else None
        client_name = None
        for uu in backend_app.users.values():
            if uu.get("id") == j["user_id"]:
                client_name = uu.get("name")
                break
        out.append({
            "journey_id": j["id"],
            "client_name": client_name,
            "day": j["day"],
            "next_step": next_step,
            "late": late,
            "due": due,
            "_late_count": len(late),
            "_sort_due": earliest_late_due or "9999-12-31",
        })
    out.sort(key=lambda r: (-r["_late_count"], r["_sort_due"]))
    for r in out:
        r.pop("_late_count", None)
        r.pop("_sort_due", None)
    return out
