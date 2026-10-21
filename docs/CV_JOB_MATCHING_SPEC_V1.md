# RoleHint — CV-to-job matching specification v1.0

Status: implementation contract; **not evidence of live acceptance**. Owner: product/engineering. 2026-10-21.

## Outcome and scope
An anonymous visitor uploads a PDF/DOCX/TXT CV or chooses a target role. A separate results screen shows **up to 10 currently open, unique, genuinely relevant vacancies**, ordered by evidence-backed suitability, each with employer, role, original apply URL, remote geography, work arrangement, provenance, dated verification, fit evidence, gaps and unknowns. The role-only path is clearly labelled provisional. Never pad to 10, invent positions, or call token overlap a verified fit percentage.

## Functional contracts
**MATCH-01 CV parsing and structured evidence.** Parse full supported CV, not first 2,500 characters. Extract normalized work history (title, employer, dates, responsibilities, measurable outcomes), skills/tools, sectors, seniority, languages, location, authorization and work model. Preserve exact CV text spans, page/section and parser confidence. Do not infer citizenship, authorization, degree, salary or achievement not explicitly stated. Ambiguous or scanned text -> user confirmation; allow editing and target-role selection. Never silently default to Product Manager.

**MATCH-02 preferences.** Separate hard constraints (remote from Spain, accepted employment/B2B, location eligibility, salary floor and currency, language, seniority) from preferences (sector, product stage, company size). Unknown != eligible; a vacancy with explicit disqualifying restriction must be excluded. Missing eligibility facts remain visible as unknown, never auto-rejected solely for omission.

**MATCH-03 real retrieval.** Reuse JobSearchService and provider adapters. Collect from multiple independent sources (ATS employer boards, credentialed aggregators and public remote feeds); record source health, query, retrieval time, pagination, upstream counts and timeouts. Expand aliases carefully; no arbitrary role substitutions (Project Manager is not Product Manager). Source outages must produce a distinct error or partial-results state. Source availability is not vacancy freshness.

**MATCH-04 normalization and verification.** Canonical vacancy ID = employer + ATS requisition ID where available, else canonical URL and normalized title. Merge duplicate feeds, prefer employer-owned ATS links, remove closed/expired positions and invalid/non-employer application URLs. Revalidate live status and timestamp when provider permits. Label unknown status; do not call it confirmed open. Reject listings whose title/body conflict or whose remote eligibility explicitly excludes Spain.

**MATCH-05 requirements.** Segment descriptions into must-have, nice-to-have, work authorization, geography, employment model, seniority, salary, domain and responsibilities. Every extracted requirement carries exact job-description excerpt, category, evidence confidence and source. Don't convert generic words such as 'strategy' or 'leadership' into an unsupported mandatory gap.

**MATCH-06 explainable fit.** For each must-have, align with CV evidence using explicit terms, title/function synonyms, recency, scope and outcome; produce one of supported / partial / unsupported / unknown with a source excerpt and short rationale. Unsupported means CV lacks evidence, **not** the candidate lacks the skill. Distinguish hard-ineligible from unconfirmed. Show 3 strongest matches, up to 3 material gaps and all hard-constraint unknowns. Do not fabricate experience years or metrics. No percentage score until calibrated and evaluated.

**MATCH-07 ranking.** First filter explicit hard disqualifications and closed listings. Rank remaining using role/function relevance (35%), must-have evidence coverage (30%), seniority/scope (15%), preference alignment (10%) and freshness/source confidence (10%); missing values get neutral/unknown handling, not zero competence. These are initial engineering weights, subject to validation; retain component scores and rationale for debugging. Use deterministic tie-break by verification recency and canonical ID. No more than two near-identical roles from one employer in top 10 unless fewer alternatives exist. Do not rank a vague job above an evidence-backed fit purely for title overlap.

**MATCH-08 results UX.** Results appear after CV or role input, no account gate. Card: role, employer, remote location, employment type, source, last checked, supported strengths, gaps/unknowns, link to employer. Provide editable filters, progress, retry, zero/partial/error states and keyboard/touch accessibility. Show a Telegram opt-in only after actual cards; disabled or hidden if Telegram provider unavailable. On role-only search say 'CV fit not assessed'.

**MATCH-09 privacy/security.** Ephemeral CV processing with short TTL, no raw CV in query parameters, URLs, analytics, logs or third-party job-board calls. POST structured evidence or short-lived server-side token for matching. No persistence or identity linking before explicit consent. Enforce size, MIME, parsing timeouts, origin policy, rate limits, output encoding, source URL validation and deletion. Do not transmit full CV to Remotive/ATS.

## API contract (target, not current implementation)
POST /web-api/anonymous/cv-analysis -> {analysis_id, expires_at, extracted_profile, role_suggestions:[{role,evidence,confidence}], warnings}. No raw CV exposed in URLs.
POST /web-api/anonymous/matches -> {analysis_id?, role, preferences, limit:10} -> {jobs:[{canonical_id,title,company,apply_url,source,source_checked_at,open_status,location,work_model,eligibility,requirements,fit:{supported,partial,unsupported,unknown,ranking_reasons}}],total_candidates,source_status,partial,generated_at}.
Status 422 invalid inputs; 429 throttled; 503 all sources unavailable; 200 with [] only for verified zero matches. Do not expose raw provider errors or personal evidence in logs.

## Acceptance and test matrix
1. Parser fixtures: PDF, DOCX, TXT, non-English, malformed, scanned, long, overlapping roles; assert provenance and editable corrections.
2. Ranking fixture with 25 contrasting jobs: exact expected top 10, stable ordering, dedupe, must-have coverage, geography and B2B disqualification; compare with expert judgments, measure precision@10 and recall of relevant candidates.
3. Negative fixture: Product vs Project Manager, false positive from generic keywords, stale job, closed employer link, Spain-excluded remote job, wrong salary currency, uncertain authorization.
4. Security: no CV in GET URL/server logs; invalid upload and malicious HTML; origin, expiry, concurrency, rate limiting and deletion.
5. Source integration: real employer-owned URLs and response status, source outage, 429, timeout, zero, partial, pagination and freshness; capture dated, redacted evidence.
6. Desktop and 320–430px Safari: CV→results, role→results, correction, filters, 10-or-fewer, fit/gap expansion, original link, back, error/retry, CTA placement.
7. Live gate: use founder-approved CV in a private staging test; manually inspect **each of 10** results for currently open, geography/B2B eligibility and fit evidence. If only 6 pass, show 6 and report coverage shortfall. Record deployment SHA, tests, source health and owner signoff. Do not declare ready on a successful Railway health check alone.

## Implementation sequence
A. Remove CV from GET query, add structured extraction and explicit target-role confirmation.
B. Instrument provider health and build sufficient multi-source retrieval with live open-status checks.
C. Normalize and dedupe, extract requirements and hard constraints.
D. Evidence alignment and deterministic ranking with source-backed explanations.
E. Regression, integration and real browser acceptance; keep release blocked until gate 7 passes.

## Current gap (2026-10-21)
Existing anonymous_jobs.py uses limited CV text tokens, role-title overlap, a single public feed plus unconfigured ATS adapters and no live vacancy revalidation; its score is **not** the specified evidence-based matching. The current /jobs GET endpoint and source_counts are provisional, not the target API.
