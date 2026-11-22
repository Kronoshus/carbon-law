"""Lesson content: load, validate, import, export, approve, publish (format: aprende/content/FORMAT.md).
CLI, from backend/:  python -m aprende.content import|export|validate <dir>"""

import json, os, sys
from datetime import datetime, timezone
from urllib.parse import urlparse

import yaml

import app as backend_app  # puts the repo root on sys.path (carbon_intake) and provides the audit log
import db
from carbon_intake import VERIFIED, questions

UNITS = {"will", "trust", "ahcd", "poa", "final", "bonus"}
KINDS = {"explain", "choice", "scenario", "listen", "truefalse", "match", "order"}
SOURCE_KINDS = {"probate_code", "courts_selfhelp", "state_agency"}
LIST_FIELDS = {"options", "pairs", "steps"}
STATE_AGENCY_HOSTS = {"www.boe.ca.gov", "www.dhcs.ca.gov"}   # Prop 19 (BOE), Medi-Cal estate recovery (DHCS)


def _qids():
    return {step["id"] for step in questions("guion-plan")[0]}


def load_dir(path):
    sources = []
    sources_path = os.path.join(path, "sources.yaml")
    if os.path.exists(sources_path):
        with open(sources_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data:
                sources = data
    lessons = []
    ld = os.path.join(path, "lessons")
    if os.path.isdir(ld):
        for name in sorted(os.listdir(ld)):
            if not name.endswith((".yaml", ".yml")):
                continue
            with open(os.path.join(ld, name), encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data:
                    lessons.append(data)
    lessons.sort(key=lambda x: x.get("id", ""))
    return {"sources": sources, "lessons": lessons}


_MISSING = object()


def validate(bundle):
    errors = []
    sources = bundle.get("sources", []) or []
    lessons = bundle.get("lessons", []) or []
    source_ids = {}
    for s in sources:
        if not isinstance(s, dict):
            continue
        sid = s.get("id")
        if sid in source_ids:
            errors.append(f"duplicate source id {sid}")
        source_ids[sid] = s
    all_ids = set(source_ids.keys())
    qids = _qids()
    days = {}
    for lesson in lessons:
        if not isinstance(lesson, dict):
            continue
        lid = lesson.get("id")
        if lid in all_ids:
            errors.append(f"duplicate id {lid}")
        all_ids.add(lid)
        unit = lesson.get("unit")
        if unit not in UNITS:
            errors.append(f"{lid}: unknown unit {unit}")
        day = lesson.get("day")
        if day is not None:
            if day in days:
                errors.append(f"duplicate day {day}")
            days[day] = lid
        for d in lesson.get("datos") or []:
            if d not in qids:
                errors.append(f"{lid}: unknown datos id {d}")
        title = lesson.get("title") or {}
        if not isinstance(title, dict) or "es" not in title or "en" not in title:
            errors.append(f"{lid}: title missing es/en")
        for step in lesson.get("steps") or []:
            if not isinstance(step, dict):
                continue
            sid = step.get("id")
            if sid in all_ids:
                errors.append(f"duplicate id {sid}")
            all_ids.add(sid)
            if not (isinstance(sid, str) and sid.startswith(str(lid) + ".")):
                errors.append(f"{sid}: id must start with {lid}.")
            stitle = step.get("title") or {}
            if not isinstance(stitle, dict) or "es" not in stitle or "en" not in stitle:
                errors.append(f"{sid}: title missing es/en")
            for it in step.get("items") or []:
                if not isinstance(it, dict):
                    continue
                iid = it.get("id")
                if iid in all_ids:
                    errors.append(f"duplicate id {iid}")
                all_ids.add(iid)
                if not (isinstance(iid, str) and iid.startswith(str(lid) + ".")):
                    errors.append(f"{iid}: id must start with {lid}.")
                kind = it.get("kind")
                if kind not in KINDS:
                    errors.append(f"{iid}: unknown kind {kind}")
                es = it.get("es")
                en = it.get("en")
                if not isinstance(es, dict) or not isinstance(en, dict):
                    errors.append(f"{iid}: missing es/en")
                    continue
                if set(es.keys()) != set(en.keys()):
                    errors.append(f"{iid}: es/en fields differ")
                for lf in LIST_FIELDS:
                    if lf in es and lf in en:
                        if isinstance(es[lf], list) and isinstance(en[lf], list):
                            if len(es[lf]) != len(en[lf]):
                                errors.append(f"{iid}: list lengths differ")
                legal = bool(it.get("legal", False))
                src = it.get("source")
                if legal:
                    if src is None:
                        errors.append(f"{iid}: legal item missing source")
                    elif src not in source_ids:
                        errors.append(f"{iid}: unknown source {src}")
                answer = it.get("answer", _MISSING)
                has_answer = answer is not _MISSING
                if kind in ("choice", "scenario", "listen"):
                    if not has_answer:
                        errors.append(f"{iid}: missing answer")
                    else:
                        if isinstance(answer, bool) or not isinstance(answer, int):
                            errors.append(f"{iid}: answer must be int")
                        else:
                            opts = es.get("options") if isinstance(es, dict) else None
                            n = len(opts) if isinstance(opts, list) else 0
                            if n and not (0 <= answer < n):
                                errors.append(f"{iid}: answer out of range {answer}")
                elif kind == "truefalse":
                    if not has_answer:
                        errors.append(f"{iid}: missing answer")
                    elif not isinstance(answer, bool):
                        errors.append(f"{iid}: truefalse needs a bool")
                else:
                    if has_answer:
                        errors.append(f"{iid}: {kind} has no answer")
    for s in sources:
        if not isinstance(s, dict):
            continue
        sid = s.get("id")
        kind = s.get("kind")
        if kind not in SOURCE_KINDS:
            errors.append(f"{sid}: unknown source kind {kind}")
        cite = s.get("cite")
        url = s.get("url", "")
        if kind == "probate_code":
            if str(cite) not in VERIFIED:
                errors.append(f"{sid}: cite {cite} not on VERIFIED")
        elif kind == "courts_selfhelp":
            if "selfhelp.courts.ca.gov" not in str(url):
                errors.append(f"{sid}: url must be on selfhelp.courts.ca.gov")
        elif kind == "state_agency":
            if urlparse(str(url)).hostname not in STATE_AGENCY_HOSTS:
                errors.append(f"{sid}: url must be on " + " or ".join(sorted(STATE_AGENCY_HOSTS)))
    return errors


def _now():
    return datetime.now(timezone.utc).isoformat()


def import_bundle(bundle, actor=""):
    errs = validate(bundle)
    if errs:
        raise ValueError("; ".join(errs))
    with db.transaction():  # all or nothing
        return _import(bundle, actor)


def _import(bundle, actor):
    sources = bundle.get("sources", []) or []
    lessons = bundle.get("lessons", []) or []
    for s in sources:
        existing = db.query("SELECT id FROM content_sources WHERE id = ?", (s["id"],))
        if existing:
            db.execute(
                "UPDATE content_sources SET kind=?,cite=?,url=?,read_on=? WHERE id=?",
                (s["kind"], s["cite"], s["url"], s.get("read_on"), s["id"]),
            )
        else:
            db.execute(
                "INSERT INTO content_sources (id,kind,cite,url,read_on) VALUES (?,?,?,?,?)",
                (s["id"], s["kind"], s["cite"], s["url"], s.get("read_on")),
            )
    items_created = 0
    items_changed = 0
    for li, lesson in enumerate(lessons):
        lid = lesson["id"]
        existing_lesson = db.query(
            "SELECT id FROM content_lessons WHERE id = ?", (lid,)
        )
        datos = lesson.get("datos")
        if existing_lesson:
            db.execute(
                "UPDATE content_lessons SET unit=?,day=?,character=?,sensitive=?,datos=?,title_es=?,title_en=?,position=? WHERE id=?",
                (
                    lesson["unit"],
                    lesson.get("day"),
                    lesson.get("character"),
                    1 if lesson.get("sensitive") else 0,
                    json.dumps(datos) if datos is not None else None,
                    (lesson.get("title") or {}).get("es"),
                    (lesson.get("title") or {}).get("en"),
                    li,
                    lid,
                ),
            )
        else:
            db.execute(
                "INSERT INTO content_lessons (id,unit,day,character,sensitive,datos,title_es,title_en,position) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    lid,
                    lesson["unit"],
                    lesson.get("day"),
                    lesson.get("character"),
                    1 if lesson.get("sensitive") else 0,
                    json.dumps(datos) if datos is not None else None,
                    (lesson.get("title") or {}).get("es"),
                    (lesson.get("title") or {}).get("en"),
                    li,
                ),
            )
        for si, step in enumerate(lesson.get("steps") or []):
            sid = step["id"]
            existing_step = db.query(
                "SELECT id FROM content_steps WHERE id = ?", (sid,)
            )
            if existing_step:
                db.execute(
                    "UPDATE content_steps SET lesson_id=?,position=?,title_es=?,title_en=? WHERE id=?",
                    (
                        lid,
                        si,
                        (step.get("title") or {}).get("es"),
                        (step.get("title") or {}).get("en"),
                        sid,
                    ),
                )
            else:
                db.execute(
                    "INSERT INTO content_steps (id,lesson_id,position,title_es,title_en) VALUES (?,?,?,?,?)",
                    (
                        sid,
                        lid,
                        si,
                        (step.get("title") or {}).get("es"),
                        (step.get("title") or {}).get("en"),
                    ),
                )
            for ii, it in enumerate(step.get("items") or []):
                iid = it["id"]
                payload_es = {k: v for k, v in (it.get("es") or {}).items()}
                payload_en = {k: v for k, v in (it.get("en") or {}).items()}
                has_answer = "answer" in it
                answer_val = it.get("answer") if has_answer else None
                legal = 1 if it.get("legal") else 0
                sensitive = 1 if it.get("sensitive") else 0
                char = it.get("character")
                source_id = it.get("source")
                new_es_json = json.dumps(payload_es, ensure_ascii=False)
                new_en_json = json.dumps(payload_en, ensure_ascii=False)
                answer_json = (
                    json.dumps(answer_val, ensure_ascii=False) if has_answer else None
                )
                version_existing = db.query(
                    "SELECT version,kind,legal,sensitive,character,source_id,answer,payload_json_es,payload_json_en FROM content_items WHERE id = ?",
                    (iid,),
                )
                if not version_existing:
                    db.execute(
                        "INSERT INTO content_items (id,lesson_id,step_id,position,kind,legal,sensitive,character,source_id,answer,version,state,payload_json_es,payload_json_en) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            iid,
                            lid,
                            sid,
                            ii,
                            it["kind"],
                            legal,
                            sensitive,
                            char,
                            source_id,
                            answer_json,
                            1,
                            "draft",
                            new_es_json,
                            new_en_json,
                        ),
                    )
                    items_created += 1
                else:
                    (ver, okind, olegal, osens, ochar, osrc, oans, oes, oen) = (
                        version_existing[0]
                    )
                    changed = (
                        okind != it["kind"]
                        or olegal != legal
                        or osens != sensitive
                        or ochar != char
                        or osrc != source_id
                        or oans != answer_json
                        or oes != new_es_json
                        or oen != new_en_json
                    )
                    if changed:
                        db.execute(
                            "UPDATE content_items SET lesson_id=?,step_id=?,position=?,kind=?,legal=?,sensitive=?,character=?,source_id=?,answer=?,version=?,state=?,payload_json_es=?,payload_json_en=? WHERE id=?",
                            (
                                lid,
                                sid,
                                ii,
                                it["kind"],
                                legal,
                                sensitive,
                                char,
                                source_id,
                                answer_json,
                                ver + 1,
                                "draft",
                                new_es_json,
                                new_en_json,
                                iid,
                            ),
                        )
                        items_changed += 1
                    else:
                        db.execute(
                            "UPDATE content_items SET lesson_id=?,step_id=?,position=? WHERE id=?",
                            (lid, sid, ii, iid),
                        )
    backend_app.log_audit(
        actor,
        "import",
        "content",
        "bundle",
        f"created={items_created} changed={items_changed}",
    )
    return {"items_created": items_created, "items_changed": items_changed}


def export_dir(path):
    os.makedirs(path, exist_ok=True)
    lessons_dir = os.path.join(path, "lessons")
    os.makedirs(lessons_dir, exist_ok=True)
    src_rows = db.query(
        "SELECT id,kind,cite,url,read_on FROM content_sources ORDER BY id"
    )
    sources = [
        {"id": r[0], "kind": r[1], "cite": r[2], "url": r[3], "read_on": r[4]}
        for r in src_rows
    ]
    with open(os.path.join(path, "sources.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(
            sources, f, sort_keys=False, allow_unicode=True, default_flow_style=False
        )
    lesson_rows = db.query(
        "SELECT id,unit,day,character,sensitive,datos,title_es,title_en FROM content_lessons ORDER BY position,id"
    )
    for lr in lesson_rows:
        lid = lr[0]
        lesson = {"id": lid, "unit": lr[1]}
        lesson["day"] = lr[2]
        if lr[3] is not None:
            lesson["character"] = lr[3]
        lesson["sensitive"] = bool(lr[4])
        if lr[5] is not None:
            lesson["datos"] = json.loads(lr[5])
        lesson["title"] = {"es": lr[6], "en": lr[7]}
        step_rows = db.query(
            "SELECT id,title_es,title_en FROM content_steps WHERE lesson_id=? ORDER BY position,id",
            (lid,),
        )
        steps = []
        for sr in step_rows:
            sid = sr[0]
            step = {"id": sid, "title": {"es": sr[1], "en": sr[2]}}
            item_rows = db.query(
                "SELECT id,kind,legal,sensitive,character,source_id,answer,position,payload_json_es,payload_json_en FROM content_items WHERE step_id=? ORDER BY position,id",
                (sid,),
            )
            items = []
            for ir in item_rows:
                iid = ir[0]
                item = {"id": iid, "kind": ir[1]}
                if ir[2]:
                    item["legal"] = True
                if ir[3]:
                    item["sensitive"] = True
                if ir[4] is not None:
                    item["character"] = ir[4]
                if ir[5] is not None:
                    item["source"] = ir[5]
                if ir[6] is not None:
                    item["answer"] = json.loads(ir[6])
                item["es"] = json.loads(ir[8])
                item["en"] = json.loads(ir[9])
                items.append(item)
            step["items"] = items
            steps.append(step)
        lesson["steps"] = steps
        with open(os.path.join(lessons_dir, f"{lid}.yaml"), "w", encoding="utf-8") as f:
            yaml.safe_dump(
                lesson, f, sort_keys=False, allow_unicode=True, default_flow_style=False
            )


def approve(item_id, attorney):
    rows = db.query("SELECT version FROM content_items WHERE id = ?", (item_id,))
    if not rows:
        raise ValueError(f"unknown item {item_id}")
    version = rows[0][0]
    existing = db.query(
        "SELECT version FROM content_approvals WHERE item_id=? AND version=?",
        (item_id, version),
    )
    if existing:
        db.execute(
            "UPDATE content_approvals SET attorney=?,approved_at=? WHERE item_id=? AND version=?",
            (attorney, _now(), item_id, version),
        )
    else:
        db.execute(
            "INSERT INTO content_approvals (item_id,version,attorney,approved_at) VALUES (?,?,?,?)",
            (item_id, version, attorney, _now()),
        )
    backend_app.log_audit(
        attorney, "approve", "content_item", item_id, f"version={version}"
    )
    return {"item_id": item_id, "version": version}


def publish(item_id, actor):
    rows = db.query("SELECT version,legal FROM content_items WHERE id = ?", (item_id,))
    if not rows:
        raise ValueError(f"unknown item {item_id}")
    version, legal = rows[0][0], bool(rows[0][1])
    if legal:
        ap = db.query(
            "SELECT version FROM content_approvals WHERE item_id=? AND version=?",
            (item_id, version),
        )
        if not ap:
            raise PermissionError(f"no approval for {item_id} version {version}")
    db.execute("UPDATE content_items SET state='published' WHERE id=?", (item_id,))
    backend_app.log_audit(
        actor, "publish", "content_item", item_id, f"version={version}"
    )
    return {"item_id": item_id, "state": "published"}


def main():
    import argparse

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("import")
    pi.add_argument("dir")
    pe = sub.add_parser("export")
    pe.add_argument("dir")
    pv = sub.add_parser("validate")
    pv.add_argument("dir")
    args = parser.parse_args()
    bundle = load_dir(args.dir)
    if args.cmd == "validate":
        errs = validate(bundle)
        if errs:
            for e in errs:
                print(e)
            sys.exit(1)
        print("ok")
        return
    if args.cmd == "import":
        print(import_bundle(bundle, actor="cli"))
        return
    if args.cmd == "export":
        export_dir(args.dir)
        print("exported")
        return


if __name__ == "__main__":
    main()


SEED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "aprende", "content")
DATOS_SEED_PATH = os.path.join(SEED_DIR, "datos.yaml")
SUMMARIES_SEED_PATH = os.path.join(SEED_DIR, "summaries.yaml")
PERSONAS_SEED_PATH = os.path.join(SEED_DIR, "personas.yaml")

def _seed_personas():
    with open(PERSONAS_SEED_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

class InvalidError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("invalid")


class LanguageError(Exception):
    def __init__(self, missing):
        self.missing = missing

class PlaceholderError(Exception):
    def __init__(self, missing):
        self.missing = missing

class NoDraftError(Exception):
    pass

class NoVersionError(Exception):
    pass

class ShapeError(ValueError):
    pass

def _seed_datos():
    with open(DATOS_SEED_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or []

def _seed_summaries():
    with open(SUMMARIES_SEED_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _kind_of(entry_id):
    if entry_id.startswith("datos:"):
        return "datos"
    if entry_id.startswith("summary:"):
        return "summary"
    if entry_id.startswith("persona:"):
        return "persona"
    return "item"

def _is_legal(kind, entry_id):
    if kind in ("datos", "summary", "persona"):
        return True
    rows = db.query("SELECT legal FROM content_items WHERE id = ?", (entry_id,))
    return bool(rows and rows[0][0])

def _item_body(row):
    # (id, kind, legal, sensitive, character, source_id, answer, version, state, payload_es, payload_en)
    body = {"es": json.loads(row[9]), "en": json.loads(row[10])}
    if row[6] is not None:
        try:
            body["answer"] = json.loads(row[6])
        except Exception:
            body["answer"] = row[6]
    if row[5] is not None:
        body["source"] = row[5]
    return body

def _ensure_item_seed(entry_id):
    rows = db.query("SELECT id, kind, legal, sensitive, character, source_id, answer, version, state, payload_json_es, payload_json_en FROM content_items WHERE id = ?", (entry_id,))
    if not rows:
        return
    r = rows[0]
    existing = db.query("SELECT 1 FROM content_versions WHERE entry_id = ?", (entry_id,))
    if existing:
        return
    body = _item_body(r)
    state = "published" if r[8] == "published" else "review"
    db.execute(
        "INSERT INTO content_versions (entry_id, version, kind, body_json, state, created_by, created_at) VALUES (?,?,?,?,?,?,?)",
        (entry_id, r[7], "item", json.dumps(body, ensure_ascii=False), state, "import", _now()),
    )

def _all_strings_ok(obj):
    if isinstance(obj, str):
        return obj.strip() != ""
    if isinstance(obj, list):
        return all(_all_strings_ok(x) for x in obj)
    if isinstance(obj, dict):
        return all(_all_strings_ok(v) for v in obj.values())
    return True

def missing_languages(body):
    missing = []
    for lang in ("es", "en"):
        if lang not in body:
            missing.append(lang)
            continue
        val = body[lang]
        if isinstance(val, str):
            if val.strip() == "":
                missing.append(lang)
        elif isinstance(val, (dict, list)):
            if not _all_strings_ok(val):
                missing.append(lang)
    return [l for l in ("es", "en") if l in missing]




def _persona_missing_placeholders(entry_id, body):
    required = PLACEHOLDERS.get(entry_id)
    if not required:
        return []
    text = body.get("text") if isinstance(body, dict) else ""
    text = text if isinstance(text, str) else ""
    missing = []
    for ph in required:
        if ph not in text:
            missing.append(ph)
    return missing


def _check_body(entry_id, body):
    if not isinstance(body, dict):
        raise LanguageError(["en"])
    if entry_id in ("persona:shared", "persona:modes.learn", "persona:modes.intake"):
        text = body.get("text")
        if not (isinstance(text, str) and text.strip() != ""):
            raise LanguageError(["en"])
        ph = _persona_missing_placeholders(entry_id, body)
        if ph:
            raise PlaceholderError(ph)
        if set(body.keys()) - {"text"}:
            raise ShapeError("bad body")
    else:
        name = body.get("name")
        if not isinstance(name, dict):
            raise LanguageError(["es", "en"])
        missing = missing_languages(name)
        if missing:
            raise LanguageError(missing)
        persona = body.get("persona")
        if not (isinstance(persona, str) and persona.strip() != ""):
            raise LanguageError(["en"])
        if set(body.keys()) - {"name", "persona"}:
            raise ShapeError("bad body")


def version_errors(entry_id, body):
    kind = _kind_of(entry_id)
    if kind in ("datos", "summary"):
        return []
    rows = db.query("SELECT lesson_id, step_id, kind, legal, sensitive, character FROM content_items WHERE id = ?", (entry_id,))
    if not rows:
        return []
    lesson_id, step_id, item_kind, legal, sensitive, character = rows[0]
    lrows = db.query("SELECT unit, title_es, title_en FROM content_lessons WHERE id = ?", (lesson_id,))
    if lrows:
        unit, title_es, title_en = lrows[0][0], lrows[0][1], lrows[0][2]
    else:
        unit, title_es, title_en = None, None, None
    srows = db.query("SELECT title_es, title_en FROM content_steps WHERE id = ?", (step_id,))
    if srows:
        stitle_es, stitle_en = srows[0][0], srows[0][1]
    else:
        stitle_es, stitle_en = None, None
    src_rows = db.query("SELECT id, kind, cite, url, read_on FROM content_sources ORDER BY id")
    sources = [{"id": r[0], "kind": r[1], "cite": r[2], "url": r[3], "read_on": r[4]} for r in src_rows]
    item = {"id": entry_id, "kind": item_kind, "legal": bool(legal),
            "sensitive": bool(sensitive), "character": character}
    if isinstance(body, dict):
        for k in ("es", "en", "answer", "source"):
            if k in body:
                item[k] = body[k]
    lesson = {"id": lesson_id, "unit": unit, "title": {"es": title_es, "en": title_en}, "steps": []}
    step = {"id": step_id, "title": {"es": stitle_es, "en": stitle_en}, "items": [item]}
    lesson["steps"].append(step)
    bundle = {"sources": sources, "lessons": [lesson]}
    return [e for e in validate(bundle) if entry_id in e]

ITEM_ALLOWED = {"es", "en", "answer", "source"}

PLACEHOLDERS = {
    "persona:shared": ["{name}", "{language}"],
    "persona:modes.learn": ["{explanations}"],
    "persona:modes.intake": ["{question}", "{question_id}"],
}

def _validate_shape(kind, entry_id=None, body=None):
    if not isinstance(body, dict):
        raise ShapeError("body must be object")
    if kind == "item":
        allowed = ITEM_ALLOWED
    elif kind == "persona":
        if entry_id in ("persona:shared", "persona:modes.learn", "persona:modes.intake"):
            allowed = {"text"}
        else:
            allowed = {"name", "persona"}
    else:
        allowed = {"es", "en"}
    for k in body:
        if k not in allowed:
            raise ShapeError("extra key")

def _max_version(entry_id, kind):
    mx = 0
    rows = db.query("SELECT MAX(version) FROM content_versions WHERE entry_id = ?", (entry_id,))
    if rows and rows[0][0] is not None:
        mx = max(mx, rows[0][0])
    if kind == "item":
        rows = db.query("SELECT version FROM content_items WHERE id = ?", (entry_id,))
        if rows and rows[0][0] is not None:
            mx = max(mx, rows[0][0])
    return mx

def _newest_version_row(entry_id):
    rows = db.query("SELECT version, state, body_json, created_by, created_at, submitted_by, submitted_at, published_by, published_at FROM content_versions WHERE entry_id = ? ORDER BY version DESC", (entry_id,))
    if not rows:
        return None
    r = rows[0]
    return {"version": r[0], "state": r[1], "body_json": r[2], "created_by": r[3], "created_at": r[4],
            "submitted_by": r[5], "submitted_at": r[6], "published_by": r[7], "published_at": r[8]}

def _approval(entry_id, version):
    rows = db.query("SELECT attorney, approved_at FROM content_approvals WHERE item_id = ? AND version = ?", (entry_id, version))
    if not rows:
        return None, None
    return rows[0][0], rows[0][1]

def _entry_versions(entry_id):
    rows = db.query("SELECT version, state, body_json, created_by, created_at, submitted_by, submitted_at, published_by, published_at FROM content_versions WHERE entry_id = ? ORDER BY version DESC", (entry_id,))
    out = []
    for r in rows:
        att, at = _approval(entry_id, r[0])
        body = json.loads(r[2])
        out.append({"version": r[0], "state": r[1], "body": body, "created_by": r[3], "created_at": r[4],
                    "submitted_by": r[5], "submitted_at": r[6], "approved_by": att, "approved_at": at,
                    "published_by": r[7], "published_at": r[8], "errors": version_errors(entry_id, body)})
    return out

def _pending_version(entry_id):
    rows = db.query("SELECT version, state FROM content_versions WHERE entry_id = ? AND state IN ('draft','review') ORDER BY version DESC LIMIT 1", (entry_id,))
    if not rows:
        return None
    return {"version": rows[0][0], "state": rows[0][1]}

def _persona_entry_ids():
    data = _seed_personas()
    eids = ["persona:shared", "persona:modes.learn", "persona:modes.intake"]
    for cid in (data.get("characters") or {}):
        eids.append("persona:characters." + str(cid))
    return eids

def _seed_body(entry_id):
    kind = _kind_of(entry_id)
    if kind == "datos":
        qid = entry_id.split(":", 1)[1]
        for q in _seed_datos():
            if q["id"] == qid:
                return {"es": q["es"], "en": q["en"]}
    elif kind == "summary":
        part = entry_id.split(":", 1)[1]
        doc, art = part.rsplit(".", 1)
        for a in _seed_summaries().get(doc, []):
            if a["article"] == int(art):
                return {"es": a["es"], "en": a["en"]}
    elif kind == "persona":
        data = _seed_personas()
        if entry_id == "persona:shared":
            return {"text": data.get("shared")}
        if entry_id == "persona:modes.learn":
            return {"text": (data.get("modes") or {}).get("learn")}
        if entry_id == "persona:modes.intake":
            return {"text": (data.get("modes") or {}).get("intake")}
        if entry_id.startswith("persona:characters."):
            cid = entry_id.split(".", 1)[1]
            ch = (data.get("characters") or {}).get(cid)
            if ch is not None:
                return {"name": ch.get("name"), "persona": ch.get("persona")}
    return None

def _published(entry_id):
    rows = db.query("SELECT version, body_json FROM content_versions WHERE entry_id = ? AND state='published' ORDER BY version DESC LIMIT 1", (entry_id,))
    if rows:
        return rows[0][0], json.loads(rows[0][1])
    return None

def entries(kind):
    if kind not in ("item", "datos", "summary", "persona"):
        raise ShapeError("bad_kind")
    out = []
    if kind == "item":
        rows = db.query("SELECT i.id, i.lesson_id, i.legal, i.version, i.state FROM content_items i ORDER BY i.id")
        for r in rows:
            iid = r[0]
            live_version = r[3] if r[4] == "published" else None
            pending = _pending_version(iid)
            if pending is None and r[4] != "published":
                pending = {"version": r[3], "state": "review"}
            out.append({"entry_id": iid, "kind": "item", "legal": bool(r[2]), "lesson_id": r[1],
                        "live_version": live_version, "pending": pending})
    elif kind == "datos":
        live_versions = {}
        for eid, ver in db.query("SELECT entry_id, MAX(version) FROM content_versions WHERE kind='datos' AND state='published' GROUP BY entry_id"):
            live_versions[eid] = ver
        pending_versions = {}
        for eid, ver, st in db.query("SELECT entry_id, version, state FROM content_versions WHERE kind='datos' AND state IN ('draft','review') ORDER BY version DESC"):
            if eid not in pending_versions:
                pending_versions[eid] = {"version": ver, "state": st}
        for q in _seed_datos():
            eid = "datos:" + q["id"]
            out.append({"entry_id": eid, "kind": "datos", "legal": True, "live_version": live_versions.get(eid, 0),
                        "pending": pending_versions.get(eid)})
    elif kind == "persona":
        live_versions = {}
        for eid, ver in db.query("SELECT entry_id, MAX(version) FROM content_versions WHERE kind='persona' AND state='published' GROUP BY entry_id"):
            live_versions[eid] = ver
        pending_versions = {}
        for eid, ver, st in db.query("SELECT entry_id, version, state FROM content_versions WHERE kind='persona' AND state IN ('draft','review') ORDER BY version DESC"):
            if eid not in pending_versions:
                pending_versions[eid] = {"version": ver, "state": st}
        eids = _persona_entry_ids()
        for eid in eids:
            out.append({"entry_id": eid, "kind": "persona", "legal": True, "live_version": live_versions.get(eid, 0),
                        "pending": pending_versions.get(eid)})
    else:
        live_versions = {}
        for eid, ver in db.query("SELECT entry_id, MAX(version) FROM content_versions WHERE kind='summary' AND state='published' GROUP BY entry_id"):
            live_versions[eid] = ver
        pending_versions = {}
        for eid, ver, st in db.query("SELECT entry_id, version, state FROM content_versions WHERE kind='summary' AND state IN ('draft','review') ORDER BY version DESC"):
            if eid not in pending_versions:
                pending_versions[eid] = {"version": ver, "state": st}
        for doc, arts in _seed_summaries().items():
            for a in arts:
                eid = f"summary:{doc}.{a['article']}"
                out.append({"entry_id": eid, "kind": "summary", "legal": True, "live_version": live_versions.get(eid, 0),
                            "pending": pending_versions.get(eid)})
    return out

def entry(entry_id):
    kind = _kind_of(entry_id)
    legal = _is_legal(kind, entry_id)
    if kind == "item":
        _ensure_item_seed(entry_id)
        rows = db.query("SELECT id, kind, legal, sensitive, character, source_id, answer, version, state, payload_json_es, payload_json_en FROM content_items WHERE id = ?", (entry_id,))
        if not rows:
            raise KeyError(entry_id)
        r = rows[0]
        live = None
        if r[8] == "published":
            live = {"version": r[7], "body": _item_body(r)}
        versions = _entry_versions(entry_id)
        return {"entry_id": entry_id, "kind": kind, "legal": legal, "live": live, "versions": versions}
    if kind == "datos":
        qid = entry_id.split(":", 1)[1]
        if qid not in {q["id"] for q in _seed_datos()}:
            raise KeyError(entry_id)
    elif kind == "persona":
        if _seed_body(entry_id) is None:
            raise KeyError(entry_id)
    else:
        part = entry_id.split(":", 1)[1]
        doc, art = part.rsplit(".", 1)
        if doc not in _seed_summaries():
            raise KeyError(entry_id)
    pub = _published(entry_id)
    if pub is not None:
        ver, body = pub
        live = {"version": ver, "body": body}
    else:
        sb = _seed_body(entry_id)
        if sb is None:
            raise KeyError(entry_id)
        live = {"version": 0, "body": sb}
    versions = _entry_versions(entry_id)
    return {"entry_id": entry_id, "kind": kind, "legal": legal, "live": live, "versions": versions}

def save_draft(entry_id, body, actor):
    kind = _kind_of(entry_id)
    _validate_shape(kind, entry_id, body)
    if kind == "item":
        if not db.query("SELECT 1 FROM content_items WHERE id = ?", (entry_id,)):
            raise KeyError(entry_id)
    else:
        entry(entry_id)
    with db.transaction():
        if kind == "item":
            _ensure_item_seed(entry_id)
        mx = _max_version(entry_id, kind)
        new_ver = mx + 1
        newest = _newest_version_row(entry_id)
        if newest is not None and newest["state"] == "draft":
            db.execute("UPDATE content_versions SET body_json = ? WHERE entry_id = ? AND version = ?",
                       (json.dumps(body, ensure_ascii=False), entry_id, newest["version"]))
            ver = newest["version"]
        else:
            if newest is not None and newest["state"] == "review":
                db.execute("UPDATE content_versions SET state = 'superseded' WHERE entry_id = ? AND version = ?",
                           (entry_id, newest["version"]))
            db.execute(
                "INSERT INTO content_versions (entry_id, version, kind, body_json, state, created_by, created_at) VALUES (?,?,?,?,?,?,?)",
                (entry_id, new_ver, kind, json.dumps(body, ensure_ascii=False), "draft", actor, _now()),
            )
            ver = new_ver
        backend_app.log_audit(actor, "content_draft", "content", entry_id, f"version={ver}")
    return {"entry_id": entry_id, "version": ver, "state": "draft"}

def submit(entry_id, actor):
    kind = _kind_of(entry_id)
    if kind == "item":
        _ensure_item_seed(entry_id)
    newest = _newest_version_row(entry_id)
    if newest is None or newest["state"] != "draft":
        raise NoDraftError()
    body = json.loads(newest["body_json"])
    if kind == "persona":
        _check_body(entry_id, body)
    else:
        missing = missing_languages(body)
        if missing:
            raise LanguageError(missing)
        errs = version_errors(entry_id, body)
        if errs:
            raise InvalidError(errs)
    with db.transaction():
        db.execute("UPDATE content_versions SET state='review', submitted_by=?, submitted_at=? WHERE entry_id=? AND version=?",
                   (actor, _now(), entry_id, newest["version"]))
        backend_app.log_audit(actor, "content_submit", "content", entry_id, f"version={newest['version']}")
    return {"entry_id": entry_id, "version": newest["version"], "state": "review"}

def _publish_transition(entry_id, version, actor):
    rows = db.query("SELECT state, body_json, kind FROM content_versions WHERE entry_id = ? AND version = ?", (entry_id, version))
    if not rows:
        raise NoVersionError()
    state, body_json, kind = rows[0][0], rows[0][1], rows[0][2]
    if state not in ("draft", "review"):
        raise NoVersionError()
    body = json.loads(body_json)
    if entry_id.startswith("persona:"):
        _check_body(entry_id, body)
    else:
        missing = missing_languages(body)
        if missing:
            raise LanguageError(missing)
        errs = version_errors(entry_id, body)
        if errs:
            raise InvalidError(errs)
    pending = _pending_version(entry_id)
    if pending is None or pending["version"] != version:
        raise NoVersionError()
    db.execute("UPDATE content_versions SET state='superseded' WHERE entry_id = ? AND state='published' AND version <> ?",
               (entry_id, version))
    db.execute("UPDATE content_versions SET state='published', published_by=?, published_at=? WHERE entry_id = ? AND version = ?",
               (actor, _now(), entry_id, version))
    if kind == "item":
        answer = json.dumps(body["answer"], ensure_ascii=False) if "answer" in body else None
        db.execute("UPDATE content_items SET payload_json_es=?, payload_json_en=?, answer=?, source_id=?, version=?, state='published' WHERE id=?",
                   (json.dumps(body["es"], ensure_ascii=False), json.dumps(body["en"], ensure_ascii=False), answer,
                    body.get("source"), version, entry_id))
    return body

def approve_version(entry_id, version, attorney):
    kind = _kind_of(entry_id)
    if kind == "item":
        _ensure_item_seed(entry_id)
    rows = db.query("SELECT state FROM content_versions WHERE entry_id = ? AND version = ?", (entry_id, version))
    if not rows or rows[0][0] != "review":
        raise NoVersionError()
    with db.transaction():
        _publish_transition(entry_id, version, attorney)
        existing = db.query("SELECT version FROM content_approvals WHERE item_id=? AND version=?", (entry_id, version))
        if existing:
            db.execute("UPDATE content_approvals SET attorney=?, approved_at=? WHERE item_id=? AND version=?", (attorney, _now(), entry_id, version))
        else:
            db.execute("INSERT INTO content_approvals (item_id, version, attorney, approved_at) VALUES (?,?,?,?)", (entry_id, version, attorney, _now()))
        backend_app.log_audit(attorney, "content_approve", "content", entry_id, f"version={version}")
    approved_at = db.query("SELECT approved_at FROM content_approvals WHERE item_id=? AND version=?", (entry_id, version))[0][0]
    return {"entry_id": entry_id, "version": version, "state": "published", "approved_by": attorney, "approved_at": approved_at}

def publish_version(entry_id, version, actor):
    kind = _kind_of(entry_id)
    legal = _is_legal(kind, entry_id)
    if legal:
        raise PermissionError("attorney_approval_required")
    rows = db.query("SELECT state FROM content_versions WHERE entry_id = ? AND version = ?", (entry_id, version))
    if not rows or rows[0][0] not in ("draft", "review"):
        raise NoVersionError()
    with db.transaction():
        if kind == "item":
            _ensure_item_seed(entry_id)
        _publish_transition(entry_id, version, actor)
        backend_app.log_audit(actor, "content_publish", "content", entry_id, f"version={version}")
    return {"entry_id": entry_id, "version": version, "state": "published"}

def live_entries(kind):
    out = {}
    if kind == "datos":
        published = {r[0]: r[1] for r in db.query("SELECT entry_id, body_json FROM content_versions WHERE kind='datos' AND state='published'")}
        for q in _seed_datos():
            eid = "datos:" + q["id"]
            out[eid] = json.loads(published[eid]) if eid in published else {"es": q["es"], "en": q["en"]}
        return out
    if kind == "summary":
        published = {r[0]: r[1] for r in db.query("SELECT entry_id, body_json FROM content_versions WHERE kind='summary' AND state='published'")}
        for doc, arts in _seed_summaries().items():
            for a in arts:
                eid = f"summary:{doc}.{a['article']}"
                out[eid] = json.loads(published[eid]) if eid in published else {"es": a["es"], "en": a["en"]}
        return out
    if kind == "persona":
        published = {r[0]: r[1] for r in db.query("SELECT entry_id, body_json FROM content_versions WHERE kind='persona' AND state='published'")}
        for eid in _persona_entry_ids():
            seed = _seed_body(eid)
            out[eid] = json.loads(published[eid]) if eid in published else seed
        return out
    return out

def preview(entry_id, version, lang):
    kind = _kind_of(entry_id)
    if version == 0:
        if kind == "item":
            rows = db.query("SELECT id, kind, legal, sensitive, character, source_id, answer, version, state, payload_json_es, payload_json_en FROM content_items WHERE id = ?", (entry_id,))
            if not rows:
                raise KeyError(entry_id)
            body = _item_body(rows[0])
        else:
            body = _seed_body(entry_id)
            if body is None:
                raise KeyError(entry_id)
    else:
        rows = db.query("SELECT body_json FROM content_versions WHERE entry_id = ? AND version = ?", (entry_id, version))
        if not rows:
            raise KeyError("version:"+str(version))
        body = json.loads(rows[0][0])
    if kind == "item":
        rows = db.query("SELECT kind, character, lesson_id FROM content_items WHERE id = ?", (entry_id,))
        if not rows:
            raise KeyError(entry_id)
        item_kind, char, lesson_id = rows[0][0], rows[0][1], rows[0][2]
        if char is None:
            lrows = db.query("SELECT character FROM content_lessons WHERE id = ?", (lesson_id,))
            char = lrows[0][0] if lrows else None
        payload = body.get("es" if lang == "es" else "en", {})
        out_item = {"id": entry_id, "kind": item_kind}
        if char:
            out_item["character"] = char
        for k, v in payload.items():
            if k not in ("explain",):
                out_item[k] = v
        out_item.pop("answer", None)
        explain = payload.get("explain")
        return {"character": char, "item": out_item, "explain": explain}
    else:
        text = body.get("es" if lang == "es" else "en")
        return {"character": None, "text": text}

def _item_kind(entry_id):
    rows = db.query("SELECT kind FROM content_items WHERE id = ?", (entry_id,))
    if not rows:
        raise KeyError(entry_id)
    return rows[0][0]
