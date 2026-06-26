# Hermes Round 4 findings — disposition record

> **Purpose**: enumerate every R4 minor (M1–M5) so future reviewers can audit
> the changelog without chasing Discord attachments. Created in v0.5.6
> (Hermes R5 M4) as the missing release-traceability artifact.

## Source

- **Reviewer**: Hermes
- **Date**: 2026-06-25
- **Round**: 4 (against v0.5.4, commit `b56e34e`)
- **Counts**: 0 blocker + 5 important + 5 minor + 3/11 R3 fixes flagged partial
- **Original report**: Discord attachment (see channel `#llm Wiki 架構研究` message
  containing `openclaw_llm_wiki_skill_round4_review_hermes.md`)

## Important (I1–I5) — all addressed in v0.5.5 (commit `197604a`)

These are summarized in the v0.5.5 commit message and `CHANGELOG.md`; not
repeated here.

## Minor (M1–M5) — disposition

| # | Finding | Disposition | Commit | Notes |
|---|---|---|---|---|
| M1 | `lint.check_lancedb_freshness` referenced `{vault.name}-lancedb`, while `init_vault` wrote `{team}-lancedb`. Mismatch when vault dir name differs from team slug. | **Fixed in v0.5.5** | `197604a` | Added `_meta/lancedb-config.yaml` with `target_dir_basename`; lint reads it, falls back to `vault.name` only if missing. Regression test `test_v055_lancedb_naming_uses_team_slug_not_vault_name`. |
| M2 | Some `lint.py` checks returned a `dict` while others returned a `list`; `--fail-on-issues` only counted lists, so `index_drift` / `log_size` / `lancedb_freshness` / `should_build` regressions did not flip exit code. | **Fixed in v0.5.4** | `b56e34e` | `lint.py --fail-on-issues` was added in v0.5.4 alongside dict-handling. Hermes R4 confirmed correct; nothing further to do. |
| M3 | `prompts/lint_missing_cross_refs.md` confidence-scoring used the prose `"low > medium > high"` inverted from intuition. | **Fixed in v0.5.4** | `b56e34e` | Rewritten as explicit truth table with `low < medium < high`. Hermes R4 confirmed correct. |
| M4 | `templates/log.md` still referenced the v0.1 layout (`raw/`, `entities/` folders). | **Fixed in v0.5.4** | `b56e34e` | Replaced with the v0.5.4 layout. Hermes R4 confirmed correct. |
| M5 | `validate_slug` docstring rejected all-digit and leading-digit slugs, contradicting the actual grammar `^[a-z0-9]+(?:-[a-z0-9]+)*$`. | **Fixed in v0.5.5** | `197604a` | Docstring corrected to match grammar (accepts `2026q1`, `123`, `1team`). |

## Why this file exists

Hermes R5 minor M4 noted:

> R5 brief says Round 4 found 5 minor items, but the "fixed in v0.5.5"
> section only names M1 and M5. The repository artifacts I reviewed do not
> include the R4 report attachment, so the other three minor items are not
> auditable from the repo alone.

`reviews/round4_findings.md` (this file) closes that traceability gap by
enumerating all 5 R4 minors and their disposition with commits cited. From
v0.5.6 onwards, every Round N review of consequence will get a sibling
`reviews/roundN_findings.md` so the repo stays self-auditable.
