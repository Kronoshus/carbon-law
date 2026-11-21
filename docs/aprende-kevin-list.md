# What needs Kevin or the firm

Plain list, most important first. Each item says what it is, what I recommend, and the steps. Nothing here was done without you.

## A. Before any real client uses the app

1. **Turn on the background worker on Render.** Today nothing runs the app's background jobs on Render: no drafts after payment, no late alerts, no reminders, no data clean-up. The app runs them in its own process when the setting `APRENDE_INPROCESS_WORKER=1` is set.
   *Recommend:* set it, but only after item 5 (the retention periods), because the worker also deletes old data on that schedule.
   *Steps:* Render dashboard → service `carbon-law` → Environment → Add `APRENDE_INPROCESS_WORKER` = `1` → Save (Render redeploys). Note: the free plan sleeps after about 15 minutes without visits, and a sleeping server sends no reminders. For reliable reminders, move to a paid instance (a cost: your call).
2. **The attorney's decisions: #50 (legal content, signing, the characters' instructions) and #57 (the engagement letter).** Nothing legal reaches a client until the attorney approves it in the admin.
   *Recommend:* accept as written. *Steps:* the attorney reads the PR on GitHub; merging it accepts every recommendation; a change goes in a PR comment.
3. **The copy review's legal points** (`docs/aprende-copy-review.md`, "Needs the attorney"): the trust "protects" vs "covers", one lesson question, the consent screen's "o dice", the letter's "cambios legales", the reminder's booking link. Also re-approval of the lesson items whose grammar changed.
4. **Firm settings the engagement letter needs** (#57): the State Bar number, the costs line, the refund policy and the data promise. The letter cannot be shown while one is missing. *Steps:* admin → Firma.
5. **Privacy and data (#52):** the data promise, the retention periods (my working assumption is 365 days), and what happens to answers when a client withdraws after giving details (the screen says "No guardamos nada", but earlier answers are kept). *Recommend:* the firm writes the promise; I build to it.
6. **Prices (#51):** the prices for each document and packages, a payment plan, and the lesson pace. The screens show "ejemplo" until the firm sets prices.
7. **Live payments:** Stripe is in test mode. Going live needs the firm's Stripe keys on Render and the switch in admin → Firma. *Recommend:* only after items 2–6.

## B. Paid runs (each costs model tokens; merging the PR is the approval)

8. **#49, the 40 test conversations against the real model** (about 145,000 tokens). *Recommend:* yes, it checks La Calavera stays within the rules in Spanish before any client sees her.
9. **#65, the legal review drafts for 5 fictional clients** (about 0.3–0.5 million tokens). *Recommend:* yes, after #50, so the attorney can review a sample before a real client pays.

## C. Things only a person can do

10. **The screen-reader check** (`docs/a11y-checklist.md`): about 30 minutes with an Android phone (TalkBack) and an iPhone (VoiceOver). Tick the boxes in the file.
11. **The Spanish review (#53):** a bilingual staff member reads every screen; a legal translator checks the legal statements once. Includes the new texts from the reminders and the error messages.
12. **Phone notifications need two keys.** Without them, reminders go by email only. *Steps:* on any computer run `npx web-push generate-vapid-keys`, then add `APRENDE_VAPID_PUBLIC_KEY` and `APRENDE_VAPID_PRIVATE_KEY` on Render (free).
13. **The conflict list (#54):** the paralegal uploads the firm's list each week (current and former clients, adverse parties). Without it, a person clears every client by hand.

## D. Your taste calls (from the copy review)

14. One name for the financial power of attorney («poder para finanzas»). 15. "Tengo 18 años o más" instead of "Soy mayor de 18 años" (the strict reading leaves out people who are exactly 18). 16. The price card says "$100" in its text; it should read the firm's discount setting (small code change). 17. Mateo is a child in one lesson and an adult in another. 18. One praise line assumes a man.

## E. Features not built yet (say yes and I build them)

19. **Paying from the side panel (F3):** Stripe sends the client back to the web app, not the panel. *Recommend:* open checkout in a new tab and let the panel watch for the payment.
20. **Publishing the extension:** the Store zip is built by CI (artifact `aprende-extension`). Publishing needs a Chrome Web Store developer account (a one-time fee) and the attorney's approval of the privacy notice. *Steps:* I prepare the upload; you press Publish.
21. **The rest of the decision PRs:** #54 (operations, the API address), #55 (staff questionnaire, interviews, two extra lessons), #56 (keep the CEO overview in the repo).
22. **Tests still missing** (audit, section 7): mostly art, animation and screenshot checks from Phases 3–4. *Recommend:* schedule them after launch.
