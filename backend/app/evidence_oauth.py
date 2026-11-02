"""OAuth 2.1 PKCE/DCR for RoleHint Evidence MCP. All tokens are hashed and audience-bound."""
from __future__ import annotations
import base64,hashlib,hmac,json,re,secrets,sqlite3,time
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode

SCHEMA="""
CREATE TABLE IF NOT EXISTS rh_oauth_clients(
 id TEXT PRIMARY KEY,name TEXT NOT NULL,redirect_uris TEXT NOT NULL,created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS rh_oauth_requests(
 id TEXT PRIMARY KEY,client_id TEXT NOT NULL,user_id TEXT NOT NULL,session_hash TEXT NOT NULL,
 redirect_uri TEXT NOT NULL,state TEXT NOT NULL,scope TEXT NOT NULL,resource TEXT NOT NULL,
 code_challenge TEXT NOT NULL,expires_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS rh_oauth_codes(
 code_hash TEXT PRIMARY KEY,client_id TEXT NOT NULL,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 redirect_uri TEXT NOT NULL,scope TEXT NOT NULL,resource TEXT NOT NULL,
 code_challenge TEXT NOT NULL,expires_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS rh_oauth_access(
 token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 client_id TEXT NOT NULL,scope TEXT NOT NULL,resource TEXT NOT NULL,expires_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS rh_oauth_refresh(
 token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 client_id TEXT NOT NULL,scope TEXT NOT NULL,resource TEXT NOT NULL,expires_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS rh_oauth_access_user ON rh_oauth_access(user_id,client_id);
CREATE INDEX IF NOT EXISTS rh_oauth_refresh_user ON rh_oauth_refresh(user_id,client_id);
CREATE TABLE IF NOT EXISTS rh_oauth_login_handoffs(
 ticket_hash TEXT PRIMARY KEY,request_json TEXT NOT NULL,
 created_at REAL NOT NULL,expires_at REAL NOT NULL);
"""
SCOPES={"evidence:read","evidence:propose"}
CLAUDE_REDIRECTS={"https://claude.ai/api/mcp/auth_callback",
                  "https://claude.com/api/mcp/auth_callback"}
CHATGPT_STABLE_REDIRECT="https://chatgpt.com/connector_platform_oauth_redirect"
CHATGPT_LEGACY_CALLBACK=re.compile(r"^/connector/oauth/[A-Za-z0-9_-]{8,160}$")
PKCE_RE=re.compile(r"^[A-Za-z0-9._~-]{43,128}$")
CHALLENGE_RE=re.compile(r"^[A-Za-z0-9_-]{43}$")

def hashed(value):return hashlib.sha256(str(value).encode()).hexdigest()
def pkce(verifier):
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()

class OAuthServer:
    def __init__(self,path:str|Path,base:str,allow_loopback=False):
        self.path=str(path);self.base=base.rstrip("/");self.resource=self.base+"/mcp"
        self.allow_loopback=allow_loopback
        if not self.base.startswith("https://") and not (allow_loopback and self.base.startswith("http://localhost:")):
            raise ValueError("Canonical OAuth issuer requires HTTPS")
        with self.db() as conn:conn.executescript(SCHEMA)
    def db(self):
        conn=sqlite3.connect(self.path,timeout=15,isolation_level=None)
        conn.row_factory=sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=15000")
        return conn
    def validate_redirect(self,uri):
        try:
            u=urlsplit(uri)
            if not u.netloc or u.username or u.password or u.fragment:return False
            if u.scheme=="https" and not u.query and uri in CLAUDE_REDIRECTS:return True
            if u.scheme=="https" and not u.query and uri==CHATGPT_STABLE_REDIRECT:return True
            if u.scheme=="https" and u.hostname=="chatgpt.com" and not u.query and CHATGPT_LEGACY_CALLBACK.fullmatch(u.path):return True
            if self.allow_loopback and u.scheme=="http" and u.hostname in ("localhost","127.0.0.1"):return True
            return False
        except ValueError:return False
    def register(self,data):
        uris=data.get("redirect_uris")
        if not isinstance(uris,list) or not 1<=len(uris)<=5 or any(
          not isinstance(x,str) or not self.validate_redirect(x) for x in uris):
            raise ValueError("Only approved assistant callback URLs allowed")
        cid="rhclient_"+secrets.token_urlsafe(20)
        name=str(data.get("client_name") or "AI assistant").strip()[:90] or "AI assistant"
        with self.db() as conn:
            conn.execute("INSERT INTO rh_oauth_clients VALUES(?,?,?,?)",
                         (cid,name,json.dumps(uris),time.time()))
        return {"client_id":cid,"client_name":name,"redirect_uris":uris,
                "token_endpoint_auth_method":"none","grant_types":["authorization_code","refresh_token"],
                "response_types":["code"],"client_id_issued_at":int(time.time())}
    def _validate_authorize(self,query):
        cid=query.get("client_id","");redirect=query.get("redirect_uri","")
        with self.db() as conn:
            row=conn.execute("SELECT * FROM rh_oauth_clients WHERE id=?",(cid,)).fetchone()
        if not row or redirect not in json.loads(row["redirect_uris"]):
            raise ValueError("Unknown client or callback URL")
        if query.get("response_type")!="code" or query.get("code_challenge_method")!="S256":
            raise ValueError("Authorization code with PKCE S256 required")
        challenge=query.get("code_challenge","")
        if not CHALLENGE_RE.fullmatch(challenge):raise ValueError("Invalid code challenge")
        if query.get("resource")!=self.resource:raise ValueError("Invalid OAuth resource")
        requested=query.get("scope","").split()
        if not requested or len(requested)!=len(set(requested)) or not set(requested)<=SCOPES:
            raise ValueError("Invalid scope")
        state=query.get("state","")
        if not 12<=len(state)<=512 or any(ord(c)<33 for c in state):
            raise ValueError("Invalid state")
        return cid,redirect,challenge,requested,state

    def stage_for_login(self,query):
        # Keep an OAuth request for a user who must sign in by email first.
        # A ticket cannot authorize tools; it only restores the user's
        # exact registered-client/PKCE request at the consent screen.
        self._validate_authorize(query)
        serialized=json.dumps(query,ensure_ascii=False,separators=(",",":"))
        if len(serialized)>4096:raise ValueError("OAuth request is too long")
        now=time.time()
        ticket=secrets.token_urlsafe(32)
        with self.db() as conn:
            conn.execute("DELETE FROM rh_oauth_login_handoffs WHERE expires_at<?",(now,))
            conn.execute("INSERT INTO rh_oauth_login_handoffs VALUES(?,?,?,?)",
                         (hashed(ticket),serialized,now,now+900))
        return ticket

    def pending_login(self,ticket):
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,96}",str(ticket)):
            return False
        with self.db() as conn:
            return conn.execute(
                "SELECT 1 FROM rh_oauth_login_handoffs WHERE ticket_hash=? AND expires_at>?",
                (hashed(ticket),time.time())).fetchone() is not None

    def resume_login(self,uid,session_token,ticket):
        if not self.pending_login(ticket):
            raise ValueError("Connection sign-in expired; reconnect the assistant")
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row=conn.execute(
                  "SELECT request_json FROM rh_oauth_login_handoffs WHERE ticket_hash=? AND expires_at>?",
                  (hashed(ticket),time.time())).fetchone()
                if not row:raise ValueError("Connection ticket expired or used")
                conn.execute("DELETE FROM rh_oauth_login_handoffs WHERE ticket_hash=?",(hashed(ticket),))
                conn.commit()
            except BaseException:
                conn.rollback()
                raise
        query=json.loads(row["request_json"])
        # Revalidate client and callback even if configuration changed during login.
        self._validate_authorize(query)
        return query

    def authorize(self,uid,session_token,query):
        cid,redirect,challenge,requested,state=self._validate_authorize(query)
        request_id=secrets.token_urlsafe(32)
        with self.db() as conn:
            conn.execute("DELETE FROM rh_oauth_requests WHERE expires_at<?",(time.time(),))
            conn.execute("INSERT INTO rh_oauth_requests VALUES(?,?,?,?,?,?,?,?,?,?)",
                         (request_id,cid,uid,hashed(session_token),redirect,state,
                          " ".join(sorted(requested)),self.resource,challenge,time.time()+600))
        return request_id,sorted(requested)
    def consent(self,uid,session_token,request_id,approve):
        now=time.time()
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row=conn.execute("SELECT * FROM rh_oauth_requests WHERE id=? AND expires_at>?",
                                 (request_id,now)).fetchone()
                if not row or row["user_id"]!=uid or not hmac.compare_digest(row["session_hash"],hashed(session_token)):
                    raise ValueError("Authorization expired or bound to another login")
                conn.execute("DELETE FROM rh_oauth_requests WHERE id=?",(request_id,))
                params={"state":row["state"],"iss":self.base}
                if approve:
                    code=secrets.token_urlsafe(48)
                    conn.execute("INSERT INTO rh_oauth_codes VALUES(?,?,?,?,?,?,?,?)",
                                 (hashed(code),row["client_id"],uid,row["redirect_uri"],
                                  row["scope"],row["resource"],row["code_challenge"],now+180))
                    params["code"]=code
                else:params["error"]="access_denied"
                conn.commit()
            except BaseException:conn.rollback();raise
        u=urlsplit(row["redirect_uri"])
        return urlunsplit((u.scheme,u.netloc,u.path,urlencode(list(parse_qsl(u.query))+list(params.items())),""))
    def _issue(self,conn,uid,cid,scope,resource,now):
        access=secrets.token_urlsafe(48);refresh=secrets.token_urlsafe(48)
        conn.execute("INSERT INTO rh_oauth_access VALUES(?,?,?,?,?,?)",
                     (hashed(access),uid,cid,scope,resource,now+3600))
        conn.execute("INSERT INTO rh_oauth_refresh VALUES(?,?,?,?,?,?)",
                     (hashed(refresh),uid,cid,scope,resource,now+86400*14))
        return {"access_token":access,"refresh_token":refresh,"token_type":"Bearer",
                "expires_in":3600,"scope":scope}
    def token(self,params):
        cid=params.get("client_id","");resource=params.get("resource")
        if not cid or resource!=self.resource:raise ValueError("Invalid client/resource")
        now=time.time()
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                if params.get("grant_type")=="authorization_code":
                    code=params.get("code","");verifier=params.get("code_verifier","")
                    row=conn.execute("SELECT * FROM rh_oauth_codes WHERE code_hash=? AND expires_at>?",
                                     (hashed(code),now)).fetchone()
                    if (not row or row["client_id"]!=cid or row["redirect_uri"]!=params.get("redirect_uri")
                      or not PKCE_RE.fullmatch(verifier)
                      or not hmac.compare_digest(pkce(verifier),row["code_challenge"])):
                        raise ValueError("Invalid or expired code/PKCE")
                    conn.execute("DELETE FROM rh_oauth_codes WHERE code_hash=?",(hashed(code),))
                elif params.get("grant_type")=="refresh_token":
                    tok=params.get("refresh_token","")
                    row=conn.execute("SELECT * FROM rh_oauth_refresh WHERE token_hash=? AND expires_at>?",
                                     (hashed(tok),now)).fetchone()
                    if not row or row["client_id"]!=cid:raise ValueError("Invalid refresh token")
                    conn.execute("DELETE FROM rh_oauth_refresh WHERE token_hash=?",(hashed(tok),))
                else:raise ValueError("Unsupported OAuth grant")
                if row["resource"]!=resource:raise ValueError("Invalid audience")
                result=self._issue(conn,row["user_id"],cid,row["scope"],resource,now)
                conn.commit();return result
            except BaseException:conn.rollback();raise
    def verify(self,access):
        if not access or len(access)<40:return None
        with self.db() as conn:
            row=conn.execute("SELECT * FROM rh_oauth_access WHERE token_hash=? AND expires_at>?",
                             (hashed(access),time.time())).fetchone()
            if not row or row["resource"]!=self.resource:return None
            return {"user_id":row["user_id"],"client_id":row["client_id"],
                    "scopes":row["scope"].split(),"expires_at":row["expires_at"]}
    def connections(self,uid):
        with self.db() as conn:
            return [dict(r) for r in conn.execute("""SELECT a.client_id,c.name,MAX(a.expires_at) expires_at
              FROM rh_oauth_access a JOIN rh_oauth_clients c ON a.client_id=c.id
              WHERE a.user_id=? AND a.expires_at>? GROUP BY a.client_id,c.name""",(uid,time.time()))]
    def revoke(self,uid,cid):
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM rh_oauth_access WHERE user_id=? AND client_id=?",(uid,cid))
            conn.execute("DELETE FROM rh_oauth_refresh WHERE user_id=? AND client_id=?",(uid,cid))
            conn.commit()
        return {"revoked":True}
