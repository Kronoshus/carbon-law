"""T7-01 acceptance tests, written by Opus (t7-tests) before the code (ticket ★). Contract: docs/tickets/T7-01.md
(content_versions + content_approvals, backend/aprende/content.py functions, /staff/content routes). Do not weaken these
tests: a builder who edits them to pass is rejected."""
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
import yaml
from fastapi.testclient import TestClient

import app as backend
import db
import migrate
from aprende import content, datos, learn

migrate.run()
c = TestClient(backend.app)

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures", "content")
SEED = os.path.join(HERE, "..", "aprende", "content")
PARA, ATT, ADMIN = "t701-para@example.com", "t701-att@example.com", "t701-admin@example.com"
PW = "t701-password-1"
for _em, _role in ((PARA, "paralegal"), (ATT, "attorney"), (ADMIN, "admin")):
    backend.users[_em] = {"id": str(uuid.uuid4()), "name": _em.split("@")[0], "email": _em, "role": _role,
                          "password_hash": backend.hash_pw(PW), "created_at": datetime.datetime.utcnow().isoformat()}


def login(em):
    return {"Authorization": "Bearer " + c.post("/auth/login", json={"email": em, "password": PW}).json()["token"]}


def client():
    r = c.post("/auth/signup", json={"name": "Ana Torres", "email": f"ana-{uuid.uuid4().hex[:8]}@example.com",
                                     "password": "long-secure-password", "source": "aprende", "adult": True})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def fresh_lesson():
    """Import the fixture lesson under a unique id (a bonus lesson, so it never changes other tests' course map)."""
    b = copy.deepcopy(content.load_dir(FIX))
    lid = "t701" + uuid.uuid4().hex[:6]
    lesson = b["lessons"][0]
    lesson.update(id=lid, day=None, unit="bonus")
    for step in lesson["steps"]:
        step["id"] = step["id"].replace("demo", lid, 1)
        for it in step["items"]:
            it["id"] = it["id"].replace("demo", lid, 1)
    content.import_bundle(b, actor="opus")
    return lid


def published(lid, n="1.1"):
    """Publish the imported version 1 with the T4-02 functions (setup only)."""
    iid = f"{lid}.{n}"
    content.approve(iid, attorney="seed-att@example.com")
    content.publish(iid, actor="seed@example.com")
    return iid


def live(iid):
    """The row the client's lesson is served from (learn.py)."""
    lid = iid.rsplit(".", 2)[0]
    return next(i for i in learn._items(lid) if i["id"] == iid)


def explain_body(es, en):
    return {"es": {"text": es}, "en": {"text": en}, "source": "pc-6110"}


def draft(iid, body, h):
    return c.put(f"/staff/content/{iid}/draft", json={"body": body}, headers=h)


def submit(iid, h):
    return c.post(f"/staff/content/{iid}/submit", headers=h)


def approve(iid, version, h):
    return c.post(f"/staff/content/{iid}/approve", json={"version": version}, headers=h)


def publish(iid, version, h):
    return c.post(f"/staff/content/{iid}/publish", json={"version": version}, headers=h)


def detail(iid, h=None):
    r = c.get(f"/staff/content/{iid}", headers=h or login(PARA))
    assert r.status_code == 200, r.text
    return r.json()


def audit_rows(entry_id):
    return [a for a in backend.audit if a["entity"] == "content" and a["entity_id"] == entry_id]


def forget(entry_id):
    """Put a seed entry back the way it was, so later test files see the YAML text."""
    db.execute("DELETE FROM content_versions WHERE entry_id = ?", (entry_id,))
    db.execute("DELETE FROM content_approvals WHERE item_id = ?", (entry_id,))


def test_content_routes_are_staff_only():
    lid = fresh_lesson()
    iid = published(lid)
    h = client()
    calls = [("GET", "/staff/content?kind=item", None), ("GET", f"/staff/content/{iid}", None),
             ("PUT", f"/staff/content/{iid}/draft", {"body": explain_body("x", "y")}),
             ("POST", f"/staff/content/{iid}/submit", None), ("POST", f"/staff/content/{iid}/approve", {"version": 2}),
             ("POST", f"/staff/content/{iid}/publish", {"version": 2}),
             ("GET", f"/staff/content/{iid}/preview?version=1&lang=es", None)]
    for method, path, body in calls:
        kw = {"json": body} if body is not None else {}
        assert c.request(method, path, headers=h, **kw).status_code == 403, path
        assert c.request(method, path, **kw).status_code == 401, path
    assert c.get("/staff/content?kind=item", headers=login(PARA)).status_code == 200
    assert c.get("/staff/content/no-such.1.1", headers=login(PARA)).status_code == 404
    assert c.get("/staff/content?kind=cooking", headers=login(PARA)).status_code == 422


def test_a_paralegal_edits_and_submits_but_cannot_publish_a_legal_item():
    lid = fresh_lesson()
    iid = published(lid)
    before = json.loads(live(iid)["es"])["text"]
    p = login(PARA)
    r = draft(iid, explain_body("Texto nuevo de la asistente.", "The paralegal's new text."), p)
    assert r.status_code == 200, r.text
    assert r.json() == {"entry_id": iid, "version": 2, "state": "draft"}
    r = submit(iid, p)
    assert r.status_code == 200, r.text
    assert r.json() == {"entry_id": iid, "version": 2, "state": "review"}
    r = publish(iid, 2, p)
    assert r.status_code == 403 and r.json()["error"] == "attorney_approval_required"
    assert approve(iid, 2, p).status_code == 403
    assert live(iid)["version"] == 1 and json.loads(live(iid)["es"])["text"] == before       # still the old text
    v2 = detail(iid)["versions"][0]
    assert v2["version"] == 2 and v2["state"] == "review" and v2["submitted_by"] == PARA and v2["created_by"] == PARA
    assert v2["approved_by"] is None
    assert db.query("SELECT 1 FROM content_approvals WHERE item_id = ? AND version = 2", (iid,)) == []


def test_only_the_attorney_approves():
    lid = fresh_lesson()
    iid = published(lid)
    draft(iid, explain_body("Otra versión.", "Another version."), login(PARA))
    submit(iid, login(PARA))
    assert approve(iid, 2, login(ADMIN)).status_code == 403
    r = publish(iid, 2, login(ATT))                          # a legal entry is published only by an approval
    assert r.status_code == 403 and r.json()["error"] == "attorney_approval_required"
    assert live(iid)["version"] == 1
    assert approve(iid, 2, login(ATT)).status_code == 200


def test_the_approval_records_who_when_and_which_version():
    lid = fresh_lesson()
    iid = published(lid)
    draft(iid, explain_body("Versión para aprobar.", "Version to approve."), login(PARA))
    submit(iid, login(PARA))
    start = datetime.datetime.now(datetime.timezone.utc)
    r = approve(iid, 2, login(ATT))
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["entry_id"] == iid and out["version"] == 2 and out["state"] == "published" and out["approved_by"] == ATT
    rows = db.query("SELECT attorney, approved_at FROM content_approvals WHERE item_id = ? AND version = ?", (iid, 2))
    assert len(rows) == 1 and rows[0][0] == ATT
    at = datetime.datetime.fromisoformat(rows[0][1].replace("Z", "+00:00"))
    at = at if at.tzinfo else at.replace(tzinfo=datetime.timezone.utc)
    assert abs((at - start).total_seconds()) < 120
    v = {x["version"]: x for x in detail(iid)["versions"]}
    assert v[2]["approved_by"] == ATT and v[2]["approved_at"] and v[2]["state"] == "published"
    assert v[1]["state"] == "superseded"


def test_editing_a_published_item_makes_a_draft_and_the_old_version_stays_live():
    lid = fresh_lesson()
    iid = published(lid)
    original = json.loads(live(iid)["es"])["text"]
    draft(iid, explain_body("Texto de la versión dos.", "Version two text."), login(PARA))
    d = detail(iid)
    assert d["live"]["version"] == 1 and d["live"]["body"]["es"]["text"] == original
    assert live(iid)["version"] == 1 and json.loads(live(iid)["es"])["text"] == original
    submit(iid, login(PARA))
    assert json.loads(live(iid)["es"])["text"] == original                                   # in review: still live v1
    assert approve(iid, 2, login(ATT)).status_code == 200
    row = live(iid)
    assert row["version"] == 2 and json.loads(row["es"])["text"] == "Texto de la versión dos."
    assert json.loads(row["en"])["text"] == "Version two text."
    draft(iid, explain_body("Texto de la versión tres.", "Version three text."), login(PARA))
    assert live(iid)["version"] == 2 and json.loads(live(iid)["es"])["text"] == "Texto de la versión dos."
    lst = {e["entry_id"]: e for e in c.get("/staff/content?kind=item", headers=login(PARA)).json()["entries"]}
    assert lst[iid]["live_version"] == 2 and lst[iid]["pending"] == {"version": 3, "state": "draft"}
    assert lst[iid]["legal"] is True and lst[iid]["lesson_id"] == lid


def test_an_approval_covers_one_version_only():
    lid = fresh_lesson()
    iid = published(lid)
    p = login(PARA)
    draft(iid, explain_body("Leída por el abogado.", "Read by the attorney."), p)
    submit(iid, p)
    r = draft(iid, explain_body("Cambiada después.", "Changed afterwards."), p)               # v2 is frozen in review
    assert r.status_code == 200 and r.json()["version"] == 3
    assert approve(iid, 2, login(ATT)).status_code == 409                                   # v2 is no longer pending
    assert approve(iid, 3, login(ATT)).status_code == 409                                   # v3 was not submitted
    submit(iid, p)
    assert approve(iid, 3, login(ATT)).status_code == 200
    assert approve(iid, 3, login(ATT)).status_code == 409                                   # already published
    assert json.loads(live(iid)["es"])["text"] == "Cambiada después."
    states = {x["version"]: x["state"] for x in detail(iid)["versions"]}
    assert states == {1: "superseded", 2: "superseded", 3: "published"}


def test_both_languages_are_required_to_publish():
    assert content.missing_languages({"es": {"text": "Hola"}, "en": {"text": "  "}}) == ["en"]
    assert content.missing_languages({"en": "Hello"}) == ["es"]
    assert content.missing_languages({"es": {"options": ["Uno", ""]}, "en": {"options": ["One", "Two"]}}) == ["es"]
    assert content.missing_languages({"es": "Hola", "en": "Hello"}) == []
    lid = fresh_lesson()
    iid = published(lid)
    p = login(PARA)
    assert draft(iid, explain_body("Solo en español.", ""), p).status_code == 200            # a draft may lack one
    r = submit(iid, p)
    assert r.status_code == 422 and r.json() == {"error": "languages", "missing": ["en"]}
    assert draft(iid, {"en": {"text": "Only English."}, "source": "pc-6110"}, p).status_code == 200
    r = submit(iid, p)
    assert r.status_code == 422 and r.json()["missing"] == ["es"]
    assert live(iid)["version"] == 1
    tf = f"{lid}.1.3"                                                                       # not legal
    body = {"es": {"statement": "Un testamento necesita notario.", "explain": "No es obligatorio."},
            "en": {"statement": "", "explain": "It is not required."}, "answer": False}
    v = draft(tf, body, p).json()["version"]
    r = publish(tf, v, p)
    assert r.status_code == 422 and r.json() == {"error": "languages", "missing": ["en"]}


def test_a_non_legal_item_is_published_by_staff_without_approval():
    lid = fresh_lesson()
    tf = f"{lid}.1.3"
    p = login(PARA)
    body = {"es": {"statement": "Un testamento siempre necesita notario.", "explain": "No es obligatorio."},
            "en": {"statement": "A will always needs a notary.", "explain": "It is not required."}, "answer": False}
    r = draft(tf, body, p)
    assert r.status_code == 200, r.text
    v = r.json()["version"]
    r = publish(tf, v, p)
    assert r.status_code == 200, r.text
    assert r.json() == {"entry_id": tf, "version": v, "state": "published"}
    row = live(tf)
    assert row["version"] == v and json.loads(row["es"])["statement"] == "Un testamento siempre necesita notario."
    assert db.query("SELECT 1 FROM content_approvals WHERE item_id = ? AND version = ?", (tf, v)) == []


def test_the_legal_flag_cannot_be_edited():
    lid = fresh_lesson()
    iid = published(lid)
    r = draft(iid, {**explain_body("Sin abogado.", "No attorney."), "legal": False}, login(PARA))
    assert r.status_code == 422
    d = detail(iid)
    assert d["legal"] is True and [x["version"] for x in d["versions"]] == [1]


def test_an_imported_item_is_approved_from_the_admin():
    lid = fresh_lesson()
    iid = f"{lid}.1.2"                                                                      # legal, imported, never published
    assert iid not in {i["id"] for i in learn._items(lid)}
    lst = {e["entry_id"]: e for e in c.get("/staff/content?kind=item", headers=login(PARA)).json()["entries"]}
    assert lst[iid]["live_version"] is None and lst[iid]["pending"] == {"version": 1, "state": "review"}
    r = approve(iid, 1, login(ATT))
    assert r.status_code == 200, r.text
    assert live(iid)["version"] == 1
    assert db.query("SELECT attorney FROM content_approvals WHERE item_id = ? AND version = 1", (iid,)) == [(ATT,)]


def test_every_change_is_audited():
    lid = fresh_lesson()
    iid = published(lid)
    draft(iid, explain_body("Auditada.", "Audited."), login(PARA))
    draft(iid, explain_body("Auditada otra vez.", "Audited again."), login(PARA))
    submit(iid, login(PARA))
    approve(iid, 2, login(ATT))
    rows = audit_rows(iid)
    assert [(a["action"], a["actor"]) for a in rows] == [("content_draft", PARA), ("content_draft", PARA),
                                                         ("content_submit", PARA), ("content_approve", ATT)]
    assert all("version=2" in a["detail"] for a in rows)
    detail(iid)                                                                             # reading writes nothing
    c.get(f"/staff/content/{iid}/preview?version=2&lang=es", headers=login(PARA))
    assert len(audit_rows(iid)) == 4
    tf = f"{lid}.1.3"
    body = {"es": {"statement": "Auditada.", "explain": "Sí."}, "en": {"statement": "Audited.", "explain": "Yes."},
            "answer": False}
    v = draft(tf, body, login(PARA)).json()["version"]
    publish(tf, v, login(PARA))
    assert [a["action"] for a in audit_rows(tf)] == ["content_draft", "content_publish"]


def _seed_datos():
    return {q["id"]: q for q in yaml.safe_load(open(os.path.join(SEED, "datos.yaml"), encoding="utf-8"))}


def _fake_journey():
    return {"id": "t701-" + uuid.uuid4().hex[:8], "documents": {"confirmed": ["will"], "tentative": []}}


def _text(qid, lang):
    return next(q["text"] for q in datos.get_datos(_fake_journey(), lang)["questions"] if q["id"] == qid)


def test_datos_text_changes_only_after_the_attorney_approves():
    seed = _seed_datos()
    eid = "datos:legados"
    lst = {e["entry_id"]: e for e in c.get("/staff/content?kind=datos", headers=login(PARA)).json()["entries"]}
    assert set(lst) == {"datos:" + q for q in seed}
    assert all(e["legal"] is True for e in lst.values())
    assert lst["datos:nombre"]["live_version"] == 0 and lst["datos:nombre"]["pending"] is None
    try:
        p = login(PARA)
        new = {"es": "¿Quiere dejar algún objeto especial a una persona o a una organización?",
               "en": "Do you want to leave a special item to a person or an organization?"}
        r = draft(eid, new, p)
        assert r.status_code == 200 and r.json()["version"] == 1, r.text
        assert submit(eid, p).status_code == 200
        r = publish(eid, 1, p)
        assert r.status_code == 403 and r.json()["error"] == "attorney_approval_required"
        assert _text("legados", "es") == seed["legados"]["es"]                                # the seed is still live
        assert approve(eid, 1, login(ATT)).status_code == 200
        assert _text("legados", "es") == new["es"] and _text("legados", "en") == new["en"]
        assert content.live_entries("datos")[eid] == new
        assert _text("nombre", "es") == seed["nombre"]["es"]                                  # other questions untouched
    finally:
        forget(eid)
    assert _text("legados", "es") == seed["legados"]["es"]


def test_summaries_follow_the_same_rules():
    seed = yaml.safe_load(open(os.path.join(SEED, "summaries.yaml"), encoding="utf-8"))
    art3 = next(a for a in seed["will"] if a["article"] == 3)
    eid = "summary:will.3"
    lst = {e["entry_id"]: e for e in c.get("/staff/content?kind=summary", headers=login(PARA)).json()["entries"]}
    assert set(lst) == {f"summary:{doc}.{a['article']}" for doc, arts in seed.items() for a in arts}
    assert lst[eid]["legal"] is True and lst[eid]["live_version"] == 0
    assert content.live_entries("summary")[eid] == {"es": art3["es"], "en": art3["en"]}
    try:
        p = login(PARA)
        new = {"es": "Los regalos especiales y qué pasa si la persona fallece antes.",
               "en": "Special gifts, and what happens if the person dies first."}
        assert draft(eid, {"es": new["es"], "en": ""}, p).status_code == 200
        r = submit(eid, p)
        assert r.status_code == 422 and r.json()["missing"] == ["en"]
        draft(eid, new, p)
        assert submit(eid, p).status_code == 200
        assert publish(eid, 1, p).status_code == 403
        assert content.live_entries("summary")[eid]["es"] == art3["es"]
        assert approve(eid, 1, login(ATT)).status_code == 200
        assert content.live_entries("summary")[eid] == new
    finally:
        forget(eid)


def test_preview_shows_the_draft_as_the_client_would_without_answers():
    lid = fresh_lesson()
    iid = published(lid, "1.2")                                                             # a choice item
    body = {"es": {"prompt": "¿Cuántos testigos firman?", "options": ["Ninguno", "Uno", "Dos"], "explain": "Dos."},
            "en": {"prompt": "How many witnesses sign?", "options": ["None", "One", "Two"], "explain": "Two."},
            "answer": 2, "source": "pc-6110"}
    v = draft(iid, body, login(PARA)).json()["version"]
    r = c.get(f"/staff/content/{iid}/preview?version={v}&lang=es", headers=login(PARA))
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["character"] == "calavera" and out["explain"] == "Dos."
    assert out["item"]["prompt"] == "¿Cuántos testigos firman?" and out["item"]["options"] == ["Ninguno", "Uno", "Dos"]
    assert "answer" not in out["item"] and "explain" not in out["item"]
    en = c.get(f"/staff/content/{iid}/preview?version={v}&lang=en", headers=login(PARA)).json()
    assert en["item"]["prompt"] == "How many witnesses sign?"
    old = c.get(f"/staff/content/{iid}/preview?version=1&lang=es", headers=login(PARA)).json()
    assert old["item"]["prompt"] == "¿Cuántos testigos?"
    s = c.get("/staff/content/summary:will.3/preview?version=0&lang=es", headers=login(PARA))
    assert s.status_code == 200 and s.json()["character"] is None and s.json()["text"]
