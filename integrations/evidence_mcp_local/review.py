"""Local review CLI for Claude MCP evidence drafts.

Nothing in this command connects to the internet or RoleHint production.
Run: python review.py list | show <id> | export <id> ... --to /absolute/file.json
"""
from __future__ import annotations

import argparse
import json
import sys

from export import export_bundle
from inbox import discard_draft, get_draft, list_drafts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review private RoleHint evidence proposals on this computer")
    actions = parser.add_subparsers(dest="action", required=True)
    listing = actions.add_parser("list", help="Show candidate IDs and short claims without source excerpts")
    listing.add_argument("--limit", type=int, default=30)
    show = actions.add_parser("show", help="Read full evidence/provenance for one private draft")
    show.add_argument("id")
    delete = actions.add_parser("discard", help="Delete a local draft (cannot undo)")
    delete.add_argument("id")
    delete.add_argument("--confirm", action="store_true")
    export = actions.add_parser("export", help="Export selected drafts to an offline JSON file")
    export.add_argument("ids", nargs="+")
    export.add_argument("--to", required=True, help="Absolute path to new JSON file, never overwritten")
    export.add_argument("--confirm", action="store_true", help="I reviewed the selected drafts and approve this local export")
    args = parser.parse_args(argv)
    try:
        if args.action == "list":
            rows = list_drafts(args.limit)
            if not rows:
                print("No local draft candidates.")
            for row in rows:
                print(f'{row["id"]}  {row["project"]}: {row["claim"][:100]}')
        elif args.action == "show":
            row = get_draft(args.id)
            if row is None:
                print("Draft not found.", file=sys.stderr)
                return 2
            print(json.dumps(row, indent=2, ensure_ascii=False))
        elif args.action == "discard":
            if not args.confirm:
                print("Add --confirm to permanently remove this private draft.", file=sys.stderr)
                return 2
            result = discard_draft(args.id)
            if not result["deleted"]:
                print("Draft not found.", file=sys.stderr)
                return 2
            print(f'Locally deleted: {args.id}')
        elif args.action == "export":
            result = export_bundle(args.ids, args.to, confirmed=args.confirm)
            print(f'Exported {result["count"]} unverified drafts locally to {result["path"]}')
            print("Not uploaded. Do not share without inspecting the file.")
        return 0
    except (ValueError, PermissionError, FileNotFoundError, LookupError, FileExistsError) as error:
        print(f"RoleHint: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
