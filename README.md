# RoleHint

## Start here — product knowledge and release plan

**[Knowledge base](docs/RELEASE_KNOWLEDGE_BASE.md)** · **[Iterative roadmap](docs/RELEASE_ROADMAP.md)** · **[Current code/deployment audit](docs/RELEASE_BASELINE_2026-10-20.md)** · **[Reproducible QA matrix](docs/RELEASE_TEST_MATRIX.md)** · **[Approved product CJM](docs/PRODUCT_EXPERIENCE_V1.md)** · [Web release ADR](docs/adr/ADR-002-web-release-boundaries.md)

**Release status: BLOCKED for public launch.** Production code has a deployed authenticated web application and automated release tests, but the complete real-user production journey (Telegram OTP → confirmed CV → actual qualified open ATS job → accurate application → manual handoff → tracked outcome across devices) has **not** been independently accepted. Do not describe CI smoke checks as production E2E.

**What if a job search remembered what had already happened?**

I started RoleHint after encountering the same broken handoffs repeatedly: uploading a CV and re-entering it, seeing jobs with impossible hiring constraints, being offered persuasive but unsupported AI-written achievements, and finding the same employer again after a rejection.

The product decision is **not** another CV generator or an opaque fit percentage. It's a continuous decision process: which opportunities are eligible, which requirements my real experience supports, which claims need review, and what happened after the last application.

**Start here if you came from LinkedIn:** [Product decisions, source code and tests](docs/CASE_ROLEHINT_PRODUCT_DECISIONS.md) · [Original 17 October post](https://www.linkedin.com/posts/dokarpov_job-hunting-has-a-fascinating-feature-collective-activity-7517137903018295296-sVIi).

**Inspect specific decisions:** [Eligibility and evidence policy](docs/DECISION_POLICY.md) · [Real ATS source test](tests/test_real_job_sources.py) · [Account preference persistence](tests/test_settings_persistence.py) · [Full CJM and release gates](docs/PRODUCT_EXPERIENCE_V1.md).

> **Release reality:** backend components and focused tests exist, but a complete authenticated web journey from real vacancy to approved application and saved result is **not yet a verified public release**. Marketing examples remain illustrative; the web app now supports a Telegram-verified web session, pending real-user end-to-end verification. There is no active paid checkout or proven hiring uplift.

## Product surfaces (not equivalent release states)

| Entry | What exists | What it does not prove |
| --- | --- | --- |
| [Public overview](https://dokarpov.github.io/rolehint/site/) | Editorial landing page with illustrative Discover / Verify / Decide states | Not an end-to-end authenticated web application |
| [Browser application](https://rolehint-api-worker-production.up.railway.app/webapp/) | Real signed-in browser routes with CV intake, preferences, ATS records, evidence review and manual employer handoff | Real production login, CV-to-job-to-handoff and cross-device recovery are **not** yet E2E signed off |
| [Telegram bot entry](https://rolehint-api-worker-production.up.railway.app/open-bot) | Current entry to the authenticated bot experience | Does not establish universal ATS submission or the complete browser CJM |
| [Browser sample workspace](https://dokarpov.github.io/rolehint/site/workspace.html) | Local demonstration using fictional jobs and locally saved preferences | No CV-to-live-vacancy matching, account sync or real application submission |
| [Experimental search desk](https://dokarpov.github.io/rolehint/) | Separate web shell for search settings and decisions | Not a separately accepted public product release |

The public website must not advertise fictional employers as live vacancies. The sample workspace should not invite real CV data without a complete privacy and security review.

## What is implemented and tested

The repository includes backend ATS discovery, vacancy checks, decision logic, search settings, application-package experiments and Telegram integrations. The [backend release gate](https://github.com/dokarpov/rolehint/actions) has passed automated checks, including a public ATS vacancy-source check on 17 October 2026. **That verifies a narrow technical slice, not the complete applicant journey.**

The static website and the backend are different release surfaces. A green build for one does not establish that the other is connected or ready.

## Product decision and acceptance

[Product experience / CJM and release acceptance](docs/PRODUCT_EXPERIENCE_V1.md) is the source of truth. The planned first value is **up to ten distinct, live, eligibility-checked opportunities without a card**, with transparent evidence gaps and job-specific materials. If fewer real opportunities exist, the product must show the actual count rather than fabricate a quota.

A public release requires verified account/session behavior; real and reachable jobs; safe CV parsing and editable facts; approved export; authorized submission or honest handoff; durable tracking; privacy/recovery paths; and real browser E2E on a deployed version.

[Decision policy](docs/DECISION_POLICY.md) · [Technical overview](docs/TECHNICAL_OVERVIEW.md) · [ADR: value before payment](docs/adr/ADR-001-value-before-payment.md)

**Pricing:** the current sample is free; the pricing and subscription pages describe a *possible future offer*, not an active trial, automatic renewal, working checkout or an available subscription.

**Status:** integrated private beta under verification; public release blocked. No hiring uplift, revenue or product–market fit is claimed. Release steps and blockers are tracked in the [iteration roadmap](docs/RELEASE_ROADMAP.md).
