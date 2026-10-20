"""Authenticated CV intake: validation, persistence, correction, isolation and deletion."""
from fastapi.testclient import TestClient
from app.main import app
from app import web_identity
import uuid

def test_cv_auth_and_lifecycle(monkeypatch):
    base="https://rolehint.example"
    monkeypatch.setenv("CFA_WEB_APP_URL",base)
    monkeypatch.setenv("CFA_SMTP_HOST","smtp.example")
    monkeypatch.setenv("CFA_MAIL_FROM","login@example.com")
    outgoing=[]
    monkeypatch.setattr(web_identity,"send_email",lambda email,url,host,sender:outgoing.append(url))
    from urllib.parse import urlsplit,parse_qs
    with TestClient(app,base_url=base) as browser:
        assert browser.get("/web-api/cv").status_code==401
        assert browser.post("/web-api/cv",files={"file":("cv.txt",b"A"*120)}).status_code==403
        assert browser.post("/web-api/login",headers={"Origin":base},json={"email":"cv-"+uuid.uuid4().hex+"@example.com"}).status_code==200
        target=urlsplit(outgoing[-1])
        token=parse_qs(target.query)["token"][0]
        assert browser.get(target.path,params={"token":token},follow_redirects=False).status_code==303
        assert browser.get("/web-api/cv").json()["uploaded"] is False
        assert browser.post("/web-api/cv",headers={"Origin":base},files={"file":("file.jpg",b"not CV")}).status_code==415
        assert browser.post("/web-api/cv",headers={"Origin":base},files={"file":("bad.pdf",b"not a PDF")}).status_code==422
        text="Work experience\nSenior product manager, five years. Led customer research and product discovery.\n"
        result=browser.post("/web-api/cv",headers={"Origin":base},files={"file":("career.txt",text.encode(),"text/plain")})
        assert result.status_code==200,result.text
        assert result.json()["uploaded"] is True
        assert browser.get("/web-api/cv").json()["text"]==text.strip()
        assert browser.get("/web-api/cv").json()["confirmed"] is False
        confirmed=browser.post("/web-api/cv/confirm",headers={"Origin":base})
        assert confirmed.status_code==200,confirmed.text
        assert confirmed.json()["verification_level"]=="self-reported"
        assert browser.get("/web-api/cv").json()["confirmed"] is True
        revised=text+"Owned roadmap prioritization with the product team."
        result=browser.put("/web-api/cv",headers={"Origin":base},json={"text":revised})
        assert result.status_code==200,result.text
        assert browser.get("/web-api/cv").json()["text"]==revised
        assert browser.get("/web-api/cv").json()["confirmed"] is False
        assert browser.delete("/web-api/cv",headers={"Origin":base}).json()["deleted"] is True
        assert browser.get("/web-api/cv").json()["uploaded"] is False
