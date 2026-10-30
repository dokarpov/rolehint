"""Consent-first Google Workspace bridge for signed-in RoleHint web users.

Gmail: READ ONLY preview and explicitly confirmed per-job association.
Calendar: READ upcoming schedule; explicit approval to create one preparation event.
No email sending, auto-accept, auto-apply or covert calendar changes.
"""
from __future__ import annotations
import hashlib
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import httpx

API="https://www.googleapis.com/calendar/v3"
class CalendarConnector:
    def __init__(self,access_token,client=None):
        self.token=access_token
        self.client=client

    async def list_events(self,after,before):
        if not after.tzinfo or not before.tzinfo or before<=after:
            raise ValueError("Calendar date range must be timezone-aware")
        async with httpx.AsyncClient(timeout=20) if self.client is None else _NoClose(self.client) as c:
            r=await c.get(f"{API}/calendars/primary/events",headers={"Authorization":f"Bearer {self.token}"},
                params={"timeMin":after.isoformat(),"timeMax":before.isoformat(),
                        "singleEvents":"true","orderBy":"startTime","maxResults":100})
            r.raise_for_status()
            return [
                {"id":e.get("id"),"summary":e.get("summary",""),
                 "start":e.get("start",{}).get("dateTime") or e.get("start",{}).get("date"),
                 "end":e.get("end",{}).get("dateTime") or e.get("end",{}).get("date"),
                 "htmlLink":e.get("htmlLink")}
                for e in r.json().get("items",[])
            ]

    async def create_preparation(self,user_id,job_id,start_local,duration,summary,description,
                                 timezone_name="Europe/Madrid"):
        zone=ZoneInfo(timezone_name)
        try:
            start=datetime.fromisoformat(str(start_local).strip())
        except ValueError as exc:
            raise ValueError("Choose a valid event start time") from exc
        if not start.tzinfo:start=start.replace(tzinfo=zone)
        else:start=start.astimezone(zone)
        duration=int(duration)
        if not 15<=duration<=180:raise ValueError("Duration must be 15 to 180 minutes")
        if not 5<=len(summary.strip())<=140:raise ValueError("Enter a descriptive event title")
        if start<=datetime.now(timezone.utc)+timedelta(minutes=1):
            raise ValueError("Preparation event must start in the future")
        end=start+timedelta(minutes=duration)
        # This check is intentionally fail-closed: do not create if the calendar
        # cannot be inspected or an existing timed event overlaps.
        events=await self.list_events(start-timedelta(hours=2),end+timedelta(hours=2))
        for ev in events:
            try:
                a=datetime.fromisoformat(str(ev["start"]))
                b=datetime.fromisoformat(str(ev["end"]))
                if a.tzinfo and b.tzinfo and a<end and b>start:
                    raise ValueError("This time overlaps an existing calendar event")
            except (TypeError,AttributeError):
                continue
        event_id=hashlib.sha256(f"rolehint:{user_id}:{job_id}:{start.isoformat()}".encode()).hexdigest()[:32]
        payload={
            "id":event_id,
            "summary":summary.strip(),
            "description":str(description or "")[:1500],
            "start":{"dateTime":start.isoformat(),"timeZone":timezone_name},
            "end":{"dateTime":end.isoformat(),"timeZone":timezone_name},
            "reminders":{"useDefault":False,"overrides":[{"method":"popup","minutes":0}]},
            "extendedProperties":{"private":{"origin":"rolehint","job_id":job_id}}
        }
        async with httpx.AsyncClient(timeout=20) if self.client is None else _NoClose(self.client) as c:
            r=await c.post(f"{API}/calendars/primary/events",
                headers={"Authorization":f"Bearer {self.token}"},
                json=payload)
            if r.status_code==409:
                # One idempotency key per job/start. Fetch existing; do not duplicate.
                prev=await c.get(f"{API}/calendars/primary/events/{event_id}",
                    headers={"Authorization":f"Bearer {self.token}"})
                prev.raise_for_status()
                val=prev.json()
                return {"created":False,"id":event_id,"url":val.get("htmlLink")}
            r.raise_for_status()
            val=r.json()
            return {"created":True,"id":val.get("id"),"url":val.get("htmlLink")}

class _NoClose:
    def __init__(self,client):self.client=client
    async def __aenter__(self):return self.client
    async def __aexit__(self,*args):return False
