# Carbon Law

Carbon Law is a workflow prototype for California estate-planning matter operations. It provides a staff/client web interface, matter and task tracking, change requests, appointment workflows, and illustrative document-generation flows. It is not a production legal practice-management system or a substitute for attorney review.

## Repository

- `web/` — static client and staff interface, deployed with GitHub Pages.
- `backend/` — FastAPI service and persistence layer.
- `docs/` — product behavior, workflow stages, implementation and deployment notes.
- `prompt-library/` — drafting prompt specifications and prompts.
- `templates/` — illustrative sample documents; not approved for execution.
- `tests/` — backend/API behavior checks.

## Matter workflow

Matters progress through intake, scope review, client data collection, drafting, attorney review, client review, signing preparation, execution, funding follow-up, and closure. Each matter should have an owner, next action, due date, and visible blockers. Legal decisions and document approval remain with the supervising attorney.

## Development and deployment

See `docs/backend-deployment.md` for backend setup and deployment notes. The web app is deployed from `web/` through GitHub Pages. Configure the frontend API endpoint and backend secrets through the documented deployment environment; never commit client information or credentials.

## Prototype and data warning

Use fictional data for demos. Do not enter real client information unless the firm has approved the deployment, security controls, data handling, and applicable vendor terms. Demo estate documents and AI-generated content are illustrative and must not be used as legal instruments without attorney review.
