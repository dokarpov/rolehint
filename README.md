# RoleHint

## Start here — product knowledge and release plan

**[Knowledge base](docs/RELEASE_KNOWLEDGE_BASE.md)** · **[Iterative roadmap](docs/RELEASE_ROADMAP.md)** · **[Current code/deployment audit](docs/RELEASE_BASELINE_2026-10-20.md)** · **[Reproducible QA matrix](docs/RELEASE_TEST_MATRIX.md)** · **[Approved product CJM](docs/PRODUCT_EXPERIENCE_V1.md)** · [Web release ADR](docs/adr/ADR-002-web-release-boundaries.md)

**Stage:** Authenticated web beta with deployed backend and automated checks. Public launch awaits independent acceptance of the real-vacancy → approved application → tracked outcome journey.

**What if a job search remembered what had already happened?**

I started RoleHint after encountering the same broken handoffs repeatedly: uploading a CV and re-entering it, seeing jobs with impossible hiring constraints, being offered persuasive but unsupported AI-written achievements, and finding the same employer again after a rejection.

The product decision is **not** another CV generator or an opaque fit percentage. It's a continuous decision process: which opportunities are eligible, which requirements my real experience supports, which claims need review, and what happened after the last application.

**Start here if you came from LinkedIn:** [Product decisions, source code and tests](docs/CASE_ROLEHINT_PRODUCT_DECISIONS.md) · [Original 17 October post](https://www.linkedin.com/posts/dokarpov_job-hunting-has-a-fascinating-feature-collective-activity-7517137903018295296-sVIi).

**Inspect specific decisions:** [Eligibility and evidence policy](docs/DECISION_POLICY.md) · [Real ATS source test](tests/test_real_job_sources.py) · [Account preference persistence](tests/test_settings_persistence.py) · [Full CJM and release gates](docs/PRODUCT_EXPERIENCE_V1.md).

## Explore the product

| Entry | Purpose |
| --- | --- |
| [Product overview](https://dokarpov.github.io/rolehint/site/) | Discover / Verify / Decide walkthrough |
| [Browser beta](https://rolehint-api-worker-production.up.railway.app/webapp/) | Signed-in CV intake, preferences, ATS records and evidence review |
| [Telegram entry](https://rolehint-api-worker-production.up.railway.app/open-bot) | Bot sign-in and conversation entry |
| [Sample workspace](https://dokarpov.github.io/rolehint/site/workspace.html) | Fictional jobs and local preference exploration |
| [Search desk](https://dokarpov.github.io/rolehint/) | Experimental search interface |

## What is implemented and tested

The repository includes backend ATS discovery, vacancy checks, decision logic, search settings, application-package experiments and Telegram integrations. The [backend release gate](https://github.com/dokarpov/rolehint/actions) has passed automated checks, including a public ATS vacancy-source check on 17 October 2026.

## Product decision and acceptance

[Product experience / CJM and release acceptance](docs/PRODUCT_EXPERIENCE_V1.md) is the source of truth. The planned first value is **up to ten distinct, live, eligibility-checked opportunities without a card**, with transparent evidence gaps and job-specific materials. If fewer real opportunities exist, the product must show the actual count rather than fabricate a quota.

A public release requires verified account/session behavior; real and reachable jobs; safe CV parsing and editable facts; approved export; authorized submission or honest handoff; durable tracking; privacy/recovery paths; and real browser E2E on a deployed version.

[Decision policy](docs/DECISION_POLICY.md) · [Technical overview](docs/TECHNICAL_OVERVIEW.md) · [ADR: value before payment](docs/adr/ADR-001-value-before-payment.md)

**Pricing:** Exploratory; no active paid checkout.

**Next evidence:** end-to-end acceptance, qualified job quality and applicant outcomes. [Release roadmap](docs/RELEASE_ROADMAP.md).
