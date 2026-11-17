# Build brief for Prime Agent: "Aprende y Planea" — a Duolingo-style estate-planning app for Carbon Law Group

Paste everything below this line into Prime Agent. This file is also in the repository at `avatar-intake/PRIME_AGENT_BUILD_PROMPT.md`.

---

## 0. Who does what

You are a build team for Carbon Law Group (attorney Pankaj Raval, Los Angeles, California estate planning).

- **Head engineer: Claude Opus 5.5.** Owns the plan, architecture, UX and visual design, character design, lesson design, AI character personas and prompts, legal-content gates, code review and final integration. Opus 5.5 approves every merge.
- **Builders: Beam agents (Reflection AI, `Beam-1.0-501B-A23B`), reasoning effort High.** Do as much of the hard technical and repetitive coding as possible: backend endpoints, database migrations, API clients, the Chrome extension plumbing, quiz and lesson data wiring, internationalisation, tests, CI, accessibility fixes, refactors.
- **Only Opus 5.5 designs characters in Blender.** Beam agents may wire a finished character file into the app, but they never create, redraw or restyle a character, its art or its rig.

### Tools and budget

- **Skills and Composio:** Opus 5.5 and every Beam agent may use any installed skill and any app or tool reachable through Composio (for example GitHub, Gmail, Google Calendar, Google Drive, Slack and the 1,000+ other connected apps), plus any connected MCP server and the browser. Use them whenever they make the work faster or better. The rules in section 7 about asking first still apply to anything that sends a message, publishes, spends money or touches real client data.
- **Token budget:** the project has a cap of **4 billion tokens**. Give every task at least **100 million tokens**: every ticket, phase, character, review and test pass. Never cut work short, skip a review, shorten tests, or reduce quality to save tokens. If a task needs more than its share, keep going and note the overrun in the decision log. Report total use at the end of each phase.

### How Opus delegates to Beam

1. Opus writes each task as a ticket: goal, files to touch, interfaces (exact function signatures, endpoint shapes, JSON schemas), what must not change, and the acceptance tests that prove it is done. Opus writes those tests first where practical.
2. One ticket is one reviewable change of about 300 lines or less. Beam reliably writes only about 2,500 words of output per reply, so split large work into parts and join them, as the existing drafters do.
3. Beam's API requires its `reasoning_content` to be sent back with every earlier assistant turn. Beam sometimes loops, repeating a sentence or block many times. Every Beam call needs a loop guard (see `looping()` in the existing `server.py`) and one retry.
4. Opus reviews every Beam diff before merge: correctness, security, the legal guardrails in section 6, and style. Opus rejects work that only passes the tests by special-casing them.
5. Opus does the design work itself: the visual system, screens, motion, the characters, lesson flow and copy, persona prompts, and final copy review in Spanish and English.

## 1. Sources you must read first

1. **The firm's repository: https://github.com/Kronoshus/carbon-law (branch `main`).** Read before planning:
   - `README.md`.
   - `docs/legal-workflow-stages.md`: the 10 matter stages (Intake, Attorney Scope, Client Data Collection, Drafting, Review Queue, Client Review, Signing Preparation, Execution, Funding Follow-Up, Closed) and the change-request triggers.
   - `docs/scope-and-review-standards.md`: the core scope (trust, will, financial power of attorney, health care directive, guardian nomination, signing preparation), the default exclusions, the decisions reserved to the attorney, and turnaround times.
   - `docs/client-portal-spec.md`: intake, uploads, status, appointment booking, cancelling and rescheduling, change requests, audit log, roles.
   - `docs/technology-stack.md`, `docs/backend-deployment.md`, `render.yaml`.
   - `backend/app.py`, `backend/db.py`, `backend/schema.sql`: the FastAPI backend with roles client, paralegal, attorney and admin. It has matters, workflows, appointments, documents, change requests, tasks and contacts, and already calls Beam (`BEAM_BASE_URL`, `BEAM_MODEL`).
   - `prompt-library/`: the drafting prompts and the California taxonomy.
   - `templates/california/`: demo forms and the verified-statute notes.
2. **The working prototype: folder `avatar-intake/` in the same repository.** Read `avatar-intake/README.md` and `avatar-intake/IMPROVE_PROMPT.md`, then `server.py`, `index.html`, `guion-plan.json` and `guion-plan-en.json`, `calavera_art.py` and `make_calavera.py`. Run it locally (`python server.py --check`, then `python server.py`, and open `http://127.0.0.1:8765/?guion=guion-plan&avatar=calavera`).
   - The photo-based avatar of attorney Raval is deliberately not in the public repository: no photos and no face model. Its build scripts (`prep_photo.py`, `make_avatar.py`) are. Ask Carbon Law for the assets privately if you need them.
   - It already solves, and the new app must keep:
   - a talking 3D or 2D character in three.js, with shape keys `jawOpen, blink, mouthRound, browUp, headYaw, headPitch, headRoll, lookX` and lip-sync from the voice's letter timings;
   - free local voices: Piper `es_MX-ald-medium` for Spanish and Kokoro `am_adam` for English (both allowed for commercial use), and faster-whisper transcription; ElevenLabs is optional and off;
   - recording consent with a three-way answer (yes, no, unclear) and an operator check when unclear; a refusal deletes the audio;
   - a conflict-of-interest check on names only, before any other personal detail is collected;
   - a hidden checklist that steers a wandering client back to the next open question (`[DONE: ...]` and `[DOCS: ...]` tags);
   - the client choosing documents (will, living trust, financial power of attorney, health care directive) and covering each in turn;
   - full-length attorney-review drafts of each document (`drafter()`, `draft()`, `draft_all()`): client facts only, yellow `[ATTORNEY TO COMPLETE]` for missing facts, green `[ATTORNEY TO CONFIRM]` for standard terms the client did not choose, no signature block, and citations only from the `VERIFIED` list of California Probate Code sections read from leginfo.legislature.ca.gov;
   - the Day of the Dead calavera character, a cheerful skull in a suit and sombrero.

   Port this logic into the new app. Do not rewrite it from memory.

## 2. The product

A fun, Duolingo-style app, Spanish first with full English, that does two things at once:

1. **Teaches estate planning.** Short daily lessons, games and quizzes take a person from "what is a will?" to understanding a California estate plan: will, revocable living trust, financial power of attorney, advance health care directive, guardians for minor children, probate, community property, beneficiary designations, funding a trust, and signing with witnesses or a notary.
2. **Builds their documents while they learn.** Each lesson ends by gathering the person's own facts for that document. After the will lesson, for example: "Who would you want to care for your children?" Those answers fill the client's intake. When the client wants the documents prepared, they pay the firm. The firm then generates the documents, the attorney reviews them, the client signs, and a final lesson teaches how to look after them.

**The whole journey takes two weeks from the first lesson to the final lesson.** The journey, in order (section 2.5 has the day-by-day timeline):
1. Sign-up, consent and the names-only conflict check.
2. Four free core lessons, each lowering the will price.
3. The rest of the intake, then payment.
4. Documents generated.
5. Attorney review.
6. Client review.
7. Signing.
8. The final lesson on keeping and sharing the documents.

The characters are interactive AI agents (Beam via the backend) who teach, answer general questions, play the games with the client, and guide the client through the intake conversation.

### 2.1 Platforms (one shared codebase)

- **Web app:** responsive, works on a phone browser and installable as a PWA. Host the static front end like the existing `web/` (GitHub Pages or similar).
- **Chrome extension (Manifest V3):** the same app in Chrome's side panel, plus a toolbar popup showing the daily streak and the next lesson.
  - Use a side panel or an offscreen document for microphone access. Request the microphone only after the user clicks.
  - The extension holds no secrets. It talks only to the firm's backend.
  - Package it for the Chrome Web Store with a privacy policy page.
- Build as one front end (for example Vite with TypeScript and three.js) with two build targets. No duplicated business logic.

### 2.2 The learning path: four core lessons and a final lesson

The free part of the app is **four core lessons**, one per document in the firm's core scope. Each can be finished in a day (about 15 to 20 minutes, split into 3 to 5 minute steps).

1. **El testamento (the will):**
   - what a will does;
   - executor, gifts and the residue;
   - guardians for minor children;
   - what happens without a will;
   - what passes outside a will (retirement accounts, life insurance, joint accounts);
   - community property.
2. **El fideicomiso en vida (the revocable living trust):**
   - what a trust is and how it avoids probate;
   - settlor, trustee and successor trustee, beneficiaries;
   - funding the trust (putting the house and accounts in it);
   - the pour-over will that goes with it.
3. **La directiva anticipada de atención médica (the advance health care directive):**
   - the health care agent and alternates;
   - end-of-life wishes;
   - pain relief, organ donation;
   - HIPAA release of medical information.
4. **Los poderes notariales (financial powers of attorney):**
   - the agent and alternates;
   - when it starts (right away, or only on incapacity);
   - what the agent can and cannot do;
   - gifts;
   - why banks may ask for it.

Each core lesson ends with **"Tus datos" (your details)**: the character gathers the client's own facts for that document, using the prototype's questions in `guion-plan.json` for that document, and saves them to the intake. These steps are optional until the client decides to buy that document.

"Tus datos" opens only after the client has given recording consent and the names-only conflict check on day 1 (section 2.5): the firm's rule is conflict check before any personal details.

After the documents are signed, the app unlocks the **final lesson: "Cuida tus documentos" (look after your documents).** It teaches how to keep the originals safe and who to give what to:
- **storing the signed originals:** in a fireproof place at home or a safe place the firm recommends, not somewhere only the client can open (a safe-deposit box can be hard for others to reach after a death);
- **who gets a copy or must know where the originals are:**
  - the **executor** (will);
  - the **successor trustee** (trust; keep the trust's funding records with it);
  - the **agent** under the financial power of attorney (and possibly the client's bank);
  - the **health care agent** and the client's doctors (health care directive).
- **Trust funding:** how to finish putting assets into the trust, and the funding checklist from the firm (Stage 9).
- **Beneficiary designations:** keep retirement accounts and life insurance in line with the plan.
- **When to update:** the firm's change-request triggers (marriage, divorce, a new child, new property or business, a change of fiduciary or of who gets what, a beneficiary's death or incapacity). Show how to send a change request in the app.
- A short closing quiz, a "plan complete" celebration, and an annual check-in reminder.

Exercise types in every lesson:
- multiple choice, true or false, match pairs, put the steps in order;
- "what would happen if…" scenarios, listening exercises using the character's voice, and spoken answers;
- a short conversation with the character at the end of each lesson.

Add Duolingo-style motivation, tuned to stay respectful about a serious subject:
- XP, a daily streak (a natural fit for the one-lesson-a-day pace), levels and badges (one per lesson, plus "plan complete");
- retries, lesson-complete celebrations, and gentle reminders that the person can switch off.

Opus may add optional bonus lessons (for example probate, community property, or "what to bring to your appointment"). They must not lengthen the core path or delay the two-week journey.

### 2.3 The characters

Opus designs a cast of Hispanic-themed characters in Blender, cheerful and warm, never mocking or stereotyped. Each character:
- has a role, a voice and a persona prompt;
- uses the same shape-key rig (so one animation engine drives all of them);
- has idle, talking, celebrating and "thinking" states.

Starting cast:
- **La Calavera (already built: the lead character and the face of the app).** Keep his look and personality and build the app around him; do not replace or redesign him without Carbon Law's approval. The other characters must sit beside him in the same style and rig.
  - **Look:** a cheerful 2D Day of the Dead sugar skull in a black suit with a purple bow tie and a marigold boutonniere, wearing a straw sombrero with a red band, a marigold, colored dots and hanging pompoms. He has sparkly gold eyes with a smiling lower lid, rosy cheeks with pink swirls, a grin that curls up at the corners, and a pink heart on his chin. Behind him: papel picado, candles and cempasúchil. See `avatar-intake/calavera-preview.png`.
  - **Files:**
    - `avatar-intake/calavera_art.py` draws the art in code (PIL) and writes `calavera.png`, `calavera-bg.png` and `calavera.json` (where the jaw, eyes, pupils, brows and neck are).
    - `avatar-intake/make_calavera.py` (`blender -b -P make_calavera.py`) builds `calavera.blend` and `calavera.glb` with the shared shape keys.
    - `index.html?avatar=calavera` animates him: lip-sync, blinking, glances, head movement, nodding while listening.
  - **Voice:** Piper `es_MX-ald-medium` in Spanish, Kokoro `am_adam` in English.
  - **Behavior already in place:**
    - he discloses that he is an AI program, not the attorney and not a person, and never claims to be the attorney's likeness;
    - he runs the full estate plan conversation: consent, conflict check, document choice, each document in turn, contact details;
    - he steers wandering clients back to the next open question.
  - **His roles in the app:** main guide; host of the course map, the will and trust lessons, the intake conversation and the final "Cuida tus documentos" lesson; he celebrates finished lessons and appears in the daily reminder.
  - **Name:** Opus proposes a warm name (for example "Don Calavera" or "Calaquita") and Carbon Law chooses.
  - **Opus's work on him:**
    - add the extra states (celebrating, thinking, waving, a happy dance for a finished unit) and a small set of costume variants for the units (for example reading glasses for the documents unit);
    - make sure he looks crisp on phones and in the extension's side panel;
    - all of it in Blender, keeping his shape-key rig.
- **Piñata**: a colorful burro piñata. Hosts the games and quizzes, bursts into confetti on a correct streak.
- **El Oso**: a big, happy bear. The gentle guide for the health care directive lesson and the hard conversations (incapacity, end of life). Calm and kind.
- Opus may add more, for example a hummingbird (colibrí) for daily reminders, or a grandmother (abuelita) figure who explains family topics. Each new character needs Opus's design and a note on why it fits.

Use the existing calavera pipeline (`avatar-intake/calavera_art.py` and `avatar-intake/make_calavera.py`) as the pattern for every new character: art drawn in code, Blender script, GLB with the shared shape keys. Keep source art, the `.blend` file and the build script in the repo, so a character can be rebuilt with one command.

### 2.4 Talking with the characters (Beam)

- All AI calls go through the firm's backend. The Beam key is a server secret (`REFLECTION_API_KEY` or `BEAM_API_KEY`) and is never sent to the browser or the extension.
- Port the prototype's conversation engine:
  - persona plus the lesson or intake checklist;
  - the hidden checklist tags that steer the client back on track;
  - `reasoning_content` round-tripping, and `spoken()` and `looping()` guards;
  - one question per turn;
  - character persona prompts editable by staff (section 3).
- Voice: speech in and speech out on the server (Whisper, Piper or Kokoro in a CPU container), with the browser's own speech as a fallback. Typed chat always works too.
- Learning mode: the character answers general questions about the lesson topic in simple words and quizzes the user. It never gives advice about the person's own situation; for that it says the attorney will answer and logs the question for the attorney.
- Intake mode, in this order:
  1. AI disclosure, and consent to record and transcribe.
  2. Conflict check on names only, before anything else.
  3. The person chooses the documents they want prepared.
  4. Each chosen document is covered in turn: anything not already given in the lessons' "Tus datos" steps.
  5. Contact details, then payment (section 2.5).

### 2.5 Payment, documents, signing: the two-week journey

**Timeline, day by day.** The app shows the client a progress tracker with the day and the next step. Staff see the same dates in the backend and are alerted when a step is late. The plan fits the firm's turnaround standards (`docs/scope-and-review-standards.md`). Days are calendar days; the attorney-review and revision steps are business days, so when a weekend falls in the middle, the later days shift and the tracker says so. Opus may adjust days, never the order.

- **Day 1: Bienvenida + El testamento** (La Calavera). Firm stage: 1 Intake.
  - Sign-up with an age check (adults only).
  - La Calavera introduces himself and says he is an AI program, not the attorney.
  - Consent to record and transcribe.
  - Names-only conflict check: the client, spouse or partner, children, and the people they would name. The firm clears it in the background over the next days.
  - Core lesson 1, the will, then its quiz and "Tus datos": family, children, guardians, executor, gifts, who inherits.
  - Will price $3,000 → **$2,900**.
- **Day 2: El fideicomiso en vida** (La Calavera, with Piñata running the games). Stage 1.
  - Core lesson 2, the living trust: games and "Tus datos" (individual or joint trust, successor trustee, what goes into the trust, ages for young beneficiaries).
  - Price → **$2,800**.
- **Day 3: La directiva de salud** (El Oso). Stage 1.
  - Core lesson 3, the advance health care directive, with "Tus datos" (health care agent and alternates, end-of-life wishes in the client's own words, pain relief, organ donation, release of medical information).
  - Price → **$2,700**.
- **Day 4: Los poderes notariales** (La Calavera and Piñata). Stage 1.
  - Core lesson 4, financial powers of attorney, with "Tus datos" (agent and alternates, starts now or on incapacity, scope, gifts).
  - Price → **$2,600**.
  - The client reviews the summary of everything they gave and fills any gaps with La Calavera (contact details, assets).
  - Finishing the intake brings the price to **$2,500** (see Pricing).
  - Optional: book a short consultation with the attorney.
- **Day 5: Firmar el acuerdo y pagar.** Stage 2 Attorney Scope.
  - The firm has cleared the conflict.
  - The client chooses the documents to prepare and receives the attorney-approved engagement letter and fee agreement, signs them in the app, and pays.
  - Payment starts generation: full-length first drafts are ready in minutes, for the attorney only (stage 4 Drafting).
  - La Calavera explains what happens next.
- **Days 6 to 8: El abogado revisa.** Stage 5 Review Queue (3 business days).
  - The attorney reviews and edits the drafts. The client sees "the attorney is reviewing your documents".
  - Meanwhile the app keeps the streak alive with short refreshers, and a "get ready" list: deeds and recent account statements for trust funding, the IDs needed at signing, and thinking about where the originals will be kept.
- **Day 9: Revisa tus documentos.** Stage 6 Client Review.
  - The attorney-approved documents are released to the client.
  - La Calavera walks through each one in plain words, section by section, without giving new legal advice. The client confirms or asks for changes in the app.
- **Day 10: Cambios y cita de firma.** Stage 6 into Stage 7.
  - Requested changes go back to the attorney (2 business days for revisions) and the revised documents come back for confirmation.
  - The client books the signing appointment for day 13.
- **Days 11 and 12: Prepárate para firmar.** Stage 7 Signing Preparation.
  - A signing guide: who signs what; that the will needs two witnesses and the powers of attorney and health care directive need witnesses or a notary; who cannot be a witness (no one who inherits under the will, not the agent named in the document); what to bring.
  - Reminders the day before.
- **Day 13: La firma.** Stage 8 Execution.
  - The signing appointment.
  - Staff upload the executed documents, which the client can then download.
  - A celebration in the app.
- **Day 14: Cuida tus documentos.** Stage 9 Funding Follow-Up.
  - The final lesson unlocks (section 2.2): storing the originals, who gets copies (executor, successor trustee, agents, doctors), finishing trust funding with the firm's funding checklist, beneficiary designations, and when to update.
  - "Plan complete" badge and an annual check-in reminder.
  - The matter moves to stage 10 Closed when funding follow-up is done.

**Pricing (settings the firm controls; these are the starting values):**
- **Will: starts at $3,000.** Each completed core lesson takes **$100** off, down to a floor of **$2,500**.
- Five steps earn $100 each: the four core lessons ($2,600) and **finishing the intake** on day 4 ($2,500). Carbon Law chose this on 2026-11-17. Keep the steps as backend settings so the firm can change them later.
- The price shown always says what was earned ("$3,000 − $400 for completing 4 lessons").
- Build the rules as settings in the backend: base price per document and per package, the discount per lesson, which steps earn a discount, and the floor. A discount, once earned, stays earned.
- Prices for the trust, the powers of attorney, the health care directive and packages are set by the firm (placeholders until then).
- The attorney approves how discounts are described in the app and in any advertising.

**Payment:**
- After the four core lessons and the intake, the client chooses the documents they want prepared and sees the price for each and for the package, with the discounts they earned.
- The client pays in the app (for example Stripe Checkout through the backend; card details never touch the firm's servers or the extension).
- Payment is taken only after the conflict check is cleared and the client has signed the engagement letter and fee agreement that the attorney approved. California requires a written fee agreement in many cases, and the attorney decides its wording.
- Prices, refunds, packages and which bank account receives the money are the firm's decisions. The attorney decides how advance fees are held under the State Bar rules. Build the settings for these; do not choose them.
- Test with the payment provider's test mode only, until the firm approves going live.

**Documents:**
- Payment starts generation: the ported drafters write full-length first drafts of the documents paid for, to the prototype's standard. A trust together with a will gives a pour-over will.
- Drafts go to the attorney's review queue (Stage 5). **The client never sees a draft until the attorney approves it**, as the client-portal spec requires.
- After approval, the client reviews in the app, can ask for changes, and confirms.

**Appointments:**
- The client books the signing appointment, and any consultation, from the firm's availability, set by staff in the backend; they can cancel or reschedule.
- A consultation can be booked any time after the core lessons if the client wants to talk to the attorney first.
- Use the backend's appointment endpoints; Cal.com is an optional adapter. Send confirmations by email, and ntfy push to staff.

## 3. The backend Carbon Law controls

Extend the existing carbon-law FastAPI backend and its staff pages (`web/admin.html`, `web/dashboard.html`). Do not build a second backend. Add:
- **Content management:** units, lessons, exercises, quiz questions, character persona prompts, scripted lines, Spanish and English text.
  - Draft, review and publish states.
  - Any change to legal wording must be approved by an attorney before it publishes. Record who approved it and when.
- **Characters:** turn characters on or off; assign them to units; preview their voice.
- **Learners and clients:** progress, streaks, intake status, conflict status, payment status, where each client is on the two-week timeline (with late steps flagged), questions logged for the attorney, drafts awaiting review, appointments.
- **Payments:** prices per document and package, the lesson-discount rules (amount per step, which steps count, the floor), engagement letter and fee agreement templates (attorney-approved), refunds, receipts, and the payment provider's settings (test mode until the firm approves live).
- **Firm controls:** office hours and appointment availability; conflict list upload (CSV, as in the prototype); data-retention settings; on/off switches for voice recording, AI chat, and the extension.
- **Analytics** without client content: lesson completion, drop-off points, quiz accuracy per question (to find confusing lessons), how many learners pay, and how many finish the two weeks on time.
- **Audit log** for every staff and client action, plus role-based access (client, paralegal, attorney, admin), as the portal spec requires.

## 4. Suggested architecture (Opus decides)

- Front end: TypeScript, three.js for the characters, one design system, i18n with Spanish and English string files (no hard-coded text), accessible (WCAG 2.1 AA), works on low-end Android phones.
- Back end: the existing FastAPI app plus new routers (`/learn`, `/characters`, `/chat`, `/voice`, `/drafts`, `/content`, `/availability`). Database migrations from `backend/schema.sql`.
- A worker for slow jobs: drafting, voice and transcription.
- AI: a Beam client module with retries, the loop guard, `reasoning_content` handling and per-call cost and latency logging. Use one interface, so the firm could switch to another model.
- Storage: client data and audio only in the firm's backend storage, encrypted at rest; never in the extension's storage beyond a session token.

## 5. Plan and acceptance criteria

Work in phases. Each phase ends with a demo, a short written report, and passing CI.

1. **Discovery (Opus):** read every source in section 1; write the product spec, information architecture, design system and the ticket backlog. Show 3 screen designs and the character lineup sketches to Carbon Law before building.
2. **Foundations (Beam, Opus reviewing):** repo layout, both build targets, backend routers and migrations, auth for the new screens, i18n, CI with tests.
3. **Characters (Opus only):** port the calavera; design and build the piñata and the bear in Blender with the shared rig; one animation engine drives all three.
4. **Learning (Opus designs the lessons, Beam builds the engine):** the four core lessons and the final lesson, complete in Spanish and English with all exercise types, XP, streaks and badges.
5. **Conversation and intake (shared):** port the conversation engine, consent, conflict check, document choice, the steering checklist, and voice in and out. Wire lessons to intake.
6. **Payment, documents and appointments (Beam builds, Opus reviews the legal outputs):**
   - engagement letter and fee agreement signing, then payment in test mode;
   - port the drafters, generation on payment, the attorney review queue, client review;
   - availability, booking, cancel and reschedule, notifications;
   - the two-week timeline tracker for the client and staff.
7. **Staff controls:** content management with attorney approval, characters, learners, firm controls, analytics, audit log.
8. **Extension and polish:** Chrome side panel and popup, PWA install, accessibility audit, performance on a mid-range phone, Store package.

The release is done when:
- a new test user can go through the whole journey in Spanish on a phone: the four core lessons, intake, conflict check, engagement letter, test payment, generated drafts in the attorney queue, attorney approval, client review, booked signing appointment, signing recorded, and the final lesson unlocked. Each step lands on the day the timeline shows, and staff are alerted when a step is late;
- the same works in the Chrome side panel;
- conflict is checked before any detail is collected, and a possible conflict stops the flow without saying why;
- a refusal to record keeps nothing;
- drafts are full-length, cite only verified sections, and are visible only to staff until attorney approval;
- staff can change a lesson, a quiz question and a character's lines without a developer, and legal wording needs attorney approval;
- automated tests cover the backend routes, the Beam client (with a stubbed model), the steering checklist, consent and conflict logic, drafting, and the main user path end to end in both build targets.

## 6. Legal and safety guardrails (non-negotiable)

- **General information only, never legal advice.** Characters and lessons explain concepts. Questions about the person's own situation are logged for the attorney. No fee quotes, no promised results, no "your will is done".
- **Every legal statement in a lesson or quiz must be traceable.** Each needs an official source (California Probate Code read on leginfo.legislature.ca.gov, or the California Courts self-help pages) recorded in the content system. Each lesson carries an "attorney approved" flag before it can publish.
  - leginfo blocks automated fetches (HTTP 403); read it in a real browser.
  - Reuse the prototype's `VERIFIED` list and add to it the same way.
- **AI disclosure:** every character says it is an AI program, not the attorney and not a person, before any conversation. A character that is not the attorney's likeness never claims to be.
- **Order of collection:** consent, then names-only conflict check, then everything else. Nothing more is collected or sent to Beam after a possible conflict or a refusal.
- **Drafts** are for attorney review only. Never show them to the client before approval; never include signature, witness or notary blocks; keep the yellow and green markers.
- **Payment:** never take payment before the conflict check is cleared and the engagement letter and fee agreement are signed. Never store card details. Prices and payment handling are set by the firm and the attorney.
- **Scope:** respect the firm's default exclusions (probate administration, trust administration after death, advanced tax, business succession, foreign assets, special-needs trusts, title review) and the attorney-reserved decisions. Characters say these need the attorney.
- **Data:**
  - Client interviews may go to Beam: the firm approved this on 2026-11-15 for this tool; confirm it covers the new app.
  - Audio stays on the firm's servers.
  - Use fictional data for all demos and tests. Never commit client data or keys. Use firm-owned keys in production.
  - The firm must set retention periods and Reflection's data settings before launch.
- **Audience:** adults only (age check at sign-up). Accessible, plain-language Spanish written for ordinary readers, reviewed by a native speaker. Spanish and English say the same thing.
- **Culture:** Day of the Dead and other Hispanic imagery used with warmth and respect. Opus reviews every character and visual for stereotypes before release.

## 7. Working rules

- Work in the carbon-law repository on feature branches with pull requests. Keep `main` deployable. Keep the existing site and backend working.
- Before claiming any phase is done, run the full test suite and the end-to-end path in both build targets. Report failures honestly, with output.
- Keep a running decision log (`docs/aprende-decisions.md`) and update `IMPROVE_PROMPT`-style hand-off notes, so another agent can continue.
- Ask Carbon Law (Kevin) before:
  - spending money;
  - publishing anything public, including the Chrome Web Store listing;
  - changing legal wording without attorney approval;
  - touching real client data.
- When a decision is the firm's (prices, which documents to offer, office hours, retention), put it in a short list of questions instead of guessing.
