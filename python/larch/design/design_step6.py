"""Step 6 prelude, cleanup, and main entry for design teardown."""
# pylint: disable=cyclic-import
# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnusedFunction=false, reportPrivateUsage=false

from __future__ import annotations

import contextlib
import sys
from pathlib import Path
from collections.abc import Mapping, Sequence

from larch.bgjob import registry
from larch.core import logging_util
from larch.state import session_env

from larch.design.design_core import (
    DESIGN_BGJOB_STEP5C,
    _CoreUsageError,
    _core_diagnostic,
    _validate_design_tmpdir_arg,
    design_bgjob_result_env_path,
)
from larch.design.design_session import (
    _call_pause_save,
    _design_require_plugin_root,
    _maybe_timing_mark,
    _parse_common_wrapper_args,
    _rehydrate_wrapper_env,
    _touch,
)
from larch.design.design_step2b import _read_simple_env
from larch.design.design_step5c import STEP5C_STATUS_ALLOW_KEYS, STEP6_INFO_ICON


def _read_step5c_status_sidecar(design_tmpdir: Path) -> dict[str, str]:
    return _read_simple_env(path=design_tmpdir / ".design-step5c-status.env", allow=STEP5C_STATUS_ALLOW_KEYS)


def _resolve_design_tmpdir_raw(env: Mapping[str, str]) -> str:
    return env.get("DESIGN_TMPDIR", "")


def _design_tmpdir_path_or_none(design_tmpdir_raw: str) -> Path | None:
    if not design_tmpdir_raw:
        return None
    return Path(design_tmpdir_raw)


def _step6_sidecar_path(design_tmpdir_raw: str) -> Path | None:
    design_tmpdir = _design_tmpdir_path_or_none(design_tmpdir_raw)
    if design_tmpdir is None:
        return None
    return design_tmpdir / ".design-step5c-status.env"


def _step6_in_flight(design_tmpdir_raw: str) -> bool:
    if not design_tmpdir_raw:
        return False
    design_tmpdir = Path(design_tmpdir_raw)
    if (design_tmpdir / ".completed" / "step-5c-terminal").is_file():
        return False
    result_env = design_bgjob_result_env_path(
        design_tmpdir=design_tmpdir,
        step=DESIGN_BGJOB_STEP5C,
    )
    if result_env.is_file() and not result_env.is_symlink():
        return False
    reg_path, entry = registry.read_for(tmpdir=design_tmpdir, step=DESIGN_BGJOB_STEP5C)
    if entry is None:
        return False
    if registry.child_liveness(entry).live or registry.daemon_liveness(entry).live:
        return True
    registry.unlink_entry(reg_path)
    return False


def _step6_emit_prelude_skipped(message: str) -> None:
    logging_util.emit(message)
    logging_util.emit_kv(key="STEP6_PRELUDE_STATUS", value="skipped")


def _step6_emit_cleanup_preserved(message: str) -> None:
    logging_util.emit(message)
    logging_util.emit_kv(key="CLEANUP_STATUS", value="preserved")


def _step6_pause_if_requested(design_tmpdir: Path | None) -> int | None:
    if design_tmpdir is not None and (design_tmpdir / ".pause-requested").is_file():
        return _call_pause_save(design_tmpdir=design_tmpdir)
    return None


def step6_prelude_core(argv: Sequence[str]) -> int:
    try:
        parsed = _parse_common_wrapper_args(argv)
    except ValueError as exc:
        _core_diagnostic(f"design-step6-prelude.sh: {exc}")
        return 2
    env = _rehydrate_wrapper_env(parsed)
    design_tmpdir_raw = _resolve_design_tmpdir_raw(env)
    design_tmpdir = _design_tmpdir_path_or_none(design_tmpdir_raw)

    pause_rc = _step6_pause_if_requested(design_tmpdir)
    if pause_rc is not None:
        return pause_rc
    if _step6_in_flight(design_tmpdir_raw):
        _core_diagnostic("**⚠ Step 6 prelude: design-step5c.sh appears still in-flight; run bgjob wait for design-step5c before Step 6.**")
        return 1
    sidecar = _step6_sidecar_path(design_tmpdir_raw)
    if sidecar is None or not sidecar.is_file() or design_tmpdir is None:
        _step6_emit_prelude_skipped(f"**{STEP6_INFO_ICON} Step 6 prelude: missing Step 5c status sidecar; skipping step-5d write.**")
        return 0

    status = _read_step5c_status_sidecar(design_tmpdir)
    if status.get("PLAN_WRITE_OK", "") != "true":
        _step6_emit_prelude_skipped(f"**{STEP6_INFO_ICON} Step 6 prelude: plan write did not succeed; skipping step-5d write.**")
        return 0
    if status.get("SESSION_ID", "") and status.get("PUBLISH_OK", "") != "true":
        _step6_emit_prelude_skipped(f"**{STEP6_INFO_ICON} Step 6 prelude: publish did not complete; skipping step-5d write.**")
        return 0
    if status.get("CLEANUP_ELIGIBLE", "") == "false":
        _step6_emit_prelude_skipped(f"**{STEP6_INFO_ICON} Step 6 prelude: cleanup not eligible per Step 5c status; skipping step-5d write.**")
        return 0

    _touch(design_tmpdir / ".completed" / "step-5d")
    pause_rc = _step6_pause_if_requested(design_tmpdir)
    if pause_rc is not None:
        return pause_rc
    _maybe_timing_mark(label="design Step 6 — cleanup")
    return 0


def step6_prelude_main(argv: Sequence[str]) -> int:
    try:
        _parse_common_wrapper_args(argv)
    except ValueError as exc:
        print(f"design-step6-prelude.sh: {exc}", file=sys.stderr)
        return 2
    logging_util.quiet_init(argv0="design-step6-prelude.sh")
    return step6_prelude_core(argv)


def step6_cleanup_core(argv: Sequence[str]) -> int:
    try:
        parsed = _parse_common_wrapper_args(argv)
    except ValueError as exc:
        _core_diagnostic(f"design-step6-cleanup.sh: {exc}")
        return 2
    env = _rehydrate_wrapper_env(parsed)
    design_tmpdir_raw = _resolve_design_tmpdir_raw(env)
    design_tmpdir = _design_tmpdir_path_or_none(design_tmpdir_raw)

    pause_rc = _step6_pause_if_requested(design_tmpdir)
    if pause_rc is not None:
        return pause_rc
    if _step6_in_flight(design_tmpdir_raw):
        _core_diagnostic("**⚠ Step 6: design-step5c.sh appears still in-flight; run bgjob wait for design-step5c before Step 6.**")
        return 1
    sidecar = _step6_sidecar_path(design_tmpdir_raw)
    if sidecar is None or not sidecar.is_file() or design_tmpdir is None:
        _step6_emit_cleanup_preserved(f"**{STEP6_INFO_ICON} Step 6: missing Step 5c status sidecar; preserving $DESIGN_TMPDIR for recovery.**")
        return 0

    status = _read_step5c_status_sidecar(design_tmpdir)
    if status.get("PLAN_WRITE_OK", "") != "true":
        _step6_emit_cleanup_preserved(f"**{STEP6_INFO_ICON} Step 6: plan write did not succeed; preserving $DESIGN_TMPDIR.**")
        return 0
    if status.get("STANDALONE_HEAVY_FAILED", "false") == "true":
        _step6_emit_cleanup_preserved(f"**{STEP6_INFO_ICON} Step 6: standalone heavy failed; preserving $DESIGN_TMPDIR.**")
        return 0
    if status.get("SESSION_ID", "") and status.get("PUBLISH_OK", "") != "true":
        _step6_emit_cleanup_preserved(f"**{STEP6_INFO_ICON} Step 6: publish did not complete; preserving $DESIGN_TMPDIR for recovery.**")
        return 0
    if status.get("CLEANUP_ELIGIBLE", "") == "false":
        _step6_emit_cleanup_preserved(f"**{STEP6_INFO_ICON} Step 6: cleanup not eligible per Step 5c status; preserving $DESIGN_TMPDIR.**")
        return 0

    try:
        design_tmpdir = _validate_design_tmpdir_arg(design_tmpdir_raw)
    except _CoreUsageError as exc:
        _core_diagnostic(f"design-step6-cleanup.sh: {exc}")
        return 1
    req = _design_require_plugin_root()
    if req != 0:
        return req
    _touch(design_tmpdir / ".completed" / "step-6")
    return session_env.cleanup_tmpdir_main(["--dir", str(design_tmpdir)])


def step6_cleanup_main(argv: Sequence[str]) -> int:
    try:
        _parse_common_wrapper_args(argv)
    except ValueError as exc:
        print(f"design-step6-cleanup.sh: {exc}", file=sys.stderr)
        return 2
    logging_util.quiet_init(argv0="design-step6-cleanup.sh")
    return step6_cleanup_core(argv)


def step6_main(argv: Sequence[str]) -> int:
    try:
        parsed = _parse_common_wrapper_args(argv)
    except ValueError as exc:
        print(f"design-step6.sh: {exc}", file=sys.stderr)
        return 2
    logging_util.quiet_init(argv0="design-step6.sh")
    env = _rehydrate_wrapper_env(parsed)
    design_tmpdir_raw = _resolve_design_tmpdir_raw(env)
    design_tmpdir = _design_tmpdir_path_or_none(design_tmpdir_raw)
    pause_complete = design_tmpdir / ".pause-save-complete" if design_tmpdir is not None else None
    if pause_complete is not None:
        with contextlib.suppress(FileNotFoundError):
            pause_complete.unlink()

    prelude_rc = step6_prelude_core(argv)
    if prelude_rc != 0:
        return prelude_rc
    if pause_complete is not None and pause_complete.is_file():
        return 0
    return step6_cleanup_core(argv)
