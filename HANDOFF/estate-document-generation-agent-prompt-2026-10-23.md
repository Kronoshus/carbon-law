# Agent prompt: Carbon Law estate demo documents and fresh-data test state

Work in `/home/dkkm10/carbon-law-gh`. Read `HANDOFF/README.md` and `HANDOFF/estate-document-generation-2026-10-23.md` before continuing. Begin with `git status --short --branch` and `git log -3 --oneline`.

## Current implementation

Commit `c262662` is pushed to `origin/main`; GitHub Pages deployment succeeded and Render auto-deployed the backend. The backend was restarted after the production reset. Attorney/admin estate demo generation, templates, document opening UI, and focused tests are implemented. Do not duplicate this work.

## Live data state

On 2026-10-23, production Neon `carbon_law` data collections were emptied in a transaction while preserving `users` (3 accounts). Sessions were cleared. Aggregate verification confirmed zero entries across all non-user collections; Render health returned `ok` after restart. Local SQLite collections were similarly cleared except for local users; the desktop `matters.csv` retains header only. The user's intent was to preserve all usernames/passwords/accounts. Do not delete users or restore data unless explicitly instructed.

## Security follow-up

A Composio Render environment-variable response exposed values for `DATABASE_URL`, `BEAM_API_KEY`, and `INITIAL_STAFF_SETUP_TOKEN` in tool context. The user was alerted by phone. Recommend rotating those credentials and reviewing access. Never repeat or print those values.

## Estate document behavior

- Four demo-only templates exist under `templates/california/demo/`; statute details are explicitly unverified. Never claim legally sufficient or signing-ready.
- `POST /workflows/{id}/attorney-demo-drafts` requires attorney/admin and a cleared conflict plus `draft_ready`; it persists versioned attorney-only drafts without advancing the workflow.
- The admin Documents table has an **Open document** expander for records with content. Metadata-only records say no draft is stored; opening does not generate one. Fresh documents must be generated from a ready workflow by an attorney/admin.
- Client/paralegal document access must remain blocked for attorney-only drafts.

## Validation history

Focused workflow/document tests passed (7 tests), as did Python compile, `node --check web/admin.js`, and `git diff --check`. Full test suite had 22 failures across auth/setup/workflow/persistence tests; do not report all tests passing. The 2026-10-23 data reset is verified.

## Next action

No implementation task is currently pending. If asked to test from scratch, preserve users, create only clearly fictional demo records, and verify after each step. Use an authorized login/browser flow; never seed production with real client information or call hosted Beam with real intake. If asked to reset production again, verify target project/branch/database and explicitly preserve `users`.
