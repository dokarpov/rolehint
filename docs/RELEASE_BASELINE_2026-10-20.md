# RoleHint implementation audit — 2026-10-20

**Audit reference:** main at release commit \`39f4e2dcdbce6f8e09285ba9192555718e09bc6c\`, plus subsequently inspected source and smoke-test changes. This is a **dated snapshot**, not a live production monitor.  
**Release decision:** **NOT ACCEPTED** for unrestricted public traffic.  
**Observed infrastructure:** Railway reports SUCCESS for commit \`39f4e2d\`; the SQLite volume is mounted at \`/app/data\`. These facts do not establish authenticated end-to-end acceptance.

## Product surfaces and truthfulness

| Surface | What code currently does | Caveat |
|---|---|---|
| GitHub Pages \`site/\` | Public explanation and CTA to Railway \`/webapp/\`; interactive illustrations remain | Illustrative examples are not real matching results; no external indexing or conversion proof |
| Railway \`/webapp/\` | Profession-first intake, browser CV selection, signed-in preferences, evidence editing, job review and application actions | Not production E2E accepted; existing web app still has known empty/error/edge-case gaps |
| Railway \`/web-api/\` | Auth/session, CV import, job discovery, manual handoff and history endpoints | A green HTTP health check does not prove actual login email/Telegram delivery or job submission |
| Railway \`/miniapp/\` | Telegram Mini App with independently existing product functionality | Different channel; not a substitute for verifying browser entry |
| Legacy \`site/workspace.html\` and \`site/onboarding.html\` | Browser-based illustration/demo paths | Never present as authenticated jobs or ask real users to submit sensitive content there |

## Reuse rather than rewrite

| Existing component | Relevant code | Reuse / status |
|---|---|---|
| Signed Telegram identity | \`services/telegram/*\`, \`web_identity.py\`, \`telegram_bot/bot.py\` | Web OTP bridge is coded; verify actual Telegram delivery/session/cross-device in production |
| Web accounts, sessions, preferences, CV text | \`web_identity.py\`; \`services/product_state/store.py\` | Server-side sessions, one-time tokens, saved CV and preferences exist; operational hardening pending |
| Parsing | \`services/evidence_ingest.py\` | PDF/DOCX/TXT text extraction and sections; not a reliably structured career/education/metric profile |
| ATS search | \`services/job_search.py\`, \`services/job_sources/*\`, \`worker.py\` | Retain real source ingestion; verify source coverage/freshness/remote geography for target roles |
| Decision/evidence | \`services/auto_match/service.py\`, \`DECISION_POLICY.md\` | Separate eligibility, evidence, preference, effort. CV claims must remain self-reported |
| First-party web discovery | \`web_release.py\` | B2B flag and employer ATS results; incomplete freshness, concurrency, quota and exclusion guarantees |
| Application packs | \`services/application_packs/*\`, \`services/pack_proposal/*\`, \`web_release.py\` | Can save/export an evidence-restricted **Markdown application pack**; not a complete tailored downloadable CV |
| History/outcomes | \`services/product_state/store.py\`, \`services/application_tracking/*\` | Records submissions, email events and responses; verify employer aliases and rejection correlation |
| Tests/release tooling | \`tests/test_web_*.py\`, \`tests/test_real_job_sources.py\`, \`site/qa-webapp.mjs\`, GitHub Actions, \`scripts/smoke_live_release.py\` | Meaningful fixtures and read-only live smoke; not a real-user production E2E |

## What tests have and have not proved

- Backend gate on the integration PR passed automated unit/contract tests for Telegram web sessions, CV lifecycle, eligibility, application-pack persistence, manual handoff, duplicate submission prevention and outcome history.
- Browser QA passed at mobile/desktop widths using **intercepted web API responses and fixtures**. This proves rendering and some interaction wiring, not actual production auth or ATS application behavior.
- Live ATS contract test finds traceable jobs from a small configured public ATS sample. It does **not** establish each returned job is still open, accepts applicants from the user's location, meets B2B requirements or is downloadable to a specific signed-in account.
- Read-only smoke checks establish health, static web app availability, route existence and some anonymous-access protections. They cannot confirm email delivery, Telegram OTP, CV content persistence across devices or real-user handoff.
- Railway SUCCESS means deployment health passed; **no proof of a full signed-in, real vacancy → accurate application → tracked result has been recorded**.
- No proven PDF/DOCX tailored-CV export, ATS form autofill, universal embedding, automatic submit, production account deletion/restore or subscription checkout.

## Critical gap register

| ID | Severity | Observed gap / risk | Required disposition |
|---|---|---|---|
| R-01 | P0 | No production evidence of real-user Telegram OTP delivery, cross-device session restore, expiry/logout and sign-in failure recovery | Run real test-user login on iPhone and desktop; instrument safe redacted status; block launch if broken |
| R-02 | P0 | Email magic links depend on unconfigured SMTP; cannot offer working email login | Hide unavailable option; keep Telegram OTP viable for private beta or configure verified sender; do not fabricate access |
| R-03 | P0 | CV import is text + paragraph fragments; candidate confirmation does not establish role/metric ownership or independent proof | Structured editable career profile, source/provenance, user confirmation and evidence limits; no invented qualifications |
| R-04 | P0 | Anonymous CV selection stays on device but is not analyzed before sign-in; agreed initial free CV value is not yet fulfilled | Transient anonymous parsing with explicit consent/expiry **or** re-scope the private-beta promise visibly and record ADR |
| R-05 | P0 | Ten-free count uses existing \`user_jobs\` and is not a transactional, unique **delivered-valid-vacancy** ledger; web and worker can race | Idempotent quota ledger and atomic reservation/commit; duplicates/stale/hard-ineligible must never charge |
| R-06 | P0 | Job URL is not reliably rechecked for open/expired/closed state at deliver/handoff; URL existence is not proof of freshness | ATS status/timestamp, live recheck (where supported), expiry quarantine, source failure/unknown states |
| R-07 | P0 | B2B/contractor and geography inference is lexical/partial; unknown can slip into recommendation if treated as positive | Explicit allow/deny/unknown decision with extracted quote + source for hiring country, contract model and work authorization |
| R-08 | P0 | Existing/history exclusion relies partly on exact employer-name equality and recorded job association | Canonical employer, aliases, employer-level rejection policy, reopening/override with user confirmation; regression fixtures |
| R-09 | P0 | Web app offers draft pack and Markdown export, not role-specific honest downloadable CVs, credible tailored letter and vacancy-specific screening answers | Build on existing pack/evidence policies; reviewable versions; block unsupported facts; annotate unanswered questions |
| R-10 | P0 | Handoff opens original employer form, user manually confirms submit; split view/auto-population not delivered | Describe as **manual handoff**; test no false 'submitted'; browser-assist separate future gated integration |
| R-11 | P0 | Plaintext CV/profile content in SQLite; retention/deletion/privacy export, operational restore, upload hardening and cross-user authorization need evidence | Threat model, per-user access tests, retention schedule, account deletion/export, backup/restore drill and upload controls |
| R-12 | P0 | Production real-user E2E, accessibility and recovery matrix not signed off | See RELEASE_TEST_MATRIX; block public release until mandatory gates green |
| R-13 | P1 | Telegram and web account histories are connected by Telegram ID; web email identities are separate and account merge not designed | No silent merge; decide whether email login is GA dependency, test account switching and duplicates |
| R-14 | P1 | Job discovery is both worker-driven and web-triggered; source outages/refresh limits and retries may confuse users | Single observable discovery state, source errors, idempotent dedupe across worker/web |
| R-15 | P1 | Site/demo screenshots, pricing and claims may outpace actual behavior | Release-conditioned landing copy; examples labelled; no fictional or unsupported performance claims |
| R-16 | P1 | Privacy/observability controls for user data, prompts, backend logs and email credentials are not independently audited | Redact tokens/CV in logs, least-privilege config, consent, safe monitoring and incident playbook |

## Architecture contracts (minimal)

- **Public site** → \`/webapp/\` → \`/web-api/*\` (same origin). No redirect to a fictional workspace for signed-in users.
- **Identity:** bot-issued OTP is tied to a browser challenge and existing Telegram user; session cookie is HttpOnly/Secure. Email magic-link remains an optional separately configured route; never claim it works without a real delivery test.
- **CV:** user-specific profile and evidence records. Extracted CV statements are *self-reported*, not independently verified, even after user confirmation.
- **Search:** ATS job URL + stable identity + company/title + raw requirements → hard-constraint preflight → evidence review; unknown contract/location/salary must remain visible.
- **History:** use real employer-level applications, declines/rejections, response dates and aliases; never erase history on new searches.
- **Application:** editable evidence-restricted pack → user review → *manual employer handoff* → user-confirmed successful submission → later outcome. Distinguish every state.
- **Data:** SQLite volume exists; persistent disk is not a backup. Backups and recovery remain to be tested.

## Deliberate non-goals for first reliable slice

Do **not** add generic CRM workspaces, unapproved Stripe checkout, fabricated fit percentages, automatically generated unverifiable CV metrics, universal ATS autofill promises, automatic job submissions, growth/outreach funnels or a cosmetic rebrand before the functional gates are accepted.

**Next action:** follow [RELEASE_ROADMAP.md](RELEASE_ROADMAP.md) and verify each claim using [RELEASE_TEST_MATRIX.md](RELEASE_TEST_MATRIX.md).
