# pyright: reportUnusedCallResult=false
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from larch.lint.lint_bg_wait_coverage import main

if TYPE_CHECKING:
    import pytest


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def run(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = main(["--root", str(root)])
    return rc, capsys.readouterr().err


def write_allowlist(root: Path, rows: str = "") -> None:
    base = "skills/shared/design-background-wait.md\tlegacy issue-2 cleanup doc.\n"
    write(root / "python/larch/lint/bg_wait_allowlist.txt", base + rows)


def test_accepts_allowlisted_legacy_skill_doc(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_allowlist(tmp_path)
    write(
        tmp_path / "skills/shared/design-background-wait.md",
        "Use `run_in_background: true` only in this retained legacy contract.",
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_rejects_new_design_background_prose(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_allowlist(tmp_path)
    write(
        tmp_path / "skills/design/SKILL.md",
        "**Immediate-background required — set `run_in_background: true`.**",
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "skills/design/SKILL.md:1:" in err
    assert "run_in_background is forbidden" in err


def test_rejects_research_background_prose(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_allowlist(tmp_path)
    write(
        tmp_path / "skills/research/references/research-phase.md",
        "Use `run_in_background: true` for this lane.",
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "skills/research/references/research-phase.md:1:" in err


def test_ignores_foreground_negative_instruction(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_allowlist(tmp_path)
    write(
        tmp_path / "skills/implement/SKILL.md",
        "Foreground required — do NOT set `run_in_background: true`.",
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_allowlist_rows_need_reasons(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "python/larch/lint/bg_wait_allowlist.txt", "skills/design/SKILL.md")
    write(tmp_path / "skills/design/SKILL.md", "No background here.")
    rc, err = run(tmp_path, capsys)
    assert rc == 2
    assert "malformed allowlist row" in err
