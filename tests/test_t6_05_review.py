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

from ai import Completion
from carbon_intake import DOCS, WORDS
from aprende import drafts, jobs

ATT, OTHER_ATT, ADMIN = "rev-att@example.com", "other-att@example.com", "rev-admin@example.com"
for em, role in ((ATT, "attorney"), (OTHER_ATT, "attorney"), (ADMIN, "admin")):
    backend.users[em] = {"id": str(uuid.uuid4()), "name": em.split("@")[0], "email": em, "role": role,
                         "password_hash": backend.hash_pw("review-password-1"), "created_at": datetime.datetime.utcnow().isoformat()}


def login(em):
    return {"Authorization": "Bearer " + c.post("/auth/login", json={"email": em, "password": "review-password-1"}).json()["token"]}


def good(kind, todo=""):
    arts = "\n\n".join(f"## ARTICLE {w}\n\n" + " ".join(f"Clause {w.lower()}-{i} of the article." for i in range(160))
                         for w in WORDS[:len(DOCS[kind]["articles"])])
    return f"### Attorney review notes\n- Check.\n\n# TITLE\n\n{todo}\n\n{arts}\n"


class Stub:
    model = "stub-model"

    def __init__(self, text): self.text = text
    async def complete(self, system, messages, max_tokens, *, purpose, temperature=None):
        return Completion(text=self.text, reasoning=None, usage={}, latency_ms=0)


def drafted(monkeypatch, todo=""):
    h = client()
    send(h, "ai_disclosed"); send(h, "consent", answer="yes")
    jid = send(h, "names_submitted", names=["Ana Torres"]).json()["id"]
    for ev, p in (("conflict_auto", {"result": "clear"}), ("conflict_firm", {"result": "cleared"})):
        journey.apply(jid, ev, p, actor="system")
    send(h, "documents_confirmed", codes=["will"])
    for ev in ("scope_approved", "engagement_signed", "engagement_countersigned", "paid"):
        journey.apply(jid, ev, {}, actor="system")
    mid = journey.get_journey(jid)["matter_id"]
    backend.matters[mid]["attorney_reviewer"] = backend.users[ATT]["id"]
    monkeypatch.setattr(drafts, "model_client", lambda: Stub(good("will", todo)))
    jobs.HANDLERS["draft_documents"]({"payload": {"journey_id": jid}})
    return h, jid


def current(jid):
    q = c.get("/staff/review-queue", headers=login(ATT)).json()
    return next(x for x in q if x["journey_id"] == jid)


def test_the_queue_lists_waiting_drafts_with_their_due_date(monkeypatch):
    h, jid = drafted(monkeypatch)
    row = current(jid)
    assert row["client_name"] == "Ana Torres" and row["due"] and [d["name"] for d in row["documents"]] == ["Last will and testament"]
    assert c.get("/staff/review-queue", headers=h).status_code == 403


def test_only_attorneys_and_admins_read_a_draft(monkeypatch):
    h, jid = drafted(monkeypatch)
    doc = current(jid)["documents"][0]["id"]
    assert c.get(f"/staff/drafts/{doc}", headers=login(ATT)).json()["content"].startswith("**DRAFT")
    assert c.get(f"/staff/drafts/{doc}", headers=staff()).status_code == 403
    assert c.get(f"/staff/drafts/{doc}", headers=h).status_code == 403
    r = c.get(f"/staff/drafts/{doc}/docx", headers=login(ATT))
    assert r.status_code == 200 and r.content[:2] == b"PK"


def test_approval_is_refused_while_anything_is_left_to_complete(monkeypatch):
    h, jid = drafted(monkeypatch, todo="[ATTORNEY TO COMPLETE - executor's address]")
    r = c.post(f"/staff/journeys/{jid}/review", json={"decision": "approve"}, headers=login(ATT))
    assert r.status_code == 409 and "ATTORNEY TO COMPLETE" in r.text


def test_a_revised_version_supersedes_the_draft(monkeypatch):
    h, jid = drafted(monkeypatch, todo="[ATTORNEY TO COMPLETE - executor's address]")
    doc = current(jid)["documents"][0]
    old = c.get(f"/staff/drafts/{doc['id']}", headers=login(ATT)).json()["content"]
    r = c.post(f"/staff/drafts/{doc['id']}/versions", json={"content": old.replace("[ATTORNEY TO COMPLETE - executor's address]", "123 Main St.")},
               headers=login(ATT))
    assert r.status_code == 200
    row = current(jid)["documents"][0]
    assert row["version"] == doc["version"] + 1 and row["id"] != doc["id"]
    assert backend.documents[doc["id"]]["status"] == "Superseded"
    assert c.post(f"/staff/drafts/{doc['id']}/versions", json={"content": "x"}, headers=staff()).status_code == 403


def test_only_the_assigned_attorney_or_an_admin_approves(monkeypatch):
    h, jid = drafted(monkeypatch)
    assert c.post(f"/staff/journeys/{jid}/review", json={"decision": "approve"}, headers=login(OTHER_ATT)).status_code == 403
    assert c.post(f"/staff/journeys/{jid}/review", json={"decision": "approve"}, headers=staff()).status_code == 403
    assert c.post(f"/staff/journeys/{jid}/review", json={"decision": "approve"}, headers=login(ADMIN)).status_code == 200


def test_approving_releases_exactly_the_approved_versions(monkeypatch):
    h, jid = drafted(monkeypatch)
    assert c.get("/documents", headers=h).json() == []
    assert c.post(f"/staff/journeys/{jid}/review", json={"decision": "approve"}, headers=login(ATT)).status_code == 200
    seen = c.get("/documents", headers=h).json()
    assert len(seen) == 1 and seen[0]["status"] == "Attorney Approved" and seen[0]["name"] == "Last will and testament"
    assert "attorney_approved" in state(h)["facts"]
    assert backend.matters[journey.get_journey(jid)["matter_id"]]["stage"] == "6 Client Review"
    assert all(d["journey_id"] != jid for d in c.get("/staff/review-queue", headers=login(ATT)).json())


def test_requesting_changes_needs_a_note_and_keeps_the_draft_private(monkeypatch):
    h, jid = drafted(monkeypatch)
    assert c.post(f"/staff/journeys/{jid}/review", json={"decision": "changes"}, headers=login(ATT)).status_code == 422
    assert c.post(f"/staff/journeys/{jid}/review", json={"decision": "changes", "note": "Revisar el artículo 3"},
                  headers=login(ATT)).status_code == 200
    assert c.get("/documents", headers=h).json() == [] and "attorney_approved" not in state(h)["facts"]
    assert current(jid)["note"] == "Revisar el artículo 3"
