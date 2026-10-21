# RoleHint — implementation backlog with dependency and acceptance contracts

> **SQL integrity dependency (2026-10-21):** [verified current SQLite architecture and migration policy](architecture/SQL_DATA_INTEGRITY_PLAN_2026-10-21.md) · [48 database cases](architecture/SQL_DATA_INTEGRITY_TEST_MATRIX_2026-10-21.md). Before E06/E08 can qualify as live results, close DB-0/DB-1: durable isolated staging, schema migrations/restore proof, pure matching before persistence, and atomic ten-free lifetime delivered-valid-job ledger with paid SKU-specific bypass. Before E09/E10 public tracking claims, close DB-2: application/event idempotency, cross-process races, FTS and CV-to-pack deletion consistency. PostgreSQL migration is an optional evidenced DB-3, **not** a prerequisite to fix present UI or race bugs.

**2026-10-21** · **Status:** approved directions translated into engineering work proposals, not deployed or tested.

**Inputs:** [full audit](UX_SERVICE_AUDIT_V2_2026-10-21.md), [200-case matrix](UX_EDGE_CASE_MATRIX_2026-10-21.md), PRODUCT_EXPERIENCE_V1, CV_JOB_MATCHING_SPEC_V1, VACANCY_RESULTS_AND_ENTITLEMENTS_V1, DECISION_POLICY, RELEASE_TEST_MATRIX and RELEASE_ROADMAP. Preserve the existing ATS/AutoMatch/pack/history services; do not rewrite working modules to ship an isolated UI prototype.

## First implementation update (2026-10-21)

- **In source on feature branch:** private POST vacancy matching, rejected CV query-string leakage, correct CV discard invalidation, no forced navigation after CV analysis; current-path browser fixtures replacing old UI assumptions.
- **D0 implemented in source:** online SQLite per-file backup and integrity audit; FTS5 CV cleanup and regressions.
- **D1 experimental foundation:** atomic ten-free reservation/ACK SQL ledger and concurrent synthetic tests, **not yet wired into production or staging user-facing discovery**.
- **Operational blocker:** staging service is a separate Railway service but remains in the environment named `production`, has no reported persistent volume and lacks ATS-board/Telegram variables. Exact staged source SHA remains older than GitHub branch. No production webapp/source/data edits or deploys have been made.
- **Remaining mandatory gates:** reliably isolated durable staging, current browser QA execution and results, real ATS source coverage, existing-accounts quota migration, writer/worker integration and real browser E2E. Do not mark D0/D1 complete on the basis of source files alone.

## A. Execution principles

1. **One vertical slice** is an observable full browser action + backend state + error recovery + test evidence; a Figma frame, CSS PR or mock fixture alone does not close a slice.
2. Keep old production webapp unmodified until a full staged release is founder-approved; separately audit landing/pages and align style safely, no staged app promotion.
3. Do not rebrand again: lowercase heavy text-only rolehint, graphite/off-white; existing legacy styles are removed or mapped, not layered over each other. No automatic UI restyle during backend work. Use approved screen baselines.
4. Create/validate isolated staging environment and persistent test storage; no shared live real-CV data or production secrets; track exact SHA.
5. Any scenario P0 in the 200-case matrix is a release blocker for the capability it covers. P1 can ship only with explicit limitation/workaround and owner consent.
6. Product value metrics: qualified real opportunities, useful application preparation, correct state transitions, effort, source precision, zero unsupported claims. “Page renders” and generic CTA clicks aren't activation.

## B. Dependency path

**E00 release/test baseline** + **DB-0 SQLite integrity / staging durability** → **E01 visual system** + **E02 guest privacy/state** → **E03 CV/role progressive entry** → **E04 source truth** → **E05 eligibility & explainable fit** → **DB-1 atomic delivery ledger** → **E06 result and decision UI** → **E07 identity/continuity** → **E08 free/paid entitlements** → **DB-2 application/history integrity** → **E09 truthful application export/handoff** → **E10 history and opt-in automation** → **E11 launch validation**.

E04 can start behind E02; E08's ledger schema can be designed before E06, but its acceptance must use E06's actual delivered-results events. E09's backed application pack depends on E05 evidence provenance, not only the UI editor.

## E00 — Make staging and release QA trustworthy (first action)

**Code / config:** Railway project environment separation, service config+volume, branch/commit pins, backend Docker build, smoke scripts, site/qa-webapp.mjs, site/qa-release.mjs and test matrix.

**Tasks:**
- Inventory staging/prod exact deployed SHA + URL, source board env var names (never values in reports), data volume, login provider state, PWA cache and deep links.
- Confirm staging persists test-account CV/job/search histories through redeploy and is not using production data. Set up isolated environment/volume if absent.
- Replace browser fixture assertions for deleted headings, old CTAs and slideshow with current user-visible flow assertions.
- Capture screen + accessibility baseline at 320/375/390/430/768/1440; record known defects as FAIL, avoid fake PASS.
- Add environment/version badge in debug mode only; release receipts include SHA, date, smoke and rollback.

**Done:** no obsolete assertions; green current-UI fixture suite and honest live-staging failures; test account survives restart; no production mutation. **Covers:** X11–X14, L01–L10.

## E01 — Freeze the design system without feature churn

**Code:** webapp/index.html inline CSS → shared design token file/components; site/design-v2.css and secondary public pages.

**Tasks:** define H1/H2/body/labels, text-only wordmark with no dot, button variants, inputs, CV uploader, tags, status/alerts, cards, disclosure, mobile widths and focus. Remove nested/competing Inter/Manrope and legacy sage declarations; never add a new cascade override to hide old styles. Align all CTA wording with what the actual available functionality does, but keep site separate from webapp route.

**Done:** screenshot pixel/structural comparison approved by founder; WCAG AA; no dark foreground on dark button, no decorative green/purple backgrounds; accessible desktop+iPhone. **Covers:** L01–L10, X07–X09.

## E02 — Guest analysis state, privacy and discard

**Code:** backend/app/web_identity.py anonymous CV endpoint, a temporary analysis store with TTL, webapp state controller. No raw CV to anonymous_jobs.py query.

**API design:** POST /web-api/anonymous/cv-analysis responds with opaque analysis_id, expires_at, parsed warnings, editable evidence + source spans, role suggestions. POST /web-api/anonymous/matches (or unified /matches/search) accepts only analysis_id, role confirmation, explicit constraints and a bounded cursor. Destroy/expire analysis on discard/TTL; reject ownership mismatch and expired token.

**Tasks:** add multipart cap/MIME and CPU timeout, transient data policy and clean errors. Make UI state ID-based, abortable; discard must clear currentCV, cvContext, candidate suggestions, cached jobs, pending async response, analysis ID and exposed DOM, with a server delete. No session/local storage of raw CV.

**Done:** network inspector + server redacted log confirm zero CV text in URLs; discard while upload/search in flight cannot resurrect data or show a delayed result; TTL and concurrent guest test pass. **Covers:** C04–C17, E04–E09, X02–X05.

## E03 — Two equal first-value routes; no irrelevant onboarding

**Code:** staging webapp first screen, CV parser/evidence formatter, role suggestions and minimum constraints.

**Tasks:**
- Role-only: title/autocomplete → confirm meaning if ambiguous → results, no CV fit assessment.
- CV-first: file → editable structured evidence/short meaningful findings → user confirms target role(s) → results. If no useful role, clearly offer role entry.
- Capture geography, remote and acceptable employment model before a high-confidence qualification claim; unknown can remain unresolved and visible. Salary unit/currency only if user supplies a floor.
- Back/cancel/retry preserve correct input. No auth, OAuth, Telegram or payment before first value; do not show a fake “AI analyzed” badge for simple text heuristics.

**Done:** user can reach real-source result/legible partial/zero state via both routes on iPhone/desktop, no auto-jump or forced Product Manager. **Covers:** E01–E10, R01–R10, P01–P15.

## E04 — Single reliable provider ingestion and vacancy identity

**Code:** services/job_search.py, existing ATS adapters, anonymous_jobs.py (deprecate old GET as public interface), web_release.py discover and new normalization/snapshot adapter.

**Tasks:** reusable source connector diagnostics (healthy/partial/rate-limited/failed), normalized fields, exact provider ID and canonical employer+requisition/URL, source status time, dedupe and optional employer URL recheck. Preserve original employer ATS link. Display “source-reported open”, “verified open at <time>”, “unknown” and “closed” as distinct states. Distinguish actual zero from zero due to provider failure. Provide partial candidate set without hiding healthy providers.

**Done:** provider outage and closed-job fixtures pass; each real sample has traceable URL/status, dedupe and repeat ingestion idempotent. Tests cover first 200 vs pagination and source failure. **Covers:** S01–S16, J01–J02.

## E05 — Eligibility, job requirements and evidence assessment

**Code:** services/auto_match/service.py, extract_constraints/evaluate_constraints, services/pack_proposal, user evidence/provenance and ranking model.

**Tasks:** add country/authorization remote tri-state, contractor mode, salary period+currency and explicit hard exclusion by sourced quote. No unsupported default eligibility. Every must-have requirement retains original text excerpt; candidate evidence source claim and ownership status; support/partial/unsupported/unknown labels. Rank with declared weights as initial hypothesis, deterministic tie-break, source freshness, per-employer diversity and no fake fit percentage.

**Important backend transaction correction:** do not call analyze_job(), which currently persists, in prefilter/preview mode; split pure analyze → policy evaluate → persist accepted delivered record with atomic ledger. Reviewing a saved vacancy must not mutate credits or saved searches.

**Done:** 25-job fixture with expert-checked top 10, 0 hard-ineligible, geographic and B2B negatives, source-excerpt traces; real user consenting to CV review approves each of first 10 (or reports fewer). **Covers:** M01–M14, P01–P15, S03/S10.

## E06 — Result-first UI and decisive single-job view

**Code:** webapp jobs-screen, /web-api/matches/search contract and source-aware result cards, details and filter controls.

**Tasks:** consistent card fields, clear eligibility status, role/CV evidence, all unknown constraints, original URL and source freshness, save/verify/skip/apply primary action. Separate results vs detail; progress/partial/verified-zero/outage/expired/invalid cursor. Persist scroll/filter and correct focus/back. No use of fake jobs to achieve 10.

**Done:** staged iPhone and desktop CV→jobs, role→jobs, filter/sort, 4-job supply, outage/retry and source link all work. **Covers:** J01–J13, H01–H02, X07–X10.

## E07 — Identity after value and durable continuity

**Code:** web_identity.py sessions and sign-in, guest analysis opt-in claim, product state user session/history. Preserve existing Telegram identities.

**Tasks:** offer only operational auth methods (private-beta Telegram if verified, non-Telegram for public GA); code invalid/expired/replay states; avoid swallowing 5xx as signout. Explicitly attach ephemeral CV only after consent to authenticated user, keep preview results and intentions without new credit charge, support logout and cross-device. No silent Telegram/email account merge.

**Done:** mobile browser OTP or live email (depending on verified config) + two-device profile/history continuity + wrong-account negative. **Covers:** A01–A14, E10.

## E08 — Ten free lifetime and unlimited subscriber pages

**Code:** product_state/store.py migration, canonical job_deliveries unique(user_id,canonical_id), entitlement SKU adapter; web_release.py quota and result endpoint; stable opaque search cursor.

**Tasks:** atomic transaction counts only first delivery of validated new qualifying ATS record; unverified/closed/duplicate/saved view/rerank/search fail never consume. Existing records always readable. Free 10 total lifetime; active paid subscription has no vacancy-count cap and can access all actually discovered matches with page_size 20/max50 and stable snapshot. Ensure **any** other entitlement (e.g. Telegram Stars) cannot unlock this. Define upgrade/cancel/expiry purely from signed provider status; do not ship Stripe checkout without owner-approved terms.

**Done:** free multiple searches/tabs/devices 10 correct; paid 120+ fixtures in 7+ pages; downgrade preserves history; no results fabricated. **Covers:** Q01–Q12, J03–J08.

## E09 — Credible application documents and manual submission

**Code:** application_packs/, pack_proposal/, /jobs/{id}/pack/export/handoff/submitted and webapp application editor.

**Tasks:** requirement↔candidate evidence provenance, user approval, edit/diff, genuine tailored CV PDF/DOCX and cover letter (if promised by the tier), screening answers with unanswered personal/legal fields, output revision IDs. Separate “save draft”, “download”, “open employer form” and “actually submitted”. Popup-block fallback. Prevent stale content after CV/job changes and duplicate submissions; use authorized test form.

**Done:** independently compare input CV, employer requirements and actual exported files; reject fictitious metrics/authorization, no fake form submit. **Covers:** F01–F13, H01–H10.

## E10 — Return value: history, saved searches and opt-in automation

**Code:** product state search profiles, application_tracking, connected email, Mini App, scheduling and notification permission UI.

**Tasks:** status timeline, deliberate employer alias resolution, opt-in alerts from genuinely new canonical jobs, saved search editing and profile-limit communication, manual record provenance, source/channel effectiveness and actual outcome denominators. Keep optional Google/GitHub evidence connectors and advanced Autopilot as post-value settings, never interrupt basic search.

**Done:** repeat query after previous submission/rejection behaves safely; correct conversions and dedupe after account restart; notifications only on consent. **Covers:** K01–K10, T01–T09, U01–U09.

## E11 — Release, instrumentation and founder go/no-go

**Work:** run 200-case matrix according to release scope and priority; P0 automated API/fixtures + live iPhone Safari and desktop; manual source checks for each first-ten listing; session + privacy + deletion + backup/restore + rollback. Release through immutable SHA with branch protection and owner signoff; don't merge staging just because it appears prettier.

**Must record:** source URL and last verification (redacted where needed), no customer CV PII, exact deployment SHA, regression suite run URL, device/OS screenshots/video, per-case PASS/FAIL/BLOCKED, P0 defects, source outage behavior, explicit founder acceptance. **Covers:** X01–X18 + full journeys.

## C. First sprint: executable tickets in exact order

| Order | Ticket | Artifact or test before coding | Completion gate |
|---|---|---|---|
| 1 | BASE-01 deployed service map and staging persistence | Current live SHAs/config names, no secrets | Isolated, durable staging; rollback URL |
| 2 | QA-01 update stale site and webapp Playwright tests | Failing tests aligned to current headings/states | QA no longer asserts deleted slideshow |
| 3 | DS-01 freeze buttons/type/logo at mobile/desktop | Approved reference images and token snapshot | No green/purple clashes or dark-on-dark CTA |
| 4 | STATE-01 guest state diagram + async cancellation | Failure tests discard during parsing/search | No ghost CV context or result |
| 5 | PRIV-01 remove CV from GET and add ephemeral analysis claim | Network-log and ID expiry tests | No raw CV in URL/logs; TTL honored |
| 6 | FLOW-01 CV and role intake review/correction | Recorded 320/390/desktop scripts | Both routes preserve value without login |
| 7 | SRC-01 provider state and honest first real vacancy | Employer/source fixture + live check | Real URL/open status or truthful outage |
| 8 | MATCH-01 constraints + evidence explanation | 25-job ranking fixture | Hard blockers absent, unknowns visible |
| 9 | RESULT-01 first list/detail iteration | Card/filter/back/retry browser E2E | User can evaluate a legitimate job |
| 10 | ACCOUNT-01 optional save+resume | Auth + 2-account/2-device test | Secure claim, no account loss |
| 11 | ENT-01 quota DB and paid cursor | Free race + paid 120 fixture | No 11th new free, no paid count cap |
| 12 | APPLY-01 credible pack and handoff | Real-read-only ATS + authorized test form | Honest downloadable content and tracking |

**Do not start ticket 7 by inserting fake jobs if live source coverage is insufficient.** Improve configured ATS boards or label partial/zero accurately. Don't change production webapp through any of these tickets until E11 evidence is accepted.

## D. Founder decisions before irreversible launch actions

1. Approve frozen webapp visual reference/screenshots (logo and monochrome direction are already stated, but existing screenshot reference still needs direct comparison).
2. Confirm operational browser login for users who do not use Telegram before GA.
3. Approve price, trial, checkout, cancellation text and which subscription SKU authorizes unlimited; billing currently not live.
4. Approve definition/TTL of anonymous preview separately from free authenticated lifetime allowance.
5. Decide whether a first release promises complete tailored CV PDF/DOCX or limits access as a private prototype until it is built; do not claim that Markdown export satisfies it.
