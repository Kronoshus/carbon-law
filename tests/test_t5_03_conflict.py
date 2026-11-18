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

from aprende import conflicts

LIST_CSV = "name\nRoberto Méndez\nAcme Holdings LLC\nMadonna\nMaría José Pérez Gómez\n"


@pytest.fixture
def alerts(monkeypatch):
    sent = []
    monkeypatch.setattr(conflicts, "notify_staff", lambda title, message: sent.append((title, message)))
    return sent


def upload(csv_text=LIST_CSV):
    r = c.post("/conflicts/list", json={"csv": csv_text}, headers=staff())
    assert r.status_code == 200, r.text
    return r.json()


def clear_list():
    assert c.delete("/conflicts/list", headers=staff()).status_code == 200


def submit(h, names):
    send(h, "ai_disclosed")
    send(h, "consent", answer="yes")
    r = send(h, "names_submitted", names=names)
    assert r.status_code == 200, r.text
    return r.json()


def auto_payloads(jid):
    rows = db.query("SELECT payload_json FROM journey_events WHERE journey_id = ? AND type = 'conflict_auto'", (jid,))
    return [json.loads(p[0]) for p in rows]


@pytest.mark.parametrize("names,result", [
    (["Ana Torres", "Luis Torres"], "clear"),
    (["Ana Torres", "Roberto Mendes"], "possible"),          # one letter off
    (["Ana Torres", "Roberto Mendez"], "possible"),          # no accent
    (["Roberto Carlos Méndez"], "possible"),                 # a middle name in between
    (["Roberto Gómez", "Ana Méndez"], "clear"),              # words from two different people
    (["Madonna"], "clear"),                                  # one-word list names are ignored
    (["maria jose perez gomez"], "possible"),                # case and accents folded
])
def test_the_automatic_check(alerts, names, result):
    upload()
    h = client()
    j = submit(h, names)
    assert auto_payloads(j["id"]) == [{"result": result}]
    assert state(h)["conflict"] == ("clear" if result == "clear" else "hold")


def test_the_list_upload_is_staff_only():
    h = client()
    assert c.post("/conflicts/list", json={"csv": LIST_CSV}, headers=h).status_code == 403
    assert c.post("/conflicts/list", json={"csv": LIST_CSV}).status_code == 401
    assert upload()["count"] == 4


def test_a_possible_conflict_tells_the_client_nothing(alerts):
    upload()
    h = client()
    j = submit(h, ["Ana Torres", "Roberto Mendes"])
    raw = c.get("/journey", headers=h).text
    for word in ("Méndez", "Mendez", "Mendes", "possible", "matches", "Roberto"):
        assert word not in raw
    g = json.loads(raw)["gates"]
    assert not any(g[k] for k in ("may_collect_details", "may_chat", "may_sign_engagement", "may_pay"))
    assert json.loads(raw)["conflict"] == "hold"


def test_matched_names_are_only_in_the_staff_queue(alerts):
    upload()
    h = client()
    j = submit(h, ["Ana Torres", "Roberto Mendes"])
    q = c.get("/conflicts/queue", headers=staff()).json()
    mine = [x for x in q if x["journey_id"] == j["id"]]
    assert len(mine) == 1
    assert mine[0]["result"] == "possible" and mine[0]["matches"] == ["Roberto Méndez"]
    assert mine[0]["names"] == ["Ana Torres", "Roberto Mendes"]
    assert c.get("/conflicts/queue", headers=h).status_code == 403
    events = db.query("SELECT payload_json FROM journey_events WHERE journey_id = ?", (j["id"],))
    assert not any("Méndez" in (p[0] or "") for p in events)


def test_staff_get_one_alert_per_possible_conflict(alerts):
    upload()
    h = client()
    submit(h, ["Ana Torres", "Roberto Mendes"])
    send(h, "names_submitted", names=["Ana Torres", "Roberto Mendes"])      # a resend
    assert len(alerts) == 1
    assert "Méndez" not in alerts[0][1] and "Mendes" not in alerts[0][1]    # the phone alert carries no names


def test_a_clear_check_sends_no_alert(alerts):
    upload()
    submit(client(), ["Ana Torres"])
    assert alerts == []


def test_without_a_list_details_wait_for_staff(alerts):
    clear_list()
    h = client()
    j = submit(h, ["Ana Torres"])
    assert auto_payloads(j["id"]) == [{"result": "no_list"}]
    assert state(h)["gates"]["may_collect_details"] is False
    assert state(h)["conflict"] == "pending"
    r = c.post(f"/conflicts/{j['id']}/decision", json={"result": "cleared"}, headers=staff())
    assert r.status_code == 200, r.text
    g = state(h)["gates"]
    assert g["may_collect_details"] is True and g["may_chat"] is True


def test_staff_can_clear_a_possible_conflict_after_review(alerts):
    upload()
    h = client()
    j = submit(h, ["Roberto Mendes"])
    assert state(h)["conflict"] == "hold"
    c.post(f"/conflicts/{j['id']}/decision", json={"result": "cleared"}, headers=staff())
    assert state(h)["conflict"] == "clear"
    assert state(h)["gates"]["may_collect_details"] is True


def test_a_staff_flag_stops_everything(alerts):
    upload()
    h = client()
    j = submit(h, ["Ana Torres"])
    assert state(h)["gates"]["may_chat"] is True
    c.post(f"/conflicts/{j['id']}/decision", json={"result": "flagged"}, headers=staff())
    assert state(h)["conflict"] == "hold" and state(h)["gates"]["may_chat"] is False


def test_decisions_are_staff_only_and_validated(alerts):
    upload()
    h = client()
    j = submit(h, ["Ana Torres"])
    assert c.post(f"/conflicts/{j['id']}/decision", json={"result": "cleared"}, headers=h).status_code == 403
    assert c.post(f"/conflicts/{j['id']}/decision", json={"result": "maybe"}, headers=staff()).status_code == 422
    assert c.post(f"/conflicts/{uuid.uuid4()}/decision", json={"result": "cleared"}, headers=staff()).status_code == 404
