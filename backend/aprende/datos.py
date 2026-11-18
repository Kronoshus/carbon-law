"""Tus datos: questions and answers per journey (T5-05)."""
import datetime
import json
import os
import uuid

import db
import yaml

from aprende import journey

HERE = os.path.dirname(os.path.abspath(__file__))
# backend/aprende/datos.py -> repo root
QUESTIONS_PATH = os.path.join(HERE, "..", "..", "aprende", "content", "datos.yaml")

_QUESTIONS = None


def _load():
    global _QUESTIONS
    if _QUESTIONS is None:
        with open(QUESTIONS_PATH, encoding="utf-8") as f:
            _QUESTIONS = yaml.safe_load(f) or []
    return _QUESTIONS


def questions(lang=None):
    return _load()


def by_id(qid):
    for q in _load():
        if q["id"] == qid:
            return q
    return None


def _docs_for_journey(j):
    confirmed = (j.get("documents") or {}).get("confirmed") or []
    tentative = (j.get("documents") or {}).get("tentative") or []
    if confirmed:
        return list(confirmed)
    if tentative:
        return list(tentative)
    return ["will", "trust", "poa", "ahcd"]


def applicable(j):
    docs = _docs_for_journey(j)
    out = []
    for q in _load():
        qdocs = q.get("docs") or []
        if not qdocs or (set(qdocs) & set(docs)):
            out.append(q)
    return out


def _answers_map(jid):
    rows = db.query("SELECT question_id, status, answer FROM datos_answers WHERE journey_id = ?", (jid,))
    return {r[0]: (r[1], r[2]) for r in rows}


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()


def get_datos(j, lang="es"):
    jid = j["id"]
    amap = _answers_map(jid)
    out_questions = []
    open_ids = []
    for q in applicable(j):
        qid = q["id"]
        status_answer = amap.get(qid)
        if status_answer is None:
            status = "open"
            answer = None
        else:
            status = status_answer[0]
            answer = status_answer[1]
        if status == "open":
            open_ids.append(qid)
        text = q["es"] if lang == "es" else q["en"]
        out_questions.append({
            "id": qid,
            "asked_after": q["asked_after"],
            "docs": q.get("docs") or [],
            "text": text,
            "status": status,
            "answer": answer,
        })
    completed = (len(open_ids) == 0) and len(applicable(j)) > 0
    return {"questions": out_questions, "open": open_ids, "completed": completed}


def put_datos(j, qid, body, actor="client"):
    # validate question exists
    q = by_id(qid)
    if q is None:
        raise KeyError("unknown question")
    # applicable? Contract doesn't require applicable check; but only known id.
    jid = j["id"]
    # determine new status/answer
    if body.get("skipped") is True:
        new_status = "skipped"
        new_answer = None
    else:
        answer = body.get("answer")
        if answer is None:
            raise ValueError("missing answer")
        if not str(answer).strip():
            raise ValueError("blank answer")
        new_status = "answered"
        new_answer = str(answer).strip() if False else str(answer)
        # keep original? test expects "Ana María Torres" exact; strip? blank check uses strip. Store as given? Test put answer="Ana María Torres". We'll store stripped.
        new_answer = str(answer).strip()

    # check applicable? If not applicable, maybe still allow? Keep simple: allow any known.

    # fetch existing
    rows = db.query("SELECT status, answer FROM datos_answers WHERE journey_id = ? AND question_id = ?", (jid, qid))
    old_status = rows[0][0] if rows else None
    old_answer = rows[0][1] if rows else None

    if rows and (old_status != new_status or old_answer != new_answer):
        db.execute(
            "INSERT INTO datos_audit (id, journey_id, question_id, old_status, old_answer, new_status, new_answer, actor, at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), jid, qid, old_status, old_answer, new_status, new_answer, actor, _now_iso()))

    db.execute(
        "INSERT INTO datos_answers (journey_id, question_id, status, answer, updated_at) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT (journey_id, question_id) DO UPDATE SET status=excluded.status, answer=excluded.answer, updated_at=excluded.updated_at",
        (jid, qid, new_status, new_answer, _now_iso()))

    # check completion
    jfresh = journey.get_journey(jid)
    data = get_datos(jfresh, "es")
    if data["completed"] and data["open"] == []:
        # only applicable questions; ensure all applicable done
        journey.apply(jid, "intake_completed", {}, actor="system")

    return {"ok": True}
