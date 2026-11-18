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
from aprende import characters, journey, learn
from carbon_intake import UNTRUSTED, spoken

router = APIRouter()
TAG = re.compile(r"\[ATTORNEY_QUESTION:\s*([^\]]*)\]")

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

class ChatBody(BaseModel):
    mode: str | None = None
    character: str | None = None
    lesson_id: str | None = None
    messages: list[dict] = Field(default_factory=list)
    covered: list = Field(default_factory=list)
    docs: list = Field(default_factory=list)
    lang: str = "es"


def _auth(authorization):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    user, _ = backend_app.require_auth(authorization)
    return user


def _journey(user):
    if user.get("role") != "client":
        raise HTTPException(403, "staff have no journey")
    if "adult_confirmed_at" not in user:
        raise HTTPException(403, "adult confirmation required")
    j = journey.get_or_create_for_user(user["id"])
    if not j["gates"].get("may_chat"):
        raise GateError(["may_chat"])
    return j


@router.post("/chat")
async def post_chat(body: ChatBody, authorization: str = Header(None)):
    user = _auth(authorization)

    if body.mode != "learn":
        raise HTTPException(422, "unsupported mode")
    if not body.character or characters.get(body.character) is None:
        raise HTTPException(422, "unknown character")
    if not body.lesson_id:
        raise HTTPException(422, "missing lesson_id")
    rows = db.query("SELECT id FROM content_lessons WHERE id = ?", (body.lesson_id,))
    if not rows:
        raise HTTPException(404, "lesson not found")

    try:
        j = _journey(user)
    except GateError as e:
        return JSONResponse(status_code=409, content={"error": "gate", "missing": e.missing})

    lang = "en" if body.lang == "en" else "es"

    system = system_prompt(body.character, body.lesson_id, lang)

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

    # The hidden tag comes off first: the spoken() guard stops at the first "?", which the client's question inside the
    # tag may contain. The model sees its own tag again next turn through `history` (the prototype's rule).
    tags = TAG.findall(completion.text or "")
    question = tags[-1].strip() if tags else None
    text_out = spoken(TAG.sub(" ", completion.text or "")).strip()
    history = text_out + (f" [ATTORNEY_QUESTION: {question}]" if question else "")
    if question:
        db.execute(
            "INSERT INTO attorney_questions (id, journey_id, question, lesson_id, character, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (journey_id, question) DO NOTHING",
            (str(uuid.uuid4()), j["id"], question, body.lesson_id, body.character, journey._now_iso()))

    return {
        "text": text_out,
        "history": history,
        "reasoning": completion.reasoning,
        "covered": body.covered or [],
        "open": [],
        "docs": body.docs or [],
        "attorney_question": question is not None,
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
