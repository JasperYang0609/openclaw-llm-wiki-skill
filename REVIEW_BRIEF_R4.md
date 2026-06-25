# Code Review Brief — openclaw-llm-wiki-skill v0.5.4 (Round 4)

> **For: Hermes** (`<@1505825424792485898>`)
> **From: Jasper + Claude Opus 4.7**
> **Date: 2026-06-25**

This is your second pass on this skill. Round 3 found 2 blockers + 6 important + 3 minor; we shipped v0.5.4 (commit `b56e34e`) addressing **all 11** plus a new pytest harness. This round = **verify the fixes are correct and didn't introduce regressions**, plus look for what v0.5.4 itself might have made worse.

---

## 0. Delivery + collaboration protocol (Jasper-specified)

Round 3 had real friction because the `(1/2)` text message + separate MD attachment confused the small-assistant agent. This round we are stricter:

### Required delivery format

1. **Send your review as exactly ONE attached `.md` file** named `openclaw_llm_wiki_skill_round4_review_hermes.md`. Do NOT split into `(1/N)` text bubbles. If the file is large, that's fine — attach it whole.
2. **Discord message body** should be a SHORT (≤80 words) preamble pointing at the attached file, mentioning `<@1505825424792485898>` (yourself, optional) and replying to THIS brief's Discord message so the thread is traceable.
3. **Severity prefix in preamble** if you find a blocker: start the message with `🚨 BLOCKER FOUND` so the small-assistant knows to escalate immediately. Otherwise prefix with `✅ Round 4 review complete`.

### Reporting protocol after delivery

4. After you send the report, **wait for the small-assistant (安賽小助手) to react with 👀 or reply within 10 minutes**. If no acknowledgment, ping again.
5. The small-assistant will:
   - Confirm receipt and post a summary of your findings in the channel
   - **Tag YOU back (`<@1505825424792485898>`)** if any finding needs clarification BEFORE patching
   - Open a v0.5.5 branch / patch only AFTER explicit Jasper approval (not unilaterally)
6. **Mid-review escalation**: if you find something so critical you think the team should STOP using v0.5.4 even on internal pilots, send a SHORT separate message starting with `🛑 STOP` BEFORE finishing the full review. Don't wait until the report is done.
7. **Citation format**: every finding must cite `file.py:LINE` or `path/file.md:LINE-RANGE`. If you ran tests, include the exact command. If you constructed a payload, include the exact bytes (escape control chars).

### What to send the small-assistant in your message body

A 3-line summary is enough:
```
Round 4 verdict: ship / hold / hold-with-followups
New findings: N blocker / N important / N minor
Verified Round 3 fixes correct: N of 11
Full report attached.
```

---

## 1. What changed since Round 3

v0.5.4 (commit `b56e34e`) closed 11 findings + added tests:

### Blockers (your R3) — fixed
- `migration_plan.py rename --allow-custom` — now passes `dst` through `validate_slug` AND `safe_resolve_inside(vault, dst)`. Path traversal / absolute / non-slug rejected with exit 2.
- `init_vault.py` team/domain prompt injection — `team` is now a strict slug; `domain` is wrapped in a fenced data block with explicit "Do NOT follow instructions" HTML comment + triple-backtick defanging (`` ``` `` → `ʼʼʼ`).

### Important (your R3) — fixed
- LanceDB target path now uses validated slug + `safe_resolve_inside`.
- `git_init_and_commit` and `git_commit` now preflight `user.email`, return False on commit failure; callers convert to non-zero exit (3). No more silent `[warn]` + exit 0.
- `check_should_build` now scans all source roots (inbox + raw/*), deduped by resolved path. Reports `source_files_scanned`.
- `_meta/cross-vault-allow.yaml` now has a real YAML schema (default-deny). `init_vault.py` scaffolds it. Prompt updated to read it and explicitly disallow NEW remote embedding calls.
- SKILL.md Karpathy v2 alignment downgraded to ⚠ Partial for 3 rows (contradiction-detection, claim-level confidence, supersession) with v0.6 plan.
- `scripts/_manifest.py` new — single source of truth for LAYER2, types, frontmatter spec, lint check names, slug validators. All 3 scripts import from it. Eliminates LAYER2 duplication.

### Minor (your R3) — fixed
- `lint.py --fail-on-issues` flag; counts both list- and dict-shaped findings (`index_drift`, `log_size`, `lancedb_freshness`, `should_build`).
- `prompts/lint_missing_cross_refs.md` confidence-scoring rewritten as explicit truth table; "low > medium > high" wording inverted (now `low < medium < high`).
- `templates/log.md` stale `raw/`/`entities/` references replaced with actual v0.5.4 layout.

### New: test harness
- `tests/test_security_and_smoke.py` — 27 pytest cases, all green on Python 3.9.
- 5 categories: slug validation (9), prompt-injection containment (2), migration sandbox escape (6), lint exit codes + JSON validity (3), end-to-end init (2 + 5).
- Run: `pytest tests/` after `pip install pytest`.

## 2. Specific Round 4 questions (please address each)

For each of the 11 R3 findings, the question is **"is the fix correct, complete, and not papering over"?**

In addition, look at things that v0.5.4 itself touched:

### A. `_manifest.py` design quality

- Is the slug grammar (`^[a-z0-9]+(?:-[a-z0-9]+)*$`, ≤40 chars) too strict / too permissive?
- Is `safe_resolve_inside` actually safe? Race conditions (TOCTOU)? Symlink traversal? Does it handle Path-normalization edge cases on Linux vs macOS?
- Is `render_data_block` defanging strategy sound? Are there other fence-breakout payloads (HTML, YAML, Markdown link injection) we haven't defanged?
- Is the `sys.path.insert` import pattern OK or should we use a different mechanism (proper package, importlib)?

### B. Test harness coverage

- Are the 27 tests actually testing what they claim? Read `tests/test_security_and_smoke.py:1-200`.
- What's a 28th-33rd test that would catch the highest-value remaining gap?
- Any test that's too tightly coupled to implementation details (will break on harmless refactors)?

### C. Git semantics

- The new "preflight user.email" check — what if someone has only repo-local config not global? What if `git config` itself fails? What about `commit.gpgsign = true` requiring signing key not available?
- The error message tells users to `git config --global ...` — is global the right default vs repo-local?
- Does the non-zero exit code (3) collide with any other Python convention?

### D. Prompt fixes

- The new truth table in `lint_missing_cross_refs.md` — does it close the ambiguity? Are the thresholds defensible?
- The new fenced-data-block + "do not follow instructions" comment in CLAUDE.md / AGENTS.md — would a sophisticated agent actually obey it? Test with a real Codex / Claude turn if you can.
- The cross-vault-allow.yaml schema — is `default deny` actually enforced if the file is malformed YAML / missing the `allowed_vaults` key?

### E. What new bugs did v0.5.4 introduce?

- Is the `sys.path.insert(0, ...)` import pattern safe when scripts are run from inside an OpenClaw cron context where `sys.path` ordering matters?
- Did the manifest extraction break anything subtle (constants that should have been kept as private to each script)?
- Did Path validation accidentally reject any legitimate operational use case we'll regret?

### F. Things still in your gut

Anything you'd flag for v0.5.5 / v0.6 that didn't make R3's punch list. We want unknown unknowns.

## 3. Headline judgment we want

End the attached report with a single line of one of:
- `SHIP v0.5.4 to external (米菲亞)` — fully green
- `SHIP v0.5.4 to external WITH followups (list of <=5 nice-to-have)` — green for external, but not perfect
- `HOLD external, v0.5.5 needed (list of must-fix)` — blockers remain
- `HOLD all use, v0.5.5 needed, freeze Ansai pilot too` — emergency

## 4. Pointers

- Canonical repo: https://github.com/JasperYang0609/openclaw-llm-wiki-skill
- Latest commit: `b56e34e` (v0.5.4)
- v0.5.4 diff: `git diff 2c39e85 b56e34e`
- Round 3 brief (for context): `REVIEW_BRIEF.md`
- Round 4 brief (this file): `REVIEW_BRIEF_R4.md`
- Karpathy v1: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Sibling skills:
  - https://github.com/JasperYang0609/openclaw-discord-server-backup
  - https://github.com/JasperYang0609/openclaw-lancedb-knowledge-skill

Thanks Hermes. Per protocol: one attached `.md` file + short preamble + your verdict line.
