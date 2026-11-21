"""T7-07 acceptance tests, written by Opus (t7-tests) before the code. Contract: docs/tickets/T7-07.md and
tests/rbac_matrix.yaml. Generated from app.routes: a new Aprende route without a matrix entry fails, and so does a new
state-changing route without a success step below. Do not weaken these tests; extend the matrix and STEPS instead."""
import base64
import datetime
import json
import os
import re
import sys
import tempfile
import time
import hashlib
import hmac
import uuid

os.environ.setdefault("DATABASE_URL", "")
os.environ.setdefault("CARBON_DB_PATH", tempfile.mktemp(suffix=".db"))
sys.path.insert(0, "backend")

import pytest
import yaml
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import app as backend
import db
import migrate
from ai import Completion
from ai.stub import StubClient
from aprende import APRENDE_PREFIXES, booking, conflicts, content, drafts, jobs, journey, payments, review, signing
from aprende import chat as chatmod
from carbon_intake import DOCS, WORDS

migrate.run()
c = TestClient(backend.app)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MATRIX = yaml.safe_load(open(os.path.join(HERE, "rbac_matrix.yaml"), encoding="utf-8"))
STAFF_ROLES = ("paralegal", "attorney", "admin")
ROLES = ("anonymous", "client") + STAFF_ROLES
PW = "t707-password-1"
EMAIL = {"paralegal": "t707-para@example.com", "attorney": "t707-att@example.com", "admin": "t707-admin@example.com"}
for _role, _em in EMAIL.items():
    backend.users[_em] = {"id": str(uuid.uuid4()), "name": "Pankaj Raval" if _role == "attorney" else _em.split("@")[0],
                          "email": _em, "role": _role, "password_hash": backend.hash_pw(PW),
                          "created_at": datetime.datetime.utcnow().isoformat()}

_bundle = content.load_dir(os.path.join(HERE, "fixtures", "learn"))
if not db.query("SELECT id FROM content_lessons WHERE id = 'lw'"):
    content.import_bundle(_bundle, actor="opus")
for _l in _bundle["lessons"]:
    for _s in _l["steps"]:
        for _it in _s["items"]:
            if _it.get("legal"):
                content.approve(_it["id"], attorney="attorney@example.com")
            content.publish(_it["id"], actor="paralegal@example.com")


def login(role):
    return {"Authorization": "Bearer " + c.post("/auth/login", json={"email": EMAIL[role], "password": PW}).json()["token"]}


def signup(name="Ana Torres"):
    r = c.post("/auth/signup", json={"name": name, "email": f"c-{uuid.uuid4().hex[:8]}@example.com",
                                     "password": "long-secure-password", "source": "aprende", "adult": True})
    assert r.status_code == 200, r.text
    h = {"Authorization": "Bearer " + r.json()["token"]}
    return h, c.get("/journey", headers=h).json()["id"]


def send(h, type_, **payload):
    return c.post("/journey/events", json={"type": type_, "payload": payload}, headers=h)


def far_along(h, jid):
    """Every gate open up to booking the signing (facts recorded directly; the routes are exercised in STEPS)."""
    send(h, "ai_disclosed"); send(h, "consent", answer="yes"); send(h, "names_submitted", names=["Ana Torres"])
    journey.apply(jid, "conflict_auto", {"result": "clear"}, actor="system")
    journey.apply(jid, "conflict_firm", {"result": "cleared"}, actor="system")
    send(h, "documents_confirmed", codes=["will"])
    for ev in ("scope_approved", "engagement_signed", "engagement_countersigned", "paid", "drafts_ready",
               "attorney_approved", "client_confirmed"):
        journey.apply(jid, ev, {}, actor="system")


# ---------------------------------------------------------------- the routes, from app.routes

def aprende_routes():
    out = {}
    for r in backend.app.routes:
        if isinstance(r, APIRoute) and any(r.path.startswith(p) for p in APRENDE_PREFIXES):
            for m in sorted(r.methods - {"HEAD"}):
                out[f"{m} {r.path}"] = r
    return out


ROUTES = aprende_routes()
CHANGES = {k for k in ROUTES if k.split(" ")[0] in ("POST", "PUT", "PATCH", "DELETE")}


def test_every_aprende_route_has_an_entry():
    missing = sorted(set(ROUTES) - set(MATRIX))
    stale = sorted(k for k, v in MATRIX.items() if k not in ROUTES and not v.get("ticket"))
    assert missing == [], f"routes with no entry in tests/rbac_matrix.yaml: {missing}"
    assert stale == [], f"entries for routes that do not exist: {stale}"
    for k, v in MATRIX.items():
        roles = v["roles"]
        assert roles in ("client", "staff", "signed_in", "public") or (isinstance(roles, list) and set(roles) <= set(STAFF_ROLES)), k


# ---------------------------------------------------------------- the access matrix

QUERY = {"codes": "will", "session_id": "cs_test_x", "kind": "signing", "from": "2027-06-08", "days": "1",
         "lang": "es", "version": "1"}


def allowed(entry, role):
    roles = entry["roles"]
    if roles == "public":
        return True
    if role == "anonymous":
        return False
    if roles == "signed_in":
        return True
    if roles == "client":
        return role == "client"
    if roles == "staff":
        return role in STAFF_ROLES
    return role in roles


OTHER_BODY = {"PATCH /booking/{booking_id}": {"start": "2027-09-14T19:00:00Z"}, "POST /review/documents/{doc_id}": {"decision": "ok"}}


def request(key, headers, params=None, body=None):
    method, path = key.split(" ", 1)
    route = ROUTES[key]
    path = re.sub(r"\{([^}:]+)(:path)?\}", lambda m: (params or {}).get(m.group(1), "x"), path)
    query = {}
    for f in route.dependant.query_params:
        if getattr(f, "required", False):
            assert f.alias in QUERY, f"{key}: add a value for the required query parameter {f.alias!r} to QUERY"
            query[f.alias] = QUERY[f.alias]
    kw = {"params": query, "headers": headers}
    if method in ("POST", "PUT", "PATCH"):
        kw["json"] = {} if body is None else body
    return c.request(method, path, **kw)


class FakeStripe:
    def __init__(self):
        self.sessions = []

    def create_checkout_session(self, *, amount_cents, currency, description, metadata, success_url, cancel_url, idempotency_key):
        sid = f"cs_test_{uuid.uuid4().hex}"
        self.sessions.append({"id": sid, "amount_cents": amount_cents, "metadata": metadata})
        return {"id": sid, "url": "https://checkout.stripe.test/1"}


@pytest.fixture(scope="module")
def people():
    """The signed-in callers, and another client's resources for `other` routes."""
    a, ajid = signup("Ana Torres")
    far_along(a, ajid)
    b, bjid = signup("Luis Torres")
    far_along(b, bjid)
    marker = "B-ONLY-" + uuid.uuid4().hex
    bid = str(uuid.uuid4())
    db.execute("INSERT INTO bookings (id, journey_id, kind, start_utc, end_utc, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
               (bid, bjid, "signing", "2027-09-14T17:00:00Z", "2027-09-14T18:00:00Z", "active", journey._now_iso()))
    doc = str(uuid.uuid4())
    backend.documents[doc] = {"id": doc, "journey_id": bjid, "matter_id": journey.get_journey(bjid).get("matter_id"),
                              "status": "Attorney Approved", "name": "Last will and testament", "version": 1,
                              "content": marker, "attorney_only": False}
    did = signing.store_executed(bjid, [{"name": "Testamento", "filename": "will.pdf",
                                         "content_b64": base64.b64encode(marker.encode()).decode()}], "seed")[0]
    heads = {"anonymous": {}, "client": a, **{r: login(r) for r in STAFF_ROLES}}
    mp = pytest.MonkeyPatch()                                  # no Stripe, no model, no email from an allowed call
    mp.setattr(payments, "stripe_client", lambda: FakeStripe())
    mp.setattr(chatmod, "model_client", lambda: StubClient(text="Hola."))
    mp.setattr(booking, "send_confirmation", lambda *a, **k: True)
    yield {"heads": heads, "other": {"booking_id": bid, "doc_id": doc, "did": did}, "marker": marker}
    mp.undo()
    backend.documents.pop(doc, None)


@pytest.mark.parametrize("key", sorted(ROUTES))
def test_the_access_matrix(key, people):
    entry = MATRIX.get(key)
    assert entry, f"{key} has no entry in tests/rbac_matrix.yaml"
    wrong = []
    for role in ROLES:
        mark = len(backend.audit)
        r = request(key, people["heads"][role])
        if r.status_code >= 500:
            wrong.append((role, r.status_code, "server error"))
        elif allowed(entry, role):
            if r.status_code in (401, 403):
                wrong.append((role, r.status_code, "should be allowed"))
        else:
            want = 401 if role == "anonymous" else 403
            if r.status_code != want:
                wrong.append((role, r.status_code, f"should be {want}"))
            elif len(backend.audit) != mark:
                wrong.append((role, r.status_code, "a refused request wrote an audit row"))
    if entry.get("other"):
        r = request(key, people["heads"]["client"], people["other"], OTHER_BODY.get(key, {}))
        if r.status_code not in (403, 404) or people["marker"] in r.text:
            wrong.append(("client_other", r.status_code, "another client's resource must be 403/404"))
    assert wrong == [], wrong


# ---------------------------------------------------------------- every state-changing route writes an audit row

SECRET = "whsec_t707"


class DraftStub:
    model = "stub-model"

    async def complete(self, system, messages, max_tokens, *, purpose, temperature=None):
        arts = "\n\n".join(f"## ARTICLE {w}\n\n" + " ".join(f"Clause {w.lower()}-{i} of the article." for i in range(160))
                           for w in WORDS[:len(DOCS["will"]["articles"])])
        return Completion(text=f"### Attorney review notes\n- Check.\n\n# TITLE\n\n{arts}\n", reasoning=None, usage={}, latency_ms=0)


def stripe_headers(raw):
    t = int(time.time())
    sig = hmac.new(SECRET.encode(), f"{t}.".encode() + raw, hashlib.sha256).hexdigest()
    return {"Stripe-Signature": f"t={t},v1={sig}", "Content-Type": "application/json"}


def test_every_state_changing_route_writes_an_audit_row(monkeypatch):
    fake = FakeStripe()
    monkeypatch.setattr(payments, "stripe_client", lambda: fake)
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", SECRET)
    monkeypatch.delenv("STRIPE_MODE", raising=False)
    monkeypatch.setattr(drafts, "model_client", lambda: DraftStub())
    monkeypatch.setattr(booking, "send_confirmation", lambda *a, **k: True)
    monkeypatch.setattr(chatmod, "model_client", lambda: StubClient(
        text="Esa es una pregunta para el abogado Raval. [ATTORNEY_QUESTION: ¿Puede mi hijo ser albacea?]"))
    att, para, adm = login("attorney"), login("paralegal"), login("admin")
    hit = {}

    def call(key, method, path, headers, **kw):
        mark = len(backend.audit)
        r = c.request(method, path, headers=headers, **kw)
        assert 200 <= r.status_code < 300, f"{key}: {r.status_code} {r.text[:300]}"
        hit[key] = backend.audit[mark:]
        return r

    holidays = json.loads((db.query("SELECT value_json FROM settings WHERE key = 'holidays'") or [("[]",)])[0][0])
    names = conflicts.get_list()
    try:
        es = open(os.path.join(ROOT, "aprende", "content", "engagement", "es.md"), encoding="utf-8").read()
        en = open(os.path.join(ROOT, "aprende", "content", "engagement", "en.md"), encoding="utf-8").read()
        call("PUT /staff/firm-profile", "PUT", "/staff/firm-profile", att, json={"bar_number": "000000",
             "costs_line": {"es": "Sin costos.", "en": "No costs."}, "refund_policy": {"es": "Prueba.", "en": "Test."},
             "data_promise": {"es": "Prueba.", "en": "Test."}})
        tid = call("POST /staff/engagement-templates", "POST", "/staff/engagement-templates", att, json={"es": es, "en": en}).json()["id"]
        call("POST /staff/engagement-templates/{tid}/approve", "POST", f"/staff/engagement-templates/{tid}/approve", att)
        call("PUT /staff/availability", "PUT", "/staff/availability", para, json={"hours": {d: [["08:00", "18:00"]] for d in
             ("mon", "tue", "wed", "thu", "fri")}, "slot_minutes": {"signing": 60, "consultation": 30}})
        call("PUT /staff/holidays", "PUT", "/staff/holidays", para, json={"dates": holidays})
        call("POST /conflicts/list", "POST", "/conflicts/list", para, json={"csv": "name\n" + "\n".join(names + ["Zacarías Prueba"])})
        call("PATCH /characters/{char_id}", "PATCH", "/characters/pinata", para, json={"enabled": True})
        call("PUT /staff/payments/live-approval", "PUT", "/staff/payments/live-approval", adm, json={"approved": False})

        h, jid = signup("Ana Torres")
        call("POST /journey/events", "POST", "/journey/events", h, json={"type": "ai_disclosed", "payload": {}})
        send(h, "consent", answer="yes"); send(h, "names_submitted", names=["Ana Torres"])
        call("POST /conflicts/{journey_id}/decision", "POST", f"/conflicts/{jid}/decision", para, json={"result": "cleared"})
        call("PUT /progress/reminders", "PUT", "/progress/reminders", h, json={"enabled": True, "local_time": "18:00"})
        if "PUT /progress/push" in ROUTES:                                             # T8-03
            call("PUT /progress/push", "PUT", "/progress/push", h, json={"endpoint": "https://fcm.googleapis.com/fcm/send/t707",
                 "keys": {"p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA", "auth": "tBHItJI5svbpez7KI4CCXg"}, "lang": "es"})
            call("DELETE /progress/push", "DELETE", "/progress/push", h)
        c.get("/learn/lessons/lw?lang=es", headers=h)
        call("POST /learn/attempts", "POST", "/learn/attempts", h, json={"item_id": "lw.1.2", "answer": 2})
        for iid, a in (("lw.1.3", False), ("lw.1.4", {"0": "0", "1": "1", "2": "2"}), ("lw.1.5", ["0", "1", "2"])):
            c.post("/learn/attempts", json={"item_id": iid, "answer": a}, headers=h)
        call("POST /learn/lessons/{lesson_id}/complete", "POST", "/learn/lessons/lw/complete", h)
        call("PUT /datos/{question_id}", "PUT", "/datos/nombre", h, json={"answer": "Ana Torres"})
        call("POST /chat", "POST", "/chat", h, json={"mode": "learn", "character": "calavera", "lesson_id": "lw",
             "messages": [{"role": "user", "content": "¿Puede mi hijo ser albacea?"}]})
        send(h, "documents_confirmed", codes=["will"])
        call("POST /staff/journeys/{jid}/scope-approval", "POST", f"/staff/journeys/{jid}/scope-approval", att)
        sha = c.get("/engagement?lang=es", headers=h).json()["sha256"]
        call("POST /engagement/sign", "POST", "/engagement/sign", h, json={"name": "Ana Torres", "accept": True, "sha256": sha})
        call("POST /staff/journeys/{jid}/engagement/countersign", "POST", f"/staff/journeys/{jid}/engagement/countersign", att)
        call("POST /payments/checkout", "POST", "/payments/checkout", h)
        sess = fake.sessions[-1]
        raw = json.dumps({"id": "evt_" + uuid.uuid4().hex, "type": "checkout.session.completed", "data": {"object": {
            "id": sess["id"], "payment_status": "paid", "amount_total": sess["amount_cents"], "metadata": {"journey_id": jid}}}}).encode()
        call("POST /payments/webhook", "POST", "/payments/webhook", stripe_headers(raw), content=raw)
        mid = journey.get_journey(jid)["matter_id"]
        backend.matters[mid]["attorney_reviewer"] = backend.users[EMAIL["attorney"]]["id"]
        jobs.HANDLERS["draft_documents"]({"payload": {"journey_id": jid}})
        doc = review._current_drafts(jid)[0]
        call("POST /staff/drafts/{doc_id}/versions", "POST", f"/staff/drafts/{doc['id']}/versions", att, json={"content": doc["content"]})
        call("POST /staff/journeys/{jid}/review", "POST", f"/staff/journeys/{jid}/review", att, json={"decision": "approve"})
        docs = c.get("/review/documents", headers=h).json()["documents"]
        for d in docs:
            call("POST /review/documents/{doc_id}", "POST", f"/review/documents/{d['id']}", h, json={"decision": "ok"})
        free = []
        for week in range(1, 30):
            day = (datetime.date(2027, 6, 1) + datetime.timedelta(weeks=week)).isoformat()
            free = c.get(f"/booking/slots?kind=signing&from={day}&days=5", headers=h).json()["slots"]
            if len(free) >= 2:
                break
        bid = call("POST /booking", "POST", "/booking", h, json={"kind": "signing", "start": free[0]["start"]}).json()["id"]
        call("PATCH /booking/{booking_id}", "PATCH", f"/booking/{bid}", h, json={"start": free[1]["start"]})
        call("DELETE /booking/{booking_id}", "DELETE", f"/booking/{bid}", h)
        call("POST /staff/journeys/{jid}/executed", "POST", f"/staff/journeys/{jid}/executed", para, json={"documents": [
             {"name": "Testamento", "filename": "will.pdf", "content_b64": base64.b64encode(b"%PDF-1.4 t707").decode()}]})
        call("POST /staff/journeys/{jid}/funding-done", "POST", f"/staff/journeys/{jid}/funding-done", para)
        call("POST /staff/journeys/{jid}/refunds", "POST", f"/staff/journeys/{jid}/refunds", adm, json={"amount_cents": 100, "reason": "prueba"})

        b = content.load_dir(os.path.join(HERE, "fixtures", "content"))
        lid = "t707" + uuid.uuid4().hex[:6]
        lesson = b["lessons"][0]
        lesson.update(id=lid, day=None, unit="bonus")
        for step in lesson["steps"]:
            step["id"] = step["id"].replace("demo", lid, 1)
            for it in step["items"]:
                it["id"] = it["id"].replace("demo", lid, 1)
        content.import_bundle(b, actor="opus")
        legal, plain = f"{lid}.1.1", f"{lid}.1.3"
        call("PUT /staff/content/{entry_id:path}/draft", "PUT", f"/staff/content/{legal}/draft", para,
             json={"body": {"es": {"text": "Texto."}, "en": {"text": "Text."}, "source": "pc-6110"}})
        v = call("POST /staff/content/{entry_id:path}/submit", "POST", f"/staff/content/{legal}/submit", para).json()["version"]
        call("POST /staff/content/{entry_id:path}/approve", "POST", f"/staff/content/{legal}/approve", att, json={"version": v})
        pv = c.put(f"/staff/content/{plain}/draft", headers=para, json={"body": {"answer": False,
                   "es": {"statement": "Necesita notario.", "explain": "No."}, "en": {"statement": "Needs a notary.", "explain": "No."}}}).json()["version"]
        call("POST /staff/content/{entry_id:path}/publish", "POST", f"/staff/content/{plain}/publish", para, json={"version": pv})

        if "PUT /staff/firm-settings" in ROUTES:                                       # T7-05
            call("PUT /staff/firm-settings", "PUT", "/staff/firm-settings", att, json={"lessons_per_day": 1})
        if "POST /staff/attorney-questions/{qid}/answer" in ROUTES:                    # T7-04
            qid = db.query("SELECT id FROM attorney_questions WHERE journey_id = ?", (jid,))[0][0]
            call("POST /staff/attorney-questions/{qid}/answer", "POST", f"/staff/attorney-questions/{qid}/answer", att,
                 json={"answer": "Sí, lo vemos en la cita."})
        call("DELETE /conflicts/list", "DELETE", "/conflicts/list", para)
    finally:
        if names:
            conflicts.replace_list("name\n" + "\n".join(names))

    assert sorted(CHANGES - set(hit)) == [], "state-changing routes with no success step in this test"
    silent = sorted(k for k, rows in hit.items() if not rows)
    assert silent == [], f"state-changing routes that wrote no audit row: {silent}"
    for k, rows in hit.items():
        assert all(r["actor"] and r["action"] for r in rows), k
    client_rows = hit["POST /journey/events"] + hit["PUT /datos/{question_id}"] + hit["POST /chat"]
    assert all("Ana" not in r["detail"] and "Torres" not in r["detail"] and "albacea" not in r["detail"] for r in client_rows)
