# Aprende y Planea — audit of Phases 1–6

Date: 2026-11-21. Base: `main` at `d0bc520` (after #96, the last Phase 8 PR).
Audience: Kevin and the reviewing attorney.

This report sums up the Part A audit. Every claim names a file, a test or a PR.
"Not verified" means no report or file proves the point.
All people in tests and examples are fictional.

Sources (outside the repo, in the lead's report folder `~/work/cl-reports/`):
`audit-coverage-a.md`, `audit-coverage-b.md`, `audit-guardrails.md`, `audit-gamed-tests.md`,
`audit-walkthrough.md`, `audit/lead-notes.md`, `FIX-WALKTHROUGH.md`, `T8-06.md`.
Where the lead's notes disagree with an agent's report, this report follows the lead's notes.

## 1. Summary

- **What was checked.** Every acceptance test in `docs/aprende-backlog.md` for Phases 2–6: 174 tests.
  Phase 1 was research and the spec; it has no tickets with acceptance tests.
  We also checked the legal and safety guardrails, looked for weakened ("gamed") tests,
  walked the app on a phone-sized screen, and ran a full release test on a fake clock (T8-06).
- **How.** Two agents mapped each acceptance test to the test that proves it. Beam and then the lead re-checked the weak rows.
  A guardrail agent wrote 24 backend tests and 1 browser test (#77). An agent scanned the git history of the tests.
  A walkthrough took 59 screenshots at 390×844, which the lead reviewed.
- **Coverage result.** 142 of 174 acceptance tests are proven.
  New tests closed 3 gaps (#77). 4 are partly proven. 2 no longer apply (F-003: no server voice). 23 are open.
  Most open items are art, animation and accessibility checks in Phases 3–4.
  Two open items are the paid model runs that wait for approval (#49, #65).
- **Guardrails.** Each guardrail has a test. The guardrail audit found 5 bugs. All 5 are fixed (#72–#76).
- **Gamed tests.** None found. One assertion became looser; a stronger guardrail test now covers the same point.
- **Phone walkthrough.** 7 findings (W1–W7). 5 are fixed (#88, #99). W2 is fixed (#78, #96). W6 waits for the Spanish review (#53).
- **After the audit.** The release test found F1–F6. 5 are fixed (#85, #90, #91, #89, #94); F3 is open.
  CI then found 2 slow-phone races (#100). We also fixed the failing Render deploys (#84) and an admin script clash (#79).
- **In total, 19 bugs were fixed and merged:** 5 guardrail, 5 walkthrough, 5 release-test, 2 race, 1 deploy, 1 admin.

## 2. Coverage

Status words:
- **proven**: a test (or, where marked, a CI step, a lint rule or a document) shows it.
- **proven (lead check)**: the coverage agent marked it weak; the lead found the test (`audit/lead-notes.md`).
- **gap fixed in #N**: the audit found no test; PR #N added one.
- **partly**: a test covers part of it; the note says which part is missing.
- **open**: no test yet. **N/A**: the requirement no longer applies.

### Phase 2 — Foundations (50 acceptance tests, 47 proven)

| Ticket | Acceptance test | Proven by | Status |
|---|---|---|---|
| T2-01 | `python server.py --check` in avatar-intake prints ok | CI step `avatar-intake check` (.github/workflows/ci.yml) | proven |
| T2-01 | tests/test_carbon_intake.py re-runs the `--check` assertions in pytest | tests/test_carbon_intake.py (10 tests) | proven |
| T2-01 | prompts and drafter output unchanged for 5 inputs | tests/test_carbon_intake_snapshots.py::test_system_prompt_unchanged, ::test_drafter_unchanged | proven |
| T2-01 | `grep -c "^def system_prompt" avatar-intake/server.py` is 0 | grep (one-off check by the coverage agent) | proven (manual) |
| T2-02 | migrations run on an empty SQLite database | tests/test_migrations.py::test_migrate_from_empty_sqlite | proven |
| T2-02 | migrations run on an empty Postgres database | tests/test_migrations.py::test_migrate_from_empty_postgres | proven (Postgres; runs in CI) |
| T2-02 | running migrations twice changes nothing | tests/test_migrations.py::test_migrate_is_idempotent | proven |
| T2-02 | a repeated journey event is stored once | tests/test_migrations.py::test_journey_event_dedupe | proven |
| T2-02 | legacy collections are untouched | tests/test_migrations.py::test_legacy_collections_untouched | proven |
| T2-03 | build:web and build:ext succeed | CI steps `build web`, `build extension` (.github/workflows/ci.yml) | proven |
| T2-03 | extension manifest is MV3 with a fixed permission list | aprende/tests/manifest.test.ts::produces MV3 manifest with 2 perms and one host permission | proven (list cut to 2 by #89, F-003) |
| T2-03 | lint fails on the fixture `tests/fixtures/bad-import.ts` | aprende/tests/lint-boundary.test.ts::flags bad-import.ts | proven |
| T2-03 | the vitest smoke test renders `<App/>` | aprende/tests/smoke.test.tsx::renders | proven |
| T2-04 | missing key in either file fails i18n:check (fixture) | aprende/tests/i18n-check.test.ts::fails when a key is missing in one language | proven |
| T2-04 | `t("precio",{cents:280000})` shows "$2,800" in both languages | aprende/tests/i18n.test.ts::money in both languages | proven |
| T2-04 | ESLint rule flags a JSX text literal | rule exists (aprende/eslint.config.js:15); no test shows it fires | open |
| T2-04 | `<html lang>` follows the chosen language | aprende/tests/i18n.test.ts::html lang updates | proven |
| T2-05 | Aprende sign-up without the adult box is refused (400) | tests/test_aprende_auth.py::test_aprende_signup_requires_adult | proven |
| T2-05 | portal signup unchanged | tests/test_aprende_auth.py::test_portal_signup_unchanged | proven |
| T2-05 | client session 30 days | tests/test_aprende_auth.py::test_client_session_30_days | proven |
| T2-05 | staff session 24h | tests/test_aprende_auth.py::test_staff_session_24h | proven |
| T2-05 | client session slides on use | tests/test_aprende_auth.py::test_client_session_slides | proven |
| T2-05 | CORS: the firm's extension origin is allowed, others are not | tests/test_aprende_auth.py::test_cors_in_subprocess | proven |
| T2-06 | an event out of order is refused (409) and names the missing step | tests/test_journey.py::test_order_is_enforced_with_the_missing_gate_named | proven |
| T2-06 | consent=no sets learning-only (may_collect_details false until re-consent) | tests/test_journey.py::test_consent_no_is_learning_only | proven |
| T2-06 | names_submitted creates exactly one legacy matter at stage 1 Intake visible to staff | tests/test_journey.py::test_names_create_exactly_one_matter_for_staff | proven |
| T2-06 | a client cannot send a server-only event (403) | tests/test_journey.py::test_client_cannot_send_server_only_events | proven |
| T2-06 | GET /journey never shows conflict names or matches | tests/test_journey.py::test_possible_conflict_stops_and_says_nothing_more | proven |
| T2-06 | facts are append-only (a re-send changes nothing) | tests/test_journey.py::test_facts_are_append_only | proven |
| T2-07 | slow aprende request does not block legacy; legacy writes serialize | tests/test_t2_07_lock.py::test_slow_aprende_request_does_not_block_legacy | proven |
| T2-08 | the model's reasoning from turn 1 is sent in turn 2 | tests/test_ai_client.py::test_reasoning_turn1_in_request_turn2 | proven |
| T2-08 | a 502 then a 200: one retry, then success | tests/test_ai_client.py::test_502_then_200_retries | proven |
| T2-08 | a looping reply is retried; two looping replies raise an error | tests/test_ai_client.py::test_looping_then_good_retries, ::test_two_looping_raises_modelerror | proven |
| T2-08 | the AI log row holds hashes and token counts, no prompt or reply text; the key is never logged | tests/test_ai_client.py::test_ai_calls_row_hashes_tokens_nosubstring, ::test_key_not_in_logs | proven |
| T2-09 | the same job key queued twice makes one job | tests/test_jobs.py::test_enqueue_same_key_twice_one_job | proven |
| T2-09 | a crashed job claim (lock over 10 min) is taken again | tests/test_jobs.py::test_crashed_claim_reclaimed_after_stale | proven |
| T2-09 | a failing job retries with backoff, then is marked failed | tests/test_jobs.py::test_fail_retry_flow_with_patched_clock | proven |
| T2-09 | two Postgres workers never take the same job | tests/test_jobs.py::test_postgres_skip_locked_real | proven (Postgres; runs in CI) |
| T2-10 | CI runs all D17 gates on every PR | .github/workflows/ci.yml runs on `pull_request` (config, not a test) | proven (config) |
| T2-10 | Pages artifact contains aprende/index.html | .github/workflows/pages.yml copies it; nothing checks it | open |
| T2-10 | existing site files unchanged in artifact | .github/workflows/pages.yml; nothing checks it | open |
| T2-11 | sign-up in Spanish with the adult box | aprende/e2e/app-shell.spec.ts::signup in Spanish lands on the day-1 gate without tabs; the app has tabs with aria-current | proven |
| T2-11 | tabs are links with aria-current | same test | proven |
| T2-11 | rail replaces tabs above 64em | aprende/e2e/app-shell.spec.ts::rail replaces tabs above 64em | proven |
| T2-11 | sign-out clears token from platform.storage | aprende/e2e/app-shell.spec.ts::sign-out clears token and returns to entrar | proven |
| T2-11 | axe no violations on four screens | aprende/e2e/app-shell.spec.ts::axe no violations on four screens | proven |
| T2-12 | clicking "Abrir" in popup opens side panel | aprende/tests/e2e/extension.spec.ts::popup reads journey and opens side panel | proven |
| T2-12 | popup reads streak + today step from GET /journey | aprende/tests/e2e/extension.spec.ts::popup reads journey and opens side panel | proven |
| T2-12 | token gone after Chrome restart (session storage) | aprende/tests/e2e/extension.spec.ts::storage.local stays empty and token clears on restart | proven |
| T2-12 | chrome.storage.local empty | aprende/tests/e2e/extension.spec.ts::storage.local stays empty and token clears on restart | proven |

### Phase 3 — Characters (15 acceptance tests, 6 proven)

| Ticket | Acceptance test | Proven by | Status |
|---|---|---|---|
| T3-01 | rebuild calavera: same 8 keys + 4 frozen poses within 1% pixel diff | none (art check) | open (manual) |
| T3-01 | `make_character.py` builds Piñata and El Oso in Blender | none | open (manual) |
| T3-01 | each GLB under 1.5MB | none | open |
| T3-02 | final art states match approved sheet; mouth reads at 160px | none (art review) | open (manual) |
| T3-03 | final art states match approved sheet; mouth reads at 160px | none (art review) | open (manual) |
| T3-04 | final art states match approved sheet; mouth reads at 160px | none (art review) | open (manual) |
| T3-05 | unit tests reproduce viseme() outputs (ES/EN alignment) | aprende/tests/visemes.test.ts::spanish alignment fixture, ::english alignment fixture | proven |
| T3-05 | three not in initial bundle | aprende/tests/bundle.test.ts::builds web and excludes three from entry chunks | proven |
| T3-05 | Playwright screenshot each char with __pose frozen | none | open |
| T3-05 | prefers-reduced-motion: head no sway, jaw follows speech | none (code: aprende/src/core/character/engine.ts:14) | open |
| T3-05 | "Programa de IA · no es el abogado" in stage accessible name | none (text exists: `character.aiLabel`, aprende/i18n/es.json:48) | open |
| T3-06 | GET /characters returns only enabled | tests/test_characters.py::test_get_characters_returns_only_enabled | proven |
| T3-06 | disabled character falls back to calavera in lessons | tests/test_characters.py::test_character_for_fallback | proven |
| T3-06 | staff-only PATCH (403 for clients) | tests/test_characters.py::test_patch_staff_only | proven |
| T3-07 | cultural/stereotype review record | docs/aprende-decisions.md | proven (document) |

### Phase 4 — Learning (35 acceptance tests, 24 proven)

| Ticket | Acceptance test | Proven by | Status |
|---|---|---|---|
| T4-01 | content validator passes | tests/test_content.py::test_fixture_is_valid | proven |
| T4-01 | every explanation is at most 2 sentences | none | open |
| T4-01 | reading level (Fernandez-Huerta/Flesch) by script | none | open |
| T4-01 | attorney approval pending, not assumed | docs/aprende/lesson-review-packet.md | proven (document); approval itself: #50 |
| T4-02 | legal item without source fails validation | tests/test_content.py::test_validator_catches | proven |
| T4-02 | probate_code source not in VERIFIED fails | tests/test_content.py::test_validator_catches | proven |
| T4-02 | item missing English fails | tests/test_content.py::test_validator_catches | proven |
| T4-02 | import then export round-trips byte-for-byte | tests/test_content.py::test_export_round_trips | proven |
| T4-02 | publishing legal item without approval row refused | tests/test_content.py::test_legal_items_need_an_attorney_approval_to_publish | proven |
| T4-03 | lesson 2 locked until local midnight after lesson1 (freezegun) | tests/test_learn.py::test_next_lesson_opens_at_local_midnight, ::test_locked_lesson_cannot_be_opened_or_answered | proven |
| T4-03 | completes at >=80% correct, any attempts | tests/test_learn.py::test_completion_needs_80_percent_and_any_retries | proven |
| T4-03 | completion emits `lesson_completed:<doc>` once | tests/test_learn.py::test_discount_event_is_emitted_once | proven |
| T4-03 | analytics item_answered rows carry no answer text | tests/test_learn.py::test_analytics_never_store_answers | proven |
| T4-04 | lesson started on phone resumes on same item in extension | none | open |
| T4-04 | leaving mid-step loses nothing | aprende/e2e/lesson.spec.ts::the will lesson: explain, a wrong answer that comes back, sources, resume | partly: reload only, same target; a save race fixed in #100 |
| T4-04 | feedback sheet shows source text + disclaimer | same lesson.spec.ts test | proven |
| T4-04 | wrong answers come back later in step | same lesson.spec.ts test | proven |
| T4-04 | screen-reader name of correct option ends "(correcta)" | none (text exists: `leccion.correctMark`) | open |
| T4-04 | no layout shift at 200% text size | aprende/e2e/a11y.spec.ts::200 % text: lesson: question with feedback (#95) | partly (#95): no lost text; layout shift not measured |
| T4-05 | every type operable by keyboard only and touch only | aprende/e2e/exercises.spec.ts::match pairs (Piñata), by click; ::put the steps in order, by keyboard only | partly: 2 of 5 types |
| T4-05 | each passes axe | aprende/e2e/exercises.spec.ts (both tests run axe); aprende/e2e/a11y.spec.ts (#95) | proven |
| T4-05 | order-the-steps works with switch-access (Tab+Enter) | aprende/e2e/exercises.spec.ts::put the steps in order, by keyboard only | proven |
| T4-06 | streak counts lesson/refresher/bonus days | tests/test_motivation.py::test_streak | proven |
| T4-06 | one free rest day per ISO week; second missed resets | tests/test_motivation.py::test_streak | proven |
| T4-06 | celebrations static card in calm mode + reduced motion | none (text exists: `celebration.calm`) | open |
| T4-06 | reminders: at most one/day, off with one switch, time in client zone | tests/test_motivation.py::test_reminders_default_off_validated_and_due_once_a_day | proven |
| T4-07 | screenshot differs at most 2% at 390×844 | none | open |
| T4-07 | today node first focusable after top bar | aprende/e2e/map.spec.ts::the course map: today's lesson, the price, locked days and their reason | open: focus order not checked |
| T4-07 | locked nodes state reason in text | aprende/e2e/map.spec.ts::the course map: today's lesson, the price, locked days and their reason | proven |
| T4-07 | dark theme icons pass 3:1 | none | open |
| T4-08 | fresh journey -> will 300000; four lessons -> 260000; plus intake -> 250000 | tests/test_pricing.py::test_fresh_journey_will_300000, ::test_four_lessons_then_intake | proven |
| T4-08 | sixth event never below floor | tests/test_pricing.py::test_sixth_event_floor | proven |
| T4-08 | settings change keeps earned discounts | tests/test_pricing.py::test_settings_change_keeps_earned | proven |
| T4-08 | quote discounts list names each event | tests/test_pricing.py::test_unit_quote_basic | proven |
| T4-09 | copy review (read aloud both languages) | docs/aprende/lesson-review-packet.md; copy review #99 | proven (document) |

### Phase 5 — Conversation and intake (36 acceptance tests, 28 proven)

| Ticket | Acceptance test | Proven by | Status |
|---|---|---|---|
| T5-01 | refused (409) before may_chat; model never called | tests/test_t5_01_chat.py::test_chat_is_refused_before_may_chat_and_the_model_is_never_called | proven |
| T5-01 | the model's reasoning round-trips | tests/test_t5_01_chat.py::test_a_learning_answer_round_trips_the_reasoning | proven |
| T5-01 | the hidden attorney tag never reaches the client's text | tests/test_t5_01_chat.py::test_a_question_about_the_clients_own_case_goes_to_the_attorney | proven |
| T5-01 | a stored attorney question is linked to the journey and staff-only | tests/test_t5_01_chat.py::test_a_question_about_the_clients_own_case_goes_to_the_attorney | proven |
| T5-01 | the chat history keeps the tags | tests/test_t5_01_chat.py::test_a_question_about_the_clients_own_case_goes_to_the_attorney | proven |
| T5-02 | phrase table passes both langs/impls | tests/test_t5_02_gate.py::test_consent_phrase_table; aprende/tests/consent.test.ts | proven |
| T5-02 | 'No, no acepto' → no | tests/test_t5_02_gate.py::test_a_refusal_wins_over_a_yes_word_in_the_same_answer | proven |
| T5-02 | a refusal keeps only the event (no audio exists: F-003) | tests/test_t5_02_gate.py::test_the_consent_event_keeps_only_the_answer; tests/test_audit_guardrails.py::test_a_refusal_keeps_nothing | gap fixed in #77 (audio part N/A, F-003) |
| T5-02 | after refusal POST /chat and PUT /datos/* → 409 | tests/test_audit_guardrails.py::test_a_refusal_keeps_nothing (11 routes incl. GET/PUT /datos) | gap fixed in #77 |
| T5-02 | disclosure text: AI program, not attorney/person; calavera never 'con su imagen' | tests/test_t5_02_gate.py::test_the_disclosure_says_ai_program_not_the_attorney_not_a_person | proven |
| T5-03 | prototype conflict cases (accents, Mendez/Mendes, middle name, one-word ignored, two people) | tests/test_t5_03_conflict.py::test_the_automatic_check | proven |
| T5-03 | possible → client sees only neutral message; AI/datos 409; staff one ntfy alert | tests/test_t5_03_conflict.py::test_a_possible_conflict_tells_the_client_nothing, ::test_staff_get_one_alert_per_possible_conflict | proven |
| T5-03 | matched names stored only in conflict_checks (staff-only) | tests/test_t5_03_conflict.py::test_matched_names_are_only_in_the_staff_queue | proven |
| T5-03 | no list → details wait for staff clearance | tests/test_t5_03_conflict.py::test_without_a_list_details_wait_for_staff | proven |
| T5-03 | analytics hold only clear / possible / no_list about the result | tests/test_audit_guardrails.py::test_no_client_content_reaches_logs_analytics_or_staff_alerts (each event keeps only its own keys) | gap fixed in #77 |
| T5-04 | spec 6.3 table for seven start weekdays ± changes | tests/test_t5_04_timeline.py::test_the_spec_table_for_every_start_weekday | proven |
| T5-04 | firm holiday shifts right steps | tests/test_t5_04_timeline.py::test_a_firm_holiday_shifts_only_the_steps_after_it | proven |
| T5-04 | shifted_days and reason_key when weekend moves date | tests/test_t5_04_timeline.py::test_a_weekend_that_moves_a_date_says_so | proven |
| T5-04 | step past due raises one alert + one flag, not per tick | tests/test_t5_04_timeline.py::test_a_late_review_raises_one_alert_and_one_flag | proven |
| T5-04 | America/LA DST weeks do not shift dates | tests/test_t5_04_timeline.py::test_dst_weeks_do_not_shift_dates | proven |
| T5-05 | covered only grows | tests/test_t5_05_datos.py::test_covered_only_grows | proven |
| T5-05 | wandering client steered back (fixture) | tests/test_t5_05_datos.py::test_a_client_who_wanders_is_steered_back_and_nothing_is_marked | proven |
| T5-05 | skipping recorded as skipped, not empty | tests/test_t5_05_datos.py::test_answer_skip_and_validation | proven |
| T5-05 | intake_completed emitted once, triggers fifth discount | tests/test_t5_05_datos.py::test_finishing_the_intake_earns_the_fifth_discount_once | proven |
| T5-05 | no datos route before may_collect_details | tests/test_t5_05_datos.py::test_details_wait_for_the_gates | proven |
| T5-06 | no webkitSpeechRecognition/SpeechRecognition in bundle (lint rule) | aprende/eslint.config.js (no-restricted-globals); runs in CI lint | proven (lint rule) |
| T5-06 | audio rows unreadable without key | none | N/A (F-003: no server voice) |
| T5-06 | retention sweep deletes past setting | none | N/A (F-003) |
| T5-06 | voice service down → browser voice + typed answers | none | open (not verified whether it still applies under F-003) |
| T5-06 | microphone never requested on page load | aprende/tests/e2e/extension-polish.spec.ts::no extension page asks for the microphone (F-003: typed answers and the browser voice) | partly: extension only; web app not tested |
| T5-07 | three characters × two modes, ES/EN, derived from prototype system_prompt; attorney approval required | docs/aprende-phase-5-report.md | proven (document); approval: #50 |
| T5-08 | 40 scripted conversations; server-side guards hold for all 40 | tests/test_t5_08_conversations.py::test_the_servers_guards_hold_for_every_conversation | proven |
| T5-08 | live run: no advice, no fee quote, not a person, one question/turn | none (paid run not done) | open: #49 |
| T5-09 | 'no sé todavía' stores all four codes | tests/test_t5_09_scope.py::test_no_se_todavia_is_all_four_documents | proven |
| T5-09 | editing an answer in summary updates datos row + audit entry | tests/test_t5_05_datos.py::test_editing_an_answer_keeps_an_audit_entry | proven |
| T5-09 | changing confirmed set after scope_approved clears it + timeline +1 business day | tests/test_t5_09_scope.py::test_changing_documents_after_scope_approval_reopens_the_scope_review, ::test_a_reopened_scope_gets_one_business_day_on_the_timeline | proven |

### Phase 6 — Payment, documents and appointments (38 acceptance tests, 37 proven)

| Ticket | Acceptance test | Proven by | Status |
|---|---|---|---|
| T6-01 | template without attorney approval cannot be used (409) | tests/test_t6_01_engagement.py::test_only_the_attorney_approves_a_template | proven |
| T6-01 | may_sign_engagement requires conflict cleared + scope approved | tests/test_t6_01_engagement.py::test_scope_approval_is_the_attorneys_and_opens_signing | proven |
| T6-01 | stored hash equals hash of text shown | tests/test_t6_01_engagement.py::test_signing_needs_the_text_that_was_shown, ::test_the_stored_hash_is_the_hash_of_the_stored_text | proven |
| T6-01 | signing twice is no-op | tests/test_t6_01_engagement.py::test_signing_twice_is_a_no_op | proven |
| T6-01 | signed PDF downloadable by client and staff only | tests/test_t6_01_engagement.py::test_the_signed_copy_is_a_pdf_for_the_client_and_staff_only | proven |
| T6-02 | refused unless may_pay | tests/test_t6_02_payments.py::test_checkout_is_refused_until_may_pay | proven |
| T6-02 | amount equals /payments/quote (server-computed) | tests/test_t6_02_payments.py::test_the_amount_is_the_servers_quote_never_the_clients | proven |
| T6-02 | test mode shows 'Modo de prueba' in UI | aprende/e2e/pago.spec.ts::the payment page: test mode, the server total, Stripe opens, and there is no card field anywhere | proven (lead check) |
| T6-02 | no card field in app (DOM assertion) | same pago.spec.ts test | proven (lead check) |
| T6-03 | bad signature → 400, nothing recorded | tests/test_t6_02_payments.py::test_a_bad_signature_records_nothing | proven |
| T6-03 | completed → one paid event + one draft_documents job even on 3 retries | tests/test_t6_02_payments.py::test_a_completed_checkout_records_one_payment_and_one_drafting_job_even_when_retried, ::test_concurrent_deliveries_of_one_payment_record_it_once | proven |
| T6-03 | refund recorded by admin appears on receipt | tests/test_t6_02_payments.py::test_refunds_are_admin_only_and_appear_on_the_receipt | proven |
| T6-03 | browser success redirect alone never marks paid | tests/test_t6_02_payments.py::test_the_success_redirect_alone_never_marks_paid | proven |
| T6-04 | drafts never appear in any client route | tests/test_t6_04_drafts.py::test_drafts_are_attorney_only_and_the_matter_moves_to_review | proven |
| T6-04 | citation check line present | tests/test_t6_04_drafts.py::test_an_unverified_citation_is_flagged_on_the_draft | proven |
| T6-04 | malformed model reply writes nothing for that doc | tests/test_t6_04_drafts.py::test_a_malformed_reply_writes_nothing_for_that_document_and_keeps_the_others | proven |
| T6-04 | AI record contains no client text (hashes only) | tests/test_t6_04_drafts.py::test_the_ai_record_holds_hashes_only | proven |
| T6-04 | matter moves to 5 Review Queue | tests/test_t6_04_drafts.py::test_drafts_are_attorney_only_and_the_matter_moves_to_review | proven |
| T6-05 | approval refused while [ATTORNEY TO COMPLETE] remains | tests/test_t6_05_review.py::test_approval_is_refused_while_anything_is_left_to_complete | proven |
| T6-05 | only assigned attorney (or admin) may approve | tests/test_t6_05_review.py::test_only_the_assigned_attorney_or_an_admin_approves | proven |
| T6-05 | approving sets attorney_approved, releases approved versions | tests/test_t6_05_review.py::test_approving_releases_exactly_the_approved_versions | proven |
| T6-05 | rendered drafts sanitised; script in draft does not execute | aprende/e2e/admin-review.spec.ts::the attorney reads a draft with its marks, and no script in a draft runs | proven (lead check) |
| T6-06 | client sees only Attorney Approved versions | tests/test_t6_06_client_review.py::test_the_client_sees_only_the_approved_versions_with_their_plain_summary | proven |
| T6-06 | change request creates legacy change request + task, moves matter back to 5 | tests/test_t6_06_client_review.py::test_a_change_request_goes_to_the_firms_records | proven |
| T6-06 | revised version supersedes old only after re-approval | tests/test_t6_06_client_review.py::test_a_revision_replaces_the_old_version_only_after_re_approval | proven |
| T6-07 | no double booking under concurrent requests | tests/test_t6_07_booking.py::test_no_double_booking_under_concurrent_requests | proven |
| T6-07 | slot inside holiday not offered | tests/test_t6_07_booking.py::test_a_firm_holiday_has_no_slots | proven |
| T6-07 | DST-gap time (2:30 spring-forward) never offered | tests/test_t6_07_booking.py::test_the_spring_forward_gap_is_never_offered | proven |
| T6-07 | signing cannot be booked before client_confirmed | tests/test_t6_07_booking.py::test_signing_needs_the_client_to_have_confirmed_the_documents | proven |
| T6-07 | consultation can be booked after four core lessons | tests/test_t6_07_booking.py::test_a_consultation_needs_the_four_core_lessons; hold: tests/test_fix_booking_conflict_hold.py (#72) | proven |
| T6-08 | staff upload executed docs records signed, moves matter 8→9, unlocks final lesson | tests/test_t6_08_signing.py::test_uploading_the_executed_documents_records_the_signing_and_moves_the_matter, ::test_the_final_lesson_opens_after_signing | proven |
| T6-08 | executed docs + funding checklist downloadable via authenticated non-guessable URLs | tests/test_t6_08_signing.py::test_executed_documents_are_the_clients_alone_through_unguessable_links, ::test_the_funding_checklist_is_filled_for_a_trust_client | proven |
| T6-08 | funding done by staff → stage 10 | tests/test_t6_08_signing.py::test_funding_check_ins_run_until_staff_mark_funding_done | proven |
| T6-09 | 14 rows with dates | tests/test_t6_09_plan.py::test_the_client_sees_every_step_with_its_date | proven |
| T6-09 | shifted-date explanation appears | tests/test_t5_04_timeline.py::test_a_weekend_that_moves_a_date_says_so | proven |
| T6-09 | late steps calm for client, flagged red-with-icon for staff | aprende/e2e/plan.spec.ts::Mi plan: every step with its date, a moved date explained, a late step said calmly | proven (lead check) |
| T6-09 | staff client list sorts by most late | tests/test_t6_09_plan.py::test_staff_list_puts_the_most_late_first | proven |
| T6-10 | 16 fictional cases drafted and read against the prototype standard; findings fixed or logged | docs/aprende-phase-6-report.md; #64 added the cases, but the paid drafting run has not run | open: #65 (re-classified in this report) |

## 3. Guardrails

The guardrail audit checked nine rules from brief section 6 in the code (`audit-guardrails.md`).
Its tests are in `tests/test_audit_guardrails.py` and `aprende/e2e/audit-staff-text.spec.ts` (#77).
The table lists the rules from the brief for this report first, then the other audit rules.

| Guardrail | Test that proves it | Bug found, fix | Still open |
|---|---|---|---|
| No immigration-status questions (also: no selling, no annuities) | `tests/test_audit_guardrails.py::test_no_scripted_line_asks_about_immigration_status_sells_or_pairs_a_plan_with_insurance`, `::test_the_rules_are_in_every_prompt_sent_to_the_model`; `tests/test_fix_chat_output_guard.py::test_a_model_reply_that_breaks_the_rules_never_reaches_the_client`, `::test_a_reply_within_the_rules_still_reaches_the_client` | The server passed any model reply to the client. Fixed in #75: a reply that asks about immigration status or mentions an annuity is refused. | "Never sell" stays a prompt rule only; no reliable pattern exists (#75). |
| No client content in logs, staff alerts or analytics | `tests/test_audit_guardrails.py::test_no_client_content_reaches_logs_analytics_or_staff_alerts`; `tests/test_ai_client.py::test_ai_calls_row_hashes_tokens_nosubstring`; `tests/test_t6_04_drafts.py::test_the_ai_record_holds_hashes_only`; `tests/test_learn.py::test_analytics_never_store_answers` | None. | — |
| No payment before conflict clearance and the attorney's countersignature (Bus. & Prof. Code § 6148(a)) | `tests/test_audit_guardrails.py::test_checkout_is_refused_at_every_step_before_the_countersignature`, `::test_a_quote_is_only_a_price_card`; `tests/test_fix_payments_webhook_gate.py` (2 tests); `tests/test_t6_02_payments.py::test_checkout_is_refused_until_may_pay`, `::test_the_success_redirect_alone_never_marks_paid` | Checkout was gated, but the Stripe webhook recorded a payment and started drafting without the countersignature. Fixed in #73. | Wording of the letter and the countersignature step: attorney, #57. |
| Tests never call a paid model | `tests/conftest.py` (autouse network guard); `tests/test_audit_guardrails.py::test_the_network_guard_is_on_for_every_collected_test`, `::test_no_test_module_replaces_or_undoes_the_guard`, `::test_a_real_call_to_beam_is_blocked`, `::test_the_legacy_demo_summary_cannot_reach_beam_even_with_the_developers_key`; `tests/test_fix_e2e_model_guard.py::test_the_playwright_backend_cannot_reach_a_paid_model`; `tests/test_t6_10_cases.py::test_the_paid_run_needs_explicit_approval` | The browser-test backend had no guard; on Kevin's PC it could load a real key. Fixed in #76. | The guard covers `urllib` and `httpx`, not `requests` or raw sockets; no code uses those (`audit-guardrails.md` §9). `scripts/conversation-eval.py` refuses to run without `--yes-i-have-approval`, but no test checks that. |
| Fictional people only | No test. Checked by reading: no test name (Torres, Mendez) and no test flag appears in production code (`audit/lead-notes.md`); the paid runs use fictional clients (#49, #65). | None. | Not proven by a test. |
| AI disclosure (an AI program, not the attorney, not a person) | `tests/test_t5_02_gate.py::test_the_disclosure_says_ai_program_not_the_attorney_not_a_person`; `tests/test_journey.py::test_order_is_enforced_with_the_missing_gate_named` (disclosure comes first); `aprende/e2e/gate.spec.ts` | None. | The label on the character ("Programa de IA · no es el abogado") has no test (T3-05, section 2). |
| Consent (a clear yes; a refusal keeps nothing) | `tests/test_t5_02_gate.py::test_consent_phrase_table`, `::test_a_refusal_wins_over_a_yes_word_in_the_same_answer`; `aprende/tests/consent.test.ts`; `tests/test_audit_guardrails.py::test_a_refusal_keeps_nothing`, `::test_after_consent_is_withdrawn_nothing_more_is_kept_or_sent_to_the_model`; `aprende/e2e/gate.spec.ts` (3 tests) | None. | A client who says yes, gives details, then says no keeps her earlier answers on the server, but the screen says "Está bien. No guardamos nada." (`gate.refused.title`). Firm decision on retention: #52. |
| Conflict check before any detail; neutral stop; names staff-only | `tests/test_audit_guardrails.py::test_no_detail_is_taken_or_shown_before_the_conflict_check_clears` (11 routes), `::test_a_possible_conflict_shows_the_matched_names_to_staff_only`; `tests/test_fix_booking_conflict_hold.py` (2 tests) | A client under a possible conflict could still book a consultation. Fixed in #72. | `/journey` shows `conflict: "hold"`, not `"pending"`; it shows no names. Lead's call; no decision PR. |
| The AI never answers the client's own legal question | `tests/test_audit_guardrails.py::test_every_chat_prompt_routes_own_case_questions_to_the_attorney_and_fences_the_clients_words`, `::test_a_tagged_own_case_question_is_stored_for_staff_and_the_tag_never_reaches_the_client` | None. | The server cannot detect advice given without the hidden tag. The paid conversation run checks the model itself: #49. |
| Drafts are staff-only until approval; only verified citations | `tests/test_audit_guardrails.py::test_no_client_route_returns_a_draft_before_the_attorney_approves_it`, `::test_every_drafter_may_cite_only_the_verified_list`; `tests/test_fix_draft_citations.py::test_a_draft_citing_an_unverified_section_is_flagged_and_cannot_be_approved` | A draft flagged "NOT VERIFIED" could be approved and released. Fixed in #74. | — |
| Client and staff text is shown as text, never run as code | `tests/test_audit_guardrails.py::test_the_app_never_renders_raw_html`, `::test_the_aprende_staff_review_builds_its_page_from_text_nodes_only`; `aprende/e2e/audit-staff-text.spec.ts`; `aprende/e2e/admin-review.spec.ts::the attorney reads a draft with its marks, and no script in a draft runs` | None. | `web/admin.js` still builds HTML with `innerHTML` plus `esc()`. It is safe and tested, but it breaks the "text nodes only" rule. A rewrite is a separate task. |

The release test (#98) repeats the payment, refusal, conflict and draft rules end to end on a fake clock (`T8-06.md`).

## 4. Gamed tests

What was checked (`audit-gamed-tests.md`, `audit/lead-notes.md`):
- Disabled tests: `skip`, `xfail`, `test.only`, `test.fixme`, `eslint-disable`, `noqa`, `ts-ignore` in `backend/`, `aprende/` and `tests/`.
- Deleted test files and removed assertions in the git history (`git log -p` over `tests/`, `aprende/e2e/`, `aprende/tests/`).
- Test names, fixture names or test flags inside production code (`Torres`, `Mendez`, `PYTEST_CURRENT_TEST`, `TESTING`).
- Mocks that replace the code under test with a no-op.
- Five known past cases: bookings deleted on hours save, loop check off in drafting, the deleted paid-model guard, one holiday hard-coded, copied change-request and email code.

Result:
- No gamed tests found.
- The only skips are the Postgres tests when `APRENDE_TEST_PG_URL` is unset. CI sets it (`.github/workflows/ci.yml`).
- Every removed assertion was replaced by an equal or stronger one (for example commits `ef54d9c` and `16a906d`).
- One assertion became looser: `cde9463` changed `"<client_data>" not in system` to `"</client_data>" not in system` (`tests/test_t5_05_datos.py:209`).
  The stronger check now lives in `tests/test_audit_guardrails.py::test_every_chat_prompt_routes_own_case_questions_to_the_attorney_and_fences_the_clients_words`.
  It checks that the client's words never reach the instructions and that the fence cannot be closed from inside.
- All five past cases are fixed on `main`. For example, `tests/test_t6_04_drafts.py::test_a_looping_draft_is_rejected` and `tests/test_t6_10_cases.py::test_the_paid_run_needs_explicit_approval`.

## 5. Phone walkthrough

Setup: Chromium at 390×844, Spanish and English (`audit-walkthrough.md`). The lead reviewed all 59 screenshots (`audit/lead-notes.md`).
Limit: the walk stopped at lesson 1, item 2. Screens after payment were seen only in their waiting state, and staff steps were not walked.
The release test (T8-06) covers the full path.

| # | Finding | Severity | What happened |
|---|---|---|---|
| W1 | A lesson screen kept the previous lesson's title ("El testamento" on the trust, directive and POA lessons). | major | Fixed in #88. Test: `aprende/e2e/client-screens.spec.ts::W1: leccion title resets when id changes`. |
| W2 | The Preguntas and Perfil tabs showed "Próximamente". | major | Preguntas: built in #78 (T7-04). Tests: `aprende/e2e/preguntas.spec.ts` (2 tests). Perfil: built in #96 (T8-03), merged; tests in `aprende/e2e/pwa.spec.ts`. |
| W3 | "Tus datos" showed only "No se pudo enviar. Revise su conexión" when the model call failed. The question was hidden and the message blamed the connection. | major | Fixed in #88: the open question shows, with a neutral retry. Test: `aprende/e2e/client-screens.spec.ts::W3: datos shows open question when chat fails`. The new Spanish text (`datos.serverError`) needs the Spanish review (#53). |
| W4 | "Firmados" offered "Tomar la lección final" before any signing. | minor | Fixed in #88. Tests: `aprende/e2e/client-screens.spec.ts::W4: firmados final-lesson link only when gate open`; `aprende/e2e/firmados.spec.ts`. |
| W5 | The POA checkbox shrank when its label wrapped. | minor | Fixed in #88. Test: `aprende/e2e/client-screens.spec.ts::W5: documentos checkbox keeps size when label wraps`. |
| W6 | Gate screens repeat the heading in the character's bubble ("Está bien. No guardamos nada." twice). | minor | Not changed: a design choice. For the Spanish and character review, #53. |
| W7 | "Tus datos" used *tú*; the app uses *usted*. | copy | Fixed in the copy review #99: now "Sus datos" (`aprende/i18n/es.json:163`). No test (copy). |

One agent finding was wrong: the names field does have an accessible name. It sits inside its `<label>` (`Inicio.tsx:103`, lead check).
Passes: no sideways scrolling at 390 px, no raw text keys, no mixed languages, a neutral conflict hold, a neutral refusal, and payment blocked before the countersignature.

## 6. Bugs found after the audit

The release test (T8-06, `T8-06.md`) runs whole client journeys on a fake clock: fictional clients starting on a Wednesday and on a Thursday, a late review, a refusal, a possible conflict, an early payment attempt and an early draft request.
The release test found F1–F6. On CI it then found the two races (#100). The Render failure and the admin clash came from other reviews (#84, #79).
Each fix has its own PR, apart from the release test PR (#98).

| # | Bug | Cause | Fix | Test that now guards it |
|---|---|---|---|---|
| F1 | A client who started on a Wednesday and did everything on time was flagged late at scope review. | The timeline started the scope clock at the day-2 choice, but the attorney could only approve after the day-4 confirmation. | #85: the attorney may approve from the day-2 choice; a different day-4 choice reopens the scope. | `tests/test_t5_04_timeline.py::test_an_on_time_wednesday_journey_raises_no_scope_alert` |
| F2 | In "Tus datos", after the character said thanks, the next question never appeared. | `Datos.tsx` kept the next question but did not show it. | #90: the screen shows the next question's approved text. | `aprende/e2e/datos.spec.ts::after the character thanks her for an answer, the next question is on screen` |
| F3 | From the side panel, Stripe sends the client back to the web app, where she is not signed in. | Stripe's `success_url` is the web app's address. | **Open** (Kevin's list). The proposed fix is front-end work in the extension (`T8-06.md`). | — |
| F4 | After a client asked for a change, her journey left the attorney's review queue. | The queue listed only unapproved drafts. | #91: the queue also lists approved documents with an open change request. | `tests/test_t6_06_client_review.py::test_after_a_change_request_the_attorney_finds_the_journey_in_the_queue_and_revises_it` |
| F5 | The extension called its own `chrome-extension://` address instead of the API. | `build:ext` had no API address. | #89 (T8-02): the build gets `VITE_API_ORIGIN`. | `aprende/tests/extension-store.test.ts::has the API origin built in (it never calls its own chrome-extension:// origin for the API)`; `aprende/tests/e2e/extension-store.spec.ts::the side panel calls the API at the origin in host_permissions, and nothing else` |
| F6 | After any payment, no draft was ever written (production bug). | The worker never loaded the drafting and signing job handlers. It also crashed at start on a circular import. | #94: the worker loads the app first, then every job module. | `tests/test_fix_worker_handlers.py::test_the_worker_process_registers_a_handler_for_every_job_the_app_queues` |
| Render | Every Render deploy since #60 (2026-11-18) crashed on start: `No module named 'fpdf'`. | Render installs the root `requirements.txt`; T6-01 added `fpdf2` and `pypdf` only to `backend/requirements.txt`. CI installed both files, so it did not notice. | #84: one package list; `render.yaml` matches the live service. The #84 deploy went live on 2026-11-20 and `/health` answered ok (lead's Render record). | CI job `render`: `scripts/render-check.sh` starts the backend the way Render does (`.github/workflows/ci.yml`). |
| Race 1 | "Confirmar mis documentos" could confirm no documents on a slow phone. Both release journeys failed on day 4 on CI. | The button worked before the document choice had loaded. | #100: the button waits until the journey loads (`Resumen.tsx`). | `aprende/e2e/datos.spec.ts::on a slow phone, confirming waits for her document choice (it never confirms no documents)` |
| Race 2 | A reload right after an answer could lose the client's place in a lesson. | The position was saved after the screen painted. | #100: the position is saved before the paint (`Leccion.tsx`). | `aprende/e2e/lesson.spec.ts::the will lesson: explain, a wrong answer that comes back, sources, resume` (was intermittent on CI before) |
| Admin | Found while reviewing T7-05: one admin script replaced another's `api()` function for the whole staff admin. | `web/content.js` (#71) declared a global `api()`. | #79: `content.js` keeps its names private. | `tests/test_admin_scripts.py::test_no_two_admin_scripts_define_the_same_global_name` |

Related work:
- **#97 (performance).** On #96 the tap response check failed at 216 ms, because a tap waited for a slow 3D frame. Phones without fast graphics draw the characters slowly too.
  The character now draws less when frames are slow. Guard: `aprende/e2e/performance.spec.ts::INP on the lesson player stays under 200 ms on a 4× slower CPU`, run alone on CI (`.github/workflows/ci.yml`, step "INP on a quiet runner").
  The release test runs without WebGL (the characters' still images), because the 3D stalled the lessons in software rendering (`T8-06.md`). So the release test does not check the 3D characters; their own tests do.
- **#92.** #90 committed a `node_modules` link by mistake; #92 removed it and ignores it (`aprende/.gitignore`). No test.

## 7. Still open

Only items that are not fixed. "Decision PR" means: merging it accepts the recommendation.

| Item | Who decides | Decision PR |
|---|---|---|
| Run the 40 test conversations against the paid model (T5-08 live run; also the check for advice given without the tag). | Kevin (cost) | #49 |
| Run the legal review drafts for the fictional cases (T6-10), then the attorney reads a sample. | Kevin (cost), then the attorney | #65 |
| Legal content of the lessons, the characters' instructions, the "Tus datos" questions, the signing method. Includes T4-01 and T5-07 approvals. | Attorney | #50 |
| The engagement letter wording and payment after the countersignature. | Attorney | #57 |
| A withdrawal after details keeps earlier answers, while the screen says "No guardamos nada". Also the retention periods and the data promise. | Firm | #52 |
| Spanish review: W6 (repeated heading), the new W3 text `datos.serverError`, the characters' names. | Firm (Spanish reviewer) | #53 |
| Aprende accounts can also use the legacy portal, which has its own conflict step. | Firm | #54 |
| F3: from the side panel, Stripe returns the client to the web app. | Kevin | none |
| `/journey` shows `conflict: "hold"` instead of `"pending"` (no names). | Lead | none |
| The chat output guard (#75) answers with the general "service not available" message. A gentler retry may be better. | Lead | none |
| `web/admin.js` uses `innerHTML` with `esc()`; a rewrite to text nodes. | Lead (team task) | none |
| No test proves that test data use fictional people only. | Lead | none |
| Missing tests (section 2): T2-04 lint test; T2-10 Pages artifact (2); T3-01 to T3-04 art checks (6, manual); T3-05 screenshots, reduced motion, character label (3); T4-01 sentence count and reading level (2); T4-04 phone-to-extension resume and "(correcta)" name (2); T4-06 calm celebration (1); T4-07 screenshot diff, focus order, icon contrast (3); T5-06 voice fallback (1). Partly proven: T4-04 mid-step save, T4-04 200 % text, T4-05 exercise types, T5-06 microphone on the web app. | Kevin (whether to schedule them) | none |
