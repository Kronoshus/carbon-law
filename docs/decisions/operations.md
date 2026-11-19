# Decision: Firm operations and systems

How the office runs the conflict list, signings and hosting.

**How to answer:** merge this PR to accept every recommendation as written. To change one, write the change in a PR comment, or edit the line "Other:". I build to your answers.

**Q-W2. How fast does the firm clear a conflict?** The app assumes 2 business days from the names step.
*Blocks:* the day-5 payment gate's expected date (T5-04). *Phase 5.*

*Recommend:* 2 business days from the names step (the timeline already uses this; it is the setting `turnaround.conflict_bd`).

- [ ] As recommended
- [ ] Other: 

---

**Q-D4. The conflict list.** Who exports `conflicts.csv` from the firm's records, how often, and does it include
adverse parties and former clients? Without a list the app waits for a person to clear every client. *Phase 5.*

*Recommend:* The paralegal uploads a CSV each week from the firm's records: current and former clients and adverse parties, one name per row. The app keeps only the latest list.

- [ ] As recommended
- [ ] Other: 

---

**Q-R7. Spanish at signing: a Spanish-speaking witness or interpreter, Spanish summaries; may documents be in Spanish?**

Why it matters: Spanish speakers who need an interpreter complete directives least often

*Recommend:* Spanish staff at every signing; attorney decides on document language

- [ ] As recommended
- [ ] Other: 

---

**Q-S2. An API address under the firm's domain** (e.g. `api.carbon.bailment.tech` pointing to Render) lets the web app
use a secure HttpOnly cookie instead of a token in browser storage. Needs one DNS record. *Phase 2.*

*Recommend:* Yes: `api.carbon.bailment.tech` pointing at Render.

- [ ] As recommended
- [ ] Other: 

---

**Q-S3. Where the app lives.** `carbon.bailment.tech/aprende/` (same site, simplest) or its own subdomain? *Phase 2.*

*Recommend:* The same site, `carbon.bailment.tech/aprende/`: simplest, with one cookie and one deploy.

- [ ] As recommended
- [ ] Other: 

---

**Q-X1. The old client workflow.** The current portal flow lets a client generate drafts that go to *Client Review*
before the attorney approves them — the opposite of the new rule. Retire it when Aprende launches, or change it now?
*Recommend:* hide it behind a staff switch now, retire at launch.

- [ ] As recommended
- [ ] Other: 
