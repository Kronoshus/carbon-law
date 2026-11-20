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

ATT = "rev6-att@example.com"
backend.users[ATT] = {"id": str(uuid.uuid4()), "name": "Pankaj Raval", "email": ATT, "role": "attorney",
                      "password_hash": backend.hash_pw("review-password-6"), "created_at": datetime.datetime.utcnow().isoformat()}
att = lambda: {"Authorization": "Bearer " + c.post("/auth/login", json={"email": ATT, "password": "review-password-6"}).json()["token"]}


def good(kind):
    arts = "\n\n".join(f"## ARTICLE {w}\n\n" + " ".join(f"Clause {w.lower()}-{i} of the article." for i in range(160))
                         for w in WORDS[:len(DOCS[kind]["articles"])])
    return f"### Attorney review notes\n- Check.\n\n# TITLE\n\n<script>window.x=1</script>\n\n{arts}\n"


class Stub:
    model = "stub-model"
    async def complete(self, system, messages, max_tokens, *, purpose, temperature=None):
        kind = purpose.rsplit("-", 1)[1]
        return Completion(text=good(kind), reasoning=None, usage={}, latency_ms=0)


def approved(monkeypatch, codes=("will", "ahcd")):
    h = client()
    send(h, "ai_disclosed"); send(h, "consent", answer="yes")
    jid = send(h, "names_submitted", names=["Ana Torres"]).json()["id"]
    for ev, p in (("conflict_auto", {"result": "clear"}), ("conflict_firm", {"result": "cleared"})):
        journey.apply(jid, ev, p, actor="system")
    send(h, "documents_confirmed", codes=list(codes))
    for ev in ("scope_approved", "engagement_signed", "engagement_countersigned", "paid"):
        journey.apply(jid, ev, {}, actor="system")
    backend.matters[journey.get_journey(jid)["matter_id"]]["attorney_reviewer"] = backend.users[ATT]["id"]
    monkeypatch.setattr(drafts, "model_client", lambda: Stub())
    jobs.HANDLERS["draft_documents"]({"payload": {"journey_id": jid}})
    assert c.post(f"/staff/journeys/{jid}/review", json={"decision": "approve"}, headers=att()).status_code == 200
    return h, jid


def docs(h, lang="es"):
    r = c.get(f"/review/documents?lang={lang}", headers=h)
    assert r.status_code == 200, r.text
    return r.json()["documents"]


def test_nothing_to_review_before_the_attorney_approves():
    h = client()
    r = c.get("/review/documents", headers=h)
    assert r.status_code == 409 and r.json()["missing"] == ["may_see_documents"]


def test_the_client_sees_only_the_approved_versions_with_their_plain_summary(monkeypatch):
    h, jid = approved(monkeypatch)
    ds = docs(h)
    assert sorted(d["name"] for d in ds) == ["Advance health care directive", "Last will and testament"]
    will = next(d for d in ds if d["name"] == "Last will and testament")
    assert will["decision"] is None and will["version"] == 1
    assert len(will["summary"]) == len(DOCS["will"]["articles"])
    assert will["summary"][6]["text"].startswith("Su albacea")                     # article 7, in plain Spanish
    assert docs(h, "en")[0]["summary"][0]["text"] != will["summary"][0]["text"]


def test_all_documents_ok_confirms_and_moves_to_signing_preparation(monkeypatch):
    h, jid = approved(monkeypatch)
    ids = [d["id"] for d in docs(h)]
    assert c.post(f"/review/documents/{ids[0]}", json={"decision": "ok"}, headers=h).status_code == 200
    assert "client_confirmed" not in state(h)["facts"]
    c.post(f"/review/documents/{ids[1]}", json={"decision": "ok"}, headers=h)
    assert "client_confirmed" in state(h)["facts"]
    assert backend.matters[journey.get_journey(jid)["matter_id"]]["stage"] == "7 Signing Preparation"
    assert state(h)["gates"]["may_book_signing"] is True


def test_a_change_request_goes_to_the_firms_records(monkeypatch):
    h, jid = approved(monkeypatch)
    will = next(d for d in docs(h) if d["name"] == "Last will and testament")
    assert c.post(f"/review/documents/{will['id']}", json={"decision": "change", "change_type": "Fiduciary change"},
                  headers=h).status_code == 422                                   # a note is required
    assert c.post(f"/review/documents/{will['id']}", json={"decision": "change", "change_type": "Pizza", "note": "x"},
                  headers=h).status_code == 422
    r = c.post(f"/review/documents/{will['id']}", json={"decision": "change", "change_type": "Fiduciary change",
                                                        "note": "Quiero que mi hermana Rosa sea la albacea."}, headers=h)
    assert r.status_code == 200
    mid = journey.get_journey(jid)["matter_id"]
    cr = [x for x in backend.changes if x["matter_id"] == mid]
    assert len(cr) == 1 and cr[0]["change_type"] == "Fiduciary change" and cr[0]["affected_documents"] == "Last will and testament"
    assert any(t["matter_id"] == mid for t in backend.tasks.values())
    assert "changes_requested" in state(h)["facts"] and backend.matters[mid]["stage"] == "5 Review Queue"
    assert next(d for d in docs(h) if d["id"] == will["id"])["decision"] == "change"


def test_a_revision_replaces_the_old_version_only_after_re_approval(monkeypatch):
    h, jid = approved(monkeypatch)
    will = next(d for d in docs(h) if d["name"] == "Last will and testament")
    c.post(f"/review/documents/{will['id']}", json={"decision": "change", "change_type": "Fiduciary change", "note": "Rosa"}, headers=h)
    r = c.post(f"/staff/drafts/{will['id']}/versions", json={"content": "**DRAFT**\n\n# LAST WILL v2\n\nRosa is executor."}, headers=att())
    assert r.status_code == 200
    seen = next(d for d in docs(h) if d["name"] == "Last will and testament")
    assert seen["version"] == 1                                                 # still the approved one while the attorney revises
    assert c.post(f"/staff/journeys/{jid}/review", json={"decision": "approve"}, headers=att()).status_code == 200
    seen = next(d for d in docs(h) if d["name"] == "Last will and testament")
    assert seen["version"] == 2 and "Rosa is executor." in seen["content"] and seen["decision"] is None
    assert backend.documents[will["id"]]["status"] == "Superseded"


def test_a_client_cannot_decide_on_someone_elses_document(monkeypatch):
    h, jid = approved(monkeypatch)
    other = client()
    doc = docs(h)[0]["id"]
    assert c.post(f"/review/documents/{doc}", json={"decision": "ok"}, headers=other).status_code in (404, 409)


def queue_row(jid):
    return next((r for r in c.get("/staff/review-queue", headers=att()).json() if r["journey_id"] == jid), None)


def test_after_a_change_request_the_attorney_finds_the_journey_in_the_queue_and_revises_it(monkeypatch):
    """Spec 6.1 day 10: "Requested changes go to the attorney (2 business days)". The review queue is where the attorney
    works, so the asked-for document is listed there until a revised version is approved."""
    h, jid = approved(monkeypatch)
    assert queue_row(jid) is None                                                # approved: nothing waits
    will = next(d for d in docs(h) if d["name"] == "Last will and testament")
    c.post(f"/review/documents/{will['id']}", json={"decision": "change", "change_type": "Fiduciary change",
                                                    "note": "Quiero que mi hermana Rosa sea la albacea."}, headers=h)
    row = queue_row(jid)
    assert row is not None and [d["id"] for d in row["documents"]] == [will["id"]]
    old = c.get(f"/staff/drafts/{will['id']}", headers=att()).json()["content"]
    new = c.post(f"/staff/drafts/{will['id']}/versions", json={"content": old + "\n\nExecutor: Rosa Pérez.\n"}, headers=att()).json()
    assert [d["id"] for d in queue_row(jid)["documents"]] == [new["id"]]       # the revision now waits for approval
    assert c.post(f"/staff/journeys/{jid}/review", json={"decision": "approve"}, headers=att()).status_code == 200
    assert queue_row(jid) is None
    assert next(d for d in docs(h) if d["name"] == "Last will and testament")["version"] == 2
