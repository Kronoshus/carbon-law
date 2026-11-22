"""T7-03 acceptance tests, written by Opus (t7-tests) before the code. Contract: docs/tickets/T7-03.md (character host
rules, GET /staff/characters, unit validation, persona prompts as T7-01 content). Do not weaken these tests."""
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
import yaml
from fastapi.testclient import TestClient

import app as backend
import db
import migrate
from ai.stub import StubClient
from aprende import chat as chatmod
from aprende import content, journey

migrate.run()
c = TestClient(backend.app)
HERE = os.path.dirname(os.path.abspath(__file__))
SEED = yaml.safe_load(open(os.path.join(HERE, "..", "aprende", "content", "personas.yaml"), encoding="utf-8"))

PARA, ATT = "t703-para@example.com", "t703-att@example.com"
PW = "t703-password-1"
for _em, _role in ((PARA, "paralegal"), (ATT, "attorney")):
    backend.users[_em] = {"id": str(uuid.uuid4()), "name": _em.split("@")[0], "email": _em, "role": _role,
                          "password_hash": backend.hash_pw(PW), "created_at": datetime.datetime.utcnow().isoformat()}

_bundle = content.load_dir(os.path.join(HERE, "fixtures", "learn"))      # lw (unit will, host calavera, games by pinata)
if not db.query("SELECT id FROM content_lessons WHERE id = 'lw'"):
    content.import_bundle(_bundle, actor="opus")
for _l in _bundle["lessons"]:
    for _s in _l["steps"]:
        for _it in _s["items"]:
            if _it.get("legal"):
                content.approve(_it["id"], attorney="attorney@example.com")
            content.publish(_it["id"], actor="paralegal@example.com")


def login(em):
    return {"Authorization": "Bearer " + c.post("/auth/login", json={"email": em, "password": PW}).json()["token"]}


def client():
    r = c.post("/auth/signup", json={"name": "Ana Torres", "email": f"ana-{uuid.uuid4().hex[:8]}@example.com",
                                     "password": "long-secure-password", "source": "aprende", "adult": True})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def send(h, type_, **payload):
    return c.post("/journey/events", json={"type": type_, "payload": payload}, headers=h)


def cleared(h):
    send(h, "ai_disclosed")
    send(h, "consent", answer="yes")
    jid = send(h, "names_submitted", names=["Ana Torres"]).json()["id"]
    journey.apply(jid, "conflict_auto", {"result": "clear"}, actor="system")


@pytest.fixture(autouse=True)
def restore_characters():
    before = db.query("SELECT id, enabled, units_json FROM characters")
    yield
    for cid, enabled, units in before:
        db.execute("UPDATE characters SET enabled = ?, units_json = ? WHERE id = ?", (enabled, units, cid))


def patch(cid, body, who=PARA):
    return c.patch(f"/characters/{cid}", json=body, headers=login(who))


def lesson(h, lid="lw"):
    r = c.get(f"/learn/lessons/{lid}?lang=es", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def item_characters(les):
    return {it["id"]: it.get("character") for s in les["steps"] for it in s["items"]}


def map_character(h, lid="lw"):
    m = c.get("/learn/map", headers=h).json()
    return next(l["character"] for u in m["units"] for l in u["lessons"] if l["id"] == lid)


def test_the_staff_list_shows_every_character():
    assert patch("pinata", {"enabled": False}).status_code == 200
    r = c.get("/staff/characters", headers=login(PARA))
    assert r.status_code == 200, r.text
    rows = {x["id"]: x for x in r.json()}
    assert set(rows) >= {"calavera", "oso", "pinata"}
    assert rows["pinata"]["enabled"] is False and rows["calavera"]["enabled"] is True
    assert rows["calavera"]["name_key"] == "character.calavera.name"
    assert {"id", "name_key", "enabled", "units", "voice_es", "voice_en"} <= set(rows["oso"])
    assert "ahcd" in rows["oso"]["units"]
    assert c.get("/staff/characters", headers=client()).status_code == 403
    assert c.get("/staff/characters").status_code == 401


def test_turning_a_character_off_takes_effect_on_the_next_lesson_load():
    h = client()
    games = [i for i, ch in item_characters(lesson(h)).items() if ch == "pinata"]
    assert games, "the fixture lesson has Piñata's games"
    assert patch("pinata", {"enabled": False}).status_code == 200
    chars = item_characters(lesson(h))
    assert "pinata" not in chars.values()
    assert all(chars[i] == "calavera" for i in games)                                   # the lesson's host runs them
    assert "pinata" not in json.dumps(c.get("/learn/map", headers=h).json())
    assert patch("pinata", {"enabled": True}).status_code == 200
    assert all(item_characters(lesson(h))[i] == "pinata" for i in games)


def test_unit_assignment_takes_effect_on_the_next_lesson_load():
    h = client()
    assert lesson(h)["character"] == "calavera" and map_character(h) == "calavera"
    oso = next(x for x in c.get("/staff/characters", headers=login(PARA)).json() if x["id"] == "oso")
    assert patch("oso", {"units": oso["units"] + ["will"]}).status_code == 200
    assert lesson(h)["character"] == "oso" and map_character(h) == "oso"
    assert patch("oso", {"enabled": False}).status_code == 200                           # assigned but off: authored host
    assert lesson(h)["character"] == "calavera" and map_character(h) == "calavera"


def test_a_unit_has_one_host():
    oso = next(x for x in c.get("/staff/characters", headers=login(PARA)).json() if x["id"] == "oso")
    assert patch("oso", {"units": oso["units"] + ["trust"]}).status_code == 200
    rows = {x["id"]: x for x in c.get("/staff/characters", headers=login(PARA)).json()}
    assert "trust" in rows["oso"]["units"]
    assert [cid for cid, x in rows.items() if "trust" in x["units"]] == ["oso"]
    assert "will" in rows["calavera"]["units"]                                          # the other units stay


def test_unknown_units_are_refused():
    before = c.get("/staff/characters", headers=login(PARA)).json()
    assert patch("oso", {"units": ["ahcd", "cooking"]}).status_code == 422
    assert c.get("/staff/characters", headers=login(PARA)).json() == before


def test_a_disabled_character_cannot_chat(monkeypatch):
    stub = StubClient(text="¡Hola!", reasoning=None)
    monkeypatch.setattr(chatmod, "model_client", lambda: stub)
    h = client()
    cleared(h)
    body = {"mode": "learn", "character": "pinata", "lesson_id": "lw", "messages": [{"role": "user", "content": "Hola"}]}
    assert c.post("/chat", json=body, headers=h).status_code == 200
    patch("pinata", {"enabled": False})
    assert c.post("/chat", json=body, headers=h).status_code == 422
    assert len(stub.calls) == 1


def forget(entry_id):
    db.execute("DELETE FROM content_versions WHERE entry_id = ?", (entry_id,))
    db.execute("DELETE FROM content_approvals WHERE item_id = ?", (entry_id,))


def draft(eid, body, who=PARA):
    return c.put(f"/staff/content/{eid}/draft", json={"body": body}, headers=login(who))


def submit(eid, who=PARA):
    return c.post(f"/staff/content/{eid}/submit", headers=login(who))


def test_persona_entries_are_listed_and_need_the_attorney():
    r = c.get("/staff/content?kind=persona", headers=login(PARA))
    assert r.status_code == 200, r.text
    rows = {e["entry_id"]: e for e in r.json()["entries"]}
    assert set(rows) == {"persona:shared", "persona:modes.learn", "persona:modes.intake",
                         "persona:characters.calavera", "persona:characters.oso", "persona:characters.pinata"}
    assert all(e["legal"] is True and e["live_version"] == 0 for e in rows.values())
    d = c.get("/staff/content/persona:characters.oso", headers=login(PARA)).json()
    assert d["live"]["body"] == {"name": SEED["characters"]["oso"]["name"], "persona": SEED["characters"]["oso"]["persona"]}
    assert c.get("/staff/content/persona:shared", headers=login(PARA)).json()["live"]["body"] == {"text": SEED["shared"]}


def test_a_persona_edit_reaches_the_character_only_after_approval(monkeypatch):
    stub = StubClient(text="Un albacea cumple el testamento.", reasoning=None)
    monkeypatch.setattr(chatmod, "model_client", lambda: stub)
    h = client()
    cleared(h)
    body = {"mode": "learn", "character": "calavera", "lesson_id": "lw", "messages": [{"role": "user", "content": "¿Qué es un albacea?"}]}
    eid = "persona:characters.calavera"
    marker = "You are La Calavera, and you always mention the marigolds (t703 marker)."
    try:
        assert draft(eid, {"name": SEED["characters"]["calavera"]["name"], "persona": marker}).status_code == 200
        assert submit(eid).status_code == 200
        r = c.post(f"/staff/content/{eid}/publish", json={"version": 1}, headers=login(PARA))
        assert r.status_code == 403 and r.json()["error"] == "attorney_approval_required"
        assert c.post("/chat", json=body, headers=h).status_code == 200
        assert marker not in stub.calls[-1]["system"]
        assert SEED["characters"]["calavera"]["persona"].strip()[:60] in stub.calls[-1]["system"]
        assert c.post(f"/staff/content/{eid}/approve", json={"version": 1}, headers=login(ATT)).status_code == 200
        assert c.post("/chat", json=body, headers=h).status_code == 200
        assert marker in stub.calls[-1]["system"]
        assert SEED["characters"]["calavera"]["persona"].strip()[:60] not in stub.calls[-1]["system"]
    finally:
        forget(eid)


@pytest.mark.parametrize("eid,text,missing", [
    ("persona:modes.learn", "Help with the lesson. Use only what you were given.", ["{explanations}"]),
    ("persona:modes.intake", "Ask the question {question}.", ["{question_id}"]),
    ("persona:shared", "You are a character in the app. Speak {language}.", ["{name}"]),
])
def test_persona_placeholders_must_stay(eid, text, missing):
    try:
        assert draft(eid, {"text": text}).status_code == 200
        r = submit(eid)
        assert r.status_code == 422 and r.json() == {"error": "placeholders", "missing": missing}
    finally:
        forget(eid)


def test_character_names_need_both_languages():
    eid = "persona:characters.oso"
    try:
        assert draft(eid, {"name": {"es": "El Oso", "en": ""}, "persona": SEED["characters"]["oso"]["persona"]}).status_code == 200
        r = submit(eid)
        assert r.status_code == 422 and r.json() == {"error": "languages", "missing": ["en"]}
        assert draft(eid, {"name": {"es": "El Oso", "en": "El Oso"}, "persona": " "}).status_code == 200
        assert submit(eid).status_code == 422
        assert draft(eid, {"name": {"es": "El Oso", "en": "El Oso"}, "persona": "Calm.", "voice": "x"}).status_code == 422
    finally:
        forget(eid)
