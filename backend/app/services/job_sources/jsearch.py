"""Optional JSearch discovery adapter.

Aggregator leads are NOT verified open employer requisitions and must be
rechecked on a directly supported employer ATS before delivery.
Requires a user-supplied RapidAPI key; does not scrape LinkedIn.
"""
from __future__ import annotations
import os
from urllib.parse import urlsplit
import httpx
from .base import JobSource

class JSearchSource(JobSource):
    name="jsearch"
    def __init__(self,client=None):self.client=client

    async def search(self,query,countries,remote_only):
        key=os.getenv("JSEARCH_RAPIDAPI_KEY","")
        if not key:return []
        country_list=[str(x).lower() for x in (countries or ["es"]) if str(x).lower() in {
            "es","de","fr","gb","it","pt","nl","ie","us","ca","ae"}][:3]
        if not country_list:country_list=["es"]
        results=[]
        headers={"X-RapidAPI-Key":key,"X-RapidAPI-Host":"jsearch.p.rapidapi.com"}
        async with httpx.AsyncClient(timeout=18) if self.client is None else _NoClose(self.client) as c:
            for country in country_list:
                try:
                    response=await c.get("https://jsearch.p.rapidapi.com/search",headers=headers,
                        params={"query":str(query)[:120],"country":country,"num_pages":"1",
                                "date_posted":"month","work_from_home":str(bool(remote_only)).lower()})
                    response.raise_for_status()
                    data=response.json()
                except (httpx.HTTPError,ValueError,TypeError):
                    continue
                for x in data.get("data") or []:
                    if not isinstance(x,dict):continue
                    target=x.get("job_apply_link") or ""
                    u=urlsplit(str(target))
                    if u.scheme!="https" or not u.netloc:continue
                    salary_currency=x.get("job_salary_currency")
                    results.append({
                        "source":"jsearch","source_job_id":str(x.get("job_id") or ""),
                        "source_url":target,
                        "company":str(x.get("employer_name") or ""),
                        "title":str(x.get("job_title") or ""),
                        "location":", ".join(str(v) for v in
                          [x.get("job_city"),x.get("job_state"),x.get("job_country")] if v),
                        "remote":x.get("job_is_remote"),
                        "salary_min":x.get("job_min_salary"),
                        "salary_max":x.get("job_max_salary"),
                        "currency":salary_currency,
                        "description":str(x.get("job_description") or "")[:20000],
                        "posted_at":x.get("job_posted_at_datetime_utc"),
                        "source_verification":"aggregator_unverified",
                        "discovered_via":"RapidAPI JSearch"
                    })
        return results[:30]

class _NoClose:
    def __init__(self,client):self.client=client
    async def __aenter__(self):return self.client
    async def __aexit__(self,*args):return False
