"""First-party web identity. Email links are delivered only with configured SMTP; no debug tokens."""
from __future__ import annotations
import hashlib, hmac, os, re, secrets, smtplib, sqlite3, ssl, time, uuid, tempfile, json
from email.message import EmailMessage
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Header
from fastapi.responses import RedirectResponse, JSONResponse as ResponseJSON
from pathlib import Path
from .services.evidence_ingest import read_text, atomize_text
import httpx

router=APIRouter(prefix="/web-api")
COOKIE="rh_session"
EMAIL_RE=re.compile(r"^[^\s@]{1,64}@[^\s@]{1,250}\.[A-Za-z]{2,}$")

def init(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS web_accounts(
      email TEXT PRIMARY KEY COLLATE NOCASE, user_id TEXT NOT NULL UNIQUE REFERENCES users(id),
      created_at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS web_login_links(
      token_hash TEXT PRIMARY KEY, email TEXT NOT NULL,
      expires_at REAL NOT NULL, consumed_at REAL, created_at REAL NOT NULL);
    CREATE INDEX IF NOT EXISTS web_login_email_created ON web_login_links(email,created_at);
    CREATE TABLE IF NOT EXISTS web_candidate_profiles(
      user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
      source_name TEXT NOT NULL, text_content TEXT NOT NULL,
      evidence_json TEXT NOT NULL, updated_at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS web_cv_confirmations(
      user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
      cv_hash TEXT NOT NULL, confirmed_at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS web_telegram_challenges(
      challenge_id TEXT PRIMARY KEY, browser_hash TEXT NOT NULL,
      user_id TEXT, code_hash TEXT, tries INTEGER NOT NULL DEFAULT 0,
      expires_at REAL NOT NULL, consumed INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS web_sessions(
      token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
      expires_at REAL NOT NULL, created_at REAL NOT NULL);
    """)
    conn.commit()

def token_hash(token):return hashlib.sha256(token.encode()).hexdigest()
def configuration():
    base=os.getenv("CFA_WEB_APP_URL","").rstrip("/")
    host=os.getenv("CFA_SMTP_HOST","")
    sender=os.getenv("CFA_MAIL_FROM","")
    if not (base.startswith("https://") and host and sender):
        raise HTTPException(503,"Web email sign-in is not configured")
    return base,host,sender

def send_email(email,url,host,sender):
    msg=EmailMessage()
    msg["Subject"]="Sign in to RoleHint"
    msg["From"]=sender
    msg["To"]=email
    msg.set_content("Use this one-time sign-in link (valid for 15 minutes):\n"+url+"\nIf you did not request it, ignore this message.")
    port=int(os.getenv("CFA_SMTP_PORT","465"))
    user=os.getenv("CFA_SMTP_USER","")
    password=os.getenv("CFA_SMTP_PASSWORD","")
    if port==465:
        with smtplib.SMTP_SSL(host,port,timeout=10,context=ssl.create_default_context()) as client:
            if user:client.login(user,password)
            client.send_message(msg)
    else:
        with smtplib.SMTP(host,port,timeout=10) as client:
            client.starttls(context=ssl.create_default_context())
            if user:client.login(user,password)
            client.send_message(msg)

def init_routes(product):
    conn=product.conn
    init(conn)

    def require_user(request:Request):
        token=request.cookies.get(COOKIE,"")
        if len(token)<30:raise HTTPException(401,"Please sign in")
        row=conn.execute("SELECT user_id FROM web_sessions WHERE token_hash=? AND expires_at>?",
                         (token_hash(token),time.time())).fetchone()
        if not row:raise HTTPException(401,"Session expired")
        return row["user_id"]

    def check_origin(request:Request):
        origin=request.headers.get("origin")
        base=os.getenv("CFA_WEB_APP_URL","").rstrip("/")
        if not base or not origin or not hmac.compare_digest(origin,base):
            raise HTTPException(403,"Invalid request origin")


    @router.post("/telegram/begin")
    async def begin_telegram(request:Request):
        check_origin(request)
        token=os.getenv("TELEGRAM_BOT_TOKEN","")
        if not token:raise HTTPException(503,"Telegram login not configured")
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response=await client.get("https://api.telegram.org/bot"+token+"/getMe")
                response.raise_for_status()
                info=response.json()
            username=str((info.get("result") or {}).get("username") or "")
            if not info.get("ok") or not re.fullmatch(r"[A-Za-z0-9_]{5,32}",username):raise ValueError("Bot unavailable")
        except (httpx.HTTPError,ValueError):
            raise HTTPException(503,"Telegram sign-in temporarily unavailable")
        state=secrets.token_urlsafe(20)
        binding=secrets.token_urlsafe(32)
        now=time.time()
        conn.execute("DELETE FROM web_telegram_challenges WHERE expires_at<?",(now-3600,))
        conn.execute("INSERT INTO web_telegram_challenges(challenge_id,browser_hash,expires_at) VALUES(?,?,?)",
                     (state,token_hash(binding),now+600))
        conn.commit()
        response=ResponseJSON({"url":"https://t.me/"+username+"?start=web_"+state,
                               "message":"Open Telegram, then enter the code sent by the RoleHint bot."})
        response.set_cookie("rh_tg_challenge",binding,secure=True,httponly=True,samesite="lax",max_age=600,path="/web-api/")
        response.set_cookie("rh_tg_state",state,secure=True,httponly=True,samesite="lax",max_age=600,path="/web-api/")
        response.headers["Cache-Control"]="no-store"
        return response

    @router.post("/telegram/bot-issue")
    async def issue_telegram_code(request:Request,x_cfa_bot_secret:str|None=Header(default=None,alias="X-CFA-Bot-Secret")):
        expected=os.getenv("CFA_INTERNAL_BOT_SECRET","")
        if not expected or not x_cfa_bot_secret or not hmac.compare_digest(expected,x_cfa_bot_secret):
            raise HTTPException(401,"Unauthorized")
        data=await request.json()
        state=str(data.get("state") or "")
        user=data.get("telegram_user")
        if not re.fullmatch(r"[A-Za-z0-9_-]{20,64}",state) or not isinstance(user,dict) or not isinstance(user.get("id"),int):
            raise HTTPException(422,"Invalid challenge")
        now=time.time()
        row=conn.execute("SELECT challenge_id FROM web_telegram_challenges WHERE challenge_id=? AND expires_at>? AND user_id IS NULL AND consumed=0",(state,now)).fetchone()
        if not row:raise HTTPException(400,"Challenge expired or already used")
        uid=product.ensure_user(telegram_user=user)
        code=str(secrets.randbelow(90000000)+10000000)
        digest=token_hash(state+":"+code)
        cur=conn.execute("UPDATE web_telegram_challenges SET user_id=?,code_hash=? WHERE challenge_id=? AND user_id IS NULL AND expires_at>? AND consumed=0",(uid,digest,state,now))
        conn.commit()
        if cur.rowcount!=1:raise HTTPException(400,"Challenge already used")
        return {"code":code}

    @router.post("/telegram/complete")
    async def complete_telegram(request:Request):
        check_origin(request)
        state=request.cookies.get("rh_tg_state","")
        binding=request.cookies.get("rh_tg_challenge","")
        if not state or len(binding)<30:raise HTTPException(401,"Begin sign-in again")
        data=await request.json()
        code=str(data.get("code") or "")
        if not re.fullmatch(r"[0-9]{8}",code):raise HTTPException(422,"Enter the 8-digit Telegram code")
        now=time.time()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row=conn.execute("SELECT * FROM web_telegram_challenges WHERE challenge_id=? AND browser_hash=? AND expires_at>? AND consumed=0",
                             (state,token_hash(binding),now)).fetchone()
            if not row or not row["user_id"] or row["tries"]>=5:raise ValueError("Invalid or expired login")
            conn.execute("UPDATE web_telegram_challenges SET tries=tries+1 WHERE challenge_id=?",(state,))
            if not hmac.compare_digest(str(row["code_hash"] or ""),token_hash(state+":"+code)):
                conn.commit()
                raise HTTPException(401,"Incorrect or expired login code")
            conn.execute("UPDATE web_telegram_challenges SET consumed=1 WHERE challenge_id=?",(state,))
            session=secrets.token_urlsafe(48)
            conn.execute("INSERT INTO web_sessions VALUES(?,?,?,?)",(token_hash(session),row["user_id"],now+86400*14,now))
            conn.commit()
        except (sqlite3.Error,ValueError):
            conn.rollback()
            raise HTTPException(401,"Invalid or expired login")
        response=ResponseJSON({"ok":True})
        response.set_cookie(COOKIE,session,max_age=86400*14,secure=True,httponly=True,samesite="lax",path="/")
        response.delete_cookie("rh_tg_challenge",path="/web-api/")
        response.delete_cookie("rh_tg_state",path="/web-api/")
        response.headers["Cache-Control"]="no-store"
        return response

    @router.get("/auth-status")
    def auth_status():
        try:
            configuration()
            return {"email_login_available":True}
        except HTTPException:
            return {"email_login_available":False}

    @router.post("/login")
    async def request_link(request:Request):
        check_origin(request)
        base,host,sender=configuration()
        body=await request.json()
        email=str(body.get("email") or "").strip().lower()
        if len(email)>254 or not EMAIL_RE.fullmatch(email):raise HTTPException(422,"Enter a valid email")
        now=time.time()
        recent=conn.execute("SELECT COUNT(*) n FROM web_login_links WHERE email=? AND created_at>?",
                            (email,now-3600)).fetchone()["n"]
        if recent>=5:raise HTTPException(429,"Too many sign-in requests")
        token=secrets.token_urlsafe(36)
        digest=token_hash(token)
        conn.execute("INSERT INTO web_login_links VALUES(?,?,?,?,?)",(digest,email,now+900,None,now))
        conn.commit()
        try:send_email(email,base+"/web-api/callback?token="+token,host,sender)
        except Exception:
            conn.execute("DELETE FROM web_login_links WHERE token_hash=?",(digest,));conn.commit()
            raise HTTPException(503,"Email delivery unavailable")
        return {"ok":True,"message":"Check your inbox for a one-time sign-in link."}

    @router.get("/callback")
    def complete_login(token:str=""):
        configuration()
        now=time.time()
        digest=token_hash(token)
        # Consume once and create account in a single SQLite transaction.
        try:
            conn.execute("BEGIN IMMEDIATE")
            row=conn.execute("SELECT email FROM web_login_links WHERE token_hash=? AND consumed_at IS NULL AND expires_at>?",(digest,now)).fetchone()
            if not row:raise ValueError("Invalid or expired link")
            email=row["email"]
            conn.execute("UPDATE web_login_links SET consumed_at=? WHERE token_hash=? AND consumed_at IS NULL",(now,digest))
            account=conn.execute("SELECT user_id FROM web_accounts WHERE email=?",(email,)).fetchone()
            if account:uid=account["user_id"]
            else:
                uid="web_"+uuid.uuid4().hex
                conn.execute("INSERT INTO users(id,telegram_user_id,first_name,username,created_at,last_seen) VALUES(?,NULL,NULL,NULL,?,?)",(uid,now,now))
                conn.execute("INSERT INTO web_accounts(email,user_id,created_at) VALUES(?,?,?)",(email,uid,now))
            session=secrets.token_urlsafe(48)
            conn.execute("INSERT INTO web_sessions VALUES(?,?,?,?)",(token_hash(session),uid,now+86400*14,now))
            conn.commit()
        except (sqlite3.Error,ValueError):
            conn.rollback()
            raise HTTPException(400,"Invalid or expired sign-in link")
        response=RedirectResponse("/webapp/",status_code=303)
        response.set_cookie(COOKIE,session,max_age=86400*14,secure=True,httponly=True,samesite="lax",path="/")
        response.headers["Cache-Control"]="no-store"
        return response

    @router.get("/me")
    def me(request:Request):
        uid=require_user(request)
        prefs=product.preferences(uid)
        profiles=product.search_profiles(uid)
        jobs=product.jobs(uid)
        return {"authenticated":True,"preferences":prefs,"search_profiles":profiles,
                "jobs":jobs[:10],"free_limit":10,"free_used":min(10,len(jobs))}

    def delete_cv_evidence_rows(uid):
        # FTS5 stores indexed plaintext separately from the relational record.
        conn.execute("""DELETE FROM user_evidence_fts WHERE user_id=? AND evidence_id IN (
            SELECT evidence_id FROM user_evidence
            WHERE user_id=? AND source_type='cv' AND source_ref='candidate-cv'
        )""",(uid,uid))
        conn.execute("DELETE FROM user_evidence WHERE user_id=? AND source_type='cv' AND source_ref='candidate-cv'",(uid,))

    def replace_cv_evidence(uid,evidence):
        # Imported text remains self-reported; never silently upgrade it to verified.
        delete_cv_evidence_rows(uid)
        for item in evidence[:40]:
            item["status"]="needs-review"
            item["direct"]=False
            item["boundary"]="Imported self-reported CV statement. User confirmation is not external verification."
            product.upsert_user_evidence(uid,item)
        conn.execute("DELETE FROM web_cv_confirmations WHERE user_id=?",(uid,))
        conn.commit()

    @router.get("/cv")
    def read_cv(request:Request):
        uid=require_user(request)
        row=conn.execute("SELECT source_name,text_content,evidence_json,updated_at FROM web_candidate_profiles WHERE user_id=?",(uid,)).fetchone()
        if not row:return {"uploaded":False}
        confirmation=conn.execute("SELECT cv_hash FROM web_cv_confirmations WHERE user_id=?",(uid,)).fetchone()
        confirmed=bool(confirmation and hmac.compare_digest(confirmation["cv_hash"],token_hash(row["text_content"])))
        return {"uploaded":True,"file_name":row["source_name"],"text":row["text_content"],
                "evidence":json.loads(row["evidence_json"]),"confirmed":confirmed,"updated_at":row["updated_at"]}

    @router.post("/anonymous/cv-analysis")
    async def anonymous_cv_analysis(request:Request,file:UploadFile=File(...)):
        """First useful CV feedback without account creation or persistent storage.

        Only self-reported text is analyzed; no candidate profile or session is created.
        """
        check_origin(request)
        name=Path(file.filename or "").name[:120]
        ext=Path(name).suffix.lower()
        if ext not in {".pdf",".docx",".txt"}:
            raise HTTPException(415,"Supported files: PDF, DOCX, TXT")
        raw=await file.read(8*1024*1024+1)
        await file.close()
        if len(raw)>8*1024*1024:raise HTTPException(413,"Maximum file size is 8 MB")
        if not raw:raise HTTPException(422,"Empty file")
        if ext==".pdf" and not raw.startswith(b"%PDF-"):raise HTTPException(422,"Invalid PDF file")
        if ext==".docx" and not raw.startswith(b"PK"):raise HTTPException(422,"Invalid DOCX file")
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/("cv"+ext)
            path.write_bytes(raw)
            try:content=read_text(path).strip()
            except Exception:raise HTTPException(422,"Could not read this CV. Try a text-based PDF, DOCX or TXT.")
        if len(content)<50:raise HTTPException(422,"Too little selectable text. Scanned CVs need OCR or pasted text.")
        if len(content)>100000:raise HTTPException(413,"CV text too long")
        evidence=atomize_text(content,"anonymous-cv","cv")
        # Deterministic, source-grounded suggestions, not AI-verified qualifications.
        metrics=re.findall(r"(?<!\w)(?:\d+(?:[.,]\d+)?\s?%|[$€£]\s?\d[\d,.]*|\d[\d,.]*\s?(?:users|customers|clients|revenue|projects|teams))",content,re.I)
        insights=[]
        if not metrics:insights.append({"kind":"missing_metric","message":"Add measurable outcomes to your strongest achievements where you have supporting evidence."})
        else:insights.append({"kind":"metric_candidates","message":"Review quantified claims and confirm their context and accuracy before using them in applications.","examples":metrics[:5]})
        if len(content.split())<180:insights.append({"kind":"limited_detail","message":"Your CV may lack enough detail for evidence-based role matching. Add responsibilities and concrete results."})
        insights.append({"kind":"verification","message":"Imported CV statements are self-reported, not independently verified. Review them before tailoring an application."})
        role_titles=["Product Manager","Product Designer","Software Engineer","Data Analyst","Project Manager","UX Researcher","Marketing Manager","Customer Success Manager"]
        suggested_roles=[title for title in role_titles if title.lower() in content[:5000].lower()][:4]
        response=ResponseJSON({"file_name":name,"evidence":evidence,"insights":insights,"suggested_roles":suggested_roles,
                               "verification_level":"self-reported","saved":False,
                               "next_step":"Sign in only when you want to save and resume your analysis."})
        response.headers["Cache-Control"]="no-store"
        return response

    @router.post("/cv")
    async def upload_cv(request:Request,file:UploadFile=File(...)):
        check_origin(request);uid=require_user(request)
        name=Path(file.filename or "").name[:120]
        ext=Path(name).suffix.lower()
        if ext not in {".pdf",".docx",".txt"}:raise HTTPException(415,"Supported files: PDF, DOCX, TXT")
        raw=await file.read(8*1024*1024+1)
        await file.close()
        if len(raw)>8*1024*1024:raise HTTPException(413,"Maximum file size is 8 MB")
        if not raw:raise HTTPException(422,"Empty file")
        if ext==".pdf" and not raw.startswith(b"%PDF-"):raise HTTPException(422,"Invalid PDF file")
        if ext==".docx" and not raw.startswith(b"PK"):raise HTTPException(422,"Invalid DOCX file")
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/("cv"+ext)
            path.write_bytes(raw)
            try:content=read_text(path).strip()
            except Exception:raise HTTPException(422,"Could not read this CV. Try a text-based PDF, DOCX or TXT.")
        if len(content)<50:raise HTTPException(422,"Too little selectable text. Scanned CVs need OCR or pasted text.")
        if len(content)>100000:raise HTTPException(413,"CV text too long")
        evidence=atomize_text(content,"candidate-cv","cv")
        # Imported text is strictly self-reported, not externally verified.
        now=time.time()
        conn.execute("""INSERT INTO web_candidate_profiles VALUES(?,?,?,?,?)
          ON CONFLICT(user_id) DO UPDATE SET source_name=excluded.source_name,
          text_content=excluded.text_content,evidence_json=excluded.evidence_json,updated_at=excluded.updated_at""",
          (uid,name,content,json.dumps(evidence),now))
        conn.commit()
        replace_cv_evidence(uid,evidence)
        return {"uploaded":True,"file_name":name,"text":content,"evidence":evidence,"confirmed":False,"updated_at":now}

    @router.put("/cv")
    async def correct_cv(request:Request):
        check_origin(request);uid=require_user(request)
        body=await request.json()
        content=str(body.get("text") or "").strip()
        if not 50<=len(content)<=100000:raise HTTPException(422,"CV text must be 50–100,000 characters")
        existing=conn.execute("SELECT source_name FROM web_candidate_profiles WHERE user_id=?",(uid,)).fetchone()
        if not existing:raise HTTPException(404,"Upload a CV first")
        evidence=atomize_text(content,"candidate-cv","cv")
        now=time.time()
        conn.execute("UPDATE web_candidate_profiles SET text_content=?,evidence_json=?,updated_at=? WHERE user_id=?",
                     (content,json.dumps(evidence),now,uid));conn.commit()
        replace_cv_evidence(uid,evidence)
        return {"uploaded":True,"file_name":existing["source_name"],"text":content,"evidence":evidence,"confirmed":False,"updated_at":now}

    @router.post("/cv/confirm")
    def confirm_cv(request:Request):
        check_origin(request);uid=require_user(request)
        row=conn.execute("SELECT text_content FROM web_candidate_profiles WHERE user_id=?",(uid,)).fetchone()
        if not row:raise HTTPException(404,"Upload your CV first")
        digest=token_hash(row["text_content"])
        conn.execute("INSERT INTO web_cv_confirmations VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET cv_hash=excluded.cv_hash,confirmed_at=excluded.confirmed_at",(uid,digest,time.time()))
        conn.commit()
        return {"confirmed":True,"verification_level":"self-reported"}

    @router.delete("/cv")
    def delete_cv(request:Request):
        check_origin(request);uid=require_user(request)
        conn.execute("DELETE FROM web_candidate_profiles WHERE user_id=?",(uid,))
        delete_cv_evidence_rows(uid)
        conn.execute("DELETE FROM web_cv_confirmations WHERE user_id=?",(uid,))
        conn.commit()
        return {"deleted":True}

    @router.put("/preferences")
    async def save_preferences(request:Request):
        check_origin(request);uid=require_user(request)
        data=await request.json()
        allowed={"remote_only","allow_relocation","salary_floor_annual","home_region","allowed_regions"}
        patch={k:v for k,v in data.items() if k in allowed}
        if not isinstance(patch.get("allowed_regions",[]),list):raise HTTPException(422,"Invalid regions")
        return product.save_preferences(uid,patch)

    @router.post("/search")
    async def save_search(request:Request):
        check_origin(request);uid=require_user(request)
        data=await request.json()
        role=str(data.get("query","")).strip()
        if not 3<=len(role)<=120:raise HTTPException(422,"Enter a target role")
        profiles=product.search_profiles(uid)
        if len(profiles)>=3:raise HTTPException(409,"Maximum three active searches")
        return product.upsert_search_profile(uid,{"query":role,"countries":[],"remote_only":bool(product.preferences(uid).get("remote_only")),"enabled":True,"interval_minutes":360})

    @router.post("/logout")
    def logout(request:Request):
        check_origin(request)
        token=request.cookies.get(COOKIE)
        if token:
            conn.execute("DELETE FROM web_sessions WHERE token_hash=?",(token_hash(token),));conn.commit()
        response=RedirectResponse("/webapp/",status_code=303)
        response.delete_cookie(COOKIE,path="/")
        return response

    from .web_release import bind_web_release
    bind_web_release(router,product,require_user,check_origin)
    return router
