import httpx
from .base import JobSource
from .source_evidence import annotate_listing

class LeverBoardSource(JobSource):
    name="lever"
    def __init__(self, sites: list[str] | None = None):
        self.sites=sites or []

    async def search(self, query, countries, remote_only):
        out=[]
        async with httpx.AsyncClient(timeout=15) as c:
            for site in self.sites:
                data=(await c.get(f"https://api.lever.co/v0/postings/{site}",params={"mode":"json"})).json()
                for x in data:
                    hay=(x.get("text","")+" "+x.get("descriptionPlain","")).lower()
                    if query.lower() not in hay:
                        continue
                    cats=x.get("categories") or {}
                    out.append(annotate_listing({
                      "source":"lever","source_job_id":x.get("id"),"source_url":x.get("hostedUrl") or x.get("applyUrl",""),
                      "company":site,"title":x.get("text",""),"location":cats.get("location"),
                      "remote":None,"salary_min":None,"salary_max":None,"currency":None,
                      "description":x.get("descriptionPlain",""),"posted_at":None
                    }))
        return out
