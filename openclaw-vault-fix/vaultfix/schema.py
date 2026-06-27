"""Schema constants for OpenClaw LLM Wiki vaults.

Mirrors `openclaw-llm-wiki/scripts/_manifest.py` (REQUIRED_FRONTMATTER,
TYPE_FROM_FOLDER). Kept as an independent copy so this tool has no import
dependency on the skill, but the two MUST stay in sync — if the skill adds a
21st folder or a 10th required field, update both.
"""
from __future__ import annotations

# Plural Layer-2 folder name -> singular `type:` value in frontmatter.
TYPE_FROM_FOLDER: dict[str, str] = {
    "decisions": "decision", "sops": "sop", "customers": "customer",
    "products": "product", "contacts": "contact", "people": "person",
    "concepts": "concept", "comparisons": "comparison", "syntheses": "synthesis",
    "queries": "query", "brand": "brand", "policies": "policy",
    "deliverables": "deliverable", "meetings": "meeting", "incidents": "incident",
    "metrics": "metric", "vendors": "vendor", "templates": "template",
    "glossary": "glossary", "summaries": "summary",
}

# The 9 required frontmatter fields every page must carry.
REQUIRED_FRONTMATTER: tuple[str, ...] = (
    "title", "created", "updated", "type", "tags", "sources",
    "confidence", "wikilinks_confidence", "categories",
)

# Fields whose natural empty value is a YAML inline list rather than a scalar.
LIST_FIELDS: frozenset[str] = frozenset({"tags", "sources", "categories"})

# Default scalar values used when a field is missing and cannot be inferred.
# `confidence` / `wikilinks_confidence` default to "low" so an operator can
# see at a glance which pages were machine-completed rather than human-curated.
DEFAULT_SCALARS: dict[str, str] = {
    "confidence": "low",
    "wikilinks_confidence": "low",
}

# Files in the vault root that are scaffolding, not knowledge pages — skip them
# exactly the way lint.py's walk_vault_pages does.
SKIP_NAMES: frozenset[str] = frozenset({
    "SCHEMA.md", "CLAUDE.md", "AGENTS.md", "index.md", "log.md", "overview.md",
})
SKIP_DIRS: frozenset[str] = frozenset({".git", "_archive", "inbox", "_meta"})
