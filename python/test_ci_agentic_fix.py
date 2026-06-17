"""Tests for the delegated agentic CI fixer CLI surface."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import ci_agentic_fix
import ci_monitor
import agents
import proc
from run_context import RunContext

if TYPE_CHECKING:
    import pytest


def test_missing_repo_root_fails_closed(capsys: pytest.CaptureFixture[str]) -> None:
    rc = ci_agentic_fix.main([
        "--pr", "1",
        "--repo", "o/r",
        "--repo-root", "relative",
        "--run-id", "42",
        "--output-dir", "/tmp",
        "--implement-tmpdir", "/tmp",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=waterfall-failed" in out
    assert "DETAIL=missing-repo-root" in out


def test_valid_repo_root_rejects_missing_directory(tmp_path: Path) -> None:
    assert ci_agentic_fix._valid_repo_root(str(tmp_path / "missing")) is None  # pyright: ignore[reportPrivateUsage]


def test_compose_exhausted_detail_includes_log_tail() -> None:
    detail = ci_agentic_fix._compose_exhausted_detail(  # pyright: ignore[reportPrivateUsage]
        "empty-delta",
        "FAIL test_foo.py\n",
    )
    assert detail.startswith("ci-fix-exhausted: empty-delta")
    assert "FAIL test_foo.py" in detail


def test_first_cycle_health_emits_first_fixer_non_health(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    def fake_read_failed_jobs(
        _runner: object,
        *,
        run_id: str,
        repo: str,
        cwd: str | None,
    ) -> tuple[tuple[ci_monitor.FailedJob, ...], str]:
        _ = run_id, repo, cwd
        return ((ci_monitor.FailedJob(name="python-lint", conclusion="failure"),), "ready")

    def fake_collect_failed_logs(
        _runner: object,
        *,
        run_id: str,
        repo: str,
        cwd: str | None,
    ) -> ci_monitor.LogCollectResult:
        _ = run_id, repo, cwd
        return ci_monitor.LogCollectResult(text="FAIL lint\n", state="ready")

    def fake_capture_baseline(
        _runner: object,
        *,
        cwd: str | None,
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], str]:
        _ = cwd
        return (), (), (), "abc123"

    def fake_launch_tier(*_args: object, **_kwargs: object) -> proc.CommandResult:
        return proc.CommandResult(("cli",), 1, "LAUNCHER_EXIT=127\n", "", 0.01)

    def fake_resolve_launcher_exit(*_args: object, **_kwargs: object) -> int:
        return 127

    def fake_classify_launch_failure(*_args: object, **_kwargs: object) -> agents.LaunchFailure:
        return agents.LaunchFailure("health", "binary-missing")

    def fake_rollback(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(ci_monitor, "read_failed_jobs", fake_read_failed_jobs)
    monkeypatch.setattr(ci_monitor, "collect_failed_logs", fake_collect_failed_logs)
    monkeypatch.setattr(ci_monitor, "_capture_baseline", fake_capture_baseline)
    monkeypatch.setattr(agents, "launch_tier", fake_launch_tier)
    monkeypatch.setattr(agents, "resolve_launcher_exit", fake_resolve_launcher_exit)
    monkeypatch.setattr(agents, "classify_launch_failure", fake_classify_launch_failure)
    monkeypatch.setattr(ci_agentic_fix, "_rollback", fake_rollback)

    rc = ci_agentic_fix.main([
        "--pr", "1",
        "--repo", "o/r",
        "--repo-root", str(repo),
        "--run-id", "42",
        "--output-dir", str(out_dir),
        "--implement-tmpdir", str(tmp_path),
        "--max-cycles", "3",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=first-fixer-non-health" in out
    assert "DETAIL=binary-missing" in out


def test_agentic_fix_result_reads_exhausted_detail_file(
    tmp_path: Path,
) -> None:
    detail_file = tmp_path / "exhausted.detail"
    _ = detail_file.write_text(
        "ci-fix-exhausted: empty-delta\nFAIL test_bar.py\n",
        encoding="utf-8",
    )
    kv = (
        "STATUS=ci-fix-exhausted\n"
        "DETAIL=empty-delta\n"
        f"EXHAUSTED_DETAIL_FILE={detail_file}\n"
        "FIX_ATTEMPTED=true\n"
        "DELTA_PATHS=\n"
        "CI_FIX_REBASE_PENDING=false\n"
    )

    class _Runner:
        def run(self, *_args: object, **_kwargs: object) -> proc.CommandResult:
            return proc.CommandResult(("cli",), 0, kv, "", 0.01)

    fix = ci_monitor._agentic_fix_result(  # pyright: ignore[reportPrivateUsage]
        _Runner(),
        pr=1,
        run_id="42",
        repo="o/r",
        plan_file=None,
        cwd="/tmp/repo",
        base_remote="origin",
        base_ref="main",
        ctx=RunContext(
            branch="feat",
            issue="",
            repo="o/r",
            run_id="42",
            tmpdir="/tmp/implement",
            merge=False,
            draft=False,
            forked=False,
            manifest_path="",
            tool_label="claude",
            no_admin_fallback=False,
            repo_unavailable=False,
            pr_number=1,
        ),
    )
    assert fix.status == "fix-exhausted"
    assert "FAIL test_bar.py" in (fix.detail or "")
