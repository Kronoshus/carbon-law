"""T7-04 acceptance tests, written by Opus (t7-tests) before the code. Contract: docs/tickets/T7-04.md (staff guard,
GET /staff/journeys[/{jid}], POST /staff/attorney-questions/{qid}/answer, GET /journey/questions). Do not weaken."""
import datetime
import os
import re
import sys
import tempfile
import uuid

os.environ.setdefault("DATABASE_URL", "")
os.environ.setdefault("CARBON_DB_PATH", tempfile.mktemp(suffix=".db"))
sys.path.insert(0, "backend")

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import app as backend
import db
import migrate
from aprende import conflicts, datos, journey

migrate.run()
c = TestClient(backend.app)

PARA, ATT, ADMIN = "t704-para@example.com", "t704-att@example.com", "t704-admin@example.com"
PW = "t704-password-1"
for _em, _role in ((PARA, "paralegal"), (ATT, "attorney"), (ADMIN, "admin")):
    backend.users[_em] = {"id": str(uuid.uuid4()), "name": _em.split("@")[0], "email": _em, "role": _role,
                          "password_hash": backend.hash_pw(PW), "created_at": datetime.datetime.utcnow().isoformat()}


def login(em):
    return {"Authorization": "Bearer " + c.post("/auth/login", json={"email": em, "password": PW}).json()["token"]}


def client(name="Ana Torres"):
    r = c.post("/auth/signup", json={"name": name, "email": f"c-{uuid.uuid4().hex[:8]}@example.com",
                                     "password": "long-secure-password", "source": "aprende", "adult": True})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def send(h, type_, **payload):
    return c.post("/journey/events", json={"type": type_, "payload": payload}, headers=h)


def cleared(h, names=("Ana Torres", "Luis Torres")):
    send(h, "ai_disclosed")
    send(h, "consent", answer="yes")
    jid = send(h, "names_submitted", names=list(names)).json()["id"]
    journey.apply(jid, "conflict_auto", {"result": "clear"}, actor="system")
    return jid


def ask_attorney(jid, text):
    qid = str(uuid.uuid4())
    db.execute("INSERT INTO attorney_questions (id, journey_id, question, lesson_id, character, created_at) VALUES (?, ?, ?, ?, ?, ?)",
               (qid, jid, text, "will", "calavera", journey._now_iso()))
    return qid


def staff_routes():
    out = []
    for r in backend.app.routes:
        if not isinstance(r, APIRoute):
            continue
        if r.path.startswith("/staff/") or r.path.startswith("/conflicts") or r.path == "/chat/attorney-questions":
            path = re.sub(r"\{[^}]+\}", "x", r.path)
            out += [(m, path) for m in sorted(r.methods) if m != "HEAD"]
    return out


def test_a_client_gets_403_on_every_staff_route():
    routes = staff_routes()
    assert len(routes) >= 20 and ("POST", "/staff/attorney-questions/x/answer") in routes
    h = client()
    wrong = [(m, p, r.status_code) for m, p in routes
             for r in [c.request(m, p, headers=h, **({} if m in ("GET", "DELETE") else {"json": {}}))] if r.status_code != 403]
    assert wrong == []


def test_no_token_gets_401_on_every_staff_route():
    wrong = [(m, p, r.status_code) for m, p in staff_routes()
             for r in [c.request(m, p, **({} if m in ("GET", "DELETE") else {"json": {}}))] if r.status_code != 401]
    assert wrong == []


def _row(jid, h=None):
    rows = c.get("/staff/journeys", headers=h or login(PARA))
    assert rows.status_code == 200, rows.text
    return next(r for r in rows.json() if r["journey_id"] == jid)


def test_the_clients_list_shows_each_column():
    h = client("Luis Torres")
    jid = cleared(h)
    j = journey.get_journey(jid)
    datos.save(j, "nombre", answer="Luis Torres")
    total = len(datos.get_datos(j)["questions"])
    journey.apply(jid, "paid", {}, actor="stripe")
    db.execute("INSERT INTO payments (id, journey_id, session_id, amount_cents, paid_at) VALUES (?, ?, ?, ?, ?)",
               (str(uuid.uuid4()), jid, "cs_test_" + uuid.uuid4().hex, 260000, journey._now_iso()))
    assert c.post(f"/staff/journeys/{jid}/refunds", json={"amount_cents": 10000, "reason": "prueba"},
                  headers=login(ADMIN)).status_code == 200
    start = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=9)).strftime("%Y-%m-%dT17:00:00Z")
    db.execute("INSERT INTO bookings (id, journey_id, kind, start_utc, end_utc, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
               (str(uuid.uuid4()), jid, "signing", start, start, "active", journey._now_iso()))
    db.execute("INSERT INTO bookings (id, journey_id, kind, start_utc, end_utc, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
               (str(uuid.uuid4()), jid, "consultation", start, start, "cancelled", journey._now_iso()))
    doc = str(uuid.uuid4())
    backend.documents[doc] = {"id": doc, "journey_id": jid, "matter_id": j.get("matter_id"), "attorney_only": True,
                              "status": "Draft", "name": "Last will and testament", "version": 1}
    q1 = ask_attorney(jid, "¿Mi hijo puede ser albacea si vive en México?")
    ask_attorney(jid, "¿Necesito un fideicomiso para mi casa?")
    try:
        assert c.post(f"/staff/attorney-questions/{q1}/answer", json={"answer": "Sí, puede; lo vemos en la cita."},
                      headers=login(ATT)).status_code == 200
        row = _row(jid)
        assert {"journey_id", "client_name", "day", "next_step", "late", "due"} <= set(row)          # T6-09 keys stay
        assert row["client_name"] == "Luis Torres" and isinstance(row["day"], int)
        assert row["conflict"] == "clear"
        assert row["datos"] == {"done": 1, "total": total, "complete": False}
        assert row["payment"] == {"paid": True, "paid_cents": 260000, "refunded_cents": 10000}
        assert row["drafts_waiting"] == 1
        assert row["appointments"] == [{"kind": "signing", "start_utc": start}]
        assert row["questions"] == {"open": 1, "answered": 1}
    finally:
        del backend.documents[doc]
    fresh = _row(cleared(client()))
    assert fresh["payment"] == {"paid": False, "paid_cents": 0, "refunded_cents": 0}
    assert fresh["drafts_waiting"] == 0 and fresh["appointments"] == [] and fresh["questions"] == {"open": 0, "answered": 0}


def test_the_client_detail_lists_the_questions_for_the_attorney():
    jid = cleared(client())
    q1 = ask_attorney(jid, "¿Puedo dejarle la casa a mi sobrina?")
    q2 = ask_attorney(jid, "¿Quién cuida a Mateo si me pasa algo?")
    c.post(f"/staff/attorney-questions/{q2}/answer", json={"answer": "Lo hablamos en su cita."}, headers=login(ATT))
    r = c.get(f"/staff/journeys/{jid}", headers=login(PARA))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["journey_id"] == jid and d["conflict"] == "clear" and isinstance(d["timeline"], list) and d["timeline"]
    qs = {q["id"]: q for q in d["questions"]}
    assert set(qs) == {q1, q2}
    assert qs[q1]["question"] == "¿Puedo dejarle la casa a mi sobrina?" and qs[q1]["answer"] is None
    assert qs[q2]["answer"] == "Lo hablamos en su cita." and qs[q2]["answered_by"] == ATT and qs[q2]["answered_at"]
    assert c.get("/staff/journeys/no-such-journey", headers=login(PARA)).status_code == 404


def test_only_the_attorney_answers():
    jid = cleared(client())
    qid = ask_attorney(jid, "¿Mi testamento de México vale aquí?")
    for who in (PARA, ADMIN):
        assert c.post(f"/staff/attorney-questions/{qid}/answer", json={"answer": "Sí."}, headers=login(who)).status_code == 403
    assert c.post(f"/staff/attorney-questions/{qid}/answer", json={"answer": "   "}, headers=login(ATT)).status_code == 422
    assert c.post(f"/staff/attorney-questions/{qid}/answer", json={"answer": "x" * 4001}, headers=login(ATT)).status_code == 422
    assert c.post("/staff/attorney-questions/nope/answer", json={"answer": "Sí."}, headers=login(ATT)).status_code == 404
    r = c.post(f"/staff/attorney-questions/{qid}/answer", json={"answer": "  Lo revisamos juntos en la cita.  "}, headers=login(ATT))
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["id"] == qid and out["answer"] == "Lo revisamos juntos en la cita." and out["answered_by"] == ATT and out["answered_at"]
    r = c.post(f"/staff/attorney-questions/{qid}/answer", json={"answer": "Mejor: tráigalo a la cita."}, headers=login(ATT))
    assert r.json()["answer"] == "Mejor: tráigalo a la cita."                                       # a new answer replaces it


def test_the_attorneys_reply_appears_in_the_clients_preguntas():
    h = client()
    jid = cleared(h)
    other = client("Sofía Torres")
    other_jid = cleared(other)
    ask_attorney(other_jid, "Pregunta de otra persona")
    qid = ask_attorney(jid, "¿Mi esposo tiene que firmar también?")
    r = c.get("/journey/questions", headers=h)
    assert r.status_code == 200, r.text
    assert r.json() == {"questions": [{"id": qid, "question": "¿Mi esposo tiene que firmar también?",
                                       "created_at": r.json()["questions"][0]["created_at"], "answer": None, "answered_at": None}]}
    c.post(f"/staff/attorney-questions/{qid}/answer", json={"answer": "Si es un fideicomiso de los dos, sí."}, headers=login(ATT))
    q = c.get("/journey/questions", headers=h).json()["questions"][0]
    assert q["answer"] == "Si es un fideicomiso de los dos, sí." and q["answered_at"]
    assert "answered_by" not in q and ATT not in c.get("/journey/questions", headers=h).text
    assert [x["question"] for x in c.get("/journey/questions", headers=other).json()["questions"]] == ["Pregunta de otra persona"]
    assert c.get("/journey/questions").status_code == 401
    assert c.get("/journey/questions", headers=login(PARA)).status_code == 403


def test_an_answer_is_audited_without_its_text():
    jid = cleared(client())
    qid = ask_attorney(jid, "¿Puedo excluir a mi hermano Roberto?")
    mark = len(backend.audit)
    c.post(f"/staff/attorney-questions/{qid}/answer", json={"answer": "Sí, se puede; lo vemos en la cita."}, headers=login(ATT))
    rows = [a for a in backend.audit[mark:] if a["entity_id"] == qid]
    assert [(a["actor"], a["action"], a["entity"]) for a in rows] == [(ATT, "answer", "attorney_question")]
    assert "Roberto" not in rows[0]["detail"] and "cita" not in rows[0]["detail"]


def test_no_conflict_match_names_on_the_clients_pages():
    before = conflicts.get_list()
    conflicts.replace_list("name\nRemedios Xochiquetzal Adversaria\n")
    try:
        h = client("Ana Torres")
        send(h, "ai_disclosed")
        send(h, "consent", answer="yes")
        jid = send(h, "names_submitted", names=["Ana Torres", "Remedios Xochiquetzal Adversaria"]).json()["id"]
        assert journey.get_journey(jid)["conflict"] == "hold"
        assert any("Remedios Xochiquetzal Adversaria" in str(x["matches"]) for x in conflicts.queue() if x["journey_id"] == jid)
        lst = c.get("/staff/journeys", headers=login(PARA))
        assert _row(jid)["conflict"] == "hold"
        det = c.get(f"/staff/journeys/{jid}", headers=login(PARA))
        assert det.status_code == 200
        for page in (lst.text, det.text, c.get("/journey", headers=h).text, c.get("/journey/questions", headers=h).text):
            assert "Xochiquetzal" not in page and "Adversaria" not in page and "matches" not in page and "possible" not in page
    finally:
        conflicts.replace_list("name\n" + "\n".join(before)) if before else conflicts.delete_list()


def test_the_staff_guard_keeps_cors_for_the_admin_page():
    """The admin page is on another origin: preflights pass, and a refusal still carries the CORS header (lead, review)."""
    origin = "https://carbon.bailment.tech"
    pre = c.options("/staff/journeys", headers={"Origin": origin, "Access-Control-Request-Method": "GET",
                                                "Access-Control-Request-Headers": "authorization"})
    assert pre.status_code == 200 and pre.headers.get("access-control-allow-origin") == origin
    refused = c.get("/staff/journeys", headers={**client(), "Origin": origin})
    assert refused.status_code == 403 and refused.headers.get("access-control-allow-origin") == origin
