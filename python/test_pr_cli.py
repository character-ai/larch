# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false
"""CLI contract tests for pr_cli."""

from __future__ import annotations

from pathlib import Path

from test_support import RecordingRunner

import pr_cli


def test_closes_issue_from_body_file(tmp_path: Path, capsys):
    body = tmp_path / "body.md"
    body.write_text("Hello\n\nCloses #3670\n", encoding="utf-8")
    assert pr_cli.closes_issue_main(["--body-file", str(body)]) == 0
    assert capsys.readouterr().out.strip() == "3670"


def test_body_update_missing_file(monkeypatch, capsys):
    monkeypatch.setattr(pr_cli, "proc", RecordingRunner())
    assert pr_cli.body_update_main(["--pr", "1", "--body-file", "/no/such/file"]) == 2
    out = capsys.readouterr().out
    assert "UPDATED=false" in out
    assert "body file not found" in out
