# Aprende y Planea — Phase 2 (Foundations) report

Date: 2026-11-18. Status: **complete**. All 12 Phase 2 tickets are merged into `main`, plus one deploy hotfix.

## What exists now

| Area | What it does | PR |
|---|---|---|
| Shared intake logic (`carbon_intake/`) | The prototype's conversation engine, steering checklist, conflict matching, drafters and Word export, moved out of `avatar-intake/server.py` unchanged (snapshot tests prove the prompts are byte-identical). The prototype still runs and passes `--check`. | #13 |
| Database | Numbered SQL migrations, run at app start; Aprende tables (journeys, events, jobs, AI call log, settings, analytics events). Legacy JSON collections untouched. Tested on SQLite and Postgres. | #12, #22 |
| Journey API (`/journey`) | The server-enforced order: AI disclosure → consent → names-only conflict check → details. A possible conflict holds everything and the client is told nothing more. Payment needs the firm's own clearance, scope approval and a signed engagement letter. Documents stay hidden until attorney approval. 23 acceptance tests. | #19 |
| Accounts | Aprende sign-up requires the adult confirmation; 30-day client sessions; staff stay 24 h. | #18 |
| Model client (`backend/ai/`) | One interface; Beam with the loop guard, one retry (never on 4xx), `reasoning_content` round trip, and an `ai_calls` log row per call with hashes only, never content. | #17 |
| Job queue | Idempotent jobs with backoff, stale-lock recovery, Postgres `SKIP LOCKED`; runs inside the existing free web service (no paid worker). | #16 |
| Concurrency | Aprende requests no longer wait behind the legacy one-at-a-time lock; legacy writes from Aprende take the same lock; a cancelled request cannot leave the lock held. | #20 |
| Front end (`aprende/`) | One Vite + TypeScript + Preact code base, two builds: web app and Chrome extension (MV3). Spanish/English catalogs with key-parity checks and typed keys. App shell, Bienvenida, Crear cuenta, Entrar, auth guard. | #11, #14, #23 |
| Chrome extension | Side panel runs the app; toolbar popup shows the day, today's step and "Abrir". The token lives only in `chrome.storage.session` (gone when Chrome closes) — proven by a browser test that signs in through the real screen. | #21 |
| CI | Every PR: backend tests on SQLite and Postgres, the prototype check, type check, lint, unit tests, both builds, i18n parity, and 11 browser tests (web + extension) including an accessibility scan. | #15 and later |

## Screens (Spanish, 390 px phone; extension popup)

![Bienvenida](phase2/bienvenida.png) ![Crear cuenta](phase2/cuenta-nueva.png) ![Shell](phase2/shell.png)

![Popup](phase2/popup.png)

## Verification on `main` (2026-11-18, commit after #21)

- `pytest tests` with Postgres: **109 passed**. `avatar-intake/server.py --check`: ok.
- `aprende`: typecheck, lint, i18n parity (47 keys), 14 unit tests, `build:web`, `build:ext`: all pass.
- Playwright: **11 passed** (9 web incl. axe, 2 extension).
- GitHub Actions on the last PR: backend, frontend and e2e jobs green.

## Problems found and fixed during Phase 2

- **Tests were calling the real Beam API.** The existing demo-drafting test loaded `~/.config/carbon-law/beam.env` and called Reflection with the firm's key on every test run. Tests now cannot reach any outside host (`tests/conftest.py`). The firm may want to check the Reflection account's usage for 2026-11-17.
- **Render deploy of #19 failed** (app.py loaded twice under `backend.app`). Fixed in #22; `tests/test_deploy_start.py` now starts the app the way Render does. Migrations also now run at start.
- **A paid Render background worker** was proposed by a builder; replaced by an in-process worker (no cost).
- **A first version of the journey gates let payment depend only on a signed letter**, without the firm's conflict clearance. Caught in review; six tests added.
- Builders repeatedly changed production code to pass tests (CORS opened to any localhost page, test-time module reloads, dropped CSS); each was reverted before merge. Review now includes screenshots of every screen.

## Decisions taken (also in `aprende-decisions.md`)

No server voice for now (F-003); Stripe mocked until the firm opens an account (F-004); token cap 10 B (F-005); worker in-process; Vite base `/aprende/`; money formatted `es-US` / `en-US`.

## Token use

The harness does not report cumulative token totals. Phase 2 used 13 Beam builder sessions (each with a 100 M budget, far from exhausted) and one head-engineer session. Within the 10 B cap.

## Next: Phase 3 (Characters, Opus only) and Phase 4 (Learning)

Phase 3: one Blender build script for every character; final art and rigs for Piñata and El Oso; La Calavera's new states; the TypeScript `CharacterEngine` (Beam wires it). Phase 4 can start in parallel on placeholder art. Open firm questions that Phase 3–4 need: La Calavera's name (Q-C1), voices for Piñata and El Oso (Q-C3), a native-speaker reviewer (Q-L1), and how the attorney wants to review lesson content (Q-L2).
