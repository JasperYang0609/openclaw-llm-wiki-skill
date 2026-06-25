# Lint check 11 — missing cross-references (AI auto-fill)

> Triggered by `@knowledge lint --auto-fix` from inside an OpenClaw agent session,
> or as the auto-fix half of the weekly `lint.py` cron. The Python `lint.py` stubs
> this check and points here; the agent reads this prompt and executes it.

## Goal

Find pages in the vault that talk about the same subject (same entity, same concept,
same decision context, same product) but are **not interlinked via wikilinks**, and
**auto-add the missing `[[wikilinks]]`** without asking the consultant for approval.

Reference: D16 / E19 from the 2026-06-25 alignment — AI auto-link is authorized;
admin review is **not** required for this check.

## Inputs the agent must have read

1. `SCHEMA.md` — domain, taxonomy, strict-tier tags
2. `_meta/active-folders.md` — which Layer-2 folders are active
3. `_meta/lint-config.yaml` — confirm `auto_fill_cross_refs: true`
4. All vault pages in active Layer-2 folders (skip `inbox/`, `_archive/`, `_meta/`)
5. The most recent 30 lines of `log.md` for context

## Procedure

1. **Build a topic index in working memory**: for each page, extract:
   - `title`
   - `tags` (strict + loose)
   - top 5 capitalized noun phrases from the body (named entities)
   - existing outbound `[[wikilinks]]`
2. **Find candidate pairs**: two pages are a candidate cross-ref pair when ALL of:
   - They are not already linked in either direction
   - They share ≥1 strict-tier tag (customer-*, product-*, type-*), OR
   - Their top-5 named entities overlap by ≥2, OR
   - One page's `title` appears verbatim in the other page's body (and is not yet a wikilink)
3. **Confidence scoring per candidate**:
   - `high` — shared strict-tier tag + named-entity overlap ≥3
   - `medium` — shared strict-tier tag OR named-entity overlap ≥3
   - `low` — only title-mention or single tag overlap
4. **Auto-fill policy**:
   - `high` and `medium`: add the wikilink immediately; do **not** ping admin
   - `low`: add the wikilink with a visible ⚠ inline marker `[[target]]⚠` and queue
     this page's path in the lint report for admin review
5. **For each auto-added link**, update the source page:
   - Insert `[[target]]` in the most contextually relevant paragraph (where the
     target's title or top entity appears as plain text), not at the bottom as a flat list
   - Bump `updated` in frontmatter
   - Append `(auto-cross-ref by lint)` to the change summary
6. **Bump frontmatter `wikilinks_confidence`** to the lowest level among all links on the page (low > medium > high)
7. **Git auto-commit** the batch (one commit per lint run, message
   `lint: auto-cross-ref N high/medium + M low (⚠ pending)`)
8. **Append to `log.md`**:
   `## [YYYY-MM-DD] lint cross-refs | N added high/medium | M added low (⚠) | K pairs skipped`

## Output format (agent → user / log)

```
[lint:cross-refs] auto-fill complete
  pairs scanned:    P
  pairs linked:     N (high) + M (medium) + L (low ⚠)
  pairs skipped:    K  (already linked, below threshold, or in inbox/)
  pages updated:    U
  commit:           <git hash>
  review queue (low ⚠ only):
    - decisions/2026-q2-pricing.md ↔ customers/customer-acme.md
    ...
```

## Hard guardrails (do not violate)

- **Never modify pages in `inbox/`, `_archive/`, or `_meta/`**
- **Never delete existing wikilinks**, only add new ones
- **Never create new pages** from this check — that is lint 10 (`should-build-but-not-built`)'s job
- **Never request admin approval per-pair** — D16/E19 authorized batch auto-fill
- **Skip pages with `do_not_lint: true` in frontmatter** (escape hatch for admin)
- **Stop and report if Git commit fails** — do not leave the vault in a half-linked state
- **Do not run if `auto_fill_cross_refs: false`** in `_meta/lint-config.yaml` (fall back to "report-only" mode and queue everything in the ⚠ review list)

## v0.5 tuning notes (post-pilot)

Once Ansai's internal pilot vault is running, revisit:
- Are the confidence thresholds catching too many false positives?
- Should the named-entity extraction use a smarter NER instead of "top 5 capitalized noun phrases"?
- Is the per-link insertion location selection good, or are links clumping at the bottom?
- Does the ⚠ marker survive Discord rendering when pages are quoted in answers?
