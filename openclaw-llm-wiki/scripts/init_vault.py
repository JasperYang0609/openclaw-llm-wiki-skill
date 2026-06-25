#!/usr/bin/env python3
"""
init_vault.py — bootstrap a team knowledge vault for openclaw-llm-wiki.

STATUS: v0.1 layout. Pending v0.3 rewrite for the 19-folder structure agreed
2026-06-25 and for Git auto-commit initialization. Until then this script
still creates the legacy 5-folder layout (entities / concepts / comparisons /
syntheses / queries). The v0.2 SKILL.md and templates/ describe the target
state; this script lags. Track in repo CHANGELOG.

Usage:
    python3 init_vault.py \\
        --vault-path ~/.openclaw/wiki/team \\
        --team mifiya \\
        --domain "Mifiya consulting team knowledge — brand, clients, methods, SOPs"

What it does:
    1. Create the vault directory structure
    2. Render SCHEMA.md, index.md, log.md from templates
    3. Call openclaw-lancedb-knowledge bootstrap to wire up search
"""
from __future__ import annotations

import argparse
import datetime
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_ROOT / "templates"

DIRS = [
    "raw/articles",
    "raw/papers",
    "raw/transcripts",
    "raw/assets",
    "entities",
    "concepts",
    "comparisons",
    "syntheses",
    "queries",
]


def render(template_path: Path, dest: Path, replacements: dict[str, str]) -> None:
    text = template_path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace("{{" + key + "}}", value)
    dest.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-path", required=True, help="Vault root directory")
    parser.add_argument("--team", required=True, help="Team name (used as LanceDB project)")
    parser.add_argument("--domain", required=True, help="One-sentence domain description")
    parser.add_argument(
        "--lancedb-skill",
        default=str(SKILL_ROOT.parent / "openclaw-lancedb-knowledge"),
        help="Path to openclaw-lancedb-knowledge skill folder (for bootstrap script)",
    )
    parser.add_argument(
        "--skip-lancedb",
        action="store_true",
        help="Skip LanceDB bootstrap (just create markdown vault)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing SCHEMA / index / log if vault already exists",
    )
    args = parser.parse_args()

    vault = Path(os.path.expanduser(args.vault_path)).resolve()
    today = datetime.date.today().isoformat()

    vault.mkdir(parents=True, exist_ok=True)
    for sub in DIRS:
        (vault / sub).mkdir(parents=True, exist_ok=True)

    replacements = {
        "TEAM_NAME": args.team,
        "DOMAIN_DESCRIPTION": args.domain,
        "INIT_DATE": today,
        "VAULT_PATH": str(vault),
    }

    for filename in ("SCHEMA.md", "index.md", "log.md"):
        target = vault / filename
        if target.exists() and not args.overwrite:
            print(f"[skip] {target} already exists (use --overwrite to replace)")
            continue
        render(TEMPLATES / filename, target, replacements)
        print(f"[write] {target}")

    if args.skip_lancedb:
        print("[lancedb] skipped (--skip-lancedb)")
    else:
        bootstrap = Path(args.lancedb_skill) / "scripts" / "bootstrap_openclaw_lancedb.py"
        if not bootstrap.exists():
            print(
                f"[warn] LanceDB bootstrap not found at {bootstrap}. "
                "Run it manually later, or pass --lancedb-skill to point at the right folder.",
                file=sys.stderr,
            )
        else:
            target = vault.parent / f"{args.team}-lancedb"
            cmd = [
                sys.executable,
                str(bootstrap),
                "--target",
                str(target),
                "--workspace",
                str(vault),
                "--project-root",
                str(vault),
                "--project-name",
                args.team,
                "--npm-install",
            ]
            print("[lancedb] " + " ".join(cmd))
            result = subprocess.run(cmd, check=False)
            if result.returncode != 0:
                print(
                    "[warn] LanceDB bootstrap returned non-zero. "
                    "Vault markdown is ready; you can rerun the bootstrap later.",
                    file=sys.stderr,
                )

    print(f"\n[done] Team vault for '{args.team}' ready at {vault}")
    print("Next steps:")
    print(f"  1. Review and customize {vault / 'SCHEMA.md'} (tag taxonomy, team rules)")
    print("  2. Ingest the first 3 sources to seed the wiki")
    print("  3. Schedule incremental indexing via OpenClaw cron")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
