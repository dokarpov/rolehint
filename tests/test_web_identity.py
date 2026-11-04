"""Web account contract: real session lifecycle, saved settings, CSRF, replay and isolation."""
from urllib.parse import urlsplit,parse_qs
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app import web_identity

def test_web_magic_link_identity_and_persistence(monkeypatch):
    base="https://rolehint.example"
    monkeypatch.setenv("CFA_WEB_APP_URL",base)
    monkeypatch.setenv("CFA_SMTP_HOST","smtp.example")
    monkeypatch.setenv("CFA_MAIL_FROM","login@rolehint.example")
    sent=[]
    monkeypatch.setattr(web_identity,"send_email",lambda email,url,host,sender:sent.append((email,url)))
    with TestClient(app,base_url=base) as browser:
        assert browser.get("/web-api/me").status_code==401
        assert browser.post("/web-api/login",json={"email":"a@example.com"}).status_code==403
        email="qa-"+uuid.uuid4().hex+"@example.com"
        r=browser.post("/web-api/login",headers={"Origin":base},json={"email":email})
        assert r.status_code==200,r.text
        assert len(sent)==1
        callback=urlsplit(sent[0][1]);token=parse_qs(callback.query)["token"][0]
        first=browser.get(callback.path,params={"token":token},follow_redirects=False)
        assert first.status_code==303
        assert first.headers["location"]=="/webapp/"
        assert "httponly" in first.headers["set-cookie"].lower()
        assert "secure" in first.headers["set-cookie"].lower()
        assert browser.get(callback.path,params={"token":token}).status_code==400
        assert browser.get("/web-api/me").status_code==200
        assert browser.put("/web-api/preferences",json={"remote_only":True}).status_code==403
        r=browser.put("/web-api/preferences",headers={"Origin":base},json={"remote_only":True,"salary_floor_annual":85000})
        assert r.status_code==200,r.text
        assert browser.post("/web-api/search",headers={"Origin":base},json={"query":"Senior Product Manager"}).status_code==200
        saved=browser.get("/web-api/me").json()
        assert saved["preferences"]["remote_only"] is True
        assert saved["preferences"]["salary_floor_annual"]==85000
        assert any(p["query"]=="Senior Product Manager" for p in saved["search_profiles"])
        assert browser.post("/web-api/logout",headers={"Origin":base},follow_redirects=False).status_code==303
        assert browser.get("/web-api/me").status_code==401

def test_web_auth_closed_without_mail_transport(monkeypatch):
    monkeypatch.delenv("CFA_SMTP_HOST",raising=False)
    with TestClient(app,base_url="https://rolehint.example") as client:
        r=client.post("/web-api/login",headers={"Origin":"https://rolehint.example"},json={"email":"person@example.com"})
        assert r.status_code in (403,503)

def test_auth_status_advertises_only_really_configured_sign_in_providers(monkeypatch):
    base="https://rolehint.example"
    monkeypatch.setenv("CFA_WEB_APP_URL",base)
    for key in ("CFA_SMTP_HOST","CFA_MAIL_FROM","TELEGRAM_BOT_TOKEN","CFA_INTERNAL_BOT_SECRET"):
        monkeypatch.delenv(key,raising=False)
    with TestClient(app,base_url=base) as client:
        none=client.get("/web-api/auth-status")
        assert none.status_code==200
        assert none.json()=={"email_login_available":False,"telegram_login_available":False}
        assert none.headers["Cache-Control"]=="no-store"
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN","123456:non-production-fixture")
        # A token alone cannot complete a Telegram challenge without the
        # bot-to-backend secret. Do not advertise a dead-end sign-in option.
        assert client.get("/web-api/auth-status").json()["telegram_login_available"] is False
        monkeypatch.setenv("CFA_INTERNAL_BOT_SECRET","test-only-callback-secret")
        telegram=client.get("/web-api/auth-status").json()
        assert telegram=={"email_login_available":False,"telegram_login_available":True}
        assert "123456" not in str(telegram)
        monkeypatch.setenv("CFA_SMTP_HOST","smtp.example")
        monkeypatch.setenv("CFA_MAIL_FROM","staging@rolehint.example")
        both=client.get("/web-api/auth-status").json()
        assert both=={"email_login_available":True,"telegram_login_available":True}
        monkeypatch.delenv("CFA_INTERNAL_BOT_SECRET")
        only_email=client.get("/web-api/auth-status").json()
        assert only_email=={"email_login_available":True,"telegram_login_available":False}
