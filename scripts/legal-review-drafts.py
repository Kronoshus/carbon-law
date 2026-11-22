#!/usr/bin/env python
"""T6-10 legal output review: real drafts for fictional clients, through the same code the app runs on payment.

COSTS MONEY (Beam). Run only with Kevin's approval (decision PR):  python scripts/legal-review-drafts.py --yes-i-have-approval
Writes reports/legal-review/<case>/<document>.md for Opus to read in full against the prototype's drafting standard."""
import os, sys, tempfile

if "--yes-i-have-approval" not in sys.argv:
    sys.exit("This calls the paid model. Re-run with --yes-i-have-approval once Kevin has approved the cost.")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "backend"), ROOT]
os.environ.setdefault("CARBON_DB_PATH", tempfile.mktemp(suffix=".db"))
os.environ["DATABASE_URL"] = ""
import yaml
import migrate
from aprende import datos, drafts

migrate.run()
CASES = yaml.safe_load(open(os.path.join(ROOT, "tests", "fixtures", "legal-review-cases.yaml"), encoding="utf-8"))


for case, spec in CASES.items():
    codes, answers = spec["codes"], spec["answers"]
    lines = [f"Assistant: {q['en']}\nClient: {answers.get(q['id'], '(skipped)')}" for q in datos.QUESTIONS
             if not q["docs"] or set(q["docs"]) & set(codes)]
    talk = "<client_data>\n" + "\n\n".join(lines) + "\n</client_data>"
    out = os.path.join(ROOT, "reports", "legal-review", case)
    os.makedirs(out, exist_ok=True)
    for kind in codes:
        for strict in (True, False):
            try:
                md, _ = drafts.draft(kind, codes, talk, strict)
                break
            except Exception as e:                         # recorded in the report: a failure is a finding
                md = f"DRAFT FAILED ({'strict' if strict else 'lenient'}): {e}"
        open(os.path.join(out, f"{drafts.name(kind, codes).lower().replace(' ', '-')}.md"), "w", encoding="utf-8").write(md)
        print(case, kind, "ok" if not md.startswith("DRAFT FAILED") else "FAILED")
