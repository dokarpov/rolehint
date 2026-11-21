"""Source retrieval evidence, distinct from application-form verification."""
from datetime import datetime, timezone

def annotate_listing(job, *, checked_at=None):
    """Mark an ATS listing seen in a successful API response, not a verified apply form."""
    enriched = dict(job)
    enriched["source_status"] = "open"
    enriched["source_checked_at"] = checked_at or datetime.now(timezone.utc).isoformat()
    enriched["source_check_method"] = "ats_listing_api"
    enriched["application_form_verified"] = False
    enriched["geographic_eligibility"] = "unknown"
    enriched["hard_requirements_checked"] = False
    return enriched
