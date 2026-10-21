# RoleHint — Vacancy results, pagination and subscription entitlements v1.0

**Status:** approved product requirement recorded 2026-10-21; implementation and billing are not verified. This document governs the **results list** and overrides any implication that all plans have a permanent 10-result ceiling.

## Product promise
- **Free:** 10 lifetime *distinct qualifying opportunities delivered*, across searches and devices, as specified in PRODUCT_EXPERIENCE_V1.md. Never debit a credit for searching, viewing, refreshing, rejected/stale/duplicate jobs or source failures. A free user may see up to their remaining allowance, not a renewed 10 for each query.
- **Paid subscription:** **unlimited qualifying vacancies** across searches, pages, saved searches and recurring discovery, while subscription entitlement is active. No product-enforced lifetime/monthly vacancy-count cap. Results depend on actual market supply and provider availability. No promise that every query finds a minimum number.
- Same evidence-based relevance, eligibility filtering, deduplication and transparent explanations in both tiers. Do not reduce free ranking quality to force upgrades.
- Search page size is a performance choice (initially 20 cards for paid; server maximum 50), **not a quota**. Continue with next-page cursor or infinite scroll with accessible “Load more” fallback.

## Results screen contract (RESULT-01–08)
**RESULT-01 Entry and scope.** CV upload and role autocomplete are equal, visible first-screen entry points. User confirms target role(s), location/remote eligibility, employment/B2B preference and salary currency. No sign-in before first value. Role-only results visibly say CV evidence not assessed.

**RESULT-02 Card.** Each item displays title, employer, location and eligible work geography, remote/hybrid/onsite, employment model, salary and currency if published (otherwise unknown), posted/last-verified date, original employer apply link, supported CV evidence, material gaps, unknown eligibility, saved/applied state and concise reason for rank. Never fabricate missing fields or numeric fit percentages.

**RESULT-03 Sorting.** Default “Best fit”; optional newest, recently verified and salary where comparable. Hard disqualifications are filtered *before* ranking. Explain whether a card is verified open, source-reported open or unverified. User can broaden preferences without disabling mandatory legal/geographic constraints silently.

**RESULT-04 Filters.** Target role and aliases, seniority, remote geography, work authorization, employment/B2B, minimum salary + currency, sector, date, source, company, excluded/applied companies. Changing filters resets cursor, preserves CV analysis and displays updated result count where known.

**RESULT-05 Pagination.** Stable opaque cursor based on search snapshot + sort key + canonical ID. Backend deduplicates across page boundaries and sources. Cursor expires with a clear refresh flow; never return duplicates or silently skip newly ranked records. Paid can traverse all eligible discovered jobs. Return has_more and next_cursor; count may be unknown. Virtualize long lists and lazy-load expanded details.

**RESULT-06 Saved search.** Paid subscribers can save multiple role/filter combinations, rerun on demand and opt into notifications for newly qualifying unique vacancies. Newness is relative to previously delivered canonical IDs, not posting date alone. Subscription cancellation stops premium recurring discovery but retains legally permissible account history/export and any unused free entitlement.

**RESULT-07 States.** Distinct loading, partially sourced, zero verified matches, upstream outage, expired vacancy, invalid cursor, entitlement exhausted, payment inactive, retry and back-navigation. Never represent a provider outage as “no jobs”. On free entitlement exhaustion show saved results and upgrade invitation; do not lock existing records behind payment.

**RESULT-08 Privacy/accessibility.** Never send raw CV in GET query, browser URL, third-party provider request or analytics. Keep mobile 320–430px functional, accessible keyboard and screen-reader controls, no UI redesign unrelated to results. Telegram opt-in after the result list, only if operational.

## API and storage target
`POST /web-api/matches/search` with `{analysis_id?,roles,preferences,sort,page_size,cursor?}`.
Response: `{jobs,has_more,next_cursor,search_id,source_status,partial,eligible_count?,entitlement:{tier,free_remaining,unlimited},generated_at}`. Jobs include stable `canonical_id`, verification state, source and explainable match.
Server stores user-scoped `job_deliveries(user_id,canonical_id,first_delivered_at,entitlement_type)` with unique constraint; an atomic transaction checks the free limit, inserts only qualifying *new* deliveries, and returns already delivered jobs without debiting. Paid `unlimited=true` bypasses **count quota**, not abuse prevention or upstream API limits. Anonymous previews require a separately defined ephemeral entitlement strategy, not a fictional persisted free ledger.
Use short-lived snapshot or cache for stable pagination; source ingestion and ranking may run asynchronously, with explicit partial-state signaling. Prevent one user's saved CV/search/history from appearing to another.

## Billing semantics
Subscription active, trialing (if explicitly approved), past_due, canceled and expired must map deterministically to entitlements from verified Stripe webhook state; no client-supplied “paid” flag. Downgrade preserves previously delivered history and free balance, but new deliveries obey free allowance. Pricing, trials, payment and webhooks are **not** authorized or launched by this specification.

## Acceptance tests
1. Free account: 10 distinct valid deliveries across 3 searches and two devices; 11th blocked; refresh, stale job, duplicate, closed job and retry never debit.
2. Paid: 120+ unique verified fixture jobs across >=7 pages; all reachable with no quota-exhausted response, no duplicates, stable ordering and valid cursor behavior. Repeat on changed filters.
3. Paid with only 4 live matching jobs: show exactly 4, not 20/120 fabricated ones.
4. Upgrade and downgrade: server-authoritative entitlement, saved history persists, no double debit or leaked data; inactive payment prevents further premium delivery.
5. Rejected/applied employer history, source outages, mixed currencies, geography/B2B exclusions and source recency correctly reflected.
6. Actual staging desktop and iPhone browser: upload→results→load more→filter→open employer link; separately free exhaustion and paid unlimited pagination.
7. Real live-source smoke: verify accessible employer listings on multiple pages; record source, timestamp, deployment SHA, test evidence and human signoff. **Do not claim live acceptance from fixtures alone.**

## Dependencies and current gap
Depends on CV_JOB_MATCHING_SPEC_V1.md for extraction, evidence and ranking. Current anonymous GET endpoint returns max 10 per request, lacks account entitlement ledger, stable pagination, verified source freshness and paid subscription state. **Paid unlimited is specified but not implemented.**
