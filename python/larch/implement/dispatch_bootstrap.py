# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""Step 0 bootstrap entrypoints."""

from __future__ import annotations

import argparse
import shutil

from larch.implement.dispatch_helpers import (
    _invoke_cli,
    _parse_kv,
    _read_session_key_default,
    _rehydrate_plugin_root,
    _run_cli_forward,
    _tmpdir_from_env,
)


def step0_degraded_gate_main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(prog="cli.py implement step-0-degraded-gate").parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    codex_binary_found = _read_session_key_default(implement_tmpdir=implement_tmpdir, key="CODEX_BINARY_FOUND", default="")
    cursor_binary_found = _read_session_key_default(implement_tmpdir=implement_tmpdir, key="CURSOR_BINARY_FOUND", default="")
    check_args = ["agent", "check-reviewers"]
    if shutil.which("codex") is None:
        check_args.append("--skip-codex-probe")
    if shutil.which("cursor") is None:
        check_args.append("--skip-cursor-probe")
    probe = _invoke_cli(check_args)
    if probe.returncode != 0:
        probe = _invoke_cli(check_args)
    values = _parse_kv(probe.stdout)
    return _run_cli_forward([
        "agent", "degraded-tools-gate", "--skill", "implement",
        "--codex-present", values.get("CODEX_PRESENT", ""),
        "--cursor-present", values.get("CURSOR_PRESENT", ""),
        "--codex-binary-found", codex_binary_found,
        "--cursor-binary-found", cursor_binary_found,
    ])
