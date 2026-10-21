# Carbon Law demo handoff

**Updated:** 2026-10-21  
**Repository:** `Kronoshus/carbon-law`  
**Current commit:** `64d2ac0` — `Improve intake help and allow demo draft progression`  
**Git state:** `main` matches `origin/main`; worktree clean at handoff.

## Live links

- Website: <https://carbon.bailment.tech/>
- Sign in: <https://carbon.bailment.tech/login.html>
- Create account: <https://carbon.bailment.tech/signup.html>
- Guided intake: <https://carbon.bailment.tech/intake.html>
- Backend health: <https://carbon-law.onrender.com/health>

## What works in the demo

- Sign-in is the primary entry point; account creation is linked from sign-in.
- Demo account passwords can be six or more characters. Use a disposable, unique password; never reuse a real password.
- Guided flow: conflict-screening form → optional five-second demo simulation → document selection → intake → review placeholder drafts → client review → staff/attorney steps.
- The optional simulation is **not AI**, does not search a conflicts database, and is **not real conflict clearance**. Real requests require staff review.
- Drafts are placeholders marked **NOT FOR SIGNING**, not legal documents or legal advice. Attorney review and California signing formalities remain necessary.
- The intake UI has a progress bar, high-contrast buttons, and explanatory help icons.

## Important limitation: account persistence

The live Render service is on its free plan and is configured with SQLite at the app’s local path. Render has no persistent disk configured for this service, and the service environment lists no database URL. **Accounts and demo workflow data may disappear after a restart or redeploy.** This explains why the demo account disappeared. Create a fresh disposable account when needed; do not rely on test data persisting. A durable fix requires provisioning persistent storage (for example, a managed database or a persistent disk) and migrating the app to use it. No hosting upgrade was made.

## Safety / demo boundaries

- Do not enter real client or confidential information. The site is a demo, not an active law-firm intake channel.
- Do not treat demo conflict simulation or generated drafts as legal determinations or documents ready to sign.
- No passwords or account credentials are included in this handoff.

## Repo and verification

- Working release checkout: `/tmp/carbon-law-release` (may be temporary); the repo is `Kronoshus/carbon-law`.
- Recent relevant commits: `64d2ac0`, `1940a74`, `2624851`, `a37619f`.
- Automated backend tests: **17 passed** at the current commit.
- GitHub Actions for the current commit completed successfully. Render reports deploy `64d2ac0` live. The static and backend releases are current.

Run tests from the repo root:

```sh
uv run --with-requirements requirements.txt --with pytest pytest -q tests/
```

