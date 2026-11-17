#!/usr/bin/env python3
"""Offline-first, non-destructive export of RoleHint's two Railway volumes.

Requires authenticated Railway CLI on the OWNER'S computer. Source services
must be stopped: a raw directory download isn't an atomic snapshot of live SQLite.
Downloads the COMPLETE volume tree including non-DB files to private storage,
then produces separately verified SQLite backups for restoration.
Never upload private data or credentials to GitHub, chat or a public VM.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.verify_backup import verify_snapshot  # noqa: E402

VOLUMES = {
    "production": "7035a583-3c98-48db-9ce6-4fb2258ee1f6",
    "staging": "0d78adb0-26cb-40fb-a425-dc05e594836a",
}
EXTENSIONS = {".db", ".sqlite", ".sqlite3"}


def private_dir(path: Path) -> Path:
    path = path.expanduser().absolute()
    for p in (path, *path.parents):
        if p.is_symlink():
            raise ValueError("Refusing destination with symlink in its path")
    path = path.resolve()
    if path == ROOT or ROOT in path.parents:
        raise ValueError("Private exports must be outside the public repository")
    if path.exists():
        if not path.is_dir():
            raise ValueError("Private destination is not a directory")
        info = path.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("Existing destination must belong to user and have private permissions")
    else:
        path.mkdir(parents=True, exist_ok=False, mode=0o700)
        os.chmod(path, 0o700)
    return path


def checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_and_snapshot(raw: Path, target: Path) -> dict:
    """Manifest of ALL files plus SQLite snapshots. Never silently drop nested DBs."""
    raw = raw.resolve(strict=True)
    if not raw.is_dir():
        raise ValueError("Raw download directory missing")
    if target.exists():
        raise FileExistsError("Refusing to replace an existing SQLite snapshot")
    all_paths = sorted(raw.rglob("*"))
    if any(p.is_symlink() for p in all_paths):
        raise ValueError("Symlink in downloaded volume; inspect manually")
    files = [p for p in all_paths if p.is_file()]
    dbs = [p for p in files if p.suffix.lower() in EXTENSIONS]
    if not dbs:
        raise ValueError("No SQLite databases detected; export cannot be accepted")
    if any(p.parent != raw for p in dbs):
        raise ValueError("Nested SQLite databases detected; manual restore mapping needed")
    names = [p.name for p in dbs]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate database filename")
    target.mkdir(mode=0o700, parents=True)
    records = []
    for db in dbs:
        if db.stat().st_size == 0:
            raise ValueError("Zero-length SQLite database; investigate source")
        snap = target / db.name
        with sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True, timeout=30) as original:
            with sqlite3.connect(snap) as copy:
                original.backup(copy, pages=100, sleep=0.05)
                if copy.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("SQLite backup failed integrity check")
        os.chmod(snap, 0o600)
        records.append({"name": db.name, "bytes": snap.stat().st_size,
                        "sha256": checksum(snap), "integrity": "ok"})
    (target / "manifest.json").write_text(json.dumps({
        "format": "RoleHint backup v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "databases": records,
        "warning": "Non-DB material must be restored from separate PRIVATE raw volume export",
    }, indent=2), encoding="utf-8")
    os.chmod(target / "manifest.json", 0o600)
    verify_snapshot(target)
    return {"status": "verified", "sqlite_databases": len(records),
            "raw_files": len(files), "raw_file_hashes": [
                {"path": str(p.relative_to(raw)), "bytes": p.stat().st_size,
                 "sha256": checksum(p)} for p in files]}


def export_volume(service: str, destination: Path) -> dict:
    name = f"rolehint-{service}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    base = destination / name
    base.mkdir(mode=0o700, exist_ok=False)
    raw = base / "raw"
    raw.mkdir(mode=0o700)
    # Official Railway volume CLI. Access to offline volumes must be verified
    # with the owner's real CLI session. No deploy/restart/overwrite commands.
    cmd = ["railway", "volume", "files", "--volume", VOLUMES[service],
           "download", "/", str(raw)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError("Railway volume download failed; existing data is unchanged") from e
    for p in raw.rglob("*"):
        if p.is_symlink():
            raise ValueError("Symlink encountered; inspect downloaded private backup")
        os.chmod(p, 0o700 if p.is_dir() else 0o600)
    report = verify_and_snapshot(raw, base / "sqlite")
    report["source"] = service
    report["volume_id"] = VOLUMES[service]
    (base / "private-export-manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    os.chmod(base / "private-export-manifest.json", 0o600)
    return {"source": service, "verified": True,
            "sqlite_databases": report["sqlite_databases"],
            "complete_raw_volume_download": True,
            "private_files_remain_outside_repo": True}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--destination", type=Path, required=True,
                   help="Encrypted owner-controlled directory OUTSIDE the repo")
    p.add_argument("--service", choices=["production", "staging", "both"], default="both")
    a = p.parse_args()
    if shutil.which("railway") is None:
        p.error("Railway CLI required. Install it and authenticate with railway login.")
    try:
        dest = private_dir(a.destination)
        requested = list(VOLUMES) if a.service == "both" else [a.service]
        for service in requested:
            result = export_volume(service, dest)
            print(json.dumps(result, sort_keys=True))
    except (OSError, sqlite3.Error, ValueError, RuntimeError):
        print("EXPORT STOPPED: check private destination and Railway CLI", file=sys.stderr)
        return 2
    print("Export is local only. Preserve ALL raw files and keys; verify target before cutover.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
