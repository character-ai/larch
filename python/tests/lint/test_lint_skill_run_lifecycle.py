"""Tests for shipped-skill universal lifecycle declarations."""

from __future__ import annotations

from pathlib import Path

import pytest

from larch.core import config
from larch.lint import lint_skill_run_lifecycle as lifecycle_lint


def _write_contract(root: Path, *, omit: str = "") -> None:
    verbs = (
        "lifecycle-start",
        "lifecycle-finalize",
        "lifecycle-failure",
        "lifecycle-cancel",
        "lifecycle-early-return",
    )
    text = "\n".join(verb for verb in verbs if verb != omit) + "\n"
    path = root / lifecycle_lint.SHARED_CONTRACT
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def _write_skill(
    root: Path,
    skill: str,
    marker: str | None,
    *,
    developer: bool = False,
    instruction: bool = True,
    allowed_tools: str = "Bash",
) -> None:
    skill_root = Path(".claude/skills") if developer else Path("skills")
    path = root / skill_root / skill / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    marker_line = f"{marker}\n" if marker is not None else ""
    instruction_line = (
        config.SKILL_LIFECYCLE_INSTRUCTION_TEMPLATE.format(skill=skill)
        if instruction
        else ""
    )
    _ = path.write_text(
        f"---\n{marker_line}name: {skill}\nallowed-tools: {allowed_tools}\n---\n\n"
        f"{instruction_line}\n",
        encoding="utf-8",
    )


def _write_empty_skill_roots(root: Path) -> None:
    for relative in lifecycle_lint.SKILL_ROOTS:
        (root / relative).mkdir(parents=True, exist_ok=True)


def test_live_shipped_inventory_is_clean() -> None:
    root = Path(__file__).resolve().parents[3]
    assert lifecycle_lint.lint_root(root) == 0


def test_missing_declaration_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_empty_skill_roots(tmp_path)
    _write_contract(tmp_path)
    _write_skill(tmp_path, "sample", None)

    assert lifecycle_lint.lint_root(tmp_path) == 1
    assert "missing shared run lifecycle declaration" in capsys.readouterr().err


def test_temporary_marker_fails_after_migration(tmp_path: Path) -> None:
    _write_empty_skill_roots(tmp_path)
    _write_contract(tmp_path)
    _write_skill(tmp_path, "sample", "# pending:7827")

    assert lifecycle_lint.lint_root(tmp_path) == 1


@pytest.mark.parametrize(
    "marker",
    [
        "# larch-run-lifecycle: shared-v1",
        "# pending:9999",
    ],
)
def test_partial_or_inexact_declaration_fails(
    tmp_path: Path, marker: str, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_empty_skill_roots(tmp_path)
    _write_contract(tmp_path)
    _write_skill(tmp_path, "sample", marker)

    assert lifecycle_lint.lint_root(tmp_path) == 1
    assert "malformed or partial" in capsys.readouterr().err


def test_declared_skill_must_match_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_empty_skill_roots(tmp_path)
    _write_contract(tmp_path)
    _write_skill(
        tmp_path,
        "sample",
        "# larch-run-lifecycle: shared-v1 skill=other",
    )

    assert lifecycle_lint.lint_root(tmp_path) == 1
    assert "does not match directory" in capsys.readouterr().err


def test_shared_declaration_requires_shared_contract_reference(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_empty_skill_roots(tmp_path)
    _write_contract(tmp_path)
    _write_skill(
        tmp_path,
        "sample",
        "# larch-run-lifecycle: shared-v1 skill=sample",
        instruction=False,
    )

    assert lifecycle_lint.lint_root(tmp_path) == 1
    assert "must reference" in capsys.readouterr().err


def test_shared_declaration_requires_exact_mandatory_instruction(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_empty_skill_roots(tmp_path)
    _write_contract(tmp_path)
    _write_skill(
        tmp_path,
        "sample",
        "# larch-run-lifecycle: shared-v1 skill=sample",
        instruction=False,
    )
    path = tmp_path / "skills" / "sample" / "SKILL.md"
    with path.open("a", encoding="utf-8") as handle:
        _ = handle.write("See skills/shared/run-lifecycle.md.\n")

    assert lifecycle_lint.lint_root(tmp_path) == 1
    assert "exact mandatory instruction" in capsys.readouterr().err


def test_developer_skill_is_part_of_inventory(tmp_path: Path) -> None:
    _write_empty_skill_roots(tmp_path)
    _write_contract(tmp_path)
    _write_skill(
        tmp_path,
        "dev-sample",
        "# larch-run-lifecycle: shared-v1 skill=dev-sample",
        developer=True,
    )

    assert lifecycle_lint.lint_root(tmp_path) == 0


def test_shared_declaration_requires_bash_permission(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_empty_skill_roots(tmp_path)
    _write_contract(tmp_path)
    _write_skill(
        tmp_path,
        "sample",
        "# larch-run-lifecycle: shared-v1 skill=sample",
        allowed_tools="Read, Skill",
    )

    assert lifecycle_lint.lint_root(tmp_path) == 1
    assert "requires Bash permission" in capsys.readouterr().err


def test_shared_contract_rejects_missing_terminal_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_empty_skill_roots(tmp_path)
    _write_contract(tmp_path, omit="lifecycle-cancel")
    _write_skill(
        tmp_path,
        "sample",
        "# larch-run-lifecycle: shared-v1 skill=sample",
    )

    assert lifecycle_lint.lint_root(tmp_path) == 1
    assert "partially wired lifecycle contract" in capsys.readouterr().err


def test_symlinked_skill_directory_is_a_tool_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_empty_skill_roots(tmp_path)
    _write_contract(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "skills" / "linked").symlink_to(outside, target_is_directory=True)

    assert lifecycle_lint.lint_root(tmp_path) == 2
    assert "skill directory is a symlink" in capsys.readouterr().err
