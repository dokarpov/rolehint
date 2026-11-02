"""Hosted MCP: auth discovery and complete OAuth + private draft lifecycle.

Runs against disposable CI database only. No Claude/ChatGPT account required.
"""
from __future__ import annotations
import hashlib
import re
import secrets
import time
import uuid
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient
from app.main import app, product
from app.evidence_oauth import pkce

BASE="https://rolehint.example"
MCP_HEADERS={"Accept":"application/json, text/event-stream",
             "Content-Type":"application/json",
             "MCP-Protocol-Version":"2025-06-18"}

def init_payload():
    return {"jsonrpc":"2.0","id":1,"method":"initialize","params":{
        "protocolVersion":"2025-06-18","capabilities":{},
        "clientInfo":{"name":"rolehint-ci-integration","version":"1.0"}}}

def _browser_user(client):
    uid="web_evidence_ci_"+uuid.uuid4().hex
    now=time.time()
    product.conn.execute("""INSERT INTO users
      (id,telegram_user_id,first_name,username,created_at,last_seen)
      VALUES(?,NULL,NULL,NULL,?,?)""",(uid,now,now))
    cookie=secrets.token_urlsafe(48)
    product.conn.execute("INSERT INTO web_sessions VALUES(?,?,?,?)",
                         (hashlib.sha256(cookie.encode()).hexdigest(),uid,now+900,now))
    product.conn.commit()
    client.cookies.set("rh_session",cookie)
    return uid

def _get_access(client,scope):
    callback="https://claude.ai/api/mcp/auth_callback"
    registration=client.post("/oauth/register",json={
        "client_name":"RoleHint CI OAuth client",
        "redirect_uris":[callback],"token_endpoint_auth_method":"none"})
    assert registration.status_code==201,registration.text
    client_id=registration.json()["client_id"]
    verifier=secrets.token_urlsafe(48)
    query={"client_id":client_id,"redirect_uri":callback,"response_type":"code",
      "code_challenge_method":"S256","code_challenge":pkce(verifier),
      "resource":BASE+"/mcp","scope":scope,"state":secrets.token_urlsafe(20)}
    authorization=client.get("/oauth/authorize",params=query)
    assert authorization.status_code==200,authorization.text
    match=re.search(r'name=request_id value=[\'"]([^\'"]+)',authorization.text)
    assert match,authorization.text[:350]
    consent=client.post("/oauth/authorize/consent",headers={"Origin":BASE},
      data={"request_id":match.group(1),"decision":"approve"},follow_redirects=False)
    assert consent.status_code==303,consent.text
    returned=parse_qs(urlsplit(consent.headers["location"]).query)
    code=returned["code"][0]
    assert returned["state"]==[query["state"]]
    token=client.post("/oauth/token",data={
      "grant_type":"authorization_code","client_id":client_id,
      "redirect_uri":callback,"code":code,"code_verifier":verifier,
      "resource":BASE+"/mcp"})
    assert token.status_code==200,token.text
    assert set(token.json()["scope"].split())==set(scope.split())
    replay=client.post("/oauth/token",data={
      "grant_type":"authorization_code","client_id":client_id,
      "redirect_uri":callback,"code":code,"code_verifier":verifier,
      "resource":BASE+"/mcp"})
    assert replay.status_code==400
    return client_id,token.json()["access_token"]

def _rpc(client,token,body,session=None):
    headers={**MCP_HEADERS,"Authorization":"Bearer "+token}
    if session:headers["Mcp-Session-Id"]=session
    response=client.post("/mcp",json=body,headers=headers)
    return response

def test_complete_oauth_mcp_capture_review_and_revocation():
    # The official MCP session manager is single-lifespan. Exercise the
    # entire unauthenticated→consent→tool→revocation journey in one TestClient.
    with TestClient(app,base_url=BASE) as client:
        doc=client.get("/.well-known/oauth-protected-resource/mcp")
        assert doc.status_code==200,doc.text
        assert doc.json()["resource"]==BASE+"/mcp"
        no_token=client.post("/mcp",json=init_payload(),headers=MCP_HEADERS)
        assert no_token.status_code==401,no_token.text
        assert "WWW-Authenticate" in no_token.headers
        _browser_user(client)
        client_id,access=_get_access(client,"evidence:read evidence:propose")
        init=_rpc(client,access,init_payload())
        assert init.status_code==200,init.text[:500]
        session=init.headers.get("mcp-session-id")
        assert session,"MCP session ID not returned"
        notification=_rpc(client,access,{"jsonrpc":"2.0","method":"notifications/initialized"},session)
        assert notification.status_code in (200,202,204),notification.text[:350]
        tools=_rpc(client,access,{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}},session)
        assert tools.status_code==200,tools.text[:700]
        assert "propose_evidence" in tools.text
        attempt=_rpc(client,access,{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{
          "name":"propose_evidence","arguments":{
           "claim":"Delivered the vacancy verification workflow",
           "source_excerpt":"Verified job links and acceptance tests were recorded in the release review.",
           "project":"RoleHint","source_ref":"release-acceptance.md",
           "source_kind":"document-selection"}}},session)
        assert attempt.status_code==200,attempt.text[:700]
        assert "needs-review" in attempt.text
        listing=client.get("/web-api/evidence/candidates")
        assert listing.status_code==200,listing.text
        rows=listing.json()["candidates"]
        assert any("vacancy verification" in x["claim"] for x in rows)
        item=next(x for x in rows if "vacancy verification" in x["claim"])
        assert item["status"]=="needs-review"
        assert client.delete("/web-api/evidence/connections/"+client_id,
                             headers={"Origin":BASE}).json()["revoked"] is True
        blocked=_rpc(client,access,{"jsonrpc":"2.0","id":4,"method":"tools/list","params":{}},session)
        assert blocked.status_code==401,blocked.text[:350]
