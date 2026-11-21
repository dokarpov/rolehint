"""Regression: URL lookalikes, stale source checks, unknown eligibility."""
from datetime import datetime, timezone
from app.services.employer_source_preflight import preflight_employer_source

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)
BASE = dict(source="ashby", source_url="https://jobs.ashbyhq.com/acme/role",
            company="Acme", source_job_id="role", source_status="open",
            source_checked_at="2026-11-21T11:30:00+00:00", source_check_method="ats_listing_api",
            application_form_verified=True, geographic_eligibility="eligible",
            hard_requirements_checked=True)

def decision(overrides=None):
    return preflight_employer_source({**BASE, **(overrides or {})}, now=NOW)

def test_legitimate_recent_ats_listing_is_verified():
    assert decision()["decision"] == "SOURCE_VERIFIED"

def test_wrong_ats_domain_is_blocked_even_when_attested():
    assert decision({"source_url": "https://attacker.example/role"})["reason"] == "source_host_mismatch"

def test_mismatched_provider_is_not_employer_source():
    assert decision({"source_url": "https://jobs.lever.co/acme/role"})["reason"] == "source_host_mismatch"

def test_compound_attack_domain_is_not_accepted():
    assert decision({"source_url": "https://jobs.ashbyhq.com.evil.test/acme/role"})["reason"] == "source_host_mismatch"

def test_missing_form_stays_unverified():
    assert decision({"application_form_verified": False})["decision"] == "VERIFY_FIRST"

def test_stale_evidence_requires_recheck():
    assert decision({"source_checked_at": "2026-11-20T11:00:00+00:00"})["reason"] == "source_evidence_stale"

def test_missing_source_method_requires_recheck():
    assert decision({"source_check_method": None})["reason"] == "source_evidence_untrusted"

def test_future_timestamp_is_not_credible():
    assert decision({"source_checked_at": "2026-11-22T11:00:00+00:00"})["reason"] == "source_evidence_stale"

def test_malformed_port_is_not_accepted():
    assert decision({"source_url": "https://jobs.ashbyhq.com:notaport/acme/role"})["reason"] == "invalid_source_url"

def test_closed_posting_is_blocked():
    assert decision({"source_status": "closed"})["decision"] == "DO_NOT_APPLY"

def test_eligibility_unknown_is_not_inferred_from_remoteness():
    assert decision({"geographic_eligibility": "unknown"})["reason"] == "geography_unknown"
