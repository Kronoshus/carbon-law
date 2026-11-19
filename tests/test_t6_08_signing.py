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

import base64

from aprende import content, datos, jobs, signing

HERE = os.path.dirname(os.path.abspath(__file__))
_b = content.load_dir(os.path.join(HERE, "fixtures", "learn"))
if not db.query("SELECT id FROM content_lessons WHERE id = 'lw'"):
    content.import_bundle(_b, actor="opus")
    for _l in _b["lessons"]:
        for _s in _l["steps"]:
            for _it in _s["items"]:
                if _it.get("legal"):
                    content.approve(_it["id"], attorney="attorney@example.com")
                content.publish(_it["id"], actor="paralegal@example.com")

PDF = b"%PDF-1.4 executed will"


@pytest.fixture
def mail(monkeypatch):
    out = {"client": [], "staff": []}
    monkeypatch.setattr(signing, "send_email", lambda to, subject, body: out["client"].append((to, body)))
    monkeypatch.setattr(signing, "notify_staff", lambda title, message: out["staff"].append(message))
    return out


def confirmed(codes=("will", "trust")):
    h = client()
    send(h, "ai_disclosed"); send(h, "consent", answer="yes")
    jid = send(h, "names_submitted", names=["Ana Torres"]).json()["id"]
    for ev, p in (("conflict_auto", {"result": "clear"}), ("conflict_firm", {"result": "cleared"})):
        journey.apply(jid, ev, p, actor="system")
    send(h, "documents_confirmed", codes=list(codes))
    for ev in ("scope_approved", "engagement_signed", "engagement_countersigned", "paid", "drafts_ready", "attorney_approved",
               "client_confirmed", "signing_booked"):
        journey.apply(jid, ev, {}, actor="system")
    datos.save(journey.get_journey(jid), "fid_bienes", answer="Mi casa en Boyle Heights y mi cuenta de Wells Fargo")
    return h, jid


def upload(jid, who=None):
    files = [{"name": "Pour-over will", "filename": "will-signed.pdf", "content_b64": base64.b64encode(PDF).decode()}]
    return c.post(f"/staff/journeys/{jid}/executed", json={"documents": files}, headers=who or staff())


def test_uploading_the_executed_documents_records_the_signing_and_moves_the_matter(mail):
    h, jid = confirmed()
    assert upload(jid, h).status_code == 403
    assert upload(jid).status_code == 200
    assert "signed" in state(h)["facts"]
    mid = journey.get_journey(jid)["matter_id"]
    stages = [s["stage"] for s in backend.stage_history[mid]]
    assert stages[-2:] == ["8 Execution", "9 Funding Follow-Up"]


def test_the_final_lesson_opens_after_signing(mail):
    h, jid = confirmed()
    final = lambda: next(l for u in c.get("/learn/map", headers=h).json()["units"] for l in u["lessons"] if l["id"] == "lf")
    assert final()["status"] == "locked"
    upload(jid)
    assert final()["status"] == "available"


def test_executed_documents_are_the_clients_alone_through_unguessable_links(mail):
    h, jid = confirmed()
    upload(jid)
    docs = c.get("/signed-documents", headers=h).json()
    assert [d["name"] for d in docs] == ["Pour-over will"]
    url = docs[0]["url"]
    assert len(url.rsplit("/", 1)[1]) >= 32                                   # not a counter or a short id
    r = c.get(url, headers=h)
    assert r.status_code == 200 and r.content == PDF and r.headers["content-type"] == "application/pdf"
    assert c.get(url).status_code == 401
    other, _ = confirmed()
    assert c.get(url, headers=other).status_code == 404


def test_the_funding_checklist_is_filled_for_a_trust_client(mail):
    h, jid = confirmed(("will", "trust"))
    assert c.get("/funding-checklist", headers=h).status_code == 409             # before signing
    upload(jid)
    text = c.get("/funding-checklist", headers=h).text
    assert "Ana Torres" in text and journey.get_journey(jid)["matter_id"] in text
    assert "Mi casa en Boyle Heights y mi cuenta de Wells Fargo" in text
    assert "{{" not in text
    h2, jid2 = confirmed(("will",))
    upload(jid2)
    assert c.get("/funding-checklist", headers=h2).status_code == 404            # no trust, no checklist


def test_funding_check_ins_run_until_staff_mark_funding_done(mail):
    h, jid = confirmed()
    upload(jid)
    rows = db.query("SELECT key, run_after FROM jobs WHERE kind = 'funding_checkin' AND key LIKE ?", (f"%{jid}%",))
    assert len(rows) == 3
    signed_at = datetime.datetime.fromisoformat(state(h)["facts"]["signed"])
    gaps = sorted((datetime.datetime.fromisoformat(r[1]) - signed_at).days for r in rows)
    assert gaps == [14, 42, 84]
    jobs.HANDLERS["funding_checkin"]({"payload": {"journey_id": jid, "week": 2}})
    assert len(mail["client"]) == 1 and len(mail["staff"]) == 1 and "Ana" not in mail["staff"][0]
    assert c.post(f"/staff/journeys/{jid}/funding-done", headers=h).status_code == 403
    assert c.post(f"/staff/journeys/{jid}/funding-done", headers=staff()).status_code == 200
    jobs.HANDLERS["funding_checkin"]({"payload": {"journey_id": jid, "week": 6}})
    assert len(mail["client"]) == 1                                             # nothing after funding is done
    mid = journey.get_journey(jid)["matter_id"]
    assert backend.matters[mid]["stage"] == "10 Closed"


def test_no_upload_before_the_client_confirmed(mail):
    h = client()
    jid = state(h)["id"]
    assert upload(jid).status_code == 409
