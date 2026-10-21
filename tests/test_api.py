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
