# RoleHint — exhaustive UX / service-flow audit v2
**Date:** 2026-10-21 · **Owner:** Product / UX / Engineering · **Status:** evidence-based source audit; not a live usability test or implementation approval.

> Scope: GitHub Pages landing and legacy interactive pages, production webapp, staging anonymous + authenticated webapp, FastAPI web endpoints, ATS/AutoMatch, persisted job/application history, existing Mini App and optional integrations, entitlements, device/accessibility and release workflow. Observations are from repository source, normative specs and Railway deployment/config metadata. No real-user browser session, source health verification, Telegram delivery or production end-to-end acceptance has been demonstrated by this review.

## 1. Exact baselines and evidence strength

- **Production webapp:** Railway rolehint-api-worker, deployment 39f4e2dcdbce6f8e09285ba9192555718e09bc6c on main (2026-10-20). This is the old green webapp.
- **Staging webapp:** Railway rolehint-staging, deployment 4b4cc2ee8d4c4c18651e2fc3e7920b429d522c24 (2026-10-20), branch feature/value-first-onboarding-20261021. Newer GitHub branch documentation commits are **not** deployed to this service.
- Both services currently belong to the Railway environment named **production**, despite the staging service name. Production reports an attached /app/data volume; staging's service configuration did not report a mounted volume. Verify data durability, isolation, config and rollback explicitly; do not treat a service named staging as an isolated Railway environment.
- **Public site:** site/index.html on main is a GitHub Pages surface. Recent landing changes are code commits, not proof of a currently visible Pages release.
- **Evidence levels:** SRC = directly observed in code; SPEC = requirement but not implemented/accepted; CONFIG = connector metadata/deployment; LIVE = observed complete browser transaction; HYP = research/product hypothesis. Current findings below are SRC/CONFIG unless labelled otherwise.
- The web-open attempts for both Railway origins and GitHub Pages were inaccessible from the research environment. No screenshot, visual browser or actual performance evidence is implied.

## 2. Governing contracts and unresolved collisions

1. docs/PRODUCT_EXPERIENCE_V1.md: value before sign-up, real ten-free distinct qualified jobs, privacy, proof-based application, mobile.
2. docs/CV_JOB_MATCHING_SPEC_V1.md: CV provenance, source retrieval and freshness, eligibility, requirements, explanation and top-ten acceptance.
3. docs/VACANCY_RESULTS_AND_ENTITLEMENTS_V1.md: lifetime 10 for free; **unlimited** paid vacancies with cursor pagination; no billing launched.
4. docs/DECISION_POLICY.md: eligibility, evidence, preference and effort must not collapse to one score.
5. docs/RELEASE_ROADMAP.md + RELEASE_TEST_MATRIX.md: vertical slices and release gates.
6. docs/product/ONBOARDING_V2.md: “Autopilot first”, optional Google/GitHub and pace selection. **Conflict:** it expects connected-signal onboarding, while the newly approved web-first flow must work immediately from CV or role, without integrations. Keep this for a separately evaluated returning-user/advanced workflow, not the mandatory first screen.
7. User's latest brand decision: **bold text-only rolehint**, no decorative emblem or dot; neutral high-contrast UI; one visual language, no competing green/purple. This overrides older color intent in PRODUCT_EXPERIENCE_V1. Freeze component snapshots before execution.
8. Early CV feedback vs no generic insight screen: combine as optional inline, editable evidence preview; do not block vacancy discovery behind a low-value insights interstitial.
9. Telegram-only sign-in is acceptable only as an explicitly labelled private-beta limitation; public browser onboarding requires a usable non-Telegram account route. A hidden/unconfigured email form is not a working option.
10. Social-listening findings are not versioned as traceable RoleHint study artifacts in the inspected repository. Preserve user-approved hypotheses, but distinguish observed evidence from assumed competitor/user patterns. Establish a source-of-truth research appendix before changing product positioning.

## 3. Surface inventory and purpose

| Surface / source | Existing responsibility | UX boundary and release rule |
|---|---|---|
| site/index.html and site/design-v2.* | Marketing, illustrative animated product logic, links to /webapp/ | Narrative only, no second interactive fake job demo; one CTA definition; no false live promise |
| site/pricing.html, subscription.html, install.html | Pricing/trial/install explanations | Currently retain older logo/color/CTA and sample-workspace claims. Must align with approved visual system and factual release status |
| site/workspace.html, onboarding.html | Legacy fictional interactive prototypes | Publicly reachable files can confuse users; exclude from navigation/canonical journey, mark clearly illustrative, no collection of private CV |
| Main /webapp/ | Existing authenticated browser workspace | Keep functional data/operations; do not redesign/fork as separate product |
| Staging /webapp/ | Anonymous CV or role → list → optional Telegram/email auth → same authenticated workspace | Candidate release direction but no verified live completion |
| /web-api/anonymous/cv-analysis | Transient file text extraction and basic deterministic “insights” | No server-side analysis ID/TTL continuity yet, no confirmation/edit step, no OCR/paste fallback |
| /web-api/anonymous/jobs | GET role + CV terms, JobSearchService + Remotive, keyword ranking, 10 per request | CV in URL, no employer open recheck, no real hard-constraint preflight, no persistent free ledger |
| /web-api/me, /cv, /preferences, /search | Identity-backed profile, CV, preferences and search profile | Session/error state, structured evidence, cross-device and migration need testing |
| /web-api/discover and /jobs/{id}/review | ATS search, AutoMatch, persistence and review | Currently two different discovery contracts; analysis saves records before all exclusions; browser quotas inaccurate |
| /web-api/jobs/{id}/pack/export/handoff/submitted/outcome | Editable text, Markdown export, manual link handoff and history | Not full tailored CV, no universal autofill/submit; track approval vs handoff vs user-reported submit |
| Mini App, worker, Gmail/GitHub/Google integrations, scheduler | Historical/advanced workflow, linked evidence and outcomes | Regression-protect existing semantics; integrations optional, permissions explicit; don't make connections onboarding blockers |
| Telegram Stars entitlements vs planned Stripe recurring | Existing active entitlement records for other product functions | Never infer unlimited subscription from existence of *any* entitlement; separate SKU/active lifecycle and billing source |

## 4. Actors, jobs-to-be-done, and entry scenarios

**Actors:** anonymous role-only seeker; anonymous CV-first seeker; returning signed-in seeker; Spain/EU remote contractor needing geography/B2B verification; career switcher with transferable experience; recruiter-facing applicant preparing a specific application; multi-device user; source-outage user; free exhausted user; future active/canceled paid subscriber; support/privacy operator.

**JTBD A, find opportunities quickly.** “When I know the role but do not want to register yet, show real relevant openings and why they are worth investigating without demanding profile completion.” Path: landing CTA → role text/suggestions → minimal disqualifying filters → results → source link/decision → optional account. Unknown CV evidence must be explicit.

**JTBD B, understand what my CV supports.** “When I upload an imperfect CV, show what was read, allow corrections, infer candidate roles cautiously, then match to real vacancies.” Path: file privacy consent → validation/progress → structured editable extraction → role confirmation/alternatives → results. Avoid a generic “add metrics” lecture or hidden default role.

**JTBD C, avoid ineligible applications.** Country of residence, right-to-work, contractor-only, relocation and salary *units/currency* must be separated into explicit exclusion, unknown-to-verify, and soft preference. Do not convert “remote” into “remote from Spain”, “Europe” into EU employment permission, or USD hourly into EUR salary silently.

**JTBD D, decide with evidence.** Each result must show employer/role, actual original URL, freshness state, hard eligibility, 2–3 supported evidence links, gaps and unknowns, reason to act, and one primary action. “CV says leadership” is not documented leadership scope; absent CV proof is not a claim of inability.

**JTBD E, prepare a defensible application.** Source requirement → approved candidate evidence → user-editable claims → comparison/diff → truthful CV, cover note and screening answers → export → handoff. Employer form may be on an external origin, block autofill or require login; no universal auto-submit claims.

**JTBD F, avoid repeating applications.** Saved/applied/rejected/skipped status, employer aliases and requisition identity must influence new discovery without hiding meaningful distinct roles. History persists across login, refresh, devices, resyncs and source relisting.

**JTBD G, resume and learn from outcomes.** Save and restore searches, applications and recruiter responses, understand stage transitions, and inspect source/channel conversion and effort without a fake probability or untraceable metric.

## 5. Canonical state machine (do not couple to screen DOM)

Entry: GUEST_IDLE → [ROLE_DRAFT | CV_SELECTED] → [CV_PARSING | ROLE_CONFIRMATION] → CONSTRAINT_CHECK → DISCOVERY_PENDING → [RESULTS_PARTIAL | RESULTS_READY | VERIFIED_EMPTY | SOURCE_ERROR] → JOB_DECISION.

Job: DISCOVERED → [SAVE | VERIFY | SKIP | PREPARE] → PACK_DRAFT → PACK_REVIEWED → HANDOFF_APPROVED → HANDOFF_OPENED → [USER_CONFIRMED_SUBMITTED | NOT_SUBMITTED | UNKNOWN_SUBMISSION] → [AWAITING | RECRUITER | INTERVIEW | REJECTED | OFFER | WITHDRAWN]. Each transition includes ownership, timestamp and origin; UI back navigation must preserve the actual object, not copy a transient DOM card.

Identity: GUEST → SIGNIN_OPTIONAL → CHALLENGE_PENDING → ACCOUNT_SESSION → SESSION_EXPIRED/REAUTH → ACCOUNT_SESSION. Anonymous analysis transfer requires explicit consent and an ID-bound, expiring one-time claim; never copy it automatically to a different authenticated account.

Quota: UNMETERED_ANONYMOUS_PREVIEW (policy separately defined) → FREE_ACCOUNT_0..10_DELIVERIES → FREE_EXHAUSTED; verified paid entitlement → PAID_ACTIVE_UNLIMITED; past_due/canceled/expired → FREE_RULES_WITH_HISTORY. Search events, impressions, already delivered, stale, hard-ineligible, duplicate and failed fetch are **not** qualifying new deliveries.

Search: QUEUED → SOURCE_FETCHING → NORMALIZING → SOURCE_CHECKING → RANKING → SNAPSHOT_AVAILABLE; source may be PARTIAL, ZERO_VERIFIED, 429, 503, TIMEOUT, FAILED_PARSE, CLOSED/UNKNOWN. Page cursors refer to an immutable search snapshot. Results cannot silently disappear on fresh source polling.

## 6. Confirmed defect register and root cause

| ID / priority | Evidence and code | Failure mechanism and user consequence | Corrective contract |
|---|---|---|---|
| UX-001 P0 | Staging webapp/index.html findJobs() | Sends cvContext via GET query string, up to 2,500 chars; URL/log leakage | POST by short-lived analysis ID only |
| UX-002 P0 | webapp anon-discard handler | Clears currentCV/file but not cvContext, lastJobs or inferred role | Discard invalidates in-memory/server analysis, cards and provenance immediately |
| UX-003 P0 | webapp anonymous CV onchange | Suggested role invokes findJobs() immediately; CV results screen hidden before review | Require visible evidence and role confirmation, then search |
| UX-004 P0 | web_identity.py anonymous cv-analysis | Returns loosely atomized text and generic insights; no analysis_id, expires_at or structured confidence | Typed profile with source spans, editing and ephemeral token lifecycle |
| UX-005 P0 | anonymous_jobs.py | Keyword overlap / title aliases only; valid HTTPS check not ATS open/eligibility verification; 10 per request | Canonical live job verification, constraint preflight, meaningful requirement alignment |
| UX-006 P0 | web_release.py discover + AutoMatchService.analyze_job | analyze_job persists *before* /discover excludes DO_NOT_APPLY/ALREADY_APPLIED. Persisted jobs affect user list/quota | Evaluate/exclude before mutation; idempotent accepted-delivery transaction |
| UX-007 P0 | /web-api/me, /release-state, /discover | Count len(product.jobs) capped at 10; not distinct qualifying delivery ledger; paid jobs also sliced to first 10 | User-scoped canonical delivery table and cursor result API; SKU-specific entitlement |
| UX-008 P0 | staging get_service_config | No volumeMounts reported; source/provider/auth variables also not reported by config | Validate persistent storage and full service config; do not claim cross-device or restart state until test |
| UX-009 P0 | browser qa-webapp.mjs / qa-release.mjs | Tests expect older headings/buttons/slideshow removed from current frontend; regressions can fail for wrong reasons or miss actual flow | Replace with versioned staging current-path tests and feature-specific contract/visual tests |
| UX-010 P0 | /web-api/discover and /anonymous/jobs | Divergent live-source allowlists, matching, quota, error and identity guarantees; Remotive accepted anonymously but not authenticated | Single normalized ingest/filter/rank model with two entitlement layers |
| UX-011 P0 | old webapp/ and newer staging | Unapproved production green, staging has inline overrides and old Inter + new Manrope CSS, logo still rolehint. | Freeze approved wordmark/tokens, one source of style and shared accessible primitives |
| UX-012 P0 | webapp refresh() | Any /me failure (401 or 5xx/offline) collapses into signed-out guest; can imply lost session/data | Separate 401, 403, 429, 5xx, offline; don't erase local navigation state on recoverable errors |
| UX-013 P1 | webapp jobs-end | “Get new matches on Telegram” is shown even when zero jobs and provider may be unavailable | Show optional notification only when provider configured and after usable results; contextual empty-state CTA |
| UX-014 P1 | webapp auth-status() | Email option remains in details but disabled if SMTP absent; Telegram-only can be 503 | Offer only operational options; informative private-beta access state |
| UX-015 P1 | webapp results → member | Guest list and anonymous CV analysis aren't directly attached to authenticated account; imported CV requires another explicit upload | Consented transfer, preserve selection, merge by canonical job ID without duplicate charge |
| UX-016 P1 | webapp handoff() | If popup is blocked, UI still says form opened; API records approval even though URL not opened | Detect null popup, provide accessible direct link/copy and accurate handoff state |
| UX-017 P1 | web_release review() | Revisiting a job invokes analyze_job again and writes records/actions; can mutate state while merely reading | Review must not mutate quotas/search, rerank only under explicit refresh with versioning |
| UX-018 P1 | preferences form | Only role, remote, contractor, EUR salary; country/permission/relocation not asked even though engine reads them | Progressive hard-constraint confirmation with persisted source and unknown state |
| UX-019 P1 | entitlement() and web_release | Any active SKU unlocks count bypass, not verified paid-subscription category | Tier entitlement projection by SKU/status/period, verified billing events; no checkout yet |
| UX-020 P1 | site pricing, subscription, install, workspace, onboarding, llms.txt | Old brand and explanatory claims still exist publicly, some reference sample workspaces | One canonical page inventory, copy truth review, redirects/noindex where appropriate, shared style |
| UX-021 P1 | web_identity email vs Telegram accounts | Different account identity IDs; no merge plan; duplicate account risk across providers | Explicit link accounts only with possession proof and migration idempotency |
| UX-022 P1 | product store and CV delete | Delete source CV and evidence, but derived pack fields may persist with prior snippets | Provenance invalidation, redact/remove derivatives and clear user-facing remnants |
| UX-023 P1 | stage after results → auth | “Save CV” vs “Get new matches” routes overlap with incomplete opt-in persistence; backend token transfer absent | Specify distinct Save, Alert, Apply intents and return location |
| UX-024 P1 | site qa-release after landing changes | Assertions target deleted story tabs, pause and clickable example; current landing won't pass this suite | Update smoke checks to automatic motion, pointer response and no duplicate demo; assert production SHA |

**Additional risks to test, not source-confirmed failures:** source 429/captcha/404, payroll B2B ambiguity, stale job redirects, older Safari File API, iOS Telegram return handoff, interrupted uploads, 2-tab race, long non-English CV, PDF encryption, browser storage blocked, secure session behind proxies and third-party cookies.

## 7. Interface structure and progressive disclosure

**Unauthenticated step 1 — Start.** One H1, one concise promise, equal CV/role paths; CV privacy/size in context; role autocomplete accessible. Do not display dashboard, configuration jargon, recruiting integrations or auth before value.

**Step 2 — Confirm minimum facts.** One small review panel for parsed role(s) or role query; ask only unavoidable unknowns (home region, remote mode, contractor policy and salary unit/currency) as progressive inputs. Editable CV evidence is shown as a compact preview with “Correct” affordance, not a generic advice page.

**Step 3 — Results.** Mobile one-column cards and sticky but non-obstructive results summary; best-fit sort and filters; tag confirmed vs unconfirmed status; expand evidence/requirements; source link; action “Review”, not “You qualify”. Free allowance explained by *new qualifying deliveries*, paid pagination after real entitlement, not fake ten from each search.

**Step 4 — Opportunity detail.** Eligibility first, then evidence/unknowns, then next action (save/verify/skip/apply). Only one primary action at each state; keep alternatives secondary; make history clear.

**Step 5 — Application preparation.** Dedicated view, not buried form under result list; trace requirement to source and candidate claim; editor, diff, preview, export format and human confirmation. Submission history cannot be manipulated by opening an external link.

**Step 6 — Return and tracking.** Saved search(s), alerts and applications are a secondary workspace for retained users; explicit filters/status and source/channel outcomes. Integrations and autopilot configurable here, never a prerequisite to the first good result.

## 8. Interaction and style requirements

- Brand: lowercase bold text-only “rolehint”, no symbol or decorative dot, one logo component used everywhere; must not be overridden per page.
- Neutral graphite/white palette. Green/amber/red reserved solely for states with text equivalents; no purple/green combined theme. Foreground contrast at least WCAG AA. No black text on dark background buttons.
- One font family with weight scale; no two style tags applying competing tokens. Semantic sizes, spacing, border, form, field, tab, disclosure, status, card and modal primitives; reset legacy styles rather than layering overrides.
- 320, 375, 390, 430, 768 and 1280/1440px, 200%/400% zoom, keyboard, VoiceOver, touch target >=44px, browser back, focus recovery, reduced motion, loading/empty/error transitions and no horizontal overflow.
- Buttons are not proof of functionality. Every CTA must reach a defined state or be hidden; disable unavailable integrations with precise explanation.
- Show stable skeleton/loading stage and realistic source-status progress, not indefinite spinner or fabricated vacancy count.
- Don't store sensitive CV in localStorage/sessionStorage, address bar, analytics, logs, or a cross-account context. Never claim data deleted before revoking/expiring derivatives.

## 9. Implementation order with hard vertical-slice gates

| Slice | Scope | Testable end-to-end exit | Explicit non-goal |
|---|---|---|---|
| M0 — source baseline + harness | Current deployed SHA, source / spec drift, test rewrite, screenshots; staging data config, rollback | A test executes on actual deployed staging at 320/390/1440; annotated failure map and approved visual snapshot | No production code merge |
| M1 — state/privacy foundations | Typed guest state, POST transient analysis ID + TTL, discard, correction, role confirmation, request cancel | CV, invalid CV, role-only, discard, slow/offline, reload have correct states and no CV in GET/logs | No paid checkout |
| M2 — source and honest top ten | Shared ATS retrieval, provider health, URL/closed checks, canonical identity, geography+B2B/salary tri-state, 25-job ranking fixture | Founder-reviewed real source 1..10 (or honest fewer); valid employer URLs and evidence per requirement, deterministic ranking | No invented 10 jobs |
| M3 — real result UI and history | Job card/detail, filters/sort, signed-in transfer, exclude/history, save/skip/verify, empty/partial/error, pagination service | Role and CV journeys work on staging iPhone/desktop; no duplicate, wrong exclusion, or lost state | No cosmetic dashboard sprawl |
| M4 — ledger and active-paid architecture | Atomic free 10 lifetime, snapshot cursor, paid 120+ fixture pages, canceled/expired rules | 2-tab/2-device free concurrency, paid all pages, no stale/duplicate charge; source data truthful | Stripe live charge not authorized |
| M5 — application and tracking | Editable evidence, source-backed tailored CV/letter/answers/export, handoff, manual confirm, status transitions, channel attribution | Real vacancy read-only + authorized test form; export diff truthful; duplicate prevented; history persists | No fake ATS auto-submit |
| M6 — operational release | Non-Telegram browser login, privacy/export/delete/backup, alerts, Mini App regression, live device E2E, ops/rollbacks | 0 P0, launch evidence, founder approval, production SHA match, rehearsed rollback | No automatic public launch |

**Per-slice discipline:** confirm contract → write failing regression tests → minimal code/migration → isolated fixtures + security tests → deploy staging by SHA → real desktop/iPhone Safari test on that SHA → screenshot/state comparison → defect closure → founder approve next slice. No “done” based on build logs alone.

## 10. Metrics, validation and research proof

**North-star:** user-confirmed useful applications per hour of total user effort, with no hard-disqualified or unsupported-claim leakage. Report actual submitted/handoff separately.

Instrument privacy-safe events: first input displayed, CV chosen/uploaded/extracted/corrected/discarded, target role confirmed, constraints supplied, first qualified vacancy rendered, source error, result review, eligibility checked, apply/verify/skip, saved resume, auth success/failure, pack review/export, actual manual handoff, user-reported submission, observed recruiter/interview/rejection, paid activation when authorized. Redact CV, email, tokens, original sensitive source excerpts in analytics.

**Research gaps:** current repository contains PRODUCT_EXPERIENCE and VALIDATION hypotheses, but inspected files do not establish source-backed 2024–2026 job-seeker social-listening insights, interview artifacts or segment behavior. Required qualitative study: first-value comprehension, trust in eligibility, CV privacy, uncertainty messaging, effort, comparison against job boards, and the actual conversion barrier. Run moderated task testing for role-only, CV-first, returning, career-switcher, Spain-based B2B applicant and free-exhausted. Do not convert an unverified hypothesis into a shipped promise.

## 10A. Database integrity is a prerequisite, not a replacement UX track (2026-10-21)

The technical source audit confirms an applied SQLite relational product, **not** an implemented PostgreSQL/pgvector production stack. The relevant live application uses `ProductStore`, `EvidenceStore`, search subscription and career SQLite connections; source-backed FTS5/BM25 exists. Some authentication consumes are protected by `BEGIN IMMEDIATE`, while free-10 entitlement and discovery persist across separate operations and are not demonstrated race-safe. `check_same_thread=False` and a persistent Railway production volume do not prove transaction isolation or recoverability. See [SQL integrity source audit and staged architecture](architecture/SQL_DATA_INTEGRITY_PLAN_2026-10-21.md) and [48 SQL fault-injection tests](architecture/SQL_DATA_INTEGRITY_TEST_MATRIX_2026-10-21.md).

**Consequences for this UX audit:** DB-0 staging durability + migration/restore proof precede live cross-device acceptance; DB-1 atomic valid deliveries precedes free ten and paid results acceptance; DB-2 idempotent application/outcome/evidence handling precedes submission/tracking promises. PostgreSQL/pgvector migration remains optional until current SQLite correctness and measured workload establish a need. Do not re-create working SQL features to make a more impressive tech stack claim.

## 11. Release decision and ownership

- **Now:** staging architecture/UX iteration only; production /webapp stays on old tested release even if visual style is unpleasant; no promotion until full end-to-end is signed off.
- **M0 blocker:** staging lacks confirmed durable volume/config, tests target obsolete UI and source build is ahead of deployed SHA. Fix environment + test evidence first.
- **Non-negotiable founder signoffs:** visual snapshot/components, value-first flow, what counts as qualifying delivery, trial/payment terms, live launch.
- **Known limitation:** this report is a static/source audit. It should be followed by recorded usability sessions and live-source / provider tests, with outcome statuses PASS / FAIL / BLOCKED / UNTESTED, not asserted as already done.

See UX_EDGE_CASE_MATRIX_2026-10-21.md for scenario-by-scenario acceptance cases and failure injection.
