# RoleHint — Evidence Inbox staging release gate (existing Railway project)

**Staging service:** `rolehint-staging` (`ad8e16ed-d9ec-415d-815b-2b5c75ef57e6`) in the existing RoleHint Railway project (`e48095fc-fb0f-4e59-bf34-d30418e5198f`), environment `production` (`40688d3e-9562-44c7-8431-3ce9c9687601`). Although Railway calls the shared environment *production*, this is a distinct staging **service**, code deployment and SQLite volume.

**Production service:** `rolehint-api-worker` (`dab3aee6-c85d-4177-b7ac-16a019a09eed`). Its volume `7035a583-3c98-48db-9ce6-4fb2258ee1f6` at `/app/data` must never be mounted on staging or otherwise modified.

**Staging volume:** `rolehint-staging-sqlite` (`0d78adb0-26cb-40fb-a425-dc05e594836a`) provisioned as 500 MB **inside the same Railway project** on 2026-11-02; attach only to `rolehint-staging` at `/app/data`. Do not claim the release is persistent until the mount and restart checks are observed.

## Separation rules

1. Reconfigure **only** `rolehint-staging`. Any staging patch must be examined with `get_staged_changes` before accepting because the parent Railway environment is also used by the production API. Never stage or set environment-wide/group variables.
2. Pin source to exact successful GitHub CI commit from [draft PR #13](https://github.com/dokarpov/rolehint/pull/13), branch `feature/evidence-cloud-inbox-20261102`. Do not change production `main` or its source trigger. Keep the PR in draft.
3. Set service-scoped `CFA_DATA_DIR=/app/data`, `CFA_PUBLIC_BETA_LOCK=1`, `CFA_SEED_DEMO=0`, `CFA_ALLOW_ANONYMOUS_SELFHOST=0`, `CFA_RUNTIME_MODE=selfhost`, `CFA_REMOTE_MCP_ENABLED=1`, `CFA_REMOTE_MCP_DEV=0` and `CFA_WEB_APP_URL=https://rolehint-staging-production.up.railway.app`. Never copy production Telegram, ATS, SMTP, OAuth or other secrets to staging.
4. Use repository `backend/Dockerfile` with root context and start **API only**, no background job worker or Telegram bot: `uvicorn app.main:app --host 0.0.0.0 --port 8080`. One replica, healthcheck `/health`, existing domain target port 8080.
5. The old staging service had **no volume**; its ephemeral testing records may be lost when the newly provisioned volume is mounted. Do not pretend its ephemeral files were backed up. New consented staging data must persist after restarts.
6. The new volume cannot be shared with production or used as a copy of production SQLite. Maintain distinct accounts and synthetic/consented evidence only. Do not enable auto-production deployments.
7. Use dedicated test-only SMTP credentials only after verifying the provider and domain; `CFA_SMTP_HOST`, `CFA_MAIL_FROM`, optional SMTP username/password must be stored as staging **service** variables, never in GitHub. Until then actual email link sign-in is **blocked**, even if automated email-link tests pass.
8. A successful /health, browser fixture or unauthenticated MCP challenge is **not** sufficient for end-user launch.

## Ordered deployment verification

1. Confirm draft PR head, backend tests, WebKit/Chromium browser QA and per-file Git SHA inventory pass.
2. Stage source, variables, start command and dedicated SQLite mount against only `rolehint-staging`. Inspect staged patch to ensure **no production service/source/volume/variable** appears.
3. Apply the staging patch and verify actual Railway deployed SHA matches the exact pinned tested Git commit. Check the production API deployment ID remains unchanged.
4. Check `/health`, `/webapp/evidence.html`, unauthenticated `/web-api/evidence/candidates` (must return 401), `/.well-known/oauth-protected-resource/mcp`, OAuth metadata and unauthenticated MCP (must return 401). Use the manual read-only [preflight workflow](../.github/workflows/evidence-staging-preflight.yml) targeting only `https://rolehint-staging-production.up.railway.app`.
5. Verify new volume appears attached exclusively to staging. Test SQLite recovery against actual staging storage, including restart and online backup to a disposable test copy, **without copying production data**.
6. Configure SMTP for a controlled test mailbox. Test real email magic link and full signed-out OAuth→email→consent→Claude/ChatGPT remote MCP→private draft→review→revoke journey; no public self-reported claims are externally verified.
7. Test actual iPhone Safari, timeouts, disconnected network, token replay, two-user isolation, duplicate evidence and sensitive-data removal. Browser WebKit CI is an approximation, not proof of real-device acceptance.
8. Founder approves separately before any move to production. Production remains unchanged throughout.

## Automated evidence

- `.github/workflows/backend-release-gate.yml`: existing API tests, OAuth PKCE, hosted MCP, SQLite FTS, backup/restore, racing writes, crash rollback, registration rate limit and Git file inventory. Green CI is code evidence **only**.
- `.github/workflows/release-qa.yml`: responsive Chromium and WebKit tests for the browser Evidence Inbox across mobile/tablet/desktop widths.
- `.github/workflows/evidence-staging-preflight.yml`: explicitly limited to the existing staging service domain; always refuses the production API domain. Its "PASS" does not override the real staging volume/SMTP/E2E blockers.
- `scripts/verify_rolehint_evidence_release.py`: every required source file tracked at the immutable Git SHA, artifact uploaded to GitHub Actions, distinguishes PR merge-test SHAs from pinned branch SHA.
- `deploy/evidence-staging.env.example`: nonsecret staging-only configuration template.

### Gate ledger

| Gate | Acceptance |
|---|---|
| GitHub source | Full SHA, tracked file manifest and CI green |
| Staging deployment | Railway service `rolehint-staging` runs exact pinned commit; production deployment unchanged |
| Persistence | Staging's own volume mounted, restart + backup/restore actually validated |
| Browser | Chromium + WebKit tests green; physical iPhone Safari still requires manual validation |
| Authentication | Real staged email link delivery, expired links, OAuth consent and revocation |
| Claude / ChatGPT | Real connector registration and first-party account integration tested; some ChatGPT capabilities depend on plan |
| Release | User approval, rollback runbook and no critical open gaps |

**No automatic production merge/deploy.** Hosting staging within the same Railway project is adequate as long as service identities, volumes, secrets and deployments remain separate; it is not equivalent to full isolation at the Railway environment level.
