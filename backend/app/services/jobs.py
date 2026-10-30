"""Canonical job identity and source-aware deduplication.

Employer ATS evidence outranks aggregators; distinct requisitions from the
same employer must not be silently folded into one listing.
"""
from __future__ import annotations
import hashlib,re,unicodedata
from .job_ingest.fetch import canonical_url as canonical_job_url

SOURCE_RANK={
    "greenhouse":4,"lever":4,"ashby":4,"workable":4,"smartrecruiters":4,
    "workday":4,"career_site":3,"career_sites":3,
    "adzuna":1,"jooble":1,"jsearch":1
}
DIRECT_ATS={"greenhouse","lever","ashby","workable","smartrecruiters","workday"}

def clean(s:str|None)->str:
    return re.sub(r"\s+"," ",str(s or "").strip())

def canonical_url(url:str)->str:
    return canonical_job_url(url) if url else ""

def _ascii(value):
    return "".join(c for c in unicodedata.normalize("NFKD",clean(value).casefold()) if not unicodedata.combining(c))

def canonical_key(job:dict)->str:
    company=re.sub(r"\b(incorporated|inc|ltd|limited|gmbh|llc|sarl|corp)\b\.?","",_ascii(job.get("company")))
    role=re.sub(r"\bsr\.?\b","senior",_ascii(job.get("title")))
    location=_ascii(job.get("location"))
    normalized="|".join(re.sub(r"[^a-z0-9]+"," ",x).strip() for x in [company,role,location])
    return hashlib.sha1(normalized.encode()).hexdigest()[:16]

def normalize(job:dict)->dict:
    j=dict(job)
    j["company"]=clean(j.get("company"))
    j["title"]=clean(j.get("title"))
    j["location"]=clean(j.get("location")) or None
    j["source_url"]=canonical_url(j.get("source_url",""))
    j["canonical_key"]=canonical_key(j)
    j["id"]=f"{j.get('source','src')}:{j.get('source_job_id') or j['canonical_key']}"
    return j

def _provenance(job):
    return {"source":job.get("source"),"url":job.get("source_url"),
            "posted_at":job.get("posted_at"),
            "source_verification":("employer_source" if job.get("source") in DIRECT_ATS else
                                    "discovery_lead")}

def dedupe(jobs:list[dict])->list[dict]:
    groups={}
    for raw in jobs:
        j=normalize(raw)
        key=j["canonical_key"]
        # Preserve distinct official requisitions within the same source.
        current=groups.get(key)
        if (current and j.get("source") in DIRECT_ATS
                and current.get("source")==j.get("source")
                and current.get("source_job_id") and j.get("source_job_id")
                and str(current["source_job_id"])!=str(j["source_job_id"])):
            key=key+":"+str(j["source_job_id"])[:50]
            current=groups.get(key)
        if current is None:
            j["sources"]=[_provenance(j)]
            groups[key]=j
            continue
        refs=current.get("sources") or []
        sig=(j.get("source"),j.get("source_url"))
        if not any((x.get("source"),x.get("url"))==sig for x in refs):
            refs.append(_provenance(j))
        if SOURCE_RANK.get(j.get("source"),0)>SOURCE_RANK.get(current.get("source"),0):
            replacement=dict(j)
            replacement["sources"]=refs
            groups[key]=replacement
            continue
        current["sources"]=refs
        if (j.get("source")==current.get("source")
                and len(j.get("description") or "")>len(current.get("description") or "")):
            current["description"]=j["description"]
        # Only borrow salary or freshness when from an equally authoritative
        # source. Do not present inferred aggregator pay as employer-published.
        if SOURCE_RANK.get(j.get("source"),0)>=SOURCE_RANK.get(current.get("source"),0):
            for field in ("salary_min","salary_max","currency","remote","posted_at","valid_through"):
                if current.get(field) is None and j.get(field) is not None:
                    current[field]=j[field]
    return list(groups.values())
