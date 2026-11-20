
"""T2-07 acceptance tests."""
import asyncio
import os
import sys
import tempfile
import threading
import time
import uuid

import pytest

os.environ.setdefault("DATABASE_URL", "")
os.environ.setdefault("CARBON_DB_PATH", tempfile.mktemp(suffix=".db"))
sys.path.insert(0, "backend")

import migrate
migrate.run()

import app as backend
import db
from aprende import journey, legacy

STAFF_EMAIL = "lock-staff@example.com"
backend.users[STAFF_EMAIL] = {"id": str(uuid.uuid4()), "name": "Lock Staff", "email": STAFF_EMAIL, "role": "paralegal",
                              "password_hash": backend.hash_pw("lock-staff-password"),
                              "created_at": __import__("datetime").datetime.utcnow().isoformat()}


def staff_token():
    c = __import__("httpx").AsyncClient  # placeholder
    return None


@pytest.fixture(autouse=True)
def slow_route():
    """A test-only slow Aprende route, removed afterwards so the T7-07 route matrix never sees it."""
    async def _slow():
        await asyncio.sleep(2)
        return {"ok": True}
    backend.app.add_api_route("/journey/__slow", _slow)
    yield
    backend.app.router.routes[:] = [r for r in backend.app.router.routes if getattr(r, "path", None) != "/journey/__slow"]


def test_slow_aprende_request_does_not_block_legacy():
    import httpx
    from httpx import ASGITransport

    async def main():
        transport = ASGITransport(app=backend.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            r = await client.post("/auth/login", json={"email": STAFF_EMAIL, "password": "lock-staff-password"})
            assert r.status_code == 200, r.text
            token = r.json()["token"]
            headers = {"Authorization": "Bearer " + token}

            slow_task = asyncio.create_task(client.get("/journey/__slow"))
            await asyncio.sleep(0.2)
            t0 = time.monotonic()
            r2 = await client.get("/matters", headers=headers)
            elapsed = time.monotonic() - t0
            assert r2.status_code == 200, r2.text
            assert elapsed < 0.5, elapsed
            await slow_task
            assert slow_task.result().status_code == 200

    asyncio.run(main())


def test_concurrent_ensure_matter_one_matter():
    user_id = str(uuid.uuid4())
    j = journey.get_or_create_for_user(user_id)
    jid = j["id"]

    results = []
    lock = threading.Lock()

    def worker():
        mid = legacy.ensure_matter({"id": jid})
        with lock:
            results.append(mid)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert len(results) == 2
    assert results[0] == results[1]
    matching = [m for m in backend.matters.values() if m.get("client_user_id") == user_id]
    assert len(matching) == 1


def test_legacy_lock_blocks_ensure_matter():
    user_id = str(uuid.uuid4())
    j = journey.get_or_create_for_user(user_id)
    jid = j["id"]

    acquired = threading.Event()
    released = threading.Event()
    done = threading.Event()
    result = {}

    def holder():
        with backend._request_lock:
            acquired.set()
            released.wait(timeout=5)
        # lock released

    def worker():
        mid = legacy.ensure_matter({"id": jid})
        result["mid"] = mid
        done.set()

    t1 = threading.Thread(target=holder)
    t1.start()
    assert acquired.wait(timeout=5)
    t2 = threading.Thread(target=worker)
    t2.start()
    # worker should not finish while lock held
    assert not done.wait(timeout=0.3)
    released.set()
    t2.join(timeout=5)
    t1.join(timeout=5)
    assert done.is_set()
    assert result.get("mid")



def test_cancelled_waiter_does_not_leave_the_lock_held():
    import asyncio
    import app as backend_app
    from starlette.requests import Request

    async def scenario():
        backend_app._request_lock.acquire()                     # a legacy request is running
        scope = {"type": "http", "method": "GET", "path": "/matters", "headers": [], "query_string": b""}

        async def call_next(request):
            raise AssertionError("must not run")
        waiter = asyncio.ensure_future(backend_app.serialize_requests(Request(scope), call_next))
        await asyncio.sleep(0.05)
        waiter.cancel()                                         # the client went away while waiting
        await asyncio.gather(waiter, return_exceptions=True)
        backend_app._request_lock.release()
        await asyncio.sleep(0.05)
        assert backend_app._request_lock.acquire(blocking=False), "lock leaked to a cancelled waiter"
        backend_app._request_lock.release()
    asyncio.run(scenario())
