"""User-confirmed, offline export of selected RoleHint evidence drafts.

This does not use any network API, does not publish claims, and never upgrades
needs-review status. Import into an authenticated inbox is a separate release.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from inbox import get_draft


def build_bundle(draft_ids: list[str]) -> dict:
    if not 1 <= len(draft_ids) <= 50 or len(set(draft_ids)) != len(draft_ids):
        raise ValueError("Choose 1–50 distinct draft IDs")
    candidates = []
    for draft_id in draft_ids:
        if not isinstance(draft_id, str) or not draft_id.startswith("candidate_"):
            raise ValueError("Only explicit evidence candidate IDs are allowed")
        row = get_draft(draft_id)
        if row is None:
            raise LookupError(f"Draft not found: {draft_id}")
        if row["status"] != "needs-review" or row["visibility"] != "private":
            raise ValueError("Only private unverified candidates may be exported")
        candidates.append({
            "candidate_id": row["id"],
            "project": row["project"],
            "claim": row["claim"],
            "source_excerpt": row["evidence"],
            "source_kind": row["source_kind"],
            "source_ref": row["source_ref"],
            "captured_at": row["captured_at"],
            "boundary": row["boundary"],
            "status": "needs-review",
            "visibility": "private",
            "verification_level": "unverified",
        })
    return {
        "format": "rolehint-evidence-candidates",
        "format_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sync_status": "local-export-only",
        "candidates": candidates,
    }


def export_bundle(draft_ids: list[str], destination: str | Path, *, confirmed: bool = False) -> dict:
    """Write a fresh 0600 file; caller must affirm selected-data disclosure."""
    if not confirmed:
        raise PermissionError("Review each draft and confirm explicit offline export")
    bundle = build_bundle(draft_ids)
    path = Path(destination).expanduser()
    if path.suffix.lower() != ".json" or not path.is_absolute():
        raise ValueError("Choose an absolute path to a .json file")
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise FileNotFoundError("Export into an existing, ordinary directory")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as target:
            json.dump(bundle, target, ensure_ascii=False, indent=2)
            target.write("\n")
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return {
        "path": str(path),
        "count": len(bundle["candidates"]),
        "visibility": "private",
        "verification_level": "unverified",
        "uploaded": False,
    }
