from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import os, uuid

app = FastAPI(title="Carbon Law Backend", version="0.1.0")

class Matter(BaseModel):
    id: str
    client_name: str
    stage: str
    owner: str
    attorney_reviewer: Optional[str] = None
    due_date: Optional[str] = None
    next_action: str = ""
    blocker: str = "None"
    risk_level: str = "Low"
    appointment_status: Optional[str] = None
    document_status: Optional[str] = None

class ChangeRequest(BaseModel):
    matter_id: str
    requested_by: str
    change_type: str
    affected_documents: str = ""
    required_attorney_decision: bool = True
    impact: str = ""

class AppointmentAction(BaseModel):
    status: str = Field(..., pattern="^(Booked|Completed|Cancelled|Rescheduled)$")
    note: str = ""

matters: Dict[str, Dict[str, Any]] = {}
changes: List[Dict[str, Any]] = []
appointments: Dict[str, Dict[str, Any]] = {}

@app.get("/health")
def health():
    return {"status": "ok", "service": "carbon-law", "time": datetime.utcnow().isoformat()}

@app.get("/matters")
def list_matters():
    return list(matters.values())

@app.post("/matters")
def upsert_matter(m: Matter):
    data = m.model_dump()
    data["updated_at"] = datetime.utcnow().isoformat()
    if m.id not in matters:
        data["created_at"] = data["updated_at"]
    matters[m.id] = data
    return data

@app.get("/matters/{matter_id}")
def get_matter(matter_id: str):
    if matter_id not in matters:
        raise HTTPException(404, "matter not found")
    return matters[matter_id]

@app.get("/reports/friday")
def friday_report():
    by_stage = {}
    for m in matters.values():
        by_stage[m["stage"]] = by_stage.get(m["stage"], 0) + 1
    return {
        "total": len(matters),
        "by_stage": by_stage,
        "high_risk": [m["id"] for m in matters.values() if m.get("risk_level") == "High"],
        "overdue": [m["id"] for m in matters.values() if m.get("priority") == "Urgent"],
    }

@app.post("/change-requests")
def create_change_request(cr: ChangeRequest):
    rec = cr.model_dump()
    rec["id"] = str(uuid.uuid4())
    rec["status"] = "Open"
    rec["created_at"] = datetime.utcnow().isoformat()
    changes.append(rec)
    return rec

@app.get("/change-requests")
def list_change_requests():
    return changes

@app.post("/appointments/{appointment_id}/status")
def appointment_status(appointment_id: str, action: AppointmentAction):
    if appointment_id not in appointments:
        appointments[appointment_id] = {"id": appointment_id, "status": "Booked"}
    appointments[appointment_id]["status"] = action.status
    appointments[appointment_id]["reschedule_note"] = action.note
    return appointments[appointment_id]
