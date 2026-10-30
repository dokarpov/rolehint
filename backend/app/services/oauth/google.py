from __future__ import annotations
import os, secrets, time
from urllib.parse import urlencode
import httpx

AUTH="https://accounts.google.com/o/oauth2/v2/auth"
TOKEN="https://oauth2.googleapis.com/token"
SCOPES=[
 "openid","email",
 "https://www.googleapis.com/auth/gmail.readonly",
 "https://www.googleapis.com/auth/drive.readonly"
]

WORKSPACE_SCOPES=[
    "openid","email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events"
]

class GoogleOAuth:
    def __init__(self,client_id=None,client_secret=None,callback_url=None):
        self.client_id=client_id or os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret=client_secret or os.getenv("GOOGLE_CLIENT_SECRET")
        self.callback_url=callback_url or os.getenv("GOOGLE_OAUTH_CALLBACK_URL")
    def configured(self):
        return bool(self.client_id and self.client_secret and self.callback_url)
    def authorize_url(self,state,scopes=None):
        if not self.configured(): raise RuntimeError("Google OAuth is not configured")
        return AUTH+"?"+urlencode({
          "client_id":self.client_id,"redirect_uri":self.callback_url,
          "response_type":"code","scope":" ".join(scopes or SCOPES),
          "access_type":"offline","include_granted_scopes":"false","prompt":"consent",
          "state":state
        })
    async def exchange(self,code):
        async with httpx.AsyncClient(timeout=30) as c:
            r=await c.post(TOKEN,data={
              "client_id":self.client_id,"client_secret":self.client_secret,
              "code":code,"grant_type":"authorization_code","redirect_uri":self.callback_url
            });r.raise_for_status();return r.json()
    async def refresh(self,refresh_token):
        async with httpx.AsyncClient(timeout=30) as c:
            r=await c.post(TOKEN,data={
              "client_id":self.client_id,"client_secret":self.client_secret,
              "refresh_token":refresh_token,"grant_type":"refresh_token"
            });r.raise_for_status();return r.json()
