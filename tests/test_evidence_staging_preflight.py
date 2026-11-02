"""Negative security tests for the manual HTTPS staging preflight."""
from __future__ import annotations
import importlib.util
import io
import json
from pathlib import Path

import pytest

SCRIPT=Path(__file__).resolve().parents[1]/"scripts"/"evidence_staging_preflight.py"
spec=importlib.util.spec_from_file_location("evidence_staging_preflight",SCRIPT)
preflight=importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)

STAGING="https://rolehint-staging-production.up.railway.app"

@pytest.mark.parametrize("url",[
    "",
    "http://rolehint-staging-production.up.railway.app",
    "https://localhost",
    "http://127.0.0.1",
    "https://rolehint-api-worker-production.up.railway.app",
    "https://rolehint-other-production.up.railway.app",
    "https://rolehint-staging-production.up.railway.app.evil.example",
    "https://evil.example",
    "https://rolehint-staging-production.up.railway.app@evil.example",
    "https://rolehint-staging-production.up.railway.app/internal",
    "https://rolehint-staging-production.up.railway.app?redirect=/private",
    "https://rolehint-staging-production.up.railway.app:8080",
])
def test_preflight_does_not_access_production_or_private_hosts(url):
    with pytest.raises(ValueError):
        preflight.require_safe_target(url)

def test_realistic_isolated_preview_domain_allowed():
    assert preflight.require_safe_target(STAGING)==STAGING

def test_preflight_is_http_only_and_never_falsely_passes_full_release(monkeypatch,capsys):
    calls=[]
    def local_request(opener,base,path,method="GET",data=None):
        assert base==STAGING
        calls.append((path,method))
        if path=="/health":return 200,{},json.dumps({"ok":True})
        if path=="/webapp/evidence.html":return 200,{},"<title>Evidence Inbox · rolehint</title>"
        if path=="/web-api/evidence/candidates":
            return (403 if method=="POST" else 401),{},"{}"
        if path=="/.well-known/oauth-protected-resource/mcp":
            return 200,{},json.dumps({"resource":STAGING+"/mcp"})
        if path=="/.well-known/oauth-authorization-server":
            return 200,{},json.dumps({
                "issuer":STAGING,"authorization_response_iss_parameter_supported":True})
        if path=="/mcp":
            return 401,{"WWW-Authenticate":"Bearer resource_metadata="+STAGING},'{}'
        raise AssertionError("Unexpected HTTP request: "+path)
    monkeypatch.setattr(preflight,"request",local_request)
    assert preflight.run(STAGING)==0
    output=capsys.readouterr().out
    assert '"http_preflight_ok": true' in output
    assert '"full_release_gate_passed": false' in output
    assert len(calls)==7
    assert all(x[1]=="GET" for x in calls[:3])

def test_preflight_fails_when_guest_reads_private_evidence(monkeypatch,capsys):
    def leaked(opener,base,path,method="GET",data=None):
        if path=="/web-api/evidence/candidates" and method=="GET":
            return 200,{},"[]"
        if path=="/health":return 200,{},'{"ok":true}'
        if path=="/webapp/evidence.html":return 200,{},"Evidence Inbox"
        if path=="/web-api/evidence/candidates":return 403,{},"{}"
        if path=="/.well-known/oauth-protected-resource/mcp":
            return 200,{},json.dumps({"resource":STAGING+"/mcp"})
        if path=="/.well-known/oauth-authorization-server":
            return 200,{},json.dumps({
                "issuer":STAGING,"authorization_response_iss_parameter_supported":True})
        return 401,{"WWW-Authenticate":"Bearer"},'{}'
    monkeypatch.setattr(preflight,"request",leaked)
    assert preflight.run(STAGING)==1
    assert "FAIL guest cannot read evidence" in capsys.readouterr().out
