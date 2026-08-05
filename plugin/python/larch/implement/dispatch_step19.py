"""Step 19 cleanup after run-log terminalization."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from larch.core import config
from larch.implement.dispatch_helpers import (
    _emit_kv,  # pyright: ignore[reportPrivateUsage]  # Shared dispatch helper.
    _larch_entrypoint,  # pyright: ignore[reportPrivateUsage]  # Shared dispatch helper.
    _run,  # pyright: ignore[reportPrivateUsage]  # Shared dispatch helper.
    _read_kv_file,  # pyright: ignore[reportPrivateUsage]  # Shared dispatch helper.
    _rehydrate_larch_triplet,  # pyright: ignore[reportPrivateUsage]  # Shared dispatch helper.
    _rehydrate_plugin_root,  # pyright: ignore[reportPrivateUsage]  # Shared dispatch helper.
    _run_cli_forward,  # pyright: ignore[reportPrivateUsage]  # Shared dispatch helper.
)


def _run_larch(argv: list[str]) -> subprocess.CompletedProcess[str]:
    """Run one Rust-owned verb through the verified bootstrap script."""
    return _run(argv)


_TRUTHY = frozenset(
    {"1", "true", "TRUE", "True", "yes", "YES", "Yes", "on", "ON", "On"}
)


def _should_restore_finalize(implement_tmpdir: Path) -> bool:
    ship_state = implement_tmpdir / "ship-pr-state.sh"
    if not ship_state.is_file():
        return False
    finalize_state = implement_tmpdir / "finalize-state.sh"
    if not finalize_state.is_file():
        return True
    ship_stall = _read_kv_file(
        path=ship_state,
        key="STALL_TRACKING",
        default="false",
    )
    ship_bail = _read_kv_file(
        path=ship_state,
        key="BAIL_NEEDS_USER_INPUT",
        default="false",
    )
    ship_step = _read_kv_file(path=ship_state, key="STALL_STEP", default="")
    final_step = _read_kv_file(
        path=finalize_state,
        key="STALL_STEP",
        default="",
    )
    if ship_stall in _TRUTHY or ship_bail in _TRUTHY:
        return True
    return bool(ship_step) and ship_step != final_step


def _terminalization_record_valid(implement_tmpdir: Path) -> bool:
    record = implement_tmpdir / ".run-log-terminalized"
    if not record.is_file() or record.is_symlink():
        return False
    return (
        _read_kv_file(
            path=record,
            key="RUN_LOG_TERMINALIZED",
            default="false",
        )
        == "true"
        and _read_kv_file(
            path=record,
            key="LIFECYCLE_TERMINALIZED",
            default="false",
        )
        == "true"
    )


def step_19_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-19")
    _ = parser.add_argument("--implement-tmpdir", default="")
    args = parser.parse_args(argv)
    raw_tmpdir = args.implement_tmpdir or os.environ.get(
        config.ENV_IMPLEMENT_TMPDIR,
        "",
    )
    if not raw_tmpdir:
        print(
            "implement step-19: --implement-tmpdir is required or "
            "IMPLEMENT_TMPDIR must be set",
            file=sys.stderr,
        )
        return 2
    implement_tmpdir = Path(raw_tmpdir)
    os.environ[config.ENV_IMPLEMENT_TMPDIR] = str(implement_tmpdir)
    plugin_root = _rehydrate_plugin_root(implement_tmpdir)
    if not plugin_root.is_dir():
        print(f"step-19: CLAUDE_PLUGIN_ROOT not found: {plugin_root}", file=sys.stderr)
        return 2
    _rehydrate_larch_triplet(implement_tmpdir)
    if not _terminalization_record_valid(implement_tmpdir):
        print(
            "Step 19: cleanup refused because Step 18 run-log "
            "terminalization is not recorded.",
            file=sys.stderr,
        )
        _emit_kv(key="CLEANUP_BLOCKED", value="run-log-not-terminalized")
        return config.EXIT_INTERNAL_ERROR

    if _should_restore_finalize(implement_tmpdir):
        restore = _run_larch(
            [
                str(_larch_entrypoint()),
                "session",
                "restore-finalize-state",
                "--implement-tmpdir",
                str(implement_tmpdir),
            ]
        )
        if restore.returncode != 0:
            print(
                "**⚠ Step 19: restore-finalize-state failed; proceeding to teardown.**",
                file=sys.stderr,
            )

    claude_pid = os.environ.get("LARCH_CLAUDE_PID") or str(os.getppid())
    _ = _run_larch(
        [
            str(_larch_entrypoint()),
            "session",
            "clear-implement-pointer",
            "--claude-pid",
            claude_pid,
        ]
    )
    return _run_cli_forward(
        [
            "implement-finalize",
            "teardown",
            "--state-file",
            str(implement_tmpdir / "finalize-state.sh"),
            "--implement-tmpdir",
            str(implement_tmpdir),
        ]
    )
