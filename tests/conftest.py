import os
import sys

sys.path.insert(0, "backend")

def pytest_runtest_setup(item):
    try:
        import db
        db.execute("DELETE FROM conflict_names")
    except Exception:
        pass
