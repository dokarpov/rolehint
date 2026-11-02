# RoleHint Evidence Inbox — isolated Railway staging rollout

**Status 2026-11-02: BLOCKED by Railway plan capacity.** An actual attempt to create
`rolehint-evidence-staging` in the user's personal Railway workspace was rejected:
`Free plan resource provision limit exceeded. Please upgrade to provision more resources!`.
**No new Railway project/service/volume was created. No existing production
service or volume was changed.** Never "solve" this by attaching an empty volume
over the production `/app/data` or by enabling MCP in the existing production
environment.

## GitHub-owned source and guardrails

- Working draft: [PR #13](https://github.com/dokarpov/rolehint/pull/13), source branch
  `feature/evidence-cloud-inbox-20261102` into
  `feature/value-first-onboarding-20261021`. Production/main are not targets.
- All source/QA/plan files are committed; CI checks content+tracking and uploads
  `evidence-release-inventory-{sha}` with the **full immutable commit SHA** and
  individual file hashes (not a claim of deployment).
- `.github/workflows/backend-release-gate.yml`: backend, OAuth code→MCP tool
  →private evidence, revocation, SQLite backup/restore, FTS and write race tests.
- `.github/workflows/release-qa.yml`: Chromium **and** WebKit responsive browser
  fixture journeys. WebKit approximates Safari, not a physical iPhone acceptance.
- `.github/workflows/evidence-staging-preflight.yml`: manual HTTP verification of
  **only a new Railway staging domain**, refusing old staging/production URLs.

## Infrastructure design — after plan capacity is available

1. Create a **separate private Railway project**, named
   `rolehint-evidence-staging`, default environment `staging`, PR deploys off,
   in the same personal workspace. Distinct project ensures environment variables
   and internal services are not shared with RoleHint production.
2. Create a fresh `rolehint-evidence-web` service sourced from
   `dokarpov/rolehint`, branch `feature/evidence-cloud-inbox-20261102`, pinned
   to an exact **successful backend+WebKit CI** SHA. Never deploy `main` or an
   untested HEAD automatically.
3. Use Dockerfile `backend/Dockerfile` (repository root build context), health
   `/health`, **one replica**, no public bot or background worker. Start command:
   `sh -c 'exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"'`.
   Restrict repository watchers/deploy triggers to owner-approved changes.
4. Create a **new staging-only persistent 500 MB (or plan-minimum) volume** at
   `/app/data` *before the first test-user record is created*. Set
   `CFA_DATA_DIR=/app/data`, then confirm data persists through restart,
   rebuild/redeploy and actual online backup→restore into disposable storage.
   Never copy production CVs, email addresses, SQLite DBs or secrets.
5. Generate one HTTPS `*.up.railway.app` domain for that new service. Configure
   `CFA_WEB_APP_URL` to this exact canonical public origin, no trailing slash.
   Set nonsecret variables from
   [evidence-staging.env.example](../evidence-staging.env.example).
6. Configure **dedicated test-only SMTP** `CFA_SMTP_HOST`,
   `CFA_SMTP_PORT`, `CFA_MAIL_FROM`, and any auth credentials required, only
   via Railway protected environment variables. Test delivery to a synthetic
   controlled inbox; do not log email magic links. Browser email login is not
   operational without these settings.
7. Set `CFA_PUBLIC_BETA_LOCK=1`, `CFA_SEED_DEMO=0`,
   `CFA_ALLOW_ANONYMOUS_SELFHOST=0`, `CFA_REMOTE_MCP_DEV=0`, and only in
   this staging service `CFA_REMOTE_MCP_ENABLED=1`. No Telegram
   bot credentials, real ATS credentials, or production OAuth token copies.
8. Deploy/pin the **exact CI tested** commit. Verify Railway lists the matching
   Git SHA; service URL and /health alone cannot prove source parity.
9. Run GitHub Actions **Evidence staging HTTPS preflight (read-only)** on the
   new domain. Its HTTP success explicitly **does not** imply the release passed.
10. With authorized staging test accounts, verify the full user sequence:
    browser email link → original request preserved → OAuth consent → Claude
    remote MCP → private unverified draft → RoleHint browser review → FTS
    consistency → revoke → old access and refresh rejected. Repeat in an
    eligible ChatGPT workspace; unsupported write access must use manual
    capture, not fictitious auto-save.
11. Test desktop browser, **physical iPhone Safari**, network interruption,
    expired/replayed email links, user separation, quota/rate limiting, account
    deletion and DB volume restart/backups. Confirm PII stays off public logs
    and user data cannot leak between accounts.
12. Publish a source/deployment/test evidence sheet with full Git SHA,
    Railway service+environment+volume IDs, CI links, sanitized timestamps,
    SMTP configured status, exact tested domains and all open issues. Owner
    signs off before any PR promotion or production deployment.

## Release/no-go table

| Gate | Evidence required | Current |
|---|---|---|
| Complete Git source | Compare PR branch to base, CI per-file SHA manifest | CI automated; confirm latest SHA |
| Backend safety | SQL/FTS backup/recovery, OAuth PKCE and MCP regression suites | Implemented in CI |
| Browser UX | Chromium + WebKit at phone/tablet/desktop widths | Implemented in CI |
| Isolated staging | Separate private project/env, one dedicated volume | **BLOCKED: Railway free plan resource cap** |
| Real login | Dedicated working SMTP, email-link replay, true browser session | **NOT TESTED against Railway** |
| Real hosted MCP | Claude and eligible ChatGPT OAuth, consent, revocation | **NOT TESTED against accounts** |
| Real device | iPhone Safari + desktop runtime | **NOT TESTED** |
| Recovery | Real volume backup, restore, restart, migration rollback | **NOT TESTED on Railway** |
| Public release | Security, accessibility, no high-severity open issues, owner approval | **BLOCKED; production untouched** |

### Cost and permissions

New Railway services and persistent volumes can incur usage charges. The user's
free resource cap currently prevents provisioning; only the user can upgrade the
workspace plan or free resources deliberately. **Do not automatically delete
the old staging service**, reuse or detach the production database volume, or
upgrade billing. Once resources are available, deploy staging only and verify
all release gates before seeking approval for production.
