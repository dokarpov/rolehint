"""Regression checks for anonymous vacancy preview without contacting job boards."""
from fastapi.testclient import TestClient
from app.main import app
from app.services.job_search import JobSearchService

def test_bad_role():
    response=TestClient(app).get("/web-api/anonymous/jobs",params={"role":"a"})
    assert response.status_code==422

def test_live_results_ranked_and_deduplicated(monkeypatch):
    monkeypatch.setenv('CFA_WEB_APP_URL','https://rolehint.example')
    async def search(self,query,countries=None,remote_only=False,sources=None):
        return [
            {"title":"Product Manager","company":"Acme","source_url":"https://example.com/1",
             "description":"Roadmap analytics strategy","location":"Remote","source":"test"},
            {"title":"Product Manager","company":"Acme","source_url":"https://example.com/2",
             "description":"Roadmap analytics strategy","location":"Remote","source":"test"},
            {"title":"Senior Product Manager","company":"Beta","source_url":"https://example.com/3",
             "description":"Roadmap analytics leadership","location":"Remote","source":"test"}]
    monkeypatch.setattr(JobSearchService,"search",search)
    from app import anonymous_jobs
    class OfflineClient:
        def __init__(self,*a,**kw):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*a):pass
        async def get(self,*a,**kw):
            import httpx
            raise httpx.ConnectError("offline")
    monkeypatch.setattr(anonymous_jobs.httpx,"AsyncClient",OfflineClient)
    response=TestClient(app,base_url="https://rolehint.example").post(
        "/web-api/anonymous/matches",headers={"Origin":"https://rolehint.example"},
        json={"role":"Product Manager","cv_terms":"roadmap analytics"})
    assert response.status_code==200,response.text
    jobs=response.json()["jobs"]
    assert len(jobs)==2
    assert all(j["url"].startswith("https://") for j in jobs)
    assert jobs[0]["fit"]["matched_terms"]
    assert all("percentage" not in j["fit"] for j in jobs)

def test_no_sources_reports_error(monkeypatch):
    async def empty(self,*a,**kw):return []
    monkeypatch.setattr(JobSearchService,"search",empty)
    from app import anonymous_jobs
    class OfflineClient:
        def __init__(self,*a,**kw):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*a):pass
        async def get(self,*a,**kw):
            import httpx
            raise httpx.ConnectError("offline")
    monkeypatch.setattr(anonymous_jobs.httpx,"AsyncClient",OfflineClient)
    response=TestClient(app).get("/web-api/anonymous/jobs",params={"role":"Product Manager"})
    assert response.status_code==503

def test_raw_cv_never_accepted_in_query_string(monkeypatch):
    monkeypatch.setenv("CFA_WEB_APP_URL","https://rolehint.example")
    with TestClient(app,base_url="https://rolehint.example") as browser:
        unsafe=browser.get("/web-api/anonymous/jobs",
            params={"role":"Product Manager","cv_terms":"Sensitive candidate experience"})
        assert unsafe.status_code==422
        assert "CV context in a URL is disabled" in unsafe.json()["detail"]
        denied=browser.post("/web-api/anonymous/matches",
            json={"role":"Product Manager","cv_terms":"Private candidate data"})
        assert denied.status_code==403
        malformed=browser.post("/web-api/anonymous/matches",
            headers={"Origin":"https://rolehint.example"},
            json={"role":"Product Manager","cv_terms":"a"*2501})
        assert malformed.status_code==422
