
import hashlib, io, json, sys, zipfile
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from carbon_intake import (
    DOCS, DraftResult, UNTRUSTED, VERIFIED, chat, checklist, conflict_hits,
    docx, drafter, draft_parts, looping, questions, sentences, spoken,
    system_prompt, unverified_cites,
)


def test_draft_result_hashes_real_request():
    calls = []

    def complete(system, messages, max_tokens):
        calls.append((system, messages, max_tokens))
        return ("## Attorney review notes\n# T\n## ARTICLE ONE: X\n" + "word " * 10, "")

    result = draft_parts("will", ["will"], "transcript body", complete=complete)
    assert isinstance(result, DraftResult)
    assert result.messages[0]["content"].startswith("Documents the client asked for:")
    assert len(result.systems) == len(calls)
    for (sys_, msgs, mt), s in zip(calls, result.systems):
        assert sys_ == s
    assert msgs == result.messages


def test_spoken_cases():
    loop = "Thank you. " + "What is your email?Thank you. What is your email?" * 50
    assert spoken(loop) == "Thank you. What is your email?" and looping(loop)
    assert spoken("Who is the guardian? Also, what state? [FIN]") == "Who is the guardian? [FIN]"
    assert spoken("Le dejo 5.000 dólares a St. Andrew. ¿Algo más?") == "Le dejo 5.000 dólares a St. Andrew. ¿Algo más?"
    assert not looping("A normal memo line that is long enough.\nAnother different line that is long enough.")


def test_checklist_cases():
    assert checklist("Nice dog! When were you born? [DONE: nombre, bogus]", ["domicilio"], ["nombre", "domicilio", "hijos"]) == \
        ("Nice dog! When were you born?", ["nombre", "domicilio"])
    assert checklist("No tag here?", ["nombre"], ["nombre", "hijos"]) == ("No tag here?", ["nombre"])


def test_questions_cases():
    ids = lambda docs: [i for i, _ in questions("guion-plan-en", docs)[1]]
    assert "poder_agente" not in ids([]) and ids([])[0] == "documentos" and "albacea" not in ids(["poa"])
    assert "poder_agente" in ids(["poa"]) and "herederos" in ids(["trust"]) and len(ids(list(DOCS))) == 26
    assert [s["id"] for s in questions("guion-plan", [])[0]] == [s["id"] for s in questions("guion-plan-en", [])[0]]


def test_system_prompt_cases():
    p = system_prompt("guion-plan-en", "en", ["documentos"], ["ahcd"])
    assert "Documents chosen so far: ahcd." in p and "[salud_agente] (for the advance health care directive)" in p
    assert "[DOCS: will, poa]" in p and "poder_agente" not in p
    assert "[DOCS:" not in system_prompt("guion-en", "en")
    assert "calavera" in system_prompt("guion-plan", "es", avatar="calavera") and "calavera" not in system_prompt("guion-plan", "es")
    p2 = system_prompt("guion-en", "en", ["nombre"])
    assert "Already covered: nombre." in p2 and "back to: [nacimiento] What is your date of birth?" in p2
    assert "Speak only English" in p2 and "date of birth" in p2 and "Do you agree" not in p2
    with pytest.raises(ValueError):
        system_prompt("../.env", "en")
    assert "conflict-of-interest check" in system_prompt("guion", "es") and "conflicto de intereses" not in system_prompt("guion", "es")


def test_chat_cases():
    llm = lambda *a, **k: ("Good. What is your full legal name? [DONE: documentos] [DOCS: poa, will]", "")
    r = chat("guion-plan-en", "en", [{"role": "user", "content": "A will and a power of attorney"}],
             [], [], "avatar", complete=lambda *a, **k: llm(*a, **k))
    assert r["docs"] == ["will", "poa"] and r["text"] == "Good. What is your full legal name?"
    assert r["history"].endswith("[DONE: documentos] [DOCS: will, poa]") and "poder_agente" in r["open"]
    llm = lambda *a, **k: ("[DONE: documentos] [DOCS: poa]", "")
    assert chat("guion-plan-en", "en", [{"role": "user", "content": "x"}],
               [], [], "avatar", complete=lambda *a, **k: llm(*a, **k))["text"].startswith("What is your full legal name?")
    llm = lambda *a, **k: ("Fine. What is your full legal name? [DONE: documentos]", "")
    assert chat("guion-plan-en", "en", [{"role": "user", "content": "I do not know"}],
               [], [], "avatar", complete=lambda *a, **k: llm(*a, **k))["docs"] == list(DOCS)


def test_drafter_cases():
    p1, p2 = drafter("will", 1, 6), drafter("will", 7, 12)
    assert "Review notes (only" in p1 and "ARTICLE SEVEN" not in p1.split("Your articles")[1] and "Stop after Article SIX" in p1
    assert 'starting directly with "## ARTICLE SEVEN"' in p2 and "testimonium" in p2 and "Stop after" not in p2
    for kind in DOCS:
        p = drafter(kind)
        assert set(DOCS[kind]["cites"]) <= set(VERIFIED) and not unverified_cites(p, DOCS[kind]["cites"]), kind
        assert "No signature, witness, notary or execution block" in p and UNTRUSTED in p


def test_unverified_cites_case():
    from carbon_intake import DOCS
    assert unverified_cites("Probate Code section 6110 and § 9999 and sections 21110", DOCS["will"]["cites"]) == ["9999"]


def test_docx_xml():
    data = docx("# T\n## Article 1\n[ATTORNEY TO CONFIRM - x] and [ATTORNEY TO COMPLETE y]")
    z = zipfile.ZipFile(io.BytesIO(data))
    assert z.testzip() is None
    xml = z.read("word/document.xml")
    assert b"w:highlight" in xml and b'w:val="green"' in xml and b'w:val="yellow"' in xml
    assert b"w:jc" in xml and b'w:val="center"' in xml
    assert b"NUMPAGES" in z.read("word/footer1.xml")


def test_conflict_hits_all_cases():
    names = ["Roberto Méndez", "Acme Holdings LLC", "Madonna"]
    assert conflict_hits("José Ramírez", None) is None
    assert conflict_hits("Me llamo Ana, mi esposo es Roberto Mendes", names) == ["Roberto Méndez"]
    assert conflict_hits("Roberto Gómez y Ana Méndez", names) == []
    assert conflict_hits("mi esposo Roberto Carlos Méndez", names) == ["Roberto Méndez"]
    assert conflict_hits("Madonna", names) == []
