"""P0 Google integration consent and scheduling tests; all users/messages synthetic."""
import asyncio,time,uuid
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import httpx
from fastapi.testclient import TestClient
from app.main import app,product
from app.web_identity import token_hash
from app.services.oauth.google import GoogleOAuth,WORKSPACE_SCOPES
from app.services.connectors.calendar import CalendarConnector

BASE="https://rolehint.example"

def session():
    uid=product.ensure_user(telegram_user={
        "id":90000000+int(uuid.uuid4().int%10000000),"first_name":"Google QA"})
    token="oauth-"+uuid.uuid4().hex+uuid.uuid4().hex
    product.conn.execute("INSERT INTO web_sessions VALUES(?,?,?,?)",
        (token_hash(token),uid,time.time()+3600,time.time()))
    product.conn.commit()
    return uid,token

def test_google_scopes_are_narrow_and_explicit():
    assert "https://www.googleapis.com/auth/gmail.readonly" in WORKSPACE_SCOPES
    assert "https://www.googleapis.com/auth/calendar.events" in WORKSPACE_SCOPES
    assert not any("drive." in x or "gmail.modify" in x or "gmail.send" in x for x in WORKSPACE_SCOPES)
    google=GoogleOAuth(client_id="test-client",client_secret="test-secret",
        callback_url=BASE+"/oauth/google/callback")
    url=google.authorize_url("opaque-state",scopes=WORKSPACE_SCOPES)
    assert "calendar.events" in url and "gmail.readonly" in url
    assert "drive.readonly" not in url
    assert "client_secret" not in url

def test_web_google_routes_require_real_account_and_explicit_origin(monkeypatch):
    import app.main as main
    uid,token=session()
    other,other_token=session()
    with TestClient(app,base_url=BASE) as client:
        assert client.get("/web-api/google/status").status_code==401
        assert client.get("/web-api/google/calendar").status_code==401
        client.cookies.set("rh_session",token)
        status=client.get("/web-api/google/status")
        assert status.status_code==200
        assert not status.json()["connected"]
        assert status.json()["can_send_email"] is False
        assert client.post("/web-api/google/connect",json={}).status_code==403
        fake=GoogleOAuth(client_id="test-client",client_secret="test-secret",
           callback_url=BASE+"/oauth/google/callback")
        monkeypatch.setattr(main,"_google",fake)
        connected=client.post("/web-api/google/connect",headers={"Origin":BASE},json={})
        assert connected.status_code==200,connected.text
        assert "calendar.events" in connected.json()["url"]
        assert client.get("/web-api/google/inbox").status_code==403
        assert client.get("/web-api/google/calendar").status_code==403
        assert client.post("/web-api/google/calendar/preparation",
            headers={"Origin":BASE},json={"job_id":"x","approved":True}).status_code==404
        client.cookies.set("rh_session",other_token)
        assert client.get("/web-api/google/status").json()["connected"] is False

def test_calendar_conflict_and_no_duplicate_event():
    async def run():
        now=datetime.now(ZoneInfo("Europe/Madrid"))+timedelta(days=2)
        start=now.replace(second=0,microsecond=0)
        responses=[]
        def handler(request):
            if request.method=="GET" and request.url.path.endswith("/events"):
                return httpx.Response(200,json={"items":[]})
            if request.method=="POST":
                import json
                data=json.loads(request.content.decode())
                responses.append(data)
                return httpx.Response(200,json={"id":data["id"],
                    "htmlLink":"https://calendar.google.com/calendar/event?eid=abc"})
            return httpx.Response(404)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            connector=CalendarConnector("fake-access-token",client)
            result=await connector.create_preparation(
                "user-a","job-a",start.isoformat(),45,"Prepare for PM interview",
                "Bring evidence and problem-solving examples")
            assert result["created"] is True
            assert len(responses)==1
            ev=responses[0]
            assert ev["reminders"]=={"useDefault":False,"overrides":[{"method":"popup","minutes":0}]}
            assert ev["start"]["timeZone"]=="Europe/Madrid"
            assert ev["extendedProperties"]["private"]["job_id"]=="job-a"
        def conflict(request):
            if request.method=="GET":
                return httpx.Response(200,json={"items":[{
                    "start":{"dateTime":start.isoformat()},
                    "end":{"dateTime":(start+timedelta(minutes=30)).isoformat()}
                }]})
            return httpx.Response(200,json={})
        async with httpx.AsyncClient(transport=httpx.MockTransport(conflict)) as client:
            connector=CalendarConnector("test",client)
            try:
                await connector.create_preparation("u","j",start.isoformat(),45,"Prepare interview","")
            except ValueError as err:
                assert "overlap" in str(err).lower()
            else:raise AssertionError("Conflict must block calendar creation")
    asyncio.run(run())
