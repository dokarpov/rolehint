"""Read-only SQLite integrity inspection and safe per-file online backup.

Each SQLite online backup is consistent, but a set of independent databases
is NOT one atomic cross-file snapshot. This module does not run automatically.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

DATABASES = ("career_fit.db", "career_state.db", "product_state.db")


def _read_only(path: Path) -> sqlite3.Connection:
    path = path.resolve(strict=True)
    if not path.is_file() or path.suffix != ".db":
        raise ValueError("Expected an existing SQLite .db file")
    conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=15)
    conn.execute("PRAGMA busy_timeout=15000")
    return conn


def inspect_sqlite(path: str | Path) -> dict:
    """Inspect schema-level consistency; never return candidate data or secrets."""
    path = Path(path)
    with closing(_read_only(path)) as conn:
        status = conn.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_errors = len(conn.execute("PRAGMA foreign_key_check").fetchall())
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        evidence_entries = fts_entries = None
        if "user_evidence" in tables and "user_evidence_fts" in tables:
            evidence_entries = conn.execute(
                "SELECT COUNT(*) FROM user_evidence").fetchone()[0]
            fts_entries = conn.execute(
                "SELECT COUNT(*) FROM user_evidence_fts").fetchone()[0]
        return {
            "database": path.name,
            "integrity_ok": status == "ok",
            "foreign_key_errors": foreign_key_errors,
            "evidence_count": evidence_entries,
            "fts_count": fts_entries,
            # Count parity is a preliminary FTS check, NOT a full content audit.
            "fts_count_matches": evidence_entries == fts_entries
                if evidence_entries is not None else None,
            "schema_tables": len(tables),
            "journal_mode": conn.execute("PRAGMA journal_mode").fetchone()[0],
        }


def backup_sqlite(source: str | Path, destination: str | Path) -> dict:
    """Back up a live SQLite database safely; never overwrite existing backups."""
    source, destination = Path(source), Path(destination)
    if destination.exists():
        raise FileExistsError(f"Backup destination already exists: {destination}")
    if source.resolve() == destination.resolve():
        raise ValueError("Source and destination must differ")
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".sqlite-backup-", suffix=".db",
            dir=destination.parent, delete=False,
        ) as handle:
            tmp = Path(handle.name)
        os.chmod(tmp, 0o600)
        with closing(_read_only(source)) as src, closing(
            sqlite3.connect(str(tmp), timeout=15)
        ) as dst:
            src.backup(dst, pages=200, sleep=0.05)
        report = inspect_sqlite(tmp)
        if (not report["integrity_ok"] or report["foreign_key_errors"]
                or report["fts_count_matches"] is False):
            raise ValueError("Backup failed database integrity verification")
        hasher = hashlib.sha256()
        with tmp.open("rb") as saved:
            for chunk in iter(lambda: saved.read(1024 * 1024), b""):
                hasher.update(chunk)
        digest = hasher.hexdigest()
        os.replace(tmp, destination)
        tmp = None
        return {
            "database": destination.name,
            "sha256": digest,
            "size_bytes": destination.stat().st_size,
            "integrity": report,
        }
    finally:
        if tmp is not None and tmp.exists():
            tmp.unlink()


def backup_database_set(source_dir: str | Path, destination_dir: str | Path) -> dict:
    """Create three individually consistent backups; no cross-file atomicity."""
    source_dir, destination_dir = Path(source_dir), Path(destination_dir)
    if destination_dir.exists():
        raise FileExistsError("Destination must be a new directory")
    for name in DATABASES:
        if not (source_dir / name).is_file():
            raise FileNotFoundError(f"Missing source SQLite file: {name}")
    destination_dir.mkdir(parents=True, mode=0o700)
    results = [
        backup_sqlite(source_dir / name, destination_dir / name)
        for name in DATABASES
    ]
    manifest = {
        "source": "sqlite-online-backup",
        "atomic_across_files": False,
        "databases": [
            {key: value for key, value in item.items() if key != "integrity"}
            for item in results
        ],
    }
    target = destination_dir / "manifest.json"
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.chmod(target, 0o600)
    return manifest
