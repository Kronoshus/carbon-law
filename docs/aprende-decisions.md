# Aprende y Planea — decision log

Newest last. Each entry: date, decision, why, who. "Opus" = the head engineer (this agent). Firm decisions are
recorded when Carbon Law answers `aprende-questions.md`.

## Phase 1 — Discovery (2026-11-17)

| # | Decision | Why | By |
|---|---|---|---|
| D-001 | Aprende is a new `aprende/` front end (Vite + TS + Preact) with web and extension targets, on the existing FastAPI backend extended by `backend/aprende/`. | Brief sections 2.1, 3, 4; one codebase, no second backend. | Opus (proposed) |
| D-002 | New domains get relational tables through migrations; legacy JSON collections are untouched; one bridge module writes matters/documents/appointments. | `db.py` stores each collection as one JSON blob; per-item progress and analytics need rows. | Opus (proposed) |
| D-003 | Aprende routes skip the global request lock. | One Beam call would otherwise freeze every request. | Opus (proposed) |
| D-004 | The prototype's logic is **moved** into `carbon_intake/` and imported by both the prototype and the backend. | Brief: "Port this logic… do not rewrite it from memory"; one copy avoids drift. | Opus (proposed) |
| D-005 | Tentative document choice moves to day 2 (final on day 4). | The firm's 2-business-day scope review must finish before day 5. Order unchanged. | Opus (proposed) |
| D-006 | "Tus datos" opens on an automatic conflict *clear*; payment waits for the firm's own clearance; without an uploaded list, details wait for staff. | Brief: conflict check before any personal detail; the firm's manual check takes days. | Opus (proposed) |
| D-007 | Consent "no" = learning-only mode (lessons and discounts, no datos, no AI). | Brief: nothing collected or sent to Beam after a refusal; lessons are general information. | Opus (proposed) |
| D-008 | No browser speech recognition anywhere. | Chrome sends that audio to Google; brief: audio stays on the firm's servers. | Opus |
| D-009 | Game mechanics without lives, hearts, timers or penalties; calm mode for sensitive items. | Serious subject; older clients; brief: "respectful about a serious subject". | Opus (proposed) |
| D-010 | Names in the app: XP = *pétalos*, streak = *vela*, badges = *sellos*. | Culturally rooted, warm, and the seal echoes a notary's stamp. | Opus (proposed) |
| D-011 | Design direction "noche de fiesta, papel de casa"; plum outline on every component; League Spartan + Work Sans (the firm's pair), self-hosted. | Makes the UI part of the characters' world; ties to the firm's brand; privacy (no font CDN). | Opus (proposed) |
| D-012 | Piñata and El Oso designed in La Calavera's style and rig (same outline, palette, eye language, frame and moving-parts map). No sombrero on the new characters. | Brief 2.3: same style and rig; avoid costume stereotyping. | Opus (proposed; firm reviews art) |
| D-013 | Spanish register *usted*. | Prototype's register; older clients. Firm may change (Q-L4). | Opus (proposed) |
| D-014 | The modern-web-guidance skill was followed for every screen decision; no conflict with the brief found. | Brief section 0 asks for the record. | Opus |
| D-015 | No Beam builder agents were used in Phase 1. | Phase 1 is discovery and design, which the brief assigns to Opus; Beam starts with Phase 2 tickets. | Opus |

## Firm answers (2026-11-17, Kevin by phone)

| # | Answer | Effect on the plan |
|---|---|---|
| F-001 (Q-W1) | Promise "about two weeks". | Copy says "unas dos semanas"; the tracker shows each client's real dates (T5-04, T6-09). |
| F-002 (Q-D1) | The Beam approval of 2026-11-15 covers Aprende. | Production AI calls are allowed after the consent and conflict gates. |
| F-003 (Q-S1) | Start without server voice. | No voice hosting. The characters speak with the browser's own voice and clients type their answers. T5-06 shrinks to the browser fallback and the ban on browser speech recognition; the voice container is deferred. |
| F-004 (Q-P1) | No Stripe account yet. | T6-02/T6-03 are built and tested against a mocked Stripe. Real test-mode keys wait for a firm-owned account. The bank account and advance-fee handling are still open. |
| F-005 (Q-B1) | Token cap raised to 10 B. | Every ticket gets at least 100 M tokens; no ticket grouping (61 tickets ≈ 6.1 B minimum). |

| F-006 | **Phase 1 approved** (Kevin, 2026-11-17). Phase 2 starts. | PR #10 merged. |

## Findings recorded during discovery

- `backend/app.py`'s client workflow can show drafts to a client before attorney approval (`POST /workflows/{id}/drafts`). Not changed in Phase 1; Q-X1.
- `backend/schema.sql` tables are not used by the app. Left as they are.
- `comms` is annotated `List` but initialised as `{}` in `app.py` (replaced by `load_data()` on start, so harmless).
- The public site's white-on-`#FF4E00` buttons are 3.3:1 contrast (below AA). Not in scope; reported.
- Baseline on `main` (2026-11-17): `pytest tests` 35 passed; `avatar-intake/server.py --check` ok.
- The 14-day journey is 14–19 calendar days under the firm's own turnaround standards (spec 6.3); Q-W1.

## Token use

Phase 1 ran in one head-engineer session (no sub-agents). The harness does not report cumulative token spend;
the session's context reached about 0.4 M tokens. Phase reports from Phase 2 on will include the builder agents' use.

## Phase 2

| Ticket | Decision |
|---|---|
| T2-09 | Worker loop runs in-process in the web service (daemon thread) gated by `APRENDE_INPROCESS_WORKER=1`; `render.yaml` has no paid worker service. `backend/worker.py` exposes `run_forever(stop_event)` and `start_in_background()`. `python -m backend.worker` still works for a separate process. Backoff 60/300/1800s. |
