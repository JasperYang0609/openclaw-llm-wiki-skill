# Changelog

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
