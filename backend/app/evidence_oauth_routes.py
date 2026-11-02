"""OAuth discovery, browser consent and token endpoints for Claude/ChatGPT."""
from __future__ import annotations
import html,json
from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import JSONResponse,HTMLResponse,RedirectResponse
from .evidence_oauth import OAuthServer,SCOPES

def create_routes(server:OAuthServer,require_user,check_origin):
    r=APIRouter(tags=["evidence-oauth"])

    @r.get("/.well-known/oauth-authorization-server")
    def metadata():
        return {"issuer":server.base,"authorization_endpoint":server.base+"/oauth/authorize",
          "token_endpoint":server.base+"/oauth/token","registration_endpoint":server.base+"/oauth/register",
          "response_types_supported":["code"],"grant_types_supported":["authorization_code","refresh_token"],
          "token_endpoint_auth_methods_supported":["none"],"code_challenge_methods_supported":["S256"],
          "scopes_supported":sorted(SCOPES),"authorization_response_iss_parameter_supported":True}

    @r.get("/.well-known/oauth-protected-resource")
    @r.get("/.well-known/oauth-protected-resource/mcp")
    def protected_resource():
        return {"resource":server.resource,"authorization_servers":[server.base],
                "scopes_supported":sorted(SCOPES),"bearer_methods_supported":["header"]}

    @r.post("/oauth/register")
    async def register(request:Request):
        if int(request.headers.get("content-length","0") or "0")>4096:
            raise HTTPException(413,"Registration too large")
        try:response=server.register(await request.json())
        except (ValueError,TypeError) as e:raise HTTPException(400,str(e)) from e
        return JSONResponse(response,status_code=201,headers={"Cache-Control":"no-store"})

    @r.get("/oauth/authorize")
    def authorize(request:Request):
        try:uid=require_user(request)
        except HTTPException:
            return HTMLResponse("""<!doctype html><html lang=en><meta name=viewport content='width=device-width,initial-scale=1'>
              <title>Sign in to RoleHint</title><main style='max-width:550px;margin:8vh auto;padding:20px;font:16px system-ui'>
              <h1>Sign in to RoleHint</h1><p>Open the Evidence Inbox and sign in, then reconnect Claude or ChatGPT.</p>
              <a href='/webapp/evidence.html'>Sign in to Evidence Inbox</a></main></html>""",status_code=401)
        try:req_id,scope=server.authorize(uid,request.cookies.get("rh_session",""),dict(request.query_params))
        except ValueError as e:raise HTTPException(400,str(e)) from e
        page="""<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>
          <title>Authorize RoleHint connection</title><main style='font:16px/1.55 system-ui;max-width:550px;margin:7vh auto;padding:20px'>
          <strong style='font-size:27px;letter-spacing:-2px'>rolehint</strong><h1>Connect your Evidence Inbox?</h1>
          <p>The assistant will access only the permissions below. It cannot approve evidence or apply to jobs.</p>
          <p><strong>Permissions:</strong> """+html.escape(", ".join(scope))+"""</p>
          <form method=post action='/oauth/authorize/consent'>
            <input type=hidden name=request_id value='"""+html.escape(req_id,quote=True)+"""'>
            <button style='padding:12px 18px;color:#fff;background:#111;border:0' name=decision value=approve>Allow</button>
            <button style='padding:12px 18px;color:#111;background:#eee;border:1px solid #999' name=decision value=deny>Deny</button>
          </form><p>Revoke access from Evidence Inbox. All candidate evidence stays private.</p></main></html>"""
        return HTMLResponse(page,headers={"Cache-Control":"no-store",
          "Content-Security-Policy":"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"})

    @r.post("/oauth/authorize/consent")
    async def consent(request:Request):
        check_origin(request);uid=require_user(request);form=await request.form()
        decision=str(form.get("decision",""))
        if decision not in ("approve","deny"):raise HTTPException(400,"Invalid choice")
        try:uri=server.consent(uid,request.cookies.get("rh_session",""),
                               str(form.get("request_id","")),decision=="approve")
        except ValueError as e:raise HTTPException(400,str(e)) from e
        return RedirectResponse(uri,status_code=303,
          headers={"Cache-Control":"no-store","Referrer-Policy":"no-referrer"})

    @r.post("/oauth/token")
    async def token(request:Request):
        data=dict(await request.form())
        try:return JSONResponse(server.token(data),headers={"Cache-Control":"no-store"})
        except ValueError as e:
            return JSONResponse({"error":"invalid_grant","error_description":str(e)},status_code=400,
                                headers={"Cache-Control":"no-store"})

    @r.get("/web-api/evidence/connections")
    def connections(request:Request):
        return JSONResponse({"connections":server.connections(require_user(request))},
                            headers={"Cache-Control":"private, no-store"})

    @r.delete("/web-api/evidence/connections/{cid}")
    def revoke(request:Request,cid:str):
        check_origin(request)
        return server.revoke(require_user(request),cid)

    return r
