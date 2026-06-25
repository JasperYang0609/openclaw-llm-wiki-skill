# Wiki Schema — {{TEAM_NAME}}

> Customer-facing name: **企業智庫 / Enterprise Knowledge Hub**

## Domain

{{DOMAIN_DESCRIPTION}}

## Roles

- **Employee**: query in Discord, zero onboarding
- **Boss**: query + review lint reports + sign off on schema changes
- **Consultant admin**: schema design + AI suggestion approval + migrations

Employees do not edit the schema or any vault files directly.

## Conventions

- File names: lowercase, hyphens, no spaces (e.g., `{{TEAM_NAME_SLUG}}-brand-voice.md`)
- Every page starts with YAML frontmatter (all 8 fields required, see below)
- Use `[[wikilinks]]` to link between pages — AI auto-fills at create time, no minimum enforced
- When updating a page, always bump the `updated` date
- Every new page must appear in `index.md` under the correct Layer-2 category
- Every action must be appended to `log.md`
- Git auto-commit is always on — never bypass

## Frontmatter (8 fields, ALL required)

```yaml
---
title: Page title in plain language
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: decision | sop | customer | product | contact | person | concept | comparison | synthesis | query | brand | policy | deliverable | meeting | incident | metric | vendor | template | glossary
tags: [from-taxonomy, ...]
sources: [raw/articles/source-file.md, discord/2026-06-25-channel-name.md, ...]
confidence: low | medium | high
wikilinks_confidence: low | medium | high
categories: [primary-folder, optional-secondary-folder]
---
```

Missing any field → page rejected back to `inbox/` for completion.

## Tag taxonomy (mixed strictness)

### Strict tier — must be pre-registered here BEFORE use

Define under {{TEAM_NAME}} below. Examples to seed:

- **Customers**: `customer-acme`, `customer-globex`, ...
- **Products**: `product-line-a`, `product-line-b`, ...
- **Layer-2 types**: `type-decision`, `type-sop`, `type-customer`, ... (one per active folder)

### Loose tier — free-form OK

- Time / period: `2026q1`, `2026-06-25`, `weekly`
- Sentiment / status: `urgent`, `wip`, `done`, `blocked`
- Ad-hoc descriptors: anything else descriptive

<!-- CUSTOMIZE FOR {{TEAM_NAME}} BELOW -->

### Strict-tier customers (add as relationships form)

- (none yet — add as they appear)

### Strict-tier products (add as products are named)

- (none yet — add as they appear)

### Strict-tier Layer-2 types (active for this team)

<!-- Mark which of the 19 categories are active. Folder-on-demand = only enable what the team uses. -->

- [ ] `type-decision` (decisions/)
- [ ] `type-sop` (sops/)
- [ ] `type-customer` (customers/)
- [ ] `type-product` (products/)
- [ ] `type-contact` (contacts/)
- [ ] `type-person` (people/)
- [ ] `type-concept` (concepts/)
- [ ] `type-comparison` (comparisons/)
- [ ] `type-synthesis` (syntheses/)
- [ ] `type-query` (queries/)
- [ ] `type-brand` (brand/)
- [ ] `type-policy` (policies/)
- [ ] `type-deliverable` (deliverables/)
- [ ] `type-meeting` (meetings/)
- [ ] `type-incident` (incidents/)
- [ ] `type-metric` (metrics/)
- [ ] `type-vendor` (vendors/)
- [ ] `type-template` (templates/)
- [ ] `type-glossary` (glossary/)

## Page thresholds

- **Build a page** when even a single source mentions an entity / concept / decision / incident AND AI judges substantive content
  - Substantive = factual statement, named entity, specific decision, commitment, lesson
  - Filtered out = chit-chat, emoji, reactions, acknowledgments, off-topic
  - Mark single-source pages with `single_source: true` for potential lint upgrade
- **Add to existing page** when a new source mentions something already covered
- **Don't build a page** for content that fails the AI substance filter — let it stay in `inbox/` or be discarded
- **Split a page** when it exceeds ~200 lines — break into sub-topics with cross-links
- **Archive a page** when fully superseded — move to `_archive/`, remove from index

## Layer-2 category guide (19 folders)

### Core 10

- `decisions/` — boss/team decisions, judgment basis ("why we picked X")
- `sops/` — standard operating procedures, playbooks
- `customers/` — customer profile, project history per client
- `products/` — product/service specs, knowledge
- `contacts/` — external partners, vendors-as-contacts
- `people/` — internal team, roles, boss/expert views
- `concepts/` — definitions, terminology, frameworks
- `comparisons/` — side-by-side analysis (A vs B)
- `syntheses/` — multi-source consolidated takes
- `queries/` — filed Q&A worth keeping

### Highly recommended 5 (enable if the team will use)

- `brand/` — brand voice, visual guidelines (essential for marketing teams)
- `policies/` — HR policies, org chart, compliance
- `deliverables/` — past reports / proposals (reusable across clients)
- `meetings/` — meeting transcripts, consensus
- `incidents/` — lessons learned, post-mortems

### Nice-to-have 4 (only if needed)

- `metrics/` — KPI definitions, formulas
- `vendors/` — supplier records (deeper than contacts/)
- `templates/` — forms, contract templates
- `glossary/` — industry-specific dictionary

**Folder-on-demand**: do not pre-create empty folders. Only open what the team actually uses. Re-evaluate at every schema review.

## Update policy (contradictions)

1. Check dates — newer generally supersedes older
2. If genuinely contradictory, keep both positions with dates and sources
3. Mark in frontmatter: `contradictions: [other-page-name]`
4. Flag for review in next lint report

## Search & retrieval

This vault is dual-indexed:
- **Semantic**: `openclaw-lancedb-knowledge` under project name `{{TEAM_NAME}}` (Gemini embedding default, client's own Google API key)
- **Text**: `grep` runs in parallel
- **Ranker**: merged (semantic 0.7 + text 0.3 by default; pages hit by both score get a boost)

Reindex triggers:
- After every Ingest action (delegated to lancedb skill cron)
- Manual: `npm run incremental` from the team's lancedb folder
- After every schema migration

## Lint configuration

Run weekly cron + admin can trigger via Discord (`@knowledge lint`).

Active checks (12):
1. broken wikilinks
2. orphan pages
3. frontmatter missing
4. tag drift (strict tier only)
5. index drift
6. stale pages (>90 days)
7. oversized pages (>200 lines)
8. log rotation (>500 entries)
9. lancedb freshness
10. **應建未建** — multi-source mentions without page
11. **missing cross-refs** — AI auto-links without admin review
12. **data gaps** — local-source first auto-fill; NEVER web search

Append `## [YYYY-MM-DD] lint | N issues found | M auto-fixed` to log.md after each run.

## Privacy / embedding

- Gemini embedding default (high recall for "employee query hit rate" north-star)
- Client uses their own Google API key — set at onboarding, taken on off-boarding
- Privacy-strict teams can switch to local hash embedding (accept recall hit)
- Secrets (`.env`, tokens, credentials) excluded from indexing by default

## Schema evolution governance

- Onboarding: consultant admin designs schema with boss
- Ongoing: client admin can self-serve schema changes with 5 guardrails:
  1. Role-gated (admin only; not employees)
  2. Preview impact before commit
  3. Git rollback always available
  4. Two-step confirmation for destructive ops (delete folder, change type, change required frontmatter)
  5. Auto-notify consultant on any admin-side schema change

## Off-boarding

- Vault is portable: plain markdown in 19 folders, zip on request
- Client takes their Google API key with them (set at onboarding)
- Lancedb index can be rebuilt by client (open source)
- No vendor lock-in

## Team-specific overrides for {{TEAM_NAME}}

<!-- Add team-specific rules here. Examples:
- "Always tag client deliverables with the engagement code"
- "Brand voice references must link to [[brand-voice]]"
- "Meeting notes are routed from meetings/ via mifiya-daily-backup"
-->

## Version

v0.2 — schema reflects 30-question alignment 2026-06-25. See repo CHANGELOG.md for diff vs v0.1.
