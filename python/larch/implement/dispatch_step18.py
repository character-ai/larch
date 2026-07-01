# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""Step 18 gate/finalize: stall layer resolution and final cleanup."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from larch.core import config
from larch.implement.dispatch_helpers import (
    _emit_kv,
    _parse_kv,
    _read_kv_file,
    _rehydrate_larch_triplet,
    _rehydrate_plugin_root,
)
from larch.implement.dispatch_leg import _run_cli_capture
from larch.state._tokens import _abandoned_checks_marker_stall_step


def _stall_layer_active(value: str) -> bool:
    return bool(value) and value != "false"


def _resolve_stall_memory_layer(*, stall_tracking_memory_arg: str, env_stall_tracking: str) -> str:
    if stall_tracking_memory_arg in {"true", "false"}:
        return stall_tracking_memory_arg
    if stall_tracking_memory_arg == "":
        return env_stall_tracking or "false"
    return stall_tracking_memory_arg


def _read_stall_layer_from_file(*, path: Path, key: str, default: str = "false") -> str:
    if not path.is_file():
        return default
    return _read_kv_file(path=path, key=key, default=default)


@dataclass(frozen=True)
class StallLayers:
    memory: str
    disk: str
    finalize: str
    session: str
    abandoned_checks_marker: str

    def any_active(self) -> bool:
        return any(
            _stall_layer_active(value)
            for value in (self.memory, self.disk, self.finalize, self.session, self.abandoned_checks_marker)
        )


def _resolve_stall_layers(implement_tmpdir: Path, *, stall_tracking_memory_arg: str) -> StallLayers:
    return StallLayers(
        memory=_resolve_stall_memory_layer(
            stall_tracking_memory_arg=stall_tracking_memory_arg,
            env_stall_tracking=os.environ.get("STALL_TRACKING", "false"),
        ),
        disk=_read_stall_layer_from_file(path=implement_tmpdir / "ship-pr-state.sh", key="STALL_TRACKING"),
        finalize=_read_stall_layer_from_file(path=implement_tmpdir / "finalize-state.sh", key="STALL_TRACKING"),
        session=_read_stall_layer_from_file(path=implement_tmpdir / "session-env.sh", key="STALL_TRACKING"),
        abandoned_checks_marker="true" if _abandoned_checks_marker_stall_step(implement_tmpdir) else "false",
    )


def _emit_stall_layers(layers: StallLayers) -> None:
    _emit_kv(key="STALL_TRACKING_MEMORY", value=layers.memory)
    _emit_kv(key="STALL_TRACKING_DISK", value=layers.disk)
    _emit_kv(key="STALL_TRACKING_FINALIZE", value=layers.finalize)
    _emit_kv(key="STALL_TRACKING_SESSION", value=layers.session)
    _emit_kv(key="STALL_TRACKING_ABANDONED_MARKER", value=layers.abandoned_checks_marker)


def _normalize_outcome_for_step18(implement_tmpdir: Path, *, memory_layer: str, env: dict[str, str]) -> dict[str, str]:
    result = _run_cli_capture(
        [
            "stall-recovery",
            "normalize-outcome",
            "--implement-tmpdir",
            str(implement_tmpdir),
            "--in-memory-stall-tracking",
            memory_layer,
        ],
        env=env,
    )
    if result.stderr:
        sys.stderr.write(result.stderr)
        sys.stderr.flush()
    if result.stdout:
        sys.stdout.write(result.stdout)
        sys.stdout.flush()
    return _parse_kv(result.stdout if result.returncode == 0 else "")


def step_18_gate_finalize_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-18-gate-finalize")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--stall-tracking-memory", default="")
    parser.add_argument("--step17-emitted", choices=("true", "false"), default="false")
    args = parser.parse_args(argv)
    implement_tmpdir = Path(args.implement_tmpdir)
    os.environ[config.ENV_IMPLEMENT_TMPDIR] = str(implement_tmpdir)
    plugin_root = _rehydrate_plugin_root(implement_tmpdir)
    _rehydrate_larch_triplet(implement_tmpdir)
    env = dict(os.environ)
    env[config.ENV_IMPLEMENT_TMPDIR] = str(implement_tmpdir)
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)

    layers = _resolve_stall_layers(implement_tmpdir, stall_tracking_memory_arg=args.stall_tracking_memory)
    _emit_stall_layers(layers)
    if layers.any_active():
        _emit_kv(key="STALL_RECOVERY_REQUIRED", value="true")
        _emit_kv(key="NEXT_ACTION", value="stall-recovery")
        return 0

    _emit_kv(key="STALL_RECOVERY_REQUIRED", value="false")
    print("⏩ 18a: stall recovery — no stall detected")
    _normalize_outcome_for_step18(implement_tmpdir, memory_layer=layers.memory, env=env)

    # lint-subprocess-via-runner: ok composite must invoke the existing Bash finalize fence verbatim
    child = subprocess.run(
        [
            shutil.which("bash") or "/bin/bash",
            str(implement_tmpdir / "larch-run.sh"),
            "skills/implement/scripts/step-18.sh",
            "--phase",
            "finalize",
            "--step17-emitted",
            args.step17_emitted,
        ],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    if child.stdout:
        sys.stdout.write(child.stdout)
        sys.stdout.flush()
    if child.stderr:
        sys.stderr.write(child.stderr)
        sys.stderr.flush()
    _emit_kv(key="NEXT_ACTION", value="finalize-done")
    return child.returncode
