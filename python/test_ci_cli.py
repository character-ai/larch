# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnusedCallResult=false
"""CLI contract tests for ci_cli."""

from __future__ import annotations

from proc import CommandResult
from test_support import RecordingRunner

import ci_cli
import ci_monitor


def _res(rc: int = 0, stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(("cmd",), rc, stdout, stderr, 0.01)


def test_behind_count_fail_open(monkeypatch, capsys):
    runner = RecordingRunner(responses=[_res(1, stderr="fetch failed")])
    monkeypatch.setattr(ci_cli, "proc", runner)
    assert ci_cli.behind_count_main([]) == 0
    assert "BEHIND_COUNT=0" in capsys.readouterr().out


def test_decide_usage_exit_one():
    assert ci_cli.decide_main([]) == 1


def test_decide_rejects_invalid_status():
    assert (
        ci_cli.decide_main(
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
        ci_cli.decide_main(
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
        ci_cli.decide_main(
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
        ci_cli.decide_main(
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
    assert ci_cli.status_main([]) == 0
    out = capsys.readouterr().out
    assert "CI_STATUS=error" in out
    assert "BEHIND_COUNT=0" in out


def test_wait_bail_exits_zero_and_emits_contract(monkeypatch, capsys):
    status = ci_monitor.CiStatus(
        status="fail",
        behind_count=0,
        failed_run_id="99",
        conflicted=False,
    )
    decision = ci_monitor.Decision(action="bail", bail_reason="too many fixes")
    monkeypatch.setattr(
        ci_cli.ci_monitor,
        "poll_ci",
        lambda *_a, **_k: (status, decision),
    )
    assert (
        ci_cli.wait_main(
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


def test_wait_output_file_writes_done_sentinel(monkeypatch, tmp_path):
    status = ci_monitor.CiStatus(
        status="pass",
        behind_count=0,
        failed_run_id=None,
        conflicted=False,
    )
    decision = ci_monitor.Decision(action="merge", bail_reason="")
    monkeypatch.setattr(
        ci_cli.ci_monitor,
        "poll_ci",
        lambda *_a, **_k: (status, decision),
    )
    out_file = tmp_path / "wait.out"
    assert ci_cli.wait_main(["--pr", "1", "--repo", "o/r", "--output-file", str(out_file)]) == 0
    assert out_file.is_file()
    done = tmp_path / "wait.out.done"
    assert done.is_file()
    assert done.read_text(encoding="utf-8").strip() == "0"
    assert out_file.read_text(encoding="utf-8").splitlines()[0] == "ACTION=merge"
