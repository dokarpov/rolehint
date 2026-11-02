"""Remote Streamable HTTP MCP tools, authenticated with RoleHint OAuth bearer tokens."""
from urllib.parse import urlsplit
from pydantic import AnyHttpUrl
from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken,TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings
from .evidence_cloud import EvidenceCloud,CandidateInput
from .evidence_oauth import OAuthServer

class RoleHintVerifier(TokenVerifier):
    def __init__(self,oauth):self.oauth=oauth
    async def verify_token(self,token:str)->AccessToken|None:
        account=self.oauth.verify(token)
        if not account:return None
        return AccessToken(token=token,client_id=account["client_id"],
                           scopes=account["scopes"],subject=account["user_id"],
                           expires_at=int(account["expires_at"]))

def current_user(scope):
    token=get_access_token()
    if not token or not token.subject or scope not in token.scopes:
        raise PermissionError("Grant "+scope+" to this connector in RoleHint first")
    return token.subject

def create_remote_server(oauth:OAuthServer,inbox:EvidenceCloud):
    server=MCPServer("RoleHint Evidence",token_verifier=RoleHintVerifier(oauth),
      auth=AuthSettings(issuer_url=AnyHttpUrl(oauth.base),
                        resource_server_url=AnyHttpUrl(oauth.resource),required_scopes=[]))

    @server.tool()
    def list_evidence_candidates(status:str="needs-review",limit:int=20)->dict:
        """List private evidence draft METADATA (no excerpts). Requires evidence:read."""
        uid=current_user("evidence:read")
        found=inbox.list_candidates(uid,status=status or None,limit=min(max(1,limit),50))
        return {"candidates":[{"id":x["id"],"project":x["project"],"claim":x["claim"],
                               "status":x["status"],"source_kind":x["source_kind"]}
                              for x in found],"private":True}

    @server.tool()
    def get_evidence_candidate(candidate_id:str)->dict:
        """Open one previously saved private claim and source passage. Requires evidence:read."""
        uid=current_user("evidence:read")
        for x in inbox.list_candidates(uid,limit=100):
            if x["id"]==candidate_id:return x
        return {"error":"Evidence not found or not authorized"}

    @server.tool()
    def propose_evidence(claim:str,source_excerpt:str,project:str,source_ref:str,
                         source_kind:str="conversation-selection",
                         boundary:str="Not independently verified")->dict:
        """Propose one PRIVATE UNVERIFIED evidence item from user-selected source text.

        This tool cannot approve/verify/apply, access your computer or scan chats.
        Requires evidence:propose.
        """
        uid=current_user("evidence:propose")
        input=CandidateInput(claim=claim,source_excerpt=source_excerpt,project=project,
                             source_ref=source_ref,source_kind=source_kind,boundary=boundary)
        result=inbox.propose(uid,[input])[0]
        return {"id":result["candidate"]["id"],"created":result["created"],
                "status":result["candidate"]["status"],"visibility":"private",
                "verification_level":"unverified",
                "review_url":oauth.base+"/webapp/evidence.html"}

    @server.tool()
    def open_evidence_inbox()->dict:
        """Get the first-party URL where ONLY YOU can review claims. Requires evidence:read."""
        current_user("evidence:read")
        return {"url":oauth.base+"/webapp/evidence.html",
                "notice":"No AI claim becomes verified or recruiter-visible automatically."}

    hostname=urlsplit(oauth.base).netloc
    app=server.streamable_http_app(streamable_http_path="/",
      transport_security=TransportSecuritySettings(
        allowed_hosts=[hostname,hostname+":*"],
        allowed_origins=[oauth.base,"https://claude.ai","https://chatgpt.com"]))
    return server,app
