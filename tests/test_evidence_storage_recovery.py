"""DB-0: replay a real evidence/OAuth lifecycle through SQLite backup and restart.

Everything uses synthetic data, a disposable directory and the same runtime
schema/tool classes used by hosted RoleHint. Never opens production databases.
"""
from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from app.evidence_cloud import EvidenceCloud, CandidateInput, ReviewInput, Conflict
from app.evidence_oauth import OAuthServer, pkce
from app.services.product_state.sqlite_integrity import inspect_sqlite, backup_sqlite


def seed_database(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript("""
        CREATE TABLE users(id TEXT PRIMARY KEY);
        INSERT INTO users VALUES('alice'),('bob');
        CREATE TABLE user_evidence(
          user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          evidence_id TEXT NOT NULL,
          source_type TEXT,source_ref TEXT,title TEXT,claim TEXT,evidence TEXT,
          tags_json TEXT,status TEXT,direct INTEGER,visibility TEXT,ownership TEXT,
          metric TEXT,boundary TEXT,updated_at REAL,
          PRIMARY KEY(user_id,evidence_id));
        CREATE VIRTUAL TABLE user_evidence_fts USING fts5(
          user_id UNINDEXED,evidence_id UNINDEXED,title,claim,evidence,tags);
        """)


def candidate() -> CandidateInput:
    return CandidateInput(
        project="RoleHint",
        claim="Implemented the evidence review workflow",
        source_kind="document-selection",
        source_ref="release-notes.md:L20-28",
        source_excerpt="Acceptance tests cover evidence review and user-scoped deletion.",
    )


def test_backup_restore_preserves_user_provenance_tokens_and_fts(tmp_path):
    source=tmp_path/"original"/"product_state.db"
    source.parent.mkdir()
    seed_database(source)
    inbox=EvidenceCloud(source)
    uid="alice"
    cid=inbox.propose(uid,[candidate()])[0]["candidate"]["id"]
    approved=inbox.review(uid,cid,ReviewInput(decision="approve"))
    assert approved["status"]=="approved-self-reported"

    oauth=OAuthServer(source,"https://rolehint.example")
    redirect="https://claude.ai/api/mcp/auth_callback"
    client=oauth.register({"client_name":"Claude","redirect_uris":[redirect]})["client_id"]
    verifier="v"*64
    request_id,scopes=oauth.authorize(uid,"browser-session",{
        "client_id":client,"redirect_uri":redirect,
        "response_type":"code","code_challenge_method":"S256",
        "code_challenge":pkce(verifier),"resource":oauth.resource,
        "scope":"evidence:read","state":"state_"+"a"*28,
    })
    assert scopes==["evidence:read"]
    signed=oauth.consent(uid,"browser-session",request_id,True)
    code=parse_qs(urlsplit(signed).query)["code"][0]
    token=oauth.token({"grant_type":"authorization_code","client_id":client,
        "code":code,"code_verifier":verifier,"redirect_uri":redirect,
        "resource":oauth.resource})
    assert oauth.verify(token["access_token"])["user_id"]==uid

    snapshot=tmp_path/"backup"/"product_state.db"
    result=backup_sqlite(source,snapshot)
    assert len(result["sha256"])==64
    integrity=inspect_sqlite(snapshot)
    assert integrity["integrity_ok"] and integrity["foreign_key_errors"]==0
    assert integrity["fts_count_matches"]

    # Simulate a completely different process opening only the restored DB.
    resumed=EvidenceCloud(snapshot)
    resumed_oauth=OAuthServer(snapshot,"https://rolehint.example")
    assert resumed.list_candidates("bob")==[]
    owned=resumed.get_candidate(uid,cid)
    assert owned["claim"]=="Implemented the evidence review workflow"
    assert owned["status"]=="approved-self-reported"
    assert resumed_oauth.verify(token["access_token"])["user_id"]==uid
    with sqlite3.connect(snapshot) as conn:
        matching=conn.execute("""
          SELECT e.evidence_id FROM user_evidence_fts f
          JOIN user_evidence e ON e.evidence_id=f.evidence_id AND e.user_id=f.user_id
          WHERE f.user_evidence_fts MATCH ? AND e.user_id=?
        """,("review",uid)).fetchall()
    assert len(matching)==1

    # Revocation and deletion persist through another independent backup/restart.
    assert resumed_oauth.revoke(uid,client)["revoked"]
    assert resumed_oauth.verify(token["access_token"]) is None
    assert resumed.delete(uid,cid)=={"deleted":True}
    final=tmp_path/"final"/"product_state.db"
    second=backup_sqlite(snapshot,final)
    assert second["integrity"]["fts_count_matches"]
    reopened=EvidenceCloud(final)
    assert reopened.list_candidates(uid)==[]
    assert OAuthServer(final,"https://rolehint.example").verify(token["access_token"]) is None
    with sqlite3.connect(final) as conn:
        assert conn.execute("SELECT COUNT(*) FROM user_evidence_fts").fetchone()[0]==0
        assert conn.execute("SELECT COUNT(*) FROM user_evidence").fetchone()[0]==0


def test_approval_failure_rolls_back_candidate_evidence_and_audit(tmp_path):
    path=tmp_path/"product_state.db"
    seed_database(path)
    inbox=EvidenceCloud(path)
    cid=inbox.propose("alice",[candidate()])[0]["candidate"]["id"]
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TABLE user_evidence_fts")
    with pytest.raises(sqlite3.OperationalError):
        inbox.review("alice",cid,ReviewInput(decision="approve"))
    assert inbox.get_candidate("alice",cid)["status"]=="needs-review"
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM user_evidence").fetchone()[0]==0
        assert conn.execute("SELECT COUNT(*) FROM evidence_candidate_audit WHERE event='approve'").fetchone()[0]==0


def test_concurrent_candidate_proposals_and_reviews_are_consistent(tmp_path):
    path=tmp_path/"product_state.db"
    seed_database(path)
    inbox=EvidenceCloud(path)
    def propose(_):
        return inbox.propose("alice",[candidate()])[0]
    with ThreadPoolExecutor(max_workers=8) as pool:
        result=list(pool.map(propose,range(16)))
    assert sum(item["created"] for item in result)==1
    assert len({item["candidate"]["id"] for item in result})==1
    cid=result[0]["candidate"]["id"]
    def review(_):
        try:
            inbox.review("alice",cid,ReviewInput(decision="approve"))
            return "approved"
        except Conflict:
            return "conflict"
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes=list(pool.map(review,range(12)))
    assert outcomes.count("approved")==1
    assert outcomes.count("conflict")==11
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM user_evidence").fetchone()[0]==1
        assert conn.execute("SELECT COUNT(*) FROM user_evidence_fts").fetchone()[0]==1
        assert conn.execute("SELECT COUNT(*) FROM evidence_candidate_audit WHERE event='approve'").fetchone()[0]==1
