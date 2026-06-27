"""openclaw-vault-fix — auto-repair for OpenClaw LLM Wiki vaults.

The sibling skill `openclaw-llm-wiki` ships a `lint.py` that *reports* schema
problems but deliberately never mutates the vault. This package is the
complementary auto-fix layer: it takes the safe, deterministic subset of those
findings (missing required frontmatter, index drift) and repairs them in place,
with a dry-run preview by default.

It is intentionally standalone (no import from the skill) so it can be vendored
or run on its own, but the schema constants in `vaultfix.schema` mirror the
skill's `_manifest.py` and must be kept in sync.
"""

__version__ = "0.1.0"
