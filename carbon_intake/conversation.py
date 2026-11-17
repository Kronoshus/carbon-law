"""Conversation logic for carbon_intake (stdlib only)."""
import json, re
from pathlib import Path

GUIONES = Path(__file__).parent / "guiones"

from .drafting import DOCS


def questions(guion, docs=()):
    """-> (steps, [(id, question)]) the model must cover: the script's questions after consent and the conflict check.
    A step tagged "doc" belongs to those documents and is asked only once the client has chosen one of them."""
    if not re.fullmatch(r"[a-z-]{1,40}", guion or ""):
        raise ValueError("bad guion")
    steps = json.loads((GUIONES / f"{guion}.json").read_text(encoding="utf-8"))
    return steps, [(s["id"], s["say"]) for s in steps if s.get("ask") and not s.get("consent") and not s.get("conflict")
                   and (not s.get("doc") or set(s["doc"]) & set(docs))]



def system_prompt(guion, lang, covered=(), docs=(), avatar="avatar"):
    """The script file is the model's source: its explanations and the questions it must cover.
    covered = ids already dealt with; the prompt names the next open question so the model always steers back to it.
    docs = documents chosen so far, for a script that lets the client choose (a step marked "choose")."""
    steps, qs = questions(guion, docs)
    explain = "\n".join("- " + s["say"] for s in steps if not s.get("ask"))
    of = {s["id"]: f" (for the {', '.join(DOCS[k]['say'] for k in s['doc'])})" for s in steps if s.get("doc")}
    ask = "\n".join(f"- [{i}]{of.get(i, '')} {q}" for i, q in qs)
    choose = "" if not any(s.get("choose") for s in steps) else f"""
Documents: this office drafts four documents, with these codes: {'; '.join(f'{c} = {k["say"]}' for c, k in DOCS.items())}. \
Before any other question, say in one short sentence each what the four documents are, then ask which of them the client wants. If the client cannot decide even after a short \
explanation, say the attorney will advise them and that you will ask about all four so he has what he needs. From then \
on, after the [DONE: ...] tag also write [DOCS: ...] with the codes of the documents chosen, for example [DOCS: will, poa]; \
change it if the client later adds or drops a document. The questions for each chosen document appear in the list below \
once it is chosen. Go through one document at a time, in the order of the list, and tell the client in a few words \
each time you move on to the next document.
Documents chosen so far: {', '.join(docs) or 'not chosen yet'}.
"""
    open_ = [(i, q) for i, q in qs if i not in covered]
    agenda = (f"Already covered: {', '.join(i for i, _ in qs if i in covered) or 'nothing yet'}.\n"
              + (f"Still open, in order: {', '.join(i for i, _ in open_)}.\nThe next open question, the one to bring the client "
                 f"back to: [{open_[0][0]}] {open_[0][1]}" if open_ else
                 "Everything is covered: ask if the client has any other questions, then close."))
    return f"""You are the virtual assistant of the law office of attorney Pankaj Raval (Carbon Law Group, Los Angeles), talking by voice with a member of the public on a video call. {'You appear as an animated Day of the Dead calavera, a cheerful decorated skull in a suit; you are not the attorney and not his likeness.' if avatar == 'calavera' else 'You appear as an animated image of the attorney.'}
The client has already been told you are an AI program and not the attorney, has agreed to be recorded, and has given names for the office's conflict-of-interest check, which found no conflict; do not repeat either step.

Speak only {"English" if lang == "en" else "Spanish (usted form)"}. Everything you write is read aloud: plain sentences, no lists, no markdown, no emojis. Keep each turn short, two to four sentences, and ask exactly one question per turn, never two or more. Never repeat a sentence. Do not ask for anything the client has already told you (infer the state from a well-known city or county, such as Santa Ana or Orange County for California, and just confirm it in passing),and do not ask questions that cannot apply (for example shares when there is only one beneficiary). If the client wants to finish before everything is covered, ask only the single most important missing item, then close.The client's words reach you through automatic transcription, so tolerate small errors and ask again if unclear.

Your job:
1. Explain estate planning in simple words and answer the client's general questions about it.
2. Collect the information the attorney needs, by covering every question below in a natural order. Ask for the spelling of a name at most once; the attorney checks names against the recording. Never ask the same question more than twice: if the client does not answer it, does not know, or does not want to answer, move on.
3. When everything is covered and the client has no more questions, thank them, say the office will contact them, and end your last message with [FIN]. Do not close while questions are still open unless the client asks to stop.

Staying on track: the client may tell stories, wander to other topics, or ask you things. Be warm and human: acknowledge what they said in one short sentence (answer a general estate-planning question briefly; for anything else say the office will follow up), then end your turn by bringing them back to the next open question. Every turn ends with a question until you close. If an answer is partial, ask only for the missing piece. If they ask why you need something, explain in one sentence that the attorney needs it to prepare their documents.

Hidden checklist: at the very end of every reply write [DONE: ...] with the ids, separated by commas, of every question now covered (answered, declined, not known, asked twice without an answer, or not applicable). Write [DONE:] if none. This tag is removed before your reply is read aloud.
{choose}
Limits: you give general information, never legal advice about the client's own situation; for that say attorney Raval will answer personally and note the question. Do not quote fees, promise results, or say that a will or trust is done. Never say you are the attorney or a person. Stay on estate planning; for anything else, say the office will follow up. If the client asks to stop or withdraws consent, say goodbye and end with [FIN].

Explanations you may draw on (keep to this content):
{explain}

Questions to cover (id in brackets):
{ask}

Checklist so far:
{agenda}"""



def sentences(text):
    text = re.sub(r"([.?!])(?=[A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d1\u00bf\u00a1])", r"\1 ", text)  # "you?Thank" -> "you? Thank"
    return [x for x in re.split(r"(?<=[.?!])\s+", text.strip()) if x]



def looping(text, times=4):
    """True when the model got stuck repeating itself (seen with Beam: one question 100+ times)."""
    counts = {}
    for x in sentences(text):
        if len(x) > 12:
            counts[x] = counts.get(x, 0) + 1
    return max(counts.values(), default=0) >= times



def spoken(text, limit=220):
    """Guard on what the avatar says aloud, applied outside the model: stop at the first repeated sentence,
    keep only the first question, and cap the length. [FIN] (end of interview) is kept if the model sent it."""
    fin, out, seen, words = "[FIN]" in text, [], set(), 0
    for x in sentences(text.replace("[FIN]", " ")):
        key = re.sub(r"\W+", " ", x).lower().strip()
        if key in seen or (out and words + len(x.split()) > limit):
            break
        out.append(x); seen.add(key); words += len(x.split())
        if "?" in x:  # ponytail: one question per turn; a rhetorical question would also end the turn here
            break
    return " ".join(out) + (" [FIN]" if fin else "")



def checklist(text, covered, ids):
    """-> (text without the [DONE: ...] tag, covered ids). The list only grows: a reply missing the tag keeps the old one."""
    tags = re.findall(r"\[DONE:([^\]]*)\]", text)
    done = set(covered) | ({x.strip() for x in tags[-1].split(",")} if tags else set())
    return re.sub(r"\[DONE:[^\]]*\]", " ", text).strip(), [i for i in ids if i in done]



def chat(guion, lang, messages, covered=(), docs=(), avatar="avatar", *, complete):
    """-> {"text", "reasoning", "covered", "open", "docs"}."""
    steps = questions(guion)[0]
    chooser = next((s["id"] for s in steps if s.get("choose")), None)
    docs = [k for k in DOCS if k in docs]
    msgs = []
    for m in messages:
        if m.get("role") == "assistant":
            msgs.append({"role": "assistant", "content": str(m["content"])[:4000]})
            if m.get("reasoning_content"):
                msgs[-1]["reasoning_content"] = str(m["reasoning_content"])[:50000]
        else:
            msgs.append({"role": "user", "content": str(m["content"])[:4000]})
    res = complete(system_prompt(guion, lang, covered, docs, avatar), msgs, 400)
    text, reasoning = (res[0], res[1]) if isinstance(res, tuple) else (res, "")
    picked = re.findall(r"\[DOCS:([^\]]*)\]", text)
    if picked:
        docs = [k for k in DOCS if k in {x.strip().lower() for x in picked[-1].split(",")}] or docs
    text, covered = checklist(re.sub(r"\[DOCS:[^\]]*\]", " ", text), covered, [s["id"] for s in steps])
    if chooser in covered and not docs:
        docs = list(DOCS)
    qs = questions(guion, docs)[1]
    ids = [i for i, _ in qs]
    said = spoken(text)
    if not said.replace("[FIN]", "").strip():
        left = [q for i, q in qs if i not in covered]
        said = left[0] if left else next((s["say"] for s in reversed(steps) if not s.get("ask")), "") + " [FIN]"
    return {"text": said, "history": said.replace("[FIN]", "").strip() + f" [DONE: {', '.join(covered)}]"
            + (f" [DOCS: {', '.join(docs)}]" if chooser else ""),
            "reasoning": reasoning, "covered": covered, "open": [i for i in ids if i not in covered], "docs": docs}

