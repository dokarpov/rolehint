# ADR-002 — Web identity, evidence provenance and application-state boundaries

**Date:** 2026-10-20  
**Status:** **Provisional implementation decision — acceptance pending**. Does **not** supersede [ADR-001](ADR-001-value-before-payment.md) or the approved [product CJM](../PRODUCT_EXPERIENCE_V1.md).  
**Scope:** the smallest testable browser release that reuses existing RoleHint systems.

## Context

RoleHint already has signed Telegram users, a persistent product-state store, ATS discovery, hard-constraint evaluation, evidence-backed matching, proposed application packs and history. The public browser app was only partly connected; email links were coded but lack a transactional sender. Rebuilding identity or matching in parallel would multiply risk. Giving users fake vacancies or an unverifiable "applied" status would break trust.

## Implementation boundary — chosen

1. **Reuse Telegram user identity for the first web beta.** An authenticated Telegram bot issues a short-lived, single-use challenge code; the browser exchanges it for an HttpOnly/Secure same-origin session bound to the existing account. Do not treat the login link itself as verification. Test OTP delivery, browser binding, guessing/rate limits, isolation, and session restoration before any release. Verified-email login remains optional and **unavailable** until delivery is operational.
2. **Preserve CV meaning.** Existing parsers extract text and evidence fragments; the candidate can edit and confirm source text. Confirmation means only "candidate says this is accurate," never "employer independently verified this." Evidence cards retain source, ownership, dates and confidence when established, and the pack export filters unsupported assertions.
3. **Reuse ATS and decision services.** Don't create fictional job records. Hard ineligibility, unresolved geography, independent-contractor requirements and salary-unit uncertainty are distinct. Verify freshness and original employer URL before spending a free opportunity or recommending an application.
4. **Reuse applications and employer history.** Company/requisition dedup, previous applications and rejections persist across sessions; prevent redundant recommendation even when role name or channel varies. Canonical employer aliasing remains an implementation gap.
5. **Submission state is explicit.** Preparing a pack is not applying. Approving an employer-site handoff is not submitting. Only an authorized integration with verifiable confirmation can say "submitted automatically"; otherwise the candidate must confirm a successful submission and that claim is recorded as **user-reported**.
6. **Keep the UI minimal.** Public CTA opens the real authenticated application; anonymous user may start with role or CV selection. Signed-in workspace presents only the next decision needed. Legacy demo pages remain illustration-only and must not be confused with live results.
7. **No card or pricing claim ahead of proof.** Trial terms, payment method and subscription webhook are separate future gates requiring explicit approval.

## Alternatives and why not now

- **Force email magic-link login:** blocked by sender configuration; a fake/send-disabled flow cannot pass onboarding.
- **Store sensitive CV in localStorage:** browser storage and client-side analytics create avoidable privacy exposure; use ephemeral memory and server-side account records with consent.
- **Pretend semantic matching proves a factual claim:** lexical/embedding match cannot independently verify dates, metrics, employer, credentials or ownership.
- **Use an iframe/split pane as universal ATS form solution:** employer CSP/X-Frame-Options and mobile Safari frequently prohibit this. A tested manual handoff is the minimum honest implementation; browser-assisted autofill requires specific support.
- **Count any search result as a free job:** duplicates, closed posts and ineligible jobs would consume value; atomically count only delivered-valid unique ATS openings.
- **Redesign the website again:** functional sign-in, job validity, export and tracking are more important than surface polish.

## Consequences / acceptance burden

- Telegram-linked browser sessions must not silently merge with a separate email account.
- SQLite volume is the database, not a tested backup; concurrency and cross-account separation remain P0.
- CV plaintext is sensitive; storage encryption choices, retention/deletion/export and upload validation must be evaluated before broad CV intake.
- Existing Markdown pack is **not** a job-specific tailored PDF/DOCX CV or employer form autofill.
- The feature implementation being present in source or passing fixture tests **does not** constitute live production acceptance.
- Revisit this ADR once email auth is actually configured, an authorized ATS form integration is implemented, or user research changes the primary onboarding decision.

**Release owner decision remains BLOCKED.** See [roadmap](../RELEASE_ROADMAP.md) and [test matrix](../RELEASE_TEST_MATRIX.md).
