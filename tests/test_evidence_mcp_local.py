"""Privacy and filesystem tests for the local-only RoleHint Claude MCP inbox.

No MCP SDK or network required for the evidence-storage tests.
"""
from __future__ import annotations

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       "integrations" / "evidence_mcp_local"))
from inbox import (  # noqa: E402
    propose_text, propose_file, list_allowed_files, list_drafts, get_draft, discard_draft,
)


class LocalEvidenceInboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.allowed = self.root / "allowed"
        self.allowed.mkdir()
        self.env = patch.dict(os.environ, {
            "ROLEHINT_ALLOWED_FOLDER": str(self.allowed),
            "ROLEHINT_LOCAL_INBOX": str(self.root / "inbox" / "drafts.sqlite3"),
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_selected_text_is_local_private_unverified_and_deduplicated(self):
        args = ("Shipped the product flow",
                "Product release PR reviewed with user testing and issue tracker.",
                "selected chat", "RoleHint")
        first = propose_text(*args)
        self.assertTrue(first["created"])
        self.assertEqual(first["status"], "needs-review")
        self.assertEqual(first["visibility"], "private")
        self.assertEqual(first["stored"], "local-only")
        again = propose_text(*args)
        self.assertFalse(again["created"])
        self.assertEqual(first["id"], again["id"])
        self.assertEqual(len(list_drafts()), 1)
        draft = get_draft(first["id"])
        self.assertEqual(draft["status"], "needs-review")
        self.assertIn("not independently verified", draft["boundary"])
        self.assertFalse(stat.S_IMODE(
            (self.root / "inbox" / "drafts.sqlite3").stat().st_mode) & 0o077)
        self.assertTrue(discard_draft(first["id"])["deleted"])
        self.assertIsNone(get_draft(first["id"]))

    def test_files_are_read_only_from_explicit_allowed_folder(self):
        (self.allowed / "readme.md").write_text(
            "Release notes:\nImplemented vacancy search and manual review.\n",
            encoding="utf-8")
        item = propose_file("readme.md", "Built a real vacancy workflow",
                            "RoleHint", 2, 2)
        draft = get_draft(item["id"])
        self.assertIn("Implemented vacancy search", draft["evidence"])
        self.assertIn("readme.md#L2-L2", draft["source_ref"])
        self.assertEqual(draft["status"], "needs-review")
        self.assertEqual(draft["source_kind"], "local-file")

    def test_no_access_to_parent_symlink_hidden_or_unlisted_files(self):
        (self.root / "private.txt").write_text("Very private user secret", encoding="utf-8")
        (self.allowed / ".env").write_text("TOKEN=secret", encoding="utf-8")
        (self.allowed / "link.txt").symlink_to(self.root / "private.txt")
        for relative in ("../private.txt", "/etc/passwd", ".env", "link.txt"):
            with self.subTest(relative=relative), self.assertRaises(PermissionError):
                propose_file(relative, "Read private data")
        os.environ["ROLEHINT_ALLOWED_FOLDER"] = str(Path.home())
        with self.assertRaises(PermissionError):
            propose_file("Documents/file.md", "No home directory scanning")
        os.environ.pop("ROLEHINT_ALLOWED_FOLDER")
        with self.assertRaises(PermissionError):
            propose_file("readme.md", "No implicit home access")

    def test_explicit_file_browser_lists_one_folder_without_reading_or_following_symlinks(self):
        (self.allowed / "README.md").write_text("Approved overview", encoding="utf-8")
        (self.allowed / "private.json").write_text("private content", encoding="utf-8")
        (self.allowed / ".env").write_text("hidden", encoding="utf-8")
        nested = self.allowed / "src"
        nested.mkdir()
        (nested / "design.md").write_text("Nested project plan", encoding="utf-8")
        (self.allowed / "outside.md").symlink_to(self.root / "secret.md")
        (self.root / "secret.md").write_text("secret", encoding="utf-8")
        files = list_allowed_files()
        names = [x["relative_path"] for x in files["entries"]]
        self.assertIn("README.md", names)
        self.assertIn("src", names)
        self.assertNotIn("src/design.md", names)
        self.assertNotIn(".env", names)
        self.assertNotIn("outside.md", names)
        self.assertFalse(files["recursive"])
        self.assertFalse(files["contents_read"])
        detail = list_allowed_files("src")
        self.assertEqual(detail["entries"][0]["relative_path"], "src/design.md")
        for bad in ("../", "/etc", ".git", "outside.md"):
            with self.subTest(bad=bad), self.assertRaises((PermissionError, ValueError)):
                list_allowed_files(bad)
        # An internal symlink may also bypass a forbidden directory.
        (self.allowed / ".private").mkdir()
        (self.allowed / ".private" / "notes.md").write_text("private", encoding="utf-8")
        (self.allowed / "alias").symlink_to(self.allowed / ".private", target_is_directory=True)
        with self.assertRaises(PermissionError):
            propose_file("alias/notes.md", "Hidden notes")

    def test_possible_credentials_and_oversized_selection_are_rejected(self):
        with self.assertRaises(ValueError):
            propose_text("Found token", "api_key='0123456789abcdef'", "chat")
        (self.allowed / "credentials.txt").write_text(
            "-----BEGIN PRIVATE KEY-----\nsecret\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            propose_file("credentials.txt", "Imported sensitive project material")
        (self.allowed / "readme.md").write_text(
            "One line of evidence", encoding="utf-8")
        with self.assertRaises(ValueError):
            propose_file("readme.md", "Attempt to read excessive lines", first_line=1, last_line=200)


if __name__ == "__main__":
    unittest.main()
