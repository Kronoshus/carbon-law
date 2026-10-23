# Agent prompt: Carbon Law estate demo document generation

Work in `/home/dkkm10/carbon-law-gh`. Start by reading `HANDOFF/estate-document-generation-2026-10-23.md` end-to-end and checking `git status --short --branch`, `git log -3 --oneline`, and `git rev-list --left-right --count origin/main...HEAD`. The handoff is authoritative task context. Continue the implementation; don’t spend the turn repeating that prior work paused due to budget limits.

## Goal

Build four California-state-law-only, document-shaped **demo drafts** (revocable living trust, pour-over will, advance health care directive, financial power of attorney), generated from the approved client intake/Beam summary by attorneys in the firm-side admin portal at `https://carbon.bailment.tech/admin.html`.

## Non-negotiable boundaries

- Generation UI exists only on `/admin.html`; add no client-side generation button or generated output to client portal/intake. Do not modify unrelated client UI.
- Enforce authorization in the backend: attorney/admin only; clients and paralegals denied before any Beam call. Do not trust request-supplied roles or `demo_mode` for authorization. Preserve workflow conflict/intake readiness and existing review gates. Generation itself must not approve, publish to client, unlock signing, or advance review state.
- The existing templates in `templates/california/` are summaries/checklists, not legal instruments. Do not call them approved forms or claim legal sufficiency. Create only four illustrative demo templates, clearly marked simulation/demo, attorney review required, not legally approved, not signing-ready, and not for client use. Leave material decisions/placeholders unresolved instead of inventing terms or execution formalities.
- Beam output is untrusted. Server-enforce labels; validate shape/nonempty output; failures must not create partial records. Preserve document ownership isolation, versioning/supersession, and audit history. Ensure client routes cannot read attorney-only drafts.
- Hosted Beam requests in tests use only fabricated data; no real client intake. Never print, log, commit, paste, or expose Beam credentials. Do not change Render secrets/config.
- Do not create a statewide prompt library. Only the four requested docs and the minimum supporting implementation/research note/tests.

## Legal research

Verify applicable California legal requirements against authoritative sources before writing form content. Prefer current California Legislative Information for statutes and official California Courts/state sources where relevant; cite exact source URLs and access date. Do not claim statutes were verified if site access fails. Research leads (not independently verified yet): Probate Code §§15200, 15206, 15400–15401 (trust); §§6110, 6300 (will/pour-over); §§4673–4675, 4701 (health directive); §§4121–4122, 4124, 4401 (financial POA). Distinguish statutory optional forms from the broader document type and don’t imply a will funds a trust. If an authoritative source cannot be accessed, report the specific gap rather than substituting secondary-source snippets as definitive law.

## Implementation plan

1. Read the handoff and inspect current backend, admin UI, test conventions, branch/remotes.
2. Verify current California authorities and record source/citation/access date. Keep a concise research note attached to the four demo artifacts.
3. Inspect current workflow stage/intake/ownership and document visibility. Add a distinct attorney/admin-only backend generate endpoint; do not repurpose the client endpoint for privilege. Put the button in `web/admin.html`/`web/admin.js`, visible only to authorized attorney/admin roles at a valid ready state. Preserve existing review and approval gates.
4. Generate only requested document types using fictional/synthetic test fixtures. Persist new version under correct workflow/matter/type, supersede prior active draft without deletion, status Attorney Review, and create an audit event containing actor/action/entity/version but no client intake, model output, prompt, or secret.
5. Prove clients cannot retrieve attorney drafts, even via document IDs or existing document listing. Keep other review flows unchanged.
6. Add focused behavior tests: role matrix + no provider call on denial; readiness/conflict gates; per-type template selection; fictional/minimized provider payload; prompt injection/untrusted model output and persistent labels; empty/provider failure atomicity; versions/supersession; audit privacy; client non-access; existing review transitions.
7. Run all project checks/tests and `git diff --check`; inspect the complete diff. Commit and push only if checks pass and remote is the expected repository. Do not deploy or change production secrets without explicit authorization. Report implemented, tested, pushed, deployed separately.

## Stop conditions

If legal requirements cannot be verified authoritatively, or an access/visibility gate would expose drafts to clients, do not paper over the gap: implement only the safe subset or stop and clearly identify what remains. Never claim demo files are firm-approved or legally usable.
