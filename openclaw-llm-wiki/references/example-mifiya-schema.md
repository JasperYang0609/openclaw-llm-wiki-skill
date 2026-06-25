# Wiki Schema — mifiya (reference example, v0.5.1)

> Filled-in SCHEMA.md for the Mifiya consulting engagement, aligned to the
> 20-folder Layer-2 structure + 8-field frontmatter agreed 2026-06-25
> (plus Karpathy-pattern fills: summaries/, contradictions lint, CLAUDE/AGENTS aliases).
> Use this as a starter when adapting `templates/SCHEMA.md` for a new client.

> Customer-facing name: **企業智庫 / Enterprise Knowledge Hub**

## Domain

Mifiya consulting engagement — Ansai AI consulting for a Taiwanese F&B / lifestyle
brand. The vault covers Mifiya's brand assets, internal SOPs, product lines,
AI-consultant deliverables, the methodology used during the engagement, and the
ongoing decision history co-owned by Mifiya's boss and the Ansai consultants.

## Roles

- **Employee** (Mifiya staff): query in Discord, zero onboarding
- **Boss** (Mifiya owner): query + reviews weekly lint reports + signs off on schema changes proposed by the admin
- **Consultant admin** (Ansai): owns schema design, drives onboarding, monitors lint, approves AI suggestions, executes migrations

## Conventions

- File names: lowercase, hyphens (e.g., `mifiya-brand-voice.md`, `decision-2026-q2-pricing-update.md`)
- All 8 frontmatter fields required (see below); pages missing fields are returned to `inbox/`
- `[[wikilinks]]` are AI-auto-filled at create time; no manual minimum enforced
- Meeting transcripts: routed in from `mifiya-daily-backup` cron → directly into `meetings/`, no extra AI filter
- Weekly consultant reports: `deliverables/weekly-report-YYYY-WW.md` (note: previously syntheses/; moved under v0.2 because they are client-facing deliverables)
- Deliverables tagged with the engagement phase: `phase-1`, `phase-2`, `phase-3`
- Git auto-commit always on; never bypass

## Frontmatter (all 8 required)

```yaml
---
title: e.g. "Decision: Q2 2026 pricing update for Mifiya retail line"
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: decision   # one of the 20 Layer-2 types
tags: [phase-2, customer-mifiya, product-retail-line, brand-tone]   # strict tier first
sources: [meetings/2026-04-12-pricing-discussion.md, raw/notion/pricing-policy-v3.md]
confidence: high   # 3+ sources cross-validated; "low" for single-source pages
wikilinks_confidence: medium
categories: [decisions, brand]   # multi-category: primary + secondary
---
```

## Tag taxonomy (mixed strictness)

### Strict tier (must be registered here BEFORE use)

**Customers (only "customer-mifiya" itself — vault is per-client)**
- `customer-mifiya`

**Products / lines (Mifiya's actual SKUs / service lines)**
- `product-retail-line`
- `product-wholesale`
- `product-online-store`
- `product-consulting-service`

**Layer-2 types (one per active folder)**
- `type-decision`, `type-sop`, `type-customer`, `type-product`, `type-contact`,
  `type-person`, `type-concept`, `type-comparison`, `type-synthesis`, `type-query`,
  `type-brand`, `type-policy`, `type-deliverable`, `type-meeting`, `type-incident`

(Nice-to-have folders not active for Mifiya: metrics/, vendors/, templates/, glossary/, summaries/ — 15 active of 20)

**Engagement phases**
- `phase-1`, `phase-2`, `phase-3`

### Loose tier (free-form)

- Time / period: `2026q1`, `2026-06-25`, `weekly`, `quarterly`
- Sentiment / status: `urgent`, `wip`, `done`, `blocked`, `risk`
- Ad-hoc descriptors: `framework`, `tool`, `case-study`, `lesson-learned`, etc.

## Active Layer-2 folders for Mifiya

Reflects folder-on-demand: only what Mifiya actually uses.

- ✅ `decisions/` — engagement-level decisions, judgment basis
- ✅ `sops/` — Mifiya internal SOPs (operations, customer service, content)
- ✅ `customers/` — Mifiya's own customer segments (Mifiya is a brand, has its own customers)
- ✅ `products/` — Mifiya product lines, specs, positioning
- ✅ `contacts/` — external partners, suppliers Mifiya works with
- ✅ `people/` — Mifiya internal team + boss + Ansai consultants
- ✅ `concepts/` — frameworks, brand concepts, methodology terms
- ✅ `comparisons/` — competitor comparisons, A/B option analyses
- ✅ `syntheses/` — cross-meeting integrations
- ✅ `queries/` — common Q&A worth keeping (e.g., "how to position product X for channel Y")
- ✅ `brand/` — Mifiya brand voice, visual, do/don't (critical for a brand-led F&B business)
- ✅ `policies/` — HR rules, working hours, holiday policy
- ✅ `deliverables/` — Ansai weekly reports, proposals, audit decks
- ✅ `meetings/` — fed by `mifiya-daily-backup` cron
- ✅ `incidents/` — past pricing miss, brand-tone misfires, customer-service incidents

Inactive (re-enable later if needed):
- `metrics/`, `vendors/`, `templates/`, `glossary/`

## Page thresholds

Standard rule: 1 source + AI substance filter. Mifiya-specific exceptions and emphases:

- **Always build a page**:
  - For every Mifiya product line, even if mentioned only once
  - For every engagement decision (Mifiya engagement maintains a complete decision log; this is a contractual deliverable)
  - For every brand-tone judgment call (Mifiya is brand-led — never lose these)
- **Never build a page**:
  - For one-off meeting attendees who never reappear
  - For pure chit-chat in Discord (AI filter handles)

## Privacy / embedding

- Gemini embedding (sales/recall priority)
- Mifiya uses **their own Google API key** — set at onboarding; carries over if off-boarded
- Secret redaction on by default (Mifiya may discuss customer info, pricing, payroll)

## Lint configuration

- Weekly cron (Sunday 02:00) + on-demand. Discord shortcut `@智庫 lint` is planned for v0.6 — meanwhile invoke `Skill openclaw-llm-wiki` in a Codex/Claude agent turn, or run `scripts/lint.py` directly.
- Should-build threshold: 2 sources (default; raise to 3 if inbox volume explodes)
- Data-gap auto-fill: local-only (never web-search)
- Cross-ref auto-fill: enabled (no admin review)

## Team-specific overrides for Mifiya

- Every `deliverables/weekly-report-*` must link to `[[engagement-overview]]` and to the previous/next week's report
- Brand-tone references must link to `[[mifiya-brand-voice]]`
- Customer-interview notes must list interviewer + date in frontmatter `sources`
- All sources from Mifiya's internal Notion arrive via the `mifiya-daily-backup` cron into `meetings/` (transcripts) or `deliverables/` (formal docs); never hand-imported
- Pricing decisions get both `decisions` + `products` as `categories` (multi-category) so they surface in product context

## Off-boarding readiness

- Vault is plain markdown — Mifiya can `git clone` and walk away anytime
- They keep their Google API key (set at onboarding)
- Lancedb index is rebuildable (open source, indexed locally on Mifiya's side)
- No vendor lock-in
