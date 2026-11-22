"""The attorney cannot approve a draft that cites a section outside the verified list (release criterion: drafts cite only verified sections).

Found by the guardrail audit (~/work/cl-reports/audit-guardrails.md). Fictional people only. (Opus)"""
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
import db
import migrate
from aprende import conflicts, journey

migrate.run()
c = TestClient(backend.app)
PASSWORD = "audit-fix-password"
ATTORNEY = "audit-fix-attorney@example.com"
backend.users[ATTORNEY] = {"id": str(uuid.uuid4()), "name": "Audit Attorney", "email": ATTORNEY, "role": "attorney",
                           "password_hash": backend.hash_pw(PASSWORD), "created_at": datetime.datetime.utcnow().isoformat()}


def login(email):
    return {"Authorization": "Bearer " + c.post("/auth/login", json={"email": email, "password": PASSWORD}).json()["token"]}


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


def consented(h, names=("Ana Torres",)):
    send(h, "ai_disclosed"); send(h, "consent", answer="yes")
    r = send(h, "names_submitted", names=list(names))
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture
def firm_list():
    """The firm's conflict list for one test; the list in force before is put back afterwards."""
    before = conflicts.get_list()
    yield lambda *names: conflicts.replace_list("name\n" + "\n".join(names) + "\n") if names else conflicts.delete_list()
    conflicts.replace_list("name\n" + "\n".join(before) + "\n") if before else conflicts.delete_list()

from ai import Completion
from aprende import drafts, jobs
from carbon_intake import DOCS, WORDS


class StubModel:
    model = "stub-model"

    def __init__(self, text):
        self.text = text

    async def complete(self, system, messages, max_tokens, *, purpose, temperature=None):
        return Completion(text=self.text, reasoning=None, usage={}, latency_ms=0)


def mark():
    return "aud" + uuid.uuid4().hex[:12]


def cleared_with_letter(h):
    jid = consented(h)
    journey.apply(jid, "conflict_auto", {"result": "clear"}, actor="system")
    journey.apply(jid, "conflict_firm", {"result": "cleared"}, actor="staff@example.com")
    send(h, "documents_confirmed", codes=["will"])
    return jid


def full_draft(kind, marker, cite=None):
    cite = cite or sorted(DOCS[kind]["cites"])[0]
    arts = "\n\n".join(f"## ARTICLE {w}\n\n" + " ".join(f"Clause {w.lower()}-{i} records the client's stated wish number {i}."
                                                          for i in range(60))
                         + f" Probate Code section {cite} applies to article {w.lower()}." for w in WORDS[:len(DOCS[kind]["articles"])])
    return f"### Attorney review notes\n- Check the names ({marker}).\n\n# LAST WILL AND TESTAMENT OF ANA TORRES\n\n{arts}\n"


def drafted(monkeypatch, marker, cite=None):
    h = client()
    jid = cleared_with_letter(h)
    for ev in ("scope_approved", "engagement_signed", "engagement_countersigned", "paid"):
        journey.apply(jid, ev, {}, actor="system")
    backend.matters[journey.get_journey(jid)["matter_id"]]["attorney_reviewer"] = backend.users[ATTORNEY]["id"]
    monkeypatch.setattr(drafts, "model_client", lambda: StubModel(full_draft("will", marker, cite)))
    jobs.HANDLERS["draft_documents"]({"payload": {"journey_id": jid}})
    docs = [d for d in backend.documents.values() if d.get("journey_id") == jid]
    assert len(docs) == 1 and marker in docs[0]["content"]
    return h, jid, docs[0]["id"]


def test_a_draft_citing_an_unverified_section_is_flagged_and_cannot_be_approved(monkeypatch, firm_list):
    firm_list()
    h, jid, doc = drafted(monkeypatch, mark(), cite="9999")
    assert "Citation check: NOT VERIFIED" in backend.documents[doc]["content"]
    r = c.post(f"/staff/journeys/{jid}/review", json={"decision": "approve"}, headers=login(ATTORNEY))
    assert r.status_code == 409 and "attorney_approved" not in state(h)["facts"]
    assert c.get("/review/documents", headers=h).status_code == 409
    # the attorney's corrected version, citing only verified sections, can be approved
    fixed = backend.documents[doc]["content"].replace("section 9999", "section " + sorted(DOCS["will"]["cites"])[0])
    fixed = fixed.replace(next(line for line in fixed.splitlines() if "Citation check" in line), "")
    assert c.post(f"/staff/drafts/{doc}/versions", json={"content": fixed}, headers=login(ATTORNEY)).status_code == 200
    assert c.post(f"/staff/journeys/{jid}/review", json={"decision": "approve"}, headers=login(ATTORNEY)).status_code == 200
