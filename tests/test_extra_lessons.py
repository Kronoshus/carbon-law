"""Decision #55: the two extra bonus lessons (children; TOD deed, Prop 19, Medi-Cal estate recovery). They wait for attorney
Raval: no client sees a legal item before he approves its exact version."""
import os
import sys
import tempfile

os.environ.setdefault("DATABASE_URL", "")
os.environ.setdefault("CARBON_DB_PATH", tempfile.mktemp(suffix=".db"))
sys.path.insert(0, "backend")

import pytest

import app as backend  # noqa: F401  (registers the app, runs migrations)
from aprende import content, learn

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "aprende", "content")
NEW = {"hijos", "sorpresas"}


def items(lessons):
    return [it for lesson in lessons for step in lesson["steps"] for it in step["items"]]


def test_the_seed_content_is_valid_and_the_new_lessons_are_bonus_lessons():
    b = content.load_dir(SEED)
    assert content.validate(b) == []
    new = [lesson for lesson in b["lessons"] if lesson["id"] in NEW]
    assert {lesson["id"] for lesson in new} == NEW
    assert all(lesson["unit"] == "bonus" and lesson["day"] is None for lesson in new)


def test_the_new_lessons_stay_hidden_until_the_attorney_approves_each_legal_item():
    b = content.load_dir(SEED)
    b["lessons"] = [lesson for lesson in b["lessons"] if lesson["id"] in NEW]
    content.import_bundle(b, actor="test")
    assert not NEW & {lesson["id"] for lesson in learn._lessons()}
    legal = [it["id"] for it in items(b["lessons"]) if it.get("legal")]
    assert legal
    for iid in legal:
        with pytest.raises(PermissionError):
            content.publish(iid, actor="paralegal@example.com")
        with pytest.raises(PermissionError):
            content.publish_version(iid, 1, "paralegal@example.com")


def test_every_lesson_item_is_in_the_attorney_review_packet():
    packet = open(os.path.join(ROOT, "docs", "aprende", "lesson-review-packet.md"), encoding="utf-8").read()
    missing = [it["id"] for it in items(content.load_dir(SEED)["lessons"]) if f"**{it['id']}**" not in packet]
    assert missing == []
