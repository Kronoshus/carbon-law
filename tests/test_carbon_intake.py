import hashlib, json
from pathlib import Path

import pytest

from carbon_intake import (
    GUIONES, chat, checklist, conflict_hits, docx, looping, questions,
    sentences, spoken, system_prompt, unverified_cites,
)


def test_spoken_looping_checklist():
    assert spoken("Thank you. What is your email? [FIN]") == "Thank you. What is your email? [FIN]"
    assert not looping("A normal memo line that is long enough.\nAnother different line that is long enough.")


def test_questions_and_system_prompt():
    qs = questions("guion-plan-en", [])[1]
    assert qs
    p = system_prompt("guion-plan-en", "en", ["documentos"], ["ahcd"])
    assert "[DOCS: will, poa]" in p


def test_chat_with_stub_complete():
    def complete(system, messages, max_tokens):
        return ("Good. What is your full legal name? [DONE: documentos] [DOCS: poa, will]", "")
    r = chat("guion-plan-en", "en", [{"role": "user", "content": "A will and a power of attorney"}],
             [], [], "avatar", complete=complete)
    assert "[DOCS:" in r["history"]


def test_conflict_hits_cases():
    names = ["Roberto Méndez", "Ana Méndez"]
    assert conflict_hits("Me llamo Ana, mi esposo es Roberto Mendes", names) == ["Roberto Méndez"]
    assert conflict_hits("José Ramírez", None) is None


def test_unverified_cites_and_docx():
    assert unverified_cites("section 9999", ["1", "2"]) == ["9999"]
    xml = docx("**DRAFT**\n# Last Will of A & B\n## Article 1\nI give **Ana** <all>.\n- one")
    assert b"word/document.xml" in xml
