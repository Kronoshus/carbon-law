# Aprende y Planea — questions only Carbon Law can answer

Phase 1 deliverable. Each question says why it matters, what I recommend, and what it blocks. Answering the
**Phase 2 blockers** (marked ●) lets Phase 2 start; the rest can come later in the phase listed.

## The two-week promise

**● Q-W1. "Two weeks" or "about two weeks"?** Under the firm's own turnaround standards (conflict 2, scope 2, attorney
review 3, revisions 2 business days), the journey takes exactly 14 days only for a Wednesday or Thursday start with no
change requests; otherwise 15–19 days (table in `aprende-spec.md` 6.3).
*Recommend:* promise "about two weeks", show the real projected date from day 1. *Alternatives:* attorney review in 2
business days, or Saturday signings. *Blocks:* marketing copy and the timeline wording (T5-04).

> **Answered 2026-11-17 (Kevin):** "about two weeks". The app shows each client's real projected dates.

**Q-W2. How fast does the firm clear a conflict?** The app assumes 2 business days from the names step.
*Blocks:* the day-5 payment gate's expected date (T5-04). *Phase 5.*

**Q-W3. Does the attorney approve each client's scope, or is a template-level approval enough?** The plan moves the
tentative document choice to day 2 so a per-client scope review fits before day 5. *Phase 6.*

## Data and AI

**● Q-D1. Does the 2026-11-15 approval for Beam (Reflection AI) cover the new app?** The app sends lesson questions,
"Tus datos" answers and the intake conversation (text only, never audio) to Beam, only after consent and a clear
conflict check. *Blocks:* every AI call in production (T5-01). Tests use a stub, so Phase 2 can start without it.

> **Answered 2026-11-17 (Kevin):** yes, the Beam approval covers Aprende.

**Q-D2. Retention periods and Reflection's data settings.** How long to keep transcripts, audio, datos answers, drafts
of clients who never pay, and accounts of people who only did lessons; and the Reflection account's retention and
training settings. *Recommend:* audio 90 days after signing; non-paying learners' personal data 12 months after last
activity. *Blocks:* launch (T7-05).

**Q-D3. A client who declines recording or AI:** can they still do the intake with staff (phone or in person)?
*Recommend:* yes — the app shows "Prefiero hablar con la oficina" and creates a task. *Phase 5.*

**Q-D4. The conflict list.** Who exports `conflicts.csv` from the firm's records, how often, and does it include
adverse parties and former clients? Without a list the app waits for a person to clear every client. *Phase 5.*

## Money

**● Q-P1. Stripe.** Does the firm have a Stripe account (or another processor it prefers)? Which bank account
receives payments, and how must advance fees be held under the State Bar rules (the attorney's decision)? Test mode
needs only test keys from the firm's own account. *Blocks:* T6-02 (Phase 6); the account owner should be the firm.

> **Answered 2026-11-17 (Kevin):** no Stripe account yet. Payment work is built and tested against a mocked Stripe until the firm opens an account. Still open: which bank account receives payments and how advance fees are held (attorney).

**Q-P2. Wording of prices and discounts.** The attorney approves how discounts are described in the app and in any
advertising ("$3,000 − $400 por 4 lecciones"). *Phase 4.*

**Q-P3. Signing the engagement letter in the app.** Is typed name + "Acepto" + timestamp + IP + a hash of the text
enough for the firm, or should we integrate an e-signature service (cost)? *Phase 6.*

**Q-P4. Prices for the trust, the powers of attorney, the health care directive and packages; refunds.** The screens
show "ejemplo" until set. Does any discount apply to documents other than the will? Refund policy before and after
drafting? *Phase 6.*

**Q-P5. One lesson a day or faster?** Should an eager client be able to take the next core lesson the same day?
*Recommend:* one a day (a setting). *Phase 4.*

**Q-P6. Couples.** A joint trust needs both spouses. One shared account, two linked accounts, or the second spouse
joins only at signing? Price for a couple? *Recommend:* two linked accounts, one price set by the firm. *Phase 5.*

## Language and legal content

**Q-L1. Native-speaker review.** Who in the firm (or which reviewer) checks the Spanish for the firm's clients?
*Phase 4.*

**Q-L2. Attorney review of lesson content.** About 120 legal statements across the lessons. How does the attorney want
to review them — in the admin pages item by item, or a printed packet per lesson? Expected turnaround? *Phase 4.*

**Q-L3. Plain-language walkthrough on day 9.** May La Calavera read a plain-language summary of each approved
document, written once per document type and approved by the attorney? Or should the walkthrough stay generic
(what each section of a will is for)? *Recommend:* generic sections plus the client's own names, all approved. *Phase 6.*

**Q-L4. *Usted* or *tú*?** The prototype uses *usted*; Duolingo-style apps use *tú*. *Recommend:* *usted* (older
clients, a law firm). *Phase 2 (strings).*

## Characters

**Q-C1. La Calavera's name.** Proposals: **Don Catrín**, **Calaquita**, **Don Calavera**. And: keep "Piñata" and
"El Oso" or name them (e.g. "Chispa", "Don Oso")? *Phase 3.*

**Q-C2. Cultural review.** Who from the firm's client community reviews the characters, names and lines? *Phase 3.*

**Q-C3. Voices for Piñata and El Oso.** From the free, commercially licensed local voices (Piper, Kokoro), the firm
picks two, as Kevin picked La Calavera's on 2026-11-16. I will prepare samples. *Phase 3.*

**Q-C4. Attorney Raval's photo avatar.** The plan does not use his likeness anywhere in Aprende. Confirm that is right.

## Systems

**● Q-S1. Hosting the voice service.** Free local voices and transcription need about 2 GB of RAM; Render's free plan
does not have it. Options: a paid Render instance (about $25/month at today's prices, to be confirmed), a firm-owned
machine, or no server voice (browser voice, typed answers). *Recommend:* start without it; add it when the firm
approves the cost. **This spends money: I will not set it up without your yes.**

> **Answered 2026-11-17 (Kevin):** start without server voice. Browser voice and typed answers for now; no hosting is set up.

**Q-S2. An API address under the firm's domain** (e.g. `api.carbon.bailment.tech` pointing to Render) lets the web app
use a secure HttpOnly cookie instead of a token in browser storage. Needs one DNS record. *Phase 2.*

**Q-S3. Where the app lives.** `carbon.bailment.tech/aprende/` (same site, simplest) or its own subdomain? *Phase 2.*

**Q-X1. The old client workflow.** The current portal flow lets a client generate drafts that go to *Client Review*
before the attorney approves them — the opposite of the new rule. Retire it when Aprende launches, or change it now?
*Recommend:* hide it behind a staff switch now, retire at launch.

**Q-X2. The homepage promise.** The public site says "A real conversation with an attorney comes first. No automated
legal advice." Aprende starts with AI lessons and offers the consultation optionally from day 4. Change the homepage
wording, or make the consultation part of the path?

## From the research (2026-11-18, see `aprende-research.md`)

| # | Question | Why it matters | Recommendation |
|---|---|---|---|
| Q-R1 | Offer a payment plan or split payment? | Cost and low savings are stated barriers; most older Hispanic homeowners without a will have little cash on hand | Yes, two or three payments, shown on the price card |
| Q-R2 | A "plan for your children" bonus lesson (guardian nomination, Caregiver's Authorization Affidavit, joint guardianship)? | Children are the strongest real-life reason to plan; deportation fear is current | Yes, as general information; the attorney decides scope and wording |
| Q-R3 | Mention transfer-on-death deeds, Prop 19 and Medi-Cal estate recovery as "things families don't expect"? | Common cost surprises; outside the four core documents | Only as one line each that routes to the attorney |
| Q-R4 | Warn that employer plans' beneficiary forms can override the will (federal law)? | A common failure; our source rule allows only the Probate Code and the courts' self-help pages | Allow this one federal point with an attorney-approved source |
| Q-R5 | The data promise at consent: who sees the client's words, how long they are kept, that they are confidential | About half of Latinos fear immigration enforcement; trust is the barrier | The firm writes it; we show it on the consent screen |
| Q-R6 | Show the attorney's State Bar number and "a notario is not a lawyer" in the app? | Notario fraud; distrust of the process | Yes, on the disclosure and the price card |
| Q-R7 | Spanish at signing: a Spanish-speaking witness or interpreter, Spanish summaries; may documents be in Spanish? | Spanish speakers who need an interpreter complete directives least often | Spanish staff at every signing; attorney decides on document language |
| Q-R8 | Ask in intake whether the client receives or expects Medi-Cal? | Affects advice; sensitive | Only if the attorney wants it, worded as a fact for him |
| Q-R9 | Add an "if you can't afford this" note pointing to legal aid (TLAP, Bet Tzedek)? | Builds trust; screens out clients the firm can't serve | Firm's business call |
| Q-R10 | Approve the staff questionnaire now and the client interviews (5–8 people, run by the firm)? | Our research is desk research only | Questionnaire now; interviews after the firm reviews the guide |

## Budget

**Q-B1. Token budget.** The backlog has 61 tasks; at the brief's minimum of 100 M tokens each that is 6.1 B, above the
4 B cap. Raise the cap, or accept grouping small related tickets into one task (listed in the decision log)?

> **Answered 2026-11-17 (Kevin):** the cap is raised to 10 B tokens. Every ticket gets its full 100 M; no grouping needed.