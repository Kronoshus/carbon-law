# Carbon Law demo handoff

**Updated:** 2026-10-21  
**Repository:** `Kronoshus/carbon-law`  
**Current commit:** `46176e8` — `Reuse one DB connection, skip unchanged writes, and serialize requests (#1)`  
**Git state:** `main` matches `origin/main`.

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

## Account persistence

Since 2026-10-21 the Render backend stores data in Neon Postgres (database `carbon_law`, US West). The connection string is set as `DATABASE_URL` in the Render service environment and is not in this repo. **Accounts and demo workflow data now survive restarts and redeploys.**

Demo accounts created before this switch lived in the old ephemeral SQLite file and were not migrated. Create a fresh disposable account once.

The backend must run as a single process (one uvicorn worker). Requests are handled one at a time because data is held in memory and saved as JSON per collection.

## Safety / demo boundaries

- Do not enter real client or confidential information. The site is a demo, not an active law-firm intake channel.
- Do not treat demo conflict simulation or generated drafts as legal determinations or documents ready to sign.
- No passwords or account credentials are included in this handoff.

## Repo and verification

- Local checkout: `~/carbon-law-gh` (`main`); the repo is `Kronoshus/carbon-law`.
- Recent relevant commits: `46176e8` (storage: Postgres connection reuse and request serialization, PR #1), `60adccc` (this handoff), `64d2ac0`, `1940a74`.
- Automated backend tests: **19 passed** at the current commit (SQLite). The same suite also passed against a throwaway Postgres and a scratch Neon database.
- Render reports deploy `46176e8` live. Live check on 2026-10-21: `/health` 200; signup, login, and workflow writes returned 200 in roughly 0.1–0.5 s and were stored in Neon.

Run tests from the repo root:

```sh
uv run --with-requirements requirements.txt --with pytest pytest -q tests/
```

