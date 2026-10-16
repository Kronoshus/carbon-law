from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import os, uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI(title="Carbon Law Backend", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Matter(BaseModel):
    id: str
    client_name: str
    stage: str = "1 Intake"
    owner: str = "Unassigned"
    attorney_reviewer: Optional[str] = None
    due_date: Optional[str] = None
    last_client_contact: Optional[str] = None
    next_client_contact: Optional[str] = None
    next_action: str = ""
    blocker: str = "None"
    document_status: Optional[str] = "Not Started"
    title_status: Optional[str] = "Unconfirmed"
    funding_status: Optional[str] = "Not Started"
    appointment_status: Optional[str] = "Not Booked"
    risk_level: str = "Low"
    priority: str = "Normal"
    notes: str = ""

class ChangeRequest(BaseModel):
    matter_id: str
    requested_by: str
    change_type: str
    affected_documents: str = ""
    required_attorney_decision: bool = True
    impact: str = ""
    status: str = "Open"

class Appointment(BaseModel):
    matter_id: str
    kind: str = "Signing"
    scheduled_at: str
    status: str = "Booked"
    note: str = ""

class PortalDocument(BaseModel):
    matter_id: str
    name: str
    version: int = 1
    status: str = "Draft"
    storage_path: str = ""

matters: Dict[str, Dict[str, Any]] = {}
changes: List[Dict[str, Any]] = []
appointments: Dict[str, Dict[str, Any]] = {}
documents: Dict[str, Dict[str, Any]] = {}

@app.get("/health")
def health():
    return {"status": "ok", "service": "carbon-law", "time": datetime.utcnow().isoformat()}

@app.get("/matters")
def list_matters():
    return list(matters.values())

@app.post("/matters")
def upsert_matter(m: Matter):
    data = m.model_dump()
    now = datetime.utcnow().isoformat()
    data["updated_at"] = now
    if m.id not in matters:
        data["created_at"] = now
    matters[m.id] = data
    return data

@app.get("/matters/{matter_id}")
def get_matter(matter_id: str):
    if matter_id not in matters:
        raise HTTPException(404, "matter not found")
    return matters[matter_id]

@app.post("/change-requests")
def create_change_request(cr: ChangeRequest):
    rec = cr.model_dump()
    rec["id"] = str(uuid.uuid4())
    rec["created_at"] = datetime.utcnow().isoformat()
    changes.append(rec)
    return rec

@app.get("/change-requests")
def list_change_requests():
    return changes

@app.post("/appointments")
def create_appointment(appt: Appointment):
    rec = appt.model_dump()
    rec["id"] = str(uuid.uuid4())
    rec["created_at"] = datetime.utcnow().isoformat()
    appointments[rec["id"]] = rec
    return rec

@app.patch("/appointments/{appointment_id}")
def update_appointment(appointment_id: str, status: str, note: str = ""):
    if appointment_id not in appointments:
        raise HTTPException(404, "appointment not found")
    appointments[appointment_id]["status"] = status
    appointments[appointment_id]["note"] = note
    appointments[appointment_id]["updated_at"] = datetime.utcnow().isoformat()
    return appointments[appointment_id]

@app.get("/appointments")
def list_appointments():
    return list(appointments.values())

@app.post("/documents")
def create_document(doc: PortalDocument):
    rec = doc.model_dump()
    rec["id"] = str(uuid.uuid4())
    rec["created_at"] = datetime.utcnow().isoformat()
    documents[rec["id"]] = rec
    return rec

@app.get("/documents")
def list_documents():
    return list(documents.values())

@app.get("/reports/friday")
def friday_report():
    by_stage = {}
    for m in matters.values():
        by_stage[m["stage"]] = by_stage.get(m["stage"], 0) + 1
    return {
        "total": len(matters),
        "by_stage": by_stage,
        "high_risk": [m["id"] for m in matters.values() if m.get("risk_level") == "High"],
        "urgent": [m["id"] for m in matters.values() if m.get("priority") == "Urgent"],
        "attorney_review_queue": [m["id"] for m in matters.values() if "Review" in m.get("stage", "")],
    }


# Seed a few demo matters for simulator use
DEMO_MATTERS = [
  {"id":"CL-0001","client_name":"Avery Family Trust","stage":"6 Client Review","owner":"Paralegal A","attorney_reviewer":"Attorney 1","due_date":"2026-10-20","risk_level":"Low","priority":"Normal","next_action":"Client review of draft trust","document_status":"Draft","title_status":"Ordered","funding_status":"Instructions Sent","appointment_status":"Booked"},
  {"id":"CL-0002","client_name":"Bennett Revocable Trust","stage":"4 Drafting","owner":"Paralegal B","attorney_reviewer":"Attorney 2","due_date":"2026-10-18","risk_level":"Medium","priority":"Urgent","next_action":"Attorney redline","document_status":"In Progress","title_status":"Unconfirmed","funding_status":"Not Started","appointment_status":"Not Booked"},
  {"id":"CL-0003","client_name":"Carter Estate Plan","stage":"9 Funding","owner":"Paralegal C","attorney_reviewer":"Attorney 1","due_date":"2026-10-22","risk_level":"Low","priority":"Normal","next_action":"Funding follow-up","document_status":"Final","title_status":"Transfer Pending","funding_status":"In Progress","appointment_status":"Completed"},
  {"id":"CL-0004","client_name":"Diaz Family Trust","stage":"10 Signing","owner":"Paralegal A","attorney_reviewer":"Attorney 3","due_date":"2026-10-17","risk_level":"High","priority":"Urgent","next_action":"Signing appointment","document_status":"Final","title_status":"Confirmed","funding_status":"Not Started","appointment_status":"Booked"},
  {"id":"CL-0005","client_name":"Ellis Living Trust","stage":"1 Intake","owner":"Unassigned","attorney_reviewer":None,"due_date":"2026-10-25","risk_level":"Low","priority":"Normal","next_action":"Complete intake","document_status":"Not Started","title_status":"Unconfirmed","funding_status":"Not Started","appointment_status":"Not Booked"},
]

def seed_demo_matters():
    if not matters:
        for m in DEMO_MATTERS:
            rec = dict(m)
            rec.setdefault("blocker","None")
            rec.setdefault("notes","Demo matter")
            rec["created_at"]=datetime.utcnow().isoformat()
            rec["updated_at"]=datetime.utcnow().isoformat()
            matters[rec["id"]]=rec

seed_demo_matters()

@app.post("/seed")
def seed():
    seed_demo_matters()
    return {"seeded": len(matters), "matters": list(matters.values())}

@app.patch("/matters/{matter_id}")
def patch_matter(matter_id: str, updates: dict):
    if matter_id not in matters:
        raise HTTPException(404, "matter not found")
    matters[matter_id].update(updates)
    matters[matter_id]["updated_at"]=datetime.utcnow().isoformat()
    return matters[matter_id]


class ContactRequest(BaseModel):
    name: str
    email: str
    phone: str = ""
    message: str = ""
    service: str = "Estate Planning"

class IntakeRequest(BaseModel):
    client_name: str
    email: str
    phone: str = ""
    goals: str = ""
    assets: str = ""
    family: str = ""

PROMPT_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompt-library", "prompts", "california")
TEMPLATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "california")
contacts: List[Dict[str, Any]] = []

@app.post("/contact")
def create_contact(c: ContactRequest):
    rec = c.model_dump()
    rec["id"] = str(uuid.uuid4())
    rec["created_at"] = datetime.utcnow().isoformat()
    contacts.append(rec)
    return rec

@app.get("/contact")
def list_contacts():
    return contacts


@app.get("/prompts")
def list_prompts():
    out = []
    if os.path.isdir(PROMPT_ROOT):
        for root,_,files in os.walk(PROMPT_ROOT):
            for fn in files:
                if fn.endswith(".md"):
                    rel = os.path.relpath(os.path.join(root,fn), PROMPT_ROOT)
                    out.append({"name": rel, "path": os.path.join(root,fn)})
    return out

@app.get("/prompts/{name:path}")
def get_prompt(name: str):
    path = os.path.realpath(os.path.join(PROMPT_ROOT, name))
    if not path.startswith(os.path.realpath(PROMPT_ROOT) + os.sep) or not os.path.isfile(path):
        raise HTTPException(404, "prompt not found")
    return {"name": name, "content": open(path).read()}

@app.get("/templates")
def list_templates():
    out = []
    if os.path.isdir(TEMPLATE_ROOT):
        for root,_,files in os.walk(TEMPLATE_ROOT):
            for fn in files:
                rel = os.path.relpath(os.path.join(root,fn), TEMPLATE_ROOT)
                out.append({"name": rel, "path": os.path.join(root,fn)})
    return out

@app.get("/templates/{name:path}")
def get_template(name: str):
    path = os.path.realpath(os.path.join(TEMPLATE_ROOT, name))
    if not path.startswith(os.path.realpath(TEMPLATE_ROOT) + os.sep) or not os.path.isfile(path):
        raise HTTPException(404, "template not found")
    return {"name": name, "content": open(path).read()}


@app.patch("/change-requests/{request_id}")
def update_change_request(request_id: str, status: str, note: str = ""):
    for cr in changes:
        if cr["id"] == request_id:
            cr["status"] = status
            cr["note"] = note
            cr["updated_at"] = datetime.utcnow().isoformat()
            return cr
    raise HTTPException(404, "change request not found")

@app.patch("/appointments/{appointment_id}/status")
def update_appointment_status(appointment_id: str, status: str, note: str = ""):
    if appointment_id not in appointments:
        raise HTTPException(404, "appointment not found")
    appointments[appointment_id]["status"] = status
    appointments[appointment_id]["note"] = note
    appointments[appointment_id]["updated_at"] = datetime.utcnow().isoformat()
    return appointments[appointment_id]

@app.get("/contacts")
def list_contacts_endpoint():
    return contacts


from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
def root():
    return """
<!DOCTYPE html>
<html><head><meta charset='utf-8'><title>Carbon Law Backend</title>
<style>
body{margin:0;font-family:Arial,sans-serif;background:#f4f6f8;color:#112337;}
header{background:#112337;color:#fff;padding:16px 24px;display:flex;justify-content:space-between;align-items:center;}
header img{height:40px;}
a{color:#204ce5;text-decoration:none;font-weight:600;}
.hero{background:linear-gradient(120deg,#112337,#1b3a6b);color:#fff;padding:60px 24px;text-align:center;}
.hero h1{font-size:40px;margin:0 0 12px;}
.section{max-width:900px;margin:40px auto;padding:0 24px;}
.card{background:#fff;border-radius:10px;padding:24px;box-shadow:0 4px 14px rgba(0,0,0,.08);margin-bottom:16px;}
.btn{display:inline-block;background:#E87722;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none;font-weight:700;margin:6px;}
</style></head><body>
<header>
  <a href='https://carbon.bailment.tech'><img src='https://carbonlg.com/wp-content/uploads/2023/08/Carbon-Law-Group-LOGO.png' alt='Carbon Law Group'></a>
  <nav><a style='color:#fff;margin-left:18px;' href='https://carbon.bailment.tech'>Frontend</a><a style='color:#fff;margin-left:18px;' href='/docs'>API Docs</a><a style='color:#fff;margin-left:18px;' href='/health'>Health</a></nav>
</header>
<section class='hero'><h1>Carbon Law Backend</h1><p>API service for the Carbon Law estate planning platform.</p>
<a class='btn' href='https://carbon.bailment.tech'>Open Frontend</a>
<a class='btn' style='background:#204ce5;' href='/docs'>API Documentation</a></section>
<section class='section'>
<div class='card'><h2>Endpoints</h2><p>Health, matters, change requests, appointments, documents, contacts, intake, prompts, templates, and reports.</p></div>
<div class='card'><h2>Status</h2><p><a href='/health'>Check health</a></p></div>
</section>
</body></html>
"""


import hashlib

users: Dict[str, Dict[str, Any]] = {}
sessions: Dict[str, str] = {}  # token -> user_id

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

# seed default paralegal Kevin Mohr
if "kevin.mohr@carbonlaw.com" not in users:
    uid = str(uuid.uuid4())
    users["kevin.mohr@carbonlaw.com"] = {
        "id": uid, "name": "Kevin Mohr", "email": "kevin.mohr@carbonlaw.com",
        "role": "paralegal", "password_hash": hash_pw("paralegal123")
    }

def get_user_from_token(token: str):
    uid = sessions.get(token)
    if not uid:
        return None
    for u in users.values():
        if u["id"] == uid:
            return u
    return None

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "client"

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/auth/signup")
def signup(req: SignupRequest):
    if req.email in users:
        raise HTTPException(400, "user already exists")
    uid = str(uuid.uuid4())
    users[req.email] = {
        "id": uid, "name": req.name, "email": req.email,
        "role": "client", "password_hash": hash_pw(req.password)
    }
    # link any matters with matching client email
    for m in matters.values():
        if m.get("client_email") == req.email:
            m["client_user_id"] = uid
    token = str(uuid.uuid4())
    sessions[token] = uid
    return {"token": token, "user": users[req.email]}

@app.post("/auth/login")
def login(req: LoginRequest):
    u = users.get(req.email)
    if not u or u["password_hash"] != hash_pw(req.password):
        raise HTTPException(401, "invalid credentials")
    token = str(uuid.uuid4())
    sessions[token] = u["id"]
    return {"token": token, "user": u}

@app.get("/auth/me")
def me(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    token = authorization.replace("Bearer ", "").strip()
    u = get_user_from_token(token)
    if not u:
        raise HTTPException(401, "not authenticated")
    return u

# Update IntakeRequest to store client email and assign default paralegal
# redefine intake endpoint by overwriting? We'll patch IntakeRequest usage via new endpoint /intake/v2

import json as _json
import urllib.request as _urlreq
import urllib.error as _urlerr

def send_signup_email(to_email: str, client_name: str):
    link = f"https://carbon.bailment.tech/signup.html?email={to_email}"
    subject = "Create your Carbon Law client portal account"
    body = f"""Hello {client_name},

Thank you for starting your estate planning matter with Carbon Law Group.

Please create your client portal account here:
{link}

Once you sign up, you can review documents, schedule appointments, and message your attorney.

Best,
Carbon Law Group
"""
    # 1) HTTP webhook (works on hosts that block SMTP, e.g. Render free tier)
    webhook = os.environ.get("EMAIL_WEBHOOK_URL")
    if webhook:
        try:
            payload = _json.dumps({
                "to": to_email,
                "subject": subject,
                "body": body,
                "from": os.environ.get("SMTP_FROM") or os.environ.get("SMTP_USER") or "bestfriendkevin@gmail.com",
            }).encode()
            req = _urlreq.Request(webhook, data=payload, headers={"Content-Type": "application/json"})
            secret = os.environ.get("EMAIL_WEBHOOK_SECRET")
            if secret:
                req.add_header("X-Webhook-Secret", secret)
            with _urlreq.urlopen(req, timeout=20) as resp:
                print("EMAIL WEBHOOK OK:", resp.status, flush=True)
                return True
        except Exception as e:
            print("EMAIL WEBHOOK ERROR:", repr(e), flush=True)
    # 2) SMTP fallback (local/dev or hosts that allow outbound SMTP)
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    if not user or not password:
        print("EMAIL: no SMTP credentials and no EMAIL_WEBHOOK_URL", flush=True)
        return False
    if os.environ.get("RENDER") and not webhook:
        print("EMAIL: running on Render without webhook; skipping blocked SMTP", flush=True)
        return False
    from_addr = os.environ.get("SMTP_FROM", user)
    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP(host, port, timeout=8) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception as e:
        print("SMTP ERROR:", repr(e), flush=True)
        return False

class IntakeRequestV2(BaseModel):
    client_name: str
    email: str
    phone: str = ""
    goals: str = ""
    assets: str = ""
    family: str = ""

@app.post("/intake")
def create_intake_v2(i: IntakeRequestV2):
    matter_id = "CL-" + str(len(matters)+1).zfill(4)
    rec = {
        "id": matter_id,
        "client_name": i.client_name,
        "client_email": i.email,
        "stage": "1 Intake",
        "owner": "Kevin Mohr",
        "attorney_reviewer": None,
        "due_date": None,
        "risk_level": "Low",
        "priority": "Normal",
        "next_action": "Review intake and schedule consultation",
        "notes": f"Email: {i.email}; Phone: {i.phone}; Goals: {i.goals}; Assets: {i.assets}; Family: {i.family}",
        "document_status": "Not Started",
        "title_status": "Unconfirmed",
        "funding_status": "Not Started",
        "appointment_status": "Not Booked",
        "blocker": "None",
        "client_user_id": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    matters[matter_id] = rec
    sent = send_signup_email(i.email, i.client_name)
    return {"message": "Thank you. Please check your email for a sign-up link to create your account and access your client portal.", "email_sent": sent, "signup_url": f"https://carbon.bailment.tech/signup.html?email={i.email}"}

@app.get("/my-matters")
def my_matters(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    token = authorization.replace("Bearer ", "").strip()
    u = get_user_from_token(token)
    if not u:
        raise HTTPException(401, "not authenticated")
    if u["role"] in ("paralegal","attorney"):
        return list(matters.values())
    return [m for m in matters.values() if m.get("client_user_id") == u["id"] or m.get("client_email") == u["email"]]
