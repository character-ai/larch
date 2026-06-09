# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false
"""Tests for phantom probe split contracts."""

from __future__ import annotations

from proc import CommandResult
from test_support import RecordingRunner

import phantom


def test_check_phantom_dirty_side_effect_free_shape(monkeypatch) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", "/tmp/impl")
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("probe",),
                0,
                "STATUS=phantom\nPHANTOM_COUNT=2\nPHANTOM_PATHS_FILE=/tmp/p\n",
                "",
                0.01,
            ),
        ],
    )
    result = phantom.check_phantom_dirty(runner, step="s1")
    assert result.status == "phantom"
    assert result.count == 2
    assert result.paths_file == "/tmp/p"
    assert len(runner.calls) == 1


def test_probe_with_warn_folds_append_failure(monkeypatch) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", "/tmp/impl")
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("probe",),
                0,
                "STATUS=phantom\nPHANTOM_COUNT=1\nPHANTOM_PATHS_FILE=/tmp/p\n",
                "",
                0.01,
            ),
            CommandResult(("append",), 1, "", "boom\n", 0.01),
        ],
    )
    result = phantom.probe_with_warn(runner, step="1.r-post-rebase")
    assert result.append_warn_error == "boom"
    assert len(runner.calls) == 3
