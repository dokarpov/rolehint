"""Fast import-time contract for the standalone RoleHint HTTP allowlist."""
from app.http_boundary import allowed_beta_path


def test_public_surface_is_intentionally_small():
    public_paths = (
        "/health", "/open-bot", "/miniapp", "/miniapp/index.html",
        "/webapp", "/webapp/index.html", "/me/bootstrap",
        "/web-api/me", "/web-api/cv", "/telegram/auth",
        "/internal/telegram/123/ingest-url",
        "/oauth/google/callback", "/oauth/github/callback",
        "/downloads/short-lived-token",
    )
    assert all(allowed_beta_path(path) for path in public_paths)


def test_legacy_and_similar_prefixes_are_not_exposed():
    legacy_paths = (
        "/", "/docs", "/openapi.json", "/evidence", "/evidence/upload",
        "/jobs/search", "/subscriptions/run-due", "/tasks", "/contacts",
        "/me", "/web-api", "/webapp-leak", "/miniapp-leak",
        "/internal/telegram", "/downloads", "/oauth/debug", "/mcp",
    )
    assert all(not allowed_beta_path(path) for path in legacy_paths)
