# Code Review Brief — openclaw-llm-wiki-skill v0.5.3

> **For: Hermes** (`<@1505825424792485898>`)
> **From: Jasper + Claude Opus 4.7**
> **Date: 2026-06-25**

This brief is for an independent third-round code review. Two prior reviews already shipped (see "Prior reviews" section). Your job is to find what they missed and would still break this in production.

---

## What this project is

OpenClaw skill that turns a Markdown vault into a team knowledge base — sales label **企業智庫 / Enterprise Knowledge Hub**. Built on Karpathy's LLM Wiki pattern (2026-02 gist). Productized for OpenClaw deployments — each client team (米菲亞 / 萊可 / 方成事 / 安賽自家) runs its own vault.

**Scope this skill owns:**
- 20-folder Layer-2 schema (Core 10 + Recommended 5 + Nice-to-have 5)
- AI-driven classification into folders
- Wikilink auto-creation
- 13-check lint (10 schema-level fully implemented + 1 should-build approximation + 2 AI-required delegated to `prompts/`)
- Schema-evolution governance with 5 guardrails + Git auto-commit
- Discord-first query formatting

**Out of scope (delegated):**
- Ingest pipeline → `openclaw-discord-server-backup` + per-team `*-daily-backup` crons
- Semantic search → `openclaw-lancedb-knowledge` (Gemini embedding default, client's own API key)
- Text search → `grep` parallel + merged ranker
- Discord routing for `@knowledge lint` → planned for v0.6, NOT in this repo

## Repo layout

```
openclaw-llm-wiki-skill/
├── README.md, CHANGELOG.md, LICENSE, .gitignore
└── openclaw-llm-wiki/
    ├── SKILL.md                          # main agent instructions
    ├── templates/
    │   ├── SCHEMA.md                     # scaffold for new vaults
    │   ├── CLAUDE.md                     # agent entry-point alias (Claude Code)
    │   ├── AGENTS.md                     # agent entry-point alias (OpenAI Codex)
    │   ├── index.md
    │   ├── log.md
    │   └── overview.md                   # top-level synthesis page (regenerated)
    ├── scripts/
    │   ├── init_vault.py                 # bootstrap a vault (20 folders + Git + lancedb wiring)
    │   ├── lint.py                       # 13-check lint runner
    │   └── migration_plan.py             # schema-change preview & apply
    ├── prompts/
    │   ├── lint_missing_cross_refs.md    # AI agent prompt for lint check 11
    │   └── lint_data_gaps.md             # AI agent prompt for lint check 12
    └── references/
        └── example-mifiya-schema.md
```

## Prior reviews (what already got caught)

**Round 1 — consistency audit (2026-06-25, v0.5.1 → v0.5.2)**
20 cross-file inconsistencies fixed: "19 folders" left over after expanding to 20, "12 checks" left over after adding contradictions, version markers stale at v0.3 in script docstrings, AGENTS.md not in lint skip-list, Python-3.9 negative-index crash at 6 sites.

**Round 2 — production readiness audit (2026-06-25, v0.5.2 → v0.5.3)**
9 real bugs fixed: lint path display was producing garbage paths (wrong fix from Round 1), `confirm_two_step` was returning `bool(b)` so any string passed step 2, `git add -A` was sweeping user's WIP into schema commits, `op_rename` accepted any `dst` string (typos broke schema), `parse_strict_tags` regex didn't match GFM checkbox prefix (so tag_drift silently always returned 0), `parse_frontmatter` couldn't handle YAML block lists (`tags:\n  - foo`), README had no quickstart, 10+ docs aspirationally promised `@knowledge lint` Discord triggers that don't exist, cron job used Chinese prose instead of Discord mention syntax. Plus 5 better error messages.

Full diff: `git log --oneline` shows the 6 commits v0.2 → v0.5.3.

## Your specific brief (what we want this round to cover)

Rounds 1-2 covered consistency and production-readiness / first-time UX. Your angle should be **everything those missed**. Specifically:

### 1. Python code quality / idioms

- Are types accurate? PEP-604 union syntax (`dict | None`) used in spots; project targets 3.9+ (where it's only allowed via `from __future__ import annotations`). Verify all files use it correctly.
- Error handling: are bare `except` lurking? Are exceptions swallowed silently? Are warnings printed to stderr vs stdout correctly?
- Are file reads opened with explicit encoding everywhere? (We added `encoding="utf-8"` in most places.)
- Resource cleanup: are context managers used?
- Subprocess calls: any shell injection vectors? `check=False` everywhere — does any of them need `check=True`?

### 2. Security

- `init_vault.py` accepts `--team` and `--domain` from CLI, then inlines them into Markdown via string `.replace("{{X}}", value)`. What if `team = "$(rm -rf ~)"` or `domain = "</div><script>"` or contains backticks? Does anything execute or render unsafely?
- Path traversal: `--vault-path ../../etc` — does any code path write into unexpected locations?
- Subprocess git invocations: `git commit -m <msg>` — any way for `msg` to be injected?
- Cron job message contains paths — could an attacker who controls a Discord message later cause those paths to mean something different?
- Are template `.replace()` calls a real risk, or is the impact bounded to one vault directory?

### 3. Prompt engineering quality (`prompts/lint_*.md`)

These two prompts will be executed by an LLM agent (Codex / Opus / Sonnet) against real vault contents. They are the actual product behavior of lint checks 11 and 12.

- Read both prompts as if you are the agent that will execute them. Are the instructions unambiguous? Where could an agent reasonably do the wrong thing?
- The `lint_missing_cross_refs.md` confidence scoring: are the high/medium/low thresholds calibrated? Are the auto-fill vs warn rules safe?
- The `lint_data_gaps.md` 5 gap-detection criteria + local-source priority order — are any criteria likely to over-trigger? Is the "at most 1 auto-fill per page per run" cap the right knob?
- Both prompts assume Git auto-commit succeeds and bail otherwise — is the failure-mode handling described correctly?
- "Never web-search" hard guardrail in `lint_data_gaps.md` — strong enough?

### 4. Karpathy v2 alignment depth

Karpathy v1 (the gist) is mostly markdown structure + workflows. [rohitg00's v2 fork](https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2) added: confidence scoring, supersession of stale claims, contradiction detection.

- Our `frontmatter.confidence` field is `low | medium | high`. Is this scheme rich enough? Should it be numeric?
- "Supersession of stale claims": we have `check_stale` (>90 days) but no automatic-supersession mechanism. Is this a gap, or is it covered by the contradictions / archive workflow?
- "Contradiction detection": lint check 13 only scans frontmatter `contradictions: [target]` — it doesn't *detect* contradictions, just validates flagged ones. Is that a gap vs Karpathy v2?

### 5. Composability / API design

- Are the 3 scripts (`init_vault`, `lint`, `migration_plan`) composable with shell pipelines? Does `lint --json` actually output valid JSON to stdout while putting warnings on stderr? Test with `lint --json | jq`.
- Exit codes: is `0` clean and non-zero a real failure? Are there warning-only paths that exit `0` despite finding lint issues — and is that the right semantics?
- Is there a way to call all 3 as a Python library, or are they CLI-only?

### 6. Maintainability

- If a new engineer joined and was told "add a 21st Layer-2 folder," how many files would they need to touch? Is there a single source of truth or is the LAYER2 list duplicated?
- If they had to "add a 14th lint check," what's the surface area?
- Are the prompts versioned with the rest of the project, or could they drift?

### 7. Testing

- Zero tests exist. What 5 tests would give the most confidence per unit of effort?
- Smoke tests in the CHANGELOG were ad-hoc bash one-liners — should they be promoted to `tests/`?

### 8. Anything you find that we didn't think to ask about

Especially: behaviors that are correct today but will become wrong at scale (1000+ pages), behaviors that work on macOS but will break on Linux server cron, anything that assumes single-user when multiple consultants might be running operations concurrently.

## Output format we'd like back

A punch list, grouped by **severity** (blocker / important / minor / nit), each item:
- **Where**: file:line or scenario
- **What's wrong**: one sentence
- **Suggested fix**: one sentence
- **Why prior reviews missed it**: one sentence (we want to learn the pattern)

End with:
- **Headline judgment**: should we ship v0.5.3 as-is to early-stage clients (Ansai's own vault first, then 米菲亞), or hold for a v0.5.4 patch?
- **Top 3 things to fix before any external eyes see the repo**.

Keep total response under 1500 words. Focus on what Rounds 1-2 missed.

## Pointers

- Canonical repo: https://github.com/JasperYang0609/openclaw-llm-wiki-skill
- Latest commit: `2c39e85` (v0.5.3)
- Karpathy v1: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Karpathy v2 (rohitg00): https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2
- Sibling skills:
  - https://github.com/JasperYang0609/openclaw-discord-server-backup
  - https://github.com/JasperYang0609/openclaw-lancedb-knowledge-skill

Thanks Hermes — fire away.
