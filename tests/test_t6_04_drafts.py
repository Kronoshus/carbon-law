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

import re

from ai import Completion
from carbon_intake import BANNER, DOCS, WORDS
from aprende import datos, drafts, jobs


def good(kind, cite=None):
    cite = cite or sorted(DOCS[kind]["cites"])[0]           # a section on that document's own verified list
    # varied sentences: a draft that repeats one sentence is (rightly) rejected as a loop by carbon_intake.looping
    arts = "\n\n".join(f"## ARTICLE {w}\n\n" + " ".join(f"Clause {w.lower()}-{i} records the client's stated wish number {i}."
                                                          for i in range(60))
                         + f" Probate Code section {cite} applies to article {w.lower()}." for w in WORDS[:len(DOCS[kind]["articles"])])
    return f"### Attorney review notes\n- Check the names.\n\n# TITLE OF THE {kind.upper()}\n\n{arts}\n"


class Stub:
    """Answers each drafting call by document: `replies[kind]` is a list used in order (the last one repeats)."""
    model = "stub-model"

    def __init__(self, replies):
        self.replies, self.calls = replies, []

    async def complete(self, system, messages, max_tokens, *, purpose, temperature=None):
        kind = next(k for k in DOCS if f"draft-{k}" in purpose)
        self.calls.append({"kind": kind, "system": system, "messages": messages})
        seq = self.replies[kind]
        text = seq.pop(0) if len(seq) > 1 else seq[0]
        return Completion(text=text, reasoning=None, usage={}, latency_ms=0)


@pytest.fixture
def alerts(monkeypatch):
    sent = []
    monkeypatch.setattr(drafts, "notify_staff", lambda title, message: sent.append(message))
    return sent


def paid(codes=("will",)):
    h = client()
    send(h, "ai_disclosed"); send(h, "consent", answer="yes")
    jid = send(h, "names_submitted", names=["Ana Torres"]).json()["id"]
    journey.apply(jid, "conflict_auto", {"result": "clear"}, actor="system")
    journey.apply(jid, "conflict_firm", {"result": "cleared"}, actor="staff@example.com")
    send(h, "documents_confirmed", codes=list(codes))
    j = journey.get_journey(jid)
    datos.save(j, "nombre", answer="Ana María Torres")
    datos.save(j, "albacea", answer="Mi hermana Rosa Pérez")
    for ev in ("scope_approved", "engagement_signed", "engagement_countersigned", "paid"):
        journey.apply(jid, ev, {}, actor="system")
    return h, jid


def run(monkeypatch, jid, stub):
    monkeypatch.setattr(drafts, "model_client", lambda: stub)
    jobs.HANDLERS["draft_documents"]({"payload": {"journey_id": jid}})


def mine(jid):
    mid = journey.get_journey(jid)["matter_id"]
    return [d for d in backend.documents.values() if d.get("matter_id") == mid]


def test_drafts_are_attorney_only_and_the_matter_moves_to_review(monkeypatch, alerts):
    h, jid = paid(("will", "trust"))
    run(monkeypatch, jid, Stub({"will": [good("will")], "trust": [good("trust")]}))
    docs = mine(jid)
    assert {d["name"] for d in docs} == {"Pour-over will", "Revocable living trust"}
    assert all(d["attorney_only"] and d["status"] == "Attorney Review" for d in docs)
    assert all(BANNER in d["content"] and "Citation check: every statute cited is on the verified list." in d["content"] for d in docs)
    assert "drafts_ready" in state(h)["facts"]
    assert backend.matters[journey.get_journey(jid)["matter_id"]]["stage"] == "5 Review Queue"
    assert c.get("/documents", headers=h).json() == []                         # nothing reaches the client


def test_the_will_knows_about_the_trust_and_the_clients_words_are_fenced(monkeypatch, alerts):
    h, jid = paid(("will", "trust"))
    stub = Stub({"will": [good("will")], "trust": [good("trust")]})
    run(monkeypatch, jid, stub)
    ask = next(c_ for c_ in stub.calls if c_["kind"] == "will")["messages"][0]["content"]
    assert "living trust" in ask                                               # pour-over: the will is told about the trust
    assert "<client_data>" in ask and "Ana María Torres" in ask and "Mi hermana Rosa Pérez" in ask


def test_the_ai_record_holds_hashes_only(monkeypatch, alerts):
    h, jid = paid()
    run(monkeypatch, jid, Stub({"will": [good("will")]}))
    rec = mine(jid)[0]["ai_record"]
    assert set(rec) == {"provider", "model", "timestamp", "workflow", "request_hash", "response_hash", "build_id"}
    assert "Ana" not in json.dumps(rec) and "Rosa" not in json.dumps(rec)


def test_an_unverified_citation_is_flagged_on_the_draft(monkeypatch, alerts):
    h, jid = paid()
    run(monkeypatch, jid, Stub({"will": [good("will", cite="9999")]}))
    assert "Citation check: NOT VERIFIED" in mine(jid)[0]["content"] and "9999" in mine(jid)[0]["content"]


def test_a_malformed_reply_writes_nothing_for_that_document_and_keeps_the_others(monkeypatch, alerts):
    h, jid = paid(("will", "ahcd"))
    stub = Stub({"will": [good("will")], "ahcd": ["Lo siento, no puedo."]})
    run(monkeypatch, jid, stub)
    assert {d["name"] for d in mine(jid)} == {"Last will and testament"}
    assert "drafts_ready" not in state(h)["facts"]
    assert len(alerts) == 1 and "ahcd" in alerts[0] and "Ana" not in alerts[0]
    assert len([c_ for c_ in stub.calls if c_["kind"] == "ahcd"]) >= 2          # one retry before giving up


def test_a_short_first_draft_is_retried_and_the_retry_accepted(monkeypatch, alerts):
    h, jid = paid()
    short = re.sub(r"(Clause [a-z]+-\d+ records the client's stated wish number \d+\. ?)+", "Short. ", good("will"))
    run(monkeypatch, jid, Stub({"will": [short, short]}))                        # strict try fails on length; lenient accepts
    assert len(mine(jid)) == 1 and "drafts_ready" in state(h)["facts"]


def test_running_the_job_twice_does_not_duplicate_drafts(monkeypatch, alerts):
    h, jid = paid()
    run(monkeypatch, jid, Stub({"will": [good("will")]}))
    run(monkeypatch, jid, Stub({"will": [good("will")]}))
    assert len(mine(jid)) == 1


def test_a_looping_draft_is_rejected(monkeypatch, alerts):
    h, jid = paid()
    loop = good("will").replace("## ARTICLE TWO", "Repito esta frase sin parar. " * 50 + "\n\n## ARTICLE TWO")
    run(monkeypatch, jid, Stub({"will": [loop]}))
    assert mine(jid) == [] and len(alerts) == 1
