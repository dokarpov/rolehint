# RoleHint Evidence Collector — Claude Desktop local connector

**Status: developer preview, not installed or connected to production.** This collects only selected chat text or the specific source-file lines requested from an explicitly approved project folder. Private drafts remain on your computer, unverified. No cloud sync or automatic scans.

See [full connector contract](../../docs/product/EVIDENCE_CONNECTORS_MCP_V1.md). EVC-1 (RoleHint account import) and EVC-2 (Claude/ChatGPT remote MCP) are separate pending releases.

## Option A — install a developer .mcpb bundle

1. Open the successful GitHub Actions **RoleHint local evidence MCP QA** run for the feature branch and download its **rolehint-claude-local-mcpb-dev** artifact. Inspect the included bundle/source before installing. No public directory listing or signature is claimed.
2. Claude Desktop → Settings → Desktop app → Extensions → Manage → Advanced settings → Install Extension (menu location can vary).
3. Select the .mcpb file and choose a **specific sanitized project folder** in the install-time folder picker. Never approve your whole home, Desktop, or entire Documents folder.
4. Ask Claude to propose a claim from a selected conversation excerpt or a particular source file and save it as a **private RoleHint draft**. Inspect the tool permissions before allowing access.
5. Review candidates locally. No evidence is automatically sent to RoleHint, ChatGPT or another server.

The extension uses the UV runtime to provision Python and the MCP SDK. First launch may require network access to install dependencies. This is not a signed or Anthropic-reviewed extension; installation on the user's real Mac remains unverified until separately tested.

## Option B — run locally from source

Use Python 3.11+. From this integration directory, create a venv, install requirements.txt and run server.py through the virtualenv. Configure the Claude Desktop custom MCP server command to the absolute virtualenv Python path, with the absolute server.py argument and an environment variable ROLEHINT_ALLOWED_FOLDER pointing at your selected project folder. Alternatively use the official mcp CLI / MCP Inspector. manifest.json defines the same folder picker and five tools for the .mcpb route.

## Local evidence review

From the repository root:

- python3 integrations/evidence_mcp_local/review.py list
- python3 integrations/evidence_mcp_local/review.py show candidate_ID
- python3 integrations/evidence_mcp_local/review.py export candidate_ID --to /absolute/private/candidates.json --confirm
- python3 integrations/evidence_mcp_local/review.py discard candidate_ID --confirm

An explicit export writes only selected claims into a new local JSON file with restrictive 0600 permissions; it cannot overwrite a file. **It does not sync to RoleHint.** Every claim retains needs-review, private and unverified status. The export file may contain personal/secret information that automatic scanning cannot reliably detect: never commit or email it without human inspection.

Drafts are in ~/.rolehint/evidence-inbox.sqlite3 (override with ROLEHINT_LOCAL_INBOX). The SQLite file is restricted to the local user, **not end-to-end encrypted**.

## Security boundaries

- No automatic scanning of local folders, conversations or the whole computer; no network requests.
- Only explicit relative file paths under the chosen folder; rejects traversal, symlinks escaping the folder, hidden files and common secret directories.
- Only UTF-8 text extensions, at most 256 KB per file, at most 120 lines and 8,000 characters per excerpt.
- Credential-pattern scanning is defense-in-depth, not a guarantee all secrets/confidential data are found.
- No generated claim becomes independently verified or recruiter-visible without a separate review process.
- The host executes MCP tools under local OS permissions; the manifest is not an operating-system sandbox.

## Test commands

From repo root:

1. python3 -m unittest discover -s tests -p test_evidence_mcp_local.py -v
2. python3 -m unittest discover -s tests -p test_evidence_mcp_export.py -v
3. python3 -m unittest discover -s tests -p test_evidence_mcp_protocol.py -v

The protocol test requires MCP SDK v2. CI also validates manifest parameters and packages an unsigned developer .mcpb artifact. A passing CI test does not prove macOS installation, ChatGPT write access, cloud import, user permissions, or real-device end-to-end quality.
