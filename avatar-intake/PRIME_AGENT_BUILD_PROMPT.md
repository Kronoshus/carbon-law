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
2. **Builds their documents while they learn.** Each lesson ends by gathering the person's own facts for that topic. After the guardian lesson, for example: "Who would you want to care for your children?" Those answers fill the client's intake, which flows into the firm's matter workflow. Once the client finishes and enters their information, they can book an appointment with the firm, and the attorney gets first drafts to review.

The characters are interactive AI agents (Beam via the backend) who teach, answer general questions, play the games with the client, and guide the client through the intake conversation.

### 2.1 Platforms (one shared codebase)

- **Web app:** responsive, works on a phone browser and installable as a PWA. Host the static front end like the existing `web/` (GitHub Pages or similar).
- **Chrome extension (Manifest V3):** the same app in Chrome's side panel, plus a toolbar popup showing the daily streak and the next lesson.
  - Use a side panel or an offscreen document for microphone access. Request the microphone only after the user clicks.
  - The extension holds no secrets. It talks only to the firm's backend.
  - Package it for the Chrome Web Store with a privacy policy page.
- Build as one front end (for example Vite with TypeScript and three.js) with two build targets. No duplicated business logic.

### 2.2 The learning path

Base the course map on the firm's stages and core scope. Suggested units, which Opus refines:

1. ¿Por qué planear? (why plan; what happens without a plan; myths)
2. Tu familia y tus bienes (family, community and separate property, what passes outside a will)
3. El testamento (will: executor, gifts, residue, guardians)
4. El fideicomiso en vida (living trust: trustee, successor trustee, probate avoided, funding)
5. Poder financiero (durable financial power of attorney: agent, when it starts, gifts)
6. Directiva de salud (advance health care directive: agent, end-of-life wishes, HIPAA)
7. Firmar y guardar (signing, witnesses and notary, storing, funding follow-up, when to update: the change-request triggers)
8. Tu cita con el abogado (what to bring, what happens next: the firm's stages 1 to 10 in plain words)

Each unit has lessons of 3 to 5 minutes. Exercise types:
- multiple choice, true or false, match pairs, put the steps in order;
- "what would happen if…" scenarios, listening exercises using the character's voice, and spoken answers;
- a boss conversation with the character at the end of each unit.

Add Duolingo-style motivation, tuned to stay respectful about a serious subject:
- XP, a daily streak with a freeze, levels, badges and a weekly goal;
- hearts or retries, lesson-complete celebrations, and gentle reminders that the person can switch off.

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
  - **His roles in the app:** main guide; host of the course map, the will and trust units and the intake conversation; he celebrates finished units and appears in the daily reminder.
  - **Name:** Opus proposes a warm name (for example "Don Calavera" or "Calaquita") and Carbon Law chooses.
  - **Opus's work on him:**
    - add the extra states (celebrating, thinking, waving, a happy dance for a finished unit) and a small set of costume variants for the units (for example reading glasses for the documents unit);
    - make sure he looks crisp on phones and in the extension's side panel;
    - all of it in Blender, keeping his shape-key rig.
- **Piñata**: a colorful burro piñata. Hosts the games and quizzes, bursts into confetti on a correct streak.
- **El Oso**: a big, happy bear. The gentle guide for health care and the hard conversations (incapacity, end of life). Calm and kind.
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
  3. The person chooses their documents.
  4. Each chosen document is covered in turn.
  5. Contact details, then appointment booking.

### 2.5 From learning to documents to appointment

- Answers gathered in lessons and conversations are saved to the client's intake on the backend, using the existing `/intake` and `/workflows` shapes. The client can review and edit everything before submitting.
- On submission:
  - the matter enters the firm's workflow at Stage 1 (Intake);
  - the conflict status is recorded;
  - first drafts of the chosen documents are generated in the background by the ported drafters (full-length, the same standard as the prototype);
  - the drafts go to the attorney's review queue (Stage 5). **The client never sees a draft until the attorney approves it**, as the client-portal spec requires.
- Appointment booking: available only after intake is submitted and the conflict check is clear.
  - The client picks a slot from the firm's availability, set by staff in the backend, and can cancel or reschedule.
  - Use the backend's appointment endpoints; Cal.com is an optional adapter.
  - Send confirmations by email, and ntfy push to staff.

## 3. The backend Carbon Law controls

Extend the existing carbon-law FastAPI backend and its staff pages (`web/admin.html`, `web/dashboard.html`). Do not build a second backend. Add:
- **Content management:** units, lessons, exercises, quiz questions, character persona prompts, scripted lines, Spanish and English text.
  - Draft, review and publish states.
  - Any change to legal wording must be approved by an attorney before it publishes. Record who approved it and when.
- **Characters:** turn characters on or off; assign them to units; preview their voice.
- **Learners and clients:** progress, streaks, intake status, conflict status, questions logged for the attorney, drafts awaiting review, appointments.
- **Firm controls:** office hours and appointment availability; conflict list upload (CSV, as in the prototype); data-retention settings; on/off switches for voice recording, AI chat, and the extension.
- **Analytics** without client content: lesson completion, drop-off points, quiz accuracy per question (to find confusing lessons), and how often learners become booked clients.
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
4. **Learning (Opus designs the lessons, Beam builds the engine):** units 1 to 3 complete in Spanish and English with all exercise types, XP, streaks and badges.
5. **Conversation and intake (shared):** port the conversation engine, consent, conflict check, document choice, the steering checklist, and voice in and out. Wire lessons to intake.
6. **Documents and appointments (Beam builds, Opus reviews the legal outputs):** port the drafters, the attorney review queue, availability, booking, cancel and reschedule, notifications.
7. **Staff controls:** content management with attorney approval, characters, learners, firm controls, analytics, audit log.
8. **Extension and polish:** Chrome side panel and popup, PWA install, accessibility audit, performance on a mid-range phone, Store package.

The release is done when:
- a new user can go from first open to a booked appointment, in Spanish, in under 45 minutes, on a phone;
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
