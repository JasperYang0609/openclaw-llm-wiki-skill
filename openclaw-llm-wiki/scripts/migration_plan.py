#!/usr/bin/env python3
"""
migration_plan.py — preview schema-change impact before applying (v0.5.4).

Implements the "preview impact before commit" guardrail (F24 #2 from the
2026-06-25 alignment). Dry-run only by default; `--apply` will actually mutate
the vault but is gated behind a two-step confirmation.

v0.5.4 (Hermes Round 3 hardening):
- `rename --allow-custom` still validates `dst` is a slug AND resolves inside
  vault (no more `..` / absolute path escape).
- Git commit failure on `--apply` ops is now FATAL (non-zero exit) — preserves
  the "Git auto-commit always on" rollback contract.
- LAYER2 list pulled from `_manifest` (single source of truth).

Supported operations:
    enable <folder>             — activate one of the 20 Layer-2 folders
    disable <folder>            — deactivate (counts pages + inbound links)
    rename <from> <to>          — rename a Layer-2 folder (counts files + wikilinks)
    add-frontmatter-field <key> — count pages missing it; suggest backfill
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Make sibling _manifest importable when invoked by path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _manifest import (  # noqa: E402
    ALL_LAYER2, SKILL_VERSION,
    ValidationError, validate_slug, safe_resolve_inside,
    git_identity_ok, preflight_git,
    GIT_TOOL_COMMIT_ARGS, GIT_COMMIT_NO_VERIFY,
    head_snapshot, rollback_paths,
)
LAYER2 = list(ALL_LAYER2)


def preflight_or_die(vault: Path) -> int | None:
    """Run BEFORE any mutation. Returns None if OK; integer exit code if fail.
    Use as: `rc = preflight_or_die(vault); if rc is not None: return rc`.

    Hermes I1 fix: ensures we never leave a vault half-mutated because Git
    refused to commit afterwards.
    """
    if not (vault / ".git").exists():
        print(
            "[error] vault is not a git repo; refusing to mutate without rollback safety.\n"
            "  Rerun init_vault.py without --skip-git, or run `git init` in the vault and add an initial commit.",
            file=sys.stderr,
        )
        return 3
    ok, reason = preflight_git(vault)
    if not ok:
        print(f"[error] git preflight failed (mutation refused): {reason}", file=sys.stderr)
        return 3
    # Working tree should be clean OR only contain expected dirty paths.
    # Strict: refuse to mutate if there are any unstaged changes (avoids the
    # `git add -A`-equivalent dirty-WIP sweep that v0.5.4 already removed).
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(vault), capture_output=True, text=True, check=False,
    )
    dirty = status.stdout.strip()
    if dirty:
        print(
            f"[error] vault working tree is not clean; refusing to mutate.\n"
            f"  Commit or stash these first:\n{dirty}",
            file=sys.stderr,
        )
        return 4
    return None

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:\|[^\]]+)?\]\]")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def confirm_two_step(prompt: str, expected: str) -> bool:
    """Strict two-step confirmation. Step 1: literal 'yes'. Step 2: exact match of
    `expected` (typically the folder name being acted on). Anything else aborts.
    """
    print(prompt)
    a = input("Type 'yes' to proceed (step 1/2): ").strip().lower()
    if a != "yes":
        return False
    b = input(f"Type '{expected}' exactly to confirm (step 2/2): ").strip()
    if b != expected:
        print(f"[abort] step 2 mismatch: expected '{expected}', got '{b}'")
        return False
    return True


def all_pages(vault: Path) -> list[Path]:
    skip = {".git", "_archive", "_meta", "inbox"}
    out = []
    for p in vault.rglob("*.md"):
        rel = p.relative_to(vault)
        if rel.name in {"SCHEMA.md", "index.md", "log.md"}:
            continue
        if any(part in skip for part in rel.parts):
            continue
        out.append(p)
    return out


def update_active_folders(vault: Path, folder: str, active: bool) -> None:
    path = vault / "_meta" / "active-folders.md"
    if not path.exists():
        print(f"[warn] {path} not found; active-folders.md not updated")
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    target_prefix = f"- {folder}/:"
    found = False
    for i, line in enumerate(lines):
        if line.startswith(target_prefix):
            lines[i] = f"- {folder}/: {'active' if active else 'inactive'}"
            found = True
            break
    if not found:
        lines.append(f"- {folder}/: {'active' if active else 'inactive'}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def git_commit(vault: Path, msg: str, paths: list[str] | None = None) -> bool:
    """Commit specific paths (relative to vault). Returns True on success.

    Never `git add -A` — schema-level commits must not sweep user's dirty WIP.
    On `--apply` operations, callers MUST treat False as fatal (exit non-zero).

    v0.5.6 (Hermes R5 B1 + I1):
    - Identity check goes through `git_identity_ok()` (the only Git-blessed
      way to recognise env-only identity), NOT the old `git config user.email`
      shortcut, which contradicted the v0.5.5 preflight and rejected legitimate
      CI env-only setups AFTER the vault had been mutated.
    - All tool-owned commits run with `commit.gpgsign=false --no-verify` so a
      user's gpg key / pre-commit hook cannot abort the commit after we
      already mutated the working tree. Tool-owned commits are deterministic
      schema/lint operations; bypassing hooks is intentional and documented
      in SKILL.md.

    Rollback on failure is the CALLER's responsibility (each `op_*` knows what
    it touched and uses `rollback_paths()` from `_manifest`).
    """
    if not (vault / ".git").exists():
        print("[error] vault is not a git repo; cannot auto-commit. "
              "Rerun init_vault.py without --skip-git, or `git init` in the vault.",
              file=sys.stderr)
        return False
    if not paths:
        print("[error] git_commit called without paths; refusing to sweep dirty WIP",
              file=sys.stderr)
        return False
    ok, reason = git_identity_ok(vault)
    if not ok:
        print(
            f"[error] git commit aborted: identity not resolvable — {reason}. "
            f"Configure: `git -C {vault} config user.email <you@example.com>` "
            f"and user.name; OR set GIT_AUTHOR_NAME/EMAIL + "
            f"GIT_COMMITTER_NAME/EMAIL in the environment.",
            file=sys.stderr,
        )
        return False
    subprocess.run(["git", "add", "--"] + paths, cwd=str(vault), check=False)
    rc = subprocess.run(
        ["git", *GIT_TOOL_COMMIT_ARGS, "commit", "-q", *GIT_COMMIT_NO_VERIFY, "-m", msg],
        cwd=str(vault), check=False,
    ).returncode
    if rc == 0:
        print(f"[git] committed: {msg}")
        return True
    print(f"[error] git commit failed (rc={rc}); check `git status` in {vault}",
          file=sys.stderr)
    return False


def git_commit_atomic(vault: Path, msg: str, paths: list[str]) -> bool:
    """Commit with path-scoped rollback on failure.

    Captures HEAD before commit. If the commit fails (signing/hooks/disk/etc.),
    every path in `paths` is reverted to its HEAD state (or removed if it's
    new since HEAD) via `rollback_paths()`. This preserves the v0.5.6
    rollback contract: failed schema ops leave the vault as it was, not
    half-mutated.

    Callers that have ALREADY done filesystem mutation should call this
    instead of `git_commit()` and pass the SAME `paths` list that describes
    what was changed.
    """
    pre_head = head_snapshot(vault)
    ok = git_commit(vault, msg, paths)
    if ok:
        return True
    print(f"[rollback] commit failed — restoring {len(paths)} path(s) to pre-mutation state",
          file=sys.stderr)
    rollback_paths(vault, pre_head, paths)
    return False


# ---- operations ------------------------------------------------------------

def op_enable(vault: Path, folder: str, apply: bool) -> int:
    if folder not in LAYER2:
        print(f"unknown folder: {folder}. Must be one of: {', '.join(LAYER2)}", file=sys.stderr)
        return 1
    target = vault / folder
    exists = target.exists()
    print("=== enable preview ===")
    print(f"  folder: {folder}/")
    print(f"  current state: {'exists' if exists else 'absent'}")
    if exists:
        print("  no-op: folder already exists; ensuring active-folders.md marks it active")
    else:
        print("  will create empty directory and mark active in active-folders.md")
    if not apply:
        print("\nDry-run only. Add --apply to perform changes.")
        return 0
    if not confirm_two_step(f"\nAbout to enable folder '{folder}/' in {vault}.", folder):
        print("aborted.")
        return 0
    # Hermes I1 fix: preflight BEFORE any mutation.
    rc = preflight_or_die(vault)
    if rc is not None:
        return rc
    target.mkdir(parents=True, exist_ok=True)
    update_active_folders(vault, folder, active=True)
    # .gitkeep ensures the otherwise-empty new folder is committable
    keep = target / ".gitkeep"
    if not keep.exists():
        keep.write_text("", encoding="utf-8")
    # v0.5.6: atomic — if commit fails, the new folder + active-folders edit
    # are rolled back. (Hermes R5 B1 + I1)
    ok = git_commit_atomic(
        vault,
        f"schema: enable {folder}/",
        paths=[folder, "_meta/active-folders.md"],
    )
    return 0 if ok else 3


def op_disable(vault: Path, folder: str, apply: bool) -> int:
    if folder not in LAYER2:
        print(f"unknown folder: {folder}. Must be one of: {', '.join(LAYER2)}", file=sys.stderr)
        return 1
    target = vault / folder
    if not target.exists():
        print(f"folder {folder}/ does not exist; nothing to disable.")
        return 0
    pages = list(target.rglob("*.md"))
    inbound = 0
    for p in all_pages(vault):
        for link in WIKILINK_RE.findall(p.read_text(encoding="utf-8")):
            if (target / f"{link}.md").exists():
                inbound += 1
    print("=== disable preview ===")
    print(f"  folder: {folder}/")
    print(f"  pages in folder: {len(pages)}")
    print(f"  inbound wikilinks from other pages: {inbound}")
    print(f"  will move contents to _archive/{folder}/ and mark inactive")
    if not apply:
        print("\nDry-run only. Add --apply to perform changes.")
        return 0
    if not confirm_two_step(
        f"\n[DESTRUCTIVE] About to archive {len(pages)} pages in '{folder}/' in {vault}.\n"
        f"  {inbound} inbound wikilinks will break unless updated.",
        folder,
    ):
        print("aborted.")
        return 0
    rc = preflight_or_die(vault)
    if rc is not None:
        return rc
    archive = vault / "_archive" / folder
    archive.parent.mkdir(parents=True, exist_ok=True)
    target.rename(archive)
    update_active_folders(vault, folder, active=False)
    # v0.5.6: atomic — if commit fails, restore folder/ from HEAD and remove
    # _archive/folder/. (Hermes R5 B1 + I1)
    ok = git_commit_atomic(
        vault,
        f"schema: disable {folder}/ (archived {len(pages)} pages; {inbound} links may break)",
        paths=[f"_archive/{folder}", folder, "_meta/active-folders.md"],
    )
    return 0 if ok else 3


def op_rename(vault: Path, src: str, dst: str, apply: bool, allow_custom: bool = False) -> int:
    if src not in LAYER2:
        print(f"source folder '{src}' is not a known Layer-2 folder. Must be one of: {', '.join(LAYER2)}", file=sys.stderr)
        return 1
    if dst not in LAYER2:
        if not allow_custom:
            print(
                f"destination folder '{dst}' is not a known Layer-2 folder. "
                f"Pass --allow-custom to bypass (rare; usually means schema drift). "
                f"Known folders: {', '.join(LAYER2)}",
                file=sys.stderr,
            )
            return 1
        # --allow-custom: still require slug grammar AND resolved path stays in vault.
        # Without this, `dst = "../escape"` or `dst = "/etc"` would move the folder
        # outside the vault sandbox (Hermes Round 3 blocker).
        try:
            validate_slug(dst, "rename dst (--allow-custom)")
            safe_resolve_inside(vault, dst, "rename dst (--allow-custom)")
        except ValidationError as e:
            print(f"[error] --allow-custom dst rejected: {e}", file=sys.stderr)
            return 2
    src_path = vault / src
    if not src_path.exists():
        print(f"source folder {src}/ does not exist in {vault}.", file=sys.stderr)
        return 1
    if (vault / dst).exists():
        print(f"destination folder {dst}/ already exists. Pick a new name.", file=sys.stderr)
        return 1
    pages = list(src_path.rglob("*.md"))
    wikilink_hits = 0
    for p in all_pages(vault):
        for link in WIKILINK_RE.findall(p.read_text(encoding="utf-8")):
            if (src_path / f"{link}.md").exists():
                wikilink_hits += 1
    print("=== rename preview ===")
    print(f"  {src}/ → {dst}/")
    print(f"  pages to move: {len(pages)}")
    print(f"  wikilink hits to update: {wikilink_hits}")
    print(f"  active-folders.md will be updated")
    if not apply:
        print("\nDry-run only. Add --apply to perform changes.")
        return 0
    if not confirm_two_step(
        f"\n[DESTRUCTIVE] About to rename {src}/ to {dst}/ in {vault}.\n"
        f"  {wikilink_hits} wikilink targets will need updating manually after rename.",
        f"{src}->{dst}",
    ):
        print("aborted.")
        return 0
    rc = preflight_or_die(vault)
    if rc is not None:
        return rc
    src_path.rename(vault / dst)
    update_active_folders(vault, src, active=False)
    update_active_folders(vault, dst, active=True)
    # v0.5.6: atomic — if commit fails, restore src/ from HEAD (which puts the
    # folder back to its original name and content) and remove dst/. (Hermes R5)
    ok = git_commit_atomic(
        vault,
        f"schema: rename {src}/ → {dst}/ ({len(pages)} pages; {wikilink_hits} links to review)",
        paths=[src, dst, "_meta/active-folders.md"],
    )
    print("\n[manual step] Update wikilinks that pointed at pages inside the old folder.")
    return 0 if ok else 3


def op_add_field(vault: Path, key: str, apply: bool) -> int:
    pages = all_pages(vault)
    missing = []
    for p in pages:
        m = FRONTMATTER_RE.match(p.read_text(encoding="utf-8"))
        if not m or f"\n{key}:" not in "\n" + m.group(1):
            missing.append(str(p.relative_to(vault)))
    print("=== add-frontmatter-field preview ===")
    print(f"  field: {key}")
    print(f"  pages missing it: {len(missing)} of {len(pages)}")
    for sample in missing[:10]:
        print(f"    - {sample}")
    if len(missing) > 10:
        print(f"    ... (+{len(missing)-10} more)")
    print("\nThis script does not auto-fill values; suggested workflow:")
    print(f"  1. Add `{key}` to SCHEMA.md frontmatter spec")
    print(f"  2. Run a one-time backfill (AI-assisted) from inside OpenClaw")
    print(f"  3. Re-run lint.py to confirm no pages still missing the field")
    if apply:
        print("\n[note] --apply ignored for this op; no automated mutation provided.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vault-path", required=True)
    sub = parser.add_subparsers(dest="op", required=True)

    for name in ("enable", "disable"):
        p = sub.add_parser(name)
        p.add_argument("folder")
        p.add_argument("--apply", action="store_true")

    p_rename = sub.add_parser("rename")
    p_rename.add_argument("src")
    p_rename.add_argument("dst")
    p_rename.add_argument("--apply", action="store_true")
    p_rename.add_argument("--allow-custom", action="store_true",
                          help="Allow renaming to a non-Layer-2 name (rare; usually wrong)")

    p_addf = sub.add_parser("add-frontmatter-field")
    p_addf.add_argument("key")
    p_addf.add_argument("--apply", action="store_true")

    args = parser.parse_args()
    vault = Path(args.vault_path).expanduser().resolve()
    if not vault.exists():
        print(
            f"vault not found: {vault}\n"
            f"  hint: create it with `python3 {Path(__file__).parent / 'init_vault.py'} "
            f"--vault-path {vault} --team <team> --domain \"<one line>\"`",
            file=sys.stderr,
        )
        return 1

    if args.op == "enable":
        return op_enable(vault, args.folder, args.apply)
    if args.op == "disable":
        return op_disable(vault, args.folder, args.apply)
    if args.op == "rename":
        return op_rename(vault, args.src, args.dst, args.apply, args.allow_custom)
    if args.op == "add-frontmatter-field":
        return op_add_field(vault, args.key, args.apply)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
