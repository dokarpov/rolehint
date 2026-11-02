"""Local reviewer/export tests. All data and directories are synthetic."""
from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integrations" / "evidence_mcp_local"))
from inbox import propose_text  # noqa: E402
from export import build_bundle, export_bundle  # noqa: E402
from review import main  # noqa: E402


class LocalExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {
            "ROLEHINT_LOCAL_INBOX": str(self.root / "inbox.db"),
        })
        self.env.start()
        self.first = propose_text(
            "Designed a job discovery prototype",
            "Documented ATS discovery tests and user feedback.",
            "selected conversation", "RoleHint",
        )["id"]
        self.second = propose_text(
            "Improved application review",
            "Source-backed manual application handoff.",
            "selected document", "RoleHint",
        )["id"]

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_export_is_private_unverified_no_network_and_non_overwriting(self):
        output = self.root / "candidates.json"
        with self.assertRaises(PermissionError):
            export_bundle([self.first], output)
        self.assertFalse(output.exists())
        exported = export_bundle([self.first, self.second], output, confirmed=True)
        self.assertFalse(exported["uploaded"])
        self.assertEqual(exported["count"], 2)
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        content = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(content["sync_status"], "local-export-only")
        self.assertEqual(len(content["candidates"]), 2)
        for entry in content["candidates"]:
            self.assertEqual(entry["status"], "needs-review")
            self.assertEqual(entry["verification_level"], "unverified")
            self.assertEqual(entry["visibility"], "private")
        with self.assertRaises(FileExistsError):
            export_bundle([self.first], output, confirmed=True)
        self.assertEqual(len(json.loads(output.read_text())["candidates"]), 2)

    def test_unknown_and_duplicate_candidates_fail_before_creating_file(self):
        with self.assertRaises(LookupError):
            build_bundle(["candidate_" + "0" * 24])
        with self.assertRaises(ValueError):
            build_bundle([self.first, self.first])
        output = self.root / "missing.json"
        with self.assertRaises(LookupError):
            export_bundle([self.first, "candidate_" + "0" * 24], output, confirmed=True)
        self.assertFalse(output.exists())

    def test_cli_requires_confirmation_and_exports_only_selected(self):
        file = self.root / "bundle.json"
        self.assertEqual(main(["export", self.first, "--to", str(file)]), 2)
        self.assertFalse(file.exists())
        self.assertEqual(main(["export", self.first, "--to", str(file), "--confirm"]), 0)
        self.assertEqual(len(json.loads(file.read_text())["candidates"]), 1)
        self.assertEqual(main(["discard", self.second]), 2)
        self.assertEqual(main(["discard", self.second, "--confirm"]), 0)


if __name__ == "__main__":
    unittest.main()
