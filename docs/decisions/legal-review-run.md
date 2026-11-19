# Decision: run the legal review drafts (paid)

**Merging this PR is your approval.** I then run `python scripts/legal-review-drafts.py --yes-i-have-approval` once, read every
draft in full, and open a findings PR: fixes to the drafter, or questions for the attorney.

## What it does
It drafts **11 documents for 5 fictional clients**, through the exact code the app runs after a client pays (T6-04):
- a will alone, and a pour-over will
- a living trust
- a financial power of attorney
- a health care directive

The cases include the hard situations: a deceased spouse still on the deed, a likely move to a nursing facility, an unmarried
partner, a child from another relationship, a business, and land in Mexico. No real client data is used.

## Cost
- **25 model calls.** Each draft is written in 2–3 parts, and each part may write up to 16,000 tokens.
- **Estimate: about 0.3–0.5 million tokens**, roughly twice that if many drafts need their one retry.
- The dollar cost is that number times Beam's price per token on the firm's account. I don't know that price.

## Why it matters
This is the first time the drafter runs on the app's own intake answers. The drafts go only to the attorney, but they are the
firm's work product: we should see their quality, and the attorney should review a sample (part of T6-10), before any real
client pays.

- [ ] Approved (merge)
- [ ] Not now
