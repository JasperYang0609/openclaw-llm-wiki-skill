# OpenClaw LLM Wiki Skill

OpenClaw skill that turns a Markdown vault into a team knowledge base — sales label **企業智庫 / Enterprise Knowledge Hub**.

Built on Karpathy's LLM Wiki pattern, productized for OpenClaw deployments. One vault per OpenClaw deployment; each client team (米菲亞 / 萊可 / 方成事 / 安賽 / future clients) runs its own.

## Scope (this skill owns)

- Vault schema: 19 Layer-2 folders (folder-on-demand), 8-field required frontmatter, mixed-strictness tag taxonomy
- AI-driven classification into folders with confidence gating
- Wikilink auto-creation and cross-reference maintenance
- Lint: 12 checks including Karpathy-pattern "should-build-but-not-built", auto-cross-ref, and local-only data-gap fill
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

```bash
git clone https://github.com/JasperYang0609/openclaw-llm-wiki-skill.git
cp -R openclaw-llm-wiki-skill/openclaw-llm-wiki ~/.openclaw/workspace/skills/
```

Install [`openclaw-lancedb-knowledge`](https://github.com/JasperYang0609/openclaw-lancedb-knowledge-skill) first so search is available, then ingest sources via [`openclaw-discord-server-backup`](https://github.com/JasperYang0609/openclaw-discord-server-backup) and the team's daily-backup cron.

## Contents

- `openclaw-llm-wiki/SKILL.md` — main skill instructions (orient, page rules, query, lint, governance)
- `openclaw-llm-wiki/templates/` — `SCHEMA.md`, `index.md`, `log.md` for new vault initialization
- `openclaw-llm-wiki/scripts/init_vault.py` — one-shot vault bootstrap (v0.1 wiring; v0.3 will rewrite for the 19-folder structure)
- `openclaw-llm-wiki/references/example-mifiya-schema.md` — example filled-in SCHEMA for a marketing-consulting team

## Vault structure (19 Layer-2 folders)

- **Core 10**: `decisions/` `sops/` `customers/` `products/` `contacts/` `people/` `concepts/` `comparisons/` `syntheses/` `queries/`
- **Highly recommended 5**: `brand/` `policies/` `deliverables/` `meetings/` `incidents/`
- **Nice-to-have 4**: `metrics/` `vendors/` `templates/` `glossary/`
- **System 2**: `inbox/` (low-confidence staging) + `_meta/` (admin config)

Folders are created on demand — small teams run with Core 10 + `brand/`.

## Privacy

- Default embedding: Google Gemini via `openclaw-lancedb-knowledge`. Client supplies their own Google API key at onboarding.
- Privacy-strict clients can switch to local hash embedding (accept the recall hit).
- Secrets (`.env`, tokens, credentials) excluded from indexing by default.
- Vault is portable: plain markdown, zip on request — no vendor lock-in.

## Status

**v0.2** — schema and SKILL.md reflect the 30-question design alignment completed 2026-06-25.

Outstanding for v0.3:
- Rewrite `scripts/init_vault.py` for 19-folder structure + Git auto-commit initialization
- Add `scripts/lint.py` covering all 12 checks
- Add `scripts/migration_plan.py` for schema evolution preview
- Update `references/example-mifiya-schema.md` to v0.2 schema

See [`CHANGELOG.md`](CHANGELOG.md) for v0.1 → v0.2 diff.

## Safety

Do not commit tokens, OpenClaw config files, customer vault contents, or daily-backup outputs. Only commit templates, scripts, prompts, references, and tests.

## Maintainer use of Codex

This project is maintained as part of the OpenClaw ecosystem. Codex assists with PR review, lint-script regression tests, schema-migration safety checks, and documentation/release-note updates as OpenClaw / lancedb / Discord-backup APIs evolve.

API-assisted maintenance should focus on safe, auditable workflows. Codex should not be used to process private customer vaults, transcripts, or daily-backup outputs.
