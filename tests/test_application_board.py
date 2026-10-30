"""Dossier-inspired application command center tests.

No external job submission. No actual emails or CV claims are fabricated.
"""
from __future__ import annotations

import time
import uuid
from fastapi.testclient import TestClient
from app.main import app, product
from app.web_identity import token_hash
from app.services.application_tracking.board import build_application_board

BASE = "https://rolehint.example"


def test_board_projection_distinguishes_handoff_from_submission():
    jobs = [
        {"job_id":"j1", "company":"First", "title":"PM", "decision":"APPLY"},
        {"job_id":"j2", "company":"Second", "title":"PM", "decision":"APPLY"},
        {"job_id":"j3", "company":"Third", "title":"PM", "decision":"VERIFY_FIRST"},
        {"job_id":"j4", "company":"Fourth", "title":"PM", "decision":"DO_NOT_APPLY"},
        {"job_id":"j5", "company":"Fifth", "title":"PM", "decision":"APPLY"},
    ]
    submissions = [
        {"job_id":"j2", "response_state":"rejected", "submitted_at":123},
        {"job_id":"j2", "response_state":"recruiter_or_interview", "submitted_at":145},
        {"job_id":"j5", "response_state":"submitted", "submitted_at":146},
    ]
    board = build_application_board(
        jobs, submissions,
        {"j1":{"approved_at":100, "state":"approved_handoff"}},
        {"j1":{"version":2}, "j3":{"version":4}},
    )
    by_id = {r["job_id"]:r for r in board["items"]}
    assert by_id["j1"]["stage"] == "handoff"
    assert by_id["j1"]["submitted_at"] is None
    assert by_id["j2"]["stage"] == "interview"
    assert by_id["j3"]["stage"] == "draft"
    assert by_id["j4"]["stage"] == "not_eligible"
    assert by_id["j5"]["stage"] == "awaiting_response"
    assert board["summary"]["confirmed_submitted"] == 2
    assert board["summary"]["interviews"] == 1
    assert board["counts"]["rejected"] == 0
    assert board["counts"]["handoff"] == 1


def _user_and_token():
    user = product.ensure_user(telegram_user={
        "id": 90000000 + int(uuid.uuid4().int % 10000000),
        "first_name": "Pipeline QA"
    })
    token = "qa-" + uuid.uuid4().hex + uuid.uuid4().hex
    product.conn.execute(
        "INSERT INTO web_sessions VALUES(?,?,?,?)",
        (token_hash(token),user,time.time()+3600,time.time())
    )
    product.conn.commit()
    return user, token


def test_board_endpoint_requires_login_and_scopes_all_data(monkeypatch):
    monkeypatch.setenv("CFA_WEB_APP_URL", BASE)
    a,ta = _user_and_token()
    b,tb = _user_and_token()
    j = {
        "source":"ashby", "source_job_id":"pipeline-"+uuid.uuid4().hex,
        "company":"Private board QA employer", "title":"Senior Product Manager",
        "source_url":"https://jobs.ashbyhq.com/private-qa/123",
        "location":"Europe remote",
        "description":"Responsibilities include user research, portfolio prioritization and experimentation. "*4
    }
    job = product.upsert_user_job(a,j)
    jid = job["job_id"]
    product.application_pack(a,jid,create=True)
    with TestClient(app,base_url=BASE) as client:
        assert client.get("/web-api/application-board").status_code == 401
        client.cookies.set("rh_session",tb)
        foreign = client.get("/web-api/application-board")
        assert foreign.status_code == 200
        assert jid not in [x["job_id"] for x in foreign.json()["items"]]
        assert "Private board QA employer" not in foreign.text
        client.cookies.set("rh_session",ta)
        own = client.get("/web-api/application-board")
        assert own.status_code == 200,own.text
        record = next(x for x in own.json()["items"] if x["job_id"] == jid)
        assert record["stage"] == "draft"
        assert record["pack_version"] == 1
        assert record["submitted_at"] is None
        assert "payload" not in record
        assert "data" not in record
        # A handoff is never a confirmed application.
        resp=client.post("/web-api/jobs/"+jid+"/handoff",headers={"Origin":BASE})
        assert resp.status_code == 200
        record=next(x for x in client.get("/web-api/application-board").json()["items"] if x["job_id"]==jid)
        assert record["stage"] == "handoff"
        assert record["submitted_at"] is None
        assert client.post("/web-api/jobs/"+jid+"/submitted",headers={"Origin":BASE}).status_code == 200
        record=next(x for x in client.get("/web-api/application-board").json()["items"] if x["job_id"]==jid)
        assert record["stage"] == "awaiting_response"
        assert record["submitted_at"] is not None
        assert client.put("/web-api/jobs/"+jid+"/outcome",
            headers={"Origin":BASE},json={"state":"recruiter_or_interview"}).status_code == 200
        record=next(x for x in client.get("/web-api/application-board").json()["items"] if x["job_id"]==jid)
        assert record["stage"] == "interview"
        client.cookies.set("rh_session",tb)
        assert jid not in [x["job_id"] for x in client.get("/web-api/application-board").json()["items"]]


def test_direct_ats_capture_is_verified_scoped_and_idempotent(monkeypatch):
    """No arbitrary URL fetch; valid captures feed the existing matching pipeline."""
    monkeypatch.setenv("CFA_WEB_APP_URL", BASE)
    from app import web_release
    called=[]
    async def fake_provider(url):
        called.append(url)
        return {
            "source":"ashby","source_job_id":"verified-qa-123",
            "source_url":url,"company":"Verified QA",
            "title":"Senior Product Manager","location":"Remote Europe",
            "fetch_status":"ok","description":(
                "Responsibilities: Lead user research, design experiments and manage the product roadmap. "
                "Requirements: Five years of B2C product experience, cross-functional leadership, "
                "discovery, analytics, customer onboarding and measurable product outcomes. "
                "You will coordinate engineers, designers and data analysts to improve activation. "*4
            ),
        }
    monkeypatch.setattr(web_release,"fetch_ashby",fake_provider)
    user,token=_user_and_token()
    second,two=_user_and_token()
    link="https://jobs.ashbyhq.com/verified-qa/verified-qa-123"
    with TestClient(app,base_url=BASE) as client:
        denied=client.post("/web-api/capture-ats-url",headers={"Origin":BASE},json={"url":link})
        assert denied.status_code == 401
        client.cookies.set("rh_session",token)
        unsafe=[
            "http://jobs.ashbyhq.com/verified-qa/1",
            "https://127.0.0.1/internal",
            "https://jobs.ashbyhq.com.evil.example/jobs/1",
            "https://admin@jobs.ashbyhq.com/jobs/1",
            "https://jobs.ashbyhq.com:8443/jobs/1",
            "https://jobs.ashbyhq.com/",
        ]
        for bad in unsafe:
            response=client.post("/web-api/capture-ats-url",
                headers={"Origin":BASE},json={"url":bad})
            assert response.status_code == 422,(bad,response.text)
        assert not called
        one=client.post("/web-api/capture-ats-url",headers={"Origin":BASE},json={"url":link})
        assert one.status_code == 200,one.text
        data=one.json()
        assert data["added"] is True and data["duplicate"] is False
        assert len(called) == 1
        board=client.get("/web-api/application-board").json()
        assert any(j["job_id"]==data["job_id"] and j["stage"]=="review" for j in board["items"])
        same=client.post("/web-api/capture-ats-url",headers={"Origin":BASE},json={"url":link+"?utm_source=reddit"})
        assert same.status_code == 200,same.text
        assert same.json()["duplicate"] is True
        assert len(called)==1
        client.cookies.set("rh_session",two)
        other=client.get("/web-api/application-board").json()
        assert data["job_id"] not in [x["job_id"] for x in other["items"]]
        # No cross-account "already saved" response.
        new=client.post("/web-api/capture-ats-url",headers={"Origin":BASE},json={"url":link})
        assert new.status_code == 200,new.text
        assert new.json()["added"] is True
        assert len(called)==2
