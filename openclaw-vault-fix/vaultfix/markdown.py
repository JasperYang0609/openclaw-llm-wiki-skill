"""Frontmatter parsing helpers.

The parser is deliberately the same tolerant, regex-driven shape as the skill's
`lint.py` so that anything this tool writes round-trips cleanly back through the
linter. We only ever *append* missing keys to an existing frontmatter block —
never reorder or rewrite the operator's existing lines — so hand-formatting and
comments are preserved.
"""
from __future__ import annotations

import re

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (frontmatter_inner, rest_of_document).

    `frontmatter_inner` is the text *between* the `---` fences (no fences), or
    None if the document has no frontmatter block. `rest_of_document` is
    everything after the closing fence (or the whole document when there is no
    block).
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def parse_keys(frontmatter_inner: str) -> dict[str, str]:
    """Extract top-level `key: value` pairs from a frontmatter block.

    Block-list values (`key:` then indented `- item` lines) collapse to a
    comma-joined string, matching lint.py. We only need key presence and scalar
    values, so this is intentionally not a full YAML parser.
    """
    fm: dict[str, str] = {}
    lines = frontmatter_inner.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" not in line or line.lstrip().startswith("#"):
            i += 1
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value == "":
            collected: list[str] = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                stripped = nxt.lstrip()
                if stripped.startswith("- "):
                    collected.append(stripped[2:].strip())
                    j += 1
                elif nxt.startswith((" ", "\t")):
                    j += 1
                else:
                    break
            fm[key] = ", ".join(collected) if collected else ""
            i = j
            continue
        fm[key] = value
        i += 1
    return fm


def first_h1(body: str) -> str | None:
    """Return the text of the first `# Heading`, if any."""
    m = H1_RE.search(body)
    return m.group(1).strip() if m else None


def humanize_stem(stem: str) -> str:
    """`mifiya-q1-launch` -> `Mifiya Q1 Launch` for a fallback title."""
    words = re.split(r"[-_]+", stem.strip())
    return " ".join(w[:1].upper() + w[1:] if w else w for w in words if w) or stem
