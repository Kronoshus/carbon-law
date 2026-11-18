"""Legacy bridge: create/update matters in the legacy portal from an Aprende journey."""
import asyncio
import threading
import uuid

import app as backend_app
import db
from aprende import journey as J


def _user_name(user_id):
    for u in backend_app.users.values():
        if u.get("id") == user_id:
            return u.get("name") or u.get("email")
    return None


def ensure_matter(journey):
    j = journey
    jid = j["id"]
    with backend_app._request_lock:
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
        backend_app.save_data()
        db.execute("UPDATE journeys SET matter_id = ? WHERE id = ?", (matter_id, jid))
        return matter_id


def set_stage(journey, stage):
    j = journey
    jj = J.get_journey(j["id"])
    mid = (jj or {}).get("matter_id") or j.get("matter_id")
    if not mid or mid not in backend_app.matters:
        return None
    with backend_app._request_lock:
        if stage not in backend_app.STAGES:
            raise ValueError("invalid stage")
        old = backend_app.matters[mid].get("stage")
        backend_app.matters[mid]["stage"] = stage
        backend_app.matters[mid]["updated_at"] = backend_app.now_iso()
        backend_app.stage_history.setdefault(mid, []).append(
            {"stage": stage, "time": backend_app.now_iso(), "by": "system"}
        )
        backend_app.save_data()
        return backend_app.matters[mid]


class _LegacyLock:
    """Dual-mode context manager over the shared legacy threading lock.

    Works both as ``with legacy.legacy_lock():`` (sync, e.g. inside worker threads) and
    ``async with legacy.legacy_lock():`` (async, without blocking the event loop).
    """

    def __enter__(self):
        backend_app._request_lock.acquire()
        return self

    def __exit__(self, *exc):
        backend_app._request_lock.release()
        return False

    async def __aenter__(self):
        await asyncio.to_thread(backend_app._request_lock.acquire)
        return self

    async def __aexit__(self, *exc):
        backend_app._request_lock.release()
        return False


def legacy_lock():
    return _LegacyLock()
