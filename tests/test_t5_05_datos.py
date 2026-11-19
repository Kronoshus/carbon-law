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
from aprende import datos

HERE = os.path.dirname(os.path.abspath(__file__))
QUESTIONS = yaml.safe_load(open(os.path.join(HERE, "..", "aprende", "content", "datos.yaml"), encoding="utf-8"))
BY_ID = {q["id"]: q for q in QUESTIONS}


def cleared(h):
    send(h, "ai_disclosed")
    send(h, "consent", answer="yes")
    j = send(h, "names_submitted", names=["Ana Torres"]).json()
    journey.apply(j["id"], "conflict_auto", {"result": "clear"}, actor="system")
    return j["id"]


def get(h, lang="es"):
    r = c.get(f"/datos?lang={lang}", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def put(h, qid, **body):
    return c.put(f"/datos/{qid}", json=body, headers=h)


def applies(q, docs):
    return not q["docs"] or set(q["docs"]) & set(docs)


@pytest.fixture
def stub(monkeypatch):
    s = StubClient(text="")
    monkeypatch.setattr(chatmod, "model_client", lambda: s)
    return s


# --- the question list (Opus's content) ---

def test_the_question_list_is_complete_and_bilingual():
    ids = [q["id"] for q in QUESTIONS]
    assert len(ids) == len(set(ids))
    for q in QUESTIONS:
        assert q["es"].strip() and q["en"].strip()
        assert q["asked_after"] in ("will", "trust", "ahcd", "poa", "resumen")
        assert set(q["docs"]) <= {"will", "trust", "poa", "ahcd"}
    assert "contacto" in ids


def test_no_question_asks_about_immigration_status():
    for q in QUESTIONS:
        text = (q["es"] + " " + q["en"]).lower()
        for word in ("inmigra", "migratori", "papeles", "ciudadan", "immigration", "citizen", "green card", "visa"):
            assert word not in text, (q["id"], word)


# --- /datos ---

def test_details_wait_for_the_gates():
    h = client()
    send(h, "ai_disclosed"); send(h, "consent", answer="yes")                   # no names yet, so no conflict check
    assert c.get("/datos", headers=h).status_code == 409
    assert put(h, "nombre", answer="Ana Torres").status_code == 409
    assert c.get("/datos", headers=staff()).status_code == 403


def test_before_choosing_documents_every_question_applies():
    h = client()
    cleared(h)
    assert {q["id"] for q in get(h)["questions"]} == set(BY_ID)


def test_the_chosen_documents_decide_the_questions():
    h = client()
    cleared(h)
    send(h, "documents_tentative", codes=["will"])
    got = {q["id"] for q in get(h)["questions"]}
    assert got == {q["id"] for q in QUESTIONS if applies(q, ["will"])}
    assert "fid_tipo" not in got and "salud_agente" not in got and "nombre" in got
    send(h, "documents_confirmed", codes=["will", "ahcd"])                      # the confirmed choice wins
    assert "salud_agente" in {q["id"] for q in get(h)["questions"]}


def test_questions_come_in_the_clients_language():
    h = client()
    cleared(h)
    es = {q["id"]: q["text"] for q in get(h, "es")["questions"]}
    en = {q["id"]: q["text"] for q in get(h, "en")["questions"]}
    assert es["nombre"] == BY_ID["nombre"]["es"] and en["nombre"] == BY_ID["nombre"]["en"]


def test_answer_skip_and_validation():
    h = client()
    cleared(h)
    assert put(h, "nombre", answer="Ana María Torres").status_code == 200
    assert put(h, "nacimiento", skipped=True).status_code == 200
    qs = {q["id"]: q for q in get(h)["questions"]}
    assert qs["nombre"]["status"] == "answered" and qs["nombre"]["answer"] == "Ana María Torres"
    assert qs["nacimiento"]["status"] == "skipped" and qs["nacimiento"]["answer"] is None   # skipped, not empty
    assert put(h, "nombre", answer="   ").status_code == 422
    assert put(h, "no_such_question", answer="x").status_code == 404
    assert "nombre" not in get(h)["open"] and "nacimiento" not in get(h)["open"]


def test_editing_an_answer_keeps_an_audit_entry():
    h = client()
    jid = cleared(h)
    put(h, "domicilio", answer="Los Ángeles")
    put(h, "domicilio", answer="Boyle Heights, Los Ángeles")
    assert {q["id"]: q for q in get(h)["questions"]}["domicilio"]["answer"] == "Boyle Heights, Los Ángeles"
    rows = db.query("SELECT old_answer, new_answer FROM datos_audit WHERE journey_id = ? AND question_id = 'domicilio' "
                    "ORDER BY at", (jid,))
    assert [tuple(r) for r in rows][-1] == ("Los Ángeles", "Boyle Heights, Los Ángeles")


def test_finishing_the_intake_earns_the_fifth_discount_once():
    h = client()
    jid = cleared(h)
    send(h, "documents_tentative", codes=["will"])
    todo = [q["id"] for q in QUESTIONS if applies(q, ["will"])]
    for qid in todo[:-1]:
        put(h, qid, answer="respuesta")
    assert get(h)["completed"] is False
    assert "intake_completed" not in state(h)["facts"]
    put(h, todo[-1], skipped=True)
    assert get(h)["completed"] is True and get(h)["open"] == []
    assert "intake_completed" in state(h)["facts"]
    put(h, todo[0], answer="otra respuesta")                                   # an edit after finishing
    events = db.query("SELECT COUNT(*) FROM journey_events WHERE journey_id = ? AND type = 'intake_completed'", (jid,))
    assert events[0][0] == 1
    q = c.get("/payments/quote?codes=will", headers=h).json()
    assert "intake_completed" in [d["event"] for d in q["items"][0]["discounts"]]


# --- intake chat ---

def ask(h, group, turns, character="calavera"):
    return c.post("/chat", json={"mode": "intake", "character": character, "group": group, "messages": turns}, headers=h)


def test_intake_chat_waits_for_the_gates(stub):
    h = client()
    send(h, "ai_disclosed"); send(h, "consent", answer="yes")
    r = ask(h, "will", [{"role": "user", "content": "hola"}])
    assert r.status_code == 409 and stub.calls == []


def test_the_character_asks_the_first_open_question_of_the_lesson(stub):
    h = client()
    cleared(h)
    put(h, "nombre", answer="Ana Torres")
    stub.text = "Gracias. " + BY_ID["nacimiento"]["es"]
    r = ask(h, "will", []).json()
    assert r["next_question"]["id"] == "nacimiento"
    assert BY_ID["nacimiento"]["es"] in stub.calls[-1]["system"]
    assert "</client_data>" not in stub.calls[-1]["system"]                    # no client words in the instructions


def test_an_answer_marked_done_is_saved_from_the_clients_words(stub):
    h = client()
    cleared(h)
    stub.text = "Muchas gracias, Ana. [DONE: nombre]"
    turns = [{"role": "assistant", "content": BY_ID["nombre"]["es"]},
             {"role": "user", "content": "Ana María Torres", "question_id": "nombre"},
             {"role": "assistant", "content": "¿Cómo se escribe su segundo apellido?"},
             {"role": "user", "content": "Torres con dos erres", "question_id": "nombre"}]
    r = ask(h, "will", turns).json()
    assert "DONE" not in r["text"] and "[DONE: nombre]" in r["history"]
    assert "nombre" in r["covered"] and r["next_question"]["id"] == "nacimiento"
    saved = {q["id"]: q for q in get(h)["questions"]}["nombre"]
    assert saved["status"] == "answered"
    assert "Ana María Torres" in saved["answer"] and "Torres con dos erres" in saved["answer"]
    assert "segundo apellido" not in saved["answer"]                            # only the client's words


def test_a_client_who_wanders_is_steered_back_and_nothing_is_marked(stub):
    h = client()
    cleared(h)
    stub.text = "Entiendo. Volvamos a su testamento: " + BY_ID["nombre"]["es"]
    r = ask(h, "will", [{"role": "user", "content": "¿Va a llover mañana?", "question_id": "nombre"}]).json()
    assert r["covered"] == [] and r["next_question"]["id"] == "nombre"
    assert {q["id"]: q for q in get(h)["questions"]}["nombre"]["status"] == "open"


def test_covered_only_grows(stub):
    h = client()
    cleared(h)
    put(h, "nombre", answer="Ana Torres")
    stub.text = "Bien."                                                         # no DONE tag at all
    r = ask(h, "will", [{"role": "user", "content": "1960", "question_id": "nacimiento"}]).json()
    assert "nombre" in r["covered"]


def test_done_for_a_question_outside_this_lesson_is_ignored(stub):
    h = client()
    cleared(h)
    stub.text = "Gracias. [DONE: salud_agente]"
    ask(h, "will", [{"role": "user", "content": "Mi hija Sofía", "question_id": "nombre"}])
    assert {q["id"]: q for q in get(h)["questions"]}["salud_agente"]["status"] == "open"


def test_a_finished_lesson_group_needs_no_model_call(stub):
    h = client()
    cleared(h)
    for q in QUESTIONS:
        if q["asked_after"] == "poa":
            put(h, q["id"], skipped=True)
    r = ask(h, "poa", []).json()
    assert r["next_question"] is None and stub.calls == []


def test_the_client_cannot_mark_questions_answered(stub):
    h = client()
    cleared(h)
    stub.text = "Bien."
    r = c.post("/chat", json={"mode": "intake", "character": "calavera", "group": "will", "covered": ["nombre", "hijos"],
                              "messages": [{"role": "user", "content": "hola", "question_id": "nombre"}]}, headers=h).json()
    assert r["covered"] == [] and r["next_question"]["id"] == "nombre"


def test_each_character_speaks_with_its_own_persona(stub):
    h = client()
    cleared(h)
    stub.text = "Gracias."
    ask(h, "ahcd", [], character="oso")
    system = stub.calls[-1]["system"]
    assert "El Oso" in system and "No hay respuestas buenas ni malas" in system
    assert "Never ask about immigration status" in system
