"""End-to-end backend contract: CV evidence -> vacancy review -> approved handoff -> confirmed outcome.
No mock submission to any employer; only user-confirmed manual handoff is recorded.
"""
import hashlib,uuid,time
from fastapi.testclient import TestClient
from app.main import app,product
from app.web_identity import token_hash
from app.web_release import is_qualified,contract_signal
from app.services.auto_match.service import evaluate_constraints

BASE="https://rolehint.example"

def test_contractual_and_currency_unknowns():
    prefs={"remote_only":False,"allow_relocation":False,"salary_floor_annual":90000}
    job={"company":"Acme","title":"Senior Product Manager","source":"ashby",
         "source_job_id":"a1","source_url":"https://jobs.ashbyhq.com/acme/a1",
         "description":"W-2 only employees. Required to work on site."*5}
    assert contract_signal(job)=="incompatible"
    assert is_qualified(job,prefs,True)[0] is False
    assert is_qualified(job,prefs,False)[0] is True
    constraints={"work_mode":"remote","relocation_required":False,"salary_min":50000,
                 "salary_max":60000,"currency":"USD","location":"Europe"}
    out=evaluate_constraints(constraints,prefs)
    assert not out["hard"]
    assert out["unknown"]
    constraints["currency"]="EUR"
    assert evaluate_constraints(constraints,prefs)["hard"]

def test_real_job_review_handoff_history(monkeypatch):
    monkeypatch.setenv("CFA_WEB_APP_URL",BASE)
    uid=product.ensure_user(telegram_user={"id":90000000+int(uuid.uuid4().int%10000000),"first_name":"QA"})
    token="test-"+uuid.uuid4().hex+uuid.uuid4().hex
    product.conn.execute("INSERT INTO web_sessions VALUES(?,?,?,?)",(token_hash(token),uid,time.time()+3600,time.time()))
    product.conn.commit()
    j={"source":"ashby","source_job_id":"qa-"+uuid.uuid4().hex,
       "company":"QA Employer","title":"Product Manager","location":"Remote Europe",
       "source_url":"https://jobs.ashbyhq.com/qa-employer/product-manager",
       "description":"We require experience in product strategy, stakeholder management and user research. "
                     "This role is remote in Europe. "+("You will lead discovery and product experiments. "*7)}
    stored=product.upsert_user_job(uid,j)
    job_id=stored["job_id"]
    with TestClient(app,base_url=BASE) as client:
        client.cookies.set("rh_session",token)
        assert client.get("/web-api/release-state").status_code==200
        r=client.get("/web-api/jobs/"+job_id+"/review")
        assert r.status_code==200,r.text
        assert r.json()["company"]=="QA Employer"
        pack=client.get("/web-api/jobs/"+job_id+"/pack")
        assert pack.status_code==200
        data=pack.json()["data"]
        data["recruiter_note"]="I am interested in discussing this role. Please refer to my attached CV."
        update=client.put("/web-api/jobs/"+job_id+"/pack",headers={"Origin":BASE},json=data)
        assert update.status_code==200,update.text
        export=client.get("/web-api/jobs/"+job_id+"/export")
        assert export.status_code==200
        assert "Please refer to my attached CV" in export.text
        assert client.post("/web-api/jobs/"+job_id+"/submitted",headers={"Origin":BASE}).status_code==409
        go=client.post("/web-api/jobs/"+job_id+"/handoff",headers={"Origin":BASE})
        assert go.status_code==200,go.text
        assert go.json()["submitted"] is False
        first=client.post("/web-api/jobs/"+job_id+"/submitted",headers={"Origin":BASE})
        assert first.status_code==200,first.text
        assert first.json()["status"]=="submitted"
        dup=client.post("/web-api/jobs/"+job_id+"/submitted",headers={"Origin":BASE})
        assert dup.json()["duplicate"] is True
        outcome=client.put("/web-api/jobs/"+job_id+"/outcome",headers={"Origin":BASE},json={"state":"rejected"})
        assert outcome.status_code==200,outcome.text
        state=client.get("/web-api/release-state").json()
        item=next(x for x in state["opportunities"] if x["job_id"]==job_id)
        assert item["already_submitted"] is True
        assert item["employer_rejected_before"] is True
        assert client.post("/web-api/jobs/"+job_id+"/handoff",headers={"Origin":BASE}).status_code==409
