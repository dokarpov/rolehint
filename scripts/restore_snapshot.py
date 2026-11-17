#!/usr/bin/env python3
"""Verify a RoleHint SQLite snapshot and optionally restore it to a NEW private directory.

No Railway access, network, secrets, environment variables, or deploy actions.
Default is verification-only. --apply never overwrites an existing destination.
Non-SQLite private files and settings must be restored separately before startup.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.verify_backup import verify_snapshot  # noqa: E402


def target_path(path: Path) -> Path:
    target = path.expanduser().absolute()
    for part in (target, *target.parents):
        if part.is_symlink():
            raise ValueError("Refusing a symlink destination or ancestor")
    target = target.resolve()
    if target == ROOT or ROOT in target.parents:
        raise ValueError("Restored private data must be outside the public repository")
    if target.exists():
        raise FileExistsError("Destination already exists; refusing to overwrite it")
    return target


def restore(snapshot: Path, dest: Path, *, apply: bool = False) -> dict:
    snapshot = snapshot.expanduser().resolve(strict=True)
    verified = verify_snapshot(snapshot)
    target = target_path(dest)
    result = {"status": "verified", "database_count": len(verified["databases"]),
              "destination_created": False,
              "non_database_private_state_must_be_restored_separately": True}
    if not apply:
        return result
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".rolehint-restore-", dir=str(target.parent)))
    try:
        os.chmod(stage, 0o700)
        for name in [*verified["databases"], "manifest.json"]:
            shutil.copyfile(snapshot / name, stage / name)
            os.chmod(stage / name, 0o600)
        verify_snapshot(stage)
        if target.exists() or target.is_symlink():
            raise FileExistsError("Destination appeared during restore")
        stage.rename(target)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    result["destination_created"] = True
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, type=Path,
                        help="Folder containing manifest.json and verified SQLite snapshots")
    parser.add_argument("--destination", required=True, type=Path,
                        help="NEW private directory outside the Git repo, e.g. /srv/rolehint/data")
    parser.add_argument("--apply", action="store_true", help="Create the new destination")
    a = parser.parse_args()
    try:
        result = restore(a.snapshot, a.destination, apply=a.apply)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"RESTORE STOPPED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
