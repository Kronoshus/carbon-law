# Decision: run the 40 test conversations against the real model (paid)

**Merging this PR is your approval.** I then run `python scripts/conversation-eval.py --yes-i-have-approval` once, grade every
reply, and open a PR with the results. Every failure becomes a new test or a persona fix.

## What it does
- It sends the 40 scripted conversations from `tests/fixtures/conversations.yaml` (20 Spanish, 20 English) through the real
  `/chat` code to Beam (`reflection/Beam-1.0-501B-A23B`), the model the firm approved for the app (F-002).
- The clients are fictional (the Torres family). No real client data is sent.
- It writes `reports/conversations-<date>.md`: each transcript, automatic checks (prices, hidden tags, one question per turn,
  length) and a pass/fail box for each rule (no advice, no fees, routes case questions to the attorney, the 911 line, and so on).

## Cost
- **41 model calls, about 145,000 tokens in total** (at most about 3,900 per call), estimated from the real prompt sizes.
  The reasoning length of each reply is a guess, so the true number may be up to twice that.
- The dollar cost is that number times Beam's price per token on the firm's account. I don't know that price.
- It runs once. Any re-run after fixes needs a new approval (another PR).

## Why now
The server's guards are proven with a deliberately misbehaving model (#47). This run checks the model itself: does La
Calavera stay within the rules when a real client pushes for advice, says "no tengo suficiente", or asks "¿son notarios?"
The research (R3) found that language models do worse in Spanish, so we should see this before any client does.

- [ ] Approved (merge)
- [ ] Not now
