# T8-07 part 1: copy review (Spanish and English), Opus

Branch `fix/t8-07-copy` (from origin/main 9df4ac5), worktree `~/work/cl-wt/t8-07-copy`.
Read: TEAM-RULES.md, aprende-spec.md §2, §7–§9, §13 (voice/language), aprende-decisions.md (D-013), PR #53 (open; Q-L4 recommends *usted*, so *usted* everywhere).
Scope read end to end: `aprende/i18n/es.json` + `en.json` (all 318 strings, side by side), every lesson in `aprende/content/lessons/`,
`datos.yaml`, `summaries.yaml`, `personas.yaml`, `engagement/es.md` + `en.md`, `backend/aprende/reminders.py` (from `origin/feat/t8-03-pwa-reminders`; PR #96 is still open, so the file is not on main and I did not edit it), and the `web/*.js|html` strings.

## Rule I used for legal text
- Items with `legal: true`, the summaries, datos questions, engagement letter and privacy page: I changed **only** grammar, pronoun/gender agreement and plain-word fixes that keep the meaning exactly (marked "legal item, … only" below). These items need the attorney's re-approval of the new wording anyway (content versions).
- Anything that would change meaning, even slightly, is **not** applied: it is in "Needs the attorney" with old and new text.

## What I changed (applied)

| File | Old | New | Why |
|---|---|---|---|
| `i18n/en.json` | "AI Program · not the lawyer" | "AI program · not the attorney" | everywhere else says 'attorney'; no capital P |
| `i18n/es.json` | "Divulgar el uso de IA" | "Leer el aviso sobre la IA" | the client reads the notice; she does not 'disclose' anything |
| `i18n/en.json` | "Disclose AI use" | "Read the AI notice" | same |
| `i18n/es.json` | "Compartir nombres" | "Dar los nombres de su familia" | clearer; matches the names screen |
| `i18n/en.json` | "Share names" | "Give your family's names" | same |
| `i18n/es.json` | "Completar datos" | "Completar sus datos" |  |
| `i18n/en.json` | "Complete details" | "Complete your details" |  |
| `i18n/en.json` | "Chat with assistant" | "Chat with the assistant" | missing article |
| `i18n/es.json` | "Firmar el contrato" | "Firmar el acuerdo" | the app calls it «acuerdo» everywhere else (acuerdo.*, plan.step.pay) |
| `i18n/en.json` | "Sign engagement" | "Sign the agreement" | same; 'engagement' alone is jargon |
| `i18n/en.json` | "Take final lesson" | "Take the final lesson" | missing article |
| `i18n/es.json` | "doc.will": "Su testamento" | "doc.will": "Testamento" | price card names now match the document picker and the engagement letter |
| `i18n/en.json` | "doc.will": "Your will" | "doc.will": "Will" | same |
| `i18n/es.json` | "doc.trust": "Fideicomiso" | "doc.trust": "Fideicomiso en vida" | same |
| `i18n/en.json` | "doc.trust": "Trust" | "doc.trust": "Living trust" | same |
| `i18n/es.json` | "doc.poa": "Poder notarial" | "doc.poa": "Poder legal para finanzas (poder notarial)" | same |
| `i18n/en.json` | "doc.poa": "Power of attorney" | "doc.poa": "Financial power of attorney" | same |
| `i18n/es.json` | "doc.ahcd": "Directiva de salud" | "doc.ahcd": "Directiva de atención médica" | same |
| `i18n/en.json` | "doc.ahcd": "Health care directive" | "doc.ahcd": "Advance health care directive" | same |
| `i18n/es.json` | "Una cada pareja" | "Junte las parejas" | «Una cada pareja» reads as 'one each pair' |
| `i18n/es.json` | "Tus datos" | "Sus datos" | tú → usted (D-013, #53 Q-L4) |
| `i18n/es.json` | las respuestas que usted da en «Tus datos» | las respuestas que usted da en «Sus datos» | screen name only (renamed); meaning unchanged |
| `i18n/es.json` | su esposo o pareja, | su esposo o esposa, o su pareja, | «esposo» assumed the client is a woman; EN says 'spouse' |
| `i18n/es.json` | Código de Sucesiones de Calif., sección | Código de Sucesiones de California, sección | no abbreviation; EN spells it out |
| `i18n/es.json` | "Revise, firme y cuide" | "Revise, firme y cuide sus documentos" | the verb had no object |
| `i18n/es.json` | "Cada lección completada le quita $100." | "Cada lección completada baja el precio $100." | «le quita $100» can read as 'takes $100 from you' |
| `i18n/en.json` | "Each lesson you finish takes $100 off." | "Each lesson you finish takes $100 off the price." | same |
| `i18n/es.json` | Su fideicomiso protege solo lo que está a su nombre. | Su fideicomiso protege solo lo que está a nombre del fideicomiso. | «a su nombre» read as 'in your name' (the opposite); EN says 'in its name' |
| `i18n/es.json` | "Paga en la página segura de Stripe. | "Usted paga en la página segura de Stripe. | «Paga» reads as a tú command |
| `i18n/en.json` | "privacy.link": "Privacy policy" | "privacy.link": "Privacy notice" | ES is «Aviso de privacidad» and the page calls itself a notice |
| `i18n/en.json` | "privacy.title": "Privacy policy" | "privacy.title": "Privacy notice" | same |
| `i18n/en.json` | "What we keep" | "What data we keep" | ES «Qué datos guardamos» |
| `i18n/en.json` | "revisar.ok": "It's right" | "revisar.ok": "It looks right" | 'It's right' is unclear |
| `i18n/en.json` | "You said it is right." | "You said it looks right." | same |
| `i18n/es.json` | "La edad para recibir" | "La edad para recibir la herencia" | the phrase had no object |
| `i18n/en.json` | "The age to receive" | "The age to receive the inheritance" | same |
| `i18n/es.json` | "Inicie sesión en el panel para ver su día." | "Inicie sesión en el panel lateral para ver su día." |  |
| `i18n/en.json` | "Sign in in the panel to see your day." | "Sign in on the side panel to see your day." | 'Sign in in' typo |
| `i18n/en.json` | "Review, sign and look after" | "Review, sign and take care of your documents" | the verb had no object; same words as the final lesson's title |
| `content/lessons/will.yaml` | even if it is a house, a car or one account. | even if it is a house, a car or an account. | not legal; 'one account' → 'an account' (ES «una cuenta») |
| `content/lessons/poa.yaml` | es: Los poderes notariales ⏎   en: Financial powers of attorney | es: El poder para finanzas ⏎   en: The financial power of attorney | lesson title now matches «Lección: el poder para finanzas» on Mi plan, and ES and EN name the same thing |
| `content/lessons/final.yaml` | Apoderado ⏎         - Poder financiero | Apoderado ⏎         - Poder para finanzas | not legal; same short name as Mi plan and the summary |
| `content/lessons/final.yaml` | text: Para pedir un cambio, use «Pedir un cambio» en Mi plan. La oficina le responde. | text: Para pedir un cambio, llame a la oficina. La oficina le responde. | not legal; there is no «Pedir un cambio» button in Mi plan |
| `content/lessons/final.yaml` | text: To ask for a change, use "Ask for a change" in My plan. The office will answer you. | text: To ask for a change, call the office. The office will answer you. | same |
| `content/lessons/final.yaml` | en: Look after your documents | en: Take care of your documents | EN title now matches Mi plan / Firmados ('take care of'); plainer words |
| `content/lessons/cita.yaml` | explain: ¡Listo para firmar! | explain: ¡Todo listo para firmar! | not legal; «Listo» assumed a man |
| `content/lessons/probate.yaml` | What should they do with the original will? | What should he do with the original will? | legal item, pronoun only: the story is about Mateo |
| `content/lessons/will.yaml` | - La persona que Ana y Luis nombraron como tutor | - La persona que Ana y Luis nombraron como tutora | legal item, agreement only: the story names Ana's sister «como tutora» |
| `content/lessons/final.yaml` | Lo mismo pasa con un hijo que nace o adopta después: | Lo mismo pasa con un hijo que nace o que usted adopta después: | legal item, grammar only: «que nace o adopta» read as if the child adopts; EN 'born or adopted later' |
| `content/lessons/ahcd.yaml` | - Hablar con él de sus deseos | - Hablar con esa persona de sus deseos | legal item, wording only: «él» assumed a man; EN 'them' |
| `content/summaries.yaml` | quiénes son su familia, | quiénes forman su familia, | legal summary, grammar only |
| `i18n/es.json` | Las estadísticas de uso no llevan su nombre ni sus respuestas. | Las estadísticas de uso no incluyen su nombre ni sus respuestas. | privacy page, plain word only, meaning unchanged |
| `i18n/en.json` | Usage statistics carry neither your name nor your answers. | Usage statistics do not include your name or your answers. | privacy page, plain words only, meaning unchanged |

E2E tests updated (copy only, the asserted string now matches the new wording):
- `aprende/e2e/lesson.spec.ts`: `'Código de Sucesiones de Calif., sección 6111'` → `'Código de Sucesiones de California, sección 6111'`
- `aprende/e2e/privacidad.spec.ts`: heading `'Privacy policy'` → `'Privacy notice'`
- `aprende/e2e/map.spec.ts`: `'Cada lección completada le quita $100.'` → `'Cada lección completada baja el precio $100.'`

## Needs the attorney (legal meaning; not applied)

1. **Trust "protects" vs "covers"** (Spanish and English say different things, and "protege" promises more than the law gives).
   - `lessons/trust.yaml` trust.3.1 ES: «Si su casa no se pasa al fideicomiso, el fideicomiso no la **protege**.» / EN: "…the trust does not **cover** it."
     Proposed ES: «…el fideicomiso no la **cubre**.» (same as final.3.1, which already says «no lo cubre» / "does not cover").
   - `i18n` firmados.funding.body: «Su fideicomiso protege solo lo que está a nombre del fideicomiso.» / "Your trust protects only what is in its name."
     Proposed: «Su fideicomiso cubre solo lo que está a nombre del fideicomiso.» / "Your trust covers only what is in its name."
   - `summaries.yaml` trust art. 3: «Los bienes solo están protegidos si se pasan a nombre del fideicomiso.» / "Property is protected only once…"
     Proposed: «El fideicomiso solo cubre los bienes que se pasan a su nombre.» / "The trust covers only property put in the trust's name."
2. **will.3.5 (guardian scenario), Spanish question does not fit its answers.** ES prompt: «¿Quién propondría al juez a la persona que cuidaría de Sofía y Mateo?» (asks *who would propose*; the right answer is the person named, who proposes nothing). EN: "Who would be proposed to the judge…".
   Proposed ES: «¿A quién se le propondría al juez para cuidar a Sofía y Mateo?»
   Same item, explain speaks to the client as if she were Ana and Luis: ES «Su nombramiento le dice al juez lo que ustedes quieren.» / EN "Your nomination tells the judge what you want."
   Proposed: «El nombramiento de Ana y Luis le dice al juez lo que ellos quieren.» / "Ana and Luis's nomination tells the judge what they want."
3. **final.4.5** explain switches from Ana to the client: ES «…su plan debe decir lo que usted quiere.» / EN "…your plan should say what you want."
   Proposed: «…su plan debe decir lo que ella quiere.» / "…her plan should say what she wants."
4. **beneficiarios.1.2** ES uses an English abbreviation with no explanation: «En una cuenta con beneficiario (P.O.D.)…». EN: "payable-on-death beneficiary".
   Proposed ES: «En una cuenta con beneficiario para cuando usted fallezca (en inglés, «payable on death» o P.O.D.)…»
5. **Consent screen mentions speaking, but nothing is spoken or recorded** (F-003; privacy page says «No grabamos su voz»). `i18n` gate.consent.body: «Guardamos por escrito lo que usted escribe **o dice** en la app…» / "…what you type **or say** in the app…".
   Proposed: «Guardamos por escrito lo que usted escribe en la app…» / "We keep a written record of what you type in the app…". (If voice comes back later, put it back.)
6. **Engagement letter §2, unclear exclusion** (`engagement/es.md` and `en.md`): «cambios legales después de firmar» / "legal changes after signing". It can mean *changes in the law* or *changes to the documents*.
   Proposed, if it means the law: «cambios en la ley después de firmar» / "changes in the law after signing"; if it means the documents: «cambios a los documentos después de firmar» / "changes to the documents after signing".
7. **Reminder texts** (`backend/aprende/reminders.py`, on PR #96, "needs attorney approval (#50)"): they read well, and the dates/times say "hora de California" / "California time". One point: the yearly text says «Puede reservar una consulta en la aplicación» / "You can book a consultation in the app", but the app has no button that opens the consultation booking (only the `#/cita` route; the yearly push opens `#/plan`). Either add a link to `#/cita?kind=consultation` or say «llame a la oficina para reservar una consulta» / "call the office to book a consultation".
8. **Wording-only edits I applied inside legal items (please re-approve):** will.3.5 option «tutor» → «tutora»; probate.2.3 EN "they" → "he"; final.4.3 «nace o adopta» → «nace o que usted adopta»; ahcd.5.4 «Hablar con él» → «Hablar con esa persona»; summaries will art. 1 «quiénes son su familia» → «quiénes forman su familia»; privacy.who.body «no llevan» → «no incluyen» / "carry neither…nor" → "do not include…or".

No problems found in `datos.yaml` (no immigration-status question; *usted* throughout) or in `personas.yaml` (the rules ban fees, selling and immigration questions).

## Needs Kevin (taste calls)

1. **One name for the financial power of attorney.** The app uses «poder notarial», «poder para finanzas», «poder legal para finanzas (poder notarial)» and (before this fix) «poder financiero». «Poder notarial» is what clients say, but in California this document can be signed with two witnesses and no notary (poa.1.3), so the name is slightly misleading. I used «poder para finanzas» as the short name and kept «Poder legal para finanzas (poder notarial)» as the full name (the same as the document picker and the engagement letter). Is that OK?
2. **"18 or older".** Sign-up says «Soy mayor de 18 años» / "I am over 18", and the error says the same. Read strictly, both leave out people who are exactly 18. Proposed: «Tengo 18 años o más» / "I am 18 or older". I did not apply it because 15 e2e specs find the checkbox by `/mayor de 18/`. If you agree, it is a one-line change in each spec.
3. **Price card hard-codes $100.** `price.howTo` («Cada lección completada baja el precio $100.») is on the price card, so it is allowed there, but the amount comes from the firm's pricing settings (`discounts.will.amount`), and the discount steps also include "Sus datos" (`intake_completed`), not only lessons. If the firm changes the amount, this sentence will be wrong. Fix: send the amount per step in `/payments/quote` and use `{amount}` in the string (small code change; the attorney approves price wording, Q-P2).
4. **Mateo in two roles.** In will.3.5 Mateo is Ana and Luis's small child. In probate.2.3 an adult Mateo finds his aunt's will. Use another name for the adult (only Ana, Luis, Sofía and Mateo are on the approved list), or say «Mateo, ya adulto»?
5. **Gendered praise.** poa.3.5: «¡Perfecto! Ya habla como un experto.» assumes a man (Ana is the main user). Option: «¡Perfecto! Ya conoce las palabras de los expertos.» (legal item, so I did not apply it).
6. **«Bienvenido.»** (`app.welcome`) is gendered, but no screen uses it now. If it is used later: «Le damos la bienvenida.»
7. **No way to ask for a change after signing.** The final lesson said to use «Pedir un cambio» in Mi plan, but that button does not exist. I changed the text to «llame a la oficina» / "call the office". If you want a button, that is a feature.
8. **La Calavera persona says "big sombrero".** This is for the cultural review (#53 Q-C2), not a copy error.

## Not changed, and why
- Staff admin `web/*.js|html`: I found no string a client can see. (`web/characters.js` and `admin.html` still label the unit "Tus datos"; those are staff-only.)
- Engagement document names in `backend/aprende/engagement.py`: already the full names; the price card now uses the same names.
- Dates: appointment times show in `America/Los_Angeles` (Cita.tsx, booking.py, reminders.py). The «Se abre el …» lesson date uses the client's own time zone (journey `tz`, default Los Angeles). That is how the backend works, so I left it.

## Checks
- `npm run i18n:check`: ok (323 keys). `npm run typecheck`: ok. `npm run test`: 14 files, 127 tests passed.
- `pytest tests/test_audit_guardrails.py tests/test_content.py tests/test_t5_05_datos.py tests/test_learn.py`: 78 passed.
- Playwright (`--project=web --workers=1`, ports 5257/8257/8357, `nice -n 19`): `e2e/lesson.spec.ts e2e/privacidad.spec.ts e2e/map.spec.ts e2e/exercises.spec.ts e2e/datos.spec.ts`: 12 passed, 0 failed. Servers stopped afterwards (the ports are free). The Vite "outside of serving allow list" font warnings come from the symlinked `node_modules` and do not affect the tests.
- Not run locally: the full backend suite with Postgres, lint, the builds, and the other e2e specs (CI runs them). No spec I did not touch asserts a string I changed (I grepped `aprende/e2e`, `aprende/tests`, `tests/` and `backend/`). `aprende/tests/e2e/extension-polish.spec.ts` has 'Look after your documents' only in its own mocked lesson list.
