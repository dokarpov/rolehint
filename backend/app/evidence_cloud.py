"""User-scoped cloud Evidence Inbox with atomic human review and FTS deletion."""
from __future__ import annotations
import sqlite3, hashlib, json, time, uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA="""
CREATE TABLE IF NOT EXISTS evidence_candidates(
 id TEXT PRIMARY KEY,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 source_kind TEXT NOT NULL,source_ref TEXT NOT NULL,source_excerpt TEXT NOT NULL,
 project TEXT NOT NULL,claim TEXT NOT NULL,boundary TEXT NOT NULL,
 fingerprint TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN('needs-review','approved-self-reported','rejected')),
 visibility TEXT NOT NULL CHECK(visibility='private'),
 approved_evidence_id TEXT,created_at REAL NOT NULL,updated_at REAL NOT NULL,
 UNIQUE(user_id,fingerprint)
);
CREATE INDEX IF NOT EXISTS idx_evidence_candidates_user
 ON evidence_candidates(user_id,status,created_at DESC);
CREATE TABLE IF NOT EXISTS evidence_candidate_audit(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 candidate_id TEXT NOT NULL,event TEXT NOT NULL,created_at REAL NOT NULL
);
"""
class CandidateInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    claim:str=Field(min_length=5,max_length=600)
    source_excerpt:str=Field(min_length=8,max_length=8000)
    source_ref:str=Field(min_length=1,max_length=350)
    project:str=Field(min_length=1,max_length=120)
    source_kind:Literal["conversation-selection","conversation-export","document-selection",
                       "local-file","github","google-drive","other-selected-source"]="conversation-selection"
    boundary:str=Field(default="Selected material is not independent verification of work.",max_length=1000)

    @field_validator("claim","source_excerpt","source_ref","project")
    @classmethod
    def not_blank(cls,value:str)->str:
        result=value.strip()
        if not result:raise ValueError("Field cannot be blank")
        return result

class CandidateBatch(BaseModel):
    model_config=ConfigDict(extra="forbid")
    candidates:list[CandidateInput]=Field(min_length=1,max_length=5)

class ReviewInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    decision:Literal["approve","reject"]
    claim:str|None=Field(default=None,min_length=5,max_length=600)
    boundary:str|None=Field(default=None,max_length=1000)

class CandidateNotFound(Exception): pass
class Conflict(Exception): pass

class EvidenceCloud:
    def __init__(self,db_path:str|Path):
        self.path=str(db_path)
        with self.connection() as db:db.executescript(SCHEMA)

    @contextmanager
    def connection(self):
        db=sqlite3.connect(self.path,timeout=15,isolation_level=None)
        db.row_factory=sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=15000")
        try:yield db
        finally:db.close()

    @staticmethod
    def public(row):
        return {key:row[key] for key in
                ("id","source_kind","source_ref","source_excerpt","project","claim",
                 "boundary","status","visibility","approved_evidence_id","created_at","updated_at")}

    def list_candidates(self,uid,status=None,limit=100):
        if status is not None and status not in ("needs-review","approved-self-reported","rejected"):
            raise ValueError("Invalid status")
        if not 1<=limit<=100:raise ValueError("Invalid limit")
        query="SELECT * FROM evidence_candidates WHERE user_id=?"
        params=[uid]
        if status:query+=" AND status=?";params.append(status)
        query+=" ORDER BY created_at DESC,id DESC LIMIT ?";params.append(limit)
        with self.connection() as db:return [self.public(row) for row in db.execute(query,params)]

    def get_candidate(self,uid,cid):
        with self.connection() as db:
            row=db.execute("SELECT * FROM evidence_candidates WHERE user_id=? AND id=?",
                           (uid,cid)).fetchone()
            if row is None:raise CandidateNotFound()
            return self.public(row)

    def get_candidate(self,uid,cid):
        # Fetch by primary key AND owner: do not truncate access to the first
        # page of candidates, or expose another account's source text.
        with self.connection() as db:
            row=db.execute("SELECT * FROM evidence_candidates WHERE user_id=? AND id=?",
                           (uid,cid)).fetchone()
            if row is None:raise CandidateNotFound()
            return self.public(row)

    def propose(self,uid,candidates:list[CandidateInput]):
        if not 1<=len(candidates)<=5:raise ValueError("Submit 1–5 candidates")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                results=[];now=time.time()
                for item in candidates:
                    fingerprint=hashlib.sha256(json.dumps([
                        item.source_kind,item.source_ref,item.source_excerpt,
                        item.claim,item.project],ensure_ascii=False).encode()).hexdigest()
                    existing=db.execute("SELECT * FROM evidence_candidates WHERE user_id=? AND fingerprint=?",
                                        (uid,fingerprint)).fetchone()
                    if existing:
                        results.append({"created":False,"candidate":self.public(existing)})
                        continue
                    cid="eic_"+uuid.uuid4().hex
                    db.execute("""INSERT INTO evidence_candidates(
                        id,user_id,source_kind,source_ref,source_excerpt,project,claim,boundary,
                        fingerprint,status,visibility,created_at,updated_at)
                        VALUES(?,?,?,?,?,?,?,?,?,'needs-review','private',?,?)""",
                        (cid,uid,item.source_kind,item.source_ref,item.source_excerpt,item.project,
                         item.claim,item.boundary,fingerprint,now,now))
                    db.execute("INSERT INTO evidence_candidate_audit(user_id,candidate_id,event,created_at) VALUES(?,?,'proposed',?)",
                               (uid,cid,now))
                    row=db.execute("SELECT * FROM evidence_candidates WHERE id=?",(cid,)).fetchone()
                    results.append({"created":True,"candidate":self.public(row)})
                db.commit();return results
            except BaseException:db.rollback();raise

    def review(self,uid,cid,payload:ReviewInput):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row=db.execute("SELECT * FROM evidence_candidates WHERE user_id=? AND id=?",(uid,cid)).fetchone()
                if row is None:raise CandidateNotFound()
                if row["status"]!="needs-review":raise Conflict("Already reviewed")
                claim=(payload.claim if payload.claim is not None else row["claim"]).strip()
                boundary=payload.boundary if payload.boundary is not None else row["boundary"]
                if not 5<=len(claim)<=600:raise ValueError("Invalid claim length")
                now=time.time();eid=None
                if payload.decision=="approve":
                    eid="ev_"+cid
                    db.execute("""INSERT INTO user_evidence(
                        user_id,evidence_id,source_type,source_ref,title,claim,evidence,tags_json,
                        status,direct,visibility,ownership,metric,boundary,updated_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (uid,eid,row["source_kind"],"inbox:"+cid,row["project"],claim,row["source_excerpt"],
                         "[]","needs-review",0,"private","self-reported",None,
                         boundary or "Not independently verified",now))
                    db.execute("DELETE FROM user_evidence_fts WHERE user_id=? AND evidence_id=?",(uid,eid))
                    db.execute("""INSERT INTO user_evidence_fts(user_id,evidence_id,title,claim,evidence,tags)
                        VALUES(?,?,?,?,?,?)""",(uid,eid,row["project"],claim,row["source_excerpt"],""))
                    status="approved-self-reported"
                else:status="rejected"
                db.execute("""UPDATE evidence_candidates SET claim=?,boundary=?,status=?,approved_evidence_id=?,
                    updated_at=? WHERE user_id=? AND id=?""",(claim,boundary,status,eid,now,uid,cid))
                db.execute("INSERT INTO evidence_candidate_audit(user_id,candidate_id,event,created_at) VALUES(?,?,?,?)",
                           (uid,cid,payload.decision,now))
                db.commit()
                return self.public(db.execute("SELECT * FROM evidence_candidates WHERE id=?",(cid,)).fetchone())
            except BaseException:db.rollback();raise

    def delete(self,uid,cid):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row=db.execute("SELECT approved_evidence_id FROM evidence_candidates WHERE user_id=? AND id=?",
                               (uid,cid)).fetchone()
                if row is None:raise CandidateNotFound()
                eid=row["approved_evidence_id"]
                if eid:
                    db.execute("DELETE FROM user_evidence_fts WHERE user_id=? AND evidence_id=?",(uid,eid))
                    db.execute("DELETE FROM user_evidence WHERE user_id=? AND evidence_id=?",(uid,eid))
                db.execute("DELETE FROM evidence_candidates WHERE user_id=? AND id=?",(uid,cid))
                db.execute("INSERT INTO evidence_candidate_audit(user_id,candidate_id,event,created_at) VALUES(?,?,'deleted',?)",
                           (uid,cid,time.time()))
                db.commit();return {"deleted":True}
            except BaseException:db.rollback();raise
