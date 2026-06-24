# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Collect, validate, and retry launch failures for external reviewer outputs."""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence

import agents
import logging_util
import retry
import review_dispatch

REPO_ROOT = Path(__file__).resolve().parents[1]
PY_CLI = REPO_ROOT / "python" / "cli.py"
_TIMEOUT_EXIT = "124"
_RETRY_WAIT_FLOOR = 30
_RETRY_WAIT_GRACE = 60
_REASON_LIMIT = 500
_VALIDATION_REASON_LIMIT = 200
_STATUS_CURSOR_EMPTY = "CURSOR_EMPTY_RESPONSE"
_STATUS_CURSOR_DEGRADED = "CURSOR_DEGRADED_RESPONSE"
_MAX_EXIT_CODE = 255
_MIN_TOOL_ARGC = 2
_EXIT_OUTPUT_EMPTY = 4
_EXIT_VALIDATION_CURSOR_EMPTY = 5
_MIN_WAIT_PARTS = 2
@dataclass(frozen=True)
class CollectorOptions:
    timeout: int
    output_files: tuple[str, ...]
    substantive_validation: bool = False
    validation_mode: bool = False
    structured_reviewer_validation: bool = False
    summary_only: bool = False
    paths_file: str = ""


# Mutable: exit_code and failure_reason are refined in place after construction.
@dataclass
class CollectorRecord:
    reviewer_file: str
    tool: str
    status: str
    exit_code: str
    structured_sidecar: str = ""
    failure_reason: str = ""
    ns_retry_mode: str = ""
    ns_retry_reason: str = ""

    def get(self, key: str) -> str:
        return {
            "REVIEWER_FILE": self.reviewer_file,
            "TOOL": self.tool,
            "STATUS": self.status,
            "EXIT_CODE": self.exit_code,
            "STRUCTURED_SIDECAR": self.structured_sidecar,
            "FAILURE_REASON": self.failure_reason,
            "NS_RETRY_MODE": self.ns_retry_mode,
            "NS_RETRY_REASON": self.ns_retry_reason,
        }.get(key, "")

    def fields(self, *, summary_only: bool = False) -> list[str]:
        fields = [
            f"REVIEWER_FILE={self.reviewer_file}",
            f"TOOL={self.tool}",
            f"STATUS={self.status}",
            f"EXIT_CODE={self.exit_code}",
        ]
        if summary_only:
            return fields
        fields.append(f"STRUCTURED_SIDECAR={self.structured_sidecar}")
        fields.append(f"FAILURE_REASON={self.failure_reason}")
        if self.ns_retry_mode:
            fields.append(f"NS_RETRY_MODE={self.ns_retry_mode}")
        if self.ns_retry_reason:
            fields.append(f"NS_RETRY_REASON={self.ns_retry_reason}")
        return fields


def parse_collector_records(text: str) -> list[dict[str, str]]:
    r"""Parse collector stdout / ``collector-results.env`` into per-reviewer dicts.

    The collector emits one ``KEY=VALUE`` per line (see ``CollectorRecord.fields``),
    with records separated by a blank line. Records are anchored on ``REVIEWER_FILE``:
    diagnostic ``KEY=VALUE`` lines emitted before the first record are ignored, a new
    ``REVIEWER_FILE`` opens the next record, and a blank line closes the current one.

    This is the single reader for that wire format. Consumers must not re-implement
    delimiter parsing: a stale ``\x1f`` split here silently dropped every reviewer
    finding (issue #4790).
    """
    records: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        if "=" not in line:
            if not line.strip() and current is not None:
                records.append(current)
                current = None
            continue
        key, value = line.split("=", 1)
        if key == "REVIEWER_FILE":
            if current is not None:
                records.append(current)
            current = {key: value}
        elif current is not None:
            current[key] = value
    if current is not None:
        records.append(current)
    return records


@dataclass(frozen=True)
class RetryMeta:
    tool: str = ""
    timeout: str = ""
    capture_stdout: str = ""
    capture_stdout_only: str = ""
    cmd_json: str = ""
    orig_output: str = ""
    outer_launcher: str = ""
    outer_launcher_prompt_file: str = ""
    outer_launcher_workdir: str = ""
    outer_launcher_site: str = ""
    outer_launcher_risk: str = ""
    outer_launcher_kind: str = ""
    outer_launcher_sandbox: str = ""
    outer_launcher_with_effort: str = ""
    outer_launcher_usage_label: str = ""
    outer_launcher_timing_kind: str = ""
    outer_launcher_add_dirs_json: str = ""
    stderr_sink: str = ""


# Mutable builder: process / sentinel / launched are set when the retry is launched.
@dataclass
class RetryPlan:
    index: int
    orig_output: str
    retry_output: str
    timeout: int
    mode: str = "empty"
    ns_retry_reason: str = ""
    launched: bool = False
    sentinel: str = ""
    process: subprocess.Popen[bytes] | None = None
    temp_prompt: str = ""


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


def _diagnostic(message: str) -> None:
    logging_util.diagnostic(message)


def _emit(text: str) -> None:
    logging_util.emit(text)


def _validate_positive_int(*, raw: str, flag: str) -> int | None:
    if not raw or not raw.isdigit():
        print(f"Error: {flag} value must be a positive integer, got '{raw}'", file=sys.stderr)
        return None
    value = int(raw, 10)
    if value < 1:
        print(f"Error: {flag} value must be a positive integer, got '{raw}'", file=sys.stderr)
        return None
    return value


def _parse_meta(meta_path: str | Path) -> RetryMeta:
    data: dict[str, str] = {}
    try:
        lines = Path(meta_path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return RetryMeta()
    for line in lines:
        key, sep, val = line.partition("=")
        if sep:
            data[key] = val
    return RetryMeta(
        tool=data.get("TOOL", ""),
        timeout=data.get("TIMEOUT", ""),
        capture_stdout=data.get("CAPTURE_STDOUT", ""),
        capture_stdout_only=data.get("CAPTURE_STDOUT_ONLY", ""),
        cmd_json=data.get("CMD_JSON", ""),
        orig_output=data.get("OUTPUT_FILE", ""),
        outer_launcher=data.get("OUTER_LAUNCHER", ""),
        outer_launcher_prompt_file=data.get("OUTER_LAUNCHER_PROMPT_FILE", ""),
        outer_launcher_workdir=data.get("OUTER_LAUNCHER_WORKDIR", ""),
        outer_launcher_site=data.get("OUTER_LAUNCHER_SITE", ""),
        outer_launcher_risk=data.get("OUTER_LAUNCHER_RISK", ""),
        outer_launcher_kind=data.get("OUTER_LAUNCHER_KIND", ""),
        outer_launcher_sandbox=data.get("OUTER_LAUNCHER_SANDBOX", ""),
        outer_launcher_with_effort=data.get("OUTER_LAUNCHER_WITH_EFFORT", ""),
        outer_launcher_usage_label=data.get("OUTER_LAUNCHER_USAGE_LABEL", ""),
        outer_launcher_timing_kind=data.get("OUTER_LAUNCHER_TIMING_KIND", ""),
        outer_launcher_add_dirs_json=data.get("OUTER_LAUNCHER_ADD_DIRS_JSON", ""),
        stderr_sink=data.get("STDERR_SINK", ""),
    )


def _registered_tools() -> tuple[str, ...]:
    return agents.external_tool_names()


def derive_tool(output_file: str) -> str:
    meta = _parse_meta(f"{output_file}.meta")
    if meta.tool in _registered_tools():
        return meta.tool
    base = Path(output_file).name
    for tool in _registered_tools():
        if tool in base:
            return tool
    return "unknown"


def _sanitize_failure_reason(text: str, *, limit: int = _REASON_LIMIT) -> str:
    one_line = re.sub(r"\s+", " ", text.replace("|", " ").replace("\r", " ").replace("\n", " ")).strip()
    if len(one_line) > limit:
        return one_line[: max(0, limit - 3)] + "..."
    return one_line


def _read_nonempty(path: str | Path) -> str:
    try:
        p = Path(path)
        if not p.is_file() or p.stat().st_size <= 0:
            return ""
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def build_failure_reason(*, output_file: str, status: str, exit_code: str) -> str:
    raw = _read_nonempty(f"{output_file}.diag")
    if not raw:
        if status == "SENTINEL_TIMEOUT":
            raw = "Process did not complete (sentinel file missing — possible crash or system kill)"
        elif status == "TIMED_OUT":
            raw = "Process timed out (exit code 124)"
        elif status == "FAILED":
            raw = f"Process failed with exit code {exit_code}"
        elif status == "EMPTY_OUTPUT":
            raw = "Process exited successfully but produced no output"
        else:
            raw = f"Unknown failure (status={status}, exit_code={exit_code})"
    return _sanitize_failure_reason(raw)


def _normalize_exit_code(*, raw: str, context: str) -> tuple[str, bool]:
    value = raw.rstrip("\n")
    if re.fullmatch(r"[0-9]{1,3}", value) and int(value, 10) <= _MAX_EXIT_CODE:
        return value, False
    _diagnostic(f"collect-results: invalid exit code from {context}; forcing EXIT_CODE=99")
    return "99", True


def _read_sentinel_exit(*, path: str, context: str) -> tuple[str, bool]:
    try:
        raw = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        raw = "99"
    return _normalize_exit_code(raw=raw, context=context)


def _classify_cursor_response(path: str) -> bool:
    try:
        with Path(path).open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped:
                    return stripped in {_STATUS_CURSOR_EMPTY, _STATUS_CURSOR_DEGRADED}
    except OSError:
        return False
    return False


def _retry_output_path(output: str) -> str:
    base = output.removesuffix(".txt")
    return f"{base}-retry.txt"


def derive_ns_retry_reason(*, val_exit: int, ns_mode: str) -> str:
    if ns_mode == "structured":
        return "JSON_PARSE_FAIL" if val_exit == _EXIT_VALIDATION_CURSOR_EMPTY else "UNKNOWN"
    if val_exit in {2, 3}:
        return "NO_ISSUES_FOUND_TOO_THIN"
    if val_exit == _EXIT_OUTPUT_EMPTY:
        return "OUTPUT_EMPTY"
    return "UNKNOWN"


def _validate_retry_timeout(meta: RetryMeta) -> tuple[int | None, str]:
    if not meta.timeout:
        return None, "Retry metadata invalid: TIMEOUT missing"
    if not re.fullmatch(r"[0-9]+", meta.timeout) or int(meta.timeout, 10) < 1:
        return None, "Retry metadata invalid: TIMEOUT not a positive integer"
    return int(meta.timeout, 10), ""


def _mark_retry_metadata_invalid(*, records: list[CollectorRecord], idx: int, orig_output: str, reason: str) -> None:
    records[idx] = CollectorRecord(
        reviewer_file=orig_output,
        tool=derive_tool(orig_output),
        status="EMPTY_OUTPUT",
        exit_code="99",
        failure_reason=reason,
    )


def _cmd_has_token(*, cmd: Sequence[str], needle: str) -> bool:
    return needle in cmd


def _cmd_json_shape_valid_for_tool(*, tool: str, cmd: Sequence[str]) -> tuple[bool, str]:
    if not cmd:
        return False, "rejected"
    argv0 = Path(cmd[0]).name
    if tool == "cursor":
        if len(cmd) < _MIN_TOOL_ARGC or argv0 != "cursor" or cmd[1] != "agent":
            return False, "rejected"
        if not _cmd_has_token(cmd=cmd, needle="--workspace") or _cmd_has_token(cmd=cmd, needle="--add-dir"):
            return False, "rejected"
        return True, ""
    if tool == "codex":
        if len(cmd) < _MIN_TOOL_ARGC or argv0 != "codex" or cmd[1] != "exec":
            return False, "rejected"
        for token in ("-C", "--add-dir", "--output-last-message"):
            if not _cmd_has_token(cmd=cmd, needle=token):
                return False, "rejected"
        return True, ""
    return False, "unknown"


def _cmd_json_requires_outer_launcher(*, orig_output: str, tool: str, cmd: Sequence[str]) -> bool:
    if Path(f"{orig_output}.prompt").is_file():
        return True
    if len(cmd) < _MIN_TOOL_ARGC:
        return False
    argv0 = Path(cmd[0]).name
    if tool == "cursor" and argv0 == "cursor" and cmd[1] == "agent":
        mode = ""
        for idx, arg in enumerate(cmd[:-1]):
            if arg == "--mode":
                mode = cmd[idx + 1]
        return mode == "ask"
    if tool == "codex" and argv0 == "codex" and cmd[1] == "exec":
        sandbox = ""
        for idx, arg in enumerate(cmd[:-1]):
            if arg == "--sandbox":
                sandbox = cmd[idx + 1]
        return sandbox == "read-only"
    return False


def _env_without_test_hooks() -> dict[str, str]:
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("LARCH_COLLECT_RESULTS_"):
            _ = env.pop(key, None)
    for key in (
        "LARCH_ALLOW_TEST_HOOKS",
        "LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE",
        "LARCH_TEST_TRAP_AFTER_INNER_DONE",
        "RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX",
    ):
        _ = env.pop(key, None)
    return env


def _safe_meta_path_value(value: str) -> bool:
    return ".." not in value


def _parse_json_string_array(raw: str) -> tuple[list[str] | None, str]:
    try:
        obj: object = json.loads(raw)
    except json.JSONDecodeError:
        return None, "malformed CMD_JSON"
    if not isinstance(obj, list) or not obj:
        return None, "malformed CMD_JSON"
    items: list[str] = []
    for item in obj:
        if not isinstance(item, str):
            return None, "malformed CMD_JSON"
        items.append(item)
    return items, ""


def _launch_cmd_json_retry(
    *, plan: RetryPlan,
    meta: RetryMeta,
    records: list[CollectorRecord],
) -> bool:
    if not meta.cmd_json and not meta.tool:
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: missing CMD_JSON and TOOL")
        return False
    if not meta.cmd_json:
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: missing CMD_JSON")
        return False
    if not meta.tool:
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: missing TOOL")
        return False
    cmd, err = _parse_json_string_array(meta.cmd_json)
    if cmd is None:
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason=f"Retry metadata invalid: {err}")
        return False
    if meta.orig_output:
        cmd = [plan.retry_output if item == meta.orig_output else item for item in cmd]
    ok, shape_reason = _cmd_json_shape_valid_for_tool(tool=meta.tool, cmd=cmd)
    if not ok:
        reason = "unknown TOOL for CMD_JSON" if shape_reason == "unknown" else f"CMD_JSON argv shape rejected for {meta.tool}"
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason=f"Retry metadata invalid: {reason}")
        return False
    if _cmd_json_requires_outer_launcher(orig_output=plan.orig_output, tool=meta.tool, cmd=cmd):
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: review-shaped CMD_JSON requires outer launcher metadata")
        return False
    if meta.stderr_sink and not _safe_meta_path_value(meta.stderr_sink):
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: STDERR_SINK contains ..")
        return False
    args = [
        sys.executable,
        str(PY_CLI),
        "agent",
        "run-external-agent",
        "--tool",
        meta.tool,
        "--output",
        plan.retry_output,
        "--timeout",
        str(plan.timeout),
    ]
    if meta.capture_stdout == "true":
        args.append("--capture-stdout")
    elif meta.capture_stdout_only == "true":
        args.append("--capture-stdout-only")
    if meta.stderr_sink:
        args.extend(["--stderr-sink", meta.stderr_sink])
    args.append("--")
    args.extend(cmd)
    plan.process = subprocess.Popen(  # pylint: disable=consider-using-with
        args,
        env=_env_without_test_hooks(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    plan.sentinel = f"{plan.retry_output}.done"
    plan.launched = True
    return True


def _build_codex_exec_retry_args(*, plan: RetryPlan, meta: RetryMeta, records: list[CollectorRecord], prompt_file: str) -> list[str] | None:
    if meta.outer_launcher_kind != "codex-exec":
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: OUTER_LAUNCHER_KIND must be codex-exec")
        return None
    if meta.outer_launcher_sandbox not in {"full-auto", "read-only"}:
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: OUTER_LAUNCHER_SANDBOX invalid")
        return None
    if meta.outer_launcher_with_effort not in {"true", "false"}:
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: OUTER_LAUNCHER_WITH_EFFORT invalid")
        return None
    if not meta.outer_launcher_usage_label:
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: missing OUTER_LAUNCHER_USAGE_LABEL")
        return None
    if not meta.outer_launcher_timing_kind:
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: missing OUTER_LAUNCHER_TIMING_KIND")
        return None
    try:
        add_dirs_obj: object = json.loads(meta.outer_launcher_add_dirs_json or "[]")
    except json.JSONDecodeError:
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: OUTER_LAUNCHER_ADD_DIRS_JSON malformed")
        return None
    if not isinstance(add_dirs_obj, list):
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: OUTER_LAUNCHER_ADD_DIRS_JSON malformed")
        return None
    add_dirs: list[str] = []
    for item in add_dirs_obj:
        if not isinstance(item, str):
            _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: OUTER_LAUNCHER_ADD_DIRS_JSON malformed")
            return None
        add_dirs.append(item)
    args = [
        "--output",
        plan.retry_output,
        "--timeout",
        str(plan.timeout),
        "--workdir",
        meta.outer_launcher_workdir,
        "--prompt-file",
        prompt_file,
        "--sandbox",
        meta.outer_launcher_sandbox,
        "--usage-label",
        meta.outer_launcher_usage_label,
        "--timing-task-kind",
        meta.outer_launcher_timing_kind,
    ]
    if meta.outer_launcher_with_effort == "true":
        args.append("--with-effort")
    for add_dir in add_dirs:
        if add_dir:
            args.extend(["--add-dir", add_dir])
    return args


def _launch_outer_retry(
    *, plan: RetryPlan,
    meta: RetryMeta,
    records: list[CollectorRecord],
) -> bool:
    if not meta.outer_launcher:
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: missing OUTER_LAUNCHER")
        return False
    if not meta.outer_launcher_prompt_file:
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: missing OUTER_LAUNCHER_PROMPT_FILE")
        return False
    if not meta.outer_launcher_workdir:
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: missing OUTER_LAUNCHER_WORKDIR")
        return False
    if not _safe_meta_path_value(meta.outer_launcher):
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: OUTER_LAUNCHER contains ..")
        return False
    if meta.outer_launcher == "agent launch-review":
        launcher_kind = "review"
    elif meta.outer_launcher == "agent launch-codex-exec":
        launcher_kind = "codex-exec"
    elif meta.outer_launcher.endswith("/launch-review.sh") or meta.outer_launcher == "launch-review.sh":
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: retired review OUTER_LAUNCHER metadata is no longer accepted")
        return False
    else:
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: OUTER_LAUNCHER not canonical agent launch-review or agent launch-codex-exec")
        return False
    expected_prompt = f"{plan.orig_output}.prompt"
    if not _safe_meta_path_value(meta.outer_launcher_prompt_file):
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: OUTER_LAUNCHER_PROMPT_FILE contains ..")
        return False
    if meta.outer_launcher_prompt_file != expected_prompt:
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: OUTER_LAUNCHER_PROMPT_FILE not the expected sidecar")
        return False
    prompt_for_launch = meta.outer_launcher_prompt_file
    prompt_path = Path(prompt_for_launch)
    if not prompt_path.is_file() or prompt_path.is_symlink():
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: OUTER_LAUNCHER_PROMPT_FILE not a readable regular non-symlink file")
        return False
    if not _safe_meta_path_value(meta.outer_launcher_workdir):
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: OUTER_LAUNCHER_WORKDIR contains ..")
        return False
    if not Path(meta.outer_launcher_workdir).is_dir():
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: OUTER_LAUNCHER_WORKDIR not a directory")
        return False
    if launcher_kind == "review":
        risk = meta.outer_launcher_risk if meta.outer_launcher_risk in {"high", "low"} else "high"
        if meta.stderr_sink and not _safe_meta_path_value(meta.stderr_sink):
            _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason="Retry metadata invalid: STDERR_SINK contains ..")
            return False
        timing_kind = meta.outer_launcher_timing_kind
        if not timing_kind:
            if meta.tool == "codex":
                timing_kind = os.environ.get("LARCH_TIMING_TASK_KIND", "codex-review")
            elif meta.tool == "cursor":
                timing_kind = os.environ.get("LARCH_TIMING_TASK_KIND", "cursor-review")
        args = [
            sys.executable,
            str(PY_CLI),
            "agent",
            "launch-review",
            "--tool",
            meta.tool,
            "--output",
            plan.retry_output,
            "--timeout",
            str(plan.timeout),
            "--risk",
            risk,
            "--timing-task-kind",
            timing_kind,
            "--prompt-file",
            prompt_for_launch,
        ]
        if meta.outer_launcher_site:
            args.extend(["--site", meta.outer_launcher_site])
        if meta.stderr_sink:
            args.extend(["--stderr-sink", meta.stderr_sink])
    else:
        extra = _build_codex_exec_retry_args(plan=plan, meta=meta, records=records, prompt_file=prompt_for_launch)
        if extra is None:
            return False
        args = [sys.executable, str(PY_CLI), "agent", "launch-codex-exec", *extra]
    plan.process = subprocess.Popen(  # pylint: disable=consider-using-with
        args,
        cwd=meta.outer_launcher_workdir,
        env=_env_without_test_hooks(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    plan.sentinel = f"{plan.retry_output}.done"
    plan.launched = True
    return True


def _launch_retry_plan(*, plan: RetryPlan, records: list[CollectorRecord]) -> bool:
    meta = _parse_meta(f"{plan.orig_output}.meta")
    timeout, reason = _validate_retry_timeout(meta)
    if timeout is None:
        _mark_retry_metadata_invalid(records=records, idx=plan.index, orig_output=plan.orig_output, reason=reason)
        return False
    plan.timeout = timeout
    if meta.outer_launcher or meta.outer_launcher_prompt_file or meta.outer_launcher_workdir:
        return _launch_outer_retry(plan=plan, meta=meta, records=records)
    return _launch_cmd_json_retry(plan=plan, meta=meta, records=records)


def _wait_retry_plans(plans: Sequence[RetryPlan]) -> None:
    sentinels = [plan.sentinel for plan in plans if plan.launched and plan.sentinel]
    if not sentinels:
        return
    timeout = _RETRY_WAIT_FLOOR
    for plan in plans:
        if plan.launched:
            timeout = max(timeout, plan.timeout + _RETRY_WAIT_GRACE)
    _ = review_dispatch.wait_reviewers(
        sentinels,
        timeout=timeout,
        emit_fn=lambda _line: None,
        diagnostic_fn=lambda _line: None,
    )
    for plan in plans:
        proc = plan.process
        if proc is not None:
            with contextlib.suppress(Exception):
                _ = proc.wait(timeout=0)


def _retry_failure_result(*, records: list[CollectorRecord], plan: RetryPlan) -> None:
    tool = derive_tool(plan.orig_output)
    sentinel = Path(plan.sentinel)
    if sentinel.is_file():
        retry_exit, _ = _read_sentinel_exit(path=str(sentinel), context="retry sentinel")
        if retry_exit == _TIMEOUT_EXIT:
            retry_status = "TIMED_OUT"
        elif retry_exit != "0":
            retry_status = "FAILED"
        else:
            retry_status = "EMPTY_OUTPUT"
        retry_reason = build_failure_reason(output_file=plan.retry_output, status=retry_status, exit_code=retry_exit)
        records[plan.index] = CollectorRecord(
            reviewer_file=plan.orig_output,
            tool=tool,
            status="EMPTY_OUTPUT",
            exit_code=retry_exit,
            failure_reason=f"Retry also failed: {retry_reason}",
        )
    else:
        records[plan.index] = CollectorRecord(
            reviewer_file=plan.orig_output,
            tool=tool,
            status="EMPTY_OUTPUT",
            exit_code="99",
            structured_sidecar="",
            failure_reason="Retry process did not complete (sentinel file missing)",
        )


def _apply_empty_retry_results(*, records: list[CollectorRecord], plans: Sequence[RetryPlan]) -> None:
    for plan in plans:
        if not plan.launched:
            continue
        tool = derive_tool(plan.orig_output)
        sentinel = Path(plan.sentinel)
        output = Path(plan.retry_output)
        if sentinel.is_file():
            retry_exit, _ = _read_sentinel_exit(path=str(sentinel), context="retry sentinel")
            if retry_exit == "0" and output.is_file() and output.stat().st_size > 0:
                if _classify_cursor_response(plan.retry_output):
                    records[plan.index] = CollectorRecord(
                        reviewer_file=plan.retry_output,
                        tool=tool,
                        status=_STATUS_CURSOR_EMPTY,
                        exit_code="0",
                        failure_reason="cursor narration-only / degraded backend response (retry)",
                    )
                else:
                    records[plan.index] = CollectorRecord(plan.retry_output, tool, "OK", "0")
                for tail in (f"{plan.orig_output}.stderr-tail", f"{plan.retry_output}.stderr-tail"):
                    with contextlib.suppress(FileNotFoundError):
                        Path(tail).unlink()
            else:
                _retry_failure_result(records=records, plan=plan)
        else:
            _retry_failure_result(records=records, plan=plan)


def _run_validator(args: Sequence[str]) -> CommandResult:
    proc = subprocess.run(
        [sys.executable, str(PY_CLI), "eval", "validate-research-output", *args],
        text=True,
        capture_output=True,
        check=False,
    )
    return CommandResult(proc.returncode, proc.stdout, proc.stderr)


def _validate_substantive(records: list[CollectorRecord], *, validation_mode: bool) -> None:
    val_args: list[str] = ["--validation-mode"] if validation_mode else []
    for idx, record in enumerate(list(records)):
        if record.status != "OK":
            continue
        result = _run_validator([*val_args, record.reviewer_file])
        if result.returncode == 0:
            continue
        diag = _sanitize_failure_reason(result.stdout + result.stderr, limit=_VALIDATION_REASON_LIMIT)
        if result.returncode == _EXIT_VALIDATION_CURSOR_EMPTY:
            records[idx] = CollectorRecord(record.reviewer_file, record.tool, _STATUS_CURSOR_EMPTY, "0", failure_reason=diag)
        else:
            records[idx] = CollectorRecord(
                record.reviewer_file,
                record.tool,
                "NOT_SUBSTANTIVE",
                "0",
                failure_reason=diag,
                ns_retry_mode="substantive",
                ns_retry_reason=derive_ns_retry_reason(val_exit=result.returncode, ns_mode="substantive"),
            )


def _structured_sidecar_path(record: CollectorRecord) -> str:
    suffix = ".tsv" if record.tool in {"cursor", "codex"} else ".jsonl"
    return f"{record.reviewer_file}{suffix}"


def _validate_structured(records: list[CollectorRecord]) -> None:
    for idx, record in enumerate(list(records)):
        if record.status != "OK":
            record.structured_sidecar = record.structured_sidecar or ""
            continue
        sidecar = _structured_sidecar_path(record)
        result = _run_validator(["--structured-reviewer-mode", "--write-structured", sidecar, record.reviewer_file])
        if result.returncode == 0:
            record.structured_sidecar = sidecar
            records[idx] = record
            if "NO_ISSUES_SENTINEL_RECOVERED_AFTER_PREAMBLE" in (result.stdout + result.stderr):
                _diagnostic(
                    "collect-results: structured reviewer output recovered a no-issues sentinel after preamble "
                    f"basename={Path(record.reviewer_file).name} tool={record.tool or 'unknown'}"
                )
        else:
            diag = _sanitize_failure_reason(result.stdout + result.stderr, limit=_VALIDATION_REASON_LIMIT)
            records[idx] = CollectorRecord(
                record.reviewer_file,
                record.tool,
                "NOT_SUBSTANTIVE",
                "0",
                structured_sidecar="",
                failure_reason=diag,
                ns_retry_mode="structured",
                ns_retry_reason=derive_ns_retry_reason(val_exit=result.returncode, ns_mode="structured"),
            )


def _emit_not_substantive_diagnostics(records: Sequence[CollectorRecord]) -> None:
    for record in records:
        if record.status != "NOT_SUBSTANTIVE":
            continue
        _diagnostic(
            "collect-results: warning: dropping NOT_SUBSTANTIVE reviewer "
            f"basename={Path(record.reviewer_file).name} "
            f"tool={record.tool or 'unknown'} "
            f"NS_RETRY_MODE={record.ns_retry_mode or 'none'} "
            f"NS_RETRY_REASON={record.ns_retry_reason or 'UNKNOWN'} "
            f"FAILURE_REASON={_sanitize_failure_reason(record.failure_reason)}"
        )


def collector_stderr_tail_candidates(reviewer_file: str) -> list[str]:
    candidates = [reviewer_file]
    if reviewer_file.endswith("-phase3.txt"):
        candidates.append(f"{reviewer_file[:-11]}-phase2.txt")
        candidates.append(f"{reviewer_file[:-11]}.txt")
    elif reviewer_file.endswith(("-phase2.txt", "-phase1.txt")):
        candidates.append(f"{reviewer_file[:-11]}.txt")
    return candidates


def _render_launch_stderr_tail(launch_stderr: str) -> str:
    if Path(launch_stderr).is_file() and Path(launch_stderr).stat().st_size > 0:
        fd, tmp_tail = tempfile.mkstemp(prefix="larch-launch-stderr-tail.", dir=os.environ.get("TMPDIR") or None)
        os.close(fd)
        rendered = agents.render_failed_agent_stderr_tail(Path(launch_stderr))
        if rendered:
            _ = Path(tmp_tail).write_text(rendered, encoding="utf-8")
            return tmp_tail
        with contextlib.suppress(FileNotFoundError):
            Path(tmp_tail).unlink()
    return ""


def resolve_collector_stderr_tail_file(reviewer_file: str) -> str:
    base = reviewer_file.removesuffix(".txt")
    retry_tail = f"{base}-retry.txt.stderr-tail"
    if Path(retry_tail).is_file() and Path(retry_tail).stat().st_size > 0:
        return retry_tail
    ns_retry_tail = f"{base}-ns-retry.txt.stderr-tail"
    if Path(ns_retry_tail).is_file() and Path(ns_retry_tail).stat().st_size > 0:
        return ns_retry_tail
    for candidate in collector_stderr_tail_candidates(reviewer_file):
        candidate_base = candidate.removesuffix(".txt")
        retry_tail = f"{candidate_base}-retry.txt.stderr-tail"
        if Path(retry_tail).is_file() and Path(retry_tail).stat().st_size > 0:
            return retry_tail
        ns_retry_tail = f"{candidate_base}-ns-retry.txt.stderr-tail"
        if Path(ns_retry_tail).is_file() and Path(ns_retry_tail).stat().st_size > 0:
            return ns_retry_tail
        for launch_stderr in (
            f"{candidate_base}-retry.txt.launch-stderr",
            f"{candidate_base}-ns-retry.txt.launch-stderr",
            f"{candidate}.launch-stderr",
        ):
            rendered_tail = _render_launch_stderr_tail(launch_stderr)
            if rendered_tail:
                return rendered_tail
        tail = f"{candidate}.stderr-tail"
        if Path(tail).is_file() and Path(tail).stat().st_size > 0:
            return tail
    return ""


def failed_agent_stderr_signature(tail_file: str) -> str:
    text = _read_nonempty(tail_file)
    if not text:
        return ""
    home_cache = str(Path.home() / ".cache" / "larch" / "sessions")
    norm = re.sub(r"0x[0-9a-fA-F]+", "0x#", text)
    norm = re.sub(r"[0-9]+", "#", norm)
    norm = re.sub(r"/tmp\S*", "<path>", norm)  # noqa: S108 - redaction pattern, not a filesystem path
    norm = re.sub(r"/var/folders\S*", "<path>", norm)
    if home_cache:
        norm = re.sub(re.escape(home_cache) + r"\S*", "<path>", norm)
    norm = re.sub(r"\S+\.(txt|stderr-tail|sidecar|diag|done)( |$)", r"<out>\2", norm)
    cksum_bin = shutil.which("cksum")
    if not cksum_bin:
        return ""
    proc = subprocess.run(
        [cksum_bin],
        input=norm.encode("utf-8"),
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0 and proc.stdout:
        return proc.stdout.decode("utf-8", errors="replace").split()[0]
    return ""


def _emit_failed_agent_stderr_tails(records: Sequence[CollectorRecord]) -> None:
    seen: dict[str, str] = {}
    for record in records:
        if record.status in {"OK", "cap_hit", ""}:
            continue
        tail_file = resolve_collector_stderr_tail_file(record.reviewer_file)
        if not tail_file:
            continue
        sig = failed_agent_stderr_signature(tail_file)
        base = Path(record.reviewer_file).name
        if sig and sig in seen:
            _diagnostic(
                f"↩ {record.tool or 'unknown'} {base}: identical failure to {seen[sig]} "
                f"(root-cause sig {sig}); stderr tail suppressed"
            )
            if "/larch-launch-stderr-tail." in tail_file:
                with contextlib.suppress(FileNotFoundError):
                    Path(tail_file).unlink()
            continue
        if sig:
            seen[sig] = base
        rendered = agents.render_failed_agent_stderr_tail(Path(tail_file))
        if rendered:
            _diagnostic("--- failed agent stderr tail ---")
            for line in rendered.splitlines():
                if line:
                    _diagnostic(line)
            _diagnostic("--- end failed agent stderr tail ---")
        if "/larch-launch-stderr-tail." in tail_file:
            with contextlib.suppress(FileNotFoundError):
                Path(tail_file).unlink()


def _parse_wait_timeouts(lines: Sequence[str]) -> set[int]:
    timed_out: set[int] = set()
    for line in lines:
        if not line.startswith("TIMEOUT "):
            continue
        parts = line.split(maxsplit=2)
        if len(parts) >= _MIN_WAIT_PARTS and parts[1].isdigit():
            timed_out.add(int(parts[1], 10))
    return timed_out


def _initial_wait(*, timeout: int, output_files: Sequence[str]) -> tuple[int, set[int]]:
    sentinels: list[str] = [f"{path}.done" for path in output_files]
    emitted: list[str] = []
    diagnostics: list[str] = []
    rc = review_dispatch.wait_reviewers(
        sentinels,
        timeout=timeout,
        emit_fn=emitted.append,
        diagnostic_fn=diagnostics.append,
    )
    if rc != 0:
        for line in diagnostics:
            if line.strip():
                _diagnostic(line)
        _diagnostic(f"collect-results: wait-reviewers exited {rc}")
        return rc, set()
    return 0, _parse_wait_timeouts(emitted)


def _build_initial_records(*, options: CollectorOptions, timed_out_indexes: set[int]) -> tuple[list[CollectorRecord], list[RetryPlan]]:
    records: list[CollectorRecord] = []
    retry_plans: list[RetryPlan] = []
    for zero_idx, output in enumerate(options.output_files):
        wait_idx = zero_idx + 1
        sentinel = f"{output}.done"
        meta_path = f"{output}.meta"
        tool = derive_tool(output)
        record = CollectorRecord(output, tool, "OK", "0")
        if wait_idx in timed_out_indexes:
            record.status = "SENTINEL_TIMEOUT"
            record.exit_code = _TIMEOUT_EXIT
            record.failure_reason = build_failure_reason(output_file=output, status=record.status, exit_code=record.exit_code)
        elif Path(sentinel).is_file():
            exit_code, coerced = _read_sentinel_exit(path=sentinel, context="initial sentinel")
            record.exit_code = exit_code
            output_nonempty = Path(output).is_file() and Path(output).stat().st_size > 0
            if record.exit_code == _TIMEOUT_EXIT:
                record.status = "TIMED_OUT"
                record.failure_reason = build_failure_reason(output_file=output, status=record.status, exit_code=record.exit_code)
            elif record.exit_code != "0" and not (coerced and not output_nonempty):
                record.status = "FAILED"
                record.failure_reason = build_failure_reason(output_file=output, status=record.status, exit_code=record.exit_code)
            elif output_nonempty and _read_nonempty(output).splitlines()[0:1] == ["STATUS=cap_hit"]:
                record.status = "cap_hit"
                record.failure_reason = "Token budget cap hit; reviewer skipped"
            elif not output_nonempty:
                record.status = "EMPTY_OUTPUT"
                record.failure_reason = build_failure_reason(output_file=output, status=record.status, exit_code=record.exit_code)
                if Path(meta_path).is_file():
                    meta = _parse_meta(meta_path)
                    timeout, reason = _validate_retry_timeout(meta)
                    if timeout is None:
                        record = CollectorRecord(output, tool, "EMPTY_OUTPUT", "99", failure_reason=reason)
                    else:
                        retry_plans.append(RetryPlan(zero_idx, output, _retry_output_path(output), timeout))
        else:
            record.status = "SENTINEL_TIMEOUT"
            record.exit_code = _TIMEOUT_EXIT
            record.failure_reason = build_failure_reason(output_file=output, status=record.status, exit_code=record.exit_code)

        if (
            record.status in {"FAILED", "TIMED_OUT", "SENTINEL_TIMEOUT"}
            and Path(f"{output}.diag").is_file()
            and retry.is_transient_net_signature(record.failure_reason)
            and Path(meta_path).is_file()
        ):
            meta = _parse_meta(meta_path)
            timeout, reason = _validate_retry_timeout(meta)
            if timeout is None:
                record = CollectorRecord(output, tool, "EMPTY_OUTPUT", "99", failure_reason=reason)
            else:
                record.status = "EMPTY_OUTPUT"
                _diagnostic(f"collect-results: transient diagnostic for {Path(output).name}; retrying once")
                retry_plans.append(RetryPlan(zero_idx, output, _retry_output_path(output), timeout))
        if record.status == "OK" and _classify_cursor_response(output):
            record.status = _STATUS_CURSOR_EMPTY
            record.failure_reason = "cursor narration-only / degraded backend response"
        records.append(record)
    return records, retry_plans


def collect_results(options: CollectorOptions) -> int:
    wait_rc, timed_out_indexes = _initial_wait(timeout=options.timeout, output_files=options.output_files)
    if wait_rc != 0:
        return 1
    records, retry_plans = _build_initial_records(options=options, timed_out_indexes=timed_out_indexes)
    launched_retry_plans = [plan for plan in retry_plans if _launch_retry_plan(plan=plan, records=records)]
    _wait_retry_plans(launched_retry_plans)
    _apply_empty_retry_results(records=records, plans=retry_plans)
    if options.substantive_validation:
        _validate_substantive(records, validation_mode=options.validation_mode)
    if options.structured_reviewer_validation:
        _validate_structured(records)
    if options.substantive_validation or options.structured_reviewer_validation:
        _emit_not_substantive_diagnostics(records)
    if not options.summary_only:
        _emit_failed_agent_stderr_tails(records)
    _emit_records(records, summary_only=options.summary_only)
    return 0


def _emit_records(records: Sequence[CollectorRecord], *, summary_only: bool) -> None:
    first = True
    for record in records:
        if first:
            first = False
        else:
            _emit("")
        for field in record.fields(summary_only=summary_only):
            _emit(field)


def _paths_from_file(path: str) -> tuple[list[str] | None, str]:
    p = Path(path)
    if not p.exists() or not os.access(p, os.R_OK):
        return None, f"collect-results: paths-file not readable: {path}"
    if not p.is_file():
        return None, f"collect-results: paths-file is not a regular file: {path}"
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None, f"collect-results: paths-file not readable: {path}"
    outputs = [line for line in lines if line.strip()]
    if not outputs:
        return None, "collect-results: paths-file contains no entries (preserves anti-pattern #4)"
    return outputs, ""


def _usage() -> str:
    return (
        "Usage: cli.py agent collect-results --timeout <seconds> "
        "[--substantive-validation [--validation-mode]] [--structured-reviewer-validation] "
        "[--summary-only] [--paths-file <file>] <output-file>..."
    )


def _parse_args(argv: Sequence[str]) -> CollectorOptions | int:
    timeout_raw = ""
    substantive = False
    validation_mode = False
    structured = False
    summary = False
    paths_file = ""
    outputs: list[str] = []
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg == "--timeout":
            if idx + 1 >= len(argv):
                print("--timeout requires a value", file=sys.stderr)
                return 1
            timeout_raw = argv[idx + 1]
            idx += 2
        elif arg == "--substantive-validation":
            substantive = True
            idx += 1
        elif arg == "--validation-mode":
            validation_mode = True
            idx += 1
        elif arg == "--structured-reviewer-validation":
            structured = True
            idx += 1
        elif arg == "--summary-only":
            summary = True
            idx += 1
        elif arg == "--paths-file":
            if idx + 1 >= len(argv):
                print("--paths-file requires a value", file=sys.stderr)
                return 1
            paths_file = argv[idx + 1]
            idx += 2
        elif arg == "--help":
            print(_usage(), file=sys.stderr)
            return 0
        elif arg.startswith("-"):
            print(f"collect-results: unknown option: {arg}", file=sys.stderr)
            return 1
        else:
            outputs.append(arg)
            idx += 1
    if not timeout_raw:
        print("collect-results: --timeout is required", file=sys.stderr)
        return 1
    timeout = _validate_positive_int(raw=timeout_raw, flag="--timeout")
    if timeout is None:
        return 1
    if paths_file and outputs:
        print("collect-results: --paths-file is mutually exclusive with positional output-file arguments", file=sys.stderr)
        return 1
    if paths_file:
        parsed, err = _paths_from_file(paths_file)
        if parsed is None:
            print(err, file=sys.stderr)
            return 1
        outputs = parsed
    if not outputs:
        print("collect-results: at least one output file is required", file=sys.stderr)
        return 1
    return CollectorOptions(
        timeout=timeout,
        output_files=tuple(outputs),
        substantive_validation=substantive,
        validation_mode=validation_mode,
        structured_reviewer_validation=structured,
        summary_only=summary,
        paths_file=paths_file,
    )


def collect_results_main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    parsed = _parse_args(argv=args)
    if isinstance(parsed, int):
        return parsed
    logging_util.quiet_init(argv0="collect-results")
    return collect_results(parsed)


if __name__ == "__main__":
    raise SystemExit(collect_results_main())
