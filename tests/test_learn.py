"""T4-03 acceptance tests, written by Opus before the code (ticket ★). Contract (see the ticket and this file):

GET  /learn/map                     -> {"units": [{"id": unit, "lessons": [{"id", "day", "title", "character", "status", "unlock_at"}]}]}
                                       status: locked | available | done; only lessons with published items are listed
GET  /learn/lessons/{id}?lang=es    -> {"id", "title", "character", "sensitive", "steps": [{"id", "title", "items": [Item]}]}
     Item never contains the answer. choice/scenario/listen: options in authored order. truefalse: statement.
     match: {"left": [{"key", "text"}], "right": [{"key", "text"}] (shuffled)}; order: {"steps": [{"key", "text"}] (shuffled)}.
     key = the authored position as a string ("0", "1", ...).
POST /learn/attempts {"item_id", "answer"} -> {"correct", "explain", "source": {"kind","cite","url"} | null}
     answer: choice/scenario/listen int; truefalse bool; match {left_key: right_key}; order [keys in order]; explain items: no attempts (422)
POST /learn/lessons/{id}/complete   -> {"completed": bool, "score": float}; completes when every gradable item has been
     answered and >= 80% of their latest answers are correct; emits `lesson_completed:<unit>` once for will/trust/ahcd/poa.
Unlocking: the core lesson of day N is available from local midnight (journey tz) after the day N-1 lesson was completed
(setting lessons_per_day = 1); day 1 is available at once; bonus lessons once the day-1 lesson is done; the final lesson
(day 14) when the journey gate may_take_final_lesson is open. Time comes from `aprende.learn.now()` (tests patch it).
"""
import datetime
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
from aprende import content, journey, learn

HERE = os.path.dirname(os.path.abspath(__file__))
c = TestClient(backend.app)
LA = ZoneInfo("America/Los_Angeles")


def publish_fixture():
    b = content.load_dir(os.path.join(HERE, "fixtures", "learn"))
    content.import_bundle(b, actor="opus")
    for lesson in b["lessons"]:
        for step in lesson["steps"]:
            for it in step["items"]:
                if it.get("legal"):
                    content.approve(it["id"], attorney="attorney@example.com")
                content.publish(it["id"], actor="paralegal@example.com")


publish_fixture()


@pytest.fixture
def clock(monkeypatch):
    t = {"now": datetime.datetime(2026, 12, 2, 10, 0, tzinfo=LA)}       # a Wednesday morning in Los Angeles
    monkeypatch.setattr(learn, "now", lambda: t["now"])
    return t


def client():
    r = c.post("/auth/signup", json={"name": "Ana Torres", "email": f"ana-{uuid.uuid4().hex[:8]}@example.com",
                                     "password": "long-secure-password", "source": "aprende", "adult": True})
    return {"Authorization": "Bearer " + r.json()["token"]}


def lessons_of(h):
    m = c.get("/learn/map", headers=h)
    assert m.status_code == 200, m.text
    return {l["id"]: l for u in m.json()["units"] for l in u["lessons"]}


def answer_all(h, lid, right=True):
    lesson = c.get(f"/learn/lessons/{lid}?lang=es", headers=h).json()
    for step in lesson["steps"]:
        for it in step["items"]:
            if it["kind"] == "explain":
                continue
            a = {"choice": 2 if right else 0, "truefalse": False if right else True,
                 "match": {l["key"]: l["key"] for l in it.get("left", [])} if right else {l["key"]: "0" for l in it.get("left", [])},
                 "order": ["0", "1", "2"] if right else ["2", "1", "0"]}[it["kind"]]
            r = c.post("/learn/attempts", json={"item_id": it["id"], "answer": a}, headers=h)
            assert r.status_code == 200, r.text
    return c.post(f"/learn/lessons/{lid}/complete", headers=h)


def test_map_lists_published_lessons_and_day_one_is_open(clock):
    ls = lessons_of(client())
    assert {"lw", "lt", "la", "lp", "lf", "lb"} <= set(ls)
    assert ls["lw"]["status"] == "available"
    assert ls["lt"]["status"] == "locked" and ls["lb"]["status"] == "locked" and ls["lf"]["status"] == "locked"


def test_lesson_hides_answers(clock):
    h = client()
    lesson = c.get("/learn/lessons/lw?lang=es", headers=h).json()
    items = {it["id"]: it for s in lesson["steps"] for it in s["items"]}
    assert all("answer" not in it for it in items.values())
    assert "pairs" not in items["lw.1.4"] and len(items["lw.1.4"]["left"]) == 3
    assert {r["key"] for r in items["lw.1.4"]["right"]} == {"0", "1", "2"}
    assert {s["key"] for s in items["lw.1.5"]["steps"]} == {"0", "1", "2"}
    assert items["lw.1.2"]["options"] == ["Cero", "Uno", "Dos"]
    en = c.get("/learn/lessons/lw?lang=en", headers=h).json()
    assert en["title"] == "Lesson lw"


def test_locked_lesson_cannot_be_opened_or_answered(clock):
    h = client()
    assert c.get("/learn/lessons/lt?lang=es", headers=h).status_code == 409
    assert c.post("/learn/attempts", json={"item_id": "lt.1.2", "answer": 2}, headers=h).status_code == 409


def test_attempt_grading_and_feedback(clock):
    h = client()
    r = c.post("/learn/attempts", json={"item_id": "lw.1.2", "answer": 2}, headers=h).json()
    assert r["correct"] is True and r["explain"] == "Dos."
    assert r["source"]["cite"] == "6110" and "leginfo" in r["source"]["url"]
    assert c.post("/learn/attempts", json={"item_id": "lw.1.2", "answer": 0}, headers=h).json()["correct"] is False
    assert c.post("/learn/attempts", json={"item_id": "lw.1.3", "answer": False}, headers=h).json()["source"] is None
    assert c.post("/learn/attempts", json={"item_id": "lw.1.4", "answer": {"0": "0", "1": "1", "2": "2"}}, headers=h).json()["correct"] is True
    assert c.post("/learn/attempts", json={"item_id": "lw.1.4", "answer": {"0": "1", "1": "0", "2": "2"}}, headers=h).json()["correct"] is False
    assert c.post("/learn/attempts", json={"item_id": "lw.1.5", "answer": ["0", "1", "2"]}, headers=h).json()["correct"] is True
    assert c.post("/learn/attempts", json={"item_id": "lw.1.1", "answer": 0}, headers=h).status_code == 422
    assert c.post("/learn/attempts", json={"item_id": "lw.1.2", "answer": "dos"}, headers=h).status_code == 422
    assert c.post("/learn/attempts", json={"item_id": "nope.1.1", "answer": 0}, headers=h).status_code == 404


def test_completion_needs_80_percent_and_any_retries(clock):
    h = client()
    r = answer_all(h, "lw", right=False).json()
    assert r["completed"] is False and r["score"] < 0.8
    r = answer_all(h, "lw", right=True).json()                      # retries count: the latest answer wins
    assert r["completed"] is True and r["score"] == 1.0


def test_completion_needs_every_gradable_item_answered(clock):
    h = client()
    c.post("/learn/attempts", json={"item_id": "lw.1.2", "answer": 2}, headers=h)
    assert c.post("/learn/lessons/lw/complete", headers=h).json()["completed"] is False


def test_discount_event_is_emitted_once(clock):
    h = client()
    answer_all(h, "lw")
    answer_all(h, "lw")
    jid = c.get("/journey", headers=h).json()["id"]
    n = db.query("SELECT COUNT(*) FROM journey_events WHERE journey_id = ? AND type = ?", (jid, "lesson_completed:will"))[0][0]
    assert n == 1
    assert c.get("/payments/quote?codes=will", headers=h).json()["items"][0]["price"] == 290000


def test_next_lesson_opens_at_local_midnight(clock):
    h = client()
    answer_all(h, "lw")
    ls = lessons_of(h)
    assert ls["lw"]["status"] == "done" and ls["lt"]["status"] == "locked"
    assert ls["lt"]["unlock_at"].startswith("2026-12-03T00:00:00")     # midnight in Los Angeles
    assert ls["lb"]["status"] == "available"                           # bonus lessons open after day 1
    clock["now"] = datetime.datetime(2026, 12, 2, 23, 59, tzinfo=LA)
    assert lessons_of(h)["lt"]["status"] == "locked"
    clock["now"] = datetime.datetime(2026, 12, 3, 0, 0, tzinfo=LA)
    assert lessons_of(h)["lt"]["status"] == "available"


def test_bonus_lessons_never_emit_a_discount(clock):
    h = client()
    answer_all(h, "lw")
    answer_all(h, "lb")
    jid = c.get("/journey", headers=h).json()["id"]
    types = {r[0] for r in db.query("SELECT type FROM journey_events WHERE journey_id = ?", (jid,))}
    assert "lesson_completed:bonus" not in types


def test_final_lesson_waits_for_signing(clock):
    h = client()
    assert lessons_of(h)["lf"]["status"] == "locked"
    jid = c.get("/journey", headers=h).json()["id"]
    journey.apply(jid, "signed", {}, actor="staff@example.com")
    assert lessons_of(h)["lf"]["status"] == "available"


def test_analytics_never_store_answers(clock):
    h = client()
    c.post("/learn/attempts", json={"item_id": "lw.1.2", "answer": 2}, headers=h)
    rows = db.query("SELECT props_json FROM events WHERE type = 'item_answered' ORDER BY created_at DESC LIMIT 5")
    assert rows and all('"answer"' not in r[0] and "Dos" not in r[0] for r in rows)


def test_unpublished_items_are_not_served(clock):
    h = client()
    db.execute("UPDATE content_items SET state = 'draft' WHERE id = ?", ("lw.1.5",))
    try:
        lesson = c.get("/learn/lessons/lw?lang=es", headers=h).json()
        assert "lw.1.5" not in {it["id"] for s in lesson["steps"] for it in s["items"]}
    finally:
        db.execute("UPDATE content_items SET state = 'published' WHERE id = ?", ("lw.1.5",))


def test_auth(clock):
    assert c.get("/learn/map").status_code == 401
    assert c.post("/learn/attempts", json={"item_id": "lw.1.2", "answer": 2}).status_code == 401
