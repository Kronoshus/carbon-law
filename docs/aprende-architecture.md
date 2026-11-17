# Aprende y Planea — architecture decision

Phase 1 deliverable. Status: **proposed**; becomes binding when Carbon Law approves Phase 1. Every later change to a
decision here is recorded in `aprende-decisions.md`.

## 1. Context: what is there today

| Piece | Finding | Consequence |
|---|---|---|
| `backend/app.py` (FastAPI 0.115, ~1,460 lines) | Roles client/paralegal/attorney/admin, bearer-token sessions (24 h), matters, workflows, appointments, documents, change requests, tasks, audit. 35 passing tests. | Extend it; do not build a second backend (brief section 3). |
| `backend/db.py` | Persists each collection as **one JSON blob** in a `collections` table (SQLite locally, Postgres on Render). `schema.sql` describes relational tables that the app does **not** use. | Fine for a few hundred matters; wrong for per-item learning progress, analytics events and concurrent chat. New domains need real tables. |
| Request middleware | **Every request except `/health` runs under one global `asyncio.Lock`**, because handlers mutate shared dicts. | A 3-second Beam chat turn or a 5-minute draft would freeze the whole backend. New routes must not hold this lock. |
| Workflow order | The existing client workflow generates drafts with status *Client Review* **before** attorney approval (`POST /workflows/{id}/drafts`, then `client-review`, then `attorney-review`). | Opposite of the brief ("the client never sees a draft until the attorney approves it"). Aprende uses its own journey with attorney-first ordering; the old portal flow is a question for the firm (Q-X1). |
| `avatar-intake/server.py` | The proven conversation engine, conflict check, drafters (`DOCS`, `VERIFIED`, `drafter`, `draft`, `draft_all`, `docx`), all covered by `--check`. Standard library only. | Port by **moving** this code into a shared package both the prototype and the backend import; do not rewrite or fork it. |
| `avatar-intake/index.html` | The animation engine: 8 shape keys, letter-timed lip-sync, blink, glances, nodding. | Port into a TypeScript `CharacterEngine` with the same parameters. |
| `web/` on GitHub Pages (`carbon.bailment.tech`), API on Render (`carbon-law.onrender.com`), `render.yaml` free plan | Static site + one web service. | The app is built into the same Pages artifact; voice needs more than the free plan (Q-S1). |

## 2. Decisions

### D1. One front end, two build targets
`aprende/` at the repo root: **Vite + TypeScript (strict) + Preact + @preact/signals**, plain CSS with the design
tokens (CSS layers, no CSS framework), hash routing.

```
aprende/
  src/core/        api client, journey state, i18n, timeline view-model, lesson engine, exercises, character engine
  src/ui/          components (design system), screens
  src/platform/    interface: storage, microphone, notifications, openUrl, audio  (no chrome.* or window-only APIs in core)
  src/targets/web/        main.ts, service worker, manifest  → dist/web     (PWA)
  src/targets/extension/  sidepanel.ts, popup.ts, background.ts, offscreen.ts, manifest.json → dist/extension (MV3)
  content/         v1 lesson content authored by Opus (YAML), imported into the backend
  i18n/es.json, i18n/en.json
  tests/           vitest unit, playwright e2e (web + extension)
```
*Why Preact:* about 4 KB, JSX that Beam writes reliably, fast on low-end Android. *Rejected:* React (size), plain web
components (more hand-written plumbing per screen for the builders), Svelte (fine, but less predictable output from
Beam). A lint rule forbids `src/core` and `src/ui` from importing `src/targets/*`; business logic exists once.

### D2. Characters: one engine, lazy three.js
`CharacterEngine` ports `frame()`/`speak()` from `index.html`: the eight shape keys, lip-sync from per-letter timings,
blink, glances, nod-while-listening, plus a state layer (idle, talking, thinking, celebrating, comforting) driven by
optional extra shape keys. three.js is a dynamic import loaded only when a stage mounts; every character also ships a
still PNG used before WebGL loads, under reduced data, or when WebGL is missing. GLBs are built by Blender scripts in
the repo (Opus only, Phase 3).

### D3. Extend the FastAPI backend with a new package
`backend/aprende/` holds routers mounted from `app.py` with a few lines: `/journey`, `/learn`, `/content`,
`/characters`, `/chat`, `/voice`, `/drafts`, `/payments`, `/availability`, `/settings`, `/analytics`. Staff screens are
new sections of `web/admin.html` / `admin.js`.

### D4. Real tables for new domains, via migrations; legacy collections untouched
Numbered SQL files in `backend/migrations/` in the SQL subset SQLite and Postgres share (tests run on both), applied
by a tiny runner (`backend/migrate.py`, table `schema_migrations`). New tables include: `journeys`, `journey_events`,
`content_units/lessons/items/sources/approvals`, `lesson_progress`, `item_attempts`, `datos_answers`, `chat_turns`,
`attorney_questions`, `conflict_checks`, `price_rules`, `discounts`, `engagement_letters`, `payments`, `jobs`,
`ai_calls`, `events`, `availability`, `holidays`, `settings`, `audio_blobs`, `push_subscriptions`.
The existing JSON collections stay exactly as they are; `schema.sql`'s unused tables are left alone and documented as
unused. **The bridge** to the legacy world is one module, `backend/aprende/legacy.py`: it creates/updates the matter (so
staff see the client and the stage in the existing dashboard), stores drafts as `attorney_only` documents, and creates
appointments — always inside the legacy lock.

### D5. The global lock applies only to legacy routes
The middleware keeps serialising legacy paths; Aprende paths skip it and use database transactions. `legacy.py`
acquires the same lock for its short legacy writes. Slow work (Beam drafting, voice) never runs inside a request.

### D6. Shared intake logic: `carbon_intake/`
A stdlib-only package at the repo root, created by **moving** (not copying) from `avatar-intake/server.py`:
`questions`, `system_prompt`, `sentences`, `looping`, `spoken`, `checklist`, `chat` (with the model call injected),
`UNTRUSTED`, `SUMMARY`, `VERIFIED`, `DOCS`, `drafter`, `unverified_cites`, `instrument_words`, `draft` (parts, joins,
checks), `docx`, `fold`, `conflict_hits`, `BANNER`, `NOTICE`. `server.py` imports them and keeps its HTTP handler,
voice and session files; `python server.py --check` must still print `ok`. The backend imports the same functions.
The guion files move to `carbon_intake/guiones/` with a link left in `avatar-intake/`.

### D7. Model access: one interface, Beam first
`backend/ai/`: a `ModelClient` protocol (`complete(system, messages, max_tokens, purpose) → Completion(text,
reasoning, usage, latency_ms)`), `BeamClient` (OpenAI-compatible; `reasoning_content` sent back for earlier turns;
`max_tokens + 4000` for reasoning; one retry; `looping()` guard; 900 s timeout only for drafting) and `StubClient` for
tests. Every call writes an `ai_calls` row: purpose, model, tokens, latency, estimated cost, request/response hashes —
never content. The key comes from `REFLECTION_API_KEY` or `BEAM_API_KEY` on the server only.

### D8. A worker for slow jobs
`backend/worker.py`, a second process from the same code. Jobs in the `jobs` table (claimed with
`FOR UPDATE SKIP LOCKED` on Postgres): `draft_documents`, `tts`, `stt`, `send_email`, `send_push`, `timeline_tick`
(late-step detection every 15 minutes), `retention_sweep`. Idempotent by job key, so a crash and restart converge.

### D9. Voice on the firm's servers
A `voice` service (Docker: Piper `es_MX-ald-medium`, Kokoro `am_adam`, faster-whisper `small`, CPU) reachable only
from the backend, returning the prototype's `{audio_base64, mime, alignment}` shape. It needs about 2 GB of RAM, which
the free Render plan does not have (**Q-S1**). Until it exists: the browser's own speech synthesis speaks (on-device;
lip-sync falls back to word boundaries as in the prototype), and answers are typed. **Browser speech recognition is
not used** — Chrome sends that audio to Google, which breaks "audio stays on the firm's servers".

### D10. Accounts and sessions
Reuse the existing users and sessions. Clients sign up through the existing `/auth/signup` plus an adult flag. Client
sessions become 30-day sliding (staff stay 24 h). Web app: an HttpOnly `__Secure-` session cookie if the API is moved
to a same-site name such as `api.carbon.bailment.tech` (**Q-S2**); until then a bearer token in `localStorage` behind a
strict Content-Security-Policy and Trusted Types. Extension: the bearer token in `chrome.storage.session` only (memory,
cleared when Chrome closes); nothing else stored. CORS gains the extension origin and PUT/DELETE.

### D11. Payments: Stripe Checkout + webhook
The backend creates a Checkout Session (prices from settings, the client's earned discounts applied server-side), the
client pays on Stripe's page, and only the signed webhook (`checkout.session.completed`) records `paid` and enqueues
drafting. Test-mode keys until the firm approves live (**Q-P1**). No card data touches the firm's servers or the extension.

### D12. Engagement letter signing in the app
The attorney-approved template (versioned) is filled with the chosen documents and prices, rendered, hashed
(SHA-256), shown in full, and signed by typed name + explicit "Acepto" + timestamp + IP + user agent; a PDF of the
signed letter is stored with the hash. Whether this suffices, or a DocuSign-type service is wanted, is the attorney's
call (**Q-P3**).

### D13. Notifications
Clients: Web Push (VAPID, free) from the PWA; `chrome.alarms` + `chrome.notifications` in the extension; email through
the existing `EMAIL_WEBHOOK_URL`. Staff: ntfy (already in the firm's stack) and the dashboard flag. One reminder a day
at the most; every channel can be switched off.

### D14. Time
All firm deadlines are computed server-side in `America/Los_Angeles` business days with a firm holiday list
(`backend/aprende/timeline.py`, a pure function; the spec's weekday table is its test vectors). Appointment times
are stored in UTC and shown with `Temporal.ZonedDateTime` (polyfilled where missing).

### D15. Content is data
Lesson content lives in the database after a one-time import of Opus's v1 YAML (`aprende/content/`). From then on staff
edit it in the admin pages, with draft → review → published states and attorney approval for legal items; an export
command writes YAML for review diffs and backups. The YAML in the repo is a seed, not a second source of truth.

### D16. Hosting and delivery
- Web app: built in CI and published in the same GitHub Pages artifact at `carbon.bailment.tech/aprende/`.
- Extension: CI builds a zip artifact; publishing to the Chrome Web Store waits for the firm's yes (brief section 7).
- Backend + worker + voice: Render (`render.yaml` gains the worker and voice services). The database stays on the existing `DATABASE_URL`; audio is stored encrypted (`audio_blobs`, key from a server secret) with a retention sweep.

### D17. Quality gates (CI)
One workflow, `.github/workflows/ci.yml`: backend pytest on SQLite and on a Postgres service container; migrations
up from empty; `avatar-intake/server.py --check`; `tsc --noEmit`, ESLint, vitest; i18n key parity; content validator;
Playwright end-to-end for the web target and for the extension (unpacked in Chromium); a bundle-size budget. Beam is
always stubbed in CI. Phase 8 adds an accessibility scan (axe) and a Lighthouse mobile run with budgets.

## 3. How the build team works

- Each backlog ticket is executed by a **Beam builder agent** (`reflection/Beam-1.0-501B-A23B`, reasoning *high*) spawned on its own branch, with the ticket text as its prompt and at least 100 M tokens of budget. Opus (head engineer) reviews every diff against the ticket, the guardrails and the tests, runs the suite, and merges. Tickets are sized to about 300 lines of change.
- Opus alone designs characters, writes lesson content and persona prompts, and reviews all legal outputs.
- Every Beam call made by the product goes through `BeamClient` (loop guard + one retry); builder agents are instructed to keep the same guards in any code that calls a model.

## 4. Risks

| Risk | Mitigation |
|---|---|
| Voice service cost/hosting not approved | D9 fallback works without it; voice is a setting |
| Beam loops or returns short drafts | prototype's guards and retry, ported intact; drafting runs in the worker with per-document retry |
| Lesson legal content needs statutes not yet verified | content cannot publish without a verified source; verification list in T4-01 |
| JSON-blob legacy store grows with Aprende clients | Aprende data is relational; legacy writes are one matter + its documents per client |
| Extension review by Chrome Web Store | minimal permissions (`sidePanel`, `storage`, `alarms`, `notifications`, `offscreen`; host permission for the API only), privacy policy page, no remote code |
