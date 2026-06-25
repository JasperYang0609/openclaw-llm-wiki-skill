# Lint check 12 — data gaps (local-only auto-fill, never web search)

> Triggered by `Skill openclaw-llm-wiki` inside an agent session (or the
> planned-for-v0.6 `@knowledge lint` Discord shortcut), as the data-gap pass of
> the weekly `lint.py` cron. The Python `lint.py` stubs this check and points
> here.

## Goal

Find pages in the vault where existing information is **skeletal or contradicting** and
either:
- **auto-fill the gap** from another local source (other vault, lancedb index, Discord backup history, daily-backup summaries, Notion ingested raw), OR
- **report the gap as data-quality findings** for the consultant to address.

Reference: E20 from the 2026-06-25 alignment — modes **a + d + e** are authorized;
mode **b (web search)** is **forbidden**.

## What counts as a "gap"

A page is gap-flagged if ANY of:
- Body < 200 characters of substantive prose (excluding frontmatter / heading)
- Frontmatter `confidence: low` AND page is in `decisions/`, `incidents/`, `policies/`, `customers/`, or `products/` (high-stakes types)
- Page references an entity in `[[wikilinks]]` for which no real page exists (broken-link gap, but contextually it shows where info should be)
- Page contains a TODO / FIXME / "details pending" / "待補" / "TBD" marker in body
- Page was created from a single source >30 days ago and still has `single_source: true`

## Inputs the agent must have read

1. `SCHEMA.md` and `_meta/active-folders.md`
2. All vault pages in active Layer-2 folders
3. `_meta/lint-config.yaml` — confirm `data_gap_local_only: true`
4. Access to other configured local sources:
   - Other vaults on the same OpenClaw deployment (if `_meta/cross-vault-allow.md` permits)
   - `openclaw-lancedb-knowledge` index (semantic search)
   - `openclaw-discord-server-backup` outputs (Discord channel history summaries)
   - `*-daily-backup` summary files (per-team)
   - Notion ingest staging
5. **Never** web search; **never** ask the user to web search; **never** call any external API beyond the local lancedb index and configured local sources

## Procedure

1. **Scan vault** and identify all gap pages per the criteria above
2. **For each gap page**, do a local-source search in this order:
   - a. Same vault's lancedb index for related chunks (top-5 hits)
   - b. Discord backup history (`openclaw-discord-server-backup` outputs) for the page title + top entities
   - c. Daily-backup summaries (per-team) for relevant dates / topics
   - d. Notion ingest staging for matching topic
   - e. (Only if `_meta/cross-vault-allow.md` lists other vaults) — sibling vaults for matching topic
3. **Classify each hit**:
   - `auto-fill candidate`: hit is clearly the same subject AND adds new factual content beyond what's already on the gap page
   - `partial fill`: hit overlaps but needs admin judgment to integrate
   - `noise`: hit is unrelated or duplicate
4. **Auto-fill policy**:
   - At most 1 `auto-fill candidate` is merged per gap page per run (avoid runaway changes)
   - Insert under a new section `## Auto-fill (lint YYYY-MM-DD)` so admin can see provenance
   - Include `source:` line citing the local source path
   - Bump `updated` and `confidence` (low→medium if 1 added source; medium→high if reaches 3 total sources)
5. **Report-only items** (`partial fill` + skipped low-confidence + gaps with no hit):
   - Write a single report file `_meta/lint-data-gaps-YYYY-MM-DD.md`
   - Each entry: page path, gap reason, top hit (if any), suggested next step
6. **Git auto-commit** the batch: `lint: data-gaps auto-fill N pages | M reported`
7. **Append to `log.md`**:
   `## [YYYY-MM-DD] lint data-gaps | N filled | M reported | scanned P pages`

## Output format (agent → user)

```
[lint:data-gaps] complete
  gap pages found:    P
  auto-filled:        N (with cited local sources)
  reported:           M (in _meta/lint-data-gaps-YYYY-MM-DD.md)
  commit:             <git hash>
  top 3 reports:
    - decisions/2026-q2-pricing.md   reason: low confidence + 35 days old; top hit: meetings/2026-04-12-pricing-discussion.md
    - customers/customer-acme.md     reason: 178 chars body; top hit: deliverables/acme-proposal-v2.md (partial overlap)
    - incidents/2026-05-brand-misfire.md  reason: TODO marker; no local source found — admin attention required
```

## Hard guardrails (do not violate)

- **NEVER web search.** Not Gemini grounding, not custom web tools, not user-supplied URLs as fetches. Only local sources. This is non-negotiable per E20.
- **NEVER fabricate content.** If no local source supports an addition, the page stays as-is and goes into the report queue.
- **NEVER modify pages in `inbox/`, `_archive/`, or `_meta/`** (except for writing the `lint-data-gaps-*.md` report)
- **Always cite the local source path** when auto-filling — every added paragraph must have its `source:` line
- **At most 1 auto-fill per page per run** — avoid runaway accretion
- **Stop and report if Git commit fails** — do not leave the vault in a half-filled state
- **Skip pages with `do_not_lint: true`** in frontmatter
- **Do not run auto-fill mode if `data_gap_local_only` is false or missing** — fall back to report-only

## v0.5 tuning notes (post-pilot)

Once Ansai's internal pilot vault is running, revisit:
- Are the 5 gap-detection criteria catching too many or too few pages?
- Is the local-source search order (lancedb → Discord → daily-backup → Notion → cross-vault) the right priority?
- Should the cross-vault rule become opt-in per-customer instead of opt-in per-source?
- Are the auto-fill insertions getting integrated by admins, or are they being reverted? (Track via `git log --grep="lint: data-gaps" --reverse` and check for follow-up reverts)
- How long is the typical pipeline? If >10 minutes for a 200-page vault, consider sharding by Layer-2 folder
