# RoleHint release knowledge base

**Updated:** 2026-10-20  
**Maintainer:** Product / engineering  
**Status:** Versioned source of truth for *implementation and evidence*. **Not** a public-release approval.

## Read in this order

1. [Approved product experience and full CJM](PRODUCT_EXPERIENCE_V1.md) — product intent and user promises.
2. [Iterative implementation and release roadmap](RELEASE_ROADMAP.md) — dependency-ordered engineering work, deliverables and stop gates.
3. [Current implementation audit](RELEASE_BASELINE_2026-10-20.md) — what exists, what is proven, what is still missing.
4. [Acceptance and reproducibility matrix](RELEASE_TEST_MATRIX.md) — tests, fixtures, manual checks, release proof and rollback.
5. [ADR-001: value before payment](adr/ADR-001-value-before-payment.md) — approved product principle.
6. [ADR-002: web auth, evidence and handoff boundaries](adr/ADR-002-web-release-boundaries.md) — implementation-level decision and its limits.
7. [Eligibility and evidence decision policy](DECISION_POLICY.md) — separation of hard blockers, unknowns, evidence and user preference.
8. [Founder problem statement and decision case study](CASE_ROLEHINT_PRODUCT_DECISIONS.md) — narrative context, **not** the release spec.

## Authority / conflict rules

- **User promise:** PRODUCT_EXPERIENCE_V1 + ADR-001 are normative; implementation details cannot silently weaken them.
- **Current observable fact:** dated release baseline plus code + reproducible tests override marketing copy, earlier assistant claims and undated README prose.
- **What to build next:** RELEASE_ROADMAP is the prioritized queue, not a statement that any stage is already complete.
- **What qualifies as done:** RELEASE_TEST_MATRIX, including deployed real-user acceptance, not only fixture-based CI.
- **Architecture changes:** write a superseding numbered ADR; retain old ADRs as historical record. Do not quietly rewrite an accepted decision.
- **Security/privacy:** when uncertain, restrict access or label unknown rather than claim verification or successful submission.
- **Marketing:** only demonstrate/tested behavior; label illustrative examples and never place fictional jobs into authenticated users' results.

## Current boundaries

- **Production entry:** https://dokarpov.github.io/rolehint/site/ → https://rolehint-api-worker-production.up.railway.app/webapp/
- **Authenticated web API:** /web-api/* on Railway. Telegram code can authenticate into the web app; email magic links are coded but unavailable without a configured sender.
- **Persistence:** SQLite on Railway mounted volume /app/data; persistence tests exist, backup/restore and operational guarantees still need release evidence.
- **Job discovery:** direct ATS sources and the existing AutoMatch / decision stack, not a new job parser.
- **Application:** human-reviewed draft and explicit employer-site handoff; **not** automatic submission or universal autofill.
- **Billing:** no public live checkout/approved paid trial.
- **Launch state:** **BLOCKED** until the minimum complete journey passes production E2E with a real test account and at least one real, open ATS vacancy.

## Updating this knowledge base

At the end of each implementation iteration:
1. Record commit + deploy SHA, environment, date/time and test-run URL(s).
2. Update baseline status with what actually changed and what was validated.
3. Mark roadmap acceptance checks passed **only with evidence**, otherwise leave them blocked.
4. Add newly discovered corner cases and failing/passing reproductions to the test matrix.
5. Retain release history and rollback pointer; never mark an untested feature released.
6. Do not store CVs, session tokens, email addresses or other real candidate data in Markdown, issue screenshots or test logs.

**Core product invariant:** assess eligibility separately from evidence, preferences and application effort. Unknown is not qualified; self-reported is not independently corroborated; opened form is not submitted.
