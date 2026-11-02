"""Local-only evidence candidate inbox for Claude Desktop.

Never uploads, verifies, or publishes evidence. No automatic file scanning.
Source directories must be explicitly allowed by the user.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from pathlib import Path

ALLOWED_EXTENSIONS = frozenset({
    ".txt", ".md", ".rst", ".py", ".js", ".jsx", ".ts", ".tsx",
    ".json", ".yml", ".yaml", ".css", ".html", ".csv", ".sql"
})
FORBIDDEN_DIR_NAMES = frozenset({"node_modules", "__pycache__", "vendor", "secrets", "credentials"})
SENSITIVE = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    r"|(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,})"
    r"|\b(?:password|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*['\"]?\S{8,}",
    re.I,
)
SCHEMA = """
CREATE TABLE IF NOT EXISTS drafts(
 id TEXT PRIMARY KEY,
 source_kind TEXT NOT NULL,
 source_ref TEXT NOT NULL,
 project TEXT NOT NULL,
 claim TEXT NOT NULL,
 evidence TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status='needs-review'),
 visibility TEXT NOT NULL CHECK(visibility='private'),
 captured_at REAL NOT NULL,
 boundary TEXT NOT NULL
);
"""


def _db_path() -> Path:
    configured = os.getenv("ROLEHINT_LOCAL_INBOX")
    path = Path(configured).expanduser() if configured else Path.home()/".rolehint"/"evidence-inbox.sqlite3"
    return path


def _connect():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not path.is_file():
        # Create privately even on machines with permissive umask.
        descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
    if path.is_symlink():
        raise PermissionError("Local inbox cannot be a symbolic link")
    os.chmod(path, 0o600)
    connection = sqlite3.connect(str(path), timeout=15)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    return connection


def _clean(label: str, value: str, max_length: int) -> str:
    result = str(value or "").strip()
    if not result or len(result) > max_length:
        raise ValueError(f"{label} must be 1–{max_length} characters")
    if SENSITIVE.search(result):
        raise ValueError(f"{label} may contain credentials: redact locally before capture")
    return result


def propose_text(claim: str, evidence: str, source_name: str, project: str = "Unassigned", *, source_kind: str = "selected-text") -> dict:
    if source_kind not in {"selected-text", "local-file"}:
        raise ValueError("Unsupported local source kind")
    claim = _clean("claim", claim, 1000)
    evidence = _clean("evidence", evidence, 8000)
    source_name = _clean("source_name", source_name, 240)
    project = _clean("project", project, 120)
    fingerprint = hashlib.sha256(
        json.dumps([claim, evidence, source_name, project, source_kind], ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    draft_id = "candidate_" + fingerprint[:24]
    with _connect() as conn:
        before = conn.total_changes
        conn.execute("""INSERT OR IGNORE INTO drafts
            (id,source_kind,source_ref,project,claim,evidence,status,visibility,captured_at,boundary)
            VALUES(?,?,?,?,?,?,'needs-review','private',?,?)""",
            (draft_id, source_kind, source_name, project, claim, evidence,
             time.time(), "Assistant-proposed; text is not independently verified evidence."))
        created = conn.total_changes > before
    return {"id": draft_id, "created": created, "status": "needs-review",
            "visibility": "private", "stored": "local-only"}


def _allowed_root() -> Path:
    allowed = os.getenv("ROLEHINT_ALLOWED_FOLDER")
    if not allowed:
        raise PermissionError("Set ROLEHINT_ALLOWED_FOLDER to a folder you explicitly approve")
    root = Path(allowed).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Allowed source root must be a directory")
    if root == Path("/") or root == Path.home().resolve():
        raise PermissionError("Allow a specific project folder, not your home or entire disk")
    return root


def _safe_relative_path(root: Path, relative_path: str, *, directory: bool = False) -> Path:
    rel = Path(str(relative_path))
    if rel.is_absolute() or ".." in rel.parts or any(
        part.startswith(".") or part in FORBIDDEN_DIR_NAMES for part in rel.parts
    ):
        raise PermissionError("Only non-hidden paths inside the selected project folder are allowed")
    if not rel.parts and not (directory and str(relative_path) == "."):
        raise PermissionError("Choose a specific relative path")
    # Reject every symlink component, even if it resolves to another file
    # inside the root: aliases can disguise secret or hidden directories.
    candidate = root
    for part in rel.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise PermissionError("Symbolic links are not allowed")
    candidate = candidate.resolve(strict=True)
    if not candidate.is_relative_to(root):
        raise PermissionError("Source path is outside the permitted folder")
    return candidate


def list_allowed_files(relative_directory: str = ".", limit: int = 50) -> dict:
    """List names of immediate children only; no recursion or file-content reads."""
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")
    root = _allowed_root()
    directory = _safe_relative_path(root, relative_directory, directory=True)
    if not directory.is_dir():
        raise ValueError("The selected path is not a directory")
    prefix = Path(relative_directory)
    files = []
    with os.scandir(directory) as entries:
        for entry in entries:
            if entry.name.startswith(".") or entry.name in FORBIDDEN_DIR_NAMES or entry.is_symlink():
                continue
            relative_name = (prefix / entry.name).as_posix()
            if entry.is_dir(follow_symlinks=False):
                files.append({"relative_path": relative_name, "type": "directory"})
            elif entry.is_file(follow_symlinks=False) and Path(entry.name).suffix.lower() in ALLOWED_EXTENSIONS:
                size = entry.stat(follow_symlinks=False).st_size
                if size <= 256_000:
                    files.append({"relative_path": relative_name, "type": "text-file", "size_bytes": size})
            if len(files) >= limit:
                break
    return {"directory": str(relative_directory), "entries": files, "recursive": False,
            "contents_read": False, "stored": "local-only"}


def propose_file(relative_path: str, claim: str, project: str = "Unassigned",
                 first_line: int = 1, last_line: int = 80) -> dict:
    root = _allowed_root()
    rel = Path(relative_path)
    path = _safe_relative_path(root, relative_path)
    if not path.is_file() or path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise PermissionError("Source is not a supported text file")
    if path.stat().st_size > 256_000:
        raise ValueError("File too large for the local text preview; select a smaller source")
    if not (1 <= first_line <= last_line <= first_line + 119):
        raise ValueError("Select no more than 120 consecutive lines, starting at line 1 or later")
    lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    if first_line > len(lines):
        raise ValueError("Start line is beyond the end of the file")
    excerpt = "\n".join(lines[first_line-1:last_line])
    if len(excerpt) > 8000:
        raise ValueError("Selected excerpt exceeds 8000 characters")
    if SENSITIVE.search(excerpt):
        raise ValueError("This selection may contain credentials; redact before capture")
    source = f"local-file:{rel.as_posix()}#L{first_line}-L{min(last_line,len(lines))}"
    result = propose_text(claim, excerpt, source, project, source_kind="local-file")
    return {**result, "source": source}


def list_drafts(limit: int = 30) -> list[dict]:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    with _connect() as conn:
        return [dict(row) for row in conn.execute(
            """SELECT id,source_kind,source_ref,project,claim,status,visibility,captured_at
               FROM drafts ORDER BY captured_at DESC LIMIT ?""", (limit,)
        )]


def get_draft(draft_id: str) -> dict | None:
    with _connect() as conn:
        record = conn.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
        return dict(record) if record else None


def discard_draft(draft_id: str) -> dict:
    with _connect() as conn:
        deleted = conn.execute("DELETE FROM drafts WHERE id=?", (draft_id,)).rowcount
    return {"deleted": bool(deleted), "id": draft_id, "stored": "local-only"}
