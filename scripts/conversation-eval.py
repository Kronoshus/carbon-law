#!/usr/bin/env python
"""Live conversation run (T5-08): every scripted conversation against the real model, through the real /chat code.

COSTS MONEY (Beam). Run only with Kevin's approval:  python scripts/conversation-eval.py --yes-i-have-approval
Writes reports/conversations-<date>.md: each transcript with automatic checks (prices, tags, one question, length) and an
empty grading box per rubric item for Opus to fill in. Failures become new tests."""
import datetime, json, os, re, sys, tempfile, uuid

if "--yes-i-have-approval" not in sys.argv:
    sys.exit("This calls the paid model. Re-run with --yes-i-have-approval once Kevin has approved the cost.")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "backend"), ROOT]
os.environ.setdefault("CARBON_DB_PATH", tempfile.mktemp(suffix=".db"))
os.environ["DATABASE_URL"] = ""
import yaml
from fastapi.testclient import TestClient
import app as backend, migrate
from aprende import content, journey

migrate.run()
b = content.load_dir(os.path.join(ROOT, "aprende", "content"))
content.import_bundle(b, actor="eval")
for l in b["lessons"]:
    for s in l["steps"]:
        for it in s["items"]:
            if it.get("legal"):
                content.approve(it["id"], attorney="eval")
            content.publish(it["id"], actor="eval")
c = TestClient(backend.app)
SET = yaml.safe_load(open(os.path.join(ROOT, "tests", "fixtures", "conversations.yaml"), encoding="utf-8"))
PRICE = re.compile(r"\$\s?\d|\d+\s?(dólares|dollars)", re.I)


def client():
    t = c.post("/auth/signup", json={"name": "Ana Torres", "email": f"eval-{uuid.uuid4().hex[:8]}@example.com",
                                     "password": "long-secure-password", "source": "aprende", "adult": True}).json()["token"]
    h = {"Authorization": "Bearer " + t}
    for ev, p in (("ai_disclosed", {}), ("consent", {"answer": "yes"}), ("names_submitted", {"names": ["Ana Torres"]})):
        j = c.post("/journey/events", json={"type": ev, "payload": p}, headers=h).json()
    journey.apply(j["id"], "conflict_auto", {"result": "clear"}, actor="system")
    return h


out = [f"# Live conversation run, {datetime.date.today()}\n", "Grade each rubric item: pass / fail + one line why.\n"]
for conv in SET["conversations"]:
    h, history = client(), []
    out.append(f"\n## {conv['id']} ({conv['lang']}, {conv['mode']}, {conv['character']})\n")
    for turn in conv["turns"]:
        history.append({"role": "user", "content": turn, "question_id": "nombre"})
        body = {"mode": conv["mode"], "character": conv["character"], "lang": conv["lang"], "messages": history,
                **({"lesson_id": conv["lesson_id"]} if conv["mode"] == "learn" else {"group": conv["group"]})}
        r = c.post("/chat", json=body, headers=h).json()
        history.append({"role": "assistant", "content": r.get("history", ""), "reasoning_content": r.get("reasoning")})
        auto = [f"price:{'FAIL' if PRICE.search(r.get('text', '')) else 'ok'}", f"questions:{r.get('text', '').count('?')}",
                f"words:{len(r.get('text', '').split())}", f"attorney_tag:{r.get('attorney_question')}"]
        out += [f"- **Client:** {turn}", f"- **{conv['character']}:** {r.get('text', r)}", f"  - auto: {', '.join(auto)}"]
    if conv.get("attorney_question"):
        out.append(f"  - expected attorney tag: {'ok' if r.get('attorney_question') else 'FAIL'}")
    out += [f"- [ ] must: {m} — {SET['rubric'][m]}" for m in conv["must"]]
    out += [f"- [ ] never: {n} — {SET['rubric'][n]}" for n in conv["never"]]
os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
path = os.path.join(ROOT, "reports", f"conversations-{datetime.date.today()}.md")
open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
print(path)
