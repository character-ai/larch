"""Ship-pr state constants, validators, and I/O helpers."""
# pyright: reportUnusedFunction=false

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from contextlib import suppress
from pathlib import Path

from larch.core import config
from larch.core import logging_util
from larch.core.run_context import RunContext
from larch.errors import ShipError
from larch.outcomes import Outcome
from larch.report import progress_file
from larch.report import run_logs
from larch.state import finalize


_REPO_SLUG_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
_BRANCH_NAME_RE = re.compile(r"^[A-Za-z0-9._/\-]+$")
_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PR_URL_RE = re.compile(r"^https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+$")
_ALLOWED_EXTRA_FIELDS = {
    "CONFLICT_FILES",
    "EMERGENCY_REPAIR_BRANCH",
    "ORIGINAL_BRANCH_FORBIDDEN",
    "MAIN_REPAIR_RUN_ID",
    "MAIN_REPAIR_HEAD",
    "EMERGENCY_REPAIR_PR_NUMBER",
    "MAIN_HEALTH_REPAIR_COMMITTED",
    "MAIN_HEALTH_REPAIR_FAILED_RUN_ID",
    "MAIN_HEALTH_REPAIR_BASE_SHA",
    "MAIN_HEALTH_REPAIR_HEAD",
    "MAIN_HEALTH_HEAD_SHA",
}
_ALLOWED_SHIP_STATE_KEYS = frozenset({
    "PHASE",
    "BRANCH_NAME",
    "ISSUE_NUMBER",
    "RUN_ID",
    "REPO",
    "REPO_UNAVAILABLE",
    "FORKED_TARGET",
    "IMPLEMENT_TMPDIR",
    "MANIFEST_PATH",
    "MERGE",
    "DRAFT",
    "PR_CLOSED",
    "PR_NUMBER",
    "PR_URL",
    "PR_TITLE",
    "MERGE_RESULT",
    "CI_FIX_REBASE_PENDING",
    "CI_FIX_REBASE_PENDING_HEAD",
    "LAST_MONITORED_HEAD",
    "REBASE_COUNT",
    "FIX_ATTEMPTS",
    "ITERATION",
    "TRANSIENT_RETRIES",
    "RESUME_PHASE",
    "CALLER_KIND",
    "CONFLICT_FILES",
    "STALL_TRACKING",
    "STALL_STEP",
    "EXIT_CODE",
    "BAIL_REASON",
    "BAIL_NEEDS_USER_INPUT",
    "FAILED_RUN_ID",
    "BAIL_FAILURE_DETAIL_LOG",
    "EXPECTED_SESSION_ID",
    "EXPECTED_TMPDIR_BASENAME_PREFIX",
    "NO_LOGS_COMMIT",
    "NO_ADMIN_FALLBACK",
    "DESIGN_ONLY_DONE",
    "DEFERRED",
    "DONE_RENAME_APPLIED",
    "CI_PASSED",
    "TOOL_LABEL",
    "OOS_PENDING",
    "EMERGENCY_REPAIR_BRANCH",
    "ORIGINAL_BRANCH_FORBIDDEN",
    "MAIN_REPAIR_RUN_ID",
    "MAIN_REPAIR_HEAD",
    "EMERGENCY_REPAIR_PR_NUMBER",
    "MAIN_HEALTH_REPAIR_COMMITTED",
    "MAIN_HEALTH_REPAIR_FAILED_RUN_ID",
    "MAIN_HEALTH_REPAIR_BASE_SHA",
    "MAIN_HEALTH_REPAIR_HEAD",
    "MAIN_HEALTH_HEAD_SHA",
})
_TERMINAL_ONLY_STATE_KEYS = frozenset({
    "EXIT_CODE",
    "BAIL_REASON",
    "BAIL_NEEDS_USER_INPUT",
    "FAILED_RUN_ID",
    "BAIL_FAILURE_DETAIL_LOG",
})
_NON_STALL_STATE_KEYS = frozenset({"STALL_TRACKING", "STALL_STEP"})
_ALLOWED_RESUME_PHASES = {"", config.SHIP_PR_RRR_RESUME_PHASE}
_ALLOWED_CALLER_KINDS = {"", config.SHIP_PR_PRE_PUSH_CALLER_KIND}
_MIN_GH_SKIPPED_MERGE_SIGNALS = 2
_PYTHON_TRANSIENT_STALL_ATTEMPT = 4

INITIAL_SHIP_STATE_KEYS: tuple[str, ...] = (
    "PHASE",
    "BRANCH_NAME",
    "ISSUE_NUMBER",
    "RUN_ID",
    "REPO",
    "REPO_UNAVAILABLE",
    "FORKED_TARGET",
    "MERGE",
    "DRAFT",
    "DEFERRED",
    "PR_CLOSED",
    "DONE_RENAME_APPLIED",
    "STALL_TRACKING",
    "STALL_STEP",
    "BAIL_NEEDS_USER_INPUT",
    "BAIL_REASON",
    "BAIL_FAILURE_DETAIL_LOG",
    "CI_PASSED",
    "PR_NUMBER",
    "PR_URL",
    "PR_TITLE",
    "RESUME_PHASE",
    "CALLER_KIND",
    "REBASE_COUNT",
    "FIX_ATTEMPTS",
    "ITERATION",
    "TRANSIENT_RETRIES",
    "FAILED_RUN_ID",
    "MANIFEST_PATH",
    "TOOL_LABEL",
    "DESIGN_ONLY_DONE",
    "EXPECTED_SESSION_ID",
    "EXPECTED_TMPDIR_BASENAME_PREFIX",
    "NO_ADMIN_FALLBACK",
    "NO_LOGS_COMMIT",
    "IMPLEMENT_TMPDIR",
    "CI_FIX_REBASE_PENDING",
    "OOS_PENDING",
    "EMERGENCY_REPAIR_BRANCH",
    "ORIGINAL_BRANCH_FORBIDDEN",
    "MAIN_REPAIR_RUN_ID",
    "MAIN_REPAIR_HEAD",
    "EMERGENCY_REPAIR_PR_NUMBER",
    "MAIN_HEALTH_REPAIR_COMMITTED",
    "MAIN_HEALTH_REPAIR_FAILED_RUN_ID",
    "MAIN_HEALTH_REPAIR_BASE_SHA",
    "MAIN_HEALTH_REPAIR_HEAD",
    "MAIN_HEALTH_HEAD_SHA",
)


def _breadcrumb(*, step: str, detail: str = "") -> None:
    suffix = f": {detail}" if detail else ""
    logging_util.BreadcrumbWriter().emit(f"ship.py: {step}{suffix}")


def _progress_note(*, step: str, text: str) -> None:
    _ = progress_file.append_breadcrumb(Path.cwd(), "implement", step, text)


def _state_bool(*, value: bool) -> str:
    return "true" if value else "false"


def _state_bool_text(value: str) -> bool:
    return value.strip() == "true"


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _bool_arg(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _valid_repo_slug(value: str) -> bool:
    return bool(value and not value.startswith("-") and _REPO_SLUG_RE.fullmatch(value))


def _valid_branch_name(value: str) -> bool:
    if not value or value.startswith("-") or value.endswith("/"):
        return False
    return (
        _BRANCH_NAME_RE.fullmatch(value) is not None
        and ".." not in value
        and "//" not in value
        and "@{" not in value
    )


def _valid_pr_url(value: str) -> bool:
    return not value or _PR_URL_RE.fullmatch(value) is not None


def _valid_merge_result(value: str) -> str:
    return value if value in config.POST_MERGE_MERGE_RESULTS else config.MERGE_RESULT_DRIVER_ALREADY_MERGED


def _valid_state_merge_result(value: str) -> bool:
    return not value or value in config.MERGE_RESULTS or value in config.POST_MERGE_MERGE_RESULTS


def _terminal_exit_code(result: Outcome) -> str:
    return str(config.OUTCOME_EXIT_MAP.get(result, config.OUTCOME_EXIT_MAP[Outcome.STALLED]))


def _terminal_overlay_fields(
    *,
    ctx: RunContext,
    result: Outcome,
    step: str,
    failed_run_id: str = "",
    bail_failure_detail_log: str = "",
) -> dict[str, str]:
    return {
        "EXIT_CODE": _terminal_exit_code(result),
        "STALL_TRACKING": _state_bool(value=result is Outcome.STALLED),
        "STALL_STEP": step if result is Outcome.STALLED or step else "",
        "BAIL_REASON": ctx.final_bail_reason,
        "BAIL_NEEDS_USER_INPUT": _state_bool(value=ctx.bail_needs_user_input),
        "FAILED_RUN_ID": failed_run_id,
        "BAIL_FAILURE_DETAIL_LOG": bail_failure_detail_log,
    }


def _validate_ship_state_value(*, key: str, value: str) -> None:
    if "\n" in value or "\r" in value:
        raise ShipError(f"invalid newline in ship state value: {key}")
    if key == "BRANCH_NAME" and value and not _valid_branch_name(value):
        raise ShipError("invalid ship state BRANCH_NAME")
    if key == "PR_URL" and not _valid_pr_url(value):
        raise ShipError("invalid ship state PR_URL")
    if key == "MERGE_RESULT" and not _valid_state_merge_result(value):
        raise ShipError("invalid ship state MERGE_RESULT")


def _validate_conflict_csv(value: str) -> None:
    if not value:
        raise ShipError("invalid empty CONFLICT_FILES")
    for item in value.split(","):
        path = item.strip()
        if not path or path != item or path.startswith("/") or "\\" in path:
            raise ShipError("invalid CONFLICT_FILES entry")
        parts = Path(path).parts
        if ".." in parts or any(part in {"", "."} for part in parts):
            raise ShipError("invalid CONFLICT_FILES entry")
        if not re.fullmatch(r"[A-Za-z0-9._/\-]+", path):
            raise ShipError("invalid CONFLICT_FILES entry")


def _write_ship_state(
    ctx: RunContext,
    *,
    phase: str,
    iteration: int = 0,
    rebase_count: int = 0,
    fix_attempts: int = 0,
    transient_retries: int = 0,
    resume_phase: str | None = None,
    caller_kind: str | None = None,
    extra_fields: dict[str, str] | None = None,
    ci_fix_rebase_pending_head: str = "",
    last_monitored_head: str | None = None,
    terminal_outcome: Outcome | None = None,
    failed_run_id: str = "",
    bail_failure_detail_log: str = "",
) -> None:
    if not ctx.state_file:
        return
    if not _tmpdir_under_allowed_root(ctx.tmpdir):
        return
    path = Path(ctx.state_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    if path.is_symlink() or tmp.is_symlink():
        raise ShipError(f"refusing to write symlinked ship state path: {path}")
    if resume_phase is None:
        resume_phase = run_logs.read_state_kv(state_file=ctx.state_file, key="RESUME_PHASE") if path.is_file() else ""
    if caller_kind is None:
        caller_kind = run_logs.read_state_kv(state_file=ctx.state_file, key="CALLER_KIND") if path.is_file() else ""
    if resume_phase not in _ALLOWED_RESUME_PHASES:
        resume_phase = ""
    if caller_kind not in _ALLOWED_CALLER_KINDS:
        caller_kind = ""
    clear_handoff_keys = resume_phase == "" and caller_kind == ""
    run_id = run_logs.effective_run_id(ctx)
    if extra_fields:
        unexpected = set(extra_fields) - _ALLOWED_EXTRA_FIELDS
        if unexpected:
            raise ShipError(f"invalid ship state extra field: {sorted(unexpected)[0]}")
        if "CONFLICT_FILES" in extra_fields:
            _validate_conflict_csv(extra_fields["CONFLICT_FILES"])
    fields: dict[str, str] = {}
    if path.is_file():
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                if key in _ALLOWED_SHIP_STATE_KEYS and "\n" not in key and "\r" not in key:
                    fields[key] = value
        except (OSError, UnicodeDecodeError) as exc:
            raise ShipError(f"cannot read existing ship state: {path}") from exc
    if clear_handoff_keys:
        _ = fields.pop("CONFLICT_FILES", None)
    if terminal_outcome is None and phase != "done":
        for key in _TERMINAL_ONLY_STATE_KEYS:
            _ = fields.pop(key, None)
        if not ctx.stall_tracking:
            for key in _NON_STALL_STATE_KEYS:
                _ = fields.pop(key, None)
    fields.update({
        "PHASE": phase,
        "BRANCH_NAME": ctx.branch_name or ctx.branch,
        "ISSUE_NUMBER": ctx.issue_number or ctx.issue,
        "RUN_ID": run_id,
        "REPO": ctx.repo,
        "REPO_UNAVAILABLE": _state_bool(value=ctx.repo_unavailable),
        "FORKED_TARGET": _state_bool(value=ctx.forked_target or ctx.forked),
        "IMPLEMENT_TMPDIR": ctx.tmpdir,
        "MANIFEST_PATH": ctx.manifest_path,
        "MERGE": _state_bool(value=ctx.merge),
        "DRAFT": _state_bool(value=ctx.draft),
        "OOS_PENDING": _state_bool(value=ctx.oos_pending),
        "NO_ADMIN_FALLBACK": _state_bool(value=ctx.no_admin_fallback),
        "PR_CLOSED": _state_bool(value=ctx.pr_closed),
        "PR_NUMBER": "" if ctx.pr_number is None else str(ctx.pr_number),
        "PR_URL": ctx.pr_url,
        "PR_TITLE": ctx.pr_title,
        "MERGE_RESULT": ctx.merge_result,
        "CI_FIX_REBASE_PENDING": _state_bool(value=ctx.ci_fix_rebase_pending),
        "CI_FIX_REBASE_PENDING_HEAD": ci_fix_rebase_pending_head
        if ctx.ci_fix_rebase_pending
        else "",
        "REBASE_COUNT": str(rebase_count),
        "FIX_ATTEMPTS": str(fix_attempts),
        "ITERATION": str(iteration),
        "TRANSIENT_RETRIES": str(transient_retries),
        "RESUME_PHASE": resume_phase,
        "CALLER_KIND": caller_kind,
    })
    if last_monitored_head is not None:
        fields["LAST_MONITORED_HEAD"] = last_monitored_head
    if phase == "done":
        fields.update({
            "STALL_TRACKING": "false",
            "STALL_STEP": "",
            "BAIL_REASON": "",
            "BAIL_NEEDS_USER_INPUT": "false",
            "BAIL_FAILURE_DETAIL_LOG": "",
            "EXIT_CODE": "0",
            "FAILED_RUN_ID": "",
        })
    else:
        if terminal_outcome is not None or ctx.stall_tracking or "STALL_TRACKING" not in fields:
            fields["STALL_TRACKING"] = _state_bool(value=ctx.stall_tracking)
        if terminal_outcome is not None or ctx.stall_step or "STALL_STEP" not in fields:
            fields["STALL_STEP"] = ctx.stall_step
    if terminal_outcome is not None:
        fields.update(
            _terminal_overlay_fields(
                ctx=ctx,
                result=terminal_outcome,
                step=ctx.stall_step,
                failed_run_id=failed_run_id,
                bail_failure_detail_log=bail_failure_detail_log,
            ),
        )
    if extra_fields:
        fields.update(extra_fields)
    for key, value in fields.items():
        _validate_ship_state_value(key=key, value=str(value))
    with suppress(FileNotFoundError):
        tmp.unlink()
    data = "".join(f"{key}={value}\n" for key, value in fields.items())
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd: int | None = None
    try:
        fd = os.open(tmp, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = None
            _ = handle.write(data)
        _ = tmp.replace(path)
    except FileExistsError as exc:
        raise ShipError(f"refusing to overwrite existing ship state temp file: {tmp}") from exc
    finally:
        if fd is not None:
            os.close(fd)
        with suppress(OSError):
            if tmp.exists() and not tmp.is_symlink():
                tmp.unlink()


def _read_patchable_ship_state(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    if path.is_file():
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                if key in _ALLOWED_SHIP_STATE_KEYS and "\n" not in key and "\r" not in key:
                    fields[key] = value
        except (OSError, UnicodeDecodeError) as exc:
            raise ShipError(f"cannot read existing ship state: {path}") from exc
    return fields


def _write_patchable_ship_state(*, path: Path, tmp: Path, fields: Mapping[str, str]) -> None:
    data = "".join(f"{key}={value}\n" for key, value in fields.items())
    with suppress(FileNotFoundError):
        tmp.unlink()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd: int | None = None
    try:
        fd = os.open(tmp, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = None
            _ = handle.write(data)
        _ = tmp.replace(path)
    except OSError as exc:
        raise ShipError(f"cannot patch ship state: {path}") from exc
    finally:
        if fd is not None:
            os.close(fd)
        with suppress(OSError):
            if tmp.exists() and not tmp.is_symlink():
                tmp.unlink()


def _patch_ship_state_keys(*, state_file: Path, patch: dict[str, str]) -> None:  # pyright: ignore[reportUnusedFunction]
    unexpected = set(patch) - _ALLOWED_SHIP_STATE_KEYS
    if unexpected:
        raise ShipError(f"invalid ship state patch field: {sorted(unexpected)[0]}")
    path = Path(state_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    if path.is_symlink() or tmp.is_symlink():
        raise ShipError(f"refusing to write symlinked ship state path: {path}")
    fields = _read_patchable_ship_state(path)
    if not fields:
        raise ShipError(f"refusing patch-only ship state write: {path}")
    fields.update(patch)
    filtered = {key: value for key, value in fields.items() if key in _ALLOWED_SHIP_STATE_KEYS}
    for key, value in filtered.items():
        _validate_ship_state_value(key=key, value=str(value))
    _write_patchable_ship_state(path=path, tmp=tmp, fields=filtered)


def _state_file_has_kv(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            key, sep, _value = line.partition("=")
            if sep and _KEY_RE.fullmatch(key):
                return True
    except (OSError, UnicodeDecodeError):
        return True
    return False


def _path_under(*, parent: Path, child: Path) -> bool:
    try:
        resolved_parent = parent.resolve(strict=False)
        resolved_child = child.resolve(strict=False)
    except OSError:
        return False
    return resolved_child == resolved_parent or resolved_parent in resolved_child.parents


def _state_file_under_tmpdir(ctx: RunContext) -> bool:
    if not ctx.state_file:
        return True
    try:
        state_path = Path(ctx.state_file).resolve(strict=False)
        tmpdir = Path(ctx.tmpdir).resolve(strict=False)
    except OSError:
        return False
    return tmpdir in state_path.parents


def _tmpdir_under_allowed_root(tmpdir: str) -> bool:
    if not tmpdir:
        return False
    path = Path(tmpdir)
    if ".." in path.parts:
        return False
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        return False
    cache_root = finalize.cache_sessions_root()
    allowed_roots = (
        Path("/tmp").resolve(strict=False),  # noqa: S108 - parity allowlist for session tmpdirs.
        Path("/private/tmp").resolve(strict=False),
        Path("/var/folders").resolve(strict=False),
        Path("/private/var/folders").resolve(strict=False),
        cache_root.resolve(strict=False),
    )
    return any(resolved == root or root in resolved.parents for root in allowed_roots)


def _state_file_kv(path: str | None) -> dict[str, str]:
    if not path:
        return {}
    if Path(path).is_symlink():
        return {}
    try:
        return finalize.read_finalize_state(path)
    except ShipError:
        return {}
