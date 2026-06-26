# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnusedCallResult=false
"""CLI contract tests for ci."""

from __future__ import annotations

import pytest
from larch.core.proc import CommandResult
from test_support import RecordingRunner

import ci
import ci_monitor
from larch.core import config


def _res(rc: int = 0, stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(("cmd",), rc, stdout, stderr, 0.01)


def test_behind_count_fail_open(monkeypatch, capsys):
    runner = RecordingRunner(responses=[_res(1, stderr="fetch failed")])
    monkeypatch.setattr(ci, "proc", runner)
    assert ci.behind_count_main([]) == 0
    assert "BEHIND_COUNT=0" in capsys.readouterr().out


def test_behind_count_fail_open_on_rev_list_timeout(monkeypatch, capsys):
    runner = RecordingRunner(responses=[_res(config.EXIT_TIMEOUT)])
    monkeypatch.setattr(ci, "proc", runner)
    assert ci.behind_count_main(["--no-fetch"]) == 0
    assert "BEHIND_COUNT=0" in capsys.readouterr().out


def test_decide_usage_exit_one():
    assert ci.decide_main([]) == 1


def test_decide_rejects_invalid_status():
    assert (
        ci.decide_main(
            [
                "--status",
                "bogus",
                "--behind",
                "0",
                "--iteration",
                "0",
                "--rebase-count",
                "0",
                "--fix-attempts",
                "0",
            ],
        )
        == 1
    )


def test_decide_rejects_negative_counter():
    assert (
        ci.decide_main(
            [
                "--status",
                "pass",
                "--behind",
                "-1",
                "--iteration",
                "0",
                "--rebase-count",
                "0",
                "--fix-attempts",
                "0",
            ],
        )
        == 1
    )


def test_decide_rejects_malformed_conflicted():
    assert (
        ci.decide_main(
            [
                "--status",
                "pass",
                "--behind",
                "0",
                "--conflicted",
                "maybe",
                "--iteration",
                "0",
                "--rebase-count",
                "0",
                "--fix-attempts",
                "0",
            ],
        )
        == 1
    )


def test_decide_accepts_legacy_flags(capsys):
    assert (
        ci.decide_main(
            [
                "--status",
                "pass",
                "--behind",
                "0",
                "--iteration",
                "0",
                "--rebase-count",
                "0",
                "--fix-attempts",
                "0",
            ],
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "ACTION=merge" in out


def test_status_usage_emits_error_kv_and_exits_zero(capsys):
    assert ci.status_main([]) == 0
    out = capsys.readouterr().out
    assert "CI_STATUS=error" in out
    assert "BEHIND_COUNT=0" in out


def test_status_rejects_invalid_base_ref(capsys):
    assert ci.status_main(["--pr", "1", "--repo", "o/r", "--base-ref", "bad ref"]) == 0
    captured = capsys.readouterr()
    assert "unsupported characters" in captured.err
    assert "CI_STATUS=error" in captured.out


def test_wait_rejects_negative_counter_before_output_file_cleanup(tmp_path, capsys):
    out_file = tmp_path / "wait.out"
    out_file.write_text("stale\n", encoding="utf-8")
    assert (
        ci.wait_main(
            ["--pr", "1", "--repo", "o/r", "--iteration", "-1", "--output-file", str(out_file)],
        )
        == 1
    )
    assert "non-negative integer" in capsys.readouterr().err
    assert out_file.read_text(encoding="utf-8") == "stale\n"


def test_failed_jobs_usage_exits_two():
    assert ci.failed_jobs_main([]) == 2


def test_failed_jobs_classifies_legacy_fixable_jobs() -> None:
    classified = ci_monitor.classify_failed_jobs(
        (
            ci_monitor.FailedJob(name="lint-local", conclusion="failure"),
            ci_monitor.FailedJob(name="bash32-check", conclusion="failure"),
        ),
    )
    assert [job.name for job in classified.fixable] == ["lint-local", "bash32-check"]


def test_wait_bail_exits_zero_and_emits_contract(monkeypatch, capsys):
    status = ci_monitor.CiStatus(
        status="fail",
        behind_count=0,
        failed_run_id="99",
        conflicted=False,
    )
    decision = ci_monitor.Decision(action="bail", bail_reason="too many fixes")
    monkeypatch.setattr(
        ci.ci_monitor,
        "poll_ci",
        lambda *_a, **_k: (status, decision),
    )
    assert (
        ci.wait_main(
            [
                "--pr",
                "1",
                "--repo",
                "o/r",
                "--iteration",
                "3",
            ],
        )
        == 0
    )
    lines = [line for line in capsys.readouterr().out.splitlines() if line]
    assert lines[0] == "ACTION=bail"
    assert lines[1] == "CI_STATUS=fail"
    assert "ITERATION=3" in lines
    assert "ELAPSED=" in lines[-1]


def test_wait_output_file_publishes_on_poll_exception(monkeypatch, tmp_path):
    def _boom(*_args: object, **_kwargs: object) -> tuple[object, object]:
        raise RuntimeError("poll failed")

    monkeypatch.setattr(ci.ci_monitor, "poll_ci", _boom)
    out_file = tmp_path / "wait.out"
    assert ci.wait_main(["--pr", "1", "--repo", "o/r", "--output-file", str(out_file)]) == 0
    text = out_file.read_text(encoding="utf-8")
    assert "ACTION=bail" in text
    assert config.CI_WAIT_BAIL_UNEXPECTED_EXIT in text
    done = tmp_path / "wait.out.done"
    assert done.read_text(encoding="utf-8").strip() == "1"


def test_wait_output_file_writes_done_sentinel(monkeypatch, tmp_path):
    status = ci_monitor.CiStatus(
        status="pass",
        behind_count=0,
        failed_run_id=None,
        conflicted=False,
    )
    decision = ci_monitor.Decision(action="merge", bail_reason="")
    monkeypatch.setattr(
        ci.ci_monitor,
        "poll_ci",
        lambda *_a, **_k: (status, decision),
    )
    out_file = tmp_path / "wait.out"
    assert ci.wait_main(["--pr", "1", "--repo", "o/r", "--output-file", str(out_file)]) == 0
    assert out_file.is_file()
    done = tmp_path / "wait.out.done"
    assert done.is_file()
    assert done.read_text(encoding="utf-8").strip() == "0"
    assert out_file.read_text(encoding="utf-8").splitlines()[0] == "ACTION=merge"


def test_wait_default_empty_checks_grace_is_bounded(monkeypatch):
    captured: dict[str, object] = {}

    def fake_poll(*_args: object, **kwargs: object) -> tuple[object, object]:
        captured["grace"] = kwargs["empty_checks_grace"]
        return (
            ci_monitor.CiStatus(status="pass", behind_count=0, failed_run_id=None, conflicted=False),
            ci_monitor.Decision(action="merge", bail_reason=""),
        )

    monkeypatch.setattr(ci.ci_monitor, "poll_ci", fake_poll)
    # No --empty-checks-grace: the bounded config default must flow through, so a
    # manual `ci wait` on a runless head does not poll the full timeout (issue #4924).
    assert ci.wait_main(["--pr", "1", "--repo", "o/r"]) == 0
    assert captured["grace"] == config.CI_WAIT_EMPTY_CHECKS_GRACE_SEC
    assert captured["grace"] == 120


def test_status_default_empty_checks_grace_is_bounded(monkeypatch):
    captured: dict[str, object] = {}

    def fake_gather(*_args: object, **kwargs: object) -> object:
        captured["grace"] = kwargs["empty_checks_grace"]
        return ci_monitor.CiStatus(status="pass", behind_count=0, failed_run_id=None, conflicted=False)

    monkeypatch.setattr(ci.ci_monitor, "gather_status", fake_gather)
    assert ci.status_main(["--pr", "1", "--repo", "o/r"]) == 0
    assert captured["grace"] == 120


def test_agentic_fix_usage_exits_nonzero(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        ci.agentic_fix_main([])
    assert exc.value.code == 2
    assert "required" in capsys.readouterr().err.lower()


def test_agentic_fix_rejects_relative_repo_root(capsys, tmp_path) -> None:
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    rc = ci.agentic_fix_main([
        "--pr", "1",
        "--repo", "o/r",
        "--repo-root", "relative",
        "--run-id", "42",
        "--output-dir", str(out_dir),
        "--implement-tmpdir", str(tmp_path),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=waterfall-failed" in out
    assert "DETAIL=missing-repo-root" in out


def test_agentic_fix_accepts_optional_flags(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    def fake_run_cycle(*_args: object, **_kwargs: object) -> tuple[str, str, bool, tuple[str, ...], bool, str | None, str]:
        return "passed", "", False, (), False, None, ""

    monkeypatch.setattr(ci.ci_agentic_fix, "_run_cycle", fake_run_cycle)
    rc = ci.agentic_fix_main([
        "--pr", "1",
        "--repo", "o/r",
        "--repo-root", str(repo),
        "--run-id", "42",
        "--output-dir", str(out_dir),
        "--implement-tmpdir", str(tmp_path),
        "--plan-file", str(tmp_path / "plan.md"),
        "--base-remote", "upstream",
        "--base-ref", "develop",
        "--max-cycles", "2",
        "--state-file", str(tmp_path / "state.sh"),
        "--no-logs-commit",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=passed" in out
    assert "CYCLES=1" in out
