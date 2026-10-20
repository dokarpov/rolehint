from __future__ import annotations
import sqlite3, json, time, uuid, os
from pathlib import Path
from .application_analytics import migrate as migrate_application_analytics, record_event as record_application_event, timeline as application_timeline, funnel as application_funnel

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(
 id TEXT PRIMARY KEY,
 telegram_user_id TEXT UNIQUE,
 first_name TEXT,
 username TEXT,
 created_at REAL NOT NULL,
 last_seen REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS user_jobs(
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 job_id TEXT NOT NULL,
 company TEXT NOT NULL,
 title TEXT NOT NULL,
 location TEXT,
 compensation TEXT,
 decision TEXT NOT NULL,
 next_action TEXT,
 blocker TEXT,
 evidence_verified INTEGER NOT NULL DEFAULT 0,
 evidence_review INTEGER NOT NULL DEFAULT 0,
 evidence_gaps INTEGER NOT NULL DEFAULT 0,
 effort_minutes INTEGER,
 source_url TEXT,
 payload_json TEXT NOT NULL DEFAULT '{}',
 updated_at REAL NOT NULL,
 PRIMARY KEY(user_id,job_id)
);
CREATE TABLE IF NOT EXISTS user_job_notes(
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 job_id TEXT NOT NULL,
 body TEXT NOT NULL DEFAULT '',
 updated_at REAL NOT NULL,
 PRIMARY KEY(user_id,job_id)
);
CREATE TABLE IF NOT EXISTS user_actions(
 id TEXT PRIMARY KEY,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 job_id TEXT,
 action_type TEXT NOT NULL,
 title TEXT NOT NULL,
 description TEXT,
 priority INTEGER NOT NULL DEFAULT 50,
 state TEXT NOT NULL DEFAULT 'open',
 payload_json TEXT NOT NULL DEFAULT '{}',
 created_at REAL NOT NULL,
 updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS email_events(
 id TEXT PRIMARY KEY,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 message_id TEXT NOT NULL,
 job_id TEXT,
 event_type TEXT NOT NULL,
 subject TEXT,
 sender TEXT,
 occurred_at TEXT,
 payload_json TEXT NOT NULL DEFAULT '{}',
 created_at REAL NOT NULL,
 UNIQUE(user_id,message_id)
);
CREATE TABLE IF NOT EXISTS entitlements(
 id TEXT PRIMARY KEY,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 sku TEXT NOT NULL,
 status TEXT NOT NULL,
 active_from REAL NOT NULL,
 active_until REAL,
 source TEXT NOT NULL,
 external_charge_id TEXT UNIQUE,
 payload_json TEXT NOT NULL DEFAULT '{}',
 created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS connector_tokens(
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 provider TEXT NOT NULL,
 encrypted_json TEXT NOT NULL,
 scopes TEXT,
 updated_at REAL NOT NULL,
 PRIMARY KEY(user_id,provider)
);
CREATE TABLE IF NOT EXISTS oauth_sessions(
 state TEXT PRIMARY KEY,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 provider TEXT NOT NULL,
 redirect_uri TEXT,
 created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS gmail_watches(
 user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 email_address TEXT NOT NULL,
 last_history_id TEXT,
 expiration_ms INTEGER,
 last_notification_at REAL,
 last_fallback_sync REAL,
 updated_at REAL NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_gmail_watches_email ON gmail_watches(email_address);

CREATE TABLE IF NOT EXISTS gmail_push_queue(
 id TEXT PRIMARY KEY,
 pubsub_message_id TEXT UNIQUE,
 email_address TEXT NOT NULL,
 history_id TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'pending',
 attempts INTEGER NOT NULL DEFAULT 0,
 last_error TEXT,
 received_at REAL NOT NULL,
 updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS notification_outbox(
 id TEXT PRIMARY KEY,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 kind TEXT NOT NULL,
 text TEXT NOT NULL,
 job_id TEXT,
 dedupe_key TEXT UNIQUE,
 state TEXT NOT NULL DEFAULT 'pending',
 attempts INTEGER NOT NULL DEFAULT 0,
 next_attempt REAL NOT NULL,
 last_error TEXT,
 created_at REAL NOT NULL,
 sent_at REAL
);





CREATE TABLE IF NOT EXISTS user_source_sync(
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 provider TEXT NOT NULL,
 last_sync REAL,
 status TEXT NOT NULL DEFAULT 'pending',
 last_error TEXT,
 item_count INTEGER NOT NULL DEFAULT 0,
 updated_at REAL NOT NULL,
 PRIMARY KEY(user_id,provider)
);


CREATE TABLE IF NOT EXISTS user_onboarding(
 user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 version INTEGER NOT NULL DEFAULT 2,
 state_json TEXT NOT NULL DEFAULT '{}',
 completed_at REAL,
 updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS user_funnel_policy(
 user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 policy_json TEXT NOT NULL DEFAULT '{}',
 updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS application_submissions(
 id TEXT PRIMARY KEY,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 job_id TEXT NOT NULL,
 application_key TEXT NOT NULL,
 base_key TEXT NOT NULL,
 requisition_id TEXT,
 role_fingerprint TEXT,
 tier TEXT NOT NULL,
 submitted_at REAL NOT NULL,
 cv_version TEXT,
 evidence_version TEXT,
 response_state TEXT NOT NULL DEFAULT 'submitted',
 source TEXT,
 estimated_minutes INTEGER,
 is_unique INTEGER NOT NULL DEFAULT 1,
 payload_json TEXT NOT NULL DEFAULT '{}',
 UNIQUE(user_id,application_key)
);
CREATE INDEX IF NOT EXISTS idx_app_submissions_user_date ON application_submissions(user_id,submitted_at);
CREATE INDEX IF NOT EXISTS idx_app_submissions_job ON application_submissions(user_id,job_id);

CREATE TABLE IF NOT EXISTS vacancy_fetch_queue(
 id TEXT PRIMARY KEY,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 url TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'pending',
 attempts INTEGER NOT NULL DEFAULT 0,
 next_attempt REAL NOT NULL,
 last_error TEXT,
 created_at REAL NOT NULL,
 updated_at REAL NOT NULL,
 UNIQUE(user_id,url)
);
CREATE INDEX IF NOT EXISTS idx_vacancy_fetch_due ON vacancy_fetch_queue(state,next_attempt);

CREATE TABLE IF NOT EXISTS user_preferences(
 user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 remote_only INTEGER NOT NULL DEFAULT 0,
 allow_relocation INTEGER NOT NULL DEFAULT 1,
 salary_floor_annual REAL NOT NULL DEFAULT 0,
 home_region TEXT,
 allowed_regions_json TEXT NOT NULL DEFAULT '[]',
 updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS user_search_profiles(
 id TEXT PRIMARY KEY,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 query TEXT NOT NULL,
 countries_json TEXT NOT NULL DEFAULT '[]',
 remote_only INTEGER NOT NULL DEFAULT 0,
 sources_json TEXT NOT NULL DEFAULT '[]',
 interval_minutes INTEGER NOT NULL DEFAULT 360,
 enabled INTEGER NOT NULL DEFAULT 1,
 last_run REAL,
 next_run REAL,
 created_at REAL NOT NULL,
 updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_user_search_due ON user_search_profiles(enabled,next_run);

CREATE TABLE IF NOT EXISTS user_evidence(
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 evidence_id TEXT NOT NULL,
 source_type TEXT NOT NULL,
 source_ref TEXT NOT NULL,
 title TEXT NOT NULL,
 claim TEXT NOT NULL,
 evidence TEXT NOT NULL,
 tags_json TEXT NOT NULL DEFAULT '[]',
 status TEXT NOT NULL DEFAULT 'needs-review',
 direct INTEGER NOT NULL DEFAULT 0,
 visibility TEXT NOT NULL DEFAULT 'private',
 ownership TEXT,
 metric TEXT,
 boundary TEXT,
 updated_at REAL NOT NULL,
 PRIMARY KEY(user_id,evidence_id)
);
CREATE VIRTUAL TABLE IF NOT EXISTS user_evidence_fts USING fts5(
 user_id UNINDEXED,
 evidence_id UNINDEXED,
 title,
 claim,
 evidence,
 tags
);

CREATE TABLE IF NOT EXISTS user_job_requirements(
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 job_id TEXT NOT NULL,
 requirement_id TEXT NOT NULL,
 label TEXT NOT NULL,
 source_text TEXT,
 must_have INTEGER NOT NULL DEFAULT 1,
 extractor TEXT,
 updated_at REAL NOT NULL,
 PRIMARY KEY(user_id,job_id,requirement_id)
);

CREATE TABLE IF NOT EXISTS pack_proposals(
 id TEXT PRIMARY KEY,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 job_id TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'proposed',
 proposal_json TEXT NOT NULL DEFAULT '{}',
 created_at REAL NOT NULL,
 updated_at REAL NOT NULL,
 UNIQUE(user_id,job_id)
);

CREATE TABLE IF NOT EXISTS application_packs(
 id TEXT PRIMARY KEY,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 job_id TEXT NOT NULL,
 version INTEGER NOT NULL DEFAULT 1,
 status TEXT NOT NULL DEFAULT 'draft',
 data_json TEXT NOT NULL DEFAULT '{}',
 created_at REAL NOT NULL,
 updated_at REAL NOT NULL,
 UNIQUE(user_id,job_id)
);

CREATE TABLE IF NOT EXISTS export_downloads(
 token TEXT PRIMARY KEY,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 job_id TEXT NOT NULL,
 format TEXT NOT NULL,
 content TEXT NOT NULL,
 file_name TEXT NOT NULL,
 expires_at REAL NOT NULL,
 created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS local_settings(
 key TEXT PRIMARY KEY,
 value_json TEXT NOT NULL,
 updated_at REAL NOT NULL
);
"""

DEFAULT_JOBS = [
 {"job_id":"alpha","company":"AlphaLife Sciences","title":"AI Product Manager — EU",
  "location":"Remote Europe","compensation":"$130k–170k","decision":"APPLY",
  "next_action":"Open application pack","blocker":None,"evidence_verified":3,"evidence_review":0,"evidence_gaps":1,"effort_minutes":30},
 {"job_id":"flodesk","company":"Flodesk","title":"Sr. Product Manager — AI",
  "location":"Spain eligibility unresolved","compensation":"$150k–200k","decision":"VERIFY FIRST",
  "next_action":"Verify Spain eligibility","blocker":"Can this role be employed from Spain / attached to the Barcelona hub?",
  "evidence_verified":7,"evidence_review":1,"evidence_gaps":0,"effort_minutes":20},
 {"job_id":"scoreplay","company":"ScorePlay","title":"Senior Product Manager — Vault",
  "location":"Western Europe remote","compensation":"Unknown","decision":"VERIFY FIRST",
  "next_action":"Verify compensation","blocker":"Compensation is the next decision.",
  "evidence_verified":3,"evidence_review":0,"evidence_gaps":1,"effort_minutes":25},
]

class ProductStore:
    def __init__(self,path):
        self.conn=sqlite3.connect(str(path),check_same_thread=False)
        self.conn.row_factory=sqlite3.Row
        self.conn.executescript(SCHEMA)
        migrate_application_analytics(self.conn)

    def record_application_event(self,user_id,job_id,event_key,stage,source,confirmed=False,occurred_at=None):
        return record_application_event(self.conn,user_id,job_id,event_key,stage,source,confirmed,occurred_at)

    def application_timeline(self,user_id,job_id):
        return application_timeline(self.conn,user_id,job_id)

    def application_funnel(self,user_id):
        return application_funnel(self.conn,user_id)

    def now(self): return time.time()
    def uid(self,prefix): return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def ensure_user(self, telegram_user:dict|None=None, local:bool=False):
        now=self.now()
        if local:
            uid="user_local"
            self.conn.execute("""INSERT INTO users VALUES(?,?,?,?,?,?)
              ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen""",
              (uid,None,"Local user",None,now,now))
        else:
            tg=str((telegram_user or {}).get("id",""))
            if not tg: raise ValueError("Telegram user id required")
            row=self.conn.execute("SELECT id FROM users WHERE telegram_user_id=?",(tg,)).fetchone()
            uid=row["id"] if row else self.uid("user")
            self.conn.execute("""INSERT INTO users(id,telegram_user_id,first_name,username,created_at,last_seen)
              VALUES(?,?,?,?,?,?)
              ON CONFLICT(telegram_user_id) DO UPDATE SET first_name=excluded.first_name,
              username=excluded.username,last_seen=excluded.last_seen""",
              (uid,tg,(telegram_user or {}).get("first_name"),(telegram_user or {}).get("username"),now,now))
        self.conn.commit()
        if os.getenv("CFA_SEED_DEMO","0")=="1":
            self.seed_user(uid)
        return uid

    def user_by_telegram_id(self,tg_id):
        r=self.conn.execute("SELECT * FROM users WHERE telegram_user_id=?",(str(tg_id),)).fetchone()
        return dict(r) if r else None

    def seed_user(self,user_id):
        n=self.conn.execute("SELECT COUNT(*) n FROM user_jobs WHERE user_id=?",(user_id,)).fetchone()["n"]
        if n: return
        now=self.now()
        for j in DEFAULT_JOBS:
            self.conn.execute("""INSERT INTO user_jobs(
             user_id,job_id,company,title,location,compensation,decision,next_action,blocker,
             evidence_verified,evidence_review,evidence_gaps,effort_minutes,source_url,payload_json,updated_at
             ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
             (user_id,j["job_id"],j["company"],j["title"],j.get("location"),j.get("compensation"),
              j["decision"],j.get("next_action"),j.get("blocker"),j.get("evidence_verified",0),
              j.get("evidence_review",0),j.get("evidence_gaps",0),j.get("effort_minutes"),
              j.get("source_url"),json.dumps(j),now))
        actions=[
          ("flodesk","verify","Verify Flodesk can hire from Spain","Strongest AI-role proof match; one direct question can resolve it.",100),
          ("alpha","apply","Apply to AlphaLife Sciences","No hard blocker; proof pack is reusable.",90),
          (None,"evidence_gap","Review one recurring evidence gap","Production RAG repeats; current evidence is adjacent, not direct.",80),
        ]
        for job_id,typ,title,desc,priority in actions:
            self.conn.execute("INSERT INTO user_actions VALUES(?,?,?,?,?,?,?,?,?,?,?)",
              (self.uid("act"),user_id,job_id,typ,title,desc,priority,"open","{}",now,now))
        self.conn.commit()

    def jobs(self,user_id):
        rows=self.conn.execute("""SELECT j.*,COALESCE(n.body,'') note
            FROM user_jobs j LEFT JOIN user_job_notes n ON n.user_id=j.user_id AND n.job_id=j.job_id
            WHERE j.user_id=? ORDER BY
              CASE j.decision WHEN 'APPLY' THEN 0 WHEN 'VERIFY FIRST' THEN 1 ELSE 2 END,
              j.updated_at DESC""",(user_id,)).fetchall()
        return [self._job(r) for r in rows]

    def job(self,user_id,job_id):
        r=self.conn.execute("""SELECT j.*,COALESCE(n.body,'') note
          FROM user_jobs j LEFT JOIN user_job_notes n ON n.user_id=j.user_id AND n.job_id=j.job_id
          WHERE j.user_id=? AND j.job_id=?""",(user_id,job_id)).fetchone()
        return self._job(r) if r else None

    def save_note(self,user_id,job_id,body):
        now=self.now()
        self.conn.execute("""INSERT INTO user_job_notes VALUES(?,?,?,?)
          ON CONFLICT(user_id,job_id) DO UPDATE SET body=excluded.body,updated_at=excluded.updated_at""",
          (user_id,job_id,body,now))
        self.conn.commit()
        return {"job_id":job_id,"body":body,"updated_at":now}

    def open_actions(self,user_id,limit=5):
        rows=self.conn.execute("""SELECT * FROM user_actions WHERE user_id=? AND state='open'
          ORDER BY priority DESC,created_at LIMIT ?""",(user_id,limit)).fetchall()
        return [dict(r) | {"payload":json.loads(r["payload_json"] or "{}")} for r in rows]

    def resolve_action(self,user_id,job_id,action_type,state="done"):
        now=self.now()
        self.conn.execute("""UPDATE user_actions SET state=?,updated_at=?
          WHERE user_id=? AND COALESCE(job_id,'')=COALESCE(?,'') AND action_type=? AND state='open'""",
          (state,now,user_id,job_id,action_type))
        if action_type=="verify" and job_id:
            self.conn.execute("""UPDATE user_jobs SET decision='APPLY',blocker=NULL,
              next_action='Open application pack',updated_at=? WHERE user_id=? AND job_id=?""",(now,user_id,job_id))
        self.conn.commit()
        return self.job(user_id,job_id) if job_id else {"ok":True}

    def add_email_event(self,user_id,event,job_id=None):
        now=self.now()
        eid=self.uid("email")
        try:
            self.conn.execute("""INSERT INTO email_events VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
              (eid,user_id,event["message_id"],job_id,event["event_type"],event.get("subject"),
               event.get("from"),event.get("date"),json.dumps(event),now))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def email_timeline(self,user_id,job_id=None,limit=30):
        if job_id:
            rows=self.conn.execute("""SELECT * FROM email_events WHERE user_id=? AND job_id=?
              ORDER BY created_at DESC LIMIT ?""",(user_id,job_id,limit)).fetchall()
        else:
            rows=self.conn.execute("""SELECT * FROM email_events WHERE user_id=?
              ORDER BY created_at DESC LIMIT ?""",(user_id,limit)).fetchall()
        return [dict(r)|{"payload":json.loads(r["payload_json"] or "{}")} for r in rows]

    def match_event_to_job(self,user_id,event):
        blob=((event.get("subject") or "")+" "+(event.get("from") or "")+" "+(event.get("body_text") or "")).lower()
        best=None;best_score=0
        for j in self.jobs(user_id):
            company_tokens=[x for x in re_words(j["company"]) if len(x)>3]
            title_tokens=[x for x in re_words(j["title"]) if len(x)>4]
            score=sum(3 for t in company_tokens if t in blob)+sum(1 for t in title_tokens if t in blob)
            if score>best_score:
                best_score=score;best=j["job_id"]
        return best if best_score>=3 else None

    def grant_entitlement(self,user_id,sku,source,external_charge_id,days,payload=None):
        now=self.now();until=now+days*86400
        existing=self.conn.execute("SELECT id FROM entitlements WHERE external_charge_id=?",(external_charge_id,)).fetchone()
        if existing: return self.entitlement(user_id)
        self.conn.execute("INSERT INTO entitlements VALUES(?,?,?,?,?,?,?,?,?,?)",
          (self.uid("ent"),user_id,sku,"active",now,until,source,external_charge_id,json.dumps(payload or {}),now))
        self.conn.commit()
        return self.entitlement(user_id)

    def entitlement(self,user_id):
        now=self.now()
        r=self.conn.execute("""SELECT * FROM entitlements WHERE user_id=? AND status='active'
          AND (active_until IS NULL OR active_until>?) ORDER BY active_until DESC LIMIT 1""",(user_id,now)).fetchone()
        return dict(r) if r else None

    def save_connector_token(self,user_id,provider,encrypted_json,scopes=""):
        now=self.now()
        self.conn.execute("""INSERT INTO connector_tokens VALUES(?,?,?,?,?)
          ON CONFLICT(user_id,provider) DO UPDATE SET encrypted_json=excluded.encrypted_json,
          scopes=excluded.scopes,updated_at=excluded.updated_at""",(user_id,provider,encrypted_json,scopes,now))
        self.conn.commit()

    def connector_token(self,user_id,provider):
        r=self.conn.execute("SELECT * FROM connector_tokens WHERE user_id=? AND provider=?",(user_id,provider)).fetchone()
        return dict(r) if r else None

    def oauth_session(self,state,user_id=None,provider=None,redirect_uri=None,create=False):
        if create:
            self.conn.execute("INSERT INTO oauth_sessions VALUES(?,?,?,?,?)",(state,user_id,provider,redirect_uri,self.now()))
            self.conn.commit();return {"state":state}
        r=self.conn.execute("SELECT * FROM oauth_sessions WHERE state=?",(state,)).fetchone()
        return dict(r) if r else None

    def delete_oauth_session(self,state):
        self.conn.execute("DELETE FROM oauth_sessions WHERE state=?",(state,));self.conn.commit()

    def setting(self,key,default=None):
        r=self.conn.execute("SELECT value_json FROM local_settings WHERE key=?",(key,)).fetchone()
        return json.loads(r["value_json"]) if r else default

    def set_setting(self,key,value):
        now=self.now()
        self.conn.execute("""INSERT INTO local_settings VALUES(?,?,?)
          ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,updated_at=excluded.updated_at""",
          (key,json.dumps(value),now));self.conn.commit()


    def user_by_id(self,user_id):
        r=self.conn.execute("SELECT * FROM users WHERE id=?",(user_id,)).fetchone()
        return dict(r) if r else None



    def dashboard_metrics(self,user_id):
        u=self.conn.execute("SELECT created_at FROM users WHERE id=?",(user_id,)).fetchone()
        jobs=self.conn.execute("SELECT COUNT(*) n FROM user_jobs WHERE user_id=?",(user_id,)).fetchone()["n"]
        applications=self.conn.execute("SELECT COUNT(*) n FROM application_submissions WHERE user_id=? AND is_unique=1",(user_id,)).fetchone()["n"]
        rejected=self.conn.execute("SELECT COUNT(*) n FROM application_submissions WHERE user_id=? AND response_state='rejected'",(user_id,)).fetchone()["n"]
        strong=self.conn.execute("""SELECT COUNT(*) n FROM application_submissions WHERE user_id=? AND response_state IN ('recruiter_or_interview','offer_candidate','offer_confirmed')""",(user_id,)).fetchone()["n"]
        days=max(0,int((self.now()-float(u["created_at"]))/86400)) if u else 0
        rate=round(strong/applications*100,1) if applications else None
        evidence_total=self.conn.execute("SELECT COUNT(*) n FROM user_evidence WHERE user_id=?",(user_id,)).fetchone()["n"]
        evidence_verified=self.conn.execute("SELECT COUNT(*) n FROM user_evidence WHERE user_id=? AND status='verified'",(user_id,)).fetchone()["n"]
        return {"search_days":days,"signal_rate":rate,"efficiency":None,"tracked_roles":jobs,"applications":applications,
                "weekly_applications":self.weekly_submission_count(user_id),"rejection_signals":rejected,"strong_signals":strong,
                "evidence_total":evidence_total,"evidence_verified":evidence_verified}

    def search_target_label(self,user_id):
        rows=self.conn.execute("SELECT query,remote_only FROM user_search_profiles WHERE user_id=? AND enabled=1 ORDER BY created_at LIMIT 3",(user_id,)).fetchall()
        prefs=self.preferences(user_id)
        if rows:
            q=" / ".join(r["query"] for r in rows)
        else:q="Search profile not configured"
        bits=[q]
        if prefs.get("remote_only"):bits.append("remote only")
        if prefs.get("salary_floor_annual"):bits.append(f"salary floor {int(prefs['salary_floor_annual']):,}")
        return " · ".join(bits)



    # ---- Autopilot/source state ----
    def active_users(self,seen_within_days=30):
        cutoff=self.now()-seen_within_days*86400
        rows=self.conn.execute("SELECT * FROM users WHERE last_seen>=? ORDER BY last_seen DESC",(cutoff,)).fetchall()
        return [dict(r) for r in rows]

    def connector_connected(self,user_id,provider):
        return self.conn.execute("SELECT 1 FROM connector_tokens WHERE user_id=? AND provider=?",(user_id,provider)).fetchone() is not None

    def source_sync_state(self,user_id,provider):
        r=self.conn.execute("SELECT * FROM user_source_sync WHERE user_id=? AND provider=?",(user_id,provider)).fetchone()
        return dict(r) if r else {"user_id":user_id,"provider":provider,"last_sync":None,"status":"never","last_error":None,"item_count":0}

    def mark_source_sync(self,user_id,provider,status,item_count=0,error=None):
        now=self.now();prev=self.source_sync_state(user_id,provider);last_sync=now if status=="ok" else prev.get("last_sync")
        self.conn.execute("""INSERT INTO user_source_sync VALUES(?,?,?,?,?,?,?)
          ON CONFLICT(user_id,provider) DO UPDATE SET last_sync=excluded.last_sync,status=excluded.status,
          last_error=excluded.last_error,item_count=excluded.item_count,updated_at=excluded.updated_at""",
          (user_id,provider,last_sync,status,str(error or "")[:500] or None,int(item_count or 0),now))
        self.conn.commit();return self.source_sync_state(user_id,provider)

    def source_sync_due(self,user_id,provider,age_seconds=43200):
        st=self.source_sync_state(user_id,provider)
        return not st.get("last_sync") or float(st["last_sync"])<=self.now()-age_seconds

    def connector_summary(self,user_id):
        return {"google":self.connector_connected(user_id,"google"),"github":self.connector_connected(user_id,"github"),
                "google_sync":self.source_sync_state(user_id,"google"),"github_sync":self.source_sync_state(user_id,"github")}

    def search_profiles(self,user_id):
        rows=self.conn.execute("SELECT * FROM user_search_profiles WHERE user_id=? AND enabled=1 ORDER BY created_at",(user_id,)).fetchall()
        return [self._search_profile(r) for r in rows]

    def disable_auto_search_profiles(self,user_id,keep_ids):
        keep=set(keep_ids or [])
        rows=self.conn.execute("SELECT id FROM user_search_profiles WHERE user_id=? AND id LIKE 'auto_%'",(user_id,)).fetchall()
        for r in rows:
            if r["id"] not in keep:self.conn.execute("UPDATE user_search_profiles SET enabled=0,updated_at=? WHERE user_id=? AND id=?",(self.now(),user_id,r["id"]))
        self.conn.commit()

    def outcome_weighted_job_titles(self,user_id):
        rows=self.conn.execute("""SELECT j.title,j.company,
          SUM(CASE WHEN e.event_type IN ('recruiter_or_interview','offer_candidate','offer_confirmed') THEN 1 ELSE 0 END) positives,
          SUM(CASE WHEN e.event_type='rejected' THEN 1 ELSE 0 END) rejections
          FROM user_jobs j LEFT JOIN email_events e ON e.user_id=j.user_id AND e.job_id=j.job_id
          WHERE j.user_id=? GROUP BY j.job_id ORDER BY positives DESC,j.updated_at DESC""",(user_id,)).fetchall()
        return [dict(r) for r in rows]

    def recent_email_subjects(self,user_id,limit=100):
        rows=self.conn.execute("SELECT subject,event_type FROM email_events WHERE user_id=? ORDER BY created_at DESC LIMIT ?",(user_id,limit)).fetchall()
        return [dict(r) for r in rows]


    # ---- Onboarding v2 ----
    def onboarding_status(self,user_id):
        r=self.conn.execute("SELECT * FROM user_onboarding WHERE user_id=?",(user_id,)).fetchone()
        if r:
            return {"version":r["version"],"completed":bool(r["completed_at"]),
                    "completed_at":r["completed_at"],"state":json.loads(r["state_json"] or "{}")}
        # Upgrade path: people who already connected a source or have real application
        # history should not be forced through onboarding after a version upgrade.
        connectors=self.conn.execute("SELECT COUNT(*) n FROM connector_tokens WHERE user_id=?",(user_id,)).fetchone()["n"]
        submissions=self.conn.execute("SELECT COUNT(*) n FROM application_submissions WHERE user_id=?",(user_id,)).fetchone()["n"]
        jobs=self.conn.execute("SELECT COUNT(*) n FROM user_jobs WHERE user_id=?",(user_id,)).fetchone()["n"]
        migrated=bool(connectors or submissions or (jobs and os.getenv("CFA_SEED_DEMO","0")!="1"))
        if migrated:
            now=self.now();state={"migrated_from_existing_state":True}
            self.conn.execute("INSERT INTO user_onboarding VALUES(?,?,?,?,?)",(user_id,2,json.dumps(state),now,now));self.conn.commit()
            return {"version":2,"completed":True,"completed_at":now,"state":state}
        return {"version":2,"completed":False,"completed_at":None,"state":{}}

    def save_onboarding_progress(self,user_id,patch):
        current=self.onboarding_status(user_id)
        if current.get("completed"):
            return current
        state=dict(current.get("state") or {});state.update(patch or {});now=self.now()
        self.conn.execute("""INSERT INTO user_onboarding(user_id,version,state_json,completed_at,updated_at) VALUES(?,?,?,?,?)
          ON CONFLICT(user_id) DO UPDATE SET version=excluded.version,state_json=excluded.state_json,updated_at=excluded.updated_at""",
          (user_id,2,json.dumps(state),None,now));self.conn.commit()
        return {"version":2,"completed":False,"completed_at":None,"state":state}

    def complete_onboarding(self,user_id,state):
        now=self.now();payload=dict(state or {});payload["completed_version"]=2
        self.conn.execute("""INSERT INTO user_onboarding(user_id,version,state_json,completed_at,updated_at) VALUES(?,?,?,?,?)
          ON CONFLICT(user_id) DO UPDATE SET version=excluded.version,state_json=excluded.state_json,
          completed_at=excluded.completed_at,updated_at=excluded.updated_at""",
          (user_id,2,json.dumps(payload),now,now));self.conn.commit()
        return {"version":2,"completed":True,"completed_at":now,"state":payload}

    # ---- Funnel policy / applications ----
    def funnel_policy(self,user_id):
        r=self.conn.execute("SELECT policy_json FROM user_funnel_policy WHERE user_id=?",(user_id,)).fetchone()
        if r:return json.loads(r["policy_json"] or "{}")
        def env_list(name):return [x.strip() for x in os.getenv(name,"").split(",") if x.strip()]
        return {
          "excluded_role_terms":env_list("CFA_DEFAULT_EXCLUDED_ROLE_TERMS"),
          "excluded_domains":env_list("CFA_DEFAULT_EXCLUDED_DOMAINS")
        }

    def save_funnel_policy(self,user_id,patch):
        cur=self.funnel_policy(user_id);cur.update(patch or {});now=self.now()
        self.conn.execute("""INSERT INTO user_funnel_policy VALUES(?,?,?)
          ON CONFLICT(user_id) DO UPDATE SET policy_json=excluded.policy_json,updated_at=excluded.updated_at""",
          (user_id,json.dumps(cur),now));self.conn.commit();return cur

    def submissions(self,user_id,limit=1000):
        rows=self.conn.execute("SELECT * FROM application_submissions WHERE user_id=? ORDER BY submitted_at DESC LIMIT ?",(user_id,limit)).fetchall()
        return [dict(r)|{"payload":json.loads(r["payload_json"] or "{}")} for r in rows]

    def latest_submission_for_base(self,user_id,base_key):
        r=self.conn.execute("SELECT * FROM application_submissions WHERE user_id=? AND base_key=? ORDER BY submitted_at DESC LIMIT 1",(user_id,base_key)).fetchone()
        return dict(r) if r else None

    def record_submission(self,user_id,job_id,application_key,base_key,tier,requisition_id=None,role_fingerprint=None,
                          evidence_version=None,cv_version=None,source=None,estimated_minutes=None,payload=None,submitted_at=None):
        now=float(submitted_at or self.now());existing=self.conn.execute("SELECT * FROM application_submissions WHERE user_id=? AND application_key=?",(user_id,application_key)).fetchone()
        if existing:return {**dict(existing),"duplicate":True}
        aid=self.uid("app")
        self.conn.execute("INSERT INTO application_submissions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
          (aid,user_id,job_id,application_key,base_key,requisition_id,role_fingerprint,tier,now,cv_version,evidence_version,
           "submitted",source,int(estimated_minutes or 0),1,json.dumps(payload or {})))
        self.conn.commit();return {**dict(self.conn.execute("SELECT * FROM application_submissions WHERE id=?",(aid,)).fetchone()),"duplicate":False}

    def update_application_response(self,user_id,job_id,state):
        r=self.conn.execute("SELECT id FROM application_submissions WHERE user_id=? AND job_id=? ORDER BY submitted_at DESC LIMIT 1",(user_id,job_id)).fetchone()
        if not r:return False
        self.conn.execute("UPDATE application_submissions SET response_state=? WHERE id=?",(state,r["id"]));self.conn.commit();return True

    def conversion_stats(self,user_id,limit=75):
        rows=self.conn.execute("""SELECT tier,COUNT(*) applications,
          SUM(CASE WHEN response_state IN ('recruiter_or_interview','offer_candidate','offer_confirmed') THEN 1 ELSE 0 END) strong,
          AVG(CASE WHEN estimated_minutes>0 THEN estimated_minutes END) avg_minutes
          FROM (SELECT * FROM application_submissions WHERE user_id=? AND is_unique=1 ORDER BY submitted_at DESC LIMIT ?)
          GROUP BY tier""",(user_id,int(limit))).fetchall()
        return {r["tier"]:{"applications":int(r["applications"]),"strong":int(r["strong"] or 0),"avg_minutes":float(r["avg_minutes"] or 0)} for r in rows}

    def weekly_submission_count(self,user_id,days=7):
        cutoff=self.now()-days*86400
        return self.conn.execute("SELECT COUNT(*) n FROM application_submissions WHERE user_id=? AND submitted_at>=? AND is_unique=1",(user_id,cutoff)).fetchone()["n"]

    # ---- Automatic URL retry queue ----
    def queue_vacancy_fetch(self,user_id,url,error=None,delay_seconds=300):
        now=self.now();existing=self.conn.execute("SELECT id,state FROM vacancy_fetch_queue WHERE user_id=? AND url=?",(user_id,url)).fetchone()
        if existing:
            self.conn.execute("""UPDATE vacancy_fetch_queue SET state='pending',next_attempt=?,last_error=?,updated_at=? WHERE id=?""",
                              (now+delay_seconds,str(error or "")[:500],now,existing["id"]));self.conn.commit();return existing["id"]
        qid=self.uid("fetch")
        self.conn.execute("INSERT INTO vacancy_fetch_queue VALUES(?,?,?,?,?,?,?,?,?)",
                          (qid,user_id,url,"pending",0,now+delay_seconds,str(error or "")[:500],now,now));self.conn.commit();return qid

    def due_vacancy_fetches(self,limit=30):
        rows=self.conn.execute("""SELECT * FROM vacancy_fetch_queue WHERE state='pending' AND next_attempt<=?
          ORDER BY next_attempt LIMIT ?""",(self.now(),limit)).fetchall()
        return [dict(r) for r in rows]

    def mark_vacancy_fetch_done(self,qid):
        self.conn.execute("UPDATE vacancy_fetch_queue SET state='done',updated_at=? WHERE id=?",(self.now(),qid));self.conn.commit()

    def mark_vacancy_fetch_failed(self,qid,error):
        row=self.conn.execute("SELECT attempts FROM vacancy_fetch_queue WHERE id=?",(qid,)).fetchone();attempts=int(row["attempts"] if row else 0)+1
        state="failed" if attempts>=6 else "pending";delay=min(21600,300*(2**min(attempts-1,6)))
        self.conn.execute("""UPDATE vacancy_fetch_queue SET state=?,attempts=?,next_attempt=?,last_error=?,updated_at=? WHERE id=?""",
                          (state,attempts,self.now()+delay,str(error)[:500],self.now(),qid));self.conn.commit()

    # ---- Per-user search preferences ----
    def preferences(self,user_id):
        r=self.conn.execute("SELECT * FROM user_preferences WHERE user_id=?",(user_id,)).fetchone()
        if not r:
            now=self.now()
            def env_bool(name,default):
                raw=os.getenv(name)
                if raw is None:return default
                return str(raw).strip().lower() in {"1","true","yes","on"}
            remote=env_bool("CFA_DEFAULT_REMOTE_ONLY",False)
            relocate=env_bool("CFA_DEFAULT_ALLOW_RELOCATION",True)
            try:salary=float(os.getenv("CFA_DEFAULT_SALARY_FLOOR","0") or 0)
            except Exception:salary=0
            home=os.getenv("CFA_DEFAULT_HOME_REGION") or None
            regions=[x.strip() for x in os.getenv("CFA_DEFAULT_ALLOWED_REGIONS","").split(",") if x.strip()]
            self.conn.execute("INSERT INTO user_preferences VALUES(?,?,?,?,?,?,?)",
                              (user_id,int(remote),int(relocate),salary,home,json.dumps(regions),now));self.conn.commit()
            r=self.conn.execute("SELECT * FROM user_preferences WHERE user_id=?",(user_id,)).fetchone()
        return {"remote_only":bool(r["remote_only"]),"allow_relocation":bool(r["allow_relocation"]),
                "salary_floor_annual":float(r["salary_floor_annual"] or 0),"home_region":r["home_region"],
                "allowed_regions":json.loads(r["allowed_regions_json"] or "[]")}

    def save_preferences(self,user_id,prefs):
        cur=self.preferences(user_id);cur.update({k:v for k,v in (prefs or {}).items() if k in cur})
        now=self.now()
        self.conn.execute("""UPDATE user_preferences SET remote_only=?,allow_relocation=?,
          salary_floor_annual=?,home_region=?,allowed_regions_json=?,updated_at=? WHERE user_id=?""",
          (int(bool(cur["remote_only"])),int(bool(cur["allow_relocation"])),float(cur["salary_floor_annual"] or 0),
           cur.get("home_region"),json.dumps(cur.get("allowed_regions") or []),now,user_id))
        self.conn.commit();return self.preferences(user_id)

    # ---- Per-user scheduled searches ----
    def upsert_search_profile(self,user_id,profile):
        now=self.now();pid=profile.get("id") or self.uid("search")
        interval=max(30,int(profile.get("interval_minutes",360)))
        next_run=profile.get("next_run") or now
        self.conn.execute("""INSERT INTO user_search_profiles VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
          ON CONFLICT(id) DO UPDATE SET query=excluded.query,countries_json=excluded.countries_json,
          remote_only=excluded.remote_only,sources_json=excluded.sources_json,interval_minutes=excluded.interval_minutes,
          enabled=excluded.enabled,next_run=excluded.next_run,updated_at=excluded.updated_at""",
          (pid,user_id,str(profile.get("query","")).strip(),json.dumps(profile.get("countries") or []),
           int(bool(profile.get("remote_only",False))),json.dumps(profile.get("sources") or []),
           interval,int(bool(profile.get("enabled",True))),profile.get("last_run"),next_run,now,now))
        self.conn.commit();return self.search_profile(user_id,pid)

    def search_profile(self,user_id,pid):
        r=self.conn.execute("SELECT * FROM user_search_profiles WHERE user_id=? AND id=?",(user_id,pid)).fetchone()
        return self._search_profile(r) if r else None

    def due_search_profiles(self,now=None,limit=30):
        now=now or self.now()
        rows=self.conn.execute("""SELECT * FROM user_search_profiles WHERE enabled=1 AND next_run<=?
          ORDER BY next_run LIMIT ?""",(now,limit)).fetchall()
        return [self._search_profile(r) for r in rows]

    def mark_search_profile_run(self,user_id,pid,when=None):
        when=when or self.now()
        r=self.conn.execute("SELECT interval_minutes FROM user_search_profiles WHERE user_id=? AND id=?",(user_id,pid)).fetchone()
        if not r:return
        self.conn.execute("UPDATE user_search_profiles SET last_run=?,next_run=?,updated_at=? WHERE user_id=? AND id=?",
                          (when,when+int(r["interval_minutes"])*60,when,user_id,pid));self.conn.commit()

    def _search_profile(self,r):
        return {"id":r["id"],"user_id":r["user_id"],"query":r["query"],
                "countries":json.loads(r["countries_json"] or "[]"),"remote_only":bool(r["remote_only"]),
                "sources":json.loads(r["sources_json"] or "[]"),"interval_minutes":r["interval_minutes"],
                "enabled":bool(r["enabled"]),"last_run":r["last_run"],"next_run":r["next_run"]}

    # ---- Job ingestion / analysis persistence ----
    def upsert_user_job(self,user_id,job,analysis=None):
        now=self.now();source_id=str(job.get("source_job_id") or "");canonical=job.get("canonical_key") or ""
        job_id=str(job.get("job_id") or source_id or canonical or self.uid("job"))
        if source_id and job.get("source"):job_id=f"{job.get('source')}:{source_id}"
        payload=dict(job)
        if analysis is not None:payload["analysis"]=analysis
        decision=(analysis or {}).get("final_action") or job.get("decision") or "REVIEW"
        next_action=(analysis or {}).get("next_action") or job.get("next_action")
        blocker=(analysis or {}).get("blocking_reason") or job.get("blocker")
        self.conn.execute("""INSERT INTO user_jobs(
          user_id,job_id,company,title,location,compensation,decision,next_action,blocker,
          evidence_verified,evidence_review,evidence_gaps,effort_minutes,source_url,payload_json,updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(user_id,job_id) DO UPDATE SET company=excluded.company,title=excluded.title,
          location=excluded.location,compensation=excluded.compensation,decision=excluded.decision,
          next_action=excluded.next_action,blocker=excluded.blocker,
          evidence_verified=excluded.evidence_verified,evidence_review=excluded.evidence_review,
          evidence_gaps=excluded.evidence_gaps,effort_minutes=excluded.effort_minutes,
          source_url=excluded.source_url,payload_json=excluded.payload_json,updated_at=excluded.updated_at""",
          (user_id,job_id,job.get("company") or "Unknown company",job.get("title") or "Untitled role",
           job.get("location"),job.get("compensation") or _salary_label(job),decision,next_action,blocker,
           int((analysis or {}).get("verified_count",0)),int((analysis or {}).get("review_count",0)),
           int((analysis or {}).get("gap_count",0)),int((analysis or {}).get("estimated_minutes") or 30),
           job.get("source_url"),json.dumps(payload),now))
        self.conn.commit();return self.job(user_id,job_id)

    def enqueue_job_action(self,user_id,job_id,analysis):
        action=analysis.get("final_action")
        if action=="DO_NOT_APPLY":return None
        if action=="APPLY":typ,title,priority="apply",f"Apply to {analysis.get('company','this role')}",90
        elif action=="VERIFY_FIRST":typ,title,priority="verify",f"Verify one blocker for {analysis.get('company','this role')}",100
        else:typ,title,priority="review",f"Review match for {analysis.get('company','this role')}",75
        existing=self.conn.execute("""SELECT id FROM user_actions WHERE user_id=? AND job_id=? AND action_type=? AND state='open'""",(user_id,job_id,typ)).fetchone()
        if existing:return existing["id"]
        now=self.now();aid=self.uid("act")
        self.conn.execute("INSERT INTO user_actions VALUES(?,?,?,?,?,?,?,?,?,?,?)",
          (aid,user_id,job_id,typ,title,analysis.get("summary",""),priority,"open",json.dumps({"auto":True}),now,now))
        self.conn.commit();return aid

    # ---- User-scoped evidence ----
    def upsert_user_evidence(self,user_id,item):
        now=self.now();tags=item.get("tags") or []
        vals=(user_id,item["id"],item.get("source_type","unknown"),item.get("source_ref",""),
              item.get("title",""),item.get("claim",""),item.get("evidence",""),json.dumps(tags),
              item.get("status","needs-review"),int(bool(item.get("direct"))),
              item.get("visibility","private"),item.get("ownership"),item.get("metric"),
              item.get("boundary"),now)
        self.conn.execute("""INSERT INTO user_evidence VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
          ON CONFLICT(user_id,evidence_id) DO UPDATE SET
          source_type=excluded.source_type,source_ref=excluded.source_ref,title=excluded.title,
          claim=excluded.claim,evidence=excluded.evidence,tags_json=excluded.tags_json,
          status=excluded.status,direct=excluded.direct,visibility=excluded.visibility,
          ownership=excluded.ownership,metric=excluded.metric,boundary=excluded.boundary,
          updated_at=excluded.updated_at""",vals)
        self.conn.execute("DELETE FROM user_evidence_fts WHERE user_id=? AND evidence_id=?",(user_id,item["id"]))
        self.conn.execute("""INSERT INTO user_evidence_fts(user_id,evidence_id,title,claim,evidence,tags)
          VALUES(?,?,?,?,?,?)""",(user_id,item["id"],item.get("title",""),item.get("claim",""),
                                 item.get("evidence","")," ".join(tags)))
        self.conn.commit()
        return item["id"]

    def user_evidence(self,user_id,status=None):
        if status:
            rows=self.conn.execute("SELECT * FROM user_evidence WHERE user_id=? AND status=? ORDER BY title",(user_id,status)).fetchall()
        else:
            rows=self.conn.execute("SELECT * FROM user_evidence WHERE user_id=? ORDER BY title",(user_id,)).fetchall()
        return [self._evidence(r) for r in rows]

    def user_evidence_one(self,user_id,evidence_id):
        r=self.conn.execute("SELECT * FROM user_evidence WHERE user_id=? AND evidence_id=?",(user_id,evidence_id)).fetchone()
        return self._evidence(r) if r else None

    def search_user_evidence(self,user_id,query,limit=12):
        terms=[t for t in str(query).replace('"'," ").split() if len(t)>2]
        if not terms:return []
        match=" OR ".join(f'"{t}"' for t in terms[:14])
        rows=self.conn.execute("""SELECT e.*,bm25(user_evidence_fts) rank
          FROM user_evidence_fts JOIN user_evidence e
          ON e.user_id=user_evidence_fts.user_id AND e.evidence_id=user_evidence_fts.evidence_id
          WHERE user_evidence_fts MATCH ? AND e.user_id=?
          ORDER BY rank LIMIT ?""",(match,user_id,limit)).fetchall()
        out=[]
        for r in rows:
            x=self._evidence(r);x["rank"]=r["rank"];out.append(x)
        return out

    def count_user_evidence(self,user_id):
        return self.conn.execute("SELECT COUNT(*) n FROM user_evidence WHERE user_id=?",(user_id,)).fetchone()["n"]

    def _evidence(self,r):
        return {
          "id":r["evidence_id"],"source_type":r["source_type"],"source_ref":r["source_ref"],
          "title":r["title"],"claim":r["claim"],"evidence":r["evidence"],
          "tags":json.loads(r["tags_json"] or "[]"),"status":r["status"],"direct":bool(r["direct"]),
          "visibility":r["visibility"],"ownership":r["ownership"],"metric":r["metric"],"boundary":r["boundary"]
        }

    # ---- Job vacancy text / requirements ----
    def update_job_payload(self,user_id,job_id,patch):
        r=self.conn.execute("SELECT payload_json FROM user_jobs WHERE user_id=? AND job_id=?",(user_id,job_id)).fetchone()
        if not r:raise ValueError("Job not found")
        data=json.loads(r["payload_json"] or "{}");data.update(patch or {})
        self.conn.execute("UPDATE user_jobs SET payload_json=?,updated_at=? WHERE user_id=? AND job_id=?",
                          (json.dumps(data),self.now(),user_id,job_id));self.conn.commit()
        return self.job(user_id,job_id)

    def save_job_requirements(self,user_id,job_id,requirements):
        now=self.now()
        self.conn.execute("DELETE FROM user_job_requirements WHERE user_id=? AND job_id=?",(user_id,job_id))
        for r in requirements:
            self.conn.execute("""INSERT INTO user_job_requirements VALUES(?,?,?,?,?,?,?,?)""",
              (user_id,job_id,r["id"],r["label"],r.get("source"),int(bool(r.get("mustHave",True))),
               r.get("extractor"),now))
        self.conn.commit()
        return self.job_requirements(user_id,job_id)

    def job_requirements(self,user_id,job_id):
        rows=self.conn.execute("""SELECT * FROM user_job_requirements WHERE user_id=? AND job_id=?
          ORDER BY requirement_id""",(user_id,job_id)).fetchall()
        return [{"id":r["requirement_id"],"label":r["label"],"source":r["source_text"],
                 "mustHave":bool(r["must_have"]),"extractor":r["extractor"]} for r in rows]

    # ---- Proposal state ----
    def save_pack_proposal(self,user_id,job_id,proposal):
        now=self.now();existing=self.conn.execute("SELECT id FROM pack_proposals WHERE user_id=? AND job_id=?",(user_id,job_id)).fetchone()
        pid=existing["id"] if existing else self.uid("proposal")
        self.conn.execute("""INSERT INTO pack_proposals VALUES(?,?,?,?,?,?,?)
          ON CONFLICT(user_id,job_id) DO UPDATE SET status=excluded.status,
          proposal_json=excluded.proposal_json,updated_at=excluded.updated_at""",
          (pid,user_id,job_id,"proposed",json.dumps(proposal),now,now))
        self.conn.commit()
        return self.pack_proposal(user_id,job_id)

    def pack_proposal(self,user_id,job_id):
        r=self.conn.execute("SELECT * FROM pack_proposals WHERE user_id=? AND job_id=?",(user_id,job_id)).fetchone()
        if not r:return None
        return {"id":r["id"],"job_id":r["job_id"],"status":r["status"],
                "proposal":json.loads(r["proposal_json"] or "{}"),"updated_at":r["updated_at"]}

    def approve_pack_proposal(self,user_id,job_id,approved_ids):
        p=self.pack_proposal(user_id,job_id)
        if not p:raise ValueError("Proposal not found")
        approved=set(approved_ids or [])
        proposal=p["proposal"]
        selected=[]
        for s in proposal.get("suggestions",[]):
            if s.get("suggestion_id") not in approved:continue
            evidence_id=s.get("evidence_id","")
            current_evidence=self.user_evidence_one(user_id,evidence_id) if evidence_id else None
            # Revalidate at approval time: proposals can become stale after evidence changes.
            if not current_evidence or current_evidence.get("status")!="verified":continue
            if str(s.get("claim","")).strip()!=str(current_evidence.get("claim","")).strip():continue
            selected.append({
              "claim":current_evidence.get("claim",""),
              "evidence_id":evidence_id,
              "verified":True,
              "approved":True,
              "requirement":s.get("requirement",""),
              "confidence":s.get("confidence",0),
              "boundary":current_evidence.get("boundary")
            })
        current=self.application_pack(user_id,job_id,create=True)
        data=current["data"]
        role=data.get("role") or {}
        claims=[x["claim"].rstrip(".") for x in selected if x.get("claim")]
        if claims:
            data["positioning"]=f"For {role.get('title','this role')} at {role.get('company','the company')}, the strongest verified evidence I would use is: " + "; ".join(claims[:3]) + "."
            data["recruiter_note"]=f"Hi — I’m looking at {role.get('title','the role')} at {role.get('company','your team')}. " + " ".join(f"I can show {c}." for c in claims[:2]) + " I’d be interested in understanding the highest-cost product uncertainty this hire is expected to remove."
        else:
            data["positioning"]=""
            data["recruiter_note"]=""
        data["interview_risks"]=proposal.get("interview_risks",[])
        data["proof_cards"]=selected
        saved=self.save_application_pack(user_id,job_id,data)
        self.conn.execute("UPDATE pack_proposals SET status='reviewed',updated_at=? WHERE user_id=? AND job_id=?",
                          (self.now(),user_id,job_id));self.conn.commit()
        return saved

    # ---- Gmail watch / PubSub queue ----
    def save_gmail_watch(self,user_id,email_address,last_history_id,expiration_ms=None):
        now=self.now()
        self.conn.execute("""INSERT INTO gmail_watches(
          user_id,email_address,last_history_id,expiration_ms,last_notification_at,last_fallback_sync,updated_at
        ) VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET email_address=excluded.email_address,
        last_history_id=excluded.last_history_id,expiration_ms=excluded.expiration_ms,updated_at=excluded.updated_at""",
        (user_id,email_address,last_history_id,int(expiration_ms) if expiration_ms else None,None,None,now))
        self.conn.commit()
        return self.gmail_watch(user_id)

    def gmail_watch(self,user_id):
        r=self.conn.execute("SELECT * FROM gmail_watches WHERE user_id=?",(user_id,)).fetchone()
        return dict(r) if r else None

    def gmail_watch_by_email(self,email):
        r=self.conn.execute("SELECT * FROM gmail_watches WHERE lower(email_address)=lower(?)",(email,)).fetchone()
        return dict(r) if r else None

    def update_gmail_history(self,user_id,history_id,notification=False,fallback=False):
        now=self.now()
        fields=["last_history_id=?","updated_at=?"];vals=[str(history_id),now]
        if notification: fields+=["last_notification_at=?"];vals+=[now]
        if fallback: fields+=["last_fallback_sync=?"];vals+=[now]
        vals.append(user_id)
        self.conn.execute(f"UPDATE gmail_watches SET {','.join(fields)} WHERE user_id=?",vals)
        self.conn.commit()

    def watches_due_for_renewal(self,within_ms=172800000):
        threshold=int((self.now()*1000)+within_ms)
        rows=self.conn.execute("""SELECT * FROM gmail_watches
          WHERE expiration_ms IS NULL OR expiration_ms<=? ORDER BY updated_at""",(threshold,)).fetchall()
        return [dict(r) for r in rows]

    def watches_due_for_fallback(self,age_seconds=21600):
        cutoff=self.now()-age_seconds
        rows=self.conn.execute("""SELECT * FROM gmail_watches
          WHERE COALESCE(last_fallback_sync,0)<=? ORDER BY COALESCE(last_fallback_sync,0)""",(cutoff,)).fetchall()
        return [dict(r) for r in rows]

    def enqueue_gmail_push(self,pubsub_message_id,email_address,history_id):
        now=self.now();pid=self.uid("push")
        try:
            self.conn.execute("INSERT INTO gmail_push_queue VALUES(?,?,?,?,?,?,?,?,?)",
              (pid,pubsub_message_id,email_address,str(history_id),"pending",0,None,now,now))
            self.conn.commit();return True
        except sqlite3.IntegrityError:
            return False

    def pending_gmail_pushes(self,limit=50):
        rows=self.conn.execute("""SELECT * FROM gmail_push_queue WHERE state='pending'
          ORDER BY received_at LIMIT ?""",(limit,)).fetchall()
        return [dict(r) for r in rows]

    def mark_gmail_push(self,push_id,state,error=None):
        now=self.now()
        self.conn.execute("""UPDATE gmail_push_queue SET state=?,attempts=attempts+1,last_error=?,updated_at=? WHERE id=?""",
                          (state,error,now,push_id))
        self.conn.commit()

    # ---- Notification outbox ----
    def queue_notification(self,user_id,kind,text,job_id=None,dedupe_key=None,delay_seconds=0):
        now=self.now();nid=self.uid("notify")
        try:
            self.conn.execute("""INSERT INTO notification_outbox VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
              (nid,user_id,kind,text,job_id,dedupe_key,"pending",0,now+delay_seconds,None,now,None))
            self.conn.commit();return nid
        except sqlite3.IntegrityError:
            return None

    def pending_notifications(self,limit=30):
        now=self.now()
        rows=self.conn.execute("""SELECT n.*,u.telegram_user_id FROM notification_outbox n
          JOIN users u ON u.id=n.user_id
          WHERE n.state='pending' AND n.next_attempt<=? AND u.telegram_user_id IS NOT NULL
          ORDER BY n.created_at LIMIT ?""",(now,limit)).fetchall()
        return [dict(r) for r in rows]

    def mark_notification_sent(self,notification_id):
        now=self.now()
        self.conn.execute("UPDATE notification_outbox SET state='sent',sent_at=? WHERE id=?",(now,notification_id))
        self.conn.commit()

    def mark_notification_failed(self,notification_id,error,retry_seconds=60):
        now=self.now()
        self.conn.execute("""UPDATE notification_outbox SET attempts=attempts+1,last_error=?,
          next_attempt=?,state=CASE WHEN attempts>=5 THEN 'failed' ELSE 'pending' END WHERE id=?""",
          (str(error)[:500],now+retry_seconds,notification_id))
        self.conn.commit()

    # ---- Application packs ----
    def _blank_pack(self,user_id,job_id):
        job=self.job(user_id,job_id)
        if not job: raise ValueError("Job not found")
        return {
          "role":{"company":job["company"],"title":job["title"],"location":job["location"],"compensation":job["compensation"]},
          "positioning":"",
          "proof_cards":[],
          "recruiter_note":"",
          "short_answers":[],
          "interview_risks":[],
          "export_policy":"Only proof cards marked verified and linked to an evidence_id are exportable."
        }

    def application_pack(self,user_id,job_id,create=True):
        r=self.conn.execute("SELECT * FROM application_packs WHERE user_id=? AND job_id=?",(user_id,job_id)).fetchone()
        if not r and create:
            now=self.now();pid=self.uid("pack");data=self._blank_pack(user_id,job_id)
            self.conn.execute("INSERT INTO application_packs VALUES(?,?,?,?,?,?,?,?)",
              (pid,user_id,job_id,1,"draft",json.dumps(data),now,now))
            self.conn.commit()
            r=self.conn.execute("SELECT * FROM application_packs WHERE id=?",(pid,)).fetchone()
        if not r:return None
        return {"id":r["id"],"job_id":r["job_id"],"version":r["version"],"status":r["status"],
                "data":json.loads(r["data_json"] or "{}"),"updated_at":r["updated_at"]}

    def save_application_pack(self,user_id,job_id,data):
        current=self.application_pack(user_id,job_id,create=True)
        clean={
          "role":data.get("role") or current["data"].get("role") or {},
          "positioning":str(data.get("positioning",""))[:5000],
          "proof_cards":[],
          "recruiter_note":str(data.get("recruiter_note",""))[:5000],
          "short_answers":data.get("short_answers") if isinstance(data.get("short_answers"),list) else [],
          "interview_risks":data.get("interview_risks") if isinstance(data.get("interview_risks"),list) else [],
          "export_policy":"Only proof cards marked verified and linked to an evidence_id are exportable."
        }
        for card in (data.get("proof_cards") or [])[:20]:
            claim=str(card.get("claim",""))[:2000]
            evidence_id=str(card.get("evidence_id",""))[:200]
            source=self.user_evidence_one(user_id,evidence_id) if evidence_id else None
            source_verified=bool(source and source.get("status")=="verified")
            exact_claim=bool(source and claim.strip()==str(source.get("claim","")).strip())
            approved=bool(card.get("approved",False) and source_verified and exact_claim)
            clean["proof_cards"].append({
              "claim":claim,
              "evidence_id":evidence_id,
              "verified":source_verified,
              "approved":approved,
              "requirement":str(card.get("requirement",""))[:1000],
              "confidence":float(card.get("confidence",0) or 0),
              "boundary":source.get("boundary") if source else card.get("boundary")
            })
        now=self.now()
        self.conn.execute("""UPDATE application_packs SET version=version+1,data_json=?,updated_at=? WHERE user_id=? AND job_id=?""",
                          (json.dumps(clean),now,user_id,job_id))
        self.conn.commit()
        return self.application_pack(user_id,job_id,create=False)

    def create_export_download(self,user_id,job_id,format,content,file_name,ttl_seconds=1800):
        token=uuid.uuid4().hex+uuid.uuid4().hex
        now=self.now()
        self.conn.execute("INSERT INTO export_downloads VALUES(?,?,?,?,?,?,?,?)",
                          (token,user_id,job_id,format,content,file_name,now+ttl_seconds,now))
        self.conn.commit()
        return token

    def export_download(self,token):
        r=self.conn.execute("SELECT * FROM export_downloads WHERE token=? AND expires_at>?",(token,self.now())).fetchone()
        return dict(r) if r else None

    def cleanup_expired_downloads(self):
        self.conn.execute("DELETE FROM export_downloads WHERE expires_at<=?",(self.now(),));self.conn.commit()

    def _job(self,r):
        if not r: return None
        return {
          "job_id":r["job_id"],"company":r["company"],"title":r["title"],
          "location":r["location"],"compensation":r["compensation"],"decision":r["decision"],
          "next_action":r["next_action"],"blocker":r["blocker"],
          "evidence_verified":r["evidence_verified"],"evidence_review":r["evidence_review"],
          "evidence_gaps":r["evidence_gaps"],"effort_minutes":r["effort_minutes"],
          "source_url":r["source_url"],"note":r["note"] if "note" in r.keys() else "",
          "payload":json.loads(r["payload_json"] or "{}")
        }


def _salary_label(job):
    lo=job.get("salary_min");hi=job.get("salary_max");cur=job.get("currency") or ""
    if lo is None and hi is None:return None
    if lo is not None and hi is not None:return f"{cur}{int(lo):,}–{cur}{int(hi):,}".strip()
    return f"{cur}{int(lo if lo is not None else hi):,}+".strip()

def re_words(s):
    import re
    return re.findall(r"[a-z0-9]+",(s or "").lower())
