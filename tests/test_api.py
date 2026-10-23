import sys, os, tempfile, subprocess; sys.path.insert(0, "backend")
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


def test_staff_stage_options_are_authoritative_and_private():
    assert c.get("/stages").status_code == 401
    token=c.post("/auth/login",json={"email":"staff@example.com","password":"staff-test-password"}).json()["token"]
    response=c.get("/stages",headers={"Authorization":"Bearer "+token})
    assert response.status_code==200
    assert response.json()==__import__("app").STAGES


def test_document_update_uses_json_body_not_query():
    staff=c.post("/auth/login",json={"email":"staff@example.com","password":"staff-test-password"}).json()
    h={"Authorization":"Bearer "+staff["token"]}
    matter=c.post("/matters",json={"client_name":"Doc Update Test"},headers=h).json()
    doc=c.post("/documents",json={"matter_id":matter["id"],"name":"Will"},headers=h).json()
    changed=c.patch(f"/documents/{doc['id']}",json={"status":"Signed","version":2},headers=h)
    assert changed.status_code==200 and changed.json()["status"]=="Signed" and changed.json()["version"]==2
    legacy=c.patch(f"/documents/{doc['id']}?status=Archived&version=3",headers=h)
    assert legacy.status_code==422
    assert c.get("/documents",headers=h).json()[0]["status"]=="Signed"


def test_matter_id_is_generated_when_omitted():
    token=c.post("/auth/login",json={"email":"staff@example.com","password":"staff-test-password"}).json()["token"]
    result=c.post("/matters",json={"client_name":"Generated ID Client"},headers={"Authorization":"Bearer "+token})
    assert result.status_code==200
    assert result.json()["id"].startswith("CL-") and len(result.json()["id"])==11


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


def test_staff_can_update_contact_status_and_note():
    login = c.post("/auth/login", json={"email":"staff@example.com", "password":"staff-test-password"})
    h = {"Authorization":"Bearer "+login.json()["token"]}
    contact = c.post("/contact", json={"name":"Client", "email":"client@example.com", "message":"Call me"}).json()
    r = c.patch(f"/contacts/{contact['id']}", json={"status":"Contacted", "note":"Left voicemail"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "Contacted"
    assert r.json()["note"] == "Left voicemail"


def test_public_contact_and_intake_reject_oversized_fields():
    oversized = "x" * 501
    assert c.post("/contact", json={"name":"n","email":"e@example.com","message":oversized}).status_code == 422
    token = c.post("/auth/signup", json={"name":"Intake","email":"intake@example.com","password":"long-secure-password"}).json()["token"]
    assert c.post("/intake", json={"client_name":"Intake","email":"intake@example.com","goals":oversized}, headers={"Authorization":"Bearer "+token}).status_code == 422


def test_all_estate_workflow_outputs_are_attorney_review_summaries():
    from app import render_workflow_document, WORKFLOW_TEMPLATES
    workflow = {"client_name": "Test Client", "intake": {"general": {}, "documents": {}}, "demo_mode": False}
    assert set(WORKFLOW_TEMPLATES) == {"Revocable living trust", "Pour-over will", "Advance health care directive", "Financial power of attorney"}
    for name in WORKFLOW_TEMPLATES:
        content = render_workflow_document(workflow, name)
        assert content.startswith("DRAFT — FOR ATTORNEY REVIEW — NOT FOR SIGNING\n")
        assert "not an executed or execution-ready legal instrument" in content


def test_demo_workflow_generates_summary_with_beam_and_keeps_review_labels(monkeypatch):
    from pathlib import Path
    import app as backend
    called = []
    monkeypatch.setattr(backend, "_beam_review_summary", lambda name, body: called.append((name, body)) or "Generated simulated summary")
    workflow = {"client_name": "Demo Client", "intake": {"general": {}, "documents": {}}, "demo_mode": True}
    content = backend.render_workflow_document(workflow, "Pour-over will")
    assert called and called[0][0] == "Pour-over will"
    assert backend.BEAM_DOCUMENT_PROMPTS["Pour-over will"] == "pour-over-will-drafter.md"
    assert (Path(backend.DOCUMENT_PROMPT_ROOT) / backend.BEAM_DOCUMENT_PROMPTS["Pour-over will"]).is_file()
    assert content.startswith("DEMO — SIMULATION ONLY — NOT A CLIENT DOCUMENT\nDRAFT — FOR ATTORNEY REVIEW — NOT FOR SIGNING\n")
    assert content.endswith("Generated simulated summary")


def test_workflow_requires_staff_conflict_clearance_and_gates_order():
    client = c.post("/auth/signup", json={"name":"Workflow Client","email":"flow@example.com","password":"long-secure-password"}).json()
    headers = {"Authorization":"Bearer "+client["token"]}
    started = c.post("/workflows", json={"phone":"555","related_names":["Example Person"]}, headers=headers)
    assert started.status_code == 200
    wid = started.json()["id"]
    assert started.json()["related_names"] == ["Example Person"]
    payload = {"general":{"marital_status":"single"},"documents":{"Pour-over will":{"executor":"Example Person"}}}
    assert c.patch(f"/workflows/{wid}/documents",json={"documents_requested":["Pour-over will"]},headers=headers).status_code == 409
    assert c.patch(f"/workflows/{wid}/intake",json=payload,headers=headers).status_code == 409
    assert c.post(f"/workflows/{wid}/drafts",headers=headers).status_code == 409
    # The client may reopen Part 2 at any time, but still cannot skip conflict clearance into Part 3.
    reopened=c.post(f"/workflows/{wid}/reopen-section",json={"part":2},headers=headers)
    assert reopened.status_code==200 and reopened.json()["stage"]=="document_selection"
    assert c.post(f"/workflows/{wid}/reopen-section",json={"part":3},headers=headers).status_code==409
    staff = c.post("/auth/login",json={"email":"staff@example.com","password":"staff-test-password"}).json()
    staff_headers = {"Authorization":"Bearer "+staff["token"]}
    assert c.patch(f"/workflows/{wid}/staff-review",json={"decision":"conflict_cleared"},headers=staff_headers).status_code == 200
    reopened=c.post(f"/workflows/{wid}/reopen-section",json={"part":2},headers=headers)
    assert reopened.status_code==200 and reopened.json()["stage"]=="document_selection"
    assert c.post(f"/workflows/{wid}/reopen-section",json={"part":3},headers=headers).status_code==200
    assert c.post(f"/workflows/{wid}/reopen-section",json={"part":1},headers=headers).status_code==200
    updated=c.patch(f"/workflows/{wid}/conflict-info",json={"phone":"555-0000","related_names":["Another Person"]},headers=headers)
    assert updated.status_code==200 and updated.json()["related_names"]==["Another Person"]
    assert c.patch(f"/workflows/{wid}/staff-review",json={"decision":"conflict_cleared"},headers=staff_headers).status_code==200
    assert c.patch(f"/workflows/{wid}/documents",json={"documents_requested":["Pour-over will"]},headers=headers).status_code == 200
    assert c.patch(f"/workflows/{wid}/intake",json=payload,headers=headers).status_code == 200
    draft = c.post(f"/workflows/{wid}/drafts",headers=headers)
    assert draft.status_code == 200
    assert "NOT FOR SIGNING" in draft.json()["drafts"]["Pour-over will"]["content"]
    content = draft.json()["drafts"]["Pour-over will"]["content"]
    assert "Pour-Over Will Summary Template (California)" in content
    assert "Executor: Example Person" in content
    assert "{{executor}}" not in content
    listed_docs = c.get("/documents", headers=headers).json()
    generated = next(doc for doc in listed_docs if doc.get("workflow_id") == wid)
    assert generated["status"] == "Client Review" and generated["content"] == content
    stranger = c.post("/auth/signup",json={"name":"Workflow Outsider","email":"flow-outsider@example.com","password":"long-secure-password"}).json()
    assert all(doc.get("workflow_id") != wid for doc in c.get("/documents",headers={"Authorization":"Bearer "+stranger["token"]}).json())
    assert c.patch(f"/workflows/{wid}/client-review",json={"decision":"changes_requested","note":"Update executor"},headers=headers).status_code == 200
    assert c.get("/documents",headers=headers).json() == []
    c.patch(f"/workflows/{wid}/intake",json=payload,headers=headers)
    revised = c.post(f"/workflows/{wid}/drafts",headers=headers).json()
    assert revised["drafts"]["Pour-over will"]["version"] == 2
    assert c.patch(f"/workflows/{wid}/client-review",json={"decision":"approved"},headers=headers).status_code == 200
    assert c.patch(f"/workflows/{wid}/staff-review",json={"decision":"attorney_approved"},headers=staff_headers).status_code == 403
    assert c.get("/my-workflows",headers=headers).json()[0]["stage"] == "attorney_review"


def test_client_portal_lists_all_planning_workflows():
    client = c.post("/auth/signup",json={"name":"Multi Plan","email":"multi-plan@example.com","password":"long-secure-password"}).json()
    headers={"Authorization":"Bearer "+client["token"]}
    first=c.post("/workflows",json={"related_names":["First Person"]},headers=headers).json()
    second=c.post("/workflows",json={"related_names":["Second Person"]},headers=headers).json()
    listed=c.get("/my-workflows",headers=headers)
    assert listed.status_code==200
    assert {workflow["id"] for workflow in listed.json()} == {first["id"],second["id"]}
    stranger=c.post("/auth/signup",json={"name":"Other","email":"multi-plan-other@example.com","password":"long-secure-password"}).json()
    assert c.get("/my-workflows",headers={"Authorization":"Bearer "+stranger["token"]}).json()==[]


def test_client_workflow_isolation_and_staff_queue_authorization():
    one = c.post("/auth/signup",json={"name":"One","email":"oneflow@example.com","password":"long-secure-password"}).json()
    two = c.post("/auth/signup",json={"name":"Two","email":"twoflow@example.com","password":"long-secure-password"}).json()
    h1={"Authorization":"Bearer "+one["token"]};h2={"Authorization":"Bearer "+two["token"]}
    w=c.post("/workflows",json={"related_names":["A Person"]},headers=h1).json()
    assert c.get("/my-workflow",headers=h1).json()["id"] == w["id"]
    assert c.get("/my-workflow",headers=h1).json()["matter_id"] in [m["id"] for m in c.get("/my-matters",headers=h1).json()]
    assert c.get("/my-workflow",headers=h2).json() is None
    assert c.patch(f"/workflows/{w['id']}/staff-review",json={"decision":"conflict_cleared"},headers=h2).status_code == 403
    assert c.get("/my-workflow",headers={"Authorization":"Bearer "+c.post("/auth/login",json={"email":"staff@example.com","password":"staff-test-password"}).json()["token"]}).status_code == 200


def test_staff_assignment_authorization_approval_attribution_and_change_notes():
    from app import users, hash_pw, matters, workflows
    attorney_ids=[]
    for email,name in [("assigned@example.com","Assigned Attorney"),("other@example.com","Other Attorney")]:
        uid=str(uuid.uuid4()); attorney_ids.append(uid)
        users[email]={"id":uid,"name":name,"email":email,"role":"attorney","password_hash":hash_pw("test-password"),"created_at":datetime.datetime.utcnow().isoformat()}
    client=c.post("/auth/signup",json={"name":"Fictional Client","email":"review-client@example.com","password":"long-secure-password"}).json()
    ch={"Authorization":"Bearer "+client["token"]}
    assigned=c.post("/auth/login",json={"email":"assigned@example.com","password":"test-password"}).json()
    ah={"Authorization":"Bearer "+assigned["token"]}
    other=c.post("/auth/login",json={"email":"other@example.com","password":"test-password"}).json()
    oh={"Authorization":"Bearer "+other["token"]}
    assert c.get("/staff").status_code==401
    staff=c.get("/staff",headers=ah)
    assert staff.status_code==200 and all(u["role"] in {"paralegal","attorney","admin"} for u in staff.json())
    matter=c.post("/matters",json={"client_name":"Fictional Matter","attorney_reviewer":attorney_ids[0]},headers=ah).json()
    mid=matter["id"]
    assert c.patch(f"/matters/{mid}",json={"attorney_reviewer":"fake"},headers=ah).status_code==400
    assert c.get(f"/matters/{mid}",headers=ah).json()["attorney_reviewer"]==attorney_ids[0]
    workflow=c.post("/workflows",json={},headers=ch).json(); wid=workflow["id"]
    workflows[wid]["matter_id"]=mid; workflows[wid]["conflict_status"]="cleared"; workflows[wid]["stage"]="attorney_review"
    doc={"id":str(uuid.uuid4()),"matter_id":mid,"workflow_id":wid,"name":"Trust","version":1,"status":"Client Review","content":"Complete terms"}
    from app import documents
    documents[doc["id"]]=doc; workflows[wid]["drafts"]={"Trust":{"document_id":doc["id"],"content":doc["content"]}}
    assert c.patch(f"/workflows/{wid}/staff-review",json={"decision":"attorney_approved"},headers=oh).status_code==403
    assert c.patch(f"/workflows/{wid}/staff-review",json={"decision":"attorney_changes"},headers=ah).status_code==400
    requested=c.patch(f"/workflows/{wid}/staff-review",json={"decision":"attorney_changes","note":"Clarify the trustee powers."},headers=ah)
    assert requested.status_code==200 and requested.json()["staff_review_note"]=="Clarify the trustee powers."
    workflows[wid]["stage"]="attorney_review"; doc["status"]="Client Review"
    doc["content"]="[ATTORNEY TO COMPLETE — trustee powers]"
    assert c.patch(f"/workflows/{wid}/staff-review",json={"decision":"attorney_approved"},headers=ah).status_code==409
    doc["content"]="Completed trust draft"
    approved=c.patch(f"/workflows/{wid}/staff-review",json={"decision":"attorney_approved"},headers=ah)
    assert approved.status_code==200 and approved.json()["approved_by"]==attorney_ids[0] and approved.json()["approved_at"]
    assert doc["status"]=="Attorney Approved"
    assert c.patch(f"/documents/{doc['id']}",json={"status":"Attorney Approved"},headers=ah).status_code==403


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
    from app import workflows, matters
    matters[workflows[wid]["matter_id"]]["attorney_reviewer"]=users["attorney@example.com"]["id"]
    approved = c.patch(f"/workflows/{wid}/staff-review",json={"decision":"attorney_approved"},headers=ah)
    assert approved.status_code==200
    client_docs = c.get("/documents",headers=h).json()
    assert any(d.get("workflow_id") == wid and d["status"] == "Attorney Approved" for d in client_docs)
    assert c.patch(f"/workflows/{wid}/appointment",json={"kind":"consultation","scheduled_at":"2030-01-01T10:00:00-07:00"},headers=h).status_code==200
    assert c.patch(f"/workflows/{wid}/staff-review",json={"decision":"consultation_completed"},headers=ah).status_code==409
    assert c.patch(f"/workflows/{wid}/appointment",json={"kind":"consultation","scheduled_at":"2030-01-01T10:00:00-07:00"},headers=ah).status_code==200
    assert c.patch(f"/workflows/{wid}/staff-review",json={"decision":"consultation_completed"},headers=ah).status_code==200
    assert c.patch(f"/workflows/{wid}/appointment",json={"kind":"signing","scheduled_at":"2030-01-02T10:00:00-07:00"},headers=h).status_code==200
    assert c.patch(f"/workflows/{wid}/appointment",json={"kind":"signing","scheduled_at":"2030-01-02T10:00:00-07:00"},headers=ah).json()["stage"]=="complete"


def test_demo_conflict_review_is_explicit_and_delayed():
    from app import workflows
    client=c.post("/auth/signup",json={"name":"Demo Client","email":"demo-flow@example.com","password":"long-secure-password"}).json()
    h={"Authorization":"Bearer "+client["token"]}
    pending=c.post("/workflows",json={"related_names":["Demo Person"]},headers=h).json()
    assert pending["demo_mode"] is False
    assert c.post(f"/workflows/{pending['id']}/demo-conflict-review",headers=h).status_code==403
    assert c.post(f"/workflows/{pending['id']}/enable-demo-review",headers=h).status_code==200
    demo_client=c.post("/auth/signup",json={"name":"Demo Client","email":"demo-mode@example.com","password":"long-secure-password"}).json()
    demo_headers={"Authorization":"Bearer "+demo_client["token"]}
    demo=c.post("/workflows",json={"related_names":["Demo Person"],"demo_mode":True},headers=demo_headers).json()
    assert c.post(f"/workflows/{demo['id']}/demo-conflict-review",headers=demo_headers).status_code==429
    workflows[demo["id"]]["created_at"]="2000-01-01T00:00:00"
    cleared=c.post(f"/workflows/{demo['id']}/demo-conflict-review",headers=demo_headers)
    assert cleared.status_code==200
    assert cleared.json()["conflict_status"]=="demo_cleared"
    assert cleared.json()["stage"]=="document_selection"
    assert c.patch(f"/workflows/{demo['id']}/documents",json={"documents_requested":["Pour-over will"]},headers=demo_headers).status_code==200
    assert c.patch(f"/workflows/{demo['id']}/intake",json={"general":{},"documents":{}},headers=demo_headers).status_code==200
    draft=c.post(f"/workflows/{demo['id']}/drafts",headers=demo_headers)
    assert draft.status_code==200
    assert draft.json()["stage"]=="client_review"
    assert "DEMO — SIMULATION ONLY" in draft.json()["drafts"]["Pour-over will"]["content"]
    assert c.patch(f"/workflows/{demo['id']}/client-review",json={"decision":"approved"},headers=demo_headers).json()["stage"]=="attorney_review"
    assert c.post(f"/workflows/{demo['id']}/demo-attorney-review",headers=demo_headers).status_code==200
    assert c.get("/my-workflow",headers=demo_headers).json()["stage"]=="consultation"
    consultation=c.patch(f"/workflows/{demo['id']}/appointment",json={"kind":"consultation","scheduled_at":"2030-01-01T10:00:00-07:00"},headers=demo_headers)
    assert consultation.status_code==200 and consultation.json()["stage"]=="consultation"
    assert consultation.json()["appointments"]["consultation"]["status"]=="requested"
    signing_request=c.patch(f"/workflows/{demo['id']}/appointment",json={"kind":"signing","scheduled_at":"2030-01-02T10:00:00-07:00"},headers=demo_headers)
    assert signing_request.status_code==200 and signing_request.json()["stage"]=="consultation"
    assert signing_request.json()["appointments"]["signing"]["status"]=="requested"
    pending_appts=c.get("/appointments",headers=demo_headers).json()
    assert any(a["kind"]=="consultation" and a["status"]=="Requested" and a["matter_id"]==demo["matter_id"] for a in pending_appts)
    from app import appointments
    appointments.clear()
    # Reads must be side-effect free; requests are materialized at write time.
    assert c.get("/appointments",headers=demo_headers).json() == []
    staff=c.post("/auth/login",json={"email":"staff@example.com","password":"staff-test-password"}).json()
    sh={"Authorization":"Bearer "+staff["token"]}
    approved=c.patch(f"/workflows/{demo['id']}/appointment",json={"kind":"consultation","scheduled_at":"2030-01-01T10:00:00-07:00"},headers=sh)
    assert approved.status_code==200 and approved.json()["appointments"]["consultation"]["status"]=="scheduled"
    assert any(a["kind"]=="consultation" and a["status"]=="Scheduled" for a in c.get("/appointments",headers=sh).json())
    assert c.patch(f"/workflows/{demo['id']}/staff-review",json={"decision":"consultation_completed"},headers=sh).json()["stage"]=="signing"
    signing=c.patch(f"/workflows/{demo['id']}/appointment",json={"kind":"signing","scheduled_at":"2030-01-02T10:00:00-07:00"},headers=demo_headers)
    assert signing.status_code==200 and signing.json()["stage"]=="signing"
    signing=c.patch(f"/workflows/{demo['id']}/appointment",json={"kind":"signing","scheduled_at":"2030-01-02T10:00:00-07:00"},headers=sh)
    assert signing.status_code==200 and signing.json()["stage"]=="complete"
    assert c.post(f"/workflows/{demo['id']}/edit",headers=demo_headers).status_code==200
    assert c.patch(f"/workflows/{demo['id']}/intake",json={"general":{"family":"Updated"},"documents":{}},headers=demo_headers).status_code==200
    assert c.get("/my-workflow",headers=demo_headers).json()["intake"]["general"]["family"]=="Updated"
    second=c.post("/workflows",json={"demo_mode":True},headers=demo_headers)
    assert second.status_code==200 and second.json()["id"]!=demo["id"] and second.json()["matter_id"]!=demo["matter_id"]


def test_workflow_appointment_requires_timezone_and_normalizes_utc():
    client=c.post("/auth/signup",json={"name":"TZ Client","email":"tz-client@example.com","password":"long-secure-password"}).json()
    h={"Authorization":"Bearer "+client["token"]}
    workflow=c.post("/workflows",json={"demo_mode":True},headers=h).json()
    from app import workflows
    workflows[workflow["id"]]["stage"]="consultation"
    naive=c.patch(f"/workflows/{workflow['id']}/appointment",json={"kind":"consultation","scheduled_at":"2030-01-01T10:00"},headers=h)
    assert naive.status_code==400
    result=c.patch(f"/workflows/{workflow['id']}/appointment",json={"kind":"consultation","scheduled_at":"2030-01-01T10:00:00-07:00"},headers=h)
    assert result.status_code==200
    assert result.json()["appointments"]["consultation"]["requested_at"]=="2030-01-01T17:00:00Z"


def test_client_can_cancel_only_own_workflow_appointment():
    one=c.post("/auth/signup",json={"name":"Cancel One","email":"cancel-one@example.com","password":"long-secure-password"}).json()
    two=c.post("/auth/signup",json={"name":"Cancel Two","email":"cancel-two@example.com","password":"long-secure-password"}).json()
    h1={"Authorization":"Bearer "+one["token"]};h2={"Authorization":"Bearer "+two["token"]}
    w=c.post("/workflows",json={"demo_mode":True},headers=h1).json()
    from app import workflows
    workflows[w["id"]]["stage"]="consultation"
    c.patch(f"/workflows/{w['id']}/appointment",json={"kind":"consultation","scheduled_at":"2030-01-01T10:00:00-07:00"},headers=h1)
    assert c.post(f"/workflows/{w['id']}/cancel-appointment",json={"decision":"cancel","note":"consultation"},headers=h2).status_code==404
    cancelled=c.post(f"/workflows/{w['id']}/cancel-appointment",json={"decision":"cancel","note":"consultation"},headers=h1)
    assert cancelled.status_code==200
    assert cancelled.json()["appointments"]["consultation"]["status"]=="cancelled"


def test_client_cannot_change_appointment_when_cancelling():
    client=c.post("/auth/signup",json={"name":"Appt Client","email":"appt-client@example.com","password":"long-secure-password"}).json()
    h={"Authorization":"Bearer "+client["token"]}
    w=c.post("/workflows",json={"demo_mode":True},headers=h).json()
    from app import workflows, appointments
    workflows[w["id"]]["stage"]="consultation"
    c.patch(f"/workflows/{w['id']}/appointment",json={"kind":"consultation","scheduled_at":"2030-01-01T10:00:00-07:00"},headers=h)
    appt=next(a for a in appointments.values() if a.get("workflow_id")==w["id"])
    result=c.patch(f"/appointments/{appt['id']}",json={"status":"Cancelled","note":"leak","scheduled_at":"2030-02-01T10:00:00-07:00"},headers=h)
    assert result.status_code==403
    assert appointments[appt["id"]]["scheduled_at"]=="2030-01-01T17:00:00Z"


def test_signup_accepts_six_character_password_and_rejects_five():
    short=c.post("/auth/signup",json={"name":"Short","email":"short-pass@example.com","password":"12345"})
    assert short.status_code==400
    valid=c.post("/auth/signup",json={"name":"Six","email":"six-pass@example.com","password":"123456"})
    assert valid.status_code==200
    assert c.post("/auth/login",json={"email":"six-pass@example.com","password":"123456"}).status_code==200


def stored_users_after_restart():
    code = "import sys; sys.path.insert(0, 'backend'); import app; print(sorted(app.users))"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True,
                         cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return out.stdout


def test_saved_data_survives_restart():
    assert c.post("/auth/signup", json={"name":"Restart","email":"restart@example.com","password":"long-secure-password"}).status_code == 200
    assert "restart@example.com" in stored_users_after_restart()


def test_concurrent_signups_with_same_email_create_one_account():
    from concurrent.futures import ThreadPoolExecutor
    with TestClient(app) as shared, ThreadPoolExecutor(16) as pool:
        signup = lambda _: shared.post("/auth/signup", json={"name":"Race","email":"race@example.com","password":"long-secure-password"})
        codes = [r.status_code for r in pool.map(signup, range(16))]
    assert codes.count(200) == 1
    assert codes.count(400) == 15

def test_one_time_initial_attorney_setup_is_private_and_restricted(monkeypatch):
    import app as app_module
    monkeypatch.setenv("INITIAL_STAFF_SETUP_TOKEN", "test-setup-key")
    bad = c.post("/auth/initial-staff-setup", json={"name":"Kevin","email":"kmohr@prompt.law","password":"long-secure-password"}, headers={"Authorization":"Bearer wrong"})
    assert bad.status_code == 404
    wrong_email = c.post("/auth/initial-staff-setup", json={"name":"Other","email":"other@example.com","password":"long-secure-password"}, headers={"Authorization":"Bearer test-setup-key"})
    assert wrong_email.status_code == 400
    result = c.post("/auth/initial-staff-setup", json={"name":"Kevin","email":"kmohr@prompt.law","password":"long-secure-password"}, headers={"Authorization":"Bearer test-setup-key"})
    assert result.status_code == 200 and result.json()["user"]["role"] == "attorney"
    assert c.get("/reports/friday", headers={"Authorization":"Bearer "+result.json()["token"]}).status_code == 200
    assert c.post("/auth/initial-staff-setup", json={"name":"Kevin","email":"kmohr@prompt.law","password":"long-secure-password"}, headers={"Authorization":"Bearer test-setup-key"}).status_code == 404
    assert "INITIAL_STAFF_SETUP_TOKEN" not in os.environ

def test_staff_dashboard_operations_keep_client_views_in_sync_and_private():
    client=c.post("/auth/signup",json={"name":"Dashboard Client","email":"dashboard-client@example.com","password":"long-secure-password"}).json()
    staff=c.post("/auth/login",json={"email":"staff@example.com","password":"staff-test-password"}).json()
    ch={"Authorization":"Bearer "+client["token"]}; sh={"Authorization":"Bearer "+staff["token"]}
    workflow=c.post("/workflows",json={"phone":"555"},headers=ch).json(); wid=workflow["id"]; mid=workflow["matter_id"]
    # Pending requests are represented at write time; reads must not overwrite staff appointment edits.
    from app import workflows, appointments, matters
    workflows[wid]["conflict_status"]="cleared"; workflows[wid]["stage"]="consultation"; workflows[wid]["attorney_approved"]=True
    workflows[wid]["appointments"]={}
    assert c.patch(f"/workflows/{wid}/appointment",json={"kind":"consultation","scheduled_at":"2030-01-01T09:00:00-07:00"},headers=ch).status_code==200
    c.get("/appointments",headers=sh)
    appt=next(a for a in appointments.values() if a.get("workflow_id")==wid and a.get("kind")=="consultation")
    assert c.patch(f"/appointments/{appt['id']}",json={"status":"Scheduled","scheduled_at":"2030-01-02T10:30:00-07:00"},headers=sh).status_code==200
    unchanged=c.patch(f"/appointments/{appt['id']}?status=Cancelled&note=private",headers=sh)
    assert unchanged.status_code==422
    assert appointments[appt["id"]]["status"]=="Scheduled" and appointments[appt["id"]]["note"]!="private"
    c.get("/appointments",headers=sh)
    assert workflows[wid]["appointments"]["consultation"]["scheduled_at"]=="2030-01-02T17:30:00Z"
    assert c.get("/my-workflows",headers=ch).json()[0]["appointments"]["consultation"]["scheduled_at"]=="2030-01-02T17:30:00Z"
    assert c.patch(f"/appointments/{appt['id']}",json={"status":"Completed"},headers=sh).status_code==200
    assert workflows[wid]["appointments"]["consultation"]["status"]=="completed"
    workflows[wid]["drafts"]={"will":"Attorney-approved draft"}
    workflows[wid]["client_approved"]=True
    workflows[wid]["attorney_approved"]=True
    assert c.patch(f"/matters/{mid}",json={"stage":"4 Drafting"},headers=sh).status_code==200
    client_workflow=c.get("/my-workflows",headers=ch).json()[0]
    assert client_workflow["stage"]=="draft_ready"
    assert client_workflow["drafts"]=={"will":"Attorney-approved draft"}
    assert client_workflow["client_approved"] and client_workflow["attorney_approved"]
    assert c.get("/my-matters",headers=ch).json()[0]["stage"] in __import__("app").STAGES
    # Sensitive internal task and comm details never leak to clients.
    task=c.post("/tasks",json={"matter_id":mid,"title":"Internal review"},headers=sh).json()
    assert c.get("/tasks",headers=ch).status_code==403
    c.post("/communications",json={"matter_id":mid,"summary":"Private note","visibility":"internal"},headers=sh)
    c.post("/communications",json={"matter_id":mid,"summary":"Client update","visibility":"client"},headers=sh)
    assert [x["summary"] for x in c.get(f"/communications?matter_id={mid}",headers=ch).json()]==["Client update"]
    matters[mid].update(owner="Staff",risk_level="High",blocker="Internal",priority="Urgent",next_action="Confidential")
    view=c.get(f"/matters/{mid}",headers=ch).json()
    assert not {"owner","risk_level","blocker","priority","next_action","client_email"} & set(view)
    saved=c.post(f"/workflows/{wid}/staff-review",json={"decision":"conflict_cleared"},headers=sh)
    # stage synchronization leaves a valid firm stage
    assert matters[mid]["stage"] in __import__("app").STAGES

def test_change_request_status_updates_client_view_and_closes_linked_task():
    staff=c.post("/auth/login",json={"email":"staff@example.com","password":"staff-test-password"}).json(); h={"Authorization":"Bearer "+staff["token"]}
    matter=c.post("/matters",json={"id":"CL-CR-RESOLVE","client_name":"CR Client"},headers=h).json()
    cr=c.post("/change-requests",json={"matter_id":matter["id"],"change_type":"Beneficiary change"},headers=h).json()
    assert c.patch(f"/change-requests/{cr['id']}",json={"status":"Whatever"},headers=h).status_code==400
    updated=c.patch(f"/change-requests/{cr['id']}",json={"status":"Resolved","resolution":"Completed after attorney review"},headers=h)
    assert updated.status_code==200
    from app import tasks
    assert tasks[cr["task_id"]]["status"]=="Done"
    assert c.get("/change-requests",headers=h).json()[-1]["resolution"]=="Completed after attorney review"
    client=c.post("/auth/signup",json={"name":"CR Client","email":"cr-client@example.com","password":"long-secure-password"}).json()
    from app import matters
    matters[matter["id"]]["client_user_id"]=__import__("app").users["cr-client@example.com"]["id"]
    c.post("/change-requests",json={"matter_id":matter["id"],"change_type":"Update beneficiary","note":"Staff-only note"},headers={"Authorization":"Bearer "+client["token"]})
    visible=c.get("/change-requests",headers={"Authorization":"Bearer "+client["token"]}).json()
    resolved=next(item for item in visible if item["id"]==cr["id"])
    assert resolved["resolution"]=="Completed after attorney review"
    assert all("note" not in item and "requested_by" not in item and "task_id" not in item for item in visible)


def test_attorney_demo_drafts_are_attorney_only_and_do_not_advance_workflow(monkeypatch):
    import app as backend
    backend.users["estate-attorney@example.com"]={"id":str(uuid.uuid4()),"name":"Estate Attorney","email":"estate-attorney@example.com","role":"attorney","password_hash":hash_pw("estate-attorney-password"),"created_at":datetime.datetime.utcnow().isoformat()}
    attorney=c.post("/auth/login",json={"email":"estate-attorney@example.com","password":"estate-attorney-password"}).json()
    ah={"Authorization":"Bearer "+attorney["token"]}
    client=c.post("/auth/signup",json={"name":"Demo Client","email":"attorney-demo-client@example.com","password":"long-secure-password"}).json()
    ch={"Authorization":"Bearer "+client["token"]}
    workflow=c.post("/workflows",json={},headers=ch).json(); wid=workflow["id"]
    assert c.post(f"/workflows/{wid}/attorney-demo-drafts",headers=ch).status_code==403
    assert c.post(f"/workflows/{wid}/attorney-demo-drafts",headers=ah).status_code==409
    paralegal=c.post("/auth/login",json={"email":"staff@example.com","password":"staff-test-password"}).json()
    ph={"Authorization":"Bearer "+paralegal["token"]}
    assert c.post(f"/workflows/{wid}/attorney-demo-drafts",headers=ph).status_code==403
    staff_clear=c.patch(f"/workflows/{wid}/staff-review",json={"decision":"conflict_cleared"},headers=ph)
    assert staff_clear.status_code==200
    assert c.patch(f"/workflows/{wid}/documents",json={"documents_requested":["Pour-over will"]},headers=ch).status_code==200
    assert c.patch(f"/workflows/{wid}/intake",json={"general":{},"documents":{"Pour-over will":{"executor":"Fictional Executor"}}},headers=ch).status_code==200
    before=c.get("/my-workflow",headers=ch).json()
    assert before["stage"]=="draft_ready"
    generated=c.post(f"/workflows/{wid}/attorney-demo-drafts",headers=ah)
    assert generated.status_code==200
    draft=generated.json()["drafts"]["Pour-over will"]["content"]
    assert "Fictional Executor" in draft and "NOT LEGALLY APPROVED" in draft and "NOT SIGNING-READY" in draft
    assert "California statutory requirements are unverified" in draft
    from app import DEMO_FORM_TEMPLATES, render_attorney_demo_form
    assert len(DEMO_FORM_TEMPLATES)==4
    for name in DEMO_FORM_TEMPLATES:
        form=render_attorney_demo_form({"client_name":"Fictional Client","intake":{"general":{},"documents":{}}},name)
        assert "DEMO — SIMULATION ONLY" in form and "ATTORNEY TO COMPLETE" in form
    assert c.get("/my-workflow",headers=ch).json()["stage"]=="draft_ready"
    assert draft not in str(c.get("/my-workflow",headers=ch).json())
    assert draft not in str(c.get("/documents",headers=ch).json())
    assert draft not in str(c.get("/documents",headers=ph).json())
    row=next(w for w in c.get("/my-workflow",headers=ah).json() if w["id"]==wid)
    assert row["attorney_demo_drafts"]["Pour-over will"]["content"]==draft
    docid=generated.json()["drafts"]["Pour-over will"]["document_id"]
    attorney_doc=next(d for d in c.get("/documents",headers=ah).json() if d["id"]==docid)
    assert attorney_doc["status"]=="Attorney Review" and attorney_doc["content"]==draft
    assert c.get("/documents",headers=ch).json()==[]
    assert c.patch(f"/documents/{docid}",json={"status":"Client Review"},headers=ph).status_code==403
    audit=[event for event in backend.audit if event.get("action")=="generate_attorney_demo_drafts" and event.get("entity_id")==wid]
    assert audit and audit[-1]["actor"]=="estate-attorney@example.com"
    assert draft not in str(audit[-1]) and "Fictional Executor" not in str(audit[-1])
    # A retry versions the draft and retains history while superseding the prior active version.
    second=c.post(f"/workflows/{wid}/attorney-demo-drafts",headers=ah).json()
    docs=[d for d in backend.documents.values() if d.get("workflow_id")==wid and d.get("attorney_only")]
    assert sorted((d["version"],d["status"]) for d in docs)==[(1,"Superseded"),(2,"Attorney Review")]
    assert next(d for d in docs if d["version"]==1)["replaced_by_version"]==2
    assert second["drafts"]["Pour-over will"]["version"]==2
