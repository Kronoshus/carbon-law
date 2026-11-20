"""The Playwright backend can never reach a paid model, even on a developer machine with a Beam key.

Found by the guardrail audit (~/work/cl-reports/audit-guardrails.md). (Opus)"""
import json
import os
import subprocess
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_the_playwright_backend_cannot_reach_a_paid_model(tmp_path):
    """Playwright starts the real backend (scripts/start-e2e-backend.sh) with the developer's environment, and that backend
    loads ~/.config/carbon-law/beam.env on the demo path: its model address must point nowhere and no key may be passed on."""
    dump = tmp_path / "env.json"
    shim = tmp_path / "python"
    shim.write_text(f"#!{sys.executable}\nimport json, os\nopen({str(dump)!r}, 'w').write(json.dumps(dict(os.environ)))\n")
    shim.chmod(0o755)
    env = {**os.environ, "PYTHON": str(shim), "PORT": "8999", "CARBON_DB_PATH": str(tmp_path / "e2e.db"),
           "REFLECTION_API_KEY": "sk-developer-key", "BEAM_API_KEY": "sk-developer-key"}
    env.pop("BEAM_BASE_URL", None)
    subprocess.run(["bash", os.path.join(ROOT, "scripts", "start-e2e-backend.sh")], env=env, check=True, timeout=60)
    seen = json.loads(dump.read_text())
    assert urllib.parse.urlsplit(seen.get("BEAM_BASE_URL", "https://api.reflection.ai")).hostname in ("127.0.0.1", "localhost")
    assert seen.get("REFLECTION_API_KEY") != "sk-developer-key" and seen.get("BEAM_API_KEY") != "sk-developer-key"

