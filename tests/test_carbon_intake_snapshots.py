"""T2-01 acceptance (written by Opus before the move): the moved carbon_intake package produces exactly the prompts the
prototype produced on main. Snapshots: tests/fixtures/carbon_intake_snapshots.json (generated from main, do not regenerate)."""
import json, pathlib
import carbon_intake as ci

SNAP = json.loads((pathlib.Path(__file__).parent / "fixtures" / "carbon_intake_snapshots.json").read_text(encoding="utf-8"))


def test_system_prompt_unchanged():
    for case in SNAP["system_prompt"]:
        assert ci.system_prompt(*case["args"]) == case["text"], case["args"]


def test_drafter_unchanged():
    for case in SNAP["drafter"]:
        assert ci.drafter(*case["args"]) == case["text"], case["args"]


def test_spoken_unchanged():
    for case in SNAP["spoken"]:
        assert ci.spoken(case["in"]) == case["out"]


def test_verified_and_docs_unchanged():
    assert sorted(ci.VERIFIED) == SNAP["verified_keys"]
    assert list(ci.DOCS) == SNAP["docs_keys"]


def test_server_has_no_copies():
    src = (pathlib.Path(__file__).parents[1] / "avatar-intake" / "server.py").read_text(encoding="utf-8")
    for name in ("def system_prompt", "def drafter", "def checklist", "def spoken", "def looping", "def conflict_hits", "VERIFIED = {", "DOCS = {"):
        assert name not in src, f"{name} still defined in server.py"
