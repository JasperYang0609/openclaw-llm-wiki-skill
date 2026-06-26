#!/usr/bin/env python3
"""
init_vault.py — bootstrap a team knowledge vault for openclaw-llm-wiki (v0.5.4).

Reflects the 2026-06-25 design alignment + Karpathy-pattern fills + Hermes Round 3
hardening (slug validation, prompt-injection-safe template rendering, fail-loud
git semantics):
- 20 Layer-2 folders (folder-on-demand) + 2 system folders (inbox/, _meta/)
- Default enabled at init: Core 10 + brand/. Use --enable to add more, --all for all 20.
- Git auto-commit enabled by default (initializes Git repo + makes first commit).
  Commit failures are now FATAL (non-zero exit) unless --skip-git.
- Wires up openclaw-lancedb-knowledge for semantic search
- `--team` must be a slug (validated via _manifest.validate_slug); `--domain` is
  rendered into agent-loaded files inside a fenced data block with explicit
  "do not follow instructions" framing to defeat prompt injection.

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

# Make the sibling _manifest.py importable when this script is invoked by path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _manifest import (  # noqa: E402
    ALL_LAYER2, DEFAULT_ENABLED, SYSTEM, SKILL_VERSION,
    ValidationError, validate_slug, safe_resolve_inside, render_data_block,
    all_layer2_list, git_identity_ok, preflight_git,
    GIT_TOOL_COMMIT_ARGS, GIT_COMMIT_NO_VERIFY,
)

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_ROOT / "templates"

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
    """Render a template by substituting `{{KEY}}` placeholders. Values are
    inserted verbatim; callers MUST pre-process untrusted values (e.g. wrap
    `domain` via render_data_block before passing it in)."""
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


CROSS_VAULT_ALLOW_TEMPLATE = """# Cross-vault search allow-list for {team}
#
# Read by lint check 12 (data gaps) and any prompt that wants to consult
# sibling vaults. **Default deny**: if `allowed_vaults` is empty, NO sibling
# vault is consulted, even if it lives on the same machine.
#
# Add an entry ONLY after the boss + consultant agree it is safe to share
# corpus across vaults. Each entry must include a human-readable `reason`.

version: 1
allowed_vaults: []
#  - path: /Users/.../wiki/ansai
#    reason: shared methodology / case studies
#  - path: /Users/.../wiki/laike
#    reason: same engagement family
"""


def write_cross_vault_allow(meta_dir: Path, team: str) -> None:
    target = meta_dir / "cross-vault-allow.yaml"
    if target.exists():
        return  # never clobber existing allow-list
    target.write_text(CROSS_VAULT_ALLOW_TEMPLATE.format(team=team), encoding="utf-8")


LANCEDB_CONFIG_TEMPLATE = """# LanceDB project + target paths for {team}
#
# Written at init so `lint.py check_lancedb_freshness` and any other consumer
# can locate the sibling LanceDB folder by the canonical project slug rather
# than by `vault.name` (which the user might rename). Don't edit by hand
# unless you're moving the lancedb folder.

project: {team}
target_dir_basename: {team}-lancedb   # under vault.parent
"""


def write_lancedb_config(meta_dir: Path, team: str) -> None:
    (meta_dir / "lancedb-config.yaml").write_text(
        LANCEDB_CONFIG_TEMPLATE.format(team=team), encoding="utf-8"
    )


def run(cmd: list[str], cwd: Path) -> int:
    return subprocess.run(cmd, cwd=str(cwd), check=False).returncode


def commit_scaffold(vault: Path, team: str, scaffolded_paths: list[str], fresh: bool) -> bool:
    """Commit explicitly scaffolded paths. Called AFTER git_init succeeded and
    identity was verified by `preflight_git`. Never uses `git add -A`."""
    gitignore = vault / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "# openclaw-llm-wiki vault\n"
            ".DS_Store\n"
            "*.tmp\n"
            ".obsidian/workspace*.json\n",
            encoding="utf-8",
        )
        scaffolded_paths.append(".gitignore")
    # Hermes I2 fix: when the repo already exists (e.g. retry after first run
    # bailed at preflight), pick up any root scaffold files we wrote this run
    # OR previously wrote but never committed (untracked + modified-untracked).
    # We use `git ls-files --others --exclude-standard --modified` to find them.
    if not fresh:
        out = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "--modified"],
            cwd=str(vault), capture_output=True, text=True, check=False,
        )
        for line in out.stdout.splitlines():
            line = line.strip()
            if line and line not in scaffolded_paths:
                scaffolded_paths.append(line)
    if scaffolded_paths:
        run(["git", "add", "--"] + scaffolded_paths, vault)
    msg = (
        f"init: {team} vault (openclaw-llm-wiki v{SKILL_VERSION} layout)" if fresh
        else f"chore: re-scaffold {team} vault templates (init_vault.py --overwrite or retry)"
    )
    # v0.5.6 (Hermes R5 I1): tool-owned commits bypass user gpgsign + hooks
    # so signing/hooks failure can't leave the vault half-scaffolded with no
    # commit. See SKILL.md for the rationale.
    rc = run(["git", *GIT_TOOL_COMMIT_ARGS, "commit", "-q", *GIT_COMMIT_NO_VERIFY, "-m", msg], vault)
    if rc == 0:
        print(f"[git] committed: {msg}")
        return True
    # No-changes case (commit failed because nothing to commit) is OK iff repo
    # already has at least one commit AND no untracked/modified files remain.
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(vault), capture_output=True, text=True, check=False,
    )
    if not status.stdout.strip():
        print("[git] no changes to commit (vault already up to date)")
        return True
    print(
        f"[error] git commit failed; vault has uncommitted changes:\n{status.stdout}",
        file=sys.stderr,
    )
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vault-path", required=True, help="Vault root directory")
    parser.add_argument("--team", required=True, help="Team name (used as LanceDB project)")
    parser.add_argument("--domain", required=True, help="One-sentence domain description")
    parser.add_argument(
        "--enable", action="append", default=[],
        choices=all_layer2_list(),
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

    # ---- input validation (sandbox / injection defence) -----------------
    try:
        team_slug = validate_slug(args.team, "--team")
    except ValidationError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 2
    if not args.domain or not args.domain.strip():
        print("[error] --domain cannot be empty", file=sys.stderr)
        return 2

    vault = Path(os.path.expanduser(args.vault_path)).resolve()
    today = datetime.date.today().isoformat()

    enabled = list(dict.fromkeys(
        list(ALL_LAYER2) if args.all else (list(DEFAULT_ENABLED) + args.enable)
    ))

    # ---- Git preflight BEFORE any filesystem write (Hermes I2 fix) ------
    # If the user is going to want a Git-tracked vault (default), refuse to
    # write any scaffold files until we know `git init` + `git commit` will
    # actually succeed. Avoids the failure mode where the first run wrote
    # half a vault but never committed; the retry then ignored existing files.
    fresh_git = False
    if not args.skip_git:
        if vault.exists() and (vault / ".git").exists():
            ok, reason = preflight_git(vault)
            if not ok:
                print(f"[error] git preflight failed: {reason}", file=sys.stderr)
                return 3
        else:
            # Will init below; identity must already be resolvable from the
            # environment (`git var` reads env vars + global config; no .git
            # required for global config to resolve).
            ok, reason = git_identity_ok(Path.cwd() if not vault.exists() else vault.parent)
            # The check above is best-effort; the strict check happens AFTER
            # `git init` succeeds. For now we just warn early if identity
            # is clearly missing system-wide.
            if not ok and "is not a git repo" not in reason:
                print(f"[warn] git identity may not be resolvable in this environment: {reason}", file=sys.stderr)

    # Create vault root + system folders + enabled Layer-2 folders
    vault.mkdir(parents=True, exist_ok=True)
    for sub in list(SYSTEM) + enabled:
        (vault / sub).mkdir(parents=True, exist_ok=True)

    replacements = {
        "TEAM_NAME": team_slug,
        "TEAM_NAME_SLUG": team_slug,
        # Wrap `domain` as a fenced data block with explicit "do not follow
        # instructions" framing — defeats prompt injection via customer name
        # like "Mifiya. IGNORE ALL PRIOR RULES AND...".
        "DOMAIN_DESCRIPTION": render_data_block(args.domain, label="domain"),
        "INIT_DATE": today,
        "VAULT_PATH": str(vault),
    }

    scaffolded: list[str] = []
    for filename in ("SCHEMA.md", "CLAUDE.md", "AGENTS.md", "index.md", "log.md", "overview.md"):
        target = vault / filename
        if target.exists() and not args.overwrite:
            print(f"[skip] {target} already exists (use --overwrite to replace)")
            continue
        render(TEMPLATES / filename, target, replacements)
        print(f"[write] {target}")
        scaffolded.append(filename)

    # _meta/ admin files
    write_active_folders(vault / "_meta", team_slug, enabled)
    write_lint_config(vault / "_meta", team_slug)
    write_cross_vault_allow(vault / "_meta", team_slug)
    write_lancedb_config(vault / "_meta", team_slug)
    print(f"[write] {vault / '_meta' / 'active-folders.md'}")
    print(f"[write] {vault / '_meta' / 'lint-config.yaml'}")
    print(f"[write] {vault / '_meta' / 'cross-vault-allow.yaml'}")
    print(f"[write] {vault / '_meta' / 'lancedb-config.yaml'}")
    scaffolded.extend([
        "_meta/active-folders.md",
        "_meta/lint-config.yaml",
        "_meta/cross-vault-allow.yaml",
        "_meta/lancedb-config.yaml",
    ])

    # Empty Layer-2 folders need a .gitkeep so Git can track them
    for sub in enabled:
        keep = vault / sub / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")
            scaffolded.append(f"{sub}/.gitkeep")

    # Git: init if needed, then commit using effective identity.
    # (The early preflight + identity check above failed loudly before any
    # files were written, so by now we expect this to succeed.)
    if args.skip_git:
        print("[git] skipped (--skip-git)")
    else:
        fresh_git = not (vault / ".git").exists()
        if fresh_git:
            if run(["git", "init", "-q", "-b", "main"], vault) != 0:
                print("[error] git init failed; vault has scaffold but no Git tracking", file=sys.stderr)
                return 3
        # Now that .git exists (either freshly or pre-existing), use the strict
        # `git var GIT_AUTHOR_IDENT` check.
        ok, reason = git_identity_ok(vault)
        if not ok:
            print(
                f"[error] git identity not resolvable in {vault}: {reason}\n"
                f"  Configure with `git -C {vault} config user.email <you@example.com>` "
                f"and user.name, OR set env GIT_AUTHOR_NAME/EMAIL + "
                f"GIT_COMMITTER_NAME/EMAIL, then RE-RUN this script. Existing "
                f"scaffold files will be picked up on retry.",
                file=sys.stderr,
            )
            return 3
        if not commit_scaffold(vault, team_slug, scaffolded, fresh_git):
            return 3

    # LanceDB
    if args.skip_lancedb:
        print("[lancedb] skipped (--skip-lancedb)")
    else:
        bootstrap = Path(args.lancedb_skill) / "scripts" / "bootstrap_openclaw_lancedb.py"
        if not bootstrap.exists():
            print(
                f"[warn] LanceDB bootstrap not found at {bootstrap}.\n"
                f"  Install openclaw-lancedb-knowledge-skill first: "
                f"https://github.com/JasperYang0609/openclaw-lancedb-knowledge-skill\n"
                f"  Or rerun with `--skip-lancedb` if you don't need semantic search yet "
                f"(text grep still works).\n"
                f"  Or rerun with `--lancedb-skill <path-to-skill-dir>` to point at a custom install.",
                file=sys.stderr,
            )
        else:
            # Validated team slug means this name is safe to embed in a path.
            # Belt-and-suspenders: also assert the resolved target stays inside
            # vault.parent so a future slug-grammar mistake can't escape.
            try:
                target = safe_resolve_inside(vault.parent, f"{team_slug}-lancedb", "--team")
            except ValidationError as e:
                print(f"[error] lancedb target unsafe: {e}", file=sys.stderr)
                return 2
            cmd = [
                sys.executable, str(bootstrap),
                "--target", str(target),
                "--workspace", str(vault),
                "--project-root", str(vault),
                "--project-name", team_slug,
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
    print(f"  4. Schedule lint: `python3 {Path(__file__).parent / 'lint.py'} --vault-path {vault}` via cron")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
