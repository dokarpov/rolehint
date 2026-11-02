# RoleHint Evidence Inbox — Web-first / Claude / ChatGPT release gate
**2026-11-02 · EVC-1/EVC-2 feature PR #13 · NOT deployed or publicly connectable.**

## What has been implemented

- **Browser UI** at `/webapp/evidence.html`, linked from the existing web app. Black-and-white text-only `rolehint` branding, mobile-first. Capture selected text or preview a TXT/MD/JSON/CSV file locally; confirm before sending. User can inspect the source, correct the claim, approve as *self-reported*, reject, delete, filter and see status. Sensitive content is never placed in an API GET query or browser address.
- **Account-bound API** at `/web-api/evidence/candidates` with current web-account session, exact first-party Origin check for mutations, input limits, 1–5 batch proposals, account isolation and duplicate detection.
- **SQLite transactional evidence** in `backend/app/evidence_cloud.py`: candidates, audit history, atomic approve→user_evidence→FTS5, rejection and delete→FTS5. Approval NEVER marks source as independently verified; source statements remain `needs-review` in the existing evidence system.
- **OAuth 2.1 authorization** in `backend/app/evidence_oauth.py` and routes: DCR, registered exact platform callbacks, PKCE S256, mandatory resource audience, code replay prevention, short-lived access/refresh tokens, rotating refresh, explicit scoped consent and revocation. Server stores only token hashes. On mobile/browser, signed-out assistant connection is restored after email magic-link login through one-time, expiring login ticket, and still requires explicit Allow.
- **Remote MCP v2** at `/mcp` (enabled only if `CFA_REMOTE_MCP_ENABLED=1`), with tools for listing metadata, viewing one user-owned draft, proposing private/unverified source-backed claims and opening the review page. No tool can approve, verify, submit applications, scan computer files or fetch entire ChatGPT/Claude chat histories.
- **CI evidence:** `.github/workflows/backend-release-gate.yml` runs SQLite ownership/FTS/CSRF, OAuth and hosted MCP lifecycle tests. `.github/workflows/release-qa.yml` runs responsive Evidence Inbox browser fixtures at 320, 375, 390, 430, 768, 1440 px. Record actual run IDs and status on the PR, not assumptions.

## How it should work for a user once staged and approved

1. Open **RoleHint → Evidence** in any browser (phone or desktop). Sign in with the working email/Telegram option and see the private inbox.
2. Select a relevant passage from a conversation or document and paste it into the Capture form; or choose a local small text file and inspect its preview. Add project, claim and source reference; choose Save privately. A chat model's statement is only a draft, not proof of ownership.
3. Review the source and claim. Approve as self-reported, reject or delete. To support a factual résumé claim, confirm provenance and ownership using real source records.
4. Once remote connector is actually deployed: copy the displayed HTTPS `/mcp` URL. In Claude web, use **Customize → Connectors → Add custom connector**, choose DCR/automatic registration if prompted, and approve only the indicated scopes. A Claude mobile user can subsequently use an already-connected remote connector; Claude's mobile app may not support first-time connector creation.
5. In eligible ChatGPT workspaces with custom MCP write permissions, add that same `/mcp` URL and authorize with RoleHint. If unavailable, use RoleHint's browser paste/file-import fallback: it provides value without any desktop extension.
6. Revoke an AI connection from the Evidence Inbox. Refresh/access tokens must stop working; previously approved evidence remains unless the user separately deletes it.

## Configuration (never enable this on the current production service)

- A **separate Railway staging environment and durable isolated volume** with synthetic/consented test records, not the service named staging inside the existing Railway environment `production`. Backup/restore drill required.
- `CFA_DATA_DIR` points to the isolated staging volume. Confirm `product_state.db` writable, FTS5 supported, and per-account isolation after restart.
- `CFA_WEB_APP_URL=https://<exact-staging-origin>` (no trailing slash, canonical HTTPS, public origin trusted). Set compatible response URLs. `CFA_REMOTE_MCP_ENABLED=1` **only in staging** after the other controls pass. Leave `CFA_REMOTE_MCP_DEV=0` except localhost test runs.
- Working email sign-in SMTP variables `CFA_SMTP_HOST` and `CFA_MAIL_FROM` (plus sender auth/port if needed), or a separately accepted browser sign-in. Do not present disabled login methods as functional.
- Run backend+browser QA on exact SHA **and** real HTTPS user-driven sign-in/OAuth/Claude connector smoke; do not rely only on simulation/fixture tests. Rate-limit/public OAuth client registration before open beta.
- Only after the complete real flow, account isolation, OAuth consent, revoke, deletion, mobile Safari, backups/rollback and founder review pass, consider a separate production rollout decision.

## Not shipped / open security and product limits

- No production deployment, no successful Claude account connection and no successful ChatGPT account connection have yet been observed.
- RoleHint cannot directly read the local computer, iCloud or complete AI chat history from a remote MCP server. Collection requires a selected passage/file or a separately authorized integration.
- ChatGPT custom write MCP availability is plan/workspace-dependent; don't market “one-click save from ChatGPT” to accounts where that capability is unavailable.
- No automatic proof verification, AI-truth scoring, confidential-work scanning, universal PDFs, ZIP export import or silent batch transfer. Existing approved visual design and CV/ATS flows must not be redesigned by this PR.
- Some source evidence and any manually exported material can be sensitive. Add retention policy, user export and deletion cascade tests before public onboarding, with privacy/security review.
- The current Docker/Railway staging-named service is not a verified isolated persistent production-like staging environment.
