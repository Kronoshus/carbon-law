import os, json, uuid, hashlib, hmac, datetime, smtplib, csv, io, asyncio
from fastapi import FastAPI, HTTPException, Header, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any

APP_DIR = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, APP_DIR)
import db as _db
ROOT_DIR = os.path.dirname(APP_DIR)
DATA_FILE = os.path.join(APP_DIR, "data.json")
PROMPT_ROOT = os.path.join(ROOT_DIR, "prompt-library", "prompts", "california")
TEMPLATE_ROOT = os.path.join(ROOT_DIR, "templates", "california")

STAGES = [
    "1 Intake", "2 Attorney Scope", "3 Client Data Collection", "4 Drafting",
    "5 Review Queue", "6 Client Review", "7 Signing Preparation", "8 Execution",
    "9 Funding Follow-Up", "10 Closed",
]
RISK_LEVELS = {"Low", "Medium", "High"}
PRIORITIES = {"Normal", "Urgent", "Low"}
ROLES = {"client", "paralegal", "attorney", "admin"}

app = FastAPI(title="Carbon Law Backend", version="0.4.0", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CORSMiddleware,
                   allow_origins=["https://carbon.bailment.tech", "http://127.0.0.1:8080", "http://localhost:8080"],
                   allow_credentials=False, allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
                   allow_headers=["Authorization", "Content-Type"])

# Handlers share the in-memory dicts below and save them as whole JSON blobs, so run one request at a time.
# /health touches no shared state and must answer Render's health check even while a slow request runs.
_request_lock = asyncio.Lock()

@app.middleware("http")
async def serialize_requests(request, call_next):
    if request.url.path == "/health":
        return await call_next(request)
    async with _request_lock:
        return await call_next(request)

# ---------- in-memory stores (persisted to data.json) ----------
matters: Dict[str, Dict[str, Any]] = {}
changes: List[Dict[str, Any]] = []
appointments: Dict[str, Dict[str, Any]] = {}
documents: Dict[str, Dict[str, Any]] = {}
users: Dict[str, Dict[str, Any]] = {}
sessions: Dict[str, Dict[str, Any]] = {}
contacts: List[Dict[str, Any]] = []
tasks: Dict[str, Dict[str, Any]] = {}
audit: List[Dict[str, Any]] = []
comms: List[Dict[str, Any]] = {}
stage_history: Dict[str, List[Dict[str, Any]]] = {}
workflows: Dict[str, Dict[str, Any]] = {}

def now_iso():
    return datetime.datetime.utcnow().isoformat()

def load_data():
    global matters, changes, appointments, documents, users, sessions, contacts, tasks, audit, comms, stage_history, workflows
    matters = _db.load_collection("matters", {})
    changes = _db.load_collection("changes", [])
    appointments = _db.load_collection("appointments", {})
    documents = _db.load_collection("documents", {})
    users = _db.load_collection("users", {})
    sessions = _db.load_collection("sessions", {})
    contacts = _db.load_collection("contacts", [])
    tasks = _db.load_collection("tasks", {})
    audit = _db.load_collection("audit", [])
    comms = _db.load_collection("comms", [])
    stage_history = _db.load_collection("stage_history", {})
    workflows = _db.load_collection("workflows", {})
    # migrate from legacy JSON if DB empty
    if not matters and os.path.exists(DATA_FILE) and os.environ.get("IMPORT_LEGACY_JSON") == "1":
        try:
            d = json.load(open(DATA_FILE))
            matters.update(d.get("matters", {}))
            changes.extend(d.get("changes", []))
            appointments.update(d.get("appointments", {}))
            documents.update(d.get("documents", {}))
            users.update(d.get("users", {}))
            sessions.update(d.get("sessions", {}))
            contacts.extend(d.get("contacts", []))
            tasks.update(d.get("tasks", {}))
            audit.extend(d.get("audit", []))
            comms.extend(d.get("comms", []))
            stage_history.update(d.get("stage_history", {}))
            save_data()
        except Exception as e:
            print("migrate error", e)

def save_data():
    try:
        _db.save_collection("matters", matters)
        _db.save_collection("changes", changes)
        _db.save_collection("appointments", appointments)
        _db.save_collection("documents", documents)
        _db.save_collection("users", users)
        _db.save_collection("sessions", sessions)
        _db.save_collection("contacts", contacts)
        _db.save_collection("tasks", tasks)
        _db.save_collection("audit", audit)
        _db.save_collection("comms", comms)
        _db.save_collection("stage_history", stage_history)
        _db.save_collection("workflows", workflows)
    except Exception:
        raise

load_data()

def log_audit(actor, action, entity, entity_id, detail=""):
    audit.append({"id": str(uuid.uuid4()), "time": now_iso(), "actor": actor,
                  "action": action, "entity": entity, "entity_id": entity_id, "detail": detail})
    if len(audit) > 5000:
        del audit[:1000]
    save_data()

# Staff users must be provisioned out-of-band before deployment.

def public_user(user):
    return {key: user[key] for key in ("id", "name", "email", "role", "created_at") if key in user}

def hash_pw(pw):
    salt = os.urandom(16)
    digest = hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$" + salt.hex() + "$" + digest.hex()

def verify_pw(pw, encoded):
    if encoded.startswith("scrypt$"):
        _, salt, expected = encoded.split("$", 2)
        actual = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
        return hmac.compare_digest(actual.hex(), expected)
    return hashlib.sha256(pw.encode()).hexdigest() == encoded

def get_user_from_token(token):
    s = sessions.get(token)
    if not s: return None
    if isinstance(s, str):
        # legacy
        uid = s
        exp = None
    else:
        uid = s.get("user_id"); exp = s.get("expires")
    if exp and datetime.datetime.fromisoformat(exp) < datetime.datetime.utcnow():
        del sessions[token]; save_data(); return None
    for u in users.values():
        if u["id"] == uid:
            return u
    return None

def require_auth(authorization, roles=None):
    if not authorization:
        raise HTTPException(401, "not authenticated")
    token = authorization.replace("Bearer ", "").strip()
    u = get_user_from_token(token)
    if not u:
        raise HTTPException(401, "not authenticated")
    if roles and u["role"] not in roles:
        raise HTTPException(403, "insufficient role")
    return u, token

# ---------- models ----------
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
    client_email: Optional[str] = None
    client_user_id: Optional[str] = None

class ChangeRequest(BaseModel):
    matter_id: str
    requested_by: str = "client"
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

class ContactRequest(BaseModel):
    name: str = Field(max_length=120)
    email: str = Field(max_length=254)
    phone: str = Field(default="", max_length=40)
    message: str = Field(default="", max_length=500)
    service: str = Field(default="Estate Planning", max_length=80)

class IntakeRequest(BaseModel):
    client_name: str = Field(max_length=120)
    email: str = Field(max_length=254)
    phone: str = Field(default="", max_length=40)
    documents_requested: List[str] = Field(default_factory=list, max_length=4)
    goals: str = Field(default="", max_length=500)
    assets: str = Field(default="", max_length=0)
    family: str = Field(default="", max_length=0)

class WorkflowStart(BaseModel):
    phone: str = Field(default="", max_length=40)
    client_name: Optional[str] = Field(default=None, max_length=120)
    related_names: List[str] = Field(default_factory=list, max_length=20)
    demo_mode: bool = False

class WorkflowDocuments(BaseModel):
    documents_requested: List[str] = Field(min_length=1, max_length=4)

class WorkflowIntake(BaseModel):
    general: Dict[str, Any] = Field(default_factory=dict)
    documents: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

class WorkflowDecision(BaseModel):
    decision: str
    note: str = Field(default="", max_length=1000)

class WorkflowAppointment(BaseModel):
    kind: str
    scheduled_at: str = Field(min_length=1, max_length=40)

class WorkflowSection(BaseModel):
    part: int = Field(ge=1, le=7)

class WorkflowConflictInfo(BaseModel):
    phone: str = Field(default="", max_length=40)
    client_name: Optional[str] = Field(default=None, max_length=120)
    related_names: List[str] = Field(default_factory=list, max_length=20)
    demo_mode: bool = False

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "client"

class LoginRequest(BaseModel):
    email: str
    password: str

class Task(BaseModel):
    matter_id: str
    title: str
    owner: str = "Unassigned"
    due_date: Optional[str] = None
    status: str = "Open"
    blocker: str = "None"

class CommEntry(BaseModel):
    matter_id: str
    channel: str = "email"
    direction: str = "outbound"
    summary: str
    visibility: str = "internal"

# ---------- helpers ----------
def send_signup_email(to_email, client_name):
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
    webhook = os.environ.get("EMAIL_WEBHOOK_URL")
    if webhook:
        try:
            import urllib.request, urllib.error, json as _j
            payload = _j.dumps({"to":to_email,"subject":subject,"body":body,
                "from": os.environ.get("SMTP_FROM", "info@carbonlaw.com")}).encode()
            req = urllib.request.Request(webhook, data=payload, headers={"Content-Type":"application/json"})
            secret = os.environ.get("EMAIL_WEBHOOK_SECRET")
            if secret: req.add_header("X-Webhook-Secret", secret)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return True
        except Exception as e:
            print("EMAIL WEBHOOK ERROR:", repr(e))
    host = os.environ.get("SMTP_HOST","smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT","587"))
    user = os.environ.get("SMTP_USER"); password = os.environ.get("SMTP_PASS")
    if not user or not password:
        print("EMAIL: no SMTP credentials"); return False
    if os.environ.get("RENDER") and not os.environ.get("EMAIL_WEBHOOK_URL"):
        print("EMAIL: running on Render without webhook; skipping"); return False
    from_addr = os.environ.get("SMTP_FROM", "info@carbonlaw.com")
    msg = None
    try:
        import smtplib as _s
        from email.mime.text import MIMEText as _MT
        from email.mime.multipart import MIMEMultipart as _MM
        msg = _MM(); msg["From"]=from_addr; msg["To"]=to_email; msg["Subject"]=subject
        msg.attach(_MT(body,"plain"))
        with _s.SMTP(host,port,timeout=8) as server:
            server.starttls(); server.login(user,password); server.send_message(msg)
        return True
    except Exception as e:
        print("SMTP ERROR:", repr(e)); return False

# ---------- routes ----------
@app.get("/health")
def health():
    return {"status":"ok","service":"carbon-law","time":now_iso()}

@app.get("/")
def root():
    return HTMLResponse("<h1>Carbon Law Backend</h1><p><a href='/docs'>API Docs</a> | <a href='/health'>Health</a></p>")

# matters
@app.get("/matters")
def list_matters(stage: Optional[str]=None, owner: Optional[str]=None,
                 risk: Optional[str]=None, q: Optional[str]=None,
                 overdue: bool=False, limit: int=Query(200,le=1000),
                 authorization: Optional[str]=Header(None)):
    u,_ = require_auth(authorization)
    out = list(matters.values()) if u["role"] in ("paralegal","attorney","admin") else [{k:v for k,v in m.items() if k not in {"notes", "client_email", "client_user_id"}} for m in matters.values() if m.get("client_user_id")==u["id"]]
    if stage: out = [m for m in out if m.get("stage")==stage]
    if owner: out = [m for m in out if m.get("owner")==owner]
    if risk: out = [m for m in out if m.get("risk_level")==risk]
    if q:
        ql = q.lower()
        out = [m for m in out if ql in (m.get("id","")+m.get("client_name","")).lower()]
    if overdue:
        today = datetime.date.today().isoformat()
        out = [m for m in out if m.get("due_date") and m["due_date"] < today and m.get("stage")!="10 Closed"]
    return out[:limit]

@app.post("/matters")
def upsert_matter(m: Matter, authorization: Optional[str]=Header(None)):
    require_auth(authorization, {"paralegal","attorney","admin"})
    if m.id in matters:
        raise HTTPException(409, "matter already exists; use PATCH")
    if m.stage not in STAGES:
        raise HTTPException(400, f"invalid stage; allowed: {STAGES}")
    if m.risk_level not in RISK_LEVELS:
        raise HTTPException(400, "invalid risk_level")
    if m.priority not in PRIORITIES:
        raise HTTPException(400, "invalid priority")
    data = m.model_dump(); data["created_at"]=now_iso(); data["updated_at"]=now_iso()
    matters[m.id]=data
    stage_history[m.id]=[{"stage":m.stage,"time":now_iso(),"by":"system"}]
    log_audit("system","create","matter",m.id,m.client_name)
    save_data()
    return data

@app.get("/matters/{matter_id}")
def get_matter(matter_id: str, authorization: Optional[str]=Header(None)):
    u,_ = require_auth(authorization)
    if matter_id not in matters: raise HTTPException(404,"matter not found")
    matter = matters[matter_id]
    if u["role"] not in ("paralegal","attorney","admin") and matter.get("client_user_id") != u["id"]:
        raise HTTPException(403,"matter access denied")
    client_fields = {"id", "client_name", "stage", "document_status", "title_status", "funding_status", "appointment_status", "created_at", "updated_at"}
    return matter if u["role"] in ("paralegal","attorney","admin") else {k:v for k,v in matter.items() if k in client_fields}

@app.patch("/matters/{matter_id}")
def patch_matter(matter_id: str, updates: dict, authorization: Optional[str]=Header(None)):
    u,_ = require_auth(authorization, {"paralegal","attorney","admin"})
    if matter_id not in matters: raise HTTPException(404,"matter not found")
    allowed_fields = {"client_name", "stage", "owner", "attorney_reviewer", "due_date", "last_client_contact", "next_client_contact", "next_action", "blocker", "document_status", "title_status", "funding_status", "appointment_status", "risk_level", "priority", "notes"}
    if set(updates) - allowed_fields: raise HTTPException(400,"unsupported matter fields")
    if "stage" in updates and updates["stage"] not in STAGES:
        raise HTTPException(400,"invalid stage")
    if "risk_level" in updates and updates["risk_level"] not in RISK_LEVELS:
        raise HTTPException(400,"invalid risk_level")
    old_stage = matters[matter_id].get("stage")
    matters[matter_id].update(updates)
    matters[matter_id]["updated_at"]=now_iso()
    if "stage" in updates and updates["stage"] != old_stage:
        stage_history.setdefault(matter_id,[]).append(
            {"stage":updates["stage"],"time":now_iso(),"by":u["email"]})
        workflow_stage = {"1 Intake":"conflict_review", "2 Attorney Scope":"document_selection", "3 Client Data Collection":"intake", "4 Drafting":"draft_ready", "5 Review Queue":"attorney_review", "6 Client Review":"client_review", "7 Signing Preparation":"consultation", "8 Execution":"signing", "9 Funding Follow-Up":"signing", "10 Closed":"complete"}.get(updates["stage"])
        for workflow in workflows.values():
            if workflow.get("matter_id") == matter_id and workflow_stage:
                workflow["stage"] = workflow_stage; workflow["updated_at"] = now_iso()
                if workflow_stage in {"conflict_review", "document_selection", "intake", "draft_ready"}:
                    workflow["client_approved"] = False; workflow["attorney_approved"] = False; workflow["drafts"] = {}
    log_audit(u["email"],"update","matter",matter_id,str(updates))
    save_data()
    return matters[matter_id]

@app.get("/matters/{matter_id}/history")
def matter_history(matter_id: str, authorization: Optional[str]=Header(None)):
    require_auth(authorization, {"paralegal","attorney","admin"})
    if matter_id not in matters: raise HTTPException(404,"matter not found")
    return {"matter_id":matter_id,"stages":stage_history.get(matter_id,[]),
            "tasks":[t for t in tasks.values() if t["matter_id"]==matter_id],
            "changes":[c for c in changes if c["matter_id"]==matter_id],
            "comms":[c for c in comms if c["matter_id"]==matter_id]}

# change requests
@app.post("/change-requests")
def create_change_request(cr: ChangeRequest, authorization: Optional[str]=Header(None)):
    u,_ = require_auth(authorization)
    if cr.matter_id not in matters: raise HTTPException(404,"matter not found")
    if u["role"] == "client" and matters[cr.matter_id].get("client_user_id") != u["id"]:
        raise HTTPException(403,"matter access denied")
    rec = cr.model_dump()
    if u["role"] == "client":
        rec["requested_by"] = u["email"]
        rec["status"] = "Open"
    rec["id"]=str(uuid.uuid4()); rec["created_at"]=now_iso()
    # auto-create revision task and retain its link for status changes
    tid = str(uuid.uuid4())
    tasks[tid] = {"id":tid,"matter_id":cr.matter_id,"title":f"Review change: {cr.change_type}",
                  "owner":matters[cr.matter_id].get("owner","Unassigned"),"due_date":None,
                  "status":"Open","blocker":"None","created_at":now_iso()}
    rec["task_id"] = tid
    changes.append(rec)
    log_audit(u["email"],"create","change_request",rec["id"],cr.change_type)
    save_data()
    return rec

@app.get("/change-requests")
def list_change_requests(matter_id: Optional[str]=None, status: Optional[str]=None, authorization: Optional[str]=Header(None)):
    u,_ = require_auth(authorization)
    out = list(changes) if u["role"] in ("paralegal","attorney","admin") else [c for c in changes if matters.get(c["matter_id"],{}).get("client_user_id")==u["id"]]
    if matter_id: out=[c for c in out if c["matter_id"]==matter_id]
    if status: out=[c for c in out if c["status"]==status]
    return out

@app.patch("/change-requests/{request_id}")
def update_change_request(request_id: str, payload: Dict[str, Any] = Body(default={}), authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"paralegal","attorney","admin"})
    allowed = {"Open", "In Review", "Resolved", "Rejected"}
    if payload.get("status") is not None and payload["status"] not in allowed:
        raise HTTPException(400, "invalid change request status")
    if set(payload) - {"status", "note", "resolution"}:
        raise HTTPException(400, "unsupported change request fields")
    for cr in changes:
        if cr["id"] == request_id:
            cr.update({key:value for key,value in payload.items() if value is not None})
            cr["updated_at"] = now_iso()
            if payload.get("status") in {"Resolved", "Rejected"} and cr.get("task_id") in tasks:
                tasks[cr["task_id"]]["status"] = "Done"; tasks[cr["task_id"]]["updated_at"] = now_iso()
            log_audit(user["email"], "update", "change_request", request_id, payload.get("status", "updated"))
            save_data()
            return cr
    raise HTTPException(404, "change request not found")

# appointments
@app.post("/appointments")
def create_appointment(appt: Appointment, authorization: Optional[str]=Header(None)):
    u,_ = require_auth(authorization)
    if appt.matter_id not in matters: raise HTTPException(404,"matter not found")
    if u["role"] == "client" and matters[appt.matter_id].get("client_user_id") != u["id"]:
        raise HTTPException(403,"matter access denied")
    rec = appt.model_dump()
    if u["role"] == "client":
        rec["status"] = "Requested"
        rec["kind"] = "Signing"
        rec["note"] = "Client requested an in-person signing appointment"
    rec["id"]=str(uuid.uuid4()); rec["created_at"]=now_iso()
    appointments[rec["id"]]=rec
    matters[appt.matter_id]["appointment_status"]=appt.status
    matters[appt.matter_id]["updated_at"]=now_iso()
    log_audit("user","create","appointment",rec["id"],appt.kind)
    save_data()
    return rec

@app.get("/appointments")
def list_appointments(matter_id: Optional[str]=None, status: Optional[str]=None, authorization: Optional[str]=Header(None)):
    u,_ = require_auth(authorization)
    out = list(appointments.values()) if u["role"] in ("paralegal","attorney","admin") else [a for a in appointments.values() if matters.get(a["matter_id"],{}).get("client_user_id")==u["id"]]
    if matter_id: out=[a for a in out if a["matter_id"]==matter_id]
    if status: out=[a for a in out if a["status"]==status]
    return out

@app.patch("/appointments/{appointment_id}")
def update_appointment(appointment_id: str, status: Optional[str]=None, note: Optional[str]=None,
                      scheduled_at: Optional[str]=None, authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization)
    if appointment_id not in appointments: raise HTTPException(404,"appointment not found")
    appointment = appointments[appointment_id]
    matter = matters.get(appointment["matter_id"])
    if user["role"] == "client":
        if not matter or matter.get("client_user_id") != user["id"]: raise HTTPException(404,"appointment not found")
        if status != "Cancelled": raise HTTPException(403,"Clients may only cancel appointments")
    elif user["role"] not in {"paralegal","attorney","admin"}:
        raise HTTPException(403,"Staff access required")
    allowed_statuses = {"Requested", "Scheduled", "Cancelled", "Completed", "Booked", "Rescheduled"}
    if status and status not in allowed_statuses:
        raise HTTPException(400, "invalid appointment status")
    if status: appointment["status"] = status
    if note is not None: appointment["note"] = note
    if scheduled_at: appointment["scheduled_at"] = scheduled_at
    appointment["updated_at"] = now_iso()
    mid = appointments[appointment_id]["matter_id"]
    if mid in matters and status:
        matters[mid]["appointment_status"]=status; matters[mid]["updated_at"]=now_iso()
    if appointment.get("workflow_id") in workflows:
        workflow = workflows[appointment["workflow_id"]]
        kind = appointment.get("kind")
        if kind in workflow.get("appointments", {}):
            detail = workflow["appointments"][kind]
            if status == "Cancelled": detail["status"] = "cancelled"
            elif status in {"Scheduled", "Booked", "Rescheduled"}: detail["status"] = "scheduled"
            if scheduled_at: detail["scheduled_at"] = scheduled_at
            elif status in {"Scheduled", "Booked", "Rescheduled"}: detail["scheduled_at"] = appointment.get("scheduled_at")
            workflow["updated_at"] = now_iso()
            if status in {"Scheduled", "Booked", "Rescheduled"} and workflow["stage"] in {"consultation", "signing"}:
                workflow["stage"] = "complete" if kind == "signing" and workflow.get("appointments", {}).get("consultation", {}).get("status") == "completed" else workflow["stage"]
    actor = user["email"]
    log_audit(actor,"update","appointment",appointment_id,status or ("rescheduled" if scheduled_at else "updated"))
    save_data()
    return appointments[appointment_id]

# documents
@app.post("/documents")
def create_document(doc: PortalDocument, authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"paralegal","attorney","admin"})
    if doc.matter_id not in matters: raise HTTPException(404,"matter not found")
    # auto-version: if same name exists, increment
    existing = [d for d in documents.values() if d["matter_id"]==doc.matter_id and d["name"]==doc.name]
    if existing:
        doc.version = max(d["version"] for d in existing)+1
    rec = doc.model_dump(); rec["id"]=str(uuid.uuid4()); rec["created_at"]=now_iso()
    documents[rec["id"]]=rec
    log_audit(user["email"],"create","document",rec["id"],doc.name)
    save_data()
    return rec

@app.get("/documents")
def list_documents(matter_id: Optional[str]=None, status: Optional[str]=None, authorization: Optional[str]=Header(None)):
    u,_ = require_auth(authorization)
    out = list(documents.values()) if u["role"] in ("paralegal","attorney","admin") else [d for d in documents.values() if matters.get(d["matter_id"],{}).get("client_user_id")==u["id"] and d.get("status") == "Client Review"]
    if matter_id: out=[d for d in out if d["matter_id"]==matter_id]
    if status: out=[d for d in out if d["status"]==status]
    return out

@app.patch("/documents/{doc_id}")
def update_document(doc_id: str, status: Optional[str]=None, version: Optional[int]=None,
                   authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"paralegal","attorney","admin"})
    if doc_id not in documents: raise HTTPException(404,"document not found")
    if status: documents[doc_id]["status"]=status
    if version: documents[doc_id]["version"]=version
    documents[doc_id]["updated_at"]=now_iso()
    log_audit(user["email"],"update","document",doc_id,status or "updated")
    save_data()
    return documents[doc_id]

# contacts
@app.post("/contact")
def create_contact(c: ContactRequest):
    rec = c.model_dump(); rec["id"]=str(uuid.uuid4()); rec["created_at"]=now_iso(); rec["status"]="New"
    contacts.append(rec)
    log_audit("public","create","contact",rec["id"],c.name)
    save_data()
    return rec

@app.get("/contacts")
def list_contacts(status: Optional[str]=None, authorization: Optional[str]=Header(None)):
    require_auth(authorization, {"paralegal","attorney","admin"})
    out = list(contacts)
    if status: out=[c for c in out if c.get("status")==status]
    return out

@app.patch("/contacts/{contact_id}")
def update_contact(contact_id: str, payload: Dict[str, Any] = Body(default={}),
                   authorization: Optional[str]=Header(None)):
    require_auth(authorization, {"paralegal","attorney","admin"})
    for c in contacts:
        if c["id"]==contact_id:
            if payload.get("status") is not None:
                if payload["status"] not in {"New", "Contacted", "Consultation Scheduled", "Converted", "Closed"}:
                    raise HTTPException(400, "invalid contact status")
                c["status"] = payload["status"]
            if "note" in payload and payload["note"] is not None:
                c["note"]=payload["note"]
            c["updated_at"]=now_iso(); log_audit(user["email"],"update","contact",contact_id,str(payload)); save_data(); return c
    raise HTTPException(404,"contact not found")

# intake
@app.post("/intake")
def create_intake(i: IntakeRequest, authorization: Optional[str]=Header(None)):
    u,_ = require_auth(authorization, {"client"})
    if i.email.lower() != u["email"].lower():
        raise HTTPException(403,"intake email must match the signed-in account")
    allowed_documents = {"Revocable living trust", "Pour-over will", "Advance health care directive", "Financial power of attorney"}
    if not i.documents_requested or not set(i.documents_requested) <= allowed_documents:
        raise HTTPException(400,"select at least one supported document")
    rec = {"id":str(uuid.uuid4()),"name":i.client_name,"email":u["email"],"phone":i.phone,
           "service":"; ".join(i.documents_requested),"message":i.goals[:500],"status":"New",
           "created_at":now_iso(),"source":"private consultation request"}
    contacts.append(rec)
    log_audit(u["email"],"create","consultation_request",rec["id"],"document types only")
    save_data()
    return {"message":"Request received. This is not an engagement or legal advice. The firm will contact you about conflicts and next steps before asking for detailed information.","request_id":rec["id"]}

WORKFLOW_DOCUMENTS = {"Revocable living trust", "Pour-over will", "Advance health care directive", "Financial power of attorney"}


def client_workflow(user):
    matches = [w for w in workflows.values() if w["client_user_id"] == user["id"]]
    return max(matches, key=lambda w: w["updated_at"]) if matches else None


def ensure_workflow_matter(workflow):
    if workflow.get("matter_id") in matters:
        return matters[workflow["matter_id"]]
    matter_id = "CL-" + workflow["id"].replace("-", "")[:8].upper()
    matter = {"id":matter_id,"client_name":workflow["client_name"],"stage":"1 Intake","owner":"Unassigned",
        "document_status":"Not Started","risk_level":"Low","priority":"Normal","client_email":workflow["client_email"],
        "client_user_id":workflow["client_user_id"],"created_at":workflow["created_at"],"updated_at":now_iso()}
    matters[matter_id] = matter
    workflow["matter_id"] = matter_id
    stage_history[matter_id] = [{"stage":"1 Intake","time":now_iso(),"by":"system"}]
    save_data()
    return matter


@app.get("/my-workflows")
def my_workflows(authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"client"})
    owned = [workflow for workflow in workflows.values() if workflow["client_user_id"] == user["id"]]
    for workflow in owned:
        ensure_workflow_matter(workflow)
    safe = [{k:v for k,v in workflow.items() if k not in {"staff_review_note"}} for workflow in owned]
    return sorted(safe, key=lambda workflow: workflow["created_at"], reverse=True)


@app.get("/my-workflow")
def my_workflow(authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization)
    if user["role"] in ("paralegal", "attorney", "admin"):
        return list(workflows.values())
    workflow = client_workflow(user)
    if workflow:
        ensure_workflow_matter(workflow)
        return {k:v for k,v in workflow.items() if k != "staff_review_note"}
    return workflow


@app.post("/workflows")
def start_workflow(req: WorkflowStart, authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"client"})
    now = now_iso()
    workflow = {"id":str(uuid.uuid4()), "client_user_id":user["id"], "client_name":req.client_name.strip() if req.client_name and req.client_name.strip() else user["name"],
        "client_email":user["email"], "phone":req.phone, "related_names":[name.strip()[:120] for name in req.related_names if name.strip()], "documents_requested":[],
        "stage":"conflict_review", "conflict_status":"pending", "demo_mode":req.demo_mode, "intake":{}, "drafts":{},
        "client_approved":False, "attorney_approved":False, "appointments":{},
        "created_at":now, "updated_at":now}
    workflows[workflow["id"]] = workflow
    ensure_workflow_matter(workflow)
    log_audit(user["email"], "create", "workflow", workflow["id"], "conflict review requested")
    save_data()
    return workflow


@app.patch("/workflows/{workflow_id}/conflict-info")
def update_workflow_conflict_info(workflow_id: str, req: WorkflowConflictInfo, authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"client"})
    workflow = workflows.get(workflow_id)
    if not workflow or workflow["client_user_id"] != user["id"]: raise HTTPException(404, "request not found")
    if workflow["stage"] != "conflict_review": raise HTTPException(409, "Conflict information is locked after review")
    workflow["phone"] = req.phone
    if req.client_name and req.client_name.strip(): workflow["client_name"] = req.client_name.strip()
    workflow["related_names"] = [name.strip()[:120] for name in req.related_names if name.strip()]
    workflow["demo_mode"] = req.demo_mode
    workflow["updated_at"] = now_iso(); save_data(); return workflow


@app.post("/workflows/{workflow_id}/reopen-section")
def reopen_workflow_section(workflow_id: str, req: WorkflowSection, authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"client"})
    workflow = workflows.get(workflow_id)
    if not workflow or workflow["client_user_id"] != user["id"]: raise HTTPException(404, "request not found")
    stages = {1:"conflict_review",2:"document_selection",3:"intake",4:"draft_ready",5:"attorney_review",6:"consultation",7:"consultation"}
    if req.part == 1:
        workflow["conflict_status"] = "pending"
        workflow["conflict_reviewed_at"] = None
    elif req.part > 2 and workflow.get("conflict_status") not in {"cleared", "demo_cleared"}:
        raise HTTPException(409, "Complete conflict review first")
    if workflow.get("conflict_status") == "flagged" and req.part > 1:
        raise HTTPException(409, "Conflict review must be resolved before continuing")
    workflow["stage"] = stages[req.part]
    if req.part <= 4:
        workflow["client_approved"] = False
        workflow["attorney_approved"] = False
        workflow["drafts"] = {}
    workflow["updated_at"] = now_iso(); save_data(); return workflow


@app.post("/workflows/{workflow_id}/enable-demo-review")
def enable_demo_review(workflow_id: str, authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"client"})
    workflow = workflows.get(workflow_id)
    if not workflow or workflow["client_user_id"] != user["id"]: raise HTTPException(404, "request not found")
    if workflow["stage"] != "conflict_review": raise HTTPException(409, "Conflict review is not pending")
    workflow["demo_mode"] = True
    workflow["updated_at"] = now_iso()
    save_data()
    return workflow


@app.post("/workflows/{workflow_id}/demo-conflict-review")
def demo_conflict_review(workflow_id: str, authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"client"})
    workflow = workflows.get(workflow_id)
    if not workflow or workflow["client_user_id"] != user["id"]: raise HTTPException(404, "request not found")
    if not workflow.get("demo_mode"): raise HTTPException(403, "Demo review is not enabled for this request")
    if workflow["stage"] != "conflict_review": raise HTTPException(409, "Conflict review is not pending")
    created = datetime.datetime.fromisoformat(workflow["created_at"])
    if (datetime.datetime.utcnow() - created).total_seconds() < 5: raise HTTPException(429, "Please wait for the demo review simulation to finish")
    workflow["conflict_status"] = "demo_cleared"
    workflow["conflict_reviewed_at"] = now_iso()
    workflow["stage"] = "document_selection"
    workflow["updated_at"] = now_iso()
    log_audit(user["email"], "demo_review", "workflow", workflow_id, "simulated conflict review; not a real clearance")
    save_data()
    return workflow


@app.patch("/workflows/{workflow_id}/documents")
def select_workflow_documents(workflow_id: str, req: WorkflowDocuments, authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"client"})
    workflow = workflows.get(workflow_id)
    if not workflow or workflow["client_user_id"] != user["id"]: raise HTTPException(404, "request not found")
    if workflow["stage"] not in {"document_selection", "intake", "draft_ready"}: raise HTTPException(409, "Documents cannot be changed at this stage")
    if not req.documents_requested or not set(req.documents_requested) <= WORKFLOW_DOCUMENTS: raise HTTPException(400, "Select at least one supported document")
    workflow["documents_requested"] = req.documents_requested
    workflow.setdefault("intake", {})["documents"] = {k:v for k,v in workflow.get("intake", {}).get("documents", {}).items() if k in req.documents_requested}
    workflow["drafts"] = {}
    workflow["stage"] = "intake"; workflow["updated_at"] = now_iso(); save_data()
    return workflow


@app.patch("/workflows/{workflow_id}/intake")
def save_workflow_intake(workflow_id: str, req: WorkflowIntake, authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"client"})
    workflow = workflows.get(workflow_id)
    if not workflow or workflow["client_user_id"] != user["id"]: raise HTTPException(404, "request not found")
    if workflow["conflict_status"] not in {"cleared", "demo_cleared"}: raise HTTPException(409, "Complete conflict review before detailed intake")
    if workflow["stage"] not in {"intake", "draft_ready"}: raise HTTPException(409, "Use the modify-request action before editing this intake")
    workflow["intake"] = {"general": req.general, "documents": {k:v for k,v in req.documents.items() if k in workflow["documents_requested"]}}
    if workflow.get("matter_id") in matters:
        matter = matters[workflow["matter_id"]]
        if matter.get("stage") != "4 Drafting":
            matter["stage"] = "4 Drafting"
            stage_history.setdefault(matter["id"], []).append({"stage":"4 Drafting","time":now_iso(),"by":user["email"]})
        matter["document_status"] = "Drafting"
        matter["updated_at"] = now_iso()
    workflow["client_approved"] = False
    workflow["attorney_approved"] = False
    workflow["drafts"] = {}
    workflow["stage"] = "draft_ready"; workflow["updated_at"] = now_iso(); save_data()
    return workflow


@app.post("/workflows/{workflow_id}/drafts")
def generate_workflow_drafts(workflow_id: str, authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"client"})
    workflow = workflows.get(workflow_id)
    if not workflow or workflow["client_user_id"] != user["id"]: raise HTTPException(404, "request not found")
    if workflow["conflict_status"] not in {"cleared", "demo_cleared"} or workflow["stage"] != "draft_ready": raise HTTPException(409, "Conflict review and completed intake are required")
    workflow["drafts"] = {name:{"status":"Review draft","content":"DRAFT FOR ATTORNEY REVIEW — NOT FOR SIGNING\n\n" + json.dumps({"document":name,"intake":workflow["intake"]},indent=2)} for name in workflow["documents_requested"]}
    workflow["stage"] = "client_review"; workflow["updated_at"] = now_iso(); save_data()
    return workflow


@app.patch("/workflows/{workflow_id}/client-review")
def client_review_workflow(workflow_id: str, req: WorkflowDecision, authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"client"})
    workflow = workflows.get(workflow_id)
    if not workflow or workflow["client_user_id"] != user["id"]: raise HTTPException(404, "request not found")
    if workflow["stage"] not in {"client_review", "draft_ready"}: raise HTTPException(409, "Drafts are not ready for review")
    if req.decision == "changes_requested":
        workflow["stage"] = "intake"
        workflow["client_approved"] = False
        workflow["drafts"] = {}
        workflow["client_review_note"] = req.note
        workflow["updated_at"] = now_iso(); save_data(); return workflow
    if req.decision not in {"changes_requested", "approved"}: raise HTTPException(400, "Choose approved or changes requested")
    workflow["client_review_note"] = req.note
    workflow["client_approved"] = req.decision == "approved"
    workflow["stage"] = "attorney_review" if workflow["client_approved"] else "draft_ready"
    workflow["updated_at"] = now_iso(); save_data(); return workflow


@app.post("/workflows/{workflow_id}/edit")
def edit_workflow(workflow_id: str, authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"client"})
    workflow = workflows.get(workflow_id)
    if not workflow or workflow["client_user_id"] != user["id"]: raise HTTPException(404, "request not found")
    if workflow["stage"] not in {"client_review", "attorney_review", "consultation", "signing", "complete", "draft_ready"}: raise HTTPException(409, "Request cannot be edited at this stage")
    workflow["stage"] = "intake"
    workflow["client_approved"] = False
    workflow["attorney_approved"] = False
    workflow["drafts"] = {}
    workflow["updated_at"] = now_iso()
    save_data()
    return workflow


@app.post("/workflows/{workflow_id}/cancel-appointment")
def cancel_workflow_appointment(workflow_id: str, req: WorkflowDecision, authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"client"})
    workflow = workflows.get(workflow_id)
    kind = req.note
    if not workflow or workflow["client_user_id"] != user["id"]: raise HTTPException(404, "request not found")
    if kind not in {"consultation", "signing"} or kind not in workflow.get("appointments", {}): raise HTTPException(404, "appointment not found")
    workflow["appointments"][kind]["status"] = "cancelled"
    for appointment in appointments.values():
        if appointment.get("workflow_id") == workflow_id and appointment.get("kind") == kind:
            appointment["status"] = "Cancelled"
            appointment["updated_at"] = now_iso()
    workflow["updated_at"] = now_iso()
    if workflow.get("demo_mode") and kind == "consultation": workflow["stage"] = "consultation"
    if workflow.get("demo_mode") and kind == "signing": workflow["stage"] = "signing"
    log_audit(user["email"], "cancel", "workflow_appointment", workflow_id, kind)
    save_data()
    return workflow


@app.post("/workflows/{workflow_id}/demo-attorney-review")
def demo_attorney_review(workflow_id: str, authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"client"})
    workflow = workflows.get(workflow_id)
    if not workflow or workflow["client_user_id"] != user["id"]: raise HTTPException(404, "request not found")
    if not workflow.get("demo_mode"): raise HTTPException(403, "Demo review is not enabled for this request")
    if workflow["stage"] != "attorney_review" or not workflow.get("client_approved"): raise HTTPException(409, "Client approval is required first")
    workflow["attorney_approved"] = True
    workflow["stage"] = "consultation"
    workflow["updated_at"] = now_iso()
    log_audit(user["email"], "demo_review", "workflow", workflow_id, "simulated attorney review; not a real legal review or approval")
    save_data()
    return workflow


@app.patch("/workflows/{workflow_id}/staff-review")
def staff_review_workflow(workflow_id: str, req: WorkflowDecision, authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"paralegal", "attorney", "admin"})
    workflow = workflows.get(workflow_id)
    if not workflow: raise HTTPException(404, "request not found")
    if req.decision == "conflict_cleared":
        if workflow["conflict_status"] != "pending": raise HTTPException(409, "Conflict review is not pending")
        workflow["conflict_status"] = "cleared"; workflow["conflict_reviewed_at"] = now_iso(); workflow["stage"] = "document_selection"
    elif req.decision == "conflict_flagged":
        workflow["conflict_status"] = "flagged"; workflow["stage"] = "conflict_hold"
    elif req.decision == "attorney_approved":
        if user["role"] not in {"attorney", "admin"}: raise HTTPException(403, "Attorney approval required")
        if workflow["stage"] != "attorney_review": raise HTTPException(409, "Client approval is required first")
        workflow["attorney_approved"] = True; workflow["stage"] = "consultation"
    elif req.decision == "attorney_changes":
        if user["role"] not in {"attorney", "admin"}: raise HTTPException(403, "Attorney review required")
        workflow["attorney_approved"] = False; workflow["stage"] = "draft_ready"
    elif req.decision == "consultation_completed":
        if user["role"] not in {"paralegal", "attorney", "admin"}: raise HTTPException(403, "Staff access required")
        if workflow["stage"] != "consultation" or workflow.get("appointments", {}).get("consultation", {}).get("status") != "scheduled": raise HTTPException(409, "Consultation must be approved first")
        workflow["appointments"]["consultation"]["status"] = "completed"
        workflow["stage"] = "complete" if workflow.get("appointments", {}).get("signing", {}).get("status") == "scheduled" else "signing"
    else: raise HTTPException(400, "Unsupported review decision")
    workflow["staff_review_note"] = req.note; workflow["updated_at"] = now_iso()
    matter = ensure_workflow_matter(workflow)
    matter_stage = {"conflict_review":"1 Intake", "conflict_hold":"1 Intake", "document_selection":"2 Attorney Scope", "intake":"3 Client Data Collection", "draft_ready":"4 Drafting", "client_review":"6 Client Review", "attorney_review":"5 Review Queue", "consultation":"7 Signing Preparation", "signing":"7 Signing Preparation", "complete":"10 Closed"}.get(workflow["stage"], matter.get("stage"))
    if matter_stage and matter.get("stage") != matter_stage:
        matter["stage"] = matter_stage; matter["updated_at"] = now_iso()
        stage_history.setdefault(matter["id"], []).append({"stage":matter_stage,"time":now_iso(),"by":user["email"]})
    log_audit(user["email"], "review", "workflow", workflow_id, req.decision); save_data(); return workflow


@app.patch("/workflows/{workflow_id}/appointment")
def schedule_workflow(workflow_id: str, req: WorkflowAppointment, authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization)
    workflow = workflows.get(workflow_id)
    if not workflow: raise HTTPException(404, "request not found")
    kind, at = req.kind, req.scheduled_at
    if kind not in {"consultation", "signing"} or not at: raise HTTPException(400, "Specify consultation/signing and a date/time")
    if kind == "consultation" and workflow["stage"] != "consultation": raise HTTPException(409, "Attorney approval must precede consultation")
    if kind == "signing" and workflow.get("appointments", {}).get("consultation", {}).get("status") not in {"requested", "scheduled", "completed"}: raise HTTPException(409, "Request a consultation before signing")
    if kind == "signing" and workflow["stage"] not in {"consultation", "signing"}: raise HTTPException(409, "Consultation review must be complete before signing")
    if user["role"] == "client":
        if workflow["client_user_id"] != user["id"]: raise HTTPException(404, "request not found")
        matter = ensure_workflow_matter(workflow)
        workflow["appointments"][kind] = {"requested_at":at,"status":"requested"}
        appointment = next((a for a in appointments.values() if a.get("workflow_id") == workflow_id and a.get("kind") == kind and a.get("status") != "Cancelled"), None)
        if not appointment:
            appointment = {"id":str(uuid.uuid4()),"matter_id":matter["id"],"kind":kind,"workflow_id":workflow_id,"created_at":now_iso()}
            appointments[appointment["id"]] = appointment
        appointment.update(scheduled_at=at,status="Requested",note=f"Client requested {kind} appointment")
        matter["appointment_status"] = "Requested"
        matter["updated_at"] = now_iso()
    elif user["role"] in {"paralegal", "attorney", "admin"}:
        matter = ensure_workflow_matter(workflow)
        workflow["appointments"][kind] = {"scheduled_at":at,"status":"scheduled"}
        appointment = next((a for a in appointments.values() if a.get("workflow_id") == workflow_id and a.get("kind") == kind and a.get("status") != "Cancelled"), None)
        if appointment:
            appointment.update(scheduled_at=at,status="Scheduled",note=f"{kind.title()} approved by staff",updated_at=now_iso())
        else:
            appointment = {"id":str(uuid.uuid4()),"matter_id":matter["id"],"kind":kind,"scheduled_at":at,"status":"Scheduled",
                "note":f"{kind.title()} approved by staff","workflow_id":workflow_id,"created_at":now_iso()}
            appointments[appointment["id"]] = appointment
        matter["appointment_status"] = "Scheduled"
        matter["updated_at"] = now_iso()
        if kind == "signing" and workflow.get("appointments", {}).get("consultation", {}).get("status") == "completed": workflow["stage"] = "complete"
    else: raise HTTPException(403, "Staff access required")
    workflow["updated_at"] = now_iso(); save_data(); return workflow


# tasks
@app.post("/tasks")
def create_task(t: Task, authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"paralegal","attorney","admin"})
    if t.matter_id not in matters: raise HTTPException(404,"matter not found")
    tid = str(uuid.uuid4())
    rec = t.model_dump(); rec["id"]=tid; rec["created_at"]=now_iso()
    tasks[tid]=rec; log_audit(user["email"],"create","task",tid,t.title); save_data(); return rec

@app.get("/tasks")
def list_tasks(matter_id: Optional[str]=None, status: Optional[str]=None, owner: Optional[str]=None, authorization: Optional[str]=Header(None)):
    u,_ = require_auth(authorization)
    if u["role"] == "client": raise HTTPException(403, "Tasks are staff-only")
    out = list(tasks.values())
    if matter_id: out=[t for t in out if t["matter_id"]==matter_id]
    if status: out=[t for t in out if t["status"]==status]
    if owner: out=[t for t in out if t["owner"]==owner]
    return out

@app.patch("/tasks/{task_id}")
def update_task(task_id: str, payload: Dict[str, Any] = Body(default={}),
                authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"paralegal","attorney","admin"})
    if task_id not in tasks: raise HTTPException(404,"task not found")
    for k in ("status","owner","due_date","blocker"):
        if k in payload and payload[k] is not None:
            tasks[task_id][k]=payload[k]
    tasks[task_id]["updated_at"]=now_iso(); log_audit(user["email"],"update","task",task_id,str(payload)); save_data()
    return tasks[task_id]

# comms
@app.post("/communications")
def create_comm(c: CommEntry, authorization: Optional[str]=Header(None)):
    user,_ = require_auth(authorization, {"paralegal","attorney","admin"})
    if c.matter_id not in matters: raise HTTPException(404,"matter not found")
    if c.visibility not in {"internal", "client"}: raise HTTPException(400, "invalid communication visibility")
    rec = c.model_dump(); rec["id"]=str(uuid.uuid4()); rec["created_at"]=now_iso()
    comms.append(rec); log_audit(user["email"],"create","communication",rec["id"],c.channel); save_data(); return rec

@app.get("/communications")
def list_comms(matter_id: Optional[str]=None, authorization: Optional[str]=Header(None)):
    u,_ = require_auth(authorization)
    out = list(comms) if u["role"] in ("paralegal","attorney","admin") else [c for c in comms if c.get("visibility") == "client" and matters.get(c["matter_id"],{}).get("client_user_id")==u["id"]]
    if matter_id: out=[c for c in out if c["matter_id"]==matter_id]
    return out

# auth
@app.post("/auth/signup")
def signup(req: SignupRequest):
    if len(req.password) < 6:
        raise HTTPException(400,"password must be at least 6 characters")
    req.email = req.email.strip().lower()
    if any(email.strip().lower() == req.email for email in users): raise HTTPException(400,"user already exists")
    if req.role not in ROLES: req.role="client"
    # clients always client role
    role = req.role if req.role in ("paralegal","attorney","admin") else "client"
    # only allow elevated via seed; public signup -> client
    role = "client"
    uid = str(uuid.uuid4())
    users[req.email] = {"id":uid,"name":req.name,"email":req.email,"role":role,
                        "password_hash":hash_pw(req.password),"created_at":now_iso()}
    token = str(uuid.uuid4())
    sessions[token] = {"user_id":uid,"expires":(datetime.datetime.utcnow()+datetime.timedelta(hours=24)).isoformat()}
    log_audit(req.email,"signup","user",uid)
    save_data()
    return {"token":token,"user":public_user(users[req.email])}

@app.post("/auth/initial-staff-setup")
def initial_staff_setup(req: SignupRequest, authorization: Optional[str]=Header(None)):
    expected = os.environ.get("INITIAL_STAFF_SETUP_TOKEN")
    supplied = authorization.replace("Bearer ", "").strip() if authorization else ""
    if not expected or not hmac.compare_digest(supplied, expected):
        raise HTTPException(404, "not found")
    if req.email.strip().lower() != "kmohr@prompt.law":
        raise HTTPException(400, "setup is restricted to the authorized email")
    if any(entry.get("action") == "initial_staff_setup" for entry in audit):
        raise HTTPException(404, "not found")
    if len(req.password) < 6:
        raise HTTPException(400, "password must be at least 6 characters")
    email = req.email.strip().lower()
    existing = next((user for stored, user in users.items() if stored.strip().lower() == email), None)
    if existing:
        raise HTTPException(409, "account already exists; use staff sign in")
    uid = str(uuid.uuid4())
    users[email] = {"id":uid,"name":req.name.strip(),"email":email,"role":"attorney",
                    "password_hash":hash_pw(req.password),"created_at":now_iso()}
    token = str(uuid.uuid4())
    sessions[token] = {"user_id":uid,"expires":(datetime.datetime.utcnow()+datetime.timedelta(hours=24)).isoformat()}
    log_audit(email,"initial_staff_setup","user",uid,"attorney account provisioned")
    save_data()
    os.environ.pop("INITIAL_STAFF_SETUP_TOKEN", None)
    return {"token":token,"user":public_user(users[email])}

@app.post("/auth/login")
def login(req: LoginRequest):
    email = req.email.strip().lower()
    u = users.get(email) or next((user for stored_email, user in users.items() if stored_email.strip().lower() == email), None)
    if not u or not verify_pw(req.password, u["password_hash"]):
        raise HTTPException(401,"invalid credentials")
    if not u["password_hash"].startswith("scrypt$"):
        u["password_hash"] = hash_pw(req.password)
    token = str(uuid.uuid4())
    sessions[token] = {"user_id":u["id"],"expires":(datetime.datetime.utcnow()+datetime.timedelta(hours=24)).isoformat()}
    save_data()
    return {"token":token,"user":public_user(u)}

@app.get("/auth/me")
def me(authorization: Optional[str]=Header(None)):
    u,_ = require_auth(authorization)
    return public_user(u)

@app.post("/auth/logout")
def logout(authorization: Optional[str]=Header(None)):
    if authorization:
        token = authorization.replace("Bearer ","").strip()
        sessions.pop(token,None); save_data()
    return {"ok":True}

# portal
@app.get("/my-matters")
def my_matters(authorization: Optional[str]=Header(None)):
    u,_ = require_auth(authorization)
    if u["role"] in ("paralegal","attorney","admin"):
        return list(matters.values())
    client_workflows = [w for w in workflows.values() if w["client_user_id"] == u["id"]]
    for workflow in client_workflows:
        ensure_workflow_matter(workflow)
    client_fields = {"id", "client_name", "stage", "document_status", "title_status", "funding_status", "appointment_status", "created_at", "updated_at"}
    return [{k:v for k,v in m.items() if k in client_fields} for m in matters.values() if m.get("client_user_id")==u["id"]]

# prompts/templates
@app.get("/prompts")
def list_prompts(authorization: Optional[str]=Header(None)):
    require_auth(authorization, {"paralegal","attorney","admin"})
    out=[]
    if os.path.isdir(PROMPT_ROOT):
        for root,_,files in os.walk(PROMPT_ROOT):
            for fn in files:
                if fn.endswith(".md"):
                    rel = os.path.relpath(os.path.join(root,fn), PROMPT_ROOT)
                    out.append({"name":rel,"path":os.path.join(root,fn)})
    return out

@app.get("/prompts/{name:path}")
def get_prompt(name: str, authorization: Optional[str]=Header(None)):
    require_auth(authorization, {"paralegal","attorney","admin"})
    path = os.path.realpath(os.path.join(PROMPT_ROOT, name))
    if not path.startswith(os.path.realpath(PROMPT_ROOT)+os.sep) or not os.path.isfile(path):
        raise HTTPException(404,"prompt not found")
    return {"name":name,"content":open(path).read()}

@app.get("/templates")
def list_templates(authorization: Optional[str]=Header(None)):
    require_auth(authorization, {"paralegal","attorney","admin"})
    out=[]
    if os.path.isdir(TEMPLATE_ROOT):
        for root,_,files in os.walk(TEMPLATE_ROOT):
            for fn in files:
                rel = os.path.relpath(os.path.join(root,fn), TEMPLATE_ROOT)
                out.append({"name":rel,"path":os.path.join(root,fn)})
    return out

@app.get("/templates/{name:path}")
def get_template(name: str, authorization: Optional[str]=Header(None)):
    require_auth(authorization, {"paralegal","attorney","admin"})
    path = os.path.realpath(os.path.join(TEMPLATE_ROOT, name))
    if not path.startswith(os.path.realpath(TEMPLATE_ROOT)+os.sep) or not os.path.isfile(path):
        raise HTTPException(404,"template not found")
    return {"name":name,"content":open(path).read()}

# reports
@app.get("/reports/friday")
def friday_report(authorization: Optional[str]=Header(None)):
    require_auth(authorization, {"paralegal","attorney","admin"})
    by_stage={}
    for m in matters.values():
        by_stage[m["stage"]]=by_stage.get(m["stage"],0)+1
    today = datetime.date.today().isoformat()
    overdue = [m["id"] for m in matters.values() if m.get("due_date") and m["due_date"]<today and m.get("stage")!="10 Closed"]
    by_owner={}
    for m in matters.values():
        by_owner[m.get("owner","Unassigned")]=by_owner.get(m.get("owner","Unassigned"),0)+1
    by_risk={}
    for m in matters.values():
        by_risk[m.get("risk_level","Low")]=by_risk.get(m.get("risk_level","Low"),0)+1
    return {
        "total": len(matters), "by_stage": by_stage, "by_owner": by_owner, "by_risk": by_risk,
        "high_risk": [m["id"] for m in matters.values() if m.get("risk_level")=="High"],
        "urgent": [m["id"] for m in matters.values() if m.get("priority")=="Urgent"],
        "attorney_review_queue": [m["id"] for m in matters.values() if "Review" in m.get("stage","")],
        "overdue": overdue,
        "overdue_count": len(overdue),
        "open_change_requests": len([c for c in changes if c.get("status")=="Open"]),
        "open_tasks": len([t for t in tasks.values() if t.get("status")=="Open"]),
        "appointments_pending": len([a for a in appointments.values() if a.get("status") in ("Booked","Rescheduled","Requested")]),
    }

@app.get("/reports/capacity")
def capacity_report(authorization: Optional[str]=Header(None)):
    require_auth(authorization, {"paralegal","attorney","admin"})
    by_owner={}
    for m in matters.values():
        o = m.get("owner","Unassigned")
        by_owner.setdefault(o,{"matters":0,"high_risk":0,"urgent":0,"overdue":0})
        by_owner[o]["matters"]+=1
        if m.get("risk_level")=="High": by_owner[o]["high_risk"]+=1
        if m.get("priority")=="Urgent": by_owner[o]["urgent"]+=1
        today=datetime.date.today().isoformat()
        if m.get("due_date") and m["due_date"]<today and m.get("stage")!="10 Closed":
            by_owner[o]["overdue"]+=1
    return {"by_owner":by_owner,"total_owners":len(by_owner)}

@app.get("/reports/bottlenecks")
def bottlenecks(authorization: Optional[str]=Header(None)):
    require_auth(authorization, {"paralegal","attorney","admin"})
    # stage counts and avg age
    counts={}
    for m in matters.values():
        counts[m.get("stage")]=counts.get(m.get("stage"),0)+1
    top = sorted(counts.items(), key=lambda x:-x[1])[:5]
    open_cr = [c for c in changes if c.get("status")=="Open"]
    return {"top_stages":top,"open_change_requests":len(open_cr),
            "waiting_on_client":len([m for m in matters.values() if "Client" in m.get("stage","")]),
            "blocked_matters":len([m for m in matters.values() if m.get("blocker","None")!="None"])}

@app.get("/audit")
def get_audit(limit: int=100, entity: Optional[str]=None, authorization: Optional[str]=Header(None)):
    require_auth(authorization, {"paralegal","attorney","admin"})
    out = list(audit)
    if entity: out=[a for a in out if a["entity"]==entity]
    return out[-limit:]

@app.get("/export/matters.csv")
def export_csv(authorization: Optional[str]=Header(None)):
    require_auth(authorization, {"paralegal","attorney","admin"})
    buf = io.StringIO()
    fields = ["id","client_name","stage","owner","attorney_reviewer","due_date","risk_level","priority","next_action","blocker","document_status","title_status","funding_status","appointment_status"]
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for m in matters.values():
        w.writerow(m)
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                            headers={"Content-Disposition":"attachment; filename=matters.csv"})

@app.post("/admin/test-email")
def test_email(to: str, authorization: Optional[str]=Header(None)):
    u,_ = require_auth(authorization, {"admin"})
    ok = send_signup_email(to, "Test User")
    return {"sent": ok, "to": to}
# admin helpers
@app.post("/matters/{matter_id}/stage")
def set_stage(matter_id: str, stage: str, authorization: Optional[str]=Header(None)):
    if matter_id not in matters: raise HTTPException(404,"matter not found")
    if stage not in STAGES: raise HTTPException(400,"invalid stage")
    u,_ = require_auth(authorization, {"paralegal","attorney","admin"})
    old = matters[matter_id].get("stage")
    matters[matter_id]["stage"]=stage; matters[matter_id]["updated_at"]=now_iso()
    stage_history.setdefault(matter_id,[]).append({"stage":stage,"time":now_iso(),"by":u["email"]})
    log_audit(u["email"],"stage_change","matter",matter_id,f"{old}->{stage}")
    save_data()
    return matters[matter_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
