import sys, os, tempfile; sys.path.insert(0, "backend")
os.environ["DATABASE_URL"] = ""
os.environ["CARBON_DB_PATH"] = tempfile.mktemp(suffix=".db")
from fastapi.testclient import TestClient
from app import app
from app import users, sessions, hash_pw
import uuid, datetime
_staff_id = str(uuid.uuid4())
users["staff@example.com"] = {"id":_staff_id,"name":"Test Staff","email":"staff@example.com","role":"paralegal","password_hash":hash_pw("staff-test-password"),"created_at":datetime.datetime.utcnow().isoformat()}

c = TestClient(app)

def test_health():
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_auth_flow():
    r = c.post("/auth/signup", json={"name":"T","email":"t2@example.com","password":"long-secure-password"})
    assert r.status_code == 200
    token = r.json()["token"]
    r = c.get("/auth/me", headers={"Authorization":"Bearer "+token})
    assert r.status_code == 200
    assert r.json()["role"] == "client"
    assert "password_hash" not in r.json()
    r = c.post("/auth/login", json={"email":"t2@example.com","password":"long-secure-password"})
    assert r.status_code == 200

def test_email_case_whitespace_normalization():
    r = c.post("/auth/signup", json={"name":"Mixed","email":"Mixed.Case@example.com","password":"long-secure-password"})
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "mixed.case@example.com"
    login = c.post("/auth/login", json={"email":"  MIXED.CASE@EXAMPLE.COM ","password":"long-secure-password"})
    assert login.status_code == 200


def test_matter_crud_rbac():
    # login as paralegal
    r = c.post("/auth/login", json={"email":"staff@example.com","password":"staff-test-password"})
    assert r.status_code == 200
    token = r.json()["token"]
    h = {"Authorization":"Bearer "+token}
    r = c.post("/matters", json={"id":"CL-TEST","client_name":"Test","stage":"1 Intake","owner":"P","risk_level":"Low"}, headers=h)
    assert r.status_code == 200
    r = c.get("/matters/CL-TEST", headers=h)
    assert r.status_code == 200
    r = c.patch("/matters/CL-TEST", json={"stage":"2 Attorney Scope"}, headers=h)
    assert r.status_code == 200
    assert r.json()["stage"] == "2 Attorney Scope"
    # client cannot create matter
    r = c.post("/auth/signup", json={"name":"C","email":"c@example.com","password":"long-secure-password"})
    ct = r.json()["token"]
    r = c.post("/matters", json={"id":"CL-X","client_name":"X","stage":"1 Intake"}, headers={"Authorization":"Bearer "+ct})
    assert r.status_code == 403

def test_intake():
    assert c.post("/intake", json={"client_name":"Intake User","email":"iu@example.com"}).status_code == 401
    signup = c.post("/auth/signup", json={"name":"Intake User","email":"iu@example.com","password":"long-secure-password"}).json()
    headers = {"Authorization":"Bearer "+signup["token"]}
    body = {"client_name":"Intake User","email":"iu@example.com","phone":"555","goals":"","assets":"","family":"","documents_requested":["Revocable living trust","Pour-over will"]}
    r = c.post("/intake", json=body, headers=headers)
    assert r.status_code == 200
    assert r.json()["request_id"]
    assert "matter_id" not in r.json()

def test_reports():
    r = c.get("/reports/friday", headers={"Authorization":"Bearer "+c.post("/auth/login", json={"email":"staff@example.com","password":"staff-test-password"}).json()["token"]})
    assert r.status_code == 200
    assert "total" in r.json()
    r = c.get("/reports/capacity", headers={"Authorization":"Bearer "+c.post("/auth/login", json={"email":"staff@example.com","password":"staff-test-password"}).json()["token"]})
    assert r.status_code == 200
    r = c.get("/reports/bottlenecks", headers={"Authorization":"Bearer "+c.post("/auth/login", json={"email":"staff@example.com","password":"staff-test-password"}).json()["token"]})
    assert r.status_code == 200

def test_export():
    r = c.get("/export/matters.csv", headers={"Authorization":"Bearer "+c.post("/auth/login", json={"email":"staff@example.com","password":"staff-test-password"}).json()["token"]})
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]

def test_tasks():
    r = c.post("/auth/login", json={"email":"staff@example.com","password":"staff-test-password"})
    token = r.json()["token"]; h={"Authorization":"Bearer "+token}
    r = c.post("/matters", json={"id":"CL-TASK","client_name":"Task Test","stage":"1 Intake","owner":"P","risk_level":"Low"}, headers=h)
    assert r.status_code == 200
    r = c.post("/tasks", json={"matter_id":"CL-TASK","title":"Test task","owner":"P"}, headers=h)
    assert r.status_code == 200
    tid = r.json()["id"]
    r = c.patch(f"/tasks/{tid}", json={"status":"Done"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "Done"

print("all tests passed")


def test_private_matter_and_document_routes():
    assert c.get("/matters").status_code == 401
    assert c.get("/documents").status_code == 401
    assert c.get("/contacts").status_code == 401
    staff = c.post("/auth/login", json={"email":"staff@example.com","password":"staff-test-password"}).json()["token"]
    headers = {"Authorization":"Bearer "+staff}
    assert c.get("/matters", headers=headers).status_code == 200
    assert c.get("/documents", headers=headers).status_code == 200


def test_client_cannot_read_another_clients_matter():
    first = c.post("/auth/signup", json={"name":"One","email":"one@example.com","password":"long-secure-password"}).json()
    second = c.post("/auth/signup", json={"name":"Two","email":"two@example.com","password":"long-secure-password"}).json()
    staff = c.post("/auth/login", json={"email":"staff@example.com","password":"staff-test-password"}).json()
    matter = c.post("/matters", json={"id":"CL-PRIVATE","client_name":"One","stage":"1 Intake","owner":"P","risk_level":"Low"},headers={"Authorization":"Bearer "+staff["token"]}).json()
    matter["client_email"]="one@example.com"
    from app import matters
    matters["CL-PRIVATE"]["client_user_id"]=first["user"]["id"]
    assert c.get("/matters/CL-PRIVATE",headers={"Authorization":"Bearer "+first["token"]}).status_code == 200
    assert c.get("/matters/CL-PRIVATE",headers={"Authorization":"Bearer "+second["token"]}).status_code == 403


def test_api_schema_is_not_public():
    assert c.get("/docs").status_code == 404
    assert c.get("/openapi.json").status_code == 404


def test_public_contact_and_intake_reject_oversized_fields():
    oversized = "x" * 501
    assert c.post("/contact", json={"name":"n","email":"e@example.com","message":oversized}).status_code == 422
    token = c.post("/auth/signup", json={"name":"Intake","email":"intake@example.com","password":"long-secure-password"}).json()["token"]
    assert c.post("/intake", json={"client_name":"Intake","email":"intake@example.com","goals":oversized}, headers={"Authorization":"Bearer "+token}).status_code == 422


def test_workflow_requires_staff_conflict_clearance_and_gates_order():
    client = c.post("/auth/signup", json={"name":"Workflow Client","email":"flow@example.com","password":"long-secure-password"}).json()
    headers = {"Authorization":"Bearer "+client["token"]}
    started = c.post("/workflows", json={"phone":"555","related_names":["Example Person"]}, headers=headers)
    assert started.status_code == 200
    wid = started.json()["id"]
    payload = {"general":{"marital_status":"single"},"documents":{"Pour-over will":{"executor":"Example Person"}}}
    assert c.patch(f"/workflows/{wid}/documents",json={"documents_requested":["Pour-over will"]},headers=headers).status_code == 409
    assert c.patch(f"/workflows/{wid}/intake",json=payload,headers=headers).status_code == 409
    assert c.post(f"/workflows/{wid}/drafts",headers=headers).status_code == 409
    staff = c.post("/auth/login",json={"email":"staff@example.com","password":"staff-test-password"}).json()
    staff_headers = {"Authorization":"Bearer "+staff["token"]}
    assert c.patch(f"/workflows/{wid}/staff-review",json={"decision":"conflict_cleared"},headers=staff_headers).status_code == 200
    assert c.patch(f"/workflows/{wid}/documents",json={"documents_requested":["Pour-over will"]},headers=headers).status_code == 200
    assert c.patch(f"/workflows/{wid}/intake",json=payload,headers=headers).status_code == 200
    draft = c.post(f"/workflows/{wid}/drafts",headers=headers)
    assert draft.status_code == 200
    assert "NOT FOR SIGNING" in draft.json()["drafts"]["Pour-over will"]["content"]
    assert c.patch(f"/workflows/{wid}/client-review",json={"decision":"approved"},headers=headers).status_code == 200
    assert c.patch(f"/workflows/{wid}/staff-review",json={"decision":"attorney_approved"},headers=staff_headers).status_code == 403


def test_client_workflow_isolation_and_staff_queue_authorization():
    one = c.post("/auth/signup",json={"name":"One","email":"oneflow@example.com","password":"long-secure-password"}).json()
    two = c.post("/auth/signup",json={"name":"Two","email":"twoflow@example.com","password":"long-secure-password"}).json()
    h1={"Authorization":"Bearer "+one["token"]};h2={"Authorization":"Bearer "+two["token"]}
    w=c.post("/workflows",json={"related_names":["A Person"]},headers=h1).json()
    assert c.get("/my-workflow",headers=h1).json()["id"] == w["id"]
    assert c.get("/my-workflow",headers=h2).json() is None
    assert c.patch(f"/workflows/{w['id']}/staff-review",json={"decision":"conflict_cleared"},headers=h2).status_code == 403
    assert c.get("/my-workflow",headers={"Authorization":"Bearer "+c.post("/auth/login",json={"email":"staff@example.com","password":"staff-test-password"}).json()["token"]}).status_code == 200


def test_workflow_attorney_consultation_and_signing_gates():
    from app import users, hash_pw
    users["attorney@example.com"]={"id":str(uuid.uuid4()),"name":"Test Attorney","email":"attorney@example.com","role":"attorney","password_hash":hash_pw("attorney-test-password"),"created_at":datetime.datetime.utcnow().isoformat()}
    client=c.post("/auth/signup",json={"name":"Gate Client","email":"gate@example.com","password":"long-secure-password"}).json(); h={"Authorization":"Bearer "+client["token"]}
    wid=c.post("/workflows",json={},headers=h).json()["id"]
    staff=c.post("/auth/login",json={"email":"staff@example.com","password":"staff-test-password"}).json(); sh={"Authorization":"Bearer "+staff["token"]}
    c.patch(f"/workflows/{wid}/staff-review",json={"decision":"conflict_cleared"},headers=sh)
    c.patch(f"/workflows/{wid}/documents",json={"documents_requested":["Pour-over will"]},headers=h)
    c.patch(f"/workflows/{wid}/intake",json={"general":{},"documents":{}},headers=h)
    c.post(f"/workflows/{wid}/drafts",headers=h)
    c.patch(f"/workflows/{wid}/client-review",json={"decision":"approved"},headers=h)
    attorney=c.post("/auth/login",json={"email":"attorney@example.com","password":"attorney-test-password"}).json(); ah={"Authorization":"Bearer "+attorney["token"]}
    assert c.patch(f"/workflows/{wid}/staff-review",json={"decision":"attorney_approved"},headers=ah).status_code==200
    assert c.patch(f"/workflows/{wid}/appointment",json={"kind":"consultation","scheduled_at":"2030-01-01T10:00"},headers=h).status_code==200
    assert c.patch(f"/workflows/{wid}/staff-review",json={"decision":"consultation_completed"},headers=ah).status_code==200
    assert c.patch(f"/workflows/{wid}/appointment",json={"kind":"signing","scheduled_at":"2030-01-02T10:00"},headers=h).status_code==200
    assert c.patch(f"/workflows/{wid}/appointment",json={"kind":"signing","scheduled_at":"2030-01-02T10:00"},headers=ah).json()["stage"]=="complete"
