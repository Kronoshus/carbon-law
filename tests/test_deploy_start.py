"""The app must start the way Render starts it (`uvicorn backend.app:app` from the repo root, see render.yaml), not only the
way the other tests import it. Runs in a subprocess with a fresh database."""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CODE = """
import importlib, sys
m = importlib.import_module("backend.app")
assert sys.modules["app"] is m, "app.py was loaded twice"
from fastapi.testclient import TestClient
c = TestClient(m.app)
assert c.get("/health").status_code == 200
t = c.post("/auth/signup", json={"name": "Ana Torres", "email": "deploy-check@example.com", "password": "long-secure-password",
                                 "source": "aprende", "adult": True}).json()["token"]
r = c.get("/journey", headers={"Authorization": "Bearer " + t})
assert r.status_code == 200, r.text
print("ok")
"""


def test_app_starts_as_render_starts_it():
    env = {**os.environ, "DATABASE_URL": "", "CARBON_DB_PATH": tempfile.mktemp(suffix=".db")}
    r = subprocess.run([sys.executable, "-c", CODE], cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip().endswith("ok"), r.stderr[-3000:]
