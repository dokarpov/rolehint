"""Conservative vacancy freshness classification. No guessed open/closed status.

Only a successful re-fetch from an official ATS marks a posting 'verified_open'.
A 404 hidden behind an adapter error is 'unknown', not a confirmed closure.
"""
from __future__ import annotations
from datetime import datetime,timezone
from urllib.parse import urlsplit

DIRECT={"greenhouse","lever","ashby","workable","smartrecruiters","workday"}
def parse_date(value):
    if isinstance(value,(int,float)):
        v=float(value)
        return datetime.fromtimestamp(v/(1000 if v>1e11 else 1),timezone.utc)
    if not value:return None
    if isinstance(value,str):
        try:
            x=datetime.fromisoformat(value.strip().replace("Z","+00:00"))
            return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
        except ValueError:return None
    return None

def assess(job,now=None):
    now=now or datetime.now(timezone.utc)
    last=job.get("source_recheck") or {}
    valid=parse_date(job.get("valid_through"))
    if valid and valid<now:
        return {"state":"closed","reason":"Employer posting is past its explicit valid-through date.",
                "checked_at":now.isoformat(),"basis":"valid_through"}
    if last.get("state")=="verified_open":
        at=parse_date(last.get("checked_at"))
        if at and 0<=(now-at).total_seconds()<72*3600:
            return {"state":"verified_open","reason":"Re-fetched from the employer's ATS.",
                    "checked_at":last.get("checked_at"),"basis":"employer_ats"}
    if last.get("state")=="unknown":
        return {"state":"unknown","reason":"Recheck did not verify the posting; inspect employer page.",
                "checked_at":last.get("checked_at"),"basis":"unconfirmed_recheck"}
    if job.get("source") in DIRECT:
        return {"state":"unknown","reason":"Direct employer source saved, but still needs a recent recheck.",
                "checked_at":None,"basis":"employer_ats_unchecked"}
    return {"state":"unknown","reason":"Aggregator or unverified job lead; original employer listing is required.",
            "checked_at":None,"basis":"aggregator_unverified"}

def same_posting(before,after):
    if not before or not after:return False
    a=str(before.get("source_job_id") or "").strip()
    b=str(after.get("source_job_id") or "").strip()
    if not a or a!=b:return False
    ua=urlsplit(str(before.get("source_url") or ""))
    ub=urlsplit(str(after.get("source_url") or ""))
    return (ua.scheme=="https" and ub.scheme=="https" and
        ua.hostname==ub.hostname and
        str(before.get("source") or "")==str(after.get("source") or ""))

def can_recheck(job):
    url=str(job.get("source_url") or "")
    u=urlsplit(url)
    hosts={"greenhouse":{"job-boards.greenhouse.io","boards.greenhouse.io"},
           "lever":{"jobs.lever.co","jobs.eu.lever.co"},
           "ashby":{"jobs.ashbyhq.com"}}
    return bool(u.scheme=="https" and u.hostname in hosts.get(job.get("source"),set())
                and u.path.strip("/") and not u.username and not u.password and u.port is None)
