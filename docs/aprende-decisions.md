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

## Phase 4

| Ticket | Decision |
|---|---|
| T4-01 | Lessons written by Opus: the four core lessons, «Cuide sus documentos» and four bonus lessons — 130 items, 111 legal statements, each citing a Probate Code section read on leginfo (in a headless browser; 20 sections added to `VERIFIED` on 2026-11-18) or a California Courts self-help page. Only those two kinds of source are used (the brief's rule), so the community-property definition in Family Code § 760 is not cited. Register *usted* throughout, so the final lesson is «Cuide sus documentos» (the brief wrote «Cuida tus documentos»). |
| T4-01 | `docs/aprende/lesson-review-packet.md` is generated from the content for the attorney's review (Q-L2); nothing publishes without his approval of the exact version. |
| T4-02 | Lesson content lives in tables with versions; YAML in `aprende/content/` is the seed and the export format. A legal item publishes only with an attorney approval of its current version; an edit makes a new draft version. |
| T4-03 | Lessons are served without answers; match/order are shuffled with a seed from the journey and item (stable across restarts). The day-N lesson opens at local midnight after day N−1 (setting `lessons_per_day`); bonus lessons after day 1; the final lesson after signing. Completion = every graded item answered and ≥ 80 % of the latest answers right, with any number of retries. |
| T4-04/05 | The player shows the speech bubble only for explanations (a question is on screen as its heading). Exercises: choice, scenario, true/false, match (tap-tap, undo), order (Subir/Bajar buttons, keyboard and switch access), listen (said by the character, text one tap away). A wrong answer comes back later in the same step; no penalties. |
| T4-06 | Petals: +10 for a first correct answer, +50 per lesson, +100 for "Tus datos". The candle forgives one missed day per ISO week; a rest day only counts if the streak continued past it. Levels at 0/300/800/1500 petals (setting). Reminders: off until the client chooses a time, at most one a day, never after a lesson that day (selection only; sending comes in Phase 6). |
| T4-07 | The map shows the firm's later steps (pay, attorney review, documents, signing) as locked nodes with their days; Phase 6 links them to the real timeline. |
| T4-08 | Discounts are recorded in the same transaction as the event that earns them and keep the amount of that moment. Prices for the trust, POA and health care directive are placeholders shown as "ejemplo" until the firm sets them (Q-P4). |
| Process | Beam builders wrote first versions of T4-02…T4-06; several ended their sessions without committing, and most needed real rewrites (SQLite-only SQL, bypassing `journey.apply`, no tests, no styles). Opus finished or rewrote each one and reviewed every screen from screenshots. |
| T5-03 | Conflict status: firm "flagged" → hold; firm "cleared" → clear (releases a possible match or no_list after review); otherwise auto "possible" → hold, auto "no_list" or nothing → pending, auto "clear" → clear. The firm's latest decision wins. Names/matches are stored only in `conflict_checks` (staff-only); `conflict_auto` carries only `{result}`. |
| T5-02 | The `consent` event keeps only `{answer}`. A typed answer is classified by one shared phrase table in Python and TypeScript: an explicit refusal wins, uncertainty is asked once more, unclear twice counts as no (changeable later). The day-1 gate shows the header (sign out) without tabs, and adds "El abogado Raval revisa y decide todo" to the disclosure (research: make the human role visible). |
| T5-05 | "Tus datos" questions are content (`aprende/content/datos.yaml`, 29 questions incl. the research additions; no immigration-status question). An answer from the intake chat is saved only when the character marks the current question `[DONE: id]`, and it is the client's own words for that question, never the character's. `covered` comes from the server only. Every change to an earlier answer keeps an audit row. |
| T5-07 | Persona prompts are content (`aprende/content/personas.yaml`): one shared rule set (AI, not the attorney; general information; no fees, results, sales, financial products or immigration-status questions; family-and-home framing; a scripted answer to "notario"; 911 for danger) plus one persona per character and one block per mode. Attorney approval required before clients see them. |
| T5-09 | Changing the tentative or confirmed documents is recorded each time (it was silently ignored before). Changing the confirmed set after the attorney approved the scope records `scope_reopened`: the scope counts as approved only if his latest decision came after it, and the timeline gives the review one business day (`turnaround.scope_change_bd`). A repeated approval is a no-op. "No sé todavía" = all four documents. |
| T6-09 | "Mi plan" shows the timeline's steps (9, or 10 with changes) rather than 14 numbered days; each row has the step's real day number and date. A late firm step shows only a calm sentence to the client, no red and no "late" label. The staff list endpoint is ready; its screen comes with the staff tickets (Phase 7). |
| T6-01 | The engagement letter follows Bus. & Prof. Code § 6148(a) (read on leginfo): the client signs the exact text shown (its SHA-256 is checked), the attorney countersigns, and payment waits for both signatures; the client's PDF carries both signatures and the hash. The template is used only after the attorney approves it in the app, and the four firm details (bar number, costs, refunds, data promise) must be set first. Wording and the countersignature rule are in decision PR #57. |
| T6-04 | Drafting reuses the prototype's checks unchanged (every article, full length, then one lenient retry; looping replies rejected; citations checked against each document's own verified list). The transcript is the client's datos answers, fenced as client data. A failed document alerts staff and keeps the others; drafts_ready only when all succeeded. |
| T6-07 | Bookings use a 30-minute grid in Los Angeles time; each booking holds one row per 30-minute block with a unique key, so two clients can never get the same time, even at the same instant. The spring-forward hour is never offered. Clients change or cancel up to 24 hours before; after that they call the office. Changing the office hours never touches existing bookings. The app's email sending is now one function, `send_email`. |
| T6-02/03 | Stripe is called over its HTTP API (no SDK) behind one function, mocked in tests (F-004). Only the signed webhook records a payment; the amount must equal the checkout session we created (or today's quote), so a discount earned after checkout never rejects a real payment. Each Stripe session is recorded once (unique id), so retries and simultaneous deliveries are safe. Live mode needs STRIPE_MODE=live and an admin's approval in the app. Refunds are recorded here and made in Stripe's dashboard. |
| T6-06 | La Calavera's day-9 walkthrough reads Opus's plain-language summary of each article (`aprende/content/summaries.yaml`, general only, attorney approval required: decision PR #50, Q-L3), never new text about the client. A change request uses the firm's own change types and goes into the firm's change-request records through one shared function (`record_change_request`). |
| T7-01 | Content is versioned in content_versions (draft, review, published, superseded) and approved in content_approvals. A paralegal drafts and submits; only the attorney approves and publishes, and the old version stays live until approval. Approval records who approved, when, and which version. Both languages are required to submit, approve, or publish. |
| T7-04 | Staff guard at the boundary: one HTTP middleware rejects unknown/missing tokens with 401 and client tokens with 403 on every `/staff/`, `/conflicts` and `/chat/attorney-questions` route before body validation. Attorney answers are stored only in `attorney_questions` (migration 0017) and audited by id without text; only the attorney role may answer, and a new answer replaces the first. Conflict match names never leave `/conflicts/*`. |
| T7-02 | The T4-02 validator (`content.validate`) runs on every item version through `content.version_errors(entry_id, body)`, which rebuilds a one-lesson bundle from the item's lesson, step and sources; its own error strings are reused unchanged. The detail endpoint adds `errors` to each version. Submit, approve and publish return 422 `invalid` with the errors before any state change; drafts still save. The admin shows the errors under the version and disables sending/approving/publishing while they exist. datos and summaries have no item rules. |
| T7-05 | The firm sets office hours, holidays, data retention, the voice/AI-chat/extension switches, and lessons_per_day in one place (Firma). Defaults: retention 365 days and one lesson a day are assumptions until #52/#51 are answered; the voice switch has nothing to enforce yet (F-003). Server enforces AI chat off (503 ai_chat_off), extension off (503 extension_off for chrome-extension origins), lessons_per_day, and a retention sweep deletes unpaid personal data after the configured days. |
| T7-07 | Auth before validation: one `backend/aprende/auth.py` module (`client_user`, `client_journey`, `signed_in`, `staff`) used as dependencies on every Aprende route, replacing the local copies; identity and role checks run before FastAPI validates query/body. Audit: one middleware in `app.py` writes `log_audit(actor, "METHOD route.path", "route", path params, "")` for a 2xx state-changing Aprende request unless the handler already wrote a row; refused requests write nothing; client text never enters the detail. |
| T8-01 | F-003: no server voice or microphone capture anywhere; typed answers and the browser's speechSynthesis (the offscreen permission/file stay for T8-02). Popup's "today's step": if may_disclose, may_consent and may_name are all true and /learn/map has an available lesson in will/trust/ahcd/poa (lowest day first) or final, show that lesson's title; otherwise the first false gate in GATE_ORDER → its popup.gate.* label, or popup.complete. No token → popup.signedOut and no /journey, /progress or /learn/map calls. |
