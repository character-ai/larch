# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false
"""CLI contract tests for gh_cli."""

from __future__ import annotations

import json
from pathlib import Path

import gh_cli


def test_workflow_path_prefers_workflow_path(tmp_path: Path, capsys):
    artifact = tmp_path / "artifact.json"
    artifact.write_text(json.dumps({"workflow_path": "HARD", "design_classification": "SIMPLE"}), encoding="utf-8")
    assert gh_cli.workflow_path_main([str(artifact)]) == 0
    assert capsys.readouterr().out.strip() == "HARD"
