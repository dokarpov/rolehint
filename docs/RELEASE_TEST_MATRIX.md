# RoleHint — release acceptance and reproducibility matrix

**Updated:** 2026-10-20 · **Status:** living QA contract, **public release blocked**.  
Supporting docs: [roadmap](RELEASE_ROADMAP.md), [baseline](RELEASE_BASELINE_2026-10-20.md), [approved CJM](PRODUCT_EXPERIENCE_V1.md).

## Rules for test evidence

- **Fixture PASS**: component behaves with mocked ATS/user/email data; not proof of production behavior.
- **Live smoke PASS**: deployed page/endpoint reachable and anonymous-access policies enforced; not proof of login.
- **Live E2E PASS**: test candidate completes the exact user-facing step on a deployed SHA, with actual signed-in state and a real traceable employer vacancy, using safe/consented data.
- **External submit PASS**: only if employer confirmation is observable. Otherwise label **approved manual handoff** or **user-reported submission**, not "automatically submitted".
- Never test by spamming a real employer with fake applications; use an authorized test form for submission mechanics and a read-only real employer listing for relevance/handoff verification.
- Record observed date, device/OS/browser, SHA, testcase ID, actual URL, expected/observed behavior, screenshot/video/log location without tokens or CV PII.
- Passing on \`localhost\` or a test fixture never upgrades the corresponding production row to PASS.

## Canonical first-user script

**Environment:** https://rolehint-api-worker-production.up.railway.app/webapp/ (origin must match configured web session). **Marketing entry:** https://dokarpov.github.io/rolehint/site/.  
**Data:** consented synthetic career-profile fixture for automated tests; separate *consented real test-user account* and public employer ATS listing for final live E2E. Never store real CV text in the repo.

1. From the landing page on iPhone (390 px) and desktop (1440 px), follow the primary CTA; URL must lead to the real web app, not the fictional \`workspace.html\`.
2. Choose target profession **or** a CV, independently. Verify neither forces unrelated setup. If the CV was selected before login, explain processing is deferred and allow explicit upload once signed in.
3. Authenticate with actual Telegram OTP (if configured); verify the bot delivers the 8-digit code to the correct Telegram account. Check wrong code, expired challenge, reuse and blocked cross-browser stealing. Email login may be disabled while SMTP is absent.
4. Import PDF/DOCX/TXT; inspect extracted text, edit one fact, save, confirm self-reported status. Sign out/in and confirm the updated same-account data is present on another device.
5. Save remote-only, eligible geography, annual EUR salary floor and B2B/independent-contractor requirement. Reload and verify persistence; deliberately leave one constraint unknown to see the correct warning.
6. Query a real role. Confirm at least one result from a real employer ATS *when available*; verify URL, company, requisition ID, source timestamp/status and active employer page. If zero: show honest empty state and preserve quota; do not invent ten jobs.
7. Inspect one role. Compare source wording to extracted requirements, decision, evidence provenance, B2B eligibility and unknowns. Confirm unsupported CV metrics are not shown as verified.
8. Prepare and save job-specific draft, export existing approved artifact, compare output text to approved evidence. No made-up dates, employers, work authorization, degrees or metrics.
9. Approve and open employer form. Verify the UI marks **handoff**, not submission. Do not submit a fake application to an external employer. For an authorized test form, complete and explicitly confirm successful submission.
10. Mark a rejection (in test data), sign out/in, then repeat search; prior employer must be visibly flagged or excluded, with an explicit override policy. No duplicate submission record.
11. Verify account-isolated histories, CV deletion, safe failure/retry paths, viewport accessibility, deployment version and rollback proof before release signoff.

## Detailed scenario matrix

Legend: \`AUTOMATED\` = existing test(s); \`NEEDED\` = not yet proven / must add. \`LIVE\` = production verification required.

| ID | Scenario and expected result | Existing coverage | Required release proof |
|---|---|---|---|
| E-01 | Marketing CTA always reaches the real authenticated app; no mock jobs shown | \`site/qa-release.mjs\` + read-only smoke | LIVE click-through on iPhone/desktop |
| E-02 | First viewport supports role and CV input; scroll/navigation coherent | \`site/qa-webapp.mjs\` fixture | LIVE mobile + keyboard |
| A-01 | Telegram OTP from correct bot signs in correct existing account | \`tests/test_web_telegram_login.py\` mocked bot | LIVE Telegram delivery + session |
| A-02 | Wrong/expired/reused codes rejected; different browser can't steal session | \`tests/test_web_telegram_login.py\`, \`test_web_identity.py\` | LIVE negative replay and expiry |
| A-03 | Logout revokes session; restart/refresh/new device restores only own data | Auth/persistence tests | LIVE two devices, two users, restart |
| A-04 | Missing SMTP doesn't offer fake email sign-in | \`test_web_identity.py\`; UI fixture | LIVE disabled/error state |
| A-05 | CORS/CSRF, session fixation, brute force and code issuance rate limits | Partial origin + auth tests | NEEDED security negative cases |
| C-01 | CV PDF/DOCX/TXT uploads and extract without exposing text in logs | \`test_web_cv.py\` (TXT, malformed PDF) | LIVE multiple real format fixtures and log review |
| C-02 | Scanned/encrypted/corrupt/huge CV reports recoverable error | Partial size/type tests | NEEDED fixture coverage and paste fallback |
| C-03 | Corrected claims persist; further changes invalidate confirmation/derived references | \`test_web_cv.py\` | LIVE cross-device, stale-pack invalidation |
| C-04 | User confirmation means self-reported, not independently verified | \`test_web_cv.py\` + evidence store | NEEDED source trace / independent proof checks |
| C-05 | Account/user deletes CV and all derivatives, storage/backups comply with retention | CV endpoint deletes some records | NEEDED deletion/export/retention/restore audit |
| P-01 | Save role, remote, hiring country, EUR floor, B2B; refresh retains all | \`test_settings_persistence.py\` + partial web API tests | LIVE account resume / relocation |
| P-02 | Eligibility: hard block vs unresolved vs soft deprioritization distinct | \`test_web_release.py\`, \`DECISION_POLICY.md\` | LIVE source excerpt comparison |
| P-03 | Work authorization and B2B/contractor restrictions explicit, not silently assumed | Partial B2B token matcher | NEEDED multinational and conflicting wording fixtures |
| P-04 | Salary floor compared only with compatible currencies and units | \`test_web_release.py\` | NEEDED EUR/USD/GBP/hourly/missing fixtures |
| J-01 | Real ATS vacancy has employer, requisition ID, original HTTPS URL | \`test_real_job_sources.py\` | LIVE per-source freshness/open-state check |
| J-02 | Closed/expired/duplicate/hard-ineligible vacancies don't use free credits | Worker regression, partial web checks | NEEDED transactional entitlement ledger test |
| J-03 | Exactly ten distinct delivered-valid openings max, across tabs/devices/worker | Worker cap fixture | NEEDED concurrency, race, idempotency, fewer-than-10 |
| J-04 | Live employer source outage returns real error/empty + retry, never invented results | Partial empty state | NEEDED outage/timeout/429/parse-failure tests |
| J-05 | Prior employer rejection, aliases, recent applications suppress/flag reruns | \`test_web_release.py\` exact company | NEEDED company canonicalization + historical email correlation |
| F-01 | Requirements map to source excerpt and candidate evidence status | AutoMatch tests + \`test_web_release.py\` | LIVE real source + trace for each key claim |
| F-02 | Unverified CV claims never appear as 'verified'; no invented fit percentage | Existing pack gate | NEEDED proof-card mutation / output truth test |
| F-03 | Job-specific accurate CV, cover letter and screening answers downloadable | Currently Markdown application pack only | NEEDED tailored CV/letter export and content QA |
| H-01 | User approves draft before employer handoff; page stays in real employer origin | Backend handoff test + browser fixture | LIVE consent and manual handoff UX |
| H-02 | Opening form isn't recorded as submission | \`test_web_release.py\` | LIVE distinction in UI/history |
| H-03 | Successful submission recorded only after confirmation; duplicate idempotent | \`test_web_release.py\` | LIVE authorized test-form flow |
| H-04 | Rejection/interview/offer state persists and informs future matching | \`test_web_release.py\` | LIVE account/device restoration |
| X-01 | No cross-account CV, packs, jobs, or history (IDOR) | Auth tests partial | NEEDED hostile cross-user matrix |
| X-02 | Data storage encrypted/retained appropriately; backup/restore drill works | Mounted SQLite volume seen | NEEDED GDPR/retention, backup restore, operational alert |
| UX-01 | At 320/375/390/768/1440 px no clipped text or horizontal overflow | \`site/qa-webapp.mjs\` fixture | LIVE iPhone Safari and desktop browser |
| UX-02 | WCAG keyboard focus, labels, announcements, meaningful loading/errors | Partial basic checks | NEEDED VoiceOver, keyboard, zoom, reduced motion, contrast |
| D-01 | Deployed SHA known and matches tested code; smoke passes | \`scripts/smoke_live_release.py\` | LIVE production SHA/smoke receipts |
| D-02 | Rollback works without losing application history/PII or quota | No proven restore drill | NEEDED staged rollback and database restore evidence |

## Reproduce existing automated checks

From the repository root (Python 3.12, Node 22, local dependencies installed):

\`\`\`bash
python -m pip install -r backend/requirements.txt pytest
export PYTHONPATH=.:backend
export CFA_PUBLIC_BETA_LOCK=1
export CFA_ALLOW_ANONYMOUS_SELFHOST=0
export CFA_SEED_DEMO=0
export CFA_RUNTIME_MODE=selfhost
export CFA_DATA_DIR=/tmp/rolehint-test-data
export TELEGRAM_BOT_TOKEN=123456:test-only-token
python -m pytest -q \
  tests/test_public_beta.py \
  tests/test_telegram_auth_release.py \
  tests/test_free_discovery_worker.py \
  tests/test_settings_persistence.py \
  tests/test_web_identity.py \
  tests/test_web_cv.py \
  tests/test_web_telegram_login.py \
  tests/test_web_release.py
python -m pytest -q tests/test_real_job_sources.py
npm install --no-save playwright@1.58.2
npx playwright install chromium
node site/qa-webapp.mjs
node site/qa-release.mjs
python scripts/smoke_live_release.py
\`\`\`

**Live ATS test is intentionally network-dependent.** It may fail when employers close listings, block search or source schema changes; investigate rather than adding fake vacancies to make CI green.

## Mandatory SQL integrity additions (2026-10-21)

The source audit confirms SQLite storage, composite keys/upserts and FTS5; it does not establish PostgreSQL/pgvector implementation, quota transaction atomicity, concurrent API+worker safety or backup/restore. The complete new failure-injection matrix is [48 SQL integrity tests](architecture/SQL_DATA_INTEGRITY_TEST_MATRIX_2026-10-21.md). All 48 cases currently start **UNTESTED** until executed; do not mark them green based on backend unit suites or Railway health. In particular, free-credit and application/history P0s are a dependency of real role/CV→delivery→application E2E. First stabilize the existing SQLite data topology, then optionally evaluate PostgreSQL against measured workload and a separate approved migration ADR.

## Known evidence (not complete E2E)

- 2026-10-20: backend PR gate and its deployed smoke stage passed for the integrated web code (see repository Actions history). Browser responsive test passed with intercepted fixture API responses; neither substitutes for the production user test.
- 2026-10-20: Railway reported deployment SUCCESS for commit \`39f4e2dcdbce6f8e09285ba9192555718e09bc6c\`.
- **Actual Telegram OTP delivery + persisted CV + real personalized ATS vacancy + user-approved application handoff + subsequent account restore in one production browser journey:** **NOT YET VERIFIED**.
- Product outcome proof and public free-ten/full-tailored CV acceptance: **NOT YET VERIFIED**.

## Final release signoff template

\`\`\`text
Date/time (local + UTC):
Target environment / URL / exact SHA:
Release owner:
1. Backend full CI URL and conclusion:
2. Browser mobile & desktop artifacts and conclusion:
3. Live OTP session evidence (redacted):
4. Consent-based CV parse/correction & cross-device evidence (redacted):
5. ATS employer record + freshness verified at:
6. Eligibility & B2B source excerpt:
7. Approved application artifact and manual/automated status:
8. Job/outcome history persistence:
9. Security + privacy + restore evidence:
10. P0 open / P1 open / mitigations:
Rollback deployment SHA + tested steps:
Decision: BLOCKED | PRIVATE TEST | PUBLIC APPROVED
\`\`\`

**Do not stamp PUBLIC APPROVED until every public-promise gate is passed.**

## Mandatory mobile-first UX gate (2026-10-21)

**Scope:** public site, anonymous onboarding, authenticated workspace, all dialogs, errors, empty/loading/success states. A feature is NOT accepted when backend works but the mobile experience fails.

**Evidence-led references:** Simplify iOS uses one actionable vacancy card at a time with progressive details; Simplify's CV import extracts an editable profile; Huntr separates compact tracking and deeper detail. Borrow interaction principles, not styling, screenshots, or unverified performance claims.

**Hard acceptance criteria (all required):**
1. At 320, 375, 390 and 430 CSS px and desktop 1280 px: no horizontal scroll, overlapping labels, clipped buttons, or obscured content. Test actual iPhone Safari, not screenshots alone.
2. Initial 390×844 viewport: one clear promise, one primary CV action, concise privacy statement; optional role input is collapsed. No forced email, Telegram or payment before meaningful analysis. Target primary action visible without scrolling.
3. After CV upload: real nonempty analysis and specific next action; visible progress, error and retry. User can discard without signup. Save CTA appears only **after** useful output. No invented matches.
4. All interactive controls ≥44×44 CSS px touch targets; ≥12 px gap between adjacent actions; ≥16 px between content sections; no colliding margins at any state.
5. Consistent monochrome system: white, black, neutral gray for surfaces, text and controls; green only success, amber only caution, red only errors. Never use color alone to communicate status.
6. Keyboard focus visible, descriptive labels, screen-reader live announcements, reduced-motion support, readable contrast (WCAG AA), no inaccessible disclosure content.
7. Test empty, loading, slow network, invalid format, oversized/scanned CV, 403/429/500, network retry, analysis success, discard, login unavailable, session expired, save-after-login and return on another device.
8. Source-of-truth components/tokens shared across public site and app. No one-off spacing exceptions without a documented reason.
9. Capture reproducible browser screenshots and interaction recording at each breakpoint and state, and attach CI run/deployment SHA. Automated DOM/visual regression checks plus real iPhone Safari verification required.
10. Staging origin and environment config validated with real multipart CV POST, not merely /health. Explicitly verify no CV data stored on anonymous request and no false save success.

**Release status:** BLOCKED until the full gate has evidence. CSS commits and Railway SUCCESS are not UX acceptance.
