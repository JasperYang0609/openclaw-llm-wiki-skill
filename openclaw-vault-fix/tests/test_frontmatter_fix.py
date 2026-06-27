from pathlib import Path

from vaultfix.fixers import fix_frontmatter
from vaultfix.markdown import parse_keys, split_frontmatter
from vaultfix.schema import REQUIRED_FRONTMATTER


def _make_page(tmp_path: Path, rel: str, text: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_adds_all_missing_fields_to_page_without_frontmatter(tmp_path):
    page = _make_page(tmp_path, "decisions/pricing.md", "# Pricing decision\n\nBody.\n")
    change = fix_frontmatter(tmp_path, page, today="2026-06-27")

    assert change.changed
    inner, body = split_frontmatter(change.new_text)
    keys = parse_keys(inner)
    for field in REQUIRED_FRONTMATTER:
        assert field in keys, f"{field} missing after fix"
    # Original body is preserved verbatim.
    assert body == "# Pricing decision\n\nBody.\n"


def test_infers_title_type_and_dates(tmp_path):
    page = _make_page(tmp_path, "customers/acme.md", "# Acme Corp\n\nNotes.\n")
    change = fix_frontmatter(tmp_path, page, today="2026-06-27")
    keys = parse_keys(split_frontmatter(change.new_text)[0])

    assert keys["title"] == "Acme Corp"          # from H1
    assert keys["type"] == "customer"            # from customers/ folder
    assert keys["updated"] == "2026-06-27"
    assert keys["tags"] == "[]"
    assert keys["confidence"] == "low"


def test_title_falls_back_to_humanized_stem(tmp_path):
    page = _make_page(tmp_path, "concepts/value-prop.md", "No heading here.\n")
    change = fix_frontmatter(tmp_path, page, today="2026-06-27")
    keys = parse_keys(split_frontmatter(change.new_text)[0])
    assert keys["title"] == "Value Prop"


def test_only_appends_missing_fields_preserving_existing(tmp_path):
    existing = (
        "---\n"
        "title: Hand Written\n"
        "type: decision\n"
        "tags: [alpha, beta]\n"
        "---\n"
        "# Body\n"
    )
    page = _make_page(tmp_path, "decisions/d.md", existing)
    change = fix_frontmatter(tmp_path, page, today="2026-06-27")

    assert change.changed
    keys = parse_keys(split_frontmatter(change.new_text)[0])
    # Existing values untouched...
    assert keys["title"] == "Hand Written"
    assert keys["tags"] == "[alpha, beta]"  # inline flow list kept verbatim
    # ...and the rest filled in.
    for field in REQUIRED_FRONTMATTER:
        assert field in keys
    # The original three lines still appear in order, unmodified.
    assert "title: Hand Written\ntype: decision\ntags: [alpha, beta]" in change.new_text


def test_complete_page_is_a_noop(tmp_path):
    lines = "\n".join(f"{f}: x" for f in REQUIRED_FRONTMATTER)
    page = _make_page(tmp_path, "sops/s.md", f"---\n{lines}\n---\nBody\n")
    change = fix_frontmatter(tmp_path, page, today="2026-06-27")
    assert not change.changed


def test_unknown_folder_type_is_empty_with_note(tmp_path):
    page = _make_page(tmp_path, "loose-page.md", "# Loose\n")
    change = fix_frontmatter(tmp_path, page, today="2026-06-27")
    keys = parse_keys(split_frontmatter(change.new_text)[0])
    assert keys["type"] == ""
    assert any("infer" in n for n in change.notes)
