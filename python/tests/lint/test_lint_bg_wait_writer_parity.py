# pyright: reportUnusedCallResult=false
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from larch.lint.lint_bg_wait_writer_parity import WRITERS, main

if TYPE_CHECKING:
    import pytest


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def writer_text(*, clone_path: bool = True) -> str:
    clone_line = r"CLONE_PATH=%s\n" if clone_path else ""
    return rf"""
printf 'PID=%s\nCLAUDE_PID=%s\nSTART_EPOCH=%s\nSTEP=fixture-step\nTIMEOUT_S=1\n{clone_line}' \
  "$$" "$claude_pid" "$start" "$clone_path" >"$TMPDIR/.bg-wait-active" 2>/dev/null || true
"""


def write_inventory(
    root: Path,
    *,
    omit_clone_path_for: str | None = None,
    omit_path: str | None = None,
) -> None:
    for spec in WRITERS:
        if spec.path == omit_path:
            continue
        write(root / spec.path, writer_text(clone_path=spec.path != omit_clone_path_for))


def run(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = main(["--root", str(root)])
    return rc, capsys.readouterr().err


def test_accepts_clean_current_writer_inventory(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_inventory(tmp_path)

    rc, err = run(tmp_path, capsys)

    assert rc == 0, err


def test_rejects_step3_writer_without_clone_path_stamp(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    offending = "skills/implement/scripts/run-step-checks.sh"
    write_inventory(tmp_path, omit_clone_path_for=offending)

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert offending in err
    assert "does not emit CLONE_PATH=" in err


def test_rejects_missing_inventory_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = "skills/implement/scripts/step-8-ship.sh"
    write_inventory(tmp_path, omit_path=missing)

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert missing in err
    assert "expected implement Step 8 ship bg-wait writer file is missing" in err


def test_ignores_non_inventory_cleanup_only_marker_references(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_inventory(tmp_path)
    write(tmp_path / "scripts/cleanup-only.sh", 'rm -f "$IMPLEMENT_TMPDIR/.bg-wait-active"')

    rc, err = run(tmp_path, capsys)

    assert rc == 0, err


def test_rejects_inventory_file_without_writer_evidence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    offending = "skills/design/scripts/design-step3b-tail.sh"
    write_inventory(tmp_path)
    write(tmp_path / offending, 'rm -f "$DESIGN_TMPDIR/.bg-wait-active"')

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert offending in err
    assert "no bg-wait marker writer evidence found" in err
