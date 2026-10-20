"""First-party web login through the existing Telegram bot: no email provider necessary."""
import uuid
from urllib.parse import urlsplit,parse_qs
from fastapi.testclient import TestClient
from app.main import app
from app import web_identity

BASE="https://rolehint.example"

class BotResponse:
    def raise_for_status(self):pass
    def json(self):return {"ok":True,"result":{"username":"rolehint_test_bot"}}

class BotClient:
    def __init__(self,*args,**kwargs):pass
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    async def get(self,url):return BotResponse()

def test_telegram_code_is_same_account_cross_device_and_one_use(monkeypatch):
    monkeypatch.setenv("CFA_WEB_APP_URL",BASE)
    monkeypatch.setenv("CFA_INTERNAL_BOT_SECRET","test-bot-internal-secret")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN","123456:test")
    monkeypatch.setattr(web_identity.httpx,"AsyncClient",BotClient)
    identity=8500000+int(uuid.uuid4().int%1000000)
    with TestClient(app,base_url=BASE) as a, TestClient(app,base_url=BASE) as b:
        assert a.post("/web-api/telegram/begin").status_code==403
        a_start=a.post("/web-api/telegram/begin",headers={"Origin":BASE},json={})
        assert a_start.status_code==200,a_start.text
        state=parse_qs(urlsplit(a_start.json()["url"]).query)["start"][0].removeprefix("web_")
        assert a.get("/web-api/me").status_code==401
        failed=a.post("/web-api/telegram/complete",headers={"Origin":BASE},json={"code":"11111111"})
        assert failed.status_code==401
        issued=a.post("/web-api/telegram/bot-issue",headers={"X-CFA-Bot-Secret":"test-bot-internal-secret"},
                       json={"state":state,"telegram_user":{"id":identity,"first_name":"QA"}})
        assert issued.status_code==200,issued.text
        otp=issued.json()["code"]
        assert len(otp)==8
        assert b.post("/web-api/telegram/complete",headers={"Origin":BASE},json={"code":otp}).status_code==401
        assert a.post("/web-api/telegram/complete",headers={"Origin":BASE},json={"code":otp}).status_code==200
        assert a.get("/web-api/me").status_code==200
        assert a.post("/web-api/telegram/complete",headers={"Origin":BASE},json={"code":otp}).status_code==401
        assert a.put("/web-api/preferences",headers={"Origin":BASE},json={"remote_only":True,"salary_floor_annual":85000}).status_code==200
        b_start=b.post("/web-api/telegram/begin",headers={"Origin":BASE},json={})
        state2=parse_qs(urlsplit(b_start.json()["url"]).query)["start"][0].removeprefix("web_")
        issued2=b.post("/web-api/telegram/bot-issue",headers={"X-CFA-Bot-Secret":"test-bot-internal-secret"},
                        json={"state":state2,"telegram_user":{"id":identity,"first_name":"QA"}})
        assert issued2.status_code==200,issued2.text
        assert b.post("/web-api/telegram/complete",headers={"Origin":BASE},json={"code":issued2.json()["code"]}).status_code==200
        assert b.get("/web-api/me").json()["preferences"]["salary_floor_annual"]==85000
        assert a.post("/web-api/logout",headers={"Origin":BASE},follow_redirects=False).status_code==303
        assert a.get("/web-api/me").status_code==401
        assert b.get("/web-api/me").status_code==200

def test_bot_issue_requires_shared_secret(monkeypatch):
    monkeypatch.setenv("CFA_INTERNAL_BOT_SECRET","test-bot-secret")
    with TestClient(app,base_url=BASE) as client:
        assert client.post("/web-api/telegram/bot-issue",json={"state":"invalid"}).status_code==401
