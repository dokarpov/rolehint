import json

import pytest

from scripts.export_railway_snapshots import check_target, read_snapshot_location, ROOT


def test_parse_location_ignores_preamble():
    result = read_snapshot_location('Connected to Railway\\n' + json.dumps({
        "snapshot_dir": "/tmp/rolehint-export/20261111T160000Z", "count": 3}))
    assert result.endswith("20261111T160000Z")


def test_refuse_untrusted_location():
    with pytest.raises(ValueError):
        read_snapshot_location('{"snapshot_dir":"/app/data/snapshot"}')


def test_prevent_private_backups_in_public_repo():
    with pytest.raises(ValueError):
        check_target(ROOT / "rolehint-data")


def test_export_commands_pass_explicit_production_environment(monkeypatch, tmp_path):
    """Railway rejects --project without --environment; cover upload, ssh, download."""
    from scripts import export_railway_snapshots as migration

    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / "backup_data.py").write_text("pass\n")
    monkeypatch.setattr(migration, "ROOT", tmp_path)
    commands = []

    def fake_run(argv):
        commands.append(argv)
        if argv[1] == "ssh":
            return json.dumps({"snapshot_dir": "/tmp/rolehint-export/20261124T100000Z"})
        return ""

    monkeypatch.setattr(migration, "run", fake_run)
    with pytest.raises(RuntimeError, match="Expected exactly one manifest"):
        migration.export_service("rolehint-api-worker", tmp_path)

    assert len(commands) == 3
    for args in commands:
        assert args[args.index("-p") + 1] == "e48095fc-fb0f-4e59-bf34-d30418e5198f"
        assert args[args.index("-e") + 1] == "40688d3e-9562-44c7-8431-3ce9c9687601"
        assert args[args.index("-s") + 1] == "rolehint-api-worker"
