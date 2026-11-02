"""EVC-0 protocol test: exercise real MCP tool discovery + calls in-process.

Uses official MCP Python SDK v2 Client/MCPServer, no network or Claude account.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp import Client

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integrations" / "evidence_mcp_local"))
from server import mcp  # noqa: E402


class MCPProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.allowed = self.root / "project"
        self.allowed.mkdir()
        (self.allowed / "README.md").write_text("Release evidence: user-tested vacancy flow.\n", encoding="utf-8")
        self.env = patch.dict(os.environ, {
            "ROLEHINT_ALLOWED_FOLDER": str(self.allowed),
            "ROLEHINT_LOCAL_INBOX": str(self.root / "local-inbox.db"),
        })
        self.env.start()

    async def asyncTearDown(self):
        self.env.stop()
        self.temp.cleanup()

    async def test_tool_discovery_capture_read_discard_and_scope(self):
        async with Client(mcp, raise_exceptions=True) as client:
            schema = await client.list_tools()
            names = {tool.name for tool in schema.tools}
            self.assertEqual(names, {
                "propose_evidence_from_text", "propose_evidence_from_file",
                "list_evidence_drafts", "get_evidence_draft", "discard_evidence_draft",
            })
            add = await client.call_tool("propose_evidence_from_file", {
                "relative_path": "README.md", "claim": "Validated vacancy discovery",
                "project": "RoleHint", "first_line": 1, "last_line": 1,
            })
            self.assertFalse(add.is_error)
            drafted = add.structured_content
            self.assertEqual(drafted["status"], "needs-review")
            candidate_id = drafted["id"]
            listed = await client.call_tool("list_evidence_drafts", {"limit": 10})
            self.assertFalse(listed.is_error)
            self.assertIn(candidate_id, str(listed.structured_content))
            read = await client.call_tool("get_evidence_draft", {"draft_id": candidate_id})
            self.assertFalse(read.is_error)
            self.assertEqual(read.structured_content["visibility"], "private")
            self.assertEqual(read.structured_content["source_kind"], "local-file")
            outside = await client.call_tool("propose_evidence_from_file", {
                "relative_path": "../private.txt", "claim": "Try forbidden path",
                "project": "RoleHint",
            })
            self.assertTrue(outside.is_error)
            deleted = await client.call_tool("discard_evidence_draft", {"draft_id": candidate_id})
            self.assertFalse(deleted.is_error)
            self.assertTrue(deleted.structured_content["deleted"])
            gone = await client.call_tool("get_evidence_draft", {"draft_id": candidate_id})
            self.assertFalse(gone.is_error)
            self.assertEqual(gone.structured_content["error"], "Draft not found")


if __name__ == "__main__":
    unittest.main()
