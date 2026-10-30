"""Search-source trust, freshness and optional JSearch tests with no network spend."""
from datetime import datetime,timedelta,timezone
import httpx
import asyncio

from app.services.jobs import dedupe
from app.services.job_sources.freshness import assess,same_posting,can_recheck
from app.services.job_sources.jsearch import JSearchSource
from app.web_release import is_qualified

def test_source_precedence_over_longer_aggregator_text():
    source="https://jobs.ashbyhq.com/example/123"
    ag={"source":"jsearch","source_job_id":"agg1","source_url":"https://other.example/apply",
        "company":"Example GmbH","title":"Sr. Product Manager","location":"Berlin",
        "description":"Marketing text "+"x"*4000,"salary_min":999999}
    ats={"source":"ashby","source_job_id":"123","source_url":source,
        "company":"Example","title":"Senior Product Manager","location":"Berlin",
        "description":"Actual requirements from employer."*10}
    combined=dedupe([ag,ats])
    assert len(combined)==1
    one=combined[0]
    assert one["source"]=="ashby"
    assert one["source_url"]==source
    assert one["description"]==ats["description"]
    assert one.get("salary_min") is None
    assert len(one["sources"])==2
    assert any(x["source_verification"]=="discovery_lead" for x in one["sources"])

def test_two_distinct_employer_requisitions_are_not_collapsed():
    base={"source":"greenhouse","company":"Test","title":"Product Manager","location":"Remote Europe",
          "description":"Requirements "*20}
    a={**base,"source_job_id":"123","source_url":"https://job-boards.greenhouse.io/test/jobs/123"}
    b={**base,"source_job_id":"124","source_url":"https://job-boards.greenhouse.io/test/jobs/124"}
    assert len(dedupe([a,b]))==2

def test_explicit_expiry_blocks_but_old_published_date_does_not():
    now=datetime(2026,10,30,tzinfo=timezone.utc)
    expired={"source":"ashby","valid_through":"2026-10-29T15:00:00Z"}
    assert assess(expired,now)["state"]=="closed"
    old={"source":"ashby","posted_at":"2025-01-01T00:00:00Z"}
    assert assess(old,now)["state"]=="unknown"
    pref={"remote_only":False,"allow_relocation":True,"salary_floor_annual":0}
    job={**expired,"company":"Acme","title":"PM",
         "source_job_id":"a","source_url":"https://jobs.ashbyhq.com/acme/a",
         "description":"Responsibilities include product experiments and discovery."*6}
    assert is_qualified(job,pref,False)[0] is False

def test_same_employer_requisition_only_and_no_untrusted_recheck():
    before={"source":"ashby","source_job_id":"a1",
            "source_url":"https://jobs.ashbyhq.com/acme/a1"}
    assert can_recheck(before)
    assert same_posting(before,dict(before))
    assert not same_posting(before,{**before,"source_job_id":"different"})
    assert not can_recheck({**before,"source_url":"https://jobs.ashbyhq.com.evil.example/a1"})

def test_jsearch_requires_key_and_is_discovery_only(monkeypatch):
    async def run():
        monkeypatch.delenv("JSEARCH_RAPIDAPI_KEY",raising=False)
        assert await JSearchSource().search("Product Manager",["es"],True)==[]
        monkeypatch.setenv("JSEARCH_RAPIDAPI_KEY","test-key")
        def handler(request):
            assert request.url.host=="jsearch.p.rapidapi.com"
            assert request.url.params["country"]=="es"
            assert request.url.params["work_from_home"]=="true"
            return httpx.Response(200,json={"data":[
                {"job_id":"external123","employer_name":"Sample GmbH",
                 "job_title":"Senior Product Manager",
                 "job_country":"ES","job_is_remote":True,
                 "job_apply_link":"https://www.linkedin.com/jobs/view/123",
                 "job_description":"Lead cross-functional product teams."*10}
            ]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result=await JSearchSource(client).search("Product Manager",["es"],True)
        assert len(result)==1
        assert result[0]["source_verification"]=="aggregator_unverified"
        assert result[0]["source"]=="jsearch"
        assert is_qualified(result[0],{"remote_only":False},False)[0] is False
    
    asyncio.run(run())