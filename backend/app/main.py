from __future__ import annotations
import os, tempfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from .models import SearchQuery
from .services.evidence_store import EvidenceStore
from .services.evidence_ingest import ingest_path
from .services.job_search import JobSearchService
from .services.esco import EscoNormalizer
from .services.vector_retrieval import LocalLSIRetriever, HybridRetriever
from .services.scheduler.subscriptions import SubscriptionStore
from .services.scheduler.runner import run_due_once
from .services.state.career_store import CareerStore
from .services.analytics.metrics import dashboard_metrics
from .services.outreach.drafts import build_outreach_draft
from .services.evidence_rebuild import rebuild_evidence
from .services.telegram import validate_init_data, TelegramAuthError, identity_from_init_data
from .services.runtime import runtime_config, capabilities
from .services.runtime.local_secrets import LocalSecretStore
from .services.product_state import ProductStore
from .services.billing import SKU
from .services.oauth import GoogleOAuth, GitHubOAuth, cipher_for, encrypt_json, decrypt_json
from .services.application_tracking import reduce_application_state, GmailSyncService
from .services.application_packs import markdown as pack_markdown, html_document as pack_html, safe_filename
from .services.pack_proposal import extract_requirements as extract_pack_requirements, propose as propose_pack
from .services.auto_match import AutoMatchService
from .services.autopilot import EvidenceAutopilot, ensure_search_profiles
from .services.funnel import weekly_plan, DEFAULT_POLICY, PACE_PRESETS, BREADTH_PRESETS, normalize_policy, submission_candidate
from .services.connectors.gmail import GmailConnector, parse_job_email
from .web_identity import init_routes as web_identity_routes
from .anonymous_jobs import router as anonymous_jobs_router

app=FastAPI(title="Career Fit Agent API",version="1.8.0")
app.include_router(anonymous_jobs_router)

@app.middleware("http")
async def beta_access_guard(request: Request, call_next):
    """Do not expose legacy unauthenticated endpoints while the public beta is being secured."""
    if os.getenv("CFA_PUBLIC_BETA_LOCK", "0") == "1":
        path=request.url.path
        if not (path in ("/health","/open-bot") or (path == "/miniapp" or path.startswith("/miniapp/")) or path.startswith("/me/") or path.startswith("/web-api/") or path == "/webapp" or path.startswith("/webapp/") or path == "/telegram/auth" or path in ("/oauth/google/callback", "/oauth/github/callback") or path.startswith("/internal/telegram/")):
            return Response(
                content='{"detail":"RoleHint backend is being prepared for private beta"}',
                media_type="application/json",
                status_code=503,
            )
    return await call_next(request)

DATA_DIR=Path(os.getenv("CFA_DATA_DIR", Path(__file__).resolve().parents[2]/"data"))
DATA_DIR.mkdir(parents=True,exist_ok=True)
store=EvidenceStore(DATA_DIR/"career_fit.db")
esco=EscoNormalizer(DATA_DIR/"esco_cache.json")
subscriptions=SubscriptionStore(DATA_DIR/"career_fit.db")
career=CareerStore(DATA_DIR/"career_state.db")
vector=LocalLSIRetriever()
hybrid=HybridRetriever(store,vector)
product=ProductStore(DATA_DIR/"product_state.db")
auto_match=AutoMatchService(product)
app.include_router(web_identity_routes(product))
local_secrets=LocalSecretStore(DATA_DIR/"local_secrets.json")
_runtime=runtime_config()
_token_cipher=cipher_for(DATA_DIR,_runtime.managed)
_google=GoogleOAuth()
_github=GitHubOAuth()
_gmail_sync=GmailSyncService(product,_token_cipher,_google,os.getenv("GMAIL_PUBSUB_TOPIC"),_runtime)
_evidence_autopilot=EvidenceAutopilot(product,_token_cipher,_gmail_sync)


def env_list(name):
    return [x.strip() for x in os.getenv(name,"").split(",") if x.strip()]

jobs=JobSearchService(
    ashby_boards=env_list("ASHBY_BOARDS"),
    lever_sites=env_list("LEVER_SITES"),
    greenhouse_boards=env_list("GREENHOUSE_BOARDS"),
    workable_accounts=env_list("WORKABLE_ACCOUNTS"),
    smartrecruiters_companies=env_list("SMARTRECRUITERS_COMPANIES"),
    career_site_urls=env_list("CAREER_SITE_URLS")+env_list("VC_PORTFOLIO_JOB_URLS")
)

@app.get("/open-bot")
async def open_real_telegram_bot():
    """Redirect to the bot identified by the deployed token, never a guessed handle."""
    import httpx
    token=os.getenv("TELEGRAM_BOT_TOKEN","")
    if not token:
        raise HTTPException(503,"Telegram bot is not configured")
    try:
        async with httpx.AsyncClient(timeout=7) as client:
            response=await client.get("https://api.telegram.org/bot"+token+"/getMe")
            response.raise_for_status()
            info=response.json()
        handle=str((info.get("result") or {}).get("username") or "")
        if not info.get("ok") or not handle or not handle.replace("_","").isalnum():
            raise ValueError("Invalid Telegram bot metadata")
        return RedirectResponse("https://t.me/"+handle,status_code=302)
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503,"Telegram bot link unavailable. Try again shortly.")

@app.get("/health")
def health():
    return {"ok":True,"version":"1.8.0","runtime":runtime_config().mode}

@app.get("/evidence")
def list_evidence():
    return store.all()

@app.get("/evidence/search")
def search_evidence(q:str,limit:int=10):
    return store.search(q,limit)

@app.post("/evidence/upload")
async def upload_evidence(file:UploadFile=File(...)):
    suffix=Path(file.filename or "").suffix
    with tempfile.NamedTemporaryFile(delete=False,suffix=suffix) as tmp:
        tmp.write(await file.read()); path=tmp.name
    try:
        items=ingest_path(path)
        for item in items:
            item["source_ref"]=file.filename or item["source_ref"]
            store.upsert(item)
        return {"imported":len(items),"status":"needs-review"}
    finally:
        Path(path).unlink(missing_ok=True)

@app.post("/jobs/search")
async def search_jobs(payload:SearchQuery):
    return await jobs.search(payload.query,payload.countries,payload.remote_only,payload.sources)

@app.post("/evidence/confirm/{evidence_id}")
def confirm_evidence(evidence_id:str):
    rows=[x for x in store.all() if x["id"]==evidence_id]
    if not rows: raise HTTPException(404,"Evidence not found")
    item=rows[0]; item["status"]="verified"; store.upsert(item)
    return item

@app.post("/evidence/reindex")
def reindex_evidence():
    hybrid.rebuild()
    return {"indexed":len(store.all()),"engine":"local-lsi-hybrid"}

@app.get("/evidence/hybrid-search")
def hybrid_search(q:str,limit:int=10):
    if vector.vectorizer is None:
        hybrid.rebuild()
    return hybrid.search(q,limit)

@app.get("/taxonomy/esco/occupation")
async def normalize_occupation(title:str,language:str="en"):
    return await esco.normalize_title(title,language)

@app.post("/subscriptions")
def save_subscription(payload:dict):
    subscriptions.upsert_subscription(payload)
    return {"ok":True,"id":payload["id"]}

@app.post("/subscriptions/run-due")
async def run_due():
    return await run_due_once(subscriptions,jobs)

@app.post("/jobs/{job_id}/notes")
def add_job_note(job_id:str,payload:dict):
    return {"id":career.add_note(job_id,payload["body"])}

@app.get("/jobs/{job_id}/notes")
def get_job_notes(job_id:str):
    return career.notes(job_id)

@app.post("/contacts")
def add_contact(payload:dict):
    return {"id":career.add_contact(payload)}

@app.get("/jobs/{job_id}/contacts")
def job_contacts(job_id:str):
    return career.contacts_for_job(job_id)

@app.get("/tasks")
def tasks():
    return career.open_tasks()

@app.post("/outreach/draft")
def outreach_draft(payload:dict):
    return build_outreach_draft(payload["job"],payload.get("contact"),payload.get("proof_cards",[]),payload.get("channel","linkedin"))

@app.post("/analytics/dashboard")
def analytics_dashboard(payload:dict):
    return dashboard_metrics(**payload)

@app.post("/telegram/auth")
def telegram_auth(payload:dict):
    token=os.getenv("TELEGRAM_BOT_TOKEN")
    if not token: raise HTTPException(503,"Telegram bot token not configured")
    try: data=validate_init_data(payload.get("initData",""),token)
    except TelegramAuthError as e: raise HTTPException(401,str(e))
    return {"ok":True,"user":data["user"]}

@app.post("/evidence/deep-rebuild")
def deep_rebuild(payload:dict):
    return rebuild_evidence(payload.get("candidates") or [],payload.get("previous_profile"))



def _ensure_local_evidence(user_id):
    # Legacy sample evidence is demo-only. Never seed real users with someone else's proof.
    if runtime_config().selfhost and os.getenv("CFA_SEED_DEMO","0")=="1" and product.count_user_evidence(user_id)==0:
        for item in store.all():
            product.upsert_user_evidence(user_id,item)

def _job_text(job):
    payload=(job or {}).get("payload") or {}
    return str(payload.get("description") or payload.get("vacancy_text") or payload.get("job_description") or "")

def _identity(x_telegram_init_data: str|None):
    return identity_from_init_data(x_telegram_init_data,product)

def _entitlement_payload(user_id):
    ent=product.entitlement(user_id)
    return {
      "active":bool(ent),
      "sku":ent["sku"] if ent else None,
      "active_until":ent["active_until"] if ent else None
    }

def _bootstrap(user_id):
    _ensure_local_evidence(user_id)
    autopilot=ensure_search_profiles(product,user_id)
    ent=_entitlement_payload(user_id)
    jobs_data=product.jobs(user_id)
    actions=product.open_actions(user_id,5)
    timeline=product.email_timeline(user_id,limit=20)
    state=reduce_application_state(timeline)
    metrics=product.dashboard_metrics(user_id)
    stats=product.conversion_stats(user_id)
    funnel=weekly_plan(jobs_data,product.submissions(user_id),stats,product.funnel_policy(user_id))
    evidence_health="empty" if metrics["evidence_total"]==0 else ("stable" if metrics["evidence_verified"] else "needs review")
    return {
      "runtime":runtime_config().mode,
      "entitlement":ent,
      "free_discovery":{"limit":10,"used":min(10,len(jobs_data)),"remaining":max(0,10-len(jobs_data)),"requires_card":False,"active":not ent["active"]},
      "capabilities":{**capabilities(ent["active"]), "oauth_google_ready":_google.configured(), "oauth_github_ready":_github.configured()},
      "metrics":metrics,
      "next_actions":actions,
      "jobs":jobs_data,
      "funnel":funnel,
      "funnel_policy":funnel.get("policy") or normalize_policy(product.funnel_policy(user_id)),
      "onboarding":product.onboarding_status(user_id),
      "preferences":product.preferences(user_id),
      "conversion_by_tier":stats,
      "autopilot":{"mode":autopilot["mode"],"search_profiles":autopilot["profiles"],"connectors":product.connector_summary(user_id)},
      "profile":{"target":product.search_target_label(user_id),"evidence_health":evidence_health,"recurring_gap":None},
      "application_state":state,
      "timeline":timeline[:8]
    }

@app.get("/me/bootstrap")
def me_bootstrap(x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    return _bootstrap(ident["user_id"])

@app.get("/me/jobs/{job_id}")
def me_job(job_id:str,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    j=product.job(ident["user_id"],job_id)
    if not j: raise HTTPException(404,"Job not found")
    return j

@app.put("/me/jobs/{job_id}/note")
def me_save_note(job_id:str,payload:dict,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    if not product.job(ident["user_id"],job_id): raise HTTPException(404,"Job not found")
    return product.save_note(ident["user_id"],job_id,str(payload.get("body",""))[:5000])

@app.post("/me/jobs/{job_id}/actions/{action_type}")
def me_resolve_action(job_id:str,action_type:str,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    return product.resolve_action(ident["user_id"],job_id,action_type)

@app.post("/me/profile/actions/{action_type}")
def me_profile_action(action_type:str,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    if action_type=="create_proof_task":
        career.add_task("Capture direct production retrieval/RAG proof",priority="high",source="profile_signal")
    product.resolve_action(ident["user_id"],None,"evidence_gap")
    return {"ok":True}

@app.get("/me/timeline")
def me_timeline(x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    events=product.email_timeline(ident["user_id"])
    return {"state":reduce_application_state(events),"events":events}

@app.post("/me/connectors/google/start")
def google_connect_start(x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    if not _google.configured():
        raise HTTPException(503,"Google OAuth not configured")
    import secrets
    state=secrets.token_urlsafe(24)
    product.oauth_session(state,ident["user_id"],"google",runtime_config().mini_app_url,create=True)
    return {"url":_google.authorize_url(state)}

@app.get("/oauth/google/callback")
async def google_callback(state:str,code:str):
    sess=product.oauth_session(state)
    if not sess: raise HTTPException(400,"Invalid OAuth state")
    tokens=await _google.exchange(code)
    import time as _time
    tokens["obtained_at"]=_time.time()
    tokens["expires_at"]=_time.time()+int(tokens.get("expires_in",3600))
    product.save_connector_token(sess["user_id"],"google",encrypt_json(_token_cipher,tokens),"gmail.readonly drive.readonly")
    product.mark_source_sync(sess["user_id"],"google","pending",0)
    product.delete_oauth_session(state)
    target=(sess.get("redirect_uri") or runtime_config().mini_app_url or "/")
    sep="&" if "?" in target else "?"
    return RedirectResponse(target+sep+"connected=google")

async def _google_access_token(user_id):
    rec=product.connector_token(user_id,"google")
    if not rec: raise HTTPException(404,"Google connector not connected")
    tok=decrypt_json(_token_cipher,rec["encrypted_json"])
    # Google access tokens typically expire in ~3600s; store created_at locally if known.
    # Refresh on 401 in the sync path or when no access token is present.
    if tok.get("access_token"): return tok["access_token"],tok
    if not tok.get("refresh_token"): raise HTTPException(401,"Google connector requires reauthorization")
    fresh=await _google.refresh(tok["refresh_token"])
    fresh["refresh_token"]=tok["refresh_token"]
    product.save_connector_token(user_id,"google",encrypt_json(_token_cipher,fresh),rec.get("scopes",""))
    return fresh["access_token"],fresh

@app.post("/me/connectors/github/start")
def github_connect_start(x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    if not _github.configured():raise HTTPException(503,"GitHub OAuth not configured")
    import secrets
    state=secrets.token_urlsafe(24)
    product.oauth_session(state,ident["user_id"],"github",runtime_config().mini_app_url,create=True)
    return {"url":_github.authorize_url(state)}

@app.get("/oauth/github/callback")
async def github_callback(state:str,code:str):
    sess=product.oauth_session(state)
    if not sess or sess.get("provider")!="github":raise HTTPException(400,"Invalid OAuth state")
    token=await _github.exchange(code)
    product.save_connector_token(sess["user_id"],"github",encrypt_json(_token_cipher,token),"repo")
    product.mark_source_sync(sess["user_id"],"github","pending",0)
    product.delete_oauth_session(state)
    target=(sess.get("redirect_uri") or runtime_config().mini_app_url or "/");sep="&" if "?" in target else "?"
    return RedirectResponse(target+sep+"connected=github")

@app.post("/me/connectors/google/sync")
async def google_sync(x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    ent=_entitlement_payload(ident["user_id"])
    if runtime_config().managed and not ent["active"]:
        raise HTTPException(402,"Managed Search Cycle required")
    full=await _gmail_sync.full_sync(ident["user_id"])
    watch=await _gmail_sync.register_watch(ident["user_id"])
    return {"full":full,"watch":watch,"timeline":product.email_timeline(ident["user_id"],limit=20)}

@app.post("/me/timeline/{event_id}/confirm-offer")
def confirm_offer(event_id:str,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    # Confirmation is stored as a new explicit event, preserving the email-derived candidate separately.
    existing=[e for e in product.email_timeline(ident["user_id"],limit=200) if e["id"]==event_id]
    if not existing: raise HTTPException(404,"Event not found")
    src=existing[0]
    ev={"message_id":"confirm:"+event_id,"event_type":"offer_confirmed","subject":src.get("subject"),
        "from":"user-confirmed","date":src.get("occurred_at"),"body_text":""}
    product.add_email_event(ident["user_id"],ev,src.get("job_id"))
    return {"ok":True,"state":reduce_application_state(product.email_timeline(ident["user_id"]))}

def _check_bot_secret(secret):
    expected=os.getenv("CFA_INTERNAL_BOT_SECRET")
    if not expected or secret!=expected: raise HTTPException(401,"Invalid bot secret")

@app.get("/internal/telegram/{telegram_user_id}/summary")
def internal_tg_summary(telegram_user_id:str,x_cfa_bot_secret:str|None=Header(default=None,alias="X-CFA-Bot-Secret")):
    _check_bot_secret(x_cfa_bot_secret)
    u=product.user_by_telegram_id(telegram_user_id)
    if not u:
        uid=product.ensure_user({"id":telegram_user_id,"first_name":""})
    else: uid=u["id"]
    return _bootstrap(uid)

@app.post("/billing/telegram-stars/confirm")
def billing_confirm(payload:dict,x_cfa_bot_secret:str|None=Header(default=None,alias="X-CFA-Bot-Secret")):
    _check_bot_secret(x_cfa_bot_secret)
    u=product.user_by_telegram_id(str(payload["telegram_user_id"]))
    uid=u["id"] if u else product.ensure_user({"id":payload["telegram_user_id"],"first_name":payload.get("first_name","")})
    charge=payload["telegram_payment_charge_id"]
    ent=product.grant_entitlement(uid,"managed_search_cycle","telegram_stars",charge,runtime_config().managed_cycle_days,payload)
    return {"ok":True,"entitlement":ent}

@app.get("/setup/status")
def setup_status():
    if not runtime_config().selfhost: raise HTTPException(404,"Self-host setup is disabled")
    saved=local_secrets.read()
    provider=product.setting("llm_provider","ollama")
    return {
      "runtime":"selfhost","provider":provider,
      "providers":{
        "ollama":{"configured":bool(saved.get("OLLAMA_BASE_URL") or os.getenv("OLLAMA_BASE_URL"))},
        "openai":{"configured":bool(saved.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"))},
        "anthropic":{"configured":bool(saved.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))},
        "openrouter":{"configured":bool(saved.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY"))}
      },
      "google_oauth":{"configured":_google.configured()},
      "github":{"configured":bool(saved.get("GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN"))}
    }

@app.post("/setup/config")
def setup_config(payload:dict):
    if not runtime_config().selfhost: raise HTTPException(404,"Self-host setup is disabled")
    provider=payload.get("provider","ollama")
    if provider not in {"ollama","openai","anthropic","openrouter"}: raise HTTPException(400,"Unsupported provider")
    product.set_setting("llm_provider",provider)
    secret_updates={}
    for key in ["OLLAMA_BASE_URL","OPENAI_API_KEY","ANTHROPIC_API_KEY","OPENROUTER_API_KEY","GITHUB_TOKEN",
                "GOOGLE_CLIENT_ID","GOOGLE_CLIENT_SECRET"]:
        if payload.get(key): secret_updates[key]=payload[key]
    local_secrets.merge(secret_updates)
    return {"ok":True,"provider":provider,"stored_keys":list(secret_updates)}


@app.post("/webhooks/gmail/pubsub")
async def gmail_pubsub_webhook(request:Request,token:str|None=None):
    expected=os.getenv("GMAIL_PUBSUB_WEBHOOK_TOKEN")
    if expected and token!=expected:
        raise HTTPException(401,"Invalid Pub/Sub webhook token")
    payload=await request.json()
    msg=(payload or {}).get("message") or {}
    raw=msg.get("data")
    if not raw:
        return {"ok":True,"ignored":"missing data"}
    import base64 as _b64, json as _json
    try:
        data=_json.loads(_b64.urlsafe_b64decode(raw+"="*((4-len(raw)%4)%4)).decode())
    except Exception:
        raise HTTPException(400,"Invalid Pub/Sub data")
    email=data.get("emailAddress");history=data.get("historyId")
    if not email or not history:
        return {"ok":True,"ignored":"missing Gmail fields"}
    product.enqueue_gmail_push(msg.get("messageId") or product.uid("pubsub"),email,history)
    # HTTP 200 acknowledges Pub/Sub quickly; worker does expensive Gmail work.
    return {"ok":True}


@app.get("/me/onboarding")
def onboarding_status(x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    uid=ident["user_id"]
    return {
      "onboarding":product.onboarding_status(uid),
      "preferences":product.preferences(uid),
      "funnel_policy":normalize_policy(product.funnel_policy(uid)),
      "connectors":product.connector_summary(uid)
    }

@app.put("/me/onboarding/progress")
def onboarding_progress(payload:dict,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    return product.save_onboarding_progress(ident["user_id"],payload)

@app.post("/me/onboarding/complete")
def onboarding_complete(payload:dict,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data);uid=ident["user_id"]
    # Onboarding asks only for genuine hard preferences + search pace.
    pref_patch={k:payload[k] for k in ["remote_only","allow_relocation","salary_floor_annual","home_region","allowed_regions"] if k in payload}
    if pref_patch:product.save_preferences(uid,pref_patch)
    pace=str(payload.get("pace_preset") or "balanced")
    if pace not in {"focused","balanced","urgent"}:pace="balanced"
    # Reach deliberately stays at Standard during onboarding. Advanced reach belongs in Settings.
    product.save_funnel_policy(uid,{"pace_preset":pace,"breadth":"standard"})
    completed=product.complete_onboarding(uid,{"pace_preset":pace,"breadth":"standard","source_step_skipped":bool(payload.get("source_step_skipped",False))})
    autopilot=ensure_search_profiles(product,uid)
    return {"onboarding":completed,"preferences":product.preferences(uid),"funnel_policy":normalize_policy(product.funnel_policy(uid)),"autopilot":autopilot}

@app.get("/me/preferences")
def get_preferences(x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    return product.preferences(ident["user_id"])

@app.put("/me/preferences")
def save_preferences(payload:dict,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    return product.save_preferences(ident["user_id"],payload)

@app.post("/me/jobs/ingest-url")
async def ingest_job_url(payload:dict,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data);_ensure_local_evidence(ident["user_id"])
    url=str(payload.get("url","")).strip()
    if not url.startswith(("http://","https://")):raise HTTPException(400,"A valid vacancy URL is required")
    result=await auto_match.ingest_url(ident["user_id"],url)
    if not result.get("ok"):
        if result.get("retryable"):
            product.queue_vacancy_fetch(ident["user_id"],url,result.get("error"))
            result["queued_for_retry"]=True
        raise HTTPException(422,detail=result)
    return result

@app.post("/me/jobs/{job_id}/analyze")
async def analyze_stored_job(job_id:str,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data);_ensure_local_evidence(ident["user_id"])
    try:result=await auto_match.ensure_analyzed(ident["user_id"],job_id)
    except LookupError as e:raise HTTPException(404,str(e))
    if not result.get("ok"):
        job=product.job(ident["user_id"],job_id)
        if result.get("retryable") and job and job.get("source_url"):
            product.queue_vacancy_fetch(ident["user_id"],job["source_url"],result.get("error"));result["queued_for_retry"]=True
        raise HTTPException(422,detail=result)
    return result

@app.post("/internal/telegram/{telegram_user_id}/ingest-url")
async def internal_ingest_url(telegram_user_id:str,payload:dict,x_cfa_bot_secret:str|None=Header(default=None,alias="X-CFA-Bot-Secret")):
    _check_bot_secret(x_cfa_bot_secret)
    u=product.user_by_telegram_id(telegram_user_id)
    uid=u["id"] if u else product.ensure_user({"id":telegram_user_id,"first_name":payload.get("first_name","")})
    _ensure_local_evidence(uid)
    url=str(payload.get("url","")).strip()
    result=await auto_match.ingest_url(uid,url)
    if not result.get("ok") and result.get("retryable"):
        product.queue_vacancy_fetch(uid,url,result.get("error"));result["queued_for_retry"]=True
    return result

@app.post("/me/search-profiles")
def save_search_profile(payload:dict,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    if not str(payload.get("query","")).strip():raise HTTPException(400,"query is required")
    return product.upsert_search_profile(ident["user_id"],payload)

@app.post("/me/autopilot/refresh")
async def refresh_autopilot(x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data);uid=ident["user_id"]
    if product.connector_connected(uid,"google"):await _evidence_autopilot.sync_google(uid,force=True)
    if product.connector_connected(uid,"github"):await _evidence_autopilot.sync_github(uid,force=True)
    return ensure_search_profiles(product,uid)

@app.get("/me/funnel")
def me_funnel(x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data);uid=ident["user_id"]
    return weekly_plan(product.jobs(uid),product.submissions(uid),product.conversion_stats(uid),product.funnel_policy(uid))

@app.put("/me/funnel/policy")
def save_funnel_policy(payload:dict,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data);uid=ident["user_id"]
    allowed={k:v for k,v in payload.items() if k in DEFAULT_POLICY}
    saved=product.save_funnel_policy(uid,allowed)
    normalized=normalize_policy(saved)
    reclassified=0
    for stored in product.jobs(uid):
        raw=dict(stored.get("payload") or {})
        if len(str(raw.get("description") or ""))<120:continue
        raw.setdefault("company",stored["company"]);raw.setdefault("title",stored["title"])
        raw.setdefault("location",stored.get("location"));raw.setdefault("source_url",stored.get("source_url"))
        try:auto_match.analyze_job(uid,raw);reclassified+=1
        except Exception:continue
    for profile in product.search_profiles(uid):
        if profile["id"].startswith("auto_"):
            product.conn.execute("UPDATE user_search_profiles SET enabled=0 WHERE user_id=? AND id=?",(uid,profile["id"]))
    product.conn.commit()
    autopilot=ensure_search_profiles(product,uid)
    plan=weekly_plan(product.jobs(uid),product.submissions(uid),product.conversion_stats(uid),saved)
    return {"policy":normalized,"plan":plan,"reclassified":reclassified,"autopilot":autopilot}

@app.get("/me/funnel/options")
def funnel_options(x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    _identity(x_telegram_init_data)
    return {"pace_presets":PACE_PRESETS,"breadth_presets":BREADTH_PRESETS,"weekly_target_range":[10,60]}

@app.get("/me/evidence")
def me_evidence(status:str|None=None,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data);_ensure_local_evidence(ident["user_id"])
    return product.user_evidence(ident["user_id"],status)

@app.post("/me/evidence")
def me_upsert_evidence(payload:dict,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    item=payload.get("evidence") or payload
    required=["id","claim","evidence"]
    if any(not str(item.get(k,"")).strip() for k in required):raise HTTPException(400,"id, claim and evidence are required")
    product.upsert_user_evidence(ident["user_id"],item)
    return product.user_evidence_one(ident["user_id"],item["id"])

@app.get("/me/jobs/{job_id}/requirements")
def get_job_requirements(job_id:str,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    return product.job_requirements(ident["user_id"],job_id)

@app.post("/me/jobs/{job_id}/pack/propose")
async def propose_application_pack(job_id:str,payload:dict|None=None,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data);_ensure_local_evidence(ident["user_id"])
    try:result=await auto_match.ensure_analyzed(ident["user_id"],job_id)
    except LookupError as e:raise HTTPException(404,str(e))
    if not result.get("ok"):
        job=product.job(ident["user_id"],job_id)
        if result.get("retryable") and job and job.get("source_url"):
            product.queue_vacancy_fetch(ident["user_id"],job["source_url"],result.get("error"));result["queued_for_retry"]=True
        raise HTTPException(422,detail=result)
    resolved_job_id=result["job"]["job_id"]
    proposal=product.pack_proposal(ident["user_id"],resolved_job_id)
    if not proposal:proposal=product.save_pack_proposal(ident["user_id"],resolved_job_id,result["analysis"]["proposal"])
    return proposal

@app.get("/me/jobs/{job_id}/pack/proposal")
def get_pack_proposal(job_id:str,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    p=product.pack_proposal(ident["user_id"],job_id)
    if not p:raise HTTPException(404,"No proposal yet")
    return p

@app.post("/me/jobs/{job_id}/pack/proposal/approve")
def approve_application_pack(job_id:str,payload:dict,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    try:return product.approve_pack_proposal(ident["user_id"],job_id,payload.get("approved_suggestion_ids") or [])
    except ValueError as e:raise HTTPException(404,str(e))

@app.get("/me/jobs/{job_id}/pack")
def get_pack(job_id:str,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    if not product.job(ident["user_id"],job_id):raise HTTPException(404,"Job not found")
    return product.application_pack(ident["user_id"],job_id,create=True)

@app.put("/me/jobs/{job_id}/pack")
def save_pack(job_id:str,payload:dict,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    if not product.job(ident["user_id"],job_id):raise HTTPException(404,"Job not found")
    return product.save_application_pack(ident["user_id"],job_id,payload.get("data") or payload)

@app.post("/me/jobs/{job_id}/pack/export")
def export_pack(job_id:str,payload:dict,request:Request,x_telegram_init_data: str|None=Header(default=None,alias="X-Telegram-Init-Data")):
    ident=_identity(x_telegram_init_data)
    pack=product.application_pack(ident["user_id"],job_id,create=True)
    fmt=(payload.get("format") or "md").lower()
    if fmt not in {"md","html"}:raise HTTPException(400,"format must be md or html")
    data=dict(pack["data"]);role=data.get("role") or {}
    # Revalidate proof against the current evidence source at export time.
    trusted=[]
    for card in data.get("proof_cards") or []:
        ev=product.user_evidence_one(ident["user_id"],card.get("evidence_id",""))
        if not ev or ev.get("status")!="verified":continue
        if not card.get("approved"):continue
        if str(card.get("claim","")).strip()!=str(ev.get("claim","")).strip():continue
        trusted.append({**card,"verified":True,"boundary":ev.get("boundary")})
    data["proof_cards"]=trusted
    if fmt=="md":
        content=pack_markdown(data);media="text/markdown";ext="md"
    else:
        content=pack_html(data);media="text/html";ext="html"
    filename=safe_filename(role.get("company",""),role.get("title",""),ext)
    token=product.create_export_download(ident["user_id"],job_id,fmt,content,filename)
    base=os.getenv("CFA_PUBLIC_BASE_URL")
    if base:url=base.rstrip("/")+"/downloads/"+token
    else:url=str(request.base_url).rstrip("/")+"/downloads/"+token
    return {"url":url,"file_name":filename,"format":fmt}

@app.get("/downloads/{token}",name="download_export")
def download_export(token:str):
    item=product.export_download(token)
    if not item:raise HTTPException(404,"Download expired or not found")
    media="text/html; charset=utf-8" if item["format"]=="html" else "text/markdown; charset=utf-8"
    return Response(
      content=item["content"],media_type=media,
      headers={
        "Content-Disposition":f'attachment; filename="{item["file_name"]}"',
        "Access-Control-Allow-Origin":"https://web.telegram.org",
        "Cache-Control":"private, max-age=300"
      })

_web_candidates=[]
if os.getenv("CFA_WEB_ROOT"):
    _web_candidates.append(Path(os.environ["CFA_WEB_ROOT"]))
_web_candidates += [Path(__file__).resolve().parents[2], Path.cwd()]
_WEB_ROOT=next((p for p in _web_candidates if (p/"telegram_miniapp").exists()), Path.cwd())
_SETUP_DIR=_WEB_ROOT/"selfhost_setup"
_MINI_DIR=_WEB_ROOT/"telegram_miniapp"
if _SETUP_DIR.exists():
    app.mount("/setup",StaticFiles(directory=str(_SETUP_DIR),html=True),name="setup")
if _MINI_DIR.exists():
    app.mount("/miniapp",StaticFiles(directory=str(_MINI_DIR),html=True),name="miniapp")
_WEBAPP_DIR=_WEB_ROOT/"webapp"
if _WEBAPP_DIR.exists():
    app.mount("/webapp",StaticFiles(directory=str(_WEBAPP_DIR),html=True),name="webapp")
