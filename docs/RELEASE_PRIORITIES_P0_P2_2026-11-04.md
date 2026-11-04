# RoleHint — P0–P2 executable priority register

**Baseline: 4 November 2026.** This is the current execution index for both the core job-search journey and the Evidence Inbox. It supersedes the *ordering and status assumptions* in the dated 21 October UX audit, but **does not replace** the approved [product experience](PRODUCT_EXPERIENCE_V1.md), [matching](CV_JOB_MATCHING_SPEC_V1.md), [ten-opportunity/paid entitlement](VACANCY_RESULTS_AND_ENTITLEMENTS_V1.md), [200-case matrix](UX_EDGE_CASE_MATRIX_2026-10-21.md), or [release test matrix](RELEASE_TEST_MATRIX.md).

## 1. Fix the prioritization model

The 200-case matrix has **133 P0, 64 P1, 3 P2** test scenarios. That is test coverage, **not** 200 independently prioritized implementation tickets, and it is not evidence that 133 bugs are still open. Repeated scenarios frequently exercise a single invariant. A case is not marked PASS because its related file exists or a feature branch has CI.

**P0 — release blocker for the affected capability:** privacy/authorization, false job or application outcomes, wrong quota/payment, untruthful source/evidence, unrecoverable data loss, unavailable entry path, and the complete user journey needed to use that capability. No release of that capability with open P0. Apply this rule separately to (A) anonymous preview, (B) private Evidence Inbox, (C) end-to-end free job application, (D) paid subscription, rather than making every paid-only condition block an anonymous preview.

**P1 — high-friction but recoverable:** nonessential path failure, confusing workflow, incomplete discovery context, robust pagination/identity reconciliation, and accessibility bugs with a usable validated alternative. A P1 can ship only with an explicit workaround, owner-approved limitation and a follow-up test. If P1 creates irreversible loss or unsafe decisions it is *promoted to P0* for that release.

**P2 — low-risk refinement:** nonessential microcopy, animation, optional categorization and visual polish. Never use P2 to defer privacy, keyboard access to primary actions, or misleading job eligibility.

**Tracking statuses** (independent of priority):
- **PLANNED** — spec and executable test criteria, no implementation confirmed.
- **CODED** — repository implementation exists; real behavior not yet demonstrated.
- **CI VERIFIED** — automated tests pass on a named commit; fixtures are not live customers.
- **STAGING VERIFIED** — exact deployed SHA and specific live read/browser behavior confirmed; no implication of full E2E.
- **BLOCKED** — required integration, real-device, operational test or owner decision missing.
- **ACCEPTED** — complete scoped E2E + negative tests + privacy/device/recovery evidence + founder approval. **None of the complete public release paths is accepted.**

For one item, specify *both* the strongest verified stage and the outstanding gate (e.g., “staging UI verified; real account E2E blocked”), rather than a single misleading green status.

## 2. Evidence reconciliation — avoid redoing fixed issues

- **Observed current staging**: <https://rolehint-staging-production.up.railway.app/webapp/evidence.html>, Railway deployment \`96b6c910-3ab8-468c-a311-d1d9b492c15c\`, Git commit \`df4758a856bc08fc0b1153ec2952ba2efc429d5d\`. Backend CI <https://github.com/dokarpov/rolehint/actions/runs/41799952520> and Chromium/WebKit browser CI <https://github.com/dokarpov/rolehint/actions/runs/41799952485> passed. **Evidence Inbox step disclosure and compact review are staging-verified for the fixture scenarios**, not real-user accepted.
- Both RoleHint services share a Railway environment name, but have distinct **service IDs, source SHAs and mounted SQLite volumes**. Current production is unchanged. Do not confuse the staging service with an independent environment.
- **Verified closed at *code/UX staging* level:** the three initial UX P0 defects (all-fields-at-once, premature unavailable sign-in wall, prominent connector setup), most optional-field/empty-state/card-friction P1s, and progressive-flow regression coverage. These are not reopened merely because broader authentication is blocked. See the [4 Nov UX review](product/EVIDENCE_UX_REVIEW_2026-11-04.md).
- **Still blocked:** no \`CFA_SMTP_HOST\`/test sender in staging service variables and live \`email_login_available=false\`; real email sign-in, Claude/eligible ChatGPT OAuth consent, actual iPhone Safari, real database restore, and the end-to-end CV→job→application path have **not** passed.
- **Outdated audit corrected:** the 21 Oct UX audit's “CV sent via GET” finding must be re-evaluated, not blindly carried forward. Current \`webapp/index.html\` uses \`POST /web-api/anonymous/matches\` with JSON and clears \`cvContext\` on discard. **Remaining risk:** this still sends derived CV excerpts in the request body and browser memory; anonymous privacy, TTL, request logging, source trace and complete discard behavior need their own negative/E2E checks. Switching GET→POST does not by itself satisfy privacy.
- **Backend presence ≠ production acceptance:** SQLite FTS, OAuth/PKCE, ATS adapters, an authenticated web app and existing automated tests are real implementations. Do not label PostgreSQL/pgvector, paid unlimited, verified ten-opportunity deliveries, working SMTP or independently accepted employer submissions as complete without specific evidence.

## 3. P0 — mandatory vertical-slice work packages, ordered

| Order / ID | Release scope · owner tracker | Current evidence and remaining defect | Exit tests / proof |
|---|---|---|---|
| **P0-01 Identity & session continuity** | Evidence/private + core · [DAR-33](https://linear.app/dokarpov/issue/DAR-33/i1-real-telegram-otp-and-recoverable-browser-session-e2e), [DAR-86](https://linear.app/dokarpov/issue/DAR-86/evc-12-rolehint-evidence-inbox-secure-remote-mcp-for-claude-and) | Email routes and OAuth exist; staging SMTP **not configured**, no real login/restore acceptance. Telegram option cannot be counted as operational without delivery proof. | Dedicated test sender, received magic link/OTP, expiry/replay/logout/clock skew, same-user browser→iPhone continuity, 2-account isolation, failure/recovery. Never log secrets; no account wall before anonymous value. |
| **P0-02 Identity error-state and data protection** | Evidence/private + core · DAR-33, DAR-86, [DAR-38](https://linear.app/dokarpov/issue/DAR-38/i6-independent-production-private-test-acceptance-with-rollback-proof) | Progressive guest/offline UI staging-verified. Authenticated \`/me\` network/5xx failure paths still need explicit separation from genuine 401; no reason to claim session loss on network error. Staging volume exists, real restore and deletion graph not verified. | Auth 401/403/429/500/offline fixtures; preserve unsaved input; signed-out only on verified 401, never silently erase content. Two-user access, SQLite integrity/restart/backup→restore, CV/evidence/FTS/dependent pack deletion, safe logs and negative upload tests. |
| **P0-03 Anonymous first value, CV fidelity & role confirmation** | Free preview · [DAR-34](https://linear.app/dokarpov/issue/DAR-34/i2-structured-cv-claim-editing-confirmation-and-invalidation), [DAR-39](https://linear.app/dokarpov/issue/DAR-39/i7-verify-anonymous-cv-value-10-valid-job-allowance-and-tailored) | Anonymous POST analysis and role/ATS preview code exist; proof/ownership, structured editing and complete real-device journey are not accepted. | On iPhone + desktop: upload PDF/DOCX/TXT **or** enter target role → correct/confirm evidence/role → *real* usable first result without login; 2 careers, scanned/invalid CV, non-English, metric ownership, cancel/discard during request, anonymous expiry and account transfer. No fabricated conclusions. |
| **P0-04 Live vacancy validity, eligibility and dedupe** | Free preview + job application · [DAR-35](https://linear.app/dokarpov/issue/DAR-35/i3-live-ats-freshness-contractor-eligibility-and-canonical-history) | ATS integration and limited source preview exist; \`anonymous/matches\` still labels eligibility unverified. Matching specs remain largely target. | Canonical employer ATS ID+URL; source open/closed/expired recheck, partial/outage/zero states, geo/remote/authorization/B2B **allow, deny, unknown** with evidence; prevent hard-ineligible delivery; 25-job expert fixture incl. geo/B2B negatives + independently opened live links. |
| **P0-05 Atomic free-ten and paid-unlimited invariant** | Authenticated job delivery · DAR-39 | SQLite/delivery tests partially exist, but exact browser+worker integration, paid pagination and durable qualifying-delivery semantics are not accepted. | Concurrent tabs/devices + retries and response loss: only 10 distinct **qualifying delivered** jobs consume free allowance; stale/duplicate/blocked jobs debit zero; paid account sees uncapped cursor results. No billing or charge without separate checkout gate. |
| **P0-06 Honest evidence ownership and AI connector authorization** | Private Evidence Inbox · DAR-86 | Transactional candidate, FTS deletion, OAuth PKCE and simulated MCP lifecycle **CI verified**; UI staged. Real Claude/ChatGPT account connection and approval path blocked on login. | Selected source → user consent → scoped OAuth → propose private/unverified → owner edits/accepts/rejects → FTS retrieval/revoke/delete; prompt-injection source, two accounts, token replay/expiry, read vs propose scope, restart/restore, real eligible host connection. Approval is not independent verification. |
| **P0-07 Credible application package & truthful handoff** | Free end-to-end · [DAR-36](https://linear.app/dokarpov/issue/DAR-36/i4-review-evidence-based-application-pack-and-truthful-exports), [DAR-37](https://linear.app/dokarpov/issue/DAR-37/i5-persist-handoff-versus-confirmed-application-and-employer-response) | Review/history/backend exist; honest job-tailored PDF/DOCX, complete form coverage and final submission tracking are **not accepted**. | Approved claim/source diff, job-specific CV PDF+DOCX, letter and draft screening answers; user approves before export. Handoff != submitted. Popup denied, CAPTCHA, expired form, network error, repeated click, duplicate vacancy, self-confirmed submission and recoverable outcome history tested. |
| **P0-08 Independent operational E2E and release sign-off** | Any public/private promise · [DAR-6](https://linear.app/dokarpov/issue/DAR-6/verify-the-real-cv-eligible-ats-vacancy-approved-handoff-journey), DAR-38 | CI, UI fixtures and healthy Railway stage **do not** constitute the real flow. Production has a separate earlier deployment; no approval to promote draft PR. | Signed-in and guest journeys on **physical iPhone Safari** + desktop; two accounts, varied CVs and live sources, credential failures, deletion/recovery, observability and rollback rehearsal; exact commit/build/test/volume evidence, P0=0 within scope, founder GO before production. |

**P0 sequencing:** do P0-01 + P0-02 first for an Evidence Inbox private pilot; P0-03 and P0-04 can run in parallel for anonymous first value; P0-05 follows verified job delivery; P0-06 follows real identity; P0-07 follows approved evidence and real vacancies; P0-08 closes each applicable release scope. The *paid billing* P0 gate is separate and must remain disabled until checkout/webhook/cancellation tests pass.

## 4. P1 — high-value improvements with explicit acceptance

| ID | User-visible objective / tracker | Current state · concrete acceptance |
|---|---|---|
| **P1-01 Account and guest continuity** | DAR-33 / DAR-34 · After anonymous review, sign in **once** and resume the exact role/job/evidence intent. Do not duplicate account identities or silently merge Telegram and email; test cross-device/back/expired links. **OPEN / unaccepted.** |
| **P1-02 Review backlog performance and navigation** | DAR-86 · Evidence API currently returns a bounded list (default 100); long review histories need explicit cursor/load-more or a truthful count, stable filters, focus retention and no hidden approved items. Test 0/1/100/101/1,000, duplicates, deletion while filtered. **OPEN.** |
| **P1-03 Async error/retry quality** | DAR-86 + DAR-33 · Preserve a partly written claim on offline/429/500; distinguish session expiry from server outage; disable double-submit and show whether a retry was saved or duplicated. Automated failure injection + real network interruption. **PARTIALLY CODED.** |
| **P1-04 Evidence detail usefulness** | DAR-86 · Each card should disclose **claim, confidence boundary, exact source, current status and next permitted action** without repetitive text. Handle long source names, sensitive/redacted excerpts, read-only decisions, conflicting claims. **Staging UX verified for basic cards; real user evaluation OPEN.** |
| **P1-05 Results decision interface** | DAR-35 · Progressive hard constraints and visible eligible/blocked/verify labels, fit/gaps by real requirement, time of last source check, filter changes while pending, partial results and retry. Never replace unknown with a fit percentage. **OPEN.** |
| **P1-06 Save/search/alerts vs apply intents** | DAR-35 / DAR-37 · Make Save, Telegram opt-in after useful results, and Apply distinct; avoid broken “get notified” when provider disabled; persist each intent after login. **OPEN.** |
| **P1-07 Source/identity coherence** | DAR-34 / DAR-86 · Corrected CV/source invalidates dependent claims and packs; no stale user evidence, no duplicate accounts; explicitly recover conflicts instead of overwriting edits. **OPEN.** |
| **P1-08 Accessibility and responsive recovery** | DAR-38 · 200% text zoom, keyboard+VoiceOver, accessible announcement, focus after transitions, dark-mode contrast, WebKit and **real** iPhone Safari. Main actions are P0 if inaccessible on supported device. **CI fixture partial; manual OPEN.** |
| **P1-09 Brand and copy consistency** | DAR-38 · Current production green and staging monochrome differ; preserve approved live storefront until review; one Inter/text-only wordmark and status colors for new staged UI; remove duplicate legacy/demo promises from public entry points. **Staging Evidence Inbox improved; cross-surface review OPEN.** |

## 5. P2 — defer until P0 gates close (unless cheap and covered by same slice)

| ID | Exit / no scope expansion |
|---|---|
| **P2-01 Microcopy and density** | Replace repeated technical/legal sentences with concise contextual help; 5-person comprehension test of Source → Claim → Review, no inaccurate verification claims. |
| **P2-02 Polished but nonessential motion** | 320–1440 responsive transitions, reduced motion, no decorative animations that block a task; static fallback. Maps to L10. |
| **P2-03 Optional smart defaults** | Source-kind prefill, optional claim suggestions and category labels; never infer proof, consent or eligibility from a model. |
| **P2-04 Additional history outcomes** | Define withdrawn/ghosted/declined-offer states (K07) and richer stats only when correct submissions and privacy-safe analytics exist. |
| **P2-05 Conditional employment details** | P14: uncertain contract/period data displayed as unknown, without overblocking candidate; escalate to P0 when it would cause wrong hard eligibility. |

## 6. Latest Evidence Inbox UX defect crosswalk (do not reopen shipped presentation work)

| Original 4 Nov UX row | Implementation evidence | Residual acceptance |
|---|---|---|
| P0: source+claim exposed at once | Source → Claim → Review staged, Chromium+WebKit fixture passed | Real device and first-time users |
| P0: sign-in blocks first action | Guest can add source and download portable private draft; sign-in contextual | **Real SMTP / session remains P0-01** |
| P0: connector overload | Advanced connections hidden until authenticated; OAuth server does not silently approve | **Real account host connection remains P0-06** |
| P1: optional source/limits too prominent | Collapsed source details; typed source preserved | Real content with provenance edge cases |
| P1: equal capture/review priority | Focused review only after save; short empty state | 100+ items / cross-device |
| P1: conflicting save/download buttons | Primary action follows auth availability | Error/fallback accessibility |
| P1: repeated long explanatory copy | Compact copy staged | Moderated comprehension test |
| P1: verbose review cards | Status/claim/source first; disclosure for excerpt/actions | Pagination/conflict states |
| P2: regressions missed progressive state | 320–1440 Chromium+WebKit and syntax gate | Real iPhone/VoiceOver |
| P2: generic/repeated status text | Contextual source/save/review messages | Network-failure announcement and focus |

## 7. Linear work packages and current owner-facing order

The four Evidence Inbox subissues are intentionally **specific acceptance work**, not another copy of the 200 test scenarios:

- [DAR-108](https://linear.app/dokarpov/issue/DAR-108) — **P0:** real email/OTP account → OAuth consent → Claude/eligible ChatGPT → evidence review; depends on working staging sender and DAR-33.
- [DAR-109](https://linear.app/dokarpov/issue/DAR-109) — **P0:** actual staging volume restart/restore, cross-user deletion/retention, FTS and token revocation.
- [DAR-110](https://linear.app/dokarpov/issue/DAR-110) — **P1:** lossless 401/5xx/offline session recovery (coded with browser regression, pending CI), 100+ item pagination, actionable error states, physical-device accessibility.
- [DAR-111](https://linear.app/dokarpov/issue/DAR-111) — **P2:** optional advanced source controls, microcopy and visual polish **after** P0 gates.

Existing [DAR-33–39](https://linear.app/dokarpov/issue/DAR-33) and [DAR-6](https://linear.app/dokarpov/issue/DAR-6) remain the owners of the broader core CV/ATS/quota/pack/application work. Their project priority labels need not all be set Urgent: *P0 is a release-blocking invariant for a named capability, not an instruction to pursue every domain simultaneously*. Track readiness evidence on the respective issue; do not create duplicate issues for every edge-case row.

## 7. Execution rhythm and proof, not ticket volume

**Next coherent release slices:**

1. **EVC S1:** configure/test a staging-only identity provider, verify live magic links/OTP and session/error semantics, two users, single source → private review → revoke and operational backup; do not claim account readiness until both live and negative tests pass.
2. **Anonymous S1:** finish CV privacy/role confirmation and real source/eligibility, prove one useful live ATS result from either entry path without login.
3. **Quota S2:** integrate one atomic normalized delivery ledger with authenticated experience and worker; run 10/11 race + paid cursor evidence.
4. **Application S2:** implement/version truthful PDF/DOCX and manual handoff/outcome record; check all cases.
5. **Public gate:** independent mobile/desktop E2E, provenance audit, privacy/deletion, restored volume, rollback and owner decision.

**Per-work-package definition of done:** precise scenario IDs from the 200-case matrix; failing regression first; source diff; CI run + browser viewports; independently observed real-host result where applicable; staging deployed immutable SHA; no change to production; per-case PASS/FAIL/BLOCKED/NOT_RUN with evidence; redacted screenshots/logs; rollback note. Test fixtures do not silently count as real user acceptance.

**Change policy:** no automatic production merge, no new mock vacancies, no fictional fit scores, no blanket “all P0 closed” from code-only tests. The system's health and missing external integrations must be visible and accurately reported.