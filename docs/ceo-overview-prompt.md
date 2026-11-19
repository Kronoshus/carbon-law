# Prompt: build a CEO-ready workflow document for "Aprende y Planea"

You are writing one document for the CEO of Carbon Law Group. It explains what has been built so far on the firm's new client app, how the work was done, and what the firm needs to decide next. The CEO is not technical. They will read it on a laptop and may show it in a meeting.

## The product, in two sentences

"Aprende y Planea" is a Spanish-first, bilingual app (website plus Chrome extension). It teaches a client estate planning in short, Duolingo-style lessons over about two weeks, while the firm prepares their will. Each finished lesson takes $100 off the will. Three animated characters guide the client: La Calavera, El Oso and Piñata.

## Where the facts are (read these first; do not invent anything)

Repository: `~/work/carbon-law` (GitHub: Kronoshus/carbon-law), branch `main`.

| What | File |
|---|---|
| The original brief from the firm | `avatar-intake/PRIME_AGENT_BUILD_PROMPT.md` |
| Product spec, architecture, design | `docs/aprende-spec.md`, `docs/aprende-architecture.md`, `docs/aprende-design.md` |
| The full plan: Phases 1–8 and every ticket | `docs/aprende-backlog.md` |
| Every decision, with the reason | `docs/aprende-decisions.md` |
| Open questions for the firm | `docs/aprende-questions.md` |
| Phase reports (what was built, tests, bugs fixed) | `docs/aprende-phase-2-report.md`, `-phase-3-`, `-phase-4-report.md` |
| Attorney review packet for the lessons | `docs/aprende/lesson-review-packet.md` |
| Lesson content | `aprende/content/` (YAML) |
| Merged work | `gh pr list --state merged --limit 40` (PRs #10–#38) |

Screenshots you can use (all real, taken from the running app):
- Phase 2, sign-up and app shell: `docs/aprende/phase2/` (`bienvenida.png`, `cuenta-nueva.png`, `shell.png`, `popup.png`)
- Characters: `docs/aprende/characters/lineup-final.png`, `states.png`; `docs/aprende/phase3/stage-phone.png`, `side-panel-160px.png`
- Phase 4, learning: `docs/aprende/phase4/` (`map-new.png`, `map-after.png`, `lesson-explain.png`, `lesson-right.png`, `lesson-wrong.png`, `lesson-done.png`, `exercise-match.png`, `exercise-order.png`, `price-card.png`)
- Original design mockups: `docs/aprende/screens/` (`mapa.png`, `leccion.png`, `pago.png`)

If a number or claim is not in these files, leave it out. Every number in your document (test counts, lessons, legal statements, PR numbers) must come from them. Check each one against the source before you finish.

## Status today (check against the files)

- Phases 1–4 of 8 are complete and merged. Phase 5 (conversation and intake) is approved and about to start.
- Phase 1 (plan): spec, architecture, design, backlog, decisions.
- Phase 2 (foundation): accounts, the client's two-week journey, the progress lock, app shell, Chrome extension.
- Phase 3 (characters): three animated 3D characters, with still images as a fallback; the browser's built-in voice.
- Phase 4 (learning): course map, lesson player with six question types, 130 lesson items in Spanish and English, 111 legal statements each tied to a California Probate Code section or a California Courts self-help page. No legal content reaches clients until the attorney approves it.
- Quality on `main` after Phase 4: 178 backend tests, 30 front-end unit tests, 16 browser tests, all passing; accessibility scans clean; the app's first download is 21 KB.
- Open questions for the firm: Q-L2 attorney review of the lessons; Q-L1 a native-speaker review of the Spanish; Q-P4 prices for the trust, power of attorney and health care directive; Q-C1 La Calavera's name; Q-C2 cultural review; Q-C3 the characters' voices.

## How the work was done (the "workflow" part)

Explain this plainly; it is the part the CEO most needs to trust:
1. **Plan first.** Phase 1 produced the spec and a ticket backlog. The firm approved it before any code (F-006).
2. **Phases with a go/no-go gate.** Each phase starts only after the firm says go. Each ends with a written report and screenshots.
3. **Two kinds of AI worker.** Claude Opus did the design, the characters, the lesson content and the legal review. Beam builder agents wrote first versions of the code in parallel. Opus reviewed every change, rewrote what was wrong, and ran all tests itself.
4. **Tests are written before the feature** for the most important behavior.
5. **Every change goes through a pull request with automatic checks** (backend, front end, browser tests) before it merges.
6. **Legal accuracy.** Every legal statement cites its source, and the statute text was read on the official leginfo site. An attorney approval gate stops unapproved content from publishing.
7. **The firm controls spending and risk.** The agents ask before spending money, publishing, or touching real client data.

## What to produce

One self-contained HTML file: `docs/aprende-ceo-overview.html`. Embed the images (base64 or relative paths into `docs/aprende/`), use no external network resources, and make it print cleanly to PDF (Letter, portrait). Also export `docs/aprende-ceo-overview.pdf` if you have a headless browser.

Sections, in this order:
1. **Title band**: "Aprende y Planea: progress report", the date, "Phases 1–4 of 8 complete".
2. **One-paragraph summary**: what the app is, where it stands, and the one thing needed from the CEO.
3. **Roadmap graphic**: all 8 phases as a horizontal timeline. Done phases are filled, Phase 5 is "next", and later phases are outlined. Take the phase names from `docs/aprende-backlog.md`.
4. **The client's journey**: a simple flow diagram from sign-up → Day 1 → daily lessons → payment → attorney review → signing. Mark which steps exist today.
5. **What we built**: one card per completed phase. Each card has 3–4 plain bullets and one screenshot.
6. **See it working**: a gallery of the Phase 4 screenshots, each with a one-line caption.
7. **How we built it**: the workflow above as a diagram (plan → ticket → AI builder → Opus review → automatic tests → merge → phase report → firm go/no-go), with short labels.
8. **Quality and safety**: the numbers as a few big figures (tests passing, legal statements sourced, accessibility clean, first download size), plus the attorney-approval gate.
9. **Decisions needed from the firm**: a table with the question, why it matters, and who should answer it.
10. **Next 30 days**: Phase 5 in plain words, and the note that live AI conversation calls will cost money and will need approval.

## Style

- Plain English for a busy executive. Short sentences. No jargon: say "automatic checks", not "CI"; say "AI builder", not "Beam-1.0-501B"; leave out file names and code terms except in a small appendix.
- Visual first: diagrams as inline SVG (or CSS), screenshots, a few large numbers. No walls of text. Each section should fit on one screen.
- Look: warm and professional. Use the app's own palette from `docs/aprende/screens/tokens.css` (plum, gold, teal, rosa), white space, one display font and one body font, and the characters as accents rather than clutter.
- Honest: show the open questions and the remaining phases plainly. Do not overstate. The app is not live with clients yet.
- Keep it to about 6–8 printed pages.

## Before you finish

- Open the HTML in a headless browser, screenshot each page, and look at it. Fix any overlap, cut-off text or broken image.
- Check every number against its source file.
- Give the user the file paths, page count, and a list of any facts you could not confirm.
