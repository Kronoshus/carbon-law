"""Signing, downloads, and funding follow-up (T6-08)."""
import os
import secrets

import app as backend_app
import db
from aprende import jobs, journey, legacy
from aprende.notify import notify_staff


def send_email(to, subject, body):
    return backend_app.send_email(to, subject, body)


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE_PATH = os.path.join(ROOT, "templates", "california", "funding-checklist.md")


def _user_email(user_id):
    for u in backend_app.users.values():
        if u.get("id") == user_id:
            return u.get("email")
    return None


def store_executed(jid, documents, uploaded_by):
    ids = []
    for d in documents or []:
        eid = secrets.token_urlsafe(32)
        db.execute(
            "INSERT INTO executed_documents (id, journey_id, name, filename, content_b64, uploaded_by, uploaded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (eid, jid, d["name"], d["filename"], d["content_b64"], uploaded_by, journey._now_iso()),
        )
        ids.append(eid)
    return ids


def list_for_journey(jid):
    rows = db.query("SELECT id, name, filename FROM executed_documents WHERE journey_id = ? ORDER BY uploaded_at", (jid,))
    return [{"id": r[0], "name": r[1], "filename": r[2], "url": f"/signed-documents/{r[0]}"} for r in rows]


def get_document(did):
    rows = db.query("SELECT id, journey_id, name, filename, content_b64 FROM executed_documents WHERE id = ?", (did,))
    if not rows:
        return None
    return dict(zip(("id", "journey_id", "name", "filename", "content_b64"), rows[0]))


CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".txt": "text/plain",
}


def content_type(filename):
    ext = os.path.splitext(filename or "")[1].lower()
    return CONTENT_TYPES.get(ext, "application/octet-stream")


def funding_checklist_text(j):
    if "signed" not in (j.get("facts") or {}):
        raise ValueError("not_signed")
    confirmed = list((j.get("documents") or {}).get("confirmed") or [])
    if "trust" not in confirmed:
        raise LookupError("no_trust")
    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        text = f.read()
    text = text.replace("{{matter_id}}", str(j.get("matter_id") or ""))
    client_name = legacy._user_name(j["user_id"]) or ""
    text = text.replace("{{client}}", client_name)
    rows = db.query("SELECT answer FROM datos_answers WHERE journey_id = ? AND question_id = ?", (j["id"], "fid_bienes"))
    answer = rows[0][0] if rows and rows[0][0] is not None else ""
    text += "\n\n## Bienes que usted nombró / Property you named\n\n" + str(answer) + "\n"
    return text


def funding_checkin_handler(job):
    jid = job["payload"]["journey_id"]
    j = journey.get_journey(jid)
    if "funding_done" in j["facts"]:
        return
    email = _user_email(j["user_id"])
    matter_id = j.get("matter_id")
    body = ("Recordatorio amable: termine de pasar sus bienes al fideicomiso. "
            "Revise la lista de fondeo para ver lo que falta.\n\n"
            "Gentle reminder: please finish moving your property into the trust. "
            "Check the funding checklist for what is left.\n")
    if email:
        send_email(email, "Funding reminder / Recordatorio de fondeo", body)
    notify_staff("Funding check-in", f"Journey {jid} (matter {matter_id}) still needs funding.")


jobs.register("funding_checkin", funding_checkin_handler)
