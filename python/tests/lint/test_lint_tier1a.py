from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from larch.lint import lint_tier1a

if TYPE_CHECKING:
    import pytest


def _write_tier1a_files(root: Path, line_counts: dict[str, int]) -> None:
    for relpath, line_count in line_counts.items():
        _ = (root / relpath).write_text("x\n" * line_count, encoding="utf-8")


def test_passing_files_at_their_caps(tmp_path: Path) -> None:
    caps = {"AGENTS.md": 2, "KARPATHY_CLAUDE.md": 1, "BASH_AUTHORING.md": 3}
    _write_tier1a_files(tmp_path, caps)

    code, rows = lint_tier1a.check_root(tmp_path, caps)

    assert code == 0
    assert rows == []


def test_one_file_over_cap_exits_1(tmp_path: Path) -> None:
    caps = {"AGENTS.md": 1, "KARPATHY_CLAUDE.md": 1, "BASH_AUTHORING.md": 1}
    _write_tier1a_files(
        tmp_path,
        {"AGENTS.md": 2, "KARPATHY_CLAUDE.md": 1, "BASH_AUTHORING.md": 1},
    )

    code, rows = lint_tier1a.check_root(tmp_path, caps)

    assert code == 1
    assert rows == ["AGENTS.md: 2 lines exceeds cap 1"]


def test_missing_file_exits_2(tmp_path: Path) -> None:
    _ = (tmp_path / "AGENTS.md").write_text("x\n", encoding="utf-8")

    code, rows = lint_tier1a.check_root(
        tmp_path,
        {"AGENTS.md": 1, "KARPATHY_CLAUDE.md": 1, "BASH_AUTHORING.md": 1},
    )

    assert code == 2
    assert rows == ["KARPATHY_CLAUDE.md: missing", "BASH_AUTHORING.md: missing"]


def test_root_points_at_temp_repo(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    caps = lint_tier1a.TIER1A_LINE_CAPS
    _write_tier1a_files(tmp_path, caps)

    assert lint_tier1a.main(["--root", str(tmp_path)]) == 0
    assert capsys.readouterr().err == ""


def test_default_cap_constants_stay_below_pre_trim_counts() -> None:
    caps = lint_tier1a.TIER1A_LINE_CAPS

    assert caps["AGENTS.md"] < 113
    assert caps["KARPATHY_CLAUDE.md"] < 65
    assert caps["BASH_AUTHORING.md"] < 111


def test_malformed_cap_configuration_exits_2(tmp_path: Path) -> None:
    code, rows = lint_tier1a.check_root(tmp_path, {"AGENTS.md": -1})

    assert code == 2
    assert rows == ["tier1a-size: malformed cap for AGENTS.md: -1"]


def test_live_repo_files_pass() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    code, rows = lint_tier1a.check_root(repo_root)

    assert code == 0
    assert rows == []
