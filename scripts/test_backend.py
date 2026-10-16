
from fastapi.testclient import TestClient
import sys; sys.path.insert(0, "backend")
from app import app
c=TestClient(app)
assert c.get("/health").status_code==200
c.post("/matters",json={"id":"CL-001","client_name":"Test","stage":"Intake","owner":"P","risk_level":"High"})
assert c.get("/matters/CL-001").status_code==200
r=c.get("/reports/friday")
assert r.status_code==200
print("backend tests passed")
