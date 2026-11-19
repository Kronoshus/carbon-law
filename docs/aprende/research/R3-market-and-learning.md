# R3 — Market and learning evidence for Aprende y Planea

Research date: 2026-11-18. Scope: (1) how existing will and estate-planning products serve this need, what users complain about, and what they charge; (2) evidence on learning and engagement (microlearning, gamification and streaks, plain language, Hispanic financial-education programs, AI disclosure and trust, Spanish-language legal information); (3) whether educating clients before they meet a lawyer saves attorney time or improves outcomes.

Background read (read-only): `docs/aprende-spec.md` §1–3 (and the motivation table in §7.4), `docs/aprende-phase-4-report.md`, and the lesson list in `aprende/content/lessons/` (will, trust, ahcd, poa, final, probate, comunidad, beneficiarios, cita).

How to read this file:
- Each finding has a number (F1, F2, …) so the implications section can point back to it.
- **Evidence** means what a source says. **Inference** means my reading of it, and it is always labeled.
- Every survey figure gives who ran it, the year, and the sample size where the source states one. Sources from before 2019 are marked **[older]**. Figures I saw only second-hand are marked **[second-hand]**.
- I checked prices and review counts on the vendors' own pages on 2026-11-18. Prices change often, and several vendors were running sales that day.

---

## Summary

- **DIY plans cost about $100–$500, and attorney help is an add-on.** LegalZoom (from $129), Trust & Will ($199 will, $499 trust, +$299 for attorney support), Quicken WillMaker ($109–$219) and Rocket Lawyer ($149–$349 a year) all fall in this range. FreeWill is free because nonprofits pay for it. Every DIY tool says it is "not a law firm". Aprende's $3,000 will is 10–20× these prices. Its case has to be what the tools do not offer: a California lawyer who drafts, reviews and supervises the signing, all in Spanish. (F1–F3)
- **No major DIY tool produces Spanish documents.** Trust & Will has a Spanish website, but its own FAQ says its documents are only in English. It says US law requires this; I could not confirm that claim. I found no Spanish document flow at LegalZoom, WillMaker or Rocket Lawyer. Free Spanish-language help in Los Angeles exists through legal aid (Bet Tzedek, LA County TLAP for people 60+) but depends on income or age. (F2, F5)
- **Complaints are mostly about billing, not the documents.** Many of LegalZoom's BBB and 1-star Trustpilot complaints are about auto-renewals and refusals to refund (BBB: 1,346 complaints in 3 years). Reddit threads and attorneys add a second theme: DIY documents fail at signing, funding and the residuary clause, and lawyers do not want to "check" them. (F4)
- **Very few Latinos have a will, and the usual reason is putting it off.** Only 14% of Hispanic respondents had a will in Caring.com/YouGov's 2025 survey (n≈2,500, all groups 24%). In Consumer Reports' 2022 survey (n=2,224), 82% of Hispanic respondents had no will. "Haven't gotten around to it" is the top reason in every survey, followed by "not enough assets" and "don't know how to start". These barriers are the kind short, scheduled lessons can address. (F6)
- **Streaks work, but breaking one hurts, and forgiveness helps.** Duolingo's own A/B tests show small but real retention gains from streak features. An RCT with 60,000 students (NBER 2025) found that streak messages increased use and math scores. The peer-reviewed work (Silverman & Barasch, JCR 2023) shows a broken streak lowers later engagement. The effect is worse when people blame themselves and weaker when the streak can be "repaired". Aprende's "su vela descansó" plus a weekly rest day matches this evidence. (F7–F9)
- **Easy-to-read, Spanish-language advance-planning tools have strong RCT evidence.** PREPARE, a self-directed Spanish/English online program with a 5th-grade-level advance directive, raised advance-care-planning documentation from 33.1% to 43.0% (n=986, 45% Spanish speakers, JAMA IM 2018). A Spanish-only trial (n=445) found the same direction. This is the closest evidence that Aprende's lessons can lead to completed documents. (F13)
- **Educating people before a meeting improves knowledge, but has not been shown to shorten the meeting.** The 2024 Cochrane review (209 RCTs) found decision aids raise knowledge by about 12 points out of 100. When used *before* a consultation, they made no significant difference to its length (−2.97 min, 95% CI −7.84 to +1.90; 5 studies). California's court self-help centers report benefit-to-cost ratios of about 3:1 to 4:1, but those rest on estimated, not measured, time savings. The firm should expect better-prepared clients and should measure attorney minutes. It should not count on saving them. (F18–F20)
- **People want to be told when AI is used, and disclosure costs engagement.** In a 2019 field experiment (n>6,200), saying up front that a sales caller was a bot cut purchases by more than 79.7%. Americans also say they want to be told: 72% in Pew's 2026 survey (n=3,488). Only 5% would make estate documents with AI and no attorney review (Trust & Will survey 2026, n=5,000). LLMs still make many legal errors and perform worse in Spanish conversations. So the AI should gather facts and explain, the lawyer should decide, and the app should say this clearly. (F14–F17)

---

## Findings

### Question 1 — How existing products serve the need

**F1. Prices and what is included (vendor pages, checked 2026-11-18).**

| Product | Price (individual) | Attorney involvement | Spanish | Source |
|---|---|---|---|---|
| **LegalZoom** | Basic Will $129 (sale $116.10); Pro Will $149 (sale $126.65) adds health care directive, medical and financial POA, HIPAA, and unlimited 30-min attorney consultations for 30 days, then $25/month; Premium Will $299 (sale $239.20) adds 1 year of consultations (renews $199/yr) and an annual 1-hour estate plan review. Couple Basic $229. | Independent network attorneys. The FAQ says Premium gives "access to an attorney licensed in your state who can … review your documents when you're done." Footer: "LegalZoom is not a law firm … except where authorized through its subsidiary law firm LZ Legal Services, LLC." | No Spanish document flow found. | legalzoom.com last-will page |
| **Trust & Will** | Will Plan from $199; Trust Plan from $499; optional $49/yr membership (updates, vault). "Attorney Led" plans for complex cases from $1,499. | Attorney Support add-on, flat $299: "a live attorney who can help with all matters related to your estate plan." Documents are "attorney-designed, customized by you." | Spanish website (trustandwill.com/es). Its Spanish FAQ says it does **not** offer Spanish documents because "US law requires estate planning documents to be written in English" (my translation). I could not confirm this legal claim; see F5. | trustandwill.com/compare; /attorney-support; /resources/spanish-language-estate-planning |
| **FreeWill** | Free. Funded by "more than 1000 nonprofit organizations." | None: "FreeWill is not a law firm … not substitutes for the advice of an attorney." Offers wills, AHCD, durable financial POA, and revocable living trusts for California residents. | Spanish articles in a "Multilingual Resources" section (e.g., "Cómo hacer un testamento en 10 pasos", 2023). I did not confirm that the document tool itself runs in Spanish. | help.freewill.com FAQ (updated 2025-07-15); freewill.com/learn/how-to-make-a-will-es |
| **Quicken WillMaker & Trust (Nolo)** | Starter $109, Plus $149, All Access $219 (1-year subscription; includes living trust, transfer-on-death deed). | No attorney review on the pricing page. | None found. | willmaker.com pricing |
| **Rocket Lawyer** | Memberships: Standard $149/yr, Plus $249/yr, Pro $349/yr (7-day free trial). Basic will document "make yours for free". A Legal Advice Session is not included in Standard and is priced separately at $149 (30 min) or $249 (60 min). | Plans include "Ask an Attorney" questions (12, 36 or unlimited) and, on higher tiers, live consultations. Membership also includes an AI legal assistant. | US site has no Spanish flow found. Rocket Lawyer España has shut down. | rocketlawyer.com/pricing; rocketlawyer.com/es/es/important-notice |
| **Willful** | From $129. | — | — | **Canada only** (willful.co). Not a US option. |

*Inference:* the market sells a one-time document package for $100–$500, with time-boxed attorney access sold as a subscription upsell. No DIY vendor drafts as the client's own law firm, supervises signing with witnesses, or works in Spanish. These are what Aprende sells.

**F2. Free and low-cost human help in Los Angeles.**
- **LA County Aging & Disabilities, Traditional Legal Assistance Program (TLAP):** free legal advice, assistance and representation for older adults and eligible caregivers. Listed issues include "Wills, trusts, and estate planning" and "Advance planning and decision-making". Providers include Bet Tzedek. Services are by appointment after an eligibility intake. (ad.lacounty.gov/services/older-adult-services/tlap, 2026 page)
- **Bet Tzedek "Leaving a Legacy":** launched in 2023 with LA County DCBA and funded by the American Rescue Plan. It offers wills, trusts and estate plans to LA County residents with low-to-moderate income who own assets and live in high-need areas. Bet Tzedek also helps with advance directives, POAs and wills for seniors. (bettzedek.org; dcba.lacounty.gov newsroom, 2023)
- **Wills for Heroes:** bar-run clinics where volunteer attorneys draft simple wills, POAs and health care directives for first responders. In Southern California the San Diego County Bar runs one for San Diego, Imperial and Riverside counties (sdcba.org/willsforheroes). I found no current Los Angeles County program.
- **California Statutory Will (Probate Code §6240):** a free fill-in form, distributed by county law libraries (e.g., LA Law Library PDF). It must be signed in front of two adult witnesses (Sacramento County Public Law Library form instructions; seen in a search snippet only).

*Inference:* free options exist but are limited by income, age or occupation, and most are not built around Spanish-first self-paced learning. Ana (58, Boyle Heights) is two years short of TLAP's 60+ threshold.

**F3. Market size and reach (company-reported).** LegalZoom claims "over 2.1 million estate plan customers". Trust & Will claims "over 1M people". The Stanford GSB article (2022) reports that FreeWill users committed "more than $7.5 billion" to causes. It also reports, citing FreeWill's 2022 Planned Giving Report, that 16% of FreeWill users (June 2021–May 2022) included a charitable bequest, versus "2% to 5% of the general population". FreeWill's free model works because nonprofits want bequests. A competitor's blog (meetneptune.com) says nonprofits "receive reports on users who opt to include a charitable bequest" **[second-hand, competitor source]**.

**F4. What users complain about.**
- **Ratings are high on vendor-subscribed platforms.** Trustpilot (read 2026-11-18): LegalZoom 4.6 (34,094 reviews), Trust & Will 4.5 (5,895), FreeWill 4.9 (4,841). All three profiles are marked "Paid Trustpilot subscription". LegalZoom and Trust & Will invite customers to review, and Trustpilot states "we don't fact-check reviews". Treat these ratings as marketing-influenced.
- **Billing and auto-renewal dominate negative reviews.** BBB lists LegalZoom as A+ accredited with "1,346 complaints in the last 3 years, 294 in the last 12 months". The complaints visible on 2026-11-18 were about renewals charged above the confirmed price, and notices that went to spam or old emails. These mostly concerned business services, not wills. Recent 1-star Trustpilot reviews say the same ("charged my card $299 for a full year … refused" a prorated refund). One estate-planning complaint: "I paid for a premium trust that includes attorney consultation … the interview process … is lacking and confusing … The attorney never called." Trust & Will negatives seen: trouble finding a notary, unwanted marketing calls, and a family member unable to get a copy of a deceased sister's will.
- **Quality and completeness worries (Reddit; anecdotal).** r/EstatePlanning, "Did we make a huge mistake by using LegalZoom?" (about 2025): a Colorado couple bought a trust package plus a deed through a third party (GoDeeds). A year later they still had not notarized or recorded it, and they did not know what to do with the deed. r/LawFirm thread (about 2026) of attorneys: callers want DIY wills "checked", and attorneys decline. One says they "almost always generate more fees off DIY wills" because of "problems with execution, absence of a residuary clause (partial intestacy)". Another says reviewing template documents "often takes longer than just drafting from scratch" and charges a $300–$500 flat review fee. These are self-selected opinions, not data.

*Inference:* the complaints point to three openings for Aprende: (a) no subscription traps; (b) the client is not left alone at signing, funding and deed recording; (c) a named lawyer who actually responds.

**F5. Spanish-language legal content and documents.**
- *Evidence:* Trust & Will's Spanish FAQ says it does not offer Spanish documents because US law requires English (above). A California court-translator association page (cacfti.org) and translation vendors say the opposite: a will "does not have to be drafted in the English language to be submitted to probate" but needs a certified translation **[second-hand, non-authoritative, possibly self-interested]**. I did not find a California statute on this. **Unresolved. It is a question for the attorney (see Implications, firm workflow).**
- *Evidence:* the California Attorney General's consumer alert (2025-06-27) warns that "in many Spanish-speaking nations, 'notarios' are powerful attorneys", while a US notary public "is not necessarily authorized to provide legal services". (oag.ca.gov)

### Who lacks a plan, and why

**F6. Will ownership and reasons (surveys disagree on levels, but not on direction).**

| Survey | Who ran it, when, n | Overall | Hispanic | Top reasons for not having one |
|---|---|---|---|---|
| Caring.com 2025 Wills & Estate Planning Study | Caring.com with YouGov, 2025, "2,500+" adults (16% Hispanic) | 24% have a will; 13% a living trust | **14%** (14.6% in 2024) | 43% "just haven't gotten around to it" (procrastination top since 2022). In 2025, 22% of Hispanic respondents with plans said an **employer benefit** prompted them (up from 13%, the largest rise of any group). Family expansion rose to 27% for Hispanics. |
| Consumer Reports | CR, April 2022, 2,224 adults | ~1 in 3 has a will | **82% have no will** (White 61%) | 43% plan to but haven't. Among Hispanics without a will, 27% think they don't have enough assets. Overall, 20% not sure how to create one; 9% want next of kin to get everything automatically. |
| AARP | AARP, April 2024, 1,869 adults 50+ (Hispanic oversample) | 51% of 50+ (38% at 50–64; 66% at 65+) | lower than White (exact figure not on the page) | 61% haven't gotten around to it; 21% not enough assets; 19% don't know how to start; 16% don't want to think about it; 15% can't afford it. 93% say having a will is important. |
| Trust & Will 2026 Estate Planning Report | Trust & Will (vendor), Jan 28–Feb 5 2026, 5,000 adults | 56% have no documents at all; will ownership 26% (31% in 2025) | — | 73% say estate planning is personally important. **Vendor survey; conflict of interest.** |

- The Center for Retirement Research at Boston College (blog, 2023) reports that older Black and Hispanic households are "much less likely" to have wills than non-Hispanic White households. It says wills matter most for the house, which intestacy can split into small shares.
- *Conflict:* overall rates range from 24% to 51% because the surveys sampled different age groups and asked differently. Use them for direction, not as one number.
- **Context:** the LSC 2022 Justice Gap study (NORC AmeriSpeak, ~5,000 adults) found low-income Americans got no or not enough legal help for 92% of civil legal problems. Of those who did not seek help, 46% cited cost; 53% doubted they could find an affordable lawyer.
- **Device and literacy context.** Pew (2024): "roughly one-in-five Black or Hispanic adults are smartphone dependent", and 75% of Hispanic adults have home broadband (vs 83% White). NCES PIAAC 2023: 28% of US adults are at Level 1 or below in literacy (up from 19% in 2017). For Hispanic adults the figure rose from 31% to 45%. PIAAC is an English-language assessment, so this measures English literacy, not ability in Spanish.

### Question 2 — Learning and engagement

**F7. Duolingo's own published streak data** (company blog posts; A/B tests or observational data, not peer-reviewed).
- 2017 (Loh) **[older]**: a "Streak Wager" raised Day-7 retention by +14%. A "Weekend Amulet" (protecting the streak over a weekend) made learners "4% more likely to come back a week later and 5% less likely to lose their streak". DAU fall 5–10% on weekends.
- 2020 (Yu): learners on a 7-day streak are "2.4 times more likely to continue using Duolingo the next day". Letting **one lesson** extend the streak, separately from the daily goal, gave +3.3% Day-14 retention, +1% DAU and +10.5% learners on a streak (+19% among new learners). Learners with "intense" daily goals were the *least* likely to be on a streak.
- 2022 (Mansur): milestone animations raised the chance a new learner was still active after 7 days by +1.7%. Allowing two Streak Freezes raised DAU by +0.38%. Learners who reach a 7-day streak are "3.6 times more likely to complete their course". Duolingo itself says breaking a streak "can … feel quite demotivating" and that "fear of losing a streak could prevent learners from even attempting one."
- *Caveat:* the "2.4×" and "3.6×" figures compare people who chose to keep streaks, so they include self-selection. The A/B effects are causal but small, and they come from a product with many millions of users.

**F8. Independent evidence on streaks.**
- **RCT:** Aulagnon, Cristia, Cueto & Malamud, NBER Working Paper 34173 (Aug 2025). 60,000 4th–6th graders in Peru were randomized to messages that highlighted streaks, personalized reminders, generic reminders, or no messages. Streak highlighting and personalized reminders both increased platform use more than generic reminders or control. Streaks worked better on *how much* students used it; personalized reminders worked better on *whether* they used it. Among the 1,500 students tested at the end, streak highlighting improved math scores compared with control.
- **Broken streaks:** Silverman & Barasch, *Journal of Consumer Research* 49(6), 2023, seven studies. Highlighting an intact streak increases later engagement relative to highlighting a broken one, "independent of actual past behavior". The negative effect is "amplified when consumers attribute a break in the streak to themselves" and "attenuated when consumers can 'repair' a broken streak".
- **Slack in goals:** Duolingo cites a UPenn/UCLA study that "a little 'slack'" is more motivating than rigid rules. The matching paper (Sharif & Shu, *Organizational Behavior and Human Decision Processes*, 2021) reports that goals framed with "emergency reserves" help people persist after missing a sub-goal. I saw only its abstract snippet.

**F9. Gamification, microlearning and retrieval practice.**
- **Gamification meta-analysis** (Sailer & Homner, *Educational Psychology Review* 2020, ERIC abstract): small significant effects on cognitive (g=0.49; k=19, N=1,686), motivational (g=0.36; k=16, N=2,246) and behavioral outcomes (g=0.25; k=9, N=951). Only the cognitive effect held up in the most rigorous studies. "Inclusion of game fiction" (a story) and social interaction were significant moderators for behavioral outcomes.
- **Negative effects:** Almeida et al., systematic review in *Information and Software Technology* (2023). The most reported negative effects were "lack of effect, worsened performance, motivational issues, lack of understanding, and irrelevance". I read only the abstract snippet.
- **Microlearning** (De Gagne et al., *JMIR Medical Education* 2019, scoping review of 17 studies, all units under 15 minutes): positive effects on knowledge and confidence. No study measured the highest-level outcomes (results in practice), and downsides included "technology inequalities, and privacy concerns". The evidence comes from health-professions students, not lay adults.
- **Retrieval practice** (Adesope, Trevisan & Sundararajan, *Review of Educational Research* 2017) **[older]**: "practice tests are more beneficial for learning than restudying and all other comparison conditions."

**F10. Dark patterns: regulators' definitions.**
- FTC staff report *Bringing Dark Patterns to Light* (Sept 2022): dark patterns are "design practices that trick or manipulate users into making choices they would not otherwise have made and that may cause harm". The report names countdown timers "on offers that are not actually time-limited" and false scarcity. It cites a study where dark patterns "doubled the percentage of consumers who signed up" for a dubious service, and says combining patterns strengthens the effect. It also flags subscriptions that are hard to cancel. (The FTC's 2024 "click-to-cancel" rule was vacated by the Eighth Circuit on 2025-07-08 on procedural grounds — law-firm alerts, WilmerHale/Sidley **[second-hand]**.)
- California Privacy Protection Agency Enforcement Advisory 2024-02: a dark pattern is an interface "with the substantial effect of subverting or impairing user autonomy, decisionmaking, or choice" (Civ. Code §1798.140(l)). "Dark patterns are about effect, not intent." It calls for "symmetrical choices" and "clear and understandable language".

**F11. Plain language and comprehension.**
- Mindlin, "Is Plain Language Better?" (Transcend, undated, uses 2000 Census data) **[older]**. 60 jury-panel members tested Judicial Council of California forms. Only 23% understood the purpose of the untreated Proof of Service (CH-130), against 70% for the plain-language version. For the Subpoena Duces Tecum, 60% vs 90% could say what the form told them to do. Both differences were significant at p<.01. This is small and old, but the effect is large.
- The PREPARE trials (F13) used advance directives written at a 5th-grade reading level.

**F12. Financial-education interventions, including for Hispanic communities.**
- Kaiser, Lusardi, Menkhoff & Urban, *Journal of Financial Economics* 2022: meta-analysis of 76 RCTs, more than 160,000 people. Financial education has "positive causal treatment effects on financial knowledge and downstream financial behaviors", effects are "economically meaningful", and results are robust to publication bias.
- Blanco, Duru & Mangione, *Journal of Family and Economic Issues* 2020, community RCT, n=142 low/moderate-income, mostly Spanish-speaking Hispanics in Los Angeles. Spanish-language retirement education plus "behavioral nudges": 14% of the treatment group opened a myRA account vs 0% of controls. The estimated effect was 12 percentage points (17 pp among people who had a bank account).
- GFLEC/TIAA P-Fin Index report on Hispanics (survey fielded 2016, n=1,043 with Hispanic oversample) **[older]**: programs that "separately address U.S.-born and foreign-born Hispanics are likely to experience better results".

**F13. Spanish-language, easy-to-read advance-care-planning tools (the closest analogue to Aprende).**
- Sudore et al., *JAMA Internal Medicine* 2018 **[older]** (PREPARE RCT, 2014–2017, four San Francisco safety-net clinics). n=986 adults 55+; 45.1% Spanish-speaking; 39.7% with limited health literacy. PREPARE (a self-directed online program) plus an easy-to-read AD vs the AD alone raised new advance-care-planning documentation at 15 months from 33.1% (167/505) to 43.0% (207/481). It also raised patient-reported engagement, with no clinician- or system-level intervention.
- PCORI summary of the Spanish-only PREPARE trial (n=445 Spanish-speaking Latino adults, mean age 64, 72% women). The PREPARE group was more likely to have wishes documented and to engage in planning at each follow-up. Its design included a reminder phone call 1–3 days before the primary-care visit to bring up wishes and the AD.

**F14. AI disclosure: effect on behavior.** Luo, Tong, Fang & Qu, *Marketing Science* 38(6), 2019: field experiment with more than 6,200 customers receiving outbound sales calls from chatbots or humans. Undisclosed chatbots were "as effective as proficient workers". Disclosure before the conversation "reduces purchase rates by more than 79.7%", because customers saw the bot as "less knowledgeable and less empathetic". The effect was smaller with late disclosure and with customers' prior AI experience. (Sales context, China. Late disclosure is not an option for Aprende — see F16.)

**F15. Public attitudes to AI in health and legal help.**
- Pew Research Center, survey of 3,488 US adults, June 22–28, 2026: 72% say it is extremely or very important that a provider tells them when AI is used in their care. 63% want more say over whether AI is used, vs 21% comfortable with their current say. White adults were more likely than Black or Hispanic adults to want to be told for tasks that shape medical decisions.
- KFF Tracking Poll on Health Information and Trust, Feb 24–Mar 2, 2026, n=1,343: 32% used AI for health information in the past year, 41% of users partly "to look up information before seeing a provider", and 77% are concerned about the privacy of medical information given to AI. Hispanic adults (19%) used AI for mental-health advice more than White adults (12%).
- Rev (vendor), SurveyMonkey, Dec 2–3, 2025, n=1,002, **unweighted**: 65% have used an AI chatbot for legal help; 39% say AI is good for early research but a lawyer should handle decisions; 43% are comfortable using AI to clarify legal terms; 46% of non-users cite accuracy concerns.
- Trust & Will 2026 report (vendor, n=5,000): 30% trust AI more than a human attorney for estate planning (20% in 2025). "Only 5% … would use AI to create estate planning documents without any attorney review."

**F16. California rules on AI disclosure, relevant by analogy.**
- Bus. & Prof. Code §17941 (SB 1001, 2018): it is unlawful to use a bot to mislead someone about its artificial identity in order to influence a purchase. The disclosure must be "clear, conspicuous, and reasonably designed to inform".
- SB 243 (2025), companion chatbots: if a reasonable person could think they are talking to a human, the operator must give a "clear and conspicuous notification" that the chatbot is not human, with extra duties toward minors. Whether Aprende's characters count as "companion chatbots" is a legal question for the attorney.
- AB 3030 (in force 2025-01-01): health-care providers must tell patients when GenAI writes clinical communications and explain how to reach a human. It does not apply to messages a licensed provider has reviewed. (Medical Board of California page; health only, cited as an analogy.)
- State Bar of California, *Practical Guidance for the Use of Generative AI in the Practice of Law*, 2026 revision (approved 2026-05-14, replaces Nov 2023): "An attorney must consider disclosure to their client that they intend to use AI in the representation, including how the technology will be used, and the benefits and risks." It also covers confidentiality when an AI system has access to client data.

**F17. Accuracy of AI and machine translation for legal information, including in Spanish.**
- Stanford RegLab/HAI (blog on a preprint, 2024-01-11): legal hallucination rates of 69%–88% on specific legal queries for the models tested (2023-era models). Models "often lack self-awareness about their errors."
- Chen et al., *JAMIA Open* 2026: a GPT-4o pre-visit chatbot tested by 31 bilingual participants (10 Spanish). English interactions scored higher on usability, conversation quality and summary quality. "Conversational performance declined most for Spanish and Hindi", with more "repetition, transcription errors, and … breakdowns" in non-English. The authors call for per-language validation. The sample is small.
- NCSC, *Machine Translation: Considerations and Cautions for Courts* (2025). It cites a study of Google-translated discharge instructions in which Spanish had the highest accuracy (94%), and warns that "even a six percent inaccuracy rate can lead to dangerous, serious consequences" **[second-hand: NCSC citing the underlying study]**.

### Question 3 — Does educating clients first save attorney time or improve outcomes?

**F18. Medical analogue: decision aids (best available evidence).** Stacey et al., *Cochrane Database of Systematic Reviews* 2024: 209 RCTs, 107,698 participants. Decision aids raised knowledge by 11.90/100 points (high certainty; 107 studies), improved risk perception (RR 1.94) and reduced decisional conflict, with no difference in decision regret. **Consultation length:** used *before* the consultation, "no difference" (MD −2.97 min, 95% CI −7.84 to +1.90; 5 studies, 420 participants). Used *during* the consultation, 1.5 minutes longer (95% CI 0.79–2.20; 8 studies, 2,702). The authors call for more research on "cost and resource use".

**F19. Small studies showing time saved on instruction.** AHRQ-funded VIC study (Yale, R21; RCT with 50 asthma patients, paper consent vs a tablet multimedia consent): VIC "reduced the time spent for initial patient instruction, including protocol explanations and questions and answers", and patients were more satisfied. The page gives no minutes. Search results also show studies where patient-education videos cut provider counseling time. I did not verify those beyond their abstracts' headlines, so I do not rely on them.

**F20. Legal analogue: court self-help centers (cost-benefit estimates, not trials).**
- Judicial Council of California, *Impact of Self-Help Center Expansion* (report to the Legislature, Jan 2021): in 2019, self-help centers served 1,011,315 visitors. 510,560 received in-depth services (30–60 min), and 7% of extended services were in a language other than English.
- Judicial Council 2022 narrative supplement (June 2022) monetizes $322 of benefit per filing. That figure combines $112 in avoided litigant trips, **10 minutes of courtroom time** ($170) and **20 minutes of clerk time** ($40). The time figures are averages of estimates from interviews and from Greacen (2009) **[older]**, not measurements. Weighted benefit-to-cost ratios are 3.32 for one-on-one help and 4.35 for workshops. For **probate**, one-on-one help was the lowest at 1.87.
- NLADA research brief (2021) summarizing older California work **[second-hand; underlying 2005 and 2009 reports older]**: litigants who used self-help centers "were less surprised by the outcome" and felt more able to communicate with the judge. Self-help services cost "roughly $.45 for every $1.00 saved".
- Law-firm blog posts claim intake questionnaires turn the meeting from "data-entry" into strategy (e.g., emersonlawfirm.com). These are anecdotes, not evidence.

*Inference (Q3):* the evidence consistently shows that pre-education improves **knowledge, preparation and completion**. It does **not** show shorter professional meetings. The best medical data has a confidence interval that allows anything from about 8 minutes saved to 2 minutes added. Time savings, where reported, come from structured instruction and paperwork, not from the expert's advice. For Aprende, the likely savings are in staff and attorney time on fact-gathering and repeated explanations. Whether the consultation itself gets shorter is unproven.

---

## Implications for Aprende

Each item names the app part, says what to do, gives a confidence level, and points to the findings it rests on. "Confidence" is about the evidence behind the recommendation, not about how much effort it takes.

### Pricing and discounts
1. **Show the $3,000 next to what it buys, not next to a DIY price.** Put a plain list on the price card: drafted by a California lawyer for you, reviewed before you see it, Spanish explanations, signing with witnesses arranged, funding checklist. Do not compare with LegalZoom by name. Clients will meet $129–$499 offers in ads, so the card has to explain the gap itself. — *Medium* (F1, F4).
2. **One price, no auto-renewing subscription.** If the firm later offers yearly reviews, make them opt-in, priced up front and easy to cancel. Billing complaints dominate the competitors' negative reviews, and regulators target hard-to-cancel subscriptions. — *High* (F4, F10).
3. **Keep the "discounts are never taken back, no timers" rule, and keep a floor visible.** A countdown on the $100-per-lesson discount would match the FTC's dark-pattern examples. — *High* (F10; spec §2 principle 4, §7.3).
4. **Price anxiety is real for this audience.** The LSC study found 53% of low-income Americans doubt they could find an affordable lawyer, and AARP found 15% "can't afford" a will. Consider a short, honest "if you can't afford this" note that points to TLAP (60+) and Bet Tzedek. *Inference:* this builds trust and screens out clients the firm cannot serve, but it is a business call. — *Low* (F2, F6).

### Lesson content
5. **Lesson 1 should answer "I don't have enough to need a will" and "I'll do it later" directly.** These are the top reasons in every survey, and Hispanic respondents name "not enough assets" a little more often (CR: 27%). Use the house and guardians for grandchildren as the anchor (CRR: the house is the asset intestacy fragments). Any statement about thresholds or intestacy needs the attorney's approval under the existing review packet. — *Medium* (F6).
6. **Add a "notario ≠ notary public ≠ abogado" item** to `cita.yaml` (what to bring to the signing) or `final.yaml`, citing the California AG alert. Spanish-speaking clients may trust a "notario" as a lawyer. — *Medium-high* (F5).
7. **Keep retrieval practice and spaced refreshers.** Quizzes, the wrong answer that comes back, and the day 6–12 refreshers are the best-supported parts of the learning design. Gamification adds a small effect on top, so do not count on game mechanics to carry learning. — *High* for retrieval practice (F9); *medium* for gamification (F9).
8. **Test comprehension with real readers, not only readability scores.** The current Fernández-Huerta 77.9 / Flesch 74.8 scores are a good start. The plain-language evidence (CH-130: 23%→70%) comes from people answering "what is this document for?". Add five-person tests with Spanish-dominant adults on the will and AHCD lessons. Make that question the first item of each core lesson. — *Medium* (F11, F13).
9. **The AHCD lesson can borrow from PREPARE's design:** 5th-grade reading level, short video stories, a step-by-step program, and an action plan at the end. The planned El Oso calm mode fits. — *Medium-high* (F13).

### Character tone and AI disclosure
10. **Keep La Calavera's up-front disclosure. Do not delay it to protect engagement.** Luo et al. found early disclosure lowers persuasion. But the State Bar guidance, §17941's purpose and public preference (Pew 72%) all point to disclosing early. Instead of hiding the AI, make the human role visible: "Yo le ayudo a aprender y a juntar sus datos; el abogado Raval decide y revisa todo." People said they want AI with attorney oversight (only 5% want no review). — *Medium-high* (F14–F16).
11. **No AI character should sell.** Luo's effect was measured on sales calls. The payment step (day 5) should be firm-branded screens and the engagement letter, not a character pitch. — *Medium* (F14).
12. **Story and characters are justified by evidence, competition and leaderboards are not.** "Game fiction" moderated gamification effects; competition helped mainly when combined with collaboration. A cast without leaderboards fits Ana. — *Medium* (F9).

### Intake questions ("Tus datos" and the closing conversation)
13. **Keep the question list scripted. Use the model only for phrasing and follow-ups, with a Spanish test set.** Legal hallucination rates and Spanish-specific conversation breakdowns (Chen 2026) argue against letting the model decide what to ask or what counts as "covered". Add Spanish test conversations with repetition, code-switching (Spanglish) and speech-to-text errors to the Phase 5 test set. The attorney reviews the structured summary, not the chat. — *High* for the scripted list (F17); *medium* for the Spanish test-set content (F17).
14. **Ask one question that the survey data suggests matters:** "¿Su empleador ofrece un plan legal o de testamentos?". Employer benefits were the fastest-growing trigger among Hispanic respondents. *Inference:* this matters both to qualify clients and as a conflict or overlap check. — *Low* (F6).
15. **Show privacy in plain words at the consent step and in "Tus datos".** 77% are concerned about medical data given to AI (KFF). Show what goes to the model, what the firm keeps, and the delete button. — *Medium* (F15, F10).

### Timeline and reminders
16. **Streak copy should never blame the client, and repair should be built in.** "Su vela descansó" plus one rest day a week matches Silverman & Barasch (self-blame amplifies the harm; repair softens it) and Duolingo's freeze tests. Avoid copy like "you broke your streak". Phrase rest days as something that happens, not something the client failed at. — *High* (F7, F8).
17. **One lesson extends the candle, and there is no daily target above that.** Duolingo found higher daily goals lowered streak-keeping. — *Medium-high* (F7).
18. **Personalize reminders (name, the next concrete step, the next price).** Personalized reminders beat generic ones in the Peru RCT, and that held for whether students came back at all. Keep the one-a-day cap. — *Medium* (F8).
19. **Add a reminder 1–3 days before the consultation and before the signing that says what to bring and what to ask,** as PREPARE's pre-visit call did. — *Medium* (F13).
20. **Two weeks with dates is a good counter to "haven't gotten around to it".** *Inference:* procrastination is the top barrier, and a dated plan with gates gives a deadline the client did not have to set. — *Medium* (F6).

### Trust and safety copy
21. **Name the lawyer, show his State Bar number with a link to the State Bar lookup, and say "this is a law firm".** The competitors all say "not a law firm", and the AG warns about notario fraud. — *Medium-high* (F1, F5).
22. **Say plainly that the documents are in English (if the attorney confirms they will be)** and explain what Spanish materials the client will get. This needs the attorney's decision; see item 26. — *Medium* (F5).
23. **Do not use the Trustpilot-style review widget as social proof** unless reviews are real and unpaid. FTC examples include fake activity and testimonials. — *Medium* (F4, F10).

### Firm workflow
24. **Do not promise the firm shorter consultations. Measure them.** Cochrane found no significant change in consult length when education came first. Log attorney minutes per matter (scope review, consultation, draft review, change requests) for the first clients and compare with the firm's current wills. Where saving is plausible: less fact-gathering and fewer repeated explanations; more complete intakes; fewer late changes. — *High* that it should be measured; *low* that minutes will drop (F18–F20).
25. **Track completion as the main outcome.** PREPARE's benefit was documents actually completed (33%→43%). Report signed plans ÷ clients who started day 1, by language. Also report the day each client drops out. — *Medium-high* (F13).
26. **Questions to put to Pankaj Raval:**
    - (a) Will executed documents be in English only, with Spanish courtesy translations, or bilingual? Trust & Will claims US law requires English; translator sources say a foreign-language will can be probated with a certified translation. I found no statute either way.
    - (b) Does SB 243 ("companion chatbot") reach the characters?
    - (c) What AI-use disclosure goes into the engagement letter under the 2026 State Bar guidance?
    — *Not an evidence call; needed before Phase 5* (F5, F16).
27. **Plan for DIY "fix-it" clients.** Attorneys describe a steady stream of people with LegalZoom/Rocket Lawyer documents who want them checked. *Inference:* the firm may want a stated policy (redo vs review) and a lesson item on "if you already made a will online". — *Low* (F4).

---

## Sources

Vendor pages and reviews (all read 2026-11-18 unless noted):
- LegalZoom, Last Will and Testament — https://www.legalzoom.com/personal/estate-planning/last-will-and-testament-overview.html (2026)
- LegalZoom, Trust & Will vs. LegalZoom — https://www.legalzoom.com/compare/trust-and-will-vs-legalzoom (2026)
- Trust & Will, Compare plans — https://trustandwill.com/compare (2026); Attorney Support — https://trustandwill.com/attorney-support (2026); Spanish resources/FAQ — https://trustandwill.com/resources/spanish-language-estate-planning (2026); Spanish will page — https://trustandwill.com/es/testamento/ (2026)
- FreeWill FAQs — https://help.freewill.com/article/81-freewill-faqs (updated 2025-07-15); "Cómo hacer un testamento en 10 pasos" — https://www.freewill.com/learn/how-to-make-a-will-es (2023)
- Quicken WillMaker pricing — https://www.willmaker.com/lander/pricing (2026)
- Rocket Lawyer pricing — https://www.rocketlawyer.com/pricing (2026); Rocket Lawyer España notice — https://www.rocketlawyer.com/es/es/important-notice
- Willful — https://www.willful.co/ (Canada)
- Trustpilot: LegalZoom — https://www.trustpilot.com/review/legalzoom.com ; Trust & Will — https://www.trustpilot.com/review/trustandwill.com ; FreeWill — https://www.trustpilot.com/review/www.freewill.com (2026)
- BBB, LegalZoom complaints — https://www.bbb.org/us/ca/mountain-view/profile/legal-document-help/legalzoom-1216-13156151/complaints (2026)
- Reddit r/EstatePlanning, "Did we make a huge mistake by using LegalZoom?" — https://www.reddit.com/r/EstatePlanning/comments/1kzyqrd/ (about 2025; anecdotal)
- Reddit r/LawFirm, "[Estate Planning] I'm in utter disbelief…" — https://www.reddit.com/r/LawFirm/comments/1t7r1hz/ (about 2026; anecdotal)
- Stanford GSB, "Where There's No Will, This Company Provides a Way" — https://www.gsb.stanford.edu/experience/news-history/where-theres-no-will-company-provides-way (2022)
- Meet Neptune blog, "Is FreeWill Legit?" — https://www.meetneptune.com/blog/is-freewill-legit-free-online-will-review (competitor; search snippet only)

Legal aid and public programs:
- LA County Aging & Disabilities, TLAP — https://ad.lacounty.gov/services/older-adult-services/tlap/ (2026)
- Bet Tzedek, Justice for Seniors — https://bettzedek.org/our-services/justice-for-seniors/ (2026)
- LA County DCBA, "Leaving a Legacy" — https://dcba.lacounty.gov/newsroom/leaving-a-legacy-plan-today-for-a-better-tomorrow/ (2023)
- San Diego County Bar, Wills for Heroes — https://www.sdcba.org/willsforheroes (2026)
- California Statutory Will (Prob. Code §6240), LA Law Library — https://www.lalawlibrary.org/pdfs/resource_lists/StatutoryWill.pdf ; Sacramento County Public Law Library form — https://saclaw.org/wp-content/uploads/2023/04/6240-Statutory-will-form.pdf
- California Attorney General, consumer alert on notario fraud — https://oag.ca.gov/news/press-releases/attorney-general-bonta-issues-consumer-alert-notario-fraud-obtaining-immigration (2025-06-27)
- California Court & Forensic Translators/Interpreters, "Translation of Wills for Courts in California" — https://www.cacfti.org/translation-of-wills-for-courts-in-california/ (search snippet only; non-authoritative)

Surveys on wills, access and devices:
- Caring.com/YouGov, 2025 Wills and Estate Planning Study — https://www.caring.com/resources/wills-survey (2025; 2,500+)
- Caring.com, Estate Planning Gaps by Race and Gender 2025 — https://www.caring.com/resources/race-and-gender-estate-planning (2025)
- Consumer Reports, "Why People of Color Are Less Likely to Have a Will" — https://www.consumerreports.org/money/estate-planning/why-people-of-color-are-less-likely-to-have-a-will-a6742820557/ (survey April 2022; n=2,224)
- AARP Public Policy Institute, "Only Half of Adults 50-Plus Have a Legal Will" — https://www.aarp.org/pri/topics/work-finances-retirement/financial-security-retirement/wealth-transfer-inheritance-wills/ (survey April 2024; n=1,869)
- Trust & Will, 2026 Estate Planning Report (press release) — https://www.prnewswire.com/news-releases/trust--wills-2026-estate-planning-report-56-of-americans-still-have-no-estate-plan-ai-trust-hits-an-all-time-high-302735330.html (2026-04-07; n=5,000; vendor)
- Center for Retirement Research at Boston College, "Blacks and Hispanics Often Lack Wills but Need Them" — https://crr.bc.edu/blacks-and-hispanics-often-lack-wills-but-need-them/ (2023)
- Legal Services Corporation / NORC, The Justice Gap (2022) — https://justicegap.lsc.gov/ (~5,000)
- Pew Research Center, Americans' Use of Mobile Technology and Home Broadband — https://www.pewresearch.org/internet/2024/01/31/americans-use-of-mobile-technology-and-home-broadband/ (2024)
- Pew Research Center, Latinos' Views of and Experiences With the Spanish Language — https://www.pewresearch.org/race-and-ethnicity/2023/09/20/latinos-views-of-and-experiences-with-the-spanish-language/ (2023; 3,029 Hispanic adults; definitions only used)
- NCES, Highlights of the 2023 U.S. PIAAC Results — https://nces.ed.gov/surveys/piaac/2023/national_results.asp (2024/2026 page)

Learning, engagement and design:
- Duolingo Blog: Loh, "How Streaks keep Duolingo learners committed…" (2017) — https://blog.duolingo.com/how-streaks-keep-duolingo-learners-committed-to-their-language-goals/ **[older]**; Yu, "Improving the streak" (2020) — https://blog.duolingo.com/improving-the-streak/ ; Mansur, "The habit-building research behind your Duolingo streak" (2022) — https://blog.duolingo.com/how-duolingo-streak-builds-habit/
- Aulagnon, Cristia, Cueto & Malamud, "Streaks to Success?" NBER WP 34173 (2025) — https://www.nber.org/papers/w34173
- Silverman & Barasch, "On or Off Track: How (Broken) Streaks Affect Consumer Decisions," *J. Consumer Research* 49(6) (2023) — https://doi.org/10.1093/jcr/ucac029 (author version: https://udspace.udel.edu/items/42ce576b-8e1f-429a-8541-e29e48dbcfbb)
- Sharif & Shu, "Nudging persistence after failure through emergency reserves," *OBHDP* (2021) — https://www.sciencedirect.com/science/article/abs/pii/S0749597818304187 (abstract snippet only)
- Sailer & Homner, "The Gamification of Learning: a Meta-analysis," *Educ. Psych. Review* (2020) — https://eric.ed.gov/?id=EJ1245270
- Almeida et al., "Negative effects of gamification in education software: Systematic mapping," *Information and Software Technology* (2023) — https://www.sciencedirect.com/science/article/abs/pii/S0950584922002518 (abstract snippet only)
- De Gagne et al., "Microlearning in Health Professions Education: Scoping Review," *JMIR Med Educ* (2019) — https://doi.org/10.2196/13997
- Adesope, Trevisan & Sundararajan, "Rethinking the Use of Tests," *Rev. Educ. Research* 87(3) (2017) — https://eric.ed.gov/?id=EJ1141817 **[older]**
- FTC Staff Report, *Bringing Dark Patterns to Light* (Sept 2022) — https://www.ftc.gov/system/files/ftc_gov/pdf/P214800+Dark+Patterns+Report+9.14.2022+-+FINAL.pdf
- California Privacy Protection Agency, Enforcement Advisory 2024-02 — https://cppa.ca.gov/pdf/enfadvisory202402.pdf (2024)
- Eighth Circuit vacatur of FTC click-to-cancel rule — WilmerHale client alert https://www.wilmerhale.com/en/insights/client-alerts/20250801-eighth-circuit-vacates-the-ftcs-click-to-cancel-rule-but-federal-and-state-regulators-likely-to-remain-active (2025) **[second-hand]**
- Mindlin, "Is Plain Language Better? A Comparative Readability Study of Plain Language Court Forms" (Transcend, undated) — https://www.transcend.net/library/legalCourts/PLStudy.pdf **[older]**

Financial education:
- Kaiser, Lusardi, Menkhoff & Urban, *J. Financial Economics* 145(2) (2022) — https://doi.org/10.1016/j.jfineco.2021.09.022
- Blanco, Duru & Mangione, "A Community-Based Randomized Controlled Trial of an Educational Intervention to Promote Retirement Saving Among Hispanics," *J. Family and Economic Issues* (2020) — https://doi.org/10.1007/s10834-019-09657-9
- GFLEC/TIAA Institute, Financial Literacy among U.S. Hispanics (P-Fin) — https://gflec.org/initiatives/p-fin-index-and-hispanic-financial-literacy/ (survey 2016) **[older]**

Advance care planning and patient education:
- Sudore et al., "Engaging Diverse English- and Spanish-Speaking Older Adults in Advance Care Planning: The PREPARE RCT," *JAMA Intern Med* (2018) — https://doi.org/10.1001/jamainternmed.2018.4657 **[older]**
- PCORI, "Preparing Spanish-Speaking Older Adults for Advance Care Planning … The PREPARE Trial" — https://www.pcori.org/research-results/2013/preparing-spanish-speaking-older-adults-advance-care-planning-and-medical-decision-making-prepare-trial
- Stacey et al., "Decision aids for people facing health treatment or screening decisions," *Cochrane Database Syst Rev* (2024) — https://doi.org/10.1002/14651858.CD001431.pub6
- AHRQ Digital Healthcare Research, Patient-Centered Virtual Multimedia Interactive Informed Consent (VIC) — https://digital.ahrq.gov/ahrq-funded-projects/patient-centered-virtual-multimedia-interactive-informed-consent-vic

Court self-help evidence:
- Judicial Council of California, *Impact of Self-Help Center Expansion in California Courts* (Jan 2021) — https://courts.ca.gov/sites/default/files/courts/default/2024-12/lr-2021-self-help-centers-funding-analysis-ba-2018-gov-code-9795.pdf
- Judicial Council of California, self-help cost-benefit narrative supplement (June 2022) — https://courts.ca.gov/system/files/2026-03/lr-2022-narrative-self-help-supplement.pdf
- NLADA, "Key Studies and Data About How Legal Aid Supports Assisted Self-Help Approaches" (2021) — https://legalaidresources.org/wp-content/uploads/2021/04/assisted-self-help.pdf (summarizes older reports) **[second-hand]**

AI disclosure, trust and accuracy:
- Luo, Tong, Fang & Qu, "Machines vs. Humans: The Impact of AI Chatbot Disclosure on Customer Purchases," *Marketing Science* 38(6) (2019) — https://doi.org/10.1287/mksc.2019.1192
- Pew Research Center, "Americans want transparency when AI is used in their healthcare" (2026-08-25; n=3,488) — https://www.pewresearch.org/short-reads/2026/08/25/americans-want-transparency-when-ai-is-used-in-their-healthcare/
- KFF Tracking Poll on Health Information and Trust: Use of AI (2026-03-25; n=1,343) — https://www.kff.org/public-opinion/kff-tracking-poll-on-health-information-and-trust-use-of-ai-for-health-information-and-advice/
- Rev, "Survey: 65% Use AI Legal Advice…" (2026-01-28; n=1,002, unweighted; vendor) — https://www.rev.com/blog/ai-legal-advice-index
- Stanford HAI, "Hallucinating Law" (2024-01-11) — https://hai.stanford.edu/news/hallucinating-law-legal-mistakes-large-language-models-are-pervasive
- Chen, Rao, Pugh, Lu & Johnson, "Multilingual evaluation of a large language model-based primary care chatbot," *JAMIA Open* (2026) — https://doi.org/10.1093/jamiaopen/ooag207
- National Center for State Courts, *Machine Translation: Considerations and Cautions for Courts* (2025) — https://www.ncsc.org/sites/default/files/media/document/NCSC%20Machine%20Translation%20Guide_0.pdf
- Cal. Bus. & Prof. Code §17941 (FindLaw, current as of 2026-01-01) — https://codes.findlaw.com/ca/business-and-professions-code/bpc-sect-17941/
- SB 243 (2025), Companion chatbots — https://calmatters.digitaldemocracy.org/bills/ca_202520260sb243
- Medical Board of California, GenAI Notification Requirements (AB 3030) — https://www.mbc.ca.gov/Resources/Medical-Resources/GenAI-Notification.aspx
- State Bar of California, *Practical Guidance for the Use of Generative AI in the Practice of Law* (2026 revision) — https://www.calbar.ca.gov/Portals/0/documents/ethics/Generative-AI-Practical-Guidance.pdf

### Limits of this research
- I did not read the full text of the Sailer, Sharif & Shu, or Almeida papers; only their abstracts.
- Review platforms were read on one day and only the first page of reviews. I did not sample them systematically.
- I found no RCT or controlled study of *legal* client pre-education that measured attorney time. The time conclusions rest on medical analogues and court cost-benefit estimates.
- Search results suggested a 2026 "State of Hispanic Wealth Report" (trust ownership among Latinos rising), but I did not reach the report itself, so I did not use it.
