#!/usr/bin/env python3
"""fix.py — openclaw-vault-fix CLI.

Auto-repairs the safe, deterministic subset of `openclaw-llm-wiki` lint
findings: missing required frontmatter fields and index.md drift. Dry-run by
default — nothing is written unless you pass --apply.

Usage:
    python3 fix.py --vault-path ~/.openclaw/wiki/team               # preview
    python3 fix.py --vault-path ~/.openclaw/wiki/team --apply       # write
    python3 fix.py --vault-path ~/.openclaw/wiki/team --only frontmatter
    python3 fix.py --vault-path ~/.openclaw/wiki/team --json        # machine-readable

Exit codes:
    0  nothing to fix (or --apply succeeded with no errors)
    1  vault not found / usage error
    2  (dry-run only) fixable issues were found but not applied
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make the vaultfix package importable when fix.py is invoked by path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vaultfix import __version__  # noqa: E402
from vaultfix.fixers import (  # noqa: E402
    fix_frontmatter,
    fix_index_drift,
    walk_vault_pages,
)

FIXERS = ("frontmatter", "index_drift")


def _collect(vault: Path, only: str | None, today: str | None):
    pages = walk_vault_pages(vault)
    changes = []
    if only in (None, "frontmatter"):
        for page in pages:
            fc = fix_frontmatter(vault, page, today=today)
            if fc.changed or fc.notes:
                changes.append(fc)
    if only in (None, "index_drift"):
        idx = fix_index_drift(vault, pages)
        if idx.changed or idx.notes:
            changes.append(idx)
    return pages, changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--vault-path", required=True)
    parser.add_argument("--apply", action="store_true",
                        help="Write changes (default is dry-run preview only)")
    parser.add_argument("--only", choices=FIXERS,
                        help="Run a single fixer instead of all")
    parser.add_argument("--json", action="store_true",
                        help="Machine-readable output to stdout")
    parser.add_argument("--version", action="version", version=f"openclaw-vault-fix {__version__}")
    args = parser.parse_args(argv)

    vault = Path(args.vault_path).expanduser().resolve()
    if not vault.exists():
        print(f"vault not found: {vault}", file=sys.stderr)
        return 1

    _pages, changes = _collect(vault, args.only, today=None)
    mutating = [c for c in changes if c.changed]

    if args.apply:
        for c in mutating:
            c.path.write_text(c.new_text, encoding="utf-8")

    if args.json:
        print(json.dumps({
            "vault": str(vault),
            "applied": args.apply,
            "changes": [
                {
                    "path": c.path.relative_to(vault).as_posix(),
                    "fixer": c.fixer,
                    "changed": c.changed,
                    "notes": c.notes,
                }
                for c in changes
            ],
            "fixable_count": len(mutating),
        }, indent=2, ensure_ascii=False))
    else:
        verb = "applied" if args.apply else "would fix"
        print(f"vault: {vault}")
        print(f"{verb}: {len(mutating)} file(s)\n")
        for c in changes:
            mark = "*" if c.changed else " "
            print(f" [{mark}] {c.path.relative_to(vault).as_posix()}  ({c.fixer})")
            for note in c.notes:
                print(f"       - {note}")
        if not changes:
            print(" nothing to fix — vault is clean")
        elif not args.apply and mutating:
            print(f"\nrun again with --apply to write {len(mutating)} change(s)")

    if not args.apply and mutating:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
