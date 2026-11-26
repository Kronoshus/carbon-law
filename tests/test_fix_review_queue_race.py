import os, sys, tempfile, threading, time, uuid
os.environ.setdefault("DATABASE_URL", "")
os.environ.setdefault("CARBON_DB_PATH", tempfile.mktemp(suffix=".db"))
sys.path.insert(0, "backend")

import app as backend_app
import migrate
migrate.run()

from aprende import review


def test_review_queue_survives_concurrent_document_writes():
    jid = "race-journey"
    stop = threading.Event()
    errors = []
    N = 50

    def writer():
        i = 0
        while not stop.is_set():
            key = f"doc-{i % N}"
            backend_app.documents[key] = {
                "id": key, "journey_id": jid, "status": "Attorney Review",
                "attorney_only": True, "name": "Will", "version": 1,
            }
            if i % 3 == 0:
                backend_app.documents.pop(f"doc-{(i - 3) % N}", None)
            i += 1
            time.sleep(0)  # yield

    t = threading.Thread(target=writer, daemon=True)
    t.start()
    deadline = time.time() + 3
    try:
        n = 0
        while time.time() < deadline:
            try:
                review._current_drafts(jid)
                review._change_requested(jid)
            except RuntimeError as e:
                errors.append(str(e))
                break
            n += 1
    finally:
        stop.set()
        t.join(timeout=5)
        for i in range(N):
            backend_app.documents.pop(f"doc-{i}", None)
    assert not errors, errors[:1]
