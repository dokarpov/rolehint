import httpx
from .base import JobSource
from .source_evidence import annotate_listing

class AshbyBoardSource(JobSource):
    name="ashby"
    def __init__(self, boards: list[str] | None = None):
        self.boards=boards or []

    async def search(self, query, countries, remote_only):
        out=[]
        async with httpx.AsyncClient(timeout=15) as c:
            for board in self.boards:
                url=f"https://api.ashbyhq.com/posting-api/job-board/{board}"
                data=(await c.get(url,params={"includeCompensation":"true"})).json()
                for x in data.get("jobs",[]):
                    hay=(x.get("title","")+" "+x.get("descriptionPlain","")).lower()
                    qwords=[w for w in query.lower().split() if len(w)>2]
                    title=x.get("title","").lower()
                    if not qwords or not all(w in title for w in qwords):
                        continue
                    out.append(annotate_listing({
                      "source":"ashby","source_job_id":x.get("id"),"source_url":x.get("jobUrl") or x.get("applyUrl",""),
                      "company":board,"title":x.get("title",""),"location":x.get("location"),
                      "remote":x.get("isRemote"),"salary_min":None,"salary_max":None,
                      "currency":None,"description":x.get("descriptionPlain",""),"posted_at":x.get("publishedAt")
                    }))
        return out
