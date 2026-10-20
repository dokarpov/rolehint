"""Anonymous, read-only live vacancy preview. No candidate persistence or fabricated results."""
import os,re,time,asyncio,httpx
from urllib.parse import urlparse
from fastapi import APIRouter,HTTPException,Request
from .services.job_search import JobSearchService

router=APIRouter(prefix="/web-api/anonymous")
_hits={}
def _list(name):
    return [v.strip() for v in os.getenv(name,"").split(",") if v.strip()]
def _tokens(s):
    return set(re.findall(r"[a-z][a-z0-9+#.-]{2,}",(s or "").lower()))
def _valid(url):
    try:
        p=urlparse(url)
        return p.scheme=="https" and bool(p.hostname) and not (p.username or p.password)
    except ValueError:return False

@router.get("/jobs")
async def preview_jobs(request:Request,role:str="",cv_terms:str=""):
    role=" ".join(role.split())
    if not 3<=len(role)<=90 or not re.search(r"[a-zA-Z]",role):
        raise HTTPException(422,"Enter a job title (3–90 characters)")
    if len(cv_terms)>2500:raise HTTPException(422,"Too much CV context")
    # Small bounded in-memory throttle; staging-only, no raw CV stored.
    client=request.client.host if request.client else "unknown"
    now=time.monotonic()
    recent=[t for t in _hits.get(client,[]) if now-t<60]
    if len(recent)>=6:raise HTTPException(429,"Too many searches. Try again in one minute.")
    _hits[client]=recent+[now]
    if len(_hits)>5000:_hits.clear()
    svc=JobSearchService(ashby_boards=_list("ASHBY_BOARDS"),lever_sites=_list("LEVER_SITES"),
        greenhouse_boards=_list("GREENHOUSE_BOARDS"),workable_accounts=_list("WORKABLE_ACCOUNTS"),
        smartrecruiters_companies=_list("SMARTRECRUITERS_COMPANIES"),
        career_site_urls=_list("CAREER_SITE_URLS")+_list("VC_PORTFOLIO_JOB_URLS"))
    try:
        raw=await asyncio.wait_for(svc.search(role),timeout=22)
    except Exception:raise HTTPException(503,"Live job sources are temporarily unavailable")
    terms=_tokens(cv_terms)
    role_terms=_tokens(role)
    feed_ok=False
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response=await client.get("https://remotive.com/api/remote-jobs",params={"search":role,"limit":100})
            response.raise_for_status()
            feed=response.json()
            feed_ok=True
        for item in feed.get("jobs",[]):
            raw.append({"source":"remotive","source_url":item.get("url",""),
                "title":item.get("title",""),"company":item.get("company_name",""),
                "location":item.get("candidate_required_location") or "Remote",
                "remote":True,"description":item.get("description",""),
                "posted_at":item.get("publication_date")})
    except (httpx.HTTPError,ValueError,KeyError):
        if not raw:raise HTTPException(503,"Job feeds are unavailable. Please retry shortly.")
    output=[]
    seen=set()
    for j in raw:
        url=j.get("source_url") or ""
        title=j.get("title") or ""
        desc=re.sub(r"<[^>]+>"," ",j.get("description") or "")
        title_terms=_tokens(title)
        overlap=role_terms & title_terms
        if not _valid(url) or not title or not overlap:continue
        key=(str(j.get("company") or "").lower(),title.lower())
        if key in seen:continue
        seen.add(key)
        words=_tokens(desc)
        # Signals are keyword overlap, not calibrated percentages or verified qualifications.
        matched=sorted((terms & words)-role_terms)[:5] if terms else []
        missing=sorted((words & {"sql","python","figma","analytics","leadership","stakeholders","roadmap","experimentation","research","strategy","salesforce","aws","kubernetes"})-terms)[:5] if terms else []
        rank=(len(overlap)*10 + len(matched)*2 - len(missing))
        output.append({"_rank":rank,"title":title[:180],"company":str(j.get("company") or "Employer")[:120],
            "location":str(j.get("location") or "Not specified")[:130],
            "url":url,"source":j.get("source"),"posted_at":j.get("posted_at"),
            "fit":{"matched_terms":matched,"unconfirmed_terms":missing,
                "label":"Partial evidence" if matched else "Not assessed",
                "note":"Keyword signals only; eligibility, experience and vacancy status require verification."},
            "remote":j.get("remote"),"description_excerpt":desc[:350]})
    output.sort(key=lambda job:job["_rank"],reverse=True)
    output=output[:10]
    for job in output:job.pop("_rank",None)
    return {"sources_available":bool(feed_ok or raw),"role":role,"jobs":output,"count":len(output),"limit":10,
        "disclaimer":"Live source listings; not independently confirmed open. No numeric fit score or eligibility guarantee."}
