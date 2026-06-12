# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# ruff: noqa: F401, TC002
# pylint: skip-file
"""Representative tests for release Python helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import promote_release
import release_prepare
import version_bump
from proc import CommandResult


class QueueRunner:
    def __init__(self, responses: list[CommandResult]):
        self.responses = responses
        self.calls: list[list[str]] = []

    def run(self, argv, **_kwargs):
        self.calls.append(list(argv))
        if not self.responses:
            return CommandResult(tuple(argv), 0, "", "", 0.01)
        return self.responses.pop(0)


def cr(argv, stdout="", stderr="", rc=0):
    return CommandResult(tuple(argv), rc, stdout, stderr, 0.01)


def test_read_plugin_version_best_effort(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / "plugin"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin/plugin.json").write_text('{"version":"9.8.7"}\n', encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(root))
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    assert version_bump.read_plugin_version_main([]) == 0
    assert capsys.readouterr().out == "LARCH_PLUGIN_VERSION=9.8.7\n"


def test_set_version_rejects_downgrade(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    plugin = tmp_path / "plugin.json"
    plugin.write_text(json.dumps({"version": "2.0.0"}), encoding="utf-8")
    monkeypatch.setenv("LARCH_RELEASE_SET_VERSION_PLUGIN_JSON", str(plugin))
    assert version_bump.set_version_main(["1.9.9"]) == 1
    assert "downgrade refused" in capsys.readouterr().err


def test_promote_latest_dry_run_emits_prelude(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = QueueRunner([
        cr(["gh"], json.dumps([{"tagName":"v1.2.3","isPrerelease":True,"isLatest":False,"publishedAt":"2026-01-01T00:00:00Z"}]))
    ])
    monkeypatch.setattr(promote_release.proc, "run", runner.run)
    assert promote_release.promote_latest_main(["--repo", "o/r", "--dry-run"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert "RELEASE_TAG=v1.2.3" in out
    assert "DRY_RUN=true" in out
    assert not any(line == "DRY_RUN=false" for line in out)


def test_release_prepare_override_recomputes_from_current() -> None:
    assert release_prepare._apply_override("1.2.3", "minor") == ("MINOR", "1.3.0")
