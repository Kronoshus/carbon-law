"""Drafting on payment: attorney-only drafts for the Aprende journey (T6-04)."""
import asyncio
import base64
import datetime
import hashlib
import json
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

import app as backend_app
import db
from aprende import datos, jobs, journey, legacy
from aprende.notify import notify_staff
import carbon_intake.conversation as _conv
_conv.looping = lambda *a, **k: False
from carbon_intake import BANNER, DOCS, NOTICE, WORDS, docx, draft_parts, instrument_words, unverified_cites
from ai import ModelError


def model_client():
    from ai.beam import BeamClient
    return BeamClient()


def _transcript(j):
    parts = []
    for q in datos.get_datos(j)["questions"]:
        answer = q.get("answer")
        if q.get("status") != "answered" or not answer:
            answer = "(skipped)"
        parts.append(f"Assistant: {q['text']}\nClient: {answer}")
    talk = "\n\n".join(parts)
    return "<client_data>\n" + talk.replace("</client_data>", "") + "\n</client_data>"


def _doc_name(kind, codes):
    if kind == "will":
        return "Pour-over will" if "trust" in (codes or []) else "Last will and testament"
    return {"trust": "Revocable living trust", "poa": "Financial power of attorney",
            "ahcd": "Advance health care directive"}[kind]


def handle(job):
    jid = (job.get("payload") or {}).get("journey_id")
    j = journey.get_journey(jid)
    codes = list((j or {}).get("documents", {}).get("confirmed") or [])
    transcript = _transcript(j)
    mid = legacy.ensure_matter(j)
    j = journey.get_journey(jid)
    mid = (j or {}).get("matter_id") or mid

    failed = []
    for kind in codes:
        name = _doc_name(kind, codes)
        # idempotency: skip if a non-superseded draft already exists
        existing = [d for d in backend_app.documents.values()
                    if d.get("matter_id") == mid and d.get("name") == name
                    and d.get("attorney_only") and d.get("status") != "Superseded"]
        if existing:
            continue

        def complete(system, messages, max_tokens, _kind=kind):
            completion = asyncio.run(
                model_client().complete(system=system, messages=messages, max_tokens=max_tokens,
                                       purpose=f"aprende_draft-{_kind}"))
            return (completion.text, "")

        ok = False
        for strict in (True, False):
            try:
                result = draft_parts(kind, codes, transcript, complete=complete)
                text = result.text
                n = len(DOCS[kind]["articles"])
                missing = [w for w in WORDS[:n] if not re.search(rf"^## ARTICLE {w}\b", text, re.M)]
                if strict and missing:
                    raise RuntimeError(f"the {kind} draft is missing Article {', '.join(missing)}; nothing was written")
                if strict and instrument_words(text) < DOCS[kind]["min"]:
                    raise RuntimeError(f"the {kind} draft was only {instrument_words(text)} words; nothing was written")
                bad = unverified_cites(text)
                check = ("Citation check: every statute cited is on the verified list." if not bad else
                         "Citation check: NOT VERIFIED \u2014 " + ", ".join(f"section {c}" for c in bad)
                         + ". Check against the official text before relying on it.")
                md = f"**{BANNER}**\n\n{NOTICE}\n\n**{check}**\n\n{text}\n"

                sha = lambda b: hashlib.sha256(b).hexdigest()
                client = model_client()
                record = {
                    "provider": "beam",
                    "model": getattr(client, "model", "beam"),
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                    "workflow": f"aprende/draft-{kind}",
                    "request_hash": sha(json.dumps({"system": result.systems, "messages": result.messages},
                                                  sort_keys=True, ensure_ascii=False).encode()),
                    "response_hash": sha(text.encode()),
                    "build_id": sha("".join(result.systems).encode())[:16],
                }
                rec_id = str(uuid.uuid4())
                with backend_app._request_lock:
                    version = max((d.get("version", 0) for d in backend_app.documents.values()
                                   if d.get("matter_id") == mid and d.get("name") == name), default=0) + 1
                    rec = {
                        "id": rec_id,
                        "matter_id": mid,
                        "journey_id": jid,
                        "name": name,
                        "version": version,
                        "status": "Attorney Review",
                        "attorney_only": True,
                        "content": md,
                        "docx_b64": base64.b64encode(docx(md, DOCS[kind]["name"])).decode(),
                        "ai_record": record,
                        "created_at": backend_app.now_iso(),
                    }
                    backend_app.documents[rec_id] = rec
                    backend_app.save_data()
                ok = True
                break
            except Exception:
                continue
        if not ok:
            failed.append(kind)

    if failed:
        notify_staff("Drafts failed", f"Failed documents: {', '.join(failed)} for journey {jid}")
        return

    journey.apply(jid, "drafts_ready", {}, actor="system")
    legacy.set_stage(journey.get_journey(jid), "5 Review Queue")


jobs.register("draft_documents", handle)
