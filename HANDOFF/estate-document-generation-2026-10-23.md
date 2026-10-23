# Estate document generation — session handoff

**Updated:** 2026-10-23  
**Repository:** `/home/dkkm10/carbon-law-gh` (`Kronoshus/carbon-law`)  
**Branch / commit:** `main` / `5b57fbd` (`Generate review summaries in estate workflow`)  
**Git state at handoff:** clean after the commit was pushed to `origin/main`.

## User’s objective

When a client submits an estate-planning request, prepare appropriate documents, make them available in the client portal, and surface them in the intake workflow for attorney review. The user asked that the PromptLaw skills (`prd-writer`, `write-taxonomy-from-prd`, `create-prompts-from-taxonomy`) guide research/prompting and document creation, and offered Beam’s approach as a reference.

## Completed in the last session

- Changed `POST /workflows/{id}/drafts` to fill the existing California template for each selected type: revocable living trust, pour-over will, advance healthcare directive, financial POA.
- Added an explicit mapping from actual intake field names to template placeholders; unprovided fields are labeled `Not provided`.
- Drafts are marked **DRAFT — FOR ATTORNEY REVIEW — NOT FOR SIGNING** and state they are summaries/checklists, not execution-ready instruments. Demo-mode drafts also say **DEMO — SIMULATION ONLY — NOT A CLIENT DOCUMENT**.
- Stores each generated item as a versioned document linked to the workflow and matter. The existing authenticated client `/documents` view exposes documents at `Client Review` and, after actual attorney approval, `Attorney Approved`; portal now renders the content. A stranger cannot list the client’s records.
- Client approval transitions to `attorney_review`; only attorney/admin review can then approve to consultation. Client change requests demote current client-visible records to `Attorney Review`; regeneration supersedes the previous client-review version. Attorney changes supersede the old drafts.
- Added API assertions for template substitution, portal visibility and ownership filtering, version increments, client review, and attorney approval.

**Not completed:** No model-generated content is wired into the app. Existing California PromptLaw library has 27 task prompts, but those are not validated document-generation schemas; Beam’s reference has generic legal drafting, not estate-plan document assembly. Existing firm templates are summaries/checklists only. Do not represent generated output as final legal instruments or send client PII to a hosted model without an explicit consent/privacy design and attorney-approved prompt/schema.

## Beam access (credential is outside the repo)

The latest user-provided Reflection/Beam key succeeded against `https://api.reflection.ai/openai/v1/chat/completions` with model `Beam-1.0-501B-A23B`. The previous key returned 401; use only the newer one.

Credential was saved locally, not committed, with mode `0600` at:

`~/.config/carbon-law/beam.env`

It defines `BEAM_API_KEY`, `BEAM_BASE_URL`, and `BEAM_MODEL`. **Do not print, paste, commit, or include the key in this handoff.** For Python, load it in-memory using `python-dotenv` with `load_dotenv(Path.home() / ".config/carbon-law/beam.env")`; use `os.environ["BEAM_API_KEY"]`. For a shell command, source that file only in the subprocess environment (`set -a; . "$HOME/.config/carbon-law/beam.env"; set +a; ...`). A separate session on this same host should be able to read the file under the same Unix user. If missing/unreadable, ask the user to re-provide it; do not search git/history for secrets.

Beam smoke test returned HTTP 200, model `Beam-1.0-501B-A23B`, finish reason `stop`, and answer: “3. The word ‘strawberry’ has three r’s.” No key value was logged here. The quick test used only a harmless public word-count prompt.

## Validation / deployment state

- `uv run --with pytest --with fastapi --with pydantic --with email-validator --with httpx --with python-multipart python -m pytest -q tests` — **30 passed**.
- `node --check web/portal.js`, `node --check web/admin.js`, `python3 -m py_compile backend/app.py`, and `git diff --check` passed.
- Commit `5b57fbd` pushed to `origin/main`.
- After push, `https://carbon-law.onrender.com/health` returned HTTP 200 and `https://carbon.bailment.tech/portal.html` returned HTTP 200. These checks do not establish that Render has deployed this exact backend commit; check Render’s deploy status before claiming full rollout.
- Browser-interactive verification was not run.

## Relevant files

- `backend/app.py` — workflow draft rendering, document records, review transitions and authorization.
- `templates/california/` — four currently used templates.
- `prompt-library/PRD_California_Estate_Planning_Prompt_Library.md`
- `prompt-library/taxonomy/california-estate-planning-taxonomy.md`
- `prompt-library/prompts/california/*.md` — 27 existing prompts.
- `web/intake.html`, `web/portal.js` — client review and portal UI.
- `web/admin.js` — staff workflow view (already shows draft text when the workflow is at attorney review).
- `tests/test_api.py` — regression tests.
- Beam reference checkout inspected at `/tmp/bailment-full-build`; user also has `/home/dkkm10/bailment-work/consolidation/full-build`. Neither implements estate document generation.

## Next actions

1. Check Render deploy status for commit `5b57fbd` and verify the updated backend route in a test account if authorized.
2. Continue the actual objective: use the California estate planning PRD/taxonomy and PromptLaw prompt practices to design attorney-approved document-generation prompts for the limited, specific fields collected. Decide whether generated artifacts remain summaries pending attorney drafting or whether client-agreed, attorney-approved legal templates and required intake fields will be added for true instrument assembly.
3. If using Beam, preserve the hosted-provider privacy decision: no real client records or sensitive estate facts until the firm explicitly approves disclosure and the input has a tested minimization/redaction plan. Keep output untrusted and attorney-reviewed. Treat the key only as a local secret; don’t put it in repository or Render configuration unless the user explicitly asks to deploy it there.
4. Keep client and attorney approval gates. Do not enable signing, execution, or legal-approval claims from model output.
