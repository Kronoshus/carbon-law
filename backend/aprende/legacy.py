"""Legacy bridge: create/update matters in the legacy portal from an Aprende journey."""
import os, sys, json, uuid, threading

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

import app as backend_app

_lock = threading.Lock()


def _user_name(user_id):
    for u in backend_app.users.values():
        if u.get("id") == user_id:
            return u.get("name") or u.get("email")
    return None


def ensure_matter(journey):
    """Create exactly one legacy matter for this journey, at stage '1 Intake'. Idempotent."""
    j = journey
    if hasattr(j, "id"):
        j = {"id": j.id, "user_id": getattr(j, "user_id", None), "matter_id": getattr(j, "matter_id", None)}
    jid = j["id"]
    with _lock:
        # reload journey to get latest matter_id
        from aprende import journey as J
        jj = J.get_journey(jid)
        if jj and jj.get("matter_id"):
            mid = jj["matter_id"]
            if mid in backend_app.matters:
                return mid
        user_id = jj["user_id"] if jj else j.get("user_id")
        client_name = _user_name(user_id) or "Client"
        matter_id = "CL-" + str(jid).replace("-", "")[:8].upper()
        if matter_id in backend_app.matters:
            matter_id = "CL-" + uuid.uuid4().hex[:8].upper()
        now = backend_app.now_iso()
        matter = {
            "id": matter_id,
            "client_name": client_name,
            "client_user_id": user_id,
            "stage": "1 Intake",
            "owner": "Unassigned",
            "risk_level": "Low",
            "priority": "Normal",
            "created_at": now,
            "updated_at": now,
        }
        backend_app.matters[matter_id] = matter
        backend_app.stage_history[matter_id] = [{"stage": "1 Intake", "time": now, "by": "system"}]
        try:
            backend_app.save_data()
        except Exception:
            pass
        # persist matter_id on journey
        try:
            import db
            db.execute("UPDATE journeys SET matter_id = ? WHERE id = ?", (matter_id, jid))
        except Exception:
            pass
        return matter_id


def set_stage(journey, stage):
    j = journey
    if hasattr(j, "id"):
        j = {"id": j.id, "matter_id": getattr(j, "matter_id", None)}
    from aprende import journey as J
    jj = J.get_journey(j["id"])
    mid = (jj or {}).get("matter_id") or j.get("matter_id")
    if not mid or mid not in backend_app.matters:
        return None
    with _lock:
        if stage not in backend_app.STAGES:
            raise ValueError("invalid stage")
        old = backend_app.matters[mid].get("stage")
        backend_app.matters[mid]["stage"] = stage
        backend_app.matters[mid]["updated_at"] = backend_app.now_iso()
        backend_app.stage_history.setdefault(mid, []).append(
            {"stage": stage, "time": backend_app.now_iso(), "by": "system"}
        )
        try:
            backend_app.save_data()
        except Exception:
            pass
        return backend_app.matters[mid]
