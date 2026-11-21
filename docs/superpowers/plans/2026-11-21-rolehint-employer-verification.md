# RoleHint Employer Verification and Continuity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Each task uses test-first changes and a separate validation gate.

**Goal:** Deliver up to ten genuinely eligible, employer-sourced opportunities with accurate application continuity and no unsupported verification claims.

**Architecture:** Preserve the existing FastAPI, HTTPX, SQLite, ATS adapters, product-state store, and verified web session path. Add source verification and status gates at existing adapter/service boundaries; preserve one canonical employer record and retain all secondary-source provenance. Keep cross-user access scoped to the authenticated account.

**Tech Stack:** Python 3.12, FastAPI, HTTPX, SQLite, pytest, existing GitHub Actions; no new paid service.

**Spec:** `docs/PRODUCT_EXPERIENCE_V1.md`, `docs/DECISION_POLICY.md`, `docs/RELEASE_ROADMAP.md`.

## Global Constraints
- Preserve user-selected distinctive CV designs; adapt verified content without inventing achievements.
- Do not automatically submit applications or advertise nonworking autofill.
- Unknown eligibility is VERIFY_FIRST, not eligible or disqualified.
- Public launch requires production E2E, not only mocked tests.
- Do not merge into main or deploy until release acceptance and production recovery are verified.

## Review Focus
- Spoofed ATS hostname: reject both discovery qualification and handoff; test URL lookalikes.
- Employer job expires after discovery: stop handoff based on authoritative recheck, never cached status.
- ATS API times out or returns malformed data: treat as unknown, do not display a false empty-list success.
- Aggregator and employer listing collide: employer description and requisition ID win; preserve second-source citations.
- User changes device after submitting: state is persisted to the right account with no duplicate submitted event.

---

### Task 1: Employer-source evidence and deduplication (implemented in PR #20; release gate pending)
**Files:** `backend/app/services/employer_source_preflight.py`, `backend/app/services/job_sources/source_evidence.py`, `backend/app/services/jobs.py`, ATS source adapters, regression tests.
**Interfaces:** `preflight_employer_source(job, *, now=None, max_age_seconds=21600)` returns decision + reason; `dedupe(jobs)` returns canonical jobs with source provenance.
- [x] Write failing tests for ATS URL/domain spoofing, freshness, and provider precedence.
- [x] Implement fail-closed, timestamped URL/source checks and prefer direct ATS records.
- [x] Add unit and route regression tests and commit to the isolated feature branch.
- [ ] Confirm all branch CI jobs except known production smoke gate pass.

### Task 2: Live ATS recheck immediately before delivery/handoff
**Files:** `backend/app/services/job_sources/`, `backend/app/web_release.py`, `tests/test_web_release.py`.
**Interfaces:** Async provider-specific lookup by trusted board + requisition ID; return open/closed/unknown and provider evidence timestamp.
- [ ] RED: offline HTTPX transport tests for 200, 404/removed, timeout, wrong ID and malicious redirect.
- [ ] GREEN: add provider-specific rechecks for Ashby, Lever, Greenhouse; do not infer work authorization from remote flags.
- [ ] Link to review + handoff; report and block closed or unsupported sources without claiming actual submission.
- [ ] Test production-like backend flows and genuine ATS links without submitting applications.

### Task 3: Accurate free delivery and state continuity
**Files:** `backend/app/web_release.py`, existing `product_state/store.py`, dedicated tests.
**Interfaces:** Count only delivered qualified opportunities; retain unknown status separately; record handoff/submission/outcome transitions per user.
- [ ] RED: zero results, fewer-than-ten, stale quota, duplicate requisition, rejected employer and cross-session persistence.
- [ ] GREEN: atomic delivered ledger on existing persistence; no quota charge for unverified/duplicate vacancy.
- [ ] Cross-account/expiry/delete tests and mobile flow validation.

### Task 4: Identity/CV and production acceptance
**Files:** existing web identity, CV store, browser UI and test matrix.
- [ ] Validate Telegram OTP on actual iPhone and desktop; cross-account session security.
- [ ] Verify CV import, source attribution, revisions, and cross-device restore.
- [ ] Keep distinctive visual CV templates and machine-readable PDF/DOCX content paths.
- [ ] Complete Oracle Cloud Always Free cutover per PR #17 only after encrypted Railway exports, verified restore, preserved SQLite volume data, OCI VM availability, and verified zero paid resources; smoke test the new backend. Do not restart Railway merely to satisfy legacy smoke checks.

## Hosting migration dependency (PR #17)
RoleHint's selected destination is Oracle Cloud Always Free A1 VM hosting the existing FastAPI/SQLite stack, **not a new database engine**. The migration preparation PR is `chore/free-vm-migration-backup-20261110` (#17). Its offline volume export and restore tools exist but **no real source data has been exported or restored, no Oracle VM is provisioned/connected, and no cutover occurred**. Changes in this PR (#20) are application code only and MUST be integrated into the Oracle deployment build after the source backup verification. Do not replace or overwrite production SQLite volumes. Only one Telegram polling process may run after cutover.

## Current deployment blocker (21 November 2026)
GitHub Actions backend test passed on PR #20, while `deployed-smoke` failed with HTTP 404 at `https://rolehint-api-worker-production.up.railway.app/health`. Railway confirms the latest listed production and staging deployments are REMOVED (30 October and 4 November). Do not claim this PR is released or the service is online.

## Dependency decision
Reuse existing FastAPI + HTTPX + SQLite and provider ATS endpoints; no new external service, new payment integration, proprietary reverse-engineered code, or third-party copied code is needed for Tasks 1-3. If adopting open-source code later, check SPDX license, attribution and compatibility before copying it.
