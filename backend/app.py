from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import os, uuid

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
