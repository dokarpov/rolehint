"""Verify a downloaded RoleHint SQLite snapshot without exposing user data.

This verifies an offline copy only; it does NOT establish source/target cutover
or the presence of non-SQLite secrets and uploads.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

FORMATS = {".db", ".sqlite", ".sqlite3"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _integrity(path: Path) -> None:
    uri = path.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=10) as conn:
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise ValueError(f"SQLite integrity failed for {path.name}: {result}")


def verify_snapshot(folder: Path, restore_test: bool = True) -> dict:
    folder = folder.resolve(strict=True)
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError("Snapshot must be a directory")
    manifest_file = folder / "manifest.json"
    if not manifest_file.is_file() or manifest_file.is_symlink():
        raise ValueError("Snapshot manifest is missing or unsafe")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("format") != "RoleHint backup v1":
        raise ValueError("Unknown snapshot format")
    records = manifest.get("databases")
    if not isinstance(records, list) or not records:
        raise ValueError("No databases in snapshot")
    seen = set()
    for record in records:
        name = record.get("name")
        if not isinstance(name, str) or not name or name != Path(name).name or name in seen:
            raise ValueError("Unsafe or duplicate backup filename")
        if Path(name).suffix.lower() not in FORMATS:
            raise ValueError("Unexpected backup extension")
        seen.add(name)
        db_file = folder / name
        if not db_file.is_file() or db_file.is_symlink():
            raise ValueError(f"Database missing or unsafe: {name}")
        if db_file.stat().st_size != record.get("bytes"):
            raise ValueError(f"Size differs from manifest: {name}")
        if _sha256(db_file) != record.get("sha256"):
            raise ValueError(f"SHA-256 differs from manifest: {name}")
        _integrity(db_file)
        if restore_test:
            with tempfile.TemporaryDirectory(prefix="rolehint-restore-check-", dir=folder) as d:
                restored = Path(d) / name
                shutil.copy2(db_file, restored)
                _integrity(restored)
    return {"status": "verified", "databases": sorted(seen),
            "restore_test": restore_test,
            "non_db_material_still_requires_separate_backup": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="Snapshot folder containing manifest.json")
    parser.add_argument("--skip-restore-test", action="store_true")
    args = parser.parse_args()
    try:
        result = verify_snapshot(args.folder, not args.skip_restore_test)
    except (OSError, ValueError, sqlite3.Error, KeyError, TypeError) as exc:
        print(f"VERIFY FAILED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
