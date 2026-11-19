"""Consent classifier (T5-02): port of the prototype's consent() with the phrase table."""
import re


def _rx(phrases):
    parts = sorted(phrases, key=len, reverse=True)
    alt = "|".join(re.escape(p) for p in parts)
    return re.compile(r"(?<!\w)(?:" + alt + r")(?!\w)", re.IGNORECASE | re.UNICODE)


_REFUSAL_PHRASES = [
    "no acepto", "no quiero", "prefiero que no", "mejor no",
    "no estoy de acuerdo", "claro que no", "no me grabe", "no me graben",
    "nunca", "no gracias", "no thanks", "i don't agree", "i do not consent",
    "not okay", "rather not", "never", "nope", "nah",
]

_UNCERTAIN_PHRASES = [
    "no sé", "no se", "no entiendo", "tal vez", "a lo mejor", "depende",
    "déjeme pensarlo", "dejeme pensarlo", "maybe", "i don't know", "let me think",
]

_NO_PROBLEM_PHRASES = [
    "no hay problema", "no me molesta", "no problem", "i don't mind",
]

_REFUSAL_RE = _rx(_REFUSAL_PHRASES)
_UNCERTAIN_RE = _rx(_UNCERTAIN_PHRASES)
_NO_PROBLEM_RE = _rx(_NO_PROBLEM_PHRASES)

_YES_WORDS = [
    "sí", "si", "acepto", "claro", "de acuerdo", "por supuesto", "está bien",
    "esta bien", "yes", "yeah", "yep", "sure", "ok", "okay", "i agree",
]

_YES_RE = _rx(_YES_WORDS)
_NO_RE = re.compile(r"(?<!\w)no(?!\w)", re.IGNORECASE | re.UNICODE)


def classify(text):
    if text is None:
        text = ""
    text = str(text)
    if _REFUSAL_RE.search(text):
        return "no"
    if "?" in text or _UNCERTAIN_RE.search(text):
        return None
    if _NO_PROBLEM_RE.search(text):
        return "yes"
    has_yes = bool(_YES_RE.search(text))
    has_no = bool(_NO_RE.search(text))
    if has_yes and not has_no:
        return "yes"
    if has_no and not has_yes:
        return "no"
    return None
