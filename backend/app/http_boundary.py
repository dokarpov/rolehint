"""Public HTTP boundary for the RoleHint FastAPI service.

Keep authorization separate: paths in this allowlist must still enforce their
own Telegram identity, browser session, internal secret or capability token.
No environment flag may re-enable the legacy unauthenticated API.
"""
from fastapi import Request
from fastapi.responses import Response

def allowed_beta_path(path: str) -> bool:
    """Small, reviewed HTTP surface. All legacy handlers remain closed on every deployment."""
    return (
        path in ("/health", "/open-bot", "/miniapp", "/webapp", "/telegram/auth",
                 "/oauth/google/callback", "/oauth/github/callback")
        or path.startswith(("/miniapp/", "/me/", "/web-api/", "/webapp/",
                            "/internal/telegram/", "/downloads/"))
    )


async def beta_access_guard(request: Request, call_next):
    """Deny legacy unauthenticated routes regardless of environment flags.

    The old CFA_PUBLIC_BETA_LOCK could be unset or accidentally set to 0 on a
    publicly reachable server. No environment variable now disables this boundary.
    Internal bot requests and export downloads retain their own secret/token checks.
    """
    if not allowed_beta_path(request.url.path):
        return Response(
            content='{"detail":"RoleHint legacy API is unavailable"}',
            media_type="application/json",
            status_code=503,
            headers={"Cache-Control": "no-store"},
        )
    return await call_next(request)

