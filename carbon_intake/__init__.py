"""Carbon intake shared logic (Carbon Law Group 'Aprende y Planea')."""
from .conversation import (
    GUIONES,
    chat,
    checklist,
    looping,
    questions,
    sentences,
    spoken,
    system_prompt,
)
from .drafting import (
    BANNER,
    DraftResult,
    DOCS,
    NOTICE,
    SUMMARY,
    UNTRUSTED,
    VERIFIED,
    WORDS,
    drafter,
    draft_parts,
    instrument_words,
    unverified_cites,
)
from .docx import docx
from .conflicts import conflict_hits, fold

__all__ = [
    "GUIONES", "chat", "checklist", "looping", "questions", "sentences", "spoken",
    "system_prompt", "BANNER", "DOCS", "NOTICE", "SUMMARY", "UNTRUSTED", "VERIFIED",
    "WORDS", "drafter", "draft_parts", "instrument_words", "unverified_cites", "docx",
    "conflict_hits", "fold",
]
