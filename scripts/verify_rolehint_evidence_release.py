#!/usr/bin/env python3
"""Repository-sourced release inventory. Never reads user credentials or data.

Use this before any staging/prod change; the JSON output is safe for GitHub
Actions artifacts and ties every feature file to an immutable repository SHA.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED: dict[str, tuple[str, ...]] = {
    "backend/app/evidence_cloud.py": ("class EvidenceCloud", "BEGIN IMMEDIATE", "self-reported"),
    "backend/app/evidence_oauth.py": ("class OAuthServer", "code_challenge_method", "stage_for_login", "hashed"),
    "backend/app/evidence_oauth_routes.py": ("/oauth/token", "/oauth/authorize", "continue_after_email"),
    "backend/app/evidence_remote_mcp.py": ("create_remote_server", "get_access_token", "evidence:propose"),
    "backend/app/web_evidence_api.py": ("init_routes", "check_origin", "/candidates"),
    "backend/app/web_identity.py": ("evidence_routes", "connect", "rh_session"),
    "backend/app/main.py": ('if os.getenv("CFA_REMOTE_MCP_ENABLED","0")=="1":', 'app.mount("/mcp",_remote_asgi)'),
    "backend/requirements.txt": ("mcp==2.3.0",),
    "webapp/evidence.html": ('class="wordmark"', "async function refresh()", "Approve as self-reported"),
    "webapp/index.html": ('href="/webapp/evidence.html"',),
    "tests/test_evidence_cloud.py": ("test_",),
    "tests/test_evidence_oauth.py": ("test_signed_out_handoff_restores_exact_oauth_request_once",),
    "tests/test_evidence_remote_mcp.py": ("test_complete_oauth_mcp_capture_review_and_revocation",),
    "tests/test_evidence_storage_recovery.py": ("test_backup_restore_preserves_user_provenance_tokens_and_fts", "test_approval_failure_rolls_back"),
    "site/qa-evidence.mjs": ("PASS Evidence Inbox mobile/browser", "guest"),
    "tests/test_evidence_staging_preflight.py": ("test_preflight_does_not_access_production",),
    "scripts/evidence_staging_preflight.py": ("FORBIDDEN", "full_release_gate_passed"),
    "scripts/verify_rolehint_evidence_release.py": ("def inventory()",),
    ".github/workflows/evidence-staging-preflight.yml": ("ROLEHINT_STAGING_URL",),
    "deploy/evidence-staging.env.example": ("CFA_REMOTE_MCP_ENABLED=1",),
    "deploy/README.md": ("Free plan resource provision limit exceeded",),

    "docs/product/EVIDENCE_WEB_RELEASE_2026-11-02.md": ("NOT deployed",),
    ".github/workflows/backend-release-gate.yml": ("test_evidence_remote_mcp.py",),
    ".github/workflows/release-qa.yml": ("node site/qa-evidence.mjs",),
}

def git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True)
    return result.stdout.strip()

def inventory() -> dict:
    sha = git("rev-parse", "HEAD")
    if len(sha) != 40:
        raise RuntimeError("Git checkout HEAD must be an exact 40-character SHA")
    dirty = git("status", "--porcelain", "--untracked-files=no")
    if dirty:
        raise RuntimeError("Tracked files contain uncommitted work: release artifact is not reproducible")
    files = {}
    for name, markers in REQUIRED.items():
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeError("Missing or symlinked required release file: " + name)
        content = path.read_bytes()
        readable = content.decode("utf-8")
        missing = [marker for marker in markers if marker not in readable]
        if missing:
            raise RuntimeError(f"Release contract missing in {name}: {missing!r}")
        # Git must track the exact file and its current contents.
        tracked = git("ls-files", "--error-unmatch", "--", name)
        if tracked != name:
            raise RuntimeError(f"Not tracked on GitHub: {name}")
        files[name] = {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
    return {
        "format": "rolehint-evidence-release-inventory",
        "format_version": 1,
        "git_sha": sha,
        "branch_or_ref": os.getenv("GITHUB_REF_NAME", git("branch", "--show-current")),
        "check_scope": "committed repository files only",
        "production_deployed": False,
        "railway_staging_verified": False,
        "all_required_paths_tracked": True,
        "files": files,
    }

def main() -> int:
    try:
        result = inventory()
        output = ROOT / "artifacts" / "rolehint-evidence-release-inventory.json"
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("PASS tracked release source inventory; commit:", result["git_sha"])
        print("Verified", len(result["files"]), "files; inventory:", output.relative_to(ROOT))
        return 0
    except (OSError, ValueError, UnicodeError, subprocess.CalledProcessError, RuntimeError) as error:
        print("BLOCKED release source inventory:", error, file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
