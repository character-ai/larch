"""Tests for phantom probe split contracts."""

from __future__ import annotations

from proc import CommandResult
from test_support import RecordingRunner

import phantom


def test_check_phantom_dirty_side_effect_free_shape():
    runner = RecordingRunner(responses=[CommandResult(("probe",), 0, "STATUS=dirty\nREASON=new-untracked\nPHANTOM_COUNT=2\nPHANTOM_PATHS_FILE=/tmp/p\n", "", 0.01)])
    result = phantom.check_phantom_dirty(runner)
    assert result.status == "dirty"
    assert result.reason == "new-untracked"
    assert result.count == 2
    assert result.paths_file == "/tmp/p"
    assert len(runner.calls) == 1


def test_probe_with_warn_folds_append_failure():
    runner = RecordingRunner(responses=[CommandResult(("probe",), 0, "STATUS=dirty\nREASON=new-untracked\nPHANTOM_COUNT=1\nPHANTOM_PATHS_FILE=/tmp/p\n", "", 0.01), CommandResult(("append",), 1, "", "boom\n", 0.01)])
    result = phantom.probe_with_warn(runner, step_prefix="1.r", short_name="post")
    assert result.append_warn_error == "boom"
    assert len(runner.calls) == 2
