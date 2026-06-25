# CLAUDE.md — agent entry point for {{TEAM_NAME}} vault

> Auto-loaded by Claude Code / Codex / OpenClaw when an agent session starts in this directory.
> Tells the agent: this is an `openclaw-llm-wiki` vault — go read `SCHEMA.md` first.

You are operating inside an **openclaw-llm-wiki** vault (customer-facing name: 企業智庫 / Enterprise Knowledge Hub).

## Before you do anything

1. Read `SCHEMA.md` — vault rules, domain, taxonomy, thresholds
2. Read `_meta/active-folders.md` — which Layer-2 folders are active
3. Read `_meta/lint-config.yaml` — lint thresholds and guardrails
4. Read `index.md` — what pages exist
5. Read the last 30 lines of `log.md` — recent activity

Skipping these causes duplicate pages, broken cross-references, and tag drift.

## Skill behind this vault

The full skill specification lives at:
- `~/.openclaw/workspace/skills/openclaw-llm-wiki/SKILL.md` (local install)
- https://github.com/JasperYang0609/openclaw-llm-wiki-skill (canonical)

The skill defines:
- 20 Layer-2 folders (Core 10 + Recommended 5 + Nice-to-have 5 including `summaries/`)
- 8-field required frontmatter
- 1-source + AI-filter page threshold
- AI auto-fill wikilinks (no minimum count enforced)
- 13 lint checks (10 schema-level fully implemented + 1 should-build approximation + 2 AI-required)
- Discord-first query, no Markdown tables
- Git auto-commit always on

Read the skill SKILL.md if you need the full rules; this file is just the entry-point pointer.

## Vault info

- Team: {{TEAM_NAME}}
- Domain: {{DOMAIN_DESCRIPTION}}
- Vault initialized: {{INIT_DATE}}
