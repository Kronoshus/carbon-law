"""Talking with the characters (spec 9): `POST /chat` in learning mode (T5-01) and intake mode (T5-05).

The persona text is content (`aprende/content/personas.yaml`, T5-07, attorney-approved); this module only fills it in,
fences the client's words, guards the reply, and handles the hidden tags."""
import json
import os
import re
import uuid

import yaml
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import app as backend_app
import db
from ai import ModelError
from aprende import characters, content, datos, firm, journey, learn
from carbon_intake import UNTRUSTED, spoken

router = APIRouter()
TAG = re.compile(r"\[ATTORNEY_QUESTION:\s*([^\]]*)\]")
DONE = re.compile(r"\[DONE:\s*([^\]]*)\]")
GROUPS = ("will", "trust", "ahcd", "poa", "resumen")
LANGUAGE = {"es": "Spanish", "en": "English"}
PERSONAS = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "..", "..", "aprende", "content", "personas.yaml"),
                               encoding="utf-8"))


def model_client():
    from ai.beam import BeamClient
    return BeamClient()


# The persona forbids these (personas.yaml); the server also refuses a reply that does them anyway (brief s.6):
# a question about immigration status, or an annuity pitch. Tags are removed first: they hold the client's own words.
IMMIGRATION = re.compile(r"inmigra|migratori|ciudadan|indocumentad|green card|tarjeta verde|\bvisas?\b|immigra|citizen|"
                         r"undocumented|residencia permanente|permanent resident", re.I)
ANNUITY = re.compile(r"anualidad|annuit", re.I)
UNAVAILABLE = "El servicio no está disponible en este momento. Intente de nuevo en unos minutos."


def _breaks_rules(reply):
    asks = [s for s in re.split(r"(?<=[.!?])\s+", reply) if "?" in s and IMMIGRATION.search(s)]
    return bool(asks or ANNUITY.search(reply))


def _fill(text, **values):
    for k, v in values.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def _persona(character, lang, mode, **values):
    live = content.live_entries("persona")
    shared_body = live["persona:shared"]
    shared_text = shared_body["text"]
    char_seed = PERSONAS["characters"][character]
    char_body = live[f"persona:characters.{character}"]
    c_name = char_body["name"]
    c_persona = char_body["persona"]
    mode_seed = PERSONAS["modes"][mode]
    mode_body = live[f"persona:modes.{mode}"]
    mode_text = mode_body["text"]
    parts = (shared_text, c_persona, mode_text)
    return _fill("\n\n".join(parts), name=c_name[lang], language=LANGUAGE[lang], **values) + "\n\n" + UNTRUSTED


def system_prompt(character, lesson_id, lang):
    """Learning mode: the lesson's published explanations, each with its source, are all the character may draw on."""
    cites = {sid: cite for sid, cite in db.query("SELECT id, cite FROM content_sources")}
    lines = []
    for it in learn._items(lesson_id):
        p = json.loads(it[lang])
        text = p.get("text") or p.get("explain")
        if text:
            lines.append(f"- {text}" + (f" (source: {cites[it['source_id']]})" if it["source_id"] in cites else ""))
    return _persona(character, lang, "learn", explanations="\n".join(lines) or "(none)")


def intake_prompt(character, question, lang):
    return _persona(character, lang, "intake", question=question[lang], question_id=question["id"])


class ChatBody(BaseModel):
    mode: str
    character: str
    lesson_id: str | None = None
    group: str | None = None
    messages: list[dict] = Field(default_factory=list)
    docs: list = Field(default_factory=list)
    lang: str = "es"


def _client_journey(authorization, gate):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    user, _ = backend_app.require_auth(authorization)
    if user.get("role") != "client":
        raise HTTPException(403, "staff have no journey")
    if "adult_confirmed_at" not in user:
        raise HTTPException(403, "adult confirmation required")
    j = journey.get_or_create_for_user(user["id"])
    return j, j["gates"].get(gate, False)


def _current(j, group):
    """The first open question of this lesson's group, or None when the group is done."""
    status = {q["id"]: q["status"] for q in datos.get_datos(j)["questions"]}
    return next((q for q in datos.applicable(j) if q["asked_after"] == group and status.get(q["id"]) == "open"), None)


def _messages(raw):
    out = []
    for m in raw:
        if m.get("role") == "assistant":
            out.append({"role": "assistant", "content": str(m.get("content", ""))[:4000]})
            if m.get("reasoning_content"):
                out[-1]["reasoning_content"] = str(m["reasoning_content"])[:50000]
        else:
            text = str(m.get("content", ""))[:4000].replace("</client_data>", "")
            out.append({"role": "user", "content": f"<client_data>{text}</client_data>"})
    return out


@router.post("/chat")
async def post_chat(body: ChatBody, authorization: str = Header(None)):
    gate = "may_chat" if body.mode == "learn" else "may_collect_details"
    j, open_ = _client_journey(authorization, gate)          # who is asking comes first (401/403)
    if not firm.switch("ai_chat"):
        return JSONResponse(status_code=503, content={"error": "ai_chat_off"})
    if body.mode not in ("learn", "intake"):
        raise HTTPException(422, "unsupported mode")
    _ch = characters.get(body.character)
    if body.character not in PERSONAS["characters"] or _ch is None or not _ch["enabled"]:
        raise HTTPException(422, "unknown character")
    if body.mode == "learn" and not db.query("SELECT id FROM content_lessons WHERE id = ?", (body.lesson_id or "",)):
        raise HTTPException(404, "lesson not found")
    if body.mode == "intake" and body.group not in GROUPS:
        raise HTTPException(422, "unknown group")
    if not open_:
        return JSONResponse(status_code=409, content={"error": "gate", "missing": [gate]})
    lang = "en" if body.lang == "en" else "es"

    current = _current(j, body.group) if body.mode == "intake" else None
    if body.mode == "intake" and current is None:
        return _reply(j, body, lang, text="", history="", reasoning=None, question=None)
    system = system_prompt(body.character, body.lesson_id, lang) if body.mode == "learn" else intake_prompt(body.character, current, lang)
    try:
        completion = await model_client().complete(system=system, messages=_messages(body.messages), max_tokens=400,
                                                   purpose=f"aprende_chat_{body.mode}", temperature=0.4)
    except ModelError:
        raise HTTPException(503, UNAVAILABLE)

    raw = completion.text or ""
    if _breaks_rules(DONE.sub(" ", TAG.sub(" ", raw))):
        raise HTTPException(503, UNAVAILABLE)
    # Tags come off before the spoken() guard, which stops at the first "?" and could cut a tag in half.
    asked = TAG.findall(raw)
    question = asked[-1].strip() if asked else None
    done = [d.strip() for d in DONE.findall(raw)]
    text = spoken(DONE.sub(" ", TAG.sub(" ", raw))).strip()
    history = text + (f" [ATTORNEY_QUESTION: {question}]" if question else "")
    if question:
        db.execute("INSERT INTO attorney_questions (id, journey_id, question, lesson_id, character, created_at) "
                   "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (journey_id, question) DO NOTHING",
                   (str(uuid.uuid4()), j["id"], question, body.lesson_id or body.group, body.character, journey._now_iso()))
    if current and current["id"] in done:
        # The answer is the client's own words for this question, never the character's.
        words = [str(m.get("content", "")).strip() for m in body.messages
                 if m.get("role") != "assistant" and m.get("question_id") == current["id"]]
        if any(words):
            datos.save(j, current["id"], answer="\n\n".join(w for w in words if w))
            history += f" [DONE: {current['id']}]"
    return _reply(j, body, lang, text=text, history=history, reasoning=completion.reasoning, question=question)


def _reply(j, body, lang, *, text, history, reasoning, question):
    out = {"text": text, "history": history, "reasoning": reasoning, "docs": body.docs,
           "attorney_question": question is not None, "covered": [], "open": [], "next_question": None}
    if body.mode == "intake":
        j = journey.get_journey(j["id"])
        d = datos.get_datos(j, lang)
        out["covered"] = [q["id"] for q in d["questions"] if q["status"] != "open"]     # from the server only: it only grows
        out["open"] = d["open"]
        nxt = _current(j, body.group)
        if nxt:
            live = content.live_entries("datos")
            body = live.get("datos:" + nxt["id"], {"es": nxt["es"], "en": nxt["en"]})
            out["next_question"] = {"id": nxt["id"], "text": body[lang]}
        else:
            out["next_question"] = None
    return out


@router.get("/chat/attorney-questions")
def list_attorney_questions(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    backend_app.require_auth(authorization, {"paralegal", "attorney", "admin"})
    rows = db.query("SELECT id, journey_id, question, lesson_id, character, created_at FROM attorney_questions "
                    "ORDER BY created_at DESC")
    return [dict(zip(("id", "journey_id", "question", "lesson_id", "character", "created_at"), r)) for r in rows]
