"""Offline tests for the no-overwrite RoleHint SQLite restore."""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.restore_snapshot import restore


def make_snapshot(tmp_path):
    snap = tmp_path / "source"
    snap.mkdir()
    db = snap / "product_state.db"
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE records(k TEXT)")
        c.execute("INSERT INTO records VALUES ('private')")
    data = db.read_bytes()
    (snap / "manifest.json").write_text(json.dumps({
        "format": "RoleHint backup v1",
        "databases": [{"name": db.name, "bytes": len(data),
                       "sha256": hashlib.sha256(data).hexdigest(), "integrity": "ok"}],
    }))
    return snap


def test_verify_only_does_not_create_directory(tmp_path):
    snap = make_snapshot(tmp_path)
    target = tmp_path / "data"
    result = restore(snap, target)
    assert result["status"] == "verified" and not result["destination_created"]
    assert not target.exists()


def test_verified_restore_and_no_overwrite(tmp_path):
    snap = make_snapshot(tmp_path)
    target = tmp_path / "data"
    assert restore(snap, target, apply=True)["destination_created"]
    assert (target / "product_state.db").exists()
    with sqlite3.connect(target / "product_state.db") as c:
        assert c.execute("SELECT k FROM records").fetchone()[0] == "private"
    with pytest.raises(FileExistsError):
        restore(snap, target, apply=True)


def test_corrupt_snapshot_refused(tmp_path):
    snap = make_snapshot(tmp_path)
    target = tmp_path / "data"
    (snap / "product_state.db").write_bytes(b"broken")
    with pytest.raises(ValueError):
        restore(snap, target, apply=True)
    assert not target.exists()


def test_symlink_destination_refused(tmp_path):
    snap = make_snapshot(tmp_path)
    target = tmp_path / "real"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError):
        restore(snap, link / "child", apply=True)
