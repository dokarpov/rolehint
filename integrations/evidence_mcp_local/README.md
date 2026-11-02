# RoleHint Evidence Collector — local Claude Desktop developer build

**Status: experimental code, not a published or installed extension.** The local tool is not connected to a RoleHint account or ChatGPT, and no cloud transfer occurs. Its SQLite inbox is private to the machine/user and is not encrypted end-to-end. Review before sharing any work.

The feature is the first EVC-0 slice of [the complete connector plan](../../docs/product/EVIDENCE_CONNECTORS_MCP_V1.md). It allows Claude Desktop/Claude Code to propose *unverified* experience evidence from selected conversation text or explicit text files in a permitted folder. It never scans the computer automatically.

## What works in the source

- Local MCP stdio server with `propose_evidence_from_text`, `propose_evidence_from_file`, `list_evidence_drafts`, `get_evidence_draft`, `discard_evidence_draft`.
- Strictly opt-in local folder; no automatic file/folder enumeration. Requires relative paths; denies dotfiles, traversal, outside-folder symlinks, unsupported/binary files, oversized excerpts and credential-like text.
- SQLite draft inbox: `needs-review`, `private`, local file permissions `0600`, deduplication and explicit discard.
- No RoleHint API requests, automatic external uploads, employee-claim verification or publication.

## Developer setup on Mac

1. Clone the RoleHint repository and switch to `feature/value-first-onboarding-20261021`.
2. Create a virtualenv and install the MCP SDK (Python 3.11+ recommended):

```sh
cd integrations/evidence_mcp_local
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

3. Choose the exact directory that Claude is allowed to use, for example a dedicated folder of **sanitized** project artifacts. Configure `ROLEHINT_ALLOWED_FOLDER` to its absolute path. Do not use `~`, `/`, the entire home folder or a cloud-synced credential directory.
4. Configure a local MCP stdio server in Claude Desktop's developer/local server configuration. Example *template*, replace all placeholder paths with actual absolute paths:

```json
{
  "mcpServers": {
    "rolehint-evidence-local": {
      "command": "/ABSOLUTE/PATH/rolehint/integrations/evidence_mcp_local/.venv/bin/python",
      "args": ["/ABSOLUTE/PATH/rolehint/integrations/evidence_mcp_local/server.py"],
      "env": {
        "ROLEHINT_ALLOWED_FOLDER": "/ABSOLUTE/PATH/SAFE-PROJECT-ARTIFACTS"
      }
    }
  }
}
```

A custom `.mcpb` single-click extension, installation test on actual Claude Desktop and a user-facing account import are **not included** in this slice. Do not label this a production-ready installer.

## Local checks

```sh
python3 -m unittest discover -s tests -p test_evidence_mcp_local.py -v
python3 -m py_compile integrations/evidence_mcp_local/inbox.py integrations/evidence_mcp_local/server.py
```

Run the unit tests from the repository root. Use the official [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) and actual Claude Desktop to verify tool discovery and first-use permissions before user installation.

## Trust boundaries

- Even a user-authored chat snippet cannot establish independently verified skills; all candidates remain `needs-review`.
- A model's tool call is not user approval for cloud publication. Nothing is uploaded in this slice.
- A local draft is not yet visible in RoleHint webapp. EVC-1 will add authenticated transfer and a review inbox, then EVC-2 remote MCP for Claude/ChatGPT where permitted.
- Treat local MCP servers as powerful programs launched on the computer. Install only your own reviewed source and inspect allowed-folder permissions.
