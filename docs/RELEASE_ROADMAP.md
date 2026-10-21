# RoleHint — iterative implementation roadmap

**Version:** 1.1 · **Updated:** 2026-10-21 · **Owner:** Product/engineering  
**Target:** smallest *complete and reliable* browser release, while preserving the backend, ATS discovery, decision policies and application history already built.  
**Present state:** **BLOCKED** (see [dated audit](RELEASE_BASELINE_2026-10-20.md)); automated CI success is not user E2E acceptance.

## Delivery method

- One **vertical slice** per iteration: build → isolated tests → existing backend regression → desktop/iPhone browser journey → staging/prod smoke → explicit go/no-go. No standalone "UI-only done" claims.
- Complete each milestone by *reducing a user-visible blocker*, not by adding more feature modules.
- Existing services are authoritative. Add thin APIs/adapters, migrations and tests; avoid replacing JobSearchService, AutoMatchService, pack rendering or application-history storage.
- Prioritize data-integrity and privacy defects before inviting users or collecting real CVs.
- Each milestone generates **(a)** a reproducible build, **(b)** test evidence with run IDs and fixtures, **(c)** documented known limitations, **(d)** rollback reference.
- If an upstream dependency fails, **stop** that release gate instead of hiding it behind a fake result.
- **No automatic merge or deployment considered release acceptance.** Release ownership remains with the founder after the evidence-based gate.

## Binding value-first activation gate (2026-10-21)

The first interaction must create meaningful value **before** email, Telegram, account creation, trial, or payment. Anonymous visitor uploads a CV (PDF/DOCX/TXT), sees extracted career evidence and actionable, honest insights, and may preview real ATS opportunities without an identity requirement. Signup is offered to **save and resume** the analysis, not to reveal its first useful result. Trial unlocks repeated application preparation and automation only after free value is demonstrated; payment comes after trial value and explicit terms. Never imply ten delivered jobs or generated CVs until validated. No fictitious vacancy, invented credential, or fabricated fit score.

**Immediate implementation slice:** anonymous upload → ephemeral structured analysis and provenance → visible insight → optional sign-in → user-approved transfer of analysis to account → cross-device restore → real vacancy preview. Privacy: anonymous uploads are not saved to persistent candidate records without explicit consent; enforce upload limits, short-lived processing, and deletion. Keep existing authenticated routes intact. **Exit:** browser E2E on iPhone and desktop, negative/recovery tests, live ATS verification and cost telemetry; no green status from code-only tests.

**Conversion instrumentation:** anonymous CV started/completed, first insight displayed, first valid vacancy preview, signup after insight, restored profile, trial activation, application prepared, paid conversion; measure latency, per-user inference/ATS costs and failure rate. Do not log raw CV or secrets.

**Ordering adjustment:** deliver the anonymous first-value slice alongside I1/I2, before advertising public access; I7 remains the ten-opportunity and ten-tailored-application expansion, not the first time an anonymous user receives value.

**Detailed matching contract:** [CV-to-job matching specification v1](CV_JOB_MATCHING_SPEC_V1.md). Matching and live top-ten acceptance remain blocked until the contract's integration and browser gates pass.

## I3a — anonymous discovery, dual-entry progressive flow (2026-10-21)

**Founder-approved screen sequence:** (1) CV upload **or visible role search with immediate suggestions**, (2) up to ten live vacancies with source URL, eligibility, evidence-backed fit and gaps per job, (3) Telegram opt-in **after** list end to receive new matches. One mobile screen per step; no generic CV-insight screen or login wall before jobs. Show fewer than ten truthfully when supply is limited; show zero-state and retry. Never invent vacancies or claim precise fit without sufficient evidence.

**Technical dependency:** current `/web-api/anonymous/cv-analysis` only extracts CV evidence; it does not search vacancies. Introduce bounded read-only `/web-api/anonymous/jobs` adapter to existing JobSearchService, with role inference/confirmation, query normalization, per-IP rate limits, safe ATS allowlist, URL freshness checks, remote/geography/B2B eligibility tri-state, provenance and no persistent candidate record. Provide an explicit role correction field before discovery. Fit should show supported requirements, unsupported gaps and unknowns; percentages only when calibrated against verified requirements. Anonymous preview is not a quota debit. Telegram opt-in requires a real configured provider; no misleading email fallback.

**Acceptance:** actual 320–430px Safari flow, role autosuggestions (keyboard and touch), CV→jobs and role→jobs, 10-or-fewer real URLs validated, per-job fit/gap expansion, load/zero/error/retry, back navigation, no signup before results, Telegram CTA only at end, security/privacy/cost tests and deployed SHA evidence. **Status: NOT IMPLEMENTED / BLOCKED until tested.**

## Two release thresholds

**Private testable vertical slice (PT):** A new test candidate uses one approved sign-in option, imports a CV, saves and confirms its text, specifies role/remote/country/B2B, receives at least one fresh real vacancy if available, reviews fit, saves an honest application pack, opens the employer form after consent, confirms submission manually and sees the outcome after logging in again. Zero-source outcome must also work. No fictional record or automatic-submit claim.

**Public free-user promise (PL):** All approved CJM requirements in [PRODUCT_EXPERIENCE_V1.md](PRODUCT_EXPERIENCE_V1.md), including CV-first value without premature account friction, a server-enforced allowance of up to ten **valid delivered opportunities**, downloadable job-specific CVs/cover letters/answers and robust recovery/privacy, have passed actual production E2E. **PT is not permission to advertise PL capabilities.**

## Sequence and exit criteria

| Iteration | Gate | Deliverable and smallest change | Required evidence |
|---|---|---|---|
| **I0. Evidence + release baseline** | PT prerequisite | Record actual main/deployment SHA, product routes, schema, existing assets, red flags; keep public access beta-gated. Confirm what current tests really verify. | Baseline docs, CI references, read-only smoke, build/persistence map |
| **I1. Identity + safe resume** | PT blocker | Verify real Telegram OTP (the currently available provider), session lifecycle, cross-device reuse of same account, expiry, replay, logout, access isolation. Hide/defer nonfunctional email option; preserve existing Telegram user/history. Keep verified email magic links optional until sender is configured. | Actual Telegram delivery on iPhone and desktop; negative auth tests; no tokens in logs; persistence after restart |
| **I2. CV-to-evidence continuity** | PT blocker | Use existing PDF/DOCX/TXT parser; introduce editable structured experience/skills/roles/dates/metrics with ownership and source; connect it to existing evidence store. Confirm after corrections; version source; imported text remains self-reported. Ensure deletion invalidates derived evidence and cached packs. | Representative CV fixtures + bad/scanned/large/non-English CV cases; cross-device restore and deletion |
| **I3. Real search + eligibility + history** | PT blocker | One validated job discovery path using existing ATS/search worker, no mock fallback. Hard-screen remote geography, residence/work eligibility, salary currency and B2B/contractor restrictions; expose unknowns. Canonicalize employer/requisition, preserve applied/rejected history, compare source freshness. | Live source URLs inspected; employer aliases & duplicate tests; expired vacancy exclusion; zero/fewer-than-ten, outage and retry |
| **I4. Evidence-first application pack** | PT blocker | Reuse existing proposal/pack. Per-job requirement → claim → source → status; no fabricated metrics or unverifiable statements. Show gaps, editable positioning/cover note and clear approval. Export an accurate pack, explicitly label missing actual tailored-CV support. | Human review of 3 contrasting real jobs; exact provenance; export matches preview; claim modification tests |
| **I5. Explicit application + history** | PT blocker | Preserve separate stages: draft, approved, employer-form handoff, confirmed submitted, employer response/rejected/offer. Open original employer URL, require submission confirmation, prevent idempotency failures and repeated employer recommendations. | One consented real employer-form handoff without submitting test spam; persistence after logout/device change; no false submit event |
| **I6. Operations + production PT acceptance** | PT release gate | Finish cross-user authorization, upload/SSRF/input limits, CSRF, rate limiting, logs redaction, deletion/export, backup+restore drill and mobile a11y; run full production E2E and rollback drill. | Signed runbook in RELEASE_TEST_MATRIX; real test user; production SHA/URLs; 0 P0 issues; owner signoff |
| **I7. Approved public free-value scope** | PL blocker | Create genuinely useful anonymous CV analysis (ephemeral consent/expiry), trustworthy occupation suggestions, atomic ten-opportunity ledger, ATS recheck before delivery, complete **downloadable tailored CV** (PDF/DOCX when implemented), cover letters, vacancy-specific prefilled answers. | End-to-end unpaid first-ten account including retries, no card, no mock jobs; verified truthful download content; retention/deletion |
| **I8. Assisted apply + monetization** | Optional/PL extension | For authorized supported ATS endpoints or browser extension, implement mapping and autofill; split companion fallback only where technically possible; Stripe trial only after price/cancellation/webhooks separately approved. | ATS-per-provider integration tests and consent; explicit submission confirmation; payment tests + founder approval |

### Work order inside each iteration

1. Write a failing acceptance test for the intended user outcome and the likely corner cases.
2. Trace from web control → API → product-state storage → existing service/worker → return state.
3. Implement the **smallest** adapter/schema migration needed (no parallel business logic).
4. Run focused tests, full backend gates, responsive browser QA, and deployed smoke.
5. Test with a real new account/device and real employer ATS source where applicable.
6. Record outcome + residual risks; decide proceed/rollback, and only then move on.

## Explicit dependencies / stop rules

- **I1 before I2–I5 with real candidate data:** no true CV persistence without authenticated identity and isolation.
- **I2 before evidence-dependent I3/I4:** role-only relevance is clearly *provisional*; never treat CV similarity as verified competence.
- **I3 before preparing applications for a job:** no closed, fabricated, hard-ineligible or duplicated vacancy can reach outward-facing pack.
- **I4 before I5:** require candidate review and approval, no unsupported proof.
- **I5 before declaring PT:** opening an ATS website does not mean submission. User-confirmed submission is a distinct event.
- **I6 is the final private-test gate.** A green CI fixture suite alone is insufficient.
- **I7 required before advertising the approved free CV analysis + ten tailored jobs experience.** Do not claim it on the private-beta landing beforehand.
- **I8 automatic form fill and billing are not release shortcuts.** Do not build them merely to mask incomplete core value.

## Implementation tickets (technical owner map)

| ID | Priority | Target component | Acceptance requirement |
|---|---|---|---|
| AUTH-01 | P0 | \`web_identity.py\`, \`telegram_bot/bot.py\` | Real OTP code arrives, binds browser session and resists replay/expiry; same Telegram identity on two devices |
| AUTH-02 | P0 | \`webapp/\`, \`web_identity.py\` | Email CTA absent/disabled until verified SMTP; honest recoverable errors |
| DATA-01 | P0 | \`services/product_state/store.py\`, migrations | SQLite transaction/locking strategy, idempotent account and quota writes; one persisted identity |
| DATA-02 | P0 | CV records/evidence | Structured editable profile with claim source, ownership, dates, confirmations and deletion/version invalidation |
| JOB-01 | P0 | JobSearchService/worker/\`web_release.py\` | Live ATS revalidation, source timestamps, distinguish fresh/unknown/closed |
| JOB-02 | P0 | \`web_release.py\`, preferences | Work authorization, remote geography, B2B model and salary **currency** are separate tri-state gates |
| JOB-03 | P0 | history and canonical employer | Historical company aliases, rejection exclusions, explicit reopen override, no duplicated invitation |
| JOB-04 | P0 | entitlement ledger | Atomic delivered-valid-job debit; max 10 free; no debit on duplicate, blocked, stale, failed or merely scanned jobs |
| PACK-01 | P0 | evidence + application_packs | Per-claim provenance and approval; downloadable truthful tailored CV + letter when supported |
| APPLY-01 | P0 | handoff/history | Distinct approved handoff vs user-confirmed submission; result persisted and rejection tracked |
| SEC-01 | P0 | auth, logging, storage, uploads | Per-user authorization, data retention/delete/export, secure upload, backups/restores, rate limits |
| QA-01 | P0 | GitHub Actions + real browser | E2E fixture and live-user paths, iPhone and desktop, negative states, accessibility and smoke |
| SITE-01 | P1 | \`site/\`, \`webapp/\` | One entry path, no fictional jobs in live signed-in state, only accurate capability claims |
| PAY-01 | Defer | Stripe/webhooks | Only after explicitly approved price/trial and end-to-end validated cancellation lifecycle |

## Acceptance scorecard (do not pre-fill success)

For each iteration record:

\`\`\`text
Iteration:
Commit SHA / environment / deploy ID:
Existing-backend regression: [pass/fail + run URL]
Desktop + iPhone browser E2E: [pass/fail + artifact]
Live ATS open-status + application URL: [pass/fail + source/timestamp]
Authorization, privacy, negative states: [pass/fail]
Persistence after fresh login/device change: [pass/fail]
Remaining P0 / P1 defects:
Rollback commit / restoration method:
Owner release decision: [BLOCKED / PRIVATE TEST / APPROVED PUBLIC]
\`\`\`

## Out of scope before functional acceptance

Cosmetic redesign, pink/purple styling variants, fictional screenshots masquerading as product, new CRM workspaces, compulsory Telegram-only positioning as if it were standalone email auth, unsupported fit scores, unverified company claims, mass cold outreach, public monetization and automatic applications.

**Next executable milestone: I1 — actually complete and test a real first-user web login, session resume and isolation**, then carry that identity through I2 and I3 without creating another mock application.
