"""T6-10: the fictional review cases use real question ids and real document codes; the paid script refuses to run unasked."""
import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = yaml.safe_load(open(os.path.join(ROOT, "tests", "fixtures", "legal-review-cases.yaml"), encoding="utf-8"))
QIDS = {q["id"] for q in yaml.safe_load(open(os.path.join(ROOT, "aprende", "content", "datos.yaml"), encoding="utf-8"))}


def test_cases_use_real_questions_and_documents():
    covered = set()
    for name, spec in CASES.items():
        assert set(spec["codes"]) <= {"will", "trust", "poa", "ahcd"}, name
        assert set(spec["answers"]) <= QIDS, (name, set(spec["answers"]) - QIDS)
        covered |= set(spec["codes"])
        if "will" in spec["codes"]:
            covered.add("pour-over" if "trust" in spec["codes"] else "will-alone")
    assert covered == {"will", "trust", "poa", "ahcd", "pour-over", "will-alone"}


def test_the_paid_run_needs_explicit_approval():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "legal-review-drafts.py")], capture_output=True, text=True)
    assert r.returncode != 0 and "approval" in r.stderr
