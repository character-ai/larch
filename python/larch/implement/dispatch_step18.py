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
from larch.errors import ShipError
from larch.issue import execution_issues
from larch.state import finalize
from larch.implement.dispatch_leg import _run_cli_capture
from larch.state._tokens import _abandoned_checks_bgjob_stall_step


_TERMINAL_SHIPPING_REFUSAL_REASON = "step18-terminal-shipping-without-pr"
_TERMINAL_SHIPPING_REFUSAL_ENTRY = (
    "- **Step 18 terminal gate**: refused terminal `shipping` without PR evidence; "
    "preserved the session for stall recovery."
)


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
    abandoned_checks_bgjob: str

    def any_active(self) -> bool:
        return any(
            _stall_layer_active(value)
            for value in (self.memory, self.disk, self.finalize, self.session, self.abandoned_checks_bgjob)
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
        abandoned_checks_bgjob="true" if _abandoned_checks_bgjob_stall_step(implement_tmpdir) else "false",
    )


def _emit_stall_layers(layers: StallLayers) -> None:
    _emit_kv(key="STALL_TRACKING_MEMORY", value=layers.memory)
    _emit_kv(key="STALL_TRACKING_DISK", value=layers.disk)
    _emit_kv(key="STALL_TRACKING_FINALIZE", value=layers.finalize)
    _emit_kv(key="STALL_TRACKING_SESSION", value=layers.session)
    _emit_kv(key="STALL_TRACKING_ABANDONED_MARKER", value=layers.abandoned_checks_bgjob)


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


def _is_terminal_shipping_without_pr(normalized: dict[str, str]) -> bool:
    return (
        normalized.get("IMPLEMENT_NORMALIZED_OUTCOME") == "shipping"
        and not normalized.get("IMPLEMENT_PR_NUMBER", "").strip()
    )


def _record_terminal_shipping_refusal(*, implement_tmpdir: Path) -> bool:
    """Persist the terminal-gate refusal before returning a hard failure.

    ``shipping`` is only valid for a committed, pre-PR snapshot.  Once Step 18
    starts terminal finalization, retaining that label would otherwise permit a
    teardown that loses the session needed to recover the failed ship attempt.
    """
    state_path = implement_tmpdir / "finalize-state.sh"
    if state_path.is_symlink():
        return False
    try:
        state: dict[str, str] = finalize.read_finalize_state(state_path)
        state.update(
            {
                "BAIL_REASON": _TERMINAL_SHIPPING_REFUSAL_REASON,
                "EXIT_CODE": str(config.EXIT_INTERNAL_ERROR),
                "PHASE": "stalled",
                "STALL_STEP": "8",
                "STALL_TRACKING": "true",
                "STEP18_GATE_REFUSAL": _TERMINAL_SHIPPING_REFUSAL_REASON,
            }
        )
        finalize.write_finalize_state_merged(path=state_path, data=state)
        persisted: dict[str, str] = finalize.read_finalize_state(state_path)
        expected = {
            "BAIL_REASON": _TERMINAL_SHIPPING_REFUSAL_REASON,
            "EXIT_CODE": str(config.EXIT_INTERNAL_ERROR),
            "PHASE": "stalled",
            "STALL_STEP": "8",
            "STALL_TRACKING": "true",
            "STEP18_GATE_REFUSAL": _TERMINAL_SHIPPING_REFUSAL_REASON,
        }
        if any(persisted.get(key) != value for key, value in expected.items()):
            return False
        issue_log = implement_tmpdir / "execution-issues.md"
        execution_issues.append_execution_issue(
            issue_log,
            category="Tool Failures",
            entry=_TERMINAL_SHIPPING_REFUSAL_ENTRY,
        )
        return _TERMINAL_SHIPPING_REFUSAL_ENTRY in issue_log.read_text(encoding="utf-8")
    except (OSError, ShipError):
        return False


def step_18_gate_finalize_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-18-gate-finalize")
    parser.add_argument("--implement-tmpdir", default="")
    parser.add_argument("--stall-tracking-memory", default="")
    parser.add_argument("--step17-emitted", choices=("true", "false"), default="false")
    args = parser.parse_args(argv)
    raw_tmpdir = args.implement_tmpdir or os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    if not raw_tmpdir:
        print("implement step-18-gate-finalize: --implement-tmpdir is required or IMPLEMENT_TMPDIR must be set", file=sys.stderr)
        return 2
    implement_tmpdir = Path(raw_tmpdir)
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

    print("⏩ 18a: stall recovery: no stall detected")
    normalized = _normalize_outcome_for_step18(implement_tmpdir, memory_layer=layers.memory, env=env)
    if _is_terminal_shipping_without_pr(normalized):
        persisted = _record_terminal_shipping_refusal(implement_tmpdir=implement_tmpdir)
        _emit_kv(key="STALL_RECOVERY_REQUIRED", value="true" if persisted else "unknown")
        _emit_kv(key="TERMINAL_FINALIZE_REFUSED", value="true")
        _emit_kv(key="STATUS", value="blocked")
        _emit_kv(key="OUTCOME", value="stalled")
        _emit_kv(key="NEXT_ACTION", value="tool-failure")
        if not persisted:
            print("implement step-18-gate-finalize: cannot persist terminal shipping refusal", file=sys.stderr)
        return config.EXIT_INTERNAL_ERROR

    _emit_kv(key="STALL_RECOVERY_REQUIRED", value="false")

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
