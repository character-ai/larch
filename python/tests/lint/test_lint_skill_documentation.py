from __future__ import annotations

from pathlib import Path

import pytest

from larch.lint.lint_skill_documentation import main
from tests.lint.conftest import lint_runner

run = lint_runner(main)


def write(root: Path, rel: str, text: str = "# skill\n") -> None:
    path: Path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def readme(*names: str) -> str:
    entries: str = "\n".join(
        f'<tr><td><a href="docs/skills.md#{name}"><code>/{name}</code></a></td></tr>'
        for name in names
    )
    return f"# Larch\n\n<table>\n{entries}\n</table>\n"


def skills_document(*names: str) -> str:
    return "# Skills\n\n" + "\n\n".join(f"### `/{name}`" for name in names) + "\n"


def write_catalog(root: Path, *, summary: tuple[str, ...], detailed: tuple[str, ...]) -> None:
    write(root, "README.md", readme(*summary))
    write(root, "docs/skills.md", skills_document(*detailed))


def test_all_public_private_and_alias_skills_documented_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "skills/implement/SKILL.md")
    write(tmp_path, "skills/im/SKILL.md")
    write(tmp_path, ".claude/skills/release/SKILL.md")
    write_catalog(
        tmp_path,
        summary=("implement", "im", "release"),
        detailed=("implement", "im", "release"),
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 0, err


def test_missing_readme_summary_entry_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "skills/implement/SKILL.md")
    write_catalog(tmp_path, summary=(), detailed=("implement",))

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "README.md: missing summary-table entry for /implement" in err


def test_readme_prose_does_not_replace_a_summary_table_entry(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "skills/implement/SKILL.md")
    write(tmp_path, "README.md", "# Larch\n\nUse [/implement](docs/skills.md#implement).\n")
    write(tmp_path, "docs/skills.md", skills_document("implement"))

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "README.md: missing summary-table entry for /implement" in err


def test_markdown_alias_table_entry_counts_as_a_summary_entry(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "skills/im/SKILL.md")
    write(tmp_path, "README.md", "# Larch\n\n| Alias | Target |\n| --- | --- |\n| [`/im`](docs/skills.md#im) | /implement |\n")
    write(tmp_path, "docs/skills.md", skills_document("im"))

    rc, err = run(tmp_path, capsys)

    assert rc == 0, err


def test_missing_detailed_heading_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, ".claude/skills/release/SKILL.md")
    write_catalog(tmp_path, summary=("release",), detailed=())

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "docs/skills.md: missing detailed skill heading for /release" in err


def test_detailed_prose_does_not_replace_a_skill_heading(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "skills/implement/SKILL.md")
    write(tmp_path, "README.md", readme("implement"))
    write(tmp_path, "docs/skills.md", "# Skills\n\nUse `/implement`.\n")

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "docs/skills.md: missing detailed skill heading for /implement" in err


def test_documented_skill_without_a_definition_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_catalog(tmp_path, summary=("retired",), detailed=("retired",))

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "README.md: summary-table entry /retired has no matching skill definition" in err
    assert "docs/skills.md: detailed skill heading /retired has no matching skill definition" in err


def test_summary_and_detailed_catalogs_must_match(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "skills/summary-only/SKILL.md")
    write(tmp_path, "skills/detailed-only/SKILL.md")
    write_catalog(tmp_path, summary=("summary-only",), detailed=("detailed-only",))

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "README.md: summary-table entry /summary-only has no matching detailed skill heading" in err
    assert "docs/skills.md: detailed skill heading /detailed-only has no matching summary-table entry" in err


@pytest.mark.parametrize("rel", ["README.md", "docs/skills.md"])
def test_missing_required_document_exits_2(
    rel: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "skills/implement/SKILL.md")
    write(tmp_path, "README.md", readme("implement"))
    write(tmp_path, "docs/skills.md", skills_document("implement"))
    _ = (tmp_path / rel).unlink()

    rc, err = run(tmp_path, capsys)

    assert rc == 2
    assert "required documentation file is missing" in err


def test_symlinked_required_document_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "skills/implement/SKILL.md")
    write(tmp_path, "README-source.md", readme("implement"))
    (tmp_path / "README.md").symlink_to(tmp_path / "README-source.md")
    write(tmp_path, "docs/skills.md", skills_document("implement"))

    rc, err = run(tmp_path, capsys)

    assert rc == 2
    assert "documentation file must not be a symlink" in err


def test_symlinked_skill_definition_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "skills/real/SKILL.md")
    alias_dir: Path = tmp_path / "skills/alias"
    alias_dir.mkdir()
    (alias_dir / "SKILL.md").symlink_to(tmp_path / "skills/real/SKILL.md")
    write_catalog(tmp_path, summary=("real",), detailed=("real",))

    rc, err = run(tmp_path, capsys)

    assert rc == 2
    assert "skill definition must not be a symlink" in err


def test_dangling_skill_definition_symlink_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    alias_dir: Path = tmp_path / "skills/alias"
    alias_dir.mkdir(parents=True)
    (alias_dir / "SKILL.md").symlink_to(tmp_path / "missing-skill.md")
    write_catalog(tmp_path, summary=(), detailed=())

    rc, err = run(tmp_path, capsys)

    assert rc == 2
    assert "skill definition must not be a symlink" in err


def test_symlinked_skill_directory_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "skills/real/SKILL.md")
    (tmp_path / "skills/alias").symlink_to(tmp_path / "skills/real", target_is_directory=True)
    write_catalog(tmp_path, summary=("real",), detailed=("real",))

    rc, err = run(tmp_path, capsys)

    assert rc == 2
    assert "skill directory must not be a symlink" in err


def test_invalid_root_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc: int = main(["--root", str(tmp_path / "missing")])

    assert rc == 2
    assert "--root is not a directory" in capsys.readouterr().err
