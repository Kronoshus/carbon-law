# Estate document generation — attorney-side demo handoff

**Updated:** 2026-10-23  
**Repo:** `/home/dkkm10/carbon-law-gh`  
**Branch:** `main`; current HEAD `95e95c9` (`Update estate generation handoff for attorney portal`), one local commit ahead of `origin/main` (`0707e99`). Check `git status` and remote state before editing or pushing. Working tree was clean at last check.
**Goal:** In the attorney-accessible firm side only (`https://carbon.bailment.tech/admin.html`), let authorized attorneys generate four document-shaped California estate-plan demo drafts from a client’s approved intake/Beam summary before initial consultation: revocable living trust, pour-over will, advance health care directive, and financial power of attorney.

## User’s current decisions

- California state law only; no county-specific variation requested.
- These are **demo forms**, intended to demonstrate document-shaped drafting from intake, not production forms. User has no firm-specific forms/clauses/mapping/signing preferences right now.
- Generation is only on `/admin.html` and its authorized backend endpoint. **Do not add a client-side Generate action or expose these generated artifacts to the client portal.**
- The demo may simulate attorney adoption/review for demonstration, but never represent that an actual attorney reviewed/adopted it. Persistent labels must say demo/simulation, attorney review required, not legally approved, and not signing-ready.
- Beam tests use only fictional data. Real-client hosted processing is forbidden absent explicit firm approval and a documented privacy/redaction plan.
- The requested legal research standard is one authoritative source (e.g. official California Legislature, CourtListener/Lexis where relevant); don’t build a statewide prompt library. Use only the four document types.

## Current implementation / safeguards

- `templates/california/` contains summary/checklist content, not operative legal instruments. Existing templates cannot be represented as valid forms. Four runtime Beam prompts live at `prompt-library/prompts/california/carbon-law/` and explicitly request attorney-review drafts with placeholders.
- `backend/app.py` currently exposes client-authenticated `POST /workflows/{id}/drafts` (`generate_workflow_drafts`, around lines 903–926). It renders the current summary/checklists, calls Beam in `demo_mode`, stores versioned document records and transitions to client review. **Do not just repurpose it for attorney-side generation.** Add a separate attorney/admin-only endpoint, use the existing staff auth and workflow readiness gates, and only make the action available in `web/admin.js`/`web/admin.html` to attorney/admin roles. Paralegals and clients must not invoke generation. The user specifically limited new generation UI to `/admin.html`.
- Existing staff workflow review is `PATCH /workflows/{id}/staff-review`; attorney/admin approval is separately gated; preserve current client review and attorney review flows and never change approval/stage as a side effect of model output. Existing document records are versioned and superseded by matter + document name; preserve this behavior unless tests prove a narrow correction necessary.
- Scope/ownership warning from reviewer: no evident per-matter attorney ACL exists; staff workflow queue is firm-wide. Do not invent a new permission model, but verify existing staff access assumptions and avoid cross-client leakage. If attorney-only is a firm-wide role, enforce attorney/admin role on backend and do not trust client-controlled `demo_mode` or payload role.
- Keep audit events (actor, action, workflow/document/version) without prompt, intake, model response, sensitive health/financial data, or secrets.
- Keep outputs untrusted; use fixed document-specific prompts, delimit intake as data, enforce labels outside model output, validate/reject empty or malformed response, and don’t partially write records on failure. Model text must not be able to remove labels or mark approval.
- Privacy: `backend/app.py` currently loads local `~/.config/carbon-law/beam.env`; never print/log/commit/share Beam credentials and do not change Render secrets. Use only fictional fixtures with mocked Beam in automated tests. The existing handoff reports prior fictional Beam smoke tests; do not repeat hosted calls with any real intake.

## Legal research status — not yet sufficient to claim verified law

A research agent identified likely relevant provisions, but official California Legislature pages returned 403/Cloudflare during retrieval, so the exact current text and amendments were **not successfully verified**. Treat these as research leads only, not verified authority. Before drafting the demo form content, obtain and cite one authoritative source per issue, preferably direct official California Legislative Information statutes, recording source URL and access date; where official access remains unavailable, report the blocker and do not falsely claim verification.

Research leads returned (must independently verify before relying):

- Trust: Probate Code §§ 15200, 15206, 15400–15401 (creation; writing for real property; revocability/revocation).
- Pour-over will: §§ 6110, 6300 (execution and devise to trust); distinguish the optional statutory will form from a pour-over will. A will does not itself fund a trust.
- Advance health care directive: §§ 4673–4675, 4701 (execution/witness restrictions/SNF requirements; optional statutory form).
- Financial POA: §§ 4121–4122, 4124, 4401 (execution, durability, statutory form). Make clear it is financial authority, not health-care authority.

A CourtListener MCP connection appeared in the environment, but tool discovery failed. CourtListener is case-law focused and not a replacement for official statutory text. Do not claim Lexis access unless discovered and actually used.

## Recommended implementation sequence

1. Start by reading this file and checking `git status --short --branch`, current HEAD, `origin/main`, and existing uncommitted/local-ahead commits. Do not lose the local handoff commit.
2. Verify the cited current California law from one authoritative source per material requirement. Record source URLs and access date in a concise research note/form metadata. If official statute retrieval fails, clearly surface it; don’t claim legal verification.
3. Draft exactly four **illustrative demo form templates**, each document-shaped and tailored to its own legal function, with blanks/placeholders for decisions or facts not in approved intake. Avoid inventing terms, clauses, witnesses, notary language, or a complete executable instrument; clearly flag unresolved issues and state that it is not signing-ready. They are not firm-approved forms and must not be used with clients.
4. Add separate backend endpoint for attorney/admin generation; preserve conflict/intake readiness gates and current review state. No client or paralegal generation. Keep client workflow generation UI unchanged or remove/disable only the Generate control if it currently exposes this new document flow (the user explicitly permits only staff-side action; avoid unrelated client UI changes).
5. Add a Generate action in `/admin.html` workflow review for attorney/admin only, at an appropriate ready state. Reload staff data after success. Generated documents remain attorney-review status; do not automatically approve or advance to client/signing.
6. Store each successful result as a new version scoped to the correct workflow/matter/document type, superseding prior active version without deleting history; audit the staff actor and action. Avoid leaking output to clients through existing document endpoints; if current visibility rules would expose these records, keep the attorney-only draft separate or tighten the narrow read path and test it.
7. Add focused tests: client/paralegal denied; attorney/admin allowed only at ready state; conflict and incomplete intake gates; Beam not invoked on denials; fixed prompt/form per requested type; fictional/minimal payload; labels survive adversarial model output; failures are atomic; version/supersession; audit without content/PII; clients cannot read attorney-side draft; existing review approval transitions remain unchanged.
8. Run all project tests/checks, inspect `git diff`, then report **implemented, tested, pushed, deployed** as separate bullets. Do not claim push/deploy unless actually done. Never print, commit, or share Beam credentials. Do not change Render configuration absent authorization.

## Important files

- `backend/app.py`: `WORKFLOW_TEMPLATES`, `BEAM_DOCUMENT_PROMPTS`, `_beam_review_summary`, `render_workflow_document`, `generate_workflow_drafts`, `/documents`, `/workflows/{id}/staff-review`.
- `web/admin.js`, `web/admin.html`: staff workflow list and review actions.
- `web/intake.html`: current client workflow flow; keep generation staff-side only.
- `tests/test_api.py`: authorization, workflow gates, versions, review tests.
- `templates/california/`: current summaries/checklists only.
- `prompt-library/prompts/california/carbon-law/`: four existing prompts.

## How this work paused

A prior agent did not modify implementation. It hit a goal budget limit and then stopped instead of continuing with available context; this is not a repository blocker. Three subagents completed source, portal, and safety reviews. Their findings are recorded above. The next agent should proceed with the work, not spend the turn re-explaining the budget limitation.
