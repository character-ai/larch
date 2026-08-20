"""Tests for Python /design lifecycle helpers."""
# pyright: reportUnusedCallResult=false, reportUnknownLambdaType=false, reportUnknownArgumentType=false

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from types import SimpleNamespace

import pytest

from larch import io as larch_io
from larch.core import config
from larch.design import plan_grammar
from larch.design import design_core
from larch.design import (
    design_step5c,
    design_step6,
)
from larch.design import design_pause
from larch.core import architectural_guidelines
from larch.core import logging_util
from larch.core.proc import CommandResult
from tests.support.design_wire import dialectic_candidate_json, plan_body, run_params_json
from larch.state import session_env
from larch.design.design_core import phase_driver_read_result_env


CLI = Path(__file__).resolve().parents[2] / "cli.py"
LARCH_ENTRYPOINT = Path(__file__).resolve().parents[3] / "scripts" / "larch.sh"




def test_phase_driver_read_result_env_filters_allowlist_and_cr(tmp_path: Path) -> None:
    env = tmp_path / "result.env"
    env.write_bytes(
        b"INIT_STATUS=ok\n"
        b"SECRET=drop\n"
        b"RUN_PARAMS_PATH=/tmp/run.json\n"
        b"OOS_SKIP_BREADCRUMB=skip\n"
        b"SETTLE_NEXT_ACTION=gate-b-continue\n"
        b"BAD=has\r\n"
    )  # pyright: ignore[reportUnusedCallResult]
    assert phase_driver_read_result_env(
        path=env,
        allow_keys=["INIT_STATUS", "RUN_PARAMS_PATH", "OOS_SKIP_BREADCRUMB", "SETTLE_NEXT_ACTION", "BAD"],
    ) == [
        ("INIT_STATUS", "ok"),
        ("RUN_PARAMS_PATH", "/tmp/run.json"),
        ("OOS_SKIP_BREADCRUMB", "skip"),
        ("SETTLE_NEXT_ACTION", "gate-b-continue"),
    ]


def test_phase_driver_read_result_env_refuses_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.env"
    target.write_text("INIT_STATUS=ok\n", encoding="utf-8")  # pyright: ignore[reportUnusedCallResult]
    link = tmp_path / "link.env"
    link.symlink_to(target)
    with pytest.raises(OSError, match="not a regular file"):
        phase_driver_read_result_env(path=link, allow_keys=["INIT_STATUS"])  # pyright: ignore[reportUnusedCallResult]


def test_decode_bash_percent_q_decodes_utf8_byte_escaped_emoji() -> None:
    assert design_core._decode_bash_percent_q("$'\\360\\237\\230\\200'") == "😀"  # pyright: ignore[reportPrivateUsage]


def test_decode_bash_percent_q_decodes_utf8_byte_escaped_accent() -> None:
    assert design_core._decode_bash_percent_q("$'caf\\303\\251'") == "café"  # pyright: ignore[reportPrivateUsage]


def test_decode_bash_percent_q_malformed_utf8_byte_escape_is_safe() -> None:
    assert design_core._decode_bash_percent_q("$'\\377'") == "ÿ"  # pyright: ignore[reportPrivateUsage]


def test_pause_save_main_accepts_wrapper_argv_without_cli_prefix(tmp_path: Path) -> None:
    rc = design_pause.pause_save_main(["--design-tmpdir", str(tmp_path), "--issue", "0"])
    assert rc == 0


def _write_session_env(tmp_path: Path, design: Path, monkeypatch: pytest.MonkeyPatch | None = None, **extra: str) -> Path:
    resolved = design.resolve()
    if monkeypatch is not None:
        monkeypatch.setenv("DESIGN_TMPDIR", str(resolved))
    env_path = tmp_path / "source-env.sh"
    lines = [
        f"export DESIGN_TMPDIR={resolved}",
        "export SESSION_ID=run-1",
        f"export CLAUDE_PLUGIN_ROOT={CLI.parent.parent}",
    ]
    lines.extend(f"export {key}={value}" for key, value in extra.items())
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return env_path


def _pid_residual_paths(home: Path, pid: str = "123") -> tuple[Path, Path, Path]:
    sessions = home / ".cache" / "larch" / "sessions"
    return (
        sessions / f"current-design-env-{pid}.sh",
        sessions / f"design-run-{pid}.sh",
        sessions / f"step0-parsed-{pid}.env",
    )


def _write_pid_residuals(home: Path, *, target: Path, pid: str = "123") -> tuple[Path, Path, Path]:
    symlink_path, run_path, parsed_path = _pid_residual_paths(home, pid)
    symlink_path.parent.mkdir(parents=True, exist_ok=True)
    symlink_path.symlink_to(target)
    run_path.write_text("launcher\n", encoding="utf-8")
    parsed_path.write_text("POSITIONAL_KIND=none\n", encoding="utf-8")
    return symlink_path, run_path, parsed_path








def test_capture_contract_stream_restores_parent_stdout_stderr(tmp_path: Path) -> None:
    out = tmp_path / "stdout.log"
    err = tmp_path / "stderr.log"

    def emit_contract() -> int:
        logging_util.emit_kv(key="CAPTURED", value="true")
        print("stderr-row", file=sys.stderr)
        return 0

    assert design_core.capture_contract_stream_to_paths(emit_contract, out, err) == 0
    os.write(1, b"")
    os.write(2, b"")
    assert "CAPTURED=true" in out.read_text(encoding="utf-8")
    assert "stderr-row" in err.read_text(encoding="utf-8")










def test_reap_pid_residuals_uses_home_cache_when_xdg_differs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    xdg = tmp_path / "xdg"
    home.mkdir()
    xdg.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CACHE_HOME", str(xdg))
    residuals = _write_pid_residuals(home, target=tmp_path / "missing-source-env.sh")
    xdg_file = xdg / "larch" / "sessions" / "step0-parsed-123.env"
    xdg_file.parent.mkdir(parents=True)
    xdg_file.write_text("POSITIONAL_KIND=none\n", encoding="utf-8")

    session_env.reap_pid_residuals("123")

    assert all(not path.exists() and not path.is_symlink() for path in residuals)
    assert xdg_file.is_file()








def test_wrapper_session_env_parser_exports_quoted_paths(tmp_path: Path) -> None:
    design = tmp_path / "design dir"
    design.mkdir()
    session_env = tmp_path / "session-env.sh"
    session_env.write_text(
        f"export DESIGN_TMPDIR={str(design)!r}\nexport ISSUE_NUMBER='42'\nexport CLAUDE_PLUGIN_ROOT={str(Path.cwd())!r}\n",
        encoding="utf-8",
    )
    parsed = design_core._parse_common_wrapper_args(["--session-env-path", str(session_env)])  # pyright: ignore[reportPrivateUsage]
    merged = design_core._rehydrate_wrapper_env(parsed)  # pyright: ignore[reportPrivateUsage]
    assert merged["DESIGN_TMPDIR"] == str(design)
    assert os.environ["ISSUE_NUMBER"] == "42"




















@pytest.mark.parametrize(
    ("check_size_rc", "kvs", "partition_requested", "expected_action", "expected_exit_rc", "expected_status"),
    [
        (2, {"SIZE_TRIGGER_FIRED": "true", "DRIFT_TRIGGER_FIRED": "true"}, True, "rc2-warning", 2, "rc2-warning"),
        (7, {"SIZE_TRIGGER_FIRED": "true"}, True, "internal-error", 7, "internal-error"),
        (0, {"SIZE_TRIGGER_FIRED": "true", "DRIFT_TRIGGER_FIRED": "true"}, True, "hard-trigger", 0, "plan-size-trigger"),
        (0, {"SIZE_TRIGGER_FIRED": "false", "DRIFT_TRIGGER_FIRED": "true"}, True, "partition-split", 0, "partition-requested"),
        (0, {"SIZE_TRIGGER_FIRED": "false", "DRIFT_TRIGGER_FIRED": "true"}, False, "drift-advisory", 0, "drift-advisory"),
        (0, {"SIZE_TRIGGER_FIRED": "false", "DRIFT_TRIGGER_FIRED": "false"}, False, "under-threshold", 0, "under-threshold"),
    ],
)
def test_step2b5_next_action_for_priority(
    check_size_rc: int,
    kvs: dict[str, str],
    partition_requested: bool,
    expected_action: str,
    expected_exit_rc: int,
    expected_status: str,
) -> None:
    result = design_core.step2b5_next_action_for(
        check_size_rc=check_size_rc,
        check_size_kvs=kvs,
        partition_requested=partition_requested,
    )
    assert result.action == expected_action
    assert result.exit_rc == expected_exit_rc
    assert result.status == expected_status














def test_step2b5_echoes_check_size_stdout_and_rc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    real_run = design_step5c.subprocess.run

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        cmd = args[0] if args else kwargs.get("args")
        if isinstance(cmd, (list, tuple)) and "check-size" in cmd:
            return subprocess.CompletedProcess(args=[], returncode=7, stdout="PLAN_SIZE_STATUS=failed\n", stderr="")
        return real_run(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(design_step5c.subprocess, "run", fake_run)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path.cwd()))
    rc = design_step5c.step2b5_main([])
    assert rc == 7
    out = capsys.readouterr().out
    assert "PLAN_SIZE_STATUS=failed" in out
    assert "STEP2B5_NEXT_ACTION=internal-error" in out
    assert "STEP2B5_EXIT_RC=7" in out


def test_step2b5_self_logs_on_rc2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    real_run = design_step5c.subprocess.run

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        cmd = args[0] if args else kwargs.get("args")
        if isinstance(cmd, (list, tuple)) and "check-size" in cmd:
            return subprocess.CompletedProcess(args=[], returncode=2, stdout="PLAN_SIZE_STATUS=missing-diff-lines\n", stderr="")
        return real_run(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(design_step5c.subprocess, "run", fake_run)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    rc = design_step5c.step2b5_main([])
    out = capsys.readouterr().out
    assert rc == 2
    assert "PLAN_SIZE_STATUS=missing-diff-lines" in out
    assert "STEP2B5_NEXT_ACTION=rc2-warning" in out
    assert "STEP2B5_EXIT_RC=2" in out
    validation_log = tmp_path / "check-plan-size.validation.log"
    assert validation_log.read_text(encoding="utf-8") == "PLAN_SIZE_STATUS=missing-diff-lines\n"
    issues = (tmp_path / "execution-issues.md").read_text(encoding="utf-8")
    assert "design Step 2b.5" in issues
    assert "plan check-size" in issues


def test_step2b5_self_logs_on_rc3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_run = design_step5c.subprocess.run

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        cmd = args[0] if args else kwargs.get("args")
        if isinstance(cmd, (list, tuple)) and "check-size" in cmd:
            return subprocess.CompletedProcess(args=[], returncode=3, stdout="", stderr="usage: missing plan\n")
        return real_run(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(design_step5c.subprocess, "run", fake_run)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    rc = design_step5c.step2b5_main([])
    assert rc == 3
    validation_log = tmp_path / "check-plan-size.validation.log"
    assert validation_log.read_text(encoding="utf-8") == "usage: missing plan\n"
    issues = (tmp_path / "execution-issues.md").read_text(encoding="utf-8")
    assert "design Step 2b.5" in issues
    assert "plan check-size" in issues


def test_step2b5_no_log_on_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    real_run = design_step5c.subprocess.run

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        cmd = args[0] if args else kwargs.get("args")
        if isinstance(cmd, (list, tuple)) and "check-size" in cmd:
            return subprocess.CompletedProcess(args=[], returncode=0, stdout="PLAN_SIZE_STATUS=ok\n", stderr="")
        return real_run(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(design_step5c.subprocess, "run", fake_run)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    rc = design_step5c.step2b5_main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STEP2B5_NEXT_ACTION=under-threshold" in out
    assert "STEP2B5_EXIT_RC=0" in out
    assert not (tmp_path / "check-plan-size.validation.log").exists()
    assert not (tmp_path / "execution-issues.md").exists()








def test_rehydrate_wrapper_env_resolves_trusted_design_symlink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    sessions = home / ".cache" / "larch" / "sessions"
    sessions.mkdir(parents=True)
    source = sessions / "design-env-123.sh"
    design = tmp_path / "design"
    design.mkdir()
    source.write_text(f"export DESIGN_TMPDIR={str(design)!r}\nexport ISSUE_NUMBER='7'\n", encoding="utf-8")
    link = sessions / "current-design-env-123.sh"
    link.symlink_to(source)
    monkeypatch.setenv("HOME", str(home))
    parsed = design_core._parse_common_wrapper_args(["--session-env-path", str(link), "--claude-pid", "123"])  # pyright: ignore[reportPrivateUsage]
    merged = design_core._rehydrate_wrapper_env(parsed)  # pyright: ignore[reportPrivateUsage]
    assert merged["DESIGN_TMPDIR"] == str(design)
    assert merged["ISSUE_NUMBER"] == "7"










def test_step2b5_pause_short_circuit_skips_check_size(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".pause-requested").write_text("", encoding="utf-8")
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    monkeypatch.setenv("ISSUE_NUMBER", "42")
    called = False

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal called
        called = True
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(design_step5c.subprocess, "run", fake_run)
    monkeypatch.setattr(design_step5c, "_call_pause_save", lambda **_kw: 11)  # type: ignore[arg-type]
    rc = design_step5c.step2b5_main([])
    assert rc == 11
    assert called is False













































def test_capture_contract_stream_restores_fd3_for_quiet_init(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "stdout.log"
    err = tmp_path / "stderr.log"
    monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
    monkeypatch.setenv(config.ENV_DESIGN_TMPDIR, str(tmp_path))

    def emit_contract() -> int:
        logging_util.emit_kv(key="CAPTURED", value="true")
        return 0

    assert design_core.capture_contract_stream_to_paths(emit_contract, out, err) == 0
    logging_util.reset_quiet_state()
    read_fd, write_fd = os.pipe()
    saved_stdout = os.dup(1)
    try:
        os.dup2(write_fd, 1)
        os.close(write_fd)
        logging_util.quiet_init(argv0="parent-quiet")
        logging_util.emit_kv(key="POST_CAPTURE", value="ok")
        os.dup2(saved_stdout, 1)
        contract = os.read(read_fd, 4096).decode("utf-8")
    finally:
        os.close(read_fd)
        os.close(saved_stdout)
        logging_util.reset_quiet_state()
    assert "POST_CAPTURE=ok" in contract






def _capture_core_contract(
    core_fn: Callable[..., tuple[int, list[str]]],
    argv: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[int, str, str]:
    monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
    logging_util.reset_quiet_state()
    out = tmp_path / "contract.stdout.log"
    err = tmp_path / "contract.stderr.log"
    rc = design_core.capture_contract_stream_to_paths(core_fn, out, err, argv)
    logging_util.reset_quiet_state()
    return rc, out.read_text(encoding="utf-8"), err.read_text(encoding="utf-8")


def _setup_step5c_design(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **extra: str) -> tuple[Path, Path]:
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    env_path = _write_session_env(
        tmp_path,
        design,
        monkeypatch,
        ISSUE_NUMBER=extra.pop("ISSUE_NUMBER", "42"),
        SESSION_ID=extra.pop("SESSION_ID", "run-1"),
        **extra,
    )
    return design, env_path


def _step5c_rows(design: Path, *, plan_write_ok: str = "true", publish_ok: str = "true", final_summary: Path | None = None) -> str:
    summary = final_summary or (design / "final-summary.md")
    return "\n".join(
        [
            f"PLAN_WRITE_OK={plan_write_ok}",
            "VALIDATE_STATUS=ok",
            "VALIDATE_DEFECT_COUNT=0",
            "VALIDATE_SKIPPED_COUNT=0",
            "VALIDATE_UNSAFE_TOKEN_COUNT=0",
            "VALIDATE_LOG_FILE=",
            f"PUBLISH_OK={publish_ok}",
            "UPSERT_STATUS=ok",
            "ARCHITECTURE_SOURCE=new",
            f"FINAL_SUMMARY_PATH={summary}",
            "",
        ]
    )


def test_step5c_core_render_uses_ctx_snapshot_when_ambient_env_overrides_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42", SESSION_ID="run-1", REPO="owner/repo")
    real_rehydrate = design_core._rehydrate_wrapper_env  # pyright: ignore[reportPrivateUsage]

    def rehydrate_then_ambient_override(parsed: object) -> dict[str, str]:
        env = real_rehydrate(parsed)  # type: ignore[arg-type]
        os.environ["ISSUE_NUMBER"] = "999"
        os.environ["SESSION_ID"] = "ambient-session"
        os.environ["REPO"] = "ambient/repo"
        return env

    monkeypatch.setattr(design_step5c, "_rehydrate_wrapper_env", rehydrate_then_ambient_override)
    seen_argv: list[list[str]] = []

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        print(_step5c_rows(design), end="")
        return 0

    def fake_render(argv: list[str]) -> int:
        seen_argv.append(list(argv))
        (design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert seen_argv == [
        [
            "--outcome",
            "approved",
            "--mode",
            "N/A",
            "--design-tmpdir",
            str(design),
            "--issue-number",
            "42",
            "--session-id",
            "run-1",
            "--post-publish-only",
            "--repo",
            "owner/repo",
        ]
    ]


def test_step5c_core_render_prefers_run_params_mode_over_source_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42", SESSION_ID="run-1", REPO="owner/repo")
    (design / "run-params.json").write_text('{"mode":"design"}\n', encoding="utf-8")
    (design / "source-env.sh").write_text("export MODE=stale\n", encoding="utf-8")
    seen_argv: list[list[str]] = []

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        print(_step5c_rows(design), end="")
        return 0

    def fake_render(argv: list[str]) -> int:
        seen_argv.append(list(argv))
        (design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert seen_argv == [
        [
            "--outcome",
            "approved",
            "--mode",
            "design",
            "--design-tmpdir",
            str(design),
            "--issue-number",
            "42",
            "--session-id",
            "run-1",
            "--post-publish-only",
            "--repo",
            "owner/repo",
        ]
    ]


def test_step5c_core_requires_design_tmpdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = tmp_path / "source-env.sh"
    env_path.write_text(f"export CLAUDE_PLUGIN_ROOT={CLI.parent.parent}\n", encoding="utf-8")
    monkeypatch.delenv("DESIGN_TMPDIR", raising=False)
    rc, _ = design_step5c.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    assert rc == 1


def test_step5c_core_requires_step5b_result_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    env_path = _write_session_env(tmp_path, design, monkeypatch, ISSUE_NUMBER="42")
    rc, _ = design_step5c.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    assert rc == 1
    status = larch_io.read_kvs(design / ".design-step5c-status.env")
    assert status["PUBLISH_RC"] == "not-run"
    assert status["CLEANUP_ELIGIBLE"] == "false"


def test_step5c_core_allows_publish_to_complete_step5b5_result_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    # step-5b.5 intentionally absent — publish_core completes it in-process
    env_path = _write_session_env(tmp_path, design, monkeypatch, ISSUE_NUMBER="42", SESSION_ID="run-1")
    (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")

    publish_called: list[list[str]] = []

    def fake_publish(argv: list[str], **_kwargs: object) -> int:
        publish_called.append(argv)
        (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
        print(_step5c_rows(design), end="")
        return 0

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    def fake_render(_argv: list[str]) -> int:
        (design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _ = design_step5c.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])

    assert rc == 0
    assert publish_called, "publish_core must be called"
    assert (design / ".completed" / "step-5b.5").is_file()
    assert (design / ".completed" / "step-5c").is_file()
    assert (design / ".design-step5c-status.env").is_file()


def test_step5c_core_pause_requested_skips_publish_and_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42", REPO="owner/repo")
    (design / ".pause-requested").write_text("", encoding="utf-8")
    called: list[list[str]] = []

    def fake_pause(argv: list[str]) -> int:
        called.append(argv)
        return 12

    def fail_publish(_argv: list[str], **_kwargs: object) -> int:
        raise AssertionError("publish_core should not run on pause")

    monkeypatch.setattr(design_pause, "pause_save_main", fake_pause)
    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fail_publish)
    rc, _ = design_step5c.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    assert rc == 12
    assert called == [["--design-tmpdir", str(design), "--issue", "42", "--repo", "owner/repo"]]
    assert True
    status = larch_io.read_kvs(design / ".design-step5c-status.env")
    assert status["PUBLISH_RC"] == "not-run"
    assert status["CLEANUP_ELIGIBLE"] == "false"


def test_step5c_core_pause_requested_emits_step5c_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42", REPO="owner/repo")
    (design / ".pause-requested").write_text("", encoding="utf-8")

    def fake_pause(_argv: list[str]) -> int:
        logging_util.emit_kv(key="PAUSE_OK", value="true")
        return 0

    monkeypatch.setattr(design_pause, "pause_save_main", fake_pause)
    rc, contract, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert "STEP5C_STATUS=pause-save" in contract
    assert "PAUSE_OK=true" in contract
    status = larch_io.read_kvs(design / ".design-step5c-status.env")
    assert status["PUBLISH_RC"] == "not-run"
    assert status["CLEANUP_ELIGIBLE"] == "false"


def test_step5c_core_assembles_publish_argv_and_writes_merge_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42", SESSION_ID="run-abc", REPO="owner/repo")
    (design / ".larch-keepalive").write_text(f"CLONE_PATH={tmp_path}\n", encoding="utf-8")
    seen: list[list[str]] = []

    def fake_publish(argv: list[str], **_kwargs: object) -> int:
        seen.append(argv)
        assert True
        print(_step5c_rows(design), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        print("unmarked render stdout")
        (design / "final-summary.md").write_text("summary body\n", encoding="utf-8")
        return 0

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, contract, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "777", "--skip-validate"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert seen == [
        [
            "--design-tmpdir",
            str(design),
            "--issue",
            "42",
            "--session-id",
            "run-abc",
            "--claude-pid",
            "777",
            "--repo",
            "owner/repo",
            "--skip-validate",
        ]
    ]
    status_text = (design / ".design-step5c-status.env").read_text(encoding="utf-8")
    assert "PUBLISH_RC=0" in status_text
    assert "FINAL_SUMMARY_PATH=" in status_text
    assert "FINAL_SUMMARY_READY=true" in status_text
    assert f"FINAL_SUMMARY_PATH={design / 'final-summary.md'}" in status_text
    final_summary_merge = (design / ".design-step-final-summary-result.env").read_text(encoding="utf-8")
    assert "FINAL_SUMMARY_READY=true" in final_summary_merge
    assert f"FINAL_SUMMARY_PATH={design / 'final-summary.md'}" in final_summary_merge
    assert True
    assert (design / ".completed" / "step-5c").is_file()
    assert (design / ".design-step5c-status.env").is_file()
    assert "PUBLISH_RC=0" in contract
    assert f"FINAL_SUMMARY_PATH={design / 'final-summary.md'}" in contract
    assert "LARCH_FINAL_SUMMARY_BEGIN\nLARCH_FINAL_SUMMARY_END" in contract
    assert "summary body" not in contract
    assert "unmarked render stdout" not in contract
    assert "unmarked render stdout" in (design / "render-final-summary.approved.stdout.log").read_text(encoding="utf-8")


def test_step5c_core_rc1_uses_stdout_over_stale_primary_and_binds_final_summary_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")
    stale = design / ".design-publish-result.env"
    stale.write_text("PLAN_WRITE_OK=true\nFINAL_SUMMARY_PATH=/stale/final-summary.md\nPUBLISH_OK=true\n", encoding="utf-8")
    current_summary = design / "current-summary.md"
    seen_env: list[str] = []
    seen_argv: list[list[str]] = []

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        print(_step5c_rows(design, plan_write_ok="false", publish_ok="", final_summary=current_summary), end="")
        current_summary.write_text("current failed summary\n", encoding="utf-8")
        return 1

    def fake_render(_argv: list[str]) -> int:
        seen_argv.append(list(_argv))
        seen_env.append(os.environ.get("FINAL_SUMMARY_PATH", ""))
        current_summary.write_text("current rendered summary\n", encoding="utf-8")
        return 0

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, contract, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert seen_env == [""]
    assert seen_argv == [
        [
            "--outcome",
            "failed-plan-write",
            "--mode",
            "N/A",
            "--design-tmpdir",
            str(design),
            "--issue-number",
            "42",
            "--session-id",
            "run-1",
            "--post-publish-only",
        ]
    ]
    status = (design / ".design-step5c-status.env").read_text(encoding="utf-8")
    assert "PLAN_WRITE_OK=false" in status
    assert "PUBLISH_STDOUT_FALLBACK=true" in status
    assert "CLEANUP_ELIGIBLE=false" in status
    assert not (design / ".completed" / "step-5c").exists()
    assert f"FINAL_SUMMARY_PATH={current_summary}" in contract
    assert "LARCH_FINAL_SUMMARY_BEGIN\nLARCH_FINAL_SUMMARY_END" in contract
    assert "current failed summary" not in contract


def test_step5c_core_rc3_stdout_fallback_keeps_success_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        print(_step5c_rows(design), end="")
        return 3

    def fake_render(_argv: list[str]) -> int:
        (design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _ = design_step5c.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    assert rc == 0
    assert (design / ".completed" / "step-5c").is_file()
    assert "PUBLISH_STDOUT_FALLBACK=true" in (design / ".design-step5c-status.env").read_text(encoding="utf-8")


def test_step5c_core_rc4_emits_validator_status_sidecars_and_no_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")
    (design / ".design-publish-result.env").write_text("PLAN_WRITE_OK=true\nVALIDATE_STATUS=ok\n", encoding="utf-8")
    (design / "design-failure-chat-print.md").write_text("sidecar body\n", encoding="utf-8")

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        print(
            "\n".join(
                [
                    "PLAN_WRITE_OK=false",
                    "VALIDATE_STATUS=defects-found",
                    "VALIDATE_DEFECT_COUNT=2",
                    "VALIDATE_SKIPPED_COUNT=0",
                    "VALIDATE_UNSAFE_TOKEN_COUNT=1",
                    "PUBLISH_REFUSE_REASON=validator-defects",
                    f"VALIDATE_LOG_FILE={design / 'validate.log'}",
                    f"FINAL_SUMMARY_PATH={design / 'final-summary.md'}",
                    "",
                ]
            ),
            end="",
        )
        return 4

    def fail_render(_argv: list[str]) -> int:
        raise AssertionError("render should not run for validator defects")

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fail_render)
    rc, contract, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert "STEP5C_STATUS=validator-defects" in contract
    assert "PUBLISH_REFUSE_REASON=validator-defects" in contract
    assert "REPORT_GATE_SIDECARS_FILE=" in contract
    assert "LARCH_FINAL_SUMMARY_BEGIN" not in contract
    assert "PLAN_WRITE_OK=false" in (design / ".design-step5c-status.env").read_text(encoding="utf-8")


def test_step5c_core_rc4_missing_invariant_assessment_not_validator_defects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        print(
            "\n".join(
                [
                    "PLAN_WRITE_OK=false",
                    "VALIDATE_STATUS=not-run",
                    "PUBLISH_REFUSE_REASON=missing-invariant-assessment",
                    "ARCH_INVARIANT_ASSESSMENT_REQUIRED=true",
                    "ARCH_INVARIANT_ASSESSMENT_PRESENT=false",
                    "ARCH_INVARIANT_ASSESSMENT_STATUS=missing",
                    "ARCH_INVARIANT_ASSESSMENT_ARTIFACT=architectural-invariant-assessment.md",
                    f"FINAL_SUMMARY_PATH={design / 'final-summary.md'}",
                    "",
                ]
            ),
            end="",
        )
        return 4

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    rc, contract, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )

    status_env = (design / ".design-step5c-status.env").read_text(encoding="utf-8")
    assert rc == 0
    assert "STEP5C_STATUS=missing-invariant-assessment" in contract
    assert "STEP5C_STATUS=validator-defects" not in contract
    assert "CLEANUP_ELIGIBLE=false" in status_env
    assert "ARCH_INVARIANT_ASSESSMENT_REQUIRED=true" in status_env
    assert not (design / ".completed" / "step-5c").exists()


def test_step5c_core_rc4_missing_guideline_assessment_not_validator_defects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        print(
            "\n".join(
                [
                    "PLAN_WRITE_OK=false",
                    "VALIDATE_STATUS=not-run",
                    "PUBLISH_REFUSE_REASON=missing-guideline-assessment",
                    "ARCH_GUIDE_ASSESSMENT_REQUIRED=true",
                    "ARCH_GUIDE_ASSESSMENT_PRESENT=false",
                    "ARCH_GUIDE_ASSESSMENT_STATUS=missing",
                    "ARCH_GUIDE_ASSESSMENT_ARTIFACT=architectural-guideline-assessment.md",
                    f"FINAL_SUMMARY_PATH={design / 'final-summary.md'}",
                    "",
                ]
            ),
            end="",
        )
        return 4

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    rc, contract, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )

    status_env = (design / ".design-step5c-status.env").read_text(encoding="utf-8")
    assert rc == 0
    assert "STEP5C_STATUS=missing-guideline-assessment" in contract
    assert "STEP5C_STATUS=validator-defects" not in contract
    assert "CLEANUP_ELIGIBLE=false" in status_env
    assert "ARCH_GUIDE_ASSESSMENT_REQUIRED=true" in status_env
    assert not (design / ".completed" / "step-5c").exists()


@pytest.mark.parametrize(
    ("refuse_reason", "status_key", "status_value"),
    [
        ("invariant-violation", "ARCH_INVARIANT_ASSESSMENT_STATUS", "violation"),
        ("invalid-guideline-deviation", "ARCH_GUIDE_ASSESSMENT_STATUS", "deviation"),
    ],
)
def test_step5c_core_rc4_gate_c_content_refusal_not_validator_defects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    refuse_reason: str,
    status_key: str,
    status_value: str,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        print(
            "\n".join(
                [
                    "PLAN_WRITE_OK=false",
                    "VALIDATE_STATUS=not-run",
                    f"PUBLISH_REFUSE_REASON={refuse_reason}",
                    f"{status_key}={status_value}",
                    f"FINAL_SUMMARY_PATH={design / 'final-summary.md'}",
                    "",
                ]
            ),
            end="",
        )
        return 4

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    rc, contract, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )

    status_env = (design / ".design-step5c-status.env").read_text(encoding="utf-8")
    assert rc == 0
    assert f"STEP5C_STATUS={refuse_reason}" in contract
    assert "STEP5C_STATUS=validator-defects" not in contract
    assert "CLEANUP_ELIGIBLE=false" in status_env
    assert not (design / ".completed" / "step-5c").exists()


def test_step5c_auto_compose_basic(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    plan = design / "plan.txt"
    plan.write_text(
        "## Approach\n\nDo the thing.\n\n## Testing strategy\n\nRun tests.\n\ndiff_lines: 5\n",
        encoding="utf-8",
    )
    design_step5c._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert "## Plan" in composed
    assert "Do the thing." in composed
    assert "## Acceptance" in composed
    assert "Run tests." in composed
    assert "diff_lines: 5" in composed


def test_step5c_auto_compose_does_not_duplicate_existing_acceptance(
    tmp_path: Path,
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "plan.txt").write_text(
        "## Approach\n\nDo the thing.\n\n"
        "## Testing strategy\n\nRun tests.\n\n"
        "## Acceptance\n\nThe focused test passes.\n\n"
        "diff_lines: 5\n",
        encoding="utf-8",
    )

    design_step5c._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]

    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert composed.count("## Acceptance") == 1
    assert "The focused test passes." in composed


def test_step5c_auto_compose_noop_when_file_exists(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    existing = plan_body(body="existing content", diff_lines=1)
    (design / "composed-plan.md").write_text(existing, encoding="utf-8")
    design_step5c._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]
    assert (design / "composed-plan.md").read_text(encoding="utf-8") == existing


def test_step5c_auto_compose_fallback_acceptance_when_no_testing_strategy(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "plan.txt").write_text(plan_body(header="## Approach", body="Body.", diff_lines=3), encoding="utf-8")
    design_step5c._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert "## Acceptance" in composed
    assert "See Testing strategy in plan." in composed


def test_step5c_auto_compose_no_plan_txt_emits_warning(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    design_step5c._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]
    assert not (design / "composed-plan.md").exists()


def test_step5c_auto_compose_strips_leading_plan_header(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "plan.txt").write_text(
        plan_body(body="## Approach\n\nDo the thing.\n\n## Testing strategy\n\nRun tests.", diff_lines=5),
        encoding="utf-8",
    )
    design_step5c._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert composed.count("## Plan") == 1
    assert "Do the thing." in composed
    assert "diff_lines: 5" in composed


def test_step5c_auto_compose_falls_back_to_diff_lines_sidecar(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "plan.txt").write_text("## Approach\n\nBody without trailer.\n", encoding="utf-8")
    (design / "diff-lines.txt").write_text("42\n", encoding="utf-8")
    design_step5c._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert "diff_lines: 42" in composed


def test_step5c_auto_compose_falls_back_to_diff_lines_with_optional_trailers(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "plan.txt").write_text("## Approach\n\nBody.\n", encoding="utf-8")
    (design / "diff-lines.txt").write_text("7\n", encoding="utf-8")
    (design / ".gate-b-optional-trailer-keys.values").write_text(
        "diff_added=10\ndiff_deleted=3\nmechanical_churn=false\noversize_override=operator\n",
        encoding="utf-8",
    )
    design_step5c._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert "diff_added: 10" in composed
    assert "diff_deleted: 3" in composed
    assert "mechanical_churn: false" in composed
    assert "oversize_override: operator" in composed
    assert "diff_lines: 7" in composed


def test_step5c_auto_compose_peels_orphan_optional_trailers(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "plan.txt").write_text(
        "## Approach\n\nBody.\n\ndiff_added: 10\ndiff_deleted: 3\nmechanical_churn: false\n",
        encoding="utf-8",
    )
    (design / "diff-lines.txt").write_text("7\n", encoding="utf-8")
    design_step5c._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert "diff_added: 10" in composed
    assert "mechanical_churn: false" in composed
    assert "Body." in composed
    assert "diff_lines: 7" in composed


def test_step5c_auto_compose_preserves_optional_trailers(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "plan.txt").write_text(
        (
            "## Approach\n\nBody.\n\ndiff_added: 10\ndiff_deleted: 3\nmechanical_churn: false\n"
            "oversize_override: operator\ndiff_lines: 7\n"
        ),
        encoding="utf-8",
    )
    design_step5c._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert "diff_added: 10" in composed
    assert "diff_deleted: 3" in composed
    assert "mechanical_churn: false" in composed
    assert "oversize_override: operator" in composed
    assert "diff_lines: 7" in composed


def test_step5c_auto_compose_preserves_full_shared_trailer_registry(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    trailer_block = "\n".join(
        plan_grammar.compose_trailer_lines(
            {
                "review_status": "complete",
                "rounds_completed": 2,
                "difficulty": "MODERATE",
                "diff_added": 10,
                "diff_deleted": 3,
                "mechanical_churn": False,
                "oversize_override": "operator",
                "diff_lines": 42,
            }
        )
    )
    (design / "plan.txt").write_text(
        f"## Approach\n\nBody.\n\n## Testing strategy\n\nRun tests.\n\n{trailer_block}\n",
        encoding="utf-8",
    )
    design_step5c._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    composed_trailers = plan_grammar.parse_final_trailers(composed, require_diff_lines=True)
    assert composed_trailers.lines == tuple(trailer_block.splitlines())
    assert [match.key for match in composed_trailers.matches] == list(plan_grammar.TRAILER_KEYS)
    assert composed_trailers.diff_lines == 42


def test_step5c_core_auto_composes_when_composed_plan_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")
    (design / "plan.txt").write_text(
        "## Approach\n\nFix the bug.\n\n## Testing strategy\n\nRun pytest.\n\ndiff_lines: 2\n",
        encoding="utf-8",
    )

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        print(_step5c_rows(design), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        (design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "777", "--skip-validate"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert "## Plan" in composed
    assert "Fix the bug." in composed
    assert "## Acceptance" in composed
    assert "Run pytest." in composed
    assert "diff_lines: 2" in composed


def test_step5c_core_publish_tail_abort_stages_renders_and_writes_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")
    (design / "design-failure-operator-action-chat.md").write_text("operator sidecar\n", encoding="utf-8")

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        return 2

    def fake_render(_argv: list[str]) -> int:
        (design / "final-summary.md").write_text("abort summary\n", encoding="utf-8")
        return 0

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, contract, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 1
    assert (design / "design-failure-terminal-state.env").is_file()
    assert "FAILURE_OUTCOME=failed-publish-tail" in (design / "design-failure-terminal-state.env").read_text(encoding="utf-8")
    stdout_log = design / "design-stage-terminal-state.stdout.log"
    stderr_log = design / "design-stage-terminal-state.stderr.log"
    assert stdout_log.is_file()
    assert stderr_log.is_file()
    assert stdout_log.stat().st_size > 0
    assert (design / ".design-step5c-status.env").is_file()
    assert f"FINAL_SUMMARY_PATH={design / 'final-summary.md'}" in contract
    assert "LARCH_FINAL_SUMMARY_BEGIN\nLARCH_FINAL_SUMMARY_END" in contract
    assert "FINAL_SUMMARY_READY=true" in (design / ".design-step5c-status.env").read_text(encoding="utf-8")
    assert "abort summary" not in contract
    assert "REPORT_GATE_SIDECARS_FILE=" in contract


def test_step5c_core_publish_tail_retries_central_publish_before_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42", SESSION_ID="run-1", REPO="owner/repo")
    central_calls: list[dict[str, str]] = []
    upsert_calls: list[dict[str, object]] = []

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        return 5

    def fake_central(**kwargs: str) -> tuple[int, bool]:
        central_calls.append(dict(kwargs))
        (design / "final-summary.md").write_text("central summary\n", encoding="utf-8")
        return 0, True

    def fail_render(**_kwargs: object) -> bool:
        raise AssertionError("local fallback should not run after clean central publish")

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_step5c, "_publish_terminal_final_summary", fake_central)
    monkeypatch.setattr(design_step5c, "_step5c_render_final_summary", fail_render)
    monkeypatch.setattr(design_summary, "upsert_final_summary_from_disk", lambda **kwargs: upsert_calls.append(dict(kwargs)) or True)  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    rc, contract, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )

    assert rc == 1
    assert central_calls[0]["outcome"] == "failed-publish-tail"
    assert upsert_calls
    assert "LARCH_FINAL_SUMMARY_BEGIN\nLARCH_FINAL_SUMMARY_END" in contract


def test_step5c_core_publish_tail_falls_back_when_central_publish_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42", SESSION_ID="run-1", REPO="owner/repo")
    central_calls: list[dict[str, str]] = []
    fallback_calls: list[dict[str, object]] = []

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        return 5

    def fake_central(**kwargs: str) -> tuple[int, bool]:
        central_calls.append(dict(kwargs))
        return 5, False

    def fake_render(**kwargs: object) -> bool:
        fallback_calls.append(dict(kwargs))
        (design / "final-summary.md").write_text("fallback summary\n", encoding="utf-8")
        return True

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_step5c, "_publish_terminal_final_summary", fake_central)
    monkeypatch.setattr(design_step5c, "_step5c_render_final_summary", fake_render)
    rc, contract, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )

    assert rc == 1
    assert central_calls[0]["outcome"] == "failed-publish-tail"
    assert len(fallback_calls) == 1
    assert (design / "final-summary.md").read_text(encoding="utf-8") == "fallback summary\n"
    assert "LARCH_FINAL_SUMMARY_BEGIN\nLARCH_FINAL_SUMMARY_END" in contract


def test_step5c_core_publish_tail_skips_retry_when_publish_evidence_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42", SESSION_ID="run-1")
    fallback_calls: list[str] = []

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        print("PUBLISH_OK=false")
        return 5

    def fake_render(**_kwargs: object) -> bool:
        fallback_calls.append("render")
        (design / "final-summary.md").write_text("fallback summary\n", encoding="utf-8")
        return True

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_step5c, "_publish_terminal_final_summary", lambda **_kwargs: (_ for _ in ()).throw(AssertionError("central publish should not run")))  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(design_step5c, "_step5c_render_final_summary", fake_render)
    rc, contract, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )

    assert rc == 1
    assert fallback_calls == ["render"]
    assert "LARCH_FINAL_SUMMARY_BEGIN\nLARCH_FINAL_SUMMARY_END" in contract


def test_step5c_core_publish_tail_falls_back_when_central_upsert_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42", SESSION_ID="run-1")
    fallback_calls: list[str] = []

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        return 5

    def fake_central(**_kwargs: str) -> tuple[int, bool]:
        (design / "final-summary.md").write_text("central summary\n", encoding="utf-8")
        return 0, True

    def fake_render(**_kwargs: object) -> bool:
        fallback_calls.append("render")
        (design / "final-summary.md").write_text("fallback summary\n", encoding="utf-8")
        return True

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_step5c, "_publish_terminal_final_summary", fake_central)
    monkeypatch.setattr(design_summary, "upsert_final_summary_from_disk", lambda **_kwargs: False)  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(design_step5c, "_step5c_render_final_summary", fake_render)
    rc, contract, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )

    assert rc == 1
    assert fallback_calls == ["render"]
    assert (design / "final-summary.md").read_text(encoding="utf-8") == "fallback summary\n"
    assert "LARCH_FINAL_SUMMARY_BEGIN\nLARCH_FINAL_SUMMARY_END" in contract


@pytest.mark.parametrize(
    ("session_id", "standalone_heavy_failed", "publish_ok", "expected_cleanup"),
    [
        ("", "false", "", "true"),
        ("run-abc", "false", "true", "true"),
        ("run-abc", "false", "false", "false"),
        ("run-abc", "false", "", "false"),
        ("run-abc", "true", "true", "false"),
    ],
)
def test_step5c_core_cleanup_eligibility_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    session_id: str,
    standalone_heavy_failed: str,
    publish_ok: str,
    expected_cleanup: str,
) -> None:
    design, env_path = _setup_step5c_design(
        tmp_path,
        monkeypatch,
        ISSUE_NUMBER="42",
        SESSION_ID=session_id,
        STANDALONE_HEAVY_FAILED=standalone_heavy_failed,
    )

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        print(_step5c_rows(design, publish_ok=publish_ok), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        (design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _ = design_step5c.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    assert rc == 0
    assert f"CLEANUP_ELIGIBLE={expected_cleanup}" in (design / ".design-step5c-status.env").read_text(encoding="utf-8")


def test_step5c_core_empty_session_id_publish_success_is_cleanup_eligible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(
        tmp_path,
        monkeypatch,
        ISSUE_NUMBER="42",
        SESSION_ID="",
        STANDALONE_HEAVY_FAILED="false",
    )
    seen: list[list[str]] = []
    render_argv: list[list[str]] = []

    def fake_publish(argv: list[str], **_kwargs: object) -> int:
        seen.append(argv)
        print(_step5c_rows(design, publish_ok=""), end="")
        return 0

    def fake_render(argv: list[str]) -> int:
        render_argv.append(list(argv))
        (design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _ = design_step5c.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    assert rc == 0
    assert seen[0][seen[0].index("--session-id") : seen[0].index("--session-id") + 2] == ["--session-id", ""]
    assert render_argv
    assert "--session-id" not in render_argv[0]
    assert "CLEANUP_ELIGIBLE=true" in (design / ".design-step5c-status.env").read_text(encoding="utf-8")


def test_step5c_core_publish_tail_abort_rc5_stages_and_writes_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        return 5

    def fake_render(_argv: list[str]) -> int:
        (design / "final-summary.md").write_text("abort summary\n", encoding="utf-8")
        return 0

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, contract, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 1
    assert (design / "design-failure-terminal-state.env").is_file()
    stdout_log = design / "design-stage-terminal-state.stdout.log"
    stderr_log = design / "design-stage-terminal-state.stderr.log"
    assert stdout_log.is_file()
    assert stderr_log.is_file()
    assert stdout_log.stat().st_size > 0
    assert (design / ".design-step5c-status.env").is_file()
    assert f"FINAL_SUMMARY_PATH={design / 'final-summary.md'}" in contract
    assert "LARCH_FINAL_SUMMARY_BEGIN\nLARCH_FINAL_SUMMARY_END" in contract
    assert "FINAL_SUMMARY_READY=true" in (design / ".design-step5c-status.env").read_text(encoding="utf-8")
    assert "abort summary" not in contract


def test_step5c_core_success_without_final_summary_skips_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")
    stale = design / "final-summary.md"
    stale.write_text("stale summary\n", encoding="utf-8")

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        print(_step5c_rows(design, final_summary=design / "missing-summary.md"), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        stale.unlink()
        return 0

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, contract, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert "LARCH_FINAL_SUMMARY_BEGIN" not in contract
    status_text = (design / ".design-step5c-status.env").read_text(encoding="utf-8")
    assert "FINAL_SUMMARY_READY=" not in status_text
    assert not (design / ".design-step-final-summary-result.env").exists()


def test_step5c_core_success_clears_bound_stale_summary_before_render(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")
    summary = design / "summaries" / "current-summary.md"
    summary.parent.mkdir()
    summary.write_text("stale success summary\n", encoding="utf-8")

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        print(_step5c_rows(design, final_summary=summary), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        assert not summary.exists()
        return 0

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, contract, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert not summary.exists()
    assert "stale success summary" not in contract
    assert "LARCH_FINAL_SUMMARY_BEGIN" not in contract
    status_text = (design / ".design-step5c-status.env").read_text(encoding="utf-8")
    assert "FINAL_SUMMARY_READY=" not in status_text
    assert not (design / ".design-step-final-summary-result.env").exists()


def test_step5c_core_render_failure_skips_stale_summary_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")
    (design / "final-summary.md").write_text("stale summary\n", encoding="utf-8")

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        print(_step5c_rows(design), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        return 1

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, contract, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert "LARCH_FINAL_SUMMARY_BEGIN" not in contract
    status_text = (design / ".design-step5c-status.env").read_text(encoding="utf-8")
    assert "FINAL_SUMMARY_READY=" not in status_text
    assert not (design / ".design-step-final-summary-result.env").exists()


def test_step5c_core_captures_subprocess_stdout_from_publish_tail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        os.write(1, b"WRITTEN=true\nMODE=write\n")
        print(_step5c_rows(design), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        (design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, contract, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert "PUBLISH_RC=0" in contract
    assert "WRITTEN=true" not in contract
    assert "MODE=write" not in contract


def test_step5c_core_restores_env_ipc_keys_after_return(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")
    before = {
        "FINAL_SUMMARY_PATH": os.environ.get("FINAL_SUMMARY_PATH"),
        "SUMMARY_OUTCOME": os.environ.get("SUMMARY_OUTCOME"),
    }

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        print(_step5c_rows(design), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        (design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    design_step5c.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    after = {
        "FINAL_SUMMARY_PATH": os.environ.get("FINAL_SUMMARY_PATH"),
        "SUMMARY_OUTCOME": os.environ.get("SUMMARY_OUTCOME"),
    }
    assert after == before




def test_step5c_core_publish_design_tmpdir_matches_ctx_on_symlinked_session_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_design = tmp_path / "real-design"
    (real_design / ".completed").mkdir(parents=True)
    (real_design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    (real_design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    link_parent = tmp_path / "link-parent"
    link_parent.mkdir()
    symlink_design = link_parent / "design-link"
    symlink_design.symlink_to(real_design)
    env_path = tmp_path / "source-env.sh"
    env_path.write_text(
        "\n".join(
            [
                f"export DESIGN_TMPDIR={symlink_design}",
                "export SESSION_ID=run-1",
                f"export CLAUDE_PLUGIN_ROOT={CLI.parent.parent}",
                "export ISSUE_NUMBER=42",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DESIGN_TMPDIR", str(symlink_design))
    seen: list[list[str]] = []

    def fake_publish(argv: list[str], **_kwargs: object) -> int:
        seen.append(argv)
        print(_step5c_rows(real_design), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        (real_design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _ = design_step5c.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    assert rc == 0
    assert seen
    publish_tmpdir = seen[0][seen[0].index("--design-tmpdir") + 1]
    assert Path(publish_tmpdir).resolve() == real_design.resolve()




def test_step5c_main_machine_rows_visible_under_inherited_quiet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        print(_step5c_rows(design), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        (design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    from larch.design import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
    monkeypatch.setenv(config.ENV_LARCH_QUIET_ACTIVE, "1")
    monkeypatch.setenv(config.ENV_LARCH_QUIET_PID, "999999")
    logging_util.reset_quiet_state()
    read_fd, write_fd = os.pipe()
    saved_stdout = os.dup(1)
    try:
        os.dup2(write_fd, 1)
        os.close(write_fd)
        rc = design_step5c.step5c_main(["--session-env-path", str(env_path), "--claude-pid", "123"])
        os.dup2(saved_stdout, 1)
        contract = os.read(read_fd, 65536).decode("utf-8")
    finally:
        os.close(read_fd)
        os.close(saved_stdout)
        logging_util.reset_quiet_state()
    assert rc == 0
    assert "PUBLISH_RC=0" in contract




def _write_step5c_status(
    design: Path,
    *,
    plan_write_ok: str = "true",
    publish_ok: str = "true",
    standalone_heavy_failed: str = "false",
    session_id: str = "",
    cleanup_eligible: str = "true",
) -> None:
    (design / ".design-step5c-status.env").write_text(
        "\n".join(
            [
                f"PLAN_WRITE_OK={plan_write_ok}",
                f"PUBLISH_OK={publish_ok}",
                f"STANDALONE_HEAVY_FAILED={standalone_heavy_failed}",
                f"SESSION_ID={session_id}",
                "PUBLISH_RC=0",
                "PUBLISH_STDOUT_FALLBACK=false",
                f"CLEANUP_ELIGIBLE={cleanup_eligible}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _step6_args(env_path: Path) -> list[str]:
    return ["--session-env-path", str(env_path), "--claude-pid", "123"]


def _step6_design(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **extra: str) -> tuple[Path, Path]:
    design = tmp_path / "design"
    design.mkdir()
    env_path = _write_session_env(tmp_path, design, monkeypatch, **extra)
    return design, env_path


def _step6_env_without_plugin_root(tmp_path: Path, design: Path, monkeypatch: pytest.MonkeyPatch | None = None, *, design_tmpdir: str | None = None, **extra: str) -> Path:
    raw_tmpdir = str(design.resolve()) if design_tmpdir is None else design_tmpdir
    if monkeypatch is not None:
        if raw_tmpdir:
            monkeypatch.setenv("DESIGN_TMPDIR", raw_tmpdir)
        else:
            monkeypatch.delenv("DESIGN_TMPDIR", raising=False)
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    env_path = tmp_path / "source-env.sh"
    lines = [
        f"export DESIGN_TMPDIR={raw_tmpdir}",
        "export SESSION_ID=run-1",
    ]
    lines.extend(f"export {key}={value}" for key, value in extra.items())
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return env_path




def _patch_step5c_registry(
    monkeypatch: pytest.MonkeyPatch,
    design: Path,
    *,
    present: bool,
    child_live: bool = False,
    daemon_live: bool = False,
) -> list[Path]:
    entry = SimpleNamespace(step="design-step5c")

    def fake_read_for(*, tmpdir: Path, step: str, run_id: str | None = None) -> tuple[Path, object | None]:
        assert tmpdir == design
        assert step == "design-step5c"
        assert run_id is None
        return design / "registry.env", entry if present else None

    def fake_child_liveness(_entry: object) -> SimpleNamespace:
        return SimpleNamespace(live=child_live)

    def fake_daemon_liveness(_entry: object) -> SimpleNamespace:
        return SimpleNamespace(live=daemon_live)

    unlinked: list[Path] = []

    def fake_unlink_entry(path: Path) -> None:
        unlinked.append(path)

    monkeypatch.setattr(design_step6.registry, "read_for", fake_read_for)
    monkeypatch.setattr(design_step6.registry, "child_liveness", fake_child_liveness)
    monkeypatch.setattr(design_step6.registry, "daemon_liveness", fake_daemon_liveness)
    monkeypatch.setattr(design_step6.registry, "unlink_entry", fake_unlink_entry)
    return unlinked

def test_step6_prelude_in_flight_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    _patch_step5c_registry(monkeypatch, design, present=True, child_live=True)
    rc = design_step6.step6_prelude_core(_step6_args(env_path))
    captured = capsys.readouterr()
    assert rc == 1
    assert "appears still in-flight" in captured.err
    assert "STEP6_PRELUDE_STATUS=skipped" not in captured.out


def test_step6_cleanup_in_flight_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    _patch_step5c_registry(monkeypatch, design, present=True, daemon_live=True)
    rc = design_step6.step6_cleanup_core(_step6_args(env_path))
    captured = capsys.readouterr()
    assert rc == 1
    assert "appears still in-flight" in captured.err
    assert "CLEANUP_STATUS=preserved" not in captured.out


def test_step6_missing_sidecar_skips_without_plugin_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    env_path = _step6_env_without_plugin_root(tmp_path, design, monkeypatch)

    assert design_step6.step6_prelude_core(_step6_args(env_path)) == 0
    prelude = capsys.readouterr()
    assert "STEP6_PRELUDE_STATUS=skipped" in prelude.out
    assert "appears still in-flight" not in prelude.err

    assert design_step6.step6_cleanup_core(_step6_args(env_path)) == 0
    cleanup = capsys.readouterr()
    assert "CLEANUP_STATUS=preserved" in cleanup.out
    assert "appears still in-flight" not in cleanup.err


def test_step6_in_flight_signal_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    raw = str(design)
    result_env = design / "bgjob" / "design-step5c.result.env"

    assert design_step6._step6_in_flight("") is False  # pyright: ignore[reportPrivateUsage]
    _patch_step5c_registry(monkeypatch, design, present=False)
    assert design_step6._step6_in_flight(raw) is False  # pyright: ignore[reportPrivateUsage]

    _patch_step5c_registry(monkeypatch, design, present=True, child_live=True)
    assert design_step6._step6_in_flight(raw) is True  # pyright: ignore[reportPrivateUsage]

    unlinked = _patch_step5c_registry(monkeypatch, design, present=True, child_live=False, daemon_live=False)
    assert design_step6._step6_in_flight(raw) is False  # pyright: ignore[reportPrivateUsage]
    assert unlinked == [design / "registry.env"]

    _patch_step5c_registry(monkeypatch, design, present=True, child_live=True)
    result_env.parent.mkdir(parents=True)
    result_env.write_text("BGJOB_RC=0\n", encoding="utf-8")
    assert design_step6._step6_in_flight(raw) is False  # pyright: ignore[reportPrivateUsage]



def test_step6_pause_wins_over_in_flight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch, ISSUE_NUMBER="42", REPO="owner/repo")
    (design / ".pause-requested").write_text("", encoding="utf-8")
    _patch_step5c_registry(monkeypatch, design, present=True, child_live=True)
    calls: list[list[str]] = []

    def fake_pause(argv: list[str]) -> int:
        calls.append(argv)
        return 0

    monkeypatch.setattr(design_pause, "pause_save_main", fake_pause)
    assert design_step6.step6_prelude_core(_step6_args(env_path)) == 0
    assert design_step6.step6_cleanup_core(_step6_args(env_path)) == 0
    captured = capsys.readouterr()
    assert len(calls) == 2
    assert all(call == ["--design-tmpdir", str(design), "--issue", "42", "--repo", "owner/repo"] for call in calls)
    assert "appears still in-flight" not in captured.err


def test_step6_prelude_writes_step5d_before_second_pause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    _write_step5c_status(design)
    original_touch = design_core._touch  # pyright: ignore[reportPrivateUsage]
    calls: list[list[str]] = []

    def fake_touch(path: Path) -> None:
        original_touch(path)
        if path == design / ".completed" / "step-5d":
            (design / ".pause-requested").write_text("", encoding="utf-8")

    def fake_pause(argv: list[str]) -> int:
        assert (design / ".completed" / "step-5d").is_file()
        calls.append(argv)
        return 7

    monkeypatch.setattr(design_step6, "_touch", fake_touch)
    monkeypatch.setattr(design_pause, "pause_save_main", fake_pause)
    assert design_step6.step6_prelude_core(_step6_args(env_path)) == 7
    assert len(calls) == 1


def test_step6_cleanup_deletion_path_validates_requires_and_writes_result_env_before_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    _write_step5c_status(design)
    order: list[str] = []

    def fake_validate(candidate: str) -> Path:
        assert candidate == str(design)
        order.append("validate")
        return design

    def fake_require() -> int:
        assert order == ["validate"]
        order.append("require")
        return 0

    def fake_cleanup(design_tmpdir: Path) -> int:
        assert order == ["validate", "require"]
        assert design_tmpdir == design
        assert (design / ".completed" / "step-6").is_file()
        order.append("cleanup")
        return 0

    def fake_reap(claude_pid: str) -> None:
        assert claude_pid == "123"
        assert order == ["validate", "require", "cleanup"]
        order.append("reap")

    monkeypatch.setattr(design_step6, "_validate_design_tmpdir_arg", fake_validate)
    monkeypatch.setattr(design_step6, "_design_require_plugin_root", fake_require)
    monkeypatch.setattr(design_step6, "_remove_design_tmpdir", fake_cleanup)
    monkeypatch.setattr(session_env, "reap_pid_residuals", fake_reap)

    assert design_step6.step6_cleanup_core(_step6_args(env_path)) == 0
    assert order == ["validate", "require", "cleanup", "reap"]


def test_step6_cleanup_reaps_pid_residuals_after_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    design, env_path = _step6_design(tmp_path, monkeypatch)
    _write_step5c_status(design)
    residuals = _write_pid_residuals(home, target=design / "source-env.sh")

    def local_cleanup(design_tmpdir: Path) -> int:
        shutil.rmtree(design_tmpdir)
        return 0

    monkeypatch.setattr(design_step6, "_remove_design_tmpdir", local_cleanup)

    assert design_step6.step6_cleanup_core(_step6_args(env_path)) == 0
    assert not design.exists()
    assert all(not path.exists() and not path.is_symlink() for path in residuals)


def test_step6_cleanup_does_not_reap_when_preserved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    _write_step5c_status(design, cleanup_eligible="false")

    def fail_reap(_claude_pid: str) -> None:
        raise AssertionError("preserved cleanup must not reap PID residuals")

    monkeypatch.setattr(session_env, "reap_pid_residuals", fail_reap)
    assert design_step6.step6_cleanup_core(_step6_args(env_path)) == 0
    assert design.exists()


def test_step6_cleanup_does_not_reap_when_tmpdir_cleanup_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    _write_step5c_status(design)

    def fail_cleanup(_design_tmpdir: Path) -> int:
        return 1

    def fail_reap(_claude_pid: str) -> None:
        raise AssertionError("failed tmpdir cleanup must not reap PID residuals")

    monkeypatch.setattr(design_step6, "_remove_design_tmpdir", fail_cleanup)
    monkeypatch.setattr(session_env, "reap_pid_residuals", fail_reap)
    assert design_step6.step6_cleanup_core(_step6_args(env_path)) == 1


def test_step6_cleanup_rejects_invalid_claude_pid_before_touch_or_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    _write_step5c_status(design)

    def fail_cleanup(_design_tmpdir: Path) -> int:
        raise AssertionError("cleanup must not run after invalid --claude-pid")

    def fail_reap(_claude_pid: str) -> None:
        raise AssertionError("reap must not run after invalid --claude-pid")

    monkeypatch.setattr(design_step6, "_remove_design_tmpdir", fail_cleanup)
    monkeypatch.setattr(session_env, "reap_pid_residuals", fail_reap)

    rc = design_step6.step6_cleanup_core(["--session-env-path", str(env_path), "--claude-pid", "bogus"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "Invalid --claude-pid" in err


def test_step6_combined_skips_cleanup_when_prelude_saves_pause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    monkeypatch.setenv(config.ENV_LARCH_QUIET_DISABLE, "1")

    def fake_prelude(_argv: Sequence[str]) -> int:
        (design / ".pause-save-complete").write_text("", encoding="utf-8")
        return 0

    def fail_cleanup(_argv: Sequence[str]) -> int:
        raise AssertionError("cleanup should not run after pause-save")

    monkeypatch.setattr(design_step6, "step6_prelude_core", fake_prelude)
    monkeypatch.setattr(design_step6, "step6_cleanup_core", fail_cleanup)
    assert design_step6.step6_main(_step6_args(env_path)) == 0


def test_step6_combined_removes_stale_pause_marker_after_rehydrate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    env_path = _write_session_env(tmp_path, design, None)
    (design / ".pause-save-complete").write_text("stale\n", encoding="utf-8")
    monkeypatch.delenv("DESIGN_TMPDIR", raising=False)
    monkeypatch.setenv(config.ENV_LARCH_QUIET_DISABLE, "1")
    calls: list[str] = []

    def fake_prelude(_argv: Sequence[str]) -> int:
        calls.append("prelude")
        assert not (design / ".pause-save-complete").exists()
        return 0

    def fake_cleanup(_argv: Sequence[str]) -> int:
        calls.append("cleanup")
        return 0

    monkeypatch.setattr(design_step6, "step6_prelude_core", fake_prelude)
    monkeypatch.setattr(design_step6, "step6_cleanup_core", fake_cleanup)
    assert design_step6.step6_main(_step6_args(env_path)) == 0
    assert calls == ["prelude", "cleanup"]


def test_step6_sidecar_has_authority_over_session_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch, PLAN_WRITE_OK="true", CLEANUP_ELIGIBLE="true")
    _write_step5c_status(design, plan_write_ok="false")

    assert design_step6.step6_prelude_core(_step6_args(env_path)) == 0
    assert "plan write did not succeed" in capsys.readouterr().out
    assert design_step6.step6_cleanup_core(_step6_args(env_path)) == 0
    assert "plan write did not succeed" in capsys.readouterr().out
    assert not (design / ".completed" / "step-5d").exists()
    assert not (design / ".completed" / "step-6").exists()


def test_step6_cleanup_preserves_publish_failure_from_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    _write_step5c_status(design, publish_ok="false", session_id="run-1")
    assert design_step6.step6_cleanup_core(_step6_args(env_path)) == 0
    out = capsys.readouterr().out
    assert "publish did not complete" in out
    assert "CLEANUP_STATUS=preserved" in out
    assert not (design / ".completed" / "step-6").exists()


def test_step6_cleanup_preserves_cleanup_ineligible_from_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    _write_step5c_status(design, cleanup_eligible="false")
    assert design_step6.step6_cleanup_core(_step6_args(env_path)) == 0
    assert "cleanup not eligible" in capsys.readouterr().out
    assert not (design / ".completed" / "step-6").exists()


def test_step6_cleanup_preserves_standalone_heavy_before_later_gates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    _write_step5c_status(design, standalone_heavy_failed="true", publish_ok="false", session_id="run-1", cleanup_eligible="false")
    assert design_step6.step6_cleanup_core(_step6_args(env_path)) == 0
    out = capsys.readouterr().out
    assert "standalone heavy failed" in out
    assert "publish did not complete" not in out
    assert "cleanup not eligible" not in out


def test_step6_empty_design_tmpdir_defers_validation_and_preserves(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    env_path = _step6_env_without_plugin_root(tmp_path, tmp_path, monkeypatch, design_tmpdir="")

    def fail_validate(_candidate: str) -> Path:
        raise AssertionError("empty tmpdir skip/preserve paths must not validate")

    monkeypatch.setattr(design_step6, "_validate_design_tmpdir_arg", fail_validate)
    assert design_step6.step6_prelude_core(_step6_args(env_path)) == 0
    assert "STEP6_PRELUDE_STATUS=skipped" in capsys.readouterr().out
    assert design_step6.step6_cleanup_core(_step6_args(env_path)) == 0
    assert "CLEANUP_STATUS=preserved" in capsys.readouterr().out


def test_step6_main_machine_rows_visible_under_inherited_quiet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _design, env_path = _step6_design(tmp_path, monkeypatch)
    monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
    monkeypatch.setenv(config.ENV_LARCH_QUIET_ACTIVE, "1")
    monkeypatch.setenv(config.ENV_LARCH_QUIET_PID, "999999")
    logging_util.reset_quiet_state()
    read_fd, write_fd = os.pipe()
    saved_stdout = os.dup(1)
    try:
        os.dup2(write_fd, 1)
        os.close(write_fd)
        rc = design_step6.step6_prelude_main(_step6_args(env_path))
        os.dup2(saved_stdout, 1)
        contract = os.read(read_fd, 65536).decode("utf-8")
    finally:
        os.close(read_fd)
        os.close(saved_stdout)
        logging_util.reset_quiet_state()
    assert rc == 0
    assert "STEP6_PRELUDE_STATUS=skipped" in contract








def test_core_style_ctx_subprocess_env_preserves_path_and_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from larch.core.ctx import Ctx  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    home = tmp_path / "home"
    home.mkdir()
    design = tmp_path / "design"
    design.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PATH", "/custom/bin:/usr/bin")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    rehydrated = {
        "DESIGN_TMPDIR": str(design),
        "CLAUDE_PLUGIN_ROOT": str(CLI.parent.parent),
        "HOME": str(home),
        "PATH": "/custom/bin:/usr/bin",
    }
    ctx = Ctx.from_mapping({**os.environ, **rehydrated, "DESIGN_TMPDIR": str(design)})
    env = ctx.subprocess_env(overrides={"LARCH_TIMING_SKILL": "design"})
    assert env.get("PATH") == "/custom/bin:/usr/bin"
    assert env.get("HOME") == str(home)
    assert env.get("LARCH_TIMING_SKILL") == "design"












































def test_step6_cleanup_deactivates_run_before_tmpdir_removal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """step6_cleanup_core calls the Rust deactivation seam before cleanup."""
    design, env_path = _step6_design(tmp_path, monkeypatch)
    (design / "source-env.sh").write_text(
        "LARCH_RUN_ID=step6-run-77\n", encoding="utf-8"
    )
    _write_step5c_status(design)

    deactivate_calls: list[tuple[object, str]] = []

    def fake_deactivate(
        _runner: object,
        *,
        repo_root: str,
        run_id: str,
        cwd: str | None = None,
    ) -> bool:
        _ = cwd
        deactivate_calls.append((repo_root, run_id))
        return True

    def fake_cleanup(_design_tmpdir: Path) -> int:
        return 0

    def fake_reap(_pid: str) -> None:
        pass

    monkeypatch.setattr(design_step6.rust_runtime, "progress_deactivate", fake_deactivate)
    monkeypatch.setattr(design_step6, "_remove_design_tmpdir", fake_cleanup)
    monkeypatch.setattr(session_env, "reap_pid_residuals", fake_reap)

    rc = design_step6.step6_cleanup_core(_step6_args(env_path))
    assert rc == 0
    assert len(deactivate_calls) == 1
    assert deactivate_calls[0][1] == "step6-run-77"




def test_step5c_rc5_uses_current_attempt_progress_and_persists_tails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")

    def fake_publish(_argv: list[str], **_kwargs: object) -> int:
        attempt_id = os.environ[config.ENV_LARCH_DESIGN_PUBLISH_ATTEMPT_ID]
        (design / config.DESIGN_PUBLISH_RESULT_FILE).write_text(
            "\n".join(
                [
                    f"PUBLISH_ATTEMPT_ID={attempt_id}",
                    "PUBLISH_RC_SOURCE=returned",
                    "LATEST_PHASE=tracking-issue-rename",
                    "PLAN_WRITE_OK=true",
                    "PUBLISH_OK=false",
                    "RENAMED=true",
                    "LOG_PUBLISH_ATTEMPTED=false",
                    "LOG_PUBLISH_COMPLETED=false",
                    "DESIGNED_ADMISSION_READY=true",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print("bounded stdout evidence")
        print("nested failure", file=sys.stderr)
        return 5

    monkeypatch.setattr(design_step5c, "_step5c_invoke_publish_core", fake_publish)
    rc, _, _ = _capture_core_contract(
        design_step5c.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )

    assert rc == 1
    state = (design / "design-failure-terminal-state.env").read_text(encoding="utf-8")
    assert "PLAN_WRITE_OK=true" in state
    assert "RENAMED=true" in state
    assert "PUBLISH_RC_SOURCE=returned" in state
    assert (design / config.DESIGN_PUBLISH_STDOUT_TAIL_FILE).read_text(encoding="utf-8")
    assert "nested failure" in (design / config.DESIGN_PUBLISH_STDERR_TAIL_FILE).read_text(encoding="utf-8")
    detail = (design / config.DESIGN_PUBLISH_FAILURE_DETAIL_FILE).read_text(encoding="utf-8")
    assert "latest_phase=tracking-issue-rename" in detail
    assert "plan_write_ok=true" in detail


def test_design_lifecycle_module_is_deleted_in_fresh_process() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import larch.design.design_lifecycle"],
        cwd=CLI.parent,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "ModuleNotFoundError" in result.stderr
