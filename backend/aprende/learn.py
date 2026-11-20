"""Learning (T4-03): which lessons a client may take, lessons served without their answers, grading, completion.
Lessons come from the content tables (aprende.content); only published items are served. All times are aware datetimes;
`now()` is the one clock (tests patch it)."""
import datetime
import hashlib
import json
import random
import uuid
from zoneinfo import ZoneInfo

import db
from aprende import journey as journeys
from aprende import characters

PASS = 0.8
DISCOUNT_UNITS = ("will", "trust", "ahcd", "poa")      # completing these emits lesson_completed:<unit> (a $100 discount)
GRADED = ("choice", "scenario", "listen", "truefalse", "match", "order")


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def _lessons():
    """Lessons that have at least one published item, in authoring order."""
    rows = db.query("SELECT l.id, l.unit, l.day, l.character, l.sensitive, l.title_es, l.title_en FROM content_lessons l "
                    "WHERE EXISTS (SELECT 1 FROM content_items i WHERE i.lesson_id = l.id AND i.state = 'published') "
                    "ORDER BY l.position, l.id")
    return [dict(zip(("id", "unit", "day", "character", "sensitive", "title_es", "title_en"), r)) for r in rows]


def _items(lesson_id):
    rows = db.query("SELECT i.id, i.step_id, i.kind, i.character, i.sensitive, i.source_id, i.answer, i.version, "
                    "i.payload_json_es, i.payload_json_en FROM content_items i JOIN content_steps s ON s.id = i.step_id "
                    "WHERE i.lesson_id = ? AND i.state = 'published' ORDER BY s.position, i.position", (lesson_id,))
    return [dict(zip(("id", "step_id", "kind", "character", "sensitive", "source_id", "answer", "version", "es", "en"), r))
            for r in rows]


def _completions(journey_id):
    """{lesson_id: completed_at} for this journey."""
    return {lid: datetime.datetime.fromisoformat(at) for lid, at in
            db.query("SELECT lesson_id, completed_at FROM lesson_completions WHERE journey_id = ?", (journey_id,))}


def _lessons_per_day():
    rows = db.query("SELECT value_json FROM settings WHERE key = 'lessons_per_day'")
    return int(json.loads(rows[0][0])) if rows else 1


def _status(journey, lesson, lessons, done):
    """-> (locked | available | done, unlock_at or None)."""
    if lesson["id"] in done:
        return "done", None
    core = sorted((l for l in lessons if l["unit"] in DISCOUNT_UNITS), key=lambda l: l["day"])
    if lesson["unit"] == "final":
        return ("available" if journey["gates"]["may_take_final_lesson"] else "locked"), None
    if lesson["unit"] == "bonus":
        return ("available" if core and core[0]["id"] in done else "locked"), None
    i = next(k for k, l in enumerate(core) if l["id"] == lesson["id"])
    if i == 0:
        return "available", None
    prev = core[i - 1]["id"]
    if prev not in done:
        return "locked", None
    tz = ZoneInfo(journey.get("tz") or "America/Los_Angeles")
    day = done[prev].astimezone(tz).date()
    same_day = sum(1 for at in done.values() if at.astimezone(tz).date() == day)
    if same_day < _lessons_per_day():
        return "available", None
    unlock = datetime.datetime.combine(day + datetime.timedelta(days=1), datetime.time(0), tzinfo=tz)
    return ("available", None) if now() >= unlock else ("locked", unlock)


def _open_lesson(journey, lesson_id):
    """The lesson row if this client may take it; KeyError if unknown, PermissionError if locked."""
    lessons = _lessons()
    lesson = next((l for l in lessons if l["id"] == lesson_id), None)
    if lesson is None:
        raise KeyError(lesson_id)
    if _status(journey, lesson, lessons, _completions(journey["id"]))[0] == "locked":
        raise PermissionError(lesson_id)
    return lesson


def _rng(journey_id, item_id):
    """The same shuffle for the same client and item, across reloads and server restarts."""
    return random.Random(int(hashlib.sha256(f"{journey_id}:{item_id}".encode()).hexdigest(), 16))


def _serve(item, lang, journey_id, host):
    payload = json.loads(item["es"] if lang == "es" else item["en"])
    out = {"id": item["id"], "kind": item["kind"]}
    char = characters.item_character(item["character"], host)
    if char:
        out["character"] = char
    if item["sensitive"]:
        out["sensitive"] = True
    if item["kind"] == "match":
        pairs = payload.pop("pairs")
        right = [{"key": str(k), "text": b} for k, (_, b) in enumerate(pairs)]
        _rng(journey_id, item["id"]).shuffle(right)
        payload.update(left=[{"key": str(k), "text": a} for k, (a, _) in enumerate(pairs)], right=right)
    elif item["kind"] == "order":
        steps = [{"key": str(k), "text": s} for k, s in enumerate(payload["steps"])]
        _rng(journey_id, item["id"]).shuffle(steps)
        payload["steps"] = steps
    payload.pop("explain", None)                    # the explanation comes back with the graded attempt
    return {**out, **payload}


def get_map(journey):
    lessons, done = _lessons(), _completions(journey["id"])
    units = {}
    for lesson in lessons:
        status, unlock = _status(journey, lesson, lessons, done)
        units.setdefault(lesson["unit"], []).append({
            "id": lesson["id"], "day": lesson["day"], "character": characters.lesson_character(lesson["unit"], lesson["character"]),
            "title": {"es": lesson["title_es"], "en": lesson["title_en"]}, "status": status,
            "unlock_at": unlock.isoformat() if unlock else None})
    return {"units": [{"id": unit, "lessons": ls} for unit, ls in units.items()]}


def get_lesson(journey, lesson_id, lang):
    lesson = _open_lesson(journey, lesson_id)
    steps = {sid: {"id": sid, "title": t_es if lang == "es" else t_en, "items": []} for sid, t_es, t_en in
             db.query("SELECT id, title_es, title_en FROM content_steps WHERE lesson_id = ? ORDER BY position", (lesson_id,))}
    for item in _items(lesson_id):
        host = characters.lesson_character(lesson["unit"], lesson["character"])
        steps[item["step_id"]]["items"].append(_serve(item, lang, journey["id"], host))
    return {"id": lesson["id"], "title": lesson["title_es"] if lang == "es" else lesson["title_en"],
            "character": characters.lesson_character(lesson["unit"], lesson["character"]), "sensitive": bool(lesson["sensitive"]),
            "steps": [s for s in steps.values() if s["items"]]}


def grade(item, answer):
    """True or False; ValueError when the answer has the wrong shape for the item."""
    kind, expected = item["kind"], json.loads(item["answer"]) if item["answer"] is not None else None
    payload = json.loads(item["es"])
    if kind in ("choice", "scenario", "listen"):
        if isinstance(answer, bool) or not isinstance(answer, int):
            raise ValueError("answer must be an option index")
        return answer == expected
    if kind == "truefalse":
        if not isinstance(answer, bool):
            raise ValueError("answer must be true or false")
        return answer == expected
    if kind == "match":                             # pairs are authored in their correct pairing
        keys = {str(k) for k in range(len(payload["pairs"]))}
        if not isinstance(answer, dict) or set(answer) != keys:
            raise ValueError("answer must map every left key to a right key")
        return all(k == v for k, v in answer.items())
    if kind == "order":                             # steps are authored in their correct order
        if not isinstance(answer, list) or sorted(answer) != sorted(str(k) for k in range(len(payload["steps"]))):
            raise ValueError("answer must list every step key once")
        return answer == [str(k) for k in range(len(payload["steps"]))]
    raise ValueError(f"{kind} items are not answered")


def submit_attempt(journey, item_id, answer, lang="es"):
    rows = db.query("SELECT lesson_id FROM content_items WHERE id = ? AND state = 'published'", (item_id,))
    if not rows:
        raise KeyError(item_id)
    _open_lesson(journey, rows[0][0])
    item = next(i for i in _items(rows[0][0]) if i["id"] == item_id)
    correct = grade(item, answer)
    at = now().isoformat()
    awarded = 0
    with db.transaction() as conn:
        attempt = conn.execute("SELECT COUNT(*) FROM item_attempts WHERE journey_id = ? AND item_id = ?",
                               (journey["id"], item_id)).fetchone()[0] + 1
        conn.execute("INSERT INTO item_attempts (id, journey_id, item_id, version, attempt, correct, created_at) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?)", (str(uuid.uuid4()), journey["id"], item_id, item["version"], attempt,
                                                      1 if correct else 0, at))
        conn.execute("INSERT INTO events (id, journey_id, type, props_json, created_at) VALUES (?, ?, ?, ?, ?)",
                     (str(uuid.uuid4()), journey["id"], "item_answered",
                      json.dumps({"item_id": item_id, "correct": correct, "attempt": attempt}), at))
        if correct:
            from aprende import motivation       # motivation imports learn (for the clock)
            awarded = motivation.award_petal_tx(conn, journey["id"], "item_correct", item_id, motivation.PETAL_ITEM, at)
    rows = db.query("SELECT kind, cite, url FROM content_sources WHERE id = ?", (item["source_id"],)) if item["source_id"] else []
    return {"correct": correct, "explain": json.loads(item[lang]).get("explain"),
            "source": dict(zip(("kind", "cite", "url"), rows[0])) if rows else None,
            "petals": awarded}


def complete_lesson(journey, lesson_id):
    lesson = _open_lesson(journey, lesson_id)
    graded = [i["id"] for i in _items(lesson_id) if i["kind"] in GRADED]
    latest = {item_id: bool(c) for item_id, c, _ in db.query(
        "SELECT item_id, correct, attempt FROM item_attempts WHERE journey_id = ? ORDER BY attempt", (journey["id"],))}
    answered = all(i in latest for i in graded)
    score = sum(latest.get(i, False) for i in graded) / len(graded) if graded else 1.0
    completed = answered and score >= PASS
    if completed and lesson_id not in _completions(journey["id"]):
        from aprende import motivation
        at = now().isoformat()
        with db.transaction() as conn:
            conn.execute("INSERT INTO lesson_completions (journey_id, lesson_id, completed_at) VALUES (?, ?, ?) "
                         "ON CONFLICT (journey_id, lesson_id) DO NOTHING", (journey["id"], lesson_id, at))
            motivation.award_petal_tx(conn, journey["id"], "lesson_complete", lesson_id, motivation.PETAL_LESSON, at)
        if lesson["unit"] in DISCOUNT_UNITS:
            journeys.apply(journey["id"], f"lesson_completed:{lesson['unit']}", {}, actor="system")
        elif lesson["unit"] == "final":
            journeys.apply(journey["id"], "final_lesson_completed", {}, actor="system")
    return {"completed": completed, "score": score}
