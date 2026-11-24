"""Mocked offline export tests. Never contacts Railway or user data."""
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch
import pytest

from scripts.export_railway_volumes_offline import (
    private_dir, verify_and_snapshot, export_volume, VOLUMES,
)


def fixture_raw(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    with sqlite3.connect(raw / "rolehint.db") as c:
        c.execute("CREATE TABLE sessions (id INTEGER, value TEXT)")
        c.execute("INSERT INTO sessions VALUES (1, 'private')")
    (raw / "local_secrets.json").write_text('{"never":"print"}')
    (raw / "uploads").mkdir()
    (raw / "uploads" / "private.txt").write_text("keep me")
    return raw


def test_snapshots_and_other_private_files_preserved(tmp_path):
    raw = fixture_raw(tmp_path)
    snap = tmp_path / "sqlite"
    out = verify_and_snapshot(raw, snap)
    assert out["status"] == "verified"
    assert out["sqlite_databases"] == 1
    assert (raw / "local_secrets.json").exists()
    assert (raw / "uploads" / "private.txt").exists()
    from backend.verify_backup import verify_snapshot
    assert verify_snapshot(snap)["status"] == "verified"


def test_refuse_missing_sqlite(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "other").write_text("hi")
    with pytest.raises(ValueError, match="No SQLite"):
        verify_and_snapshot(raw, tmp_path / "snap")


def test_refuse_nested_sqlite(tmp_path):
    raw = fixture_raw(tmp_path)
    (raw / "uploads" / "nested.db").write_bytes(b"test")
    with pytest.raises(ValueError, match="Nested SQLite"):
        verify_and_snapshot(raw, tmp_path / "snap")


def test_refuse_existing_destination(tmp_path):
    raw = fixture_raw(tmp_path)
    snap = tmp_path / "snap"
    verify_and_snapshot(raw, snap)
    with pytest.raises(FileExistsError):
        verify_and_snapshot(raw, snap)


def test_reject_repository_destination(tmp_path):
    from scripts.export_railway_volumes_offline import ROOT
    with pytest.raises(ValueError, match="outside"):
        private_dir(ROOT / "dangerous")


def test_railway_command_is_download_only(tmp_path):
    output = tmp_path / "backup"
    output.mkdir()
    captured = []
    def fake_run(cmd, **kwargs):
        captured.append(cmd)
        dest = Path(cmd[-1])
        with sqlite3.connect(dest / "rolehint.db") as c:
            c.execute("CREATE TABLE t(x INTEGER)")
        (dest / "secret").write_text("not printed")
    with patch("scripts.export_railway_volumes_offline.subprocess.run", side_effect=fake_run):
        result = export_volume("production", output)
    assert result["verified"]
    assert captured[0][:6] == [
        "railway", "volume", "files", "--volume", VOLUMES["production"], "download"
    ]
    assert "deploy" not in captured[0] and "delete" not in captured[0]
