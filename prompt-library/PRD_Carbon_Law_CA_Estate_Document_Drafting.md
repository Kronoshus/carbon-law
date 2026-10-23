# Carbon Law California Estate Document Drafting — Project PRD

## Purpose and scope
Create exactly four document-specific Beam prompts used by the Carbon Law demo estate workflow: revocable living trust, pour-over will, advance health care directive, and financial power of attorney. Beam uses intake answers and the existing California review templates to produce a document-shaped **attorney-review draft**. No additional statewide prompt library is in scope.

## Inputs and output
Backend selects one approved prompt by document type, provides the existing template with resolved intake values, and saves Beam output through the existing versioned document workflow. Preserve client ownership checks, client review, attorney approval, and version supersession. Prompt must not override backend approval state.

## Safety boundaries
Current templates are summaries/checklists, not attorney-approved operative forms. Intake is incomplete for execution-ready instruments. Output must be clearly labeled DEMO when demo mode, DRAFT — FOR ATTORNEY REVIEW — NOT FOR SIGNING, and not an execution-ready/legal-approved instrument. No signature or notary blocks that imply executable signing. Do not invent names, family facts, legal elections, powers, statutory validity, or missing clauses. Missing or contradictory information goes into a separate Attorney Review / Missing Information section. Generation failure must not create or supersede document records.

## California research anchors
As of 2026-10-23, initial research identified California Probate Code §§ 15200 and 15400 (trust creation/revocability), §§ 6110–6111 (will execution), §§ 6300–6303 (testamentary additions to trusts), §§ 4121–4122 and 4401 (powers of attorney and statutory form), §§ 4670–4675 and 4701 (advance health care directives). Prompt authors must not treat this list as a substitute for verifying current law and attorney-approved forms. California Courts Self-Help, “Wills, estates, and advance care planning”: https://selfhelp.courts.ca.gov/wills-estates-probate/legal-documents. Secondary lookup used FindLaw California Probate Code summaries; re-check all authorities against current official California Legislative Information before attorney adoption.

## Acceptance
Four distinct prompt files; backend selects the correct file for each supported type; Beam is called only for demo-mode workflows; model output remains untrusted and review-gated; tests prove prompt selection, demo labeling, and existing authorization/versioning behavior.
