# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false
"""Tests for phantom probe split contracts."""

from __future__ import annotations

from proc import CommandResult, Runner
from test_support import RecordingRunner

import phantom


def test_check_phantom_dirty_side_effect_free_shape(monkeypatch, tmp_path) -> None:
    impl = tmp_path / "impl"
    impl.mkdir()
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))

    def dirty_probe(
        _runner: Runner,
        _baseline_file: str,
        *,
        cwd: str | None,
    ) -> tuple[str, str, str]:
        del cwd
        delta = impl / "delta.z"
        _ = delta.write_bytes(b"a.txt\0b.txt\0")
        return ("dirty", "working-tree-dirty", str(delta))

    monkeypatch.setattr(
        phantom,
        "_baseline_dirty_probe",
        dirty_probe,
    )
    runner = RecordingRunner()
    result = phantom.check_phantom_dirty(
        runner,
        step="s1",
        baseline_file=str(impl / "baseline.z"),
        phantom_paths_dir=str(impl),
    )
    assert result.status == "phantom"
    assert result.count == 2
    assert result.paths_file == str(impl / "phantom-paths-s1.z")
    assert not any("check-phantom-dirty.sh" in str(call) for call in runner.calls)


def test_baseline_dirty_probe_ignores_failed_stdout(tmp_path) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("check-mid-run-dirty-tree.sh",),
                1,
                "STATUS=clean\n",
                "boom\n",
                0.01,
            ),
        ],
    )
    status, reason, paths_file = phantom._baseline_dirty_probe(  # pyright: ignore[reportPrivateUsage]
        runner,
        str(tmp_path / "baseline.z"),
        cwd=None,
    )
    assert (status, reason, paths_file) == ("unknown", "check-mid-run-dirty-tree-failed", "")


def test_probe_with_warn_folds_append_failure(monkeypatch, tmp_path) -> None:
    impl = tmp_path / "impl"
    impl.mkdir()
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))

    def dirty_probe(
        _runner: Runner,
        _baseline_file: str,
        *,
        cwd: str | None,
    ) -> tuple[str, str, str]:
        del cwd
        delta = impl / "delta.z"
        _ = delta.write_bytes(b"only.txt\0")
        return ("dirty", "working-tree-dirty", str(delta))

    monkeypatch.setattr(
        phantom,
        "_baseline_dirty_probe",
        dirty_probe,
    )
    runner = RecordingRunner(
        responses=[
            CommandResult(("append",), 1, "", "boom\n", 0.01),
        ],
    )
    result = phantom.probe_with_warn(runner, step="1.r-post-rebase")
    assert result.append_warn_error == "boom"
    assert len(runner.calls) == 2
