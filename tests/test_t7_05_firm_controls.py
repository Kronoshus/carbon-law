"""T7-05 acceptance tests, written by Opus (t7-tests) before the code. Contract: docs/tickets/T7-05.md (firm.py,
routes_firm.py, retention.py, the AI chat and extension switches). Do not weaken these tests."""
import datetime
import json
import os
import sys
import tempfile
import uuid
from zoneinfo import ZoneInfo

os.environ.setdefault("DATABASE_URL", "")
os.environ.setdefault("CARBON_DB_PATH", tempfile.mktemp(suffix=".db"))
sys.path.insert(0, "backend")

import pytest
from fastapi.testclient import TestClient

import app as backend
import db
import migrate
from ai.stub import StubClient
from aprende import chat as chatmod
from aprende import content, datos, jobs, journey, learn

migrate.run()
c = TestClient(backend.app)
HERE = os.path.dirname(os.path.abspath(__file__))
LA = ZoneInfo("America/Los_Angeles")
EXT = "chrome-extension://aprendet705testextensionid"
if EXT not in backend._cors_origins:          # what APRENDE_EXTENSION_ORIGIN does in production
    backend._cors_origins.append(EXT)

PARA, ATT, ADMIN = "t705-para@example.com", "t705-att@example.com", "t705-admin@example.com"
PW = "t705-password-1"
for _em, _role in ((PARA, "paralegal"), (ATT, "attorney"), (ADMIN, "admin")):
    backend.users[_em] = {"id": str(uuid.uuid4()), "name": _em.split("@")[0], "email": _em, "role": _role,
                          "password_hash": backend.hash_pw(PW), "created_at": datetime.datetime.utcnow().isoformat()}

# the learning tests' lessons (lw, lt, la, lp, lf, lb), published once per test database
_bundle = content.load_dir(os.path.join(HERE, "fixtures", "learn"))
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
    j = send(h, "names_submitted", names=["Ana Torres", "Luis Torres"]).json()
    journey.apply(j["id"], "conflict_auto", {"result": "clear"}, actor="system")
    return j["id"]


def put(body, who=ATT):
    return c.put("/staff/firm-settings", json=body, headers=login(who))


@pytest.fixture
def restore():
    """Every test leaves the firm's settings as it found them (the settings are shared by every test file)."""
    yield
    put({"switches": {"voice_recording": True, "ai_chat": True, "extension": True},
         "retention": {"unpaid_personal_data_days": 365}, "lessons_per_day": 1})


@pytest.fixture
def stub(monkeypatch):
    s = StubClient(text="Un albacea es la persona que cumple su testamento.", reasoning=None)
    monkeypatch.setattr(chatmod, "model_client", lambda: s)
    return s


def test_firm_settings_are_staff_only_and_only_attorney_or_admin_change_them(restore):
    assert c.get("/staff/firm-settings").status_code == 401
    assert c.get("/staff/firm-settings", headers=client()).status_code == 403
    got = c.get("/staff/firm-settings", headers=login(PARA))
    assert got.status_code == 200, got.text
    assert set(got.json()) == {"availability", "holidays", "retention", "switches", "lessons_per_day"}
    assert set(got.json()["switches"]) == {"voice_recording", "ai_chat", "extension"}
    assert c.put("/staff/firm-settings", json={"lessons_per_day": 2}).status_code == 401
    assert c.put("/staff/firm-settings", json={"lessons_per_day": 2}, headers=client()).status_code == 403
    assert put({"lessons_per_day": 2}, PARA).status_code == 403
    r = put({"lessons_per_day": 2}, ADMIN)
    assert r.status_code == 200 and r.json()["lessons_per_day"] == 2
    r = put({"switches": {"voice_recording": False}}, ATT)
    assert r.status_code == 200
    assert r.json()["switches"] == {"voice_recording": False, "ai_chat": True, "extension": True}   # partial update


def test_one_place_shows_the_existing_hours_and_holidays(restore):
    hours = {"hours": {"mon": [["09:00", "17:00"]], "tue": [["09:00", "12:00"]]}, "slot_minutes": {"signing": 60, "consultation": 30}}
    assert c.put("/staff/availability", json=hours, headers=login(PARA)).status_code == 200
    before = c.get("/staff/firm-settings", headers=login(PARA)).json()["holidays"]
    dates = sorted(set(before) | {"2026-12-25", "2027-01-01"})
    assert c.put("/staff/holidays", json={"dates": dates}, headers=login(PARA)).status_code == 200
    got = c.get("/staff/firm-settings", headers=login(PARA)).json()
    assert got["availability"] == hours
    assert sorted(got["holidays"]) == dates
    assert db.query("SELECT value_json FROM settings WHERE key = 'holidays'")[0][0] == json.dumps(dates)  # the one list


def test_holidays_and_hours_keep_their_own_routes(restore):
    for body in ({"holidays": ["2026-12-24"]}, {"availability": {"hours": {}, "slot_minutes": {}}}):
        r = put(body)
        assert r.status_code == 422, body


@pytest.mark.parametrize("body", [
    {"lessons_per_day": 0}, {"lessons_per_day": 5}, {"lessons_per_day": "dos"},
    {"switches": {"karaoke": True}}, {"switches": {"ai_chat": "no"}},
    {"retention": {"unpaid_personal_data_days": 0}}, {"retention": {"unpaid_personal_data_days": 7}},
    {"retention": {"audio_forever": 1}}, {"colour": "red"},
])
def test_bad_values_are_refused(restore, body):
    before = c.get("/staff/firm-settings", headers=login(PARA)).json()
    assert put(body).status_code == 422, body
    assert c.get("/staff/firm-settings", headers=login(PARA)).json() == before


def test_ai_chat_off_gives_503_and_lessons_still_work(restore, stub):
    h = client()
    cleared(h)
    body = {"mode": "learn", "character": "calavera", "lesson_id": "lw", "messages": [{"role": "user", "content": "¿Qué es un albacea?"}]}
    assert c.post("/chat", json=body, headers=h).status_code == 200                   # on: chat answers
    calls = len(stub.calls)
    assert put({"switches": {"ai_chat": False}}).status_code == 200
    r = c.post("/chat", json=body, headers=h)
    assert r.status_code == 503 and r.json() == {"error": "ai_chat_off"}
    r = c.post("/chat", json={"mode": "intake", "character": "calavera", "group": "will", "messages": []}, headers=h)
    assert r.status_code == 503 and r.json() == {"error": "ai_chat_off"}
    assert len(stub.calls) == calls                                                   # the model was never called
    assert c.post("/chat", json=body).status_code == 401                              # who asks still comes first
    assert c.get("/learn/map", headers=h).status_code == 200
    lesson = c.get("/learn/lessons/lw?lang=es", headers=h)
    assert lesson.status_code == 200
    item = next(it for s in lesson.json()["steps"] for it in s["items"] if it["kind"] == "truefalse")
    assert c.post("/learn/attempts", json={"item_id": item["id"], "answer": False}, headers=h).status_code == 200
    assert c.get("/datos", headers=h).status_code == 200
    assert put({"switches": {"ai_chat": True}}).status_code == 200
    assert c.post("/chat", json=body, headers=h).status_code == 200


def test_extension_off_refuses_the_extension_origin_only(restore):
    h = client()
    ext = {**h, "Origin": EXT}
    assert c.get("/journey", headers=ext).status_code == 200
    assert put({"switches": {"extension": False}}).status_code == 200
    r = c.get("/journey", headers=ext)
    assert r.status_code == 503 and r.json() == {"error": "extension_off"}
    assert r.headers.get("access-control-allow-origin") == EXT                       # the extension can read why
    other = c.get("/learn/map", headers={**h, "Origin": "chrome-extension://someotherextension"})
    assert other.status_code == 503
    r = c.post("/auth/login", json={"email": PARA, "password": PW}, headers={"Origin": EXT})
    assert r.status_code == 503                                                       # not only Aprende routes
    assert c.get("/settings/public", headers={"Origin": EXT}).status_code == 503
    assert c.get("/health", headers={"Origin": EXT}).status_code == 200
    assert c.get("/journey", headers=h).status_code == 200                            # the web app is untouched
    assert c.get("/journey", headers={**h, "Origin": "https://carbon.bailment.tech"}).status_code == 200
    assert put({"switches": {"extension": True}}).status_code == 200
    assert c.get("/journey", headers=ext).status_code == 200


def test_public_settings_show_the_switches(restore):
    r = c.get("/settings/public")
    assert r.status_code == 200 and r.json() == {"switches": {"voice_recording": True, "ai_chat": True, "extension": True}}
    put({"switches": {"voice_recording": False, "ai_chat": False}})
    assert c.get("/settings/public").json() == {"switches": {"voice_recording": False, "ai_chat": False, "extension": True}}


def answer_all(h, lid):
    lesson = c.get(f"/learn/lessons/{lid}?lang=es", headers=h).json()
    for step in lesson["steps"]:
        for it in step["items"]:
            if it["kind"] == "explain":
                continue
            a = {"choice": 2, "truefalse": False, "match": {l["key"]: l["key"] for l in it.get("left", [])},
                 "order": ["0", "1", "2"]}[it["kind"]]
            assert c.post("/learn/attempts", json={"item_id": it["id"], "answer": a}, headers=h).status_code == 200
    return c.post(f"/learn/lessons/{lid}/complete", headers=h)


def test_lessons_per_day_is_enforced_by_the_server(restore, monkeypatch):
    t = {"now": datetime.datetime(2026, 12, 2, 10, 0, tzinfo=LA)}
    monkeypatch.setattr(learn, "now", lambda: t["now"])
    assert put({"lessons_per_day": 1}).status_code == 200
    h = client()
    assert answer_all(h, "lw").json()["completed"] is True
    assert c.get("/learn/lessons/lt?lang=es", headers=h).status_code == 409           # one a day: tomorrow
    assert put({"lessons_per_day": 2}).status_code == 200
    assert c.get("/learn/lessons/lt?lang=es", headers=h).status_code == 200           # the server reads it at once
    assert answer_all(h, "lt").json()["completed"] is True
    assert c.get("/learn/lessons/la?lang=es", headers=h).status_code == 409           # two today, the third waits
    t["now"] = datetime.datetime(2026, 12, 3, 0, 1, tzinfo=LA)
    assert c.get("/learn/lessons/la?lang=es", headers=h).status_code == 200


def _age(jid, days):
    """Make every trace of a journey `days` old (naive UTC ISO, as the app stores them)."""
    old = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).replace(tzinfo=None).isoformat()
    db.execute("UPDATE journeys SET started_at = ? WHERE id = ?", (old, jid))
    db.execute("UPDATE journey_events SET created_at = ? WHERE journey_id = ?", (old, jid))
    db.execute("UPDATE datos_answers SET updated_at = ? WHERE journey_id = ?", (old, jid))
    db.execute("UPDATE item_attempts SET created_at = ? WHERE journey_id = ?", (old, jid))


def _with_personal_data(days, paid=False):
    h = client()
    jid = cleared(h)
    j = journey.get_journey(jid)
    datos.save(j, "nombre", answer="Ana Torres")
    datos.save(j, "nombre", answer="Ana María Torres")                                 # a change keeps a datos_audit row
    db.execute("INSERT INTO attorney_questions (id, journey_id, question, lesson_id, character, created_at) VALUES (?, ?, ?, ?, ?, ?)",
               (str(uuid.uuid4()), jid, "¿Mi hijo puede ser albacea?", "will", "calavera", journey._now_iso()))
    if paid:
        journey.apply(jid, "paid", {}, actor="stripe")
    _age(jid, days)
    return jid


def _personal(jid):
    return tuple(db.query(f"SELECT COUNT(*) FROM {t} WHERE journey_id = ?", (jid,))[0][0]
                 for t in ("datos_answers", "datos_audit", "attorney_questions"))


def run_sweep():
    jobs.HANDLERS["retention_sweep"]({"payload": None})


def test_a_retention_change_takes_effect_at_the_next_sweep(restore):
    from aprende import retention  # noqa: F401  (registers the job)
    assert put({"retention": {"unpaid_personal_data_days": 365}}).status_code == 200
    old_unpaid = _with_personal_data(200)
    old_paid = _with_personal_data(200, paid=True)
    recent = _with_personal_data(10)
    run_sweep()
    assert _personal(old_unpaid) == (1, 1, 1)                                         # 200 days < 365: kept
    assert put({"retention": {"unpaid_personal_data_days": 180}}).status_code == 200
    assert _personal(old_unpaid) == (1, 1, 1)                                         # not before the sweep
    run_sweep()
    assert _personal(old_unpaid) == (0, 0, 0)
    assert _personal(old_paid) == (1, 1, 1)                                           # a client's file is the firm's
    assert _personal(recent) == (1, 1, 1)
    assert journey.get_journey(old_unpaid) is not None                                # the account and journey stay
    rows = [a for a in backend.audit if a["action"] == "retention_sweep" and a["entity_id"] == old_unpaid]
    assert len(rows) == 1 and rows[0]["actor"] == "retention"
    assert "Ana" not in rows[0]["detail"] and "albacea" not in rows[0]["detail"]
    assert retention.sweep(datetime.datetime.now(datetime.timezone.utc)) == {"journeys": 0}   # nothing left to sweep
    assert db.query("SELECT COUNT(*) FROM jobs WHERE kind = 'retention_sweep' AND status = 'pending'")[0][0] >= 1


def test_every_change_is_audited(restore):
    mark = len(backend.audit)
    put({"lessons_per_day": 2, "switches": {"ai_chat": False}})
    c.put("/staff/holidays", json={"dates": ["2026-12-25"]}, headers=login(PARA))
    c.put("/staff/availability", json={"hours": {"mon": [["09:00", "17:00"]]}, "slot_minutes": {"signing": 60}},
          headers=login(PARA))
    rows = [(a["actor"], a["action"], a["entity_id"]) for a in backend.audit[mark:] if a["action"] == "firm_settings"]
    assert sorted(rows) == sorted([(ATT, "firm_settings", "lessons_per_day"), (ATT, "firm_settings", "switches"),
                                   (PARA, "firm_settings", "holidays"), (PARA, "firm_settings", "availability")])
    mark = len(backend.audit)
    c.get("/staff/firm-settings", headers=login(PARA))
    put({"lessons_per_day": 5})                                                       # refused: nothing written
    assert [a for a in backend.audit[mark:] if a["action"] == "firm_settings"] == []
