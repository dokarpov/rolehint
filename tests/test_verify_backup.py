"""Offline unit tests for the private RoleHint backup verifier."""
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from backend.verify_backup import verify_snapshot


def _make_snapshot(tmp_path: Path):
    folder = tmp_path / "snapshot"
    folder.mkdir()
    db = folder / "product_state.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO sample(value) VALUES ('private-user-data')")
    payload = db.read_bytes()
    (folder / "manifest.json").write_text(json.dumps({
        "format": "RoleHint backup v1",
        "databases": [{"name": db.name, "bytes": len(payload),
                       "sha256": hashlib.sha256(payload).hexdigest(), "integrity": "ok"}],
    }))
    return folder, db


def test_valid_snapshot_with_restore(tmp_path):
    folder, _ = _make_snapshot(tmp_path)
    result = verify_snapshot(folder)
    assert result["status"] == "verified"
    assert result["restore_test"] is True
    assert result["non_db_material_still_requires_separate_backup"] is True
    assert "private-user-data" not in str(result)


def test_tampered_snapshot_refused(tmp_path):
    folder, db = _make_snapshot(tmp_path)
    db.write_bytes(db.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="Size differs"):
        verify_snapshot(folder)


def test_missing_database_refused(tmp_path):
    folder, db = _make_snapshot(tmp_path)
    db.unlink()
    with pytest.raises(ValueError, match="Database missing"):
        verify_snapshot(folder)


def test_traversal_refused(tmp_path):
    folder, _ = _make_snapshot(tmp_path)
    manifest = json.loads((folder / "manifest.json").read_text())
    manifest["databases"][0]["name"] = "../outside.db"
    (folder / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Unsafe"):
        verify_snapshot(folder)


def test_corrupt_manifest_refused(tmp_path):
    folder, _ = _make_snapshot(tmp_path)
    (folder / "manifest.json").write_text("broken")
    with pytest.raises(ValueError):
        verify_snapshot(folder)
