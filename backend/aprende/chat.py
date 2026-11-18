"""Chat (Aprende y Planea): learning-mode chat over Beam (T5-01)."""
import datetime
import json
import re
import uuid

import db
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import app as backend_app
from ai import ModelError
from aprende import characters, journey, learn, datos
from carbon_intake import UNTRUSTED, spoken

router = APIRouter()
TAG = re.compile(r"\[ATTORNEY_QUESTION:\s*([^\]]*)\]")
DONE = re.compile(r"\[DONE:\s*([^\]]*)\]")

class GateError(Exception):
    def __init__(self, missing):
        self.missing = missing


def model_client():
    from ai.beam import BeamClient

    return BeamClient()


def system_prompt(character, lesson, lang):
    char_id = character if isinstance(character, str) else (character or {}).get("id", "")
    lesson_id = lesson if isinstance(lesson, str) else (lesson or {}).get("id", lesson)
    char = characters.get(char_id) if char_id else None
    name = (char or {}).get("id") or char_id or "calavera"
    try:
        items = learn._items(lesson_id)
    except Exception:
        items = []
    expls = []
    for it in items or []:
        try:
            payload = json.loads(it["es"] if lang == "es" else it["en"])
        except Exception:
            payload = {}
        text = payload.get("text") or payload.get("explain")
        if text:
            src = ""
            if it.get("source_id"):
                rows = db.query("SELECT kind, cite, url FROM content_sources WHERE id = ?", (it["source_id"],))
                if rows:
                    src = " (source: " + str(rows[0][1]) + ")"
            expls.append("- " + str(text) + src)
    explanations = "\n".join(expls) if expls else "(none)"
    lang_name = "Spanish (usted form)" if lang == "es" else "English"
    return (
        "You are " + name + ", an AI program and not the attorney or a person. "
        "You give general information only, never legal advice about the client's own situation, "
        "never fees or results. Speak only " + lang_name + ". "
        "Answer in short turns and ask exactly one question per turn. "
        "The only explanations you may draw on are the published lesson items below.\n\n"
        "Explanations you may draw on:\n" + explanations + "\n\n"
        "If the client asks about their own situation, answer with: " +
        chr(34) + "Esa es una pregunta para el abogado Raval. Ya se la anoté y él le responde." + chr(34) + " "
        "and append the hidden tag [ATTORNEY_QUESTION: <the question>]. "
        "You are not the attorney and not a person (no es el abogado ni una persona). " + UNTRUSTED
    )

def _question_text(q, lang):
    if isinstance(q, str):
        qo = datos.by_id(q)
        q = qo if qo is not None else {"id": q, "es": q, "en": q}
    if isinstance(q, dict):
        # support either datos yaml shape or {"id","text"}
        if "text" in q and isinstance(q.get("text"), str):
            return q["text"], q.get("id") or q.get("question_id")
        qid = q.get("id")
        qo = datos.by_id(qid) if qid else None
        if qo is not None:
            q = qo
        text = q.get("es") if lang == "es" else q.get("en")
        if isinstance(text, str):
            return text, q.get("id")
        # maybe q has es/en already
        return str(q.get("es" if lang == "es" else "en", "")), q.get("id")
    return str(q), None


def intake_prompt(character, question, lang):
    char_id = character if isinstance(character, str) else (character or {}).get("id", "")
    char = characters.get(char_id) if char_id else None
    name = (char or {}).get("id") if char else (char_id or "calavera")
    text, qid = _question_text(question, lang)
    lang_name = "Spanish (usted form)" if lang == "es" else "English"
    qid = qid or (question if isinstance(question, str) else (question or {}).get("id", ""))
    return (
        "You are " + str(name) + ", an AI program and not the attorney or a person. "
        "You give general information only, never legal advice about the client's own situation, "
        "never fees or results. Speak only " + lang_name + ". "
        "Ask one thing at a time, and steer back gently if the client wanders. "
        "The current question you must ask is: " + chr(34) + str(text) + chr(34) + " (id: " + str(qid) + "). "
        "When the client has answered the current question fully, end your reply with [DONE: " + str(qid) + "]."
    )

class ChatBody(BaseModel):
    mode: str | None = None
    character: str | None = None
    lesson_id: str | None = None
    messages: list[dict] = Field(default_factory=list)
    covered: list = Field(default_factory=list)
    docs: list = Field(default_factory=list)
    group: str | None = None
    lang: str = "es"


def _auth(authorization):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    user, _ = backend_app.require_auth(authorization)
    return user


def _journey(user, gate="may_chat"):
    if user.get("role") != "client":
        raise HTTPException(403, "staff have no journey")
    if "adult_confirmed_at" not in user:
        raise HTTPException(403, "adult confirmation required")
    j = journey.get_or_create_for_user(user["id"])
    if not j["gates"].get(gate):
        raise GateError([gate])
    return j


@router.post("/chat")
async def post_chat(body: ChatBody, authorization: str = Header(None)):
    user = _auth(authorization)

    mode = body.mode or "learn"
    if mode not in ("learn", "intake"):
        raise HTTPException(422, "unsupported mode")
    if not body.character or characters.get(body.character) is None:
        raise HTTPException(422, "unknown character")

    if mode == "learn":
        if not body.lesson_id:
            raise HTTPException(422, "missing lesson_id")
        rows = db.query("SELECT id FROM content_lessons WHERE id = ?", (body.lesson_id,))
        if not rows:
            raise HTTPException(404, "lesson not found")
        gate_name = "may_chat"
    else:
        group = body.group if hasattr(body, "group") else None
        # group is on body? ChatBody has no group field yet; add handling via getattr with default from body dict
        group = getattr(body, "group", None)
        if group is None:
            # pydantic model may not have group; try raw
            group = None
        if group not in ("will", "trust", "ahcd", "poa", "resumen"):
            raise HTTPException(422, "invalid group")
        gate_name = "may_collect_details"

    try:
        j = _journey(user, gate=gate_name)
    except GateError as e:
        return JSONResponse(status_code=409, content={"error": "gate", "missing": e.missing})

    lang = "en" if body.lang == "en" else "es"

    if mode == "learn":
        system = system_prompt(body.character, body.lesson_id, lang)
    else:
        # determine current question
        applicable_qs = [q for q in datos.applicable(j) if q.get("asked_after") == group]
        amap = {r[0]: r[1] for r in [(a, None) for a in []]}  # placeholder
        # compute open statuses
        ddata = datos.get_datos(j, lang)
        status_by = {q["id"]: q["status"] for q in ddata["questions"]}
        current_q = None
        for q in applicable_qs:
            if status_by.get(q["id"], "open") == "open":
                current_q = q
                break
        if current_q is None:
            # no model call
            covered_ids = [qid for qid, st in [(q["id"], status_by.get(q["id"])) for q in ddata["questions"]] if st in ("answered", "skipped")]
            # union with client covered
            covered = sorted(set((body.covered or []) + covered_ids))
            open_ids = ddata["open"]
            next_q = None
            return {
                "text": "",
                "history": "",
                "reasoning": None,
                "covered": covered,
                "open": open_ids,
                "docs": body.docs or [],
                "attorney_question": False,
                "next_question": next_q,
            }
        system = intake_prompt(body.character, current_q, lang)

    msgs = []
    for m in body.messages or []:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "assistant":
            entry = {"role": "assistant", "content": str(content)[:4000]}
            if m.get("reasoning_content"):
                entry["reasoning_content"] = str(m["reasoning_content"])[:50000]
            msgs.append(entry)
        else:
            fenced = "<client_data>" + str(content)[:4000].replace("</client_data>", "") + "</client_data>"
            msgs.append({"role": "user", "content": fenced})

    client = model_client()
    try:
        completion = await client.complete(system=system, messages=msgs, max_tokens=400, purpose="aprende_chat_learn", temperature=0.4)
    except ModelError:
        raise HTTPException(503, "Lo sentimos, el servicio no esta disponible en este momento.")

    raw = completion.text or ""
    tags = TAG.findall(raw)
    question = tags[-1].strip() if tags else None
    done_tags = DONE.findall(raw)
    done_id = done_tags[-1].strip() if done_tags else None

    # strip hidden tags from spoken text
    text_no_tags = TAG.sub(" ", raw)
    text_no_tags = DONE.sub(" ", text_no_tags)
    text_out = spoken(text_no_tags).strip()

    # attorney question storage (learn + intake)
    if question:
        db.execute(
            "INSERT INTO attorney_questions (id, journey_id, question, lesson_id, character, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (journey_id, question) DO NOTHING",
            (str(uuid.uuid4()), j["id"], question, body.lesson_id, body.character, journey._now_iso()))

    # build history keeping tags
    history = text_out
    if question:
        history = history + f" [ATTORNEY_QUESTION: {question}]"
    if done_id:
        history = history + f" [DONE: {done_id}]"

    # intake: save answer if DONE names current question
    if mode == "intake":
        # recompute current question id
        ddata = datos.get_datos(j, lang)
        status_by = {q["id"]: q["status"] for q in ddata["questions"]}
        applicable_qs = [q for q in datos.applicable(j) if q.get("asked_after") == group]
        current_q = None
        for q in applicable_qs:
            if status_by.get(q["id"], "open") == "open":
                current_q = q
                break
        current_id = current_q["id"] if current_q else None
        if done_id and current_id and done_id == current_id:
            # save answer = user turns with that question_id
            user_turns = [m.get("content", "") for m in (body.messages or [])
                          if m.get("role") != "assistant" and m.get("question_id") == done_id]
            answer = "\n\n".join(str(t) for t in user_turns)
            try:
                datos.put_datos(j, done_id, {"answer": answer})
            except Exception:
                pass
        # ignore DONE for other ids

    # covered
    if mode == "intake":
        ddata = datos.get_datos(j, lang)
        status_by = {q["id"]: q["status"] for q in ddata["questions"]}
        covered_ids = [qid for qid, st in status_by.items() if st in ("answered", "skipped")]
        covered = sorted(set((body.covered or []) + covered_ids))
        open_ids = ddata["open"]
        # next_question
        applicable_qs = [q for q in datos.applicable(j) if q.get("asked_after") == group]
        status_by2 = {q["id"]: q["status"] for q in datos.get_datos(j, lang)["questions"]}
        next_q = None
        for q in applicable_qs:
            if status_by2.get(q["id"], "open") == "open":
                next_q = {"id": q["id"], "text": (q["es"] if lang == "es" else q["en"])}
                break
    else:
        covered = body.covered or []
        open_ids = []
        next_q = None

    return {
        "text": text_out,
        "history": history,
        "reasoning": completion.reasoning,
        "covered": covered,
        "open": open_ids,
        "docs": body.docs or [],
        "attorney_question": question is not None,
        "next_question": next_q,
    }


@router.get("/chat/attorney-questions")
def list_attorney_questions(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    user, _ = backend_app.require_auth(authorization, {"paralegal", "attorney", "admin"})
    if user.get("role") not in ("paralegal", "attorney", "admin"):
        raise HTTPException(403, "staff only")
    rows = db.query(
        "SELECT id, journey_id, question, lesson_id, character, created_at FROM attorney_questions ORDER BY created_at DESC"
    )
    out = []
    for r in rows:
        out.append({
            "id": r[0],
            "journey_id": r[1],
            "question": r[2],
            "lesson_id": r[3],
            "character": r[4],
            "created_at": r[5],
        })
    return out
