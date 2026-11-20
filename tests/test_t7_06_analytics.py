"""T7-06 acceptance tests, written by Opus (t7-tests) before the code. Contract: docs/tickets/T7-06.md (analytics.record,
the recording points, GET /staff/analytics). Do not weaken these tests: the scan seeds realistic fictional client content
first, and test_the_scanner_finds_planted_content proves the scan can fail."""
import datetime
import json
import logging
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
from ai.stub import StubClient
from aprende import chat as chatmod
from aprende import content, datos, journey

migrate.run()
c = TestClient(backend.app)
HERE = os.path.dirname(os.path.abspath(__file__))
EXT = "chrome-extension://aprendet706testextensionid"
if EXT not in backend._cors_origins:
    backend._cors_origins.append(EXT)
PARA = "t706-para@example.com"
PW = "t706-password-1"
backend.users[PARA] = {"id": str(uuid.uuid4()), "name": "Rosa Paralegal", "email": PARA, "role": "paralegal",
                       "password_hash": backend.hash_pw(PW), "created_at": datetime.datetime.utcnow().isoformat()}

_bundle = content.load_dir(os.path.join(HERE, "fixtures", "learn"))   # lw: day 1; graded lw.1.2 choice(2) .3 tf(False) .4 match .5 order
if not db.query("SELECT id FROM content_lessons WHERE id = 'lw'"):
    content.import_bundle(_bundle, actor="opus")
for _l in _bundle["lessons"]:
    for _s in _l["steps"]:
        for _it in _s["items"]:
            if _it.get("legal"):
                content.approve(_it["id"], attorney="attorney@example.com")
            content.publish(_it["id"], actor="paralegal@example.com")

RIGHT = {"lw.1.2": 2, "lw.1.3": False, "lw.1.4": {"0": "0", "1": "1", "2": "2"}, "lw.1.5": ["0", "1", "2"]}
WRONG = {"lw.1.2": 0, "lw.1.3": True, "lw.1.4": {"0": "1", "1": "0", "2": "2"}, "lw.1.5": ["2", "1", "0"]}


def staff():
    return {"Authorization": "Bearer " + c.post("/auth/login", json={"email": PARA, "password": PW}).json()["token"]}


def client(name="Ana Torres", email=None):
    r = c.post("/auth/signup", json={"name": name, "email": email or f"c-{uuid.uuid4().hex[:8]}@example.com",
                                     "password": "long-secure-password", "source": "aprende", "adult": True})
    assert r.status_code == 200, r.text
    h = {"Authorization": "Bearer " + r.json()["token"]}
    return h, c.get("/journey", headers=h).json()["id"]


def since():
    """Now, in the format of journeys.started_at: the dashboard then counts only the journeys this test starts."""
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()


def dash(s):
    r = c.get("/staff/analytics", params={"since": s}, headers=staff())
    assert r.status_code == 200, r.text
    return r.json()


def open_lesson(h):
    assert c.get("/learn/lessons/lw?lang=es", headers=h).status_code == 200


def answer(h, iid, right=True):
    r = c.post("/learn/attempts", json={"item_id": iid, "answer": (RIGHT if right else WRONG)[iid]}, headers=h)
    assert r.status_code == 200, r.text


def finish(h):
    open_lesson(h)
    for iid in RIGHT:
        answer(h, iid)
    assert c.post("/learn/lessons/lw/complete", headers=h).json()["completed"] is True


def events_of(jid):
    return [(t, json.loads(p or "{}"), tg) for t, p, tg in
            db.query("SELECT type, props_json, target FROM events WHERE journey_id = ? ORDER BY created_at, id", (jid,))]


def test_analytics_is_staff_only():
    h, _ = client()
    assert c.get("/staff/analytics").status_code == 401
    assert c.get("/staff/analytics", headers=h).status_code == 403
    out = c.get("/staff/analytics", headers=staff())
    assert out.status_code == 200 and set(out.json()) == {"lessons", "items", "conversion", "on_time"}


def test_record_refuses_unknown_types_props_and_free_text():
    from aprende import analytics
    _, jid = client()
    with pytest.raises(ValueError):
        analytics.record(jid, "datos_answer_text", {"question_id": "nombre"})
    with pytest.raises(ValueError):
        analytics.record(jid, "datos_question_answered", {"question_id": "nombre", "answer": "ana"})
    with pytest.raises(ValueError):
        analytics.record(jid, "datos_question_answered", {"question_id": "Mi hija Sofía Torres"})
    with pytest.raises(ValueError):
        analytics.record(jid, "step_late", {"step": "x" * 41})
    with pytest.raises(ValueError):
        analytics.record(jid, "consent", {"answer": {"text": "sí"}})
    assert events_of(jid) == []
    analytics.record(jid, "datos_question_answered", {"question_id": "nombre", "skipped": False})
    (typ, props, target), = events_of(jid)
    assert typ == "datos_question_answered" and props == {"question_id": "nombre", "skipped": False, "day": 1}
    assert target == "web"


SPEC = {"lesson_started": {"lesson_id"}, "item_answered": {"item_id", "correct", "attempt"}, "lesson_completed": {"lesson_id"},
        "datos_question_answered": {"question_id", "skipped"}, "datos_completed": set(), "consent": {"answer"},
        "conflict_auto": {"result"}, "documents_tentative": {"codes"}, "engagement_signed": set(),
        "checkout_started": set(), "paid": set(), "drafts_ready": set(), "attorney_approved": set(),
        "client_confirmed": set(), "changes_requested": set(), "signing_booked": set(), "signed": set(),
        "final_lesson_completed": set(), "step_late": {"step"}}


def walk(h, jid):
    """A whole journey with fictional client content, through the real routes where a client acts."""
    c.post("/journey/events", json={"type": "ai_disclosed", "payload": {}}, headers=h)
    c.post("/journey/events", json={"type": "consent", "payload": {"answer": "yes"}}, headers=h)
    c.post("/journey/events", json={"type": "names_submitted", "payload": {"names": ["Ana Torres", "Luis Torres", "Sofía Torres", "Mateo Torres"]}}, headers=h)
    journey.apply(jid, "conflict_auto", {"result": "clear"}, actor="system")
    finish(h)
    assert c.post("/journey/events", json={"type": "documents_tentative", "payload": {"codes": ["will", "trust"]}}, headers=h).status_code == 200
    assert c.put("/datos/nombre", json={"answer": "Ana María Torres Gutiérrez"}, headers=h).status_code == 200
    assert c.put("/datos/domicilio", json={"answer": "Calle Girasol 742, Pomona, condado de Los Ángeles"}, headers=h).status_code == 200
    assert c.put("/datos/hijos", json={"skipped": True}, headers=h).status_code == 200
    for ev in ("intake_completed", "conflict_firm", "scope_approved", "engagement_signed", "engagement_countersigned", "paid",
               "drafts_ready", "attorney_approved", "client_confirmed", "signing_booked", "signed", "final_lesson_completed"):
        journey.apply(jid, ev, {"result": "cleared"} if ev == "conflict_firm" else {}, actor="system")


def test_events_follow_the_spec_list():
    h, jid = client()
    walk(h, jid)
    rows = events_of(jid)
    types = {t for t, _, _ in rows}
    assert {"lesson_started", "item_answered", "lesson_completed", "datos_question_answered", "datos_completed", "consent",
            "conflict_auto", "documents_tentative", "engagement_signed", "paid", "drafts_ready", "attorney_approved",
            "client_confirmed", "signing_booked", "signed", "final_lesson_completed"} <= types, types
    for t, props, target in rows:
        assert t in SPEC, t
        assert set(props) <= SPEC[t] | {"day"}, (t, props)
        assert isinstance(props["day"], int) and target == "web"
    assert ("consent", {"answer": "yes"}) in [(t, {k: v for k, v in p.items() if k != "day"}) for t, p, _ in rows]
    assert [p["codes"] for t, p, _ in rows if t == "documents_tentative"] == [["will", "trust"]]
    answered = sorted((p["question_id"], p["skipped"]) for t, p, _ in rows if t == "datos_question_answered")
    assert answered == [("domicilio", False), ("hijos", True), ("nombre", False)]
    assert [t for t, _, _ in rows].count("lesson_started") == 1
    c.get("/learn/lessons/lw?lang=es", headers=h)                                      # opened again: still one start
    assert [t for t, _, _ in events_of(jid)].count("lesson_started") == 1
    n = len(events_of(jid))
    journey.apply(jid, "paid", {}, actor="stripe")                                     # a repeated fact records nothing
    assert len(events_of(jid)) == n


def test_the_extension_is_its_own_target():
    h, jid = client()
    assert c.get("/learn/lessons/lw?lang=es", headers={**h, "Origin": EXT}).status_code == 200
    assert c.post("/learn/attempts", json={"item_id": "lw.1.3", "answer": False}, headers={**h, "Origin": EXT}).status_code == 200
    assert {(t, tg) for t, _, tg in events_of(jid)} == {("lesson_started", "extension"), ("item_answered", "extension")}


def _lesson_row(d):
    return next(l for l in d["lessons"] if l["lesson_id"] == "lw")


def _item_row(d, iid):
    return next(i for i in d["items"] if i["item_id"] == iid)


def test_lesson_completion_and_drop_off_by_item():
    s = since()
    a, _ = client()
    finish(a)
    b, _ = client()
    open_lesson(b)
    answer(b, "lw.1.2")
    answer(b, "lw.1.3", right=False)                                                   # stops after the true/false
    e, _ = client()
    open_lesson(e)                                                                     # opens it, answers nothing
    client()                                                                           # never opens it
    d = dash(s)
    assert _lesson_row(d) == {"lesson_id": "lw", "started": 3, "completed": 1, "completion_rate": 0.333,
                              "dropped_before_first_item": 1}
    assert _item_row(d, "lw.1.3")["drop_off"] == 1
    assert _item_row(d, "lw.1.2")["drop_off"] == 0 and _item_row(d, "lw.1.5")["drop_off"] == 0
    assert [i["item_id"] for i in d["items"] if i["lesson_id"] == "lw"] == ["lw.1.2", "lw.1.3", "lw.1.4", "lw.1.5"]
    empty = dash((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).replace(tzinfo=None).isoformat())
    assert empty["lessons"] == [] and empty["conversion"] == {"journeys": 0, "paid": 0, "rate": None}


def test_accuracy_per_item_uses_first_attempts():
    s = since()
    a, _ = client()
    open_lesson(a)
    answer(a, "lw.1.2", right=False)
    answer(a, "lw.1.2")                                                                # right on the second try
    b, _ = client()
    open_lesson(b)
    answer(b, "lw.1.2")
    answer(b, "lw.1.3")
    d = dash(s)
    assert {k: _item_row(d, "lw.1.2")[k] for k in ("answered", "first_try_correct", "accuracy")} == \
        {"answered": 2, "first_try_correct": 1, "accuracy": 0.5}
    assert {k: _item_row(d, "lw.1.3")[k] for k in ("answered", "first_try_correct", "accuracy")} == \
        {"answered": 1, "first_try_correct": 1, "accuracy": 1.0}


def test_paid_conversion_and_on_time_completion():
    s = since()
    jids = [client()[1] for _ in range(4)]
    for jid in jids[:2]:
        journey.apply(jid, "paid", {}, actor="stripe")
        journey.apply(jid, "final_lesson_completed", {}, actor="system")
    db.execute("INSERT INTO timeline_alerts (id, journey_id, step, due, created_at) VALUES (?, ?, ?, ?, ?)",
               (str(uuid.uuid4()), jids[1], "attorney_review", "2026-11-10", "2026-11-11T08:00:00"))
    d = dash(s)
    assert d["conversion"] == {"journeys": 4, "paid": 2, "rate": 0.5}
    assert d["on_time"] == {"finished": 2, "on_time": 1, "rate": 0.5}


NEEDLES = ["Ana", "Torres", "Gutiérrez", "Sofía", "Mateo", "Luis", "Girasol", "Pomona", "ana.torres.t706@example.com",
           "albacea en México", "dejarle la casa"]


def scan(caplog_text="", out=""):
    """Every analytics sink as text: the events and ai_calls tables (all columns), the logs, stdout/stderr."""
    parts = [caplog_text, out]
    for table in ("events", "ai_calls"):
        parts += [json.dumps(row, ensure_ascii=False, default=str) for row in db.query(f"SELECT * FROM {table}")]
    blob = "\n".join(parts)
    return sorted({n for n in NEEDLES if n.lower() in blob.lower()})


def test_the_scanner_finds_planted_content():
    _, jid = client()
    bad = str(uuid.uuid4())
    db.execute("INSERT INTO events (id, journey_id, type, props_json, created_at) VALUES (?, ?, ?, ?, ?)",
               (bad, jid, "datos_question_answered", json.dumps({"answer": "Calle Girasol 742, Pomona"}), "2026-11-20T00:00:00"))
    try:
        assert scan() == ["Girasol", "Pomona"]
        assert scan(caplog_text="staff alert: Ana Torres") == ["Ana", "Girasol", "Pomona", "Torres"]
    finally:
        db.execute("DELETE FROM events WHERE id = ?", (bad,))


def test_no_client_content_in_any_analytics_sink(monkeypatch, caplog, capsys):
    monkeypatch.delenv("APRENDE_STAFF_NTFY_TOPIC", raising=False)                     # staff alerts go to the log
    caplog.set_level(logging.DEBUG)
    assert scan() == [], "the events or ai_calls table already holds client content"
    stub = StubClient(replies=[("Un albacea cumple el testamento.", None),
                               ("Esa es una pregunta para el abogado Raval. Ya se la anoté y él le responde. "
                                "[ATTORNEY_QUESTION: ¿Mi hijo puede ser albacea en México y dejarle la casa?]", None)])
    monkeypatch.setattr(chatmod, "model_client", lambda: stub)
    h, jid = client("Ana Torres", "ana.torres.t706@example.com")
    walk(h, jid)
    for text in ("¿Qué es un albacea?", "Mi hijo Mateo vive en México: ¿puede ser albacea en México y dejarle la casa?"):
        r = c.post("/chat", json={"mode": "learn", "character": "calavera", "lesson_id": "lw",
                                  "messages": [{"role": "user", "content": text}]}, headers=h)
        assert r.status_code == 200, r.text
    from aprende import timeline
    db.execute("UPDATE journeys SET started_at = ? WHERE id = ?", ("2026-09-01T17:00:00", jid))
    timeline.tick(datetime.datetime.now(datetime.timezone.utc))                        # late steps: alerts and step_late
    assert len(events_of(jid)) >= 15                                                   # the scan has something to read
    captured = capsys.readouterr()
    assert scan(caplog.text, captured.out + captured.err) == []
