import json
from pathlib import Path

import fix as cli


def _vault(tmp_path: Path) -> Path:
    (tmp_path / "decisions").mkdir(parents=True)
    (tmp_path / "decisions" / "a.md").write_text("# Alpha\n\nBody\n", encoding="utf-8")
    (tmp_path / "index.md").write_text("# Index\n", encoding="utf-8")
    return tmp_path


def test_dry_run_changes_nothing_and_exits_2(tmp_path, capsys):
    vault = _vault(tmp_path)
    before = (vault / "decisions" / "a.md").read_text(encoding="utf-8")

    code = cli.main(["--vault-path", str(vault)])
    out = capsys.readouterr().out

    assert code == 2
    assert (vault / "decisions" / "a.md").read_text(encoding="utf-8") == before
    assert "would fix" in out


def test_apply_writes_and_exits_0(tmp_path):
    vault = _vault(tmp_path)
    code = cli.main(["--vault-path", str(vault), "--apply"])
    assert code == 0

    page = (vault / "decisions" / "a.md").read_text(encoding="utf-8")
    assert page.startswith("---\n")
    assert "title: Alpha" in page
    assert "[[a]]" in (vault / "index.md").read_text(encoding="utf-8")


def test_apply_is_idempotent(tmp_path):
    vault = _vault(tmp_path)
    assert cli.main(["--vault-path", str(vault), "--apply"]) == 0
    # Second run finds nothing left to fix.
    assert cli.main(["--vault-path", str(vault), "--apply"]) == 0


def test_only_filter(tmp_path):
    vault = _vault(tmp_path)
    cli.main(["--vault-path", str(vault), "--apply", "--only", "index_drift"])
    # frontmatter was skipped, so the page is still unfixed.
    assert not (vault / "decisions" / "a.md").read_text(encoding="utf-8").startswith("---")
    assert "[[a]]" in (vault / "index.md").read_text(encoding="utf-8")


def test_json_output(tmp_path, capsys):
    vault = _vault(tmp_path)
    cli.main(["--vault-path", str(vault), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["applied"] is False
    assert payload["fixable_count"] >= 1


def test_missing_vault_exits_1(tmp_path, capsys):
    code = cli.main(["--vault-path", str(tmp_path / "nope")])
    assert code == 1
    assert "vault not found" in capsys.readouterr().err
