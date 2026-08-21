"""Tests for Python /design lifecycle helpers."""
# pyright: reportUnusedCallResult=false, reportUnknownLambdaType=false, reportUnknownArgumentType=false

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from larch.core import config
from larch.design import design_core
from larch.core import logging_util
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
        allow_keys=[
            "INIT_STATUS",
            "RUN_PARAMS_PATH",
            "OOS_SKIP_BREADCRUMB",
            "SETTLE_NEXT_ACTION",
            "BAD",
        ],
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


def test_pause_save_command_uses_rehydrated_environment(tmp_path: Path) -> None:
    command = design_core._pause_save_command(  # pyright: ignore[reportPrivateUsage]
        design_tmpdir=tmp_path,
        env={
            "CLAUDE_PLUGIN_ROOT": str(tmp_path / "plugin"),
            "ISSUE_NUMBER": "42",
            "REPO": "owner/repo",
        },
    )

    assert command[1:3] == ["design", "pause-save"]
    assert command[command.index("--issue") + 1] == "42"
    assert command[command.index("--repo") + 1] == "owner/repo"


def _write_session_env(
    tmp_path: Path,
    design: Path,
    monkeypatch: pytest.MonkeyPatch | None = None,
    **extra: str,
) -> Path:
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


def _write_pid_residuals(
    home: Path, *, target: Path, pid: str = "123"
) -> tuple[Path, Path, Path]:
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


def test_reap_pid_residuals_uses_home_cache_when_xdg_differs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    parsed = design_core._parse_common_wrapper_args(
        ["--session-env-path", str(session_env)]
    )  # pyright: ignore[reportPrivateUsage]
    merged = design_core._rehydrate_wrapper_env(parsed)  # pyright: ignore[reportPrivateUsage]
    assert merged["DESIGN_TMPDIR"] == str(design)
    assert os.environ["ISSUE_NUMBER"] == "42"


def test_rehydrate_wrapper_env_resolves_trusted_design_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    sessions = home / ".cache" / "larch" / "sessions"
    sessions.mkdir(parents=True)
    source = sessions / "design-env-123.sh"
    design = tmp_path / "design"
    design.mkdir()
    source.write_text(
        f"export DESIGN_TMPDIR={str(design)!r}\nexport ISSUE_NUMBER='7'\n",
        encoding="utf-8",
    )
    link = sessions / "current-design-env-123.sh"
    link.symlink_to(source)
    monkeypatch.setenv("HOME", str(home))
    parsed = design_core._parse_common_wrapper_args(
        ["--session-env-path", str(link), "--claude-pid", "123"]
    )  # pyright: ignore[reportPrivateUsage]
    merged = design_core._rehydrate_wrapper_env(parsed)  # pyright: ignore[reportPrivateUsage]
    assert merged["DESIGN_TMPDIR"] == str(design)
    assert merged["ISSUE_NUMBER"] == "7"


def test_capture_contract_stream_restores_fd3_for_quiet_init(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
