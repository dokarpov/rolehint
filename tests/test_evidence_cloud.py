"""Standalone SQLite evidence integrity tests with synthetic accounts."""
import sqlite3
import pytest
from app.evidence_cloud import EvidenceCloud,CandidateInput,ReviewInput,CandidateNotFound,Conflict

def source():
    return CandidateInput(claim="Built a real vacancy review flow",
      source_excerpt="The release log documents implementation and tests for the vacancy workflow.",
      source_ref="release-log.md",project="RoleHint",source_kind="document-selection")

@pytest.fixture
def cloud(tmp_path):
    db=tmp_path/"product_state.db"
    with sqlite3.connect(db) as c:
        c.executescript("""CREATE TABLE users(id TEXT PRIMARY KEY);
          INSERT INTO users VALUES('u1'),('u2');
          CREATE TABLE user_evidence(user_id TEXT,evidence_id TEXT,source_type TEXT,source_ref TEXT,
            title TEXT,claim TEXT,evidence TEXT,tags_json TEXT,status TEXT,direct INTEGER,
            visibility TEXT,ownership TEXT,metric TEXT,boundary TEXT,updated_at REAL,
            PRIMARY KEY(user_id,evidence_id));
          CREATE VIRTUAL TABLE user_evidence_fts USING fts5(
            user_id UNINDEXED,evidence_id UNINDEXED,title,claim,evidence,tags);""")
    return EvidenceCloud(db)

def test_deduplication_and_account_separation(cloud):
    one=cloud.propose("u1",[source()])[0]
    assert one["created"] and one["candidate"]["status"]=="needs-review"
    assert one["candidate"]["visibility"]=="private"
    assert not cloud.propose("u1",[source()])[0]["created"]
    assert cloud.list_candidates("u2")==[]
    assert cloud.propose("u2",[source()])[0]["created"]
    with pytest.raises(CandidateNotFound):
        cloud.review("u2",one["candidate"]["id"],ReviewInput(decision="approve"))

def test_human_approval_remains_unverified_and_deletion_clears_fts(cloud):
    cid=cloud.propose("u1",[source()])[0]["candidate"]["id"]
    result=cloud.review("u1",cid,ReviewInput(decision="approve"))
    assert result["status"]=="approved-self-reported"
    with cloud.connection() as c:
        record=c.execute("SELECT status,direct,visibility,ownership FROM user_evidence WHERE user_id='u1'").fetchone()
        assert tuple(record)==("needs-review",0,"private","self-reported")
        assert c.execute("SELECT COUNT(*) FROM user_evidence_fts").fetchone()[0]==1
    with pytest.raises(Conflict):
        cloud.review("u1",cid,ReviewInput(decision="approve"))
    cloud.delete("u1",cid)
    with cloud.connection() as c:
        assert c.execute("SELECT COUNT(*) FROM user_evidence").fetchone()[0]==0
        assert c.execute("SELECT COUNT(*) FROM user_evidence_fts").fetchone()[0]==0

def test_rejection_never_adds_verified_evidence(cloud):
    cid=cloud.propose("u1",[source()])[0]["candidate"]["id"]
    assert cloud.review("u1",cid,ReviewInput(decision="reject"))["status"]=="rejected"
    with cloud.connection() as c:
        assert c.execute("SELECT COUNT(*) FROM user_evidence").fetchone()[0]==0
