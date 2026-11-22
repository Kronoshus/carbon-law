"""The worker process can run every job the app queues. Found by the T8-06 release test: after a payment, the
draft_documents job failed three times with "no handler registered", so no draft was ever written. (Opus)"""
import glob
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUED = {k for p in glob.glob(os.path.join(ROOT, "backend", "**", "*.py"), recursive=True)          # every kind the app enqueues
          for k in re.findall(r'jobs\.enqueue\(\s*"([a-z_]+)"', open(p, encoding="utf-8").read())}


def test_the_worker_process_registers_a_handler_for_every_job_the_app_queues(tmp_path):
    """As `python backend/worker.py` runs it: its own process, which never imports app.py's routers."""
    code = ("import threading, time, worker, aprende.jobs as jobs\n"
            "stop = threading.Event()\n"
            "t = threading.Thread(target=worker.run_forever, args=(stop,), daemon=True); t.start()\n"
            "time.sleep(3); stop.set(); t.join(10)\n"
            "print(','.join(sorted(jobs.HANDLERS)))\n")
    env = {**os.environ, "CARBON_DB_PATH": str(tmp_path / "worker.db"), "DATABASE_URL": ""}
    r = subprocess.run([sys.executable, "-c", code], cwd=os.path.join(ROOT, "backend"), env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0 and "Traceback" not in r.stderr, r.stderr                  # the worker starts
    handlers = set(r.stdout.strip().split(","))
    assert QUEUED <= handlers, f"no handler for {sorted(QUEUED - handlers)}"
