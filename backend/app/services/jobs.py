from __future__ import annotations
import hashlib, re
from .job_ingest.fetch import canonical_url as canonical_job_url

def clean(s:str|None)->str:
    return re.sub(r"\s+"," ",(s or "").strip())

def canonical_url(url:str)->str:
    return canonical_job_url(url) if url else ""

def canonical_key(job:dict)->str:
    raw="|".join([
      clean(job.get("company")).lower(),
      clean(job.get("title")).lower(),
      clean(job.get("location")).lower()
    ])
    return hashlib.sha1(raw.encode()).hexdigest()[:16]

def normalize(job:dict)->dict:
    j=dict(job)
    j["company"]=clean(j.get("company"))
    j["title"]=clean(j.get("title"))
    j["location"]=clean(j.get("location")) or None
    j["source_url"]=canonical_url(j.get("source_url",""))
    j["canonical_key"]=canonical_key(j)
    j["id"]=f"{j.get('source','src')}:{j.get('source_job_id') or j['canonical_key']}"
    return j

DIRECT_EMPLOYER_SOURCES = frozenset({"ashby", "lever", "greenhouse", "workable", "smartrecruiters"})

def dedupe(jobs:list[dict])->list[dict]:
    """Prefer original employer ATS records; keep other sources as attribution only.

    Aggregator descriptions, compensation or verification cannot overwrite
    a matching employer record.
    """
    groups={}
    for job in jobs:
        j=normalize(job)
        key=j["canonical_key"]
        citation={"source":j["source"],"url":j["source_url"]}
        if key not in groups:
            j["sources"]=[citation]
            groups[key]=j
            continue
        cur=groups[key]
        provenance=cur["sources"]+[citation]
        current_direct=cur.get("source") in DIRECT_EMPLOYER_SOURCES
        candidate_direct=j.get("source") in DIRECT_EMPLOYER_SOURCES
        if candidate_direct and not current_direct:
            j["sources"]=provenance
            groups[key]=j
            continue
        cur["sources"]=provenance
        if current_direct and not candidate_direct:
            continue
        if len(j.get("description") or "") > len(cur.get("description") or ""):
            cur["description"]=j["description"]
        for f in ["salary_min","salary_max","currency","remote","posted_at"]:
            if cur.get(f) is None and j.get(f) is not None:
                cur[f]=j[f]
    return list(groups.values())
