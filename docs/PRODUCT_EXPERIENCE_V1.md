# RoleHint — Product experience and acceptance contract
Status: **Approved product direction; not implemented/validated end to end**
Decision date: 2026-10-16
Owner: Product
Version: 1.0

This document is the normative source for product behavior. Illustrative UI, mock records and smoke tests must not be counted as customer value or release acceptance.

## Outcome and audience
A new job seeker can start from the landing page, receive a useful CV analysis (when a CV is provided), find **up to ten distinct live vacancies** matching declared constraints, understand evidence gaps for each job, generate and download an honest tailored CV and accompanying application material, and complete an application with as little manual repetition as technically feasible. The first ten successful qualifying opportunities are free without a card. No fabricated listings or unsupported claims.

North-star activation: percentage of qualified first-time visitors who create an approved, vacancy-specific application package and complete a submission/handoff. Track separately: real source-verified vacancies delivered; CV review completion; packages approved; actual applications submitted/confirmed; return-to-track rate. Do not confuse a CTA click with activation.

## CJM and state transitions
| Stage | User intent | Input + consent | Product response | Failure/exit/recovery |
|---|---|---|---|---|
| Landing / first viewport | See why this is useful | Single primary action with two paths: Upload CV or Enter target role | Concrete description and genuine product flow, not fabricated results or statistics | Scroll guidance, mobile fit, accessible controls, no forced registration |
| Anonymous entry | Start without committing | CV PDF/DOCX/TXT or role name, plus minimum hard constraints later | Parse in ephemeral session, or discover based on role | Bad/scanned CV -> accessible editing/paste; no CV -> role path; malformed upload -> retry |
| CV understanding (optional before results) | Correct interpretation | Structured experience, dates, skills, ownership, quantified results; confirmation | Explain transferable strengths, gaps, confidence and source provenance; confirm inferred role(s) | Career change, multi-CV, non-English, no metrics, ambiguous dates/claims, no hallucination |
| Eligibility | Avoid wasted matches | Hiring country/work eligibility, work arrangement, exclusions, salary floor; unknown allowed | Separate hard blocks, unresolved questions and soft fit | Unknown != passed; request minimal missing inputs; correct or change constraints |
| Identity boundary | Save results securely | Verified email magic link or other audited sign-in; separate privacy consent | Account, session, saved search and quota on server; resume same journey | Expired link, duplicate identity, no email access, multi-device, sign-out/revoke |
| Discovery | Receive real opportunities | Target role/CV+constraints | Source URL, company, title, timestamp, status, dedupe, rationale, unresolved facts; <=10 counted free opportunities | Zero/fewer than 10 -> truthfully show real number, retry later, retain unused allowance; source outage/expired/duplicate never debit |
| Job assessment | Decide whether worth applying | Existing CV evidence + vacancy requirements | Evidence status per requirement, hard blockers, what to change/prove, source trace | No CV -> provisional goal-fit only; missing evidence -> review; contradictory CV -> clarification |
| Application studio | Produce credible submission | Approved original CV, selectable evidence and tone | Versioned tailored CV (download), letter, recruiter insights, pre-drafted questionnaire answers; difference review and approval | Unsupported claims withheld; questions needing personal/legal answers remain unanswered; preview/revise/re-export |
| Apply | Submit with minimal friction | User approval, explicit target job/form | (A) authorized ATS integration, (B) supported browser-assisted autofill, (C) assisted handoff/companion; never claim universal autofill | Cross-origin frames/X-Frame-Options, CAPTCHA, login, changed fields, upload failure, browser/mobile limitations -> honest manual fallback preserving package |
| Tracking + return | Monitor impact and improve | Submission confirmation or user confirmation and later outcomes | Durable job/application history, follow-ups, dedupe, iteration | Network failure, repeated submit, uncertain submission: no false success; resume safely |
| Upgrade | Continue after value | Clear terms and separate payment consent | Free entitlement stays usable; card-backed trial/subscription via provider-hosted checkout when fully configured | Trial end, cancel, declined card, refunds, reactivation, deletion; no silent charging |

## Vacancy discovery by plan

**Free:** 10 lifetime qualifying distinct opportunities. **Active paid subscription:** unlimited qualifying vacancy discovery across searches and paginated results, with no product-imposed vacancy-count ceiling; actual availability depends on live sources. See [Vacancy results and entitlements specification](VACANCY_RESULTS_AND_ENTITLEMENTS_V1.md). Paid results must not be capped at ten. Billing is not yet live.

## Ten-opportunity entitlement
- Server enforces exactly **10 qualifying, distinct, real opportunities delivered per account** without a card, **not** ten page views, source scans, raw candidates, generated drafts or arbitrary timeout.
- Count only after a validated accessible source URL and job record have been durably delivered to the user's account. Suppress stale, duplicates, inaccessible or explicitly hard-ineligible items; replace without consuming quota. Preserve unused allowance if supply is low.
- Each of these ten may have one or more revisions of an approved, job-specific application pack without extra vacancy credits. Define abuse/rate limits without silently breaking this promise.
- Paid continuation is separate: card-backed trial only after explicit consent, disclosed price/duration/renewal/cancellation, tested Stripe webhooks and entitlement recovery. **No checkout is live or approved by this document.**

## Evidence and generation rules
- Store claim text, original source, document version, dates, candidate ownership/contribution, metric definitions, provenance, confidence, and user's approval independently.
- Statuses: self-reported; document-supported; ownership-supported; independently corroborated; unresolved/conflicting. A retrieved lexical/semantic match is **not** external verification.
- Every vacancy requirement traces to an excerpt and evidence decision. For CV-only assertions, say "self-reported"; never represent inferred claims, adjacent experience or unverified numbers as facts.
- The model may rephrase approved facts for a role; may not invent employers, dates, degrees, metrics, work authorization, project ownership or personal/EEO answers. Highlight all material edits; explicitly approve before exports/submission.
- Generate tailored CV, cover letter, recruiter note, interview gaps and draft answers. Vacancy-specific questions are extracted from a **real accessible form** where permitted; do not promise coverage of unknown questions.

## Data boundaries and safety
- Anonymous CV content is sensitive; avoid analytics capture, query strings, persistent browser storage or third-party leakage. Define ephemeral processing/expiry and consent before implementation.
- Saved identity/profile/documents/results live in per-user authenticated storage with authorization checks. Implement encryption in transit, managed secrets, retention/deletion, export, backups/restore, audit logs and GDPR review appropriate for EU users before inviting public data.
- Store only Stripe customer/payment references, never raw card details. Authenticated sessions and billing webhooks must be signed and idempotent.
- Start with a web account mechanism; Telegram is an optional channel and must not be the only way a browser visitor uses the service.
- Explicitly test cross-user isolation, IDOR, SSRF in vacancy fetching, upload malware/content handling, quota races, replay and retry.

## UX/design and discoverability
- One coherent CTA module and two clear entry methods, not a forest of competing buttons.
- Graphite, off-white, muted green-grey and tactile/grainy graphic texture; **no pink or lilac/purple dominant surfaces**. Product screenshots must come from implemented testable screens; any illustrative states must be labelled.
- iPhone/desktop, keyboard, VoiceOver basics, reduced motion, sufficient WCAG contrast and no clipping. Loading/empty/error/retry states are part of the product.
- Site copy, canonical URL, sitemap, structured data and llms.txt must accurately distinguish intended vs available features. Indexability checks are not proof of appearance in LLM recommendations.

## Release acceptance — ALL must pass
1. New visitor (iPhone + desktop) starts from hero, scrolls and uses either CV or role entry; no hidden demo redirect.
2. Anonymous input has explained data handling; authenticated session persists progress correctly, with logout and account isolation.
3. Real job sources return nonfictional current openings with working application URLs, explanations and hard-constraint filtering; zero-results behavior correct.
4. At most 10 unique eligible deliveries, correct server-side counting across refresh, concurrency, multiple devices and expired links.
5. CV import from representative real PDF/DOCX/TXT fixtures, including malformed/scanned cases; structured facts editable; no fictitious proof.
6. For a real job, evidence mapping and all application artifacts are reviewed, editable, downloadable and versioned without unsupported claims.
7. Successful full application with a genuinely supported route or honestly labelled assisted fallback, plus durable outcome tracking; no double submission.
8. Persistence, privacy/delete/export, backups/recovery, auth/security, negative/error states pass documented tests.
9. Visual/contrast/responsive plus authenticated browser E2E; production commit/version and rollback verified. A green marketing CI alone does not satisfy release.
10. Billing gates are disabled until Stripe test+live setup, trial terms, webhooks, cancel and expired-payment behavior are separately approved.

**Release decision:** public advertising and recommendation **blocked** until the relevant free-user gates are demonstrated on the deployed release. A card-backed trial is a subsequent separate gate.
