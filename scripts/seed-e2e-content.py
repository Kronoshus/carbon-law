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
