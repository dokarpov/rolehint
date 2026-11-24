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

def test_staging_is_woken_by_public_health_before_file_upload(monkeypatch, tmp_path):
    """Serverless staging cannot accept file uploads while asleep."""
    import urllib.request
    from scripts import export_railway_snapshots as migration

    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / "backup_data.py").write_text("pass\n")
    monkeypatch.setattr(migration, "ROOT", tmp_path)
    wakes = []

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None

    def open_health(url, timeout):
        wakes.append(url)
        return Response()

    def run(argv):
        if "upload" in argv:
            assert wakes == ["https://rolehint-staging-production.up.railway.app/health"]
            raise RuntimeError("test stopped before any remote write")
        return ""

    monkeypatch.setattr(urllib.request, "urlopen", open_health)
    monkeypatch.setattr(migration, "run", run)
    with pytest.raises(RuntimeError, match="test stopped"):
        migration.export_service("rolehint-staging", tmp_path)


def test_staging_wake_retries_initial_502_cold_boot(monkeypatch):
    import urllib.error
    import urllib.request
    from scripts import export_railway_snapshots as migration

    attempts = []
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None

    def open_health(url, timeout):
        attempts.append(url)
        if len(attempts) == 1:
            raise urllib.error.HTTPError(url, 502, "cold start", None, None)
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", open_health)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)
    migration.wake_staging()
    assert len(attempts) == 2
