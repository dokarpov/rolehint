# RoleHint HTTP boundary: default-deny legacy routes

Date: 2026-11-06 · Status: draft, awaiting CI and production configuration review.

## Confirmed code-level issue

Previously `beta_access_guard` enforced the public HTTP allowlist only when `CFA_PUBLIC_BETA_LOCK=1`. That setting defaulted to `0`, so legacy handlers such as `GET /evidence`, `POST /evidence/upload` and `POST /evidence/confirm/{id}` were reachable without individual authorization checks if the environment omitted the flag. This is a potential exposure, **not** a claim that live Railway was misconfigured or that any data leaked.

## Remediation

The HTTP allowlist now applies unconditionally. Environment flags, client IP, headers, or a reverse-proxy address cannot disable it. The retired routes remain in source for controlled migration, but are never externally served by this FastAPI app. Do not reintroduce an anonymous fallback for self-hosted traffic; migrate required functionality behind authenticated, user-scoped `/me/*` or `/web-api/*` APIs.

Allowed URL families:
- `/health`, `/open-bot` (public utilities);
- `/miniapp/*`, `/webapp/*` (static clients);
- `/me/*` (Telegram identity check in handlers);
- `/web-api/*` (first-party session / origin checks in handlers);
- `/internal/telegram/*` (separate internal bot secret check);
- `/oauth/google/callback`, `/oauth/github/callback` (state validation);
- `/telegram/auth` (signed Telegram init data);
- `/downloads/*` (random time-limited capability tokens issued only after authenticated export).

An allowlisted path is not automatically authorized. Handler-level checks remain mandatory. Export responses now set `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, and conservative attachment headers.

## Acceptance before production

1. CI: `tests/test_public_beta.py` must pass with `CFA_PUBLIC_BETA_LOCK` unset, `0`, and `1`, in both runtime modes.
2. Existing signed Telegram `/me/*`, web login, CV and application review tests must continue to pass.
3. Confirm no legitimate frontend still calls old `/evidence`, `/jobs/search`, `/subscriptions` or other legacy endpoints.
4. Inspect Railway environment/ingress and review logs without exposing tokens/CVs.
5. Test CV export capability URLs through a real signed-in session (success/expiry/no caching).
6. Review the draft PR and deploy only after explicit approval.

Not covered by this patch: full CV encryption, incident response, backups, account erasure, ATS freshness or public launch acceptance.
