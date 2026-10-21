# RoleHint — UX review and implementation gates (2026-10-21)

Status: working plan; NOT a release approval. Scope: staging webapp first. Production webapp remains unchanged until explicit founder signoff.

## Sources of truth and precedence
1. PRODUCT_EXPERIENCE_V1.md — approved outcomes, first value, privacy, CJM.
2. CV_JOB_MATCHING_SPEC_V1.md — source-backed matching, eligibility and provenance.
3. VACANCY_RESULTS_AND_ENTITLEMENTS_V1.md — free 10 lifetime / active paid unlimited.
4. RELEASE_ROADMAP.md and RELEASE_TEST_MATRIX.md — acceptance and deployment gates.
5. Existing working services — reuse, do not rewrite without evidence.

## Findings (source-code review, not live usability test)
- Main and staging webapps both use sage/green CSS tokens; visual hierarchy and branding are not aligned with the approved text-only wordmark and neutral landing direction.
- Main's first screen contains explanatory steps before value. Staging adds an anonymous CV/role flow but still uses an interim GET endpoint with CV text in query parameters.
- Staging jobs endpoint uses role-title and CV-token overlap, not requirement-to-evidence mapping. It returns at most ten per request, not an atomic lifetime entitlement.
- Staging source coverage and live vacancy freshness are insufficiently verified. A blank or unavailable feed must not be represented as zero opportunities.
- Authenticated workspace, application pack and history exist; preserve their data contracts. Do not imply tailored PDF/DOCX or universal autofill is working.
- Production webapp is a separate old release; do not promote staging wholesale.

## Approved UX target
1. Entry: one clear headline and two equally visible paths: upload CV or enter role. No signup gate.
2. Minimal hard constraints: country, remote/hybrid, B2B/employee, salary currency; request progressively, preserve unknown as unknown.
3. Jobs: real verified source links, explicit open/freshness state, hard constraints, fit evidence and missing/unknown requirements. Show fewer than ten if warranted.
4. Decision: Apply / Save / Verify / Skip; explain why, not fake percentages.
5. Optional account: save/resume after value. Telegram optional when operational.
6. Preparation: evidence review, editable truthful documents, explicit export and handoff; durable outcomes.

## Visual system freeze
- One text-only bold `rolehint` wordmark, no emblem.
- Neutral graphite / off-white palette; no competing green/purple or decorative gradients.
- One font family with deliberate display/body scale; shared button, card, field, alert and status tokens.
- Single primary CTA per screen, secondary navigation subordinate.
- Mobile 320–430px, keyboard, reduced motion and WCAG contrast.
- Capture approved reference screenshots before implementation; changes outside the slice require explicit review.

## Milestones and acceptance
M0 — Baseline: capture main/staging deployed SHA, 320/390/430px and desktop screens, user-visible journeys, dead ends, source health, regression status. Output: frozen screenshot baseline and prioritized issues.
M1 — First value: CV/role → results → fit/gap → optional signup, with no CV in GET URLs, meaningful errors/retry/back and truthful provider status. Test both entry paths on real staging and mobile.
M2 — Matching: structured CV claims, requirement extraction and source evidence, geography/B2B tri-state, source freshness, dedupe, real top-ten human audit; no invented scores.
M3 — Entitlements/results: server-atomic 10 lifetime distinct deliveries; paid unlimited paginated architecture with 120+ fixture jobs; no live billing before separate approval.
M4 — Application: truthful reviewable CV/letter/answers, download, consented manual handoff and persistent tracking. No false submission.
M5 — Production release: live real-user E2E, data/privacy/security, cross-device, rollback, founder signoff. Only then promote approved webapp.

## Delivery discipline
For each milestone: failing acceptance test → minimal backend/frontend implementation → tests → browser/mobile staging → compare screenshots → document source/deployment SHA and defects → founder go/no-go. No unapproved production webapp merge/deploy. Never claim browser validation from fixtures, static source inspection or Railway health alone.

## Open product decisions
- Confirm final webapp visual reference screenshots (landing design alone does not establish all app components).
- Clarify which authentication method must work for non-Telegram users before public release.
- Price/trial/subscription terms require separate approval; no Stripe checkout yet.
