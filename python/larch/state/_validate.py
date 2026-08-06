"""Terminal state and token validation for stall recovery."""

# pyright: reportUnusedCallResult=false
# pyright: reportPrivateUsage=false
# pyright: reportUnusedFunction=false

from __future__ import annotations

import re
from pathlib import Path

from larch import io as larch_io
from larch.state._tokens import (
    _COMMON_PHASES,
    _GENERIC_PHASES,
    _reject_rawish_terminal_value,
    _safe_bail_reason_value,
    _safe_outcome,
    _safe_source_script_value,
    _safe_step,
    _safe_token,
    _validate_tmpdir_local_file,
)

_TERMINAL_STATE_ALLOWED_KEYS = {
    "DESIGN_FAILURE_VERSION", "DESIGN_FAILURE_KIND", "FAILURE_OUTCOME", "SUMMARY_OUTCOME",
    "STALL_STEP", "PHASE", "SITE", "TRIGGER", "BAIL_REASON", "EXIT_CODE",
    "FAILURE_DETAIL_LOG", "SOURCE_SCRIPT", "ROOT_CAUSE_HINT", "OCCURRED_AT", "EVIDENCE_REF",
    "PUBLISH_ATTEMPT_ID", "PUBLISH_RC_SOURCE", "LATEST_PHASE", "PLAN_WRITE_OK", "PUBLISH_OK",
    "RENAMED", "LOG_PUBLISH_ATTEMPTED", "LOG_PUBLISH_COMPLETED", "DESIGNED_ADMISSION_READY",
    "PR_URL", "RECOVERY_BRANCH",
}
_TERMINAL_STATE_REQUIRED_KEYS = {
    "DESIGN_FAILURE_VERSION", "DESIGN_FAILURE_KIND", "FAILURE_OUTCOME",
    "STALL_STEP", "PHASE", "SITE", "TRIGGER", "BAIL_REASON", "EXIT_CODE",
    "FAILURE_DETAIL_LOG", "SOURCE_SCRIPT",
}


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
    if key == "PUBLISH_ATTEMPT_ID":
        return re.fullmatch(r"[A-Za-z0-9._-]{8,128}", value) is not None
    if key == "PUBLISH_RC_SOURCE":
        return value in {"returned", "exception"}
    if key == "LATEST_PHASE":
        return re.fullmatch(r"[a-z0-9-]+", value) is not None
    if key in {"PLAN_WRITE_OK", "PUBLISH_OK", "RENAMED", "LOG_PUBLISH_ATTEMPTED", "LOG_PUBLISH_COMPLETED", "DESIGNED_ADMISSION_READY"}:
        return value in {"true", "false"}
    if key == "PR_URL":
        return re.fullmatch(r"https://github\.com/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+/pull/[1-9][0-9]*", value) is not None
    if key == "RECOVERY_BRANCH":
        return re.fullmatch(r"[A-Za-z0-9._/-]+", value) is not None and ".." not in value and not value.startswith(("/", "-"))
    if key in {"OCCURRED_AT", "EVIDENCE_REF"}:
        return not value or not _reject_rawish_terminal_value(value)
    return False


def _validated_terminal_state_values(*, tmpdir: Path, state_file: Path, generic: bool) -> dict[str, str] | None:
    if not tmpdir.is_dir() or not state_file.is_file():
        return None
    if not _validate_tmpdir_local_file(tmpdir=tmpdir, file_path=state_file):
        return None
    normalized_lines: list[str] = []
    for raw in larch_io.read_text(state_file, errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            return None
        normalized_lines.append(line)
    parsed = larch_io.parse_kv(
        "\n".join(normalized_lines),
        duplicate_policy="all",
        skip_comments=True,
    )
    if any(key not in _TERMINAL_STATE_ALLOWED_KEYS or len(values) != 1 for key, values in parsed.items()):
        return None
    found = {key: values[0] for key, values in parsed.items()}
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
        if key not in {"PR_URL", "RECOVERY_BRANCH"} and _reject_rawish_terminal_value(value):
            return None
        if not _terminal_state_value_valid(key=key, value=value, tmpdir=tmpdir, generic=generic):
            return None
    return found
