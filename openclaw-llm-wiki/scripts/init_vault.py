#!/usr/bin/env python3
"""
init_vault.py — bootstrap a team knowledge vault for openclaw-llm-wiki (v0.5).

Reflects the 2026-06-25 design alignment + Karpathy-pattern fills:
- 20 Layer-2 folders (folder-on-demand) + 2 system folders (inbox/, _meta/)
- Default enabled at init: Core 10 + brand/. Use --enable to add more, --all for all 19.
- Git auto-commit is enabled by default (initializes Git repo + makes first commit)
- Wires up openclaw-lancedb-knowledge for semantic search

Usage:
    python3 init_vault.py \\
        --vault-path ~/.openclaw/wiki/team \\
        --team mifiya \\
        --domain "Mifiya consulting team — brand, clients, methods, SOPs" \\
        --enable policies --enable deliverables

    python3 init_vault.py --vault-path /tmp/test --team test \\
        --domain "Smoke test" --all --skip-lancedb --skip-git
"""
from __future__ import annotations

import argparse
import datetime
import os
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_ROOT / "templates"

CORE_10 = [
    "decisions", "sops", "customers", "products", "contacts",
    "people", "concepts", "comparisons", "syntheses", "queries",
]
RECOMMENDED_5 = ["brand", "policies", "deliverables", "meetings", "incidents"]
NICE_TO_HAVE_5 = ["metrics", "vendors", "templates", "glossary", "summaries"]
SYSTEM = ["inbox", "_meta"]

ALL_LAYER2 = CORE_10 + RECOMMENDED_5 + NICE_TO_HAVE_5
DEFAULT_ENABLED = CORE_10 + ["brand"]

ACTIVE_FOLDERS_TEMPLATE = """# Active Layer-2 folders for {team}

Maintained by the consultant admin. Lint and AI classification only target folders listed
as `active`. Folder-on-demand: do not pre-create empty folders.

{rows}

To enable an additional folder later: create the directory, add a row here, then re-run
the next lint cycle. To deactivate: archive its contents, remove the row, then delete
the directory.
"""

LINT_CONFIG_TEMPLATE = """# Lint configuration for {team}

# Weekly cron + on-demand via Discord. All 13 checks active by default.
# Adjust thresholds here; do not delete the keys.

stale_page_days: 90
oversized_page_lines: 200
log_rotate_entries: 500
should_build_min_sources: 2
data_gap_local_only: true   # never web-search; use other vaults / lancedb / discord history
auto_fill_cross_refs: true  # no admin review required
"""


def render(template_path: Path, dest: Path, replacements: dict[str, str]) -> None:
    text = template_path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace("{{" + key + "}}", value)
    dest.write_text(text, encoding="utf-8")


def write_active_folders(meta_dir: Path, team: str, enabled: list[str]) -> None:
    rows = []
    for folder in ALL_LAYER2:
        status = "active" if folder in enabled else "inactive"
        rows.append(f"- {folder}/: {status}")
    text = ACTIVE_FOLDERS_TEMPLATE.format(team=team, rows="\n".join(rows))
    (meta_dir / "active-folders.md").write_text(text, encoding="utf-8")


def write_lint_config(meta_dir: Path, team: str) -> None:
    (meta_dir / "lint-config.yaml").write_text(
        LINT_CONFIG_TEMPLATE.format(team=team), encoding="utf-8"
    )


def run(cmd: list[str], cwd: Path) -> int:
    return subprocess.run(cmd, cwd=str(cwd), check=False).returncode


def git_init_and_commit(vault: Path, team: str) -> None:
    if (vault / ".git").exists():
        print("[git] repo already exists, skipping init")
        return
    if run(["git", "init", "-q", "-b", "main"], vault) != 0:
        print("[warn] git init failed; vault is usable but rollback is unavailable", file=sys.stderr)
        return
    # Don't override user's git identity; let Git use system config.
    # If no identity is configured, the commit will fail with a clear message.
    gitignore = vault / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "# openclaw-llm-wiki vault\n"
            ".DS_Store\n"
            "*.tmp\n"
            ".obsidian/workspace*.json\n",
            encoding="utf-8",
        )
    run(["git", "add", "-A"], vault)
    msg = f"init: {team} vault (openclaw-llm-wiki v0.5 layout)"
    rc = run(["git", "commit", "-q", "-m", msg], vault)
    if rc == 0:
        print("[git] initial commit done")
    else:
        print(
            "[warn] initial commit failed (likely missing git user.name/user.email). "
            "Configure git identity and run `git add -A && git commit` manually.",
            file=sys.stderr,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vault-path", required=True, help="Vault root directory")
    parser.add_argument("--team", required=True, help="Team name (used as LanceDB project)")
    parser.add_argument("--domain", required=True, help="One-sentence domain description")
    parser.add_argument(
        "--enable", action="append", default=[],
        choices=ALL_LAYER2,
        help="Enable an additional Layer-2 folder beyond defaults. Repeat for multiple.",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Enable all 20 Layer-2 folders (not recommended for new vaults).",
    )
    parser.add_argument(
        "--lancedb-skill",
        default=str(SKILL_ROOT.parent / "openclaw-lancedb-knowledge"),
        help="Path to openclaw-lancedb-knowledge skill folder (for bootstrap script)",
    )
    parser.add_argument("--skip-lancedb", action="store_true", help="Skip LanceDB bootstrap")
    parser.add_argument("--skip-git", action="store_true", help="Skip Git init + commit")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite SCHEMA/index/log if exists")
    args = parser.parse_args()

    vault = Path(os.path.expanduser(args.vault_path)).resolve()
    today = datetime.date.today().isoformat()

    enabled = list(dict.fromkeys(ALL_LAYER2 if args.all else (DEFAULT_ENABLED + args.enable)))

    # Create vault root + system folders + enabled Layer-2 folders
    vault.mkdir(parents=True, exist_ok=True)
    for sub in SYSTEM + enabled:
        (vault / sub).mkdir(parents=True, exist_ok=True)

    replacements = {
        "TEAM_NAME": args.team,
        "TEAM_NAME_SLUG": args.team.lower().replace(" ", "-"),
        "DOMAIN_DESCRIPTION": args.domain,
        "INIT_DATE": today,
        "VAULT_PATH": str(vault),
    }

    for filename in ("SCHEMA.md", "CLAUDE.md", "AGENTS.md", "index.md", "log.md", "overview.md"):
        target = vault / filename
        if target.exists() and not args.overwrite:
            print(f"[skip] {target} already exists (use --overwrite to replace)")
            continue
        render(TEMPLATES / filename, target, replacements)
        print(f"[write] {target}")

    # _meta/ admin files
    write_active_folders(vault / "_meta", args.team, enabled)
    write_lint_config(vault / "_meta", args.team)
    print(f"[write] {vault / '_meta' / 'active-folders.md'}")
    print(f"[write] {vault / '_meta' / 'lint-config.yaml'}")

    # Git
    if args.skip_git:
        print("[git] skipped (--skip-git)")
    else:
        git_init_and_commit(vault, args.team)

    # LanceDB
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
                sys.executable, str(bootstrap),
                "--target", str(target),
                "--workspace", str(vault),
                "--project-root", str(vault),
                "--project-name", args.team,
                "--npm-install",
            ]
            print("[lancedb] " + " ".join(cmd))
            if run(cmd, vault) != 0:
                print(
                    "[warn] LanceDB bootstrap returned non-zero. Vault markdown is ready; "
                    "rerun the bootstrap when ready.",
                    file=sys.stderr,
                )

    print(f"\n[done] Team vault for '{args.team}' ready at {vault}")
    print(f"  Enabled folders ({len(enabled)}): {', '.join(enabled)}")
    print("Next steps:")
    print(f"  1. Review and customize {vault / 'SCHEMA.md'} (tag taxonomy, team rules)")
    print(f"  2. Edit {vault / '_meta' / 'active-folders.md'} if you want to enable more folders")
    print("  3. Hook up daily-backup cron to drop summaries into this vault")
    print("  4. Schedule lint via OpenClaw cron (`@knowledge lint`)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
