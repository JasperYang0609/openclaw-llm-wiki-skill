#!/usr/bin/env python3
"""
lint.py — openclaw-llm-wiki v0.5 lint runner.

Runs the 13 checks defined in the SKILL.md and writes a grouped report.
Schema-level checks (1-9 + 13) are fully implemented. Karpathy-pattern checks
(10-12) that require AI are stubbed with explicit "requires AI runtime" markers
— invoke those from inside an OpenClaw agent session rather than the bare CLI.

Check 13 (contradictions) was added in v0.5 to scan for unresolved contradictions
flagged in page frontmatter — close a gap noted in the Karpathy-pattern review.

Usage:
    python3 lint.py --vault-path ~/.openclaw/wiki/team
    python3 lint.py --vault-path /tmp/test --auto-fix      # apply missing-cross-ref auto-fill
    python3 lint.py --vault-path /tmp/test --json          # machine-readable output
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REQUIRED_FRONTMATTER = {
    "title", "created", "updated", "type", "tags", "sources",
    "confidence", "wikilinks_confidence", "categories",
}
LAYER2_TYPES = {
    "decision", "sop", "customer", "product", "contact", "person",
    "concept", "comparison", "synthesis", "query",
    "brand", "policy", "deliverable", "meeting", "incident",
    "metric", "vendor", "template", "glossary", "summary",
}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:\|[^\]]+)?\]\]")
# Allow optional GFM checkbox prefix: `- [ ]` or `- [x]` before the backticked tag
TAG_LINE_RE = re.compile(r"^\s*-\s*(?:\[[ xX]\]\s*)?`([^`]+)`")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def strip_comments(text: str) -> str:
    return HTML_COMMENT_RE.sub("", text)


def load_config(meta_dir: Path) -> dict:
    cfg_path = meta_dir / "lint-config.yaml"
    cfg = {
        "stale_page_days": 90,
        "oversized_page_lines": 200,
        "log_rotate_entries": 500,
        "should_build_min_sources": 2,
        "data_gap_local_only": True,
        "auto_fill_cross_refs": True,
    }
    if not cfg_path.exists():
        return cfg
    for line in cfg_path.read_text(encoding="utf-8").splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.split("#")[0].strip()
            if key not in cfg:
                continue
            if value.lower() in ("true", "false"):
                cfg[key] = value.lower() == "true"
            else:
                try:
                    cfg[key] = int(value)
                except ValueError:
                    cfg[key] = value
    return cfg


def parse_frontmatter(text: str) -> dict | None:
    """Tolerant YAML-frontmatter parser. Handles:
    - `key: value` inline scalars
    - `key:` followed by indented `  - item` block lists (converted to comma-joined str)
    - `key: [a, b, c]` inline flow lists (left as-is for downstream regex extraction)
    Not a full YAML parser — only what this lint actually consumes.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    fm: dict = {}
    lines = m.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" not in line or line.lstrip().startswith("#"):
            i += 1
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value == "":
            # collect block-list continuation lines: `  - foo`
            collected: list[str] = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                stripped = nxt.lstrip()
                if stripped.startswith("- "):
                    collected.append(stripped[2:].strip())
                    j += 1
                elif nxt.startswith(" ") or nxt.startswith("\t"):
                    j += 1  # other indented line, skip
                else:
                    break
            if collected:
                fm[key] = ", ".join(collected)
            else:
                fm[key] = ""
            i = j
            continue
        fm[key] = value
        i += 1
    return fm


def parse_strict_tags(schema_path: Path) -> set[str]:
    """Extract strict-tier tags from SCHEMA.md (lines under 'Strict-tier' headers)."""
    tags: set[str] = set()
    if not schema_path.exists():
        return tags
    text = schema_path.read_text(encoding="utf-8")
    in_strict = False
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("###"):
            in_strict = "Strict-tier" in stripped or "Strict tier" in stripped or "strict tier" in stripped.lower()
            continue
        if stripped.startswith("##") and not stripped.startswith("###"):
            in_strict = False
            continue
        if in_strict:
            m = TAG_LINE_RE.match(line)
            if m:
                tags.add(m.group(1).strip())
    return tags


def walk_vault_pages(vault: Path) -> list[Path]:
    skip_dirs = {".git", "_archive", "inbox", "_meta"}
    skip_names = {"SCHEMA.md", "CLAUDE.md", "AGENTS.md", "index.md", "log.md", "overview.md"}
    pages: list[Path] = []
    for path in vault.rglob("*.md"):
        rel = path.relative_to(vault)
        if rel.name in skip_names:
            continue
        if any(part in skip_dirs for part in rel.parts):
            continue
        pages.append(path)
    return pages


def page_stem_to_path(vault: Path, pages: list[Path]) -> dict[str, Path]:
    return {p.stem: p for p in pages}


# ---- checks ----------------------------------------------------------------

def rel(vault: Path, page: Path) -> str:
    """Vault-relative POSIX path for human-readable output."""
    return page.relative_to(vault).as_posix()


def check_broken_wikilinks(vault, pages, stem_to_path):
    findings = []
    for page in pages:
        text = strip_comments(page.read_text(encoding="utf-8"))
        for target in set(WIKILINK_RE.findall(text)):
            if target not in stem_to_path:
                findings.append({"page": rel(vault, page), "target": target})
    return findings


def check_orphans(vault, pages, stem_to_path):
    inbound = Counter()
    for page in pages:
        for target in set(WIKILINK_RE.findall(strip_comments(page.read_text(encoding="utf-8")))):
            inbound[target] += 1
    return [rel(vault, p) for p in pages if inbound[p.stem] == 0]


def check_frontmatter_missing(vault, pages):
    findings = []
    for page in pages:
        fm = parse_frontmatter(page.read_text(encoding="utf-8"))
        if fm is None:
            findings.append({"page": rel(vault, page), "missing": "all (no frontmatter block)"})
            continue
        missing = REQUIRED_FRONTMATTER - set(fm.keys())
        if missing:
            findings.append({"page": rel(vault, page), "missing": sorted(missing)})
    return findings


def check_tag_drift(vault, pages, strict_tags):
    findings = []
    if not strict_tags:
        return findings  # nothing to enforce
    for page in pages:
        fm = parse_frontmatter(page.read_text(encoding="utf-8")) or {}
        tag_value = fm.get("tags", "")
        tags = re.findall(r"[\w\-/]+", tag_value)
        used_strict_candidates = [t for t in tags if t.startswith(("customer-", "product-", "type-"))]
        drift = [t for t in used_strict_candidates if t not in strict_tags]
        if drift:
            findings.append({"page": rel(vault, page), "unregistered_strict_tags": drift})
    return findings


def check_index_drift(vault, pages):
    index_path = vault / "index.md"
    if not index_path.exists():
        return {"error": "index.md missing"}
    text = strip_comments(index_path.read_text(encoding="utf-8"))
    listed = set(re.findall(r"\[\[([^\]|]+)\]\]", text))
    actual = {p.stem for p in pages}
    return {
        "in_vault_not_in_index": sorted(actual - listed),
        "in_index_not_in_vault": sorted(listed - actual),
    }


def check_stale(vault, pages, max_days):
    today = datetime.date.today()
    findings = []
    for page in pages:
        fm = parse_frontmatter(page.read_text(encoding="utf-8")) or {}
        updated = fm.get("updated", "")
        try:
            d = datetime.date.fromisoformat(updated)
        except ValueError:
            continue
        if (today - d).days > max_days:
            findings.append({"page": rel(vault, page), "updated": updated, "days_old": (today - d).days})
    return findings


def check_oversized(vault, pages, max_lines):
    findings = []
    for page in pages:
        n = sum(1 for _ in page.open(encoding="utf-8"))
        if n > max_lines:
            findings.append({"page": rel(vault, page), "lines": n})
    return findings


def check_log_size(vault, max_entries):
    log_path = vault / "log.md"
    if not log_path.exists():
        return None
    entries = sum(1 for line in log_path.read_text(encoding="utf-8").splitlines() if line.startswith("## "))
    return {"entries": entries, "needs_rotation": entries > max_entries}


def check_lancedb_freshness(vault):
    """Best-effort: check if a sibling -lancedb folder's last index file is older
    than the latest vault markdown modification time."""
    lancedb = vault.parent / f"{vault.name}-lancedb"
    if not lancedb.exists():
        return {"status": f"lancedb not configured (skip if intentional). Expected at {lancedb}; "
                          f"set up with openclaw-lancedb-knowledge bootstrap or rerun "
                          f"init_vault.py without --skip-lancedb."}
    latest_md = max((p.stat().st_mtime for p in vault.rglob("*.md")), default=0)
    latest_index = 0
    for p in lancedb.rglob("*.lance"):
        latest_index = max(latest_index, p.stat().st_mtime)
    if latest_index == 0:
        return {"status": "lancedb folder exists but contains no index files; run incremental indexer"}
    return {
        "stale": latest_md > latest_index,
        "vault_latest": datetime.datetime.fromtimestamp(latest_md).isoformat(),
        "index_latest": datetime.datetime.fromtimestamp(latest_index).isoformat(),
    }


def check_should_build(vault, pages, min_sources):
    """Approximate: scan raw source folders for #hashtags and [[wikilink]]-style mentions
    that appear in >= min_sources files but have no page. Full AI version requires
    an LLM and lives in the OpenClaw agent runtime."""
    raw_root = None
    for candidate in ("inbox", "raw", "raw/transcripts", "raw/articles"):
        path = vault / candidate
        if path.exists():
            raw_root = path
            break
    if raw_root is None:
        return {"status": "no source folder found; nothing to check"}

    existing_stems = {p.stem for p in pages}
    mention_counts: dict[str, set] = defaultdict(set)
    candidate_re = re.compile(r"#([\w\-]{3,40})|\[\[([^\]|]+)\]\]")
    for src in raw_root.rglob("*.md"):
        text = src.read_text(encoding="utf-8")
        for hashtag, wikilink in candidate_re.findall(text):
            cand = (hashtag or wikilink).strip()
            mention_counts[cand].add(str(src))
    candidates = [
        {"topic": cand, "mention_count": len(srcs)}
        for cand, srcs in mention_counts.items()
        if len(srcs) >= min_sources and cand not in existing_stems
    ]
    return {
        "method": "keyword-approximation (full AI version requires OpenClaw agent runtime)",
        "candidates": sorted(candidates, key=lambda x: -x["mention_count"])[:50],
    }


def check_missing_cross_refs(auto_fix: bool):
    """Requires AI to determine semantic similarity between pages."""
    return {
        "status": "stub",
        "note": "Requires AI runtime. Invoke `Skill openclaw-llm-wiki` inside a Codex/Claude turn "
                "and ask it to run the cross-ref auto-fill pass (see prompts/lint_missing_cross_refs.md). "
                "CLI invocation cannot do this.",
        "auto_fix_was_set": auto_fix,
    }


def check_data_gaps():
    """Requires AI + access to other vaults/lancedb/discord history."""
    return {
        "status": "stub",
        "note": "Requires AI runtime + cross-source search. Invoke `Skill openclaw-llm-wiki` inside "
                "a Codex/Claude turn and ask it to run the data-gap pass (see prompts/lint_data_gaps.md). "
                "Never web-searches.",
    }


def check_contradictions(vault, pages, stem_to_path):
    """Scan for pages with frontmatter `contradictions: [target]`. Report:
    - target page missing
    - target page no longer flags this page back (one-sided contradiction)
    - contradictions older than 30 days (stale, needs admin resolution)"""
    today = datetime.date.today()
    findings = []
    # First pass: build forward graph of contradictions
    forward: dict[str, list[str]] = {}
    for page in pages:
        fm = parse_frontmatter(page.read_text(encoding="utf-8")) or {}
        raw = fm.get("contradictions", "")
        targets = [t.strip() for t in re.findall(r"[\w\-/]+", raw) if t.strip()]
        if targets:
            forward[page.stem] = targets
    # Second pass: validate each edge
    for src_stem, targets in forward.items():
        src_page = stem_to_path[src_stem]
        fm = parse_frontmatter(src_page.read_text(encoding="utf-8")) or {}
        updated = fm.get("updated", "")
        days_old = None
        try:
            days_old = (today - datetime.date.fromisoformat(updated)).days
        except ValueError:
            pass
        for target in targets:
            issue: dict = {"page": rel(vault, src_page), "target": target}
            if target not in stem_to_path:
                issue["problem"] = "target page missing"
            elif src_stem not in forward.get(target, []):
                issue["problem"] = "one-sided contradiction (target does not flag back)"
            elif days_old is not None and days_old > 30:
                issue["problem"] = f"stale: unresolved for {days_old} days"
            else:
                continue  # healthy contradiction
            findings.append(issue)
    return findings


# ---- runner ----------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vault-path", required=True)
    parser.add_argument("--auto-fix", action="store_true", help="Apply auto-fixes for cross-ref check (no-op in CLI; requires OpenClaw agent runtime)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--no-log", action="store_true", help="Do not append summary to log.md")
    args = parser.parse_args()

    vault = Path(args.vault_path).expanduser().resolve()
    if not vault.exists():
        print(f"vault not found: {vault}\n"
              f"  hint: create it with `python3 {Path(__file__).parent / 'init_vault.py'} "
              f"--vault-path {vault} --team <team> --domain \"<one line>\"`",
              file=sys.stderr)
        return 1
    cfg = load_config(vault / "_meta")
    pages = walk_vault_pages(vault)
    stem_to_path = page_stem_to_path(vault, pages)
    strict_tags = parse_strict_tags(vault / "SCHEMA.md")

    report = {
        "vault": str(vault),
        "total_pages": len(pages),
        "checks": {
            "broken_wikilinks": check_broken_wikilinks(vault, pages, stem_to_path),
            "orphan_pages": check_orphans(vault, pages, stem_to_path),
            "frontmatter_missing": check_frontmatter_missing(vault, pages),
            "tag_drift": check_tag_drift(vault, pages, strict_tags),
            "index_drift": check_index_drift(vault, pages),
            "stale_pages": check_stale(vault, pages, cfg["stale_page_days"]),
            "oversized_pages": check_oversized(vault, pages, cfg["oversized_page_lines"]),
            "log_size": check_log_size(vault, cfg["log_rotate_entries"]),
            "lancedb_freshness": check_lancedb_freshness(vault),
            "should_build_but_not_built": check_should_build(vault, pages, cfg["should_build_min_sources"]),
            "missing_cross_refs": check_missing_cross_refs(args.auto_fix),
            "data_gaps": check_data_gaps(),
            "contradictions": check_contradictions(vault, pages, stem_to_path),
        },
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"vault: {vault} ({len(pages)} pages)\n")
        for name, finding in report["checks"].items():
            if isinstance(finding, list):
                print(f"  [{name}] {len(finding)} issue(s)")
                for item in finding[:5]:
                    print(f"    - {item}")
                if len(finding) > 5:
                    print(f"    ... (+{len(finding)-5} more)")
            else:
                print(f"  [{name}] {finding}")

    if not args.no_log:
        issue_count = sum(
            len(v) if isinstance(v, list) else 0 for v in report["checks"].values()
        )
        date = datetime.date.today().isoformat()
        log_path = vault / "log.md"
        if log_path.exists():
            with log_path.open("a", encoding="utf-8") as f:
                f.write(
                    f"\n## [{date}] lint | {issue_count} schema issues | "
                    f"AI checks pending: missing_cross_refs, data_gaps "
                    f"(invoke via Skill openclaw-llm-wiki agent turn)\n"
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
