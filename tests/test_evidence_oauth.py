"""OAuth code/PKCE, token rotation, audience and account isolation tests."""
import sqlite3,secrets
from urllib.parse import urlsplit,parse_qs
import pytest
from app.evidence_oauth import OAuthServer,pkce,OAuthRateLimit

@pytest.fixture
def oauth(tmp_path):
    db=tmp_path/"auth.db"
    with sqlite3.connect(db) as conn:
        conn.executescript("CREATE TABLE users(id TEXT PRIMARY KEY);INSERT INTO users VALUES('u1'),('u2');")
    return OAuthServer(db,"https://rolehint.example",allow_loopback=True)

def initial(oauth,cid):
    verifier=secrets.token_urlsafe(48)
    req,scopes=oauth.authorize("u1","browser-cookie",{
      "client_id":cid,"redirect_uri":"https://claude.ai/api/mcp/auth_callback",
      "response_type":"code","code_challenge_method":"S256","code_challenge":pkce(verifier),
      "resource":oauth.resource,"scope":"evidence:read evidence:propose","state":secrets.token_urlsafe(24)})
    assert set(scopes)=={"evidence:read","evidence:propose"}
    return req,verifier

def test_oauth_code_is_single_use_and_token_is_restricted(oauth):
    cid=oauth.register({"client_name":"Claude","redirect_uris":["https://claude.ai/api/mcp/auth_callback"]})["client_id"]
    req,verifier=initial(oauth,cid)
    with pytest.raises(ValueError):oauth.consent("u2","browser-cookie",req,True)
    with pytest.raises(ValueError):oauth.consent("u1","wrong-cookie",req,True)
    uri=oauth.consent("u1","browser-cookie",req,True)
    args=parse_qs(urlsplit(uri).query)
    assert args["iss"]==["https://rolehint.example"]
    token_input={"grant_type":"authorization_code","client_id":cid,
      "redirect_uri":"https://claude.ai/api/mcp/auth_callback","code":args["code"][0],
      "code_verifier":verifier,"resource":oauth.resource}
    token=oauth.token(token_input)
    assert oauth.verify(token["access_token"])["user_id"]=="u1"
    with pytest.raises(ValueError):oauth.token(token_input)
    refresh={"grant_type":"refresh_token","client_id":cid,
      "resource":oauth.resource,"refresh_token":token["refresh_token"]}
    new_token=oauth.token(refresh)
    with pytest.raises(ValueError):oauth.token(refresh)
    oauth.revoke("u1",cid)
    assert oauth.verify(new_token["access_token"]) is None

def test_registration_rejects_redirect_host_tricks(oauth):
    for url in ["https://evil.example/steal","https://claude.ai.evil.example/x",
        "http://claude.ai/x","https://chatgpt.com@evil.example/x",
        "https://claude.ai/callback#fragment","https://claude.ai/open-redirect",
        "https://chatgpt.com/not-a-callback","https://claude.ai/api/mcp/auth_callback?next=bad"]:
        with pytest.raises(ValueError):
            oauth.register({"redirect_uris":[url]})

def test_official_platform_callbacks_are_allowed(oauth):
    callbacks=["https://claude.ai/api/mcp/auth_callback",
               "https://claude.com/api/mcp/auth_callback",
               "https://chatgpt.com/connector_platform_oauth_redirect",
               "https://chatgpt.com/connector/oauth/callback_0123456789"]
    for uri in callbacks:
        result=oauth.register({"client_name":"AI connector","redirect_uris":[uri]})
        assert result["redirect_uris"]==[uri]


def test_signed_out_handoff_restores_exact_oauth_request_once(oauth):
    callback="https://claude.ai/api/mcp/auth_callback"
    client_id=oauth.register({"redirect_uris":[callback]})["client_id"]
    verifier=secrets.token_urlsafe(48)
    query={"client_id":client_id,"redirect_uri":callback,
        "response_type":"code","code_challenge_method":"S256",
        "code_challenge":pkce(verifier),"resource":oauth.resource,
        "scope":"evidence:read","state":secrets.token_urlsafe(24)}
    ticket=oauth.stage_for_login(query)
    assert oauth.pending_login(ticket)
    restored=oauth.resume_login("u1","browser-session",ticket)
    assert restored==query
    assert not oauth.pending_login(ticket)
    with pytest.raises(ValueError):
        oauth.resume_login("u1","browser-session",ticket)
    request_id,scope=oauth.authorize("u1","browser-session",restored)
    assert scope==["evidence:read"]
    url=oauth.consent("u1","browser-session",request_id,True)
    assert parse_qs(urlsplit(url).query)["state"]==[query["state"]]


def test_invalid_scope_and_wrong_audience_rejected(oauth):
    cid=oauth.register({"redirect_uris":["https://claude.ai/api/mcp/auth_callback"]})["client_id"]
    for scope,resource in [("evidence:admin",oauth.resource),("evidence:read","https://evil.example/mcp")]:
        with pytest.raises(ValueError):
            oauth.authorize("u1","cookie",{"client_id":cid,
             "redirect_uri":"https://claude.ai/api/mcp/auth_callback",
             "response_type":"code","code_challenge_method":"S256",
             "code_challenge":pkce(secrets.token_urlsafe(48)),
             "resource":resource,"scope":scope,"state":secrets.token_urlsafe(24)})


def test_oauth_registration_is_bounded_per_source(oauth):
    callback="https://claude.ai/api/mcp/auth_callback"
    for i in range(10):
        client=oauth.register({"redirect_uris":[callback],"client_name":"Connector"},
                              source="synthetic-ip-one")
        assert client["client_id"].startswith("rhclient_")
    with pytest.raises(OAuthRateLimit):
        oauth.register({"redirect_uris":[callback]},source="synthetic-ip-one")
    assert oauth.register({"redirect_uris":[callback]},
                          source="synthetic-ip-two")["client_id"].startswith("rhclient_")
    with pytest.raises(ValueError):
        oauth.register({"redirect_uris":[callback],
                        "token_endpoint_auth_method":"client_secret_basic"},
                       source="synthetic-ip-two")


def test_revocation_invalidates_unredeemed_codes_and_consent_requests(oauth):
    callback="https://claude.ai/api/mcp/auth_callback"
    cid=oauth.register({"redirect_uris":[callback]})["client_id"]
    request_id,verifier=initial(oauth,cid)
    oauth.revoke("u1",cid)
    with pytest.raises(ValueError):
        oauth.consent("u1","browser-cookie",request_id,True)
    pending,verifier=initial(oauth,cid)
    response=oauth.consent("u1","browser-cookie",pending,True)
    code=parse_qs(urlsplit(response).query)["code"][0]
    assert oauth.revoke("u1",cid)["revoked"]
    with pytest.raises(ValueError):
        oauth.token({"grant_type":"authorization_code","client_id":cid,
           "redirect_uri":callback,"code":code,"code_verifier":verifier,
           "resource":oauth.resource})

