"""T4-06 (motivation): written by Opus after the builder delivered no tests."""
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
from aprende import content, journey, learn, motivation

HERE = os.path.dirname(os.path.abspath(__file__))
c = TestClient(backend.app)
LA = ZoneInfo("America/Los_Angeles")
D = datetime.date


# ---------- the streak rule (pure) ----------
@pytest.mark.parametrize("days,today,count,rested", [
    ([], D(2026, 12, 2), 0, False),
    ([D(2026, 12, 2)], D(2026, 12, 2), 1, False),                                   # done today
    ([D(2026, 12, 1)], D(2026, 12, 2), 1, False),                                   # today not done yet: no miss
    ([D(2026, 11, 30), D(2026, 12, 1), D(2026, 12, 2)], D(2026, 12, 2), 3, False),  # Mon-Wed
    ([D(2026, 11, 30), D(2026, 12, 2)], D(2026, 12, 2), 2, True),                   # Tue missed: the week's rest day
    ([D(2026, 11, 30), D(2026, 12, 3)], D(2026, 12, 3), 1, False),                  # Tue and Wed missed: second miss ends it (no rest used)
    ([D(2026, 11, 23), D(2026, 11, 25), D(2026, 11, 26)], D(2026, 11, 26), 3, True),   # Tue rested, same ISO week as today
    ([D(2026, 11, 27), D(2026, 11, 28), D(2026, 11, 30)], D(2026, 11, 30), 3, False),  # Sun rested, but that was last ISO week
    ([D(2026, 11, 26), D(2026, 11, 28), D(2026, 11, 30), D(2026, 12, 2)], D(2026, 12, 2), 3, True),  # Tue rests (wk 49), Sun rests (wk 48), Fri is wk 48's second miss
    ([D(2026, 11, 26), D(2026, 11, 27), D(2026, 11, 30)], D(2026, 11, 30), 1, False),  # Sat+Sun missed: two misses in one week end it
])
def test_streak(days, today, count, rested):
    s = motivation.streak(days, today)
    assert (s["count"], s["rested_this_week"]) == (count, rested), s


def test_streak_before_the_first_day_is_not_a_rest():
    assert motivation.streak([D(2026, 12, 2)], D(2026, 12, 3))["count"] == 1


# ---------- through the API ----------
def publish(dirname):
    b = content.load_dir(os.path.join(HERE, "fixtures", dirname))
    content.import_bundle(b, actor="opus")
    for lesson in b["lessons"]:
        for step in lesson["steps"]:
            for it in step["items"]:
                if it.get("legal"):
                    content.approve(it["id"], attorney="attorney@example.com")
                content.publish(it["id"], actor="paralegal@example.com")


publish("learn")


@pytest.fixture
def clock(monkeypatch):
    t = {"now": datetime.datetime(2026, 12, 2, 10, 0, tzinfo=LA)}
    monkeypatch.setattr(learn, "now", lambda: t["now"])
    return t


def client():
    r = c.post("/auth/signup", json={"name": "Ana Torres", "email": f"ana-{uuid.uuid4().hex[:8]}@example.com",
                                     "password": "long-secure-password", "source": "aprende", "adult": True})
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_petals_for_correct_answers_once_and_for_lessons(clock):
    h = client()
    first = c.post("/learn/attempts", json={"item_id": "lw.1.2", "answer": 2}, headers=h).json()
    again = c.post("/learn/attempts", json={"item_id": "lw.1.2", "answer": 2}, headers=h).json()
    wrong = c.post("/learn/attempts", json={"item_id": "lw.1.3", "answer": True}, headers=h).json()
    assert (first["petals"], again["petals"], wrong["petals"]) == (10, 0, 0)
    for item_id, a in (("lw.1.3", False), ("lw.1.4", {"0": "0", "1": "1", "2": "2"}), ("lw.1.5", ["0", "1", "2"])):
        c.post("/learn/attempts", json={"item_id": item_id, "answer": a}, headers=h)
    assert c.post("/learn/lessons/lw/complete", headers=h).json()["completed"] is True
    c.post("/learn/lessons/lw/complete", headers=h)
    p = c.get("/progress", headers=h).json()
    assert p["petals"] == 4 * 10 + 50
    assert p["level"] == {"name_key": "level.aprendiz", "next_at": 300}
    assert p["streak"] == {"count": 1, "rested_this_week": False}
    seals = {s["id"]: s["earned"] for s in p["seals"]}
    assert seals["will"] is True and seals["trust"] is False and seals["plan_completo"] is False


def test_reminders_default_off_validated_and_due_once_a_day(clock):
    h = client()
    assert c.get("/progress", headers=h).json()["reminders"] == {"enabled": False, "local_time": None}
    assert c.put("/progress/reminders", json={"enabled": True, "local_time": "25:00"}, headers=h).status_code == 422
    assert c.put("/progress/reminders", json={"enabled": True, "local_time": "18:30"}, headers=h).json() == {"enabled": True, "local_time": "18:30"}
    jid = c.get("/journey", headers=h).json()["id"]
    at = lambda hh, mm, d=2: datetime.datetime(2026, 12, d, hh, mm, tzinfo=LA)
    assert jid not in motivation.reminders_due(at(18, 0))
    assert jid in motivation.reminders_due(at(18, 31))
    motivation.mark_reminded(jid, at(18, 31))
    assert jid not in motivation.reminders_due(at(21, 0))                 # at most one a day
    assert jid in motivation.reminders_due(at(18, 31, d=3))               # tomorrow again
    c.put("/progress/reminders", json={"enabled": False, "local_time": "18:30"}, headers=h)
    assert jid not in motivation.reminders_due(at(18, 31, d=4))           # off with one switch


def test_no_reminder_after_a_lesson_today(clock):
    h = client()
    c.put("/progress/reminders", json={"enabled": True, "local_time": "08:00"}, headers=h)
    for item_id, a in (("lw.1.2", 2), ("lw.1.3", False), ("lw.1.4", {"0": "0", "1": "1", "2": "2"}), ("lw.1.5", ["0", "1", "2"])):
        c.post("/learn/attempts", json={"item_id": item_id, "answer": a}, headers=h)
    c.post("/learn/lessons/lw/complete", headers=h)
    jid = c.get("/journey", headers=h).json()["id"]
    assert jid not in motivation.reminders_due(datetime.datetime(2026, 12, 2, 20, 0, tzinfo=LA))


def test_progress_auth():
    assert c.get("/progress").status_code == 401
