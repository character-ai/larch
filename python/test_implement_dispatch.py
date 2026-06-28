# pyright: reportPrivateUsage=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

import errno
import fcntl
import inspect
import json
import shlex
import signal
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from larch.cli import _REGISTRY

from larch.agents import agents
from larch.agents import _ci_launcher
from larch.agents import _run_external
from larch.report import exec_issue_detail
from larch.implement import implement_dispatch
from larch.implement import (
    dispatch_commit_route,
    dispatch_leg,
    dispatch_ship,
    dispatch_step18,
    dispatch_step2,
    dispatch_recovery,
)
from larch.core import logging_util
from larch.report import run_logs
from larch.core.proc import CommandResult


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True, check=False)


@pytest.fixture(autouse=True)
def quiet_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    logging_util.reset_quiet_state()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-b", "feature"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
    (root / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    monkeypatch.chdir(root)
    return root


def _session(tmp_path: Path) -> Path:
    tmp = tmp_path / "impl"
    tmp.mkdir()
    (tmp / "plan.txt").write_text("## Plan\n", encoding="utf-8")
    (tmp / "feature-description.txt").write_text("feature\n", encoding="utf-8")
    plugin_root = Path(__file__).resolve().parents[1]
    (tmp / "session-env.sh").write_text(
        f"CURSOR_PRESENT=false\nCODEX_BINARY_FOUND=true\nCURSOR_BINARY_FOUND=true\nLARCH_CLAUDE_PLUGIN_ROOT={plugin_root}\n",
        encoding="utf-8",
    )
    return tmp


def _mock_disposition_checkpoint_only(monkeypatch: pytest.MonkeyPatch, *, stdout: str = "", rc: int = 0) -> None:
    original = subprocess.run

    def selective_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        cmd = cast("Sequence[str]", args[0] if args else kwargs.get("args", []))
        if any("disposition-checkpoint" in str(part) for part in cmd):
            return subprocess.CompletedProcess(["checkpoint"], rc, stdout, "")
        return original(*args, **kwargs)  # pylint: disable=subprocess-run-check

    monkeypatch.setattr(subprocess, "run", selective_run)


def test_cli_registry_has_implement_and_launcher_verbs() -> None:
    assert _REGISTRY[("implement", "step2-dispatch")] == ("larch.implement.implement_dispatch", "step2_dispatch_main")
    assert _REGISTRY[("implement", "run-dispatch")] == ("larch.implement.implement_dispatch", "run_dispatch_main")
    assert _REGISTRY[("implement", "recovery-paths")] == ("larch.implement.implement_dispatch", "recovery_paths_main")
    assert _REGISTRY[("implement", "commit")] == ("larch.implement.implement_dispatch", "commit_main")
    assert _REGISTRY[("implement", "commit-route")] == ("larch.implement.implement_dispatch", "commit_route_main")
    assert _REGISTRY[("implement", "checks-commit-route")] == ("larch.implement.implement_dispatch", "checks_commit_route_main")
    assert _REGISTRY[("implement", "checks-step5-resume")] == ("larch.implement.implement_dispatch", "checks_step5_resume_main")
    assert _REGISTRY[("implement", "clone-tag")] == ("larch.implement.implement_dispatch", "clone_tag_main")
    assert _REGISTRY[("implement", "normalize-coder-scout")] == ("larch.implement.implement_dispatch", "normalize_coder_scout_main")
    assert _REGISTRY[("implement", "step-5-review")] == ("larch.implement.implement_dispatch", "step5_review_main")
    assert _REGISTRY[("implement", "step-6-entry")] == ("larch.implement.implement_dispatch", "step6_entry_main")
    assert _REGISTRY[("implement", "step-8-ship")] == ("larch.implement.implement_dispatch", "step8_ship_main")
    assert _REGISTRY[("implement", "step-18-gate-finalize")] == ("larch.implement.implement_dispatch", "step_18_gate_finalize_main")
    assert _REGISTRY[("implement", "run-step-checks")] == ("larch.implement.implement_dispatch", "run_step_checks_main")
    assert _REGISTRY[("ship", "pre-driver")] == ("larch.implement.implement_dispatch", "ship_pre_driver_main")
    assert _REGISTRY[("ship", "route-exit")] == ("larch.implement.implement_dispatch", "ship_route_exit_main")
    assert _REGISTRY[("execution-issues", "flush-safety-net")] == ("larch.issue.execution_issues", "flush_execution_issues_safety_net_main")
    assert _REGISTRY[("agent", "launch-codex-implement")] == ("larch.agents.agents", "launch_codex_implement_main")
    assert _REGISTRY[("agent", "launch-cursor-implement")] == ("larch.agents.agents", "launch_cursor_implement_main")


def _write_ship_handoff(tmp: Path, rc: int, payload: dict[str, object]) -> None:
    (tmp / ".step-8-ship-handoff.rc").write_text(f"{rc}\n", encoding="utf-8")
    (tmp / ".step-8-ship-handoff.json").write_text(json.dumps(payload), encoding="utf-8")


def _route_exit(
    tmp: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    rc: int,
    payload: dict[str, object],
) -> tuple[int, str, str]:
    _write_ship_handoff(tmp, rc, payload)
    monkeypatch.setattr(implement_dispatch.time, "sleep", lambda _seconds: None)
    exit_rc = implement_dispatch.ship_route_exit_main(["--implement-tmpdir", str(tmp)])
    captured = capsys.readouterr()
    return exit_rc, captured.out, captured.err


@pytest.mark.parametrize(
    ("rc", "payload", "action"),
    [
        (0, {"outcome": "OK"}, "complete"),
        (0, {"outcome": "NEEDS_USER_INPUT"}, "reship"),
        (3, {"outcome": "NEEDS_USER_INPUT", "needs_user_reason": "oos-filing"}, "oos-pipeline"),
        (3, {"outcome": "NEEDS_USER_INPUT", "needs_user_reason": "first-fixer-non-health"}, "ci-fix"),
        (3, {"outcome": "NEEDS_USER_INPUT", "needs_user_reason": "ship-pr-internal-lint-fix"}, "ci-fix"),
        (3, {"outcome": "NEEDS_USER_INPUT", "needs_user_reason": "ci-local-unfixable:lint"}, "ci-fix"),
        (3, {"outcome": "NEEDS_USER_INPUT", "needs_user_reason": "local-unfixable"}, "ci-fix"),
        (3, {"outcome": "NEEDS_USER_INPUT", "needs_user_reason": "ci-fix-exhausted"}, "operator-bail"),
        (3, {"outcome": "NEEDS_USER_INPUT", "needs_user_reason": "unknown"}, "operator-bail"),
        (1, {"outcome": "INTERNAL_ERROR"}, "tool-failure"),
        (4, {"outcome": "STALLED"}, "stall"),
    ],
)
def test_ship_route_exit_classifies_driver_sidecars(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    rc: int,
    payload: dict[str, object],
    action: str,
) -> None:
    tmp = _session(tmp_path)

    exit_rc, out, _err = _route_exit(tmp, capsys, monkeypatch, rc, payload)

    assert exit_rc == 0
    assert out == f"NEXT_ACTION={action}\n"
    assert f"NEXT_ACTION={action}\n" in (tmp / ".ship-route-exit-handoff.env").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("rc", "payload"),
    [
        (3, {"outcome": "NEEDS_USER_INPUT"}),
        (1, {"outcome": "STALLED"}),
        (4, {}),
        (0, {}),
    ],
)
def test_ship_route_exit_fails_closed_without_required_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    rc: int,
    payload: dict[str, object],
) -> None:
    tmp = _session(tmp_path)

    exit_rc, out, _err = _route_exit(tmp, capsys, monkeypatch, rc, payload)

    assert exit_rc != 0
    assert "NEXT_ACTION=" not in out
    assert not (tmp / ".ship-route-exit-handoff.env").exists()


def test_ship_route_exit_retries_transient_and_persists_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    sleeps: list[int] = []
    monkeypatch.setattr(implement_dispatch.time, "sleep", lambda seconds: sleeps.append(int(seconds)))

    _write_ship_handoff(tmp, 6, {"outcome": "TRANSIENT"})
    assert implement_dispatch.ship_route_exit_main(["--implement-tmpdir", str(tmp)]) == 0
    first = capsys.readouterr().out
    _write_ship_handoff(tmp, 6, {"outcome": "TRANSIENT"})
    assert implement_dispatch.ship_route_exit_main(["--implement-tmpdir", str(tmp)]) == 0
    second = capsys.readouterr().out

    assert first == "NEXT_ACTION=reship\n"
    assert second == "NEXT_ACTION=reship\n"
    assert sleeps == [30, 30]
    assert (tmp / "ship-pr-net-retries-python.count").read_text(encoding="utf-8").strip() == "2"
    assert "RESHIP_DELAY_SECONDS=30" in (tmp / ".ship-route-exit-handoff.env").read_text(encoding="utf-8")


def test_ship_route_exit_fourth_transient_seeds_stall(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    (tmp / "ship-pr-net-retries-python.count").write_text("3\n", encoding="utf-8")
    calls: list[list[str]] = []
    monkeypatch.setattr(implement_dispatch.time, "sleep", lambda _seconds: None)

    def fake_capture(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(implement_dispatch, "_run_cli_capture", fake_capture)
    monkeypatch.setattr(dispatch_ship, "_run_cli_capture", fake_capture)
    _write_ship_handoff(tmp, 6, {"outcome": "TRANSIENT"})

    assert implement_dispatch.ship_route_exit_main(["--implement-tmpdir", str(tmp)]) == 0
    assert capsys.readouterr().out == "NEXT_ACTION=stall\n"
    assert calls == [[
        "stall-recovery",
        "seed-terminal-state",
        "--implement-tmpdir",
        str(tmp),
        "--stall-step",
        "transient-retry-cap",
        "--phase",
        "ci-initial",
    ]]


def test_ship_route_exit_rc_file_wins_and_multiline_detail_uses_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    payload: dict[str, object] = {"outcome": "STALLED", "detail": "line one\nline two", "ledger_ready": True}
    _write_ship_handoff(tmp, 4, payload)
    monkeypatch.setattr(implement_dispatch.time, "sleep", lambda _seconds: None)

    assert implement_dispatch.ship_route_exit_main([
        "--implement-tmpdir",
        str(tmp),
        "--exit-code",
        "0",
    ]) == 0

    assert capsys.readouterr().out == "NEXT_ACTION=stall\n"
    env = (tmp / ".ship-route-exit-handoff.env").read_text(encoding="utf-8")
    assert "DETAIL_FILE=" in env
    assert "DETAIL=line one" not in env
    assert "ledger_ready=true" in env


def test_step8_oos_checkpoint_success_writes_stats_stamp_and_clears_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp))
    (tmp / "ship-pr-state.sh").write_text(
        "PHASE=ci-initial\nRUN_ID=state-run\nPR_NUMBER=12\nRESUME_PHASE=ship-pr-rrr-phase14\nOOS_PENDING=true\n",
        encoding="utf-8",
    )
    run_dir = tmp / "larch-logs" / "implement" / "state-run"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text('{"steps_ran":{}}\n', encoding="utf-8")
    (run_dir / "oos-issues.ndjson").write_text(
        json.dumps({"body": "Filed URL: https://github.com/owner/repo/issues/1"}) + "\n",
        encoding="utf-8",
    )
    _mock_disposition_checkpoint_only(monkeypatch, stdout="child stdout\n")

    assert implement_dispatch.step8_oos_checkpoint_main([]) == 0

    captured = capsys.readouterr()
    assert captured.out == "OOS_CHECKPOINT_RC=0\nNEXT_ACTION=reship\n"
    assert "child stdout" not in captured.out
    assert (run_dir / "run-statistics.md").read_text(encoding="utf-8") == "Run state-run: 1 OOS issue(s) filed.\n"
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["steps_ran"]["step9a1"] is True
    state = (tmp / "ship-pr-state.sh").read_text(encoding="utf-8")
    assert "OOS_PENDING=false\n" in state
    assert "PR_NUMBER=12\n" in state
    assert "RESUME_PHASE=ship-pr-rrr-phase14\n" in state


def test_step8_oos_checkpoint_success_refreshes_execution_issues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp))
    (tmp / "ship-pr-state.sh").write_text("RUN_ID=run\nOOS_PENDING=true\n", encoding="utf-8")
    run_dir = tmp / "larch-logs" / "implement" / "run"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text('{"steps_ran":{}}\n', encoding="utf-8")
    _mock_disposition_checkpoint_only(monkeypatch)
    calls: list[tuple[Path, bool]] = []

    def fake_refresh(implement_tmpdir: Path, *, best_effort: bool = False) -> tuple[int, bool, str]:
        calls.append((implement_tmpdir, best_effort))
        return 0, True, ""

    monkeypatch.setattr(implement_dispatch.execution_issues, "refresh_execution_issues", fake_refresh)

    assert implement_dispatch.step8_oos_checkpoint_main([]) == 0

    assert capsys.readouterr().out == "OOS_CHECKPOINT_RC=0\nNEXT_ACTION=reship\n"
    assert calls == [(tmp, True)]


def test_step8_oos_checkpoint_refresh_failure_still_reships(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp))
    (tmp / "ship-pr-state.sh").write_text("RUN_ID=run\nOOS_PENDING=true\n", encoding="utf-8")
    run_dir = tmp / "larch-logs" / "implement" / "run"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text('{"steps_ran":{}}\n', encoding="utf-8")
    _mock_disposition_checkpoint_only(monkeypatch)

    def fake_refresh(_implement_tmpdir: Path, *, best_effort: bool = False) -> tuple[int, bool, str]:
        _ = best_effort
        raise RuntimeError("refresh failed")

    monkeypatch.setattr(implement_dispatch.execution_issues, "refresh_execution_issues", fake_refresh)

    assert implement_dispatch.step8_oos_checkpoint_main([]) == 0

    assert capsys.readouterr().out == "OOS_CHECKPOINT_RC=0\nNEXT_ACTION=reship\n"


def test_step8_oos_checkpoint_stall_does_not_refresh(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp))
    monkeypatch.setattr(
        implement_dispatch.subprocess,
        "run",
        lambda *_a, **_k: subprocess.CompletedProcess(["checkpoint"], 1, "", ""),
    )
    calls: list[Path] = []
    monkeypatch.setattr(
        implement_dispatch.execution_issues,
        "refresh_execution_issues",
        lambda implement_tmpdir, **_kwargs: calls.append(implement_tmpdir),
    )

    assert implement_dispatch.step8_oos_checkpoint_main([]) == 0

    assert capsys.readouterr().out == "OOS_CHECKPOINT_RC=1\nNEXT_ACTION=stall\n"
    assert not calls


def test_step8_oos_checkpoint_bookkeeping_failure_stalls_and_preserves_oos_pending(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp))
    (tmp / "ship-pr-state.sh").write_text("RUN_ID=run\nOOS_PENDING=true\n", encoding="utf-8")
    (tmp / "larch-logs" / "implement" / "run").mkdir(parents=True)
    stamps: list[bool] = []
    monkeypatch.setattr(
        implement_dispatch.subprocess,
        "run",
        lambda *_a, **_k: subprocess.CompletedProcess(["checkpoint"], 0, "", ""),
    )

    def fake_stamp(_tmp: Path, _run_id: str, *, value: bool) -> bool:
        stamps.append(value)
        if value:
            raise RuntimeError("stamp failed")
        return True

    monkeypatch.setattr(implement_dispatch.oos_filer, "_stamp_manifest", fake_stamp)

    assert implement_dispatch.step8_oos_checkpoint_main([]) == 0

    assert capsys.readouterr().out == "OOS_CHECKPOINT_RC=2\nNEXT_ACTION=stall\n"
    assert stamps == [True, False]
    assert "OOS_PENDING=true\n" in (tmp / "ship-pr-state.sh").read_text(encoding="utf-8")
    assert not (tmp / "larch-logs" / "implement" / "run" / "run-statistics.md").is_file()


def test_step8_oos_checkpoint_run_id_precedence_state_over_session_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp))
    (tmp / "session-id").write_text("session-run\n", encoding="utf-8")
    (tmp / "ship-pr-state.sh").write_text("RUN_ID=state-run\nOOS_PENDING=true\n", encoding="utf-8")
    state_run_dir = tmp / "larch-logs" / "implement" / "state-run"
    state_run_dir.mkdir(parents=True)
    (state_run_dir / "manifest.json").write_text('{"steps_ran":{}}\n', encoding="utf-8")
    (state_run_dir / "oos-issues.ndjson").write_text(
        json.dumps({"body": "Filed URL: https://github.com/owner/repo/issues/1"}) + "\n",
        encoding="utf-8",
    )
    session_run_dir = tmp / "larch-logs" / "implement" / "session-run"
    session_run_dir.mkdir(parents=True)
    (session_run_dir / "oos-issues.ndjson").write_text(
        json.dumps({"body": "Filed URL: https://github.com/owner/repo/issues/99"}) + "\n",
        encoding="utf-8",
    )
    _mock_disposition_checkpoint_only(monkeypatch)

    assert implement_dispatch.step8_oos_checkpoint_main([]) == 0

    assert capsys.readouterr().out == "OOS_CHECKPOINT_RC=0\nNEXT_ACTION=reship\n"
    assert (state_run_dir / "run-statistics.md").read_text(encoding="utf-8") == "Run state-run: 1 OOS issue(s) filed.\n"
    assert not (session_run_dir / "run-statistics.md").is_file()


def test_step8_oos_checkpoint_stats_write_failure_stalls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp))
    (tmp / "ship-pr-state.sh").write_text("RUN_ID=run\nOOS_PENDING=true\n", encoding="utf-8")
    (tmp / "larch-logs" / "implement" / "run").mkdir(parents=True)
    (tmp / "larch-logs" / "implement" / "run" / "manifest.json").write_text('{"steps_ran":{}}\n', encoding="utf-8")
    _mock_disposition_checkpoint_only(monkeypatch)
    monkeypatch.setattr(
        implement_dispatch.oos_filer,
        "_write_run_statistics",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("stats write failed")),
    )

    assert implement_dispatch.step8_oos_checkpoint_main([]) == 0

    assert capsys.readouterr().out == "OOS_CHECKPOINT_RC=2\nNEXT_ACTION=stall\n"
    assert "OOS_PENDING=true\n" in (tmp / "ship-pr-state.sh").read_text(encoding="utf-8")
    assert not (tmp / "larch-logs" / "implement" / "run" / "run-statistics.md").is_file()


def test_step8_oos_checkpoint_state_patch_failure_stalls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp))
    (tmp / "ship-pr-state.sh").write_text("RUN_ID=run\nOOS_PENDING=true\n", encoding="utf-8")
    run_dir = tmp / "larch-logs" / "implement" / "run"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text('{"steps_ran":{}}\n', encoding="utf-8")
    _mock_disposition_checkpoint_only(monkeypatch)
    monkeypatch.setattr(
        implement_dispatch.ship,
        "_patch_ship_state_keys",
        lambda **_k: (_ for _ in ()).throw(RuntimeError("state patch failed")),
    )

    assert implement_dispatch.step8_oos_checkpoint_main([]) == 0

    assert capsys.readouterr().out == "OOS_CHECKPOINT_RC=2\nNEXT_ACTION=stall\n"
    assert "OOS_PENDING=true\n" in (tmp / "ship-pr-state.sh").read_text(encoding="utf-8")
    assert not (run_dir / "run-statistics.md").is_file()


def test_step8_oos_checkpoint_bookkeeping_resolves_run_id_from_session_id_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp))
    (tmp / "session-id").write_text("session-run\n", encoding="utf-8")
    (tmp / "ship-pr-state.sh").write_text("OOS_PENDING=true\nPR_NUMBER=3\n", encoding="utf-8")
    run_dir = tmp / "larch-logs" / "implement" / "session-run"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text('{"steps_ran":{}}\n', encoding="utf-8")
    _mock_disposition_checkpoint_only(monkeypatch)

    assert implement_dispatch.step8_oos_checkpoint_main([]) == 0

    assert capsys.readouterr().out == "OOS_CHECKPOINT_RC=0\nNEXT_ACTION=reship\n"
    assert (run_dir / "run-statistics.md").read_text(encoding="utf-8") == "Run session-run: 0 OOS issue(s) filed.\n"
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["steps_ran"]["step9a1"] is True
    assert "OOS_PENDING=false\n" in (tmp / "ship-pr-state.sh").read_text(encoding="utf-8")


def test_step8_oos_checkpoint_resolves_run_id_from_single_ndjson_without_state_run_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp))
    (tmp / "ship-pr-state.sh").write_text("OOS_PENDING=true\nPR_NUMBER=3\n", encoding="utf-8")
    run_dir = tmp / "larch-logs" / "implement" / "ndjson-run"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text('{"steps_ran":{}}\n', encoding="utf-8")
    (run_dir / "oos-issues.ndjson").write_text(
        json.dumps({"body": "Filed URL: https://github.com/owner/repo/issues/2"}) + "\n",
        encoding="utf-8",
    )
    _mock_disposition_checkpoint_only(monkeypatch)

    assert implement_dispatch.step8_oos_checkpoint_main([]) == 0

    assert capsys.readouterr().out == "OOS_CHECKPOINT_RC=0\nNEXT_ACTION=reship\n"
    assert (run_dir / "run-statistics.md").read_text(encoding="utf-8") == "Run ndjson-run: 1 OOS issue(s) filed.\n"
    assert "OOS_PENDING=false\n" in (tmp / "ship-pr-state.sh").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("value", "active"),
    [("", False), ("false", False), ("true", True), ("1", True), ("maybe", True)],
)
def test_step18_stall_layer_active_matches_shell(value: str, active: bool) -> None:
    assert implement_dispatch._stall_layer_active(value) is active


@pytest.mark.parametrize(
    ("arg", "env_value", "expected"),
    [
        ("", "", "false"),
        ("", "true", "true"),
        ("true", "false", "true"),
        ("false", "true", "false"),
        ("1", "false", "1"),
        ("maybe", "true", "maybe"),
    ],
)
def test_step18_resolve_stall_memory_layer(arg: str, env_value: str, expected: str) -> None:
    assert implement_dispatch._resolve_stall_memory_layer(stall_tracking_memory_arg=arg, env_stall_tracking=env_value) == expected


def _install_step18_normalize(
    monkeypatch: pytest.MonkeyPatch,
    *,
    succeeded: bool,
    calls: list[list[str]] | None = None,
) -> None:
    def fake_capture(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if calls is not None:
            calls.append(list(args))
        return subprocess.CompletedProcess(
            list(args),
            0,
            f"IMPLEMENT_OUTCOME_SUCCEEDED={'true' if succeeded else 'false'}\n",
            "",
        )

    monkeypatch.setattr(implement_dispatch, "_run_cli_capture", fake_capture)
    monkeypatch.setattr(dispatch_step18, "_run_cli_capture", fake_capture)


def _install_step18_finalize(
    monkeypatch: pytest.MonkeyPatch,
    *,
    calls: list[list[str]],
    rc: int = 0,
    stdout: str = "EMIT_BODY=false\n",
) -> None:
    def fake_run(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(args))
        return subprocess.CompletedProcess(list(args), rc, stdout, "finalize stderr\n" if rc else "")

    monkeypatch.setattr(implement_dispatch.subprocess, "run", fake_run)


def test_step18_gate_finalize_no_stall_runs_finalize_and_forwards_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("STALL_TRACKING", "false")
    normalize_calls: list[list[str]] = []
    finalize_calls: list[list[str]] = []
    _install_step18_normalize(monkeypatch, succeeded=False, calls=normalize_calls)
    _install_step18_finalize(monkeypatch, calls=finalize_calls, stdout="---LARCH-SUMMARY-FINAL-BEGIN---\nbody\n---LARCH-SUMMARY-FINAL-END---\n")

    assert implement_dispatch.step_18_gate_finalize_main([
        "--implement-tmpdir",
        str(tmp),
        "--stall-tracking-memory",
        "",
        "--step17-emitted",
        "true",
    ]) == 0

    captured = capsys.readouterr()
    assert "STALL_TRACKING_MEMORY=false\n" in captured.out
    assert "STALL_RECOVERY_REQUIRED=false\n" in captured.out
    assert "⏩ 18a: stall recovery — no stall detected\n" in captured.out
    assert "IMPLEMENT_OUTCOME_SUCCEEDED=false\n" in captured.out
    assert "---LARCH-SUMMARY-FINAL-BEGIN---\nbody\n---LARCH-SUMMARY-FINAL-END---\n" in captured.out
    assert captured.out.rstrip().endswith("NEXT_ACTION=finalize-done")
    assert normalize_calls == [[
        "stall-recovery",
        "normalize-outcome",
        "--implement-tmpdir",
        str(tmp),
        "--in-memory-stall-tracking",
        "false",
    ]]
    assert Path(finalize_calls[0][0]).name == "bash"
    assert finalize_calls[0][1:] == [
        str(tmp / "larch-run.sh"),
        "skills/implement/scripts/step-18.sh",
        "--phase",
        "finalize",
        "--step17-emitted",
        "true",
    ]


def test_step18_gate_finalize_active_stall_breaks_out_without_finalize(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    (tmp / "ship-pr-state.sh").write_text("STALL_TRACKING=1\n", encoding="utf-8")
    monkeypatch.setattr(
        implement_dispatch,
        "_run_cli_capture",
        lambda *_a, **_k: pytest.fail("normalize-outcome should not run for active stall"),
    )
    monkeypatch.setattr(dispatch_step18, "_run_cli_capture", lambda *_a, **_k: pytest.fail("normalize-outcome should not run for active stall"))
    monkeypatch.setattr(
        implement_dispatch.subprocess,
        "run",
        lambda *_a, **_k: pytest.fail("finalize should not run for active stall"),
    )

    assert implement_dispatch.step_18_gate_finalize_main(["--implement-tmpdir", str(tmp)]) == 0

    captured = capsys.readouterr()
    assert "STALL_TRACKING_DISK=1\n" in captured.out
    assert "STALL_RECOVERY_REQUIRED=true\n" in captured.out
    assert captured.out.rstrip().endswith("NEXT_ACTION=stall-recovery")


def test_step18_gate_finalize_outcome_false_skips_filing_even_with_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    (tmp / "stall-recovery-escalation-fallback.tsv").write_text("site=step8\n", encoding="utf-8")
    _install_step18_normalize(monkeypatch, succeeded=False)
    finalize_calls: list[list[str]] = []
    _install_step18_finalize(monkeypatch, calls=finalize_calls)

    assert implement_dispatch.step_18_gate_finalize_main(["--implement-tmpdir", str(tmp)]) == 0

    assert finalize_calls
    assert capsys.readouterr().out.rstrip().endswith("NEXT_ACTION=finalize-done")


def test_step18_gate_finalize_terminal_sentinel_skips_filing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    (tmp / "stall-recovery-terminal-report.env").write_text("TERMINAL=true\n", encoding="utf-8")
    (tmp / "stall-recovery-escalation-record-failure.env").write_text("FAILED=true\n", encoding="utf-8")
    _install_step18_normalize(monkeypatch, succeeded=True)
    finalize_calls: list[list[str]] = []
    _install_step18_finalize(monkeypatch, calls=finalize_calls)

    assert implement_dispatch.step_18_gate_finalize_main(["--implement-tmpdir", str(tmp)]) == 0

    assert finalize_calls
    assert capsys.readouterr().out.rstrip().endswith("NEXT_ACTION=finalize-done")


def test_step18_gate_finalize_escalation_success_sentinel_skips_filing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    (tmp / "stall-recovery-escalation-success.env").write_text("FILED=true\n", encoding="utf-8")
    (tmp / "stall-recovery-escalation-record-failure.env").write_text("FAILED=true\n", encoding="utf-8")
    _install_step18_normalize(monkeypatch, succeeded=True)
    finalize_calls: list[list[str]] = []
    _install_step18_finalize(monkeypatch, calls=finalize_calls)

    assert implement_dispatch.step_18_gate_finalize_main(["--implement-tmpdir", str(tmp)]) == 0

    assert finalize_calls
    assert capsys.readouterr().out.rstrip().endswith("NEXT_ACTION=finalize-done")


def test_step18_gate_finalize_preserves_finalize_rc(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    _install_step18_normalize(monkeypatch, succeeded=False)
    finalize_calls: list[list[str]] = []
    _install_step18_finalize(monkeypatch, calls=finalize_calls, rc=9, stdout="EMIT_BODY=true\n")

    assert implement_dispatch.step_18_gate_finalize_main(["--implement-tmpdir", str(tmp)]) == 9

    captured = capsys.readouterr()
    assert "EMIT_BODY=true\n" in captured.out
    assert "finalize stderr\n" in captured.err
    assert captured.out.rstrip().endswith("NEXT_ACTION=finalize-done")


def test_step8_oos_checkpoint_filed_count_ignores_stale_sentinel_without_ndjson(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp))
    (tmp / "ship-pr-state.sh").write_text("RUN_ID=run\nOOS_PENDING=true\nPR_NUMBER=1\n", encoding="utf-8")
    run_dir = tmp / "larch-logs" / "implement" / "run"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text('{"steps_ran":{}}\n', encoding="utf-8")
    (tmp / "oos-issues-created.md").write_text(
        "- **Filed URL**: https://github.com/owner/repo/issues/stale\n",
        encoding="utf-8",
    )
    _mock_disposition_checkpoint_only(monkeypatch)

    assert implement_dispatch.step8_oos_checkpoint_main([]) == 0

    assert capsys.readouterr().out == "OOS_CHECKPOINT_RC=0\nNEXT_ACTION=reship\n"
    assert (run_dir / "run-statistics.md").read_text(encoding="utf-8") == "Run run: 0 OOS issue(s) filed.\n"


def test_step8_oos_checkpoint_nonzero_preserves_child_written_stderr_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp))
    (tmp / "oos-disposition-checkpoint.stderr.log").write_text("child validation detail\n", encoding="utf-8")
    monkeypatch.setattr(
        implement_dispatch.subprocess,
        "run",
        lambda *_a, **_k: subprocess.CompletedProcess(["checkpoint"], 2, "", ""),
    )
    monkeypatch.setattr(implement_dispatch, "_invoke_cli", lambda *_a, **_k: subprocess.CompletedProcess(["append"], 0, "", ""))

    assert implement_dispatch.step8_oos_checkpoint_main([]) == 0

    assert capsys.readouterr().out == "OOS_CHECKPOINT_RC=2\nNEXT_ACTION=stall\n"
    assert (tmp / "oos-disposition-checkpoint.stderr.log").read_text(encoding="utf-8") == "child validation detail\n"


def _parse_clone_tag_env(out: str) -> dict[str, str]:
    lines = out.splitlines()
    assert [line.split("=", 1)[0] for line in lines] == [
        "CLONE_TAG_FULL",
        "EXPECTED_TMPDIR_BASENAME_PREFIX",
    ]
    parsed: dict[str, str] = {}
    for line in lines:
        fields = shlex.split(line)
        assert len(fields) == 1
        key, value = fields[0].split("=", 1)
        parsed[key] = value
    return parsed


def test_clone_tag_cli_passes_clone_tag_through_with_shell_quoting(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    value = "tag with spaces; $(echo nope) 'quoted'"
    monkeypatch.setenv("CLONE_TAG", value)

    assert implement_dispatch.clone_tag_main([]) == 0

    parsed = _parse_clone_tag_env(capsys.readouterr().out)
    assert parsed == {
        "CLONE_TAG_FULL": value,
        "EXPECTED_TMPDIR_BASENAME_PREFIX": f"claude-implement-{value}-",
    }


def test_clone_tag_cli_derives_from_logical_pwd(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.delenv("CLONE_TAG", raising=False)
    monkeypatch.setenv("PWD", "/logical/repo with spaces!")

    assert implement_dispatch.clone_tag_main([]) == 0

    parsed = _parse_clone_tag_env(capsys.readouterr().out)
    assert parsed["CLONE_TAG_FULL"] == "repo_with_spaces_"
    assert parsed["EXPECTED_TMPDIR_BASENAME_PREFIX"] == "claude-implement-repo_with_spaces_-"


def test_clone_tag_derivation_truncates_sanitized_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLONE_TAG", raising=False)
    monkeypatch.setenv("PWD", "/" + ("é" * 20))

    assert implement_dispatch._derive_clone_tag_full() == "_" * 32


def test_clone_tag_derivation_keeps_one_underscore_per_invalid_byte(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLONE_TAG", raising=False)
    monkeypatch.setenv("PWD", "/!!!")

    assert implement_dispatch._derive_clone_tag_full() == "___"


def test_clone_tag_derivation_empty_basename_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLONE_TAG", raising=False)
    monkeypatch.setenv("PWD", "/")

    assert implement_dispatch._derive_clone_tag_full() == "_"


def test_clone_tag_derivation_strips_trailing_slash_from_pwd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLONE_TAG", raising=False)
    monkeypatch.setenv("PWD", "/logical/larch4/")

    assert implement_dispatch._derive_clone_tag_full() == "larch4"


def test_clone_tag_derivation_uses_pwd_not_physical_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    physical = tmp_path / "physical"
    physical.mkdir()
    monkeypatch.chdir(physical)
    monkeypatch.delenv("CLONE_TAG", raising=False)
    monkeypatch.setenv("PWD", "/logical/logical clone")

    assert physical.name != "logical clone"
    assert implement_dispatch._derive_clone_tag_full() == "logical_clone"


def test_clone_expected_tmpdir_prefix_reuses_clone_tag_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLONE_TAG", raising=False)
    monkeypatch.setenv("PWD", "/logical/repo.name")

    assert implement_dispatch._clone_expected_tmpdir_prefix() == f"claude-implement-{implement_dispatch._derive_clone_tag_full()}-"


def test_ship_pre_driver_guard_failure_isolates_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp))
    calls: list[list[str]] = []

    def fake_run_cli(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(args))
        return subprocess.CompletedProcess(list(args), 4, '{"outcome":"STALLED"}\n', "guard stderr\n")

    monkeypatch.setattr(implement_dispatch, "_run_cli_capture", fake_run_cli)
    monkeypatch.setattr(dispatch_ship, "_run_cli_capture", fake_run_cli)

    assert implement_dispatch.ship_pre_driver_main([]) == 4

    captured = capsys.readouterr()
    assert captured.out == "NEXT_ACTION=stall\n"
    assert captured.err == '{"outcome":"STALLED"}\nguard stderr\n'
    assert calls == [["implement", "step-8-python-guard"]]


def test_ship_pre_driver_seed_failure_stops_before_oos(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp))
    results = [
        subprocess.CompletedProcess(["guard"], 0, "", ""),
        subprocess.CompletedProcess(["seed"], 7, "seed stdout\n", "seed stderr\n"),
    ]
    calls: list[list[str]] = []

    def fake_run_cli(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(args))
        return results.pop(0)

    monkeypatch.setattr(implement_dispatch, "_run_cli_capture", fake_run_cli)
    monkeypatch.setattr(dispatch_ship, "_run_cli_capture", fake_run_cli)

    assert implement_dispatch.ship_pre_driver_main([]) == 7

    captured = capsys.readouterr()
    assert captured.out == "NEXT_ACTION=halt-seed\n"
    assert captured.err == "seed stdout\nseed stderr\n"
    assert calls == [["implement", "step-8-python-guard"], ["implement", "step-8-seed-initial"]]


def test_ship_pre_driver_oos_failure_uses_distinct_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp))
    results = [
        subprocess.CompletedProcess(["guard"], 0, "", ""),
        subprocess.CompletedProcess(["seed"], 0, "seed stdout\n", ""),
        subprocess.CompletedProcess(["oos"], 5, '{"accepted":0}\n', "oos stderr\n"),
    ]
    calls: list[list[str]] = []

    def fake_run_cli(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(args))
        return results.pop(0)

    monkeypatch.setattr(implement_dispatch, "_run_cli_capture", fake_run_cli)
    monkeypatch.setattr(dispatch_ship, "_run_cli_capture", fake_run_cli)

    assert implement_dispatch.ship_pre_driver_main([]) == 5

    captured = capsys.readouterr()
    assert captured.out == "NEXT_ACTION=halt-oos\n"
    assert captured.err == 'seed stdout\n{"accepted":0}\noos stderr\n'
    assert calls == [
        ["implement", "step-8-python-guard"],
        ["implement", "step-8-seed-initial"],
        ["oos", "file", "--implement-tmpdir", str(tmp)],
    ]


def test_ship_pre_driver_success_skips_seed_when_state_has_kv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)
    (tmp / "ship-pr-state.sh").write_text("# comment\nPHASE=checks\n", encoding="utf-8")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp))
    results = [
        subprocess.CompletedProcess(["guard"], 0, "", ""),
        subprocess.CompletedProcess(["oos"], 0, '{"accepted":0}\n', ""),
    ]
    calls: list[list[str]] = []

    def fake_run_cli(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(args))
        return results.pop(0)

    monkeypatch.setattr(implement_dispatch, "_run_cli_capture", fake_run_cli)
    monkeypatch.setattr(dispatch_ship, "_run_cli_capture", fake_run_cli)

    assert implement_dispatch.ship_pre_driver_main([]) == 0

    captured = capsys.readouterr()
    assert captured.out == "NEXT_ACTION=ship\n"
    assert captured.err == '{"accepted":0}\n'
    assert calls == [["implement", "step-8-python-guard"], ["oos", "file", "--implement-tmpdir", str(tmp)]]


def test_recovery_paths_filters_tmpdir_and_detects_changed_predirty(repo: Path) -> None:
    tmp = repo / ".tmp-impl"
    tmp.mkdir()
    predirty = repo / "README.md"
    predirty.write_text("dirty-before\n", encoding="utf-8")
    pre = tmp / "pre.nul"
    post = tmp / "post.nul"
    digests = tmp / "digests.txt"
    out = tmp / "out.nul"
    pre.write_bytes(_git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout.encode())
    digest = implement_dispatch.hashlib.sha256(predirty.read_bytes()).hexdigest()
    digests.write_text(f"{digest}\tREADME.md\n", encoding="utf-8")
    predirty.write_text("changed-after\n", encoding="utf-8")
    (repo / "new.txt").write_text("new\n", encoding="utf-8")
    (tmp / "scratch.txt").write_text("scratch\n", encoding="utf-8")
    post.write_bytes(_git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout.encode())

    ok = implement_dispatch.compute_recovery_paths(
        repo_root=repo,
        tmpdir=tmp,
        prelaunch_porcelain=pre,
        postlaunch_porcelain=post,
        prelaunch_digests=digests,
        out_file=out,
    )

    assert ok is True
    paths = set(out.read_bytes().rstrip(b"\0").split(b"\0"))
    assert b"README.md" in paths
    assert b"new.txt" in paths
    assert all(not p.startswith(b".tmp-impl/") for p in paths)


def test_step2_dispatch_claude_fallback(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "claude",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=claude_fallback" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=allowed" in out


def test_step2_dispatch_claude_fallback_clears_scout_sidecars(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    (tmp / "scout-coder-manifest.json").write_text('{"archetypes":[]}\n', encoding="utf-8")
    (tmp / "step2-external-scout-eligible.txt").write_text("eligible\n", encoding="utf-8")
    (tmp / "step2-scout-coder-status.env").write_text("SCOUT_CODER_STATUS=ok\n", encoding="utf-8")
    (tmp / "scout-coder-manifest.raw.json").write_text('{"archetypes":[]}\n', encoding="utf-8")
    (tmp / ".producer-scout-warning-logged").write_text("logged\n", encoding="utf-8")
    codex_out = tmp / "codex-step2-out"
    codex_out.mkdir()
    (codex_out / "scout-coder-manifest.json").write_text('{"archetypes":[]}\n', encoding="utf-8")
    cursor_out = tmp / "cursor-step2-out"
    cursor_out.mkdir()
    (cursor_out / "scout-coder-manifest.json").write_text('{"archetypes":[]}\n', encoding="utf-8")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "claude",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=claude_fallback" in out
    for path in (
        tmp / "scout-coder-manifest.json",
        tmp / "step2-external-scout-eligible.txt",
        tmp / "step2-scout-coder-status.env",
        tmp / "scout-coder-manifest.raw.json",
        tmp / ".producer-scout-warning-logged",
        codex_out / "scout-coder-manifest.json",
        cursor_out / "scout-coder-manifest.json",
    ):
        assert not path.exists(), f"expected {path} removed after claude_fallback"


def _legacy_malformed_manifest() -> str:
    return '{"status":"complete","summary":"done","checks":"ok"}\n'


def _assert_bailed_no_recovery(out: str, *, reason: str = "manifest-schema-invalid") -> None:
    assert "STATUS=bailed" in out
    assert f"REASON={reason}" in out
    assert "RECOVERY_FROM=" not in out


def _assert_recovery_envelope(out: str, tool: str) -> None:
    assert "STATUS=claude_fallback" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=allowed" in out
    assert "RECOVERY_FROM=manifest-schema-invalid" in out
    assert f"RECOVERY_PRIOR_TOOL={tool}" in out
    assert "RECOVERY_PATHS_FILE=" in out
    assert _auth_lines(out) == 1


def _recovery_paths_from_file(path: Path) -> list[str]:
    return [p.decode() for p in path.read_bytes().split(b"\0") if p]


def _kv_value(out: str, key: str) -> str:
    prefix = f"{key}="
    for line in out.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):]
    raise AssertionError(f"missing {key}= in output")


def _malformed_launcher(edit: Callable[[Path, implement_dispatch.DispatchState], None]):
    def fake_launcher(st: implement_dispatch.DispatchState):
        edit(st.repo_root, st)
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(_legacy_malformed_manifest(), encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    return fake_launcher


def test_run_dispatch_missing_tmpdir_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        implement_dispatch.run_dispatch_main(["--coder", "codex"])
    assert exc.value.code == 2
    assert "--implement-tmpdir" in capsys.readouterr().err


def test_run_dispatch_missing_answers_path_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    rc = implement_dispatch.run_dispatch_main([
        "--implement-tmpdir", str(tmp),
        "--coder", "codex",
        "--answers", str(tmp / "missing.json"),
    ])
    assert rc == 2
    assert "--answers path does not exist" in capsys.readouterr().err


def test_run_dispatch_ignores_legacy_cursor_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tmp = _session(tmp_path)
    (tmp / "session-env.sh").write_text(
        "CURSOR_PRESENT=maybe\nCODEX_BINARY_FOUND=true\nCURSOR_BINARY_FOUND=true\nLARCH_CLAUDE_PLUGIN_ROOT=.\n",
        encoding="utf-8",
    )
    captured: dict[str, list[str]] = {}

    def fake_run(argv, **_kwargs):  # type: ignore[no-untyped-def]
        if len(argv) >= 4 and argv[2:4] == ["implement", "step2-dispatch"]:
            captured["argv"] = list(argv)
            return subprocess.CompletedProcess(argv, 0, "STATUS=claude_fallback\nORCHESTRATOR_EDIT_AUTHORITY=allowed\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(implement_dispatch.subprocess, "run", fake_run)
    monkeypatch.setattr(implement_dispatch, "_resolve_repo_root", lambda: Path("/repo"))
    monkeypatch.setattr(dispatch_step2, "_resolve_repo_root", lambda: Path("/repo"))
    monkeypatch.setattr(implement_dispatch, "_capture_prelaunch_porcelain", lambda **_kwargs: 0)
    monkeypatch.setattr(dispatch_step2, "_capture_prelaunch_porcelain", lambda **_kwargs: 0)
    rc = implement_dispatch.run_dispatch_main(["--implement-tmpdir", str(tmp), "--coder", "codex"])
    assert rc == 0
    assert "--cursor-binary-found" in captured["argv"]


def test_run_dispatch_forwards_answers_to_step2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tmp = _session(tmp_path)
    answers = tmp / "answers.json"
    answers.write_text('{"answers":[]}\n', encoding="utf-8")
    captured: dict[str, list[str]] = {}

    def fake_run(argv, **_kwargs):  # type: ignore[no-untyped-def]
        if len(argv) >= 4 and argv[2:4] == ["implement", "step2-dispatch"]:
            captured["argv"] = list(argv)
            return subprocess.CompletedProcess(argv, 0, "STATUS=claude_fallback\nORCHESTRATOR_EDIT_AUTHORITY=allowed\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(implement_dispatch.subprocess, "run", fake_run)
    monkeypatch.setattr(implement_dispatch, "_resolve_repo_root", lambda: Path("/repo"))
    monkeypatch.setattr(dispatch_step2, "_resolve_repo_root", lambda: Path("/repo"))
    monkeypatch.setattr(implement_dispatch, "_capture_prelaunch_porcelain", lambda **_kwargs: 0)
    monkeypatch.setattr(dispatch_step2, "_capture_prelaunch_porcelain", lambda **_kwargs: 0)
    rc = implement_dispatch.run_dispatch_main([
        "--implement-tmpdir", str(tmp),
        "--coder", "codex",
        "--answers", str(answers),
    ])
    assert rc == 0
    argv = captured["argv"]
    assert "--answers" in argv
    assert str(answers) in argv


def test_run_dispatch_marks_step2_once_under_lock_and_skips_answers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp = _session(tmp_path)
    (tmp / "session-env.sh").write_text(
        "CODEX_BINARY_FOUND=false\nLARCH_CLAUDE_PLUGIN_ROOT=.\n",
        encoding="utf-8",
    )
    answers = tmp / "answers.json"
    answers.write_text('{"answers":[]}\n', encoding="utf-8")
    token_calls: list[list[str]] = []
    timing_calls: list[list[str]] = []

    def fake_run(argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        call = list(argv)
        if call[-3:] == ["token", "mark", "Step 2 — implementation"]:
            token_calls.append(call)
            return subprocess.CompletedProcess(call, 0, "", "")
        if call[-3:] == ["timing", "mark", "Step 2 — implementation"]:
            timing_calls.append(call)
            return subprocess.CompletedProcess(call, 0, "", "")
        if len(call) >= 4 and call[2:4] == ["implement", "step2-dispatch"]:
            return subprocess.CompletedProcess(
                call,
                0,
                "STATUS=claude_fallback\nORCHESTRATOR_EDIT_AUTHORITY=allowed\n",
                "",
            )
        return subprocess.CompletedProcess(call, 0, "", "")

    monkeypatch.setattr(implement_dispatch.subprocess, "run", fake_run)
    monkeypatch.setattr(implement_dispatch, "_resolve_repo_root", lambda: Path("/repo"))
    monkeypatch.setattr(dispatch_step2, "_resolve_repo_root", lambda: Path("/repo"))
    monkeypatch.setattr(implement_dispatch, "_capture_prelaunch_porcelain", lambda **_kwargs: 0)
    monkeypatch.setattr(dispatch_step2, "_capture_prelaunch_porcelain", lambda **_kwargs: 0)

    assert implement_dispatch.run_dispatch_main(["--implement-tmpdir", str(tmp), "--coder", "codex"]) == 0
    assert implement_dispatch.run_dispatch_main([
        "--implement-tmpdir",
        str(tmp),
        "--coder",
        "codex",
        "--answers",
        str(answers),
    ]) == 0

    assert len(token_calls) == 1
    assert len(timing_calls) == 1
    assert (tmp / ".step2-telemetry-marked").is_file()


def test_run_dispatch_fails_closed_when_fallback_repo_root_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tmp = _session(tmp_path)

    def fake_run(argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        call = list(argv)
        if len(call) >= 4 and call[2:4] == ["implement", "step2-dispatch"]:
            return subprocess.CompletedProcess(
                call,
                0,
                "STATUS=claude_fallback\nORCHESTRATOR_EDIT_AUTHORITY=allowed\n",
                "",
            )
        return subprocess.CompletedProcess(call, 0, "", "")

    monkeypatch.setattr(implement_dispatch.subprocess, "run", fake_run)
    monkeypatch.setattr(implement_dispatch, "_resolve_repo_root", lambda: None)
    monkeypatch.setattr(dispatch_step2, "_resolve_repo_root", lambda: None)

    rc = implement_dispatch.run_dispatch_main(["--implement-tmpdir", str(tmp), "--coder", "claude"])

    captured = capsys.readouterr()
    assert rc == 2
    assert "STATUS=claude_fallback" not in captured.out
    assert "git rev-parse --show-toplevel failed" in captured.err
    assert not (tmp / ".step2-telemetry-marked").is_file()


def test_run_dispatch_rejects_concurrent_caller(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    lock_path = tmp / "dispatch.lock"
    lock_path.touch()
    with lock_path.open("w") as holder:
        fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
        rc = implement_dispatch.run_dispatch_main(["--implement-tmpdir", str(tmp), "--coder", "codex"])
    assert rc == 2
    assert "another dispatch is already running" in capsys.readouterr().err


def test_run_dispatch_permission_error_not_reported_as_contention(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # An OSError with errno != EAGAIN/EWOULDBLOCK must not claim another dispatch is running.
    def _flock_raises_eacces(fd: object, operation: object) -> None:
        _ = fd, operation
        raise OSError(errno.EACCES, "Operation not permitted")

    monkeypatch.setattr(fcntl, "flock", _flock_raises_eacces)
    tmp = _session(tmp_path)
    rc = implement_dispatch.run_dispatch_main(["--implement-tmpdir", str(tmp), "--coder", "codex"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "another dispatch is already running" not in err
    assert "failed to acquire dispatch lock" in err


def test_step2_dispatch_complete_commits_manifest_message(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "implemented.txt").write_text("done\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(json.dumps({
            "schema_version": "1",
            "status": "complete",
            "files_touched": [{"path": "implemented.txt", "lines_added": 1, "lines_removed": 0}],
            "tests_added_or_modified": [],
            "summary_bullets": ["Implement the feature"],
            "commit_message": "Implement via fake launcher",
            "todos_left": [],
            "oos_observations": [],
        }), encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(dispatch_step2, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    monkeypatch.setattr(dispatch_step2, "_materialize_oos", lambda *_a, **_k: "")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=complete" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out
    assert _git(repo, "log", "-1", "--pretty=%s").stdout.strip() == "Implement via fake launcher"


def test_step2_dispatch_malformed_manifest_recovery(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "recovered.txt").write_text("done\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text('{"status":"complete","summary":"x","checks":"y"}\n', encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "cursor",
        "--cursor-present", "true",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=claude_fallback" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=allowed" in out
    assert "RECOVERY_FROM=manifest-schema-invalid" in out
    assert (tmp / "step2-recovery-paths.nul").read_bytes() == b"recovered.txt\0"


def test_step2_dispatch_malformed_manifest_empty_delta_bails(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _ = repo
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))
    monkeypatch.setattr(implement_dispatch, "_run_launcher", _malformed_launcher(lambda _repo, _st: None))
    monkeypatch.setattr(dispatch_step2, "_run_launcher", _malformed_launcher(lambda _repo, _st: None))
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    _assert_bailed_no_recovery(capsys.readouterr().out)


def test_step2_dispatch_prelaunch_staged_index_blocks_recovery(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    (repo / "staged.txt").write_text("prelaunch staged\n", encoding="utf-8")
    _git(repo, "add", "staged.txt")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def edit_readme(repo_root: Path, _st: implement_dispatch.DispatchState) -> None:
        (repo_root / "README.md").write_text("recovered edit\n", encoding="utf-8")

    monkeypatch.setattr(
        implement_dispatch,
        "_run_launcher",
        _malformed_launcher(edit_readme),
    )
    monkeypatch.setattr(dispatch_step2, "_run_launcher", _malformed_launcher(edit_readme))
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    _assert_bailed_no_recovery(capsys.readouterr().out)
    assert "PRELAUNCH_INDEX_NONEMPTY=true" in (tmp / "step2-prelaunch-index.env").read_text(encoding="utf-8")


def test_step2_dispatch_rename_recovery_uses_destination_path(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _ = repo
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def edit(repo_root: Path, _st: implement_dispatch.DispatchState) -> None:
        _git(repo_root, "mv", "README.md", "RENAMED.md")

    monkeypatch.setattr(implement_dispatch, "_run_launcher", _malformed_launcher(edit))
    monkeypatch.setattr(dispatch_step2, "_run_launcher", _malformed_launcher(edit))
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    _assert_recovery_envelope(out, "codex")
    recovery_file = Path(_kv_value(out, "RECOVERY_PATHS_FILE"))
    assert _recovery_paths_from_file(recovery_file) == ["RENAMED.md"]


def test_step2_dispatch_baseline_persists_across_answers_resume(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))
    state = {"round": 0}

    def fake_launcher(st: implement_dispatch.DispatchState):
        state["round"] += 1
        if state["round"] == 1:
            (repo / "A.txt").write_text("round1\n", encoding="utf-8")
            st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
            st.manifest_path.write_text(json.dumps({
                "schema_version": "1",
                "status": "needs_qa",
                "needs_qa": {"questions": [{"id": "q1", "text": "continue?"}]},
            }), encoding="utf-8")
            st.qa_pending_path.write_text(json.dumps({
                "questions": [{"id": "q1", "text": "continue?"}],
            }), encoding="utf-8")
            return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""
        (repo / "B.txt").write_text("round2\n", encoding="utf-8")
        st.manifest_path.write_text(_legacy_malformed_manifest(), encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(dispatch_step2, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    rc_qa = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc_qa == 0
    assert "STATUS=needs_qa" in capsys.readouterr().out
    answers = tmp / "answers.json"
    answers.write_text('{"answers":[{"id":"q1","text":"yes"}]}\n', encoding="utf-8")
    rc_recovery = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
        "--answers", str(answers),
    ])
    assert rc_recovery == 0
    out = capsys.readouterr().out
    _assert_recovery_envelope(out, "codex")
    recovery_file = Path(_kv_value(out, "RECOVERY_PATHS_FILE"))
    assert _recovery_paths_from_file(recovery_file) == ["A.txt", "B.txt"]


def test_step2_dispatch_non_v1_schema_version_hard_bails(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        readme = repo / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "edit\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(
            '{"schema_version":2,"status":"complete","summary":"done","checks":"ok"}\n',
            encoding="utf-8",
        )
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    _assert_bailed_no_recovery(capsys.readouterr().out)


def test_step2_dispatch_launcher_retries_on_clean_post_failure(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))
    launcher_calls = 0

    def fake_launcher(st: implement_dispatch.DispatchState):
        nonlocal launcher_calls
        launcher_calls += 1
        if launcher_calls == 1:
            return 1, {"LAUNCHER_EXIT": "1", "MANIFEST_WRITTEN": "false"}, ""
        (repo / "implemented.txt").write_text("done\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(json.dumps(_complete_manifest_payload()), encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(dispatch_step2, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    monkeypatch.setattr(dispatch_step2, "_materialize_oos", lambda *_a, **_k: "")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    assert launcher_calls == 2
    out = capsys.readouterr().out
    assert "STATUS=complete" in out


def test_step2_dispatch_oos_materialize_failure_bails(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    plugin_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin_root))
    monkeypatch.setenv("LARCH_TEST_MATERIALIZE_FORCE_FAIL", "true")

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "README.md").write_text("edited by stub\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(json.dumps({
            "schema_version": "1",
            "status": "complete",
            "files_touched": [{"path": "README.md"}],
            "commit_message": "stub: edit README",
            "summary_bullets": ["edited README"],
            "tests_added_or_modified": [],
            "todos_left": [],
            "oos_observations": [{"title": "OOS", "description": "manifest OOS", "phase": "implement"}],
        }), encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(dispatch_step2, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=bailed" in out
    assert "REASON=manifest-oos-materialization-failed" in out


def test_commit_main_commits_named_file(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / "commit-me.txt").write_text("x\n", encoding="utf-8")
    rc = implement_dispatch.commit_main(["--message", "Commit helper", "commit-me.txt"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "COMMITTED=true" in out
    assert _git(repo, "log", "-1", "--pretty=%s").stdout.strip() == "Commit helper"


def test_commit_main_passes_named_files_once(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    calls: list[list[str]] = []

    def fake_run(argv, **_kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(argv))
        stdout = "abc123\n" if argv[:2] == ["git", "rev-parse"] else ""
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    monkeypatch.setattr(implement_dispatch, "_invoke_cli", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(dispatch_recovery, "_invoke_cli", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(implement_dispatch, "_run", fake_run)
    monkeypatch.setattr(dispatch_recovery, "_run", fake_run)

    rc = implement_dispatch.commit_main(["--message", "Commit helper", "one.txt", "two.txt"])

    assert rc == 0
    assert calls[0][-2:] == ["one.txt", "two.txt"]
    assert calls[0].count("one.txt") == 1
    assert calls[0].count("two.txt") == 1
    assert "SHA=abc123" in capsys.readouterr().out


def test_commit_main_missing_message_emits_envelope(capsys: pytest.CaptureFixture[str]) -> None:
    rc = implement_dispatch.commit_main(["file.txt"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "COMMITTED=false" in captured.out
    assert "ERROR=--message is required" in captured.out
    assert "review-and-fix commit-fixes" in captured.err


def test_commit_main_stage_all_unknown_option_emits_envelope(capsys: pytest.CaptureFixture[str]) -> None:
    rc = implement_dispatch.commit_main(["--stage-all"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "COMMITTED=false" in captured.out
    assert "ERROR=unknown option: --stage-all" in captured.out
    assert "review-and-fix commit-fixes" in captured.err


def test_commit_main_git_commit_failure_preserves_exit_code(repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / "file.txt").write_text("x\n", encoding="utf-8")

    def fake_run(argv, **_kwargs):  # type: ignore[no-untyped-def]
        if list(argv[:4]) == [sys.executable, str(implement_dispatch._current_cli_path()), "git", "commit"]:  # pyright: ignore[reportPrivateUsage]
            return subprocess.CompletedProcess(argv, 7, "", "hook rejected commit")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(implement_dispatch, "_invoke_cli", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(dispatch_recovery, "_invoke_cli", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(implement_dispatch, "_run", fake_run)
    monkeypatch.setattr(dispatch_recovery, "_run", fake_run)
    rc = implement_dispatch.commit_main(["--message", "Implement thing", "file.txt"])
    assert rc == 7
    captured = capsys.readouterr()
    assert "COMMITTED=false" in captured.out
    assert "ERROR=hook rejected commit" in captured.out


_STEP5_COMMIT_OK = "COMMITTED=true\nSHA=abc123\nERROR=\nCOMMIT_OUTCOME=ok\n"
_STEP5_COMMIT_NOOP = "COMMITTED=false\nSHA=\nERROR=\nCOMMIT_OUTCOME=noop\n"
_STEP5_COMMIT_FAILED = "COMMITTED=false\nSHA=\nERROR=no review delta paths\nCOMMIT_OUTCOME=failed\n"
_STEP5_ROUTE_OK = _STEP5_COMMIT_OK + "NEXT_ACTION=continue\n"
_STEP5_ROUTE_NOOP = _STEP5_COMMIT_NOOP + "NEXT_ACTION=continue\n"
_STEP5_ROUTE_STALL = _STEP5_COMMIT_FAILED + "NEXT_ACTION=stall\n"


def _setup_commit_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    commit_stdout: str,
    commit_rc: int = 0,
    commit_stderr: str = "",
    porcelain_stdout: str = "",
    porcelain_rc: int = 0,
    seed_rc: int = 0,
) -> tuple[Path, list[list[str]], list[list[str]]]:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    invoke_calls: list[list[str]] = []
    seed_calls: list[list[str]] = []

    def fake_invoke(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        call = list(args)
        invoke_calls.append(call)
        if call == ["review-and-fix", "commit-fixes", "--stage-all"]:
            return subprocess.CompletedProcess(call, commit_rc, commit_stdout, commit_stderr)
        if call[:2] == ["run-log", "append-failure"]:
            return subprocess.CompletedProcess(call, 0, "", "")
        return subprocess.CompletedProcess(call, 0, "", "")

    def fake_seed(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        call = list(args)
        seed_calls.append(call)
        if seed_rc == 0:
            (impl / "ship-pr-state.sh").write_text(
                "STALL_TRACKING=true\nSTALL_STEP=seeded\nBAIL_REASON=seeded\n",
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(call, seed_rc, "", "seed failed\n" if seed_rc else "")

    def fake_run(argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(list(argv), porcelain_rc, porcelain_stdout, "")

    monkeypatch.setattr(implement_dispatch, "_invoke_cli", fake_invoke)
    monkeypatch.setattr(dispatch_commit_route, "_invoke_cli", fake_invoke)
    monkeypatch.setattr(implement_dispatch, "_run_cli_capture", fake_seed)
    monkeypatch.setattr(dispatch_commit_route, "_run_cli_capture", fake_seed)
    monkeypatch.setattr(implement_dispatch, "_run", fake_run)
    monkeypatch.setattr(dispatch_commit_route, "_run", fake_run)
    return impl, invoke_calls, seed_calls


@pytest.mark.parametrize("site", ["step5-self-review", "step5-resume-handoff", "step7"])
@pytest.mark.parametrize("commit_stdout", [_STEP5_COMMIT_OK, _STEP5_COMMIT_NOOP])
def test_commit_route_success_relays_continue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    site: str,
    commit_stdout: str,
) -> None:
    _impl, invoke_calls, seed_calls = _setup_commit_route(tmp_path, monkeypatch, commit_stdout=commit_stdout)

    rc = implement_dispatch.commit_route_main(["--site", site])

    assert rc == 0
    out = capsys.readouterr().out
    assert "COMMIT_OUTCOME=" in out
    assert "NEXT_ACTION=continue\n" in out
    assert out.count("NEXT_ACTION=") == 1
    assert ["review-and-fix", "commit-fixes", "--stage-all"] in invoke_calls
    assert not [call for call in invoke_calls if call[:2] == ["run-log", "append-failure"]]
    assert not seed_calls


@pytest.mark.parametrize(
    ("site", "stall_step", "bail_reason"),
    [
        ("step5-self-review", "5", "review-fix-commit-failed"),
        ("step5-resume-handoff", "5", "resume-handoff-commit-failed"),
        ("step7", "7", "review-fix-commit-failed"),
    ],
)
@pytest.mark.parametrize(
    "commit_stdout",
    [
        "COMMITTED=false\nERROR=missing outcome with COMMIT_OUTCOME=ok in prose\n",
        "COMMITTED=false\nCOMMIT_OUTCOME=bogus\n",
        _STEP5_COMMIT_FAILED,
    ],
)
def test_commit_route_failure_seeds_stall_and_logs_redacted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    site: str,
    stall_step: str,
    bail_reason: str,
    commit_stdout: str,
) -> None:
    impl, invoke_calls, _seed_calls = _setup_commit_route(
        tmp_path,
        monkeypatch,
        commit_stdout=commit_stdout,
        commit_rc=1 if "COMMIT_OUTCOME=failed" in commit_stdout else 0,
    )
    (impl / "ship-pr-state.sh").write_text("RUN_ID=run\nOOS_PENDING=false\n", encoding="utf-8")

    rc = implement_dispatch.commit_route_main(["--site", site])

    assert rc == 0
    out = capsys.readouterr().out
    assert "NEXT_ACTION=stall\n" in out
    assert out.count("NEXT_ACTION=") == 1
    state = (impl / "ship-pr-state.sh").read_text(encoding="utf-8")
    assert "STALL_TRACKING=true\n" in state
    assert f"STALL_STEP={stall_step}\n" in state
    assert f"BAIL_REASON={bail_reason}\n" in state
    log_calls = [call for call in invoke_calls if call[:2] == ["run-log", "append-failure"]]
    assert len(log_calls) == 1
    assert "--redact" in log_calls[0]


@pytest.mark.parametrize(("porcelain_stdout", "porcelain_rc"), [(" M leftover.txt\n", 0), ("", 1)])
def test_commit_route_resume_porcelain_failure_seeds_and_logs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    porcelain_stdout: str,
    porcelain_rc: int,
) -> None:
    impl, invoke_calls, _seed_calls = _setup_commit_route(
        tmp_path,
        monkeypatch,
        commit_stdout=_STEP5_COMMIT_OK,
        porcelain_stdout=porcelain_stdout,
        porcelain_rc=porcelain_rc,
    )
    (impl / "ship-pr-state.sh").write_text("RUN_ID=run\nOOS_PENDING=false\n", encoding="utf-8")

    rc = implement_dispatch.commit_route_main(["--site", "step5-resume-handoff"])

    assert rc == 0
    assert "NEXT_ACTION=stall\n" in capsys.readouterr().out
    state = (impl / "ship-pr-state.sh").read_text(encoding="utf-8")
    assert "STALL_STEP=5\n" in state
    assert "BAIL_REASON=resume-handoff-commit-failed\n" in state
    log_calls = [call for call in invoke_calls if call[:2] == ["run-log", "append-failure"]]
    assert len(log_calls) == 1
    assert "--redact" in log_calls[0]


def test_commit_route_self_review_skips_porcelain_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _impl, _invoke_calls, _seed_calls = _setup_commit_route(
        tmp_path,
        monkeypatch,
        commit_stdout=_STEP5_COMMIT_OK,
        porcelain_stdout=" M ignored.txt\n",
    )

    rc = implement_dispatch.commit_route_main(["--site", "step5-self-review"])

    assert rc == 0
    assert "NEXT_ACTION=continue\n" in capsys.readouterr().out


def test_commit_route_absent_state_uses_initial_seed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl, _invoke_calls, seed_calls = _setup_commit_route(
        tmp_path,
        monkeypatch,
        commit_stdout=_STEP5_COMMIT_FAILED,
        commit_rc=1,
    )

    rc = implement_dispatch.commit_route_main(["--site", "step7"])

    assert rc == 0
    assert "NEXT_ACTION=stall\n" in capsys.readouterr().out
    assert seed_calls
    assert "--stall-tracking" in seed_calls[0]
    assert (impl / "ship-pr-state.sh").is_file()


def test_commit_route_empty_state_uses_initial_seed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl, _invoke_calls, seed_calls = _setup_commit_route(
        tmp_path,
        monkeypatch,
        commit_stdout=_STEP5_COMMIT_FAILED,
        commit_rc=1,
    )
    (impl / "ship-pr-state.sh").write_text("", encoding="utf-8")

    rc = implement_dispatch.commit_route_main(["--site", "step7"])

    assert rc == 0
    assert "NEXT_ACTION=stall\n" in capsys.readouterr().out
    assert seed_calls


def test_commit_route_seed_failure_omits_next_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _impl, _invoke_calls, _seed_calls = _setup_commit_route(
        tmp_path,
        monkeypatch,
        commit_stdout=_STEP5_COMMIT_FAILED,
        commit_rc=1,
        seed_rc=1,
    )

    rc = implement_dispatch.commit_route_main(["--site", "step7"])

    assert rc != 0
    assert "NEXT_ACTION=" not in capsys.readouterr().out


def test_commit_route_malformed_state_omits_next_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl, _invoke_calls, seed_calls = _setup_commit_route(
        tmp_path,
        monkeypatch,
        commit_stdout=_STEP5_COMMIT_FAILED,
        commit_rc=1,
    )
    (impl / "ship-pr-state.sh").write_text("# not a shell kv\nmalformed\n", encoding="utf-8")

    rc = implement_dispatch.commit_route_main(["--site", "step7"])

    assert rc != 0
    assert not seed_calls
    assert "NEXT_ACTION=" not in capsys.readouterr().out


def test_commit_route_relay_helper_includes_next_action(capsys: pytest.CaptureFixture[str]) -> None:
    implement_dispatch._relay_commit_kvs("NEXT_ACTION=stall\nCOMMIT_OUTCOME=failed\nIGNORED=1\n")
    assert capsys.readouterr().out == "NEXT_ACTION=stall\nCOMMIT_OUTCOME=failed\n"


def test_checks_relay_uses_whitespace_parser_without_parse_kv(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_parse_kv(_text: str) -> dict[str, str]:
        raise AssertionError("line-oriented parse_kv must not parse checks relay")

    monkeypatch.setattr(implement_dispatch, "_parse_kv", fail_parse_kv)
    line = "STATUS=fail FAILURE_REASON=relevant-checks-failed EXIT_CODE=2 PHASE=checks REDACTED_LOG_FILE=/tmp/redacted.log trailing prose"

    values = implement_dispatch._parse_whitespace_kv_line(line)

    assert values == {
        "STATUS": "fail",
        "FAILURE_REASON": "relevant-checks-failed",
        "EXIT_CODE": "2",
        "PHASE": "checks",
        "REDACTED_LOG_FILE": "/tmp/redacted.log",
    }
    assert implement_dispatch._checks_relay_line(values) == (
        "STATUS=fail FAILURE_REASON=relevant-checks-failed EXIT_CODE=2 "
        "PHASE=checks REDACTED_LOG_FILE=/tmp/redacted.log"
    )


def test_checks_relay_formats_pass_and_skipped() -> None:
    assert implement_dispatch._checks_relay_line(
        {"RELEVANT_CHECKS_OK": "true", "SITE": "step6", "COVERAGE": "changed", "PHASE": "checks"}
    ) == "RELEVANT_CHECKS_OK=true SITE=step6 COVERAGE=changed PHASE=checks"
    assert implement_dispatch._checks_relay_line(
        {"RELEVANT_CHECKS_SKIPPED": "true", "SITE": "step5-self-review"}
    ) == "RELEVANT_CHECKS_SKIPPED=true SITE=step5-self-review"


def test_commit_route_child_envelope_omits_next_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _impl, _invoke_calls, _seed_calls = _setup_commit_route(tmp_path, monkeypatch, commit_stdout=_STEP5_COMMIT_OK)

    rc = implement_dispatch.commit_route_main(["--site", "step5-self-review", "--emit-next-action", "false"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "COMMIT_ROUTE_OUTCOME=continue\n" in out
    assert "COMMIT_OUTCOME=ok\n" in out
    assert "NEXT_ACTION=" not in out


def test_commit_route_child_envelope_distinguishes_seed_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _impl, _invoke_calls, _seed_calls = _setup_commit_route(
        tmp_path,
        monkeypatch,
        commit_stdout=_STEP5_COMMIT_FAILED,
        commit_rc=1,
        seed_rc=1,
    )

    rc = implement_dispatch.commit_route_main(["--site", "step7", "--emit-next-action", "false"])

    assert rc == 1
    out = capsys.readouterr().out
    assert "COMMIT_ROUTE_OUTCOME=seed-failed\n" in out
    assert "NEXT_ACTION=" not in out


def _mock_composite_continue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, commit_stdout: str = "COMMIT_ROUTE_OUTCOME=continue\nCOMMITTED=true\nCOMMIT_OUTCOME=ok\n") -> Path:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_relevant_checks_for_site",
        lambda **_kwargs: (
            {"RELEVANT_CHECKS_OK": "true", "SITE": "step6", "COVERAGE": "changed", "PHASE": "checks"},
            False,
        ),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_relevant_checks_for_site", lambda **_kwargs: (
            {"RELEVANT_CHECKS_OK": "true", "SITE": "step6", "COVERAGE": "changed", "PHASE": "checks"},
            False,
        ))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_commit_route_leg",
        lambda **_kwargs: ("continue", commit_stdout),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_commit_route_leg", lambda **_kwargs: ("continue", commit_stdout))
    return impl


def _completed(args: Sequence[str], stdout: str, stderr: str = "", rc: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(list(args), rc, stdout, stderr)


def _mock_step6_check_changes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    stdout: str,
    rc: int = 0,
    calls: list[list[str]] | None = None,
) -> None:
    def fake_capture(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if calls is not None:
            calls.append(list(args))
        return _completed(args, stdout, "check stderr\n", rc)

    monkeypatch.setattr(implement_dispatch, "_run_cli_capture", fake_capture)
    monkeypatch.setattr(dispatch_commit_route, "_run_cli_capture", fake_capture)


def test_step6_entry_skip_relays_degradation_kvs_and_does_not_run_composite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    _mock_step6_check_changes(
        monkeypatch,
        stdout="FILES_CHANGED=false\nUNTRACKED_BASELINE=missing\nGIT_PROBE_FAILED=true\n",
    )

    def fail_composite(_argv: list[str] | None = None) -> int:
        raise AssertionError("Step 6 composite must not run when FILES_CHANGED=false")

    monkeypatch.setattr(implement_dispatch, "checks_commit_route_main", fail_composite)
    monkeypatch.setattr(dispatch_commit_route, "checks_commit_route_main", fail_composite)

    rc = implement_dispatch.step6_entry_main([])

    captured = capsys.readouterr()
    assert rc == 0
    assert (impl / ".review-boundary-passed").is_file()
    assert captured.out == (
        "FILES_CHANGED=false\n"
        "UNTRACKED_BASELINE=missing\n"
        "GIT_PROBE_FAILED=true\n"
        "NEXT_ACTION=skip-to-7a\n"
    )
    assert captured.err == "check stderr\n"


def test_step6_entry_check_changes_uses_pinned_baselines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    calls: list[list[str]] = []
    _mock_step6_check_changes(
        monkeypatch,
        stdout="FILES_CHANGED=false\nUNTRACKED_BASELINE=present\nGIT_PROBE_FAILED=false\n",
        calls=calls,
    )

    assert implement_dispatch.step6_entry_main([]) == 0
    assert calls == [[
        "review-and-fix",
        "check-changes",
        "--baseline",
        str(impl / "pre-review-untracked.txt"),
        "--head-baseline",
        str(impl / "pre-review-head.txt"),
    ]]


def test_step6_entry_files_changed_runs_fixed_composite_with_forked_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    _mock_step6_check_changes(
        monkeypatch,
        stdout="FILES_CHANGED=true\nUNTRACKED_BASELINE=present\nGIT_PROBE_FAILED=false\n",
    )
    composite_calls: list[list[str] | None] = []

    def fake_composite(argv: list[str] | None = None) -> int:
        composite_calls.append(argv)
        print("CHECKPOINT_NEXT=continue")
        print("NEXT_ACTION=continue")
        return 0

    monkeypatch.setattr(implement_dispatch, "checks_commit_route_main", fake_composite)
    monkeypatch.setattr(dispatch_commit_route, "checks_commit_route_main", fake_composite)

    rc = implement_dispatch.step6_entry_main(["--forked-target", "true"])

    out = capsys.readouterr().out
    assert rc == 0
    assert out.startswith("FILES_CHANGED=true\nUNTRACKED_BASELINE=present\nGIT_PROBE_FAILED=false\n")
    assert "CHECKPOINT_NEXT=continue\nNEXT_ACTION=continue\n" in out
    assert out.count("NEXT_ACTION=") == 1
    assert composite_calls == [[
        "--checks-site",
        "step6",
        "--commit-site",
        "step7",
        "--emit-step7-breadcrumb",
        "--rebase-checkpoint-7r",
        "--forked-target",
        "true",
    ]]


def test_step6_entry_checks_failed_relay_keeps_redacted_log_after_leading_change_kvs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    _mock_step6_check_changes(
        monkeypatch,
        stdout="FILES_CHANGED=true\nUNTRACKED_BASELINE=present\nGIT_PROBE_FAILED=false\n",
    )

    def fake_composite(_argv: list[str] | None = None) -> int:
        print("STATUS=fail FAILURE_REASON=checks-failed REDACTED_LOG_FILE=/tmp/redacted.log")
        print("NEXT_ACTION=checks-failed")
        return 0

    monkeypatch.setattr(implement_dispatch, "checks_commit_route_main", fake_composite)
    monkeypatch.setattr(dispatch_commit_route, "checks_commit_route_main", fake_composite)

    rc = implement_dispatch.step6_entry_main([])

    lines = capsys.readouterr().out.splitlines()
    assert rc == 0
    assert lines[:3] == ["FILES_CHANGED=true", "UNTRACKED_BASELINE=present", "GIT_PROBE_FAILED=false"]
    assert lines[3] == "STATUS=fail FAILURE_REASON=checks-failed REDACTED_LOG_FILE=/tmp/redacted.log"
    assert "NEXT_ACTION=checks-failed" in lines
    assert any("REDACTED_LOG_FILE=/tmp/redacted.log" in line for line in lines)


@pytest.mark.parametrize(
    ("composite_stdout", "next_action"),
    [
        ("COMMIT_ROUTE_OUTCOME=seeded-stall\nNEXT_ACTION=stall\n", "stall"),
        ("CHECKPOINT_NEXT=load-routing\nREBASE_OUTCOME=conflict\nNEXT_ACTION=continue\n", "continue"),
    ],
)
def test_step6_entry_relays_composite_stall_and_rebase_routing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    composite_stdout: str,
    next_action: str,
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    _mock_step6_check_changes(
        monkeypatch,
        stdout="FILES_CHANGED=true\nUNTRACKED_BASELINE=present\nGIT_PROBE_FAILED=false\n",
    )

    def fake_composite(_argv: list[str] | None = None) -> int:
        sys.stdout.write(composite_stdout)
        return 0

    monkeypatch.setattr(implement_dispatch, "checks_commit_route_main", fake_composite)
    monkeypatch.setattr(dispatch_commit_route, "checks_commit_route_main", fake_composite)

    rc = implement_dispatch.step6_entry_main([])

    out = capsys.readouterr().out
    assert rc == 0
    assert f"NEXT_ACTION={next_action}\n" in out
    if next_action == "continue":
        assert out.index("CHECKPOINT_NEXT=load-routing") < out.index("NEXT_ACTION=continue")


@pytest.mark.parametrize("stdout", ["", "FILES_CHANGED=maybe\n", "FILES_CHANGED=true\nFILES_CHANGED=false\n"])
def test_step6_entry_malformed_files_changed_seeds_stall(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    stdout: str,
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    seed_calls: list[tuple[str, str]] = []
    _mock_step6_check_changes(monkeypatch, stdout=stdout)

    def fake_seed(_tmpdir: Path, *, stall_step: str, bail_reason: str) -> bool:
        seed_calls.append((stall_step, bail_reason))
        return True

    def fail_composite(_argv: list[str] | None = None) -> int:
        raise AssertionError("Step 6 composite must not run after malformed FILES_CHANGED")

    monkeypatch.setattr(implement_dispatch, "_seed_durable_stall_state", fake_seed)
    monkeypatch.setattr(dispatch_commit_route, "_seed_durable_stall_state", fake_seed)
    monkeypatch.setattr(implement_dispatch, "checks_commit_route_main", fail_composite)
    monkeypatch.setattr(dispatch_commit_route, "checks_commit_route_main", fail_composite)

    rc = implement_dispatch.step6_entry_main([])

    assert rc == 0
    assert "NEXT_ACTION=stall\n" in capsys.readouterr().out
    assert seed_calls == [("6", "review-change-detection-failed")]


def test_step6_entry_check_changes_nonzero_seed_failure_returns_nonzero_without_next_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    _mock_step6_check_changes(
        monkeypatch,
        stdout="FILES_CHANGED=true\nUNTRACKED_BASELINE=present\nGIT_PROBE_FAILED=false\n",
        rc=1,
    )
    monkeypatch.setattr(implement_dispatch, "_seed_durable_stall_state", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(dispatch_commit_route, "_seed_durable_stall_state", lambda *_args, **_kwargs: False)

    rc = implement_dispatch.step6_entry_main([])

    assert rc == 1
    assert "NEXT_ACTION=" not in capsys.readouterr().out


def test_step6_entry_composite_seed_failed_output_does_not_fabricate_next_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    _mock_step6_check_changes(
        monkeypatch,
        stdout="FILES_CHANGED=true\nUNTRACKED_BASELINE=present\nGIT_PROBE_FAILED=false\n",
    )

    def fake_composite(_argv: list[str] | None = None) -> int:
        print("COMMIT_ROUTE_OUTCOME=seed-failed")
        return 1

    monkeypatch.setattr(implement_dispatch, "checks_commit_route_main", fake_composite)
    monkeypatch.setattr(dispatch_commit_route, "checks_commit_route_main", fake_composite)

    rc = implement_dispatch.step6_entry_main([])

    out = capsys.readouterr().out
    assert rc == 1
    assert "COMMIT_ROUTE_OUTCOME=seed-failed\n" in out
    assert "NEXT_ACTION=continue" not in out
    assert "NEXT_ACTION=skip-to-7a" not in out


def test_step6_entry_force_checks_skips_change_gate_and_never_emits_skip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))

    def fail_check_changes(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("force-checks must bypass review-change detection")

    def fake_composite(_argv: list[str] | None = None) -> int:
        print("NEXT_ACTION=checks-failed")
        return 0

    monkeypatch.setattr(implement_dispatch, "_run_cli_capture", fail_check_changes)
    monkeypatch.setattr(dispatch_commit_route, "_run_cli_capture", fail_check_changes)
    monkeypatch.setattr(implement_dispatch, "checks_commit_route_main", fake_composite)
    monkeypatch.setattr(dispatch_commit_route, "checks_commit_route_main", fake_composite)

    rc = implement_dispatch.step6_entry_main(["--force-checks", "true"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "FILES_CHANGED=" not in out
    assert "NEXT_ACTION=skip-to-7a" not in out
    assert out == "NEXT_ACTION=checks-failed\n"


def test_run_relevant_checks_for_site_does_not_allow_skip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl = _session(tmp_path)
    calls: list[tuple[list[str], int, str]] = []

    def fake_run_leg(*, argv: Sequence[str], deadline_ms: int, label: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((list(argv), deadline_ms, label))
        return subprocess.CompletedProcess(
            list(argv),
            0,
            "RELEVANT_CHECKS_OK=true SITE=step6\n",
            "",
        )

    monkeypatch.setattr(implement_dispatch, "_run_leg_with_timeout", fake_run_leg)
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", fake_run_leg)

    captured, timed_out = implement_dispatch._run_relevant_checks_for_site(
        implement_tmpdir=impl,
        checks_site="step6",
        deadline_ms=1234,
    )

    assert not timed_out
    assert implement_dispatch._checks_pass(captured)
    assert captured == {"RELEVANT_CHECKS_OK": "true", "SITE": "step6"}
    assert calls == [
        (
            ["checks", "run-relevant", "--site", "step6", "--tmpdir", str(impl)],
            1234,
            "checks_run_relevant_main:step6",
        )
    ]


def test_checks_commit_route_ok_envelope_continues_through_real_helper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    checks_calls: list[list[str]] = []
    commit_calls: list[str] = []

    def fake_run_leg(*, argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        checks_calls.append(list(argv))
        return subprocess.CompletedProcess(
            list(argv),
            0,
            "RELEVANT_CHECKS_OK=true SITE=step5-self-review\n",
            "",
        )

    def fake_commit(*, site_name: str, **_kwargs: object) -> tuple[implement_dispatch.CommitRouteOutcome, str]:
        commit_calls.append(site_name)
        return "continue", "COMMIT_ROUTE_OUTCOME=continue\nCOMMITTED=true\nCOMMIT_OUTCOME=ok\n"

    def fail_checkpoint(_forked_target: str) -> int:
        raise AssertionError("7.r checkpoint must not run without the explicit Step 6 flag")

    monkeypatch.setattr(implement_dispatch, "_run_leg_with_timeout", fake_run_leg)
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", fake_run_leg)
    monkeypatch.setattr(implement_dispatch, "_run_commit_route_leg", fake_commit)
    monkeypatch.setattr(dispatch_commit_route, "_run_commit_route_leg", fake_commit)
    monkeypatch.setattr(implement_dispatch, "_run_7r_rebase_checkpoint", fail_checkpoint)
    monkeypatch.setattr(dispatch_commit_route, "_run_7r_rebase_checkpoint", fail_checkpoint)

    rc = implement_dispatch.checks_commit_route_main(
        ["--checks-site", "step5-self-review", "--commit-site", "step5-self-review"]
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert checks_calls == [
        ["checks", "run-relevant", "--site", "step5-self-review", "--tmpdir", str(impl)]
    ]
    assert commit_calls == ["step5-self-review"]
    assert "RELEVANT_CHECKS_OK=true SITE=step5-self-review" in out
    assert "NEXT_ACTION=checks-failed" not in out
    assert [line for line in out.splitlines() if line == "NEXT_ACTION=continue"] == ["NEXT_ACTION=continue"]


def test_checks_step5_resume_ok_envelope_runs_resume_without_continue_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    checks_calls: list[list[str]] = []
    resume_calls: list[tuple[str, int]] = []

    def fake_run_leg(*, argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        checks_calls.append(list(argv))
        return subprocess.CompletedProcess(
            list(argv),
            0,
            "RELEVANT_CHECKS_OK=true SITE=step5-review-fixes\n",
            "",
        )

    def fake_resume(*, final_round_num: str, deadline_ms: int, **_kwargs: object) -> tuple[int, str]:
        resume_calls.append((final_round_num, deadline_ms))
        return 0, "STEP5_REVIEW_STATUS=complete\n"

    monkeypatch.setattr(implement_dispatch, "_run_leg_with_timeout", fake_run_leg)
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", fake_run_leg)
    monkeypatch.setattr(implement_dispatch, "_run_step5_resume_leg", fake_resume)
    monkeypatch.setattr(dispatch_commit_route, "_run_step5_resume_leg", fake_resume)

    rc = implement_dispatch.checks_step5_resume_main(
        ["--checks-site", "step5-review-fixes", "--final-round-num", "3", "--resume-deadline-ms", "5678"]
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert checks_calls == [
        ["checks", "run-relevant", "--site", "step5-review-fixes", "--tmpdir", str(impl)]
    ]
    assert resume_calls == [("3", 5678)]
    assert "RELEVANT_CHECKS_OK=true SITE=step5-review-fixes" in out
    assert "STEP5_REVIEW_STATUS=complete\n" in out
    assert "NEXT_ACTION=checks-failed" not in out
    assert "NEXT_ACTION=continue" not in out


def test_composite_outer_timeout_budgets_match_leg_sums_and_fences() -> None:
    assert implement_dispatch.CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS == (
        implement_dispatch._CHECKS_DEADLINE_MS
        + implement_dispatch._COMMIT_ROUTE_DEADLINE_MS
        + implement_dispatch._REBASE_CHECKPOINT_DEADLINE_MS
        + implement_dispatch._COMPOSITE_OUTER_SLACK_MS
    )
    assert implement_dispatch.CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS == 15_600_000
    assert implement_dispatch.CHECKS_STEP5_RESUME_OUTER_TIMEOUT_MS == (
        implement_dispatch._CHECKS_DEADLINE_MS
        + implement_dispatch._STEP5_RESUME_DEADLINE_MS
        + implement_dispatch._COMPOSITE_OUTER_SLACK_MS
    )
    assert implement_dispatch.CHECKS_STEP5_RESUME_OUTER_TIMEOUT_MS == 32_700_000

    root = Path(__file__).resolve().parents[1]
    structure = (root / "scripts" / "test-implement-structure.sh").read_text(encoding="utf-8")
    skill = (root / "skills" / "implement" / "SKILL.md").read_text(encoding="utf-8")
    self_review_ref = (root / "skills" / "implement" / "references" / "self-review.md").read_text(
        encoding="utf-8"
    )
    step6_launcher = "skills/implement/scripts/step-6-entry.sh"
    assert (
        f"(launcher + '{step6_launcher}', 'timeout: {implement_dispatch.CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS}')"
        in structure
    )
    assert "require_near('skills/implement/references/self-review.md', self_review_composite" in structure
    assert "python/cli.py implement checks-commit-route --checks-site step5-self-review', 'timeout: 14700000'" not in structure
    assert f"timeout: {implement_dispatch.CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS}" in skill
    assert "checks-commit-route --checks-site step5-self-review" not in skill
    assert "timeout: 14700000" not in skill
    assert "checks-commit-route --checks-site step5-self-review" in self_review_ref
    assert "timeout: 14700000" in self_review_ref


def test_7r_rebase_checkpoint_invokes_cli_and_relays_stdout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[list[str]] = []

    def fake_invoke(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(args))
        return subprocess.CompletedProcess(
            list(args),
            1,
            "\nCHECKPOINT_NEXT=load-routing\n\nREBASE_OUTCOME=conflict\nCONFLICT_FILES=a.py,b.py\n",
            "probe warning\n",
        )

    monkeypatch.setattr(implement_dispatch, "_invoke_cli", fake_invoke)
    monkeypatch.setattr(dispatch_commit_route, "_invoke_cli", fake_invoke)

    rc = implement_dispatch._run_7r_rebase_checkpoint("true")

    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out == "CHECKPOINT_NEXT=load-routing\nREBASE_OUTCOME=conflict\nCONFLICT_FILES=a.py,b.py\n"
    assert captured.err == "probe warning\n"
    assert calls == [["push", "checkpoint-probe", "7.r", "commit (review)", "--forked-target", "true"]]


@pytest.mark.parametrize(
    ("probe_rc", "forked_target", "probe_outcome"),
    [(0, "false", "ok"), (1, "true", "conflict")],
)
def test_composite_rebase_checkpoint_relays_probe_and_returns_probe_rc(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    probe_rc: int,
    forked_target: str,
    probe_outcome: str,
) -> None:
    _mock_composite_continue(tmp_path, monkeypatch)
    checkpoint_calls: list[str] = []

    def fake_checkpoint(value: str) -> int:
        checkpoint_calls.append(value)
        print(f"CHECKPOINT_NEXT={'continue' if probe_rc == 0 else 'load-routing'}")
        print(f"REBASE_OUTCOME={probe_outcome}")
        if probe_rc == 1:
            print("CONFLICT_FILES=changed.py")
        return probe_rc

    monkeypatch.setattr(implement_dispatch, "_run_7r_rebase_checkpoint", fake_checkpoint)
    monkeypatch.setattr(dispatch_commit_route, "_run_7r_rebase_checkpoint", fake_checkpoint)

    rc = implement_dispatch.checks_commit_route_main(
        [
            "--checks-site",
            "step6",
            "--commit-site",
            "step7",
            "--rebase-checkpoint-7r",
            "--forked-target",
            forked_target,
        ]
    )

    out = capsys.readouterr().out
    assert rc == probe_rc
    assert checkpoint_calls == [forked_target]
    assert "RELEVANT_CHECKS_OK=true SITE=step6 COVERAGE=changed PHASE=checks\n" in out
    assert f"REBASE_OUTCOME={probe_outcome}\n" in out
    assert "NEXT_ACTION=continue\n" in out
    assert out.count("NEXT_ACTION=") == 1
    assert out.index(f"REBASE_OUTCOME={probe_outcome}") < out.index("NEXT_ACTION=continue")


def test_composite_without_rebase_flag_preserves_step5_self_review_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_composite_continue(tmp_path, monkeypatch)

    def fail_checkpoint(_forked_target: str) -> int:
        raise AssertionError("7.r checkpoint must not run without the explicit Step 6 flag")

    monkeypatch.setattr(implement_dispatch, "_run_7r_rebase_checkpoint", fail_checkpoint)
    monkeypatch.setattr(dispatch_commit_route, "_run_7r_rebase_checkpoint", fail_checkpoint)

    rc = implement_dispatch.checks_commit_route_main(
        ["--checks-site", "step5-self-review", "--commit-site", "step5-self-review"]
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "NEXT_ACTION=continue\n" in out
    assert "CHECKPOINT_NEXT=" not in out


def test_composite_rebase_checkpoint_skips_checks_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_relevant_checks_for_site",
        lambda **_kwargs: ({"STATUS": "fail", "FAILURE_REASON": "relevant-checks-failed"}, False),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_relevant_checks_for_site", lambda **_kwargs: ({"STATUS": "fail", "FAILURE_REASON": "relevant-checks-failed"}, False))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_commit_route_leg",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("commit must not run after checks failure")),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_commit_route_leg", lambda **_kwargs: (_ for _ in ()).throw(AssertionError("commit must not run after checks failure")))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_7r_rebase_checkpoint",
        lambda _forked_target: (_ for _ in ()).throw(AssertionError("7.r checkpoint must not run after checks failure")),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_7r_rebase_checkpoint", lambda _forked_target: (_ for _ in ()).throw(AssertionError("7.r checkpoint must not run after checks failure")))

    rc = implement_dispatch.checks_commit_route_main(
        ["--checks-site", "step6", "--commit-site", "step7", "--rebase-checkpoint-7r"]
    )

    assert rc == 0
    assert capsys.readouterr().out == "STATUS=fail FAILURE_REASON=relevant-checks-failed\nNEXT_ACTION=checks-failed\n"


def test_composite_rebase_checkpoint_skips_seeded_stall(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_composite_continue(tmp_path, monkeypatch, commit_stdout="COMMIT_ROUTE_OUTCOME=seeded-stall\nCOMMIT_OUTCOME=failed\n")
    monkeypatch.setattr(
        implement_dispatch,
        "_run_commit_route_leg",
        lambda **_kwargs: ("seeded-stall", "COMMIT_ROUTE_OUTCOME=seeded-stall\nCOMMIT_OUTCOME=failed\n"),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_commit_route_leg", lambda **_kwargs: ("seeded-stall", "COMMIT_ROUTE_OUTCOME=seeded-stall\nCOMMIT_OUTCOME=failed\n"))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_7r_rebase_checkpoint",
        lambda _forked_target: (_ for _ in ()).throw(AssertionError("7.r checkpoint must not run after seeded stall")),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_7r_rebase_checkpoint", lambda _forked_target: (_ for _ in ()).throw(AssertionError("7.r checkpoint must not run after seeded stall")))

    rc = implement_dispatch.checks_commit_route_main(
        ["--checks-site", "step6", "--commit-site", "step7", "--rebase-checkpoint-7r"]
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "NEXT_ACTION=stall\n" in out
    assert "CHECKPOINT_NEXT=" not in out


def test_step4_composite_noop_runs_4r_and_does_not_double_emit_continue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_relevant_checks_for_site",
        lambda **_kwargs: (
            {"RELEVANT_CHECKS_OK": "true", "SITE": "step3", "COVERAGE": "changed", "PHASE": "checks"},
            False,
        ),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_relevant_checks_for_site", lambda **_kwargs: (
            {"RELEVANT_CHECKS_OK": "true", "SITE": "step3", "COVERAGE": "changed", "PHASE": "checks"},
            False,
        ))
    monkeypatch.setattr(implement_dispatch, "_resolve_repo_root", lambda: Path("/repo"))
    monkeypatch.setattr(dispatch_commit_route, "_resolve_repo_root", lambda: Path("/repo"))
    monkeypatch.setattr(implement_dispatch, "_run_step4_recovery_recompute", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(dispatch_commit_route, "_run_step4_recovery_recompute", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(
        implement_dispatch,
        "_run_step4_commit_leg",
        lambda *_args, **_kwargs: ("noop", "COMMIT_ROUTE_OUTCOME=noop\n"),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_step4_commit_leg", lambda *_args, **_kwargs: ("noop", "COMMIT_ROUTE_OUTCOME=noop\n"))

    def fake_4r(forked_target: str) -> int:
        assert forked_target == "true"
        print("CHECKPOINT_NEXT=continue")
        print("REBASE_OUTCOME=ok")
        print("NEXT_ACTION=continue")
        return 0

    monkeypatch.setattr(implement_dispatch, "_run_4r_rebase_checkpoint", fake_4r)
    monkeypatch.setattr(dispatch_commit_route, "_run_4r_rebase_checkpoint", fake_4r)

    rc = implement_dispatch.checks_commit_route_main([
        "--checks-site",
        "step3",
        "--commit-site",
        "step4",
        "--rebase-checkpoint-4r",
        "--forked-target",
        "true",
    ])

    out = capsys.readouterr().out
    assert rc == 0
    assert "RELEVANT_CHECKS_OK=true SITE=step3 COVERAGE=changed PHASE=checks\n" in out
    assert "COMMIT_ROUTE_OUTCOME=noop\n" in out
    assert out.count("NEXT_ACTION=continue") == 1


def test_step4_composite_seeded_stall_skips_4r(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_relevant_checks_for_site",
        lambda **_kwargs: ({"RELEVANT_CHECKS_OK": "true", "SITE": "step3"}, False),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_relevant_checks_for_site", lambda **_kwargs: ({"RELEVANT_CHECKS_OK": "true", "SITE": "step3"}, False))
    monkeypatch.setattr(implement_dispatch, "_resolve_repo_root", lambda: Path("/repo"))
    monkeypatch.setattr(dispatch_commit_route, "_resolve_repo_root", lambda: Path("/repo"))
    monkeypatch.setattr(implement_dispatch, "_run_step4_recovery_recompute", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(dispatch_commit_route, "_run_step4_recovery_recompute", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(
        implement_dispatch,
        "_run_step4_commit_leg",
        lambda *_args, **_kwargs: ("seeded-stall", "COMMIT_ROUTE_OUTCOME=seeded-stall\n"),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_step4_commit_leg", lambda *_args, **_kwargs: ("seeded-stall", "COMMIT_ROUTE_OUTCOME=seeded-stall\n"))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_4r_rebase_checkpoint",
        lambda _forked_target: (_ for _ in ()).throw(AssertionError("4.r must not run after seeded stall")),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_4r_rebase_checkpoint", lambda _forked_target: (_ for _ in ()).throw(AssertionError("4.r must not run after seeded stall")))

    rc = implement_dispatch.checks_commit_route_main([
        "--checks-site",
        "step3",
        "--commit-site",
        "step4",
        "--rebase-checkpoint-4r",
    ])

    assert rc == 0
    assert "NEXT_ACTION=stall\n" in capsys.readouterr().out


def test_run_step4_commit_leg_commits_ordinary_pathspec(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl = _session(tmp_path)
    (impl / "implementation-commit-message.txt").write_text("Implement thing\n", encoding="utf-8")
    (impl / "implementation-commit-paths.nul").write_bytes(b"file.txt\0")
    calls: list[list[str]] = []

    def fake_run_leg(*, argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 0, "COMMITTED=true\nSHA=abc\n", "")

    monkeypatch.setattr(implement_dispatch, "_run_leg_with_timeout", fake_run_leg)
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", fake_run_leg)

    outcome, stdout = implement_dispatch._run_step4_commit_leg(impl, deadline_ms=123)

    assert outcome == "continue"
    assert "COMMIT_ROUTE_OUTCOME=continue\n" in stdout
    assert calls == [[
        "implement",
        "commit",
        "--message",
        "Implement thing",
        "--pathspec-from-file",
        str(impl / "implementation-commit-paths.nul"),
        "--pathspec-file-nul",
    ]]


def test_run_step4_commit_leg_failure_seeds_step4_stall(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl = _session(tmp_path)
    (impl / "implementation-commit-message.txt").write_text("Implement thing\n", encoding="utf-8")
    (impl / "implementation-commit-paths.nul").write_bytes(b"file.txt\0")
    seed_calls: list[tuple[str, str]] = []

    monkeypatch.setattr(
        implement_dispatch,
        "_run_leg_with_timeout",
        lambda **_kwargs: subprocess.CompletedProcess([], 1, "COMMITTED=false\nERROR=failed\n", ""),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", lambda **_kwargs: subprocess.CompletedProcess([], 1, "COMMITTED=false\nERROR=failed\n", ""))
    monkeypatch.setattr(
        implement_dispatch,
        "_invoke_cli",
        lambda args, **_kwargs: subprocess.CompletedProcess(list(args), 0, "", ""),
    )
    monkeypatch.setattr(dispatch_commit_route, "_invoke_cli", lambda args, **_kwargs: subprocess.CompletedProcess(list(args), 0, "", ""))

    def fake_seed(_tmpdir: Path, *, stall_step: str, bail_reason: str) -> bool:
        seed_calls.append((stall_step, bail_reason))
        return True

    monkeypatch.setattr(implement_dispatch, "_seed_durable_stall_state", fake_seed)
    monkeypatch.setattr(dispatch_commit_route, "_seed_durable_stall_state", fake_seed)

    outcome, stdout = implement_dispatch._run_step4_commit_leg(impl, deadline_ms=123)

    assert outcome == "seeded-stall"
    assert "COMMIT_ROUTE_OUTCOME=seeded-stall\n" in stdout
    assert seed_calls == [("4", "implementation-commit-failed")]


def test_persist_ship_seed_context_refreshes_blank_manifest_path(tmp_path: Path) -> None:
    impl = _session(tmp_path)
    (impl / "ship-seed-input.env").write_text("MANIFEST_PATH=\nTOOL_LABEL=\n", encoding="utf-8")
    (impl / "manifest.json").write_text('{"schema_version":"1"}\n', encoding="utf-8")
    (impl / "bootstrap-routing.env").write_text("coder=codex\n", encoding="utf-8")

    implement_dispatch._persist_ship_seed_context(impl)

    seed = (impl / "ship-seed-input.env").read_text(encoding="utf-8")
    assert f"MANIFEST_PATH={impl / 'manifest.json'}" in seed
    assert "TOOL_LABEL=Codex" in seed


def test_run_step4_commit_leg_noop_emits_dispatcher_committed_breadcrumb(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = _session(tmp_path)
    manifest = impl / "manifest.json"
    manifest.write_text('{"schema_version":"1"}\n', encoding="utf-8")
    (impl / "ship-seed-input.env").write_text(
        f"MANIFEST_PATH={manifest}\nDISPATCHER_COMMITTED=true\n",
        encoding="utf-8",
    )

    outcome, stdout = implement_dispatch._run_step4_commit_leg(impl, deadline_ms=123)

    captured = capsys.readouterr()
    assert outcome == "noop"
    assert "COMMIT_ROUTE_OUTCOME=noop\n" in stdout
    assert "dispatcher-committed" in captured.out


def test_run_step4_commit_leg_recovery_branch_uses_recovery_pathspec(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl = _session(tmp_path)
    (impl / "recovery-metadata.json").write_text("{}\n", encoding="utf-8")
    (impl / "recovery-commit-message.txt").write_text("Recover implementation\n", encoding="utf-8")
    (impl / "step2-recovery-paths-final.nul").write_bytes(b"recovered.txt\0")
    calls: list[list[str]] = []

    def fake_run_leg(*, argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 0, "COMMITTED=true\nSHA=abc\n", "")

    monkeypatch.setattr(implement_dispatch, "_run_leg_with_timeout", fake_run_leg)
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", fake_run_leg)

    outcome, stdout = implement_dispatch._run_step4_commit_leg(impl, deadline_ms=123)

    assert outcome == "continue"
    assert "COMMIT_ROUTE_OUTCOME=continue\n" in stdout
    assert calls == [[
        "implement",
        "commit",
        "--message",
        "Recover implementation",
        "--pathspec-from-file",
        str(impl / "step2-recovery-paths-final.nul"),
        "--pathspec-file-nul",
    ]]


def test_run_step4_commit_leg_recovery_metadata_missing_message_seed_fails(
    tmp_path: Path,
) -> None:
    impl = _session(tmp_path)
    (impl / "recovery-metadata.json").write_text("{}\n", encoding="utf-8")
    (impl / "implementation-commit-message.txt").write_text("Ordinary\n", encoding="utf-8")
    (impl / "implementation-commit-paths.nul").write_bytes(b"file.txt\0")

    outcome, stdout = implement_dispatch._run_step4_commit_leg(impl, deadline_ms=123)

    assert outcome == "seed-failed"
    assert stdout == "COMMIT_ROUTE_OUTCOME=seed-failed\n"


def test_run_step4_recovery_recompute_scope_check_failure_emits_bail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = _session(tmp_path)
    (impl / "recovery-metadata.json").write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(implement_dispatch, "_derive_pathspec_via_recovery_paths", lambda **_kwargs: 0)
    monkeypatch.setattr(dispatch_commit_route, "_derive_pathspec_via_recovery_paths", lambda **_kwargs: 0)
    monkeypatch.setattr(
        implement_dispatch,
        "_invoke_cli",
        lambda args, **_kwargs: subprocess.CompletedProcess(list(args), 1, "", "scope fail"),
    )
    monkeypatch.setattr(dispatch_commit_route, "_invoke_cli", lambda args, **_kwargs: subprocess.CompletedProcess(list(args), 1, "", "scope fail"))

    rc = implement_dispatch._run_step4_recovery_recompute(impl, repo_root=Path("/repo"))

    out = capsys.readouterr()
    assert rc == 1
    assert "BAIL_REASON=recovery-out-of-scope\n" in out.out
    assert "NEXT_ACTION=" not in out.out


def test_step4_composite_recovery_out_of_scope_emits_bail_without_next_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    (impl / "recovery-metadata.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        implement_dispatch,
        "_run_relevant_checks_for_site",
        lambda **_kwargs: ({"RELEVANT_CHECKS_OK": "true", "SITE": "step3"}, False),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_relevant_checks_for_site", lambda **_kwargs: ({"RELEVANT_CHECKS_OK": "true", "SITE": "step3"}, False))
    monkeypatch.setattr(implement_dispatch, "_resolve_repo_root", lambda: Path("/repo"))
    monkeypatch.setattr(dispatch_commit_route, "_resolve_repo_root", lambda: Path("/repo"))
    monkeypatch.setattr(implement_dispatch, "_derive_pathspec_via_recovery_paths", lambda **_kwargs: 0)
    monkeypatch.setattr(dispatch_commit_route, "_derive_pathspec_via_recovery_paths", lambda **_kwargs: 0)
    monkeypatch.setattr(
        implement_dispatch,
        "_invoke_cli",
        lambda args, **_kwargs: subprocess.CompletedProcess(list(args), 1, "", "scope fail"),
    )
    monkeypatch.setattr(dispatch_commit_route, "_invoke_cli", lambda args, **_kwargs: subprocess.CompletedProcess(list(args), 1, "", "scope fail"))

    rc = implement_dispatch.checks_commit_route_main([
        "--checks-site",
        "step3",
        "--commit-site",
        "step4",
    ])

    out = capsys.readouterr().out
    assert rc == 1
    assert "BAIL_REASON=recovery-out-of-scope\n" in out
    assert "NEXT_ACTION=" not in out


def test_run_dispatch_skips_telemetry_marker_on_timing_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp = _session(tmp_path)
    token_calls: list[list[str]] = []
    timing_calls: list[list[str]] = []

    def fake_run(argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        call = list(argv)
        if call[-3:] == ["token", "mark", "Step 2 — implementation"]:
            token_calls.append(call)
            return subprocess.CompletedProcess(call, 0, "", "")
        if call[-3:] == ["timing", "mark", "Step 2 — implementation"]:
            timing_calls.append(call)
            return subprocess.CompletedProcess(call, 1, "", "timing failed")
        if len(call) >= 4 and call[2:4] == ["implement", "step2-dispatch"]:
            return subprocess.CompletedProcess(call, 0, "STATUS=complete\n", "")
        return subprocess.CompletedProcess(call, 0, "", "")

    monkeypatch.setattr(implement_dispatch.subprocess, "run", fake_run)

    rc = implement_dispatch.run_dispatch_main(["--implement-tmpdir", str(tmp), "--coder", "claude"])

    assert rc == 0
    assert len(token_calls) == 1
    assert len(timing_calls) == 1
    assert not (tmp / ".step2-telemetry-marked").is_file()


def test_run_dispatch_retries_step2_telemetry_after_bailed_first_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp = _session(tmp_path)
    (tmp / "session-env.sh").write_text(
        "CODEX_BINARY_FOUND=false\nLARCH_CLAUDE_PLUGIN_ROOT=.\n",
        encoding="utf-8",
    )
    dispatch_calls = 0
    token_calls: list[list[str]] = []
    timing_calls: list[list[str]] = []

    def fake_run(argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal dispatch_calls
        call = list(argv)
        if call[-3:] == ["token", "mark", "Step 2 — implementation"]:
            token_calls.append(call)
            return subprocess.CompletedProcess(call, 0, "", "")
        if call[-3:] == ["timing", "mark", "Step 2 — implementation"]:
            timing_calls.append(call)
            return subprocess.CompletedProcess(call, 0, "", "")
        if len(call) >= 4 and call[2:4] == ["implement", "step2-dispatch"]:
            dispatch_calls += 1
            if dispatch_calls == 1:
                return subprocess.CompletedProcess(call, 1, "STATUS=bailed\n", "")
            return subprocess.CompletedProcess(call, 0, "STATUS=complete\n", "")
        return subprocess.CompletedProcess(call, 0, "", "")

    monkeypatch.setattr(implement_dispatch.subprocess, "run", fake_run)

    assert implement_dispatch.run_dispatch_main(["--implement-tmpdir", str(tmp), "--coder", "codex"]) == 1
    assert implement_dispatch.run_dispatch_main(["--implement-tmpdir", str(tmp), "--coder", "codex"]) == 0

    assert len(token_calls) == 1
    assert len(timing_calls) == 1
    assert (tmp / ".step2-telemetry-marked").is_file()


@pytest.mark.parametrize(
    ("launcher", "tool"),
    [
        (agents.launch_codex_implement_main, "codex"),
        (agents.launch_cursor_implement_main, "cursor"),
    ],
)
def test_implement_launchers_do_not_emit_step2_token_mark(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    launcher: Callable[[list[str]], int],
    tool: str,
) -> None:
    launcher_source = inspect.getsource(launcher)
    assert '["token", "mark", "Step 2 — implementation"]' not in launcher_source
    assert '"Step 2 — implementation"' not in launcher_source

    args = _launcher_args(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setattr(agents.shutil, "which", lambda name: f"/usr/bin/{name}" if name in {"codex", "cursor"} else "/bin/true")
    monkeypatch.setattr(agents, "_implement_token_budget_hit", lambda **_kwargs: False)
    monkeypatch.setattr(agents, "_record_implement_timing", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "_record_usage_from_events", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "_mirror_codex_quota_from_events", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "_record_cursor_implement_usage", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "_promote_inner_done", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "cursor_auth_preflight", lambda **_kwargs: agents.AuthVerdict(ok=True, rc=0, message=""))
    monkeypatch.setattr(agents, "cursor_preread_service_token", lambda: True)
    monkeypatch.setattr(agents, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(agents, "_resolve_review_codex_workdir", lambda _cwd: str(tmp_path))
    proc_calls: list[list[str]] = []
    original_proc_run = agents.proc.run

    def spy_proc_run(argv: Sequence[str], **kwargs: object) -> CommandResult:
        proc_calls.append(list(argv))
        if list(argv)[-3:] == ["token", "mark", "Step 2 — implementation"]:
            raise AssertionError(f"launcher must not emit Step 2 token mark: {tool}")
        return original_proc_run(argv, **cast("Any", kwargs))

    monkeypatch.setattr(agents.proc, "run", spy_proc_run)

    def fake_run_external_agent_with_auth_retries(**kwargs: object) -> agents.RunExternalAgentResult:
        output = cast("Path", kwargs["output"])
        output.write_text('{"usage":{"inputTokens":1}}\n', encoding="utf-8")
        return agents.RunExternalAgentResult(0, output)

    monkeypatch.setattr(agents, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)

    rc = launcher(args)

    assert rc == 0
    assert not any(call[-3:] == ["token", "mark", "Step 2 — implementation"] for call in proc_calls)


def test_step2_dispatch_main_answers_redispatch_no_timing_mark(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))
    answers = tmp / "answers.json"
    answers.write_text('{"answers":[{"id":"q1","text":"yes"}]}\n', encoding="utf-8")
    timing_calls: list[list[str]] = []
    original_run = subprocess.run

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        cmd = cast("Sequence[str]", args[0] if args else kwargs.get("args", []))
        if list(cmd)[-3:] == ["timing", "mark", "Step 2 — implementation"]:
            timing_calls.append(list(cmd))
        if any("launch-codex-implement" in str(part) for part in cmd):
            return subprocess.CompletedProcess(list(cmd), 0, "STATUS=complete\n", "")
        return original_run(*args, **kwargs)  # pylint: disable=subprocess-run-check

    monkeypatch.setattr(subprocess, "run", fake_run)

    def fake_launcher(st: implement_dispatch.DispatchState) -> tuple[int, dict[str, str], str]:
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text('{"schema_version":"1","status":"complete"}\n', encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(dispatch_step2, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    monkeypatch.setattr(dispatch_step2, "_materialize_oos", lambda *_a, **_k: "")

    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
        "--answers", str(answers),
    ])

    assert rc == 0
    assert not timing_calls


def test_composite_commit_route_spawns_child_with_emit_next_action_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    calls: list[list[str]] = []

    def fake_run_leg(*, argv: Sequence[str], deadline_ms: int, label: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        assert deadline_ms == 1234
        assert label == "commit-route:step7"
        return subprocess.CompletedProcess(
            list(argv),
            0,
            "COMMIT_ROUTE_OUTCOME=continue\nCOMMITTED=true\nCOMMIT_OUTCOME=ok\n",
            "",
        )

    monkeypatch.setattr(
        implement_dispatch,
        "_run_relevant_checks_for_site",
        lambda **_kwargs: (
            {"RELEVANT_CHECKS_OK": "true", "SITE": "step6", "COVERAGE": "changed", "PHASE": "checks"},
            False,
        ),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_relevant_checks_for_site", lambda **_kwargs: (
            {"RELEVANT_CHECKS_OK": "true", "SITE": "step6", "COVERAGE": "changed", "PHASE": "checks"},
            False,
        ))
    monkeypatch.setattr(implement_dispatch, "_run_leg_with_timeout", fake_run_leg)
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", fake_run_leg)

    rc = implement_dispatch.checks_commit_route_main(
        ["--checks-site", "step6", "--commit-site", "step7", "--commit-deadline-ms", "1234"]
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "RELEVANT_CHECKS_OK=true SITE=step6 COVERAGE=changed PHASE=checks\n" in out
    assert "NEXT_ACTION=continue\n" in out
    assert calls == [
        [
            "implement",
            "commit-route",
            "--site",
            "step7",
            "--implement-tmpdir",
            str(impl),
            "--emit-next-action",
            "false",
        ]
    ]


def test_composite_checks_timeout_with_partial_pass_skips_commit_leg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_leg_with_timeout",
        lambda **_kwargs: subprocess.TimeoutExpired(
            cmd=["checks", "run-relevant"],
            timeout=1,
            output="RELEVANT_CHECKS_OK=true SITE=step6 COVERAGE=changed PHASE=checks\n",
            stderr="timeout",
        ),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", lambda **_kwargs: subprocess.TimeoutExpired(
            cmd=["checks", "run-relevant"],
            timeout=1,
            output="RELEVANT_CHECKS_OK=true SITE=step6 COVERAGE=changed PHASE=checks\n",
            stderr="timeout",
        ))

    def fail_commit(**_kwargs: object) -> tuple[implement_dispatch.CommitRouteOutcome, str]:
        raise AssertionError("commit leg must not start after checks-leg timeout")

    monkeypatch.setattr(implement_dispatch, "_run_commit_route_leg", fail_commit)
    monkeypatch.setattr(dispatch_commit_route, "_run_commit_route_leg", fail_commit)

    rc = implement_dispatch.checks_commit_route_main(["--checks-site", "step6", "--commit-site", "step7"])

    assert rc == 0
    assert capsys.readouterr().out == "STATUS=fail FAILURE_REASON=checks-leg-timeout\nNEXT_ACTION=checks-failed\n"


def test_composite_checks_timeout_with_partial_pass_skips_resume_leg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_leg_with_timeout",
        lambda **_kwargs: subprocess.TimeoutExpired(
            cmd=["checks", "run-relevant"],
            timeout=1,
            output="RELEVANT_CHECKS_OK=true SITE=step5-review-fixes COVERAGE=changed PHASE=review\n",
            stderr="timeout",
        ),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", lambda **_kwargs: subprocess.TimeoutExpired(
            cmd=["checks", "run-relevant"],
            timeout=1,
            output="RELEVANT_CHECKS_OK=true SITE=step5-review-fixes COVERAGE=changed PHASE=review\n",
            stderr="timeout",
        ))

    def fail_resume(**_kwargs: object) -> tuple[int, str]:
        raise AssertionError("resume leg must not start after checks-leg timeout")

    monkeypatch.setattr(implement_dispatch, "_run_step5_resume_leg", fail_resume)
    monkeypatch.setattr(dispatch_commit_route, "_run_step5_resume_leg", fail_resume)

    rc = implement_dispatch.checks_step5_resume_main(
        ["--checks-site", "step5-review-fixes", "--final-round-num", "3"]
    )

    assert rc == 0
    assert capsys.readouterr().out == "STATUS=fail FAILURE_REASON=checks-leg-timeout\nNEXT_ACTION=checks-failed\n"


def test_composite_checks_failure_skips_commit_leg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_relevant_checks_for_site",
        lambda **_kwargs: ({"STATUS": "fail", "FAILURE_REASON": "checks-leg-timeout"}, True),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_relevant_checks_for_site", lambda **_kwargs: ({"STATUS": "fail", "FAILURE_REASON": "checks-leg-timeout"}, True))

    def fail_commit(**_kwargs: object) -> tuple[implement_dispatch.CommitRouteOutcome, str]:
        raise AssertionError("commit leg must not start after checks failure")

    monkeypatch.setattr(implement_dispatch, "_run_commit_route_leg", fail_commit)
    monkeypatch.setattr(dispatch_commit_route, "_run_commit_route_leg", fail_commit)

    rc = implement_dispatch.checks_commit_route_main(["--checks-site", "step6", "--commit-site", "step7"])

    assert rc == 0
    assert capsys.readouterr().out == "STATUS=fail FAILURE_REASON=checks-leg-timeout\nNEXT_ACTION=checks-failed\n"


def test_commit_leg_timeout_seeds_stall_in_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl = _session(tmp_path)
    seed_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        implement_dispatch,
        "_run_leg_with_timeout",
        lambda **_kwargs: subprocess.TimeoutExpired(cmd=["child"], timeout=1, output="COMMITTED=false\n", stderr="timeout"),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", lambda **_kwargs: subprocess.TimeoutExpired(cmd=["child"], timeout=1, output="COMMITTED=false\n", stderr="timeout"))
    monkeypatch.setattr(implement_dispatch, "_commit_route_log_failure", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(dispatch_commit_route, "_commit_route_log_failure", lambda *_args, **_kwargs: None)

    def fake_seed(_tmp: Path, *, stall_step: str, bail_reason: str) -> bool:
        seed_calls.append((stall_step, bail_reason))
        return True

    monkeypatch.setattr(implement_dispatch, "_seed_durable_stall_state", fake_seed)
    monkeypatch.setattr(dispatch_commit_route, "_seed_durable_stall_state", fake_seed)

    outcome, stdout = implement_dispatch._run_commit_route_leg(
        site_name="step7",
        implement_tmpdir=impl,
        deadline_ms=1,
    )

    assert outcome == "seeded-stall"
    assert stdout == "COMMITTED=false\n"
    assert seed_calls == [("7", "review-fix-commit-failed")]


def test_checks_step5_resume_timeout_relays_partial_without_composite_continue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = _session(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    resume_calls: list[int] = []
    monkeypatch.setattr(
        implement_dispatch,
        "_run_relevant_checks_for_site",
        lambda **_kwargs: (
            {"RELEVANT_CHECKS_OK": "true", "SITE": "step5-review-fixes", "COVERAGE": "changed", "PHASE": "review"},
            False,
        ),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_relevant_checks_for_site", lambda **_kwargs: (
            {"RELEVANT_CHECKS_OK": "true", "SITE": "step5-review-fixes", "COVERAGE": "changed", "PHASE": "review"},
            False,
        ))

    def fake_resume(*, deadline_ms: int, **_kwargs: object) -> tuple[int, str]:
        resume_calls.append(deadline_ms)
        return 124, "partial resume stdout\n"

    monkeypatch.setattr(implement_dispatch, "_run_step5_resume_leg", fake_resume)
    monkeypatch.setattr(dispatch_commit_route, "_run_step5_resume_leg", fake_resume)

    rc = implement_dispatch.checks_step5_resume_main(
        ["--checks-site", "step5-review-fixes", "--final-round-num", "3", "--resume-deadline-ms", "5678"]
    )

    assert rc == 124
    out = capsys.readouterr().out
    assert "partial resume stdout\n" in out
    assert "NEXT_ACTION=continue" not in out
    assert resume_calls == [5678]


def test_run_leg_with_timeout_group_kills(monkeypatch: pytest.MonkeyPatch) -> None:
    killed: list[tuple[int, int]] = []
    descendant_kills: list[tuple[int, int]] = []

    class FakeProcess:
        pid = 4242
        returncode = None
        communicate_calls = 0
        wait_calls = 0
        stdout = None
        stderr = None

        def poll(self) -> int | None:
            return self.returncode

        def wait(self, timeout: float | None = None) -> int:
            self.wait_calls += 1
            if self.wait_calls == 1:
                raise subprocess.TimeoutExpired(cmd=["child"], timeout=timeout or 0)
            self.returncode = -9
            return -9

        def communicate(self, timeout: float | None = None) -> tuple[str, str]:
            self.communicate_calls += 1
            if self.communicate_calls == 1:
                raise subprocess.TimeoutExpired(cmd=["child"], timeout=timeout or 0, output="before\n", stderr="")
            return "after\n", "timed out\n"

    popen_kwargs: dict[str, object] = {}

    def fake_popen(*_args: object, **kwargs: object) -> FakeProcess:
        popen_kwargs.update(kwargs)
        return FakeProcess()

    monkeypatch.setattr(implement_dispatch.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(implement_dispatch.os, "getpgid", lambda pid: pid + 1)
    monkeypatch.setattr(implement_dispatch.os, "killpg", lambda pgid, sig: killed.append((pgid, sig)))
    monkeypatch.setattr(implement_dispatch.os, "kill", lambda pid, sig: descendant_kills.append((pid, sig)))
    monkeypatch.setattr(implement_dispatch, "_descendants", lambda pid: [9001, 9002] if pid == 4242 else [])
    monkeypatch.setattr(dispatch_leg, "_descendants", lambda pid: [9001, 9002] if pid == 4242 else [])

    result = implement_dispatch._run_leg_with_timeout(argv=["checks", "run-relevant"], deadline_ms=1, label="checks")

    assert isinstance(result, subprocess.TimeoutExpired)
    assert popen_kwargs["start_new_session"] is True
    assert killed == [(4243, signal.SIGTERM), (4243, signal.SIGKILL)]
    assert descendant_kills == [
        (9001, signal.SIGTERM),
        (9002, signal.SIGTERM),
        (9001, signal.SIGKILL),
        (9002, signal.SIGKILL),
    ]
    assert implement_dispatch._timeout_stdout(result) == "after\n"


def test_kill_active_leg_clears_tracked_process(monkeypatch: pytest.MonkeyPatch) -> None:
    killed: list[int] = []

    class FakeProcess:
        pid = 5150
        returncode = None

        def poll(self) -> int | None:
            return self.returncode

        def wait(self, timeout: float | None = None) -> int:  # pylint: disable=unused-argument
            self.returncode = -15
            return -15

    process = FakeProcess()
    implement_dispatch._LEG_STATE.active = cast("subprocess.Popen[str]", process)
    monkeypatch.setattr(implement_dispatch, "_descendants", lambda _pid: [])
    monkeypatch.setattr(dispatch_leg, "_descendants", lambda _pid: [])
    monkeypatch.setattr(implement_dispatch.os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(implement_dispatch.os, "killpg", lambda _pgid, _sig: killed.append(1))

    implement_dispatch._kill_active_leg()

    assert killed == [1, 1]
    assert implement_dispatch._LEG_STATE.active is None


def _setup_step5_resume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    route_stdout: str,
    route_rc: int = 0,
) -> list[list[str]]:
    impl = tmp_path / "impl"
    impl.mkdir()
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.delenv("STEP5_HANDOFF_READY_TO_COMMIT", raising=False)
    monkeypatch.setattr(
        implement_dispatch,
        "_invoke_cli",
        lambda args, **_kwargs: subprocess.CompletedProcess(list(args), route_rc, route_stdout, ""),
    )
    monkeypatch.setattr(dispatch_commit_route, "_invoke_cli", lambda args, **_kwargs: subprocess.CompletedProcess(list(args), route_rc, route_stdout, ""))
    resume_calls: list[list[str]] = []

    def fake_forward(args, **_kwargs):  # type: ignore[no-untyped-def]
        resume_calls.append(list(args))
        return 0

    monkeypatch.setattr(implement_dispatch, "_run_cli_forward", fake_forward)
    monkeypatch.setattr(dispatch_commit_route, "_run_cli_forward", fake_forward)
    monkeypatch.setattr(
        implement_dispatch.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""),
    )
    return resume_calls


def test_step5_resume_registry() -> None:
    assert _REGISTRY[("implement", "step-5-resume")] == ("larch.implement.implement_dispatch", "step5_resume_main")


def test_step5_resume_non_numeric_round_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    rc = implement_dispatch.step5_resume_main(["--final-round-num", "abc"])
    assert rc == 2
    assert "must be numeric" in capsys.readouterr().err


def test_step5_resume_commit_ok_relays_and_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    resume_calls = _setup_step5_resume(tmp_path, monkeypatch, route_stdout=_STEP5_ROUTE_OK)
    rc = implement_dispatch.step5_resume_main(["--final-round-num", "2", "--ready-to-commit"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "COMMIT_OUTCOME=ok" in out
    assert "SHA=abc123" in out
    assert "NEXT_ACTION=continue" in out
    assert len(resume_calls) == 1
    assert resume_calls[0][:2] == ["review-and-fix", "step5"]
    assert resume_calls[0][resume_calls[0].index("--starting-round") + 1] == "3"


def test_step5_resume_commit_noop_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    resume_calls = _setup_step5_resume(tmp_path, monkeypatch, route_stdout=_STEP5_ROUTE_NOOP)
    rc = implement_dispatch.step5_resume_main(["--final-round-num", "4", "--ready-to-commit"])
    assert rc == 0
    assert "COMMIT_OUTCOME=noop" in capsys.readouterr().out
    assert len(resume_calls) == 1


def test_step5_resume_commit_failed_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    resume_calls = _setup_step5_resume(tmp_path, monkeypatch, route_stdout=_STEP5_ROUTE_STALL, route_rc=0)
    rc = implement_dispatch.step5_resume_main(["--final-round-num", "2", "--ready-to-commit"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "COMMIT_OUTCOME=failed" in out
    assert "NEXT_ACTION=stall" in out
    assert not resume_calls


def test_step5_resume_absent_outcome_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resume_calls = _setup_step5_resume(tmp_path, monkeypatch, route_stdout="COMMITTED=false\n", route_rc=0)
    rc = implement_dispatch.step5_resume_main(["--final-round-num", "1", "--ready-to-commit"])
    assert rc == 1
    assert not resume_calls


def test_step5_resume_duplicate_next_action_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    resume_calls = _setup_step5_resume(
        tmp_path, monkeypatch, route_stdout=_STEP5_ROUTE_OK + "NEXT_ACTION=continue\n"
    )
    rc = implement_dispatch.step5_resume_main(["--final-round-num", "2", "--ready-to-commit"])
    assert rc == 1
    out = capsys.readouterr().out
    assert out.count("NEXT_ACTION=continue") == 2
    assert not resume_calls


def test_step5_resume_continue_with_nonzero_route_rc_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    resume_calls = _setup_step5_resume(tmp_path, monkeypatch, route_stdout=_STEP5_ROUTE_OK, route_rc=1)
    rc = implement_dispatch.step5_resume_main(["--final-round-num", "2", "--ready-to-commit"])
    assert rc == 1
    out = capsys.readouterr().out
    assert out.count("NEXT_ACTION=continue") == 1
    assert "COMMIT_OUTCOME=ok" in out
    assert not resume_calls


def test_step5_resume_invalid_next_action_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    resume_calls = _setup_step5_resume(tmp_path, monkeypatch, route_stdout=_STEP5_COMMIT_OK + "NEXT_ACTION=bogus\n")
    rc = implement_dispatch.step5_resume_main(["--final-round-num", "2", "--ready-to-commit"])
    assert rc == 1
    assert "NEXT_ACTION=bogus" in capsys.readouterr().out
    assert not resume_calls


def test_step5_resume_record_only_skips_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    resume_calls = _setup_step5_resume(tmp_path, monkeypatch, route_stdout=_STEP5_ROUTE_OK)
    rc = implement_dispatch.step5_resume_main(["--final-round-num", "2", "--record-only"])
    assert rc == 0
    assert not resume_calls
    assert "COMMIT_OUTCOME" not in capsys.readouterr().out


def test_step5_resume_without_commit_flag_resumes_without_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    resume_calls = _setup_step5_resume(tmp_path, monkeypatch, route_stdout=_STEP5_ROUTE_OK)
    rc = implement_dispatch.step5_resume_main(["--final-round-num", "2"])
    assert rc == 0
    assert len(resume_calls) == 1
    assert "COMMIT_OUTCOME" not in capsys.readouterr().out


def _launcher_args(tmp: Path) -> list[str]:
    for name in ("out", "plan.txt", "feature.txt", "agent.md"):
        path = tmp / name
        if "." in name:
            path.write_text("---\ndescription: x\n---\nbody\n", encoding="utf-8")
    outdir = tmp / "out"
    outdir.mkdir(exist_ok=True)
    return [
        "--transcript-path", str(outdir / "transcript.txt"),
        "--sidecar-log", str(tmp / "sidecar.log"),
        "--manifest-path", str(outdir / "manifest.json"),
        "--qa-pending-path", str(outdir / "qa-pending.json"),
        "--scout-manifest-path", str(outdir / "scout-coder-manifest.json"),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature.txt"),
        "--agent-prompt", str(tmp / "agent.md"),
        "--timeout", "1",
    ]


def test_codex_launcher_missing_binary_emits_kv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    args = _launcher_args(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setattr(agents.shutil, "which", lambda name: None if name == "codex" else "/bin/true")
    rc = agents.launch_codex_implement_main(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "LAUNCHER_EXIT=127" in out
    assert "MANIFEST_WRITTEN=false" in out


@pytest.mark.parametrize(
    ("launcher", "tool"),
    [
        (agents.launch_codex_implement_main, "codex"),
        (agents.launch_cursor_implement_main, "cursor"),
    ],
)
def test_implement_launchers_reject_bad_timeout(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    launcher: Callable[[list[str]], int],
    tool: str,
) -> None:
    args = _launcher_args(tmp_path)
    args[args.index("--timeout") + 1] = "0"

    rc = launcher(args)

    assert rc == 2
    assert f"agent launch-{tool}-implement: --timeout must be a positive integer" in capsys.readouterr().err


def test_codex_launcher_rejects_session_tmpdir_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    args = _launcher_args(tmp_path)
    outdir = tmp_path / "out"
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(outdir))

    rc = agents.launch_codex_implement_main(args)

    assert rc == 2
    assert "--manifest-path parent must not be the implement session tmpdir root" in capsys.readouterr().err


def test_codex_launcher_builds_exec_argv_and_dynamic_prompt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    args = _launcher_args(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setattr(agents.shutil, "which", lambda name: "/usr/bin/codex" if name == "codex" else "/bin/true")
    monkeypatch.setattr(_ci_launcher, "_record_implement_timing", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_ci_launcher, "_record_usage_from_events", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_run_external, "_mirror_codex_quota_from_events", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_ci_launcher, "_promote_inner_done", lambda *_args, **_kwargs: None)
    resolved = tmp_path / "resolved-repo"
    resolved.mkdir()
    monkeypatch.setattr(_ci_launcher, "_resolve_review_codex_workdir", lambda _cwd: str(resolved))  # type: ignore[arg-type]
    captured: dict[str, object] = {}

    def fake_run_external_agent_with_auth_retries(**kwargs):  # type: ignore[no-untyped-def]
        cmd = list(kwargs["cmd"])
        output = kwargs["output"]
        stdout_path = kwargs["stdout_path"]
        captured["cmd"] = cmd
        captured["cwd"] = kwargs["cwd"]
        captured["config"] = (Path(agents.os.environ["CODEX_HOME"]) / "config.toml").read_text(encoding="utf-8")
        output.write_text("codex transcript\n", encoding="utf-8")
        stdout_path.write_text('{"type":"turn_completed","usage":{"input_tokens":1}}\n', encoding="utf-8")
        return agents.RunExternalAgentResult(0, output)

    monkeypatch.setattr(_ci_launcher, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)

    rc = agents.launch_codex_implement_main(args)

    cmd = captured["cmd"]
    assert rc == 0
    assert isinstance(cmd, list)
    assert cmd[:4] == ["codex", "exec", "--full-auto", "-C"]
    assert cmd.count("--add-dir") == 2
    assert str(tmp_path / "out") in cmd
    assert cmd[4] == str(resolved)
    add_dir_values = [cmd[index + 1] for index, value in enumerate(cmd) if value == "--add-dir"]
    assert str(resolved) in add_dir_values
    assert f'projects."{resolved}".trust_level="trusted"' in cmd
    assert captured["cwd"] == str(resolved)
    assert "--output-last-message" in cmd
    assert cmd[-2] == "--"
    assert "body" not in Path(str(tmp_path / "out" / "transcript.txt.prompt")).read_text(encoding="utf-8")
    assert "instructions = '''" in str(captured["config"])
    assert "body" in str(captured["config"])


def test_cursor_launcher_missing_binary_emits_kv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    args = _launcher_args(tmp_path)
    monkeypatch.setattr(agents.shutil, "which", lambda name: None if name == "cursor" else "/bin/true")
    rc = agents.launch_cursor_implement_main(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "LAUNCHER_EXIT=127" in out
    assert "MANIFEST_WRITTEN=false" in out


def test_cursor_launcher_builds_agent_argv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    args = _launcher_args(tmp_path)
    monkeypatch.setattr(agents.shutil, "which", lambda name: "/usr/bin/cursor" if name == "cursor" else "/bin/true")
    monkeypatch.setattr(_ci_launcher, "cursor_auth_preflight", lambda **_kwargs: agents.AuthVerdict(ok=True, rc=0, message=""))
    monkeypatch.setattr(_ci_launcher, "cursor_preread_service_token", lambda: True)
    monkeypatch.setattr(_ci_launcher, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(_ci_launcher, "_record_implement_timing", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_ci_launcher, "_record_cursor_implement_usage", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_ci_launcher, "_promote_inner_done", lambda *_args, **_kwargs: None)
    resolved = tmp_path / "resolved-repo"
    resolved.mkdir()
    monkeypatch.setattr(_ci_launcher, "_resolve_review_codex_workdir", lambda _cwd: str(resolved))  # type: ignore[arg-type]
    captured: dict[str, object] = {}

    def fake_run_external_agent_with_auth_retries(**kwargs):  # type: ignore[no-untyped-def]
        cmd = list(kwargs["cmd"])
        output = kwargs["output"]
        captured["cmd"] = cmd
        captured["capture_stdout_only"] = kwargs["capture_stdout_only"]
        output.write_text('{"usage":{"inputTokens":1}}\n', encoding="utf-8")
        return agents.RunExternalAgentResult(0, output)

    monkeypatch.setattr(_ci_launcher, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)

    rc = agents.launch_cursor_implement_main(args)

    cmd = captured["cmd"]
    assert rc == 0
    assert isinstance(cmd, list)
    assert cmd[:7] == ["cursor", "agent", "-p", "--force", "--trust", "--output-format", "json"]
    assert "--workspace" in cmd
    assert cmd[cmd.index("--workspace") + 1] == str(resolved)
    assert "--" not in cmd
def _auth_lines(out: str) -> int:
    return sum(1 for line in out.splitlines() if line.startswith("ORCHESTRATOR_EDIT_AUTHORITY="))


def test_step2_dispatch_auth_pair_claude_fallback(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "claude",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=claude_fallback" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=allowed" in out


def test_step2_dispatch_auth_pair_external_bailed(repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    (tmp / "step2-baseline.txt").write_text(_git(repo, "rev-parse", "HEAD").stdout, encoding="utf-8")
    (tmp / "step2-spawn-branch.txt").write_text(_git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout, encoding="utf-8")
    (tmp / "codex-resume-count.txt").write_text("5\n", encoding="utf-8")
    answers = tmp / "answers.json"
    answers.write_text("{}\n", encoding="utf-8")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
        "--answers", str(answers),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=bailed" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=allowed" not in out


def test_commit_main_pathspec_with_spaced_paths(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    spaced = repo / "path with spaces.txt"
    spaced.write_text("x\n", encoding="utf-8")
    pathspec = tmp_path / "paths.nul"
    pathspec.write_bytes(b"path with spaces.txt\0")
    calls: list[list[str]] = []

    def fake_run(argv, **_kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(argv))
        stdout = "abc123\n" if argv[:2] == ["git", "rev-parse"] else ""
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    monkeypatch.setattr(implement_dispatch, "_invoke_cli", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(dispatch_recovery, "_invoke_cli", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(implement_dispatch, "_run", fake_run)
    monkeypatch.setattr(dispatch_recovery, "_run", fake_run)

    rc = implement_dispatch.commit_main([
        "--message", "Recover spaced path",
        "--pathspec-from-file", str(pathspec),
        "--pathspec-file-nul",
        "ignored.txt",
    ])

    assert rc == 0
    assert calls[0][-4:] == ["--only", "--pathspec-from-file", str(pathspec), "--pathspec-file-nul"]
    assert "ignored.txt" not in calls[0]
    out = capsys.readouterr().out
    assert "COMMITTED=true" in out
    assert "SHA=abc123" in out


def test_step2_dispatch_git_add_failure_bails(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "implemented.txt").write_text("done\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(json.dumps({
            "schema_version": "1",
            "status": "complete",
            "files_touched": [{"path": "implemented.txt", "lines_added": 1, "lines_removed": 0}],
            "tests_added_or_modified": [],
            "summary_bullets": ["Implement the feature"],
            "commit_message": "Implement via fake launcher",
            "todos_left": [],
            "oos_observations": [],
        }), encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    real_run = implement_dispatch.subprocess.run

    def fake_run(argv, **kwargs):  # type: ignore[no-untyped-def]
        if len(argv) >= 4 and argv[0:3] == [implement_dispatch.GIT_BIN, "-C", str(repo)] and argv[3] == "add":
            return subprocess.CompletedProcess(argv, 1, "", "index.lock")
        return real_run(argv, check=kwargs.pop("check", False), **kwargs)

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(dispatch_step2, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    monkeypatch.setattr(dispatch_step2, "_materialize_oos", lambda *_a, **_k: "")
    monkeypatch.setattr(implement_dispatch.subprocess, "run", fake_run)

    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=bailed" in out
    assert "REASON=commit-failed" in out


def test_step2_dispatch_main_branch_prohibited(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    subprocess.run(["git", "-C", str(repo), "checkout", "-B", "main"], check=True, stdout=subprocess.DEVNULL)
    tmp = _session(tmp_path)
    (tmp / "session-env.sh").write_text("ISSUE_NUMBER=123\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "cursor",
        "--cursor-binary-found", "true",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=bailed" in out
    assert "REASON=main-branch-prohibited" in out


def test_step2_dispatch_needs_qa_repair_from_pending(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _ = repo
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(json.dumps({
            "schema_version": "1",
            "status": "needs_qa",
            "needs_qa": {"questions": []},
            "files_touched": [{"path": "implemented.txt"}],
            "summary_bullets": ["q"],
            "commit_message": "x",
            "tests_added_or_modified": [],
            "todos_left": [],
            "oos_observations": [],
        }), encoding="utf-8")
        st.qa_pending_path.write_text(json.dumps({
            "items": [{"area": "auth", "risk": "high", "suggested_check": "verify login"}],
        }), encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(dispatch_step2, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=needs_qa" in out
    qa_path = tmp / "codex-step2-out" / "qa-pending.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    assert qa["questions"][0]["text"].startswith("Area: auth")


def _seed_external_dispatch_state(
    repo: Path,
    tmp: Path,
    *,
    resume_count: str | None = None,
    spawn_coder: str | None = None,
) -> None:
    (tmp / "step2-baseline.txt").write_text(_git(repo, "rev-parse", "HEAD").stdout, encoding="utf-8")
    (tmp / "step2-spawn-branch.txt").write_text(_git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout, encoding="utf-8")
    if resume_count is not None:
        (tmp / "codex-resume-count.txt").write_text(resume_count + "\n", encoding="utf-8")
    if spawn_coder is not None:
        (tmp / "step2-spawn-coder.txt").write_text(spawn_coder + "\n", encoding="utf-8")


def _complete_manifest_payload(*, path: str = "implemented.txt", commit_message: str = "Implement via fake launcher") -> dict[str, object]:
    return {
        "schema_version": "1",
        "status": "complete",
        "files_touched": [{"path": path, "lines_added": 1, "lines_removed": 0}],
        "tests_added_or_modified": [],
        "summary_bullets": ["Implement the feature"],
        "commit_message": commit_message,
        "todos_left": [],
        "oos_observations": [],
    }


def test_step2_dispatch_qa_loop_exceeded(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    _seed_external_dispatch_state(repo, tmp, resume_count="5")
    answers = tmp_path / "answers.json"
    answers.write_text('{"answers":[{"id":"q1","text":"x"}]}\n', encoding="utf-8")
    launcher_calls = 0

    def fake_launcher(_st: implement_dispatch.DispatchState):
        nonlocal launcher_calls
        launcher_calls += 1
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
        "--answers", str(answers),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert launcher_calls == 0
    assert _auth_lines(out) == 1
    assert "STATUS=bailed" in out
    assert "REASON=qa-loop-exceeded" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out
    assert (tmp / "codex-resume-count.txt").is_file()


def test_step2_dispatch_corrupt_resume_counter_bails(repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    _seed_external_dispatch_state(repo, tmp, resume_count="garbage")
    answers = tmp_path / "answers.json"
    answers.write_text('{"answers":[{"id":"q1","text":"x"}]}\n', encoding="utf-8")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
        "--answers", str(answers),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=bailed" in out
    assert "REASON=manifest-schema-invalid" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out


def test_step2_dispatch_coder_mismatch_tmpdir_reuse(repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    _seed_external_dispatch_state(repo, tmp, spawn_coder="codex")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "cursor",
        "--cursor-present", "true",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=bailed" in out
    assert "REASON=coder-mismatch-tmpdir-reuse" in out
    assert "TOOL=cursor" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out
    assert (tmp / "step2-spawn-coder.txt").read_text(encoding="utf-8").strip() == "codex"
    assert not (tmp / "cursor-resume-count.txt").exists()


def test_step2_dispatch_detached_head_prohibited(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    subprocess.run(["git", "-C", str(repo), "checkout", "--detach"], check=True, stdout=subprocess.DEVNULL)
    tmp = _session(tmp_path)
    (tmp / "session-env.sh").write_text("ISSUE_NUMBER=2486\nFORKED_TARGET=false\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))
    launcher_calls = 0

    def fake_launcher(_st: implement_dispatch.DispatchState):
        nonlocal launcher_calls
        launcher_calls += 1
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "cursor",
        "--cursor-binary-found", "true",
    ])
    assert rc == 0
    assert launcher_calls == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=bailed" in out
    assert "REASON=detached-head-prohibited" in out
    assert "TOOL=cursor" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out


def test_step2_dispatch_cap_hit_bails(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _ = repo
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(_st: implement_dispatch.DispatchState):
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "false", "STATUS": "cap_hit"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=bailed" in out
    assert "REASON=cap_hit" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out


def test_step2_dispatch_wrapper_validation_failure_bails(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _ = repo
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(_st: implement_dispatch.DispatchState):
        return implement_dispatch.WRAPPER_VALIDATION_RC, dict[str, str](), ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=bailed" in out
    assert "REASON=wrapper-validation-failure" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out


def test_step2_dispatch_dirty_state_after_timeout_bails(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(_st: implement_dispatch.DispatchState):
        (repo / "dirty-after-timeout.txt").write_text("x\n", encoding="utf-8")
        return 1, {"LAUNCHER_EXIT": "1", "MANIFEST_WRITTEN": "false"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=bailed" in out
    assert "REASON=dirty-state-after-timeout" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out


def test_step2_dispatch_codex_nonzero_exit_salvages_complete(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "README.md").write_text("edited by stub\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(
            json.dumps(_complete_manifest_payload(path="README.md", commit_message="stub: edit README after self-verify failure")),
            encoding="utf-8",
        )
        return 0, {"LAUNCHER_EXIT": "1", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(dispatch_step2, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    monkeypatch.setattr(dispatch_step2, "_materialize_oos", lambda *_a, **_k: "")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=complete" in out
    assert "WARN_CODEX_NONZERO_EXIT=true" in out
    assert "REASON=codex-runtime-failure" not in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out
    assert _git(repo, "log", "-1", "--pretty=%s").stdout.strip() == "stub: edit README after self-verify failure"
    issues = (tmp / "execution-issues.md").read_text(encoding="utf-8")
    assert "WARN_CODEX_NONZERO_EXIT=true" in issues


@pytest.mark.parametrize(
    "manifest_payload",
    [
        pytest.param(
            {
                "schema_version": "1",
                "status": "needs_qa",
                "needs_qa": {"questions": [{"id": "q1", "text": "stub question?"}]},
            },
            id="needs_qa",
        ),
        pytest.param(
            {
                "schema_version": "1",
                "status": "bailed",
                "bail_reason": "stub-self-bail",
            },
            id="bailed",
        ),
    ],
)
def test_step2_dispatch_codex_nonzero_exit_does_not_salvage_non_complete(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    manifest_payload: dict[str, object],
) -> None:
    _ = repo
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(json.dumps(manifest_payload), encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "1", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=bailed" in out
    assert "REASON=codex-runtime-failure" in out
    assert "WARN_CODEX_NONZERO_EXIT=true" not in out
    assert "STATUS=complete" not in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out
    if manifest_payload.get("status") == "bailed":
        assert "REASON=stub-self-bail" not in out


def test_step2_dispatch_complete_emits_scout_kv(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "implemented.txt").write_text("done\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(json.dumps(_complete_manifest_payload()), encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    def fake_normalize_scout(st: implement_dispatch.DispatchState) -> None:
        st.scout_status = "ok"
        st.scout_coder_manifest.parent.mkdir(parents=True, exist_ok=True)
        st.scout_coder_manifest.write_text('{"archetypes":[{"name":"api-contract"}]}\n', encoding="utf-8")
        st.external_scout_marker.write_text("eligible\n", encoding="utf-8")

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", fake_normalize_scout)
    monkeypatch.setattr(dispatch_step2, "_normalize_scout", fake_normalize_scout)
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    monkeypatch.setattr(dispatch_step2, "_materialize_oos", lambda *_a, **_k: "")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=complete" in out
    assert f"SCOUT_CODER_MANIFEST={tmp / 'scout-coder-manifest.json'}" in out
    assert "SCOUT_CODER_STATUS=ok" in out


def _dynamic_archetype(name: str) -> dict[str, object]:
    return {
        "name": name,
        "focus_area": "architecture",
        "weight": 1,
        "rationale": "Architecture changed.",
        "prompt_body": "Check architecture risks in the changed code.",
    }


def test_normalize_coder_scout_intentional_empty_is_ok(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    raw.write_text('{"archetypes":[]}\n', encoding="utf-8")
    status = implement_dispatch.normalize_coder_scout(tmpdir=tmp_path, input_path=raw, producer="main-agent")
    assert status == "ok"
    assert (tmp_path / "step2-external-scout-eligible.txt").is_file()
    assert "SCOUT_CODER_STATUS=ok" in (tmp_path / "step2-scout-coder-status.env").read_text(encoding="utf-8")
    assert json.loads((tmp_path / "scout-coder-manifest.json").read_text(encoding="utf-8")) == {"archetypes": []}


def test_normalize_coder_scout_filtered_to_zero_is_invalid(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"archetypes": [_dynamic_archetype("correctness"), _dynamic_archetype("testing")]}) + "\n", encoding="utf-8")
    status = implement_dispatch.normalize_coder_scout(tmpdir=tmp_path, input_path=raw, producer="main-agent")
    captured = capsys.readouterr()
    assert status == "missing-or-invalid"
    assert "dynamic-archetype manifest missing or invalid" in captured.err
    assert not (tmp_path / "step2-external-scout-eligible.txt").exists()
    assert "SCOUT_CODER_STATUS=missing-or-invalid" in (tmp_path / "step2-scout-coder-status.env").read_text(encoding="utf-8")
    assert json.loads((tmp_path / "scout-coder-manifest.json").read_text(encoding="utf-8")) == {"archetypes": []}


def test_normalize_coder_scout_uses_review_mode_so_arch_survives(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"archetypes": [_dynamic_archetype("arch")]}) + "\n", encoding="utf-8")
    status = implement_dispatch.normalize_coder_scout(tmpdir=tmp_path, input_path=raw, producer="external")
    assert status == "ok"
    manifest = json.loads((tmp_path / "scout-coder-manifest.json").read_text(encoding="utf-8"))
    assert [item["name"] for item in manifest["archetypes"]] == ["arch"]


def test_step2_dispatch_complete_allows_plugin_json_edit(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        plugin_json = repo / ".claude-plugin" / "plugin.json"
        plugin_json.parent.mkdir(parents=True, exist_ok=True)
        plugin_json.write_text('{"name": "larch", "version": "1.0.0", "description": "edited"}\n', encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(
            json.dumps(_complete_manifest_payload(path=".claude-plugin/plugin.json", commit_message="Edit plugin.json description")),
            encoding="utf-8",
        )
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(dispatch_step2, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    monkeypatch.setattr(dispatch_step2, "_materialize_oos", lambda *_a, **_k: "")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=complete" in out
    assert "protected-path-modified" not in out


def test_step2_dispatch_undeclared_path_warning(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "README.md").write_text("declared edit\n", encoding="utf-8")
        (repo / "undeclared.txt").write_text("undeclared edit\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(
            json.dumps(_complete_manifest_payload(path="README.md", commit_message="stub: edit README with undeclared side file")),
            encoding="utf-8",
        )
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(dispatch_step2, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    monkeypatch.setattr(dispatch_step2, "_materialize_oos", lambda *_a, **_k: "")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=complete" in out
    issues = (tmp / "execution-issues.md").read_text(encoding="utf-8")
    assert "not declared in manifest files_touched/tests_added_or_modified" in issues
    assert "**Step 7a.1" in issues
    assert "undeclared.txt" in issues
    assert "- undeclared.txt" not in issues  # paths now inline after ": ", not as sub-bullets
    assert "README.md" not in issues


def test_step2_dispatch_plan_coverage_warns_for_untouched_plan_path(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    tmp = _session(tmp_path)
    (tmp / "plan.txt").write_text(
        "## Files to modify/create\n"
        "### UPDATED: `README.md`\n"
        "### UPDATED: `docs/expected.md`\n"
        "### MAY_UPDATE: `docs/optional.md`\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "README.md").write_text("declared edit\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(
            json.dumps(_complete_manifest_payload(path="README.md", commit_message="stub: edit README only")),
            encoding="utf-8",
        )
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(dispatch_step2, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    monkeypatch.setattr(dispatch_step2, "_materialize_oos", lambda *_a, **_k: "")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=complete" in out
    assert "WARN_PLAN_FILES_UNTOUCHED=true" in out
    assert "WARN_PLAN_FILES_UNTOUCHED_COUNT=1" in out
    assert _git(repo, "log", "-1", "--pretty=%s").stdout.strip() == "stub: edit README only"
    issues = (tmp / "execution-issues.md").read_text(encoding="utf-8")
    assert "docs/expected.md" in issues
    assert "docs/optional.md" not in issues


def test_step2_dispatch_plan_coverage_no_warning_when_all_plan_paths_touched(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    tmp = _session(tmp_path)
    (tmp / "plan.txt").write_text("## Files to modify/create\n### UPDATED: `README.md`\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "README.md").write_text("declared edit\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(
            json.dumps(_complete_manifest_payload(path="README.md", commit_message="stub: edit README")),
            encoding="utf-8",
        )
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(dispatch_step2, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    monkeypatch.setattr(dispatch_step2, "_materialize_oos", lambda *_a, **_k: "")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=complete" in out
    assert "WARN_PLAN_FILES_UNTOUCHED" not in out
    issues = (tmp / "execution-issues.md").read_text(encoding="utf-8") if (tmp / "execution-issues.md").is_file() else ""
    assert "explicit plan-listed path" not in issues


def test_step2_dispatch_plan_coverage_no_warning_for_optional_only_scope(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    tmp = _session(tmp_path)
    (tmp / "plan.txt").write_text("## Files to modify/create\n### MAY_UPDATE: `docs/optional.md`\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "README.md").write_text("declared edit\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(
            json.dumps(_complete_manifest_payload(path="README.md", commit_message="stub: edit README")),
            encoding="utf-8",
        )
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(dispatch_step2, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    monkeypatch.setattr(dispatch_step2, "_materialize_oos", lambda *_a, **_k: "")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=complete" in out
    assert "WARN_PLAN_FILES_UNTOUCHED" not in out
    issues = (tmp / "execution-issues.md").read_text(encoding="utf-8") if (tmp / "execution-issues.md").is_file() else ""
    assert "explicit plan-listed path" not in issues
    assert "docs/optional.md" not in issues


def test_step2_dispatch_plan_coverage_no_warning_without_explicit_scope(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    tmp = _session(tmp_path)
    (tmp / "plan.txt").write_text("## Plan\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "README.md").write_text("declared edit\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(
            json.dumps(_complete_manifest_payload(path="README.md", commit_message="stub: edit README")),
            encoding="utf-8",
        )
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(dispatch_step2, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    monkeypatch.setattr(dispatch_step2, "_materialize_oos", lambda *_a, **_k: "")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=complete" in out
    assert "WARN_PLAN_FILES_UNTOUCHED" not in out
    issues = (tmp / "execution-issues.md").read_text(encoding="utf-8") if (tmp / "execution-issues.md").is_file() else ""
    assert "skills/design/SKILL.md" not in issues
    assert "explicit plan-listed path" not in issues


def test_step2_dispatch_plan_coverage_no_warning_without_files_section_and_unrelated_heading(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    tmp = _session(tmp_path)
    (tmp / "plan.txt").write_text(
        "## Plan\n"
        "### UPDATED: `docs/expected.md`\n"
        "## Acceptance\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "README.md").write_text("declared edit\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(
            json.dumps(_complete_manifest_payload(path="README.md", commit_message="stub: edit README")),
            encoding="utf-8",
        )
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(dispatch_step2, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    monkeypatch.setattr(dispatch_step2, "_materialize_oos", lambda *_a, **_k: "")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=complete" in out
    assert "WARN_PLAN_FILES_UNTOUCHED" not in out
    issues = (tmp / "execution-issues.md").read_text(encoding="utf-8") if (tmp / "execution-issues.md").is_file() else ""
    assert "docs/expected.md" not in issues
    assert "explicit plan-listed path" not in issues


def test_step2_dispatch_git_probe_failure_suppresses_plan_and_undeclared_warnings(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    tmp = _session(tmp_path)
    (tmp / "plan.txt").write_text(
        "## Files to modify/create\n"
        "### UPDATED: `README.md`\n"
        "### UPDATED: `docs/expected.md`\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "README.md").write_text("declared edit\n", encoding="utf-8")
        (repo / "undeclared.txt").write_text("undeclared edit\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(
            json.dumps(_complete_manifest_payload(path="README.md", commit_message="stub: edit README with undeclared side file")),
            encoding="utf-8",
        )
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    real_git = implement_dispatch._git

    def fake_git(repo_root: Path, *args: str, binary: bool = False):
        if args == ("diff", "--name-only", "HEAD"):
            return subprocess.CompletedProcess(["git", *args], 1, "", "boom")
        return real_git(repo_root, *args, binary=binary)

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(dispatch_step2, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    monkeypatch.setattr(dispatch_step2, "_materialize_oos", lambda *_a, **_k: "")
    monkeypatch.setattr(implement_dispatch, "_git", fake_git)
    monkeypatch.setattr(dispatch_step2, "_git", fake_git)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=complete" in out
    assert "WARN_PLAN_FILES_UNTOUCHED" not in out
    issues = (tmp / "execution-issues.md").read_text(encoding="utf-8")
    assert "git probe(s) failed" in issues
    assert "git diff --name-only HEAD" in issues
    assert "docs/expected.md" not in issues
    assert "not declared in manifest files_touched/tests_added_or_modified" not in issues
    assert "undeclared.txt" not in issues


def test_step2_dispatch_plan_read_failure_suppresses_coverage_kv(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    tmp = _session(tmp_path)
    plan_path = tmp / "plan.txt"
    plan_path.write_text(
        "## Files to modify/create\n"
        "### UPDATED: `README.md`\n"
        "### UPDATED: `docs/expected.md`\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "README.md").write_text("declared edit\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(
            json.dumps(_complete_manifest_payload(path="README.md", commit_message="stub: edit README")),
            encoding="utf-8",
        )
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    real_read_text = Path.read_text

    def fake_read_text(self: Path, encoding: str | None = None, errors: str | None = None) -> str:
        if self == plan_path:
            raise OSError("synthetic plan read failure")
        return real_read_text(self, encoding=encoding, errors=errors)

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(dispatch_step2, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(dispatch_step2, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    monkeypatch.setattr(dispatch_step2, "_materialize_oos", lambda *_a, **_k: "")
    monkeypatch.setattr(Path, "read_text", fake_read_text)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(plan_path),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=complete" in out
    assert "WARN_PLAN_FILES_UNTOUCHED" not in out
    issues = (tmp / "execution-issues.md").read_text(encoding="utf-8")
    assert "could not read plan file for plan-file coverage" in issues
    assert "synthetic plan read failure" in issues
    assert "docs/expected.md" not in issues
    # Regression (#5219): the single-line plan-read-failure warning must be
    # bullet-normalized by _append_warning so the final-summary parser counts
    # and renders it instead of dropping it from "## Exec Issues and Warnings".
    warn_groups = exec_issue_detail.parse_markdown_execution_issues(issues)
    assert exec_issue_detail.count_issue_groups(warn_groups) == (0, 1)
    rendered = exec_issue_detail.render_issue_detail_block(
        exec_issue_detail.LoadResult(warn_groups, listing_degraded=False), assess=False
    )
    assert "could not read plan file for plan-file coverage" in rendered


def test_append_warning_normalizes_plain_text_for_final_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression (#5219): _append_warning must bullet-normalize plain warning
    text so exec_issue_detail counts/renders it, while leaving already-bulleted
    entries untouched (no double "- " prefix).
    """
    log = tmp_path / "execution-issues.md"
    captured: list[str] = []

    def fake_invoke(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        argv = list(args)
        entry = argv[argv.index("--entry") + 1]
        captured.append(entry)
        run_logs.append_execution_issue(
            log_file=Path(argv[argv.index("--log") + 1]), category=argv[argv.index("--category") + 1], entry=entry
        )
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(implement_dispatch, "_invoke_cli", fake_invoke)
    monkeypatch.setattr(dispatch_step2, "_invoke_cli", fake_invoke)
    st = cast("implement_dispatch.DispatchState", SimpleNamespace(tmpdir=tmp_path))

    implement_dispatch._append_warning(st=st, text="Step 7a.1 — could not read plan file for plan-file coverage: /p: boom")
    implement_dispatch._append_warning(st=st, text="- **Step 7a.1 — 2 paths**: a, b")

    assert captured[0] == "- Step 7a.1 — could not read plan file for plan-file coverage: /p: boom"
    assert captured[1] == "- **Step 7a.1 — 2 paths**: a, b"

    groups = exec_issue_detail.parse_markdown_execution_issues(log.read_text(encoding="utf-8"))
    assert exec_issue_detail.count_issue_groups(groups) == (0, 2)
    rendered = exec_issue_detail.render_issue_detail_block(
        exec_issue_detail.LoadResult(groups, listing_degraded=False), assess=False
    )
    assert "could not read plan file for plan-file coverage" in rendered


def _materialize_dispatch_state(tmp_path: Path, observations: object) -> implement_dispatch.DispatchState:
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    tmp = tmp_path / "impl"
    tmp.mkdir()
    manifest = tmp / "manifest.json"
    manifest.write_text(json.dumps({"oos_observations": observations}), encoding="utf-8")
    return implement_dispatch.DispatchState(
        repo_root=tmp_path,
        tmpdir=tmp,
        plan_file=tmp / "plan.txt",
        feature_file=tmp / "feature.txt",
        coder="codex",
        cursor_present="false",
        cursor_binary_found="true",
        codex_binary_found="true",
        answers_file=None,
        plugin_root=plugin,
        tool_tag="codex",
        manifest_path=manifest,
        manifest_raw_path=tmp / "manifest-raw.json",
        qa_pending_path=tmp / "qa-pending.json",
        transcript_path=tmp / "transcript.txt",
        sidecar_log=tmp / "sidecar.log",
        scout_coder_manifest=tmp / "scout.json",
        launch_scout_manifest=tmp / "launch-scout.json",
        external_scout_marker=tmp / "marker.txt",
        baseline_file=tmp / "baseline.txt",
        prelaunch_porcelain=tmp / "pre.nul",
        postlaunch_porcelain=tmp / "post.nul",
        prelaunch_digests=tmp / "digests.txt",
        prelaunch_index_flag=tmp / "index.env",
        recovery_paths_file=tmp / "recovery.nul",
        resume_count_file=tmp / "resume.txt",
        spawn_branch_file=tmp / "branch.txt",
        spawn_coder_file=tmp / "coder.txt",
        runtime_failure_token="codex-runtime-failure",  # noqa: S106
        bailed_no_reason_token="codex-bailed-no-reason",  # noqa: S106
        requires_head_unchanged=False,
        nonzero_exit_warn_token="",
    )


def test_materialize_oos_full_failure_with_observations_bails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    st = _materialize_dispatch_state(tmp_path, [{"title": "t"}])
    calls: list[bool] = []

    def fake_materialize(_manifest: Path, _tmpdir: Path, *, count_only: bool = False) -> int:
        calls.append(count_only)
        if count_only:
            return 1
        raise RuntimeError("forced materialize failure")

    monkeypatch.setattr(implement_dispatch.file_oos, "materialize_manifest_oos", fake_materialize)
    monkeypatch.setattr(implement_dispatch, "_invoke_cli", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))
    reason = implement_dispatch._materialize_oos(st, oos_observations_nonempty=True)

    assert reason == "manifest-oos-materialization-failed"
    assert calls == [True, False]
    assert (st.tmpdir / "materialize-manifest-oos.log").is_file()
    assert "forced materialize failure" in (st.tmpdir / "materialize-manifest-oos.log").read_text(encoding="utf-8")


def test_oos_materialize_should_bail_gates_positive_count_on_failure() -> None:
    assert (
        implement_dispatch._oos_materialize_should_bail(
            count_rc=0,
            count_str="1",
            oos_nonempty=True,
            materialize_failed=False,
        )
        is False
    )
    assert (
        implement_dispatch._oos_materialize_should_bail(
            count_rc=0,
            count_str="1",
            oos_nonempty=False,
            materialize_failed=True,
        )
        is True
    )
    assert (
        implement_dispatch._oos_materialize_should_bail(
            count_rc=1,
            count_str="0",
            oos_nonempty=False,
            materialize_failed=False,
        )
        is True
    )


def test_materialize_oos_successful_dual_pass_positive_count_does_not_bail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st = _materialize_dispatch_state(tmp_path, [{"title": "t"}])
    calls: list[bool] = []

    def fake_materialize(_manifest: Path, _tmpdir: Path, *, count_only: bool = False) -> int:
        calls.append(count_only)
        return 1

    monkeypatch.setattr(implement_dispatch.file_oos, "materialize_manifest_oos", fake_materialize)

    assert implement_dispatch._materialize_oos(st, oos_observations_nonempty=True) == ""
    assert calls == [True, False]


def test_materialize_oos_count_type_error_runs_full_pass_and_bails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st = _materialize_dispatch_state(tmp_path, [{"title": "t"}])
    calls: list[bool] = []

    def fake_materialize(_manifest: Path, _tmpdir: Path, *, count_only: bool = False) -> int:
        calls.append(count_only)
        if count_only:
            raise TypeError("bad count")
        return 0

    monkeypatch.setattr(implement_dispatch.file_oos, "materialize_manifest_oos", fake_materialize)

    assert implement_dispatch._materialize_oos(st, oos_observations_nonempty=True) == "manifest-oos-materialization-failed"
    assert calls == [True, False]
    assert "bad count" in (st.tmpdir / "materialize-manifest-oos.log").read_text(encoding="utf-8")


def test_materialize_oos_preassignment_failure_and_full_failure_logs_both(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st = _materialize_dispatch_state(tmp_path, [{"title": "t"}])
    calls: list[bool] = []

    def fake_materialize(_manifest: Path, _tmpdir: Path, *, count_only: bool = False) -> int:
        calls.append(count_only)
        if count_only:
            raise TypeError("count boom")
        raise RuntimeError("full boom")

    monkeypatch.setattr(implement_dispatch.file_oos, "materialize_manifest_oos", fake_materialize)
    monkeypatch.setattr(implement_dispatch, "_invoke_cli", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))

    assert implement_dispatch._materialize_oos(st, oos_observations_nonempty=True) == "manifest-oos-materialization-failed"
    assert calls == [True, False]
    log_text = (st.tmpdir / "materialize-manifest-oos.log").read_text(encoding="utf-8")
    assert "count boom" in log_text
    assert "full boom" in log_text


def test_materialize_oos_count_result_is_bound_as_string(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st = _materialize_dispatch_state(tmp_path, [{"title": "t"}])

    def fake_materialize(_manifest: Path, _tmpdir: Path, *, count_only: bool = False) -> int:
        return 1 if count_only else 0

    monkeypatch.setattr(implement_dispatch.file_oos, "materialize_manifest_oos", fake_materialize)

    assert implement_dispatch._materialize_oos(st, oos_observations_nonempty=True) == ""


def test_codex_launcher_rejects_control_char_parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad\nparent"
    bad.mkdir()
    outdir = bad / "out"
    outdir.mkdir()
    for name in ("plan.txt", "feature.txt", "agent.md"):
        (tmp_path / name).write_text("---\ndescription: x\n---\nbody\n", encoding="utf-8")
    args = [
        "--transcript-path", str(outdir / "transcript.txt"),
        "--sidecar-log", str(tmp_path / "sidecar.log"),
        "--manifest-path", str(outdir / "manifest.json"),
        "--qa-pending-path", str(outdir / "qa-pending.json"),
        "--scout-manifest-path", str(outdir / "scout-coder-manifest.json"),
        "--plan-file", str(tmp_path / "plan.txt"),
        "--feature-file", str(tmp_path / "feature.txt"),
        "--agent-prompt", str(tmp_path / "agent.md"),
        "--timeout", "1",
    ]
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    rc = agents.launch_codex_implement_main(args)
    assert rc == 2
    assert "parent is not a directory" in capsys.readouterr().err


def test_codex_launcher_rejects_symlink_parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    real = tmp_path / "real-out"
    real.mkdir()
    symlink = tmp_path / "symlink-out"
    symlink.symlink_to(real)
    for name in ("plan.txt", "feature.txt", "agent.md"):
        (tmp_path / name).write_text("---\ndescription: x\n---\nbody\n", encoding="utf-8")
    args = [
        "--transcript-path", str(symlink / "transcript.txt"),
        "--sidecar-log", str(tmp_path / "sidecar.log"),
        "--manifest-path", str(symlink / "manifest.json"),
        "--qa-pending-path", str(symlink / "qa-pending.json"),
        "--scout-manifest-path", str(symlink / "scout-coder-manifest.json"),
        "--plan-file", str(tmp_path / "plan.txt"),
        "--feature-file", str(tmp_path / "feature.txt"),
        "--agent-prompt", str(tmp_path / "agent.md"),
        "--timeout", "1",
    ]
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    rc = agents.launch_codex_implement_main(args)
    assert rc == 2
    assert "parent is not a directory" in capsys.readouterr().err


def test_codex_launcher_rejects_transcript_parent_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    outdir = tmp_path / "out"
    outdir.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    for name in ("plan.txt", "feature.txt", "agent.md"):
        (tmp_path / name).write_text("---\ndescription: x\n---\nbody\n", encoding="utf-8")
    args = [
        "--transcript-path", str(other / "transcript.txt"),
        "--sidecar-log", str(tmp_path / "sidecar.log"),
        "--manifest-path", str(outdir / "manifest.json"),
        "--qa-pending-path", str(outdir / "qa-pending.json"),
        "--scout-manifest-path", str(outdir / "scout-coder-manifest.json"),
        "--plan-file", str(tmp_path / "plan.txt"),
        "--feature-file", str(tmp_path / "feature.txt"),
        "--agent-prompt", str(tmp_path / "agent.md"),
        "--timeout", "1",
    ]
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    rc = agents.launch_codex_implement_main(args)
    assert rc == 2
    assert "must share the parent directory" in capsys.readouterr().err


def test_codex_launcher_codex_home_outside_implement_tmpdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    args = _launcher_args(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setattr(agents.shutil, "which", lambda name: "/usr/bin/codex" if name == "codex" else "/bin/true")
    monkeypatch.setattr(_ci_launcher, "_record_implement_timing", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_ci_launcher, "_record_usage_from_events", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_run_external, "_mirror_codex_quota_from_events", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_ci_launcher, "_promote_inner_done", lambda *_args, **_kwargs: None)
    captured: dict[str, str] = {}

    def fake_run_external_agent_with_auth_retries(**kwargs):  # type: ignore[no-untyped-def]
        captured["home"] = agents.os.environ["CODEX_HOME"]
        output = kwargs["output"]
        stdout_path = kwargs["stdout_path"]
        output.write_text("codex transcript\n", encoding="utf-8")
        stdout_path.write_text('{"type":"turn_completed"}\n', encoding="utf-8")
        return agents.RunExternalAgentResult(0, output)

    monkeypatch.setattr(_ci_launcher, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)
    rc = agents.launch_codex_implement_main(args)
    assert rc == 0
    home = Path(captured["home"]).resolve()
    assert not str(home).startswith(str(tmp_path.resolve()))


def test_codex_launcher_env_key_auth_argv_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    args = _launcher_args(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(agents.shutil, "which", lambda name: "/usr/bin/codex" if name == "codex" else "/bin/true")
    monkeypatch.setattr(_ci_launcher, "_record_implement_timing", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_ci_launcher, "_record_usage_from_events", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_run_external, "_mirror_codex_quota_from_events", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_ci_launcher, "_promote_inner_done", lambda *_args, **_kwargs: None)
    captured: dict[str, object] = {}

    def fake_run_external_agent_with_auth_retries(**kwargs):  # type: ignore[no-untyped-def]
        cmd = list(kwargs["cmd"])
        captured["cmd"] = cmd
        captured["config"] = (Path(agents.os.environ["CODEX_HOME"]) / "config.toml").read_text(encoding="utf-8")
        output = kwargs["output"]
        stdout_path = kwargs["stdout_path"]
        output.write_text("ok\n", encoding="utf-8")
        stdout_path.write_text('{"type":"turn_completed"}\n', encoding="utf-8")
        return agents.RunExternalAgentResult(0, output)

    monkeypatch.setattr(_ci_launcher, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)
    rc = agents.launch_codex_implement_main(args)
    assert rc == 0
    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert 'model_provider="openai-larch-env"' in cmd
    config = str(captured["config"])
    assert "api_key" not in config
    assert "OPENAI_API_KEY" not in config


def test_cursor_launcher_continues_when_config_copy_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    args = _launcher_args(tmp_path)
    monkeypatch.setattr(agents.shutil, "which", lambda name: "/usr/bin/cursor" if name == "cursor" else "/bin/true")
    monkeypatch.setattr(_ci_launcher, "cursor_auth_preflight", lambda **_kwargs: agents.AuthVerdict(ok=True, rc=0, message=""))
    monkeypatch.setattr(_ci_launcher, "cursor_preread_service_token", lambda: True)
    monkeypatch.setattr(_ci_launcher, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(_ci_launcher, "_record_implement_timing", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_ci_launcher, "_record_cursor_implement_usage", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_ci_launcher, "_promote_inner_done", lambda *_args, **_kwargs: None)

    def boom_copy(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise OSError("permission denied")

    real_is_file = Path.is_file

    def selective_is_file(self: Path) -> bool:
        if str(self).endswith(".cursor/cli-config.json"):
            return True
        return real_is_file(self)

    monkeypatch.setattr(agents.shutil, "copyfile", boom_copy)
    monkeypatch.setattr(Path, "is_file", selective_is_file)

    def fake_run_external_agent_with_auth_retries(**kwargs):  # type: ignore[no-untyped-def]
        output = kwargs["output"]
        output.write_text('{"usage":{"inputTokens":1}}\n', encoding="utf-8")
        return agents.RunExternalAgentResult(0, output)

    monkeypatch.setattr(_ci_launcher, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)
    rc = agents.launch_cursor_implement_main(args)
    assert rc == 0
    assert "LAUNCHER_EXIT=0" in capsys.readouterr().out


def test_auth_retry_includes_stderr_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "out.txt"
    stderr_path = tmp_path / "sidecar.log"
    stderr_path.write_text("auth error\n", encoding="utf-8")
    seen: list[Path] = []

    def fake_verdict(_tool: str, *paths: Path) -> str:
        seen.extend(paths)
        return "auth" if stderr_path in paths else ""

    def fake_run_external_agent(**_kwargs):  # type: ignore[no-untyped-def]
        return agents.RunExternalAgentResult(2, output)

    monkeypatch.setattr(_run_external, "external_auth_verdict", fake_verdict)
    monkeypatch.setattr(_run_external, "run_external_agent", fake_run_external_agent)
    monkeypatch.setattr(_run_external, "_auth_retry_limit", lambda: 2)
    monkeypatch.setattr(_run_external, "external_startup_lock_acquire", lambda tool: object())  # noqa: ARG005
    monkeypatch.setattr(_run_external, "external_startup_lock_release_after", lambda state: None)  # noqa: ARG005
    result = _run_external._run_external_agent_with_auth_retries(
        tool="codex",
        output=output,
        timeout_seconds=1,
        cmd=["codex", "exec", "hi"],
        stderr_path=stderr_path,
    )
    assert result.exit_code == 2
    assert stderr_path in seen


def test_parse_kv_keeps_first_duplicate_stdout_value() -> None:
    assert implement_dispatch._parse_kv("STATUS=first\nSTATUS=second\nBAD-key=no\n") == {"STATUS": "first"}
