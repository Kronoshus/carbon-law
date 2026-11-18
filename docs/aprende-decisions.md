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
| T2-10 | Vite `base` comes from `VITE_BASE` (default `/`); the Pages workflow builds with `VITE_BASE=/aprende/` and copies `aprende/dist/web` into `_site/aprende` without touching the existing `web/` files. Tests may not reach the network (`tests/conftest.py`): the existing demo-drafting test had been calling the real Beam API with the local key on every run. |
| T2-09 | Worker loop runs in-process in the web service (daemon thread) gated by `APRENDE_INPROCESS_WORKER=1`; `render.yaml` has no paid worker service. `backend/worker.py` exposes `run_forever(stop_event)` and `start_in_background()`. `python -m backend.worker` still works for a separate process. Backoff 60/300/1800s. |
| T2-12 | Popup is a separate tiny Preact view (`src/targets/extension/Popup.tsx`), not `App`; no three.js/character stage in the popup bundle. Streak shows 0 until Phase 4. Today's step = journey `day` plus the first gate in `GATE_ORDER` that is false, mapped via a typed `Record<Gate, I18nKey>`. Token storage uses `chrome.storage.session` only; `local`/`sync` are never touched. Side panel opens via `chrome.sidePanel.open({ windowId })` from the popup button. |

## Phase 3

| Ticket | Decision |
|---|---|
| T3-01 | One build for every character: `python characters/build.py` (art in code → atlas → Blender `make_character.py` → `aprende/public/characters/`). Lighter than the prototype's sheet: 140-cell grid, fully transparent cells dropped, sparse morph targets, no normals, WebP textures, JPEG backdrop. La Calavera's GLB went from 11 MB to 1.3 MB; rendered against the old one in four frozen poses it differs in 0.00 % (base), 0.25 % (jaw), 0.03 % (blink), 0.04 % (turn) of pixels. Piñata 0.7 MB, El Oso 0.8 MB. |
| T3-01 | States are overlays inside the one mesh and texture: each state's art (the pixels that differ from the base) is folded to a point in the basis and opened by its own shape key, and the head keys move it too. So one engine, one draw call, no texture swaps. Costumes (glasses, pen) are overlays toggled by one key each, not a material switch (the backlog said material switch; a key is simpler for the engine). |
| T3-01 | Bug found in the prototype pipeline: Blender exported every shape key with a default weight of 1 (`make_calavera.py` never set `value = 0`). The prototype hid it by setting all eight keys every frame. `make_character.py` sets every key to 0; the prototype's own GLB is unchanged. |
| T3-02/03 | Piñata's teeth moved above the mouth band and El Oso given a small dark mouth, so `jawOpen` opens a mouth instead of stretching a line. `jawDrop`/`jawFade` are per-character in the rig map. |
| T3-04 | La Calavera: base art unchanged (`avatar-intake/calavera.png`); new layers `celebrate` (happy closed eyes), `wave` (+ `waveSwing`, a raised skeletal hand in his sleeve, swinging from the shoulder), costumes `glasses` (day 9) and `pen` (signing day). The happy dance is engine motion over `celebrate`, not new art. |
| T3-07 | Cultural review of the final art (Opus): Day of the Dead imagery kept as an *ofrenda* (marigolds, candles, papel picado), no realistic bones or gore; the one sombrero stays La Calavera's; no moustaches, no costume clichés on Piñata or El Oso; the sarape stripes are generic; El Oso's comfort pose reads as kind at 160 px. Still needed: the firm's native-speaker review of names, lines and art (Q-C2). |
| T3-06 | Characters API: `GET /characters` lists the enabled characters with `name_key` = `character.<id>.name` (an i18n key; the names wait for Q-C1); staff `PATCH` is audited; La Calavera cannot be disabled (409); `character_for(unit)` falls back to La Calavera. |
| T3-05 | `CharacterEngine` ports the prototype's animation (same constants, camera, unlit materials, body group) with states `idle, talking, thinking, listening, celebrating, comforting, waving, dancing` and costumes; overlay keys ease in. `three` 0.160.0 (the prototype's version, with `@types/three`) is loaded only when a stage mounts. No server voice (F-003): `speak()` uses the browser's speech synthesis with word-timed lip sync; `speakAudio()` keeps the prototype's server shape for later. Canvas at the device pixel ratio (capped at 2). |
