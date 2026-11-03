#!/usr/bin/env python3
"""Safe read-only HTTP preflight of the dedicated RoleHint staging service.

This is not full acceptance, a database test or a mail-delivery test.
The Railway environment is named production, but only the explicitly named
rolehint-staging service is allowed here; production API is always forbidden.
"""
from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

FORBIDDEN = {"rolehint-api-worker-production.up.railway.app"}
ALLOWED = {"rolehint-staging-production.up.railway.app"}

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        raise RuntimeError("Unexpected external redirect in staging preflight")

def require_safe_target(value: str) -> str:
    parsed=urlsplit(value.rstrip("/"))
    host=(parsed.hostname or "").lower()
    if (parsed.scheme!="https" or parsed.port not in (None,443) or parsed.username
        or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("","/")
        or host in FORBIDDEN or host not in ALLOWED):
        raise ValueError("Only the verified rolehint-staging service HTTPS origin is allowed; production is forbidden")
    return "https://"+host

def request(opener,base,path,*,method="GET",data=None):
    headers={"Accept":"application/json, text/html;q=0.9"}
    if data is not None:headers["Content-Type"]="application/json"
    req=Request(base+path,headers=headers,data=data,method=method)
    try:
        with opener.open(req,timeout=12) as response:
            return response.status,dict(response.headers.items()),response.read(4096).decode("utf-8","replace")
    except HTTPError as error:
        return error.code,dict(error.headers.items()),error.read(4096).decode("utf-8","replace")

def run(base):
    opener=build_opener(NoRedirect())
    checks=[]
    def check(label,ok,detail=""):
        checks.append({"check":label,"ok":bool(ok),"detail":detail[:150]})
        print(("PASS" if ok else "FAIL"),label)
    code,_,body=request(opener,base,"/health")
    try:live=json.loads(body)
    except ValueError:live={}
    check("staging health",code==200 and live.get("ok") is True,f"HTTP {code}")
    code,_,body=request(opener,base,"/webapp/evidence.html")
    check("browser Evidence Inbox published",code==200 and "Evidence Inbox" in body,f"HTTP {code}")
    code,_,body=request(opener,base,"/web-api/evidence/candidates")
    check("guest cannot read evidence",code==401,f"HTTP {code}")
    code,_,_=request(opener,base,"/web-api/evidence/candidates",method="POST",
         data=b'{"candidates":[]}')
    check("CSRF or auth blocks anonymous writes",code in (401,403),f"HTTP {code}")
    code,_,body=request(opener,base,"/web-api/auth-status")
    try:auth_status=json.loads(body)
    except ValueError:auth_status={}
    email_configured=code==200 and auth_status.get("email_login_available") is True
    check("email sign-in configured for actual user onboarding",
          email_configured, f"HTTP {code}; available={email_configured}")
    code,_,body=request(opener,base,"/.well-known/oauth-protected-resource/mcp")
    try:resource=json.loads(body)
    except ValueError:resource={}
    check("OAuth protected resource available",code==200 and resource.get("resource")==base+"/mcp",f"HTTP {code}")
    code,_,body=request(opener,base,"/.well-known/oauth-authorization-server")
    try:oauth=json.loads(body)
    except ValueError:oauth={}
    check("OAuth issuer and mix-up protection",code==200 and oauth.get("issuer")==base
        and oauth.get("authorization_response_iss_parameter_supported") is True,f"HTTP {code}")
    code,headers,_=request(opener,base,"/mcp",method="POST",data=json.dumps({
       "jsonrpc":"2.0","id":1,"method":"initialize","params":{
          "protocolVersion":"2025-06-18","capabilities":{},
          "clientInfo":{"name":"rolehint-preflight","version":"1"}}}).encode())
    challenge=next((value for name,value in headers.items() if name.lower()=="www-authenticate"),"")
    check("remote MCP rejects missing token",code==401 and "Bearer" in challenge,f"HTTP {code}")
    result={"target":base,"checks":checks,
            "http_preflight_ok":all(x["ok"] for x in checks),
            "email_login_configured":email_configured,
            "full_release_gate_passed":False,
            "unverified":["actual staging-volume data recovery after restart",
                          "real email delivery","actual Claude/ChatGPT account connection",
                          "real iPhone Safari"]}
    print(json.dumps(result,indent=2))
    if not result["http_preflight_ok"]:return 1
    print("HTTP PREVIEW PASS ONLY — full release still blocked until operational acceptance.")
    return 0

if __name__=="__main__":
    try:
        base=require_safe_target(os.environ.get("ROLEHINT_STAGING_URL",""))
        raise SystemExit(run(base))
    except (ValueError,URLError,RuntimeError,OSError) as exc:
        print("STAGING PREFLIGHT BLOCKED:",exc,file=sys.stderr)
        raise SystemExit(2)
