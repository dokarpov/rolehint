"""Browser-only routes: signed-in account and first-party Origin for every mutation."""
from typing import Literal
from pydantic import BaseModel,ConfigDict
from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import JSONResponse
from .evidence_cloud import EvidenceCloud,CandidateBatch,ReviewInput,CandidateNotFound,Conflict

class EraseInboxInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    confirmation:Literal["DELETE MY EVIDENCE"]

def init_routes(db_path,require_user,check_origin):
    router=APIRouter(prefix="/evidence",tags=["evidence-inbox"])
    inbox=EvidenceCloud(db_path)
    def private(payload,status=200):
        result=JSONResponse(payload,status_code=status)
        result.headers["Cache-Control"]="private, no-store"
        result.headers["X-Content-Type-Options"]="nosniff"
        return result

    @router.get("/candidates")
    def candidates(request:Request,status:str|None=None,limit:int=100):
        uid=require_user(request)
        try:return private({"candidates":inbox.list_candidates(uid,status,limit)})
        except ValueError as e:raise HTTPException(422,str(e)) from e

    @router.post("/candidates")
    def propose(request:Request,payload:CandidateBatch):
        check_origin(request);uid=require_user(request)
        try:return private({"items":inbox.propose(uid,payload.candidates)},201)
        except ValueError as e:raise HTTPException(422,str(e)) from e

    @router.patch("/candidates/{candidate_id}")
    def review(request:Request,candidate_id:str,payload:ReviewInput):
        check_origin(request);uid=require_user(request)
        try:return private({"candidate":inbox.review(uid,candidate_id,payload)})
        except CandidateNotFound as e:raise HTTPException(404,"Evidence draft not found") from e
        except Conflict as e:raise HTTPException(409,str(e)) from e
        except ValueError as e:raise HTTPException(422,str(e)) from e

    @router.delete("/candidates")
    def erase_all_candidates(request:Request,payload:EraseInboxInput):
        check_origin(request);uid=require_user(request)
        # The caller must explicitly type the exact phrase. This erases only
        # Evidence Inbox data, never the user's account, CV, jobs or packs.
        return private(inbox.erase_inbox(uid))

    @router.delete("/candidates/{candidate_id}")
    def delete(request:Request,candidate_id:str):
        check_origin(request);uid=require_user(request)
        try:return private(inbox.delete(uid,candidate_id))
        except CandidateNotFound as e:raise HTTPException(404,"Evidence draft not found") from e
    return router
