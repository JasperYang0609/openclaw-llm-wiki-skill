# openclaw-vault-fix

Auto-repair for [OpenClaw LLM Wiki](https://github.com/JasperYang0609/openclaw-llm-wiki-skill) vaults.

The `openclaw-llm-wiki` skill ships a `lint.py` that **reports** schema problems
but deliberately never touches the vault. `openclaw-vault-fix` is the
complementary layer: it takes the safe, deterministic subset of those findings
and **repairs them in place**, with a dry-run preview by default.

It is a standalone Python tool — no dependency on the skill, no third-party
packages (only `pytest` for the test suite).

## What it fixes

| lint finding | what this tool does |
|---|---|
| `frontmatter_missing` | Adds any of the 9 required frontmatter fields that are absent. Infers `title` (from the first `# H1`, else the humanized filename), `type` (from the Layer-2 folder), `created` (file mtime) and `updated` (today). List fields default to `[]`; `confidence` / `wikilinks_confidence` default to `low` so machine-completed pages are visible at a glance. |
| `index_drift` | Appends vault pages that are missing from `index.md` as `- [[stem]]` lines under an `## Auto-added by openclaw-vault-fix` heading. |

**Conservative by design.** It only ever *appends* — existing frontmatter
lines, formatting, and comments are preserved untouched, and index entries are
never removed. Findings that need human or AI judgement (broken wikilinks, tag
drift, contradictions, the AI-only checks) are left to `lint.py` and the skill's
agent runtime.

## Usage

Requires Python 3.9+.

```bash
# Preview (default — writes nothing, exits 2 if there are fixable issues)
python3 fix.py --vault-path ~/.openclaw/wiki/team

# Apply the fixes
python3 fix.py --vault-path ~/.openclaw/wiki/team --apply

# Run a single fixer
python3 fix.py --vault-path ~/.openclaw/wiki/team --only frontmatter

# Machine-readable output (for CI / cron)
python3 fix.py --vault-path ~/.openclaw/wiki/team --json
```

### Exit codes

| code | meaning |
|---|---|
| `0` | nothing to fix, or `--apply` succeeded |
| `1` | vault not found / usage error |
| `2` | dry-run found fixable issues (none written) |

The `2` exit makes it usable as a CI gate: run without `--apply` and fail the
job if the vault has un-repaired drift.

## Recommended flow

```bash
python3 openclaw-llm-wiki/scripts/lint.py  --vault-path VAULT   # see what's wrong
python3 openclaw-vault-fix/fix.py          --vault-path VAULT   # preview the fix
python3 openclaw-vault-fix/fix.py          --vault-path VAULT --apply
python3 openclaw-llm-wiki/scripts/lint.py  --vault-path VAULT   # confirm it's clean
```

Everything `fix.py` writes is designed to round-trip cleanly back through the
skill's `lint.py` parser.

## Tests

```bash
pip install pytest
pytest tests/
```

16 tests covering frontmatter inference, append-only preservation, index drift,
idempotency, and the CLI exit-code contract.

## Layout

```
fix.py                 CLI entry point
vaultfix/
  schema.py            required fields + folder→type map (mirrors the skill's _manifest.py)
  markdown.py          tolerant frontmatter parse (same shape as lint.py)
  fixers.py            the repair passes — pure, return-a-change, never write
tests/                 pytest suite
```

## Keeping in sync

`vaultfix/schema.py` duplicates `REQUIRED_FRONTMATTER` and `TYPE_FROM_FOLDER`
from the skill's `openclaw-llm-wiki/scripts/_manifest.py`. If the skill adds a
folder or a required field, update `schema.py` to match.

## License

MIT — see [LICENSE](LICENSE).
