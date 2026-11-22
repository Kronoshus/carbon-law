#!/usr/bin/env python
"""Dev-only: seed the e2e backend with published lesson content. Used only by start-e2e-backend.sh."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

import app  # noqa: F401  (ensures repo root on path)
from aprende import content, conflicts

BUNDLE_DIR = os.path.join(ROOT, "aprende", "content")
bundle = content.load_dir(BUNDLE_DIR)
content.import_bundle(bundle, actor="e2e-seed")
for lesson in bundle["lessons"]:
    for step in lesson.get("steps", []):
        for it in step.get("items", []):
            if it.get("legal"):
                content.approve(it["id"], attorney="attorney@example.com")
            content.publish(it["id"], actor="paralegal@example.com")
conflicts.replace_list("name\nRoberto Méndez\n")
print("seeded e2e content")

# Seed attorney account for e2e engagement flow.
import uuid, datetime
from aprende import engagement
att_email = "attorney-e2e@example.com"
att_password = "attorney-e2e-password"
if att_email not in app.users:
    uid = str(uuid.uuid4())
    app.users[att_email] = {"id": uid, "name": "Pankaj Raval", "email": att_email, "role": "attorney",
                           "password_hash": app.hash_pw(att_password), "created_at": datetime.datetime.utcnow().isoformat()}
# Seed a paralegal for the release test's staff steps (T8-06).
par_email, par_password = "paralegal-e2e@example.com", "paralegal-e2e-password"
if par_email not in app.users:
    app.users[par_email] = {"id": str(uuid.uuid4()), "name": "Lucía Paralegal", "email": par_email, "role": "paralegal",
                            "password_hash": app.hash_pw(par_password), "created_at": datetime.datetime.utcnow().isoformat()}
# Approved engagement template.
es = open(os.path.join(ROOT, "aprende", "content", "engagement", "es.md"), encoding="utf-8").read()
en = open(os.path.join(ROOT, "aprende", "content", "engagement", "en.md"), encoding="utf-8").read()
t = engagement.create_template(es, en, "seed")
engagement.approve_template(t["id"], "seed")
# Firm profile.
engagement.set_firm_profile({"bar_number": "000000",
    "costs_line": {"es": "Sin costos adicionales.", "en": "No additional costs."},
    "refund_policy": {"es": "Política de reembolso de prueba.", "en": "Test refund policy."},
    "data_promise": {"es": "Promesa de datos de prueba.", "en": "Test data promise."}}, "seed")
app.save_data()                         # users live in the legacy store: persist the test attorney
print("seeded e2e engagement")
