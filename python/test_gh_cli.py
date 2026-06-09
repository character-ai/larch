# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false
"""CLI contract tests for gh_cli."""

from __future__ import annotations

import json
from pathlib import Path

import gh_cli
from proc import CommandResult
from test_support import RecordingRunner


def test_workflow_path_prefers_workflow_path(tmp_path: Path, capsys):
    artifact = tmp_path / "artifact.json"
    artifact.write_text(json.dumps({"workflow_path": "HARD", "design_classification": "SIMPLE"}), encoding="utf-8")
    assert gh_cli.workflow_path_main([str(artifact)]) == 0
    assert capsys.readouterr().out.strip() == "HARD"


def test_run_logs_main_in_progress_exit_three(monkeypatch, capsys):
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "run", "view", "7"),
                1,
                "",
                "run is still in progress; logs will be available when it is complete",
                0.01,
            ),
        ],
    )
    monkeypatch.setattr(gh_cli, "proc", runner)
    assert gh_cli.run_logs_main(["--run-id", "7", "--repo", "o/r"]) == 3
    assert "Full log: https://github.com/o/r/actions/runs/7" in capsys.readouterr().out


def test_run_logs_main_failure_exit_one(monkeypatch, capsys):
    runner = RecordingRunner(responses=[CommandResult(("gh", "run", "view", "7"), 1, "", "boom", 0.01)])
    monkeypatch.setattr(gh_cli, "proc", runner)
    assert gh_cli.run_logs_main(["--run-id", "7", "--repo", "o/r"]) == 1
    assert "boom" in capsys.readouterr().out


def test_run_logs_main_tails_raw_log(monkeypatch, capsys):
    raw = "\n".join(f"line-{idx}" for idx in range(105))
    runner = RecordingRunner(responses=[CommandResult(("gh", "run", "view", "7"), 0, raw, "", 0.01)])
    monkeypatch.setattr(gh_cli, "proc", runner)
    assert gh_cli.run_logs_main(["--run-id", "7", "--repo", "o/r"]) == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert "line-4" not in lines
    assert "line-5" in lines
    assert "line-104" in lines
