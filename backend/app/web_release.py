"""Narrow authenticated web release: real ATS -> evidence review -> approved handoff -> outcome.
Do not claim auto-submission, independently verified CV evidence, or a sourced salary when absent.
"""
from __future__ import annotations
import hashlib, os, re, time
from urllib.parse import urlsplit
from fastapi import HTTPException, Request
from fastapi.responses import PlainTextResponse
from .services.job_search import JobSearchService
from .services.auto_match import AutoMatchService
from .services.auto_match.service import extract_constraints, evaluate_constraints
from .services.application_packs import markdown as pack_markdown

def _envlist(name):
    return [x.strip() for x in os.getenv(name,"").split(",") if x.strip()]

def contract_signal(job):
    body=(str(job.get("description") or "")+" "+str(job.get("employment_type") or "")).lower()
    if re.search(r"\b(w-?2 only|employees only|employee only|no contractors|no b2b|permanent employees only)\b",body):
        return "incompatible"
    if re.search(r"\b(b2b|independent contractor|contract basis|self[- ]employed|freelance contract)\b",body):
        return "supported"
    return "unconfirmed"

def is_qualified(job,prefs,contractor_only):
    url=str(job.get("source_url") or "")
    parsed=urlsplit(url)
    if parsed.scheme!="https" or not parsed.netloc or not job.get("company") or not job.get("title"):
        return False,"Missing valid employer URL or identity"
    if str(job.get("source") or "") not in {"ashby","lever","greenhouse","workable","smartrecruiters"}:
        return False,"Not a directly supported employer ATS source"
    if not (job.get("source_job_id") or job.get("canonical_key")):
        return False,"Missing stable ATS identity"
    if evaluate_constraints(extract_constraints(job),prefs).get("hard"):
        return False,"Hard eligibility blocker"
    if contractor_only and contract_signal(job)=="incompatible":
        return False,"Explicit employee-only position"
    return True,None

def bind_web_release(router,product,require_user,check_origin,search_service=None,matcher=None):
    store=product.conn
    store.executescript("""
    CREATE TABLE IF NOT EXISTS web_search_constraints(
      user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
      contractor_only INTEGER NOT NULL DEFAULT 0, updated_at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS web_application_handoffs(
      user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      job_id TEXT NOT NULL, approved_at REAL NOT NULL,
      state TEXT NOT NULL DEFAULT 'approved_handoff', updated_at REAL NOT NULL,
      PRIMARY KEY(user_id,job_id));
    CREATE TABLE IF NOT EXISTS web_discovery_attempts(
      user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
      last_attempt REAL NOT NULL);
    """)
    store.commit()
    search=search_service or JobSearchService(
      ashby_boards=_envlist("ASHBY_BOARDS"),lever_sites=_envlist("LEVER_SITES"),
      greenhouse_boards=_envlist("GREENHOUSE_BOARDS"),
      workable_accounts=_envlist("WORKABLE_ACCOUNTS"),
      smartrecruiters_companies=_envlist("SMARTRECRUITERS_COMPANIES"),
      career_site_urls=_envlist("CAREER_SITE_URLS")+_envlist("VC_PORTFOLIO_JOB_URLS"))
    match=matcher or AutoMatchService(product)

    def contractor_only(uid):
        r=store.execute("SELECT contractor_only FROM web_search_constraints WHERE user_id=?",(uid,)).fetchone()
        return bool(r and r["contractor_only"])

    def history(uid):
        submissions=product.submissions(uid)
        jobs={j["job_id"]:j for j in product.jobs(uid)}
        employer_rejections=set()
        applied=set()
        for s in submissions:
            j=jobs.get(s["job_id"])
            if j:
                applied.add(j["job_id"])
                if s.get("response_state")=="rejected":employer_rejections.add(j["company"].casefold())
        for e in product.email_timeline(uid,limit=1000):
            if e.get("event_type")=="rejected":
                j=jobs.get(e.get("job_id"))
                if j:employer_rejections.add(j["company"].casefold())
        return submissions,applied,employer_rejections

    @router.get("/release-state")
    def release_state(request:Request):
        uid=require_user(request)
        submissions,applied,rejected=history(uid)
        jobs=product.jobs(uid)
        return {"contractor_only":contractor_only(uid),
                "opportunities":[{**j,"already_submitted":j["job_id"] in applied,
                    "employer_rejected_before":j["company"].casefold() in rejected}
                    for j in jobs[:10]],
                "free_used":min(10,len(jobs)),
                "application_history":[{"job_id":s["job_id"],"response_state":s["response_state"],
                    "submitted_at":s["submitted_at"]} for s in submissions[:50]]}

    @router.put("/contractor")
    async def save_contractor(request:Request):
        check_origin(request);uid=require_user(request)
        data=await request.json()
        if not isinstance(data.get("contractor_only"),bool):raise HTTPException(422,"contractor_only must be true or false")
        store.execute("INSERT INTO web_search_constraints VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET contractor_only=excluded.contractor_only,updated_at=excluded.updated_at",
                      (uid,int(data["contractor_only"]),time.time()))
        store.commit()
        return {"contractor_only":data["contractor_only"]}

    @router.post("/discover")
    async def discover(request:Request):
        check_origin(request);uid=require_user(request)
        data=await request.json()
        query=str(data.get("query") or "").strip()
        if not 3<=len(query)<=120:raise HTTPException(422,"Choose a target role")
        now=time.time()
        last=store.execute("SELECT last_attempt FROM web_discovery_attempts WHERE user_id=?",(uid,)).fetchone()
        if last and now-last["last_attempt"]<120:
            raise HTTPException(429,"Search was just run; please wait two minutes before refreshing")
        store.execute("INSERT INTO web_discovery_attempts VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET last_attempt=excluded.last_attempt",
                      (uid,now));store.commit()
        existing=product.jobs(uid)
        if len(existing)>=10 and not product.entitlement(uid):
            return {"added":0,"remaining":0,"message":"Your ten free openings have already been delivered."}
        prefs=product.preferences(uid)
        submitted,applied,rejections=history(uid)
        try:
            found=await search.search(query,prefs.get("allowed_regions") or [],
                                      bool(prefs.get("remote_only")))
        except Exception:
            raise HTTPException(503,"Employer job sources are temporarily unavailable")
        seen={(j["company"].casefold(),j["title"].casefold()) for j in existing}
        count=0
        for job in found[:200]:
            if not product.entitlement(uid) and len(product.jobs(uid))>=10:break
            eligible,_=is_qualified(job,prefs,contractor_only(uid))
            if not eligible:continue
            identity=(str(job["company"]).casefold(),str(job["title"]).casefold())
            if identity in seen:continue
            seen.add(identity)
            # Do not turn scraped summaries into match claims: require the original ATS job text.
            if len(str(job.get("description") or "").strip())<120:continue
            result=match.analyze_job(uid,job)
            if not result.get("ok"):continue
            if result.get("analysis",{}).get("final_action") in {"DO_NOT_APPLY","ALREADY_APPLIED"}:
                continue
            count+=1
        return {"added":count,"remaining":max(0,10-len(product.jobs(uid))),
                "message":("New live jobs were found." if count else "No new eligible ATS vacancies found. Your unused allowance remains.")}

    @router.get("/jobs/{job_id}/review")
    def review(request:Request,job_id:str):
        uid=require_user(request);job=product.job(uid,job_id)
        if not job:raise HTTPException(404,"Opportunity not found")
        raw=job.get("payload") or {}
        analysis=(raw.get("analysis") or {})
        if len(str(raw.get("description") or ""))>=120:
            result=match.analyze_job(uid,raw)
            if result.get("ok"):analysis=result["analysis"]
        _,applied,rejections=history(uid)
        return {"job_id":job_id,"title":job["title"],"company":job["company"],
                "source_url":job.get("source_url"),
                "requirements":analysis.get("requirements",[]),
                "constraints":analysis.get("constraint_evaluation",{}),
                "proposal":analysis.get("proposal",{}),
                "final_action":analysis.get("final_action","VERIFY_FIRST"),
                "contractor_status":contract_signal(raw),
                "already_submitted":job_id in applied,
                "employer_rejected_before":job["company"].casefold() in rejections,
                "freshness":"Retrieved from employer ATS; confirm the vacancy is still open before submitting."}

    @router.get("/jobs/{job_id}/pack")
    def get_pack(request:Request,job_id:str):
        uid=require_user(request)
        if not product.job(uid,job_id):raise HTTPException(404,"Opportunity not found")
        return product.application_pack(uid,job_id,create=True)

    @router.put("/jobs/{job_id}/pack")
    async def save_pack(request:Request,job_id:str):
        check_origin(request);uid=require_user(request)
        if not product.job(uid,job_id):raise HTTPException(404,"Opportunity not found")
        data=await request.json()
        # Existing product policy ignores unsupported or unapproved proof.
        return product.save_application_pack(uid,job_id,data)

    @router.get("/jobs/{job_id}/export")
    def export_pack(request:Request,job_id:str):
        uid=require_user(request)
        if not product.job(uid,job_id):raise HTTPException(404,"Opportunity not found")
        saved=product.application_pack(uid,job_id,create=False)
        if not saved:raise HTTPException(404,"Prepare an application first")
        response=PlainTextResponse(pack_markdown(saved["data"]),media_type="text/markdown")
        response.headers["Content-Disposition"]='attachment; filename="rolehint-application.md"'
        response.headers["Cache-Control"]="private, no-store"
        return response

    @router.post("/jobs/{job_id}/handoff")
    def handoff(request:Request,job_id:str):
        check_origin(request);uid=require_user(request)
        job=product.job(uid,job_id)
        if not job:raise HTTPException(404,"Opportunity not found")
        url=str(job.get("source_url") or "")
        parsed=urlsplit(url)
        if parsed.scheme!="https" or not parsed.netloc:raise HTTPException(422,"Employer application URL unavailable")
        if any(s["job_id"]==job_id for s in product.submissions(uid)):
            raise HTTPException(409,"This opening is already recorded as submitted")
        now=time.time()
        store.execute("INSERT INTO web_application_handoffs VALUES(?,?,?,?,?) ON CONFLICT(user_id,job_id) DO UPDATE SET approved_at=excluded.approved_at,updated_at=excluded.updated_at",
                      (uid,job_id,now,"approved_handoff",now))
        store.commit()
        return {"url":url,"status":"approved_handoff","submitted":False,
                "message":"Employer form opened by user. Submission not yet confirmed."}

    @router.post("/jobs/{job_id}/submitted")
    def confirm_submitted(request:Request,job_id:str):
        check_origin(request);uid=require_user(request)
        job=product.job(uid,job_id)
        if not job:raise HTTPException(404,"Opportunity not found")
        hand=store.execute("SELECT * FROM web_application_handoffs WHERE user_id=? AND job_id=?",(uid,job_id)).fetchone()
        if not hand:raise HTTPException(409,"Approve the employer handoff first")
        prior=next((x for x in product.submissions(uid) if x["job_id"]==job_id),None)
        if prior:return {"status":"submitted","duplicate":True}
        key=hashlib.sha256((uid+":"+job_id).encode()).hexdigest()
        product.record_submission(uid,job_id,key,key,"MANUAL",source="user_confirmed_handoff",
                                  payload={"source_url":job.get("source_url"),"user_confirmed":True})
        store.execute("UPDATE web_application_handoffs SET state='user_confirmed_submitted',updated_at=? WHERE user_id=? AND job_id=?",
                      (time.time(),uid,job_id));store.commit()
        return {"status":"submitted","duplicate":False,"confirmation":"User reported successful employer submission"}

    @router.put("/jobs/{job_id}/outcome")
    async def outcome(request:Request,job_id:str):
        check_origin(request);uid=require_user(request)
        data=await request.json()
        state=data.get("state")
        if state not in {"awaiting_response","rejected","recruiter_or_interview","offer_candidate","offer_confirmed"}:
            raise HTTPException(422,"Invalid outcome")
        if not product.update_application_response(uid,job_id,state):raise HTTPException(404,"No confirmed submission for this job")
        return {"job_id":job_id,"state":state}
