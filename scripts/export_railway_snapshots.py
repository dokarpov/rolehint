#!/usr/bin/env python3
"""Read-only-from-source export of both RoleHint Railway SQLite volumes.

Run on the owner's authenticated laptop with a recent Railway CLI. Requires
`railway login` and Railway SSH key registration. Does not deploy, restart,
change variables, delete volumes or modify the live databases. Private files
other than SQLite must be backed up separately before migration.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT = "e48095fc-fb0f-4e59-bf34-d30418e5198f"
SERVICES = ("rolehint-api-worker", "rolehint-staging")
REMOTE_HELPER = "/tmp/rolehint_backup_data.py"
REMOTE_BASE = "/tmp/rolehint-export"
ROOT = Path(__file__).resolve().parents[1]


def check_target(dest: Path) -> Path:
    dest = dest.expanduser().resolve()
    if dest == ROOT or ROOT in dest.parents:
        raise ValueError("Private snapshots must be outside the Git repository")
    dest.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(dest, 0o700)
    return dest


def run(args: list[str]) -> str:
    # Never log environment variables, tokens, contents of private files or CVs.
    done = subprocess.run(args, text=True, capture_output=True, check=True)
    return done.stdout


def read_snapshot_location(stdout: str) -> str:
    # Railway may print a short preamble before the script's JSON result.
    for match in re.finditer(r"\{", stdout):
        try:
            value, _ = json.JSONDecoder().raw_decode(stdout[match.start():])
        except ValueError:
            continue
        if isinstance(value, dict) and value.get("snapshot_dir", "").startswith(REMOTE_BASE + "/"):
            return value["snapshot_dir"]
    raise ValueError("No verified backup location returned by Railway SSH")


def export_service(service: str, dest: Path) -> Path:
    helper = ROOT / "backend" / "backup_data.py"
    if not helper.is_file():
        raise FileNotFoundError(f"Missing backup helper: {helper}")
    print(f"[{service}] uploading read-only backup helper to ephemeral /tmp")
    run(["railway", "service", "files", "-p", PROJECT, "-s", service,
         "upload", str(helper), REMOTE_HELPER])
    print(f"[{service}] taking an online SQLite snapshot")
    output = run(["railway", "ssh", "-p", PROJECT, "-s", service, "--",
                  "python", REMOTE_HELPER, "--data-dir", "/app/data",
                  "--output-base", REMOTE_BASE])
    remote_folder = read_snapshot_location(output)
    timestamp = Path(remote_folder).name
    local = dest / f"{service}-{timestamp}"
    if local.exists():
        raise FileExistsError(f"Refusing to overwrite an existing backup: {local}")
    print(f"[{service}] downloading to private local storage")
    run(["railway", "service", "files", "-p", PROJECT, "-s", service,
         "download", remote_folder, str(local)])
    manifests = list(local.rglob("manifest.json")) if local.is_dir() else []
    if len(manifests) != 1:
        raise RuntimeError(f"Expected exactly one manifest in {local}; got {len(manifests)}")
    manifest_dir = manifests[0].parent
    result = run([sys.executable, str(ROOT / "backend" / "verify_backup.py"), str(manifest_dir)])
    check = json.loads(result)
    if check.get("status") != "verified":
        raise RuntimeError("Restore verification did not pass")
    print(f"[{service}] VERIFIED: {len(check['databases'])} SQLite databases; no row contents printed")
    return manifest_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path,
                        help="Owner-controlled encrypted folder OUTSIDE the repo")
    parser.add_argument("--service", choices=[*SERVICES, "both"], default="both")
    args = parser.parse_args()
    if shutil.which("railway") is None:
        parser.error("Railway CLI not installed; install and run railway login first")
    try:
        dest = check_target(args.destination)
        services = SERVICES if args.service == "both" else (args.service,)
        for service in services:
            export_service(service, dest)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"EXPORT STOPPED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print("SQLite snapshots passed download + SHA256 + integrity + restore tests.")
    print("BLOCKER: copy local_secrets.json, encryption keys, upload files and any other non-DB state separately before cutover.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
