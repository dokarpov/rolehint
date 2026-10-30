# RoleHint × Dossier — capability comparison and development decision

**Date:** 2026-10-30. **Reference:** [AienTech/dossier](https://github.com/AienTech/dossier) (AGPL-3.0). This note contains original analysis only; no Dossier code has been copied.

## Why not clone Dossier into the existing RoleHint backend?

Dossier is a strong self-hosted, single-person desktop workflow: one profile, job finding, 12 document themes, AI-assisted tailored CV/cover letter drafting, editable revisions, Gmail/Calendar connectors and a board. RoleHint already has a different stack and stronger eligibility/evidence distinctions, but a weaker end-to-end presentation and document-writing experience.

- **License:** Dossier uses GNU AGPL v3. A modified hosted version must meet its network-source obligations. This PR implements the *concept* of an application board independently, rather than mixing Dossier source into RoleHint.
- **Architecture:** Dossier uses a Next.js + PostgreSQL single-user deployment. RoleHint's public web is FastAPI + authenticated SQLite product store, a Telegram bridge and direct employer ATS sources. Wholesale transplantation would duplicate user and application state.
- **Mobile:** Dossier describes the main app as desktop-only; RoleHint must keep an accessible iPhone-sized workflow.
- **Truthfulness:** RoleHint separates known eligibility, self-reported CV claims, verification, saved draft, employer handoff and confirmed application. Do not turn all of them into a single AI-generated match percentage.

## Capability inventory (as of 30 Oct 2026)

| Capability | Dossier | RoleHint before this PR | Recommended treatment |
| --- | --- | --- | --- |
| User profile, PDF/DOCX parsing | Profile & import | Saved CV and raw evidence | Improve structured, editable profile; version original and claims |
| Job search | JSearch, Adzuna, startups, manual posting | ATS search + location constraints; URL ingest mainly Telegram | Keep ATS as primary; secure manual capture with allowlist, SSRF protection and clear unverified origin |
| Fit diagnosis | Match and missing requirements | Constraint + evidence + gaps | Keep RoleHint's decision split; expose personal contribution and sources |
| Job agent | Optional scheduled sourcing | Scheduler/search profiles | Enforce duplicate/rejection suppression, stable IDs and delivery quota |
| Tailored CV, letters | Themes, AI editing, PDF | Markdown evidence pack; no fully styled PDF CV | Introduce single-page PDF/DOCX pipeline with stable template and human approval after core release |
| Status board | Draft → offer dashboard | Individual handoff/outcome fields, no concise pipeline | **This PR** adds true application board, filters, per-job review and safe CSV export |
| Gmail/Calendar | Optional inbox + interviews | Connector scaffolding and Gmail event timeline | Release only after OAuth, consent, identity checks and deduped event audit |
| Security/privacy | Self-host one password | Separate web/Telegram identities | Prioritize tests and session/device isolation before wide rollout |

## Slice implemented here — Applications command center

The signed-in web workspace presents a chronological, readable application pipeline without a new database, external requests, or fabricated records.

- GET `/web-api/application-board` is authenticated and scoped by user; only minimal job metadata is sent. No CV text, document content, Gmail, API keys, or connector tokens.
- Stage precedence: confirmed submission and response > opened employer form > draft pack > review.
- Data from existing `user_jobs`, `application_submissions`, `web_application_handoffs`, `application_packs`; changing outcomes stays behind the existing `PUT /jobs/{job_id}/outcome` and the manual submit confirmation.
- Mobile-first table-like rows, simple stage filter, local search and CSV download. CSV cells starting with formula characters are escaped to reduce spreadsheet formula injection.
- Includes tests for cross-user isolation and no false submit; published backend release gate includes them.
- No email is sent; no employer form is submitted. Existing private beta lock remains.

## Next slices — acceptance-driven, not speculative

**P0: close private-beta release gaps before exposing public data.** Do real Telegram login on iPhone/desktop, CV correction and evidence ownership, live ATS employer URL, cross-device persistence and logged-out privacy. Verify Railway secret rotation separately.

**I2: Import a posting safely.** A user can paste a job description or direct URL and see its claimed source, its verification state, original URL, duplicate status and salary/geo uncertainties. No server-side fetching of arbitrary untrusted URLs: implement DNS/IP/redirect SSRF controls, rate limits and explicit consent before network requests. User-pasted text is labeled unverified, and does not reduce the quota.

**I3: Evidence-based document kit.** Canonical user profile, section-level fact provenance; editable tailored CV (single page by default), cover letter and form answers. No made-up impact metrics. PDF and DOCX files should have typography QA and controlled revisions; 12 generic themes are less valuable than one reliable one.

**I4: Replies + interviews.** User-authorized Gmail read; AI suggestions as drafts; reply and calendar modifications require explicit confirmation. Link by employer domain + requisition + thread ID and never infer confirmed interview from a generic autoresponder.

**I5: New sources & agent.** Adzuna/JSearch if configured and licensed. Personal job-agent suggestions with data timestamps, country eligibility and stable deduplication; never auto-apply or claim user confirmation.

**I6: Measurement.** Funnel from genuine stored stages, by job source and format; latency and user-visible errors; guardrails for rejection/duplicate rates, privacy and false-positive eligibility.

## Test plan and release status

- Unit tests: stage order, pack/handoff distinction, correct response precedence, output schema, nil states and isolation.
- Integration: logged-out API 401; 2 users with unrelated jobs; status history persists and edits via authorized endpoint.
- UI: iPhone 390px, narrow 320px, desktop 1440px; keyboard and label relationships, blank state, long titles, filter and CSV injection data.
- Platform: run GitHub release gate and inspect deployment smoke. **Do not merge or deploy before owner signs off** on the actual UI/browser acceptance.

**Known limitations:** the tracker is only as complete as the user's saved RoleHint records; it is not Gmail-based inbox sync, does not recover past external applications, and cannot produce a finished CV/PDF yet. The imported Dossier features above are roadmap references, not shipped claims.
