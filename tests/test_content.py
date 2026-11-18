"""T4-02 acceptance tests, written by Opus before the code (ticket ★). Contract: aprende/content/FORMAT.md and
backend/aprende/content.py with load_dir, validate, import_bundle, export_dir, approve, publish, and the CLI
`python -m aprende.content import|export|validate <dir>` (run from backend/). Do not weaken these tests."""
import copy
import os
import shutil
import subprocess
import sys
import tempfile
import uuid

os.environ.setdefault("DATABASE_URL", "")
os.environ.setdefault("CARBON_DB_PATH", tempfile.mktemp(suffix=".db"))
sys.path.insert(0, "backend")

import pytest

import app as backend   # noqa: F401  (registers the app, runs migrations)
import db
from aprende import content

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures", "content")
ROOT = os.path.dirname(HERE)


def bundle():
    return content.load_dir(FIX)


def errors_for(mutate):
    b = copy.deepcopy(bundle())
    mutate(b)
    return content.validate(b)


def item(b, item_id):
    for lesson in b["lessons"]:
        for step in lesson["steps"]:
            for it in step["items"]:
                if it["id"] == item_id:
                    return it
    raise KeyError(item_id)


def fresh_ids(b):
    """Give the fixture lesson a unique id so tests do not collide in the shared database."""
    lid = "demo" + uuid.uuid4().hex[:6]
    lesson = b["lessons"][0]
    lesson["id"] = lid
    lesson["day"] = None
    lesson["unit"] = "bonus"
    for step in lesson["steps"]:
        step["id"] = step["id"].replace("demo", lid, 1)
        for it in step["items"]:
            it["id"] = it["id"].replace("demo", lid, 1)
    return lid


def test_fixture_is_valid():
    assert content.validate(bundle()) == []


@pytest.mark.parametrize("mutate,needle", [
    (lambda b: item(b, "demo.1.1").pop("source"), "demo.1.1"),                                       # legal without source
    (lambda b: item(b, "demo.1.1").update(source="nope"), "nope"),                                   # unknown source
    (lambda b: b["sources"][0].update(cite="9999"), "9999"),                                        # not on VERIFIED
    (lambda b: b["sources"][1].update(url="https://example.com/wills"), "selfhelp.courts.ca.gov"),  # not the courts site
    (lambda b: item(b, "demo.1.2").pop("en"), "demo.1.2"),                                           # missing English
    (lambda b: item(b, "demo.1.2")["en"].pop("explain"), "demo.1.2"),                                # fields differ
    (lambda b: item(b, "demo.1.2").update(answer=3), "demo.1.2"),                                    # answer out of range
    (lambda b: item(b, "demo.1.3").update(answer=1), "demo.1.3"),                                    # truefalse needs a bool
    (lambda b: item(b, "demo.1.4")["en"]["pairs"].pop(), "demo.1.4"),                                # list lengths differ
    (lambda b: item(b, "demo.1.5").update(answer=0), "demo.1.5"),                                    # order has no answer
    (lambda b: item(b, "demo.1.5").update(kind="essay"), "essay"),                                   # unknown kind
    (lambda b: item(b, "demo.1.5").update(id="other.1.5"), "other.1.5"),                             # id prefix
    (lambda b: item(b, "demo.1.3").update(id="demo.1.2"), "demo.1.2"),                               # duplicate id
    (lambda b: b["lessons"][0].update(datos=["nombre", "no_such_question"]), "no_such_question"),    # unknown datos id
    (lambda b: b["lessons"][0].update(unit="cooking"), "cooking"),                                   # unknown unit
])
def test_validator_catches(mutate, needle):
    errs = errors_for(mutate)
    assert errs, "expected a validation error"
    assert any(needle in e for e in errs), errs


def test_duplicate_day_is_an_error():
    b = copy.deepcopy(bundle())
    twin = copy.deepcopy(b["lessons"][0])
    twin["id"] = "twin"
    for step in twin["steps"]:
        step["id"] = step["id"].replace("demo", "twin", 1)
        for it in step["items"]:
            it["id"] = it["id"].replace("demo", "twin", 1)
    b["lessons"].append(twin)
    assert any("day" in e for e in content.validate(b))


def test_import_is_idempotent_and_versions_changes():
    b = copy.deepcopy(bundle())
    lid = fresh_ids(b)
    first = content.import_bundle(b, actor="opus")
    assert first["items_created"] == 5
    again = content.import_bundle(b, actor="opus")
    assert again["items_created"] == 0 and again["items_changed"] == 0
    item(b, f"{lid}.1.1")["es"]["text"] = "Texto nuevo."
    changed = content.import_bundle(b, actor="opus")
    assert changed["items_changed"] == 1
    rows = db.query("SELECT version, state FROM content_items WHERE id = ?", (f"{lid}.1.1",))
    assert rows[0][0] == 2 and rows[0][1] == "draft"


def test_import_refuses_an_invalid_bundle():
    b = copy.deepcopy(bundle())
    fresh_ids(b)
    item(b, b["lessons"][0]["steps"][0]["items"][0]["id"]).pop("source")
    with pytest.raises(ValueError):
        content.import_bundle(b, actor="opus")


def test_legal_items_need_an_attorney_approval_to_publish():
    b = copy.deepcopy(bundle())
    lid = fresh_ids(b)
    content.import_bundle(b, actor="opus")
    with pytest.raises(PermissionError):
        content.publish(f"{lid}.1.1", actor="paralegal@example.com")
    content.publish(f"{lid}.1.3", actor="paralegal@example.com")          # not legal: publishes without approval
    content.approve(f"{lid}.1.1", attorney="attorney@example.com")
    content.publish(f"{lid}.1.1", actor="paralegal@example.com")
    rows = db.query("SELECT state FROM content_items WHERE id IN (?, ?)", (f"{lid}.1.1", f"{lid}.1.3"))
    assert {r[0] for r in rows} == {"published"}
    approval = db.query("SELECT attorney, version FROM content_approvals WHERE item_id = ?", (f"{lid}.1.1",))
    assert approval[0][0] == "attorney@example.com" and approval[0][1] == 1


def test_an_approval_covers_one_version_only():
    b = copy.deepcopy(bundle())
    lid = fresh_ids(b)
    content.import_bundle(b, actor="opus")
    content.approve(f"{lid}.1.2", attorney="attorney@example.com")
    item(b, f"{lid}.1.2")["es"]["explain"] = "Otra explicación."
    content.import_bundle(b, actor="opus")                                  # version 2, not approved
    with pytest.raises(PermissionError):
        content.publish(f"{lid}.1.2", actor="paralegal@example.com")


def test_export_round_trips():
    b = copy.deepcopy(bundle())
    lid = fresh_ids(b)
    content.import_bundle(b, actor="opus")
    out1, out2 = tempfile.mkdtemp(), tempfile.mkdtemp()
    content.export_dir(out1)
    exported = content.load_dir(out1)
    mine = next(l for l in exported["lessons"] if l["id"] == lid)
    assert mine == b["lessons"][0]                                          # same content back
    assert {s["id"] for s in b["sources"]} <= {s["id"] for s in exported["sources"]}
    content.import_bundle(exported, actor="opus")                           # re-importing an export changes nothing
    content.export_dir(out2)
    for name in sorted(os.listdir(os.path.join(out1, "lessons"))):
        assert open(os.path.join(out1, "lessons", name), encoding="utf-8").read() == \
            open(os.path.join(out2, "lessons", name), encoding="utf-8").read(), name
    shutil.rmtree(out1); shutil.rmtree(out2)


def test_cli_validate_reports_errors():
    ok = subprocess.run([sys.executable, "-m", "aprende.content", "validate", FIX], cwd=os.path.join(ROOT, "backend"),
                        capture_output=True, text=True)
    assert ok.returncode == 0, ok.stderr
    bad = tempfile.mkdtemp()
    shutil.copytree(FIX, bad, dirs_exist_ok=True)
    path = os.path.join(bad, "lessons", "demo.yaml")
    _txt = open(path, encoding="utf-8").read()
    open(path, "w", encoding="utf-8").write(_txt.replace("source: pc-6110\n        es: {text", "es: {text", 1))
    r = subprocess.run([sys.executable, "-m", "aprende.content", "validate", bad], cwd=os.path.join(ROOT, "backend"),
                       capture_output=True, text=True)
    assert r.returncode != 0 and "demo.1.1" in (r.stdout + r.stderr)
    shutil.rmtree(bad)
