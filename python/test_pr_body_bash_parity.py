"""Bash parity for compose-pr-summary."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import pr_body
from proc import CommandResult

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSE = REPO_ROOT / "scripts" / "compose-pr-summary.sh"


@pytest.mark.skipif(not COMPOSE.is_file(), reason="compose script missing")
def test_compose_summary_semantic_parity(tmp_path: Path) -> None:
    goals = tmp_path / "goals.md"
    _ = goals.write_text("## Goal\n\nParity goal line.\n", encoding="utf-8")
    completed = subprocess.run(
        ["bash", str(COMPOSE), "--plan-goals-file", str(goals)],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert completed.returncode == 0

    class _NoopRunner:
        def run(self, *args: object, **kwargs: object) -> CommandResult:  # pylint: disable=unused-argument
            return CommandResult((), 1, "", "", 0.0)

    py_summary = pr_body.compose_summary_bullets(
        _NoopRunner(),  # type: ignore[arg-type]
        plan_goals_file="goals.md",
        cwd=str(tmp_path),
    )
    assert "Parity goal line" in completed.stdout
    assert "Parity goal line" in py_summary
