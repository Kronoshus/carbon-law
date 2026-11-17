# Aprende y Planea — ticket backlog, Phases 2–8

Phase 1 deliverable. Each ticket is written to be pasted as the prompt of one **Beam builder agent**
(`reflection/Beam-1.0-501B-A23B`, reasoning *high*, at least 100 M tokens) unless its owner is **Opus**. Opus reviews and
merges every Beam diff. Read `aprende-spec.md`, `aprende-design.md` and `aprende-architecture.md` before any ticket.

## Rules for every ticket (definition of done)

1. One branch, one pull request, about 300 changed lines or fewer (split otherwise; a ticket says where).
2. Acceptance tests are written **first** (Opus writes them for tickets marked ★; the builder writes them otherwise, before the code). A change that passes by special-casing a test is rejected.
3. CI green: backend pytest (SQLite and Postgres), `avatar-intake/server.py --check`, `tsc`, ESLint, vitest, i18n parity, Playwright for the targets the ticket touches.
4. No client data and no keys in the repo; fictional people only (the test family is *Ana Torres*, *Luis Torres*, children *Sofía* and *Mateo*).
5. Every user-visible string in `aprende/i18n/es.json` **and** `en.json`; Spanish uses *usted*.
6. Front-end tickets: run the modern-web-guidance skill (`npx -y modern-web-guidance@latest search "<task>"`) for the listed guide ids and follow them.
7. Any code that calls a model goes through `BeamClient` (loop guard + one retry). Never send anything to a model before the journey's consent and conflict gates.
8. The guardrails in `PRIME_AGENT_BUILD_PROMPT.md` section 6 are not yours to relax. If a ticket seems to need it, stop and say so in the PR.
9. Update `docs/aprende-decisions.md` with any decision the ticket forced.

Sizes: **S** ≤ 120 lines, **M** ≤ 300 lines, **L** = split into the parts listed.

## Shared interfaces (the contract between tickets)

```text
GET  /journey                         → Journey
POST /journey/events {type, payload}  → Journey | 409 {error: "gate", missing: [gate…]}
     client-sent types only: ai_disclosed · consent{answer: yes|no} · names_submitted{names: [str ≤120] ≤20}
                             documents_tentative{codes} · documents_confirmed{codes}
     every other type is server-only (see spec section 5)
Journey = {id, user_id, started_at, tz, day: int, facts: {event_type: iso_time}, gates: {name: bool},
           conflict: "pending"|"clear"|"hold",          # never more detail to the client
           documents: {tentative: [code], confirmed: [code]},
           timeline: [{step, day, due: iso_date, status: done|today|next|late|waiting, shifted_days, reason_key}]}
codes = will | trust | poa | ahcd   (the prototype's DOCS keys)

GET  /learn/map                       → {units: [{id, doc, lessons: [{id, day, status: locked|available|done, unlock_at}]}]}
GET  /learn/lessons/{id}?lang=es      → {id, title, character, sensitive, steps: [{id, items: [Item]}]}   (no answers inside)
POST /learn/attempts {item_id, answer}→ {correct, explanation, source: {kind, cite, url}, petals}
POST /learn/lessons/{id}/complete     → {completed: bool, score, discount_event?: str}
GET  /datos                           → {questions: [{id, doc, text, status: open|answered|skipped}], complete: bool}
PUT  /datos/{question_id} {text?|skip?}
POST /chat {mode: learn|intake, character, lesson_id?, messages: [{role, content, reasoning_content?}], covered, docs}
     → {text, history, reasoning, covered, open, docs, attorney_question: bool}
GET  /payments/quote?codes=…          → {items: [{code, base, discounts: [{event, amount}], price}], package?, total, currency, test_mode}
POST /payments/checkout {codes}       → {url} | 409 gate
POST /payments/webhook                (Stripe-signed)
Money is integer cents everywhere.
```

---

## Phase 2 — Foundations (Beam, Opus reviewing)

### T2-01 · Move the prototype's intake logic into `carbon_intake/` ★
- **Owner:** Beam · **Size:** M · **Depends:** —
- **Goal:** one copy of the proven logic that both `avatar-intake/server.py` and the backend import (architecture D6). Pure move, no behaviour change.
- **Files:** new `carbon_intake/__init__.py`, `conversation.py` (`questions, system_prompt, sentences, looping, spoken, checklist, chat`), `drafting.py` (`UNTRUSTED, SUMMARY, VERIFIED, DOCS, WORDS, drafter, BANNER, NOTICE, unverified_cites, instrument_words, draft_parts`), `docx.py`, `conflicts.py` (`fold, conflict_hits(text, names)`), `guiones/` (the eight `guion*.json`); edit `avatar-intake/server.py` to import them.
- **Interfaces:** `chat(guion, lang, messages, covered, docs, avatar, *, complete)` where `complete(system, messages, max_tokens) -> (text, reasoning)` is injected (today's `llm(..., full=True)`). `draft_parts(kind, docs, transcript, *, complete)` returns the joined markdown or raises; file writing stays in `server.py`. `conflict_hits(text, names: list[str])` takes the list instead of reading `conflicts.csv`.
- **Must not change:** any prompt text, regex, threshold, or output; `server.py`'s HTTP behaviour; the guion files' content (moved, with `avatar-intake/guion*.json` kept working via the new path).
- **Acceptance tests:**
  - `cd avatar-intake && python server.py --check` prints `ok` (its monkeypatching of `llm` updated to patch the injected function).
  - New `tests/test_carbon_intake.py` re-runs every assertion of `--check` that does not touch the file system, through pytest.
  - `test_prompts_unchanged`: `system_prompt` and `drafter` output for five fixed inputs equals snapshots generated from `main` **before** the move (committed in the same PR).
  - `grep -c "^def system_prompt" avatar-intake/server.py` is 0.

### T2-02 · Migration runner and the first Aprende tables
- **Owner:** Beam · **Size:** M · **Depends:** —
- **Goal:** relational storage for new domains without touching legacy collections (D4).
- **Files:** `backend/migrate.py`, `backend/migrations/0001_aprende_core.sql`, `backend/db.py` (add `query(sql, params)` / `execute(sql, params)` / `transaction()` helpers that translate `?` placeholders for Postgres), `tests/test_migrations.py`.
- **Tables in 0001:** `schema_migrations(version, applied_at)`, `settings(key PK, value_json, updated_by, updated_at)`, `journeys(id PK, user_id UNIQUE, tz, started_at, matter_id)`, `journey_events(id PK, journey_id, type, payload_json, actor, created_at, UNIQUE(journey_id, type, dedupe_key))`, `jobs(id PK, kind, key UNIQUE, payload_json, status, attempts, run_after, locked_by, locked_at, last_error)`, `ai_calls(id, purpose, model, prompt_tokens, completion_tokens, latency_ms, cost_usd_est, request_sha256, response_sha256, ok, created_at)`, `events(id, journey_id, type, props_json, target, created_at)`.
- **Must not change:** the `collections` table or any legacy collection.
- **Acceptance tests:** `test_migrate_from_empty_sqlite`, `test_migrate_from_empty_postgres` (CI service container), `test_migrate_is_idempotent` (second run applies nothing), `test_journey_event_dedupe` (same `(journey, type, dedupe_key)` inserted twice → one row), `test_legacy_collections_untouched`.

### T2-03 · Front-end scaffold with two build targets
- **Owner:** Beam · **Size:** L (part a: tooling + web target; part b: extension target)
- **Depends:** —
- **Goal:** `aprende/` per architecture D1; `npm run build:web` → `dist/web`, `npm run build:ext` → `dist/extension`.
- **Files:** `aprende/package.json`, `vite.config.ts` (mode `web` / `extension`), `tsconfig.json` (strict), `eslint.config.js` with an import-boundary rule (`src/core`, `src/ui` may not import `src/targets/**`), `src/ui/tokens.css` (copied from `docs/aprende/screens/tokens.css` — that file then becomes a link to it), `src/platform/index.ts` (interface: `storage.get/set/remove`, `getMicrophone()`, `notify()`, `openUrl()`, `scheduleReminder()`), `src/targets/web/{main.ts,platform.ts}`, `src/targets/extension/{sidepanel.html,sidepanel.ts,popup.html,popup.ts,background.ts,offscreen.html,offscreen.ts,platform.ts,manifest.json}`.
- **Must not change:** anything outside `aprende/` except `.gitignore`.
- **Acceptance tests:** `build:web` and `build:ext` succeed; `dist/extension/manifest.json` is MV3 with only `sidePanel, storage, alarms, notifications, offscreen` permissions and one host permission (the API origin from an env var); `lint` fails on the fixture `tests/fixtures/bad-import.ts`; vitest smoke test renders `<App/>`.
- **Web guidance:** `css`, `performance`.

### T2-04 · Internationalisation with parity checks
- **Owner:** Beam · **Size:** S · **Depends:** T2-03
- **Goal:** no hard-coded text; Spanish default, English full.
- **Files:** `aprende/i18n/es.json`, `en.json`, `src/core/i18n.ts` (`t(key, vars)`, `Intl.PluralRules`, `Intl.NumberFormat` for money in cents, `Intl.DateTimeFormat`), `scripts/i18n-check.mjs`, generated `src/core/i18n-keys.d.ts`.
- **Acceptance tests:** a key missing from either file fails `npm run i18n:check` (fixture); `t("precio", {cents: 280000})` → `"$2,800"` in both; ESLint rule flags a JSX text literal; `<html lang>` follows the chosen language.

### T2-05 · Client accounts for Aprende ★
- **Owner:** Beam · **Size:** M · **Depends:** T2-02
- **Goal:** sign-up with the adult check, 30-day sliding client sessions, CORS for the extension (D10).
- **Files:** `backend/app.py` (`SignupRequest.adult: bool`, session expiry by role, CORS origins/methods from env `APRENDE_EXTENSION_ORIGIN` and PUT/DELETE), `aprende/src/core/api.ts` (fetch wrapper, token via `platform.storage`), `tests/test_aprende_auth.py`.
- **Must not change:** staff session length (24 h), password hashing, existing auth tests.
- **Acceptance tests:** signup without `adult: true` → 400 for Aprende sign-ups (`source: "aprende"`), existing portal signup unchanged; client session `expires` slides forward on use and is 30 days; staff still 24 h; CORS preflight from the configured `chrome-extension://…` origin succeeds, from another extension fails.

### T2-06 · Journey API and server-enforced gates ★
- **Owner:** Beam · **Size:** L (a: model + gates + events endpoint; b: legacy bridge)
- **Depends:** T2-02, T2-05
- **Goal:** the state machine of spec section 5 as one pure function plus endpoints.
- **Files:** `backend/aprende/journey.py` (`gates(facts) -> dict[str, bool]`, `apply(journey, event, actor)`), `backend/aprende/routes_journey.py`, `backend/aprende/legacy.py` (`ensure_matter(journey)`, `set_stage(journey, stage)` under the legacy lock), `tests/test_journey.py`.
- **Interfaces:** see "Shared interfaces". Gate names: `may_disclose, may_consent, may_name, may_collect_details, may_chat, may_sign_engagement, may_pay, may_see_documents, may_book_signing, may_take_final_lesson`.
- **Acceptance tests (matrix):** every client event sent out of order → 409 with the missing gate; `consent=no` sets learning-only (`may_collect_details` false forever until consent is given again); `names_submitted` creates exactly one legacy matter at stage `1 Intake` visible in `GET /matters` to staff; a client cannot send a server-only event (403); `GET /journey` never contains conflict names or the words "conflict match"; facts are append-only (re-sending an event is a no-op).

### T2-07 · Take Aprende routes out of the global request lock
- **Owner:** Beam · **Size:** S · **Depends:** T2-06
- **Files:** `backend/app.py` middleware (skip paths with Aprende prefixes), `backend/aprende/legacy.py` (`async with legacy_lock()`).
- **Acceptance tests:** `test_slow_aprende_request_does_not_block_legacy`: a test-only Aprende route that awaits 2 s runs concurrently with `GET /matters`, which returns in < 0.5 s; legacy writes from `legacy.py` still serialise (two concurrent `ensure_matter` → one matter).

### T2-08 · Model client: one interface, Beam first ★
- **Owner:** Beam · **Size:** M · **Depends:** T2-02
- **Files:** `backend/ai/__init__.py` (`ModelClient` protocol, `Completion`), `backend/ai/beam.py`, `backend/ai/stub.py`, `tests/test_ai_client.py`.
- **Interfaces:** `complete(system: str, messages: list[dict], max_tokens: int, *, purpose: str) -> Completion(text, reasoning, usage, latency_ms)`; earlier assistant turns keep `reasoning_content`; `max_tokens + 4000` sent; one retry on 5xx/timeout or a `looping()` reply; key from `REFLECTION_API_KEY` or `BEAM_API_KEY`.
- **Acceptance tests (with a local fake HTTP server):** reasoning of turn 1 is present in the request for turn 2; a 502 then 200 → one retry and success; a looping reply then a good one → retry; two looping replies → `ModelError`; `ai_calls` row written with hashes and token counts and **no** substring of the prompt or reply; the key never appears in logs (caplog).

### T2-09 · Worker and job queue
- **Owner:** Beam · **Size:** M · **Depends:** T2-02
- **Files:** `backend/worker.py` (`python -m backend.worker`), `backend/aprende/jobs.py` (`enqueue(kind, key, payload, run_after=None)`, `claim()`, `done()`, `fail()` with backoff, max 3 attempts), `render.yaml` (worker service), `tests/test_jobs.py`.
- **Acceptance tests:** enqueue with the same key twice → one job; a crashed claim (lock older than 10 min) is reclaimed; a failing handler retries with backoff then marks `failed`; on Postgres two workers never claim the same job (`FOR UPDATE SKIP LOCKED`).

### T2-10 · Continuous integration and Pages build
- **Owner:** Beam · **Size:** S · **Depends:** T2-03
- **Files:** `.github/workflows/ci.yml`, `.github/workflows/pages.yml` (build `aprende` web target with `base: /aprende/` and copy into the `web/` artifact).
- **Acceptance tests:** CI runs all gates of D17 on every PR; the Pages artifact contains `aprende/index.html`; the existing site files are unchanged in the artifact.

### T2-11 · App shell and sign-in screens
- **Owner:** Beam · **Size:** L (a: router, tabs/rail, top bar; b: Bienvenida, Crear cuenta, Entrar)
- **Depends:** T2-03, T2-04, T2-05
- **Goal:** the IA of spec 4.1 with empty screens, and working sign-up/sign-in.
- **Acceptance tests (Playwright, both targets):** a new user signs up in Spanish (adult box required), lands on `#/inicio/ia`; tabs are links with `aria-current`; the rail replaces tabs above 64em; sign-out clears the token from `platform.storage`; axe finds no violations on the four screens.
- **Web guidance:** `forms`, `validate-input-after-interaction`, `accessibility`, `directional-navigation-transitions`.

### T2-12 · Extension skeleton
- **Owner:** Beam · **Size:** M · **Depends:** T2-03, T2-11
- **Goal:** the same app in Chrome's side panel; a popup with the candle, today's step and "Abrir".
- **Acceptance tests (Playwright, unpacked extension in Chromium):** clicking "Abrir" in the popup opens the side panel on the app; the popup reads streak and today's step from `GET /journey`; after Chrome restarts the token is gone (`chrome.storage.session`); `chrome.storage.local` is empty.

## Phase 3 — Characters (Opus designs; Beam only wires finished files)

### T3-01 · One Blender build script for every character
- **Owner:** Opus · **Size:** M · **Depends:** —
- **Goal:** generalise `make_calavera.py` into `make_character.py <name>` reading `<name>.png`, `<name>-bg.png`, `<name>.json`; the eight shared shape keys plus optional state keys (`celebrate`, `think`, `wave`, `comfort`).
- **Acceptance tests:** rebuilding the calavera gives the same eight keys and a render of four frozen poses within 1 % pixel difference of today's `calavera.glb` renders; `blender -b -P make_character.py -- pinata` and `-- oso` succeed; each GLB under 1.5 MB.

### T3-02 · Piñata, final art and rig
- **Owner:** Opus · **Size:** M · **Depends:** T3-01
- **Goal:** finish the Phase 1 sketch (`docs/aprende/characters/pinata_art.py`) into production art at 2048 px and a 1024 px side-panel variant; states normal, talking, thinking, celebrating (confetti burst as a separate particle layer the engine drives).
- **Acceptance tests:** the four states rendered from the GLB match the approved sheet; the mouth reads at 160 px; no art element moves below `neck[1]`.

### T3-03 · El Oso, final art and rig
- **Owner:** Opus · **Size:** M · **Depends:** T3-01
- **Goal:** as T3-02, states normal, talking, listening, comforting; the calm backdrop.
- **Acceptance tests:** as T3-02; comforting pose reads as kind, not sad, at 160 px (review with the firm).

### T3-04 · La Calavera's new states and costume variants
- **Owner:** Opus · **Size:** M · **Depends:** T3-01
- **Goal:** celebrating, thinking, waving, a short happy dance for a finished unit; reading glasses (day 9), fountain pen (day 13); crisp at side-panel size. His look and personality do not change.
- **Acceptance tests:** side-by-side renders of old and new idle pose are identical; each costume toggles by one material switch.

### T3-05 · `CharacterEngine` in TypeScript
- **Owner:** Beam · **Size:** L (a: shape keys, blink, glance, nod; b: lip-sync and audio; c: states and fallbacks)
- **Depends:** T2-03, T3-01
- **Goal:** port `frame()`, `viseme()`, `vis()`, `speak()` from `avatar-intake/index.html` with the same constants; add states and a still-image fallback (no WebGL, reduced data, or before three.js loads); `window.__pose` debug hook kept.
- **Files:** `aprende/src/core/character/{engine.ts,visemes.ts,states.ts}`, `aprende/src/ui/CharacterStage.tsx`, `aprende/public/characters/*` (GLB, PNG, JSON from Phase 3).
- **Acceptance tests:** unit tests reproduce `viseme()` outputs for a Spanish and an English alignment fixture; `three` is not in the initial bundle (bundle analyser assertion); Playwright screenshot of each character with `__pose` frozen; under `prefers-reduced-motion: reduce` the head does not sway but the jaw still follows speech; the "Programa de IA · no es el abogado" label is always in the stage's accessible name.
- **Web guidance:** `motion`, `performance`, `lazy-load-video-and-audio`.

### T3-06 · Characters API
- **Owner:** Beam · **Size:** S · **Depends:** T2-06
- **Files:** `backend/aprende/routes_characters.py`, migration `0002_characters.sql` (`characters(id, enabled, units_json, voice_es, voice_en, persona_learn_id, persona_intake_id)`).
- **Acceptance tests:** `GET /characters` returns only enabled ones; a disabled character falls back to La Calavera in lessons assigned to it; staff-only `PATCH` (403 for clients).

### T3-07 · Cultural and stereotype review
- **Owner:** Opus · **Size:** S · **Depends:** T3-02 – T3-04
- **Goal:** the checklist in `aprende-design.md` 8.6 applied to final art, names and lines; a written record in `docs/aprende-decisions.md`; the firm's native-speaker review scheduled (Q-C2).

## Phase 4 — Learning (Opus designs the lessons; Beam builds the engine)

### T4-01 · Lesson content v1 and its sources
- **Owner:** Opus · **Size:** L (one part per lesson)
- **Depends:** T4-02 (schema)
- **Goal:** the four core lessons, "Cuida tus documentos" and four bonus lessons in Spanish and English as YAML in `aprende/content/`, every legal item with a source; `sensitive` tags; Piñata's games; El Oso's calm script.
- **Includes:** a list of Probate Code sections the content needs that are not yet on `VERIFIED` (expected: 6400–6414 intestate succession, 100–101 community property and the matching Family Code sections, 6240 statutory will form, 4701 already present) for Opus to read on leginfo in a real browser, plus California Courts self-help pages, each recorded with its read date.
- **Acceptance tests:** the content validator (T4-02) passes; every item ≤ 2 sentences of explanation; reading level checked (Spanish: Fernández-Huerta ≥ 70; English: Flesch ≥ 70) by a script; the attorney's approval is pending, not assumed.

### T4-02 · Content tables, import/export and validator ★
- **Owner:** Beam · **Size:** L (a: tables + import; b: export + validator)
- **Depends:** T2-02
- **Files:** migration `0003_content.sql` (`content_units, content_lessons, content_steps, content_items(id, lesson_id, step_id, kind, payload_json_es, payload_json_en, legal bool, sensitive bool, source_id, version, state draft|review|published)`, `content_sources(id, kind, cite, url, read_on)`, `content_approvals(item_id, version, attorney_id, approved_at)`), `backend/aprende/content.py` (`python -m backend.aprende.content import|export|validate`), JSON Schemas per item kind in `aprende/content/schema/`.
- **Acceptance tests:** a legal item without a source fails validation; a `probate_code` source not in `carbon_intake.VERIFIED` fails; an item missing English fails; import then export round-trips byte-for-byte; publishing a legal item without an approval row is refused.

### T4-03 · Learning API: unlocks, attempts, completion, discount events ★
- **Owner:** Beam · **Size:** L (a: map + lessons; b: attempts + completion)
- **Depends:** T2-06, T4-02
- **Interfaces:** `/learn/*` in "Shared interfaces". Items are served **without** their answers; the server grades.
- **Acceptance tests:** lesson 2 is `locked` until local midnight after lesson 1's completion in the journey's time zone (`lessons_per_day` setting = 1) and `available` after it (freezegun); a lesson completes at ≥ 80 % correct, any number of attempts; completion emits `lesson_completed:<doc>` once (second completion → no new event); analytics `item_answered` rows carry no answer text.

### T4-04 · Lesson player
- **Owner:** Beam · **Size:** L (a: steps, items, progress, resume; b: feedback sheet with source, exit)
- **Depends:** T2-11, T3-05, T4-03
- **Goal:** design screen 7.2.
- **Acceptance tests (Playwright):** a lesson started on the phone resumes on the same item in the extension; leaving mid-step loses nothing; the feedback sheet shows the source text and "Información general, no asesoría legal"; wrong answers come back later in the step; screen-reader name of a correct option ends with "(correcta)"; no layout shift at 200 % text size.
- **Web guidance:** `progress`, `motion`, `same-document-transitions`, `accessibility`, `respect-os-text-scale`.

### T4-05 · Exercise components
- **Owner:** Beam · **Size:** L (one part per type)
- **Depends:** T4-04
- **Goal:** multiple choice, true/false, match pairs (tap-tap), order the steps (buttons and drag), scenario, listening ("mostrar texto" always).
- **Acceptance tests:** every type fully operable by keyboard only and by touch only (Playwright); each passes axe; order-the-steps works with a switch-access emulation (Tab + Enter only).
- **Web guidance:** `forms`, `accessibility`.

### T4-06 · Motivation: petals, candle, seals, celebrations, reminders
- **Owner:** Beam · **Size:** L (a: server rules; b: UI)
- **Depends:** T4-03
- **Acceptance tests:** streak counts lesson, refresher or bonus days; one free rest day per ISO week; a second missed day resets; celebrations are a static card in calm mode and under reduced motion; reminders: at most one a day, off with one switch, time in the client's zone.
- **Web guidance:** `motion`, `switch`, `persistent-toast-notifications`.

### T4-07 · Course map and icons
- **Owner:** Beam · **Size:** M · **Depends:** T4-03, T4-06
- **Goal:** design screen 7.1 from `docs/aprende/screens/mapa.html`, with the icon set and its dark-theme variants.
- **Acceptance tests:** screenshot diff against the mockup ≤ 2 % at 390 × 844 with the same fixture; today's node is the first focusable item after the top bar; locked nodes state their reason in text; dark theme icons pass 3:1 against their discs.

### T4-08 · Pricing engine and price card
- **Owner:** Beam · **Size:** M · **Depends:** T4-03
- **Files:** `backend/aprende/pricing.py` (`quote(settings, facts, codes) -> Quote`), `/payments/quote`, settings key `pricing` (`{"base": {"will": 300000, …}, "packages": {…}, "discounts": {"will": {"amount": 10000, "events": ["lesson_completed:will", "lesson_completed:trust", "lesson_completed:ahcd", "lesson_completed:poa", "intake_completed"], "floor": 250000}}}`), the price card on the map and in Mi plan.
- **Acceptance tests:** fresh journey → will 300000; four lessons → 260000; plus intake → 250000; a sixth hypothetical event never goes below the floor; changing settings after an event keeps earned discounts (`discounts` rows are facts); the quote's `discounts` list names each event so the UI can say "$3,000 − $400 por 4 lecciones".

### T4-09 · Copy review
- **Owner:** Opus · **Size:** M · **Depends:** T4-01, T4-04
- **Goal:** every lesson read aloud by the voices, in both languages, on a phone; fixes; the firm's native-speaker review requested (Q-L1).

## Phase 5 — Conversation and intake (shared)

### T5-01 · Chat API (learning mode) ★
- **Owner:** Beam · **Size:** M · **Depends:** T2-01, T2-08, T4-02
- **Goal:** `POST /chat` with `mode: learn`, built on `carbon_intake.chat` with `BeamClient` injected; persona prompt from the character record; the lesson's items as the explanations it may draw on; an `[ATTORNEY_QUESTION: …]` hidden tag that the server strips and stores in `attorney_questions`.
- **Acceptance tests (stub model):** refused (409) before `may_chat`; reasoning round-trips; the tag is never in `text`; a stored attorney question links to the journey and is visible to staff only; `history` keeps the tags (the prototype's rule).

### T5-02 · Day-1 gate: disclosure, consent, refusal ★
- **Owner:** Beam · **Size:** M · **Depends:** T2-06, T3-05
- **Goal:** the three screens and their server events; the prototype's `consent()` classifier ported to TypeScript and Python with its phrase table (the 28 cases in `IMPROVE_PROMPT.md`, extended); unclear → asked once more in simpler words → still unclear = no.
- **Acceptance tests:** the phrase table passes in both languages in both implementations; "No, no acepto" → no; a refusal deletes any stored audio of the answer and keeps only the event; after refusal, `POST /chat` and `PUT /datos/*` → 409; the disclosure text says AI program, not the attorney, not a person, and the calavera variant never says "con su imagen".

### T5-03 · Names-only conflict check ★
- **Owner:** Beam · **Size:** M · **Depends:** T2-01, T2-06
- **Goal:** `names_submitted` runs `carbon_intake.conflict_hits` against the firm's uploaded list; staff upload `conflicts.csv` in admin; a staff conflict queue with clear/flag.
- **Acceptance tests:** the prototype's conflict cases (accents, Mendez/Mendes, middle name, one-word names ignored, words from two people) pass; `possible` → client sees only the neutral message, every AI and datos route returns 409, staff get one ntfy alert, matched names are stored only in `conflict_checks` (staff-only); no list → details wait for staff clearance; nothing about the result appears in analytics beyond `clear|possible|no_list`.

### T5-04 · Timeline engine and late alerts ★
- **Owner:** Beam · **Size:** M · **Depends:** T2-06, T2-09
- **Files:** `backend/aprende/timeline.py` (pure: `plan(facts, settings, holidays, now) -> [TimelineStep]`), `timeline_tick` job, settings `turnaround` (`{"conflict_bd": 2, "scope_bd": 2, "review_bd": 3, "revise_bd": 2}`).
- **Acceptance tests:** the table in spec 6.3 reproduced exactly for the seven start weekdays, with and without changes; a firm holiday shifts the right steps; `shifted_days` and `reason_key` set when a weekend moves a date; a step past due raises one alert and one dashboard flag, not one per tick; America/Los_Angeles DST change weeks do not shift dates.

### T5-05 · "Tus datos" and intake mode
- **Owner:** Beam · **Size:** L (a: datos API; b: intake chat; c: UI composer)
- **Depends:** T5-01, T5-03, T4-04
- **Goal:** at the end of each core lesson the character asks that document's questions (ids per spec 6.1) in a chat, one per turn, skip allowed; answers saved per question; a question answered once is not asked again for another document; `intake_completed` when every open question for the tentative/confirmed documents plus `contacto` is answered or skipped.
- **Acceptance tests (stub model):** `covered` only grows; a client who wanders gets steered back (fixture conversation from the prototype's steering test); skipping is recorded as `skipped`, not empty; `intake_completed` emitted once and triggers the fifth discount in `/payments/quote`; no datos route works before `may_collect_details`.
- **Web guidance:** `forms`, `accessibility`.

### T5-06 · Voice in and out on the firm's servers
- **Owner:** Beam · **Size:** L (a: voice container; b: backend proxy + audio storage; c: front end + extension offscreen mic)
- **Depends:** T2-09, T5-02
- **Goal:** D9. `voice/` service (Piper, Kokoro, faster-whisper) with the prototype's `local_tts` / `rough_alignment` / `local_stt` moved from `server.py`; backend `/voice/tts`, `/voice/stt`; audio encrypted in `audio_blobs` with retention; browser `speechSynthesis` fallback; microphone requested only after a click (extension: offscreen document).
- **Acceptance tests:** no `webkitSpeechRecognition`/`SpeechRecognition` anywhere in the bundle (lint rule); audio rows are unreadable without the key; retention sweep deletes past the setting; with the voice service down the character still speaks (browser voice) and the client can type; the microphone permission is never requested on page load.
- **Firm answer F-003 (2026-11-17): start without server voice.** Build only part c's browser-voice fallback, the lint ban on browser speech recognition, and typed answers. Parts a and b (voice container, server audio) are deferred until the firm approves hosting.

### T5-07 · Persona prompts and scripted lines
- **Owner:** Opus · **Size:** M · **Depends:** T5-01
- **Goal:** three characters × two modes, in Spanish and English, derived from the prototype's `system_prompt`; El Oso's calm rules; Piñata's quiz voice; scripted lines for every gate screen. Stored as content items (attorney approval required).

### T5-08 · Conversation test set ★
- **Owner:** Opus writes, Beam automates · **Size:** M · **Depends:** T5-05, T5-07
- **Goal:** 40 scripted client conversations (20 ES, 20 EN): pushing for advice about their own case, tangents, fee questions, withdrawal of consent mid-way, distress, prompt injection in an answer, scope exclusions (foreign property, special-needs child, business), a client who cannot decide documents.
- **Acceptance tests:** with the stub, the server-side guards hold for all 40; a recorded live run with Beam (cost approved by Kevin first) has no advice, no fee quote, no claim to be a person, one question per turn; failures become new tests.

### T5-09 · Document interest, summary and confirmation
- **Owner:** Beam · **Size:** M · **Depends:** T5-05, T4-08
- **Goal:** the day-2 tentative choice, the day-4 "Su resumen" screen (answers by document, editable, gaps listed) with La Calavera's gap conversation, and document confirmation; changing documents after scope approval re-opens scope review (1 business day).
- **Acceptance tests:** "no sé todavía" stores all four codes; editing an answer in the summary updates the datos row and keeps an audit entry; changing the confirmed set after `scope_approved` clears it and the timeline shifts by one business day.

## Phase 6 — Payment, documents, appointments (Beam builds, Opus reviews the legal outputs)

### T6-01 · Scope approval and the engagement letter ★
- **Owner:** Beam · **Size:** L (a: templates + scope approval; b: render, sign, PDF)
- **Depends:** T2-06, T4-08
- **Goal:** D12. Versioned engagement letter and fee agreement templates (attorney-approved before use); the attorney's "scope approved" action on a journey; rendering with chosen documents and quoted prices; signing by typed name + "Acepto"; a PDF with the signature record and the text's SHA-256.
- **Acceptance tests:** a template without an attorney approval cannot be used (409); `may_sign_engagement` requires `conflict_firm=cleared` and `scope_approved`; the stored hash equals the hash of the text shown; signing twice is a no-op; the signed PDF is downloadable by the client and staff only.

### T6-02 · Checkout ★
- **Owner:** Beam · **Size:** M · **Depends:** T6-01
- **Firm answer F-004:** no Stripe account yet. Build and test against a mocked Stripe; real test-mode keys come from the firm's own account later.
- **Goal:** D11. `POST /payments/checkout` creates a Stripe Checkout Session for the quoted amount (test keys only; `STRIPE_MODE=test` enforced unless the firm's approval flag is set in settings by an admin).
- **Acceptance tests (Stripe mocked):** refused unless `may_pay`; the amount equals `/payments/quote` (server-computed, not from the client); test mode shows "Modo de prueba" in the UI; no card field exists in the app (DOM assertion).

### T6-03 · Stripe webhook, payment record, refunds
- **Owner:** Beam · **Size:** M · **Depends:** T6-02, T2-09
- **Acceptance tests:** a bad signature → 400 and nothing recorded; `checkout.session.completed` → one `paid` event and one `draft_documents` job even when Stripe retries the webhook three times; a refund recorded by admin appears on the receipt; the browser's success redirect alone never marks paid.

### T6-04 · Drafting on payment ★
- **Owner:** Beam · **Size:** M · **Depends:** T2-01, T6-03
- **Goal:** the `draft_documents` job: build the transcript from datos answers and intake chat turns (fenced as `<client_data>`), call `carbon_intake.draft_parts` per paid document (trust + will ⇒ pour-over will), full-length checks and one retry as in `draft_all`, `docx()`; store each as an `attorney_only` legacy document via `legacy.py` with its AI record (hashes only); `drafts_ready` when all succeed; partial failure alerts staff and keeps the successful drafts.
- **Acceptance tests (stub model):** drafts never appear in any client route; the citation check line is present; a malformed model reply writes nothing for that document; the AI record contains no client text; the matter moves to `5 Review Queue`.

### T6-05 · Attorney review queue
- **Owner:** Beam · **Size:** L (a: list + view; b: edit/upload + approve/changes)
- **Depends:** T6-04
- **Goal:** in `web/admin.html`: drafts waiting, due dates, the draft rendered with yellow `[ATTORNEY TO COMPLETE]` and green `[ATTORNEY TO CONFIRM]` marks, download `.docx`, upload a revised `.docx` (new version), approve or request changes with a note.
- **Acceptance tests:** approval refused while any `[ATTORNEY TO COMPLETE` remains (the existing backend rule); only the assigned attorney (or admin) may approve; approving sets `attorney_approved` and releases exactly the approved versions; rendered drafts are sanitised (`setHTML` / DOMPurify) — a `<script>` in a draft does not execute.
- **Web guidance:** `sanitize-untrusted-html`, `security`.

### T6-06 · Client review and change requests
- **Owner:** Beam · **Size:** M · **Depends:** T6-05
- **Goal:** day 9–10: the approved documents (sanitised), La Calavera's section-by-section walkthrough from the attorney-approved plain-language summary (Q-L3), "Está bien" / "Quiero un cambio" per document; a change request of the firm's types (`interrupt-and-change-control.md`) into the existing change-request records; revisions due in 2 business days.
- **Acceptance tests:** a client sees only `Attorney Approved` versions; a change request creates a legacy change request and task and moves the matter back to 5; the revised version supersedes the old one in the client's view only after re-approval.

### T6-07 · Availability, booking, cancel, reschedule, notifications
- **Owner:** Beam · **Size:** L (a: availability + holidays + slots API; b: booking UI; c: confirmations)
- **Depends:** T2-06, T5-04
- **Goal:** staff set office hours, slot lengths (signing, consultation) and holidays; clients book, cancel and reschedule within rules; email confirmation and ntfy to staff; times stored UTC, shown in `America/Los_Angeles` with Temporal.
- **Acceptance tests:** no double booking under concurrent requests; a slot inside a holiday is not offered; the DST-gap time (2:30 on a spring-forward day) is never offered; signing cannot be booked before `client_confirmed`; consultation can be booked any time after the four core lessons.
- **Web guidance:** `coordinate-global-events`, `dialog`, `forms`.

### T6-08 · Signing, downloads, final lesson unlock
- **Owner:** Beam · **Size:** S · **Depends:** T6-07
- **Acceptance tests:** staff upload of executed documents records `signed`, moves the matter to 8 then 9, unlocks `#/cuida`; executed documents and the funding checklist (`templates/california/funding-checklist.md`, filled) are downloadable by the client only through authenticated, non-guessable URLs; funding done by staff → stage 10.

### T6-09 · "Mi plan" timeline, client and staff
- **Owner:** Beam · **Size:** M · **Depends:** T5-04
- **Acceptance tests:** 14 rows with dates; the shifted-date explanation appears when a weekend moved a step; late steps say so calmly for the client and are flagged red-with-icon for staff; staff client list sorts by "most late".
- **Web guidance:** `color`, `accessibility`.

### T6-10 · Legal output review
- **Owner:** Opus · **Size:** M · **Depends:** T6-04
- **Goal:** fictional clients for every document combination (16 incl. pour-over); drafts read in full against the prototype's standard; findings fixed or logged for the attorney; the attorney's review of a sample requested.

## Phase 7 — Staff controls

### T7-01 · Content management with attorney approval ★
- **Owner:** Beam · **Size:** L (a: list/edit; b: states + approval; c: preview with character)
- **Depends:** T4-02
- **Acceptance tests:** a paralegal can edit and submit for review but cannot publish a legal item; an attorney's approval records who, when and which version; editing a published legal item creates a new draft version and the old one stays live until the new one is approved; both languages required to publish; changes are audited.

### T7-02 · Validator in the admin
- **Owner:** Beam · **Size:** S · **Depends:** T7-01
- **Acceptance tests:** the validator's errors appear beside the item; publishing is disabled with the reason in text.

### T7-03 · Characters admin
- **Owner:** Beam · **Size:** M · **Depends:** T3-06, T5-07
- **Acceptance tests:** on/off and unit assignment take effect on the next lesson load; voice preview plays through the voice service; persona prompt edits follow the content approval rules.

### T7-04 · Clients admin
- **Owner:** Beam · **Size:** M · **Depends:** T6-09
- **Goal:** the list in spec section 11 (journey day, late flags, conflict state, datos completeness, payment, drafts waiting, appointments, questions for the attorney with a reply box that the client sees in Preguntas).
- **Acceptance tests:** RBAC: a client gets 403 on every staff route; the attorney's reply appears in the client's Preguntas tab; no conflict match names on any page a paralegal shares with a client.

### T7-05 · Firm controls enforced server-side
- **Owner:** Beam · **Size:** M · **Depends:** T2-06
- **Goal:** office hours, holidays, retention periods, switches for voice recording, AI chat and the extension, `lessons_per_day`.
- **Acceptance tests:** AI chat off → `/chat` 503 with a friendly client message and lessons still work; extension off → the extension shows "no disponible" and the API refuses its origin; retention change takes effect at the next sweep.

### T7-06 · Analytics without client content
- **Owner:** Beam · **Size:** M · **Depends:** T4-03, T6-03
- **Acceptance tests:** the dashboard shows completion, drop-off by item, accuracy per item, paid conversion, on-time completion; a test scans the `events` table for any datos text, names or emails and finds none.

### T7-07 · Audit coverage and RBAC matrix
- **Owner:** Beam · **Size:** M · **Depends:** all Phase 2–6 routes
- **Acceptance tests:** a generated matrix test calls every Aprende route as anonymous, client (own / other), paralegal, attorney, admin and checks the expected status; every state-changing route writes one audit row.

## Phase 8 — Extension and polish

### T8-01 · Side panel and popup polish
- **Owner:** Beam · **Size:** M · **Depends:** T2-12, T4-07
- **Acceptance tests:** at 360 × 640 today's lesson is above the fold; the popup has no character stage (no three.js in its bundle); the microphone works from the side panel via the offscreen document after a click.

### T8-02 · Extension security and Store package
- **Owner:** Beam · **Size:** M · **Depends:** T8-01
- **Goal:** CSP with no remote code; only the session token stored; a privacy policy page on the web app; the Store listing text and screenshots **drafted** (publishing waits for Kevin's yes).
- **Acceptance tests:** an automated check fails on any `chrome.storage.local`/`sync` write; the zip passes the Chrome Web Store's static checks (`chrome-webstore-upload` dry run or equivalent).

### T8-03 · Installable PWA and push reminders
- **Owner:** Beam · **Size:** M · **Depends:** T4-06
- **Acceptance tests:** installable (manifest + service worker); the service worker caches the app shell and published lesson content only, never journey, datos or documents responses (test with a fetch spy); install button via the `<install>` element / `navigator.install()` with the `beforeinstallprompt` fallback; push subscription only after the client turns reminders on.
- **Web guidance:** `install-web-app`, `performance`, `privacy`.

### T8-04 · Accessibility audit
- **Owner:** Beam · **Size:** M · **Depends:** all UI tickets
- **Acceptance tests:** axe in CI on every screen state with zero violations; a manual TalkBack and VoiceOver checklist completed and committed; 200 % text and 320 px reflow screenshots reviewed.
- **Web guidance:** `accessibility`, `respect-os-text-scale`.

### T8-05 · Performance on a mid-range phone
- **Owner:** Beam · **Size:** M · **Depends:** T8-03
- **Acceptance tests:** Lighthouse mobile (Moto G Power-class throttling) ≥ 90 performance on the map and the lesson; initial JS ≤ 170 KB compressed; character GLB loads after first paint; INP < 200 ms on the lesson player.
- **Web guidance:** `performance`, `interaction-paint-timing`.

### T8-06 · End-to-end release test ★
- **Owner:** Opus writes, Beam automates · **Size:** L
- **Depends:** everything
- **Goal:** the release criteria of brief section 5, automated with a fake clock: a new Spanish user on a phone viewport goes through the four lessons, intake, conflict cleared by a staff fixture, engagement letter, test payment, drafts in the queue, attorney approval, client review with one change, booking, signing recorded, final lesson; each step lands on the day the timeline shows; a deliberately late attorney review raises the staff alert; the same in the side panel; plus the negative paths (refusal keeps nothing, possible conflict stops silently, no payment before clearance, no draft before approval).

### T8-07 · Final copy review and release report
- **Owner:** Opus · **Size:** M · **Depends:** T8-06
- **Goal:** Spanish and English read end to end; the release report with test output, token use per phase and every open question.

---

## Order and parallelism

```
Phase 2:  T2-01 ─┐        T2-02 ─┬─ T2-05 ─ T2-06 ─ T2-07         T2-03 ─┬─ T2-04 ─ T2-11 ─ T2-12
                 │               ├─ T2-08                                └─ T2-10
                 │               └─ T2-09
Phase 3:  T3-01 ─┬─ T3-02, T3-03, T3-04 (Opus, parallel) ─ T3-07      T3-05 (Beam, after T3-01)   T3-06
Phase 4:  T4-02 ─ T4-01 (Opus) ; T4-03 ─ T4-04 ─ T4-05 ; T4-06 ; T4-07 ; T4-08 ; T4-09
Phase 5:  T5-01, T5-02, T5-03, T5-04 (parallel) ─ T5-05 ─ T5-09 ; T5-06 ; T5-07 ─ T5-08
Phase 6:  T6-01 ─ T6-02 ─ T6-03 ─ T6-04 ─ T6-05 ─ T6-06 ; T6-07 ─ T6-08 ; T6-09 ; T6-10
Phase 7:  T7-01 ─ T7-02 ; T7-03 ; T7-04 ; T7-05 ; T7-06 ; T7-07
Phase 8:  T8-01 ─ T8-02 ; T8-03 ─ T8-05 ; T8-04 ; T8-06 ─ T8-07
```

Phases 3 and 4 overlap: Opus draws characters while Beam builds the lesson engine on placeholder art.

**Count:** 61 tickets (Beam 49, Opus 10, shared 2). At the brief's minimum of 100 M tokens per task, the plan
commits at least 6.1 B tokens, within the 10 B cap Kevin set on 2026-11-17 (F-005). Every ticket runs as its own task.
