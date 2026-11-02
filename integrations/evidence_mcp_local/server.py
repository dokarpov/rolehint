"""RoleHint Evidence Collector: opt-in, local stdio MCP for Claude Desktop.

Install the official MCP Python SDK v2 in a virtual environment first.
This program never contacts RoleHint servers and never marks claims verified.
"""
from __future__ import annotations

from mcp.server import MCPServer
from inbox import propose_text, propose_file, list_allowed_files, list_drafts, get_draft, discard_draft

mcp = MCPServer("RoleHint Evidence Collector")


@mcp.tool()
def propose_evidence_from_text(claim: str, selected_text: str,
                               source_name: str, project: str = "Unassigned") -> dict:
    """Draft a private, UNVERIFIED RoleHint evidence claim from selected text.

    Use only text the user has chosen to capture, not unrelated chat history.
    This stores locally on the user's computer, not in a cloud account.
    """
    return propose_text(claim, selected_text, source_name, project)


@mcp.tool()
def list_allowed_project_files(relative_directory: str = ".", limit: int = 50) -> dict:
    """List visible filenames in ONE explicitly approved folder without reading contents.

    Use only when the user requests to browse their allowed project artifacts.
    No recursion, full-disk search, hidden files, symlink aliases or cloud sync.
    """
    return list_allowed_files(relative_directory, limit)


@mcp.tool()
def propose_evidence_from_file(relative_path: str, claim: str,
                               project: str = "Unassigned",
                               first_line: int = 1, last_line: int = 80) -> dict:
    """Draft private evidence from selected lines of an explicitly allowed local file.

    The path MUST be relative to the user's ROLEHINT_ALLOWED_FOLDER.
    This does not scan directories, upload data, or verify a claim.
    """
    return propose_file(relative_path, claim, project, first_line, last_line)


@mcp.tool()
def list_evidence_drafts(limit: int = 30) -> list[dict]:
    """List metadata for private local candidate claims awaiting user review."""
    return list_drafts(limit)


@mcp.tool()
def get_evidence_draft(draft_id: str) -> dict:
    """Read an existing private local draft. No external network or publishing."""
    return get_draft(draft_id) or {"error": "Draft not found"}


@mcp.tool()
def discard_evidence_draft(draft_id: str) -> dict:
    """Permanently discard a specified local draft, only when user requests it."""
    return discard_draft(draft_id)


if __name__ == "__main__":
    mcp.run(transport="stdio")
