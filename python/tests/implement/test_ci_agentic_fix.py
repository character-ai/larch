"""Tests for the delegated agentic CI fixer CLI surface."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from typing import TYPE_CHECKING

from larch.implement import ci_agentic_fix
from larch.implement import ci_monitor
from larch.agents import agents
from larch.core import coder_delta_guards
from larch.core import config
from larch.core import proc
from larch.core.run_context import RunContext
from larch.report import run_log_flush
from larch.report import run_logs
from test_support import RecordingRunner
from test_support import make_run_context

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pytest


def _make_ctx() -> RunContext:
    return RunContext(
        branch="feat", issue="", repo="o/r", run_id="42",
        tmpdir="/tmp/implement", merge=False, draft=False, forked=False,
        manifest_path="", tool_label="claude", no_admin_fallback=False,
        repo_unavailable=False, pr_number=1,
    )


def _call_agentic_fix(kv: str) -> ci_monitor.FixResult:
    class _KvRunner:
        def run(self, *_a: object, **_kw: object) -> proc.CommandResult:
            return proc.CommandResult(("cli",), 0, kv, "", 0.01)

    return ci_monitor._agentic_fix_result(  # pyright: ignore[reportPrivateUsage]
        _KvRunner(), pr=1, run_id="42", repo="o/r", plan_file=None,
        cwd="/tmp/repo", base_remote="origin", base_ref="main",
        ctx=_make_ctx(),
    )


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
    detail = ci_agentic_fix._compose_exhausted_detail(cycle_detail="empty-delta", failure_log_text="FAIL test_foo.py\n")  # pyright: ignore[reportPrivateUsage]
    assert detail.startswith("ci-fix-exhausted: empty-delta")
    assert "FAIL test_foo.py" in detail


def _write_legacy_guard_fixture(repo: Path) -> None:
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    _ = (scripts / "test-legacy-title-prefix-literals-scope.sh").write_text(
        "#!/usr/bin/env bash\nALLOW=(\n  python/existing.py\n)\n",
        encoding="utf-8",
    )


def test_legacy_prefix_helper_inserts_incident_path(tmp_path: Path) -> None:
    repo = tmp_path
    _write_legacy_guard_fixture(repo)
    (repo / "python").mkdir()
    _ = (repo / "python" / "preflight.py").write_text('TITLE="[PLANNED] x"\n', encoding="utf-8")
    changed, detail = ci_agentic_fix._apply_legacy_prefix_allow_fix(repo_root=repo, failure_log_text="FAIL: legacy prefix literal in unexpected path: python/preflight.py (extend ALLOW= only when deliberate)\n")  # pyright: ignore[reportPrivateUsage]
    assert changed is True
    assert detail == "legacy-prefix-allow:python/preflight.py"
    assert "  'python/preflight.py'\n)" in (repo / "scripts" / "test-legacy-title-prefix-literals-scope.sh").read_text(encoding="utf-8")


def test_legacy_prefix_helper_ignores_other_paths(tmp_path: Path) -> None:
    repo = tmp_path
    _write_legacy_guard_fixture(repo)
    (repo / "python").mkdir()
    _ = (repo / "python" / "other.py").write_text('TITLE="[PLANNED] x"\n', encoding="utf-8")
    changed, detail = ci_agentic_fix._apply_legacy_prefix_allow_fix(repo_root=repo, failure_log_text="FAIL: legacy prefix literal in unexpected path: python/other.py (extend ALLOW= only when deliberate)\n")  # pyright: ignore[reportPrivateUsage]
    assert (changed, detail) == (False, "")


def test_legacy_prefix_helper_requires_literal(tmp_path: Path) -> None:
    repo = tmp_path
    _write_legacy_guard_fixture(repo)
    (repo / "python").mkdir()
    _ = (repo / "python" / "preflight.py").write_text("TITLE='plain'\n", encoding="utf-8")
    changed, detail = ci_agentic_fix._apply_legacy_prefix_allow_fix(repo_root=repo, failure_log_text="FAIL: legacy prefix literal in unexpected path: python/preflight.py (extend ALLOW= only when deliberate)\n")  # pyright: ignore[reportPrivateUsage]
    assert (changed, detail) == (False, "")


def test_finalize_cleanup_partition_helper_rewrites_target_only(tmp_path: Path) -> None:
    makefile = tmp_path / "Makefile"
    _ = makefile.write_text(
        "test-finalize-sanity-check:\n\tpython3 -m pytest python/test_finalize.py -q -k cleanup_target_ok\n\n"
        "test-implement-cleanup-script:\n\tpython3 -m pytest python/test_finalize.py -q -k cleanup\n",
        encoding="utf-8",
    )
    log = (
        "harness pytest partition guard: FAILED\n"
        "python/test_finalize.py: NOT a strict partition\n"
        "cleanup_target_ok\n"
    )
    changed, detail = ci_agentic_fix._apply_finalize_cleanup_partition_fix(repo_root=tmp_path, failure_log_text=log)  # pyright: ignore[reportPrivateUsage]
    assert changed is True
    assert detail == "finalize-cleanup-partition"
    text = makefile.read_text(encoding="utf-8")
    assert "\tpython3 -m pytest python/test_finalize.py -q -k 'cleanup and not cleanup_target_ok'\n" in text
    assert "-k cleanup_target_ok" in text


def test_finalize_cleanup_partition_helper_noops_when_fixed(tmp_path: Path) -> None:
    _ = (tmp_path / "Makefile").write_text(
        "test-implement-cleanup-script:\n\tpython3 -m pytest python/test_finalize.py -q -k 'cleanup and not cleanup_target_ok'\n",
        encoding="utf-8",
    )
    changed, detail = ci_agentic_fix._apply_finalize_cleanup_partition_fix(repo_root=tmp_path, failure_log_text="harness pytest partition guard: FAILED\npython/test_finalize.py: NOT a strict partition\ncleanup_target_ok\n")  # pyright: ignore[reportPrivateUsage]
    assert (changed, detail) == (False, "")


def test_finalize_cleanup_partition_helper_rejects_non_tab_recipe(tmp_path: Path) -> None:
    _ = (tmp_path / "Makefile").write_text(
        "test-implement-cleanup-script:\n  python3 -m pytest python/test_finalize.py -q -k cleanup\n",
        encoding="utf-8",
    )
    changed, detail = ci_agentic_fix._apply_finalize_cleanup_partition_fix(repo_root=tmp_path, failure_log_text="harness pytest partition guard: FAILED\npython/test_finalize.py: NOT a strict partition\ncleanup_target_ok\n")  # pyright: ignore[reportPrivateUsage]
    assert (changed, detail) == (False, "")


def test_apply_known_harness_fix_applies_both_helpers(tmp_path: Path) -> None:
    _write_legacy_guard_fixture(tmp_path)
    (tmp_path / "python").mkdir()
    _ = (tmp_path / "python" / "preflight.py").write_text('TITLE="[IN PROGRESS] x"\n', encoding="utf-8")
    _ = (tmp_path / "Makefile").write_text(
        "test-implement-cleanup-script:\n\tpython3 -m pytest python/test_finalize.py -q -k cleanup\n",
        encoding="utf-8",
    )
    log = (
        "FAIL: legacy prefix literal in unexpected path: python/preflight.py (extend ALLOW= only when deliberate)\n"
        "harness pytest partition guard: FAILED\npython/test_finalize.py: NOT a strict partition\ncleanup_target_ok\n"
    )
    changed, detail = ci_agentic_fix._apply_known_harness_fix(repo_root=tmp_path, failure_log_text=log)  # pyright: ignore[reportPrivateUsage]
    assert changed is True
    assert "legacy-prefix-allow:python/preflight.py" in detail
    assert "finalize-cleanup-partition" in detail


def test_first_cycle_health_emits_ci_fix_exhausted(
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
    assert "STATUS=ci-fix-exhausted" in out
    assert "DETAIL=binary-missing" in out


def test_ci_fix_retry_reason_recognizes_empty_result_sentinel(tmp_path: Path) -> None:
    output = tmp_path / "claude.out"
    _ = output.write_text("CLAUDE_CI_EMPTY_RESULT\n", encoding="utf-8")
    _ = output.with_suffix(output.suffix + ".done").write_text("1\n", encoding="utf-8")

    retry_reason = ci_agentic_fix._ci_fix_retry_reason(  # pyright: ignore[reportPrivateUsage]
        launcher_exit=1,
        output=output,
        binary_present=True,
    )

    assert retry_reason == "empty-result"


def test_ci_fix_retry_reason_skips_permanent_done_rc(tmp_path: Path) -> None:
    output = tmp_path / "claude.out"
    _ = output.write_text("", encoding="utf-8")
    _ = output.with_suffix(output.suffix + ".done").write_text("127\n", encoding="utf-8")

    retry_reason = ci_agentic_fix._ci_fix_retry_reason(  # pyright: ignore[reportPrivateUsage]
        launcher_exit=1,
        output=output,
        binary_present=True,
    )

    assert retry_reason is None


def test_ci_fix_retry_reason_skips_auth_empty_output(tmp_path: Path) -> None:
    output = tmp_path / "claude.out"
    _ = output.write_text("", encoding="utf-8")
    _ = output.with_suffix(output.suffix + ".done").write_text("1\n", encoding="utf-8")
    _ = output.with_suffix(output.suffix + ".diag").write_text("apiKeyHelper failed\n", encoding="utf-8")

    retry_reason = ci_agentic_fix._ci_fix_retry_reason(  # pyright: ignore[reportPrivateUsage]
        launcher_exit=1,
        output=output,
        binary_present=True,
    )

    assert retry_reason is None


def test_ci_fix_retry_reason_keeps_transient_empty_retry(tmp_path: Path) -> None:
    output = tmp_path / "claude.out"
    _ = output.write_text("", encoding="utf-8")
    _ = output.with_suffix(output.suffix + ".done").write_text("1\n", encoding="utf-8")

    retry_reason = ci_agentic_fix._ci_fix_retry_reason(  # pyright: ignore[reportPrivateUsage]
        launcher_exit=1,
        output=output,
        binary_present=True,
    )

    assert retry_reason == "empty-output"


def test_first_cycle_binary_missing_empty_output_skips_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    launch_calls = {"n": 0}

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

    def fake_launch_tier(*_args: object, **kwargs: object) -> proc.CommandResult:
        launch_calls["n"] += 1
        output = Path(str(kwargs["output"]))
        _ = output.write_text("", encoding="utf-8")
        _ = output.with_suffix(output.suffix + ".done").write_text("127\n", encoding="utf-8")
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
    assert "STATUS=ci-fix-exhausted" in out
    assert "DETAIL=binary-missing" in out
    assert launch_calls["n"] == 1


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

    fix = _call_agentic_fix(kv)
    assert fix.status == "fix-exhausted"
    assert "FAIL test_bar.py" in (fix.detail or "")


def test_agentic_fix_result_local_unfixable_prefixes_detail(tmp_path: Path) -> None:
    detail_file = tmp_path / "local-unfixable.detail"
    _ = detail_file.write_text(
        "local-unfixable: gitleaks\nFAIL gitleaks scan\n",
        encoding="utf-8",
    )
    kv = (
        "STATUS=local-unfixable\n"
        "DETAIL=gitleaks\n"
        f"EXHAUSTED_DETAIL_FILE={detail_file}\n"
        "FIX_ATTEMPTED=false\n"
        "DELTA_PATHS=\n"
        "CI_FIX_REBASE_PENDING=false\n"
    )

    fix = _call_agentic_fix(kv)
    assert fix.status == "local-unfixable"
    assert fix.detail == "local-unfixable: gitleaks\nFAIL gitleaks scan"


def test_agentic_fix_result_missing_repo_root_fail_closed() -> None:
    fix = ci_monitor._agentic_fix_result(  # pyright: ignore[reportPrivateUsage]
        proc,
        pr=1,
        run_id="42",
        repo="o/r",
        plan_file=None,
        cwd=None,
        base_remote="origin",
        base_ref="main",
        ctx=None,
    )
    assert fix.status == "waterfall-failed"
    assert fix.detail == "missing repo_root"


def test_first_cycle_transient_health_continues_delegate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    cycles = {"n": 0}

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
        return proc.CommandResult(("cli",), 1, "LAUNCHER_EXIT=1\n", "", 0.01)

    def fake_resolve_launcher_exit(*_args: object, **_kwargs: object) -> int:
        return 1

    def fake_classify_launch_failure(*_args: object, **_kwargs: object) -> agents.LaunchFailure:
        return agents.LaunchFailure("health", "health-probe")

    def fake_rollback(*_args: object, **_kwargs: object) -> None:
        return None

    def fake_run_cycle(*_args: object, **_kwargs: object) -> tuple[str, str, bool, tuple[str, ...], bool, str | None, str]:
        cycles["n"] += 1
        if cycles["n"] < 2:
            return "waterfall-failed", "health-probe", True, (), False, None, "FAIL lint\n"
        return "passed", "", True, ("file.py",), False, None, ""

    monkeypatch.setattr(ci_monitor, "read_failed_jobs", fake_read_failed_jobs)
    monkeypatch.setattr(ci_monitor, "collect_failed_logs", fake_collect_failed_logs)
    monkeypatch.setattr(ci_monitor, "_capture_baseline", fake_capture_baseline)
    monkeypatch.setattr(agents, "launch_tier", fake_launch_tier)
    monkeypatch.setattr(agents, "resolve_launcher_exit", fake_resolve_launcher_exit)
    monkeypatch.setattr(agents, "classify_launch_failure", fake_classify_launch_failure)
    monkeypatch.setattr(ci_agentic_fix, "_rollback", fake_rollback)
    monkeypatch.setattr(ci_agentic_fix, "_run_cycle", fake_run_cycle)

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
    assert "STATUS=passed" in out
    assert cycles["n"] == 2


def test_mixed_fixable_and_unfixable_launches_claude(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    launch_calls = {"n": 0}

    def fake_read_failed_jobs(
        _runner: object,
        *,
        run_id: str,
        repo: str,
        cwd: str | None,
    ) -> tuple[tuple[ci_monitor.FailedJob, ...], str]:
        _ = run_id, repo, cwd
        return (
            (
                ci_monitor.FailedJob(name="python-lint", conclusion="failure"),
                ci_monitor.FailedJob(name="gitleaks", conclusion="failure"),
            ),
            "ready",
        )

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

    def fake_launch_tier(*_args: object, **kwargs: object) -> proc.CommandResult:
        launch_calls["n"] += 1
        _ = Path(str(kwargs["output"])).write_text("failure details\n", encoding="utf-8")
        return proc.CommandResult(("cli",), 1, "LAUNCHER_EXIT=1\n", "", 0.01)

    def fake_resolve_launcher_exit(*_args: object, **_kwargs: object) -> int:
        return 1

    def fake_classify_launch_failure(*_args: object, **_kwargs: object) -> agents.LaunchFailure:
        return agents.LaunchFailure("other", "parse")

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
        "--max-cycles", "1",
    ])
    assert rc == 0
    assert launch_calls["n"] == 1
    out = capsys.readouterr().out
    assert "STATUS=first-fixer-non-health" in out


def test_head_changed_continues_until_cycle_cap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    cycles = {"n": 0}

    def fake_run_cycle(*_args: object, **_kwargs: object) -> tuple[str, str, bool, tuple[str, ...], bool, str | None, str]:
        cycles["n"] += 1
        return "waterfall-failed", "head-changed", True, (), False, None, "FAIL lint\n"

    monkeypatch.setattr(ci_agentic_fix, "_run_cycle", fake_run_cycle)

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
    assert "STATUS=ci-fix-exhausted" in out
    assert cycles["n"] == 3


def test_ci_wait_rebase_action_surfaces_rebase_required(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    def fake_run_cycle(*_args: object, **_kwargs: object) -> tuple[str, str, bool, tuple[str, ...], bool, str | None, str]:
        return "rebase-required", "ci-wait-rebase-required", True, ("a.py",), True, None, ""

    monkeypatch.setattr(ci_agentic_fix, "_run_cycle", fake_run_cycle)

    rc = ci_agentic_fix.main([
        "--pr", "1",
        "--repo", "o/r",
        "--repo-root", str(repo),
        "--run-id", "42",
        "--output-dir", str(out_dir),
        "--implement-tmpdir", str(tmp_path),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=rebase-required" in out
    assert "CI_FIX_REBASE_PENDING=true" in out


def test_wait_for_ci_fails_closed_on_nonzero_exit(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()

    class _Runner:
        def run(self, *_args: object, **_kwargs: object) -> proc.CommandResult:
            return proc.CommandResult(("cli",), 1, "", "wait crashed", 0.01)

    args = Namespace(
        pr=1,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        output_dir=str(out_dir),
    )
    parsed, err = ci_agentic_fix._wait_for_ci(  # pyright: ignore[reportPrivateUsage]
        _Runner(),
        args=args,
        repo_root=repo,
        cycle=1,
    )
    assert not parsed
    assert err == "ci-wait-exit-1"


def test_wait_for_ci_fails_closed_on_malformed_output(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    wait_out = out_dir / "ci-agentic-wait-1.out"
    _ = wait_out.write_text("UNRELATED=noise\n", encoding="utf-8")

    class _Runner:
        def run(self, *_args: object, **_kwargs: object) -> proc.CommandResult:
            return proc.CommandResult(("cli",), 0, "", "", 0.01)

    args = Namespace(
        pr=1,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        output_dir=str(out_dir),
    )
    parsed, err = ci_agentic_fix._wait_for_ci(  # pyright: ignore[reportPrivateUsage]
        _Runner(),
        args=args,
        repo_root=repo,
        cycle=1,
    )
    assert not parsed
    assert err == "ci-wait-malformed-output"


def test_run_cycle_invalidates_guidelines_via_stage_callback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run_case(*, known_helper: bool) -> None:
        repo = tmp_path / f"repo-{known_helper}"
        repo.mkdir()
        out_dir = tmp_path / f"out-{known_helper}"
        out_dir.mkdir()
        implement_dir = tmp_path / f"implement-{known_helper}"
        invalidated: list[str] = []
        push_calls: list[str] = []

        args = Namespace(
            pr=1,
            repo="o/r",
            repo_root=str(repo),
            run_id="42",
            plan_file="",
            base_remote="origin",
            base_ref="main",
            output_dir=str(out_dir),
            implement_tmpdir=str(implement_dir),
        )
        ctx = make_run_context(tmpdir=str(implement_dir), run_id="42", repo="o/r")
        _ = run_logs.init_run(ctx)
        _ = (implement_dir / ".execution-issues-step7a-reached").write_text("", encoding="utf-8")

        def fake_read_failed_jobs(*_args: object, **_kwargs: object) -> tuple[tuple[ci_monitor.FailedJob, ...], str]:
            return ((ci_monitor.FailedJob(name="python-lint", conclusion="failure"),), "ready")

        def fake_collect_failed_logs(*_args: object, **_kwargs: object) -> ci_monitor.LogCollectResult:
            return ci_monitor.LogCollectResult(text="FAIL lint\n", state="ready")

        def fake_capture_baseline(
            *_args: object,
            **_kwargs: object,
        ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], str]:
            return (), (), (), "abc123"

        def fake_known_fix(*_args: object, **_kwargs: object) -> tuple[bool, str]:
            return known_helper, "known" if known_helper else ""

        def fake_launch_tier(*_args: object, **kwargs: object) -> proc.CommandResult:
            _ = Path(str(kwargs["output"])).write_text("fixed\n", encoding="utf-8")
            return proc.CommandResult(("cli",), 0, "LAUNCHER_EXIT=0\n", "", 0.01)

        def fake_commit_with_trailer(*_args: object, **_kwargs: object) -> proc.CommandResult:
            return proc.CommandResult(("git", "commit"), 0, "", "", 0.01)

        def fake_fetch(*_args: object, **_kwargs: object) -> proc.CommandResult:
            return proc.CommandResult(("git", "fetch"), 0, "", "", 0.01)

        def fake_current_branch(*_args: object, **_kwargs: object) -> str:
            return "feat"

        def fake_try_rev_parse(*_args: object, **_kwargs: object) -> str:
            return "abc123"

        def fake_push(*args: object, **_kwargs: object) -> proc.CommandResult:
            push_calls.append(str(args[2]))
            return proc.CommandResult(("git", "push"), 0, "", "", 0.01)

        def fake_wait_for_ci(*_args: object, **_kwargs: object) -> tuple[dict[str, str], str | None]:
            batch = implement_dir / "larch-logs" / "implement" / "42" / "execution-issues.ndjson"
            assert batch.is_file()
            issue_text = batch.read_text(encoding="utf-8")
            assert "architectural-guidelines drop notice persist failed before invalidate" in issue_text
            assert (implement_dir / ".execution-issues-flushed.sha").is_file()
            return {"ACTION": "merge", "CI_STATUS": "pass"}, None

        def fake_prepare_python_toolchain(*_args: object, **_kwargs: object) -> bool:
            return True

        def fake_verify_job_locally(*_args: object, **_kwargs: object) -> bool:
            return True

        def fake_delta_paths(*_args: object, **_kwargs: object) -> tuple[str, ...]:
            return ("file.py",)

        def fake_resolve_launcher_exit(*_args: object, **_kwargs: object) -> int:
            return 0

        def fake_classify_launch_failure(*_args: object, **_kwargs: object) -> agents.LaunchFailure:
            return agents.LaunchFailure("none", "")

        def fake_capture_head(*_args: object, **_kwargs: object) -> str:
            return "abc123"

        def fake_head_changed(*_args: object, **_kwargs: object) -> bool:
            return False

        def fake_forbidden_paths(*_args: object, **_kwargs: object) -> tuple[str, ...]:
            return ()

        def fake_revert_forbidden_paths(*_args: object, **_kwargs: object) -> int:
            return 0

        def fake_invalidate(implement_tmpdir: str) -> bool:
            invalidated.append(implement_tmpdir)
            run_logs.append_execution_issue(
                log_file=Path(implement_tmpdir) / "execution-issues.md",
                category="Warnings",
                entry="- **architectural-guidelines drop notice persist failed before invalidate**",
            )
            return True

        def fake_commit_run(*_args: object, **_kwargs: object) -> proc.CommandResult:
            return proc.CommandResult(("git", "commit"), 0, "", "", 0.01)

        def fake_run_log_flush_noop(*_args: object, **_kwargs: object) -> None:
            return None

        monkeypatch.setattr(ci_monitor, "read_failed_jobs", fake_read_failed_jobs)
        monkeypatch.setattr(ci_monitor, "collect_failed_logs", fake_collect_failed_logs)
        monkeypatch.setattr(ci_monitor, "_capture_baseline", fake_capture_baseline)
        monkeypatch.setattr(ci_agentic_fix, "_apply_known_harness_fix", fake_known_fix)
        monkeypatch.setattr(ci_monitor, "prepare_python_toolchain", fake_prepare_python_toolchain)
        monkeypatch.setattr(ci_monitor, "verify_job_locally", fake_verify_job_locally)
        monkeypatch.setattr(ci_monitor, "_delta_paths", fake_delta_paths)
        monkeypatch.setattr(ci_monitor.git, "commit_with_trailer", fake_commit_with_trailer)
        monkeypatch.setattr(ci_monitor.git, "fetch", fake_fetch)
        monkeypatch.setattr(ci_monitor.git, "current_branch", fake_current_branch)
        monkeypatch.setattr(ci_monitor.git, "try_rev_parse", fake_try_rev_parse)
        monkeypatch.setattr(ci_monitor.git, "push", fake_push)
        monkeypatch.setattr(agents, "launch_tier", fake_launch_tier)
        monkeypatch.setattr(agents, "resolve_launcher_exit", fake_resolve_launcher_exit)
        monkeypatch.setattr(agents, "classify_launch_failure", fake_classify_launch_failure)
        monkeypatch.setattr(coder_delta_guards, "capture_head", fake_capture_head)
        monkeypatch.setattr(coder_delta_guards, "head_changed_from_baseline", fake_head_changed)
        monkeypatch.setattr(coder_delta_guards, "coder_forbidden_paths", fake_forbidden_paths)
        monkeypatch.setattr(coder_delta_guards, "revert_forbidden_paths", fake_revert_forbidden_paths)
        monkeypatch.setattr(ci_agentic_fix.ship_guidelines, "_invalidate_guidelines_note", fake_invalidate)
        monkeypatch.setattr(run_log_flush, "_commit_run", fake_commit_run)
        monkeypatch.setattr(run_log_flush, "_write_final_report", fake_run_log_flush_noop)
        monkeypatch.setattr(run_log_flush, "capture_session_transcript", fake_run_log_flush_noop)
        monkeypatch.setattr(run_log_flush, "_render_ledger_reports", fake_run_log_flush_noop)
        monkeypatch.setattr(run_log_flush, "_render_token_timing_batches", fake_run_log_flush_noop)
        monkeypatch.setattr(run_log_flush, "_refresh_difficulty_record", fake_run_log_flush_noop)
        monkeypatch.setattr(run_log_flush, "_stage_vendor_failure_diagnostics", fake_run_log_flush_noop)
        monkeypatch.setattr(run_log_flush, "_stage_ship_route_handoff", fake_run_log_flush_noop)
        monkeypatch.setattr(run_log_flush, "_reconcile_stalled_summary_backstop", fake_run_log_flush_noop)
        monkeypatch.setattr(ci_agentic_fix, "_wait_for_ci", fake_wait_for_ci)
        monkeypatch.setattr(run_logs, "_commit_run", fake_commit_run)

        status, _detail, _attempted, paths, pending, _next_run, _log_text = ci_agentic_fix._run_cycle(  # pyright: ignore[reportPrivateUsage]
            RecordingRunner(),
            args=args,
            repo_root=repo,
            ctx=ctx,
            cycle=1,
            run_id="42",
        )

        assert status == "passed"
        assert paths == ("file.py",)
        assert pending is False
        assert invalidated == [str(implement_dir)]
        assert push_calls == ["feat"]


    run_case(known_helper=True)
    run_case(known_helper=False)


def test_agentic_fix_result_missing_implement_tmpdir_fail_closed() -> None:
    fix = ci_monitor._agentic_fix_result(  # pyright: ignore[reportPrivateUsage]
        proc,
        pr=1,
        run_id="42",
        repo="o/r",
        plan_file=None,
        cwd="/tmp/repo",
        base_remote="origin",
        base_ref="main",
        ctx=None,
    )
    assert fix.status == "waterfall-failed"
    assert fix.detail == "missing implement_tmpdir"


def test_wait_for_ci_accepts_action_bail(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    wait_out = out_dir / "ci-agentic-wait-1.out"
    _ = wait_out.write_text(
        "ACTION=bail\nBAIL_REASON=CI_WAIT_BAIL_POLL_BUDGET_EXHAUSTED\n",
        encoding="utf-8",
    )

    class _Runner:
        def run(self, *_args: object, **_kwargs: object) -> proc.CommandResult:
            return proc.CommandResult(("cli",), 0, "", "", 0.01)

    args = Namespace(
        pr=1,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        output_dir=str(out_dir),
    )
    parsed, err = ci_agentic_fix._wait_for_ci(  # pyright: ignore[reportPrivateUsage]
        _Runner(),
        args=args,
        repo_root=repo,
        cycle=1,
    )
    assert err is None
    assert parsed.get("ACTION") == "bail"


def test_wait_for_ci_passes_post_fix_empty_checks_grace(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    wait_out = out_dir / "ci-agentic-wait-1.out"
    _ = wait_out.write_text("ACTION=merge\n", encoding="utf-8")
    seen_args: list[list[str]] = []

    class _Runner:
        def run(self, argv: Sequence[str], **_kwargs: object) -> proc.CommandResult:
            seen_args.append(list(argv))
            return proc.CommandResult(("cli",), 0, "", "", 0.01)

    args = Namespace(
        pr=1,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        output_dir=str(out_dir),
    )
    parsed, err = ci_agentic_fix._wait_for_ci(  # pyright: ignore[reportPrivateUsage]
        _Runner(),
        args=args,
        repo_root=repo,
        cycle=1,
    )
    assert err is None
    assert parsed.get("ACTION") == "merge"
    assert seen_args
    cli_args = seen_args[0]
    grace_idx = cli_args.index("--empty-checks-grace")
    assert cli_args[grace_idx + 1] == str(config.CI_WAIT_POST_FIX_EMPTY_CHECKS_GRACE_SEC)


def test_first_cycle_quota_emits_ci_fix_exhausted(
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
        return proc.CommandResult(("cli",), 1, "LAUNCHER_EXIT=1\n", "", 0.01)

    def fake_resolve_launcher_exit(*_args: object, **_kwargs: object) -> int:
        return 1

    def fake_classify_launch_failure(*_args: object, **_kwargs: object) -> agents.LaunchFailure:
        return agents.LaunchFailure("health", "quota")

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
    assert "STATUS=ci-fix-exhausted" in out
    assert "DETAIL=quota" in out


def test_agentic_fix_result_timeout_reads_push_checkpoint(tmp_path: Path) -> None:
    implement = tmp_path / "implement"
    implement.mkdir()
    checkpoint_dir = implement / "ci-agentic-fix"
    checkpoint_dir.mkdir()
    _ = (checkpoint_dir / "ci-agentic-push-checkpoint.latest").write_text(
        "RUN_ID=42\nDELTA_PATHS=a.py\nCI_FIX_REBASE_PENDING=true\nDETAIL=wait-timeout\n",
        encoding="utf-8",
    )

    class _Runner:
        def run(self, *_args: object, **_kwargs: object) -> proc.CommandResult:
            return proc.CommandResult(("cli",), config.EXIT_TIMEOUT, "", "", 0.01)

    fix = ci_monitor._agentic_fix_result(  # pyright: ignore[reportPrivateUsage]
        _Runner(),
        pr=1,
        run_id="42",
        repo="o/r",
        plan_file=None,
        cwd=str(tmp_path / "repo"),
        base_remote="origin",
        base_ref="main",
        ctx=RunContext(
            branch="feat",
            issue="",
            repo="o/r",
            run_id="42",
            tmpdir=str(implement),
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
    assert fix.status == "pushed"
    assert fix.ci_fix_rebase_pending is True
    assert fix.delta_paths == ("a.py",)


def test_run_cycle_empty_delta_returns_no_progress_without_push(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    push_calls = {"n": 0}

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

    def fake_launch_tier(*_args: object, **kwargs: object) -> proc.CommandResult:
        _ = Path(str(kwargs["output"])).write_text("fixed\n", encoding="utf-8")
        return proc.CommandResult(("cli",), 0, "LAUNCHER_EXIT=0\n", "", 0.01)

    def fake_resolve_launcher_exit(*_args: object, **_kwargs: object) -> int:
        return 0

    def fake_classify_launch_failure(*_args: object, **_kwargs: object) -> agents.LaunchFailure:
        return agents.LaunchFailure("none", "")

    def fake_prepare_python_toolchain(*_args: object, **_kwargs: object) -> bool:
        return True

    def fake_verify_job_locally(*_args: object, **_kwargs: object) -> bool:
        return True

    def fake_delta_paths(*_args: object, **_kwargs: object) -> tuple[str, ...]:
        return ()

    def fake_stage_and_push(*_args: object, **_kwargs: object) -> tuple[bool, str | None, tuple[str, ...], bool, bool]:
        push_calls["n"] += 1
        return True, "head", ("a.py",), False, False

    def fake_rollback(*_args: object, **_kwargs: object) -> None:
        return None

    def fake_capture_head(*_args: object, **_kwargs: object) -> str:
        return "abc123"

    def fake_head_changed(*_args: object, **_kwargs: object) -> bool:
        return False

    def fake_forbidden_paths(*_args: object, **_kwargs: object) -> tuple[str, ...]:
        return ()

    def fake_revert_forbidden(*_args: object, **_kwargs: object) -> int:
        return 0

    monkeypatch.setattr(ci_monitor, "read_failed_jobs", fake_read_failed_jobs)
    monkeypatch.setattr(ci_monitor, "collect_failed_logs", fake_collect_failed_logs)
    monkeypatch.setattr(ci_monitor, "_capture_baseline", fake_capture_baseline)
    monkeypatch.setattr(ci_monitor, "prepare_python_toolchain", fake_prepare_python_toolchain)
    monkeypatch.setattr(ci_monitor, "verify_job_locally", fake_verify_job_locally)
    monkeypatch.setattr(ci_monitor, "_delta_paths", fake_delta_paths)
    monkeypatch.setattr(ci_monitor, "stage_and_push", fake_stage_and_push)
    monkeypatch.setattr(agents, "launch_tier", fake_launch_tier)
    monkeypatch.setattr(agents, "resolve_launcher_exit", fake_resolve_launcher_exit)
    monkeypatch.setattr(agents, "classify_launch_failure", fake_classify_launch_failure)
    monkeypatch.setattr(ci_agentic_fix, "_rollback", fake_rollback)
    monkeypatch.setattr(ci_agentic_fix.coder_delta_guards, "capture_head", fake_capture_head)
    monkeypatch.setattr(ci_agentic_fix.coder_delta_guards, "head_changed_from_baseline", fake_head_changed)
    monkeypatch.setattr(ci_agentic_fix.coder_delta_guards, "coder_forbidden_paths", fake_forbidden_paths)
    monkeypatch.setattr(ci_agentic_fix.coder_delta_guards, "revert_forbidden_paths", fake_revert_forbidden)

    args = Namespace(
        pr=1,
        repo="o/r",
        plan_file="",
        base_remote="origin",
        base_ref="main",
        output_dir=str(out_dir),
    )
    ctx = make_run_context(
        issue="",
        run_id="42",
        tmpdir=str(tmp_path),
        merge=False,
        manifest_path="",
        tool_label="claude",
        pr_number=1,
    )
    status, detail, attempted, _delta, _pending, _next_run, _log = ci_agentic_fix._run_cycle(  # pyright: ignore[reportPrivateUsage]
        proc,
        args=args,
        repo_root=repo,
        ctx=ctx,
        cycle=1,
        run_id="42",
    )
    assert status == "no-progress"
    assert detail == "empty-delta"
    assert attempted is True
    assert push_calls["n"] == 0


def _stub_successful_fix_until_wait(
    monkeypatch: pytest.MonkeyPatch,
    *,
    wait_result: tuple[dict[str, str], str | None],
) -> dict[str, int]:
    calls = {"push": 0}

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
        return proc.CommandResult(("cli",), 0, "LAUNCHER_EXIT=0\n", "", 0.01)

    def fake_resolve_launcher_exit(*_args: object, **_kwargs: object) -> int:
        return 0

    def fake_classify_launch_failure(*_args: object, **_kwargs: object) -> agents.LaunchFailure:
        return agents.LaunchFailure("none", "")

    def fake_prepare_python_toolchain(*_args: object, **_kwargs: object) -> bool:
        return True

    def fake_verify_job_locally(*_args: object, **_kwargs: object) -> bool:
        return True

    def fake_delta_paths(*_args: object, **_kwargs: object) -> tuple[str, ...]:
        return ("fixed.py",)

    def fake_stage_and_push(*_args: object, **_kwargs: object) -> tuple[bool, str | None, tuple[str, ...], bool, bool]:
        calls["push"] += 1
        return True, "head", ("fixed.py",), False, False

    def fake_capture_head(*_args: object, **_kwargs: object) -> str:
        return "abc123"

    def fake_head_changed(*_args: object, **_kwargs: object) -> bool:
        return False

    def fake_forbidden_paths(*_args: object, **_kwargs: object) -> tuple[str, ...]:
        return ()

    def fake_revert_forbidden(*_args: object, **_kwargs: object) -> int:
        return 0

    def fake_wait_for_ci(*_args: object, **_kwargs: object) -> tuple[dict[str, str], str | None]:
        return wait_result

    monkeypatch.setattr(ci_monitor, "read_failed_jobs", fake_read_failed_jobs)
    monkeypatch.setattr(ci_monitor, "collect_failed_logs", fake_collect_failed_logs)
    monkeypatch.setattr(ci_monitor, "_capture_baseline", fake_capture_baseline)
    monkeypatch.setattr(ci_monitor, "prepare_python_toolchain", fake_prepare_python_toolchain)
    monkeypatch.setattr(ci_monitor, "verify_job_locally", fake_verify_job_locally)
    monkeypatch.setattr(ci_monitor, "_delta_paths", fake_delta_paths)
    monkeypatch.setattr(ci_monitor, "stage_and_push", fake_stage_and_push)
    monkeypatch.setattr(agents, "launch_tier", fake_launch_tier)
    monkeypatch.setattr(agents, "resolve_launcher_exit", fake_resolve_launcher_exit)
    monkeypatch.setattr(agents, "classify_launch_failure", fake_classify_launch_failure)
    monkeypatch.setattr(ci_agentic_fix.coder_delta_guards, "capture_head", fake_capture_head)
    monkeypatch.setattr(ci_agentic_fix.coder_delta_guards, "head_changed_from_baseline", fake_head_changed)
    monkeypatch.setattr(ci_agentic_fix.coder_delta_guards, "coder_forbidden_paths", fake_forbidden_paths)
    monkeypatch.setattr(ci_agentic_fix.coder_delta_guards, "revert_forbidden_paths", fake_revert_forbidden)
    monkeypatch.setattr(ci_agentic_fix, "_wait_for_ci", fake_wait_for_ci)
    return calls


def _cycle_args(out_dir: Path) -> Namespace:
    return Namespace(
        pr=1,
        repo="o/r",
        plan_file="",
        base_remote="origin",
        base_ref="main",
        output_dir=str(out_dir),
    )


def test_run_cycle_mechanical_fix_skips_delegate_and_pushes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    calls = {"push": 0, "launch": 0}

    monkeypatch.setattr(ci_monitor, "read_failed_jobs", lambda *_a, **_kw: ((ci_monitor.FailedJob(name="python-lint", conclusion="failure"),), "ready"))  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_monitor, "collect_failed_logs", lambda *_a, **_kw: ci_monitor.LogCollectResult(text="known failure\n", state="ready"))  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_monitor, "_capture_baseline", lambda *_a, **_kw: ((), (), (), "abc123"))  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_monitor, "prepare_python_toolchain", lambda *_a, **_kw: True)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_monitor, "verify_job_locally", lambda *_a, **_kw: True)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_monitor, "_delta_paths", lambda *_a, **_kw: ("fixed.py",))  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_agentic_fix, "_apply_known_harness_fix", lambda *_a, **_kw: (True, "known"))  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_agentic_fix.coder_delta_guards, "coder_forbidden_paths", lambda *_a, **_kw: ())  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_agentic_fix.coder_delta_guards, "revert_forbidden_paths", lambda *_a, **_kw: 0)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_agentic_fix, "_wait_for_ci", lambda *_a, **_kw: ({"ACTION": "merge"}, None))  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]

    def fake_launch(*_args: object, **_kwargs: object) -> proc.CommandResult:
        calls["launch"] += 1
        return proc.CommandResult(("cli",), 1, "", "", 0.01)

    def fake_stage_and_push(*_args: object, **_kwargs: object) -> tuple[bool, str | None, tuple[str, ...], bool, bool]:
        calls["push"] += 1
        return True, "head", ("fixed.py",), False, False

    monkeypatch.setattr(agents, "launch_tier", fake_launch)
    monkeypatch.setattr(ci_monitor, "stage_and_push", fake_stage_and_push)

    status, detail, attempted, delta, pending, next_run, _log = ci_agentic_fix._run_cycle(  # pyright: ignore[reportPrivateUsage]
        proc,
        args=_cycle_args(out_dir),
        repo_root=repo,
        ctx=_make_ctx(),
        cycle=1,
        run_id="42",
    )
    assert status == "passed"
    assert detail == ""
    assert attempted is True
    assert delta == ("fixed.py",)
    assert pending is False
    assert next_run is None
    assert calls == {"push": 1, "launch": 0}


def test_run_cycle_mixed_mechanical_failure_rolls_back_then_delegates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    calls = {"rollback": 0, "launch": 0, "verify": 0}

    monkeypatch.setattr(ci_monitor, "read_failed_jobs", lambda *_a, **_kw: ((ci_monitor.FailedJob(name="python-lint", conclusion="failure"),), "ready"))  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_monitor, "collect_failed_logs", lambda *_a, **_kw: ci_monitor.LogCollectResult(text="known failure\n", state="ready"))  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_monitor, "_capture_baseline", lambda *_a, **_kw: ((), (), (), "abc123"))  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_monitor, "prepare_python_toolchain", lambda *_a, **_kw: True)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_monitor, "_delta_paths", lambda *_a, **_kw: ("fixed.py",))  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_agentic_fix, "_apply_known_harness_fix", lambda *_a, **_kw: (True, "known"))  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_agentic_fix.coder_delta_guards, "capture_head", lambda *_a, **_kw: "abc123")  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_agentic_fix.coder_delta_guards, "head_changed_from_baseline", lambda *_a, **_kw: False)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_agentic_fix.coder_delta_guards, "coder_forbidden_paths", lambda *_a, **_kw: ())  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_agentic_fix.coder_delta_guards, "revert_forbidden_paths", lambda *_a, **_kw: 0)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(agents, "resolve_launcher_exit", lambda *_a, **_kw: 0)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(agents, "classify_launch_failure", lambda *_a, **_kw: agents.LaunchFailure("none", ""))  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_agentic_fix, "_wait_for_ci", lambda *_a, **_kw: ({"ACTION": "merge"}, None))  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_agentic_fix, "_rollback", lambda *_a, **_kw: calls.__setitem__("rollback", calls["rollback"] + 1))  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(ci_monitor, "stage_and_push", lambda *_a, **_kw: (True, "head", ("fixed.py",), False, False))  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]

    def fake_verify(*_args: object, **_kwargs: object) -> bool:
        calls["verify"] += 1
        return calls["verify"] > 1

    def fake_launch(*_args: object, **kwargs: object) -> proc.CommandResult:
        calls["launch"] += 1
        _ = Path(str(kwargs["output"])).write_text("fixed\n", encoding="utf-8")
        return proc.CommandResult(("cli",), 0, "LAUNCHER_EXIT=0\n", "", 0.01)

    monkeypatch.setattr(ci_monitor, "verify_job_locally", fake_verify)
    monkeypatch.setattr(agents, "launch_tier", fake_launch)

    status, _detail, attempted, _delta, _pending, _next_run, _log = ci_agentic_fix._run_cycle(  # pyright: ignore[reportPrivateUsage]
        proc,
        args=_cycle_args(out_dir),
        repo_root=repo,
        ctx=_make_ctx(),
        cycle=1,
        run_id="42",
    )
    assert status == "passed"
    assert attempted is True
    assert calls["rollback"] == 1
    assert calls["launch"] == 1


def test_run_cycle_wait_error_fails_closed_without_reusing_run_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    calls = _stub_successful_fix_until_wait(
        monkeypatch,
        wait_result=({}, "ci-wait-malformed-output"),
    )

    status, detail, attempted, delta, pending, next_run, _log = ci_agentic_fix._run_cycle(  # pyright: ignore[reportPrivateUsage]
        proc,
        args=_cycle_args(out_dir),
        repo_root=repo,
        ctx=_make_ctx(),
        cycle=1,
        run_id="42",
    )
    assert status == "ci-fix-exhausted"
    assert detail == "ci-wait-malformed-output"
    assert attempted is True
    assert delta == ("fixed.py",)
    assert pending is False
    assert next_run is None
    assert calls["push"] == 1


def test_run_cycle_wait_untrusted_action_fails_closed_without_reusing_run_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    _ = _stub_successful_fix_until_wait(
        monkeypatch,
        wait_result=({"ACTION": "retry", "CI_STATUS": "fail"}, None),
    )

    status, detail, _attempted, _delta, _pending, next_run, _log = ci_agentic_fix._run_cycle(  # pyright: ignore[reportPrivateUsage]
        proc,
        args=_cycle_args(out_dir),
        repo_root=repo,
        ctx=_make_ctx(),
        cycle=1,
        run_id="42",
    )
    assert status == "ci-fix-exhausted"
    assert detail == "ci-wait-untrusted-output"
    assert next_run is None


def test_run_cycle_wait_action_bail_fails_closed_with_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    _ = _stub_successful_fix_until_wait(
        monkeypatch,
        wait_result=({"ACTION": "bail", "BAIL_REASON": "CI_WAIT_BAIL_POLL_BUDGET_EXHAUSTED"}, None),
    )

    status, detail, _attempted, _delta, _pending, next_run, _log = ci_agentic_fix._run_cycle(  # pyright: ignore[reportPrivateUsage]
        proc,
        args=_cycle_args(out_dir),
        repo_root=repo,
        ctx=_make_ctx(),
        cycle=1,
        run_id="42",
    )
    assert status == "ci-fix-exhausted"
    assert detail == "CI_WAIT_BAIL_POLL_BUDGET_EXHAUSTED"
    assert next_run is None


def test_run_cycle_later_non_health_is_waterfall_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
        return proc.CommandResult(("cli",), 1, "LAUNCHER_EXIT=1\n", "", 0.01)

    def fake_resolve_launcher_exit(*_args: object, **_kwargs: object) -> int:
        return 1

    def fake_classify_launch_failure(*_args: object, **_kwargs: object) -> agents.LaunchFailure:
        return agents.LaunchFailure("other", "parse")

    def fake_rollback(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(ci_monitor, "read_failed_jobs", fake_read_failed_jobs)
    monkeypatch.setattr(ci_monitor, "collect_failed_logs", fake_collect_failed_logs)
    monkeypatch.setattr(ci_monitor, "_capture_baseline", fake_capture_baseline)
    monkeypatch.setattr(agents, "launch_tier", fake_launch_tier)
    monkeypatch.setattr(agents, "resolve_launcher_exit", fake_resolve_launcher_exit)
    monkeypatch.setattr(agents, "classify_launch_failure", fake_classify_launch_failure)
    monkeypatch.setattr(ci_agentic_fix, "_rollback", fake_rollback)

    status, detail, _attempted, _delta, _pending, next_run, _log = ci_agentic_fix._run_cycle(  # pyright: ignore[reportPrivateUsage]
        proc,
        args=_cycle_args(out_dir),
        repo_root=repo,
        ctx=_make_ctx(),
        cycle=2,
        run_id="42",
    )
    assert status == "waterfall-failed"
    assert detail == "parse"
    assert next_run is None


def test_run_cycle_retries_once_on_exit_124(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_run_cycle retries launch_tier once when the first attempt exits 124."""
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    launch_calls: list[int] = []
    resolve_calls: list[int] = []

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
        launch_calls.append(1)
        return proc.CommandResult(("cli",), 0, "", "", 0.01)

    def fake_resolve_launcher_exit(*_args: object, **_kwargs: object) -> int:
        resolve_calls.append(1)
        if len(resolve_calls) == 1:
            return config.EXIT_TIMEOUT
        # Second call (retry): succeed
        return 0

    def fake_classify_launch_failure(*_args: object, **_kwargs: object) -> agents.LaunchFailure:
        return agents.LaunchFailure("none", "")

    def fake_capture_head(*_args: object, **_kwargs: object) -> str:
        return "abc123"

    def fake_head_changed(*_args: object, **_kwargs: object) -> bool:
        return False

    def fake_coder_forbidden_paths(*_args: object, **_kwargs: object) -> tuple[str, ...]:
        return ()

    def fake_revert_forbidden_paths(*_args: object, **_kwargs: object) -> int:
        return 0

    def fake_prepare_python_toolchain(*_args: object, **_kwargs: object) -> bool:
        return True

    def fake_verify_job_locally(*_args: object, **_kwargs: object) -> bool:
        return True

    def fake_delta_paths(*_args: object, **_kwargs: object) -> tuple[str, ...]:
        return ("file.py",)

    def fake_stage_and_push(*_args: object, **_kwargs: object) -> tuple[bool, str, tuple[str, ...], bool, bool]:
        return True, "abc124", ("file.py",), False, False

    def fake_wait_for_ci(*_args: object, **_kwargs: object) -> tuple[dict[str, str], str | None]:
        return {"ACTION": "merge", "CI_STATUS": "pass"}, None

    def fake_write_push_checkpoint(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(ci_monitor, "read_failed_jobs", fake_read_failed_jobs)
    monkeypatch.setattr(ci_monitor, "collect_failed_logs", fake_collect_failed_logs)
    monkeypatch.setattr(ci_monitor, "_capture_baseline", fake_capture_baseline)
    monkeypatch.setattr(agents, "launch_tier", fake_launch_tier)
    monkeypatch.setattr(agents, "resolve_launcher_exit", fake_resolve_launcher_exit)
    monkeypatch.setattr(agents, "classify_launch_failure", fake_classify_launch_failure)
    monkeypatch.setattr(coder_delta_guards, "capture_head", fake_capture_head)
    monkeypatch.setattr(coder_delta_guards, "head_changed_from_baseline", fake_head_changed)
    monkeypatch.setattr(coder_delta_guards, "coder_forbidden_paths", fake_coder_forbidden_paths)
    monkeypatch.setattr(coder_delta_guards, "revert_forbidden_paths", fake_revert_forbidden_paths)
    monkeypatch.setattr(ci_monitor, "prepare_python_toolchain", fake_prepare_python_toolchain)
    monkeypatch.setattr(ci_monitor, "verify_job_locally", fake_verify_job_locally)
    monkeypatch.setattr(ci_monitor, "_delta_paths", fake_delta_paths)
    monkeypatch.setattr(ci_monitor, "stage_and_push", fake_stage_and_push)
    monkeypatch.setattr(ci_agentic_fix, "_wait_for_ci", fake_wait_for_ci)
    monkeypatch.setattr(ci_agentic_fix, "_write_push_checkpoint", fake_write_push_checkpoint)

    args = Namespace(
        pr=1,
        repo="o/r",
        plan_file="",
        base_remote="origin",
        base_ref="main",
        output_dir=str(out_dir),
        implement_tmpdir=str(tmp_path),
    )
    status, _detail, _attempted, _delta, _pending, _next_run, _log = ci_agentic_fix._run_cycle(  # pyright: ignore[reportPrivateUsage]
        proc,
        args=args,
        repo_root=repo,
        ctx=_make_ctx(),
        cycle=1,
        run_id="42",
    )
    assert len(launch_calls) == 2, "should have called launch_tier twice (retry)"
    assert len(resolve_calls) == 2, "should have called resolve_launcher_exit twice"
    assert status == "passed"
    issue_log = tmp_path / "execution-issues.md"
    assert issue_log.is_file()
    issue_text = issue_log.read_text(encoding="utf-8")
    assert "retried once" in issue_text
    assert "rc=124" in issue_text
    assert "exit-124" in issue_text


def _run_cycle_retry_output_case(
    case_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    first_output_state: str,
) -> tuple[str, int, int, str]:
    repo = case_dir / "repo"
    repo.mkdir(parents=True)
    out_dir = case_dir / "out"
    out_dir.mkdir()
    implement_dir = case_dir / "implement"
    implement_dir.mkdir()
    launch_calls: list[int] = []
    resolve_calls: list[int] = []
    _ = _stub_successful_fix_until_wait(
        monkeypatch,
        wait_result=({"ACTION": "merge", "CI_STATUS": "pass"}, None),
    )

    def fake_launch_tier(*_args: object, **kwargs: object) -> proc.CommandResult:
        launch_calls.append(1)
        output = Path(str(kwargs["output"]))
        if len(launch_calls) == 1:
            if first_output_state == "empty":
                _ = output.write_text("", encoding="utf-8")
            return proc.CommandResult(("cli",), 1, "LAUNCHER_EXIT=1\n", "", 0.01)
        _ = output.write_text("fixed\n", encoding="utf-8")
        return proc.CommandResult(("cli",), 0, "LAUNCHER_EXIT=0\n", "", 0.01)

    def fake_resolve_launcher_exit(*_args: object, **_kwargs: object) -> int:
        resolve_calls.append(1)
        return 1 if len(resolve_calls) == 1 else 0

    monkeypatch.setattr(agents, "launch_tier", fake_launch_tier)
    monkeypatch.setattr(agents, "resolve_launcher_exit", fake_resolve_launcher_exit)

    args = _cycle_args(out_dir)
    args.implement_tmpdir = str(implement_dir)
    status, _detail, _attempted, _delta, _pending, _next_run, _log = ci_agentic_fix._run_cycle(  # pyright: ignore[reportPrivateUsage]
        proc,
        args=args,
        repo_root=repo,
        ctx=_make_ctx(),
        cycle=1,
        run_id="42",
    )
    issue_text = (implement_dir / "execution-issues.md").read_text(encoding="utf-8")
    return status, len(launch_calls), len(resolve_calls), issue_text


def test_run_cycle_retries_once_on_missing_or_empty_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for output_state, expected_reason in (
        ("missing", "missing-output"),
        ("empty", "empty-output"),
    ):
        with monkeypatch.context() as case_monkeypatch:
            status, launch_count, resolve_count, issue_text = _run_cycle_retry_output_case(
                tmp_path / output_state,
                case_monkeypatch,
                first_output_state=output_state,
            )
        assert status == "passed"
        assert launch_count == 2
        assert resolve_count == 2
        assert "retried once" in issue_text
        assert "rc=1" in issue_text
        assert expected_reason in issue_text
