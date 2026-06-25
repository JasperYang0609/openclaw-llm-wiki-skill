# Changelog

## v0.4 — 2026-06-25

Adds the AI-runtime prompts for lint checks 11 and 12 (the two checks `lint.py` stubs).

**New: `openclaw-llm-wiki/prompts/`**
- `lint_missing_cross_refs.md` — agent prompt for lint check 11. Authorized batch auto-fill of `[[wikilinks]]` between related pages without per-pair admin approval (D16 / E19). Includes confidence scoring (high / medium / low), per-link insertion-context selection, Git auto-commit, and `do_not_lint: true` escape hatch.
- `lint_data_gaps.md` — agent prompt for lint check 12. Five gap-detection criteria, local-source-only auto-fill priority (lancedb → Discord → daily-backup → Notion → sibling vaults), at-most-1 auto-fill per page per run, reports remainder to `_meta/lint-data-gaps-YYYY-MM-DD.md`. **Never web-searches** (E20 mode b forbidden, hard guardrail).

**SKILL.md update**
- New `## AI-runtime lint checks (delegated to prompts/)` section explaining the prompts and when they are triggered (`@knowledge lint --auto-fix` in Discord, or weekly cron).
- Bundled-resources list now includes both prompt files.
- Version + outstanding-work footer updated to v0.4.

**README update**
- Lists the two new prompt files in Contents.
- Status section notes pilot ordering: Ansai own vault first (faster feedback loop), then Mifiya.

**Pilot ordering decision (2026-06-25)**
- Mifiya's data feedback loop is slow → Ansai's internal vault becomes the v0.4 pilot for prompt tuning.
- v0.5 will revisit prompt thresholds and gap-detection rules using Ansai pilot data.

### Outstanding for v0.5+

- Tune both prompts using Ansai pilot data (named-entity extraction quality, gap-detection precision, insertion-location heuristics)
- F23 pricing decision (deferred to Ansai team; early-stage clients onboard free during pilot)
- Smoke tests for the prompts (will need a fixture vault + golden output)

## v0.3 — 2026-06-25

Scripts and reference example brought in line with the v0.2 schema. SKILL.md / templates were not modified; this release is the implementation layer behind v0.2's design.

**`scripts/init_vault.py` (rewritten)**
- Creates 19-folder Layer-2 structure + `inbox/` + `_meta/` (folder-on-demand)
- Default enabled: Core 10 + `brand/` (11 folders)
- `--enable <folder>` repeatable to add more; `--all` enables all 19
- Initializes Git + makes first commit by default (skip with `--skip-git`)
- Writes `_meta/active-folders.md` and `_meta/lint-config.yaml`
- `--skip-lancedb` short-circuits the lancedb bootstrap for offline / smoke-test runs

**`scripts/lint.py` (new)**
- 9 schema-level checks fully implemented: broken wikilinks, orphan pages, frontmatter missing, tag drift (strict tier), index drift, stale pages, oversized pages, log size, lancedb freshness
- 1 Karpathy-pattern check approximated (`should_build_but_not_built` via hashtag/wikilink frequency)
- 2 Karpathy-pattern checks explicitly stubbed (`missing_cross_refs`, `data_gaps`) — they require an AI runtime and must run from inside an OpenClaw agent session
- `--json` for machine-readable output; `--auto-fix` flag accepted but no-ops in CLI (passes through to AI runtime)
- Appends a one-line summary to `log.md` after each run

**`scripts/migration_plan.py` (new)**
- Dry-run preview for `enable`, `disable`, `rename`, `add-frontmatter-field`
- `--apply` gated behind two-step confirmation for destructive ops (matches F24 guardrail #4)
- Auto-commits the change to Git when applied (matches F27 guardrail)
- Updates `_meta/active-folders.md` on enable/disable/rename

**`references/example-mifiya-schema.md` (rewritten)**
- Reflects the 8-field frontmatter
- Lists Mifiya-specific active folders (15 active of 19; metrics/vendors/templates/glossary inactive)
- Documents the `mifiya-daily-backup` ingest routing
- Adds privacy / embedding section (Mifiya supplies own Google API key)
- Adds off-boarding readiness section

### Outstanding for v0.4+

- Lint checks 11 (missing_cross_refs) and 12 (data_gaps) need an AI runtime implementation living in `openclaw-llm-wiki/prompts/`
- F23 pricing decision still deferred to Ansai team
- Smoke tests live in CI (not yet bundled)

## v0.2 — 2026-06-25

Schema and SKILL.md reflect the 30-question design alignment completed with Jasper on 2026-06-25.

### Highlights vs v0.1

**Sales / positioning**
- Customer-facing name standardized: **企業智庫 / Enterprise Knowledge Hub** (internal name unchanged: `openclaw-llm-wiki`)
- Three explicit user roles: employee (zero-onboarding) / boss / consultant admin

**Architecture / scope**
- Layer-2 categories expanded from 5 → **19** (Core 10 + Recommended 5 + Nice-to-have 4) + 2 system folders (`inbox/` + `_meta/`)
- Folder-on-demand: do not pre-create empty folders
- Skill scope deliberately narrowed: ingest pipeline is now fully delegated to `openclaw-discord-server-backup` + per-team `*-daily-backup` crons
- Search is dual: `openclaw-lancedb-knowledge` semantic + `grep` text, parallel + merged ranker (semantic 0.7 / text 0.3, boost on both-hit)
- Long-term plan: this skill unifies and replaces the legacy `wiki-maintainer` skill once Ansai internal vault is migrated

**Page rules**
- Build threshold: **1 source + AI substance filter** (was 2+ sources). Captures "important things only discussed once" while filtering chit-chat
- Frontmatter: **8 required fields** (added `confidence`, `wikilinks_confidence`, `categories`)
- Tag taxonomy: mixed strictness (strict for customer/product/Layer-2 type names; loose for time/sentiment/ad-hoc)
- Wikilinks: AI auto-fills, **no minimum count enforced**; orphan lint as fallback

**Query (Discord-first)**
- Discord chat is the only UI (no CLI, no Web UI in v1.0)
- Semi-RAG: AI auto-retrieves relevant vault pages based on conversation context
- Output formats: structured lists with bold/emoji/grouping — **no Markdown tables** (they break on Discord), no charts, no Marp; complex outputs delegated to GPT / Notion

**Lint**
- 12 checks total (was 9): added Karpathy-pattern checks for **應建未建 (should-build-but-not-built)**, **missing cross-refs** (AI auto-fills without admin review), and **data gaps** (local-source first auto-fill; never web-searches)
- Schedule: weekly cron + on-demand via Discord

**Governance / privacy**
- Git auto-commit always on; consultants never run Git commands
- Schema evolution: 5 admin guardrails (role-gated / preview / rollback / two-step destructive / auto-notify consultant)
- Embedding default: Gemini via lancedb skill; **client supplies their own Google API key** at onboarding (also makes off-boarding clean)
- Off-boarding: vault is portable markdown, zip on request; no vendor lock-in

**Deferred to Ansai team**
- Pricing model (bundle vs add-on) — likely add-on pack, finalized in team planning

### Outstanding for v0.3

- Rewrite `scripts/init_vault.py` for 19-folder structure + Git auto-commit init
- Add `scripts/lint.py` covering all 12 checks
- Add `scripts/migration_plan.py` for schema evolution preview
- Update `references/example-mifiya-schema.md` to v0.2 schema

## v0.1 — 2026-06-15

Initial draft. Five-category Layer-2 (entities / concepts / comparisons / syntheses / queries). Single-vault-per-deployment architecture. Search delegated to `openclaw-lancedb-knowledge`. Coexisted with `wiki-maintainer`.
