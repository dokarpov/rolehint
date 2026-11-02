"""Smoke hosted MCP transport: no anonymous access, OAuth metadata and tools."""
from fastapi.testclient import TestClient
from app.main import app

def test_remote_mcp_requires_token_and_advertises_oauth():
    with TestClient(app,base_url="https://rolehint.example") as client:
        doc=client.get("/.well-known/oauth-protected-resource/mcp")
        assert doc.status_code==200,doc.text
        assert doc.json()["resource"]=="https://rolehint.example/mcp"
        payload={"jsonrpc":"2.0","id":1,"method":"initialize","params":{
            "protocolVersion":"2025-06-18","capabilities":{},
            "clientInfo":{"name":"acceptance-test","version":"1.0"}}}
        result=client.post("/mcp",json=payload,headers={"Accept":"application/json, text/event-stream"})
        assert result.status_code==401,result.text
        assert "WWW-Authenticate" in result.headers
