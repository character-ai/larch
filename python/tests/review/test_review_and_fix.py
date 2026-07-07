# pyright: reportUnusedCallResult=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportPrivateUsage=false, reportUnknownLambdaType=false
# ruff: noqa: ARG001, ARG005
# pylint: disable=unused-argument
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest import mock

from larch.calibration import difficulty_calibration
from larch.report import exec_issue_detail
from larch.core import logging_util
import pytest
from larch.review import review_and_fix
from larch.review import review_tally
from larch.review import batch_report
from larch.review import coder_runner
from larch.review import round_runner
from larch.review import snapshot
from _pytest.mark.structures import Mark, MarkDecorator


def _mark(name: str) -> MarkDecorator:
    return MarkDecorator(Mark(name, (), {}, _ispytest=True), _ispytest=True)


MARK_CHECK_CHANGES = _mark("check_changes")
MARK_CONVERGENCE = _mark("convergence")
MARK_DISPATCH = _mark("dispatch")
MARK_LOOP_TIMING = _mark("loop_timing")
MARK_PARSERS = _mark("parsers")
MARK_STARTING_ROUND = _mark("starting_round")
MARK_STEP5 = _mark("step5")
MARK_WRITE_REJECTED = _mark("write_rejected")


def _tmp_impl(tmp_path: Path) -> Path:
    impl = tmp_path / "impl"
    impl.mkdir()
    (impl / "session-env.sh").write_text(
        "RUN_ID=run-1\nCODEX_PRESENT=false\nCURSOR_PRESENT=false\nLARCH_CLAUDE_PLUGIN_ROOT=/tmp/plugin\n",
        encoding="utf-8",
    )
    (impl / "plan.txt").write_text("plan\n", encoding="utf-8")
    (impl / "feature-description.txt").write_text("feature\n", encoding="utf-8")
    return impl


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _arg_value(argv: list[str], flag: str) -> str:
    return argv[argv.index(flag) + 1]


def _write_python3_capture_shim(shim_path: Path) -> None:
    shim_path.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [ -z "${REAL_PYTHON3:-}" ]; then
  printf '%s\n' 'python3 shim: REAL_PYTHON3 is required' >&2
  exit 127
fi
if [ "${2:-}" = "review-and-fix" ] && [ "${3:-}" = "step5" ]; then
  : "${CAPTURE_ARGV_FILE:?CAPTURE_ARGV_FILE required}"
  printf '%s\n' "$@" >"$CAPTURE_ARGV_FILE"
  printf '%s\n' 'STEP5_REVIEW_STATUS=complete' 'STALL_TRACKING=false' 'STALL_REASON=' 'ROUNDS_COMPLETED=1' 'FINAL_ROUND_NUM=1' 'FINAL_REVIEW_AND_FIX_STATUS=complete' 'CODER_STATUS=' 'FILES_CHANGED_HINT=' 'EFFECTIVE_ROUND_CAP=2'
  exit 0
fi
exec "$REAL_PYTHON3" "$@"
""",
        encoding="utf-8",
    )
    shim_path.chmod(0o755)


def _run_step5_shell_wrapper(
    tmp_path: Path,
    *,
    wrapper_name: str,
    wrapper_args: list[str],
    include_run_flags: bool,
) -> tuple[Path, list[str], subprocess.CompletedProcess[str]]:
    repo_root = _repo_root()
    impl = tmp_path / "impl"
    impl.mkdir()
    (impl / "session-env.sh").write_text(
        f"RUN_ID=run-1\nCODEX_PRESENT=false\nCURSOR_PRESENT=false\nLARCH_CLAUDE_PLUGIN_ROOT={repo_root}\n",
        encoding="utf-8",
    )
    (impl / "plan.txt").write_text("plan\n", encoding="utf-8")
    (impl / "feature-description.txt").write_text("feature\n", encoding="utf-8")
    if include_run_flags:
        (impl / "run-flags.sh").write_text("DIFFICULTY_OVERRIDE=HARD\n", encoding="utf-8")

    shim_bin = tmp_path / "bin"
    shim_bin.mkdir()
    capture_file = tmp_path / "captured-argv.txt"
    _write_python3_capture_shim(shim_bin / "python3")

    env = {
        "CAPTURE_ARGV_FILE": str(capture_file),
        "CLAUDE_PLUGIN_ROOT": str(repo_root),
        "IMPLEMENT_TMPDIR": str(impl),
        "LARCH_QUIET_DISABLE": "1",
        "PATH": f"{shim_bin}{os.pathsep}{os.environ.get('PATH', '')}",
        "REAL_PYTHON3": sys.executable,
    }
    for key in ("HOME", "PYTHONPATH", "TMPDIR", "USER"):
        if key in os.environ:
            env[key] = os.environ[key]

    result = subprocess.run(
        [str(repo_root / "skills" / "implement" / "scripts" / wrapper_name), *wrapper_args],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    argv = capture_file.read_text(encoding="utf-8").splitlines() if capture_file.exists() else []
    return impl, argv, result


def _fix_applied_round_result(impl: Path, *, round_num: int = 1) -> review_and_fix.RoundResult:
    round_dir = impl / f"round-{round_num}"
    round_dir.mkdir(parents=True, exist_ok=True)
    return review_and_fix.RoundResult(
        0,
        "fix-applied",
        "fix-required",
        round_num,
        1,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        round_dir / "accepted-findings.md",
        round_dir / "rejected-findings.md",
        round_dir,
        impl / "review-and-fix-summary.json",
        impl / "accumulated-oos.jsonl",
        review_and_fix.CoderResult(0, status="applied", input_count=1),
    )


def _step5_round_result(
    impl: Path,
    *,
    status: str,
    rc: int = 0,
    round_num: int = 1,
) -> review_and_fix.RoundResult:
    round_dir = impl / f"round-{round_num}"
    round_dir.mkdir(parents=True, exist_ok=True)
    return review_and_fix.RoundResult(
        rc,
        status,
        "ok",
        round_num,
        3,
        2,
        1,
        4,
        5,
        6,
        7,
        8,
        round_dir / "accepted-findings.md",
        round_dir / "rejected-findings.md",
        round_dir,
        impl / "review-and-fix-summary.json",
        impl / "accumulated-oos.jsonl",
        review_and_fix.CoderResult(0, status="applied", input_count=3),
    )


def test_review_core_capture_captures_stdout_emit_and_restores_env(tmp_path, monkeypatch):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", "old")
    env_path = tmp_path / "round-1" / "review-core.env"

    def fake_core(argv: list[str]) -> int:
        assert "--round-num" in argv
        print("PRINTED=1")
        logging_util.emit("REVIEW_CORE_STATUS=ok")
        assert os.environ["IMPLEMENT_TMPDIR"] == str(tmp_path)
        return 0

    rc = review_and_fix.review_core_capture(core_args=["--round-num", "1"], env_path=env_path, review_core_impl=fake_core, implement_tmpdir=tmp_path)

    assert rc == 0
    assert "PRINTED=1" in env_path.read_text(encoding="utf-8")
    assert "REVIEW_CORE_STATUS=ok" in env_path.read_text(encoding="utf-8")
    assert os.environ["IMPLEMENT_TMPDIR"] == "old"


@MARK_PARSERS
def test_step5_single_emits_round_kvs_without_review_core_leak(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)

    def fake_core(argv: list[str]) -> int:
        out_dir = Path(argv[argv.index("--output-dir") + 1])
        (out_dir / "accepted-findings.md").write_text("", encoding="utf-8")
        logging_util.emit("REVIEW_CORE_STATUS=ok")
        logging_util.emit("ACCEPTED_COUNT=0")
        logging_util.emit("REJECTED_COUNT=0")
        logging_util.emit(f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}")
        logging_util.emit(f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}")
        return 0

    monkeypatch.setattr(review_and_fix.review_pipeline, "review_core", fake_core)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "single", "--round-num", "1"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "REVIEW_AND_FIX_STATUS=complete" in out
    assert "REVIEW_CORE_STATUS=ok" in out
    assert "ROUND_NUM=1" in out
    assert "REVIEW_CORE_STATUS=ok\nACCEPTED_COUNT" not in out
    assert (impl / "round-1" / "review-core.env").is_file()
    assert (impl / "progress" / "done").is_file()


@MARK_LOOP_TIMING
def test_step5_loop_emits_single_final_envelope(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)

    def fake_core(argv: list[str]) -> int:
        out_dir = Path(argv[argv.index("--output-dir") + 1])
        (out_dir / "accepted-findings.md").write_text("", encoding="utf-8")
        logging_util.emit("REVIEW_CORE_STATUS=ok")
        logging_util.emit("ACCEPTED_COUNT=0")
        logging_util.emit("REJECTED_COUNT=0")
        logging_util.emit(f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}")
        logging_util.emit(f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}")
        return 0

    monkeypatch.setattr(review_and_fix.review_pipeline, "review_core", fake_core)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1"])

    out = capsys.readouterr().out
    assert rc == 0
    assert out.count("STEP5_REVIEW_STATUS=") == 1
    assert "STEP5_REVIEW_STATUS=complete" in out
    assert "EFFECTIVE_ROUND_CAP=2" in out
    assert not any(line.startswith("REVIEW_AND_FIX_STATUS=") for line in out.splitlines())


@MARK_LOOP_TIMING
def test_step5_loop_writes_mergeable_completion_kvs(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)

    def fake_core(argv: list[str]) -> int:
        out_dir = Path(argv[argv.index("--output-dir") + 1])
        (out_dir / "accepted-findings.md").write_text("", encoding="utf-8")
        logging_util.emit("REVIEW_CORE_STATUS=ok")
        logging_util.emit("ACCEPTED_COUNT=0")
        logging_util.emit("REJECTED_COUNT=0")
        logging_util.emit(f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}")
        logging_util.emit(f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}")
        return 0

    monkeypatch.setattr(review_and_fix.review_pipeline, "review_core", fake_core)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1"])

    result_lines = (impl / ".step5-review-result.env").read_text(encoding="utf-8").splitlines()
    result = dict(line.split("=", 1) for line in result_lines)

    assert rc == 0
    assert result["STEP5_REVIEW_STATUS"] == "complete"
    assert result["STALL_TRACKING"] == "false"
    assert result["STALL_REASON"] == ""
    assert result["ROUNDS_COMPLETED"] == "1"
    assert result["FINAL_ROUND_NUM"] == "1"
    assert result["FINAL_REVIEW_AND_FIX_STATUS"] == "complete"
    assert result["EFFECTIVE_ROUND_CAP"] == "2"
    assert all("=" in line for line in result_lines)
    assert not any(line.startswith(">") for line in result_lines)
    assert "STEP5_REVIEW_STATUS=complete" in capsys.readouterr().out


@MARK_STEP5
def test_step5_loop_preflight_failure_writes_result_env(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    (impl / "plan.txt").unlink()

    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1"])

    out = capsys.readouterr().out
    result_env = impl / ".step5-review-result.env"
    result = dict(line.split("=", 1) for line in result_env.read_text(encoding="utf-8").splitlines())
    assert rc == 2
    assert result["STEP5_REVIEW_STATUS"] == "stall"
    assert result["STALL_TRACKING"] == "false"
    assert result["STALL_REASON"] == "preflight-failed"
    assert "STEP5_REVIEW_STATUS=stall" in out


@MARK_DISPATCH
def test_apply_findings_empty_file_contract(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    findings = tmp_path / "findings.md"
    findings.write_text("", encoding="utf-8")
    rc = review_and_fix.apply_findings(["--findings-file", str(findings), "--review-tmpdir", str(tmp_path / "review")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "REVIEW_AND_FIX_STATUS=no-findings" in out
    assert "CODER_STATUS=skipped" in out


@MARK_CHECK_CHANGES
def test_check_changes_parse_error_stable_kvs(monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    rc = review_and_fix.check_changes(["--bogus"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.splitlines() == [
        "FILES_CHANGED=false",
        "UNTRACKED_BASELINE=missing",
        "GIT_PROBE_FAILED=false",
    ]


@MARK_WRITE_REJECTED
def test_write_rejected_counts_and_copies(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = tmp_path / "impl"
    impl.mkdir()
    (impl / "rejected-findings.md").write_text("### [Code Review] One\nbody\n", encoding="utf-8")
    rc = review_and_fix.write_rejected([
        "--implement-tmpdir", str(impl),
        "--run-id", "run-1",
        "--log-root", str(tmp_path / "logs"),
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "REJECTED_COUNT=1" in out
    assert "STATUS=ok" in out
    assert (tmp_path / "logs" / "implement" / "run-1" / "rejected-findings.md").is_file()


def test_review_and_fix_source_uses_in_process_review_core():
    raf_source = Path(review_and_fix.__file__).read_text(encoding="utf-8")
    rr_source = Path(round_runner.__file__).read_text(encoding="utf-8")
    assert '"review", "core"' not in raf_source
    assert '"review", "core"' not in rr_source
    assert "python/cli.py review core" not in raf_source
    assert "python/cli.py review core" not in rr_source
    assert "review_core_capture" in raf_source  # present via import
    assert "--prune-ledger" in rr_source  # in _core_args_for_round


@MARK_DISPATCH
def test_compose_coder_prompt_uses_canonical_submodule_prohibition(tmp_path):
    submodules = ["vendor/foo"]
    body = review_and_fix._compose_coder_prompt(prompt_file=tmp_path / "prompt.md", findings_file=tmp_path / "f.md", round_dir=tmp_path, submodules=submodules)
    assert "Do NOT read, edit, create, delete, move" in body
    assert "Do NOT touch `.git/`" in body


@MARK_DISPATCH
def test_resolve_coder_timing_ledger_round_and_flat_layouts(tmp_path: Path) -> None:
    assert review_and_fix._resolve_coder_timing_ledger(tmp_path / "round-1") == tmp_path / "timing-ledger.tsv"
    flat = tmp_path / "review-flat"
    assert review_and_fix._resolve_coder_timing_ledger(flat) == flat / "timing-ledger.tsv"


@MARK_DISPATCH
def test_run_coder_codex_rejects_nonzero_launcher_exit(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_PRESENT", "true")
    monkeypatch.setattr(coder_runner, "_codex_available", lambda: True)
    output = tmp_path / "coder-codex.log"
    output.write_text("ok\n", encoding="utf-8")

    def fake_run(_argv, **_kwargs):
        class Result:
            returncode = 0
            stdout = "LAUNCHER_EXIT=1\n"
            stderr = ""

        return Result()

    monkeypatch.setattr(coder_runner, "_run", fake_run)
    assert coder_runner._run_coder_codex(round_dir=tmp_path, prompt_body="prompt", tool_log=tmp_path / "tool.log") is False


@MARK_DISPATCH
def test_run_coder_codex_exports_resolved_timing_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    output = round_dir / "coder-codex.log"
    output.write_text("ok\n", encoding="utf-8")
    seen_env: dict[str, str] = {}
    seen_argv: list[str] = []
    monkeypatch.setenv("CODEX_BINARY_FOUND", "true")
    monkeypatch.setattr(coder_runner, "_codex_available", lambda: True)

    def fake_run(argv: list[str], **kwargs: object) -> review_and_fix.proc.CommandResult:
        seen_argv[:] = argv
        seen_env.update(kwargs.get("env") or {})  # type: ignore[arg-type]
        return review_and_fix.proc.CommandResult(tuple(argv), 0, "LAUNCHER_EXIT=0\n", "", 0.0)

    monkeypatch.setattr(coder_runner, "_run", fake_run)

    assert coder_runner._run_coder_codex(round_dir=round_dir, prompt_body="prompt", tool_log=round_dir / "tool.log") is True
    assert seen_env["LARCH_TIMING_LEDGER"] == str(tmp_path / "timing-ledger.tsv")
    assert seen_env["IMPLEMENT_TMPDIR"] == str(tmp_path)
    assert seen_argv[seen_argv.index("--model-role") + 1] == "fix"


@MARK_DISPATCH
def test_run_coder_codex_overrides_stale_implement_tmpdir_in_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    round_dir = tmp_path / "impl-session" / "round-1"
    round_dir.mkdir(parents=True)
    stale = tmp_path / "stale-implement"
    stale.mkdir()
    output = round_dir / "coder-codex.log"
    output.write_text("ok\n", encoding="utf-8")
    seen_env: dict[str, str] = {}
    monkeypatch.setenv("CODEX_BINARY_FOUND", "true")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(stale))
    monkeypatch.setattr(coder_runner, "_codex_available", lambda: True)

    def fake_run(argv: list[str], **kwargs: object) -> review_and_fix.proc.CommandResult:
        seen_env.update(kwargs.get("env") or {})  # type: ignore[arg-type]
        return review_and_fix.proc.CommandResult(tuple(argv), 0, "LAUNCHER_EXIT=0\n", "", 0.0)

    monkeypatch.setattr(coder_runner, "_run", fake_run)

    assert coder_runner._run_coder_codex(round_dir=round_dir, prompt_body="prompt", tool_log=round_dir / "tool.log") is True
    assert seen_env["IMPLEMENT_TMPDIR"] == str(round_dir.parent)
    assert seen_env["LARCH_TIMING_LEDGER"] == str(round_dir.parent / "timing-ledger.tsv")


@MARK_DISPATCH
def test_run_coder_claude_uses_write_capable_review_fix_launcher(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    seen_argv: list[str] = []
    seen_env: dict[str, str] = {}
    monkeypatch.setattr(coder_runner.shutil, "which", lambda name: "/usr/bin/claude" if name == "claude" else None)

    def fake_run(argv: list[str], **kwargs: object) -> review_and_fix.proc.CommandResult:
        seen_argv[:] = argv
        seen_env.update(kwargs.get("env") or {})  # type: ignore[arg-type]
        output = Path(argv[argv.index("--output") + 1])
        output.write_text("APPLIED: FINDING_1\n", encoding="utf-8")
        return review_and_fix.proc.CommandResult(tuple(argv), 0, "LAUNCHER_EXIT=0\n", "", 0.0)

    monkeypatch.setattr(coder_runner, "_run", fake_run)

    assert coder_runner._run_coder_claude(round_dir=round_dir, prompt_body="prompt", tool_log=round_dir / "tool.log") is True
    assert seen_argv[:4] == ["python3", str(review_and_fix._plugin_root() / "python" / "cli.py"), "agent", "launch-claude-review-fix"]
    assert "launch-claude-review" not in seen_argv
    assert seen_argv[seen_argv.index("--timing-task-kind") + 1] == "claude-review-fix"
    assert seen_env["LARCH_TIMING_LEDGER"] == str(tmp_path / "timing-ledger.tsv")
    assert (round_dir / "tool.log").read_text(encoding="utf-8") == "APPLIED: FINDING_1\n"


@MARK_DISPATCH
def test_dynamic_archetypes_defaults_to_one_with_implement_tmpdir(monkeypatch, tmp_path):
    monkeypatch.delenv("LARCH_DYNAMIC_ARCHETYPES_MAX", raising=False)
    impl = _tmp_impl(tmp_path)
    args = mock.Mock(dynamic_archetypes="", session_env_path="")
    assert review_and_fix._dynamic_archetypes(args=args, implement_tmpdir=impl) == "1"



@MARK_DISPATCH
def test_dynamic_archetypes_uses_exported_env(monkeypatch, tmp_path):
    monkeypatch.setenv("LARCH_DYNAMIC_ARCHETYPES_MAX", "1")
    impl = _tmp_impl(tmp_path)
    args = mock.Mock(dynamic_archetypes="", session_env_path="")
    assert review_and_fix._dynamic_archetypes(args=args, implement_tmpdir=impl) == "1"


@MARK_DISPATCH
def test_dynamic_archetypes_rejects_over_cap_env(monkeypatch, tmp_path):
    monkeypatch.setenv("LARCH_DYNAMIC_ARCHETYPES_MAX", "2")
    impl = _tmp_impl(tmp_path)
    args = mock.Mock(dynamic_archetypes="", session_env_path="")
    with pytest.raises(ValueError, match="integer from 0 to 1"):
        review_and_fix._dynamic_archetypes(args=args, implement_tmpdir=impl)


def test_step5_shell_exports_validated_dynamic_cap_before_python_call() -> None:
    text = (Path(__file__).resolve().parents[3] / "skills/implement/scripts/step-5-review.sh").read_text(encoding="utf-8")
    validation = 'case "$dynamic_archetypes_cap" in [0-1])'
    export = 'export LARCH_DYNAMIC_ARCHETYPES_MAX="$dynamic_archetypes_cap"'
    banner = "dynamic-archetypes cap=%s"
    python_call = "--starting-round 1"
    assert validation in text
    assert export in text
    assert text.index(validation) < text.index(export) < text.index(banner) < text.index(python_call)


@MARK_STEP5
def test_step5_new_process_group_invokes_setsid(monkeypatch, tmp_path):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    called = []
    monkeypatch.setattr(review_and_fix.os, "setsid", lambda: called.append("setsid"))
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--new-process-group", "--orphan-timeout-s", "0"])
    assert called == ["setsid"]
    assert rc == 2


@MARK_STEP5
def test_step5_new_process_group_unavailable_exits_2(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    monkeypatch.delattr(review_and_fix.os, "setsid", raising=False)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--new-process-group", "--orphan-timeout-s", "1"])
    assert rc == 2
    assert "os.setsid is unavailable" in capsys.readouterr().err


@MARK_STEP5
def test_step5_new_process_group_oserror_exits_2(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)

    def failing_setsid() -> None:
        raise OSError("boom")

    monkeypatch.setattr(review_and_fix.os, "setsid", failing_setsid)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--new-process-group", "--orphan-timeout-s", "1"])
    assert rc == 2
    assert "boom" in capsys.readouterr().err


@MARK_STEP5
def test_step5_invalid_orphan_timeout_fails_closed(tmp_path, capsys):
    impl = _tmp_impl(tmp_path)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--orphan-timeout-s", "0"])
    assert rc == 2
    assert "--orphan-timeout-s must be positive" in capsys.readouterr().err


@MARK_STEP5
def test_step5_orphan_timeout_emits_stall(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    marker = impl / ".step5-wrapper-detached"
    old_epoch = time.time() - 10
    marker.write_text(f"PID=123\nSTDOUT_FILE=/tmp/out\nDETACHED_AT_EPOCH={int(old_epoch)}\n", encoding="utf-8")
    now = time.time()
    os.utime(marker, (now, now))
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--orphan-timeout-s", "1"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "STEP5_REVIEW_STATUS=stall" in out
    assert "STALL_REASON=orphan-timeout" in out


@MARK_STEP5
def test_step5_normalize_status_replays_envelope(tmp_path, capsys):
    impl = _tmp_impl(tmp_path)
    stdout_file = tmp_path / "stdout.txt"
    stdout_file.write_text("STEP5_REVIEW_STATUS=complete\nROUNDS_COMPLETED=1\n", encoding="utf-8")
    rc = review_and_fix.normalize_status(["--implement-tmpdir", str(impl), "--stdout-file", str(stdout_file), "--loop-rc", "0"])
    result_env = impl / ".step5-review-result.env"
    assert rc == 0
    assert result_env.is_file()
    assert "STEP5_REVIEW_STATUS=complete" in result_env.read_text(encoding="utf-8")
    assert "STEP5_REVIEW_STATUS=complete" in capsys.readouterr().out


@MARK_STEP5
def test_step5_normalize_status_writes_terminal_sentinel_for_nonzero_loop_rc(tmp_path, capsys):
    impl = _tmp_impl(tmp_path)
    stdout_file = tmp_path / "stdout.txt"
    stdout_file.write_text("STEP5_REVIEW_STATUS=complete\nROUNDS_COMPLETED=1\n", encoding="utf-8")
    rc = review_and_fix.normalize_status(["--implement-tmpdir", str(impl), "--stdout-file", str(stdout_file), "--loop-rc", "7"])
    assert rc == 7
    assert (impl / ".completed" / "step-5-terminal").is_file()
    assert "STEP5_REVIEW_STATUS=complete" in capsys.readouterr().out


@MARK_STEP5
@pytest.mark.parametrize(
    ("stdout_contents", "expected_reason"),
    [
        pytest.param(None, "missing-captured-stdout", id="missing-file"),
        pytest.param("ROUNDS_COMPLETED=1\n", "missing-step5-envelope", id="missing-envelope"),
    ],
)
def test_step5_normalize_status_failure_sets_stall_tracking_true(
    tmp_path,
    capsys,
    stdout_contents: str | None,
    expected_reason: str,
) -> None:
    impl = _tmp_impl(tmp_path)
    stdout_file = tmp_path / "stdout.txt"
    if stdout_contents is not None:
        stdout_file.write_text(stdout_contents, encoding="utf-8")
    rc = review_and_fix.normalize_status(["--implement-tmpdir", str(impl), "--stdout-file", str(stdout_file), "--loop-rc", "0"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "STALL_TRACKING=true" in out
    assert f"STALL_REASON={expected_reason}" in out


@MARK_STEP5
@pytest.mark.parametrize(
    ("wrapper_name", "wrapper_args", "expected_starting_round", "include_run_flags"),
    [
        pytest.param("step-5-review.sh", [], "1", True, id="review-difficulty-override"),
        pytest.param("step-5-review.sh", [], "1", False, id="review-no-override"),
        pytest.param("step-5-resume.sh", ["--final-round-num", "2"], "3", True, id="resume-difficulty-override"),
        pytest.param("step-5-resume.sh", ["--final-round-num", "2"], "3", False, id="resume-no-override"),
    ],
)
def test_step5_shell_wrappers_forward_difficulty_override(
    tmp_path: Path,
    wrapper_name: str,
    wrapper_args: list[str],
    expected_starting_round: str,
    include_run_flags: bool,
) -> None:
    impl, argv, result = _run_step5_shell_wrapper(
        tmp_path,
        wrapper_name=wrapper_name,
        wrapper_args=wrapper_args,
        include_run_flags=include_run_flags,
    )

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert argv, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert Path(argv[0]).as_posix().endswith("/python/cli.py")
    assert argv[1:3] == ["review-and-fix", "step5"]
    assert _arg_value(argv, "--implement-tmpdir") == str(impl)
    assert _arg_value(argv, "--mode") == "loop"
    assert _arg_value(argv, "--starting-round") == expected_starting_round
    if wrapper_name == "step-5-review.sh":
        assert "--new-process-group" in argv
        assert _arg_value(argv, "--orphan-timeout-s") == "7200"
    if include_run_flags:
        assert _arg_value(argv, "--difficulty") == "HARD"
    else:
        assert "--difficulty" not in argv

@MARK_DISPATCH
def test_dynamic_archetypes_defaults_to_zero_without_implement_tmpdir(monkeypatch, tmp_path):
    monkeypatch.delenv("LARCH_DYNAMIC_ARCHETYPES_MAX", raising=False)
    args = mock.Mock(dynamic_archetypes="", session_env_path="")
    assert review_and_fix._dynamic_archetypes(args=args, implement_tmpdir=tmp_path / "missing") == "0"


@MARK_DISPATCH
def test_post_dispatch_submodule_revert_restores_tracked_path_with_trailing_slash(tmp_path, monkeypatch):
    sub = tmp_path / "vendor"
    sub.mkdir()
    (sub / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    monkeypatch.setattr(coder_runner, "_capture_round_tracked_paths", lambda: ["vendor/tracked.txt"])
    monkeypatch.setattr(coder_runner, "_capture_round_untracked_paths", list)
    monkeypatch.setattr(coder_runner, "_run", lambda argv, **_kw: review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0))  # type: ignore[arg-type]
    count = coder_runner._post_dispatch_submodule_revert(round_dir=round_dir, submodules=["vendor"])
    assert count == 1


@MARK_STEP5
def test_step5_handoff_envelope_uses_false_stall_tracking(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)

    def fake_round(args, *, suppress_emit, review_core_impl=None):
        del args, suppress_emit, review_core_impl
        return review_and_fix.RoundResult(
            0, "coder-main-agent-required", "fix-required", 1, 1, 0, 0, 0, 1, 0, 0, 0,
            impl / "round-1" / "accepted-findings.md",
            impl / "round-1" / "rejected-findings.md",
            impl / "round-1",
            impl / "review-and-fix-summary.json",
            impl / "accumulated-oos.jsonl",
            review_and_fix.CoderResult(4, status="main-agent-required"),
        )

    monkeypatch.setattr(review_and_fix, "_run_round", fake_round)
    monkeypatch.setattr(review_and_fix, "record_round_timing", lambda _argv: 0)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1", "--round-cap", "1"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "STEP5_REVIEW_STATUS=coder-main-agent-required" in out
    assert "STALL_TRACKING=false" in out


@MARK_STEP5
def test_round_runner_maps_zero_survivor_panel_failed_to_self_review_required(tmp_path, monkeypatch):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    args = argparse.Namespace(
        implement_tmpdir=str(impl),
        session_env_path=str(impl / "session-env.sh"),
        codex_available="true",
        cursor_available="true",
        round_num="1",
        dynamic_archetypes="0",
        pre_scouted_manifest="",
        diff_file="",
        commit_count="0",
        plan_file=str(impl / "plan.txt"),
        feature_file=str(impl / "feature-description.txt"),
        run_id="",
        round_cap="2",
    )

    def fake_core(argv: list[str]) -> int:
        out_dir = Path(argv[argv.index("--output-dir") + 1])
        (out_dir / "accepted-findings.md").write_text("", encoding="utf-8")
        (out_dir / "rejected-findings.md").write_text("", encoding="utf-8")
        logging_util.emit("REVIEW_CORE_STATUS=panel-failed")
        logging_util.emit("THRESHOLD_REASON=no successful launched reviewer output")
        logging_util.emit("ACCEPTED_COUNT=0")
        logging_util.emit("REJECTED_COUNT=0")
        logging_util.emit(f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}")
        logging_util.emit(f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}")
        return 2

    result = round_runner._run_round(args, suppress_emit=True, review_core_impl=fake_core)

    assert result.rc == 0
    assert result.status == "self-review-required"
    assert result.core_status == "panel-failed"


@MARK_STEP5
def test_step5_zero_survivor_emits_self_review_required_without_stall(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    events: list[str] = []
    timing_calls: list[list[str]] = []
    flush_calls: list[dict[str, object]] = []
    now = {"value": 10}

    def fake_time() -> int:
        now["value"] += 1
        return now["value"]

    def fake_round(args, *, suppress_emit, review_core_impl=None):
        del args, suppress_emit, review_core_impl
        events.append("round")
        return review_and_fix.RoundResult(
            0, "self-review-required", "panel-failed", 1, 0, 0, 0, 0, 0, 0, 0, 0,
            impl / "round-1" / "accepted-findings.md",
            impl / "round-1" / "rejected-findings.md",
            impl / "round-1",
            impl / "review-and-fix-summary.json",
            impl / "accumulated-oos.jsonl",
            review_and_fix.CoderResult(0),
        )

    def fake_record(argv):
        events.append("timing")
        timing_calls.append(argv)
        return 0

    def fake_flush(**kwargs):
        events.append("flush")
        flush_calls.append(kwargs)
        return True

    monkeypatch.setattr(review_and_fix.time, "time", fake_time)
    monkeypatch.setattr(review_and_fix, "_run_round", fake_round)
    monkeypatch.setattr(review_and_fix, "record_round_timing", fake_record)
    monkeypatch.setattr(review_and_fix, "flush_review_batches", fake_flush)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1", "--round-cap", "1"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "STEP5_REVIEW_STATUS=self-review-required" in out
    assert "FINAL_REVIEW_AND_FIX_STATUS=self-review-required" in out
    assert "STALL_TRACKING=false" in out
    assert "STALL_REASON=\n" in out
    assert events == ["round", "timing", "flush"]
    assert len(timing_calls) == 1
    timing_call = timing_calls[0]
    assert timing_call[timing_call.index("--round") + 1] == "1"
    assert timing_call[timing_call.index("--start-s") + 1] == "11"
    assert len(flush_calls) == 1
    assert flush_calls[0]["rounds"] == 1


@MARK_STEP5
def test_step5_static_panel_failed_still_stalls(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)

    def fake_round(args, *, suppress_emit, review_core_impl=None):
        del args, suppress_emit, review_core_impl
        return review_and_fix.RoundResult(
            2, "panel-failed", "panel-failed", 1, 0, 0, 0, 0, 0, 0, 0, 0,
            impl / "round-1" / "accepted-findings.md",
            impl / "round-1" / "rejected-findings.md",
            impl / "round-1",
            impl / "review-and-fix-summary.json",
            impl / "accumulated-oos.jsonl",
            review_and_fix.CoderResult(0),
        )

    monkeypatch.setattr(review_and_fix, "_run_round", fake_round)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1", "--round-cap", "1"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "STEP5_REVIEW_STATUS=stall" in out
    assert "STALL_TRACKING=true" in out
    assert "STALL_REASON=panel-failed" in out


@MARK_STARTING_ROUND
def test_step5_starting_round_missing_prior_emits_invalid(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    rc = review_and_fix.step5([
        "--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "3", "--round-cap", "2",
    ])
    out = capsys.readouterr().out
    assert rc == 2
    assert "STEP5_REVIEW_STATUS=stall" in out
    assert "STALL_REASON=starting-round-invalid" in out


@MARK_STARTING_ROUND
def test_step5_resume_past_cap_with_prior_artifact(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    prior = impl / "round-2" / "review-and-fix.env"
    prior.parent.mkdir(parents=True)
    prior.write_text("REVIEW_AND_FIX_STATUS=main-agent-vote-required\n", encoding="utf-8")
    rc = review_and_fix.step5([
        "--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "3", "--round-cap", "2",
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "STEP5_REVIEW_STATUS=mav-resume-past-cap" in out


@MARK_STEP5
def test_mav_apply_writes_full_pre_coder_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    findings = impl / "accepted.md"
    findings.write_text("### FINDING_1: x\n- **Severity**: nit\n", encoding="utf-8")
    monkeypatch.setattr(review_and_fix, "apply_findings_with_coder", lambda *a, **k: review_and_fix.CoderResult(0, status="no-changes"))  # type: ignore[arg-type]
    monkeypatch.setattr(snapshot, "_git_head", lambda: "abc123")
    monkeypatch.setattr(snapshot, "_capture_round_tracked_paths", list)
    monkeypatch.setattr(snapshot, "_capture_round_untracked_paths", list)
    rc = review_and_fix.step5([
        "--implement-tmpdir", str(impl), "--mode", "mav-apply", "--round-num", "1", "--findings-file", str(findings),
    ])
    snap = review_and_fix.pre_coder_snapshot_dir(impl / "round-1")
    assert rc == 0
    assert (snap / "pre-coder-head.txt").is_file()
    assert (snap / "pre-coder-tracked-paths.txt").is_file()
    assert (snap / "pre-coder-untracked-paths.txt").is_file()
    assert not (impl / "round-1" / "pre-coder-head.txt").exists()


@MARK_WRITE_REJECTED
def test_write_rejected_redacts_tmpdir_and_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = tmp_path / "impl"
    impl.mkdir()
    secret = "sk-" + "a" * 40
    (impl / "rejected-findings.md").write_text(f"### [Code Review] One\n{tmp_path}/secret {secret}\n", encoding="utf-8")
    rc = review_and_fix.write_rejected([
        "--implement-tmpdir", str(impl),
        "--run-id", "run-1",
        "--log-root", str(tmp_path / "logs"),
    ])
    dest = tmp_path / "logs" / "implement" / "run-1" / "rejected-findings.md"
    text = dest.read_text(encoding="utf-8")
    assert rc == 0
    assert secret not in text
    assert "<REDACTED-TOKEN>" in text


@MARK_CONVERGENCE
def test_step5_post_round_substantial_at_cap_emits_cap_hit(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    snap = review_and_fix.pre_coder_snapshot_dir(round_dir)
    snap.mkdir(parents=True)
    (snap / "pre-coder-head.txt").write_text("head\n", encoding="utf-8")
    (round_dir / "post-coder-head.txt").write_text("head\n", encoding="utf-8")
    accepted = round_dir / "accepted-findings.md"
    accepted.write_text("### FINDING_1: a **Important**\n### FINDING_2: b **Important**\n", encoding="utf-8")
    result = review_and_fix.RoundResult(
        0, "fix-applied", "fix-required", 1, 2, 0, 0, 0, 2, 0, 0, 0,
        accepted, round_dir / "rejected-findings.md", round_dir,
        impl / "review-and-fix-summary.json", impl / "accumulated-oos.jsonl",
        review_and_fix.CoderResult(0, input_count=2, status="applied"),
    )
    status, _reason, cont = review_and_fix._step5_post_round_gates(result=result, round_num=2, round_cap=2)
    assert status == "cap-hit"
    assert cont is False


@MARK_DISPATCH
def test_process_skipped_findings_routes_security_vs_oos(tmp_path):
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    in_scope = round_dir / "accepted-in-scope-findings.md"
    in_scope.write_text("### FINDING_1: [security] x\n- focus-area: security\n", encoding="utf-8")
    coder_log = round_dir / "coder-output.log"
    coder_log.write_text("SKIPPED: FINDING_1\n", encoding="utf-8")
    impl = tmp_path / "impl"
    impl.mkdir()
    count, failed = review_and_fix._process_skipped_findings(round_dir=round_dir, in_scope_file=in_scope, coder_log=coder_log, implement_tmpdir=impl)
    assert failed is False
    assert count == 1
    assert (round_dir / "skipped-findings.security.md").stat().st_size > 0
    assert not (impl / "accumulated-oos.md").exists()


@MARK_DISPATCH
def test_process_skipped_findings_mirrors_security_aggregate_across_rounds(tmp_path):
    impl = tmp_path / "impl"
    impl.mkdir()
    for round_num, finding_id in ((1, "FINDING_1"), (2, "FINDING_2")):
        round_dir = impl / f"round-{round_num}"
        round_dir.mkdir()
        in_scope = round_dir / "accepted-in-scope-findings.md"
        in_scope.write_text(f"### {finding_id}: [security] x\n- focus-area: security\n", encoding="utf-8")
        coder_log = round_dir / "coder-output.log"
        coder_log.write_text(f"SKIPPED: {finding_id}\n", encoding="utf-8")
        count, failed = review_and_fix._process_skipped_findings(round_dir=round_dir, in_scope_file=in_scope, coder_log=coder_log, implement_tmpdir=impl)
        assert failed is False
        assert count == 1
    aggregate = (impl / "skipped-security-findings.md").read_text(encoding="utf-8")
    assert "FINDING_1" in aggregate
    assert "FINDING_2" in aggregate
    assert not (impl / "accumulated-oos.md").exists()


def test_surface_parse_failed_warning_calls_surface_warning_when_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, str]] = []

    def fake_surface_warning(*, session_env_path: str, entry: str) -> None:
        calls.append({"session_env_path": session_env_path, "entry": entry})

    monkeypatch.setattr(review_tally, "surface_warning", fake_surface_warning)
    core = {"PARSE_FAILED_COUNT": "2"}
    review_and_fix._surface_parse_failed_warning(core=core, round_num=3, session_env_path="/tmp/session-env.sh")
    assert len(calls) == 1
    assert "round 3" in calls[0]["entry"]
    assert "2 voter slot(s)" in calls[0]["entry"]


def test_surface_parse_failed_warning_skips_when_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, str]] = []

    def fake_surface_warning(*, session_env_path: str, entry: str) -> None:
        calls.append({"session_env_path": session_env_path, "entry": entry})

    monkeypatch.setattr(review_tally, "surface_warning", fake_surface_warning)
    review_and_fix._surface_parse_failed_warning(core={"PARSE_FAILED_COUNT": "0"}, round_num=1, session_env_path="/tmp/session-env.sh")
    assert not calls


def test_surface_dropped_reviewer_warning_uses_dynamic_counters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_surface_warning(*, session_env_path: str, entry: str) -> None:
        calls.append(entry)

    monkeypatch.setattr(review_tally, "surface_warning", fake_surface_warning)
    attempts = tmp_path / "dropped-reviewer-attempts.env"
    attempts.write_text("DYNAMIC_FAILED_SLOTS=1\nDYNAMIC_DROPPED_SLOTS=0\n", encoding="utf-8")

    review_and_fix._surface_dropped_reviewer_warning(  # pyright: ignore[reportPrivateUsage]
        core={},
        round_num=2,
        session_env_path="/tmp/session-env.sh",
        attempts_env=attempts,
        threshold_env=None,
        dropped_slots_file=None,
        panel_manifest=None,
    )

    assert len(calls) == 1
    assert "round 2" in calls[0]
    assert "failed=1" in calls[0]


def test_surface_dropped_reviewer_warning_static_straggler_backstop_does_not_warn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def capture_warning(*, session_env_path: str, entry: str) -> None:
        calls.append(entry)

    monkeypatch.setattr(review_tally, "surface_warning", capture_warning)
    threshold = tmp_path / "review-core-threshold.env"
    threshold.write_text("STRAGGLER_DROPPED_COUNT=1\n", encoding="utf-8")
    dropped = tmp_path / "panel.output-files.dropped-slots"
    dropped.write_text("testing\tcursor\tstraggler-dropped\tcut\n", encoding="utf-8")

    review_and_fix._surface_dropped_reviewer_warning(  # pyright: ignore[reportPrivateUsage]
        core={},
        round_num=1,
        session_env_path="/tmp/session-env.sh",
        attempts_env=None,
        threshold_env=threshold,
        dropped_slots_file=dropped,
        panel_manifest=None,
    )

    assert not calls


def test_surface_dropped_reviewer_warning_static_straggler_with_dynamic_manifest_does_not_warn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def capture_warning(*, session_env_path: str, entry: str) -> None:
        calls.append(entry)

    monkeypatch.setattr(review_tally, "surface_warning", capture_warning)
    threshold = tmp_path / "review-core-threshold.env"
    threshold.write_text("STRAGGLER_DROPPED_COUNT=1\n", encoding="utf-8")
    dropped = tmp_path / "panel.output-files.dropped-slots"
    dropped.write_text("testing\tcursor\tstraggler-dropped\tcut\n", encoding="utf-8")
    manifest = tmp_path / "panel-manifest.ndjson"
    manifest.write_text(
        json.dumps(
            {
                "slot": "dyn-dyn-lint-escalation",
                "tool": "cursor",
                "output": str(tmp_path / "dyn-dyn-lint-escalation-output.txt"),
                "agent": "agents/reviewer.md",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    review_and_fix._surface_dropped_reviewer_warning(  # pyright: ignore[reportPrivateUsage]
        core={},
        round_num=1,
        session_env_path="/tmp/session-env.sh",
        attempts_env=None,
        threshold_env=threshold,
        dropped_slots_file=dropped,
        panel_manifest=manifest,
    )

    assert not calls


def test_surface_dropped_reviewer_warning_static_straggler_without_ledger_does_not_warn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def capture_warning(*, session_env_path: str, entry: str) -> None:
        calls.append(entry)

    monkeypatch.setattr(review_tally, "surface_warning", capture_warning)
    threshold = tmp_path / "review-core-threshold.env"
    threshold.write_text("STRAGGLER_DROPPED_COUNT=1\n", encoding="utf-8")
    manifest = tmp_path / "panel-manifest.ndjson"
    manifest.write_text(
        json.dumps(
            {
                "slot": "dyn-dyn-lint-escalation",
                "tool": "cursor",
                "output": str(tmp_path / "dyn-dyn-lint-escalation-output.txt"),
                "agent": "agents/reviewer.md",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    review_and_fix._surface_dropped_reviewer_warning(  # pyright: ignore[reportPrivateUsage]
        core={},
        round_num=1,
        session_env_path="/tmp/session-env.sh",
        attempts_env=None,
        threshold_env=threshold,
        dropped_slots_file=None,
        panel_manifest=manifest,
    )

    assert not calls


def test_surface_dropped_reviewer_warning_dynamic_straggler_backstop_warns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def capture_warning(*, session_env_path: str, entry: str) -> None:
        calls.append(entry)

    monkeypatch.setattr(review_tally, "surface_warning", capture_warning)
    threshold = tmp_path / "review-core-threshold.env"
    threshold.write_text("STRAGGLER_DROPPED_COUNT=1\n", encoding="utf-8")
    dropped = tmp_path / "panel.output-files.dropped-slots"
    dropped.write_text("dyn-dyn-lint-escalation\tcursor\tstraggler-dropped\tcut\n", encoding="utf-8")

    review_and_fix._surface_dropped_reviewer_warning(  # pyright: ignore[reportPrivateUsage]
        core={},
        round_num=1,
        session_env_path="/tmp/session-env.sh",
        attempts_env=None,
        threshold_env=threshold,
        dropped_slots_file=dropped,
        panel_manifest=None,
    )

    assert len(calls) == 1


@MARK_STEP5
def test_step5_loop_preflight_empty_plan_emits_stall(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    (impl / "plan.txt").write_text("", encoding="utf-8")
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "STEP5_REVIEW_STATUS=stall" in out
    assert "STALL_REASON=preflight-failed" in out


@MARK_STEP5
def test_step5_mav_apply_missing_findings_file(tmp_path, monkeypatch):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    rc = review_and_fix.step5([
        "--implement-tmpdir", str(impl), "--mode", "mav-apply", "--round-num", "1",
        "--findings-file", str(impl / "missing.md"),
    ])
    assert rc == 2


@MARK_STEP5
def test_step5_main_agent_vote_emits_ledger_kvs(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)

    def fake_round(args, *, suppress_emit, review_core_impl=None):
        del args, suppress_emit, review_core_impl
        return review_and_fix.RoundResult(
            0, "main-agent-vote-required", "main-agent-vote-required", 1, 1, 0, 0, 0, 1, 0, 0, 0,
            impl / "round-1" / "accepted-findings.md",
            impl / "round-1" / "rejected-findings.md",
            impl / "round-1",
            impl / "review-and-fix-summary.json",
            impl / "accumulated-oos.jsonl",
            review_and_fix.CoderResult(0),
        )

    monkeypatch.setattr(review_and_fix, "_run_round", fake_round)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1", "--round-cap", "1"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "STEP5_REVIEW_LEDGER_READY=true" in out
    assert "STEP5_REVIEW_LEDGER_SITE=step5-mav" in out
    assert "STEP5_REVIEW_LEDGER_TRIGGER=main-agent-vote-required" in out


@MARK_STEP5
@pytest.mark.parametrize("handoff_status", ["main-agent-vote-required", "coder-main-agent-required"])
def test_step5_handoff_restages_difficulty_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    handoff_status: str,
) -> None:
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    record = impl / "difficulty-rating.json"
    record.write_text(json.dumps({"audit_evaluated": True}), encoding="utf-8")
    events: list[str] = []
    run_log_calls: list[list[str]] = []

    def fake_round(args, *, suppress_emit, review_core_impl=None):
        del args, suppress_emit, review_core_impl
        return review_and_fix.RoundResult(
            0,
            handoff_status,
            handoff_status,
            1,
            1,
            0,
            0,
            0,
            1,
            0,
            0,
            0,
            impl / "round-1" / "accepted-findings.md",
            impl / "round-1" / "rejected-findings.md",
            impl / "round-1",
            impl / "review-and-fix-summary.json",
            impl / "accumulated-oos.jsonl",
            review_and_fix.CoderResult(4 if handoff_status == "coder-main-agent-required" else 0, status="main-agent-required"),
        )

    def fake_run(argv: list[str], **_kwargs: object) -> review_and_fix.proc.CommandResult:
        if "stall-recovery" in argv and "record-escalation" in argv:
            events.append("record-escalation")
        if "run-log" in argv and "write" in argv and "--batch" in argv and argv[argv.index("--batch") + 1] == "difficulty-rating":
            events.append("restage")
            run_log_calls.append(argv)
        return review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(review_and_fix, "_run_round", fake_round)
    monkeypatch.setattr(review_and_fix, "record_round_timing", lambda _argv: 0)
    monkeypatch.setattr(review_and_fix, "_run", fake_run)

    rc = review_and_fix.step5([
        "--implement-tmpdir",
        str(impl),
        "--mode",
        "loop",
        "--starting-round",
        "1",
        "--round-cap",
        "1",
        "--run-id",
        "run-1",
        "--codex-available",
        "false",
        "--cursor-available",
        "false",
    ])

    out = capsys.readouterr().out
    assert rc == 0
    assert f"STEP5_REVIEW_STATUS={handoff_status}" in out
    expected_events = ["record-escalation", "restage"] if handoff_status == "coder-main-agent-required" else ["restage"]
    assert events == expected_events
    assert len(run_log_calls) == 1
    call = run_log_calls[0]
    assert call[call.index("--run-id") + 1] == "run-1"
    assert call[call.index("--input-file") + 1] == str(record)


@MARK_STEP5
def test_step5_handoff_returns_zero_when_core_rc_nonzero(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)

    def fake_round(args, *, suppress_emit, review_core_impl=None):
        del args, suppress_emit, review_core_impl
        return review_and_fix.RoundResult(
            2, "main-agent-vote-required", "main-agent-vote-required", 1, 1, 0, 0, 0, 1, 0, 0, 0,
            impl / "round-1" / "accepted-findings.md",
            impl / "round-1" / "rejected-findings.md",
            impl / "round-1",
            impl / "review-and-fix-summary.json",
            impl / "accumulated-oos.jsonl",
            review_and_fix.CoderResult(0),
        )

    monkeypatch.setattr(review_and_fix, "_run_round", fake_round)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1", "--round-cap", "1"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "STEP5_REVIEW_STATUS=main-agent-vote-required" in out
    assert "STEP5_REVIEW_LEDGER_EXIT_CODE=0" in out


@MARK_LOOP_TIMING
def test_step5_handoff_persists_round_start_before_normal_round_returns(tmp_path, monkeypatch):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    timing_calls: list[list[str]] = []
    round_entered = threading.Event()
    release_round = threading.Event()
    rc_box: list[int] = []
    exc_box: list[BaseException] = []

    def fake_round(args, *, suppress_emit, review_core_impl=None):
        del args, suppress_emit, review_core_impl
        round_entered.set()
        assert release_round.wait(5)
        return review_and_fix.RoundResult(
            0, "complete", "complete", 1, 0, 0, 0, 0, 0, 0, 0, 0,
            impl / "round-1" / "accepted-findings.md",
            impl / "round-1" / "rejected-findings.md",
            impl / "round-1",
            impl / "review-and-fix-summary.json",
            impl / "accumulated-oos.jsonl",
            review_and_fix.CoderResult(0),
        )

    monkeypatch.setattr(review_and_fix, "_run_round", fake_round)
    monkeypatch.setattr(review_and_fix, "record_round_timing", lambda argv: timing_calls.append(argv) or 0)

    def run_step5() -> None:
        try:
            rc_box.append(
                review_and_fix.step5([
                    "--implement-tmpdir", str(impl),
                    "--mode", "loop",
                    "--starting-round", "1",
                    "--round-cap", "1",
                ])
            )
        except BaseException as exc:  # pragma: no cover - re-raised in parent thread
            exc_box.append(exc)

    worker = threading.Thread(target=run_step5)
    worker.start()
    try:
        assert round_entered.wait(5)
        start_file = impl / "round-1" / "round-start-s"
        assert start_file.is_file()
        start_value = start_file.read_text(encoding="utf-8").strip()
        assert start_value.isdigit()
        assert not timing_calls
    finally:
        release_round.set()
        worker.join(5)
    assert not worker.is_alive()
    if exc_box:
        raise exc_box[0]
    assert rc_box == [0]
    assert timing_calls
    timing_argv = timing_calls[0]
    assert timing_argv[timing_argv.index("--start-s") + 1] == start_value


def test_persist_round_start_skips_symlinked_round_dir(tmp_path: Path) -> None:
    impl = tmp_path / "impl"
    impl.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (impl / "round-1").symlink_to(outside)
    review_and_fix._persist_round_start(implement_tmpdir=impl, round_num=1, start_s=12345)
    assert not (outside / "round-start-s").exists()


def test_persist_round_start_tolerates_write_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    impl = tmp_path / "impl"
    impl.mkdir()

    def boom(*_args: object, **_kwargs: object) -> object:
        raise OSError("write failed")

    monkeypatch.setattr(os, "fdopen", boom)
    review_and_fix._persist_round_start(implement_tmpdir=impl, round_num=1, start_s=12345)


@MARK_STEP5
def test_step5_invalid_dynamic_archetypes_emits_stall(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("LARCH_DYNAMIC_ARCHETYPES_MAX", "9")
    impl = _tmp_impl(tmp_path)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "STEP5_REVIEW_STATUS=stall" in out


@MARK_STEP5
def test_record_escalation_failure_appends_tool_failure(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    stderr_path = impl / "round-1" / "review-and-fix.stderr"
    stderr_path.parent.mkdir(parents=True)
    stderr_path.write_text("boom\n", encoding="utf-8")

    def fail_helper(_argv, **_kwargs):
        class Result:
            returncode = 1
            stdout = ""
            stderr = "record failed"

        return Result()

    monkeypatch.setattr(review_and_fix, "_run", fail_helper)
    review_and_fix._record_escalation_if_needed(implement_tmpdir=impl, review_status="coder-main-agent-required", review_rc=2, stderr_path=stderr_path)
    text = (impl / "execution-issues.md").read_text(encoding="utf-8")
    assert "Tool Failure: record-escalation" in text


@MARK_WRITE_REJECTED
def test_write_rejected_findings_aggregate_multi_round(tmp_path):
    impl = tmp_path / "impl"
    impl.mkdir()
    r1 = impl / "round-1"
    r2 = impl / "round-2"
    r1.mkdir()
    r2.mkdir()
    (r1 / "rejected-findings-full.md").write_text("### FINDING_1: A\nbody\n", encoding="utf-8")
    (r2 / "rejected-findings-full.md").write_text("### FINDING_2: B\nbody\n", encoding="utf-8")
    review_and_fix.write_rejected_findings_aggregate(impl_tmpdir=impl)
    text = (impl / "rejected-findings.md").read_text(encoding="utf-8")
    assert "# Review Round 1" in text
    assert "# Review Round 2" in text
    assert "FINDING_1" in text
    assert "FINDING_2" in text


@MARK_CONVERGENCE
def test_fix_applied_not_rewritten_to_converged_before_gates(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    accepted = round_dir / "accepted-findings.md"
    accepted.write_text("### FINDING_1: nit only\n- **Severity**: nit\n", encoding="utf-8")
    (round_dir / "findings.md").write_text("### FINDING_1: nit only\n", encoding="utf-8")

    def fake_capture(*, core_args, env_path, **_kwargs):
        core_out = env_path  # mapped from env_path kwarg
        out_dir = Path(core_args[core_args.index("--output-dir") + 1])
        if accepted.resolve() != (out_dir / "accepted-findings.md").resolve():
            shutil.copyfile(accepted, out_dir / "accepted-findings.md")
        (out_dir / "findings.md").write_text("### FINDING_1: nit only\n", encoding="utf-8")
        core_out.write_text(
            "\n".join([
                "REVIEW_CORE_STATUS=fix-required",
                "ACCEPTED_COUNT=1",
                "REJECTED_COUNT=0",
                f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}",
                f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}",
            ]) + "\n",
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(round_runner, "review_core_capture", fake_capture)
    monkeypatch.setattr(round_runner, "apply_findings_with_coder", lambda *a, **k: review_and_fix.CoderResult(0, status="applied", input_count=1))
    monkeypatch.setattr(round_runner, "_compose_review_findings_output", lambda *_a, **_k: False)
    monkeypatch.setattr(review_and_fix, "flush_review_batches", lambda *_a, **_k: True)
    monkeypatch.setattr(round_runner, "flush_round_log_after_coder", lambda *_a, **_k: None)
    monkeypatch.setattr(round_runner, "_run", lambda argv, **_kw: review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0))
    args = review_and_fix._build_step5_parser().parse_args([
        "--implement-tmpdir", str(impl), "--round-num", "1", "--mode", "single",
        "--session-env-path", str(impl / "session-env.sh"),
        "--plan-file", str(impl / "plan.txt"),
        "--feature-file", str(impl / "feature-description.txt"),
        "--run-id", "run-1",
        "--codex-available", "false",
        "--cursor-available", "false",
    ])
    result = review_and_fix._run_round(args, suppress_emit=True)
    assert result.status == "fix-applied"


@MARK_CONVERGENCE
def test_run_round_tally_flush_failure_becomes_stall_status(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)

    def fake_capture(*, core_args, env_path, **_kwargs):
        core_out = env_path  # mapped from env_path kwarg
        out_dir = Path(core_args[core_args.index("--output-dir") + 1])
        (out_dir / "accepted-findings.md").write_text("", encoding="utf-8")
        core_out.write_text(
            "\n".join([
                "REVIEW_CORE_STATUS=ok",
                "ACCEPTED_COUNT=0",
                "REJECTED_COUNT=0",
                f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}",
                f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}",
            ]) + "\n",
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(round_runner, "review_core_capture", fake_capture)
    monkeypatch.setattr(round_runner, "_compose_review_findings_output", lambda *_a, **_k: False)
    monkeypatch.setattr(review_and_fix, "flush_review_batches", lambda *_a, **_k: False)
    monkeypatch.setattr(round_runner, "flush_round_log_after_coder", lambda *_a, **_k: None)
    monkeypatch.setattr(round_runner, "_run", lambda argv, **_kw: review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0))
    args = review_and_fix._build_step5_parser().parse_args([
        "--implement-tmpdir", str(impl), "--round-num", "1", "--mode", "single",
        "--session-env-path", str(impl / "session-env.sh"),
        "--plan-file", str(impl / "plan.txt"),
        "--feature-file", str(impl / "feature-description.txt"),
        "--run-id", "run-1",
        "--codex-available", "false",
        "--cursor-available", "false",
    ])

    result = review_and_fix._run_round(args, suppress_emit=True)

    assert result.status == "tally-flush-failed"
    assert result.rc == 2
    summary = json.loads((impl / "review-and-fix-summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "tally-flush-failed"


@MARK_CONVERGENCE
def test_step5_stalls_when_round_tally_flush_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    accepted = round_dir / "accepted-findings.md"
    accepted.write_text("", encoding="utf-8")
    result = review_and_fix.RoundResult(
        2, "tally-flush-failed", "ok", 1, 0, 0, 0, 0, 0, 0, 0, 0,
        accepted, round_dir / "rejected-findings.md", round_dir,
        impl / "review-and-fix-summary.json", impl / "accumulated-oos.jsonl",
        review_and_fix.CoderResult(0),
    )
    monkeypatch.setattr(review_and_fix, "_run_round", lambda *_a, **_k: result)
    monkeypatch.setattr(review_and_fix, "record_round_timing", lambda *_a, **_k: 0)
    monkeypatch.setattr(review_and_fix, "_run", lambda argv, **_kw: review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0))

    rc = review_and_fix.step5([
        "--implement-tmpdir", str(impl),
        "--mode", "loop",
        "--round-cap", "1",
        "--session-env-path", str(impl / "session-env.sh"),
        "--plan-file", str(impl / "plan.txt"),
        "--feature-file", str(impl / "feature-description.txt"),
        "--run-id", "run-1",
        "--codex-available", "false",
        "--cursor-available", "false",
    ])

    out = capsys.readouterr().out
    assert rc == 2
    assert "STEP5_REVIEW_STATUS=stall" in out
    assert "STALL_REASON=tally-flush-failed" in out


@pytest.mark.record_timing
def test_record_round_timing_writes_ledger_row(tmp_path, monkeypatch):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    round_dir = impl / "round-1"
    round_dir.mkdir()
    (round_dir / "accepted-findings.md").write_text("### FINDING_1: x\n", encoding="utf-8")
    rc = review_and_fix.record_round_timing([
        "--implement-tmpdir", str(impl), "--round", "1", "--start-s", "100", "--end-s", "200",
    ])
    assert rc == 0
    assert (impl / "timing-ledger.tsv").is_file()


def test_write_self_review_tally_emits_step5_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = tmp_path / "impl"
    impl.mkdir()
    rc = review_and_fix.write_self_review_tally([
        "--implement-tmpdir", str(impl),
        "--run-id", "run-sr",
    ])
    assert rc == 0
    run_dir = impl / "larch-logs" / "implement" / "run-sr"
    tally_path = run_dir / "code-review-tally.json"
    assert tally_path.is_file()
    tally = json.loads(tally_path.read_text(encoding="utf-8"))
    assert tally["phase"] == "code-review"
    assert tally["mode"] == "self-review"
    assert tally["rounds"] == 1
    assert tally["accepted_count"] == 0
    assert tally["rejected_count"] == 0
    findings_path = run_dir / "review-findings-full.jsonl"
    assert findings_path.is_file()
    assert findings_path.read_text(encoding="utf-8") == ""


def test_write_self_review_tally_nonzero_counts(tmp_path, monkeypatch):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = tmp_path / "impl"
    impl.mkdir()
    (impl / "self-review-accepted.md").write_text(
        "### [Code Review] Self-review accepted\n"
        "body\n"
        "### [Code Review] Self-review accepted: with suffix\n",
        encoding="utf-8",
    )
    (impl / "rejected-findings.md").write_text(
        "### [Code Review] Self-review\n"
        "body\n"
        "### [Code Review] Self-review with suffix does not count\n",
        encoding="utf-8",
    )
    rc = review_and_fix.write_self_review_tally([
        "--implement-tmpdir", str(impl),
        "--run-id", "run-sr",
    ])
    assert rc == 0
    run_dir = impl / "larch-logs" / "implement" / "run-sr"
    tally_path = run_dir / "code-review-tally.json"
    assert tally_path.is_file()
    tally = json.loads(tally_path.read_text(encoding="utf-8"))
    assert tally["mode"] == "self-review"
    assert tally["rounds"] == 1
    assert tally["accepted_count"] == 2
    assert tally["rejected_count"] == 1
    findings_path = run_dir / "review-findings-full.jsonl"
    assert findings_path.is_file()
    rows = [json.loads(line) for line in findings_path.read_text(encoding="utf-8").splitlines()]
    assert [(row["id"], row["outcome"], row["schema_version"]) for row in rows] == [
        ("SELF_REVIEW_ACCEPTED_1", "accepted", "2"),
        ("SELF_REVIEW_ACCEPTED_2", "accepted", "2"),
        ("SELF_REVIEW_REJECTED_1", "rejected", "2"),
    ]
    assert all(row["phase"] == "code-review" for row in rows)
    assert all(row["round_num"] == "1" for row in rows)
    state = difficulty_calibration.AnalyzerState()
    parsed, source_parseable, count = difficulty_calibration._parse_jsonl_source(findings_path, skill="implement", state=state)
    assert source_parseable is True
    assert count == 3
    assert sum(1 for row in parsed if row.accepted) == 2


def test_write_self_review_tally_nonzero_tally_failure_writes_sidecars_once(tmp_path, monkeypatch):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = tmp_path / "impl"
    impl.mkdir()
    (impl / "self-review-accepted.md").write_text("### [Code Review] Self-review accepted\n", encoding="utf-8")
    (impl / "rejected-findings.md").write_text("### [Code Review] Self-review\n", encoding="utf-8")

    def fake_run(argv, **_kwargs):
        if argv[2:4] == ["voting", "write-tally"]:
            return review_and_fix.proc.CommandResult(tuple(argv), 9, "tally stdout", "tally stderr", 0.0)
        if argv[2:4] == ["run-log", "write"]:
            log_root = Path(_arg_value(argv, "--log-root"))
            run_id = _arg_value(argv, "--run-id")
            batch = _arg_value(argv, "--batch")
            source = Path(_arg_value(argv, "--input-file"))
            dest = log_root / "implement" / run_id / f"{batch}.jsonl"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            return review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0)
        raise AssertionError(argv)

    monkeypatch.setattr(review_and_fix, "_run", fake_run)

    rc = review_and_fix.write_self_review_tally([
        "--implement-tmpdir", str(impl),
        "--run-id", "run-sr",
    ])

    assert rc == 0
    run_dir = impl / "larch-logs" / "implement" / "run-sr"
    tmp_sidecar = impl / "code-review-tally.flush.err"
    run_sidecar = run_dir / "code-review-tally.flush.err"
    assert tmp_sidecar.read_text(encoding="utf-8") == run_sidecar.read_text(encoding="utf-8")
    sidecar_text = run_sidecar.read_text(encoding="utf-8")
    assert "returncode=9" in sidecar_text
    assert "tally stderr" in sidecar_text
    assert "tally stdout" in sidecar_text
    warning_text = (impl / "execution-issues.md").read_text(encoding="utf-8")
    assert warning_text.count("`code-review-tally` write failed") == 1
    assert "larch-logs/implement/run-sr/code-review-tally.flush.err" in warning_text
    rows = [json.loads(line) for line in (run_dir / "review-findings-full.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [row["id"] for row in rows] == ["SELF_REVIEW_ACCEPTED_1", "SELF_REVIEW_REJECTED_1"]


def test_self_review_prompt_reconciles_tally_counts_from_artifacts():
    self_review_section = (
        Path(__file__).resolve().parents[3]
        / "skills"
        / "implement"
        / "references"
        / "self-review.md"
    ).read_text(encoding="utf-8")
    assert "grep -c" not in self_review_section
    assert "<ACCEPTED_COUNT>" not in self_review_section
    assert "<REJECTED_COUNT>" not in self_review_section
    assert "--accepted" not in self_review_section
    assert "$IMPLEMENT_TMPDIR/self-review-accepted.md" in self_review_section
    assert "$IMPLEMENT_TMPDIR/rejected-findings.md" in self_review_section
    assert 'write-self-review-tally --implement-tmpdir "$IMPLEMENT_TMPDIR" --run-id "$RUN_ID"' in self_review_section


def _fake_review_batch_run(argv: list[str], *, tally_result: review_and_fix.proc.CommandResult) -> review_and_fix.proc.CommandResult:
    if argv[2:4] == ["voting", "write-tally"]:
        return tally_result
    if argv[2:4] == ["run-log", "write"]:
        log_root = Path(_arg_value(argv, "--log-root"))
        run_id = _arg_value(argv, "--run-id")
        batch = _arg_value(argv, "--batch")
        source = Path(_arg_value(argv, "--input-file"))
        suffix = ".tsv" if batch.endswith("ledger") else ".jsonl"
        dest = log_root / "implement" / run_id / f"{batch}{suffix}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        return review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0)
    raise AssertionError(argv)


def test_flush_review_batches_nonzero_tally_writes_sidecars_and_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = tmp_path / "impl"
    impl.mkdir()
    findings_source = tmp_path / "findings.jsonl"
    findings_source.write_text(json.dumps({"id": "FINDING_1", "phase": "code-review", "outcome": "accepted"}) + "\n", encoding="utf-8")
    result = review_and_fix.proc.CommandResult(("python3",), 7, "tally stdout", "tally stderr", 0.0)
    monkeypatch.setattr(batch_report, "_run", lambda argv, **_kwargs: _fake_review_batch_run(argv, tally_result=result))

    ok = batch_report.flush_review_batches(impl_tmpdir=impl, run_id="run-flush", rounds=1, _accepted=1, _rejected=0, composed_findings_source=findings_source)

    assert ok is False
    run_dir = impl / "larch-logs" / "implement" / "run-flush"
    tmp_sidecar = impl / "code-review-tally.flush.err"
    run_sidecar = run_dir / "code-review-tally.flush.err"
    assert tmp_sidecar.is_file()
    assert run_sidecar.is_file()
    assert tmp_sidecar.read_text(encoding="utf-8") == run_sidecar.read_text(encoding="utf-8")
    sidecar_text = run_sidecar.read_text(encoding="utf-8")
    assert "returncode=7" in sidecar_text
    assert "tally stderr" in sidecar_text
    assert "tally stdout" in sidecar_text
    warning_text = (impl / "execution-issues.md").read_text(encoding="utf-8")
    assert "larch-logs/implement/run-flush/code-review-tally.flush.err" in warning_text
    assert (run_dir / "review-findings-full.jsonl").read_text(encoding="utf-8") == findings_source.read_text(encoding="utf-8")


def test_flush_review_batches_success_removes_stale_tally_sidecars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    impl = tmp_path / "impl"
    run_dir = impl / "larch-logs" / "implement" / "run-flush"
    run_dir.mkdir(parents=True)
    (impl / "code-review-tally.flush.err").write_text("stale", encoding="utf-8")
    (run_dir / "code-review-tally.flush.err").write_text("stale", encoding="utf-8")
    findings_source = tmp_path / "findings.jsonl"
    findings_source.write_text(json.dumps({"id": "FINDING_1", "phase": "code-review", "outcome": "accepted"}) + "\n", encoding="utf-8")
    result = review_and_fix.proc.CommandResult(("python3",), 0, "", "", 0.0)
    monkeypatch.setattr(batch_report, "_run", lambda argv, **_kwargs: _fake_review_batch_run(argv, tally_result=result))

    assert batch_report.flush_review_batches(impl_tmpdir=impl, run_id="run-flush", rounds=1, _accepted=1, _rejected=0, composed_findings_source=findings_source)

    assert not (impl / "code-review-tally.flush.err").exists()
    assert not (run_dir / "code-review-tally.flush.err").exists()


def test_flush_review_batches_tally_warning_append_is_fail_open(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    impl = tmp_path / "impl"
    impl.mkdir()
    findings_source = tmp_path / "findings.jsonl"
    findings_source.write_text(json.dumps({"id": "FINDING_1", "phase": "code-review", "outcome": "accepted"}) + "\n", encoding="utf-8")
    result = review_and_fix.proc.CommandResult(("python3",), 7, "", "", 0.0)
    monkeypatch.setattr(batch_report, "_run", lambda argv, **_kwargs: _fake_review_batch_run(argv, tally_result=result))

    def boom(**_kwargs):
        raise OSError("append failed")

    monkeypatch.setattr(batch_report.run_log_batch, "append_execution_issue", boom)

    ok = batch_report.flush_review_batches(impl_tmpdir=impl, run_id="run-flush", rounds=1, _accepted=1, _rejected=0, composed_findings_source=findings_source)

    assert ok is False
    assert (impl / "code-review-tally.flush.err").is_file()


def test_flush_review_batches_rewrites_cumulative_tally_with_ignored_body_header(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = tmp_path / "impl"
    impl.mkdir()
    run_id = "run-flush"
    round1 = impl / "round-1"
    round2 = impl / "round-2"
    round1.mkdir()
    round2.mkdir()
    (round1 / "review-round-summary.md").write_text(
        "# Review Round 1\n\n## Accepted Findings\n\n### FINDING_1: first\n",
        encoding="utf-8",
    )
    (round1 / "voting-tally.md").write_text(
        "# Code Review Voting Tally\n\n## Per-finding vote breakdown\n",
        encoding="utf-8",
    )
    round1_jsonl = tmp_path / "round1.jsonl"
    round1_jsonl.write_text(
        json.dumps({"id": "FINDING_1", "phase": "code-review", "outcome": "accepted"}) + "\n",
        encoding="utf-8",
    )

    assert review_and_fix.flush_review_batches(impl_tmpdir=impl, run_id=run_id, rounds=1, _accepted=1, _rejected=0, composed_findings_source=round1_jsonl)
    run_dir = impl / "larch-logs" / "implement" / run_id
    tally_path = run_dir / "code-review-tally.json"
    tally = json.loads(tally_path.read_text(encoding="utf-8"))
    assert tally["rounds"] == 1
    assert tally["accepted_count"] == 1
    assert tally["rejected_count"] == 0
    assert "body" not in tally

    (round2 / "review-round-summary.md").write_text(
        "# Review Round 2\n\n## Round 2\n\n### FINDING_2: second\n",
        encoding="utf-8",
    )
    (round2 / "voting-tally.md").write_text(
        "# Code Review Voting Tally\n\n## Per-finding vote breakdown\n",
        encoding="utf-8",
    )
    round2_records = [
        {"id": "FINDING_1", "phase": "code-review", "outcome": "accepted"},
        {"id": "FINDING_2", "phase": "code-review", "outcome": "accepted"},
        {"id": "FINDING_3", "phase": "code-review", "outcome": "rejected"},
    ]
    round2_jsonl = tmp_path / "round2.jsonl"
    round2_jsonl.write_text(
        "".join(json.dumps(record) + "\n" for record in round2_records),
        encoding="utf-8",
    )

    assert review_and_fix.flush_review_batches(impl_tmpdir=impl, run_id=run_id, rounds=2, _accepted=2, _rejected=1, composed_findings_source=round2_jsonl)
    tally = json.loads(tally_path.read_text(encoding="utf-8"))
    assert tally["rounds"] == 2
    assert tally["accepted_count"] == 2
    assert tally["rejected_count"] == 1
    assert "body" not in tally
    findings_path = run_dir / "review-findings-full.jsonl"
    assert findings_path.read_text(encoding="utf-8") == round2_jsonl.read_text(encoding="utf-8")
    assert sorted(path.name for path in impl.glob("round-*")) == ["round-1", "round-2"]


@pytest.mark.commit_fixes
def test_commit_fixes_emits_committed_kv(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(_tmp_impl(tmp_path)))
    monkeypatch.setattr(review_and_fix, "_run", lambda argv, **_kw: review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0))
    monkeypatch.setattr(review_and_fix, "_git_head", lambda: "deadbeef")
    rc = review_and_fix.commit_fixes(["--message", "fix review"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "COMMITTED=true" in out
    assert "SHA=deadbeef" in out
    assert "ERROR=" in out
    assert "COMMIT_OUTCOME=ok" in out


@pytest.mark.commit_fixes
def test_commit_fixes_marks_token_and_timing(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    (impl / "session-env.sh").write_text(
        "LARCH_TOKEN_SESSION_ID=parent-session\nLARCH_TIMING_LEDGER=/tmp/ledger.tsv\n",
        encoding="utf-8",
    )
    calls: list[tuple[list[str], dict[str, str]]] = []

    def fake_run(argv, **kwargs):
        env = kwargs.get("env", {})
        calls.append((list(argv), dict(env) if env else {}))
        return review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(review_and_fix, "_run", fake_run)
    monkeypatch.setattr(review_and_fix, "_git_head", lambda: "deadbeef")
    rc = review_and_fix.commit_fixes(["--message", "fix review"])
    assert rc == 0
    token_calls = [argv for argv, _env in calls if "token" in argv and "mark" in argv]
    timing_calls = [(argv, env) for argv, env in calls if "timing" in argv and "mark" in argv]
    assert token_calls
    assert timing_calls
    assert "Step 7 — commit review fixes" in token_calls[0]
    assert "Step 7 — commit review fixes" in timing_calls[0][0]
    assert timing_calls[0][1].get("LARCH_TIMING_SKILL") == "implement"


@pytest.mark.commit_fixes
def test_commit_fixes_replaces_empty_session_backed_env(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setenv("LARCH_TOKEN_SESSION_ID", "")
    monkeypatch.setenv("LARCH_TIMING_LEDGER", "")
    (impl / "session-env.sh").write_text(
        "LARCH_TOKEN_SESSION_ID=parent-session\nLARCH_TIMING_LEDGER=/tmp/ledger.tsv\n",
        encoding="utf-8",
    )
    calls: list[tuple[list[str], dict[str, str]]] = []

    def fake_run(argv, **kwargs):
        env = kwargs.get("env", {})
        calls.append((list(argv), dict(env) if env else {}))
        return review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(review_and_fix, "_run", fake_run)
    monkeypatch.setattr(review_and_fix, "_git_head", lambda: "deadbeef")
    rc = review_and_fix.commit_fixes(["--message", "fix review"])
    assert rc == 0
    timing_calls = [(argv, env) for argv, env in calls if "timing" in argv and "mark" in argv]
    assert timing_calls
    assert timing_calls[0][1].get("LARCH_TIMING_LEDGER") == "/tmp/ledger.tsv"


@pytest.mark.commit_fixes
def test_commit_fixes_stage_all_clean_tree_noops(tmp_path, monkeypatch, capsys):
    impl = _tmp_impl(tmp_path)
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(review_and_fix, "_run", lambda argv, **_kw: review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0))
    rc = review_and_fix.commit_fixes(["--stage-all"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "COMMITTED=false" in out
    assert "SHA=" in out
    assert "ERROR=" in out
    assert "COMMIT_OUTCOME=noop" in out


@pytest.mark.commit_fixes
def test_commit_fixes_stage_all_dirty_no_delta_paths_noops(tmp_path, monkeypatch, capsys):
    # Dirty tree with no review-delta paths is benign — pre-existing dirt (issue #5715).
    impl = _tmp_impl(tmp_path)
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(review_and_fix, "_collect_review_fix_stage_paths", lambda _impl: [])  # type: ignore[arg-type]
    committed_calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: object) -> review_and_fix.proc.CommandResult:
        if argv == ["git", "status", "--porcelain"]:
            return review_and_fix.proc.CommandResult(tuple(argv), 0, " M unrelated.py\n", "", 0.0)
        committed_calls.append(argv)
        return review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(review_and_fix, "_run", fake_run)
    rc = review_and_fix.commit_fixes(["--stage-all"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "COMMITTED=false" in out
    assert "COMMIT_OUTCOME=noop" in out
    commit_calls = [c for c in committed_calls if "commit" in c]
    assert not commit_calls


@pytest.mark.commit_fixes
def test_commit_fixes_stage_all_uses_review_delta_pathspec(tmp_path, monkeypatch, capsys):
    impl = _tmp_impl(tmp_path)
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(review_and_fix, "_collect_review_fix_stage_paths", lambda _impl: ["a.py"])
    monkeypatch.setattr(review_and_fix, "_git_head", lambda: "deadbeef")
    calls: list[list[str]] = []
    porcelain_outputs = [" M a.py\n M unrelated.py\n", ""]

    def fake_run(argv, **_kwargs):
        calls.append(list(argv))
        if argv == ["git", "status", "--porcelain"]:
            return review_and_fix.proc.CommandResult(tuple(argv), 0, porcelain_outputs.pop(0), "", 0.0)
        return review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(review_and_fix, "_run", fake_run)
    rc = review_and_fix.commit_fixes(["--stage-all", "--message", "fix review"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "COMMITTED=true" in out
    assert "SHA=deadbeef" in out
    assert "COMMIT_OUTCOME=ok" in out
    stage_file = impl / "review-fix-stage-paths.txt"
    assert stage_file.read_text(encoding="utf-8") == "a.py\n"
    assert ["git", "add", "--pathspec-from-file", str(stage_file)] not in calls
    commit_calls = [
        argv
        for argv in calls
        if argv[:4] == [review_and_fix.sys.executable, str(review_and_fix._PY_CLI), "git", "commit"]
    ]
    assert commit_calls
    assert "--only" in commit_calls[0]
    assert "--pathspec-from-file" in commit_calls[0]
    assert "unrelated.py" not in " ".join(commit_calls[0])


@pytest.mark.commit_fixes
def test_commit_fixes_stage_all_dirty_after_success_nonfatal(tmp_path, monkeypatch, capsys):
    # Residual dirty state outside the --only pathspec is non-fatal (issue #5678).
    impl = _tmp_impl(tmp_path)
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(review_and_fix, "_collect_review_fix_stage_paths", lambda _impl: ["a.py"])
    monkeypatch.setattr(review_and_fix, "_git_head", lambda: "deadbeef")
    status_outputs = [" M a.py\n", " M unrelated.py\n"]

    def fake_run(argv: list[str], **_kwargs: object) -> review_and_fix.proc.CommandResult:
        if argv == ["git", "status", "--porcelain"]:
            return review_and_fix.proc.CommandResult(tuple(argv), 0, status_outputs.pop(0), "", 0.0)
        return review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(review_and_fix, "_run", fake_run)
    rc = review_and_fix.commit_fixes(["--stage-all", "--message", "fix review"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "COMMITTED=true" in out
    assert "SHA=deadbeef" in out
    assert "COMMIT_OUTCOME=ok" in out


@pytest.mark.commit_fixes
def test_commit_fixes_stage_all_post_commit_status_probe_failure_fails(tmp_path, monkeypatch, capsys):
    impl = _tmp_impl(tmp_path)
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(review_and_fix, "_collect_review_fix_stage_paths", lambda _impl: ["a.py"])
    monkeypatch.setattr(review_and_fix, "_git_head", lambda: "deadbeef")
    status_calls = 0

    def fake_run(argv: list[str], **_kwargs: object) -> review_and_fix.proc.CommandResult:
        nonlocal status_calls
        if argv == ["git", "status", "--porcelain"]:
            status_calls += 1
            if status_calls == 1:
                return review_and_fix.proc.CommandResult(tuple(argv), 0, " M a.py\n", "", 0.0)
            return review_and_fix.proc.CommandResult(tuple(argv), 128, "", "fatal status", 0.0)
        return review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(review_and_fix, "_run", fake_run)
    rc = review_and_fix.commit_fixes(["--stage-all", "--message", "fix review"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "COMMITTED=true" in out
    assert "SHA=deadbeef" in out
    assert "ERROR=git status probe failed" in out
    assert "COMMIT_OUTCOME=failed" in out


@pytest.mark.commit_fixes
def test_commit_fixes_stage_all_pre_commit_status_probe_failure_fails(tmp_path, monkeypatch, capsys):
    impl = _tmp_impl(tmp_path)
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))

    def fake_run(argv: list[str], **_kwargs: object) -> review_and_fix.proc.CommandResult:
        if argv == ["git", "status", "--porcelain"]:
            return review_and_fix.proc.CommandResult(tuple(argv), 128, "", "fatal status", 0.0)
        return review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(review_and_fix, "_run", fake_run)
    rc = review_and_fix.commit_fixes(["--stage-all", "--message", "fix review"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "COMMITTED=false" in out
    assert "SHA=" in out
    assert "ERROR=git status probe failed" in out
    assert "COMMIT_OUTCOME=failed" in out


@pytest.mark.commit_fixes
def test_commit_fixes_failure_error_token_does_not_change_outcome(tmp_path, monkeypatch, capsys):
    impl = _tmp_impl(tmp_path)
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(review_and_fix, "_collect_review_fix_stage_paths", lambda _impl: ["a.py"])

    def fake_run(argv: list[str], **_kwargs: object) -> review_and_fix.proc.CommandResult:
        if argv == ["git", "status", "--porcelain"]:
            return review_and_fix.proc.CommandResult(tuple(argv), 0, " M a.py\n", "", 0.0)
        if argv[:4] == [review_and_fix.sys.executable, str(review_and_fix._PY_CLI), "git", "commit"]:
            return review_and_fix.proc.CommandResult(tuple(argv), 1, "", "fatal COMMIT_OUTCOME=ok nope", 0.0)
        return review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(review_and_fix, "_run", fake_run)
    rc = review_and_fix.commit_fixes(["--stage-all", "--message", "fix review"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "ERROR=fatal COMMIT_OUTCOME=ok nope" in out
    assert any(line == "COMMIT_OUTCOME=failed" for line in out.splitlines())


@pytest.mark.commit_fixes
def test_collect_review_fix_stage_paths_self_review_fallback(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    (impl / "self-review-accepted.md").write_text("### [Code Review] Self-review accepted\n", encoding="utf-8")
    snap = snapshot._self_review_snapshot_dir(impl)
    snap.mkdir(parents=True)
    (snap / "pre-self-review-head.txt").write_text("abc123\n", encoding="utf-8")
    (snap / "pre-self-review-tracked-paths.txt").write_text("notes.txt\n", encoding="utf-8")
    (snap / "pre-self-review-untracked-paths.txt").write_text("", encoding="utf-8")
    monkeypatch.setattr(
        snapshot,
        "_self_review_delta_paths",
        lambda **_k: ["fixed.py"],
    )
    monkeypatch.setattr(
        snapshot,
        "_self_review_untracked_delta_paths",
        lambda _impl: ["new.py"],
    )
    paths = coder_runner._collect_review_fix_stage_paths(impl)
    assert paths == ["fixed.py", "new.py"]


@pytest.mark.commit_fixes
def test_collect_self_review_stage_paths_excludes_preexisting_dirty(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    (impl / "self-review-accepted.md").write_text("### [Code Review] Self-review accepted\n", encoding="utf-8")
    snap = snapshot._self_review_snapshot_dir(impl)
    snap.mkdir(parents=True)
    (snap / "pre-self-review-head.txt").write_text("abc123\n", encoding="utf-8")
    (snap / "pre-self-review-tracked-paths.txt").write_text("notes.txt\n", encoding="utf-8")
    (snap / "pre-self-review-untracked-paths.txt").write_text("", encoding="utf-8")
    monkeypatch.setattr(
        snapshot,
        "_self_review_delta_paths",
        lambda **_k: ["fixed.py"],
    )
    monkeypatch.setattr(snapshot, "_self_review_untracked_delta_paths", lambda _impl: [])
    paths = review_and_fix._collect_self_review_stage_paths(impl)
    assert paths == ["fixed.py"]
    assert "notes.txt" not in paths


@pytest.mark.commit_fixes
def test_collect_self_review_stage_paths_without_snapshot_returns_empty(tmp_path):
    impl = _tmp_impl(tmp_path)
    (impl / "self-review-accepted.md").write_text("### [Code Review] Self-review accepted\n", encoding="utf-8")
    paths = review_and_fix._collect_self_review_stage_paths(impl)
    assert not paths


@pytest.mark.commit_fixes
def test_write_pre_self_review_snapshot_blocks_on_unstaged_changes(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)

    def fake_git_output(args: list[str]) -> str:
        if args == ["diff", "--name-only"]:
            return "dirty.py\nanother.py"
        return ""

    monkeypatch.setattr(review_and_fix, "_git_output", fake_git_output)
    rc = review_and_fix.write_pre_self_review_snapshot(["--implement-tmpdir", str(impl)])
    assert rc == 1
    snap = snapshot._self_review_snapshot_dir(impl)
    assert not (snap / "pre-self-review-head.txt").is_file()


@pytest.mark.commit_fixes
def test_write_pre_self_review_snapshot_proceeds_when_tree_clean(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)

    def fake_git_output(args: list[str]) -> str:
        if args == ["diff", "--name-only"]:
            return ""
        if args[:1] == ["diff"] or args[:2] == ["diff", "--cached"]:
            return ""
        if args == ["rev-parse", "HEAD"]:
            return "abc123"
        return ""

    calls: list[list[str]] = []

    def tracking_git_output(args: list[str]) -> str:
        calls.append(args)
        return fake_git_output(args)

    monkeypatch.setattr(review_and_fix, "_git_output", tracking_git_output)
    monkeypatch.setattr(snapshot, "_git_head", lambda: "abc123")
    monkeypatch.setattr(snapshot, "_capture_round_tracked_paths", list)
    monkeypatch.setattr(snapshot, "_capture_round_untracked_paths", list)
    rc = review_and_fix.write_pre_self_review_snapshot(["--implement-tmpdir", str(impl)])
    assert rc == 0
    # Confirmed the unstaged check ran (first _git_output call was the guard)
    assert any(c == ["diff", "--name-only"] for c in calls)


@pytest.mark.commit_fixes
def test_collect_review_fix_stage_paths_skips_head_only_mav_round(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    round_dir = impl / "round-1"
    round_dir.mkdir()
    snap = review_and_fix.pre_coder_snapshot_dir(round_dir)
    snap.mkdir(parents=True)
    (snap / "pre-coder-head.txt").write_text("head\n", encoding="utf-8")
    monkeypatch.setattr(snapshot, "_capture_round_tracked_paths", lambda: ["unrelated.py"])
    monkeypatch.setattr(snapshot, "_capture_round_untracked_paths", list)
    paths = coder_runner._collect_review_fix_stage_paths(impl)
    assert not paths


@pytest.mark.commit_fixes
def test_collect_review_fix_stage_paths_uses_post_coder_head(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    round_dir = impl / "round-1"
    round_dir.mkdir()
    snap = review_and_fix.pre_coder_snapshot_dir(round_dir)
    snap.mkdir(parents=True)
    (snap / "pre-coder-head.txt").write_text("pre\n", encoding="utf-8")
    (snap / "pre-coder-tracked-paths.txt").write_text("", encoding="utf-8")
    (snap / "pre-coder-untracked-paths.txt").write_text("", encoding="utf-8")
    (round_dir / "post-coder-head.txt").write_text("post\n", encoding="utf-8")
    seen_bases: list[str] = []

    def fake_delta(*, round_dir, diff_base, **_kwargs):
        seen_bases.append(diff_base)
        return ["fresh.py"] if diff_base == "post" else ["stale.py"]

    monkeypatch.setattr(snapshot, "_round_coder_delta_paths", fake_delta)
    monkeypatch.setattr(snapshot, "_round_coder_untracked_delta_paths", lambda _round: [])
    paths = coder_runner._collect_review_fix_stage_paths(impl)
    assert seen_bases == ["post"]
    assert paths == ["fresh.py"]


@pytest.mark.commit_fixes
def test_collect_round_stage_paths_without_snapshot_returns_empty(tmp_path, monkeypatch):
    round_dir = _tmp_impl(tmp_path) / "round-1"
    round_dir.mkdir()

    monkeypatch.setattr(snapshot, "_capture_round_tracked_paths", lambda: ["stale.py"])
    monkeypatch.setattr(snapshot, "_capture_round_untracked_paths", lambda: ["stale-untracked.py"])

    assert not snapshot._collect_round_stage_paths(round_dir)


@pytest.mark.commit_fixes
def test_collect_round_stage_paths_with_empty_baseline_returns_empty(tmp_path, monkeypatch):
    round_dir = _tmp_impl(tmp_path) / "round-1"
    round_dir.mkdir()
    snap = review_and_fix.pre_coder_snapshot_dir(round_dir)
    snap.mkdir(parents=True)
    (snap / "pre-coder-head.txt").write_text("", encoding="utf-8")

    monkeypatch.setattr(snapshot, "_capture_round_tracked_paths", lambda: ["stale.py"])
    monkeypatch.setattr(snapshot, "_capture_round_untracked_paths", lambda: ["stale-untracked.py"])

    assert not snapshot._collect_round_stage_paths(round_dir)


@pytest.mark.commit_fixes
def test_collect_round_stage_paths_since_committed_requires_post_coder_head(tmp_path, monkeypatch):
    round_dir = _tmp_impl(tmp_path) / "round-1"
    round_dir.mkdir()
    snap = review_and_fix.pre_coder_snapshot_dir(round_dir)
    snap.mkdir(parents=True)
    (snap / "pre-coder-head.txt").write_text("pre\n", encoding="utf-8")
    (snap / "pre-coder-tracked-paths.txt").write_text("fixed.py\n", encoding="utf-8")
    (snap / "pre-coder-untracked-paths.txt").write_text("", encoding="utf-8")
    (round_dir / "post-coder-head.txt").write_text("", encoding="utf-8")
    delta_calls: list[str] = []

    def fake_delta(*, round_dir: Path, diff_base: str, **_kwargs) -> list[str]:
        delta_calls.append(diff_base)
        return ["stale.py"]

    monkeypatch.setattr(snapshot, "_capture_round_tracked_paths", lambda: ["stale.py"])
    monkeypatch.setattr(snapshot, "_capture_round_untracked_paths", lambda: ["stale-untracked.py"])
    monkeypatch.setattr(snapshot, "_round_coder_delta_paths", fake_delta)
    monkeypatch.setattr(snapshot, "_round_coder_untracked_delta_paths", lambda _round: ["stale-new.py"])

    assert not snapshot._collect_round_stage_paths(round_dir, since_committed=True)
    assert not delta_calls


@pytest.mark.commit_fixes
def test_collect_round_stage_paths_excludes_pre_dirty_unrelated_since_committed(tmp_path, monkeypatch):
    round_dir = _tmp_impl(tmp_path) / "round-1"
    round_dir.mkdir()
    snap = review_and_fix.pre_coder_snapshot_dir(round_dir)
    snap.mkdir(parents=True)
    (snap / "pre-coder-head.txt").write_text("pre\n", encoding="utf-8")
    (snap / "pre-coder-tracked-paths.txt").write_text("unrelated.py\nfixed.py\n", encoding="utf-8")
    (snap / "pre-coder-untracked-paths.txt").write_text("", encoding="utf-8")
    (round_dir / "post-coder-head.txt").write_text("post\n", encoding="utf-8")

    def fake_git_output(args):
        if args == ["diff", "--name-only", "post"]:
            return "unrelated.py\nfixed.py\n"
        return ""

    def fake_matches(*, round_dir, pre_head, path):
        return pre_head == "pre" and path == "unrelated.py"

    monkeypatch.setattr(snapshot, "_git_output", fake_git_output)
    monkeypatch.setattr(snapshot, "_path_matches_pre_coder_snapshot", fake_matches)
    monkeypatch.setattr(snapshot, "_round_coder_untracked_delta_paths", lambda _round: [])
    paths = snapshot._collect_round_stage_paths(round_dir, since_committed=True)
    assert paths == ["fixed.py"]


@pytest.mark.commit_fixes
def test_commit_fixes_stage_all_passes_repo_root_as_cwd(tmp_path, monkeypatch, capsys):
    impl = _tmp_impl(tmp_path)
    repo_root = str(tmp_path / "repo")
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", repo_root)
    monkeypatch.setattr(review_and_fix, "_collect_review_fix_stage_paths", lambda _impl: ["python/a.py"])  # type: ignore[arg-type]
    monkeypatch.setattr(review_and_fix, "_git_head", lambda: "deadbeef")
    captured_cwds: list[object] = []
    porcelain_outputs = [" M python/a.py\n", ""]

    def fake_run(argv: list[str], *, cwd: object = None, **_kwargs: object) -> review_and_fix.proc.CommandResult:
        if argv == ["git", "status", "--porcelain"]:
            return review_and_fix.proc.CommandResult(tuple(argv), 0, porcelain_outputs.pop(0), "", 0.0)
        if argv[:5] == ["git", "-C", repo_root, "rev-parse", "--show-toplevel"]:
            return review_and_fix.proc.CommandResult(tuple(argv), 0, f"{repo_root}\n", "", 0.0)
        if argv[:4] == [review_and_fix.sys.executable, str(review_and_fix._PY_CLI), "git", "commit"]:
            captured_cwds.append(cwd)
        return review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(review_and_fix, "_run", fake_run)
    rc = review_and_fix.commit_fixes(["--stage-all", "--message", "fix review"])
    assert rc == 0
    assert len(captured_cwds) == 1
    assert captured_cwds[0] == review_and_fix.Path(repo_root)


@pytest.mark.commit_fixes
def test_stage_and_commit_round_passes_repo_root_as_cwd(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    round_dir = impl / "round-1"
    round_dir.mkdir()
    repo_root = str(tmp_path / "repo")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", repo_root)
    monkeypatch.setattr(coder_runner, "_collect_round_stage_paths", lambda _rd: ["python/a.py"])  # type: ignore[arg-type]
    monkeypatch.setattr(coder_runner, "_git_head", lambda: "abc123")
    monkeypatch.setattr(coder_runner, "_step5_repo_root", lambda: repo_root)
    captured_cwds: list[object] = []

    def fake_run(argv: list[str], *, cwd: object = None, **_kwargs: object) -> review_and_fix.proc.CommandResult:
        if argv[:4] == [review_and_fix.sys.executable, str(review_and_fix._PY_CLI), "git", "commit"]:
            captured_cwds.append(cwd)
        return review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(coder_runner, "_run", fake_run)
    result = coder_runner._stage_and_commit_round(round_num=1, round_dir=round_dir)
    assert result.sha == "abc123"
    assert len(captured_cwds) == 1
    assert captured_cwds[0] == review_and_fix.Path(repo_root)


@MARK_DISPATCH
def test_apply_findings_rehydrates_session_env_before_coder(tmp_path, monkeypatch):
    monkeypatch.delenv("LARCH_TOKEN_SESSION_ID", raising=False)
    monkeypatch.delenv("LARCH_TIMING_LEDGER", raising=False)
    monkeypatch.setenv("CODEX_BINARY_FOUND", "true")
    monkeypatch.setenv("CURSOR_BINARY_FOUND", "true")
    session = tmp_path / "session-env.sh"
    session.write_text(
        "LARCH_TOKEN_SESSION_ID=parent-session\nLARCH_TIMING_LEDGER=/tmp/ledger.tsv\n"
        "CODEX_PRESENT=false\nCURSOR_PRESENT=false\nCODEX_BINARY_FOUND=false\nCURSOR_BINARY_FOUND=false\n",
        encoding="utf-8",
    )
    findings = tmp_path / "findings.md"
    findings.write_text("### FINDING_1: x\n- **Severity**: nit\n", encoding="utf-8")
    seen: dict[str, str] = {}

    def fake_coder(input_file, round_dir, result_file, round_num=None):
        del input_file, round_dir, result_file, round_num
        seen["token"] = os.environ.get("LARCH_TOKEN_SESSION_ID", "")
        seen["ledger"] = os.environ.get("LARCH_TIMING_LEDGER", "")
        seen["codex"] = os.environ.get("CODEX_BINARY_FOUND", "")
        seen["cursor"] = os.environ.get("CURSOR_BINARY_FOUND", "")
        return review_and_fix.CoderResult(0, status="no-changes")

    monkeypatch.setattr(review_and_fix, "apply_findings_with_coder", fake_coder)
    rc = review_and_fix.apply_findings([
        "--findings-file", str(findings),
        "--review-tmpdir", str(tmp_path / "review"),
        "--session-env-path", str(session),
    ])
    assert rc == 0
    assert seen["token"] == "parent-session"
    assert seen["ledger"] == "/tmp/ledger.tsv"
    assert seen["codex"] == "false"
    assert seen["cursor"] == "false"


@MARK_DISPATCH
def test_apply_findings_uses_flat_review_tmpdir_timing_ledger_without_session_ledger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.delenv("LARCH_TIMING_LEDGER", raising=False)
    findings = tmp_path / "findings.md"
    findings.write_text("### FINDING_1: apply me\n- Suggested revision: change file.\n", encoding="utf-8")
    review_tmpdir = tmp_path / "review"
    session_env = tmp_path / "session-env.sh"
    session_env.write_text("CODEX_BINARY_FOUND=false\nCURSOR_BINARY_FOUND=true\n", encoding="utf-8")
    seen: dict[str, Path] = {}

    def fake_scrub(*, input_file: Path, output_file: Path, log_file: Path) -> tuple[bool, int]:
        shutil.copyfile(input_file, output_file)
        return True, 0

    def fake_cursor(*, round_dir: Path, prompt_body: str, tool_log: Path) -> bool:
        seen["ledger"] = review_and_fix._resolve_coder_timing_ledger(round_dir)
        tool_log.write_text("APPLIED: FINDING_1\n", encoding="utf-8")
        return True

    monkeypatch.setattr(coder_runner, "_scrub_findings", fake_scrub)
    monkeypatch.setattr(coder_runner, "_submodule_paths", list)
    monkeypatch.setattr(coder_runner, "_run_coder_codex", lambda *_a, **_k: False)
    monkeypatch.setattr(coder_runner, "_run_coder_cursor", fake_cursor)
    monkeypatch.setattr(coder_runner, "_run_coder_claude", lambda *_a, **_k: False)
    monkeypatch.setattr(coder_runner, "_collect_round_stage_paths", lambda *_args, **_kwargs: ["changed.py"])
    monkeypatch.setattr(review_and_fix, "_git_status_porcelain", lambda: "")

    rc = review_and_fix.apply_findings([
        "--findings-file", str(findings),
        "--review-tmpdir", str(review_tmpdir),
        "--session-env-path", str(session_env),
    ])

    assert rc == 0
    assert seen["ledger"] == review_tmpdir / "timing-ledger.tsv"
    assert "REVIEW_AND_FIX_STATUS=complete" in capsys.readouterr().out


@MARK_DISPATCH
def test_scrub_findings_missing_output_fails_closed(tmp_path, monkeypatch):
    input_file = tmp_path / "in.md"
    output_file = tmp_path / "out.md"
    input_file.write_text("### FINDING_1: x\n", encoding="utf-8")

    def fake_run(_argv, **_kwargs):
        class Result:
            returncode = 0
            stdout = "SCRUB_OK=true\nSCRUB_COUNT=0\n"
            stderr = ""

        return Result()

    monkeypatch.setattr(coder_runner, "_run", fake_run)
    ok, count = coder_runner._scrub_findings(input_file=input_file, output_file=output_file, log_file=tmp_path / "scrub.log")
    assert ok is False
    assert count == 0
    assert not output_file.exists()


def test_review_core_capture_rejects_non_executable_override(tmp_path, monkeypatch):
    override = tmp_path / "fake-core.sh"
    override.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    monkeypatch.setenv("LARCH_TEST_REVIEW_CORE_OVERRIDE", "1")
    monkeypatch.setenv("REVIEW_AND_FIX_REVIEW_CORE_SH", str(override))
    env_path = tmp_path / "review-core.env"
    rc = review_and_fix.review_core_capture(core_args=["--round-num", "1"], env_path=env_path, implement_tmpdir=tmp_path)
    assert rc == 2
    assert "override-not-executable" in env_path.read_text(encoding="utf-8")


@MARK_DISPATCH
def test_run_coder_cursor_acquires_external_startup_lock(tmp_path, monkeypatch):
    monkeypatch.setenv("CURSOR_PRESENT", "true")
    monkeypatch.setenv("CURSOR_BINARY_FOUND", "true")
    monkeypatch.setattr(coder_runner, "_cursor_available", lambda: True)
    monkeypatch.setattr(coder_runner.time, "time", mock.Mock(side_effect=[100, 125]))
    monkeypatch.setattr(
        coder_runner.agents,
        "cursor_auth_preflight",
        lambda **_kw: coder_runner.agents.AuthVerdict(ok=True, rc=0),
    )
    monkeypatch.setattr(coder_runner.agents, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(
        coder_runner.agents,
        "resolve_model_args",
        lambda *_a, **_k: coder_runner.agents.ModelArgResult(argv=("--model", "test")),
    )
    lock_calls: list[str] = []
    release_calls: list[coder_runner.agents.StartupLockState] = []
    run_calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_acquire(tool):
        lock_calls.append(tool)
        return coder_runner.agents.StartupLockState(None)

    def fake_release(state):
        release_calls.append(state)

    monkeypatch.setattr(coder_runner.agents, "external_startup_lock_acquire", fake_acquire)
    monkeypatch.setattr(coder_runner.agents, "external_startup_lock_release_after", fake_release)

    def fake_run(argv: list[str], **kwargs: object) -> review_and_fix.proc.CommandResult:
        run_calls.append((argv, kwargs))
        stdout = "wrapped prompt" if "cursor-wrap-prompt" in argv else ""
        return review_and_fix.proc.CommandResult(tuple(argv), 0, stdout, "", 0.0)

    monkeypatch.setattr(coder_runner, "_run", fake_run)
    assert review_and_fix._run_coder_cursor(round_dir=tmp_path, prompt_body="prompt", tool_log=tmp_path / "tool.log") is True
    assert lock_calls == ["cursor"]
    assert len(release_calls) == 1
    timing_calls = [call for call in run_calls if call[0][2:4] == ["timing", "record-vendor-task"]]
    assert len(timing_calls) == 1
    argv = timing_calls[0][0]
    assert argv[argv.index("--ledger") + 1] == str(tmp_path / "timing-ledger.tsv")
    assert argv[argv.index("--task-kind") + 1] == "cursor-review-fix"
    assert argv[argv.index("--output") + 1] == str(tmp_path / "coder-cursor.log")
    assert argv[argv.index("--start-s") + 1] == "100"
    assert argv[argv.index("--end-s") + 1] == "125"


@MARK_DISPATCH
def test_run_coder_cursor_records_failure_vendor_task(tmp_path, monkeypatch):
    monkeypatch.setenv("CURSOR_BINARY_FOUND", "true")
    monkeypatch.setattr(coder_runner, "_cursor_available", lambda: True)
    monkeypatch.setattr(coder_runner.time, "time", mock.Mock(side_effect=[200, 205]))
    monkeypatch.setattr(
        coder_runner.agents,
        "cursor_auth_preflight",
        lambda **_kw: coder_runner.agents.AuthVerdict(ok=True, rc=0),
    )
    monkeypatch.setattr(coder_runner.agents, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(
        coder_runner.agents,
        "resolve_model_args",
        lambda *_a, **_k: coder_runner.agents.ModelArgResult(argv=("--model", "test")),
    )
    monkeypatch.setattr(coder_runner.agents, "external_startup_lock_acquire", lambda tool: coder_runner.agents.StartupLockState(None))
    monkeypatch.setattr(coder_runner.agents, "external_startup_lock_release_after", lambda state: None)
    run_calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: object) -> review_and_fix.proc.CommandResult:
        run_calls.append(argv)
        if "cursor-wrap-prompt" in argv:
            return review_and_fix.proc.CommandResult(tuple(argv), 0, "wrapped prompt", "", 0.0)
        if "run-external-agent" in argv:
            return review_and_fix.proc.CommandResult(tuple(argv), 7, "", "failed", 0.0)
        return review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(coder_runner, "_run", fake_run)

    assert review_and_fix._run_coder_cursor(round_dir=tmp_path, prompt_body="prompt", tool_log=tmp_path / "tool.log") is False

    timing_call = next(argv for argv in run_calls if argv[2:4] == ["timing", "record-vendor-task"])
    assert timing_call[timing_call.index("--task-kind") + 1] == "cursor-review-fix"
    assert timing_call[timing_call.index("--exit-code") + 1] == "7"
    assert timing_call[timing_call.index("--status") + 1] == "signal"


@MARK_CONVERGENCE
def test_important_present_matches_concern_only_marker(tmp_path):
    findings = tmp_path / "findings.md"
    findings.write_text(
        "### FINDING_1: title without heading tag\n- **Concern**: [Important] real issue\n",
        encoding="utf-8",
    )
    assert round_runner._important_present(findings) is True


@MARK_CONVERGENCE
def test_step5_high_severity_major_acceptance_triggers_escalation(tmp_path):
    impl = _tmp_impl(tmp_path)
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    accepted = round_dir / "accepted-findings.md"
    accepted.write_text(
        "### FINDING_1: first\n- **Severity**: major\n\n### FINDING_2: second\n- **Severity**: major\n",
        encoding="utf-8",
    )
    result = review_and_fix.RoundResult(
        0,
        "fix-applied",
        "fix-required",
        1,
        2,
        0,
        0,
        0,
        2,
        0,
        0,
        0,
        accepted,
        round_dir / "rejected-findings.md",
        round_dir,
        impl / "review-and-fix-summary.json",
        impl / "accumulated-oos.jsonl",
        review_and_fix.CoderResult(0, status="applied", input_count=2),
    )

    assert round_runner._high_severity_count(accepted) == 2
    assert review_and_fix._escalation_trigger_for_result(result) == "high-severity"


@MARK_CONVERGENCE
def test_run_round_missing_findings_sets_classifier_failed(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    accepted = round_dir / "accepted-findings.md"
    accepted.write_text("### FINDING_1: [OUT_OF_SCOPE] real issue\n- **Severity**: important\n", encoding="utf-8")

    def fake_capture(*, core_args, env_path, **_kwargs):
        core_out = env_path  # mapped from env_path kwarg
        out_dir = Path(core_args[core_args.index("--output-dir") + 1])
        dest = out_dir / "accepted-findings.md"
        if accepted.resolve() != dest.resolve():
            shutil.copyfile(accepted, dest)
        core_out.write_text(
            "\n".join([
                "REVIEW_CORE_STATUS=ok",
                "ACCEPTED_COUNT=1",
                "REJECTED_COUNT=0",
                f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}",
                f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}",
            ]) + "\n",
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(round_runner, "review_core_capture", fake_capture)
    monkeypatch.setattr(round_runner, "_compose_review_findings_output", lambda *_a, **_k: False)
    monkeypatch.setattr(review_and_fix, "flush_review_batches", lambda *_a, **_k: True)
    monkeypatch.setattr(round_runner, "flush_round_log_after_coder", lambda *_a, **_k: None)
    monkeypatch.setattr(round_runner, "_run", lambda argv, **_kw: review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0))
    args = review_and_fix._build_step5_parser().parse_args([
        "--implement-tmpdir", str(impl), "--round-num", "1", "--mode", "single",
        "--session-env-path", str(impl / "session-env.sh"),
        "--plan-file", str(impl / "plan.txt"),
        "--feature-file", str(impl / "feature-description.txt"),
        "--run-id", "run-1",
        "--codex-available", "false",
        "--cursor-available", "false",
    ])
    result = review_and_fix._run_round(args, suppress_emit=True)
    assert result.status == "classifier-failed"
    assert result.rc == 2


@MARK_CONVERGENCE
def test_implement_round_meta_write_failure_does_not_block_flush(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    accepted = round_dir / "accepted-findings.md"
    accepted.write_text("### FINDING_1: nit only\n- **Severity**: nit\n", encoding="utf-8")
    (round_dir / "findings.md").write_text("### FINDING_1: nit only\n", encoding="utf-8")

    def fake_capture(*, core_args, env_path, **_kwargs):
        core_out = env_path  # mapped from env_path kwarg
        out_dir = Path(core_args[core_args.index("--output-dir") + 1])
        if accepted.resolve() != (out_dir / "accepted-findings.md").resolve():
            shutil.copyfile(accepted, out_dir / "accepted-findings.md")
        (out_dir / "findings.md").write_text("### FINDING_1: nit only\n", encoding="utf-8")
        core_out.write_text(
            "\n".join([
                "REVIEW_CORE_STATUS=fix-required",
                "ACCEPTED_COUNT=1",
                "REJECTED_COUNT=0",
                f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}",
                f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}",
            ]) + "\n",
            encoding="utf-8",
        )
        return 0

    flush_called: list[bool] = []

    def track_flush(*_args, **_kwargs):
        flush_called.append(True)

    meta_called: list[bool] = []

    def failing_meta(*_args, **_kwargs):
        meta_called.append(True)
        raise RuntimeError("meta write failed")

    monkeypatch.setattr(round_runner, "review_core_capture", fake_capture)
    monkeypatch.setattr(round_runner, "apply_findings_with_coder", lambda *a, **k: review_and_fix.CoderResult(0, status="applied", input_count=1))
    monkeypatch.setattr(round_runner, "_compose_review_findings_output", lambda *_a, **_k: False)
    monkeypatch.setattr(review_and_fix, "flush_review_batches", lambda *_a, **_k: True)
    monkeypatch.setattr(round_runner, "flush_round_log_after_coder", track_flush)
    monkeypatch.setattr(round_runner.progress_report, "write_implement_round_meta", failing_meta)
    monkeypatch.setattr(round_runner, "_run", lambda argv, **_kw: review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0))
    args = review_and_fix._build_step5_parser().parse_args([
        "--implement-tmpdir", str(impl), "--round-num", "1", "--mode", "single",
        "--session-env-path", str(impl / "session-env.sh"),
        "--plan-file", str(impl / "plan.txt"),
        "--feature-file", str(impl / "feature-description.txt"),
        "--run-id", "run-1",
        "--codex-available", "false",
        "--cursor-available", "false",
    ])
    result = review_and_fix._run_round(args, suppress_emit=True)
    assert result.status == "fix-applied"
    assert meta_called
    assert flush_called


@MARK_CONVERGENCE
def test_prior_summary_accumulates_exonerated_and_neutral(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    (impl / "review-and-fix-summary.json").write_text(
        json.dumps({
            "schema_version": 3,
            "rounds_completed": 1,
            "accepted_count": 1,
            "rejected_count": 2,
            "exonerated_count": 3,
            "neutral_count": 4,
        }),
        encoding="utf-8",
    )
    round_dir = impl / "round-2"
    round_dir.mkdir(parents=True)
    accepted = round_dir / "accepted-findings.md"
    accepted.write_text("", encoding="utf-8")

    def fake_capture(*, core_args, env_path, **_kwargs):
        core_out = env_path  # mapped from env_path kwarg
        out_dir = Path(core_args[core_args.index("--output-dir") + 1])
        (out_dir / "accepted-findings.md").write_text("", encoding="utf-8")
        core_out.write_text(
            "\n".join([
                "REVIEW_CORE_STATUS=ok",
                "ACCEPTED_COUNT=0",
                "REJECTED_COUNT=0",
                "EXONERATED_COUNT=2",
                "NEUTRAL_COUNT=1",
                f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}",
                f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}",
            ]) + "\n",
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(round_runner, "review_core_capture", fake_capture)
    monkeypatch.setattr(round_runner, "_compose_review_findings_output", lambda *_a, **_k: False)
    monkeypatch.setattr(review_and_fix, "flush_review_batches", lambda *_a, **_k: True)
    monkeypatch.setattr(round_runner, "flush_round_log_after_coder", lambda *_a, **_k: None)
    monkeypatch.setattr(round_runner, "_run", lambda argv, **_kw: review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0))
    args = review_and_fix._build_step5_parser().parse_args([
        "--implement-tmpdir", str(impl), "--round-num", "2", "--mode", "single",
        "--session-env-path", str(impl / "session-env.sh"),
        "--plan-file", str(impl / "plan.txt"),
        "--feature-file", str(impl / "feature-description.txt"),
        "--run-id", "run-1",
        "--codex-available", "false",
        "--cursor-available", "false",
    ])
    result = review_and_fix._run_round(args, suppress_emit=True)
    assert result.total_exonerated_count == 5
    assert result.total_neutral_count == 5
    summary = json.loads((impl / "review-and-fix-summary.json").read_text(encoding="utf-8"))
    assert summary["exonerated_count"] == 5
    assert summary["neutral_count"] == 5


@MARK_STEP5
def test_step5_loop_complete_returns_zero_despite_round_rc(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)

    def fake_round(args, *, suppress_emit, review_core_impl=None):
        del args, suppress_emit, review_core_impl
        return review_and_fix.RoundResult(
            2, "complete", "ok", 1, 0, 0, 0, 0, 0, 0, 0, 0,
            impl / "round-1" / "accepted-findings.md",
            impl / "round-1" / "rejected-findings.md",
            impl / "round-1",
            impl / "review-and-fix-summary.json",
            impl / "accumulated-oos.jsonl",
            review_and_fix.CoderResult(0),
        )

    monkeypatch.setattr(review_and_fix, "_run_round", fake_round)
    monkeypatch.setattr(review_and_fix, "record_round_timing", lambda _argv: 0)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1", "--round-cap", "1"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "STEP5_REVIEW_STATUS=complete" in out


@MARK_STEP5
@pytest.mark.parametrize(
    ("round_status", "gate_status", "expected_status"),
    [
        ("complete", "", "complete"),
        ("fix-applied", "cap-hit", "cap-hit"),
    ],
)
def test_step5_terminal_flushes_review_batches_with_counts(
    tmp_path,
    monkeypatch,
    capsys,
    round_status: str,
    gate_status: str,
    expected_status: str,
):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    flush_calls: list[dict[str, object]] = []
    events: list[str] = []
    original_emit = review_and_fix._emit_step5_envelope

    def fake_flush(**kwargs):
        events.append("flush")
        flush_calls.append(kwargs)
        return True

    def fake_emit(**kwargs):
        events.append("envelope")
        original_emit(**kwargs)

    monkeypatch.setattr(review_and_fix, "_run_round", lambda *_a, **_k: _step5_round_result(impl, status=round_status))
    if gate_status:
        monkeypatch.setattr(review_and_fix, "_step5_post_round_gates", lambda **_kw: (gate_status, "", False))
    monkeypatch.setattr(review_and_fix, "record_round_timing", lambda _argv: 0)
    monkeypatch.setattr(review_and_fix, "flush_review_batches", fake_flush)
    monkeypatch.setattr(review_and_fix, "_emit_step5_envelope", fake_emit)

    rc = review_and_fix.step5([
        "--implement-tmpdir", str(impl),
        "--mode", "loop",
        "--starting-round", "1",
        "--round-cap", "1",
        "--run-id", "run-1",
        "--codex-available", "false",
        "--cursor-available", "false",
    ])

    out = capsys.readouterr().out
    assert rc == 0
    assert f"STEP5_REVIEW_STATUS={expected_status}" in out
    assert events == ["flush", "envelope"]
    assert len(flush_calls) == 1
    call = flush_calls[0]
    assert call["run_id"] == "run-1"
    assert call["rounds"] == 1
    assert call["_accepted"] == 5
    assert call["_rejected"] == 6
    assert call["exonerated"] == 7
    assert call["_neutral"] == 8


@MARK_STEP5
@pytest.mark.parametrize(
    ("round_status", "gate_status", "expected_status"),
    [
        ("complete", "", "complete"),
        ("fix-applied", "cap-hit", "cap-hit"),
    ],
)
def test_step5_terminal_restages_resolved_difficulty_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    round_status: str,
    gate_status: str,
    expected_status: str,
) -> None:
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    record = impl / "difficulty-rating.json"
    record.write_text(json.dumps({"audit_evaluated": True, "audit_upgrade": False}), encoding="utf-8")
    stale = impl / "larch-logs" / "implement" / "run-1" / "difficulty-rating.json"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text(json.dumps({"audit_evaluated": None}), encoding="utf-8")
    run_log_calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: object) -> review_and_fix.proc.CommandResult:
        if "run-log" in argv and "write" in argv and "--batch" in argv and argv[argv.index("--batch") + 1] == "difficulty-rating":
            run_log_calls.append(argv)
        return review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(review_and_fix, "_run_round", lambda *_a, **_k: _step5_round_result(impl, status=round_status))
    if gate_status:
        monkeypatch.setattr(review_and_fix, "_step5_post_round_gates", lambda **_kw: (gate_status, "", False))
    monkeypatch.setattr(review_and_fix, "record_round_timing", lambda _argv: 0)
    monkeypatch.setattr(review_and_fix, "flush_review_batches", lambda **_kwargs: True)
    monkeypatch.setattr(review_and_fix, "_run", fake_run)

    rc = review_and_fix.step5([
        "--implement-tmpdir",
        str(impl),
        "--mode",
        "loop",
        "--starting-round",
        "1",
        "--round-cap",
        "1",
        "--run-id",
        "run-1",
        "--codex-available",
        "false",
        "--cursor-available",
        "false",
    ])

    out = capsys.readouterr().out
    assert rc == 0
    assert f"STEP5_REVIEW_STATUS={expected_status}" in out
    assert len(run_log_calls) == 1
    call = run_log_calls[0]
    assert call[call.index("--log-root") + 1] == str(impl / "larch-logs")
    assert call[call.index("--run-id") + 1] == "run-1"
    assert call[call.index("--input-file") + 1] == str(record)
    assert call[call.index("--input-file") + 1] != str(stale)


@MARK_STEP5
def test_step5_difficulty_restage_warning_preserves_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    (impl / "difficulty-rating.json").write_text(json.dumps({"audit_evaluated": True}), encoding="utf-8")

    def fake_run(argv: list[str], **_kwargs: object) -> review_and_fix.proc.CommandResult:
        if "run-log" in argv and "write" in argv:
            return review_and_fix.proc.CommandResult(tuple(argv), 1, "", "write boom", 0.0)
        return review_and_fix.proc.CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(review_and_fix, "_run_round", lambda *_a, **_k: _step5_round_result(impl, status="complete"))
    monkeypatch.setattr(review_and_fix, "record_round_timing", lambda _argv: 0)
    monkeypatch.setattr(review_and_fix, "flush_review_batches", lambda **_kwargs: True)
    monkeypatch.setattr(review_and_fix, "_run", fake_run)

    rc = review_and_fix.step5([
        "--implement-tmpdir",
        str(impl),
        "--mode",
        "loop",
        "--starting-round",
        "1",
        "--round-cap",
        "1",
        "--run-id",
        "run-1",
        "--codex-available",
        "false",
        "--cursor-available",
        "false",
    ])

    captured = capsys.readouterr()
    assert rc == 0
    assert "STEP5_REVIEW_STATUS=complete" in captured.out
    assert "difficulty-rating batch restage failed: helper-exit-1: write boom" in captured.err
    issues = (impl / "execution-issues.md").read_text(encoding="utf-8")
    assert "### Warnings" in issues
    assert "difficulty-rating` restage failed" in issues
    assert "helper-exit-1: write boom" in issues


@MARK_STEP5
@pytest.mark.parametrize("append_raises", [False, True])
def test_step5_complete_flush_warning_preserves_success(
    tmp_path,
    monkeypatch,
    capsys,
    append_raises: bool,
):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)

    def fail_flush(**_kwargs):
        raise RuntimeError("flush boom")

    def fail_append(**_kwargs):
        raise OSError("append boom")

    monkeypatch.setattr(review_and_fix, "_run_round", lambda *_a, **_k: _step5_round_result(impl, status="complete"))
    monkeypatch.setattr(review_and_fix, "record_round_timing", lambda _argv: 0)
    monkeypatch.setattr(review_and_fix, "flush_review_batches", fail_flush)
    if append_raises:
        monkeypatch.setattr(review_and_fix.run_logs, "append_execution_issue", fail_append)

    rc = review_and_fix.step5([
        "--implement-tmpdir", str(impl),
        "--mode", "loop",
        "--starting-round", "1",
        "--round-cap", "1",
        "--run-id", "run-1",
        "--codex-available", "false",
        "--cursor-available", "false",
    ])

    captured = capsys.readouterr()
    assert rc == 0
    assert "STEP5_REVIEW_STATUS=complete" in captured.out
    assert "code-review batch flush failed: flush boom" in captured.err
    if not append_raises:
        issues = (impl / "execution-issues.md").read_text(encoding="utf-8")
        assert "### Warnings" in issues
        assert "code-review` flush failed" in issues
        assert "flush boom" in issues


@MARK_CONVERGENCE
def test_step5_loop_prune_skipped_converges_below_cap(tmp_path, monkeypatch, capsys):
    # #5255: a prune-to-empty round (every reviewer pruned, zero findings) must
    # converge the loop immediately rather than advancing toward the round-2
    # backup pass.
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)

    def fake_round(args, *, suppress_emit, review_core_impl=None):
        del args, suppress_emit, review_core_impl
        return review_and_fix.RoundResult(
            0, "prune-skipped", "prune-skipped", 1, 0, 0, 0, 0, 0, 0, 0, 0,
            impl / "round-1" / "accepted-findings.md",
            impl / "round-1" / "rejected-findings.md",
            impl / "round-1",
            impl / "review-and-fix-summary.json",
            impl / "accumulated-oos.jsonl",
            review_and_fix.CoderResult(0),
        )

    monkeypatch.setattr(review_and_fix, "_run_round", fake_round)
    monkeypatch.setattr(review_and_fix, "record_round_timing", lambda _argv: 0)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1", "--round-cap", "2"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "STEP5_REVIEW_STATUS=complete" in out
    # Converged on the first prune-empty round; did not advance past round 2.
    assert "ROUNDS_COMPLETED=1" in out


@MARK_STEP5
def test_step5_fix_applied_records_round_timing_after_post_round_gates(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    events: list[str] = []
    timing_calls: list[list[str]] = []
    now = {"value": 99}
    gate_done = {"value": 0}

    def fake_time() -> int:
        now["value"] += 1
        return now["value"]

    def fake_round(args, *, suppress_emit, review_core_impl=None):
        del args, suppress_emit, review_core_impl
        events.append("round")
        return _fix_applied_round_result(impl)

    def fake_gates(*, result, round_num, round_cap):
        del result, round_num, round_cap
        assert not timing_calls
        events.append("gates")
        now["value"] = 200
        gate_done["value"] = now["value"]
        return "complete", "", False

    def fake_record(argv):
        events.append("record")
        timing_calls.append(argv)
        return 0

    monkeypatch.setattr(review_and_fix.time, "time", fake_time)
    monkeypatch.setattr(review_and_fix, "_run_round", fake_round)
    monkeypatch.setattr(review_and_fix, "_step5_post_round_gates", fake_gates)
    monkeypatch.setattr(review_and_fix, "record_round_timing", fake_record)

    rc = review_and_fix.step5([
        "--implement-tmpdir", str(impl),
        "--mode", "loop",
        "--starting-round", "1",
        "--round-cap", "1",
    ])
    _ = capsys.readouterr()

    assert rc == 0
    assert events == ["round", "gates", "record"]
    assert len(timing_calls) == 1
    call = timing_calls[0]
    assert call[call.index("--start-s") + 1] == "100"
    assert int(call[call.index("--end-s") + 1]) > gate_done["value"]


@MARK_STEP5
def test_step5_fix_applied_gate_continue_records_before_next_round(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    events: list[str] = []
    timing_calls: list[list[str]] = []
    now = {"value": 299}

    def fake_time() -> int:
        now["value"] += 1
        return now["value"]

    def fake_round(args, *, suppress_emit, review_core_impl=None):
        del suppress_emit, review_core_impl
        round_num = int(args.round_num)
        events.append(f"round-{round_num}")
        if round_num == 1:
            return _fix_applied_round_result(impl, round_num=1)
        return review_and_fix.RoundResult(
            0,
            "complete",
            "ok",
            2,
            0,
            0,
            0,
            0,
            1,
            0,
            0,
            0,
            impl / "round-2" / "accepted-findings.md",
            impl / "round-2" / "rejected-findings.md",
            impl / "round-2",
            impl / "review-and-fix-summary.json",
            impl / "accumulated-oos.jsonl",
            review_and_fix.CoderResult(0),
        )

    def fake_gates(*, result, round_num, round_cap):
        del result, round_cap
        events.append(f"gates-{round_num}")
        return None, None, True

    def fake_record(argv):
        events.append(f"record-{argv[argv.index('--round') + 1]}")
        timing_calls.append(argv)
        return 0

    monkeypatch.setattr(review_and_fix.time, "time", fake_time)
    monkeypatch.setattr(review_and_fix, "_run_round", fake_round)
    monkeypatch.setattr(review_and_fix, "_step5_post_round_gates", fake_gates)
    monkeypatch.setattr(review_and_fix, "record_round_timing", fake_record)

    rc = review_and_fix.step5([
        "--implement-tmpdir", str(impl),
        "--mode", "loop",
        "--starting-round", "1",
        "--round-cap", "2",
    ])
    _ = capsys.readouterr()

    assert rc == 0
    assert events[:4] == ["round-1", "gates-1", "record-1", "round-2"]
    round_one_calls = [
        call for call in timing_calls
        if call[call.index("--round") + 1] == "1"
    ]
    assert len(round_one_calls) == 1
    assert round_one_calls[0][round_one_calls[0].index("--start-s") + 1] == "300"


@MARK_STEP5
def test_step5_fix_applied_post_gate_exception_still_records_round_timing(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    timing_calls: list[list[str]] = []
    now = {"value": 399}

    def fake_time() -> int:
        now["value"] += 1
        return now["value"]

    def fake_round(args, *, suppress_emit, review_core_impl=None):
        del args, suppress_emit, review_core_impl
        return _fix_applied_round_result(impl)

    def fake_gates(*, result, round_num, round_cap):
        del result, round_num, round_cap
        now["value"] = 500
        raise RuntimeError("post-gate boom")

    def fake_record(argv):
        timing_calls.append(argv)
        return 0

    monkeypatch.setattr(review_and_fix.time, "time", fake_time)
    monkeypatch.setattr(review_and_fix, "_run_round", fake_round)
    monkeypatch.setattr(review_and_fix, "_step5_post_round_gates", fake_gates)
    monkeypatch.setattr(review_and_fix, "record_round_timing", fake_record)

    rc = review_and_fix.step5([
        "--implement-tmpdir", str(impl),
        "--mode", "loop",
        "--starting-round", "1",
        "--round-cap", "1",
    ])
    out = capsys.readouterr().out

    assert rc == 2
    assert "STEP5_REVIEW_STATUS=stall" in out
    assert len(timing_calls) == 1
    call = timing_calls[0]
    assert call[call.index("--start-s") + 1] == "400"
    assert int(call[call.index("--end-s") + 1]) > 500


@MARK_STEP5
def test_step5_loop_preflight_failure_touches_progress_done(tmp_path, monkeypatch):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    (impl / "plan.txt").write_text("", encoding="utf-8")
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1"])
    assert rc == 2
    assert (impl / "progress" / "done").is_file()


@MARK_CHECK_CHANGES
def _mk_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    review_and_fix._run(["git", "init", "--quiet"], cwd=repo)
    review_and_fix._run(["git", "config", "user.email", "test@example.com"], cwd=repo)
    review_and_fix._run(["git", "config", "user.name", "Test"], cwd=repo)
    (repo / "tracked.txt").write_text("initial\n", encoding="utf-8")
    review_and_fix._run(["git", "add", "tracked.txt"], cwd=repo)
    review_and_fix._run(["git", "commit", "--quiet", "-m", "initial"], cwd=repo)
    return repo


def _coder_findings(tmp_path: Path) -> Path:
    findings = tmp_path / "findings.md"
    findings.write_text("### FINDING_1: fix\n- **Severity**: nit\n", encoding="utf-8")
    return findings


def _patch_coder_basics(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_scrub(*, input_file: Path, output_file: Path, log_file: Path) -> tuple[bool, int]:
        shutil.copyfile(input_file, output_file)
        return True, 0

    monkeypatch.setattr(coder_runner, "_scrub_findings", fake_scrub)
    monkeypatch.setattr(coder_runner, "_submodule_paths", list)
    monkeypatch.setattr(coder_runner, "_run_coder_codex", lambda *_a, **_k: False)
    monkeypatch.setattr(coder_runner, "_run_coder_cursor", lambda *_a, **_k: False)
    monkeypatch.setattr(coder_runner, "_run_coder_claude", lambda *_a, **_k: False)


def _git_porcelain(repo: Path) -> str:
    return review_and_fix._run(["git", "status", "--porcelain"], cwd=repo).stdout


def _git_cached_names(repo: Path) -> str:
    return review_and_fix._run(["git", "diff", "--cached", "--name-only"], cwd=repo).stdout


@MARK_DISPATCH
def test_apply_findings_with_coder_failed_codex_cleans_and_falls_through_to_cursor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    _patch_coder_basics(monkeypatch)
    round_dir = tmp_path / "impl" / "round-1"

    def codex(*, round_dir: Path, prompt_body: str, tool_log: Path) -> bool:
        (repo / "tracked.txt").write_text("codex\n", encoding="utf-8")
        review_and_fix._run(["git", "add", "tracked.txt"])
        return False

    def cursor(*, round_dir: Path, prompt_body: str, tool_log: Path) -> bool:
        (repo / "tracked.txt").write_text("cursor\n", encoding="utf-8")
        tool_log.write_text("cursor\n", encoding="utf-8")
        return True

    monkeypatch.setattr(coder_runner, "_run_coder_cursor", cursor)
    monkeypatch.setattr(coder_runner, "_run_coder_codex", codex)
    result = review_and_fix.apply_findings_with_coder(input_file=_coder_findings(tmp_path), round_dir=round_dir, result_file=round_dir / "coder.env")

    assert result.rc == 0
    assert result.tool == "cursor"
    assert result.status == "applied"
    assert (repo / "tracked.txt").read_text(encoding="utf-8") == "cursor\n"


@MARK_DISPATCH
def test_apply_findings_with_coder_records_scrubbed_payload_bytes_and_tsv_row(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    _patch_coder_basics(monkeypatch)
    round_dir = tmp_path / "impl" / "round-1"
    findings = _coder_findings(tmp_path)
    scrubbed_bytes = findings.read_bytes()

    def codex(*, round_dir: Path, prompt_body: str, tool_log: Path) -> bool:
        (repo / "tracked.txt").write_text("codex\n", encoding="utf-8")
        review_and_fix._run(["git", "add", "tracked.txt"])
        tool_log.write_text("codex\n", encoding="utf-8")
        return True

    monkeypatch.setattr(coder_runner, "_run_coder_codex", codex)
    monkeypatch.setattr(coder_runner, "_stage_and_commit_round", lambda **_kwargs: review_and_fix.RoundCommitResult(sha="deadbeef"))

    result = review_and_fix.apply_findings_with_coder(
        input_file=findings,
        round_dir=round_dir,
        result_file=round_dir / "coder.env",
        round_num=1,
    )

    assert result.rc == 0
    assert result.tool == "codex"
    assert result.status == "applied"
    tsv = round_dir / "panel-prompt-sizes.tsv"
    rows = [line for line in tsv.read_text(encoding="utf-8").splitlines() if line and not line.startswith("site\t")]
    assert len(rows) == 1
    fields = rows[0].split("\t")
    assert fields[11] == str(len(scrubbed_bytes))
    assert fields[12] == str((len(scrubbed_bytes) + 3) // 4)


@MARK_DISPATCH
def test_apply_findings_with_coder_commit_failure_cleans_and_falls_through(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    _patch_coder_basics(monkeypatch)
    round_dir = tmp_path / "impl" / "round-1"

    def cursor(*, round_dir: Path, prompt_body: str, tool_log: Path) -> bool:
        (repo / "tracked.txt").write_text("cursor\n", encoding="utf-8")
        tool_log.write_text("cursor\n", encoding="utf-8")
        return True

    def codex(*, round_dir: Path, prompt_body: str, tool_log: Path) -> bool:
        tool_log.write_text("codex noop\n", encoding="utf-8")
        return True

    def fail_commit(*, round_num: int, round_dir: Path) -> review_and_fix.RoundCommitResult:
        review_and_fix._run(["git", "add", "tracked.txt"])
        return review_and_fix.RoundCommitResult()

    monkeypatch.setattr(coder_runner, "_run_coder_cursor", cursor)
    monkeypatch.setattr(coder_runner, "_run_coder_codex", codex)
    monkeypatch.setattr(coder_runner, "_stage_and_commit_round", fail_commit)

    result = review_and_fix.apply_findings_with_coder(
        input_file=_coder_findings(tmp_path),
        round_dir=round_dir,
        result_file=round_dir / "coder.env",
        round_num=1
    )

    assert result.rc == 4
    assert result.tool == "none"
    assert result.status == "main-agent-required"
    assert _git_porcelain(repo) == ""
    assert (repo / "tracked.txt").read_text(encoding="utf-8") == "initial\n"


@MARK_DISPATCH
def test_apply_findings_with_coder_stale_index_lock_status_skips_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    _patch_coder_basics(monkeypatch)
    round_dir = tmp_path / "impl" / "round-1"
    result_file = round_dir / "coder.env"

    def cursor(*, round_dir: Path, prompt_body: str, tool_log: Path) -> bool:
        (repo / "tracked.txt").write_text("cursor\n", encoding="utf-8")
        tool_log.write_text("cursor\n", encoding="utf-8")
        return True

    def stale_commit(*, round_num: int, round_dir: Path) -> review_and_fix.RoundCommitResult:
        return review_and_fix.RoundCommitResult(failure_reason="stale-index-lock")

    monkeypatch.setattr(coder_runner, "_run_coder_cursor", cursor)
    monkeypatch.setattr(coder_runner, "_stage_and_commit_round", stale_commit)

    result = review_and_fix.apply_findings_with_coder(
        input_file=_coder_findings(tmp_path),
        round_dir=round_dir,
        result_file=result_file,
        round_num=1
    )

    assert result.rc == 2
    assert result.status == "stale-index-lock"
    assert "CODER_STATUS=stale-index-lock" in result_file.read_text(encoding="utf-8")
    assert (repo / "tracked.txt").read_text(encoding="utf-8") == "cursor\n"


@MARK_DISPATCH
def test_apply_findings_with_coder_all_coders_exhausted_returns_main_agent_required_clean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    _patch_coder_basics(monkeypatch)
    round_dir = tmp_path / "impl" / "round-1"

    def cursor(*, round_dir: Path, prompt_body: str, tool_log: Path) -> bool:
        (repo / "tracked.txt").write_text("cursor\n", encoding="utf-8")
        review_and_fix._run(["git", "add", "tracked.txt"])
        (repo / "newdir").mkdir()
        (repo / "newdir" / "file.py").write_text("x\n", encoding="utf-8")
        return False

    monkeypatch.setattr(coder_runner, "_run_coder_cursor", cursor)
    monkeypatch.setattr(coder_runner, "_run_coder_codex", lambda *_a, **_k: False)

    result = review_and_fix.apply_findings_with_coder(input_file=_coder_findings(tmp_path), round_dir=round_dir, result_file=round_dir / "coder.env")

    assert result.rc == 4
    assert result.status == "main-agent-required"
    assert _git_porcelain(repo) == ""
    assert not (repo / "newdir").exists()
    assert (round_dir / "coder-main-agent-required.log").read_text(encoding="utf-8") == "main-agent-required\n"
    ledger = round_dir.parent / "timing-ledger.tsv"
    assert "\tclaude\tclaude-review-fix\t" in ledger.read_text(encoding="utf-8")


@MARK_DISPATCH
def test_apply_findings_with_coder_submodule_violation_terminal_but_clean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    _patch_coder_basics(monkeypatch)
    monkeypatch.setattr(coder_runner, "_submodule_paths", lambda: ["vendor"])
    round_dir = tmp_path / "impl" / "round-1"

    def cursor(*, round_dir: Path, prompt_body: str, tool_log: Path) -> bool:
        (repo / "vendor").mkdir()
        (repo / "vendor" / "file.txt").write_text("bad\n", encoding="utf-8")
        tool_log.write_text("cursor\n", encoding="utf-8")
        return True

    monkeypatch.setattr(coder_runner, "_run_coder_cursor", cursor)
    monkeypatch.setattr(coder_runner, "_run_coder_codex", lambda *_a, **_k: False)

    result = review_and_fix.apply_findings_with_coder(input_file=_coder_findings(tmp_path), round_dir=round_dir, result_file=round_dir / "coder.env")

    assert result.rc == 3
    assert result.status == "submodule-violation"
    assert _git_porcelain(repo) == ""


@MARK_DISPATCH
def test_apply_findings_with_coder_unavailable_preserves_preexisting_tracked_edit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    _patch_coder_basics(monkeypatch)
    (repo / "tracked.txt").write_text("user edit\n", encoding="utf-8")
    round_dir = tmp_path / "impl" / "round-1"

    monkeypatch.setattr(coder_runner, "_run_coder_cursor", lambda *_a, **_k: False)
    monkeypatch.setattr(coder_runner, "_run_coder_codex", lambda *_a, **_k: False)

    result = review_and_fix.apply_findings_with_coder(input_file=_coder_findings(tmp_path), round_dir=round_dir, result_file=round_dir / "coder.env")

    assert result.rc == 4
    assert (repo / "tracked.txt").read_text(encoding="utf-8") == "user edit\n"
    assert " M tracked.txt" in _git_porcelain(repo)


@MARK_DISPATCH
def test_apply_findings_with_coder_full_snapshot_preserves_staged_carryover(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    _patch_coder_basics(monkeypatch)
    (repo / "carry.txt").write_text("staged\n", encoding="utf-8")
    review_and_fix._run(["git", "add", "carry.txt"])
    round_dir = tmp_path / "impl" / "round-1"

    def cursor(*, round_dir: Path, prompt_body: str, tool_log: Path) -> bool:
        (repo / "carry.txt").write_text("coder overwrite\n", encoding="utf-8")
        return False

    monkeypatch.setattr(coder_runner, "_run_coder_cursor", cursor)
    monkeypatch.setattr(coder_runner, "_run_coder_codex", lambda *_a, **_k: False)

    result = review_and_fix.apply_findings_with_coder(input_file=_coder_findings(tmp_path), round_dir=round_dir, result_file=round_dir / "coder.env")

    assert result.rc == 4
    assert (repo / "carry.txt").read_text(encoding="utf-8") == "staged\n"
    assert _git_cached_names(repo) == "carry.txt\n"


@MARK_DISPATCH
def test_apply_findings_with_coder_legacy_head_only_not_upgraded_to_full(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    _patch_coder_basics(monkeypatch)
    round_dir = tmp_path / "impl" / "round-1"
    snap = review_and_fix.pre_coder_snapshot_dir(round_dir)
    snap.mkdir(parents=True)
    (snap / "pre-coder-head.txt").write_text(review_and_fix._git_head() + "\n", encoding="utf-8")

    monkeypatch.setattr(coder_runner, "_run_coder_cursor", lambda *_a, **_k: False)
    monkeypatch.setattr(coder_runner, "_run_coder_codex", lambda *_a, **_k: False)

    result = review_and_fix.apply_findings_with_coder(input_file=_coder_findings(tmp_path), round_dir=round_dir, result_file=round_dir / "coder.env")

    assert result.rc == 4
    assert not (snap / "pre-coder-tracked-paths.txt").exists()
    assert (snap / "pre-coder-untracked-paths.txt").is_file()


@MARK_DISPATCH
def test_apply_findings_with_coder_head_only_no_edit_preserves_preexisting_untracked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    _patch_coder_basics(monkeypatch)
    (repo / "stray.txt").write_text("user\n", encoding="utf-8")
    round_dir = tmp_path / "impl" / "round-1"
    snap = review_and_fix.pre_coder_snapshot_dir(round_dir)
    snap.mkdir(parents=True)
    (snap / "pre-coder-head.txt").write_text(review_and_fix._git_head() + "\n", encoding="utf-8")

    monkeypatch.setattr(coder_runner, "_run_coder_cursor", lambda *_a, **_k: False)
    monkeypatch.setattr(coder_runner, "_run_coder_codex", lambda *_a, **_k: False)

    result = review_and_fix.apply_findings_with_coder(input_file=_coder_findings(tmp_path), round_dir=round_dir, result_file=round_dir / "coder.env")

    assert result.rc == 4
    assert (repo / "stray.txt").read_text(encoding="utf-8") == "user\n"


@MARK_DISPATCH
def test_apply_findings_with_coder_successful_noop_with_baseline_dirt_falls_through(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    _patch_coder_basics(monkeypatch)
    (repo / "tracked.txt").write_text("user edit\n", encoding="utf-8")
    round_dir = tmp_path / "impl" / "round-1"

    def cursor(*, round_dir: Path, prompt_body: str, tool_log: Path) -> bool:
        tool_log.write_text("noop\n", encoding="utf-8")
        return True

    monkeypatch.setattr(coder_runner, "_run_coder_cursor", cursor)
    monkeypatch.setattr(coder_runner, "_run_coder_codex", lambda *_a, **_k: False)

    result = review_and_fix.apply_findings_with_coder(input_file=_coder_findings(tmp_path), round_dir=round_dir, result_file=round_dir / "coder.env")

    assert result.rc == 4
    assert result.status == "main-agent-required"
    assert (repo / "tracked.txt").read_text(encoding="utf-8") == "user edit\n"


@MARK_DISPATCH
def test_apply_findings_with_coder_failed_coder_new_untracked_directory_removed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    _patch_coder_basics(monkeypatch)
    round_dir = tmp_path / "impl" / "round-1"

    def cursor(*, round_dir: Path, prompt_body: str, tool_log: Path) -> bool:
        (repo / "newdir").mkdir()
        (repo / "newdir" / "file.py").write_text("x\n", encoding="utf-8")
        return False

    monkeypatch.setattr(coder_runner, "_run_coder_cursor", cursor)
    monkeypatch.setattr(coder_runner, "_run_coder_codex", lambda *_a, **_k: False)

    result = review_and_fix.apply_findings_with_coder(input_file=_coder_findings(tmp_path), round_dir=round_dir, result_file=round_dir / "coder.env")

    assert result.rc == 4
    assert not (repo / "newdir").exists()
    assert _git_porcelain(repo) == ""


@MARK_DISPATCH
def test_apply_findings_with_coder_head_only_successful_noedit_falls_through_without_staging_preexisting_untracked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    _patch_coder_basics(monkeypatch)
    (repo / "stray.txt").write_text("user\n", encoding="utf-8")
    round_dir = tmp_path / "impl" / "round-1"
    snap = review_and_fix.pre_coder_snapshot_dir(round_dir)
    snap.mkdir(parents=True)
    (snap / "pre-coder-head.txt").write_text(review_and_fix._git_head() + "\n", encoding="utf-8")

    def cursor(*, round_dir: Path, prompt_body: str, tool_log: Path) -> bool:
        tool_log.write_text("noop\n", encoding="utf-8")
        return True

    monkeypatch.setattr(coder_runner, "_run_coder_cursor", cursor)
    monkeypatch.setattr(coder_runner, "_run_coder_codex", lambda *_a, **_k: False)

    result = review_and_fix.apply_findings_with_coder(
        input_file=_coder_findings(tmp_path),
        round_dir=round_dir,
        result_file=round_dir / "coder.env",
        round_num=1
    )

    assert result.rc == 4
    assert result.status == "main-agent-required"
    assert (repo / "stray.txt").is_file()
    assert _git_cached_names(repo) == ""


@MARK_DISPATCH
def test_apply_findings_with_coder_cleanup_verification_failure_stops_without_staged_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    _patch_coder_basics(monkeypatch)
    round_dir = tmp_path / "impl" / "round-1"

    def cursor(*, round_dir: Path, prompt_body: str, tool_log: Path) -> bool:
        (repo / "tracked.txt").write_text("cursor\n", encoding="utf-8")
        review_and_fix._run(["git", "add", "tracked.txt"])
        return False

    monkeypatch.setattr(coder_runner, "_run_coder_cursor", cursor)
    monkeypatch.setattr(coder_runner, "_run_coder_codex", lambda *_a, **_k: True)
    monkeypatch.setattr(snapshot, "_verify_post_cleanup_state", lambda *_a, **_k: (False, "forced failure"))

    result = review_and_fix.apply_findings_with_coder(input_file=_coder_findings(tmp_path), round_dir=round_dir, result_file=round_dir / "coder.env")

    assert result.rc == 2
    assert result.status == "failed"
    assert _git_cached_names(repo) == ""
    assert _git_porcelain(repo) == ""


@MARK_DISPATCH
def test_apply_findings_with_coder_full_snapshot_partial_cleanup_verification_mismatch_stops_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    _patch_coder_basics(monkeypatch)
    (repo / "tracked.txt").write_text("user edit\n", encoding="utf-8")
    round_dir = tmp_path / "impl" / "round-1"
    review_and_fix._write_pre_coder_snapshot(round_dir)
    assert snapshot._snapshot_mode(round_dir) == "full"
    cursor_calls: list[bool] = []
    original_matches = snapshot._path_matches_pre_coder_snapshot

    def codex(*, round_dir: Path, prompt_body: str, tool_log: Path) -> bool:
        (repo / "tracked.txt").write_text("codex\n", encoding="utf-8")
        review_and_fix._run(["git", "add", "tracked.txt"])
        return False

    def cursor(*, round_dir: Path, prompt_body: str, tool_log: Path) -> bool:
        cursor_calls.append(True)
        return True

    def path_matches(*, round_dir: Path, pre_head: str, path: str) -> bool:
        if path == "tracked.txt":
            return False
        return original_matches(round_dir=round_dir, pre_head=pre_head, path=path)

    monkeypatch.setattr(coder_runner, "_run_coder_cursor", cursor)
    monkeypatch.setattr(coder_runner, "_run_coder_codex", codex)
    monkeypatch.setattr(snapshot, "_path_matches_pre_coder_snapshot", path_matches)

    result = review_and_fix.apply_findings_with_coder(input_file=_coder_findings(tmp_path), round_dir=round_dir, result_file=round_dir / "coder.env")

    assert result.rc == 2
    assert result.status == "failed"
    assert not cursor_calls
    assert _git_cached_names(repo) == ""
    assert (repo / "tracked.txt").read_text(encoding="utf-8") == "user edit\n"
    cleanup_log = (round_dir / "coder-cleanup.log").read_text(encoding="utf-8")
    assert "pre-coder snapshot mismatch: tracked.txt" in cleanup_log


@MARK_DISPATCH
def test_apply_findings_with_coder_finalize_preserves_staged_carryover(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    _patch_coder_basics(monkeypatch)
    (repo / "carry.txt").write_text("staged\n", encoding="utf-8")
    review_and_fix._run(["git", "add", "carry.txt"])
    round_dir = tmp_path / "impl" / "round-1"

    def cursor(*, round_dir: Path, prompt_body: str, tool_log: Path) -> bool:
        (repo / "carry.txt").write_text("coder overwrite\n", encoding="utf-8")
        return False

    monkeypatch.setattr(coder_runner, "_run_coder_cursor", cursor)
    monkeypatch.setattr(coder_runner, "_run_coder_codex", lambda *_a, **_k: True)
    monkeypatch.setattr(snapshot, "_verify_post_cleanup_state", lambda *_a, **_k: (False, "forced failure"))

    result = review_and_fix.apply_findings_with_coder(input_file=_coder_findings(tmp_path), round_dir=round_dir, result_file=round_dir / "coder.env")

    assert result.rc == 2
    assert result.status == "failed"
    assert (repo / "carry.txt").read_text(encoding="utf-8") == "staged\n"
    assert _git_cached_names(repo) == "carry.txt\n"


@MARK_DISPATCH
def test_apply_findings_with_coder_stale_snapshot_entry_finalizes_before_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    _patch_coder_basics(monkeypatch)
    round_dir = tmp_path / "impl" / "round-1"
    review_and_fix._write_pre_coder_snapshot(round_dir)
    (repo / "tracked.txt").write_text("committed advance\n", encoding="utf-8")
    review_and_fix._run(["git", "add", "tracked.txt"])
    review_and_fix._run(["git", "commit", "--quiet", "-m", "advance head"])
    (repo / "tracked.txt").write_text("staged residue\n", encoding="utf-8")
    review_and_fix._run(["git", "add", "tracked.txt"])

    result = review_and_fix.apply_findings_with_coder(input_file=_coder_findings(tmp_path), round_dir=round_dir, result_file=round_dir / "coder.env")

    assert result.rc == 2
    assert result.tool == "none"
    assert result.status == "failed"
    assert "cleanup failure: stale pre-coder snapshot" in (round_dir / "coder-cleanup.log").read_text(encoding="utf-8")


@MARK_DISPATCH
def test_apply_findings_with_coder_head_untracked_preserves_staged_carryover(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    _patch_coder_basics(monkeypatch)
    (repo / "carry.txt").write_text("staged\n", encoding="utf-8")
    review_and_fix._run(["git", "add", "carry.txt"])
    round_dir = tmp_path / "impl" / "round-1"
    snap = review_and_fix.pre_coder_snapshot_dir(round_dir)
    snap.mkdir(parents=True)
    (snap / "pre-coder-head.txt").write_text(review_and_fix._git_head() + "\n", encoding="utf-8")

    def cursor(*, round_dir: Path, prompt_body: str, tool_log: Path) -> bool:
        (repo / "carry.txt").write_text("coder overwrite\n", encoding="utf-8")
        review_and_fix._run(["git", "add", "carry.txt"])
        return False

    monkeypatch.setattr(coder_runner, "_run_coder_cursor", cursor)
    monkeypatch.setattr(coder_runner, "_run_coder_codex", lambda *_a, **_k: False)

    result = review_and_fix.apply_findings_with_coder(input_file=_coder_findings(tmp_path), round_dir=round_dir, result_file=round_dir / "coder.env")

    assert result.rc == 4
    assert (repo / "carry.txt").read_text(encoding="utf-8") == "staged\n"
    assert _git_cached_names(repo) == "carry.txt\n"


@MARK_DISPATCH
def test_apply_findings_with_coder_head_untracked_failed_cleans_new_untracked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    _patch_coder_basics(monkeypatch)
    round_dir = tmp_path / "impl" / "round-1"
    snap = review_and_fix.pre_coder_snapshot_dir(round_dir)
    snap.mkdir(parents=True)
    (snap / "pre-coder-head.txt").write_text(review_and_fix._git_head() + "\n", encoding="utf-8")

    def cursor(*, round_dir: Path, prompt_body: str, tool_log: Path) -> bool:
        (repo / "new-untracked.txt").write_text("coder\n", encoding="utf-8")
        return False

    monkeypatch.setattr(coder_runner, "_run_coder_cursor", cursor)
    monkeypatch.setattr(coder_runner, "_run_coder_codex", lambda *_a, **_k: False)

    result = review_and_fix.apply_findings_with_coder(input_file=_coder_findings(tmp_path), round_dir=round_dir, result_file=round_dir / "coder.env")

    assert result.rc == 4
    assert not (repo / "new-untracked.txt").exists()
    assert _git_porcelain(repo) == ""


@MARK_CHECK_CHANGES
def test_check_changes_clean_tree_no_baseline(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    rc = review_and_fix.check_changes([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "FILES_CHANGED=false" in out
    assert "UNTRACKED_BASELINE=missing" in out


@MARK_CHECK_CHANGES
def test_check_changes_preexisting_untracked_with_baseline(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    repo = _mk_git_repo(tmp_path)
    (repo / "stray.txt").write_text("x\n", encoding="utf-8")
    ls = review_and_fix._run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=repo,
    )
    baseline = tmp_path / "baseline.txt"
    baseline.write_text(ls.stdout, encoding="utf-8")
    monkeypatch.chdir(repo)
    rc = review_and_fix.check_changes(["--baseline", str(baseline)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "FILES_CHANGED=false" in out
    assert "UNTRACKED_BASELINE=present" in out


@MARK_CHECK_CHANGES
def test_check_changes_head_baseline_detects_commit_movement(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    repo = _mk_git_repo(tmp_path)
    head_bl = repo / "pre-review-head.txt"
    review_and_fix._run(["git", "rev-parse", "HEAD"], cwd=repo)
    head_bl.write_text(review_and_fix._run(["git", "rev-parse", "HEAD"], cwd=repo).stdout, encoding="utf-8")
    (repo / "tracked.txt").write_text("initial\nreview-fix\n", encoding="utf-8")
    review_and_fix._run(["git", "add", "tracked.txt"], cwd=repo)
    review_and_fix._run(["git", "commit", "--quiet", "-m", "Address code review feedback (round 1)"], cwd=repo)
    monkeypatch.chdir(repo)
    rc = review_and_fix.check_changes(["--head-baseline", str(head_bl)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "FILES_CHANGED=true" in out


@MARK_CHECK_CHANGES
def test_check_changes_strict_promotes_probe_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    sandbox = tmp_path / "not-a-git-repo"
    sandbox.mkdir()
    monkeypatch.chdir(sandbox)
    rc = review_and_fix.check_changes(["--strict"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "FILES_CHANGED=true" in out
    assert "GIT_PROBE_FAILED=true" in out


@MARK_CONVERGENCE
def test_step5_post_round_gates_bulk_skip_ratio_continues(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    accepted = round_dir / "accepted-findings.md"
    accepted.write_text("### FINDING_1: a\n", encoding="utf-8")
    result = review_and_fix.RoundResult(
        0, "fix-applied", "fix-required", 1, 4, 0, 0, 0, 4, 0, 0, 0,
        accepted, round_dir / "rejected-findings.md", round_dir,
        impl / "review-and-fix-summary.json", impl / "accumulated-oos.jsonl",
        review_and_fix.CoderResult(0, input_count=4, status="applied"),
        skipped_finding_count=3,
    )
    monkeypatch.setattr(review_and_fix, "_skip_ratio_threshold", lambda: 0.5)
    status, reason, cont = review_and_fix._step5_post_round_gates(result=result, round_num=1, round_cap=2)
    assert status is None
    assert reason is None
    assert cont is True


@MARK_DISPATCH
def test_core_args_for_round_forwards_pre_scouted_manifest(tmp_path):
    impl = _tmp_impl(tmp_path)
    manifest = impl / "scout-coder-manifest.json"
    manifest.write_text("{}\n", encoding="utf-8")
    args = review_and_fix._build_step5_parser().parse_args([
        "--implement-tmpdir", str(impl),
        "--round-num", "1",
        "--session-env-path", str(impl / "session-env.sh"),
        "--plan-file", str(impl / "plan.txt"),
        "--feature-file", str(impl / "feature-description.txt"),
        "--pre-scouted-manifest", str(manifest),
        "--codex-available", "false",
        "--cursor-available", "false",
    ])
    core_args = round_runner._core_args_for_round(args=args, round_dir=impl / "round-1", dynamic_archetypes="0", prune_ledger=impl / "ledger.tsv")
    idx = core_args.index("--pre-scouted-manifest")
    assert core_args[idx + 1] == str(manifest)


def test_core_args_for_round_threads_implement_step5_site(tmp_path):
    impl = _tmp_impl(tmp_path)
    args = review_and_fix._build_step5_parser().parse_args([
        "--implement-tmpdir", str(impl),
        "--round-num", "1",
        "--session-env-path", str(impl / "session-env.sh"),
        "--plan-file", str(impl / "plan.txt"),
        "--feature-file", str(impl / "feature-description.txt"),
        "--codex-available", "false",
        "--cursor-available", "false",
    ])
    core_args = round_runner._core_args_for_round(args=args, round_dir=impl / "round-1", dynamic_archetypes="0", prune_ledger=impl / "ledger.tsv")
    idx = core_args.index("--site")
    assert core_args[idx + 1] == "implement Step 5"


@MARK_STEP5
def test_step5_preflight_missing_session_env_emits_stall(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    (impl / "session-env.sh").unlink()
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "STEP5_REVIEW_STATUS=stall" in out
    assert "STALL_REASON=preflight-failed" in out


@MARK_DISPATCH
def test_preflight_auto_forwards_eligible_scout_manifest(tmp_path):
    impl = _tmp_impl(tmp_path)
    (impl / "step2-external-scout-eligible.txt").write_text("ok\n", encoding="utf-8")
    (impl / "step2-scout-coder-status.env").write_text("SCOUT_CODER_STATUS=ok\n", encoding="utf-8")
    manifest = impl / "scout-coder-manifest.json"
    manifest.write_text("{}\n", encoding="utf-8")
    args = review_and_fix._build_step5_parser().parse_args([
        "--implement-tmpdir", str(impl),
        "--mode", "loop",
    ])
    _, _ = review_and_fix._preflight_step5(args)
    assert args.pre_scouted_manifest == str(manifest)


@MARK_DISPATCH
def test_preflight_skips_manifest_when_scout_ineligible(tmp_path):
    impl = _tmp_impl(tmp_path)
    args = review_and_fix._build_step5_parser().parse_args([
        "--implement-tmpdir", str(impl),
        "--mode", "loop",
    ])
    _, _ = review_and_fix._preflight_step5(args)
    assert args.pre_scouted_manifest == ""


@MARK_DISPATCH
def test_preflight_skips_manifest_when_scout_status_non_ok(tmp_path):
    impl = _tmp_impl(tmp_path)
    (impl / "step2-external-scout-eligible.txt").write_text("eligible\n", encoding="utf-8")
    (impl / "step2-scout-coder-status.env").write_text("SCOUT_CODER_STATUS=missing-or-invalid\n", encoding="utf-8")
    (impl / "scout-coder-manifest.json").write_text('{"archetypes":[]}\n', encoding="utf-8")
    args = review_and_fix._build_step5_parser().parse_args([
        "--implement-tmpdir", str(impl),
        "--mode", "loop",
    ])
    _, _ = review_and_fix._preflight_step5(args)
    assert args.pre_scouted_manifest == ""


@MARK_DISPATCH
def test_preflight_mav_apply_clears_pre_scouted_manifest(tmp_path):
    impl = _tmp_impl(tmp_path)
    findings = impl / "accepted.md"
    findings.write_text("### FINDING_1: x\n", encoding="utf-8")
    args = review_and_fix._build_step5_parser().parse_args([
        "--implement-tmpdir", str(impl),
        "--mode", "mav-apply",
        "--round-num", "1",
        "--findings-file", str(findings),
        "--pre-scouted-manifest", str(impl / "scout-coder-manifest.json"),
    ])
    _, _ = review_and_fix._preflight_step5(args)
    assert args.pre_scouted_manifest == ""


@MARK_STEP5
def test_step5_preflight_missing_feature_file_emits_stall(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    (impl / "feature-description.txt").unlink()
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "STEP5_REVIEW_STATUS=stall" in out
    assert "STALL_REASON=preflight-failed" in out


@MARK_STEP5
def test_step5_preflight_invalid_codex_present_emits_stall(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    (impl / "session-env.sh").write_text("CODEX_PRESENT=maybe\nCURSOR_PRESENT=false\n", encoding="utf-8")
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "STEP5_REVIEW_STATUS=stall" in out


@MARK_STEP5
def test_step5_unresolved_run_id_preflight_stall(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = tmp_path / "impl"
    impl.mkdir()
    (impl / "session-env.sh").write_text("CODEX_PRESENT=false\nCURSOR_PRESENT=false\n", encoding="utf-8")
    (impl / "plan.txt").write_text("plan\n", encoding="utf-8")
    (impl / "feature-description.txt").write_text("feature\n", encoding="utf-8")
    core_calls: list[int] = []

    def fake_capture(*_args, **_kwargs):
        core_calls.append(1)
        return 0

    monkeypatch.setattr(review_and_fix, "review_core_capture", fake_capture)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "STEP5_REVIEW_STATUS=stall" in out
    assert "STALL_REASON=preflight-failed" in out
    assert not core_calls


@MARK_DISPATCH
def test_flush_scout_manifest_writes_batch(tmp_path, monkeypatch):
    impl = tmp_path / "impl"
    impl.mkdir()
    round_dir = impl / "round-1"
    round_dir.mkdir()
    calls: list[list[str]] = []

    def fake_run(argv, **_kwargs):
        calls.append(list(argv))
        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    monkeypatch.setattr(batch_report, "_run", fake_run)
    review_and_fix.flush_scout_manifest(
        implement_tmpdir=impl,
        run_id="run-1",
        round_num=1,
        round_dir=round_dir,
        core={
            "SCOUT_STATUS": "ok",
            "DYNAMIC_SLOTS": "2",
            "SCOUT_MANIFEST": str(round_dir / "scout-round1-manifest.json"),
            "YIELD_TSV_FILE": str(round_dir / "scout-archetype-yield.tsv"),
        }
    )
    assert calls
    assert "review-scout-manifest" in calls[0]
    payload_path = round_dir / ".scout-payload.json"
    assert not payload_path.exists()


@MARK_DISPATCH
def test_run_coder_cursor_normalizes_api_key_before_launch(tmp_path, monkeypatch):
    monkeypatch.setenv("CURSOR_PRESENT", "true")
    monkeypatch.setenv("CURSOR_BINARY_FOUND", "true")
    monkeypatch.setenv("CURSOR_API_KEY", "  key-with-padding  ")
    monkeypatch.setattr(coder_runner, "_cursor_available", lambda: True)
    monkeypatch.setattr(
        coder_runner.agents,
        "resolve_model_args",
        lambda *_a, **_k: coder_runner.agents.ModelArgResult(argv=("--model", "test")),
    )
    seen_env: list[str | None] = []
    original_export = coder_runner.agents.cursor_auth_export_env

    def capture_export() -> None:
        original_export()
        seen_env.append(os.environ.get("CURSOR_API_KEY"))

    monkeypatch.setattr(coder_runner.agents, "cursor_auth_export_env", capture_export)
    monkeypatch.setattr(coder_runner, "_run", lambda argv, **_kw: review_and_fix.proc.CommandResult(
        argv, 0, "wrapped prompt", "", 0.0,
    ))
    assert review_and_fix._run_coder_cursor(round_dir=tmp_path, prompt_body="prompt", tool_log=tmp_path / "tool.log") is True
    assert seen_env == ["key-with-padding"]


def test_clear_reviewer_prune_round_uses_python_helper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[Path, int, Path, Path]] = []

    def fake_record(ledger: Path, round_num: int, manifest: Path, classification: Path) -> None:
        calls.append((ledger, round_num, manifest, classification))

    monkeypatch.setattr(review_and_fix.review_pipeline, "reviewer_prune_record", fake_record)
    ledger = tmp_path / "ledger.tsv"
    work_dir = tmp_path / "work"

    batch_report._clear_reviewer_prune_round(ledger=ledger, round_num=3, work_dir=work_dir)

    assert calls == [(ledger, 3, work_dir / "reviewer-prune-clear-empty.ndjson", work_dir / "reviewer-prune-clear-classification.tsv")]
    assert (work_dir / "reviewer-prune-clear-empty.ndjson").read_text(encoding="utf-8") == ""
    assert "reviewer_slots" in (work_dir / "reviewer-prune-clear-classification.tsv").read_text(encoding="utf-8")


def test_shared_finding_parser_preserves_filter_preamble_and_inner_headings(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    out = tmp_path / "in-scope.md"
    accepted.write_text(
        "Coder preamble\n\n"
        "### FINDING_1: keep\n"
        "body\n"
        "### Details\n"
        "nested detail\n"
        "### FINDING_2: drop [OUT_OF_SCOPE]\n"
        "oos body\n",
        encoding="utf-8",
    )

    round_runner._filter_in_scope(accepted_file=accepted, output=out)

    assert out.read_text(encoding="utf-8") == (
        "Coder preamble\n\n"
        "### FINDING_1: keep\n"
        "body\n"
        "### Details\n"
        "nested detail\n"
    )


def test_parser_backed_extraction_and_counts_tolerate_malformed_utf8(tmp_path: Path) -> None:
    findings = tmp_path / "findings.md"
    findings.write_bytes(b"### FINDING_1: title\nbody\xff\n### Details\nignored by extraction\n")
    text = findings.read_text(encoding="utf-8", errors="replace")

    assert review_and_fix._count_findings(findings) == 1
    assert batch_report._extract_finding_block(text=text, finding_id="FINDING_1") == "### FINDING_1: title\nbody�\n"


def test_nit_count_keeps_interior_heading_segment_semantics(tmp_path: Path) -> None:
    findings = tmp_path / "accepted.md"
    findings.write_text(
        "### FINDING_1: nit\n"
        "- **Severity**: nit\n"
        "### Details\n"
        "- **Severity**: nit\n"
        "### FINDING_2: not nit\n"
        "body\n",
        encoding="utf-8",
    )

    assert round_runner._nit_count(findings) == 1


def test_degraded_retry_preserves_attempt_1_when_retry_succeeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    call_count = 0

    def fake_core(argv: list[str]) -> int:
        nonlocal call_count
        call_count += 1
        out_dir = Path(argv[argv.index("--output-dir") + 1])
        (out_dir / "accepted-findings.md").write_text("", encoding="utf-8")
        (out_dir / "rejected-findings.md").write_text("", encoding="utf-8")
        if call_count == 1:
            (out_dir / "voting-tally.md").write_text(
                "**⚠ Degraded code-review panel: 1 judge(s) available.**\n\nfirst degraded marker\n",
                encoding="utf-8",
            )
        else:
            (out_dir / "voting-tally.md").write_text("clean retry marker\n", encoding="utf-8")
        logging_util.emit("REVIEW_CORE_STATUS=ok")
        logging_util.emit("ACCEPTED_COUNT=0")
        logging_util.emit("REJECTED_COUNT=0")
        logging_util.emit(f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}")
        logging_util.emit(f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}")
        logging_util.emit("VOTER_COUNT=3")
        return 0

    args = argparse.Namespace(
        implement_tmpdir=str(impl),
        round_num="1",
        session_env_path=str(impl / "session-env.sh"),
        codex_available="false",
        cursor_available="false",
        diff_file="",
        commit_count="",
        plan_file="",
        feature_file="",
        run_id="",
        pre_scouted_manifest="",
        dynamic_archetypes="0",
    )
    review_and_fix._run_round(args, suppress_emit=True, review_core_impl=fake_core)

    round_dir = impl / "round-1"
    assert call_count == 2
    assert (round_dir / "voting-tally-degraded-attempt-1.md").read_text(encoding="utf-8") == (
        "**⚠ Degraded code-review panel: 1 judge(s) available.**\n\nfirst degraded marker\n"
    )
    assert (round_dir / "voting-tally.md").read_text(encoding="utf-8") == "clean retry marker\n"
    assert not (round_dir / "voting-tally-degraded-attempt-2.md").exists()


def test_degraded_retry_skips_zero_findings_round(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    call_count = 0

    def fake_core(argv: list[str]) -> int:
        nonlocal call_count
        call_count += 1
        out_dir = Path(argv[argv.index("--output-dir") + 1])
        (out_dir / "accepted-findings.md").write_text("", encoding="utf-8")
        (out_dir / "rejected-findings.md").write_text("", encoding="utf-8")
        (out_dir / "voting-tally.md").write_text(
            "**⚠ Degraded code-review panel: 0 judges available.**\n\nlegacy empty-ballot marker\n",
            encoding="utf-8",
        )
        logging_util.emit("REVIEW_CORE_STATUS=zero-findings")
        logging_util.emit("ACCEPTED_COUNT=0")
        logging_util.emit("REJECTED_COUNT=0")
        logging_util.emit(f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}")
        logging_util.emit(f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}")
        logging_util.emit("PARSE_FAILED_COUNT=1")
        logging_util.emit("VOTER_COUNT=0")
        return 0

    warned: list[str] = []

    def capture_warning(*, session_env_path: str, entry: str) -> None:
        warned.append(entry)

    monkeypatch.setattr(review_tally, "surface_warning", capture_warning)

    args = argparse.Namespace(
        implement_tmpdir=str(impl),
        round_num="1",
        session_env_path=str(impl / "session-env.sh"),
        codex_available="false",
        cursor_available="false",
        diff_file="",
        commit_count="",
        plan_file="",
        feature_file="",
        run_id="",
        pre_scouted_manifest="",
        dynamic_archetypes="0",
    )
    review_and_fix._run_round(args, suppress_emit=True, review_core_impl=fake_core)

    assert call_count == 1
    assert not (impl / "round-1" / "voting-tally-degraded-attempt-1.md").exists()
    assert not any("narrative-only output" in item for item in warned)


def test_degraded_retry_preserves_attempt_1_and_2_when_retry_stays_degraded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    call_count = 0

    def fake_core(argv: list[str]) -> int:
        nonlocal call_count
        call_count += 1
        out_dir = Path(argv[argv.index("--output-dir") + 1])
        (out_dir / "accepted-findings.md").write_text("", encoding="utf-8")
        (out_dir / "rejected-findings.md").write_text("", encoding="utf-8")
        tally = (
            "**⚠ Degraded code-review panel: 1 judge(s) available.**\n\n"
            f"degraded attempt {call_count} marker\n"
        )
        (out_dir / "voting-tally.md").write_text(tally, encoding="utf-8")
        logging_util.emit("REVIEW_CORE_STATUS=ok")
        logging_util.emit("ACCEPTED_COUNT=0")
        logging_util.emit("REJECTED_COUNT=0")
        logging_util.emit(f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}")
        logging_util.emit(f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}")
        logging_util.emit("VOTER_COUNT=3")
        return 0

    args = argparse.Namespace(
        implement_tmpdir=str(impl),
        round_num="1",
        session_env_path=str(impl / "session-env.sh"),
        codex_available="false",
        cursor_available="false",
        diff_file="",
        commit_count="",
        plan_file="",
        feature_file="",
        run_id="",
        pre_scouted_manifest="",
        dynamic_archetypes="0",
    )
    review_and_fix._run_round(args, suppress_emit=True, review_core_impl=fake_core)

    round_dir = impl / "round-1"
    first = "**⚠ Degraded code-review panel: 1 judge(s) available.**\n\ndegraded attempt 1 marker\n"
    second = "**⚠ Degraded code-review panel: 1 judge(s) available.**\n\ndegraded attempt 2 marker\n"
    assert call_count == 2
    assert (round_dir / "voting-tally-degraded-attempt-1.md").read_text(encoding="utf-8") == first
    assert (round_dir / "voting-tally-degraded-attempt-2.md").read_text(encoding="utf-8") == second
    assert (round_dir / "voting-tally.md").read_text(encoding="utf-8") == second


def test_no_spurious_under_quorum_warning_after_successful_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Issue #5334: successful degraded-panel retry must not leave a stale under-quorum warning."""
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    call_count = 0

    def fake_core(argv: list[str]) -> int:
        nonlocal call_count
        call_count += 1
        out_dir = Path(argv[argv.index("--output-dir") + 1])
        (out_dir / "accepted-findings.md").write_text("", encoding="utf-8")
        (out_dir / "rejected-findings.md").write_text("", encoding="utf-8")
        if call_count == 1:
            # First call: degraded panel with one under-quorum finding.
            tally = (
                "**⚠ Degraded code-review panel: 1 finding(s) decided below the 2-of-3 panel quorum "
                "because per-item JUDGE_ERROR dropped valid votes below quorum (FINDING_X). "
                "These items were resolved by the remaining voter(s) and may warrant manual review.**\n\n"
                "## Per-finding vote breakdown\n\n| Item | YES | NO | JERR | Result |\n|---|---:|---:|---:|---|\n"
            )
            (out_dir / "voting-tally.md").write_text(tally, encoding="utf-8")
            logging_util.emit("REVIEW_CORE_STATUS=ok")
            logging_util.emit("ACCEPTED_COUNT=0")
            logging_util.emit("REJECTED_COUNT=0")
            logging_util.emit(f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}")
            logging_util.emit(f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}")
            logging_util.emit("UNDER_QUORUM_COUNT=1")
            logging_util.emit("UNDER_QUORUM_ITEMS=FINDING_X")
            logging_util.emit("VOTER_COUNT=3")
        else:
            # Second call (retry): clean panel — no degraded banner, UNDER_QUORUM_COUNT=0.
            (out_dir / "voting-tally.md").write_text(
                "## Per-finding vote breakdown\n\n| Item | YES | NO | JERR | Result |\n|---|---:|---:|---:|---|\n",
                encoding="utf-8",
            )
            logging_util.emit("REVIEW_CORE_STATUS=ok")
            logging_util.emit("ACCEPTED_COUNT=0")
            logging_util.emit("REJECTED_COUNT=0")
            logging_util.emit(f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}")
            logging_util.emit(f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}")
            logging_util.emit("UNDER_QUORUM_COUNT=0")
            logging_util.emit("UNDER_QUORUM_ITEMS=")
            logging_util.emit("VOTER_COUNT=3")
        return 0

    warned: list[str] = []

    def capture_warning(*, session_env_path: str, entry: str) -> None:
        warned.append(entry)

    monkeypatch.setattr(review_tally, "surface_warning", capture_warning)

    args = argparse.Namespace(
        implement_tmpdir=str(impl),
        round_num="1",
        session_env_path=str(impl / "session-env.sh"),
        codex_available="false",
        cursor_available="false",
        diff_file="",
        commit_count="",
        plan_file="",
        feature_file="",
        run_id="",
        pre_scouted_manifest="",
        dynamic_archetypes="0",
    )
    review_and_fix._run_round(args, suppress_emit=True, review_core_impl=fake_core)

    # Retry was triggered (first call degraded) and succeeded (second call clean).
    assert call_count == 2
    # No under-quorum warning must appear after a successful retry.
    assert not any("decided below" in w for w in warned)


def test_dropped_reviewer_warning_persists_after_successful_degraded_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    call_count = 0

    def fake_core(argv: list[str]) -> int:
        nonlocal call_count
        call_count += 1
        out_dir = Path(argv[argv.index("--output-dir") + 1])
        (out_dir / "accepted-findings.md").write_text("", encoding="utf-8")
        (out_dir / "rejected-findings.md").write_text("", encoding="utf-8")
        if call_count == 1:
            (out_dir / "voting-tally.md").write_text(
                "**⚠ Degraded code-review panel: 1 judge(s) available.**\n\n",
                encoding="utf-8",
            )
            (out_dir / "review-core-threshold.env").write_text(
                "DYNAMIC_FAILED_SLOTS=0\nDYNAMIC_DROPPED_SLOTS=1\nTHRESHOLD_OK=true\n",
                encoding="utf-8",
            )
        else:
            (out_dir / "voting-tally.md").write_text("## Per-finding vote breakdown\n", encoding="utf-8")
            (out_dir / "review-core-threshold.env").write_text(
                "DYNAMIC_FAILED_SLOTS=0\nDYNAMIC_DROPPED_SLOTS=0\nTHRESHOLD_OK=true\n",
                encoding="utf-8",
            )
        logging_util.emit("REVIEW_CORE_STATUS=ok")
        logging_util.emit("ACCEPTED_COUNT=0")
        logging_util.emit("REJECTED_COUNT=0")
        logging_util.emit(f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}")
        logging_util.emit(f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}")
        return 0

    warned: list[str] = []

    def capture_warning(*, session_env_path: str, entry: str) -> None:
        warned.append(entry)

    monkeypatch.setattr(review_tally, "surface_warning", capture_warning)

    args = argparse.Namespace(
        implement_tmpdir=str(impl),
        round_num="1",
        session_env_path=str(impl / "session-env.sh"),
        codex_available="false",
        cursor_available="false",
        diff_file="",
        commit_count="",
        plan_file="",
        feature_file="",
        run_id="",
        pre_scouted_manifest="",
        dynamic_archetypes="0",
    )
    review_and_fix._run_round(args, suppress_emit=True, review_core_impl=fake_core)

    assert call_count == 2
    assert sum("dynamic reviewer slot" in item for item in warned) == 1
    attempts = impl / "round-1" / "dropped-reviewer-attempts.env"
    assert "DYNAMIC_DROPPED_SLOTS=1" in attempts.read_text(encoding="utf-8")


def test_parse_failed_warning_surfaces_after_still_degraded_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Issue #5345: still-degraded retry must surface parse-failed warning from final core KVs."""
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    call_count = 0

    def fake_core(argv: list[str]) -> int:
        nonlocal call_count
        call_count += 1
        out_dir = Path(argv[argv.index("--output-dir") + 1])
        (out_dir / "accepted-findings.md").write_text("", encoding="utf-8")
        (out_dir / "rejected-findings.md").write_text("", encoding="utf-8")
        degraded_banner = "**⚠ Degraded code-review panel: 1 judge(s) available.**\n\n"
        (out_dir / "voting-tally.md").write_text(degraded_banner, encoding="utf-8")
        logging_util.emit("REVIEW_CORE_STATUS=ok")
        logging_util.emit("ACCEPTED_COUNT=0")
        logging_util.emit("REJECTED_COUNT=0")
        logging_util.emit(f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}")
        logging_util.emit(f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}")
        logging_util.emit(f"PARSE_FAILED_COUNT={2 if call_count == 1 else 1}")
        logging_util.emit("VOTER_COUNT=2")
        return 0

    warned: list[str] = []

    def capture_warning(*, session_env_path: str, entry: str) -> None:
        warned.append(entry)

    monkeypatch.setattr(review_tally, "surface_warning", capture_warning)

    args = argparse.Namespace(
        implement_tmpdir=str(impl),
        round_num="1",
        session_env_path=str(impl / "session-env.sh"),
        codex_available="false",
        cursor_available="false",
        diff_file="",
        commit_count="",
        plan_file="",
        feature_file="",
        run_id="",
        pre_scouted_manifest="",
        dynamic_archetypes="0",
    )
    review_and_fix._run_round(args, suppress_emit=True, review_core_impl=fake_core)

    assert call_count == 2
    assert len(warned) == 1
    assert "1 voter slot(s)" in warned[0]
    assert "narrative-only output" in warned[0]


def test_no_spurious_parse_failed_warning_after_successful_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Issue #5345: successful degraded-panel retry must not leave a stale parse-failed warning."""
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    call_count = 0

    def fake_core(argv: list[str]) -> int:
        nonlocal call_count
        call_count += 1
        out_dir = Path(argv[argv.index("--output-dir") + 1])
        (out_dir / "accepted-findings.md").write_text("", encoding="utf-8")
        (out_dir / "rejected-findings.md").write_text("", encoding="utf-8")
        if call_count == 1:
            (out_dir / "voting-tally.md").write_text(
                "**⚠ Degraded code-review panel: 1 judge(s) available.**\n\n",
                encoding="utf-8",
            )
            logging_util.emit("PARSE_FAILED_COUNT=2")
        else:
            (out_dir / "voting-tally.md").write_text(
                "## Per-finding vote breakdown\n\n| Item | YES | NO | JERR | Result |\n|---|---:|---:|---:|---|\n",
                encoding="utf-8",
            )
            logging_util.emit("PARSE_FAILED_COUNT=0")
        logging_util.emit("REVIEW_CORE_STATUS=ok")
        logging_util.emit("ACCEPTED_COUNT=0")
        logging_util.emit("REJECTED_COUNT=0")
        logging_util.emit(f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}")
        logging_util.emit(f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}")
        logging_util.emit("VOTER_COUNT=3")
        return 0

    warned: list[str] = []

    def capture_warning(*, session_env_path: str, entry: str) -> None:
        warned.append(entry)

    monkeypatch.setattr(review_tally, "surface_warning", capture_warning)

    args = argparse.Namespace(
        implement_tmpdir=str(impl),
        round_num="1",
        session_env_path=str(impl / "session-env.sh"),
        codex_available="false",
        cursor_available="false",
        diff_file="",
        commit_count="",
        plan_file="",
        feature_file="",
        run_id="",
        pre_scouted_manifest="",
        dynamic_archetypes="0",
    )
    review_and_fix._run_round(args, suppress_emit=True, review_core_impl=fake_core)

    assert call_count == 2
    assert not any("narrative-only output" in w for w in warned)


def test_run_round_reentry_clears_stale_dropped_reviewer_attempts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stale dropped-reviewer-attempts.env from a prior _run_round must not inflate warnings on re-entry."""
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    run_count = 0

    def fake_core(argv: list[str]) -> int:
        nonlocal run_count
        run_count += 1
        out_dir = Path(argv[argv.index("--output-dir") + 1])
        (out_dir / "accepted-findings.md").write_text("", encoding="utf-8")
        (out_dir / "rejected-findings.md").write_text("", encoding="utf-8")
        (out_dir / "voting-tally.md").write_text("## Per-finding vote breakdown\n", encoding="utf-8")
        if run_count == 1:
            (out_dir / "review-core-threshold.env").write_text(
                "DYNAMIC_FAILED_SLOTS=0\nDYNAMIC_DROPPED_SLOTS=1\nTHRESHOLD_OK=true\n",
                encoding="utf-8",
            )
        else:
            (out_dir / "review-core-threshold.env").write_text(
                "DYNAMIC_FAILED_SLOTS=0\nDYNAMIC_DROPPED_SLOTS=0\nTHRESHOLD_OK=true\n",
                encoding="utf-8",
            )
        logging_util.emit("REVIEW_CORE_STATUS=ok")
        logging_util.emit("ACCEPTED_COUNT=0")
        logging_util.emit("REJECTED_COUNT=0")
        logging_util.emit(f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}")
        logging_util.emit(f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}")
        return 0

    args = argparse.Namespace(
        implement_tmpdir=str(impl),
        round_num="1",
        session_env_path=str(impl / "session-env.sh"),
        codex_available="false",
        cursor_available="false",
        diff_file="",
        commit_count="",
        plan_file="",
        feature_file="",
        run_id="",
        pre_scouted_manifest="",
        dynamic_archetypes="0",
    )

    first_warned: list[str] = []

    def capture_first(*, session_env_path: str, entry: str) -> None:
        first_warned.append(entry)

    monkeypatch.setattr(review_tally, "surface_warning", capture_first)
    review_and_fix._run_round(args, suppress_emit=True, review_core_impl=fake_core)

    assert run_count == 1
    assert any("dynamic reviewer slot" in item for item in first_warned)
    attempts = impl / "round-1" / "dropped-reviewer-attempts.env"
    assert "DYNAMIC_DROPPED_SLOTS=1" in attempts.read_text(encoding="utf-8")

    second_warned: list[str] = []

    def capture_second(*, session_env_path: str, entry: str) -> None:
        second_warned.append(entry)

    monkeypatch.setattr(review_tally, "surface_warning", capture_second)
    review_and_fix._run_round(args, suppress_emit=True, review_core_impl=fake_core)

    assert run_count == 2
    assert not any("dynamic reviewer slot" in item for item in second_warned)


def test_run_round_dynamic_straggler_warn_count_reaches_count_load_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)

    def fake_core(argv: list[str]) -> int:
        out_dir = Path(argv[argv.index("--output-dir") + 1])
        (out_dir / "accepted-findings.md").write_text("", encoding="utf-8")
        (out_dir / "rejected-findings.md").write_text("", encoding="utf-8")
        (out_dir / "voting-tally.md").write_text("## Per-finding vote breakdown\n", encoding="utf-8")
        (out_dir / "review-core-threshold.env").write_text(
            "THRESHOLD_OK=true\n"
            "STRAGGLER_DROPPED_COUNT=1\n"
            "DYNAMIC_DROPPED_SLOTS=1\n"
            "DYNAMIC_FAILED_SLOTS=0\n"
            "INTENDED_SLOTS=9\n"
            "FAILED_SLOTS=1\n",
            encoding="utf-8",
        )
        (out_dir / "panel.output-files.dropped-slots").write_text(
            "dyn-dyn-lint-escalation\tcursor\tstraggler-dropped\tcut\n",
            encoding="utf-8",
        )
        logging_util.emit("REVIEW_CORE_STATUS=ok")
        logging_util.emit("ACCEPTED_COUNT=0")
        logging_util.emit("REJECTED_COUNT=0")
        logging_util.emit(f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}")
        logging_util.emit(f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}")
        return 0

    args = argparse.Namespace(
        implement_tmpdir=str(impl),
        round_num="1",
        session_env_path=str(impl / "session-env.sh"),
        codex_available="false",
        cursor_available="false",
        diff_file="",
        commit_count="",
        plan_file="",
        feature_file="",
        run_id="",
        pre_scouted_manifest="",
        dynamic_archetypes="0",
    )
    review_and_fix._run_round(args, suppress_emit=True, review_core_impl=fake_core)

    exec_issues = impl / "execution-issues.md"
    assert exec_issues.is_file()
    assert "dynamic reviewer slot drop/failure" in exec_issues.read_text(encoding="utf-8")

    load_result = exec_issue_detail.load_issue_detail_groups(impl, run_dir=None)
    assert exec_issue_detail.count_load_result(load_result) == (0, 1)


@MARK_STEP5
def test_step5_escalates_before_lower_tier_cap(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    calls: list[int] = []

    def fake_run_round(args: argparse.Namespace, *, suppress_emit: bool) -> review_and_fix.RoundResult:
        round_num = int(args.round_num)
        calls.append(round_num)
        if round_num == 1:
            result = _fix_applied_round_result(impl, round_num=1)
            result.accepted_file.write_text(
                "### FINDING_1: **Important** one\n\n### FINDING_2: **Important** two\n",
                encoding="utf-8",
            )
            return result
        round_dir = impl / f"round-{round_num}"
        round_dir.mkdir(parents=True, exist_ok=True)
        return review_and_fix.RoundResult(
            0,
            "complete",
            "zero-findings",
            round_num,
            0,
            0,
            0,
            0,
            1,
            0,
            0,
            0,
            round_dir / "accepted-findings.md",
            round_dir / "rejected-findings.md",
            round_dir,
            impl / "review-and-fix-summary.json",
            impl / "accumulated-oos.jsonl",
            review_and_fix.CoderResult(0, status="skipped"),
        )

    monkeypatch.setattr(review_and_fix, "_run_round", fake_run_round)

    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--difficulty", "TRIVIAL", "--audit-roll", "30"])
    out = capsys.readouterr().out

    assert rc == 0
    assert calls == [1, 2]
    assert "ESCALATED_FROM=TRIVIAL" in out
    assert "ESCALATED_TO=MODERATE" in out
    assert "STEP5_REVIEW_STATUS=complete" in out
    data = json.loads((impl / "difficulty-rating.json").read_text(encoding="utf-8"))
    assert data["applied_tier"] == "MODERATE"
    assert data["escalations"][0]["round"] == 2
