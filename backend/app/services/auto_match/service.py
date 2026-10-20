from __future__ import annotations
import re
from ..job_ingest import fetch_job
from ..jobs import normalize
from ..pack_proposal import extract_requirements, propose
from ..funnel import classify, submission_candidate


def _lower(x): return str(x or "").lower()


def _parse_published_salary(text):
    s=str(text or "")
    rx=re.compile(r"([$€£])\s*(\d{2,3}(?:[,.]\d{3})?|\d{2,3}(?:\.\d+)?)\s*([kK])?\s*(?:[-–—]|to)\s*([$€£])?\s*(\d{2,3}(?:[,.]\d{3})?|\d{2,3}(?:\.\d+)?)\s*([kK])?",re.I)
    for m in rx.finditer(s):
        def val(raw,k):
            n=float(raw.replace(",",""));return n*1000 if k or n<1000 else n
        lo=val(m.group(2),m.group(3));hi=val(m.group(5),m.group(6))
        if min(lo,hi)<25000:continue
        cur={"$":"USD","€":"EUR","£":"GBP"}.get(m.group(1) or m.group(4))
        return min(lo,hi),max(lo,hi),cur
    return None,None,None


def extract_constraints(job):
    text=_lower(job.get("description"));loc=_lower(job.get("location"));combined=text+" "+loc
    work_mode="unknown"
    if re.search(r"\b(remote[- ]first|fully remote|100% remote|remote role|remote position|remote within)\b",combined):work_mode="remote"
    if re.search(r"\b(hybrid|days? (?:a|per) week in (?:the )?office)\b",combined):work_mode="hybrid"
    if re.search(r"\b(on[- ]site|onsite|in[- ]office|office[- ]based)\b",combined) and work_mode=="unknown":work_mode="onsite"
    if job.get("remote") is True and work_mode=="unknown":work_mode="remote"
    relocation_required=bool(re.search(r"\b(relocation required|must relocate|required to relocate)\b",combined))
    # Only explicit exclusive geography becomes a hard eligibility signal. Ambiguous office labels stay VERIFY.
    geo=None
    geo_patterns=[
      ("US",r"\b(?:remote (?:only )?(?:in|within|from) (?:the )?(?:u\.?s\.?|united states)|(?:u\.?s\.?|united states)[ -]only|must be (?:located|based) in (?:the )?(?:u\.?s\.?|united states))\b"),
      ("UK",r"\b(?:remote (?:only )?(?:in|within|from) (?:the )?(?:uk|united kingdom)|(?:uk|united kingdom)[ -]only|must be (?:located|based) in (?:the )?(?:uk|united kingdom))\b"),
      ("Canada",r"\b(?:remote (?:only )?(?:in|within|from) canada|canada[ -]only|must be (?:located|based) in canada)\b"),
      ("Europe",r"\b(?:remote (?:only )?(?:in|within|from) (?:europe|eu|eea)|(?:europe|eu|eea)[ -]only|must be (?:located|based) in (?:europe|eu|eea))\b"),
      ("Spain",r"\b(?:remote (?:only )?(?:in|within|from) spain|spain[ -]only|must be (?:located|based) in spain)\b"),
    ]
    for label,pat in geo_patterns:
        if re.search(pat,combined,re.I):geo=label;break
    salary_min,salary_max,currency=job.get("salary_min"),job.get("salary_max"),job.get("currency")
    if salary_min is None and salary_max is None:salary_min,salary_max,currency=_parse_published_salary(job.get("description"))
    return {"work_mode":work_mode,"relocation_required":relocation_required,"salary_min":salary_min,"salary_max":salary_max,"currency":currency,"location":job.get("location"),"remote_geo_restriction":geo}


def evaluate_constraints(constraints,prefs):
    hard=[];unknown=[];notes=[]
    if prefs.get("remote_only"):
        if constraints["work_mode"] in {"hybrid","onsite"}:hard.append(f"Work mode is {constraints['work_mode']}, while the profile is remote-only.")
        elif constraints["work_mode"]=="unknown":unknown.append("Remote/office mode is not explicit in the source.")
    if not prefs.get("allow_relocation",True) and constraints["relocation_required"]:hard.append("The vacancy explicitly requires relocation.")
    floor=float(prefs.get("salary_floor_annual") or 0)
    salary_max=constraints.get("salary_max");salary_min=constraints.get("salary_min")
    published_max=salary_max if salary_max is not None else salary_min
    currency=str(constraints.get("currency") or "").upper()
    if floor and published_max is not None and currency=="EUR" and float(published_max)<floor:
        hard.append(f"Published EUR compensation ({float(published_max):g}) is below the configured EUR hard salary floor ({floor:g}).")
    elif floor and published_max is not None and currency!="EUR":
        unknown.append("Published compensation currency is not EUR or is unknown; verify before comparing with the EUR salary floor.")
    if salary_min is None and salary_max is None:notes.append("Compensation is undisclosed; this changes funnel priority, not eligibility by itself.")
    allowed=[_lower(x) for x in prefs.get("allowed_regions") or [] if str(x).strip()]
    home=_lower(prefs.get("home_region"))
    if home:allowed.append(home)
    restriction=constraints.get("remote_geo_restriction")
    if restriction and allowed:
        groups={
          "us":{"us","usa","united states","united states of america"},
          "uk":{"uk","gb","united kingdom","great britain"},
          "canada":{"canada","ca"},
          "spain":{"spain","es","europe","eu","eea"},
          "europe":{"spain","es","europe","eu","eea","germany","de","france","fr","italy","it","netherlands","nl","portugal","pt","ireland","ie"},
        }
        r=_lower(restriction);compatible=groups.get(r,{r})
        if not any(a in compatible or any(c in a for c in compatible) for a in allowed):
            hard.append(f"The vacancy explicitly restricts remote work to {restriction}, which does not match the configured work region.")
    elif allowed and constraints.get("location"):
        l=_lower(constraints["location"])
        if not any(a in l or l in a for a in allowed):unknown.append(f"Published location '{constraints['location']}' needs an eligibility check against configured regions.")
    return {"hard":hard,"unknown":unknown,"notes":notes,"state":"BLOCKED" if hard else ("VERIFY" if unknown else "CLEAR")}


def evidence_assessment(requirements,proposal):
    must=[r for r in requirements if r.get("mustHave")];denom=max(1,len(must));by_req={s["requirement_id"]:s for s in proposal.get("suggestions",[])}
    verified=review=missing=0
    for r in must:
        st=(by_req.get(r["id"]) or {}).get("match_status","missing")
        if st=="verified":verified+=1
        elif st=="needs_review":review+=1
        else:missing+=1
    return {"coverage":round(verified/denom,2),"verified_count":verified,"review_count":review,"gap_count":missing,"must_have_count":len(must)}


class AutoMatchService:
    def __init__(self,product_store): self.product=product_store

    async def ingest_url(self,user_id,url):
        job=await fetch_job(url)
        if job.get("fetch_status")!="ok":
            return {"ok":False,"source_url":url,"fetch_status":job.get("fetch_status","unavailable"),"fetch_method":job.get("fetch_method"),"error":job.get("fetch_error") or "Vacancy source unavailable.","retryable":True}
        return self.analyze_job(user_id,job)

    def analyze_job(self,user_id,job):
        job=normalize(job);description=str(job.get("description") or "").strip()
        if len(description)<120:return {"ok":False,"source_url":job.get("source_url"),"fetch_status":"insufficient","error":"The source did not provide enough vacancy text for a defensible match.","retryable":True}
        reqs=extract_requirements(description)
        if not reqs:return {"ok":False,"source_url":job.get("source_url"),"fetch_status":"parsed_no_requirements","error":"The vacancy was parsed, but no defensible requirements were extracted.","retryable":False}
        evidence=self.product.user_evidence(user_id);proposal=propose(job,reqs,evidence);constraints=extract_constraints(job);prefs=self.product.preferences(user_id);ce=evaluate_constraints(constraints,prefs)
        fit=evidence_assessment(reqs,proposal)
        base_analysis={**fit,"company":job.get("company"),"title":job.get("title"),"constraints":constraints,"constraint_evaluation":ce,
          "requirements":reqs,"proposal":proposal,"parser":{"source":job.get("source"),"method":job.get("fetch_method") or job.get("source"),"status":"ok"}}
        funnel=classify(job,base_analysis,prefs,self.product.funnel_policy(user_id))
        tier=funnel["tier"]
        if tier=="BLOCKED":action="DO_NOT_APPLY";reason=funnel["hard_blockers"][0] if funnel["hard_blockers"] else "Hard constraint failed."
        elif tier=="VERIFY":action="VERIFY_FIRST";reason=funnel["verify_items"][0] if funnel["verify_items"] else "One hard eligibility fact is unresolved."
        elif tier in {"P0","P1","P2","LOW_COST"}:action="APPLY";reason=f"Eligible {tier} funnel candidate. Evidence gaps affect effort/priority, not automatic rejection."
        else:action="DEPRIORITIZE";reason="Eligible but below the current weekly funnel priority."
        summary=f"{fit['verified_count']}/{fit['must_have_count']} must-haves direct verified"
        if fit["review_count"]:summary+=f" · {fit['review_count']} review"
        if fit["gap_count"]:summary+=f" · {fit['gap_count']} gaps"
        analysis={**base_analysis,"final_action":action,"reason":reason,"summary":summary,"funnel":funnel,
          "next_action":{"APPLY":"Open application pack","VERIFY_FIRST":"Await/resolve hard eligibility","DEPRIORITIZE":"No action","DO_NOT_APPLY":"No action"}[action],
          "blocking_reason":reason if action in {"VERIFY_FIRST","DO_NOT_APPLY"} else None,"estimated_minutes":funnel["estimated_minutes"]}
        pseudo={"company":job.get("company"),"title":job.get("title"),"payload":{**job,"analysis":analysis}}
        cand=submission_candidate(self.product,user_id,pseudo,self.product.funnel_policy(user_id))
        if not cand["eligible"]:
            analysis["funnel"]={**funnel,"tier":"DUPLICATE","duplicate_reason":cand["reason"]};analysis["final_action"]="ALREADY_APPLIED";analysis["reason"]="This application identity is already in history and does not qualify as a meaningful repeat.";analysis["next_action"]="No action";analysis["blocking_reason"]=None
        analysis["submission_candidate"]=cand
        saved=self.product.upsert_user_job(user_id,job,analysis);job_id=saved["job_id"]
        self.product.save_job_requirements(user_id,job_id,reqs);self.product.save_pack_proposal(user_id,job_id,proposal)
        if analysis["final_action"] in {"APPLY","VERIFY_FIRST"}:self.product.enqueue_job_action(user_id,job_id,analysis)
        return {"ok":True,"job":self.product.job(user_id,job_id),"analysis":analysis}

    async def ensure_analyzed(self,user_id,job_id):
        job=self.product.job(user_id,job_id)
        if not job:raise LookupError("Job not found")
        payload=job.get("payload") or {};existing=payload.get("analysis")
        if existing and existing.get("requirements"):return {"ok":True,"job":job,"analysis":existing}
        desc=str(payload.get("description") or "")
        if len(desc)>=120:
            raw=dict(payload);raw.setdefault("company",job["company"]);raw.setdefault("title",job["title"]);raw.setdefault("location",job["location"]);raw.setdefault("source_url",job["source_url"])
            return self.analyze_job(user_id,raw)
        if job.get("source_url"):return await self.ingest_url(user_id,job["source_url"])
        return {"ok":False,"fetch_status":"unavailable","error":"No retrievable source URL is stored for this vacancy.","retryable":False}
