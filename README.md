# RoleHint

**What if a job search remembered what had already happened?**

I started RoleHint after meeting the same broken handoffs again and again: uploading a CV and re-entering it, seeing jobs with impossible hiring constraints, being offered persuasive AI-written achievements nobody could support, and finding the same employer again after a rejection.

RoleHint runs a continuous decision process: which opportunities are eligible, which requirements my real experience supports, which claims need review, and what happened after the last application.

**If you came from LinkedIn:** [Product decisions, source code and tests](docs/CASE_ROLEHINT_PRODUCT_DECISIONS.md) · [Original 17 October post](https://www.linkedin.com/posts/dokarpov_job-hunting-has-a-fascinating-feature-collective-activity-7517137903018295296-sVIi).

**Specific decisions:** [Eligibility and evidence policy](docs/DECISION_POLICY.md) · [Real ATS source test](tests/test_real_job_sources.py) · [Account preference persistence](tests/test_settings_persistence.py) · [Customer journey](docs/PRODUCT_EXPERIENCE_V1.md).

## Explore the product

| Entry | Purpose |
| --- | --- |
| [Product overview](https://dokarpov.github.io/rolehint/site/) | Discover / Verify / Decide walkthrough |
| [Web app](https://rolehint-api-worker-production.up.railway.app/webapp/) | Signed-in CV intake, preferences, ATS records and evidence review |
| [Telegram entry](https://rolehint-api-worker-production.up.railway.app/open-bot) | Bot sign-in and conversation entry |
| [Example workspace](https://dokarpov.github.io/rolehint/site/workspace.html) | Example jobs and local preferences |
| [Search desk](https://dokarpov.github.io/rolehint/) | Search interface |

## How it works

RoleHint finds up to ten distinct, live opportunities that pass the eligibility check, without asking for a card. Each one shows which requirements the candidate’s experience supports, where the evidence has gaps, and comes with job-specific materials. When fewer real opportunities exist, RoleHint shows the actual count.

Every claim in an application comes from experience the candidate has confirmed. After an application, RoleHint keeps the outcome, so the same employer and the same role are recognized next time.

## Implementation

The repository includes backend ATS discovery, vacancy checks, decision logic, search settings, application packages and Telegram integrations. The [backend release gate](https://github.com/dokarpov/rolehint/actions) runs automated checks, including a public ATS vacancy-source check.

[Decision policy](docs/DECISION_POLICY.md) · [Technical overview](docs/TECHNICAL_OVERVIEW.md) · [ADR: value before payment](docs/adr/ADR-001-value-before-payment.md)
