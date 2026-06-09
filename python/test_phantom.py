# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false
"""Tests for phantom probe split contracts."""

from __future__ import annotations

from proc import CommandResult
from test_support import RecordingRunner

import phantom


def test_check_phantom_dirty_side_effect_free_shape(monkeypatch, tmp_path) -> None:
    impl = tmp_path / "impl"
    impl.mkdir()
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        phantom,
        "_baseline_dirty_probe",
        lambda *_a, **_k: ("dirty", "working-tree-dirty", ["a.txt", "b.txt"]),
    )
    runner = RecordingRunner()
    result = phantom.check_phantom_dirty(runner, step="s1")
    assert result.status == "phantom"
    assert result.count == 2
    assert result.paths_file == str(impl / "phantom-paths-s1.z")
    assert not any("check-phantom-dirty.sh" in str(call) for call in runner.calls)


def test_probe_with_warn_folds_append_failure(monkeypatch, tmp_path) -> None:
    impl = tmp_path / "impl"
    impl.mkdir()
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        phantom,
        "_baseline_dirty_probe",
        lambda *_a, **_k: ("dirty", "working-tree-dirty", ["only.txt"]),
    )
    runner = RecordingRunner(
        responses=[
            CommandResult(("append",), 1, "", "boom\n", 0.01),
        ],
    )
    result = phantom.probe_with_warn(runner, step="1.r-post-rebase")
    assert result.append_warn_error == "boom"
    assert len(runner.calls) == 2
