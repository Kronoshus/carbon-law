#!/usr/bin/env python
"""Dev-only, read-only (T8-06): what the e2e backend's database holds for one journey, as JSON row counts.
Usage: CARBON_DB_PATH=/tmp/cl-e2e-<port>.db python scripts/e2e-db.py <journey_id>
Every table with a journey_id column is counted, plus the legacy matters and documents of the journey's client."""
import json
import os
import sqlite3
import sys

jid = sys.argv[1]
con = sqlite3.connect(f"file:{os.environ['CARBON_DB_PATH']}?mode=ro", uri=True)
tables = [t for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
out = {t: con.execute(f"SELECT COUNT(*) FROM {t} WHERE journey_id = ?", (jid,)).fetchone()[0]
       for t in tables if any(c[1] == "journey_id" for c in con.execute(f"PRAGMA table_info({t})"))}
user = con.execute("SELECT user_id FROM journeys WHERE id = ?", (jid,)).fetchone()
out["events"] = sorted({t for (t,) in con.execute("SELECT type FROM journey_events WHERE journey_id = ?", (jid,))})
legacy = {n: json.loads(d) for n, d in con.execute("SELECT name, data FROM collections WHERE name IN ('matters', 'documents')")}
out["legacy_matters"] = sum(1 for m in legacy.get("matters", {}).values() if user and m.get("client_user_id") == user[0])
out["legacy_documents"] = sum(1 for d in legacy.get("documents", {}).values() if d.get("journey_id") == jid)
print(json.dumps(out, sort_keys=True))
