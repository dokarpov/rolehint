from __future__ import annotations
import hashlib, math, re, time

PACE_PRESETS={
  "focused":{"weekly_target":16,"batch_size":4,"batch_minutes":45,"label":"Focused"},
  "balanced":{"weekly_target":23,"batch_size":5,"batch_minutes":60,"label":"Balanced"},
  "fast":{"weekly_target":35,"batch_size":7,"batch_minutes":80,"label":"Fast"},
  "urgent":{"weekly_target":45,"batch_size":9,"batch_minutes":105,"label":"Urgent"},
}
BREADTH_PRESETS={
  "precise":{"label":"Precise","p2_salary_floor":95000,"p0_coverage":.80,"p1_coverage":.75,"p2_coverage":.45,"p2_min_verified":2,"max_role_sprawl":4,"search_query_count":2},
  "standard":{"label":"Standard","p2_salary_floor":85000,"p0_coverage":.75,"p1_coverage":.70,"p2_coverage":.35,"p2_min_verified":2,"max_role_sprawl":4,"search_query_count":3},
  "wider":{"label":"Wider","p2_salary_floor":75000,"p0_coverage":.70,"p1_coverage":.60,"p2_coverage":.25,"p2_min_verified":1,"max_role_sprawl":5,"search_query_count":4},
  "broad":{"label":"Broad","p2_salary_floor":65000,"p0_coverage":.65,"p1_coverage":.55,"p2_coverage":.15,"p2_min_verified":1,"max_role_sprawl":6,"search_query_count":5},
}
DEFAULT_POLICY={
  "pace_preset":"balanced","breadth":"standard","weekly_target":23,
  "strong_salary":120000,"p2_salary_floor":85000,
  "p01_target":6,"p2_target":10,"low_cost_target":7,
  "batch_size":5,"batch_minutes":60,"repeat_cooldown_days":90,
  "adapt_after_unique":50,"adapt_review_at":75,
  "excluded_role_terms":[],"excluded_domains":[],"min_seniority":"senior","max_role_sprawl":4,
  "conversion_prior_low":.03,"conversion_prior_high":.06,
}
SENIORITY={"intern":0,"junior":1,"associate":1,"mid":2,"middle":2,"senior":3,"sr":3,"staff":4,"principal":4,"lead":4,"head":5,"director":5,"vp":6}
FUNCTIONS={
 "operations":["operations","operational","ops manager"],"sales":["sales quota","account executive","pipeline generation"],
 "marketing":["marketing campaigns","demand generation","brand marketing"],"support":["customer support","support tickets","customer service"],
 "implementation":["implementation manager","professional services","client implementation"],"engineering":["write production code","software engineer","coding daily"],
 "finance":["financial reporting","accounting","bookkeeping"],
}

def _norm(s): return re.sub(r"[^a-z0-9]+"," ",str(s or "").lower()).strip()
def _clamp(v,lo,hi): return max(lo,min(hi,v))

def _baseline_quotas(total):
    total=max(3,int(total));p01=max(1,int(round(total*(6/23))));p2=max(1,int(round(total*(10/23))))
    low=max(1,total-p01-p2);diff=total-(p01+p2+low);low+=diff
    return {"P01":p01,"P2":p2,"LOW_COST":low}

def normalize_policy(policy=None):
    raw={**DEFAULT_POLICY,**(policy or {})}
    pace=str(raw.get("pace_preset") or "balanced").lower()
    if pace not in PACE_PRESETS and pace!="custom": pace="balanced"
    breadth=str(raw.get("breadth") or "standard").lower()
    if breadth not in BREADTH_PRESETS: breadth="standard"
    if pace=="custom":
        target=_clamp(int(raw.get("weekly_target") or 23),10,60)
        batch_size=_clamp(int(raw.get("batch_size") or round(target/5)),4,10)
        batch_minutes=_clamp(int(raw.get("batch_minutes") or batch_size*12),40,150)
    else:
        pp=PACE_PRESETS[pace];target=int(pp["weekly_target"]);batch_size=int(pp["batch_size"]);batch_minutes=int(pp["batch_minutes"])
    bp=BREADTH_PRESETS[breadth];q=_baseline_quotas(target);out={**raw,**bp}
    out.update({
      "pace_preset":pace,"breadth":breadth,"weekly_target":target,"batch_size":batch_size,"batch_minutes":batch_minutes,
      "p01_target":q["P01"],"p2_target":q["P2"],"low_cost_target":q["LOW_COST"],
      "search_interval_minutes":{"focused":480,"balanced":360,"fast":240,"urgent":180,"custom":max(120,int(1440/max(2,target/6)))}[pace],
    })
    return out

def evidence_version(evidence):
    raw="|".join(sorted(f"{e.get('id')}:{e.get('status')}:{e.get('claim')}" for e in evidence));return hashlib.sha1(raw.encode()).hexdigest()[:16]

def requisition_id(job):
    text=" ".join([str(job.get("description") or ""),str(job.get("title") or "")])
    m=re.search(r"(?:requisition|req(?:uisition)?|job)\s*(?:id|#|number|no\.?)\s*[:#-]*\s*([a-z0-9-]{3,})",text,re.I)
    if m:return m.group(1)
    direct={"greenhouse","lever","ashby","workable","smartrecruiters","workday"}
    if str(job.get("source") or "").lower() in direct and job.get("source_job_id"):return str(job["source_job_id"])
    return None

def role_fingerprint(requirements):
    labels=sorted(_norm(r.get("label")) for r in requirements if r.get("label"));return hashlib.sha1("|".join(labels).encode()).hexdigest()[:16]

def application_base_key(job):
    company=_norm(job.get("company"));title=_norm(job.get("title"));rid=requisition_id(job)
    return hashlib.sha1(f"{company}|{title}|{rid or ''}".encode()).hexdigest()[:20]

def detect_seniority(title):
    words=_norm(title).split();found=[SENIORITY[w] for w in words if w in SENIORITY];return max(found) if found else 3

def role_sprawl(description):
    t=_norm(description);hits=[]
    for fn,terms in FUNCTIONS.items():
        if any(_norm(x) in t for x in terms):hits.append(fn)
    return hits

def friction(job):
    text=_norm(job.get("description"));src=str(job.get("source") or "").lower()
    cover=bool(re.search(r"\bcover letter\b|\bmotivation letter\b",text));assignment=bool(re.search(r"\btake home\b|\btake-home\b|\bcase study\b|\bassessment\b|\btest assignment\b|\bhomework\b",text));portfolio=bool(re.search(r"\bportfolio required\b|\bsubmit (?:a )?portfolio\b",text))
    base=5 if src in {"greenhouse","lever","ashby","workable","smartrecruiters","workday"} else (6 if src=="career_sites" else 8)
    minutes=base+(12 if cover else 0)+(45 if assignment else 0)+(8 if portfolio else 0)
    return {"estimated_minutes":minutes,"cover_letter":cover,"assignment":assignment,"portfolio_extra":portfolio,"low_cost":minutes<=5 and not cover and not assignment}

def hard_policy_checks(job,prefs,policy,constraints):
    p=normalize_policy(policy);hard=[];verify=[];title=_norm(job.get("title"));desc=_norm(job.get("description"))
    for term in p.get("excluded_role_terms") or []:
        if _norm(term) in title:hard.append(f"Excluded role term: {term}")
    for term in p.get("excluded_domains") or []:
        if _norm(term) in desc or _norm(term) in title:hard.append(f"Excluded domain: {term}")
    min_level=SENIORITY.get(str(p.get("min_seniority") or "senior").lower(),3)
    if detect_seniority(job.get("title"))<min_level:hard.append("Role seniority is below the configured minimum.")
    spread=role_sprawl(job.get("description"))
    if len(spread)>=int(p.get("max_role_sprawl",4)):hard.append("Role scope spans too many unrelated functions: "+", ".join(spread))
    if prefs.get("remote_only") and constraints.get("work_mode")=="unknown":verify.append("Remote/office mode is not explicit.")
    return hard,verify,spread

def classify(job,analysis,prefs,policy=None):
    p=normalize_policy(policy);constraints=analysis.get("constraints") or {};hard=list((analysis.get("constraint_evaluation") or {}).get("hard") or []);unknown=list((analysis.get("constraint_evaluation") or {}).get("unknown") or [])
    extra_hard,extra_verify,spread=hard_policy_checks(job,prefs,p,constraints);hard+=extra_hard;unknown+=extra_verify;f=friction(job)
    verified=int(analysis.get("verified_count") or 0);must=max(1,int(analysis.get("must_have_count") or 0));gaps=int(analysis.get("gap_count") or 0);coverage=verified/must
    salary_max=constraints.get("salary_max");salary_min=constraints.get("salary_min");currency=str(constraints.get("currency") or "").upper();comp=(salary_max if salary_max is not None else salary_min) if currency=="EUR" else None;strong_reason=verified>=1 or coverage>=.25
    if hard:tier="BLOCKED"
    elif unknown and any("Remote/office" in x or "location" in x.lower() for x in unknown):tier="VERIFY"
    elif comp is not None and float(comp)>=float(p["strong_salary"]) and coverage>=float(p["p1_coverage"]):tier="P0" if coverage>=float(p["p0_coverage"]) and gaps<=1 else "P1"
    elif coverage>=float(p["p1_coverage"]) and gaps<=2:tier="P1"
    elif coverage>=float(p["p2_coverage"]) or verified>=int(p["p2_min_verified"]):tier="P2"
    elif f["low_cost"] and strong_reason:tier="LOW_COST"
    else:tier="HOLD"
    penalty=(4 if comp is None else 0)+(5*min(gaps,2))+(8 if analysis.get("review_count") else 0);value=max(0,round(100*coverage-penalty+(10 if comp and float(comp)>=float(p["strong_salary"]) else 0),1))
    return {"tier":tier,"hard_blockers":hard,"verify_items":unknown,"role_sprawl":spread,"estimated_minutes":f["estimated_minutes"],"application_friction":f,"value_score":value,"strong_reason":strong_reason,"breadth":p["breadth"],"salary_signal":{"currency":currency or None,"observed_published_max":salary_max,"target_eur":p["strong_salary"],"below_target":comp is not None and float(comp)<float(p["strong_salary"]),"note":"Salary changes ranking, never blocks a role unless the user explicitly sets a hard floor. Non-EUR published bands are not numerically compared to EUR targets."}}

def _bounded_allocate(total,weights,mins,maxs):
    out={k:int(mins[k]) for k in weights};remaining=max(0,int(total)-sum(out.values()))
    while remaining:
        choices=[k for k in weights if out[k]<int(maxs[k])]
        if not choices:break
        k=max(choices,key=lambda x:weights[x]/max(1,out[x]-mins[x]+1));out[k]+=1;remaining-=1
    return out

def _adaptive_bounds(defaults):
    floors={"P01":max(1,int(round(defaults["P01"]*.83))),"P2":max(1,int(round(defaults["P2"]*.50))),"LOW_COST":max(1,int(round(defaults["LOW_COST"]*.43)))}
    caps={"P01":max(defaults["P01"],int(round(defaults["P01"]*1.65))),"P2":max(defaults["P2"],int(round(defaults["P2"]*1.20))),"LOW_COST":max(defaults["LOW_COST"],int(round(defaults["LOW_COST"]*1.45)))}
    return floors,caps

def adaptive_quotas(stats,policy=None):
    p=normalize_policy(policy);total=int(p["weekly_target"]);defaults=_baseline_quotas(total);n=sum(int(x.get("applications",0)) for x in stats.values());start=int(p["adapt_after_unique"]);full=max(start+1,int(p.get("adapt_review_at",75)))
    if n<start:return {**defaults,"mode":"baseline","sample":n,"learning_progress":0.0}
    pooled=sum(int(x.get("strong",0)) for x in stats.values())/max(1,n)
    def tier_score(keys):
        apps=sum(stats.get(k,{}).get("applications",0) for k in keys);strong=sum(stats.get(k,{}).get("strong",0) for k in keys);mins=[stats.get(k,{}).get("avg_minutes") for k in keys if stats.get(k,{}).get("avg_minutes")];effort=sum(mins)/len(mins) if mins else 15
        rate=(strong+4*pooled)/(apps+4) if apps else pooled;return max(.0001,rate)/math.sqrt(max(3,effort))
    weights={"P01":tier_score(["P0","P1"]),"P2":tier_score(["P2"]),"LOW_COST":tier_score(["LOW_COST"])};floors,caps=_adaptive_bounds(defaults);ideal=_bounded_allocate(total,weights,floors,caps)
    while sum(ideal.values())<total:ideal[max(weights,key=weights.get)]+=1
    alpha=min(1.0,max(0.0,(n-start)/max(1,full-start)))
    if n<full:
        raw={k:(1-alpha)*defaults[k]+alpha*ideal[k] for k in defaults};alloc={k:int(round(v)) for k,v in raw.items()};diff=total-sum(alloc.values())
        while diff:
            ordered=sorted(defaults,key=lambda k:(raw[k]-alloc[k]),reverse=(diff>0));moved=False
            for k in ordered:
                nv=alloc[k]+(1 if diff>0 else -1)
                if nv>=1:alloc[k]=nv;diff += -1 if diff>0 else 1;moved=True;break
            if not moved:break
        return {**alloc,"mode":"learning","sample":n,"weights":weights,"learning_progress":round(alpha,2)}
    return {**ideal,"mode":"adaptive","sample":n,"weights":weights,"learning_progress":1.0}

def conversion_forecast(stats,weekly_target,policy=None):
    p=normalize_policy(policy);n=sum(int(x.get("applications",0)) for x in stats.values());strong=sum(int(x.get("strong",0)) for x in stats.values());prior_low=float(p.get("conversion_prior_low",.03));prior_high=float(p.get("conversion_prior_high",.06));prior_mid=(prior_low+prior_high)/2;prior_half=(prior_high-prior_low)/2
    if n<=0:low,mid,high=prior_low,prior_mid,prior_high;mode="baseline";weight=0.0;observed=None
    else:
        observed=strong/n;weight=min(1.0,n/max(1,int(p.get("adapt_review_at",75))));mid=(1-weight)*prior_mid+weight*observed;empirical_half=max(.008,1.28*math.sqrt(max(mid*(1-mid),.0001)/max(n,1)));half=(1-weight)*prior_half+weight*empirical_half;low=max(0.0,mid-half);high=min(.50,mid+half);mode="observed" if weight>=1 else "blended"
    target=int(weekly_target)
    return {"mode":mode,"sample":n,"observed_rate_percent":None if observed is None else round(observed*100,1),"estimated_rate_low_percent":round(low*100,1),"estimated_rate_mid_percent":round(mid*100,1),"estimated_rate_high_percent":round(high*100,1),"expected_screenings_low":round(target*low,2),"expected_screenings_mid":round(target*mid,2),"expected_screenings_high":round(target*high,2),"data_weight":round(weight,2),"baseline_range_percent":[round(prior_low*100,1),round(prior_high*100,1)]}

def tier_conversion_forecasts(stats,policy=None):
    return {tier:conversion_forecast({tier:stats.get(tier) or {}},1,policy) for tier in ("P0","P1","P2","LOW_COST")}

def _job_funnel(j):
    p=j.get("payload") or {};return p.get("funnel") or (p.get("analysis") or {}).get("funnel") or {}

def weekly_plan(jobs,submissions,stats,policy=None,now=None):
    p=normalize_policy(policy);q=adaptive_quotas(stats,p);now=now or time.time();week_start=now-7*86400;week=[s for s in submissions if float(s.get("submitted_at") or 0)>=week_start and s.get("is_unique",True)]
    done={"P01":sum(s.get("tier") in {"P0","P1"} for s in week),"P2":sum(s.get("tier")=="P2" for s in week),"LOW_COST":sum(s.get("tier")=="LOW_COST" for s in week)};need={k:max(0,int(q[k])-int(done[k])) for k in done};groups={"P01":[],"P2":[],"LOW_COST":[],"VERIFY":[]};applied_job_ids={s.get("job_id") for s in submissions};applied_base_keys={s.get("base_key") for s in submissions if s.get("base_key")};unique={}
    for j in jobs:
        if j.get("job_id") in applied_job_ids:continue
        payload=j.get("payload") or {};raw={**payload,"company":j.get("company"),"title":j.get("title"),"description":payload.get("description","")};key=application_base_key(raw)
        if key in applied_base_keys:continue
        cur=unique.get(key)
        if cur is None or float(_job_funnel(j).get("value_score",0))>float(_job_funnel(cur).get("value_score",0)):unique[key]=j
    for j in unique.values():
        tier=_job_funnel(j).get("tier")
        if tier in {"P0","P1"}:groups["P01"].append(j)
        elif tier in groups:groups[tier].append(j)
    for k in groups:groups[k].sort(key=lambda j:(-float(_job_funnel(j).get("value_score",0)),int(_job_funnel(j).get("estimated_minutes",30))))
    queue=[]
    for k in ("P01","P2","LOW_COST"):queue.extend(groups[k][:need[k]])
    queue=queue[:int(p["weekly_target"])];batch=[];minutes=0
    for j in queue:
        m=int(_job_funnel(j).get("estimated_minutes",10))
        if len(batch)>=int(p["batch_size"]):break
        if batch and minutes+m>int(p["batch_minutes"]):break
        batch.append(j);minutes+=m
    forecast=conversion_forecast(stats,p["weekly_target"],p)
    return {"policy":p,"quotas":q,"completed":done,"remaining":need,"queue":queue,"today_batch":batch,"today_minutes":minutes,"target_total":int(p["weekly_target"]),"verify":groups["VERIFY"][:5],"conversion_forecast":forecast,"tier_conversion_forecasts":tier_conversion_forecasts(stats,p),"expected_screenings":{"mode":forecast["mode"],"low":forecast["expected_screenings_low"],"mid":forecast["expected_screenings_mid"],"high":forecast["expected_screenings_high"]}}

def requirement_similarity(a,b):
    aa={_norm(x) for x in (a or []) if _norm(x)};bb={_norm(x) for x in (b or []) if _norm(x)}
    if not aa and not bb:return 1.0
    if not aa or not bb:return 0.0
    return len(aa&bb)/len(aa|bb)

def submission_candidate(product,user_id,job,policy=None,now=None):
    p=normalize_policy(policy);now=now or time.time();payload=job.get("payload") or {};analysis=payload.get("analysis") or {};reqs=analysis.get("requirements") or [];labels=[r.get("label","") for r in reqs];raw={**payload,"company":job.get("company"),"title":job.get("title"),"description":payload.get("description","")};base=application_base_key(raw);rid=requisition_id(raw);fp=role_fingerprint(reqs);ev=evidence_version(product.user_evidence(user_id,status="verified"));last=product.latest_submission_for_base(user_id,base)
    if not last:return {"eligible":True,"application_key":base,"base_key":base,"requisition_id":rid,"role_fingerprint":fp,"evidence_version":ev,"reason":"new_unique_role","requirement_labels":labels}
    old_payload={}
    try:old_payload=__import__('json').loads(last.get("payload_json") or "{}")
    except Exception:pass
    old_labels=old_payload.get("requirement_labels") or []
    if requirement_similarity(labels,old_labels)<.60 and labels and old_labels:
        key=f"{base}:changed:{fp[:8]}";return {"eligible":True,"application_key":key,"base_key":base,"requisition_id":rid,"role_fingerprint":fp,"evidence_version":ev,"reason":"substantially_changed_role","requirement_labels":labels}
    age_days=(now-float(last.get("submitted_at") or now))/86400
    if age_days>=int(p.get("repeat_cooldown_days",90)) and ev and ev!=last.get("evidence_version"):
        key=f"{base}:repeat:{int(now//86400)}";return {"eligible":True,"application_key":key,"base_key":base,"requisition_id":rid,"role_fingerprint":fp,"evidence_version":ev,"reason":"cooldown_plus_new_evidence","requirement_labels":labels}
    return {"eligible":False,"application_key":last.get("application_key"),"base_key":base,"requisition_id":rid,"role_fingerprint":fp,"evidence_version":ev,"reason":"duplicate_application","requirement_labels":labels}
