"""Drafting on payment (T6-04): a first draft of each paid document, for the attorney only.

It follows the prototype's draft()/draft_all() (avatar-intake/server.py): the drafter prompts and their checks live in
carbon_intake; a strict try (every article, full length), then one lenient retry; a malformed or looping reply writes nothing."""
import asyncio
import base64
import datetime
import hashlib
import json
import re

import app as backend_app
from ai import ModelError
from aprende import datos, jobs, journey, legacy
from aprende.notify import notify_staff
from carbon_intake import BANNER, DOCS, NOTICE, UNTRUSTED, WORDS, docx, draft_parts, instrument_words, unverified_cites

NAMES = {"trust": "Revocable living trust", "poa": "Financial power of attorney", "ahcd": "Advance health care directive"}


def model_client():
    from ai.beam import BeamClient
    return BeamClient()


def name(kind, codes):
    if kind == "will":
        return "Pour-over will" if "trust" in codes else "Last will and testament"
    return NAMES[kind]


def transcript(j):
    """The client's own answers, fenced: they are data, never instructions (UNTRUSTED is in every drafter prompt)."""
    lines = [f"Assistant: {q['text']}\nClient: {q['answer'] if q['status'] == 'answered' else '(skipped)'}"
             for q in datos.get_datos(j, "en")["questions"]]
    return "<client_data>\n" + "\n\n".join(lines).replace("</client_data>", "") + "\n</client_data>"


def draft(kind, codes, talk, strict):
    """One document's markdown and AI record, or RuntimeError/ModelError when the reply is not usable."""
    client = model_client()

    def complete(system, messages, max_tokens):
        reply = asyncio.run(client.complete(system=system, messages=messages, max_tokens=max_tokens,
                                                    purpose=f"aprende_draft-{kind}"))
        return reply.text, ""

    result = draft_parts(kind, codes, talk, complete=complete)
    text = result.text
    missing = [w for w in WORDS[:len(DOCS[kind]["articles"])] if not re.search(rf"^## ARTICLE {w}\b", text, re.M)]
    if strict and missing:
        raise RuntimeError(f"missing Article {', '.join(missing)}")
    if strict and instrument_words(text) < DOCS[kind]["min"]:
        raise RuntimeError(f"only {instrument_words(text)} words")
    bad = unverified_cites(text, DOCS[kind]["cites"])
    check = ("Citation check: every statute cited is on the verified list." if not bad else
             "Citation check: NOT VERIFIED \u2014 " + ", ".join(f"section {c}" for c in bad)
             + ". Check against the official text before relying on it.")
    md = f"**{BANNER}**\n\n{NOTICE}\n\n**{check}**\n\n{text}\n"
    sha = lambda b: hashlib.sha256(b).hexdigest()
    record = {"provider": "reflection", "model": client.model,
              "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
              "workflow": f"aprende/draft-{kind}",
              "request_hash": sha(json.dumps({"system": result.systems, "messages": result.messages}, sort_keys=True, ensure_ascii=False).encode()),
              "response_hash": sha(text.encode()), "build_id": sha("".join(result.systems).encode())[:16]}
    return md, record


def handle(job):
    jid = job["payload"]["journey_id"]
    j = journey.get_journey(jid)
    codes, talk, failed = j["documents"]["confirmed"], transcript(j), []
    for kind in codes:
        title = name(kind, codes)
        if any(d.get("matter_id") == j["matter_id"] and d.get("name") == title and d.get("status") != "Superseded"
               for d in backend_app.documents.values()):
            continue                                                  # already drafted (the job ran before)
        for strict in (True, False):
            try:
                md, record = draft(kind, codes, talk, strict)
            except (RuntimeError, ModelError):
                continue
            legacy.add_document_version(j["matter_id"], jid, title, {
                "status": "Attorney Review", "attorney_only": True, "content": md, "ai_record": record,
                "docx_b64": base64.b64encode(docx(md, DOCS[kind]["name"])).decode()})
            break
        else:
            failed.append(kind)
    if failed:
        notify_staff("Borradores fallidos", f"Expediente {jid}: no se pudo redactar {', '.join(failed)}. Revise y vuelva a intentar.")
        return
    journey.apply(jid, "drafts_ready", {}, actor="system")
    legacy.set_stage(journey.get_journey(jid), "5 Review Queue")


jobs.register("draft_documents", handle)
