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
