# Aprende y Planea — release report (Phases 7 and 8)

Date: 2026-11-21. Base: `main` after PR #96. Audience: Kevin and the firm.
The audit of Phases 1–6 is in `docs/aprende-audit.md`. The copy review is in `docs/aprende-copy-review.md`.

## 1. What is done

**Phase 7: staff controls (all merged)**

| Ticket | What staff can do | PR |
|---|---|---|
| T7-01 | Edit lessons, Sus datos questions and summaries; legal items need the attorney's approval of the exact version | #71 |
| T7-02 | See validator errors before publishing | #80 |
| T7-03 | Turn characters on or off (La Calavera always on), assign units, set voices, edit the characters' instructions through review | #86 |
| T7-04 | See every client's day, delays, conflict, payment, drafts, bookings and questions | #78 |
| T7-05 | Firm settings: switches (AI chat, voice, extension), prices, turnaround, retention, live payments | #81 |
| T7-06 | Analytics with counts only: completion, drop-off, accuracy, paid conversion, on-time completion | #83 |
| T7-07 | Every route checked for every role; every change writes an audit row | #82 |

**Phase 8: extension and polish (all merged)**

| Ticket | Result | PR |
|---|---|---|
| T8-01 | Side panel and popup fit a small screen; the popup has no 3D; no page asks for the microphone | #87 |
| T8-02 | Extension security (2 permissions, no remote code), the Store zip and its checks, the privacy notice page, the Store listing draft. **Not published.** | #89 |
| T8-03 | The web app installs as a phone app; Perfil (language, daily reminder, install, sign out); the daily nudge, the appointment reminder 24 hours before, the yearly review | #96 |
| T8-04 | Accessibility: axe on 31 screen states in both languages, 320 px and 200 % text on 12 screens. The manual TalkBack/VoiceOver checklist is for a person. | #95 |
| T8-05 | Phone speed: Lighthouse mobile map 97–99, lesson 89–98 (target 90); first JavaScript about 35 KB; taps under 200 ms on a 4× slower CPU | #93, #97 |
| T8-06 | The release test: two full two-week journeys on a fake clock, the late-review alert, the refusal paths, the side panel | #98 |
| T8-07 | The Spanish and English copy review (53 fixes) and this report | #99 |

**Bugs found and fixed while building** (each with a test that failed first): the Render deploy (#84), the Wednesday false late flag (#85), Sus datos hid the next question (#90), a change request left the attorney queue (#91), the extension called the wrong server (#89), drafts were never written after payment (#94), two slow-phone races (#100), the node_modules link in git (#92). 19 bugs in total since the audit started (see the audit, section 6).

## 2. Test results on `main`

| Check | Result |
|---|---|
| Backend (pytest, SQLite and Postgres) | 665 passed, 2 skipped |
| Front end (typecheck, lint, vitest) | 131 passed |
| Browser tests, web and extension (Playwright) | all passed in CI |
| Release journeys (fake clock, one worker) | 8 passed |
| Lighthouse mobile (map, lesson) | ≥ 90 in CI |
| Render start check (CI job `render`) | passes; the live `/health` answers |

Known noise in CI: the tap-speed test and the lesson-resume test are sensitive to a busy CI machine. Each passed on rerun; CI now keeps the failed tests' page snapshots so a real failure can be read. One backend test (the Wednesday journey) fails when only three particular test files run together; the full suite passes. It is a test-setup quirk, not an app bug.

## 3. Token use (this lead session and its agents)

| Work | Model | Output tokens | Input incl. cache | Cost (USD) |
|---|---|---|---|---|
| Audit | Beam-1.0-501B-A23B | 56,316 | 15,968,553 | 0.00 |
| Audit | claude-opus-5-5 | 142,059 | 44,886,994 | 17.58 |
| Audit fixes | Beam-1.0-501B-A23B | 14,340 | 2,753,922 | 0.00 |
| Lead | claude-opus-5-5 | 342,434 | 273,739,137 | 79.58 |
| Phase 7 | Beam-1.0-501B-A23B | 272,830 | 73,619,670 | 0.00 |
| Phase 7 | claude-opus-5-5 | 191,138 | 33,157,555 | 14.18 |
| Phase 8 | Beam-1.0-501B-A23B | 145,548 | 43,525,635 | 0.00 |
| Phase 8 | claude-opus-5-5 | 347,913 | 109,440,106 | 45.22 |

Beam's price per token on the firm's account is not known, so Beam cost shows as 0. No paid model run was made (#49 and #65 wait for approval). Tests never call a paid model.

## 4. Open questions

The full list, with recommendations and steps, is in `docs/aprende-kevin-list.md`.
