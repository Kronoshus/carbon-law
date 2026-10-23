# Estate document generation — attorney-side generation handoff

**Updated:** 2026-10-23  
**Repo:** `/home/dkkm10/carbon-law-gh`  
**Branch:** `main`, clean at `0707e99` (`Use document-specific California drafting prompts`)  
**Goal:** Continue estate document generation so an attorney can turn the approved intake/current Beam draft into a document-shaped draft using firm-approved California forms, from the firm portal. Keep all outputs attorney-reviewed and never signing-ready/legal-approved by implication.

## Current state

- The workflow offers four document types: revocable living trust, pour-over will, advance health care directive, and financial power of attorney.
- `templates/california/` has summary/checklist templates only. They are **not operative, attorney-approved legal forms** and lack required clauses, execution formalities, and full signature/acknowledgment pages. Do not use them to claim or assemble legally sufficient instruments.
- Four project-specific prompts are stored at `prompt-library/prompts/california/carbon-law/`. Backend maps types to these prompt files and passes the template filled with intake answers to Beam. The prompt files tell Beam to preserve only supplied facts, flag missing decisions, and produce a proposed attorney-review draft with `[ATTORNEY TO COMPLETE]` placeholders. The output is not a complete instrument.
- Project scope docs: `prompt-library/PRD_Carbon_Law_CA_Estate_Document_Drafting.md` and `prompt-library/taxonomy/carbon-law-ca-estate-document-drafting.md`.
- Beam is called only in `demo_mode`; the output is persistently labeled `DEMO — SIMULATION ONLY — NOT A CLIENT DOCUMENT` and `DRAFT — FOR ATTORNEY REVIEW — NOT FOR SIGNING`. The implementation loads a local `~/.config/carbon-law/beam.env` if available; Render needs its own environment variable. Never show/log/commit the secret.
- User reported a generated attorney-review trust outline that used example intake facts and clearly listed missing terms. That confirms Beam output is reaching the workflow; it does not prove the current templates can support full instruments.
- Client portal already has Change Request Status and reloads the list immediately after submit (commit `23f6080`). User limited client-facing scope to document generation and change-request status. Do not add other client UI features without asking.

## Deployment and verification

- `0707e99` is pushed to `origin/main`. User supplied Render log showing Render checked out full SHA `0707e9988ce9c5ebe375d7046c59d77ad989dad0`, build succeeded, and service reported live.
- Four document-specific Beam prompt smoke tests passed with fictional data; generated output was not logged. Test suite: **32 passed**; Python compile, JS checks, and `git diff --check` passed.
- Current working tree was clean at handoff. Verify current deployment/branch before edits.
- The PRD cites California Probate Code §§ 15200, 15400, 6110–6111, 6300–6303, 4121–4122, 4401, 4670–4675, and 4701 as *research anchors*. They have not all been independently verified against current official California Legislative Information. Verify law, statutory language, current forms, and firm requirements before using in an instrument prompt/template.

## Next work: attorney portal generation

1. Ask the firm/user to provide the **attorney-approved, current forms** for the four document types, plus applicable clause/options library, field mapping, and signing/execution requirements. Existing repo files are not substitutes. If forms are not available, stop at the current attorney-review outline; do not invent an executable form or fill legal terms from model knowledge.
2. Confirm legal research against official California sources with attorney review. Record form/source version and effective date. Identify required inputs and block generation on unresolved material choices rather than filling them with assumptions.
3. Add an **attorney/admin-only** Generate Document action in the firm portal, driven by an authorized backend endpoint. Do not expose that action or its output to clients before the existing review/approval gate allows it. Resolve exactly whether attorney generation requires client review complete, existing workflow attorney-review state, and/or separate attorney authorization before implementation.
4. Give Beam the approved prompt, approved template, and minimized/validated intake values; have it fill only authorized fields. Treat model output as untrusted: verify required fields/placeholders, reject missing or malformed output, and leave unresolved legal choices for counsel. Do not have Beam create statutory terms, execution pages, or legal conclusions unless explicitly part of the attorney-approved form/spec.
5. Store each output through existing versioned document records, link to matter/workflow, supersede prior version correctly, preserve client ownership checks and attorney/client approval transitions, and log audit events. Keep generated artifacts in `Attorney Review` until attorney expressly approves; never let model output itself transition approval state.
6. Add focused behavior tests: role authorization (client/paralegal denied as appropriate), gate ordering, prompt/template selection per type, no model use on non-demo/non-authorized paths, missing-field behavior, version/supersession, audit, and no cross-client exposure. Run all project tests and checks.
7. Client-side changes remain limited to: (a) using intake to generate the requested drafts and (b) showing change-request status. Do not reshape unrelated portal UI.

## Important files

- `backend/app.py`: `WORKFLOW_TEMPLATES`, `BEAM_DOCUMENT_PROMPTS`, `_beam_review_summary`, `render_workflow_document`, `generate_workflow_drafts`, `/documents`, `/workflows/{id}/staff-review`.
- `web/admin.js` / `web/admin.html`: firm workflow review currently displays existing draft content and supports attorney approval/request changes; no attorney-generation action yet.
- `web/intake.html`: client workflow stages; draft generation and review gates.
- `web/portal.js` / `web/portal.html`: change status and client portal documents.
- `tests/test_api.py`: workflow ownership, stage gates, versioning and review tests.
- `templates/california/`: current summary/checklists only.
- `prompt-library/prompts/california/carbon-law/`: four runtime prompts.
- `HANDOFF/estate-document-generation-2026-10-23.md`: prior handoff.

## Secret/privacy boundary

Beam is a hosted provider. Use only simulated/fictitious data for smoke tests unless the firm explicitly approves hosted processing of real client data and a documented privacy/redaction plan. The key at `~/.config/carbon-law/beam.env` is private. Load in memory if needed; never print, commit, paste, or include it in logs, prompts, artifacts, or handoffs. Never put it in repo files. Do not change Render secret configuration unless explicitly authorized.
