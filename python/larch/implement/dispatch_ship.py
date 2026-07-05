# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""Step 8+ ship state machine: seed, route-exit, pre-driver, ship, OOS checkpoint."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from larch.issue import execution_issues
from larch.issue import file_oos
from larch.issue import oos_filer
from larch.core import config
from larch.core import proc
from larch.core.run_context import RunContext
from larch.errors import PrePushConflictHandoff, ShipError, Stalled, TransientNetworkError
from larch.git import git, gh, rebase
from larch.implement import ship
from larch.implement.dispatch_helpers import (
    _clone_expected_tmpdir_prefix,
    _current_cli_path,
    _emit_kv,
    _emit_phantom_probe_with_warn,
    _env_value,
    _first_nonempty,
    _forward_child_output_to_stderr,
    _invoke_cli,
    _read_kv_file,
    _read_session_key_default,
    _rehydrate_plugin_root,
    _resolve_repo_root,
    _run_cli_forward,
    _tmpdir_from_env,
    _tracking_sentinel_values,
    _write_text_atomic,
)
from larch.implement.dispatch_leg import _run_cli_capture
from larch.implement.dispatch_commit_route import step8_python_guard_main

SHIP_ROUTE_EXIT_NEEDS_USER = 3
SHIP_ROUTE_EXIT_STALLED = 4
SHIP_ROUTE_EXIT_TRANSIENT = 6
SHIP_ROUTE_TRANSIENT_STALL_RETRY = 4
SHIP_ROUTE_DETAIL_FILE_MAX = 300

_SHIP_ROUTE_EXIT_AUTONOMOUS_REASONS = {
    "first-fixer-non-health",
    "ship-pr-internal-lint-fix",
    "local-unfixable",
}
_SHIP_ROUTE_EXIT_LEDGER_KEYS = (
    "ledger_ready",
    "ledger_site",
    "ledger_trigger",
    "ledger_step",
    "ledger_phase",
    "ledger_dispatcher",
    "ledger_exit_code",
    "ledger_failure_detail_log",
)
_PRE_FIX_REBASE_OK_SENTINEL = ".ship-pre-fix-rebase-ok"
_PRE_FIX_PHASE14_ALLOWED_REASONS = frozenset({"mergeStateStatus=DIRTY", "mergeStateStatus=BEHIND"})


@dataclass(frozen=True)
class ShipRouteResult:
    exit_code: int
    payload: dict[str, object]
    action: str


@dataclass(frozen=True)
class ShipPreFixRebaseRequest:
    implement_tmpdir: Path
    state: Mapping[str, str]
    cwd: str


@dataclass(frozen=True)
class ShipPreFixRebaseResult:
    status: str
    action: str
    detail: str = ""


def _ship_state_has_shell_kv_entries(state_file: Path) -> bool:
    if not state_file.is_file():
        return False
    text = state_file.read_text(encoding="utf-8", errors="replace")
    return re.search(r"^[A-Za-z_][A-Za-z0-9_]*=", text, re.MULTILINE) is not None


def step8_seed_initial_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-8-seed-initial")
    for flag in ("merge", "draft", "no-admin-fallback", "no-logs-commit", "manifest-path", "tool-label", "stall-tracking", "stall-step", "bail-reason", "bail-failure-detail-log"):
        parser.add_argument(f"--{flag}", default="")
    args = parser.parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    state_file = implement_tmpdir / "ship-pr-state.sh"
    if state_file.is_file() and state_file.stat().st_size > 0 and re.search(r"^[A-Za-z_][A-Za-z0-9_]*=", state_file.read_text(encoding="utf-8", errors="replace"), re.MULTILINE):
        print("step-8-seed-initial: initial ship state is create-if-absent only; refusing to re-seed non-empty ship-pr-state.sh", file=sys.stderr)
        return 2
    bootstrap_file = implement_tmpdir / "bootstrap-routing.env"
    seed_file = implement_tmpdir / "ship-seed-input.env"
    parent_issue = implement_tmpdir / "parent-issue.md"
    sentinel = _tracking_sentinel_values(parent_issue)
    bootstrap_coder = _read_kv_file(path=bootstrap_file, key="coder", default="")
    mapped_tool = "Codex" if bootstrap_coder == "codex" else "Cursor" if bootstrap_coder == "cursor" else "" if not bootstrap_coder else "claude"
    branch = _first_nonempty(_read_kv_file(path=bootstrap_file, key="BRANCH_NAME", default=""), _read_kv_file(path=parent_issue, key="BRANCH_NAME", default=""), sentinel.get("BRANCH_NAME", ""))
    issue = _first_nonempty(_read_kv_file(path=bootstrap_file, key="ISSUE_NUMBER", default=""), _read_kv_file(path=parent_issue, key="ISSUE_NUMBER", default=""), sentinel.get("ISSUE_NUMBER", ""))
    run_id = _first_nonempty(_read_kv_file(path=bootstrap_file, key="RUN_ID", default=""), _read_session_key_default(implement_tmpdir=implement_tmpdir, key="LARCH_RUN_ID", default=""), _read_kv_file(path=parent_issue, key="RUN_ID", default=""), sentinel.get("RUN_ID", ""))
    repo = _first_nonempty(_read_kv_file(path=bootstrap_file, key="REPO", default=""), _read_session_key_default(implement_tmpdir=implement_tmpdir, key="REPO", default=""))
    if not branch:
        print("step-8-seed-initial: BRANCH_NAME is required but missing from durable inputs", file=sys.stderr)
        return 2
    if not issue.isdigit():
        print("step-8-seed-initial: ISSUE_NUMBER must be a non-empty digit value", file=sys.stderr)
        return 2
    if not run_id:
        print("step-8-seed-initial: RUN_ID is required but missing from durable inputs", file=sys.stderr)
        return 2
    if not repo:
        print("step-8-seed-initial: REPO is required but missing from durable inputs", file=sys.stderr)
        return 2
    expected_session_id = (implement_tmpdir / "session-id").read_text(encoding="utf-8", errors="replace").strip() if (implement_tmpdir / "session-id").is_file() else ""
    return _run_cli_forward([
        "ship", "seed-initial-state", "--tmpdir", str(implement_tmpdir), "--state-file", str(state_file),
        "--branch", branch, "--issue", issue, "--repo", repo, "--run-id", run_id,
        "--manifest-path", _first_nonempty(args.manifest_path, _read_kv_file(path=seed_file, key="MANIFEST_PATH", default="")),
        "--tool-label", _first_nonempty(args.tool_label, _read_kv_file(path=seed_file, key="TOOL_LABEL", default=""), mapped_tool, "claude"),
        "--merge", _first_nonempty(args.merge, _read_kv_file(path=seed_file, key="MERGE", default=""), "false"),
        "--draft", _first_nonempty(args.draft, _read_kv_file(path=seed_file, key="DRAFT", default=""), "false"),
        "--forked", _first_nonempty(_read_kv_file(path=seed_file, key="FORKED_TARGET", default=""), _read_session_key_default(implement_tmpdir=implement_tmpdir, key="FORKED_TARGET", default=""), "false"),
        "--repo-unavailable", _first_nonempty(_read_kv_file(path=bootstrap_file, key="REPO_UNAVAILABLE", default=""), _read_session_key_default(implement_tmpdir=implement_tmpdir, key="REPO_UNAVAILABLE", default=""), "false"),
        "--deferred", _first_nonempty(_read_kv_file(path=bootstrap_file, key="DEFERRED", default=""), _read_kv_file(path=seed_file, key="DEFERRED", default=""), "false"),
        "--no-admin-fallback", _first_nonempty(args.no_admin_fallback, _read_kv_file(path=seed_file, key="NO_ADMIN_FALLBACK", default=""), "false"),
        "--no-logs-commit", _first_nonempty(args.no_logs_commit, _read_kv_file(path=seed_file, key="NO_LOGS_COMMIT", default=""), "false"),
        "--expected-session-id", expected_session_id,
        "--expected-tmpdir-basename-prefix", _clone_expected_tmpdir_prefix(),
        "--stall-tracking", args.stall_tracking or "false",
        "--stall-step", args.stall_step,
        "--bail-reason", args.bail_reason,
        "--bail-failure-detail-log", args.bail_failure_detail_log,
    ])


def _ship_route_exit_fail(*, message: str, handoff: Path) -> int:
    with contextlib.suppress(FileNotFoundError):
        handoff.unlink()
    print(f"ship route-exit: {message}", file=sys.stderr)
    return 2


def _read_ship_route_exit_code(*, args: argparse.Namespace, default_file: Path) -> tuple[int | None, str]:
    file_path = Path(args.exit_code_file) if args.exit_code_file else default_file
    if file_path.is_file():
        raw = file_path.read_text(encoding="utf-8", errors="replace").strip()
        try:
            return int(raw), ""
        except ValueError:
            return None, f"invalid exit-code sidecar: {file_path}"
    if args.exit_code is not None:
        return int(args.exit_code), ""
    return None, f"missing exit-code sidecar: {file_path}"


def _read_ship_route_json(path: Path) -> tuple[dict[str, object] | None, str]:
    if not path.is_file():
        return None, f"missing json sidecar: {path}"
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"malformed json sidecar: {exc}"
    if not isinstance(raw, dict):
        return None, "json sidecar is not an object"
    return cast("dict[str, object]", raw), ""


def _ship_route_required_str(*, payload: Mapping[str, object], key: str) -> tuple[str, str]:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        return "", f"missing required JSON field: {key}"
    return value, ""


def _classify_ship_needs_user_reason(reason: str) -> str:
    if reason == "oos-filing":
        return "oos-pipeline"
    if reason in _SHIP_ROUTE_EXIT_AUTONOMOUS_REASONS or reason.startswith("ci-local-unfixable:"):
        return "ci-fix"
    return "operator-bail"


def _ship_route_conflict_handoff_fields(implement_tmpdir: Path) -> dict[str, str]:
    state_file = implement_tmpdir / "ship-pr-state.sh"
    resume_phase = _read_kv_file(path=state_file, key="RESUME_PHASE", default="")
    caller_kind = _read_kv_file(path=state_file, key="CALLER_KIND", default="")
    conflict_files = _read_kv_file(path=state_file, key="CONFLICT_FILES", default="")
    if (
        resume_phase == config.SHIP_PR_RRR_RESUME_PHASE
        and caller_kind == config.SHIP_PR_PRE_PUSH_CALLER_KIND
        and conflict_files
    ):
        return {
            "RESUME_PHASE": resume_phase,
            "CALLER_KIND": caller_kind,
            "CONFLICT_FILES": conflict_files,
        }
    return {}


def _ship_route_phase14_reship_pending(
    *,
    implement_tmpdir: Path,
    payload: Mapping[str, object],
    exit_code: int,
) -> bool:
    if exit_code != SHIP_ROUTE_EXIT_STALLED:
        return False
    if payload.get("detail") != config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED:
        return False
    phase14_flag = implement_tmpdir / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME
    return phase14_flag.is_file() and not phase14_flag.is_symlink()


def _ship_route_adjust_stalled_action(
    *,
    implement_tmpdir: Path,
    payload: Mapping[str, object],
    exit_code: int,
    action: str,
) -> tuple[str, dict[str, str]]:
    if exit_code != SHIP_ROUTE_EXIT_STALLED:
        return action, {}
    route_fields = _ship_route_conflict_handoff_fields(implement_tmpdir)
    if route_fields:
        return "conflict-fix", route_fields
    if _ship_route_phase14_reship_pending(
        implement_tmpdir=implement_tmpdir,
        payload=payload,
        exit_code=exit_code,
    ):
        return "reship", {}
    return action, {}


def _classify_ship_route_exit(*, exit_code: int, payload: dict[str, object]) -> tuple[str, str]:
    outcome, error = _ship_route_required_str(payload=payload, key="outcome")
    if error:
        return "", error
    if exit_code == SHIP_ROUTE_EXIT_NEEDS_USER:
        reason, error = _ship_route_required_str(payload=payload, key="needs_user_reason")
        return ("", error) if error else (_classify_ship_needs_user_reason(reason), "")
    actions = {
        0: "complete" if outcome == "OK" else "reship",
        1: "tool-failure" if outcome == "INTERNAL_ERROR" else "",
        SHIP_ROUTE_EXIT_STALLED: "stall",
        SHIP_ROUTE_EXIT_TRANSIENT: "transient",
    }
    action = actions.get(exit_code)
    if action:
        return action, ""
    if exit_code == 1:
        return "", "exit 1 requires outcome=INTERNAL_ERROR"
    return "", f"unsupported driver exit code: {exit_code}"


def _ship_route_safe_line(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def _ship_route_detail_needs_file(detail: str) -> bool:
    return "\n" in detail or "\r" in detail or len(detail) > SHIP_ROUTE_DETAIL_FILE_MAX


def _write_ship_route_handoff(
    *,
    implement_tmpdir: Path,
    payload: Mapping[str, object],
    action: str,
    delay_seconds: int = 0,
    route_fields: Mapping[str, str] | None = None,
) -> None:
    handoff = implement_tmpdir / ".ship-route-exit-handoff.env"
    detail_file = implement_tmpdir / ".ship-route-exit-detail.txt"
    lines: list[str] = []
    key_map = {
        "failed_run_id": "FAILED_RUN_ID",
        "needs_user_reason": "NEEDS_USER_REASON",
    }
    for source_key, out_key in key_map.items():
        value = _ship_route_safe_line(payload.get(source_key, ""))
        if value:
            lines.append(f"{out_key}={value}")
    detail_raw = payload.get("detail", "")
    detail = detail_raw if isinstance(detail_raw, str) else str(detail_raw or "")
    if detail:
        if _ship_route_detail_needs_file(detail):
            _write_text_atomic(path=detail_file, text=detail if detail.endswith("\n") else f"{detail}\n")
            lines.append(f"DETAIL_FILE={detail_file}")
        else:
            lines.append(f"DETAIL={_ship_route_safe_line(detail)}")
    lines.extend(f"{key}={_ship_route_safe_line(payload[key])}" for key in _SHIP_ROUTE_EXIT_LEDGER_KEYS if key in payload)
    if route_fields:
        lines.extend(
            f"{key}={_ship_route_safe_line(value)}"
            for key, value in route_fields.items()
            if _ship_route_safe_line(value)
        )
    if action in {"ci-fix", "reship"}:
        with contextlib.suppress(OSError):
            (implement_tmpdir / _PRE_FIX_REBASE_OK_SENTINEL).unlink()
        lines.append("PRE_FIX_REBASE_REQUIRED=true")
    lines.append(f"NEXT_ACTION={action}")
    if delay_seconds:
        lines.append(f"RESHIP_DELAY_SECONDS={delay_seconds}")
    _write_text_atomic(path=handoff, text="\n".join(lines) + "\n")


def _ship_route_read_retry_count(path: Path) -> int:
    if not path.is_file():
        return 0
    with contextlib.suppress(ValueError, OSError, UnicodeDecodeError):
        return int(path.read_text(encoding="utf-8").strip() or "0")
    return 0


def _ship_route_write_retry_count(*, path: Path, value: int) -> None:
    _write_text_atomic(path=path, text=f"{value}\n")


def _ship_route_seed_transient_stall(implement_tmpdir: Path) -> None:
    result = _run_cli_capture([
        "stall-recovery",
        "seed-terminal-state",
        "--implement-tmpdir",
        str(implement_tmpdir),
        "--stall-step",
        "transient-retry-cap",
        "--phase",
        "ci-initial",
    ])
    if result.returncode != 0:
        print(
            "ship route-exit: transient retry-cap stall seed failed; continuing with NEXT_ACTION=stall",
            file=sys.stderr,
        )
        _forward_child_output_to_stderr(result)


def _ship_pre_fix_fail(message: str) -> int:
    print(f"ship pre-fix-rebase: {message}", file=sys.stderr)
    return 2


def _ship_pre_fix_resolve_tmpdir(raw_tmpdir: str) -> Path | None:
    if not raw_tmpdir:
        return None
    path = Path(raw_tmpdir)
    if not path.is_dir():
        return None
    return path


def _ship_pre_fix_cwd(raw_cwd: str) -> str:
    if raw_cwd:
        return str(Path(raw_cwd))
    repo_root = _resolve_repo_root()
    return str(repo_root) if repo_root is not None else str(Path.cwd())


def _ship_pre_fix_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _ship_pre_fix_read_state(implement_tmpdir: Path) -> tuple[dict[str, str], str]:
    state_file = implement_tmpdir / "ship-pr-state.sh"
    if not state_file.is_file():
        return {}, "ship-pr-state.sh is missing"
    keys = (
        "BRANCH_NAME",
        "ISSUE_NUMBER",
        "RUN_ID",
        "REPO",
        "REPO_UNAVAILABLE",
        "FORKED_TARGET",
        "MERGE",
        "DRAFT",
        "MANIFEST_PATH",
        "TOOL_LABEL",
        "NO_ADMIN_FALLBACK",
        "NO_LOGS_COMMIT",
        "PR_NUMBER",
        "PR_URL",
        "PR_TITLE",
        "MERGE_RESULT",
        "PR_CLOSED",
        "DESIGN_ONLY_DONE",
        "DEFERRED",
        "DONE_RENAME_APPLIED",
        "STALL_TRACKING",
        "STALL_STEP",
        "EXPECTED_SESSION_ID",
        "EXPECTED_TMPDIR_BASENAME_PREFIX",
        "REBASE_COUNT",
        "FIX_ATTEMPTS",
        "ITERATION",
        "TRANSIENT_RETRIES",
        "OOS_PENDING",
    )
    values = {key: _read_kv_file(path=state_file, key=key, default="") for key in keys}
    if not values["REPO"]:
        return values, "REPO is missing from ship-pr-state.sh"
    if not values["RUN_ID"]:
        return values, "RUN_ID is missing from ship-pr-state.sh"
    return values, ""


def _ship_pre_fix_clear_ok_sentinel(implement_tmpdir: Path) -> None:
    with contextlib.suppress(OSError):
        (implement_tmpdir / _PRE_FIX_REBASE_OK_SENTINEL).unlink()


def _ship_pre_fix_write_ok_sentinel(implement_tmpdir: Path) -> None:
    _write_text_atomic(path=implement_tmpdir / _PRE_FIX_REBASE_OK_SENTINEL, text="PRE_FIX_REBASE_OK=true\n")


def _ship_pre_fix_flag_fields(implement_tmpdir: Path) -> dict[str, str]:
    flag = implement_tmpdir / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME
    if not flag.is_file() or flag.is_symlink():
        return {}
    fields: dict[str, str] = {}
    try:
        text = flag.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep and key and key not in fields:
            fields[key] = value.strip()
    return fields


def _ship_pre_fix_phase14_skip_allowed(implement_tmpdir: Path) -> bool:
    fields = _ship_pre_fix_flag_fields(implement_tmpdir)
    return (
        fields.get("RESUME_PHASE") == config.SHIP_PR_RRR_RESUME_PHASE
        and fields.get("REASON") in _PRE_FIX_PHASE14_ALLOWED_REASONS
    )


def _ship_pre_fix_int(value: str) -> int:
    with contextlib.suppress(ValueError):
        return int(value.strip() or "0")
    return 0


def _ship_pre_fix_context(*, implement_tmpdir: Path, state: Mapping[str, str]) -> RunContext:
    pr_number_raw = state.get("PR_NUMBER", "").strip()
    return RunContext(
        branch=state.get("BRANCH_NAME", ""),
        issue=state.get("ISSUE_NUMBER", ""),
        repo=state.get("REPO", ""),
        run_id=state.get("RUN_ID", ""),
        tmpdir=str(implement_tmpdir),
        merge=_ship_pre_fix_truthy(state.get("MERGE", "")),
        draft=_ship_pre_fix_truthy(state.get("DRAFT", "")),
        forked=_ship_pre_fix_truthy(state.get("FORKED_TARGET", "")),
        manifest_path=state.get("MANIFEST_PATH", ""),
        tool_label=state.get("TOOL_LABEL", "") or "claude",
        no_admin_fallback=_ship_pre_fix_truthy(state.get("NO_ADMIN_FALLBACK", "")),
        repo_unavailable=_ship_pre_fix_truthy(state.get("REPO_UNAVAILABLE", "")),
        pr_number=int(pr_number_raw) if pr_number_raw.isdigit() else None,
        state_file=str(implement_tmpdir / "ship-pr-state.sh"),
        no_logs_commit=_ship_pre_fix_truthy(state.get("NO_LOGS_COMMIT", "")),
        merge_result=state.get("MERGE_RESULT", ""),
        pr_closed=_ship_pre_fix_truthy(state.get("PR_CLOSED", "")),
        design_only_done=_ship_pre_fix_truthy(state.get("DESIGN_ONLY_DONE", "")),
        stall_tracking=_ship_pre_fix_truthy(state.get("STALL_TRACKING", "")),
        stall_step=state.get("STALL_STEP", ""),
        done_rename_applied=_ship_pre_fix_truthy(state.get("DONE_RENAME_APPLIED", "")),
        issue_number=state.get("ISSUE_NUMBER", ""),
        pr_title=state.get("PR_TITLE", ""),
        pr_url=state.get("PR_URL", ""),
        expected_session_id=state.get("EXPECTED_SESSION_ID", ""),
        expected_tmpdir_basename_prefix=state.get("EXPECTED_TMPDIR_BASENAME_PREFIX", ""),
        deferred=_ship_pre_fix_truthy(state.get("DEFERRED", "")),
        oos_pending=_ship_pre_fix_truthy(state.get("OOS_PENDING", "true")),
    )


def _ship_pre_fix_patch_handoff(*, implement_tmpdir: Path, patch: Mapping[str, str]) -> None:
    handoff = implement_tmpdir / ".ship-route-exit-handoff.env"
    existing: dict[str, str] = {}
    if handoff.is_file():
        for line in handoff.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key and key not in existing:
                existing[key] = value
    existing.update({key: _ship_route_safe_line(value) for key, value in patch.items() if _ship_route_safe_line(value)})
    _write_text_atomic(path=handoff, text="\n".join(f"{key}={value}" for key, value in existing.items()) + "\n")


def _ship_pre_fix_emit(*, status: str, action: str, detail: str = "") -> int:
    _emit_kv(key="PRE_FIX_REBASE_STATUS", value=status)
    _emit_kv(key="NEXT_ACTION", value=action)
    if detail:
        _emit_kv(key="DETAIL", value=_ship_route_safe_line(detail))
    return 0


def _ship_pre_fix_write_conflict_state(
    *,
    implement_tmpdir: Path,
    state: Mapping[str, str],
    resume_phase: str,
    caller_kind: str,
    conflict_files: str,
) -> None:
    ctx = _ship_pre_fix_context(implement_tmpdir=implement_tmpdir, state=state)
    ship._write_ship_state(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        ctx,
        phase="rebase",
        iteration=_ship_pre_fix_int(state.get("ITERATION", "")),
        rebase_count=_ship_pre_fix_int(state.get("REBASE_COUNT", "")),
        fix_attempts=_ship_pre_fix_int(state.get("FIX_ATTEMPTS", "")),
        transient_retries=_ship_pre_fix_int(state.get("TRANSIENT_RETRIES", "")),
        resume_phase=resume_phase,
        caller_kind=caller_kind,
        extra_fields={"CONFLICT_FILES": conflict_files},
    )


def _ship_pre_fix_validate_checkout(*, state: Mapping[str, str], cwd: str) -> str | None:
    current_branch = git.try_current_branch(proc, cwd=cwd)
    if current_branch != state["BRANCH_NAME"]:
        return f"checked-out branch {current_branch!r} does not match ship-pr-state.sh BRANCH_NAME {state['BRANCH_NAME']!r}"
    if current_branch in {"main", "master"} and not _ship_pre_fix_truthy(state.get("FORKED_TARGET", "")):
        return f"refusing pre-fix rebase on checked-out branch {current_branch!r} without a forked target"
    current_repo = gh.resolve_repo(proc, cwd=cwd)
    if current_repo != state["REPO"]:
        return f"checked-out repo {current_repo!r} does not match ship-pr-state.sh REPO {state['REPO']!r}"
    return None


def _ship_pre_fix_rebase_step(
    *, implement_tmpdir: Path, state: Mapping[str, str], cwd: str
) -> tuple[str | None, str, str]:
    error = _ship_pre_fix_validate_checkout(state=state, cwd=cwd)
    if error:
        return error, "", ""
    route_fields = _ship_route_conflict_handoff_fields(implement_tmpdir)
    if git.rebase_in_progress(proc, cwd=cwd):
        if not route_fields:
            return None, "stall", "stall"
        _ship_pre_fix_write_conflict_state(
            implement_tmpdir=implement_tmpdir,
            state=state,
            resume_phase=route_fields["RESUME_PHASE"],
            caller_kind=route_fields["CALLER_KIND"],
            conflict_files=route_fields["CONFLICT_FILES"],
        )
        _ship_pre_fix_patch_handoff(
            implement_tmpdir=implement_tmpdir,
            patch={
                **route_fields,
                "PRE_FIX_REBASE_STATUS": "conflict",
                "NEXT_ACTION": "conflict-fix",
            },
        )
        return None, "conflict", "conflict-fix"
    if route_fields:
        _ship_pre_fix_write_conflict_state(
            implement_tmpdir=implement_tmpdir,
            state=state,
            resume_phase=route_fields["RESUME_PHASE"],
            caller_kind=route_fields["CALLER_KIND"],
            conflict_files=route_fields["CONFLICT_FILES"],
        )
        _ship_pre_fix_patch_handoff(
            implement_tmpdir=implement_tmpdir,
            patch={
                **route_fields,
                "PRE_FIX_REBASE_STATUS": "conflict",
                "NEXT_ACTION": "conflict-fix",
            },
        )
        return None, "conflict", "conflict-fix"
    if _ship_pre_fix_phase14_skip_allowed(implement_tmpdir):
        return None, "skip", "continue"
    base_remote = "upstream" if _ship_pre_fix_truthy(state.get("FORKED_TARGET", "")) else "origin"
    rebase_result = rebase.rebase_and_push(
        runner=proc,
        repo=state["REPO"],
        run_id=state["RUN_ID"],
        cwd=cwd,
        tmpdir=str(implement_tmpdir),
        base_remote=base_remote,
        base_ref="main",
        defer_push=False,
        allow_conflict_fix=True,
        enable_pre_push_handoff=True,
    )
    if getattr(rebase_result, "rebased", False):
        ship._patch_ship_state_keys(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            state_file=implement_tmpdir / "ship-pr-state.sh",
            patch={"REBASE_COUNT": str(_ship_pre_fix_int(state.get("REBASE_COUNT", "")) + 1)},
        )
    return None, "ok", "continue"


def _ship_pre_fix_handle_conflict(
    *, implement_tmpdir: Path, state: Mapping[str, str], exc: PrePushConflictHandoff
) -> str | None:
    try:
        _ship_pre_fix_write_conflict_state(
            implement_tmpdir=implement_tmpdir,
            state=state,
            resume_phase=exc.resume_phase,
            caller_kind=exc.caller_kind,
            conflict_files=exc.conflict_csv,
        )
        _ship_pre_fix_patch_handoff(
            implement_tmpdir=implement_tmpdir,
            patch={
                "RESUME_PHASE": exc.resume_phase,
                "CALLER_KIND": exc.caller_kind,
                "CONFLICT_FILES": exc.conflict_csv,
                "PRE_FIX_REBASE_STATUS": "conflict",
                "NEXT_ACTION": "conflict-fix",
            },
        )
    except (OSError, ShipError) as write_exc:
        return f"cannot write conflict handoff: {write_exc}"
    return None


def _ship_pre_fix_rebase_request(argv: list[str] | None) -> tuple[ShipPreFixRebaseRequest | None, str | None]:
    parser = argparse.ArgumentParser(prog="cli.py ship pre-fix-rebase")
    parser.add_argument("--implement-tmpdir", default="")
    parser.add_argument("--cwd", default="")
    args = parser.parse_args(argv)
    raw_tmpdir = args.implement_tmpdir or os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    implement_tmpdir = _ship_pre_fix_resolve_tmpdir(raw_tmpdir)
    if implement_tmpdir is None:
        return None, "--implement-tmpdir is required and must be an existing directory"
    _ship_pre_fix_clear_ok_sentinel(implement_tmpdir)
    state, error = _ship_pre_fix_read_state(implement_tmpdir)
    if error:
        return None, error
    cwd = _ship_pre_fix_cwd(args.cwd)
    return ShipPreFixRebaseRequest(implement_tmpdir=implement_tmpdir, state=state, cwd=cwd), None


def _ship_pre_fix_rebase_run(request: ShipPreFixRebaseRequest) -> tuple[ShipPreFixRebaseResult | None, str | None]:
    result: ShipPreFixRebaseResult | None = None
    error: str | None = None
    try:
        error, status, action = _ship_pre_fix_rebase_step(
            implement_tmpdir=request.implement_tmpdir, state=request.state, cwd=request.cwd
        )
        if not error:
            result = ShipPreFixRebaseResult(status=status, action=action)
    except PrePushConflictHandoff as exc:
        error = _ship_pre_fix_handle_conflict(
            implement_tmpdir=request.implement_tmpdir,
            state=request.state,
            exc=exc,
        )
        if not error:
            result = ShipPreFixRebaseResult(status="conflict", action="conflict-fix")
    except (Stalled, TransientNetworkError) as exc:
        result = ShipPreFixRebaseResult(status="stall", action="stall", detail=str(exc))
    except (OSError, ShipError) as exc:
        error = f"handoff setup failed: {exc}"
    return result, error


def ship_pre_fix_rebase_main(argv: list[str] | None = None) -> int:
    request, error = _ship_pre_fix_rebase_request(argv)
    if error or request is None:
        return _ship_pre_fix_fail(error or "--implement-tmpdir is required and must be an existing directory")
    result, error = _ship_pre_fix_rebase_run(request)
    if error or result is None:
        return _ship_pre_fix_fail(error or "pre-fix rebase did not produce a result")
    if result.action in {"continue", "conflict-fix"}:
        try:
            _ship_pre_fix_write_ok_sentinel(request.implement_tmpdir)
        except OSError as exc:
            return _ship_pre_fix_fail(f"cannot write pre-fix rebase sentinel: {exc}")
    return _ship_pre_fix_emit(status=result.status, action=result.action, detail=result.detail)


def ship_route_exit_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py ship route-exit")
    parser.add_argument("--implement-tmpdir", default="")
    parser.add_argument("--json-file", default="")
    parser.add_argument("--exit-code-file", default="")
    parser.add_argument("--exit-code", type=int)
    args = parser.parse_args(argv)
    raw_tmpdir = args.implement_tmpdir or os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    if not raw_tmpdir:
        print("ship route-exit: --implement-tmpdir is required or IMPLEMENT_TMPDIR must be set", file=sys.stderr)
        return 2
    implement_tmpdir = Path(raw_tmpdir)
    handoff = implement_tmpdir / ".ship-route-exit-handoff.env"
    json_file = Path(args.json_file) if args.json_file else implement_tmpdir / ".step-8-ship-handoff.json"
    exit_code_file = implement_tmpdir / ".step-8-ship-handoff.rc"
    exit_code, error = _read_ship_route_exit_code(args=args, default_file=exit_code_file)
    payload = None
    if not error and exit_code is not None:
        payload, error = _read_ship_route_json(json_file)
    if error or exit_code is None or payload is None:
        message = error or ("missing exit code" if exit_code is None else "missing json")
        return _ship_route_exit_fail(message=message, handoff=handoff)
    action, error = _classify_ship_route_exit(exit_code=exit_code, payload=payload)
    if error:
        return _ship_route_exit_fail(message=error, handoff=handoff)
    action, route_fields = _ship_route_adjust_stalled_action(
        implement_tmpdir=implement_tmpdir,
        payload=payload,
        exit_code=exit_code,
        action=action,
    )
    delay_seconds = 0
    if action == "transient":
        count_file = implement_tmpdir / "ship-pr-net-retries-python.count"
        retry = _ship_route_read_retry_count(count_file) + 1
        try:
            _ship_route_write_retry_count(path=count_file, value=retry)
        except OSError as exc:
            return _ship_route_exit_fail(message=f"cannot persist transient retry counter: {exc}", handoff=handoff)
        if retry >= SHIP_ROUTE_TRANSIENT_STALL_RETRY:
            _ship_route_seed_transient_stall(implement_tmpdir)
            action = "stall"
        else:
            delay_seconds = 30
            time.sleep(delay_seconds)
            action = "reship"
    try:
        _write_ship_route_handoff(
            implement_tmpdir=implement_tmpdir,
            payload=payload,
            action=action,
            delay_seconds=delay_seconds,
            route_fields=route_fields,
        )
    except OSError as exc:
        return _ship_route_exit_fail(message=f"cannot write route-exit handoff: {exc}", handoff=handoff)
    _emit_kv(key="NEXT_ACTION", value=action)
    return 0


def ship_pre_driver_main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(prog="cli.py ship pre-driver").parse_args(argv)
    raw_tmpdir = os.environ.get("IMPLEMENT_TMPDIR", "")
    if not raw_tmpdir:
        print("IMPLEMENT_TMPDIR required", file=sys.stderr)
        _emit_kv(key="NEXT_ACTION", value="halt-seed")
        return 2
    implement_tmpdir = Path(raw_tmpdir)
    _rehydrate_plugin_root(implement_tmpdir)
    state_file = implement_tmpdir / "ship-pr-state.sh"

    guard = _run_cli_capture(["implement", "step-8-python-guard"])
    _forward_child_output_to_stderr(guard)
    if guard.returncode != 0:
        _emit_kv(key="NEXT_ACTION", value="stall")
        return 4

    if not _ship_state_has_shell_kv_entries(state_file):
        seed = _run_cli_capture(["implement", "step-8-seed-initial"])
        _forward_child_output_to_stderr(seed)
        if seed.returncode != 0:
            _emit_kv(key="NEXT_ACTION", value="halt-seed")
            return seed.returncode

    oos = _run_cli_capture(["oos", "file", "--implement-tmpdir", str(implement_tmpdir)])
    if oos.returncode != 0:
        _forward_child_output_to_stderr(oos)
        payload: object
        try:
            payload = json.loads((oos.stdout or "").strip() or "{}")
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict) and payload.get("status") == "security_sidecar_present":
            _emit_kv(key="NEXT_ACTION", value="oos-pipeline")
            return oos.returncode
        _emit_kv(key="NEXT_ACTION", value="halt-oos")
        return oos.returncode
    _forward_child_output_to_stderr(oos)

    _emit_kv(key="NEXT_ACTION", value="ship")
    return 0


def step8_ship_main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(prog="cli.py implement step-8-ship").parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    state_file = implement_tmpdir / "ship-pr-state.sh"
    def state(*, key: str, default: str = "") -> str:
        return _read_kv_file(path=state_file, key=key, default=default)
    branch = os.environ.get("BRANCH_NAME", "") or state(key="BRANCH_NAME")
    issue = os.environ.get("ISSUE_NUMBER", "") or state(key="ISSUE_NUMBER")
    run_id = os.environ.get("RUN_ID", "") or state(key="RUN_ID")
    repo = os.environ.get("REPO", "") or state(key="REPO")
    merge = _env_value(name="merge") or state(key="MERGE", default="false") or "false"
    draft = _env_value(name="draft") or state(key="DRAFT", default="false") or "false"
    forked = _env_value(name="forked_target") or state(key="FORKED_TARGET", default="false") or "false"
    repo_unavailable = os.environ.get("REPO_UNAVAILABLE", "") or state(key="REPO_UNAVAILABLE", default="false") or "false"
    manifest = os.environ.get("MANIFEST_PATH", "") or state(key="MANIFEST_PATH")
    tool = _env_value(name="coder") or state(key="TOOL_LABEL", default="claude") or "claude"
    no_admin = _env_value(name="no_admin_fallback") or state(key="NO_ADMIN_FALLBACK", default="false") or "false"
    no_logs = _env_value(name="no_logs_commit") or state(key="NO_LOGS_COMMIT", default="false") or "false"
    for name, value in (("BRANCH_NAME", branch), ("RUN_ID", run_id), ("REPO", repo)):
        if not value:
            print(f"step-8-ship: missing {name} (not exported and absent from ship-pr-state.sh)", file=sys.stderr)
            return 2
    guard_rc = step8_python_guard_main([])
    if guard_rc != 0:
        return guard_rc
    print("→ phantom-probe: 8-pre-ship", file=sys.stderr)
    with contextlib.redirect_stdout(sys.stderr):
        _emit_phantom_probe_with_warn("8-pre-ship")
    expected_session_id = (implement_tmpdir / "session-id").read_text(encoding="utf-8", errors="replace").strip() if (implement_tmpdir / "session-id").is_file() else ""
    return _run_cli_forward([
        "ship", "pr", "--branch", branch, "--issue", issue, "--repo", repo, "--run-id", run_id,
        "--tmpdir", str(implement_tmpdir), "--manifest-path", manifest, "--state-file", str(state_file),
        "--tool-label", tool, "--merge", merge, "--draft", draft, "--forked", forked,
        "--repo-unavailable", repo_unavailable, "--no-admin-fallback", no_admin or "false", "--no-logs-commit", no_logs or "false",
        "--expected-session-id", expected_session_id, "--expected-tmpdir-basename-prefix", _clone_expected_tmpdir_prefix(),
    ])


def _step8_oos_checkpoint_log_failure(*, implement_tmpdir: Path, rc: int, err: Path) -> None:
    log_file = implement_tmpdir / "execution-issues.md"
    log_text = log_file.read_text(encoding="utf-8", errors="replace") if log_file.is_file() else ""
    if rc == 1:
        already = "Step step-8-oos-checkpoint —" in log_text or (
            "step-8-oos-checkpoint" in log_text and "step-8-oos-checkpoint-validation" not in log_text
        )
    else:
        already = "step-8-oos-checkpoint-validation" in log_text
    if rc != 0 and not already:
        site = "step-8-oos-checkpoint" if rc == 1 else "step-8-oos-checkpoint-validation"
        _invoke_cli([
            "run-log",
            "append-failure",
            "--log",
            str(log_file),
            "--site",
            site,
            "--tool",
            "python/cli.py oos disposition-checkpoint",
            "--exit-code",
            str(rc),
            "--category",
            "Tool Failures",
            "--output-file",
            str(err),
            "--redact",
        ])


def _step8_oos_checkpoint_filed_count(*, implement_tmpdir: Path, run_id: str) -> int:
    ndjson = implement_tmpdir / "larch-logs" / "implement" / run_id / "oos-issues.ndjson"
    if ndjson.is_file():
        return len(oos_filer._ndjson_filed_evidence(tmpdir=implement_tmpdir, run_id=run_id))  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    return 0


def _step8_oos_checkpoint_bookkeeping(implement_tmpdir: Path) -> tuple[bool, str]:
    run_id = file_oos.resolve_implement_run_id_for_disposition(implement_tmpdir)
    if not run_id:
        print("step-8-oos-checkpoint: bookkeeping failed: cannot resolve canonical run id", file=sys.stderr)
        return False, ""
    stats_path = implement_tmpdir / "larch-logs" / "implement" / run_id / "run-statistics.md"
    try:
        filed_count = _step8_oos_checkpoint_filed_count(implement_tmpdir=implement_tmpdir, run_id=run_id)
        stamped = oos_filer._stamp_manifest(implement_tmpdir, run_id, value=True)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        if not stamped:
            raise RuntimeError("manifest stamp returned false")
        _ = oos_filer._write_run_statistics(tmpdir=implement_tmpdir, run_id=run_id, filed_count=filed_count)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        ship._patch_ship_state_keys(state_file=implement_tmpdir / "ship-pr-state.sh", patch={"OOS_PENDING": "false"})  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    except Exception as exc:
        print(f"step-8-oos-checkpoint: bookkeeping failed: {exc}", file=sys.stderr)
        with contextlib.suppress(Exception):
            _ = oos_filer._stamp_manifest(implement_tmpdir, run_id, value=False)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        with contextlib.suppress(OSError):
            if stats_path.is_file():
                stats_path.unlink()
        return False, run_id
    return True, run_id


def step8_oos_checkpoint_main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(prog="cli.py implement step-8-oos-checkpoint").parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    err = implement_tmpdir / "oos-disposition-checkpoint.stderr.log"
    args = ["oos", "disposition-checkpoint", "--implement-tmpdir", str(implement_tmpdir)]
    if os.environ.get("DESIGN_TMPDIR"):
        args.extend(["--design-tmpdir", os.environ["DESIGN_TMPDIR"]])
    result = subprocess.run([sys.executable, str(_current_cli_path()), *args], capture_output=True, text=True, check=False)
    if result.stderr:
        existing = err.read_text(encoding="utf-8", errors="replace") if err.is_file() else ""
        err.write_text(existing + result.stderr, encoding="utf-8")
    _step8_oos_checkpoint_log_failure(implement_tmpdir=implement_tmpdir, rc=result.returncode, err=err)
    if result.returncode != 0:
        _emit_kv(key="OOS_CHECKPOINT_RC", value=result.returncode)
        _emit_kv(key="NEXT_ACTION", value="stall")
        return 0
    ok, _run_id = _step8_oos_checkpoint_bookkeeping(implement_tmpdir)
    if ok:
        with contextlib.suppress(Exception):
            execution_issues.refresh_execution_issues(implement_tmpdir, best_effort=True)
        _emit_kv(key="OOS_CHECKPOINT_RC", value=0)
        _emit_kv(key="NEXT_ACTION", value="reship")
    else:
        _emit_kv(key="OOS_CHECKPOINT_RC", value=2)
        _emit_kv(key="NEXT_ACTION", value="stall")
    return 0
