# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalMemberAccess=false, reportPrivateUsage=false
"""Cursor auth helpers plus thin Rust CLI wrappers for reviewer availability."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import cast

from larch.core import config
from larch import io as larch_io
from larch.core.proc import ProcRunner
from larch.core.repo_roots import larch_entrypoint

from larch.agents._types import (
    _CURSOR_AUTH_MAX_ATTEMPTS,
    CURSOR_PREREAD_FAIL_MSG,
    AuthVerdict,
    CheckReviewersResult,
    CodexGateDetail,
    CodexGateSignal,
    DegradedToolsResult,
    _err,
    _env_int,
)
from larch.agents._launch_failure import resolve_model_args
from larch.agents._run_external import (
    external_startup_lock_acquire,
    external_startup_lock_release_after,
    _codex_env_key_enabled,
)


def cursor_auth_preflight(*, caller: str = "agent cursor-auth-preflight") -> AuthVerdict:
    raw_key = os.environ.get("CURSOR_API_KEY", "")
    key = raw_key.strip()
    if not key or "\n" in raw_key or "\r" in raw_key:
        os.environ.pop("CURSOR_API_KEY", None)
    if "\n" in raw_key or "\r" in raw_key:
        key = ""
    if key:
        os.environ["CURSOR_API_KEY"] = key
        return AuthVerdict(ok=True, rc=0)
    uname_out = os.environ.get("LIB_CURSOR_AUTH_TEST_UNAME", "") if os.environ.get("LARCH_LIB_CURSOR_AUTH_TEST_MODE") == "1" else ""
    if not uname_out:
        uname_out = platform.system() or "unknown"
    if uname_out != "Darwin":
        return AuthVerdict(ok=True, rc=0)

    seq = os.environ.get("LIB_CURSOR_AUTH_TEST_SECURITY_RC_SEQ", "") if os.environ.get("LARCH_LIB_CURSOR_AUTH_TEST_MODE") == "1" else ""
    seq_values = seq.split(",") if seq else []
    test_rc = os.environ.get("LIB_CURSOR_AUTH_TEST_SECURITY_RC", "") if os.environ.get("LARCH_LIB_CURSOR_AUTH_TEST_MODE") == "1" else ""
    last_rc = seq_values[-1] if seq_values else test_rc
    state = external_startup_lock_acquire(tool="cursor")
    try:
        for attempt in range(_CURSOR_AUTH_MAX_ATTEMPTS):
            token = ""
            if seq_values:
                rc_text = seq_values[attempt] if attempt < len(seq_values) else last_rc
                rc = int(rc_text or "1")
                if rc == 0:
                    token = os.environ.get("LIB_CURSOR_AUTH_TEST_PREREAD_TOKEN", "").strip()
            elif test_rc:
                rc = int(test_rc)
                if rc == 0:
                    token = os.environ.get("LIB_CURSOR_AUTH_TEST_PREREAD_TOKEN", "").strip()
            else:
                # Probe readability with -w, not just existence (#5518): on macOS an
                # access-controlled keychain entry can pass an existence check yet deny
                # the -w read without UI interaction, so an existence-only preflight
                # reports green while Cursor's own in-process read fails (exit 1, 0 bytes).
                # Reading here makes the preflight fail closed when the token is present
                # but unreadable. Require a non-empty stripped token, not just exit 0.
                result = subprocess.run(
                    [shutil.which("security") or "/usr/bin/security", "find-generic-password", "-a", "cursor-user", "-s", "cursor-access-token", "-w"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                rc = result.returncode
                token = result.stdout.strip() if rc == 0 else ""
            if rc == 0 and token:
                return AuthVerdict(ok=True, rc=0)
            if attempt < _CURSOR_AUTH_MAX_ATTEMPTS - 1:
                time.sleep(0.2)
    finally:
        external_startup_lock_release_after(state=state, delay=0)
    msg = (
        f"{caller}: cursor-auth-preflight failed.\n"
        "  CURSOR_API_KEY is unset/empty AND the `cursor-user` / `cursor-access-token`\n"
        "  keychain entry is missing or unreadable (-w denied) on this Darwin host.\n"
        "  Cursor would otherwise emit the cryptic `Security process exited with code: 45`.\n\n"
        "  See docs/installation-and-setup.md (Cursor section) for setup.\n\n"
        "  To fix, choose one:\n"
        "    (a) export CURSOR_API_KEY=<your-cursor-api-key>\n"
        "    (b) security delete-generic-password -a cursor-user 2>/dev/null; cursor login"
    )
    return AuthVerdict(ok=False, rc=2, message=msg)


def cursor_preread_service_token() -> bool:
    raw_key = os.environ.get("CURSOR_API_KEY", "")
    key = raw_key.strip()
    if key and "\n" not in raw_key and "\r" not in raw_key:
        return True
    uname_out = os.environ.get("LIB_CURSOR_AUTH_TEST_UNAME", "") if os.environ.get("LARCH_LIB_CURSOR_AUTH_TEST_MODE") == "1" else ""
    if not uname_out:
        uname_out = platform.system() or "unknown"
    if uname_out != "Darwin":
        return True
    state = external_startup_lock_acquire(tool="cursor")
    read_failed = False
    token = ""
    try:
        if os.environ.get("LARCH_LIB_CURSOR_AUTH_TEST_MODE") == "1":
            token = os.environ.get("LIB_CURSOR_AUTH_TEST_PREREAD_TOKEN", "").strip()
            read_failed = not token
        else:
            result = subprocess.run(
                [shutil.which("security") or "/usr/bin/security", "find-generic-password", "-a", "cursor-user", "-s", "cursor-access-token", "-w"],
                capture_output=True,
                text=True,
                check=False,
            )
            token = result.stdout.strip() if result.returncode == 0 else ""
            read_failed = result.returncode != 0 or not token
    finally:
        external_startup_lock_release_after(state=state, delay=0)
    if token:
        os.environ["CURSOR_API_KEY"] = token
        return True
    if read_failed:
        # Surface the silent token-read drop (#5518) instead of proceeding with an empty
        # CURSOR_API_KEY: the entry may exist (so the old existence-only preflight passed)
        # while the -w read is denied, which lets the Cursor slot auth-fail in-process and
        # return a canned, un-reviewed response that the panel scores as clean.
        _err(CURSOR_PREREAD_FAIL_MSG)
    return False


def cursor_auth_export_env() -> None:
    # Suppress cursor-agent's deeplink/browser opener (`open <cursor://…>`) so it
    # never launches the Cursor.app "Composer" GUI window in headless larch lanes
    # (issue #5797). All cursor lanes call this pre-spawn and the child inherits
    # os.environ, so this single assignment covers every cursor subprocess.
    os.environ["NO_OPEN_BROWSER"] = "1"
    raw_key = os.environ.get("CURSOR_API_KEY", "")
    key = raw_key.strip()
    if "\n" in key or "\r" in key:
        os.environ.pop("CURSOR_API_KEY", None)
    elif key:
        os.environ["CURSOR_API_KEY"] = key
    else:
        os.environ.pop("CURSOR_API_KEY", None)



def _probe_tmpdir() -> Path:
    return Path(os.environ.get("TMPDIR") or "/tmp")  # noqa: S108 - parity with Bash TMPDIR fallback.


def _probe_user() -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]", "", os.environ.get("USER", ""))
    return sanitized or "larch"


def _probe_stamp_path(kind: str) -> Path:
    return _probe_tmpdir() / f"larch-{kind}-present-{_probe_user()}.stamp"


def _resolved_codex_review_model() -> str:
    argv = resolve_model_args("codex", codex_role="review").argv
    return next((argv[index + 1] for index, token in enumerate(argv[:-1]) if token == "-m"), config.CODEX_REVIEW_MODEL_DEFAULT)


def _codex_probe_identity(model: str) -> str:
    auth_mode = "env-key" if _codex_env_key_enabled() else "login"
    digest = hashlib.sha256(model.encode("utf-8")).hexdigest()[:16]
    return f"codex-{auth_mode}-{digest}"


def _codex_gate_detail_path(identity: str) -> Path:
    return _probe_tmpdir() / f"larch-{identity}-gate-{_probe_user()}.json"


def _parse_codex_gate_detail(*, payload: object, identity: str) -> CodexGateDetail | None:
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != 1:
        return None
    if payload.get("identity") != identity:
        return None
    model = payload.get("model")
    signal = payload.get("signal")
    message = payload.get("message")
    if not isinstance(model, str) or not isinstance(signal, str) or not isinstance(message, str):
        return None
    if signal not in {"model-metadata-not-found", "newer-codex-required"}:
        return None
    return CodexGateDetail(model=model, signal=cast("CodexGateSignal", signal), message=message)


def _read_codex_gate_detail(*, identity: str, max_age: int) -> CodexGateDetail | None:
    path = _codex_gate_detail_path(identity)
    try:
        if path.is_symlink() or not path.is_file():
            return None
        detail_stat = path.stat()
        age = time.time() - detail_stat.st_mtime
        if age < 0 or age > max_age:
            return None
        stamp = _probe_stamp_path(identity)
        if stamp.is_file() and not stamp.is_symlink() and detail_stat.st_mtime_ns < stamp.stat().st_mtime_ns:
            return None
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return _parse_codex_gate_detail(payload=payload, identity=identity)


def _codex_gate_detail_max_age() -> int:
    ttl = _env_int(name="LARCH_PROBE_TTL_SECONDS", default=60)
    negative_ttl = _env_int(name="LARCH_PROBE_NEGATIVE_TTL_SECONDS", default=0)
    immediate = config.CODEX_PROBE_GATE_IMMEDIATE_TTL_SEC
    return max(negative_ttl, ttl if ttl > 0 else immediate)


def _current_codex_gate_detail() -> CodexGateDetail | None:
    try:
        model = _resolved_codex_review_model()
    except ValueError:
        return None
    identity = _codex_probe_identity(model)
    return _read_codex_gate_detail(identity=identity, max_age=_codex_gate_detail_max_age())


def _bool_kv(stdout: str, key: str) -> bool:
    return larch_io.kv_value(text=stdout, key=key, duplicate_policy="first").strip().lower() == "true"


def check_reviewers(
    *,
    skip_codex_probe: bool = False,
    skip_cursor_probe: bool = False,
    probe_timeout_seconds: int | None = None,
    env: dict[str, str] | None = None,
) -> CheckReviewersResult:
    """Shell out to the Rust `agent check-reviewers` owner and parse the KV envelope."""
    cmd = [str(larch_entrypoint(Path(__file__).resolve().parents[3])), "agent", "check-reviewers"]
    if skip_codex_probe:
        cmd.append("--skip-codex-probe")
    if skip_cursor_probe:
        cmd.append("--skip-cursor-probe")
    run_env = {**os.environ, **(env or {})}
    if probe_timeout_seconds is not None:
        run_env["LARCH_PROBE_TIMEOUT_SECONDS"] = str(probe_timeout_seconds)
    result = ProcRunner().run(cmd, env=run_env)
    stdout = result.stdout or ""
    present_false = not _bool_kv(stdout, "CODEX_PRESENT")
    gate_detail = _current_codex_gate_detail() if present_false else None
    return CheckReviewersResult(
        codex_binary_found=_bool_kv(stdout, "CODEX_BINARY_FOUND"),
        cursor_binary_found=_bool_kv(stdout, "CURSOR_BINARY_FOUND"),
        codex_present=_bool_kv(stdout, "CODEX_PRESENT"),
        cursor_present=_bool_kv(stdout, "CURSOR_PRESENT"),
        codex_probe_timed_out=_bool_kv(stdout, "CODEX_PROBE_TIMED_OUT"),
        cursor_probe_timed_out=_bool_kv(stdout, "CURSOR_PROBE_TIMED_OUT"),
        codex_gate_detail=gate_detail,
    )


EXTERNAL_TOOL_NAMES: tuple[str, ...] = ("codex", "cursor")


def external_tool_names() -> tuple[str, ...]:
    return EXTERNAL_TOOL_NAMES


def degraded_tools_result(
    *,
    codex_binary_found: str,
    codex_present: str,
    cursor_binary_found: str,
    cursor_present: str,
    skill: str,
) -> DegradedToolsResult:
    """Shell out to the Rust `agent degraded-tools-gate` owner and parse the envelope."""
    cmd = [
        str(larch_entrypoint(Path(__file__).resolve().parents[3])),
        "agent",
        "degraded-tools-gate",
        "--codex-binary-found",
        codex_binary_found,
        "--codex-present",
        codex_present,
        "--cursor-binary-found",
        cursor_binary_found,
        "--cursor-present",
        cursor_present,
        "--skill",
        skill,
    ]
    result = ProcRunner().run(cmd)
    stdout = result.stdout or ""
    explanation: list[str] = []
    capturing = False
    for line in stdout.splitlines():
        if line == "DEGRADED_EXPLANATION_BEGIN":
            capturing = True
            continue
        if line == "DEGRADED_EXPLANATION_END":
            capturing = False
            continue
        if capturing:
            explanation.append(line)
    return DegradedToolsResult(
        degraded=larch_io.kv_value(text=stdout, key="DEGRADED", duplicate_policy="first").strip().lower() == "true",
        codex_state=larch_io.kv_value(text=stdout, key="CODEX_STATE", duplicate_policy="first").strip(),
        cursor_state=larch_io.kv_value(text=stdout, key="CURSOR_STATE", duplicate_policy="first").strip(),
        both_down=larch_io.kv_value(text=stdout, key="BOTH_DOWN", duplicate_policy="first").strip().lower() == "true",
        presence_input_empty=larch_io.kv_value(text=stdout, key="PRESENCE_INPUT_EMPTY", duplicate_policy="first").strip().lower() == "true",
        explanation=tuple(explanation),
    )
