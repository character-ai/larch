"""Terminal state and token validation for stall recovery."""

# pyright: reportUnusedCallResult=false
# pyright: reportPrivateUsage=false
# pyright: reportUnusedFunction=false

from __future__ import annotations

import argparse
import re
from pathlib import Path

from larch.state._tokens import (
    _COMMON_PHASES,
    _GENERIC_PHASES,
    _reject_rawish_terminal_value,
    _reject_rawish_token_value,
    _safe_bail_reason_value,
    _safe_outcome,
    _safe_source_script_value,
    _safe_step,
    _safe_token,
    _validate_tmpdir_local_file,
    emit,
)

_TERMINAL_STATE_ALLOWED_KEYS = {
    "DESIGN_FAILURE_VERSION", "DESIGN_FAILURE_KIND", "FAILURE_OUTCOME", "SUMMARY_OUTCOME",
    "STALL_STEP", "PHASE", "SITE", "TRIGGER", "BAIL_REASON", "EXIT_CODE",
    "FAILURE_DETAIL_LOG", "SOURCE_SCRIPT", "ROOT_CAUSE_HINT", "OCCURRED_AT", "EVIDENCE_REF",
}
_TERMINAL_STATE_REQUIRED_KEYS = {
    "DESIGN_FAILURE_VERSION", "DESIGN_FAILURE_KIND", "FAILURE_OUTCOME",
    "STALL_STEP", "PHASE", "SITE", "TRIGGER", "BAIL_REASON", "EXIT_CODE",
    "FAILURE_DETAIL_LOG", "SOURCE_SCRIPT",
}


def validate_token(args: argparse.Namespace) -> int:
    token = args.token or ""
    kind = getattr(args, "token_kind", "") or ""
    profile = getattr(args, "profile", "implement") or "implement"
    generic = profile == "generic"
    if not token or _reject_rawish_token_value(token):
        emit(key="TOKEN_VALID", value="false")
        return 1
    if kind == "bail":
        valid = _safe_bail_reason_value(token, generic=generic)
    elif kind:
        valid = _safe_token(kind=kind, value=token, generic=generic)
    else:
        valid = True
    if kind and not valid:
        emit(key="TOKEN_VALID", value="false")
        return 1
    emit(key="TOKEN_VALID", value="true")
    return 0


def _terminal_state_value_valid(*, key: str, value: str, tmpdir: Path, generic: bool) -> bool:
    if key == "DESIGN_FAILURE_VERSION":
        return value == "1"
    if key == "DESIGN_FAILURE_KIND":
        return value == "terminal"
    if key in {"FAILURE_OUTCOME", "SUMMARY_OUTCOME"}:
        return _safe_outcome(value)
    if key == "STALL_STEP":
        return _safe_step(value, generic=generic)
    if key == "PHASE":
        return value in _COMMON_PHASES or (generic and value in _GENERIC_PHASES)
    if key == "SITE":
        return _safe_token(kind="site", value=value, generic=generic)
    if key == "TRIGGER":
        return _safe_token(kind="trigger", value=value, generic=generic)
    if key == "BAIL_REASON":
        return _safe_bail_reason_value(value, generic=generic)
    if key == "EXIT_CODE":
        return value == "unknown" or (value.isdigit() and re.fullmatch(r"[0-9]+", value) is not None)
    if key == "FAILURE_DETAIL_LOG":
        if not value:
            return True
        return _validate_tmpdir_local_file(tmpdir=tmpdir, file_path=Path(value))
    if key == "SOURCE_SCRIPT":
        return _safe_source_script_value(value, generic=generic)
    if key == "ROOT_CAUSE_HINT":
        return not value or value in {"larch-defect", "environment", "operator-action"}
    if key in {"OCCURRED_AT", "EVIDENCE_REF"}:
        return not value or not _reject_rawish_terminal_value(value)
    return False


def _validated_terminal_state_values(*, tmpdir: Path, state_file: Path, generic: bool) -> dict[str, str] | None:
    if not tmpdir.is_dir() or not state_file.is_file():
        return None
    if not _validate_tmpdir_local_file(tmpdir=tmpdir, file_path=state_file):
        return None
    found: dict[str, str] = {}
    for raw in state_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            return None
        k, v = line.split("=", 1)
        if k not in _TERMINAL_STATE_ALLOWED_KEYS:
            return None
        found[k] = v
    for required in _TERMINAL_STATE_REQUIRED_KEYS:
        if required not in found:
            return None
        if required != "FAILURE_DETAIL_LOG" and not found[required]:
            return None
    for key, value in found.items():
        if key == "FAILURE_DETAIL_LOG":
            if not _terminal_state_value_valid(key=key, value=value, tmpdir=tmpdir, generic=generic):
                return None
            continue
        if _reject_rawish_terminal_value(value):
            return None
        if not _terminal_state_value_valid(key=key, value=value, tmpdir=tmpdir, generic=generic):
            return None
    return found


def validate_terminal_state(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    profile = getattr(args, "profile", "implement") or "implement"
    generic = profile == "generic"
    state_file = Path(getattr(args, "primary_state_file", None) or tmpdir / "design-failure-terminal-state.env")
    if _validated_terminal_state_values(tmpdir=tmpdir, state_file=state_file, generic=generic) is None:
        emit(key="VALID", value="false")
        return 1
    emit(key="VALID", value="true")
    return 0
