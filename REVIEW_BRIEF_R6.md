# Code Review Brief — openclaw-llm-wiki-skill v0.5.6 (Round 6)

> **For: Hermes** (`<@1505825424792485898>`)
> **From: Jasper + Claude Opus 4.7 (安賽小助手)**
> **Date: 2026-06-26**

This is your fourth pass. Round 5 found 1 blocker + 3 important + 4 minor and gave verdict `HOLD external, v0.5.6 needed`. We shipped v0.5.6 (commit `f47299c`) addressing **all 8 R5 items** plus added the Git commit policy you suggested + 9 new regression tests. Test count grew 34 → 43, all green.

This round = **verify the v0.5.6 fixes are correct, complete, and not papering over**, plus look for what v0.5.6 itself made worse. You gated 米菲亞 / 萊可 / 方成事 onboarding on R6; we are again asking for the external-unlock verdict.

---

## 0. Delivery + collaboration protocol (unchanged from R5)

### Required delivery format

1. **Send your review as exactly ONE attached `.md` file** named `openclaw_llm_wiki_skill_round6_review_hermes.md`. Do NOT split into `(1/N)` text bubbles. If the file is large, attach whole.
2. **Discord message body** ≤80 words preamble pointing at the attached file; mention `<@1505825424792485898>` (yourself, optional); reply to THIS brief's Discord message for thread traceability.
3. **Severity prefix**: `🚨 BLOCKER FOUND` if blocker present, else `✅ Round 6 review complete`.

### Reporting protocol after delivery

4. After you send the report, wait for the small-assistant (安賽小助手) to react with 👀 or reply within 10 minutes.
5. The small-assistant will: confirm receipt + post summary; tag YOU back if any finding needs clarification BEFORE patching; open v0.5.7 branch only AFTER explicit Jasper approval.
6. **Mid-review escalation**: if you find something so critical that 米菲亞 / Ansai pilot should STOP using v0.5.6, send a SHORT separate message starting with `🛑 STOP` BEFORE finishing the full review.
7. **Citation format**: every finding must cite `file.py:LINE` or `path/file.md:LINE-RANGE`. If you ran tests, include the exact command. If you constructed a payload, include the exact bytes (escape control chars).

### Message body summary template

```
Round 6 verdict: ship / hold / hold-with-followups
New findings: N blocker / N important / N minor
Verified Round 5 fixes correct: N of 8
Full report attached.
```

---

## 1. What changed since Round 5

v0.5.6 (commit `f47299c`) closes all 8 R5 findings + introduces the Git commit policy + adds 9 new pytest cases. Full diff: `git diff 197604a f47299c`.

### R5 BLOCKER B1 — fixed in v0.5.6

- **B1 (migration_plan.git_commit still rejected env-only identity after mutation)**
  - Removed the stale `git config user.email` check in `migration_plan.git_commit()` (file `openclaw-llm-wiki/scripts/migration_plan.py:124-189`).
  - Replaced with `git_identity_ok(vault)` so init + migration agree on what counts as a valid identity.
  - Env-only CI/cron environments now pass BOTH preflight AND commit.
  - Regression: `test_v056_migration_apply_with_env_only_identity_commits_cleanly`.

### R5 Important I1–I3 — fixed in v0.5.6

- **I1 (commit signing/hooks failure still left half-mutated vaults)**
  - New **Git commit policy** documented in `SKILL.md`: all tool-owned commits run with `git -c user.useConfigOnly=true -c commit.gpgsign=false commit --no-verify ...`. Bypass is intentional + documented.
  - Rationale (3 points) in `SKILL.md` § `Git commit policy (v0.5.6)`.
  - `migration_plan` now has `git_commit_atomic()` that captures HEAD before commit and calls `rollback_paths()` on failure — restores touched paths from HEAD or removes if new.
  - `_manifest` exports new helpers: `GIT_TOOL_COMMIT_ARGS`, `GIT_COMMIT_NO_VERIFY`, `head_snapshot(vault)`, `rollback_paths(vault, head, paths)`.
  - `op_enable` / `op_disable` / `op_rename` all switched from `git_commit` to `git_commit_atomic`.
  - `init_vault.commit_scaffold` adopts the new commit args.
  - `preflight_git` no longer emits the misleading `commit.gpgsign=true` warning (v0.5.5 claimed it would refuse to mutate; it didn't).
  - Regression: `test_v056_migration_apply_commit_signing_failure_disabled_succeeds`, `test_v056_init_commit_signing_failure_disabled_succeeds`.
- **I2 (cross-vault YAML did not actually fail-closed on all malformed input)**
  - `load_cross_vault_allow` now strict. Default-deny on:
    - Unknown top-level key (was: silently ignored)
    - Unknown entry key (was: silently accepted)
    - Tab indentation anywhere
    - NBSP / ZWSP whitespace anywhere
    - YAML anchor / alias tokens (`&`, `*`)
    - `allowed_vaults: <scalar>` (e.g. `/tmp`)
    - Empty / `null` / `~` `path:` values
    - Empty `reason:` value
    - Any line not consumed by a known grammar production (catches trailing garbage)
  - Allowed top-level keys frozen to `{version, allowed_vaults}`; allowed entry keys to `{path, reason}`.
  - Regression: 5 new tests + existing 5-sub-case malformed test still passes.
- **I3 (same-deployment / vault-parent constraint documented but not implemented)**
  - `load_cross_vault_allow(meta_dir, *, vault_root=None)` — when `vault_root=` is passed, every entry's resolved path must be under `vault_root.resolve().parent` or default-deny.
  - `prompts/lint_data_gaps.md` updated to instruct callers to pass `vault_root=`.
  - Regression: `test_v056_cross_vault_allow_rejects_existing_path_outside_vault_parent`.

### R5 Minor M1–M4 — fixed in v0.5.6

- **M1**: renamed misleading test `test_v055_init_no_identity_at_all_exits_nonzero_without_writing_scaffold` → `test_v055_init_no_identity_exits_nonzero_without_commit`.
- **M2**: `_isolated_git_env` strips every `GIT_CONFIG_*` env override except `GIT_CONFIG_NOSYSTEM=1`. New test `test_v056_isolated_git_env_hides_GIT_CONFIG_GLOBAL`.
- **M3**: `prompts/lint_data_gaps.md:76` `.md` → `.yaml` typo fixed.
- **M4**: new `reviews/round4_findings.md` enumerates all 5 R4 minor findings with disposition + commits cited.

### New audit-pattern lesson

> "Preflight + warning is not the same as preflight + block. A preflight that warns about a risk while subsequent code does nothing to mitigate the warned risk is theatre, not safety."

Documented in `CHANGELOG.md` alongside the previous five lessons.

### Test counts

- 34 → 43 (+9 R6 regression):
  - `test_v056_migration_apply_with_env_only_identity_commits_cleanly` (B1)
  - `test_v056_migration_apply_commit_signing_failure_disabled_succeeds` (I1)
  - `test_v056_init_commit_signing_failure_disabled_succeeds` (I1)
  - `test_v056_cross_vault_allow_rejects_trailing_garbage_after_valid_entry` (I2)
  - `test_v056_cross_vault_allow_rejects_existing_path_outside_vault_parent` (I3)
  - `test_v056_cross_vault_allow_rejects_scalar_allowed_vaults` (I2)
  - `test_v056_cross_vault_allow_rejects_tab_indent` (I2)
  - `test_v056_cross_vault_allow_rejects_unknown_top_level_key` (I2)
  - `test_v056_isolated_git_env_hides_GIT_CONFIG_GLOBAL` (M2)
- Run: `pytest tests/ -q` → `43 passed in 5.43s` (Python 3.9, fully hermetic).

---

## 2. Specific Round 6 questions (please address each)

For each of the 8 R5 findings, the question is **"is the v0.5.6 fix correct, complete, and not papering over"?** Also look at what v0.5.6 itself touched.

### A. Git commit policy correctness

- `-c commit.gpgsign=false --no-verify` — does this actually bypass EVERY hook category we care about?
  - `pre-commit` ✓ (`--no-verify` skips it)
  - `commit-msg` ✓ (`--no-verify` skips it)
  - `prepare-commit-msg` ? (verify it is skipped by `--no-verify`)
  - `post-commit` — not blocked by `--no-verify`; a failing `post-commit` can still print noise but cannot abort the commit (verify this assumption)
  - `core.hooksPath` redirecting hooks to a malicious path — does `--no-verify` cover that too?
- Are there other env vars that can re-enable signing despite `commit.gpgsign=false`?
  - `GPG_TTY` does not re-enable signing on its own.
  - What about `gpg.program` being set to a wrapper that always exits non-zero?
- Is the policy correctly applied to BOTH `init_vault.commit_scaffold()` and `migration_plan.git_commit()`?
- Is there a test verifying `core.hooksPath` redirecting to a failing hook is bypassed by `--no-verify`?

### B. Rollback correctness (`git_commit_atomic` + `rollback_paths`)

- `head_snapshot(vault)` returns the SHA before commit — verify it captures the right state when called from inside `op_enable` / `op_disable` / `op_rename` (after mutation but before commit).
- `rollback_paths`:
  - Uses `git checkout <head> -- <path>` to restore tracked content. Does this leave any staged residue? (We also call `git reset -q HEAD -- <path>` after; verify ordering is correct.)
  - For new paths (not in HEAD), it uses `git rm --cached --ignore-unmatch` + `shutil.rmtree` / `unlink`. Are there race conditions? Symlinks? Hidden files?
  - For renames (`op_rename`): the rollback path list contains both `src` and `dst`. Restoring `src` from HEAD should put the folder back; removing `dst` should clean up the new name. But what if `git checkout HEAD -- src` fails because `src` was moved away? Does the fallback (`git clean` style) actually restore correctly?
- The 3 atomic regression tests force commit failure via signing — but with v0.5.6 bypassing signing, those tests verify SUCCESS, not the rollback path itself. Is there a test that actively forces commit failure (e.g. by injecting a write-protected `.git/objects/`) to exercise the rollback?
- What if `head_snapshot` returns None (fresh init) and commit fails — does `rollback_paths` correctly nuke untracked content without exploding?

### C. Strict YAML parser

- `_ALLOWED_TOPLEVEL_KEYS` / `_ALLOWED_ENTRY_KEYS` frozensets — are they the complete set? Should `description` or `since_version` be accepted in entries for future schema growth (forward compat)?
- Anchor / alias detection (`" &"`, `" *"`, `"- &"`, `"- *"`) — is this robust to keys that legitimately contain `*` as part of a glob-like reason? (Probably not a real concern since reason is short prose, but worth checking.)
- NBSP / ZWSP detection uses literal `" "` and `"​"` strings in `_manifest.py`. Verify those exact codepoints are correct (U+00A0 and U+200B). Are there other zero-width Unicode chars we should add (U+FEFF BOM, U+200C/D zero-width-joiner)?
- The same-parent check uses `vault_root.resolve().parent`. On macOS, `/tmp` is a symlink to `/private/tmp` — does this cause false positives or false negatives when vault is in `/tmp/xxx`? (Our test passes; verify the logic itself.)
- What about an allow-list path that is `vault_root.parent` ITSELF (i.e. the deployment root)? Should that be denied or allowed? Currently it is allowed; is that intended?

### D. Test harness coverage (43 cases)

- Are the 9 new tests actually exercising what they claim? Read `tests/test_security_and_smoke.py:457-` (the v0.5.6 block).
- `test_v056_migration_apply_commit_signing_failure_disabled_succeeds` sets `commit.gpgsign=true` in local config but does the tool override actually win? Verify by reading the actual command line emitted.
- `_isolated_git_env` v0.5.6 update — does the `monkeypatch` test correctly simulate a CI environment? Are there other GIT_* vars we forgot (e.g. `GIT_DIR`, `GIT_WORK_TREE`, `GIT_NAMESPACE`)?
- Coverage gaps:
  - Is there a test for rollback firing on an actual injected commit failure (e.g. setting `.git` to read-only mid-op)?
  - Is there a test for `git_commit_atomic` being called with `head_snapshot=None` (fresh repo with no commits)?
  - Is there a test for `load_cross_vault_allow` when `_meta/cross-vault-allow.yaml` is a symlink to `/etc/passwd`?
- What's a 44th–48th test that would catch the highest-value remaining risk?

### E. v0.5.6 regressions (what did this round break?)

- The R5 `_manifest.load_cross_vault_allow` was called with positional `meta_dir` only. v0.5.6 added a keyword-only `vault_root=None`. Verify no caller breaks. (`lint.py` imports the symbol but does not currently call it — verify.)
- The R5 test `test_v055_cross_vault_allow_default_deny_on_malformed_yaml` had a case `version: 99\nallowed_vaults: []\n`. With v0.5.6 strictness, does this case still default-deny via the version check (it should)? Verify the test still passes.
- The R5 `_isolated_git_env` returned `dict[str, str]`. v0.5.6 still returns `dict`. Verify mutating its result inside a test does not corrupt parent `os.environ` (it shouldn't, since `os.environ.copy()` is shallow but values are strings — immutable).
- Did the new `GIT_TOOL_COMMIT_ARGS` constant accidentally break any existing test that asserted the exact `git commit` argv?
- The new rollback for `op_rename`: if the user runs `--apply`, sees the rollback message, and re-runs WITHOUT fixing the underlying cause, does the second attempt land cleanly? Or does the rollback leave a subtle inconsistency?

### F. Things still in your gut

- Anything you'd flag for v0.5.7 / v0.6 that didn't make R5's punch list.
- Unknown unknowns: a class of bug we're not even thinking about (concurrency, multi-vault cross-contamination, OpenClaw runtime sandbox assumptions, Windows / WSL path semantics, NFS-mounted vaults).
- Is the skill *actually* ready to hand to 米菲亞 admin who may have weird Mac/Win environments + cron + global signing config?
- Should we publish a `MIGRATION_v055_to_v056.md` for existing v0.5.5 vaults? Or does the change require zero migration?

---

## 3. Headline judgment we want

End the attached report with a single line of one of:

- `SHIP v0.5.6 to external (米菲亞 + 萊可 + 方成事 + other clients)` — fully green; unlock all external client onboarding
- `SHIP v0.5.6 to external WITH followups (list of <=5 nice-to-have for v0.5.7)` — green for external, but document the followups
- `HOLD external, v0.5.7 needed (list of must-fix)` — blockers remain; Ansai pilot continues, external HOLD
- `HOLD all use, v0.5.7 needed, freeze Ansai pilot too` — emergency

---

## 4. Pointers

- Canonical repo: https://github.com/JasperYang0609/openclaw-llm-wiki-skill
- Latest commit: `f47299c` (v0.5.6)
- v0.5.6 diff: `git diff 197604a f47299c`
- Round 3 brief: `REVIEW_BRIEF.md`
- Round 4 brief: `REVIEW_BRIEF_R4.md`
- Round 5 brief: `REVIEW_BRIEF_R5.md`
- Round 6 brief (this file): `REVIEW_BRIEF_R6.md`
- Round 5 report (Hermes): see channel attachment `openclaw_llm_wiki_skill_round5_review_hermes.md`
- Round 4 findings record (new): `reviews/round4_findings.md`
- Karpathy v1: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Sibling skills:
  - https://github.com/JasperYang0609/openclaw-discord-server-backup
  - https://github.com/JasperYang0609/openclaw-lancedb-knowledge-skill

---

## 5. Context: why R6 matters

Same as R5 — R6 is the external-unlock gate. v0.5.6 was built in direct response to your R5 verdict. Ansai's own vault can pilot regardless; the moment your verdict is green, we open:
- 米菲亞 (paying client, AI consulting case)
- 萊可集團 (AI consulting case, in onboarding)
- 方成事 (consulting case)
- All other downstream OpenClaw deployments

If you find a blocker, flag it now rather than after a client has a poisoned vault. Be ruthless.

Thanks Hermes. Per protocol: one attached `.md` file + short preamble + your verdict line.
