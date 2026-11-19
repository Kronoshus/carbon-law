"""Tus datos (spec 6.1): the questions after each core lesson and in the day-4 summary, and the client's answers.

The questions are content (`aprende/content/datos.yaml`). A question applies when it belongs to every client (`docs: []`)
or to one of the client's documents: the confirmed choice, else the tentative one, else all four."""
import os
import uuid

import yaml

import db
from aprende import journey

QUESTIONS = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "..", "..", "aprende", "content", "datos.yaml"),
                                encoding="utf-8"))
BY_ID = {q["id"]: q for q in QUESTIONS}


def applicable(j):
    docs = set(j["documents"]["confirmed"] or j["documents"]["tentative"] or journey.DOC_CODES)
    return [q for q in QUESTIONS if not q["docs"] or set(q["docs"]) & docs]


def get_datos(j, lang="es"):
    saved = {qid: (status, answer) for qid, status, answer in
             db.query("SELECT question_id, status, answer FROM datos_answers WHERE journey_id = ?", (j["id"],))}
    qs = [{"id": q["id"], "asked_after": q["asked_after"], "docs": q["docs"], "text": q[lang],
           "status": saved.get(q["id"], ("open", None))[0], "answer": saved.get(q["id"], ("open", None))[1]}
          for q in applicable(j)]
    open_ = [q["id"] for q in qs if q["status"] == "open"]
    return {"questions": qs, "open": open_, "completed": not open_}


def save(j, qid, *, answer=None, actor="client"):
    """Record an answer (or a skip, with answer=None). A change to an earlier answer keeps an audit row. When no applicable
    question is left open, the intake is complete (the event de-duplicates, so the discount is earned once)."""
    status = "skipped" if answer is None else "answered"
    with db.transaction() as conn:
        old = conn.execute("SELECT status, answer FROM datos_answers WHERE journey_id = ? AND question_id = ?",
                           (j["id"], qid)).fetchone()
        if old and tuple(old) != (status, answer):
            conn.execute("INSERT INTO datos_audit (id, journey_id, question_id, old_status, old_answer, new_status, new_answer, "
                         "actor, at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (str(uuid.uuid4()), j["id"], qid, old[0], old[1], status, answer, actor, journey._now_iso()))
        conn.execute("INSERT INTO datos_answers (journey_id, question_id, status, answer, updated_at) VALUES (?, ?, ?, ?, ?) "
                     "ON CONFLICT (journey_id, question_id) DO UPDATE SET status = excluded.status, answer = excluded.answer, "
                     "updated_at = excluded.updated_at", (j["id"], qid, status, answer, journey._now_iso()))
    if get_datos(j)["completed"]:
        journey.apply(j["id"], "intake_completed", {}, actor="system")
