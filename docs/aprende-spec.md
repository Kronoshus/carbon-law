# Aprende y Planea — product spec, information architecture and the 14-day journey

Phase 1 (Discovery) deliverable. Status: **draft for Carbon Law's approval**. Nothing in Phase 2 starts until this is approved.

Companion documents: `aprende-design.md` (design system, screens, characters), `aprende-architecture.md` (how it is built),
`aprende-backlog.md` (tickets for Phases 2–8), `aprende-questions.md` (decisions only the firm can make),
`aprende-decisions.md` (running decision log).

Sources read for this spec: `avatar-intake/PRIME_AGENT_BUILD_PROMPT.md` (the brief) and everything its section 1 lists:
the repo `README.md`; `docs/legal-workflow-stages.md`, `scope-and-review-standards.md`, `client-portal-spec.md`,
`technology-stack.md`, `backend-deployment.md`, `interrupt-and-change-control.md`; `render.yaml`;
`backend/app.py`, `db.py`, `schema.sql`; `prompt-library/` (both PRDs, both taxonomies, the four Carbon Law drafters);
`templates/california/` (checklists, the demo forms and their research note); and the whole `avatar-intake/` prototype
(`README.md`, `IMPROVE_PROMPT.md`, `server.py`, `index.html`, `guion-plan.json`, `guion-plan-en.json`, `calavera_art.py`,
`make_calavera.py`). The prototype's self-check (`python server.py --check`) and the backend suite (35 tests) pass on `main`.

---

## 1. What it is, for whom

A Spanish-first, fully bilingual, Duolingo-style app in which a cast of warm Day of the Dead and fiesta characters
teaches a person how a California estate plan works, one short lesson a day, and **gathers that person's own facts for
each document while they learn**. When they are ready they sign the firm's engagement letter, pay, and the firm drafts,
reviews, signs and closes the plan with them. The whole path takes about two weeks (firm decision F-001).

**Who it is for**

| Person | What they need from the app |
|---|---|
| **Ana, 58, Boyle Heights.** Spanish first, an Android phone a few years old, never used a lawyer, worried about her house and her grandchildren. | Plain Spanish, big text, nothing that feels like a test she can fail, the price in plain sight, a human at the end. |
| **Marco, 34, her son.** Bilingual, helps his mother with forms, uses Chrome at work. | English when he wants it, the side panel while he reads email, a clear "what happens next". |
| **Pankaj Raval, the attorney.** | A complete, consistent intake, drafts only after the client has paid and the conflict is cleared, nothing shown to a client he has not approved, questions about the client's own situation routed to him. |
| **Firm staff (paralegal, admin).** | Where every client is on the 14 days, what is late, the conflict queue, the content they can edit without a developer. |

## 2. Product principles

1. **Learn first, then decide.** The lessons are free and complete without buying anything. Buying is a separate, explicit step on day 5.
2. **General information, never advice.** Characters explain concepts. Anything about the person's own situation becomes a logged question for the attorney (section 9.3).
3. **The attorney is the gate.** Conflict clearance, the engagement letter, every draft and every word of legal content pass through the attorney before a client relies on them. The app makes those gates visible to the client instead of hiding them.
4. **Respectful game mechanics.** Streaks, petals (XP), seals (badges) and celebration — but **no lives, no hearts, no penalty for wrong answers, no countdown timers**, and **no confetti on hard topics** (incapacity, end of life, death of a parent). El Oso's lessons run in a calm mode (section 7.6).
5. **One thing per screen.** One question per screen and one question per character turn (the prototype's rule).
6. **Spanish and English say the same thing.** Every string exists in both catalogs; CI fails if one is missing. Spanish is the Spanish of Mexico, the most common variety among the firm's clients, with *usted* (decision #53, Q-L4); no Spain-only words.
7. **Order of collection is enforced by the server, not the screen.** Consent → names-only conflict check → everything else. The UI only reflects the server's gates.

## 3. Scope

**In v1:** the four core lessons, the final lesson "Cuida tus documentos", optional bonus lessons, three characters
(La Calavera, Piñata, El Oso), intake through "Tus datos" and a closing conversation, the conflict check, engagement letter
and fee agreement signing in the app, test-mode payment, draft generation and the attorney review queue, client review
and change requests, signing appointment booking, the 14-day tracker for client and staff, staff content management
with attorney approval, analytics without client content, the web app (installable PWA) and the Chrome extension.

**Not in v1:** live payments (test mode until the firm approves going live), a native mobile app, a deed or HIPAA form
as separate documents (HIPAA release is a section of the health care directive, as in the prototype), real-time video
with the attorney, any document type outside the firm's core scope, couples sharing one account (question Q-P6).

---

## 4. Information architecture

### 4.1 Map of the app

```
Bienvenida (public)
├── ¿Qué es esto?  — what the app is, the cast, "información general, no asesoría legal"
├── Crear cuenta   — adult check (yes/no, no birth date yet), name, email, password, language
└── Iniciar sesión

Day-1 gate (once, in this order, server-enforced)
├── 1. AI disclosure by La Calavera (he is an AI program, not the attorney, not a person)
├── 2. Consent to record and transcribe (sí / no / unclear → asked again in plain words; "no" = learning-only mode)
└── 3. Names-only conflict check (the client, spouse/partner, children, people they would name)

App (four tabs)
├── Aprender (course map)                       host: La Calavera
│   ├── Day node → Lesson player (steps, exercises, feedback with source)
│   │             → "Tus datos" (the character gathers that document's facts) → Lesson complete (petals, seal, new price)
│   ├── Bonus lessons (optional, never on the critical path)
│   └── Day 6–8 refreshers (Piñata)
├── Mi plan (the 14-day tracker)
│   ├── Timeline: each day, its date, done / today / next / late (and why a date moved)
│   ├── Precio: base price, each discount earned, the floor
│   ├── Mis datos: the summary of everything given, by document, with gaps to fill
│   ├── Documentos: chosen documents → engagement letter → payment → status → approved documents (client review)
│   │              → signed documents (download)  → funding checklist (download)
│   ├── Citas: consultation (optional, any time after the core lessons) and signing; book, cancel, reschedule
│   └── Cambios: send a change request (the firm's change types)
├── Preguntas
│   ├── Talk to a character (learning mode: general questions only)
│   └── Preguntas para el abogado: questions the characters logged for him, and his answers when he replies
└── Perfil
    ├── Language (español / English), voice on/off, voice speed, text size note
    ├── Reminders (daily time, on/off), notifications
    ├── Privacy: what the firm keeps, consent status, request deletion
    └── Cerrar sesión

Staff (existing web/admin.html and dashboard.html, extended — section 11)
Chrome extension: side panel = the whole app in a compact layout; toolbar popup = streak, today's step, "Abrir"
```

### 4.2 Routes and gates

Routes are hash routes inside one single-page app so the same bundle runs on GitHub Pages and in the extension.
Every gate below is checked **by the backend**; the router only hides what the server would refuse.

| Route | Who | Server gate |
|---|---|---|
| `#/bienvenida`, `#/entrar`, `#/cuenta-nueva` | public | — |
| `#/inicio/ia`, `#/inicio/consentimiento`, `#/inicio/nombres` | client | in that order; each step requires the previous |
| `#/aprender` | client | signed in |
| `#/leccion/:id` | client | lesson unlocked (section 6.2) |
| `#/leccion/:id/tus-datos` | client | consent = yes **and** automatic conflict result = clear (or firm-cleared) |
| `#/charla` | client | consent = yes and automatic conflict = clear |
| `#/plan`, `#/plan/precio`, `#/plan/datos` | client | signed in |
| `#/plan/carta` (engagement letter) | client | firm conflict clearance **and** attorney scope approval (section 6.1, day 5) |
| `#/plan/pago` | client | engagement letter and fee agreement signed |
| `#/plan/documentos/:id` | client | document status = Attorney Approved (never before) |
| `#/plan/citas` | client | consultation: core lessons done; signing: documents confirmed |
| `#/cuida` (final lesson) | client | signing recorded by staff |
| `#/perfil`, `#/preguntas` | client | signed in |

### 4.3 Navigation rules

- Four bottom tabs on phones and in the side panel; a left rail on screens wider than 64em.
- The lesson player is full screen with only "salir" (exit, keeps progress) and the progress bar.
- Deep links from reminders and the popup open the exact day node.
- "Back" never loses an answer: every step and every "Tus datos" answer is saved when it is given.

---

## 5. The journey as a state machine

One **journey** per client. Its state is a set of server-recorded facts (who did what, when); the "day" the client sees is
computed from those facts and the calendar (section 6.3), never stored as a counter.

| Fact (event) | Set by | Unlocks | Firm stage |
|---|---|---|---|
| `adult_confirmed` | client at sign-up | account | — |
| `ai_disclosed` | client (heard/read the disclosure) | consent question | 1 Intake |
| `consent` = yes / no | client | yes: names step; no: learning-only mode | 1 |
| `names_submitted` | client | automatic conflict check; a matter is created for staff | 1 |
| `conflict_auto` = clear / possible / no_list | server (`conflict_hits`, ported) | clear: "Tus datos" and character chat. possible: stop. no_list: wait for staff | 1 |
| `conflict_firm` = cleared / flagged | staff | cleared: engagement letter (with scope). flagged: stop | 1 |
| `lesson_completed:{will,trust,ahcd,poa}` | client | next day's lesson; a $100 discount each | 1 |
| `documents_tentative` | client (end of day 2) | attorney scope review starts | 1 → 2 |
| `scope_approved` | attorney | engagement letter can be generated | 2 Attorney Scope |
| `intake_completed` | server (every open question for the chosen documents covered or declined, plus contact) | the fifth $100 discount | 3 Client Data Collection (complete) |
| `documents_confirmed` | client (day 4 summary / day 5) | engagement letter content | 2 |
| `engagement_signed` | client | payment | 2 |
| `paid` | payment webhook (Stripe) | draft generation job | 4 Drafting |
| `drafts_ready` | worker | attorney review queue | 5 Review Queue |
| `attorney_approved` | attorney | documents released to the client | 6 Client Review |
| `client_confirmed` / `changes_requested` | client | confirmed: signing. changes: back to the attorney (2 business days) | 6 |
| `signing_booked` | client or staff | signing guide | 7 Signing Preparation |
| `signed` (executed documents uploaded) | staff | final lesson; signed documents downloadable | 8 Execution |
| `final_lesson_completed` | client | "plan completo" seal, annual reminder | 9 Funding Follow-Up |
| `funding_done` | staff | matter closed | 10 Closed |

Rules the server enforces:
- **Nothing personal is collected and nothing is sent to Beam** before `consent = yes` and `conflict_auto = clear` (or `conflict_firm = cleared` when the firm has uploaded no conflict list).
- After `conflict_auto = possible` or `conflict_firm = flagged`: the client sees *"Antes de continuar, la oficina necesita revisar alguna información. Le llamaremos pronto."* and nothing else. No reason, no names. All AI calls stop. The lessons stay readable.
- After `consent = no`: learning-only mode. Lessons and quizzes work (scripted content, no model), discounts are earned, no "Tus datos", no chat, no audio is kept. The client can change their mind from Perfil, which re-runs disclosure, consent and the names step. (Whether a declining client can do the intake with staff by phone: question Q-D3.)
- **No payment** before `conflict_firm = cleared` and `engagement_signed`.
- **No client sees a draft** before `attorney_approved`.

---

## 6. The 14-day journey, as it will be built

### 6.1 Day by day

Days 1–4 are the client's own pace (one core lesson a day). From day 5 the firm's turnaround standards set the pace.
"Firm stage" is the matter stage staff see in the dashboard.

**Day 1 — Bienvenida + El testamento** (La Calavera) · firm stage 1 Intake · price $3,000 → **$2,900**
1. Sign-up with an adult check ("Tengo 18 años o más": yes/no; the birth date is collected later, in "Tus datos").
2. La Calavera introduces himself: *"Soy un programa de inteligencia artificial de la oficina del abogado Pankaj Raval. No soy el abogado ni una persona. Lo que le explico es información general, no asesoría legal."*
3. Consent to record and transcribe (voice and typed chat are both transcripts). Three-way answer, as in the prototype: clear yes → continue; clear no → learning-only mode, and any audio of the answer is deleted; unclear → he asks once more in simpler words; still unclear → treated as no, with a button to change it later.
4. Names only, for the conflict check: the client, spouse or partner, children, and anyone they might name. The automatic check runs at once against the firm's uploaded list; the firm's own AI-assisted check continues in the background and clears the names within 24 hours, any day (decision #54, Q-W2).
5. Core lesson 1, the will (5 steps of 3–4 minutes): what a will does; executor, gifts and the residue; guardians for minor children; what happens without a will; what passes outside a will; community property. Quiz.
6. **Tus datos — testamento** (if the automatic check is clear): question ids `nombre, nacimiento, domicilio, estado_civil, hijos, herederos, legados, tutor, albacea` from `guion-plan.json`. Optional; skippable per question; resumable.
7. Celebration, price chip $2,900, reminder time chosen ("¿A qué hora le recuerdo mañana?").

**Day 2 — El fideicomiso en vida** (La Calavera; Piñata runs the games) · stage 1 · **$2,800**
1. Core lesson 2: what a trust is and how it avoids probate; settlor, trustee, successor trustee, beneficiaries; funding the trust; the pour-over will. Piñata hosts the match-pairs and order-the-steps games.
2. **Tus datos — fideicomiso**: `fid_tipo, fid_sucesor, fid_bienes, fid_menores` (the inheritance questions from day 1 also apply to the trust and are not asked again).
3. **Tentative document choice** (new, see 6.2): *"¿Qué documentos le interesan?"* — will, trust, health care directive, financial power of attorney, or "no sé todavía" (= all four, the attorney advises). This starts the attorney's scope review now, so the engagement letter is ready on day 5.

**Day 3 — La directiva de salud** (El Oso, calm mode) · stage 1 · **$2,700**
1. Core lesson 3: the health care agent and alternates; end-of-life wishes; pain relief; organ donation; release of medical information (HIPAA). No confetti, slower voice, a pause button always visible, an "hablemos después" exit that keeps progress.
2. **Tus datos — salud**: `salud_agente, salud_vida, salud_donacion, salud_info, salud_otros`. The end-of-life question is answered in the client's own words; El Oso never suggests an answer.

**Day 4 — Los poderes notariales** (La Calavera and Piñata) · stage 1 · **$2,600**, then **$2,500**
1. Core lesson 4: the agent and alternates; starts now or on incapacity; what the agent can and cannot do; gifts; why banks may ask for it.
2. **Tus datos — poder**: `poder_agente, poder_inicio, poder_alcance, poder_regalos`.
3. **Su resumen**: everything given so far, grouped by document, each answer editable; gaps listed. La Calavera fills the gaps in a short conversation: `bienes, otros, contacto`, plus anything skipped.
4. **Finishing the intake** (every open question for the documents of interest covered or declined, plus contact) earns the fifth discount: **$2,500**.
5. Confirms the documents to prepare (changing the day-2 choice re-opens the attorney's scope review: 1 business day).
6. Optional: book a short consultation with the attorney (available from here on).

**Day 5 — Firmar el acuerdo y pagar** · stage 2 Attorney Scope → 4 Drafting
1. Gates shown as a checklist: conflict cleared by the firm ✓, engagement letter ready ✓ (scope approved by the attorney).
2. The engagement letter and fee agreement (the attorney's approved template, filled with the chosen documents and prices) is shown in full; the client signs in the app (typed name + "Acepto" + timestamp; legal sufficiency: question Q-P3).
3. The price screen (design screen 3): each chosen document, the will's discount ledger, the package if cheaper, the total.
4. Payment through Stripe Checkout (test mode). The payment webhook — not the browser — records `paid`.
5. Payment starts generation: full-length drafts of the paid documents (trust + will ⇒ pour-over will), attorney-only.
6. La Calavera explains what happens next and that the attorney reviews before the client sees anything.

**Days 6–8 — El abogado revisa** · stage 5 Review Queue (3 business days)
- The client sees *"El abogado está revisando sus documentos"*, the expected release date, and nothing of the drafts.
- Daily 3-minute refreshers with Piñata keep the streak; a "prepárese" list: deeds and recent statements for trust funding, IDs for signing, where the originals will be kept.
- Staff are alerted (dashboard flag + ntfy) if the review is not done by its due date.

**Day 9 — Revise sus documentos** · stage 6 Client Review
- The attorney-approved documents are released. La Calavera walks through each one section by section in plain words, using the attorney-approved plain-language summary (question Q-L3), never new advice.
- Per document: "Está bien" or "Quiero un cambio" (a change request of the firm's types, with the client's words).

**Day 10 — Cambios y cita de firma** · stage 6 → 7
- Requested changes go to the attorney (2 business days); the revised documents come back for confirmation.
- The client books the signing appointment from the firm's availability (target: day 13).

**Days 11–12 — Prepárese para firmar** · stage 7 Signing Preparation
- The signing guide: who signs what; the will needs two witnesses present together (Probate Code section 6110), no one who inherits under the will should witness (section 6112); the powers of attorney and the health care directive need two qualified witnesses or a notary (sections 4121–4122, 4673–4674); the agent named in a document cannot witness it; what to bring.
- Reminders the day before and two hours before.

**Day 13 — La firma** · stage 8 Execution
- The appointment. Staff upload the executed documents; the client can download them. Celebration (the one big fiesta moment: all three characters).

**Day 14 — Cuida sus documentos** · stage 9 Funding Follow-Up
- The final lesson unlocks: storing the originals; who gets copies or must know where the originals are (executor, successor trustee with the funding records, financial agent and possibly the bank, health care agent and doctors); finishing trust funding with the firm's funding checklist (`templates/california/funding-checklist.md`); beneficiary designations; when to update (the firm's change-request triggers) and how to send a change request in the app.
- Closing quiz, "Plan completo" seal, annual check-in reminder. The matter moves to stage 10 when staff mark funding done.

### 6.2 Changes from the brief's timeline (order unchanged)

| Change | Why |
|---|---|
| **Tentative document choice on day 2** (final confirmation day 4) | The firm's standard is *"New matter scope review: 2 business days"*. If documents were chosen only on day 5, the engagement letter could not be attorney-approved the same day. Day 2 gives the attorney days 2–4. |
| **Next core lesson unlocks the next calendar day** (client's time zone), bonus lessons any time | Keeps the one-lesson-a-day rhythm the streak is built on, and gives the firm's background conflict check time to finish before payment. The limit is a firm setting (`lessons_per_day`, default 1; question Q-P5). |
| **"Tus datos" requires an automatic clear, not only a submitted list** | The brief's rule is "conflict check before any personal details". The firm's manual clearance takes days; the prototype's automatic check is instant. Details open on an automatic *clear*; payment waits for the firm's clearance. With no uploaded list, details wait for staff. |
| **Client review can happen the morning after release, any day of the week** | Only the firm's steps count business days; the client's do not. |

### 6.3 Timeline rules (what "Día 9" means on a calendar)

- Days 1–4: calendar days from the first lesson, in the client's time zone.
- Firm steps use **business days** in `America/Los_Angeles`, with a firm holiday list (setting): scope review (2), attorney review (3), revisions (2). Conflict clearance is the exception: the firm's AI-assisted check clears names within **24 hours, any day** (decision #54, setting `turnaround.conflict_hours`). Each step's due date is computed at the moment its clock starts and stored with the step.
- Every later day is computed from the actual completion time of the step before it. The tracker shows the **date** next to each day number, and when a weekend or holiday moves a date it says so: *"Día 9 · jueves 10 de diciembre (el fin de semana movió esta fecha 2 días)"*.
- **A step is late** when its due date passes without its event; staff are alerted once (dashboard flag + ntfy), and the client sees a calm message, never a blame.

**What this means in practice.** Simulating the firm's own turnaround standards (conflict within 24 hours, any day; scope 2, review 3, revisions
2 business days; signing on a business day) for each weekday a client could start on, with the reference implementation
the timeline ticket (T5-04) turns into a tested function (rerun with `timeline.plan` after decision #54 on 2026-11-23: the
24-hour conflict check changes no row, because the scope review sets the payment day):

| Client starts on | Pays on | Drafts released | Total days, no changes | Total days, with changes |
|---|---|---|---|---|
| Monday | Friday | Wednesday | 16 | 18 |
| Tuesday | Saturday | Wednesday | 15 | 17 |
| **Wednesday** | Sunday | Wednesday | **14** | 16 |
| **Thursday** | Tuesday | Friday | **14** | 16 |
| Friday | Wednesday | Monday | 16 | 19 |
| Saturday | Wednesday | Monday | 15 | 18 |
| Sunday | Thursday | Tuesday | 17 | 17 |

So **"two weeks" holds only for a Wednesday or Thursday start with no change requests**; otherwise the journey is 15–19
days. The app will say this honestly from day 1 ("Su plan termina alrededor del …"). **Firm decision (F-001, 2026-11-17): the app and
marketing promise "about two weeks".**

---

## 7. Learning

### 7.1 Structure

Unit (one per document, plus "Cuida tus documentos") → lesson (one per day, 15–20 minutes) → **steps** of 3–5 minutes
(a client can stop between steps) → **items** (one screen each: an explanation by the character, or an exercise).
The final step of every core lesson is "Tus datos". Lessons are content in the database (section 11), not code.

### 7.2 Exercise types

| Type | What the client does | Notes |
|---|---|---|
| Multiple choice | picks one of 2–4 | the workhorse; screen 2 in the design doc |
| True / false | "Cierto" / "Falso" | |
| Match pairs | joins term ↔ meaning (e.g. *albacea* ↔ "carries out the will") | Piñata's game; tap-tap, not drag-only |
| Put the steps in order | orders 3–5 steps (e.g. signing a will) | buttons to move up/down for keyboard and switch users |
| "¿Qué pasaría si…?" | a short scenario with fictional people, then a choice | never the client's own facts |
| Listening | hears the character, answers | always with a "mostrar texto" button; never the only way to answer |
| Spoken answer | answers out loud | only with consent; typed alternative always offered; transcribed on the firm's server |
| Conversation | a short chat with the character at the end of each lesson | learning mode (9.2); after consent and a clear conflict check |

Every item's feedback states the rule in one sentence and shows its **source** (section 10.2) and "Información general,
no asesoría legal". A wrong answer shows the right one and why; the item comes back later in the lesson. No penalty.

### 7.3 Completion and discounts

- A **core lesson is complete** when every step is done and its quiz is passed (80 % of items correct, any number of retries; the item order reshuffles). "Tus datos" is not required for the lesson discount.
- Discount events are recorded once and never revoked: `lesson_completed:will`, `:trust`, `:ahcd`, `:poa`, `intake_completed`.

### 7.4 Motivation

| Mechanic | Name in the app | Rule |
|---|---|---|
| XP | **pétalos** (cempasúchil petals) | +10 per correct item, +50 per lesson, +100 per "Tus datos" finished |
| Streak | **vela** (a candle, lit each day) | one lesson, refresher or bonus lesson a day; days 6–12 refreshers count; a missed day is "su vela descansó", not a loss of everything: one free rest day a week |
| Levels | Aprendiz → Conocedor → Planeador → Guardián | by petals; cosmetic only |
| Badges | **sellos** (notary-style seals) | one per core lesson, one for "Tus datos" complete, "Firmado", "Plan completo" |
| Celebration | full-screen moment | after lessons and signing; in calm mode a quiet card instead (7.6) |
| Reminders | the daily nudge | client picks the time; off with one switch; no more than one a day; La Calavera in the notification |

### 7.5 Bonus lessons (optional, never on the critical path)

"¿Qué es la sucesión (probate)?", "Bienes comunitarios en California", "Beneficiarios de cuentas y seguros",
"Qué traer a su cita". Each unlocks after day 1 and can be taken any day; none earns a price discount.

### 7.6 Calm mode

Used by El Oso and any item tagged `sensitive` (incapacity, end of life, death, disinheritance). Slower voice (0.9×),
no confetti or Piñata, a visible pause and "hablemos después", a soft completion card. Calm mode also turns off the
"+10" animation. Staff can tag any lesson item as sensitive.

---

## 8. The characters

| Character | Role | Hosts | Voice |
|---|---|---|---|
| **La Calavera** (name proposals in Q-C1) | lead guide, face of the app | course map, will and trust lessons, every "Tus datos", the intake conversation, day 9 walkthrough, "Cuida tus documentos", reminders | Piper `es_MX-ald-medium` / Kokoro `am_adam` (unchanged) |
| **Piñata** | games and quizzes | match pairs, order the steps, quizzes on days 2 and 4, refreshers days 6–8; confetti on a correct streak of 3 | to choose (Q-C3) |
| **El Oso** | the gentle guide | day 3 (health care directive) and every `sensitive` item | to choose; slow, warm (Q-C3) |

All three use one rig (the prototype's eight shape keys) and one animation engine, with four states each: idle,
talking, thinking/listening, celebrating (El Oso: comforting instead). Designs, sheets and the cultural review are in
`aprende-design.md` section 8. A hummingbird (colibrí) for reminders is proposed as an icon only, not a rigged character.

---

## 9. Talking with the characters (Beam, through the backend)

### 9.1 Both modes

Ported from `avatar-intake/server.py`, not rewritten: persona + checklist system prompt (`system_prompt`), the hidden
`[DONE: …]` and `[DOCS: …]` tags (`checklist`), `reasoning_content` sent back on every earlier assistant turn,
`spoken()` (first repeat, first question, 220 words) and `looping()` guards outside the model, one question per turn,
client text fenced as `<client_data>` (`UNTRUSTED`). Typed chat always works; voice is optional.

### 9.2 Learning mode

The character answers general questions about the lesson's topic in simple words, can quiz the client, and stays on
the lesson's approved explanations (the lesson's items are the "explanations you may draw on"). A question about the
client's own situation (*"¿mi hijo puede ser mi albacea si vive en México?"*) gets: *"Esa es una pregunta para el
abogado Raval. Ya se la anoté y él le responde."* The server stores it in **Preguntas para el abogado**.

### 9.3 Intake mode

In order: disclosure → consent → names-only conflict check → document interest → each document's "Tus datos" (at the
end of its lesson) → the day-4 summary conversation for gaps and contact → payment. The checklist is the union of the
chosen documents' question ids; anything already answered in a lesson is not asked again.

### 9.4 What a character never does

Claims to be the attorney or a person; quotes a fee (prices are shown by the app from firm settings, never spoken by a
character); promises a result; says a document is done or valid; gives advice about the client's own situation;
handles excluded scope (probate administration, trust administration after death, tax beyond standard provisions,
business succession, foreign assets, special-needs trusts, title review) other than to say the attorney will advise;
asks about immigration status (if the client raises it, it becomes a question for the attorney); sells or pitches
(payment is the firm's own screens, never a character); pairs a trust with insurance, annuities or other financial products.

---

## 10. Legal guardrails → how each is enforced

| Guardrail (brief section 6) | Enforced by | Proven by |
|---|---|---|
| General information only | persona prompts; `[ATTORNEY_QUESTION: …]` tag routed to the attorney log; content review | conversation test set (T5-08) incl. pushing for advice |
| Every legal statement traceable | content model: every item that states law must reference a `source` (a `VERIFIED` Probate Code section or a California Courts self-help URL); publish blocked otherwise | content validator test (T7-02) |
| Attorney approval of legal wording | content states draft → review → published; publishing a legal item requires an attorney's approval record (who, when, which version) | T7-01 tests |
| AI disclosure first | journey gate `ai_disclosed` before any chat endpoint answers | T5-02 |
| Consent, then names-only conflict, then everything else | server gates on every intake and chat route; `/chat` refuses before `conflict_auto=clear` | T5-03, T2-06 |
| Refusal keeps nothing | `consent=no` deletes any captured audio and transcript, keeps only the fact | T5-03 |
| Possible conflict stops without saying why | client endpoints return one neutral status; matched names only in a staff-only record | T5-03 |
| Drafts staff-only until approval | drafts stored `attorney_only`; client document routes return only `Attorney Approved`; no signature/witness/notary blocks; yellow/green markers kept | T6-05, T6-06 |
| No payment before clearance and signed letter | `/payments/checkout` refuses otherwise; `paid` only from a verified webhook | T6-02, T6-03 |
| Never store card details | Stripe Checkout hosted page; the backend sees only session ids | T6-03 review checklist |
| Scope exclusions | persona prompts and a scope list in settings | T5-08 |
| Data: audio and client data only on the firm's servers | voice service on the firm's backend; no browser speech recognition (it sends audio to a third party); extension stores only a session token | T5-06, T8-02 |
| Adults only | `adult_confirmed` required at sign-up | T2-05 |
| Spanish and English say the same thing | i18n key parity check in CI; content items have both languages before publish | T2-04, T7-01 |

### 10.1 Prices the characters may not quote

The app shows prices in UI chips and the price screen, from firm settings. Persona prompts forbid fee talk; the
attorney approves the wording of every price and discount description (Q-P2).

### 10.2 Sources

Each legal item stores `source_kind` (`probate_code` / `courts_selfhelp`), the citation (e.g. section 6110) and the date
it was read. `probate_code` must be in the `VERIFIED` list (`avatar-intake/server.py`, 56 sections read on leginfo
2026-11-15/16/17); a new section is added the same way the prototype added them (read in a real browser — leginfo
returns HTTP 403 to scripts). **Lesson content in Phase 4 will need sections that are not yet verified**, notably
intestate succession (6400–6414), community property (100–101 and the Family Code), and witness rules already covered;
the content ticket lists them for verification before it can publish.

---

## 11. Staff side (extends `web/admin.html` and `web/dashboard.html`)

- **Contenido**: units, lessons, steps, items (both languages), sources, persona prompts, scripted lines; draft → review → published; legal items need attorney approval; a preview with the character speaking.
- **Personajes**: on/off, unit assignment, voice preview.
- **Clientes**: list with journey day, late flags, conflict state, intake completeness, payment, drafts waiting, appointments, questions for the attorney.
- **Conflictos**: queue of submitted names (staff-only), automatic result, clear/flag buttons; upload `conflicts.csv`.
- **Pagos**: prices per document and package, discount rules (amount, which events, floor), engagement letter and fee agreement templates (attorney-approved, versioned), refunds, receipts, Stripe settings (test until approved).
- **Firma**: office hours, availability, holidays; data retention; switches for voice recording, AI chat and the extension.
- **Analítica** (no client content): lesson completion, drop-off by item, quiz accuracy per item, conversion to paid, on-time completion of the 14 days.
- **Auditoría**: every staff and client action (the existing audit log, extended).

---

## 12. Analytics events (no client content)

`lesson_started`, `item_answered{item_id, correct, attempt}`, `lesson_completed`, `datos_question_answered{question_id}` (no answer text),
`datos_completed`, `reminder_sent/opened`, `consent{yes|no}`, `conflict_auto{result}`, `documents_tentative{codes}`,
`engagement_signed`, `checkout_started`, `paid`, `drafts_ready`, `attorney_approved`, `client_confirmed`,
`changes_requested`, `signing_booked`, `signed`, `final_lesson_completed`, `step_late{step}`. Each carries the journey
day and the build target (web / extension). No names, no answers, no free text, no IP addresses in analytics.

## 13. Accessibility and language

WCAG 2.1 AA; text resizes to 200 % and honours the phone's text size (`<meta name="text-scale">`); 48 px targets; every
character line is also on screen as text; captions for every audio; no information by colour alone; reduced motion
respected; works with TalkBack and VoiceOver; plain-language Spanish reviewed by a native speaker (Q-L1) and the same
meaning in English. Performance budget for a low-end Android phone: first screen interactive < 3 s on 4G, JS < 170 KB
compressed before the character engine, three.js loaded only on screens with a character stage.

## 14. Open decisions

All firm decisions are in `aprende-questions.md`. The most important for Phase 2: the 14-day promise (Q-W1), Beam
approval covering the new app (Q-D1), the hosting budget for voice (Q-S1), the Stripe account and where funds go (Q-P1),
and the e-signature method for the engagement letter (Q-P3).
