"""Fail-closed employer source gate; ATS listing presence is not application verification."""
from datetime import datetime, timezone
from urllib.parse import urlsplit

INTERMEDIARIES = frozenset({"linkedin.com", "indeed.com", "glassdoor.com", "ziprecruiter.com", "simplify.jobs"})
ATS_HOSTS = {
    "ashby": frozenset({"jobs.ashbyhq.com"}),
    "lever": frozenset({"jobs.lever.co", "jobs.eu.lever.co"}),
    "greenhouse": frozenset({"boards.greenhouse.io", "job-boards.greenhouse.io", "boards.eu.greenhouse.io"}),
    "workable": frozenset({"apply.workable.com", "jobs.workable.com", "www.workable.com"}),
    "smartrecruiters": frozenset({"jobs.smartrecruiters.com", "careers.smartrecruiters.com"}),
}

def _source_host(job):
    try:
        parts = urlsplit(str(job.get("source_url") or "").strip())
        host = (parts.hostname or "").lower().rstrip(".")
        port = parts.port
    except (ValueError, TypeError):
        return None
    if (parts.scheme != "https" or not host or parts.username or parts.password
            or port not in (None, 443) or not parts.path.strip("/")):
        return None
    return host

def preflight_employer_source(job, *, now=None, max_age_seconds=21600):
    """Return conservative source gate; never infer eligibility or form availability."""
    host = _source_host(job)
    if not host:
        return {"decision": "VERIFY_FIRST", "reason": "invalid_source_url"}
    if any(host == root or host.endswith("." + root) for root in INTERMEDIARIES):
        return {"decision": "VERIFY_FIRST", "reason": "intermediary_source"}
    source = job.get("source")
    if source not in ATS_HOSTS:
        return {"decision": "VERIFY_FIRST", "reason": "source_not_direct_ats"}
    if host not in ATS_HOSTS[source]:
        return {"decision": "VERIFY_FIRST", "reason": "source_host_mismatch"}
    if not job.get("company") or not job.get("source_job_id"):
        return {"decision": "VERIFY_FIRST", "reason": "missing_employer_identity"}
    if job.get("source_status") == "closed":
        return {"decision": "DO_NOT_APPLY", "reason": "closed_vacancy"}
    if job.get("source_status") != "open" or job.get("application_form_verified") is not True:
        return {"decision": "VERIFY_FIRST", "reason": "unverified_live_form"}
    if job.get("source_check_method") not in {"ats_listing_api", "ats_recheck_api"}:
        return {"decision": "VERIFY_FIRST", "reason": "source_evidence_untrusted"}
    current = now or datetime.now(timezone.utc)
    try:
        checked = datetime.fromisoformat(job.get("source_checked_at") or "")
        age = (current - checked).total_seconds()
        if checked.tzinfo is None or not -300 <= age <= max_age_seconds:
            raise ValueError("stale or future timestamp")
    except (ValueError, TypeError, OverflowError):
        return {"decision": "VERIFY_FIRST", "reason": "source_evidence_stale"}
    if job.get("geographic_eligibility") == "ineligible":
        return {"decision": "DO_NOT_APPLY", "reason": "geography_ineligible"}
    if job.get("geographic_eligibility") != "eligible":
        return {"decision": "VERIFY_FIRST", "reason": "geography_unknown"}
    if job.get("hard_requirements_checked") is not True:
        return {"decision": "VERIFY_FIRST", "reason": "requirements_unverified"}
    return {"decision": "SOURCE_VERIFIED", "reason": "verified_adapter_evidence"}
