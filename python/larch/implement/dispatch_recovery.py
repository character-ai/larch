# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""Recovery-path CLI consumer and implement-commit entrypoint.

Recovery-path computation is Rust-owned (`implement recovery-paths`). This
module keeps a thin typed wrapper for still-Python dispatch callers plus the
Python-owned `implement commit` command.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from larch.core import logging_util
from larch.core.repo_roots import larch_entrypoint, larch_entrypoint_env
from larch.implement.dispatch_helpers import (
    _current_cli_path,
    _emit_kv,
    _err,
    _invoke_larch,
    _run,
    _session_get,
)


@dataclass(frozen=True)
class RecoveryPorcelainInputs:
    prelaunch_porcelain: Path
    postlaunch_porcelain: Path
    prelaunch_digests: Path


def compute_recovery_paths(
    *,
    repo_root: Path,
    tmpdir: Path,
    porcelain: RecoveryPorcelainInputs,
    out_file: Path,
) -> bool:
    """Rust-owned recovery-path computation via ``scripts/larch.sh``.

    Returns True when at least one candidate path was written (CLI rc 0).
    """
    result = _invoke_larch(
        [
            "implement",
            "recovery-paths",
            "--repo-root",
            str(repo_root),
            "--tmpdir",
            str(tmpdir),
            "--prelaunch-porcelain",
            str(porcelain.prelaunch_porcelain),
            "--postlaunch-porcelain",
            str(porcelain.postlaunch_porcelain),
            "--prelaunch-digests",
            str(porcelain.prelaunch_digests),
            "--out-file",
            str(out_file),
        ],
        cwd=repo_root,
    )
    return result.returncode == 0


def _commit_usage_fail(error: str) -> int:
    _err("Usage: implement commit --message MSG [--pathspec-from-file PATH [--pathspec-file-nul]] [files...]")
    _err("HINT: --stage-all belongs to review-and-fix commit-fixes (Step 5 review fixes); implementation commits name specific files or use --pathspec-from-file.")
    _emit_kv(key="COMMITTED", value="false")
    _emit_kv(key="SHA", value="")
    _emit_kv(key="ERROR", value=error)
    return 2


def _scan_commit_argv(argv_list: list[str]) -> int | None:
    known_flags = {"--message", "-m", "--pathspec-from-file", "--pathspec-file-nul", "--help", "-h"}
    idx = 0
    while idx < len(argv_list):
        arg = argv_list[idx]
        if arg in ("--help", "-h"):
            argparse.ArgumentParser(prog="cli.py implement commit").print_help()
            return 0
        if arg.startswith("-") and arg not in known_flags:
            return _commit_usage_fail(f"unknown option: {arg}")
        if arg in ("--message", "-m", "--pathspec-from-file"):
            if idx + 1 >= len(argv_list) or argv_list[idx + 1].startswith("-"):
                return _commit_usage_fail(f"{arg} requires a value")
            idx += 2
            continue
        if arg == "--pathspec-file-nul":
            idx += 1
            continue
        idx += 1
    return None


def _rehydrate_commit_session_from_tmpdir() -> None:
    env_file = Path(os.environ.get("IMPLEMENT_TMPDIR", "")) / "session-env.sh" if os.environ.get("IMPLEMENT_TMPDIR") else None
    if env_file and env_file.is_file():
        for key in ("LARCH_TOKEN_SESSION_ID", "LARCH_CLAUDE_SOURCE_FILE", "LARCH_TIMING_LEDGER"):
            if not os.environ.get(key):
                value = _session_get(file=env_file, key=key, default="")
                if value:
                    os.environ[key] = value


def _mark_commit_timing() -> None:
    env = larch_entrypoint_env(_current_cli_path().parents[1])
    _invoke_cli(["token", "mark", "Step 4 — commit implementation"], env=env)
    env["LARCH_TIMING_SKILL"] = "implement"
    _invoke_cli(["timing", "mark", "Step 4 — commit implementation"], env=env)


def _invoke_cli(args: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Invoke one Rust-owned command through the verified bootstrap script."""
    return subprocess.run(
        [str(larch_entrypoint(_current_cli_path().parents[1])), *args],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _build_commit_args(args: argparse.Namespace) -> list[str]:
    commit_args = [str(larch_entrypoint(_current_cli_path().parents[1])), "git", "commit", "-m", args.message]
    if args.pathspec_from_file:
        commit_args.extend(["--only", "--pathspec-from-file", args.pathspec_from_file])
        if args.pathspec_file_nul:
            commit_args.append("--pathspec-file-nul")
    else:
        commit_args.extend(args.files)
    return commit_args


def _emit_commit_result(result: subprocess.CompletedProcess[str]) -> int:
    if result.returncode == 0:
        sha = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
        _emit_kv(key="COMMITTED", value="true")
        _emit_kv(key="SHA", value=sha)
        return 0
    error = (result.stderr or result.stdout).replace("\n", " ")[:500]
    _emit_kv(key="COMMITTED", value="false")
    _emit_kv(key="SHA", value="")
    _emit_kv(key="ERROR", value=error)
    return result.returncode


def commit_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    argv_list = list(argv if argv is not None else sys.argv[1:])
    scan_rc = _scan_commit_argv(argv_list)
    if scan_rc is not None:
        return scan_rc
    parser = argparse.ArgumentParser(prog="cli.py implement commit", add_help=True)
    parser.add_argument("--message", "-m", default="")
    parser.add_argument("--pathspec-from-file", default="")
    parser.add_argument("--pathspec-file-nul", action="store_true")
    parser.add_argument("files", nargs="*")
    args = parser.parse_args(argv_list)
    if not args.message.strip():
        return _commit_usage_fail("--message is required")
    _rehydrate_commit_session_from_tmpdir()
    _mark_commit_timing()
    return _emit_commit_result(_run(_build_commit_args(args)))
