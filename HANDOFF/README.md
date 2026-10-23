# Carbon Law demo handoff

**Updated:** 2026-10-23
**Repository:** `Kronoshus/carbon-law`
**Current commit:** `3db3d6f` — `Open planning request edits at document selection`
**Git state:** `main` matches `origin/main`; last GitHub Actions deployment workflow completed successfully for this commit.

## Live links

- Website: <https://carbon.bailment.tech/>
- Sign in: <https://carbon.bailment.tech/login.html>
- Guided intake: <https://carbon.bailment.tech/intake.html>
- Client portal: <https://carbon.bailment.tech/portal.html>
- Backend health: <https://carbon-law.onrender.com/health>

## Current workflow behavior

- Clients can create multiple planning workflows. The client portal lists all workflows and each workflow’s matter, status, selected documents, consultation/signing requests, and approval status.
- Portal **Modify planning request** reopens the selected workflow at Part 2 (document selection) and carries its workflow ID in the intake URL (`?workflow=...&part=2`). This avoids accidentally loading a different, most-recent workflow.
- Completed sections have Modify controls. Appointment requests are requests until staff approval; they are not workflow completion. Part 7 should only reflect actual completion.
- Part 1 captures the client’s legal name, phone, and related names for conflict screening. Do not collect sensitive/confidential matter details before conflict review.
- `GET /my-workflows` returns all workflows owned by the authenticated client, newest first. `GET /my-workflow` remains a compatibility endpoint returning the newest workflow and is still used by intake/login flows.

## Demo safety

- This is a demo, not an active law-firm intake channel. Never enter real client or confidential information.
- Simulated conflict review is not AI, does not query a conflicts database, and is not real clearance.
- Generated drafts are placeholders marked **NOT FOR SIGNING**, not legal documents or legal advice.
- Appointment preferences remain pending until staff explicitly approves them.
- No credentials or passwords belong in this file.

## Repository / implementation

- Local checkout: `/home/dkkm10/carbon-law-gh` (`main`).
- Frontend: `web/intake.html`, `web/portal.js`, `web/login.html`, `web/admin.js`.
- Backend: `backend/app.py` (FastAPI workflow, appointment and portal endpoints).
- Tests: `tests/test_api.py`.
- Persisted data uses Neon Postgres in production (`DATABASE_URL` is configured in Render, not stored here). Local tests use a temporary SQLite database.
- Backend expects a single Uvicorn worker because the current in-memory collection model serializes writes and persists collections per request.

## Recent changes

- `3db3d6f` — modify request opens its selected workflow directly at Part 2.
- `f9bf63c` — added `/my-workflows` and rendered every planning workflow on the portal.
- `6858bd4` — corrected completion status, added completed-section editing and Part 1 conflict-screening fields.
- Prior work added multiple planning requests and routed completed clients to the portal.

## Verification

From the repository root:

```sh
uv run --with-requirements requirements.txt --with pytest pytest -q tests/
```

Last run: **21 passed** (2026-10-23). The Part 2 edit also passed targeted API tests and `node --check` for the intake and portal scripts. GitHub Actions deployment for `3db3d6f` completed successfully.

## Known follow-up / open user request

The user asked to delete the portal workflow with matter ID `CL-16277949` (currently shown as “conflict review”, no documents or appointment requests). No deletion was performed. There is no workflow-delete endpoint; confirm the exact request/owner and implement a safe, ownership-checked deletion or an explicit archive/cancel flow before changing production data. Do not delete by matter ID alone or remove the matter without considering linked workflow and appointment records.
