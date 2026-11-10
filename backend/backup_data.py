"""Produce verified SQLite snapshots on the mounted RoleHint volume.

Run inside the original service. Never commit snapshots, user CVs, or secrets.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

SUFFIXES = {".db", ".sqlite", ".sqlite3"}

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def snapshot(data_dir: Path, output_base: Path | None = None) -> dict:
    data_dir = data_dir.resolve(strict=True)
    if not data_dir.is_dir():
        raise ValueError("CFA_DATA_DIR is not a directory")
    output_base = (output_base or data_dir / "backups").resolve()
    target = output_base / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target.mkdir(parents=True, exist_ok=False, mode=0o700)
    os.chmod(target, 0o700)
    dbs = [p for p in sorted(data_dir.iterdir())
           if p.is_file() and not p.is_symlink() and p.suffix.lower() in SUFFIXES]
    if not dbs:
        raise RuntimeError("No SQLite databases on this volume. Check mount before migration.")
    backups = []
    for source in dbs:
        if source.stat().st_size == 0:
            raise RuntimeError(f"Zero-length DB: {source.name}")
        output = target / source.name
        source_conn = sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
        output_conn = sqlite3.connect(str(output))
        try:
            source_conn.backup(output_conn, pages=100, sleep=0.05)
            integrity = output_conn.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise RuntimeError(f"Invalid SQLite backup {source.name}: {integrity}")
        finally:
            output_conn.close()
            source_conn.close()
        os.chmod(output, 0o600)
        backups.append({"name": source.name, "bytes": output.stat().st_size,
                        "sha256": sha256(output), "integrity": "ok"})
    non_db = [p.name for p in sorted(data_dir.iterdir())
              if p.is_file() and p.suffix.lower() not in SUFFIXES]
    manifest = {
        "format": "RoleHint backup v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "databases": backups,
        "other_top_level_files_NOT_backed_up": non_db,
        "warning": "Copy local_secrets.json and other non-DB private files separately to encrypted local storage. NEVER commit production backups."
    }
    target.joinpath("manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.chmod(target / "manifest.json", 0o600)
    return {"snapshot_dir": str(target), "count": len(backups),
            "names": [r["name"] for r in backups], "non_db_files": len(non_db)}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(os.getenv("CFA_DATA_DIR", "/app/data")))
    parser.add_argument("--output-base", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(snapshot(args.data_dir, args.output_base), indent=2))
        return 0
    except Exception as exc:
        print(f"BACKUP FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
