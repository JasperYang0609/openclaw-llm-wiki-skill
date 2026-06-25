---
name: openclaw-llm-wiki
description: Operate a team knowledge base (對外名稱「企業智庫」) as an interlinked Markdown vault. One vault per OpenClaw deployment (mifiya, laike, fangchengshi, ansai, or future clients). Scope = vault schema + AI classification + link maintenance + lint. Ingest pipeline is delegated to `openclaw-discord-server-backup` and team-specific daily-backup crons; semantic search is delegated to `openclaw-lancedb-knowledge`. Provides Discord-first Query, source-cited answers, and schema-enforced consistency. Use when the user asks to set up a team wiki, query the knowledge base, lint or audit the wiki, evolve the schema, or migrate scattered docs into a structured vault.
---

# OpenClaw LLM Wiki

Team knowledge base (sales label: **企業智庫 / Enterprise Knowledge Hub**) as a Markdown vault. Built on Karpathy's LLM Wiki pattern, productized for OpenClaw deployments. **One vault per OpenClaw deployment** — each client team gets their own; Ansai itself is also a client of this skill.

```
sources (Discord backups, daily-backup summaries, Notion, URLs, PDFs)
  → openclaw-discord-server-backup / *-daily-backup crons (delegated ingest)
  → inbox/ (AI confidence-gated staging)
  → classified into 20 Layer-2 folders (this skill's core job)
  → openclaw-lancedb-knowledge + grep (delegated dual search)
  → Discord-first source-cited answers
```

## Scope

**IN scope (this skill owns):**
- Vault schema (folder taxonomy, frontmatter, tag rules)
- AI-driven classification into Layer-2 folders
- Wikilink auto-creation and cross-reference maintenance
- Lint (應建未建 / missing cross-refs / data gaps / orphan / stale)
- Schema evolution governance (5 guardrails)
- Discord-first query formatting

**OUT of scope (delegated):**
- Ingest pipeline → `openclaw-discord-server-backup`, per-team `*-daily-backup` crons
- Semantic search → `openclaw-lancedb-knowledge` (Gemini embedding default)
- Text search → `grep` (run in parallel with lancedb, merged ranker)
- Large binaries → external storage (Drive / Dropbox); vault only stores links

**Not a replacement** for Notion / Drive / Chat. Complementary: this skill owns "company knowledge for AI retrieval"; Notion stays for collaborative docs, Drive stays for files, Chat stays for conversations.

## Roles

Three tiers (zero overlap):

| Role | What they do |
|---|---|
| **Employee** | Query in Discord. **Zero onboarding.** They only learn "how to ask the knowledge base." |
| **Boss** | Same as employee + reviews periodic lint reports + signs off on schema changes the admin proposes |
| **Consultant admin** | Owns schema design (onboarding), monitors lint, approves AI suggestions, executes major migrations |

All schema setup is done by consultant admin in collaboration with the boss; employees never touch the schema.

## Activation triggers

- User asks to create, set up, or initialize a team wiki / knowledge base / 企業智庫
- User asks a question in Discord and a vault exists for the team (AI auto-retrieves via RAG)
- User asks to lint / audit / health-check the wiki
- User asks to evolve / change / extend the schema
- User references "the team wiki", "the knowledge base", "企業智庫", "our notes"

## Vault location

Single vault per OpenClaw deployment. Default path:

```
~/.openclaw/wiki/team/
```

Override via env var `OPENCLAW_WIKI_TEAM_PATH` or `--vault-path` argument.

**Long-term plan:** This skill unifies and replaces the legacy `wiki-maintainer` skill (which managed Ansai's internal vault). Transition state: short-term coexist; once v1.0 is shipped and Ansai's internal vault is migrated to the new schema, `wiki-maintainer` will be retired.

## Architecture: vault structure

```
<vault>/
├── _meta/                  # System: schema files, taxonomy, permission, lint config (admin only)
├── inbox/                  # System: low-confidence ingest staging, awaiting AI/admin promotion
├── SCHEMA.md               # Team domain, taxonomy, thresholds, exceptions
├── index.md                # Catalog of all wiki pages by Layer-2 category
├── log.md                  # Append-only chronological action log (auto-commit by Git)
│
│   # === Core 10 (must-have, business-language naming) ===
├── decisions/              # Company decisions, judgment basis
├── sops/                   # Standard operating procedures, playbooks
├── customers/              # Customer profiles, project history
├── products/               # Product knowledge, specs
├── contacts/               # External contacts, partners
├── people/                 # Internal team, boss views, roles
├── concepts/               # Concepts, terminology, jargon
├── comparisons/            # Side-by-side analyses (A vs B)
├── syntheses/              # Multi-source consolidated takes
├── queries/                # Filed Q&A worth keeping
│
│   # === Highly recommended 5 (open if team needs) ===
├── brand/                  # Brand voice, visual guidelines (critical for marketing-consulting teams)
├── policies/               # HR policies, org chart, compliance
├── deliverables/           # Past reports / proposals (reusable across clients)
├── meetings/               # Meeting transcripts, consensus records
├── incidents/              # Lessons learned, post-mortems
│
│   # === Nice-to-have 5 (only if needed) ===
├── metrics/                # KPI definitions, formulas
├── vendors/                # Suppliers, outsourced partners, tools
├── templates/              # Forms, contract templates, proposal templates
├── glossary/               # Industry-specific terminology dictionary
└── summaries/              # Per-source one-pagers (Karpathy v1 digest pattern)
```

**Folder-on-demand rule:** Do NOT pre-create empty folders. Onboarding only creates the folders the team will actually use. Small teams may run with just Core 10 + brand/.

## Layer model

- **Layer 1 (inbox/, source backups via lancedb skill):** raw evidence; agent reads, never modifies, never deletes
- **Layer 2 (decisions/, sops/, ... — the 20 folders):** agent-curated, cross-referenced, schema-enforced
- **Layer 3 (_meta/, SCHEMA.md):** rules — domain definition, taxonomy, thresholds, guardrails

## Orient before acting (every session)

When invoked against an existing vault:

1. Read `SCHEMA.md` — team domain, conventions, taxonomy, thresholds
2. Read `_meta/` config files — active folders, lint rules, governance settings
3. Read `index.md` — what pages exist by category
4. Read last 30 lines of `log.md` — recent activity
5. For vaults with 100+ pages, run a dual search (lancedb + grep) for the topic at hand before creating anything new

Skipping orient causes duplicate pages, missed cross-references, and tag drift.

## Page rules

### Build threshold

**1 source + AI filter.** Build a page when even a single source mentions something AND AI judges it has substance.

- ✅ Build: factual statement, decision, named entity, specific commitment, lesson learned
- ❌ Filter out: pure chit-chat, emojis, reactions, acknowledgments, off-topic banter
- Mark single-source pages with `single_source: true` for lint to potentially upgrade later

This is intentionally permissive — "things discussed only once" are often the most important (boss decisions, customer-specific commitments, one-off lessons). AI filter prevents pure noise.

### Frontmatter (8 fields, ALL required)

```yaml
---
title: Page title in plain language
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: decision | sop | customer | product | contact | person | concept | comparison | synthesis | query | brand | policy | deliverable | meeting | incident | metric | vendor | template | glossary
tags: [from-taxonomy, ...]
sources: [path/to/raw-source, ...]
confidence: low | medium | high   # low = single source, high = 3+ sources cross-validated
wikilinks_confidence: low | medium | high   # AI's confidence in auto-added wikilinks
categories: [primary-folder, secondary-folder-if-multi]   # supports multi-category placement
---
```

Pages missing required fields are rejected back to `inbox/` for admin/AI to complete.

### Tag taxonomy (mixed strictness)

- **Strict tier (must be pre-registered in SCHEMA.md):** customer names, product names, Layer-2 types — prevents synonyms like `#客戶` / `#客戶資料` / `#客戶端`
- **Loose tier (free-form OK):** time-based, sentiment, ad-hoc descriptors

### Wikilinks (AI auto-fills)

- **No minimum link count enforced** — does not block page creation
- AI adds candidate links at page creation time, each tagged with confidence
- Low-confidence links get visible ⚠ marker on the page for admin review
- Weekly lint scans orphan pages as fallback safety net

## Core operations

### Ingest (delegated, automation-only)

This skill does NOT run ingest. Sources flow in via:

- **`openclaw-discord-server-backup`** — channel-by-channel cron with V3 cursor state
- **per-team `*-daily-backup`** crons (e.g. `mifiya-daily-backup`) — already produce curated summaries
- **`openclaw-lancedb-knowledge`** — incremental indexing

This skill's role on ingest = receive the produced summaries, run AI classification, place in the right Layer-2 folder, fill frontmatter, auto-link.

**Triggering:** automation-only (no manual triggers from employees). Admin/consultant "补data" path = drop the resource into a watched source (Discord channel, Notion page, vault file) and wait for the next cron cycle.

**Source-specific routing:**

- Daily-backup summaries (Ansai + every client team) → routed directly to vault, classified, no extra AI filter (they are already curated)
- Raw Discord messages → routed through inbox/ → AI filter (single-source rule) → vault
- Notion pages → routed similarly to Discord raw
- URLs / PDFs (phase 2) → admin-injected, similar to Notion

### Query (Discord-first, semi-RAG)

When the team asks a question:

1. **AI auto-retrieves** relevant vault pages via dual search (lancedb + grep, parallel, merged rank) — based on conversation context, not requiring explicit `@knowledge` invocation
2. **Synthesize** answer grounded in retrieved pages; cite source paths
3. **Format for Discord** — structured lists with bold / emoji / indentation / dash alignment; no Markdown tables (they break on Discord); 1–2 columns = single list, 3+ columns = grouped display
4. **For complex outputs** (charts, slides), delegate to other skills: "ask OpenClaw to generate a Notion report" or "ask GPT to generate an image"
5. **File valuable answers back** to `queries/` if synthesis is substantial
6. **Log** the query and whether it was filed; track hit/miss for the "employee query hit rate" north-star metric

If the dual search returns weak hits, say so explicitly and either widen the search or tell the user the vault lacks coverage on this topic (which itself becomes a `data gaps` lint signal).

### Lint (cron + on-demand)

Run weekly cron + admin can trigger anytime via Discord (`@knowledge lint`).

**Schema-level checks:**
1. **Broken wikilinks** — `[[target]]` where target doesn't exist
2. **Orphan pages** — no inbound links from any other page
3. **Frontmatter missing** — pages without required 8 fields → returned to `inbox/`
4. **Tag drift** — strict-tier tags used but not in SCHEMA's taxonomy
5. **Index drift** — vault files not in `index.md`, or index entries with no file
6. **Stale pages** — `updated` >90 days older than most recent source mentioning same entities
7. **Oversized pages** — >200 lines, candidate for splitting
8. **Log size** — rotate when `log.md` > 500 entries
9. **lancedb freshness** — flag if index older than last vault modification

**Karpathy-pattern checks (additions beyond classic lint):**
10. **應建未建 (should-build-but-not-built)** — topics that 2+ sources mention but no page exists; lists for consultant review
11. **Missing cross-references** — same-topic pages not interlinked; AI auto-links without consultant review (matches D16 / E19)
12. **Data gaps** — topics where existing pages are skeletal; reports candidates + auto-searches local sources first (other vaults, lancedb index, Discord history); never web-searches
13. **Contradictions** — scan `contradictions: [...]` frontmatter for: target page missing, one-sided pairing (target does not flag back), or unresolved for >30 days. Reports for admin to resolve (no auto-fix; contradictions need human judgment).

Append `## [YYYY-MM-DD] lint | N issues found | M auto-fixed` to log.md.

### Schema evolution

Initial schema design = consultant admin works with boss during onboarding.

After onboarding, the client admin can self-serve schema changes (add categories, adjust thresholds, taxonomy). **5 guardrails (all built-in):**

1. **Role-gated:** only admin role can edit schema (employees cannot)
2. **Preview before commit:** show "this change will affect X pages and Y links"
3. **Rollback via Git** (see Governance below)
4. **Two-step confirmation** for destructive ops: deleting a folder, changing `type`, modifying required frontmatter fields
5. **Notify consultant:** any admin-side schema change auto-pings consultant Discord (no approval required, just visibility)

## Governance

### Git auto-commit (always on)

Vaults are Git-tracked from initialization. Every action (page create / update / delete / schema change) is auto-committed. Consultants don't need to know Git commands — the skill wraps it transparently.

- Conflicts trigger automatic merge attempt; on failure, prompts admin
- Rollback path: any past commit can be restored via `@knowledge rollback <commit-id>`

### Privacy / embedding

- **Default:** Gemini embedding via `openclaw-lancedb-knowledge`. Required because client teams already use this pipeline successfully and the recall improvement directly supports the "employee query hit rate" north-star metric.
- **Client uses their own Google API key** — set at onboarding. This both keeps cost-of-embedding off Ansai's ledger AND makes off-boarding clean (client takes the key with them, no migration needed).
- Privacy-strict clients can switch to local hash embedding (lancedb skill supports it) — accept the recall hit.
- Secret redaction runs before any text is sent to Gemini (lancedb skill enforces this).

### Off-boarding

Vault is portable by design:
- It IS just markdown files in 20 folders
- Client receives a zip on request
- They can rebuild the lancedb index with their own API key (lancedb is open source)
- No vendor lock-in

## Search delegation

This skill delegates ALL search to other skills; nothing runs here directly.

- Each team's vault gets one lancedb project: `--project <team-name>`
- Bootstrap runs `bootstrap_openclaw_lancedb.py` with the vault path as `--workspace`
- Incremental indexing runs via lancedb skill cron, plus after each manual schema migration
- Query operations call dual search: lancedb (semantic) + grep (text), in parallel, merged ranker
  - v1.0 merge rule: pages hit by both score get a boost; otherwise weighted blend (semantic 0.7, text 0.3)
  - v1.x: refine ranker once usage data exists

## Viewer

The vault is plain markdown. Choose any viewer if you want to browse files directly. In practice, daily querying happens through OpenClaw / Discord — that path is always faster. The vault is optimized for AI consumption, not human browsing.

## Workflow patterns

### Schema migration

When categories are added/renamed/removed:
1. Stop ingestion crons (admin via Discord)
2. Generate migration plan via `scripts/migration_plan.py` (preview the impact)
3. Get admin two-step confirmation
4. Run migration (auto-committed in Git)
5. Re-trigger incremental lancedb indexing
6. Resume crons
7. Notify consultant

### Bulk classification of historical inbox

When inbox/ accumulates (e.g. after backfill or migration):
1. Run AI batch classification with confidence threshold
2. High-confidence → directly into Layer-2 folders
3. Low-confidence → stays in inbox/ with reason annotation
4. Admin reviews low-confidence queue weekly

### Contradictions

When new info conflicts with existing content:
1. Check dates — newer generally supersedes older
2. If genuinely contradictory, keep both positions with dates and sources
3. Mark in frontmatter: `contradictions: [other-page-name]`
4. Flag for review in the next lint report

## Pitfalls

- **Vault is for AI, not humans** — do not optimize for human browsability; optimize for AI retrieval and citation accuracy
- **Never modify `inbox/` files manually** — let the AI promote them via classification; manual edits desync the pipeline
- **Always orient first** — read SCHEMA + index + recent log + `_meta/` before any operation in a fresh session
- **Folder-on-demand** — do not pre-create all 20 folders for every client; only what they need
- **Frontmatter is non-negotiable** — missing fields = page goes back to inbox/
- **Strict-tier tags require SCHEMA registration first** — never invent customer or product tags on the fly
- **Don't index secrets** — `.env`, tokens, credentials are excluded by `openclaw-lancedb-knowledge` by default; don't override
- **Don't run ingest pipeline from here** — that's `openclaw-discord-server-backup` and `*-daily-backup` crons' job
- **Don't host multiple teams in one vault** — each client deploys their own OpenClaw with their own vault
- **Don't break Git auto-commit** — every action must commit; bypassing breaks rollback safety
- **Don't web-search for data gaps** — local-only auto-fill (lint check 12); web search risks introducing unverified content

## Bundled resources

- `templates/SCHEMA.md` — domain-agnostic SCHEMA with placeholders, customized at init
- `templates/CLAUDE.md` — agent entry-point pointer for Claude Code (auto-loaded when an agent session starts in the vault directory)
- `templates/AGENTS.md` — agent entry-point pointer for OpenAI Codex / ChatGPT Codex (auto-loaded equivalent); mirrors CLAUDE.md so all daily-backup crons running on Codex find the vault schema correctly
- `templates/index.md` — initial 20-category sectioned index
- `templates/log.md` — initial log entry
- `templates/overview.md` — top-level synthesis page, regenerated periodically (monthly cron)
- `scripts/init_vault.py` — vault bootstrap (20 folders + Git auto-commit + lancedb wiring + CLAUDE.md + overview.md scaffold)
- `scripts/lint.py` — 13-check lint runner (10 schema-level fully implemented; 2 AI-required delegated to `prompts/`; 1 contradictions scan added v0.5)
- `scripts/migration_plan.py` — schema-change preview & apply (two-step confirm, Git auto-commit)
- `prompts/lint_missing_cross_refs.md` — AI prompt for lint check 11
- `prompts/lint_data_gaps.md` — AI prompt for lint check 12 (local sources only; never web search)
- `references/example-mifiya-schema.md` — filled-in SCHEMA reference for a marketing-consulting team

## AI-runtime lint checks (delegated to prompts/)

Lint checks 11 (`missing_cross_refs`) and 12 (`data_gaps`) require AI reasoning over vault contents — they cannot run as plain Python. When `scripts/lint.py` reaches those checks it emits a "stub" notice and points at:

- `prompts/lint_missing_cross_refs.md` — auto-add wikilinks between related pages (D16 / E19 authorized batch auto-fill; no per-pair approval)
- `prompts/lint_data_gaps.md` — fill skeletal pages from **local sources only** (lancedb / Discord backups / daily-backup / Notion / sibling vaults if permitted). **Never web-search** (E20 mode b is forbidden).

When the user triggers `@knowledge lint --auto-fix` in Discord (or as part of the weekly cron), the agent reads these prompt files and executes them against the vault. Both prompts include hard guardrails (skip `inbox/_archive/_meta`, Git auto-commit, never fabricate, etc.).

## Karpathy v1 / v2 alignment

This skill is a productized OpenClaw-native version of [Karpathy's LLM Wiki pattern (2026-02, gist)](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) with extensions inspired by [rohitg00's v2 fork](https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2). Alignment summary:

| Karpathy v1 / v2 | This skill (v0.5) |
|---|---|
| 3 layers (raw / wiki / schema) | ✅ inbox+lancedb / 19+1 folders / SCHEMA.md + _meta/ |
| Workflows Ingest / Query / Lint | ✅ Ingest delegated, Query Discord-first, Lint 13 checks |
| `index.md` + `log.md` | ✅ both, with timestamped prefixes |
| Wikilinks for cross-refs | ✅ AI auto-fills (no minimum enforced) |
| Schema doc auto-loaded by agent | ✅ `CLAUDE.md` (Claude Code) + `AGENTS.md` (Codex) aliases both point at `SCHEMA.md` |
| Per-source summaries | ✅ optional `summaries/` Layer-2 folder (v0.5) |
| Top-level overview page | ✅ `overview.md` (v0.5, regenerated periodically) |
| Contradiction detection | ✅ frontmatter + lint check 13 (v0.5) |
| Confidence scoring (v2 add-on) | ✅ `confidence` frontmatter field (D17) |
| Supersession of stale claims (v2) | ✅ stale-page lint + contradiction handling |
| Output formats (table / Marp / chart) | ⚠ deliberate divergence — Discord-first list output only; complex outputs delegated to GPT / Notion |
| Viewer (Obsidian / Dataview / qmd) | ⚠ deliberate divergence — vault is for AI, not humans; viewer not recommended |
| Multi-agent runtime support | ✅ OpenClaw-native + Claude Code via `CLAUDE.md` + OpenAI Codex via `AGENTS.md` |
| Search engine | ⚠ uses `lancedb + grep` dual instead of `qmd` |

## Version

v0.5 — adds Karpathy alignment fills: per-source `summaries/` folder, top-level `overview.md`, `CLAUDE.md` agent entry-point alias, contradictions lint check 13. Total Layer-2 folders now 20 (added `summaries/`).

Pilot ordering: Ansai's own vault first (faster feedback loop), then Mifiya, then other clients. The first weekly prompt-tuning cron runs Mondays at 09:37 Asia/Taipei and reports to channel 1493072746702311474.

Outstanding:
- F23 pricing decision (deferred to Ansai team; early-stage clients onboard free during pilot)
- v0.6 prompt tuning based on Ansai pilot data
- v0.6 `overview.md` auto-regeneration cron (currently manual)
