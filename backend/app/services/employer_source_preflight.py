"""Employer-source eligibility annotation; no URL-only proof of a live vacancy."""
from urllib.parse import urlsplit

INTERMEDIARIES = {"linkedin.com", "indeed.com", "glassdoor.com", "ziprecruiter.com", "simplify.jobs"}
DIRECT_ATS = {"ashby", "lever", "greenhouse", "workable", "smartrecruiters", "career_sites"}

def preflight_employer_source(job):
    parts = urlsplit(str(job.get("source_url") or "").strip())
    host = (parts.hostname or "").lower().rstrip(".")
    if parts.scheme != "https" or not host or parts.username or parts.password:
        return {"decision": "VERIFY_FIRST", "reason": "invalid_source_url"}
    if any(host == domain or host.endswith("." + domain) for domain in INTERMEDIARIES):
        return {"decision": "VERIFY_FIRST", "reason": "intermediary_source"}
    if job.get("source") not in DIRECT_ATS:
        return {"decision": "VERIFY_FIRST", "reason": "source_not_direct_ats"}
    if not job.get("company") or not job.get("source_job_id"):
        return {"decision": "VERIFY_FIRST", "reason": "missing_employer_identity"}
    if job.get("source_status") == "closed":
        return {"decision": "DO_NOT_APPLY", "reason": "closed_vacancy"}
    if job.get("source_status") != "open" or job.get("application_form_verified") is not True:
        return {"decision": "VERIFY_FIRST", "reason": "unverified_live_form"}
    if job.get("geographic_eligibility") == "ineligible":
        return {"decision": "DO_NOT_APPLY", "reason": "geography_ineligible"}
    if job.get("geographic_eligibility") != "eligible":
        return {"decision": "VERIFY_FIRST", "reason": "geography_unknown"}
    if job.get("hard_requirements_checked") is not True:
        return {"decision": "VERIFY_FIRST", "reason": "requirements_unverified"}
    return {"decision": "SOURCE_VERIFIED", "reason": "verified_adapter_evidence"}
