"""The server never passes on a character reply that asks about immigration status or pitches an annuity, whatever the model says.

Found by the guardrail audit (~/work/cl-reports/audit-guardrails.md). Fictional people only. (Opus)"""
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
import db
import migrate
from aprende import conflicts, journey

migrate.run()
c = TestClient(backend.app)
PASSWORD = "audit-fix-password"
ATTORNEY = "audit-fix-attorney@example.com"
backend.users[ATTORNEY] = {"id": str(uuid.uuid4()), "name": "Audit Attorney", "email": ATTORNEY, "role": "attorney",
                           "password_hash": backend.hash_pw(PASSWORD), "created_at": datetime.datetime.utcnow().isoformat()}


def login(email):
    return {"Authorization": "Bearer " + c.post("/auth/login", json={"email": email, "password": PASSWORD}).json()["token"]}


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


def consented(h, names=("Ana Torres",)):
    send(h, "ai_disclosed"); send(h, "consent", answer="yes")
    r = send(h, "names_submitted", names=list(names))
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture
def firm_list():
    """The firm's conflict list for one test; the list in force before is put back afterwards."""
    before = conflicts.get_list()
    yield lambda *names: conflicts.replace_list("name\n" + "\n".join(names) + "\n") if names else conflicts.delete_list()
    conflicts.replace_list("name\n" + "\n".join(before) + "\n") if before else conflicts.delete_list()

import re

from ai import Completion
from aprende import chat as chatmod


IMMIGRATION = re.compile(r"inmigra|migratori|ciudadan|indocumentad|green card|tarjeta verde|\bvisas?\b|immigra|citizen|"
                         r"undocumented|residencia permanente|permanent resident", re.I)
SELLING = re.compile(r"\bcompre\b|cómprel|buy now|\boferta|limited time|tiempo limitado|aprovech|hurry|apúrese|"
                     r"no se lo pierda|don't miss|last chance|última oportunidad|act now", re.I)
PRODUCT = re.compile(r"anualidad|annuit", re.I)
TRUST = re.compile(r"fideicomiso|trust", re.I)
INSURANCE = re.compile(r"seguros? de vida|insurance|anualidad|annuit", re.I)




class StubModel:
    model = "stub-model"

    def __init__(self, text=""):
        self.text, self.calls = text, []

    async def complete(self, system, messages, max_tokens, *, purpose, temperature=None):
        self.calls.append({"system": system, "messages": messages, "purpose": purpose})
        return Completion(text=self.text, reasoning=None, usage={}, latency_ms=0)


@pytest.fixture
def model(monkeypatch):
    stub = StubModel()
    monkeypatch.setattr(chatmod, "model_client", lambda: stub)
    return stub


def chat_body(mode, text, **extra):
    body = {"mode": mode, "character": "calavera", "lang": "es", "group": "will",
            "messages": [{"role": "user", "content": text, "question_id": "nombre"}]}
    body.update(extra)
    return body


@pytest.mark.parametrize("reply", [
    "Gracias. ¿Cuál es su estatus migratorio?",
    "Antes de seguir, ¿usted es ciudadano o tiene green card?",
    "Thank you. Are you a US citizen?",
    "Para proteger a su familia le conviene una anualidad junto con su fideicomiso.",
    "A trust works best together with an annuity.",
])
def test_a_model_reply_that_breaks_the_rules_never_reaches_the_client(reply, model, firm_list):
    """The persona prompt is the first line; the server must not pass on a reply that asks about immigration status or
    pitches an annuity even if the model ignores it (nothing is said, nothing is stored)."""
    firm_list()
    h = client()
    jid = consented(h)
    journey.apply(jid, "conflict_auto", {"result": "clear"}, actor="system")
    model.text = reply
    r = c.post("/chat", json=chat_body("intake", "Ana Torres"), headers=h)
    said = r.json().get("text", "") + r.json().get("history", "") if r.status_code == 200 else r.text
    assert not IMMIGRATION.search(said) and not PRODUCT.search(said), said


@pytest.mark.parametrize("reply", [
    "Esa es una pregunta para el abogado Raval. Ya se la anoté y él le responde. "
    "[ATTORNEY_QUESTION: No tengo papeles ni green card. ¿Eso es un problema para mi testamento?]",
    "Gracias. Su pregunta sobre inmigración es para el abogado Raval. ¿Cuál es su nombre completo?",
    "Los seguros de vida se pagan a quien usted nombró en el formulario. ¿Tiene alguno?",
])
def test_a_reply_within_the_rules_still_reaches_the_client(reply, model, firm_list):
    firm_list()
    h = client()
    journey.apply(consented(h), "conflict_auto", {"result": "clear"}, actor="system")
    model.text = reply
    r = c.post("/chat", json=chat_body("intake", "No tengo papeles. ¿Eso es un problema?"), headers=h)
    assert r.status_code == 200 and r.json()["text"]
