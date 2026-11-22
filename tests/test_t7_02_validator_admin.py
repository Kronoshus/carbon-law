"""T7-02 acceptance tests, written by Opus (t7-tests) before the code. Contract: docs/tickets/T7-02.md
(content.version_errors, `errors` in the detail, 422 invalid on submit/approve/publish). Do not weaken these tests."""
import copy
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
from aprende import content, learn

migrate.run()
c = TestClient(backend.app)
HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures", "content")
PARA, ATT = "t702-para@example.com", "t702-att@example.com"
PW = "t702-password-1"
for _em, _role in ((PARA, "paralegal"), (ATT, "attorney")):
    backend.users[_em] = {"id": str(uuid.uuid4()), "name": _em.split("@")[0], "email": _em, "role": _role,
                          "password_hash": backend.hash_pw(PW), "created_at": datetime.datetime.utcnow().isoformat()}


def login(em):
    return {"Authorization": "Bearer " + c.post("/auth/login", json={"email": em, "password": PW}).json()["token"]}


def fresh():
    """The fixture lesson under a unique id, imported and published (bundle, lesson id)."""
    b = copy.deepcopy(content.load_dir(FIX))
    lid = "t702" + uuid.uuid4().hex[:6]
    lesson = b["lessons"][0]
    lesson.update(id=lid, day=None, unit="bonus")
    for step in lesson["steps"]:
        step["id"] = step["id"].replace("demo", lid, 1)
        for it in step["items"]:
            it["id"] = it["id"].replace("demo", lid, 1)
    content.import_bundle(b, actor="opus")
    for step in lesson["steps"]:
        for it in step["items"]:
            if it.get("legal"):
                content.approve(it["id"], attorney="seed-att@example.com")
            content.publish(it["id"], actor="seed@example.com")
    return b, lid


def item_of(b, iid):
    return next(it for s in b["lessons"][0]["steps"] for it in s["items"] if it["id"] == iid)


def body_of(it):
    return {k: copy.deepcopy(it[k]) for k in ("es", "en", "answer", "source") if k in it}


def draft(iid, body):
    return c.put(f"/staff/content/{iid}/draft", json={"body": body}, headers=login(PARA))


def detail(iid):
    r = c.get(f"/staff/content/{iid}", headers=login(PARA))
    assert r.status_code == 200, r.text
    return r.json()


def live(iid, lid):
    return next(i for i in learn._items(lid) if i["id"] == iid)


def test_the_detail_shows_each_versions_validator_errors():
    b, lid = fresh()
    iid = f"{lid}.1.2"                                                     # a legal choice item, 3 options, answer 2
    body = {**body_of(item_of(b, iid)), "answer": 5, "source": "nope"}
    assert draft(iid, body).status_code == 200
    v = {x["version"]: x for x in detail(iid)["versions"]}
    errs = v[2]["errors"]
    assert any("answer out of range" in e for e in errs), errs
    assert any("nope" in e for e in errs), errs
    assert all(iid in e for e in errs)
    assert v[1]["errors"] == []                                             # the live version is valid


def test_the_errors_are_the_validators_own():
    b, lid = fresh()
    iid = f"{lid}.1.4"                                                     # match
    it = item_of(b, iid)
    body = body_of(it)
    body["en"]["pairs"].pop()                                              # list lengths differ
    body["en"].pop("explain")                                              # es/en fields differ
    mutated = copy.deepcopy(b)
    m = item_of(mutated, iid)
    m["en"]["pairs"].pop()
    m["en"].pop("explain")
    expected = {e for e in content.validate(mutated) if iid in e}
    assert len(expected) >= 2
    assert set(content.version_errors(iid, body)) == expected
    draft(iid, body)
    assert set(detail(iid)["versions"][0]["errors"]) == expected
    legal = f"{lid}.1.1"
    no_source = {k: v for k, v in body_of(item_of(b, legal)).items() if k != "source"}
    m2 = copy.deepcopy(b)
    item_of(m2, legal).pop("source")
    assert set(content.version_errors(legal, no_source)) == {e for e in content.validate(m2) if legal in e} != set()


def test_an_invalid_draft_is_saved_but_cannot_be_submitted():
    b, lid = fresh()
    iid = f"{lid}.1.2"
    r = draft(iid, {**body_of(item_of(b, iid)), "answer": 7})
    assert r.status_code == 200 and r.json()["version"] == 2
    mark = len(backend.audit)
    r = c.post(f"/staff/content/{iid}/submit", headers=login(PARA))
    assert r.status_code == 422, r.text
    out = r.json()
    assert out["error"] == "invalid" and any("answer out of range" in e for e in out["errors"])
    assert detail(iid)["versions"][0]["state"] == "draft"
    assert [a for a in backend.audit[mark:] if a["entity_id"] == iid] == []


def test_the_languages_check_still_comes_first():
    b, lid = fresh()
    iid = f"{lid}.1.2"
    body = {**body_of(item_of(b, iid)), "answer": 7}
    body["en"]["prompt"] = ""
    draft(iid, body)
    r = c.post(f"/staff/content/{iid}/submit", headers=login(PARA))
    assert r.status_code == 422 and r.json() == {"error": "languages", "missing": ["en"]}


def test_the_server_refuses_to_approve_an_invalid_version_even_in_review():
    b, lid = fresh()
    iid = f"{lid}.1.2"
    draft(iid, {**body_of(item_of(b, iid)), "source": "nope"})
    db.execute("UPDATE content_versions SET state = 'review', submitted_by = ? WHERE entry_id = ? AND version = 2",
               (PARA, iid))                                                # reached review some other way
    before = json.loads(live(iid, lid)["es"])
    r = c.post(f"/staff/content/{iid}/approve", json={"version": 2}, headers=login(ATT))
    assert r.status_code == 422 and r.json()["error"] == "invalid", r.text
    assert any("nope" in e for e in r.json()["errors"])
    assert db.query("SELECT 1 FROM content_approvals WHERE item_id = ? AND version = 2", (iid,)) == []
    row = live(iid, lid)
    assert row["version"] == 1 and json.loads(row["es"]) == before and row["source_id"] == "pc-6110"


def test_the_server_refuses_to_publish_an_invalid_non_legal_item():
    b, lid = fresh()
    iid = f"{lid}.1.3"                                                     # truefalse, not legal
    v = draft(iid, {**body_of(item_of(b, iid)), "answer": 1}).json()["version"]   # truefalse needs a bool
    r = c.post(f"/staff/content/{iid}/publish", json={"version": v}, headers=login(PARA))
    assert r.status_code == 422 and r.json()["error"] == "invalid", r.text
    assert live(iid, lid)["version"] == 1 and json.loads(live(iid, lid)["answer"]) is False


def test_a_fixed_version_goes_through():
    b, lid = fresh()
    iid = f"{lid}.1.2"
    draft(iid, {**body_of(item_of(b, iid)), "answer": 9})
    fixed = {**body_of(item_of(b, iid)), "answer": 1}
    fixed["es"]["explain"] = "Una explicación corregida."
    assert draft(iid, fixed).status_code == 200
    assert detail(iid)["versions"][0]["errors"] == []
    assert c.post(f"/staff/content/{iid}/submit", headers=login(PARA)).status_code == 200
    assert c.post(f"/staff/content/{iid}/approve", json={"version": 2}, headers=login(ATT)).status_code == 200
    assert json.loads(live(iid, lid)["answer"]) == 1


def test_datos_and_summaries_have_no_item_rules():
    assert content.version_errors("datos:nombre", {"es": "¿Su nombre?", "en": "Your name?"}) == []
    assert content.version_errors("summary:will.3", {"es": "Regalos.", "en": "Gifts."}) == []
    d = detail("datos:nombre")
    assert all(v["errors"] == [] for v in d["versions"])
