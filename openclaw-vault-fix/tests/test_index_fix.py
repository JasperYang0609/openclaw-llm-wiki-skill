from pathlib import Path

from vaultfix.fixers import fix_index_drift, walk_vault_pages


def _page(tmp_path: Path, rel: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("# x\n", encoding="utf-8")
    return p


def test_appends_unlisted_pages(tmp_path):
    _page(tmp_path, "decisions/a.md")
    _page(tmp_path, "decisions/b.md")
    (tmp_path / "index.md").write_text("# Index\n\n- [[a]]\n", encoding="utf-8")

    pages = walk_vault_pages(tmp_path)
    change = fix_index_drift(tmp_path, pages)

    assert change.changed
    assert "[[b]]" in change.new_text
    assert change.new_text.count("[[a]]") == 1  # already listed, not duplicated


def test_clean_index_is_noop(tmp_path):
    _page(tmp_path, "decisions/a.md")
    (tmp_path / "index.md").write_text("# Index\n\n- [[a]]\n", encoding="utf-8")
    change = fix_index_drift(tmp_path, walk_vault_pages(tmp_path))
    assert not change.changed


def test_missing_index_is_reported_not_created(tmp_path):
    _page(tmp_path, "decisions/a.md")
    change = fix_index_drift(tmp_path, walk_vault_pages(tmp_path))
    assert not change.changed
    assert not (tmp_path / "index.md").exists()
    assert any("missing" in n for n in change.notes)


def test_walk_skips_scaffolding_and_system_dirs(tmp_path):
    _page(tmp_path, "decisions/keep.md")
    _page(tmp_path, "inbox/staged.md")
    _page(tmp_path, "_meta/config.md")
    (tmp_path / "index.md").write_text("# Index\n", encoding="utf-8")
    (tmp_path / "SCHEMA.md").write_text("# Schema\n", encoding="utf-8")

    stems = {p.stem for p in walk_vault_pages(tmp_path)}
    assert stems == {"keep"}
