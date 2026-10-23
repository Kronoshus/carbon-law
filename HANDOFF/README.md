# Carbon Law demo handoff

**Updated:** 2026-10-23
**Repository:** `Kronoshus/carbon-law`
**Current commit:** `c262662` — `feat: add attorney estate demo drafts`
**Git state at last check:** `main` matches `origin/main`; GitHub Pages deployment succeeded. The Render backend was restarted after the production data reset described below.

## Live links

- Website: <https://carbon.bailment.tech/>
- Sign in: <https://carbon.bailment.tech/login.html>
- Guided intake: <https://carbon.bailment.tech/intake.html>
- Client portal: <https://carbon.bailment.tech/portal.html>
- Staff admin: <https://carbon.bailment.tech/admin.html>
- Backend health: <https://carbon-law.onrender.com/health>

## Current data state (2026-10-23)

- The live Neon `carbon_law` production collections were reset. `users` was preserved (3 accounts); matters, workflows, documents, appointments, sessions, contacts, tasks, changes, communications, audit history, and stage history were emptied.
- The Render service was restarted after the transaction. Read-only verification showed zero entries in every non-user collection and `/health` returned `ok`.
- The local SQLite application collections were also cleared while preserving all 29 local users. `/mnt/c/Users/bestf/Desktop/matters.csv` was reduced to its original header row (14 columns, no data rows).
- This is a fresh test state. Do not restore old matters or sessions unless Kevin asks.

## Current workflow behavior

- Clients can create multiple planning workflows. The client portal lists workflows, their matter, status, selected documents, consultation/signing requests, and approval state.
- Portal **Modify planning request** opens that workflow at Part 2 using its workflow ID (`?workflow=...&part=2`).
- Appointment requests remain pending until staff approval; they do not themselves complete a workflow.
- Part 1 collects identity/contact and related names for conflict screening. Do not collect sensitive matter details before conflict review.
- `GET /my-workflows` returns a client's owned workflows; `GET /my-workflow` is used by the intake and staff views.

## Attorney estate demo drafts

- Four illustrative templates exist in `templates/california/demo/` (revocable living trust, pour-over will, advance health care directive, financial power of attorney). They are marked demo/simulation, attorney review required, not legally approved, not signing-ready, and not for client use.
- Generation is attorney/admin-only via the staff admin portal and `POST /workflows/{id}/attorney-demo-drafts`; client and paralegal access is denied. Drafts are attorney-only, versioned, and do not advance workflow approval state.
- Admin Documents now exposes stored content through an **Open document** expander. Metadata-only records explicitly show that no draft content is stored; opening documents does not generate missing content.
- California statute details remain unverified; see `templates/california/demo/README.md`. Never describe the templates as legally sufficient or signing-ready.
- Automated tests use fictional data and do not call hosted Beam. Never send real client information to Beam without firm approval and a documented privacy/redaction plan.

## Demo safety and credential handling

- This is a demo, not an active law-firm intake channel. Do not enter real client or confidential information.
- Simulated conflict review is not a database check or real clearance.
- Keep user accounts; sessions were cleared during the reset, so users may need to sign in again.
- A prior Render environment inspection returned secret values in a tool response. Rotate Render's database credential, `BEAM_API_KEY`, and `INITIAL_STAFF_SETUP_TOKEN`; do not copy their values into repository files, logs, or chat. Check other potentially exposed credentials and access logs.
- Do not print or commit secrets, or change Render configuration unless asked.

## Repository / implementation

- Local checkout: `/home/dkkm10/carbon-law-gh` (`main`).
- Frontend: `web/intake.html`, `web/portal.js`, `web/admin.js`.
- Backend: `backend/app.py` (FastAPI workflow, documents, and portal endpoints).
- Tests: `tests/test_api.py`.
- Production storage: Neon Postgres configured through Render `DATABASE_URL`; local tests use temporary SQLite.
- Backend expects one Uvicorn worker because collection writes are serialized and persisted as whole JSON blobs.

## Verification

Focused estate generation/access tests passed (7 tests); Python compile, JavaScript syntax, and `git diff --check` passed at implementation time. The full test suite had 22 failures in unrelated/auth/setup/workflow/persistence tests and must not be reported as passing. Latest production reset verification: 2026-10-23, all non-user Neon collection counts zero, 3 live users retained, Render health `ok` after restart.

See `HANDOFF/estate-document-generation-2026-10-23.md` for implementation and legal-research history. See `HANDOFF/estate-document-generation-agent-prompt-2026-10-23.md` for a current continuation prompt.
