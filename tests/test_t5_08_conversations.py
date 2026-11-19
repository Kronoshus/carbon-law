import datetime
import json
import os
import sys
import tempfile
import uuid

os.environ.setdefault("DATABASE_URL", "")
os.environ.setdefault("CARBON_DB_PATH", tempfile.mktemp(suffix=".db"))
sys.path.insert(0, "backend")

import pytest
from fastapi.testclient import TestClient

import app as backend
import migrate
import db
from aprende import journey

migrate.run()
c = TestClient(backend.app)

STAFF_EMAIL = "p5-staff@example.com"
backend.users[STAFF_EMAIL] = {"id": str(uuid.uuid4()), "name": "P5 Staff", "email": STAFF_EMAIL, "role": "paralegal",
                              "password_hash": backend.hash_pw("p5-staff-password"),
                              "created_at": datetime.datetime.utcnow().isoformat()}


def staff():
    token = c.post("/auth/login", json={"email": STAFF_EMAIL, "password": "p5-staff-password"}).json()["token"]
    return {"Authorization": "Bearer " + token}


def client():
    body = {"name": "Ana Torres", "email": f"ana-{uuid.uuid4().hex[:8]}@example.com", "password": "long-secure-password",
            "source": "aprende", "adult": True}
    r = c.post("/auth/signup", json=body)
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def send(h, type_, **payload):
    return c.post("/journey/events", json={"type": type_, "payload": payload}, headers=h)


def state(h):
    r = c.get("/journey", headers=h)
    assert r.status_code == 200, r.text
    return r.json()

import yaml

from ai.stub import StubClient
from aprende import chat as chatmod
from aprende import content

HERE = os.path.dirname(os.path.abspath(__file__))
SET = yaml.safe_load(open(os.path.join(HERE, "fixtures", "conversations.yaml"), encoding="utf-8"))
CONVS = SET["conversations"]

_bundle = content.load_dir(os.path.join(os.path.dirname(HERE), "aprende", "content"))
if not db.query("SELECT id FROM content_lessons WHERE id = 'will'"):
    content.import_bundle(_bundle, actor="opus")
    for _l in _bundle["lessons"]:
        for _s in _l["steps"]:
            for _it in _s["items"]:
                if _it.get("legal"):
                    content.approve(_it["id"], attorney="attorney@example.com")
                content.publish(_it["id"], actor="paralegal@example.com")


def cleared():
    h = client()
    send(h, "ai_disclosed"); send(h, "consent", answer="yes")
    j = send(h, "names_submitted", names=["Ana Torres"]).json()
    journey.apply(j["id"], "conflict_auto", {"result": "clear"}, actor="system")
    return h, j["id"]


def bad_reply(conv, turn):
    """A model reply that breaks every rule the server itself can enforce."""
    return (f"Claro. [ATTORNEY_QUESTION: {turn}] [DONE: salud_agente] " + "Repito esto muchas veces. " * 30 +
            "¿Primera pregunta? ¿Segunda pregunta? ¿Tercera?")


def test_the_set_is_complete():
    assert len(CONVS) == 40 and sum(c["lang"] == "es" for c in CONVS) == 20
    names = set(SET["rubric"])
    for c in CONVS:
        assert set(c["must"]) | set(c["never"]) <= names, c["id"]


@pytest.mark.parametrize("conv", CONVS, ids=[c["id"] for c in CONVS])
def test_the_servers_guards_hold_for_every_conversation(conv, monkeypatch):
    h, jid = cleared()
    stub = StubClient()
    monkeypatch.setattr(chatmod, "model_client", lambda: stub)
    history = []
    for turn in conv["turns"]:
        stub.text = bad_reply(conv, turn)
        history.append({"role": "user", "content": turn, "question_id": "nombre"})
        body = {"mode": conv["mode"], "character": conv["character"], "lang": conv["lang"], "messages": history}
        body.update({"lesson_id": conv["lesson_id"]} if conv["mode"] == "learn" else {"group": conv["group"]})
        r = c.post("/chat", json=body, headers=h)
        assert r.status_code == 200, r.text
        out = r.json()
        assert "[" not in out["text"] and "ATTORNEY_QUESTION" not in out["text"] and "DONE" not in out["text"]
        assert out["text"].count("?") <= 1                                           # one question per turn
        assert len(out["text"].split()) <= 220
        assert turn not in stub.calls[-1]["system"]                                  # the client's words never become instructions
        assert all(m["content"].startswith("<client_data>") for m in stub.calls[-1]["messages"] if m["role"] == "user")
        history.append({"role": "assistant", "content": out["history"], "reasoning_content": out["reasoning"]})
    saved = db.query("SELECT question_id FROM datos_answers WHERE journey_id = ?", (jid,))
    assert ("salud_agente",) not in [tuple(s) for s in saved]                      # a DONE for another question saves nothing
    stored = db.query("SELECT COUNT(*) FROM attorney_questions WHERE journey_id = ?", (jid,))[0][0]
    assert stored == len(set(conv["turns"]))
