# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalMemberAccess=false, reportPrivateUsage=false, reportUnusedFunction=false
"""Types, constants, and IO utilities shared by all agent launcher modules."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from larch.core import logging_util

_PARSE_RE = re.compile(
    r"invalid json|unexpected token|parse error|jq: error|syntaxerror|"
    r"unmarshal|cannot unmarshal",
    re.IGNORECASE,
)
_REFUSAL_RE = re.compile(
    r"refused to|refusal|denied by policy|policy violation",
    re.IGNORECASE,
)
_QUOTA_RE = re.compile(
    r"usage limit|rate[ _-]?limit|too many requests|quota|429 too many|over your usage",
    re.IGNORECASE,
)
# Window during which the Claude lint-fix / CI subprocess lanes scan stderr for a
# degraded-but-present auth state and fast-fail, instead of burning the full
# timeout budget. See issue #5605 (Claude analogue of the Codex fast-fail #5543).
_CLAUDE_AUTH_FAST_FAIL_WINDOW = 60.0
# Genuine degraded-auth signatures on `claude` stderr: apiKeyHelper failed or
# returned no value. The benign "connectors disabled / takes precedence" message
# is intentionally excluded — it appears on successful runs when ANTHROPIC_API_KEY
# is set (#5677, ~41/50 healthy voters carry it) and must not trigger fast-fail.
# Shared into _AUTH_RE["claude"] below so external_auth_verdict classifies real
# failures as health/auth.
_CLAUDE_DEGRADED_AUTH_RE = re.compile(
    r"apiKeyHelper failed|"
    r"did not return a value",
    re.IGNORECASE,
)
_CLAUDE_STDERR_SCAN_TAIL_BYTES = 65536
_AUTH_RE = {
    "cursor": re.compile(
        r"Password not found|cursor-user|cursor-access-token|keychain.*(not found|failed)|"
        r"([^-]|^)auth[-_ ]?error|authentication (failed|required)|"
        r"Security (process exited with code|command failed)",
        re.IGNORECASE,
    ),
    "codex": re.compile(
        r"auth[-_ ]?error|not logged in|login required|authentication (failed|required)|"
        r"unauthorized|invalid api key",
        re.IGNORECASE,
    ),
    "claude": re.compile(
        r"auth[-_ ]?error|not logged in|login required|authentication (failed|required)|"
        r"unauthorized|invalid api key|api key not found|"
        + _CLAUDE_DEGRADED_AUTH_RE.pattern,
        re.IGNORECASE,
    ),
}
_SAFE_META_PATH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
_CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")
_PLUGIN_ROOT = Path(__file__).resolve().parents[3]
_PY_CLI = _PLUGIN_ROOT / "python" / "cli.py"
_CURSOR_AUTH_MAX_ATTEMPTS = 3
CURSOR_PREREAD_FAIL_RC = 2
CURSOR_PREREAD_FAIL_MSG = (
    "cursor-preread-service-token: cursor-access-token keychain -w read returned no token; "
    "CURSOR_API_KEY left unset (Cursor may fail auth in-process and return a degraded response)."
)
_MAX_CONTEXT_FILES = 20
_MAX_CLAUDE_TIMEOUT = 1800
_DEFAULT_CURSOR_CI_STALL_THRESHOLD = 180
_TOML_CLOSED_STRING_DELIMITER_COUNT = 2
_AUTH_RETRY_RC = 2
_PROBE_NO_RETRY_RC = 3
_CURSOR_PREFLIGHT_AUTH_RC = 2
_CLAUDE_REVIEW_READ_ONLY_PREAMBLE = (
    "HARD CONSTRAINTS — your role is read-only review. "
    "Do not create, edit, delete, or overwrite files. "
    "Do not run Bash, shell, or git commands. "
    "Use only the explicitly granted read-only tools."
)
_CURSOR_DEGRADED_OUTPUT_TOKEN_FLOOR = 1000
_CURSOR_DEGRADED_RESULT_BYTES_CEILING = 500
# Plan-review Cursor slots inline the full plan (#5518 WI1), so input-token work alone
# no longer signals a real review; the no-work floor below catches canned sentinels.
# A genuine Cursor review ingests the prompt (and the files it reads) — thousands of
# input tokens. A slot that never ran inference (e.g. an in-process auth failure, #5518)
# can still exit 0 and return the bare no-issues sentinel, reporting ~0 input work. This
# floor sits far below any real review yet above pure-zero noise, so a no-issues sentinel
# at/below it is treated as degraded without mis-flagging a legitimate clean review.
_CURSOR_NO_WORK_INPUT_TOKEN_FLOOR = 64


@dataclass(frozen=True)
class LaunchFailure:
    failure_class: str
    reason: str


@dataclass(frozen=True)
class TierAttempt:
    tier: str
    wrapper_rc: int
    launcher_exit: int
    failure: LaunchFailure
    failure_log: str | Path | None = None


@dataclass(frozen=True)
class WaterfallResult:
    winning_tier: str | None
    attempts: tuple[TierAttempt, ...]
    short_circuited: bool = False


@dataclass(frozen=True)
class ModelArgResult:
    argv: tuple[str, ...]
    warning: str = ""


@dataclass(frozen=True)
class AuthVerdict:
    ok: bool
    rc: int
    message: str = ""


@dataclass(frozen=True)
class UsageTotals:
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int

    @property
    def uncached_input_tokens(self) -> int:
        return self.input_tokens - self.cached_input_tokens

    @property
    def total_tokens(self) -> int:
        return self.uncached_input_tokens + self.cached_input_tokens + self.output_tokens


@dataclass(frozen=True)
class DegradedToolsResult:
    degraded: bool
    codex_state: str
    cursor_state: str
    both_down: bool
    presence_input_empty: bool
    explanation: tuple[str, ...]


@dataclass(frozen=True)
class RunExternalAgentResult:
    exit_code: int
    output: Path


@dataclass(frozen=True)
class RunExternalAgentFilePrep:
    tool: str
    output: str
    timeout_seconds: int
    capture_stdout: bool
    capture_stdout_only: bool
    stderr_sink: str
    cmd: Sequence[str]
    stdout_path: str | Path | None
    stderr_path: str | Path | None
    sentinel_suffix: str


@dataclass(frozen=True)
class TailReadResult:
    offset: int
    text: str


@dataclass(frozen=True)
class LaunchResult:
    launcher_exit: int
    output: Path


@dataclass(frozen=True)
class LauncherPaths:
    output: Path
    done: Path
    inner_done: Path
    meta: Path
    sidecar: Path
    diag: Path
    events: Path
    token_record: Path
    failure_diag: Path
    prompt: Path
    stderr_tail: Path
    stall_json: Path
    stderr: Path
    launch_stderr: Path
    launcher_stderr: Path
    sidecar_history: Path
    events_history: Path

    @classmethod
    def from_output(cls, output: Path) -> LauncherPaths:
        suffix = output.suffix
        return cls(
            output=output,
            done=output.with_suffix(suffix + ".done"),
            inner_done=output.with_suffix(suffix + ".inner.done"),
            meta=output.with_suffix(suffix + ".meta"),
            sidecar=output.with_suffix(suffix + ".sidecar"),
            diag=output.with_suffix(suffix + ".diag"),
            events=output.with_suffix(suffix + ".events.jsonl"),
            token_record=output.with_suffix(suffix + ".token-record"),
            failure_diag=output.with_suffix(suffix + ".failure-diag"),
            prompt=output.with_suffix(suffix + ".prompt"),
            stderr_tail=output.with_suffix(suffix + ".stderr-tail"),
            stall_json=output.with_suffix(suffix + ".stall.json"),
            stderr=output.with_suffix(suffix + ".stderr"),
            launch_stderr=output.with_suffix(suffix + ".launch-stderr"),
            launcher_stderr=output.with_suffix(suffix + ".launcher-stderr"),
            sidecar_history=output.with_suffix(suffix + ".sidecar.history"),
            events_history=output.with_suffix(suffix + ".events.history"),
        )

    def sentinel_done(self, suffix: str) -> Path:
        return self.output.with_suffix(self.output.suffix + suffix)


@dataclass(frozen=True)
class DrafterParseResult:
    plan_lines: int
    diff_lines: int
    summary_written: bool
    scout_candidate_written: bool = False
    scout_fail_reason: str = ""
    dialectic_payload: str = ""
    dialectic_parsed: bool = False
    dialectic_fail_reason: str = ""


@dataclass(frozen=True)
class StartupLockState:
    lock_path: Path | None


@dataclass(frozen=True)
class CheckReviewersResult:
    codex_binary_found: bool
    cursor_binary_found: bool
    codex_present: bool
    cursor_present: bool
    codex_probe_timed_out: bool = False
    cursor_probe_timed_out: bool = False

    def kv(self) -> dict[str, str]:
        return {
            "CODEX_BINARY_FOUND": str(self.codex_binary_found).lower(),
            "CURSOR_BINARY_FOUND": str(self.cursor_binary_found).lower(),
            "CODEX_PRESENT": str(self.codex_present).lower(),
            "CURSOR_PRESENT": str(self.cursor_present).lower(),
            "CODEX_PROBE_TIMED_OUT": str(self.codex_probe_timed_out).lower(),
            "CURSOR_PROBE_TIMED_OUT": str(self.cursor_probe_timed_out).lower(),
        }

    def kv_lines(self) -> tuple[str, ...]:
        data = self.kv()
        return tuple(f"{key}={data[key]}" for key in (
            "CODEX_BINARY_FOUND",
            "CURSOR_BINARY_FOUND",
            "CODEX_PRESENT",
            "CURSOR_PRESENT",
            "CODEX_PROBE_TIMED_OUT",
            "CURSOR_PROBE_TIMED_OUT",
        ))


def _err(message: str) -> None:
    logging_util.diagnostic(message)


def _emit(text: str) -> None:
    logging_util.emit(text)


def _emit_kv(*, key: str, value: str | int) -> None:
    logging_util.emit_kv(key=key, value=str(value))


def _read_text(path: str | Path | None) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def _write(*, path: str | Path, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _append(*, path: str | Path, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as handle:
        _ = handle.write(text)


def _parse_positive_or_zero_int(value: str) -> int | None:
    if value.isdigit():
        return int(value, 10)
    return None


def _is_positive_int(value: str) -> bool:
    return bool(value) and value.isdigit() and int(value, 10) > 0


def _valid_model_token(value: str) -> bool:
    return bool(value) and not any(ch.isspace() for ch in value) and not _CTRL_RE.search(value)


def _validate_meta_path(*, label: str, value: str) -> bool:
    if not _SAFE_META_PATH_RE.fullmatch(value):
        _err(f"ERROR: {label} contains unsupported characters")
        return False
    return True


def _sanitize_tool_label(value: str) -> str:
    sanitized = "".join(ch if ch.isascii() and (ch.isalnum() or ch in "._-") else "_" for ch in value)
    return sanitized or "sanitized-empty"


def _json_array(values: Sequence[str]) -> str:
    return json.dumps(list(values), ensure_ascii=False, separators=(",", ":"))


def _plugin_root() -> Path:
    return Path(os.environ.get("CLAUDE_PLUGIN_ROOT", str(_PLUGIN_ROOT))).resolve()


def _env_int(*, name: str, default: int, zero_allowed: bool = True) -> int:
    raw = os.environ.get(name, str(default))
    parsed = _parse_positive_or_zero_int(raw)
    if parsed is None:
        return default
    if parsed == 0 and not zero_allowed:
        return default
    return parsed
