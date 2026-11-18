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

from aprende.consent import classify

HERE = os.path.dirname(os.path.abspath(__file__))
PHRASES = json.load(open(os.path.join(HERE, "fixtures", "consent_phrases.json"), encoding="utf-8"))
EXPECT = {"yes": "yes", "no": "no", "unclear": None}


@pytest.mark.parametrize("kind,text", [(k, t) for k, ts in PHRASES.items() for t in ts])
def test_consent_phrase_table(kind, text):
    assert classify(text) == EXPECT[kind], text


def test_a_refusal_wins_over_a_yes_word_in_the_same_answer():
    assert classify("No, no acepto") == "no"     # the prototype's original bug: "acepto" was read as yes


def test_the_consent_event_keeps_only_the_answer():
    h = client()
    send(h, "ai_disclosed")
    r = send(h, "consent", answer="no", text="No, no acepto. Me llamo Ana Torres.")
    assert r.status_code == 200, r.text
    rows = db.query("SELECT payload_json FROM journey_events WHERE journey_id = ? AND type = 'consent'", (r.json()["id"],))
    assert [json.loads(p[0]) for p in rows] == [{"answer": "no"}]


def test_after_a_refusal_nothing_personal_can_be_sent():
    h = client()
    send(h, "ai_disclosed")
    send(h, "consent", answer="no")
    r = send(h, "names_submitted", names=["Ana Torres"])
    assert r.status_code == 409 and r.json()["missing"] == ["may_name"]
    assert state(h)["gates"]["may_chat"] is False


def test_a_refusal_can_be_changed_later():
    h = client()
    send(h, "ai_disclosed")
    send(h, "consent", answer="no")
    assert send(h, "consent", answer="yes").status_code == 200
    assert state(h)["gates"]["may_name"] is True


def _i18n(lang):
    return json.load(open(os.path.join(HERE, "..", "aprende", "i18n", f"{lang}.json"), encoding="utf-8"))


def test_the_disclosure_says_ai_program_not_the_attorney_not_a_person():
    es, en = _i18n("es"), _i18n("en")
    d_es = es["gate.disclosure.calavera"].lower()
    for words in ("programa de inteligencia artificial", "no soy el abogado", "ni una persona", "información general",
                  "no asesoría legal"):
        assert words in d_es
    d_en = en["gate.disclosure.calavera"].lower()
    for words in ("artificial intelligence program", "not the attorney", "not a person", "general information",
                  "not legal advice"):
        assert words in d_en
    for key, text in {**es, **en}.items():
        if key.startswith("gate."):
            assert "con su imagen" not in text.lower() and "his likeness" not in text.lower()
