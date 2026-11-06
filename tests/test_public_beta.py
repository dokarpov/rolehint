"""Regression checks for anonymous access and unavailable OAuth integrations.

Run: CFA_PUBLIC_BETA_LOCK=1 CFA_ALLOW_ANONYMOUS_SELFHOST=0 pytest -q tests/test_public_beta.py
This is deliberately separate from signed Telegram identity tests.
"""
import os
os.environ["CFA_PUBLIC_BETA_LOCK"]="1"
os.environ["CFA_ALLOW_ANONYMOUS_SELFHOST"]="0"
from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)

def test_health_works_without_login():
    assert client.get("/health").status_code == 200

def test_unknown_user_cannot_read_profile():
    response=client.get("/me/bootstrap")
    assert response.status_code == 401

def test_unprotected_legacy_api_is_not_public():
    assert client.get("/evidence").status_code == 503

def test_miniapp_root_redirect_is_not_blocked():
    assert client.get("/miniapp",follow_redirects=False).status_code in (200,307,308)

def test_provider_connection_requires_identity_before_oauth():
    for provider in ("google","github"):
        assert client.post(f"/me/connectors/{provider}/start",json={}).status_code == 401

def test_invalid_google_oauth_state_is_rejected():
    response=client.get("/oauth/google/callback",params={"state":"invalid","code":"invalid"})
    assert response.status_code == 400

def test_invalid_github_oauth_state_is_rejected():
    response=client.get("/oauth/github/callback",params={"state":"invalid","code":"invalid"})
    assert response.status_code == 400

def test_signed_accounts_keep_preferences_separate(monkeypatch):
    from test_telegram_auth_release import BOT_TOKEN, signed_data
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    headers_a={"X-Telegram-Init-Data":signed_data(9100101)}
    headers_b={"X-Telegram-Init-Data":signed_data(9100202)}
    a=client.put("/me/preferences",headers=headers_a,json={"remote_only":True,"salary_floor_annual":90000})
    b=client.put("/me/preferences",headers=headers_b,json={"remote_only":False,"salary_floor_annual":40000})
    assert a.status_code == 200, a.text
    assert b.status_code == 200, b.text
    a_read=client.get("/me/preferences",headers=headers_a)
    b_read=client.get("/me/preferences",headers=headers_b)
    assert a_read.status_code == 200
    assert b_read.status_code == 200
    assert a_read.json().get("salary_floor_annual") == 90000
    assert b_read.json().get("salary_floor_annual") == 40000

def test_new_user_can_start_real_discovery_without_oauth(monkeypatch):
    from test_telegram_auth_release import BOT_TOKEN, signed_data
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    headers={"X-Telegram-Init-Data":signed_data(9111733)}
    response=client.post("/me/search-profiles",headers=headers,json={
        "query":"Senior Product Manager","countries":["Spain","Europe"],
        "remote_only":True,"enabled":True,"interval_minutes":360
    })
    assert response.status_code==200,response.text
    state=client.get("/me/bootstrap",headers=headers)
    assert state.status_code==200,state.text
    profiles=state.json()["autopilot"]["search_profiles"]
    assert any(p["query"]=="Senior Product Manager" for p in profiles)


def test_legacy_guard_remains_closed_when_beta_flag_is_missing_or_disabled(monkeypatch):
    # Before this fix, missing/0 disabled the entire HTTP boundary.
    for flag in (None, "0", "1"):
        if flag is None:
            monkeypatch.delenv("CFA_PUBLIC_BETA_LOCK", raising=False)
        else:
            monkeypatch.setenv("CFA_PUBLIC_BETA_LOCK", flag)
        for mode in ("selfhost", "managed"):
            monkeypatch.setenv("CFA_RUNTIME_MODE", mode)
            for method, path in (
                ("get", "/evidence"),
                ("get", "/evidence/search?q=private"),
                ("post", "/evidence/confirm/any"),
                ("post", "/jobs/search"),
                ("post", "/subscriptions/run-due"),
                ("get", "/docs"),
            ):
                response=getattr(client, method)(path)
                assert response.status_code == 503, (flag, mode, method, path, response.status_code)


def test_beta_public_boundaries_keep_auth_checks():
    assert client.get("/web-api/me").status_code == 401
    assert client.get("/downloads/does-not-exist").status_code == 404
    assert client.get("/health").status_code == 200
