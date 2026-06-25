# OpenClaw LLM Wiki Skill

OpenClaw skill that turns a Markdown vault into a team knowledge base — sales label **企業智庫 / Enterprise Knowledge Hub**.

Built on Karpathy's LLM Wiki pattern, productized for OpenClaw deployments. One vault per OpenClaw deployment; each client team (米菲亞 / 萊可 / 方成事 / 安賽 / future clients) runs its own.

## Scope (this skill owns)

- Vault schema: 20 Layer-2 folders (folder-on-demand), 8-field required frontmatter, mixed-strictness tag taxonomy
- AI-driven classification into folders with confidence gating
- Wikilink auto-creation and cross-reference maintenance
- Lint: 13 checks including Karpathy-pattern "should-build-but-not-built", auto-cross-ref, local-only data-gap fill, and contradiction scan
- Schema evolution governance: 5 admin guardrails + Git auto-commit + rollback
- Discord-first query formatting (no Markdown tables, no Marp slides, no charts — those are delegated)

## Delegated to other skills

- **Ingest pipeline** → [`openclaw-discord-server-backup`](https://github.com/JasperYang0609/openclaw-discord-server-backup) + per-team `*-daily-backup` crons
- **Semantic search** → [`openclaw-lancedb-knowledge`](https://github.com/JasperYang0609/openclaw-lancedb-knowledge-skill) (Gemini embedding default, client uses own API key)
- **Text search** → `grep` runs in parallel with lancedb; merged ranker
- **Complex outputs** → ask OpenClaw to make a Notion report, or GPT to generate an image

This skill is **not** a replacement for Notion / Drive / Chat. It complements them with an AI-retrieval-optimized knowledge layer.

## Roles

| Role | Behavior |
|---|---|
| Employee | Discord chat only; zero onboarding |
| Boss | Same as employee + reviews lint, signs off on schema changes |
| Consultant admin | Owns schema design, lint monitoring, AI suggestion approval, migrations |

## Install

Requires Python 3.9+ and `git`. Lancedb integration is optional on day 1 (text grep still works).

```bash
git clone https://github.com/JasperYang0609/openclaw-llm-wiki-skill.git
cp -R openclaw-llm-wiki-skill/openclaw-llm-wiki ~/.openclaw/workspace/skills/
```

(Optional) install the sibling skills for full functionality:
- [`openclaw-lancedb-knowledge`](https://github.com/JasperYang0609/openclaw-lancedb-knowledge-skill) — semantic search
- [`openclaw-discord-server-backup`](https://github.com/JasperYang0609/openclaw-discord-server-backup) — Discord channel ingest

## Quickstart

Initialize a vault for a team (default location `~/.openclaw/wiki/team/`, default folders Core 10 + `brand/`):

```bash
python3 ~/.openclaw/workspace/skills/openclaw-llm-wiki/scripts/init_vault.py \
    --vault-path ~/.openclaw/wiki/mifiya \
    --team mifiya \
    --domain "Mifiya consulting team — brand, customers, methods, SOPs" \
    --skip-lancedb     # drop this flag once openclaw-lancedb-knowledge is installed
```

Enable extra folders at init time with `--enable policies --enable deliverables`, or enable later via `scripts/migration_plan.py`.

Run health-check anytime:

```bash
python3 ~/.openclaw/workspace/skills/openclaw-llm-wiki/scripts/lint.py \
    --vault-path ~/.openclaw/wiki/mifiya
```

Preview a schema change (dry-run; add `--apply` to commit):

```bash
python3 ~/.openclaw/workspace/skills/openclaw-llm-wiki/scripts/migration_plan.py \
    --vault-path ~/.openclaw/wiki/mifiya enable policies
```

> **Discord triggers** like `@knowledge lint` / `@智庫 lint` are referenced in SKILL.md as the eventual operator UX. The Discord/agent router that wires those mentions to this skill is **planned for v0.6 and is not in this repo**. For now, invoke the skill via your agent runtime (`Skill openclaw-llm-wiki ...` inside a Codex or Claude Code turn) or run the Python scripts directly as shown above.

## Contents

- `openclaw-llm-wiki/SKILL.md` — main skill instructions (orient, page rules, query, lint, governance)
- `openclaw-llm-wiki/templates/` — `SCHEMA.md`, `CLAUDE.md`, `AGENTS.md`, `index.md`, `log.md`, `overview.md` for new vault initialization
- `openclaw-llm-wiki/scripts/init_vault.py` — one-shot vault bootstrap: 20-folder structure (folder-on-demand) + Git auto-commit + lancedb wiring + CLAUDE.md + AGENTS.md + overview.md scaffold
- `openclaw-llm-wiki/scripts/lint.py` — runs 13-check lint (10 schema-level fully implemented including contradictions scan; 2 AI-required checks stubbed for agent runtime)
- `openclaw-llm-wiki/scripts/migration_plan.py` — preview & apply schema changes (`enable` / `disable` / `rename` / `add-frontmatter-field`) with two-step confirmation + Git auto-commit
- `openclaw-llm-wiki/prompts/lint_missing_cross_refs.md` — AI prompt for lint check 11 (batch auto-link, no admin approval)
- `openclaw-llm-wiki/prompts/lint_data_gaps.md` — AI prompt for lint check 12 (local sources only; **never** web-search)
- `openclaw-llm-wiki/references/example-mifiya-schema.md` — filled-in SCHEMA reference for a marketing-consulting client

## Vault structure (20 Layer-2 folders)

- **Core 10**: `decisions/` `sops/` `customers/` `products/` `contacts/` `people/` `concepts/` `comparisons/` `syntheses/` `queries/`
- **Highly recommended 5**: `brand/` `policies/` `deliverables/` `meetings/` `incidents/`
- **Nice-to-have 5**: `metrics/` `vendors/` `templates/` `glossary/` `summaries/`
- **System 2**: `inbox/` (low-confidence staging) + `_meta/` (admin config)

Folders are created on demand — small teams run with Core 10 + `brand/`.

## Privacy

- Default embedding: Google Gemini via `openclaw-lancedb-knowledge`. Client supplies their own Google API key at onboarding.
- Privacy-strict clients can switch to local hash embedding (accept the recall hit).
- Secrets (`.env`, tokens, credentials) excluded from indexing by default.
- Vault is portable: plain markdown, zip on request — no vendor lock-in.

## Status

**v0.5.3** — production-readiness audit pass: fixes 9 real bugs the consistency pass missed. Highlights: lint path display now actually vault-relative; two-step confirm now actually compares the typed name; `git add -A` removed (no more sweeping user WIP into schema commits); `op_rename` validates `dst`; `parse_strict_tags` regex now matches checkbox-prefixed lines; YAML block-list tags now parse correctly; README quickstart added; aspirational `@knowledge` Discord triggers labeled "planned for v0.6" everywhere.

**v0.5.2** — same-day audit pass: fixes 20 inconsistencies (folder counts 19→20, lint count 12→13, AGENTS.md missing from lint skip list, 6 more Python 3.9 `parents[-2]` crash sites). Smoke-tested clean.

**v0.5.1** — same-day patch adds `AGENTS.md` (OpenAI Codex equivalent of `CLAUDE.md`) so daily-backup crons running on Codex auto-load the vault orientation pointer.

**v0.5** — closes 3 Karpathy-v1/v2 alignment gaps: per-source `summaries/` folder (#20 Layer-2, default off), top-level `overview.md` synthesis page, lint check 13 for contradiction scanning. Adds `CLAUDE.md` agent entry-point alias and a Karpathy alignment table in SKILL.md.

**Pilot ordering**: Ansai's own vault first (faster feedback loop than waiting on Mifiya), then Mifiya, then other clients. First weekly prompt-tuning cron runs Mondays 09:37 Asia/Taipei → channel 1493072746702311474.

Outstanding:
- F23 pricing decision (deferred; early-stage clients onboard free during pilot)
- v0.6 prompt tuning based on Ansai pilot data
- v0.6 `overview.md` auto-regeneration cron (monthly)

See [`CHANGELOG.md`](CHANGELOG.md) for the v0.1 → v0.5.3 trail.

## Safety

Do not commit tokens, OpenClaw config files, customer vault contents, or daily-backup outputs. Only commit templates, scripts, prompts, references, and tests.

## Maintainer use of Codex

This project is maintained as part of the OpenClaw ecosystem. Codex assists with PR review, lint-script regression tests, schema-migration safety checks, and documentation/release-note updates as OpenClaw / lancedb / Discord-backup APIs evolve.

API-assisted maintenance should focus on safe, auditable workflows. Codex should not be used to process private customer vaults, transcripts, or daily-backup outputs.
