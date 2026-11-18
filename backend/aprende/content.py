
import json, os, sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path: sys.path.insert(0, REPO_ROOT)
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path: sys.path.insert(0, BACKEND)

import db, yaml
try:
    from carbon_intake import VERIFIED, questions as _ci_questions
except Exception:
    from carbon_intake.drafting import VERIFIED
    from carbon_intake.conversation import questions as _ci_questions
try:
    from app import log_audit
except Exception:
    def log_audit(actor, action, entity, entity_id, detail=""): pass

UNITS = {"will","trust","ahcd","poa","final","bonus"}
KINDS = {"explain","choice","scenario","listen","truefalse","match","order"}
SOURCE_KINDS = {"probate_code","courts_selfhelp"}
LIST_FIELDS = {"options","pairs","steps"}

def _qids():
    qs = _ci_questions("guion-plan")
    if isinstance(qs, tuple): qs = qs[0]
    return {q["id"] for q in qs}

def load_dir(path):
    sources=[]; sources_path=os.path.join(path,"sources.yaml")
    if os.path.exists(sources_path):
        with open(sources_path,encoding="utf-8") as f:
            data=yaml.safe_load(f)
            if data: sources=data
    lessons=[]; ld=os.path.join(path,"lessons")
    if os.path.isdir(ld):
        for name in sorted(os.listdir(ld)):
            if not name.endswith((".yaml",".yml")): continue
            with open(os.path.join(ld,name),encoding="utf-8") as f:
                data=yaml.safe_load(f)
                if data: lessons.append(data)
    lessons.sort(key=lambda x: x.get("id",""))
    return {"sources":sources,"lessons":lessons}

_MISSING=object()

def validate(bundle):
    errors=[]; sources=bundle.get("sources",[]) or []; lessons=bundle.get("lessons",[]) or []
    source_ids={}
    for s in sources:
        if not isinstance(s,dict): continue
        sid=s.get("id")
        if sid in source_ids: errors.append(f"duplicate source id {sid}")
        source_ids[sid]=s
    all_ids=set(source_ids.keys()); qids=_qids(); days={}
    for lesson in lessons:
        if not isinstance(lesson,dict): continue
        lid=lesson.get("id")
        if lid in all_ids: errors.append(f"duplicate id {lid}")
        all_ids.add(lid)
        unit=lesson.get("unit")
        if unit not in UNITS: errors.append(f"{lid}: unknown unit {unit}")
        day=lesson.get("day")
        if day is not None:
            if day in days: errors.append(f"duplicate day {day}")
            days[day]=lid
        for d in lesson.get("datos") or []:
            if d not in qids: errors.append(f"{lid}: unknown datos id {d}")
        title=lesson.get("title") or {}
        if not isinstance(title,dict) or "es" not in title or "en" not in title: errors.append(f"{lid}: title missing es/en")
        for step in lesson.get("steps") or []:
            if not isinstance(step,dict): continue
            sid=step.get("id")
            if sid in all_ids: errors.append(f"duplicate id {sid}")
            all_ids.add(sid)
            if not (isinstance(sid,str) and sid.startswith(str(lid)+".")): errors.append(f"{sid}: id must start with {lid}.")
            stitle=step.get("title") or {}
            if not isinstance(stitle,dict) or "es" not in stitle or "en" not in stitle: errors.append(f"{sid}: title missing es/en")
            for it in step.get("items") or []:
                if not isinstance(it,dict): continue
                iid=it.get("id")
                if iid in all_ids: errors.append(f"duplicate id {iid}")
                all_ids.add(iid)
                if not (isinstance(iid,str) and iid.startswith(str(lid)+".")): errors.append(f"{iid}: id must start with {lid}.")
                kind=it.get("kind")
                if kind not in KINDS: errors.append(f"{iid}: unknown kind {kind}")
                es=it.get("es"); en=it.get("en")
                if not isinstance(es,dict) or not isinstance(en,dict):
                    errors.append(f"{iid}: missing es/en"); continue
                if set(es.keys())!=set(en.keys()): errors.append(f"{iid}: es/en fields differ")
                for lf in LIST_FIELDS:
                    if lf in es and lf in en:
                        if isinstance(es[lf],list) and isinstance(en[lf],list):
                            if len(es[lf])!=len(en[lf]): errors.append(f"{iid}: list lengths differ")
                legal=bool(it.get("legal",False)); src=it.get("source")
                if legal:
                    if src is None: errors.append(f"{iid}: legal item missing source")
                    elif src not in source_ids: errors.append(f"{iid}: unknown source {src}")
                answer=it.get("answer",_MISSING); has_answer=answer is not _MISSING
                if kind in ("choice","scenario","listen"):
                    if not has_answer: errors.append(f"{iid}: missing answer")
                    else:
                        if isinstance(answer,bool) or not isinstance(answer,int): errors.append(f"{iid}: answer must be int")
                        else:
                            opts=es.get("options") if isinstance(es,dict) else None
                            n=len(opts) if isinstance(opts,list) else 0
                            if n and not (0<=answer<n): errors.append(f"{iid}: answer out of range {answer}")
                elif kind=="truefalse":
                    if not has_answer: errors.append(f"{iid}: missing answer")
                    elif not isinstance(answer,bool): errors.append(f"{iid}: truefalse needs a bool")
                else:
                    if has_answer: errors.append(f"{iid}: {kind} has no answer")
    for s in sources:
        if not isinstance(s,dict): continue
        sid=s.get("id"); kind=s.get("kind")
        if kind not in SOURCE_KINDS: errors.append(f"{sid}: unknown source kind {kind}")
        cite=s.get("cite"); url=s.get("url","")
        if kind=="probate_code":
            if str(cite) not in VERIFIED: errors.append(f"{sid}: cite {cite} not on VERIFIED")
        elif kind=="courts_selfhelp":
            if "selfhelp.courts.ca.gov" not in str(url): errors.append(f"{sid}: url must be on selfhelp.courts.ca.gov")
    return errors

def _now(): return datetime.now(timezone.utc).isoformat()

def import_bundle(bundle, actor=""):
    errs=validate(bundle)
    if errs: raise ValueError("; ".join(errs))
    sources=bundle.get("sources",[]) or []; lessons=bundle.get("lessons",[]) or []
    for s in sources:
        existing=db.query("SELECT id FROM content_sources WHERE id = ?",(s["id"],))
        if existing:
            db.execute("UPDATE content_sources SET kind=?,cite=?,url=?,read_on=? WHERE id=?",(s["kind"],s["cite"],s["url"],s.get("read_on"),s["id"]))
        else:
            db.execute("INSERT INTO content_sources (id,kind,cite,url,read_on) VALUES (?,?,?,?,?)",(s["id"],s["kind"],s["cite"],s["url"],s.get("read_on")))
    items_created=0; items_changed=0
    for li,lesson in enumerate(lessons):
        lid=lesson["id"]; existing_lesson=db.query("SELECT id FROM content_lessons WHERE id = ?",(lid,))
        datos=lesson.get("datos")
        if existing_lesson:
            db.execute("UPDATE content_lessons SET unit=?,day=?,character=?,sensitive=?,datos=?,title_es=?,title_en=?,position=? WHERE id=?",(lesson["unit"],lesson.get("day"),lesson.get("character"),1 if lesson.get("sensitive") else 0,json.dumps(datos) if datos is not None else None,(lesson.get("title") or {}).get("es"),(lesson.get("title") or {}).get("en"),li,lid))
        else:
            db.execute("INSERT INTO content_lessons (id,unit,day,character,sensitive,datos,title_es,title_en,position) VALUES (?,?,?,?,?,?,?,?,?)",(lid,lesson["unit"],lesson.get("day"),lesson.get("character"),1 if lesson.get("sensitive") else 0,json.dumps(datos) if datos is not None else None,(lesson.get("title") or {}).get("es"),(lesson.get("title") or {}).get("en"),li))
        for si,step in enumerate(lesson.get("steps") or []):
            sid=step["id"]; existing_step=db.query("SELECT id FROM content_steps WHERE id = ?",(sid,))
            if existing_step:
                db.execute("UPDATE content_steps SET lesson_id=?,position=?,title_es=?,title_en=? WHERE id=?",(lid,si,(step.get("title") or {}).get("es"),(step.get("title") or {}).get("en"),sid))
            else:
                db.execute("INSERT INTO content_steps (id,lesson_id,position,title_es,title_en) VALUES (?,?,?,?,?)",(sid,lid,si,(step.get("title") or {}).get("es"),(step.get("title") or {}).get("en")))
            for ii,it in enumerate(step.get("items") or []):
                iid=it["id"]; payload_es={k:v for k,v in (it.get("es") or {}).items()}; payload_en={k:v for k,v in (it.get("en") or {}).items()}
                has_answer="answer" in it; answer_val=it.get("answer") if has_answer else None
                legal=1 if it.get("legal") else 0; sensitive=1 if it.get("sensitive") else 0; char=it.get("character"); source_id=it.get("source")
                new_es_json=json.dumps(payload_es,ensure_ascii=False); new_en_json=json.dumps(payload_en,ensure_ascii=False); answer_json=json.dumps(answer_val,ensure_ascii=False) if has_answer else None
                version_existing=db.query("SELECT version,kind,legal,sensitive,character,source_id,answer,payload_json_es,payload_json_en FROM content_items WHERE id = ?",(iid,))
                if not version_existing:
                    db.execute("INSERT INTO content_items (id,lesson_id,step_id,position,kind,legal,sensitive,character,source_id,answer,version,state,payload_json_es,payload_json_en) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(iid,lid,sid,ii,it["kind"],legal,sensitive,char,source_id,answer_json,1,"draft",new_es_json,new_en_json))
                    items_created+=1
                else:
                    (ver,okind,olegal,osens,ochar,osrc,oans,oes,oen)=version_existing[0]
                    changed=(okind!=it["kind"] or olegal!=legal or osens!=sensitive or ochar!=char or osrc!=source_id or oans!=answer_json or oes!=new_es_json or oen!=new_en_json)
                    if changed:
                        db.execute("UPDATE content_items SET lesson_id=?,step_id=?,position=?,kind=?,legal=?,sensitive=?,character=?,source_id=?,answer=?,version=?,state=?,payload_json_es=?,payload_json_en=? WHERE id=?",(lid,sid,ii,it["kind"],legal,sensitive,char,source_id,answer_json,ver+1,"draft",new_es_json,new_en_json,iid))
                        items_changed+=1
                    else:
                        db.execute("UPDATE content_items SET lesson_id=?,step_id=?,position=? WHERE id=?",(lid,sid,ii,iid))
    log_audit(actor,"import","content","bundle",f"created={items_created} changed={items_changed}")
    return {"items_created":items_created,"items_changed":items_changed}

def export_dir(path):
    os.makedirs(path,exist_ok=True); lessons_dir=os.path.join(path,"lessons"); os.makedirs(lessons_dir,exist_ok=True)
    src_rows=db.query("SELECT id,kind,cite,url,read_on FROM content_sources ORDER BY id")
    sources=[{"id":r[0],"kind":r[1],"cite":r[2],"url":r[3],"read_on":r[4]} for r in src_rows]
    with open(os.path.join(path,"sources.yaml"),"w",encoding="utf-8") as f:
        yaml.safe_dump(sources,f,sort_keys=False,allow_unicode=True,default_flow_style=False)
    lesson_rows=db.query("SELECT id,unit,day,character,sensitive,datos,title_es,title_en FROM content_lessons ORDER BY position,id")
    for lr in lesson_rows:
        lid=lr[0]; lesson={"id":lid,"unit":lr[1]}
        lesson["day"]=lr[2]
        if lr[3] is not None: lesson["character"]=lr[3]
        lesson["sensitive"]=bool(lr[4])
        if lr[5] is not None:
            try: lesson["datos"]=json.loads(lr[5])
            except Exception: lesson["datos"]=lr[5]
        lesson["title"]={"es":lr[6],"en":lr[7]}
        step_rows=db.query("SELECT id,title_es,title_en FROM content_steps WHERE lesson_id=? ORDER BY position,id",(lid,))
        steps=[]
        for sr in step_rows:
            sid=sr[0]; step={"id":sid,"title":{"es":sr[1],"en":sr[2]}}
            item_rows=db.query("SELECT id,kind,legal,sensitive,character,source_id,answer,position,payload_json_es,payload_json_en FROM content_items WHERE step_id=? ORDER BY position,id",(sid,))
            items=[]
            for ir in item_rows:
                iid=ir[0]; item={"id":iid,"kind":ir[1]}
                if ir[2]: item["legal"]=True
                if ir[3]: item["sensitive"]=True
                if ir[4] is not None: item["character"]=ir[4]
                if ir[5] is not None: item["source"]=ir[5]
                if ir[6] is not None:
                    try: item["answer"]=json.loads(ir[6])
                    except Exception: item["answer"]=ir[6]
                item["es"]=json.loads(ir[8]); item["en"]=json.loads(ir[9]); items.append(item)
            step["items"]=items; steps.append(step)
        lesson["steps"]=steps
        with open(os.path.join(lessons_dir,f"{lid}.yaml"),"w",encoding="utf-8") as f:
            yaml.safe_dump(lesson,f,sort_keys=False,allow_unicode=True,default_flow_style=False)

def approve(item_id, attorney):
    rows=db.query("SELECT version FROM content_items WHERE id = ?",(item_id,))
    if not rows: raise ValueError(f"unknown item {item_id}")
    version=rows[0][0]
    existing=db.query("SELECT version FROM content_approvals WHERE item_id=? AND version=?",(item_id,version))
    if existing:
        db.execute("UPDATE content_approvals SET attorney=?,approved_at=? WHERE item_id=? AND version=?",(attorney,_now(),item_id,version))
    else:
        db.execute("INSERT INTO content_approvals (item_id,version,attorney,approved_at) VALUES (?,?,?,?)",(item_id,version,attorney,_now()))
    log_audit(attorney,"approve","content_item",item_id,f"version={version}")
    return {"item_id":item_id,"version":version}

def publish(item_id, actor):
    rows=db.query("SELECT version,legal FROM content_items WHERE id = ?",(item_id,))
    if not rows: raise ValueError(f"unknown item {item_id}")
    version,legal=rows[0][0],bool(rows[0][1])
    if legal:
        ap=db.query("SELECT version FROM content_approvals WHERE item_id=? AND version=?",(item_id,version))
        if not ap: raise PermissionError(f"no approval for {item_id} version {version}")
    db.execute("UPDATE content_items SET state='published' WHERE id=?",(item_id,))
    log_audit(actor,"publish","content_item",item_id,f"version={version}")
    return {"item_id":item_id,"state":"published"}

def main():
    import argparse
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="cmd",required=True)
    pi=sub.add_parser("import"); pi.add_argument("dir")
    pe=sub.add_parser("export"); pe.add_argument("dir")
    pv=sub.add_parser("validate"); pv.add_argument("dir")
    args=parser.parse_args()
    bundle=load_dir(args.dir)
    if args.cmd=="validate":
        errs=validate(bundle)
        if errs:
            for e in errs: print(e)
            sys.exit(1)
        print("ok"); return
    if args.cmd=="import":
        print(import_bundle(bundle,actor="cli")); return
    if args.cmd=="export":
        export_dir(args.dir); print("exported"); return

if __name__=="__main__": main()
