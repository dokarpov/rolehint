"""Conservative employer-source preflight. Network verification belongs to the ATS adapter.

Never promote a candidate to APPLY from URL shape alone.
"""
from urllib.parse import urlsplit

BLOCKED_HOSTS = frozenset({
    "linkedin.com", "www.linkedin.com", "indeed.com", "www.indeed.com",
    "glassdoor.com", "www.glassdoor.com", "ziprecruiter.com",
    "www.ziprecruiter.com", "simplify.jobs", "www.simplify.jobs",
})

def preflight_employer_source(job):
    """Return an auditable gate; unknown evidence always requires verification.

    Required verified fields must be supplied by a trusted ATS adapter, not an LLM.
    """
    url = str(job.get("source_url") or "").strip()
    parts = urlsplit(url)
    host = (parts.hostname or "").lower().rstrip(".")
    if parts.scheme != "https" or not host or parts.username or parts.password:
        return {"decision": "VERIFY_FIRST", "reason": "invalid_source_url"}
    if host in BLOCKED_HOSTS or any(host.endswith("." + h) for h in BLOCKED_HOSTS):
        return {"decision": "VERIFY_FIRST", "reason": "intermediary_source"}
    if not job.get("employer") or not job.get("requisition_id"):
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
