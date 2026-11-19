"""Staff views of Aprende journeys (spec 11)."""
import datetime

from fastapi import APIRouter, Header, HTTPException

import app as backend_app
import db
from aprende import journey, legacy, timeline

router = APIRouter()


@router.get("/staff/journeys")
def list_journeys(authorization: str = Header(None)):
    """Every journey with its late firm steps, the most late first (T6-09)."""
    if not authorization:
        raise HTTPException(401, "not authenticated")
    backend_app.require_auth(authorization, {"paralegal", "attorney", "admin"})
    now = datetime.datetime.now(datetime.timezone.utc)
    rows = []
    for (jid,) in db.query("SELECT id FROM journeys"):
        j = journey.get_journey(jid)
        steps = timeline.for_journey(j, now)
        late = [s for s in steps if s["status"] == "late"]
        upcoming = next((s for s in steps if s["status"] != "done"), steps[-1])
        rows.append({"journey_id": jid, "client_name": legacy._user_name(j["user_id"]), "day": j["day"],
                     "next_step": upcoming["step"], "late": [s["step"] for s in late],
                     "due": min(s["due"] for s in late) if late else upcoming["due"] or upcoming["date"]})
    return sorted(rows, key=lambda r: (-len(r["late"]), r["due"] if r["late"] else "9999"))
