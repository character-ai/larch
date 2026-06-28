"""State file management (clear and seed stall state) for stall recovery."""

# pyright: reportUnusedCallResult=false
# pyright: reportPrivateUsage=false
# pyright: reportUnusedFunction=false

from __future__ import annotations

import argparse
import contextlib
import os
from collections.abc import Mapping
from pathlib import Path

from larch.state._tokens import (
    _safe_phase_value,
    _safe_step_value,
    _state_file_syntax_ok,
    emit,
    read_kv,
)


def _state_layer_paths(tmpdir: Path) -> list[Path]:
    return [tmpdir / name for name in ("ship-pr-state.sh", "finalize-state.sh", "session-env.sh")]


def _rewrite_state_keys(*, path: Path, updates: Mapping[str, str]) -> bool:
    if path.is_symlink() or not path.is_file() or not os.access(path, os.W_OK):
        return False
    existing: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            existing[key] = value
    existing.update(updates)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text("".join(f"{key}={value}\n" for key, value in existing.items()), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        with contextlib.suppress(OSError):
            tmp.unlink()
        return False
    return True


def clear_stall(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    for name in ("stall-recovery-classification.env", "stall-recovery-issue.env"):
        with contextlib.suppress(OSError):
            (tmpdir / name).unlink()
    present = False
    for path in _state_layer_paths(tmpdir):
        if path.is_symlink() and not path.exists():
            emit(key="CLEARED", value="false")
            return 3
        if not path.exists():
            continue
        present = True
        if path.is_symlink() or not path.is_file() or not os.access(path, os.R_OK | os.W_OK):
            emit(key="CLEARED", value="false")
            return 3
        if not _state_file_syntax_ok(path):
            emit(key="CLEARED", value="false")
            return 3
    if not present:
        emit(key="CLEARED", value="true")
        return 0
    for path in _state_layer_paths(tmpdir):
        if not path.is_file():
            continue
        if not _rewrite_state_keys(path=path, updates={
                "STALL_TRACKING": "false",
                "STALL_STEP": "",
                "BAIL_REASON": "",
                "IMPLEMENT_BAIL_REASON": "",
                "EXIT_CODE": "unknown",
            }):
            emit(key="CLEARED", value="false")
            return 1
        if read_kv(path=path, key="STALL_TRACKING") != "false" or read_kv(path=path, key="STALL_STEP") != "":
            emit(key="CLEARED", value="false")
            return 1
    emit(key="CLEARED", value="true")
    return 0


def seed_terminal_state(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    state = tmpdir / "ship-pr-state.sh"
    stall_step_arg = getattr(args, "stall_step", "") or getattr(args, "step", "") or ""
    phase_arg = getattr(args, "phase", "") or ""
    if state.is_symlink() and not state.exists():
        emit(key="SEEDED", value="false")
        return 3
    if state.is_file() and not state.is_symlink() and not _state_file_syntax_ok(state):
        emit(key="SEEDED", value="false")
        return 3
    seed_mode = ""
    step = _safe_step_value(stall_step_arg or read_kv(path=state, key="STALL_STEP", default="8") or "8")
    phase = _safe_phase_value(phase_arg or read_kv(path=state, key="PHASE", default="ci-initial") or "ci-initial")
    if stall_step_arg:
        step = _safe_step_value(stall_step_arg)
    if phase_arg:
        phase = _safe_phase_value(phase_arg)
    if state.is_file() and state.stat().st_size > 0 and any("=" in line for line in state.read_text(encoding="utf-8", errors="replace").splitlines()):
        seed_mode = "rewrite"
        if not _rewrite_state_keys(path=state, updates={"STALL_TRACKING": "true", "STALL_STEP": step, "PHASE": phase}):
            emit(key="SEEDED", value="false")
            return 1
    else:
        seed_mode = "seed"
        tmpdir.mkdir(parents=True, exist_ok=True)
        content = {
            "PHASE": phase,
            "STALL_TRACKING": "true",
            "STALL_STEP": step,
            "BAIL_REASON": "",
            "BAIL_FAILURE_DETAIL_LOG": "",
            "EXIT_CODE": "4",
        }
        tmp = state.with_suffix(state.suffix + ".tmp")
        try:
            tmp.write_text("".join(f"{key}={value}\n" for key, value in content.items()), encoding="utf-8")
            tmp.replace(state)
        except OSError:
            emit(key="SEEDED", value="false")
            return 1
    if read_kv(path=state, key="STALL_TRACKING") != "true":
        emit(key="SEEDED", value="false")
        return 1
    emit(key="SEEDED", value="true")
    emit(key="SEED_MODE", value=seed_mode)
    return 0
