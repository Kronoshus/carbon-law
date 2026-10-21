import os, json, uuid, hashlib, hmac, datetime, smtplib, csv, io
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

def now_iso():
    return datetime.datetime.utcnow().isoformat()

def load_data():
    global matters, changes, appointments, documents, users, sessions, contacts, tasks, audit, comms, stage_history
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
    return matter if u["role"] in ("paralegal","attorney","admin") else {k:v for k,v in matter.items() if k not in {"notes", "client_email", "client_user_id"}}

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
            {"stage":updates["stage"],"time":now_iso(),"by": (u["email"] if u else "system")})
    log_audit((u["email"] if u else "system"),"update","matter",matter_id,str(updates))
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
    changes.append(rec)
    # auto-create revision task
    tid = str(uuid.uuid4())
    tasks[tid] = {"id":tid,"matter_id":cr.matter_id,"title":f"Review change: {cr.change_type}",
                  "owner":matters[cr.matter_id].get("owner","Unassigned"),"due_date":None,
                  "status":"Open","blocker":"None","created_at":now_iso()}
    log_audit("client" if not authorization else "user","create","change_request",rec["id"],cr.change_type)
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
def update_change_request(request_id: str, status: Optional[str]=None, note: Optional[str]=None,
                         resolution: Optional[str]=None, authorization: Optional[str]=Header(None)):
    require_auth(authorization, {"paralegal","attorney","admin"})
    for cr in changes:
        if cr["id"]==request_id:
            if status: cr["status"]=status
            if note: cr["note"]=note
            if resolution: cr["resolution"]=resolution
            cr["updated_at"]=now_iso()
            log_audit("user","update","change_request",request_id,status or "")
            save_data()
            return cr
    raise HTTPException(404,"change request not found")

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
    require_auth(authorization, {"paralegal","attorney","admin"})
    if appointment_id not in appointments: raise HTTPException(404,"appointment not found")
    if status: appointments[appointment_id]["status"]=status
    if note: appointments[appointment_id]["note"]=note
    if scheduled_at: appointments[appointment_id]["scheduled_at"]=scheduled_at
    appointments[appointment_id]["updated_at"]=now_iso()
    mid = appointments[appointment_id]["matter_id"]
    if mid in matters and status:
        matters[mid]["appointment_status"]=status; matters[mid]["updated_at"]=now_iso()
    log_audit("user","update","appointment",appointment_id,status or "")
    save_data()
    return appointments[appointment_id]

# documents
@app.post("/documents")
def create_document(doc: PortalDocument, authorization: Optional[str]=Header(None)):
    require_auth(authorization, {"paralegal","attorney","admin"})
    if doc.matter_id not in matters: raise HTTPException(404,"matter not found")
    # auto-version: if same name exists, increment
    existing = [d for d in documents.values() if d["matter_id"]==doc.matter_id and d["name"]==doc.name]
    if existing:
        doc.version = max(d["version"] for d in existing)+1
    rec = doc.model_dump(); rec["id"]=str(uuid.uuid4()); rec["created_at"]=now_iso()
    documents[rec["id"]]=rec
    log_audit("user","create","document",rec["id"],doc.name)
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
    require_auth(authorization, {"paralegal","attorney","admin"})
    if doc_id not in documents: raise HTTPException(404,"document not found")
    if status: documents[doc_id]["status"]=status
    if version: documents[doc_id]["version"]=version
    documents[doc_id]["updated_at"]=now_iso()
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
            if "status" in payload and payload["status"] is not None:
                c["status"]=payload["status"]
            if "note" in payload and payload["note"] is not None:
                c["note"]=payload["note"]
            c["updated_at"]=now_iso(); save_data(); return c
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

# tasks
@app.post("/tasks")
def create_task(t: Task, authorization: Optional[str]=Header(None)):
    require_auth(authorization, {"paralegal","attorney","admin"})
    if t.matter_id not in matters: raise HTTPException(404,"matter not found")
    tid = str(uuid.uuid4())
    rec = t.model_dump(); rec["id"]=tid; rec["created_at"]=now_iso()
    tasks[tid]=rec; save_data(); return rec

@app.get("/tasks")
def list_tasks(matter_id: Optional[str]=None, status: Optional[str]=None, owner: Optional[str]=None, authorization: Optional[str]=Header(None)):
    u,_ = require_auth(authorization)
    out = list(tasks.values()) if u["role"] in ("paralegal","attorney","admin") else [t for t in tasks.values() if matters.get(t["matter_id"],{}).get("client_user_id")==u["id"]]
    if matter_id: out=[t for t in out if t["matter_id"]==matter_id]
    if status: out=[t for t in out if t["status"]==status]
    if owner: out=[t for t in out if t["owner"]==owner]
    return out

@app.patch("/tasks/{task_id}")
def update_task(task_id: str, payload: Dict[str, Any] = Body(default={}),
                authorization: Optional[str]=Header(None)):
    require_auth(authorization, {"paralegal","attorney","admin"})
    if task_id not in tasks: raise HTTPException(404,"task not found")
    for k in ("status","owner","due_date","blocker"):
        if k in payload and payload[k] is not None:
            tasks[task_id][k]=payload[k]
    tasks[task_id]["updated_at"]=now_iso(); save_data()
    return tasks[task_id]

# comms
@app.post("/communications")
def create_comm(c: CommEntry, authorization: Optional[str]=Header(None)):
    require_auth(authorization, {"paralegal","attorney","admin"})
    if c.matter_id not in matters: raise HTTPException(404,"matter not found")
    rec = c.model_dump(); rec["id"]=str(uuid.uuid4()); rec["created_at"]=now_iso()
    comms.append(rec); save_data(); return rec

@app.get("/communications")
def list_comms(matter_id: Optional[str]=None, authorization: Optional[str]=Header(None)):
    u,_ = require_auth(authorization)
    out = list(comms) if u["role"] in ("paralegal","attorney","admin") else [c for c in comms if matters.get(c["matter_id"],{}).get("client_user_id")==u["id"]]
    if matter_id: out=[c for c in out if c["matter_id"]==matter_id]
    return out

# auth
@app.post("/auth/signup")
def signup(req: SignupRequest):
    if len(req.password) < 12:
        raise HTTPException(400,"password must be at least 12 characters")
    if req.email in users: raise HTTPException(400,"user already exists")
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
    return {"token":token,"user":{k:v for k,v in users[req.email].items() if k != "password_hash"}}

@app.post("/auth/login")
def login(req: LoginRequest):
    u = users.get(req.email)
    if not u or not verify_pw(req.password, u["password_hash"]):
        raise HTTPException(401,"invalid credentials")
    if not u["password_hash"].startswith("scrypt$"):
        u["password_hash"] = hash_pw(req.password)
    token = str(uuid.uuid4())
    sessions[token] = {"user_id":u["id"],"expires":(datetime.datetime.utcnow()+datetime.timedelta(hours=24)).isoformat()}
    save_data()
    return {"token":token,"user":{k:v for k,v in u.items() if k != "password_hash"}}

@app.get("/auth/me")
def me(authorization: Optional[str]=Header(None)):
    u,_ = require_auth(authorization)
    return {k:v for k,v in u.items() if k != "password_hash"}

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
    return [{k:v for k,v in m.items() if k not in {"notes", "client_email", "client_user_id"}} for m in matters.values() if m.get("client_user_id")==u["id"]]

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
        "appointments_pending": len([a for a in appointments.values() if a.get("status") in ("Booked","Rescheduled")]),
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
