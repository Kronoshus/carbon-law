from fastapi.testclient import TestClient
import sys
sys.path.insert(0, "backend")
from app import app

c = TestClient(app)
assert c.get("/health").status_code == 200
assert c.get("/matters/CL-001").status_code == 401
assert c.get("/reports/friday").status_code == 401
print("backend auth checks passed")
