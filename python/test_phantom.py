# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnusedCallResult=false
"""Tests for phantom probe split contracts."""

from __future__ import annotations

import subprocess
from pathlib import Path

from larch.git import git
from larch.core.proc import CommandResult, ProcRunner, Runner
from test_support import RecordingRunner

from larch.implement import phantom


def _impl_dir(tmp_path: Path) -> Path:
    impl = tmp_path / "impl"
    impl.mkdir()
    return impl


def test_check_phantom_dirty_clean_status(monkeypatch, tmp_path) -> None:
    impl = _impl_dir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        phantom,
        "_baseline_dirty_probe",
        lambda *_args, **_kwargs: ("clean", "", ""),
    )
    result = phantom.check_phantom_dirty(
        RecordingRunner(),
        step="clean",
        baseline_file=str(impl / "baseline.z"),
        phantom_paths_dir=str(impl),
    )
    assert result.status == "clean"
    assert result.count == 0
    assert result.paths_file == ""


def test_check_phantom_dirty_tracked_only(monkeypatch, tmp_path) -> None:
    impl = _impl_dir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        phantom,
        "_baseline_dirty_probe",
        lambda *_args, **_kwargs: ("dirty", "working-tree-dirty", ""),
    )
    result = phantom.check_phantom_dirty(
        RecordingRunner(),
        step="tracked",
        baseline_file=str(impl / "baseline.z"),
        phantom_paths_dir=str(impl),
    )
    assert result.status == "tracked-only"


def test_check_phantom_dirty_missing_baseline_unknown(monkeypatch, tmp_path) -> None:
    impl = _impl_dir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        phantom,
        "_baseline_dirty_probe",
        lambda *_args, **_kwargs: ("unknown", "baseline-missing-untracked-ambiguous", ""),
    )
    result = phantom.check_phantom_dirty(
        RecordingRunner(),
        step="missing-baseline",
        baseline_file=str(impl / "missing.z"),
        phantom_paths_dir=str(impl),
    )
    assert result.status == "unknown"
    assert result.reason == "baseline-missing-untracked-ambiguous"


def test_check_phantom_dirty_failed_capture_unknown(monkeypatch, tmp_path) -> None:
    impl = _impl_dir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        phantom,
        "_baseline_dirty_probe",
        lambda *_args, **_kwargs: ("unknown", "check-mid-run-dirty-tree-failed", ""),
    )
    result = phantom.check_phantom_dirty(
        RecordingRunner(),
        step="capture",
        baseline_file=str(impl / "baseline.z"),
        phantom_paths_dir=str(impl),
    )
    assert result.status == "unknown"
    assert result.status != "phantom"


def test_check_phantom_dirty_bad_step_rejected(monkeypatch, tmp_path) -> None:
    impl = _impl_dir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    for bad_step in ("../x", "/", "line\nbreak", "a=1"):
        result = phantom.check_phantom_dirty(
            RecordingRunner(),
            step=bad_step,
            baseline_file=str(impl / "baseline.z"),
            phantom_paths_dir=str(impl),
        )
        assert result.status == "unknown"
        assert result.reason == "bad-step"


def test_check_phantom_dirty_real_repo_phantom(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _ = subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    _ = subprocess.run(["git", "config", "user.email", "t@example.invalid"], cwd=repo, check=True)
    _ = subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    _ = (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    _ = subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    _ = subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    baseline = tmp_path / "baseline.z"
    completed = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    _ = baseline.write_bytes(completed.stdout)
    _ = (repo / "new.txt").write_text("new\n", encoding="utf-8")
    impl = _impl_dir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    result = phantom.check_phantom_dirty(
        ProcRunner(),
        step="2-post-dispatch",
        baseline_file=str(baseline),
        phantom_paths_dir=str(impl),
        cwd=str(repo),
    )
    assert result.status == "phantom"
    assert result.count == 1
    assert Path(result.paths_file).read_bytes() == b"new.txt\0"


def test_check_phantom_dirty_real_repo_empty_baseline_phantom(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "repo-empty"
    repo.mkdir()
    _ = subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    _ = subprocess.run(["git", "config", "user.email", "t@example.invalid"], cwd=repo, check=True)
    _ = subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    _ = (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    _ = subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    _ = subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    baseline = tmp_path / "empty.baseline"
    _ = baseline.write_bytes(b"")
    _ = (repo / "after-empty.txt").write_text("new\n", encoding="utf-8")
    impl = _impl_dir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    result = phantom.check_phantom_dirty(
        ProcRunner(),
        step="empty",
        baseline_file=str(baseline),
        phantom_paths_dir=str(impl),
        cwd=str(repo),
    )
    assert result.status == "phantom"
    assert result.count == 1


def test_check_phantom_dirty_real_repo_space_path_preserved(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "repo-space"
    repo.mkdir()
    _ = subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    _ = subprocess.run(["git", "config", "user.email", "t@example.invalid"], cwd=repo, check=True)
    _ = subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    _ = (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    _ = subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    _ = subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    baseline = tmp_path / "space.baseline"
    completed = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    _ = baseline.write_bytes(completed.stdout)
    spaced = repo / "dir"
    spaced.mkdir()
    _ = (spaced / "name - dash.txt").write_text("new\n", encoding="utf-8")
    impl = _impl_dir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    result = phantom.check_phantom_dirty(
        ProcRunner(),
        step="space.dash",
        baseline_file=str(baseline),
        phantom_paths_dir=str(impl),
        cwd=str(repo),
    )
    assert result.status == "phantom"
    assert Path(result.paths_file).read_bytes() == b"dir/name - dash.txt\0"


def test_check_phantom_dirty_side_effect_free_shape(monkeypatch, tmp_path) -> None:
    impl = tmp_path / "impl"
    impl.mkdir()
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))

    def dirty_probe(
        *,
        runner: Runner,
        baseline_file: str,
        cwd: str | None,
    ) -> tuple[str, str, str]:
        _, _ = runner, baseline_file
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
    assert not any("git check-phantom-dirty" in str(call) for call in runner.calls)


def test_baseline_dirty_probe_reports_detector_unknown(tmp_path) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("python/cli.py dirty-tree",),
                1,
                "STATUS=clean\n",
                "boom\n",
                0.01,
            ),
        ],
    )
    status, reason, paths_file = phantom._baseline_dirty_probe(  runner=# pyright: ignore[reportPrivateUsage]
        runner,
        baseline_file=str(tmp_path / "baseline.z"),
        cwd=None,
    )
    assert status == "unknown"
    assert reason
    assert paths_file == ""


def test_probe_with_warn_folds_append_failure(monkeypatch, tmp_path) -> None:
    impl = tmp_path / "impl"
    impl.mkdir()
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))

    def dirty_probe(
        *,
        runner: Runner,
        baseline_file: str,
        cwd: str | None,
    ) -> tuple[str, str, str]:
        _, _ = runner, baseline_file
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


def test_probe_with_warn_implement_tmpdir_unset(monkeypatch) -> None:
    monkeypatch.delenv("IMPLEMENT_TMPDIR", raising=False)
    runner = RecordingRunner()
    result = phantom.probe_with_warn(runner, step="s1")
    assert result.dirty.status == "unknown"
    assert result.dirty.reason == "IMPLEMENT_TMPDIR-unset"
    assert result.append_warn_error == ""
    assert not runner.calls


def test_probe_with_warn_tracked_only_status(monkeypatch, tmp_path) -> None:
    impl = _impl_dir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        phantom,
        "check_phantom_dirty",
        lambda *_args, **_kwargs: phantom.PhantomDirtyResult(status="tracked-only"),
    )
    result = phantom.probe_with_warn(RecordingRunner(), step="s2")
    assert result.dirty.status == "tracked-only"
    assert result.append_warn_error == ""


def test_probe_with_warn_unknown_append_ok(monkeypatch, tmp_path) -> None:
    impl = _impl_dir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        phantom,
        "check_phantom_dirty",
        lambda *_args, **_kwargs: phantom.PhantomDirtyResult(status="unknown", reason="r1"),
    )
    runner = RecordingRunner(
        responses=[CommandResult(("append",), 0, "APPENDED=true\n", "", 0.01)],
    )
    result = phantom.probe_with_warn(runner, step="s4")
    assert result.dirty.status == "unknown"
    assert result.append_warn_error == ""


def test_probe_with_warn_append_failure_parses_error_kv(monkeypatch, tmp_path) -> None:
    impl = _impl_dir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        phantom,
        "check_phantom_dirty",
        lambda *_args, **_kwargs: phantom.PhantomDirtyResult(status="phantom", count=1),
    )
    runner = RecordingRunner(
        responses=[
            CommandResult(("append",), 2, "FAILED=true\nERROR=stdout-err\n", "", 0.01),
            CommandResult(("append",), 0, "", "", 0.01),
        ],
    )
    result = phantom.probe_with_warn(runner, step="s5")
    assert result.append_warn_error == "stdout-err"


def test_probe_with_warn_append_failure_folds_stderr(monkeypatch, tmp_path) -> None:
    impl = _impl_dir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        phantom,
        "check_phantom_dirty",
        lambda *_args, **_kwargs: phantom.PhantomDirtyResult(status="unknown", reason="u1"),
    )
    runner = RecordingRunner(
        responses=[
            CommandResult(("append",), 2, "", "tail-err\n", 0.01),
            CommandResult(("append",), 0, "", "", 0.01),
        ],
    )
    result = phantom.probe_with_warn(runner, step="s6")
    assert result.append_warn_error == "tail-err"


def test_phantom_probe_main_clean_status(monkeypatch, tmp_path, capsys) -> None:
    impl = _impl_dir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        phantom,
        "probe_with_warn",
        lambda *_args, **_kwargs: phantom.PhantomProbeResult(
            dirty=phantom.PhantomDirtyResult(status="clean"),
        ),
    )
    assert git.phantom_probe_main(["--step", "s1"]) == 0
    captured = capsys.readouterr()
    assert "PHANTOM_STATUS=clean" in captured.out
    assert "PHANTOM_COUNT=" not in captured.out
    assert captured.err.count("→ phantom-probe:") == 1


def test_phantom_probe_main_phantom_emits_count(monkeypatch, tmp_path, capsys) -> None:
    impl = _impl_dir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        phantom,
        "probe_with_warn",
        lambda *_args, **_kwargs: phantom.PhantomProbeResult(
            dirty=phantom.PhantomDirtyResult(status="phantom", count=3, paths_file=str(impl / "paths.z")),
        ),
    )
    assert git.phantom_probe_main(["--step", "s3"]) == 0
    out = capsys.readouterr().out
    assert "PHANTOM_STATUS=phantom" in out
    assert "PHANTOM_COUNT=3" in out


def test_phantom_probe_main_bad_step(monkeypatch, tmp_path, capsys) -> None:
    impl = _impl_dir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    assert git.phantom_probe_main(["--step", "bad!step"]) == 0
    out = capsys.readouterr().out
    assert "PHANTOM_STATUS=unknown" in out
    assert "PHANTOM_REASON=bad-step" in out
