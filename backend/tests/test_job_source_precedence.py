"""Employer ATS data must not be replaced by an aggregator's listing."""
from app.services.jobs import dedupe

AGG = {"source":"adzuna","source_job_id":"agg-1",
       "source_url":"https://www.adzuna.com/job/1","company":"Example",
       "title":"Product Manager","location":"Remote",
       "description":"third-party summary " * 25, "salary_min":999999}
ATS = {"source":"ashby","source_job_id":"ats-123",
       "source_url":"https://jobs.ashbyhq.com/example/ats-123","company":"Example",
       "title":"Product Manager","location":"Remote",
       "description":"Original employer role details.","source_checked_at":"2026-11-21T12:00:00+00:00"}

def test_direct_ats_replaces_aggregator_even_when_aggregator_arrives_first():
    result=dedupe([AGG,ATS])
    assert len(result)==1
    job=result[0]
    assert job["source"]=="ashby"
    assert job["source_job_id"]=="ats-123"
    assert job["source_url"]=="https://jobs.ashbyhq.com/example/ats-123"
    assert job["description"]=="Original employer role details."
    assert job["source_checked_at"]=="2026-11-21T12:00:00+00:00"
    assert job.get("salary_min") is None
    assert len(job["sources"])==2

def test_later_aggregator_cannot_override_employer_description_or_salary():
    job=dedupe([ATS,AGG])[0]
    assert job["source"]=="ashby"
    assert job["description"]=="Original employer role details."
    assert job.get("salary_min") is None

def test_aggregator_only_remains_discoverable_but_not_employer_verified():
    job=dedupe([AGG])[0]
    assert job["source"]=="adzuna"
    assert job["source_job_id"]=="agg-1"
