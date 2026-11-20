"""Staff views of Aprende journeys (spec 11)."""
import datetime

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

import app as backend_app
import db
from aprende import analytics, datos, journey, legacy, review, timeline

router = APIRouter()


def _row(j, now):
    jid = j["id"]
    steps = timeline.for_journey(j, now)
    late = [s for s in steps if s["status"] == "late"]
    upcoming = next((s for s in steps if s["status"] != "done"), steps[-1] if steps else None)
    dd = datos.get_datos(j)
    qs = dd["questions"]
    total = len(qs)
    done = sum(1 for q in qs if q["status"] != "open")
    paid_cents = sum(r[0] for r in db.query("SELECT amount_cents FROM payments WHERE journey_id = ?", (jid,)))
    refunded_cents = sum(r[0] for r in db.query("SELECT amount_cents FROM refunds WHERE journey_id = ?", (jid,)))
    appointments = [{"kind": r[0], "start_utc": r[1]}
                    for r in db.query("SELECT kind, start_utc FROM bookings WHERE journey_id = ? AND status = 'active' ORDER BY start_utc", (jid,))]
    qrows = db.query("SELECT answer FROM attorney_questions WHERE journey_id = ?", (jid,))
    open_q = sum(1 for (a,) in qrows if a is None)
    answered_q = len(qrows) - open_q
    return {"journey_id": jid, "client_name": legacy._user_name(j["user_id"]), "day": j["day"],
            "next_step": upcoming["step"] if upcoming else None, "late": [s["step"] for s in late],
            "due": (min(s["due"] for s in late) if late else ((upcoming.get("due") or upcoming.get("date")) if upcoming else None)),
            "conflict": j["conflict"],
            "datos": {"done": done, "total": total, "complete": not dd["open"]},
            "payment": {"paid": "paid" in j["facts"], "paid_cents": paid_cents, "refunded_cents": refunded_cents},
            "drafts_waiting": len(review._current_drafts(jid)),
            "appointments": appointments,
            "questions": {"open": open_q, "answered": answered_q}}


@router.get("/staff/journeys")
def list_journeys(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    backend_app.require_auth(authorization, {"paralegal", "attorney", "admin"})
    now = datetime.datetime.now(datetime.timezone.utc)
    rows = []
    for (jid,) in db.query("SELECT id FROM journeys"):
        j = journey.get_journey(jid)
        if not j:
            continue
        rows.append(_row(j, now))
    return sorted(rows, key=lambda r: (-len(r["late"]), r["due"] if r["late"] else "9999"))


@router.get("/staff/journeys/{jid}")
def get_journey_detail(jid: str, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    backend_app.require_auth(authorization, {"paralegal", "attorney", "admin"})
    j = journey.get_journey(jid)
    if not j:
        raise HTTPException(404, "journey not found")
    now = datetime.datetime.now(datetime.timezone.utc)
    row = _row(j, now)
    steps = timeline.for_journey(j, now)
    qrows = db.query("SELECT id, question, lesson_id, character, created_at, answer, answered_by, answered_at "
                     "FROM attorney_questions WHERE journey_id = ? ORDER BY created_at, id", (jid,))
    questions = [{"id": r[0], "question": r[1], "lesson_id": r[2], "character": r[3], "created_at": r[4],
                  "answer": r[5], "answered_by": r[6], "answered_at": r[7]} for r in qrows]
    return {**row, "timeline": steps, "questions": questions}


class AnswerBody(BaseModel):
    answer: str = Field(...)


@router.post("/staff/attorney-questions/{qid}/answer")
def answer_question(qid: str, body: AnswerBody, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    u, _ = backend_app.require_auth(authorization, {"attorney"})
    rows = db.query("SELECT id FROM attorney_questions WHERE id = ?", (qid,))
    if not rows:
        raise HTTPException(404, "question not found")
    ans = (body.answer or "").strip()
    if len(ans) < 1 or len(ans) > 4000:
        raise HTTPException(422, "answer must be 1-4000 chars")
    now = journey._now_iso()
    with db.transaction() as conn:
        conn.execute("UPDATE attorney_questions SET answer = ?, answered_by = ?, answered_at = ? WHERE id = ?",
                     (ans, u["email"], now, qid))
    backend_app.log_audit(u["email"], "answer", "attorney_question", qid, "")
    return {"id": qid, "answer": ans, "answered_by": u["email"], "answered_at": now}


@router.get("/staff/analytics")
def staff_analytics(since: str = None, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    backend_app.require_auth(authorization, {"paralegal", "attorney", "admin"})
    return analytics.dashboard(since)
