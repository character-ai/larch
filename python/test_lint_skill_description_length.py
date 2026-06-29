from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from larch.lint.lint_skill_description_length import main

if TYPE_CHECKING:
    import pytest


def write_skill(root: Path, rel: str, body: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(body, encoding="utf-8")


def run(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = main(["--root", str(root)])
    return rc, capsys.readouterr().err


def skill_doc(description_line: str) -> str:
    return f"---\nname: fixture\n{description_line}\n---\n\nBody.\n"


def test_clean_quoted_description_at_cap_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(tmp_path, "skills/exact/SKILL.md", skill_doc(f'description: "{"x" * 200}"'))
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_over_cap_fails_with_path_length_and_cap(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(tmp_path, "skills/long/SKILL.md", skill_doc(f'description: "{"x" * 201}"'))
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "lint-skill-description-length: skills/long/SKILL.md" in err
    assert "description is 201 chars" in err
    assert "max 200" in err


def test_public_and_claude_skill_trees_are_scanned(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(tmp_path, "skills/public/SKILL.md", skill_doc(f'description: "{"x" * 201}"'))
    write_skill(tmp_path, ".claude/skills/private/SKILL.md", skill_doc(f'description: "{"y" * 201}"'))
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "skills/public/SKILL.md" in err
    assert ".claude/skills/private/SKILL.md" in err


def test_missing_description_does_not_duplicate_schema_validation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_skill(tmp_path, "skills/missing/SKILL.md", "---\nname: missing\n---\n\nBody.\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_unquoted_value_length_is_measured(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(tmp_path, "skills/unquoted/SKILL.md", skill_doc(f"description: {'x' * 201}"))
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "skills/unquoted/SKILL.md" in err
    assert "description is 201 chars" in err


def test_inline_comment_after_unquoted_value_does_not_count(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_skill(tmp_path, "skills/comment/SKILL.md", skill_doc(f"description: {'x' * 200} # ignored"))
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_hash_inside_quoted_description_counts_as_content(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    description = "#" + ("x" * 200)
    write_skill(tmp_path, "skills/hash/SKILL.md", skill_doc(f'description: "{description}" # ignored'))
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "skills/hash/SKILL.md" in err
    assert "description is 201 chars" in err


def test_apostrophe_in_unquoted_description_does_not_start_a_quote(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_skill(tmp_path, "skills/apostrophe/SKILL.md", skill_doc("description: Use when user's issue #123 is open"))
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_crlf_and_utf8_bom_are_accepted(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "skills/crlf/SKILL.md"
    path.parent.mkdir(parents=True)
    body = f'---\r\nname: crlf\r\ndescription: "{"x" * 200}"\r\n---\r\n\r\nBody.\r\n'
    _ = path.write_bytes(("\ufeff" + body).encode("utf-8"))
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_non_utf8_input_exits_2_through_lint_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "skills/bad/SKILL.md"
    path.parent.mkdir(parents=True)
    _ = path.write_bytes(b"\xff\xfe")
    rc, err = run(tmp_path, capsys)
    assert rc == 2
    assert "skills/bad/SKILL.md" in err
    assert "cannot read file" in err


def test_malformed_frontmatter_without_closing_marker_does_not_crash(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_skill(tmp_path, "skills/malformed/SKILL.md", f'---\nname: malformed\ndescription: "{"x" * 201}"\n')
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err
