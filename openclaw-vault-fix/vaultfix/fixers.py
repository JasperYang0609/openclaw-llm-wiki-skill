"""The actual repair passes.

Each fixer is pure with respect to the filesystem: it reads, computes the new
content, and returns a `FileChange` describing the edit. Nothing is written
here — the CLI decides whether to apply, so dry-run and apply share identical
logic and there is no chance the preview diverges from what gets written.
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path

from .markdown import (
    first_h1,
    humanize_stem,
    parse_keys,
    split_frontmatter,
)
from .schema import (
    DEFAULT_SCALARS,
    LIST_FIELDS,
    REQUIRED_FRONTMATTER,
    SKIP_DIRS,
    SKIP_NAMES,
    TYPE_FROM_FOLDER,
)

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:\|[^\]]+)?\]\]")
AUTO_INDEX_HEADER = "## Auto-added by openclaw-vault-fix"


@dataclass
class FileChange:
    """A proposed edit to one file. `new_text is None` means no change."""
    path: Path
    fixer: str
    notes: list[str] = field(default_factory=list)
    new_text: str | None = None

    @property
    def changed(self) -> bool:
        return self.new_text is not None


def walk_vault_pages(vault: Path) -> list[Path]:
    """Knowledge pages only — same skip rules as lint.py's walker."""
    pages: list[Path] = []
    for path in sorted(vault.rglob("*.md")):
        rel = path.relative_to(vault)
        if rel.name in SKIP_NAMES:
            continue
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        pages.append(path)
    return pages


def _infer_type(vault: Path, page: Path) -> str:
    """Map the page's top-level folder to a singular `type:` value.

    Pages directly in the vault root, or under a non-Layer-2 folder, yield ""
    (present-but-empty) — enough to satisfy the linter's presence check while
    signalling that a human should fill it in.
    """
    rel = page.relative_to(vault)
    if len(rel.parts) < 2:
        return ""
    return TYPE_FROM_FOLDER.get(rel.parts[0], "")


def _field_value(name: str, *, vault: Path, page: Path, body: str, today: str) -> str:
    if name == "title":
        return first_h1(body) or humanize_stem(page.stem)
    if name == "created":
        mtime = datetime.date.fromtimestamp(page.stat().st_mtime)
        return mtime.isoformat()
    if name == "updated":
        return today
    if name == "type":
        return _infer_type(vault, page)
    if name in LIST_FIELDS:
        return "[]"
    if name in DEFAULT_SCALARS:
        return DEFAULT_SCALARS[name]
    return ""


def fix_frontmatter(vault: Path, page: Path, *, today: str | None = None) -> FileChange:
    """Add any missing required frontmatter fields, appending them so existing
    lines and formatting are left untouched."""
    today = today or datetime.date.today().isoformat()
    change = FileChange(path=page, fixer="frontmatter")
    text = page.read_text(encoding="utf-8")
    inner, body = split_frontmatter(text)

    present = set(parse_keys(inner)) if inner is not None else set()
    missing = [f for f in REQUIRED_FRONTMATTER if f not in present]
    if not missing:
        return change

    added_lines: list[str] = []
    for name in missing:
        value = _field_value(name, vault=vault, page=page, body=body, today=today)
        added_lines.append(f"{name}: {value}".rstrip())
        if name == "type" and value == "":
            change.notes.append("could not infer `type` from folder — set it manually")

    if inner is None:
        # No frontmatter at all: wrap the whole document in a fresh block.
        block = "\n".join(added_lines)
        change.new_text = f"---\n{block}\n---\n{text}"
        change.notes.insert(0, f"created frontmatter block with {len(missing)} field(s)")
    else:
        new_inner = inner + "\n" + "\n".join(added_lines)
        change.new_text = f"---\n{new_inner}\n---\n{body}"
        change.notes.insert(0, f"added {len(missing)} field(s): {', '.join(missing)}")
    return change


def fix_index_drift(vault: Path, pages: list[Path]) -> FileChange:
    """Append vault pages that are missing from index.md as `- [[stem]]` lines.

    Never removes entries (a listed-but-absent page may be an intentional
    placeholder or a typo a human should resolve) — only adds the unambiguous
    in-vault-not-in-index direction.
    """
    index_path = vault / "index.md"
    change = FileChange(path=index_path, fixer="index_drift")
    if not index_path.exists():
        change.notes.append("index.md missing — run init_vault.py to scaffold it; skipping")
        return change

    text = index_path.read_text(encoding="utf-8")
    listed = set(WIKILINK_RE.findall(text))
    actual = [p.stem for p in pages]
    missing = [stem for stem in actual if stem not in listed]
    if not missing:
        return change

    new_lines = [f"- [[{stem}]]" for stem in missing]
    if AUTO_INDEX_HEADER in text:
        body = text.rstrip("\n") + "\n" + "\n".join(new_lines) + "\n"
    else:
        sep = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        body = text + sep + f"{AUTO_INDEX_HEADER}\n" + "\n".join(new_lines) + "\n"
    change.new_text = body
    change.notes.append(f"added {len(missing)} missing entry(ies): {', '.join(missing)}")
    return change


def collect_changes(vault: Path, *, today: str | None = None) -> list[FileChange]:
    """Run every fixer over the vault and return only the changes that mutate
    a file (plus any informational no-op notes)."""
    pages = walk_vault_pages(vault)
    changes: list[FileChange] = []
    for page in pages:
        fc = fix_frontmatter(vault, page, today=today)
        if fc.changed or fc.notes:
            changes.append(fc)
    idx = fix_index_drift(vault, pages)
    if idx.changed or idx.notes:
        changes.append(idx)
    return changes
