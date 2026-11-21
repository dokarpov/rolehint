import httpx
from .base import JobSource
from .source_evidence import annotate_listing

class GreenhouseBoardSource(JobSource):
    name="greenhouse"
    def __init__(self, boards: list[str] | None = None):
        self.boards=boards or []

    async def search(self, query, countries, remote_only):
        out=[]
        async with httpx.AsyncClient(timeout=15) as c:
            for board in self.boards:
                url=f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
                data=(await c.get(url,params={"content":"true"})).json()
                for x in data.get("jobs",[]):
                    title=x.get("title","")
                    content=x.get("content","") or ""
                    if query.lower() not in (title+" "+content).lower():
                        continue
                    out.append(annotate_listing({
                      "source":"greenhouse","source_job_id":str(x.get("id","")),
                      "source_url":x.get("absolute_url",""),"company":board,"title":title,
                      "location":(x.get("location") or {}).get("name"),"remote":None,
                      "salary_min":None,"salary_max":None,"currency":None,
                      "description":content,"posted_at":x.get("updated_at")
                    }))
        return out
