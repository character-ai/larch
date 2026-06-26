"""Top-level ship-pr Python driver and CLI."""
# ruff: noqa: E402

from __future__ import annotations

import json
import sys


def _version_supported(version_info: object) -> bool:
    return tuple(version_info) >= (3, 11)  # type: ignore[arg-type]


if not _version_supported(sys.version_info):
    _VERSION_ERROR = "Python ship driver requires Python 3.11 or newer"
    print(
        json.dumps(
            {
                "detail": _VERSION_ERROR,
                "failed_run_id": "",
                "ledger_dispatcher": "",
                "ledger_exit_code": None,
                "ledger_failure_detail_log": "",
                "ledger_phase": "",
                "ledger_ready": False,
                "ledger_site": "",
                "ledger_step": "",
                "ledger_trigger": "",
                "merge_result": "",
                "needs_user_reason": "",
                "outcome": "STALLED",
                "pr_number": None,
                "pr_url": "",
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
    )
    print(f"ERROR: {_VERSION_ERROR}", file=sys.stderr)
    raise SystemExit(4)

import argparse
import os
import re
import traceback
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, TextIO, cast

import architectural_guidelines
import ci_monitor
from larch.core import config
import file_oos
import finalize
import gh
import git
from larch.core import logging_util
import merge
import pr
import pr_body
from larch.core import proc
import push
from larch.core import redact
import rebase
import run_logs
from larch.errors import NeedsUserInput, PrePushConflictHandoff, ShipError, Stalled, TransientNetworkError
from larch.outcomes import Outcome, StepResult
from larch.core.proc import Runner
from larch.core.run_context import RunContext


_REPO_SLUG_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
_BRANCH_NAME_RE = re.compile(r"^[A-Za-z0-9._/\-]+$")
_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PR_URL_RE = re.compile(r"^https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+$")
_ALLOWED_EXTRA_FIELDS = {"CONFLICT_FILES"}
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
)


@dataclass(frozen=True)
class ShipResult:
    outcome: Outcome
    needs_user_reason: str = ""
    failed_run_id: str = ""
    pr_number: int | None = None
    pr_url: str = ""
    merge_result: str = ""
    detail: str = ""
    ledger_ready: bool = False
    ledger_site: str = ""
    ledger_trigger: str = ""
    ledger_step: str = ""
    ledger_phase: str = ""
    ledger_dispatcher: str = ""
    ledger_exit_code: int | None = None
    ledger_failure_detail_log: str = ""

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "needs_user_reason": self.needs_user_reason,
            "failed_run_id": self.failed_run_id,
            "pr_number": self.pr_number,
            "pr_url": self.pr_url,
            "merge_result": self.merge_result,
            "detail": self.detail,
            "ledger_ready": self.ledger_ready,
            "ledger_site": self.ledger_site,
            "ledger_trigger": self.ledger_trigger,
            "ledger_step": self.ledger_step,
            "ledger_phase": self.ledger_phase,
            "ledger_dispatcher": self.ledger_dispatcher,
            "ledger_exit_code": self.ledger_exit_code,
            "ledger_failure_detail_log": self.ledger_failure_detail_log,
        }


class ShipRebaseVariant(StrEnum):
    GOTO_REBASE = "goto_rebase"
    MAIN_ADVANCED = "main_advanced"


@dataclass(frozen=True)
class ShipRebasePhaseResult:
    rebase_count: int
    terminal: ShipResult | None = None


@dataclass(frozen=True)
class ResumePlan:
    start: str
    iteration: int
    rebase_count: int
    fix_attempts: int
    transient_retries: int
    pr_number: int | None
    pr_url: str
    merge_result: str
    branch_name: str
    repo: str
    durable: run_logs.DurableFlags
    detail: str = ""


def _step_result_to_ship(
    step: StepResult,
    *,
    failed_run_id: str = "",
    pr_number: int | None = None,
    pr_url: str = "",
    merge_result: str = "",
    default_ledger_phase: str = "ci-merge",
    default_ledger_failure_detail_log: str = "",
) -> ShipResult:
    reason = ""
    detail = step.detail
    if step.outcome is Outcome.NEEDS_USER_INPUT:
        reason = detail or "needs-user-input"
        for token in config.NEEDS_USER_REASON_TOKENS:
            if reason == token or reason.startswith(f"{token}\n"):
                reason = token
                break
            if token == config.NEEDS_USER_CI_LOCAL_UNFIXABLE and reason.startswith(f"{token}:"):
                suffix = reason.split(":", 1)[1].splitlines()[0]
                if suffix and all(ch.isalnum() or ch in "_," or ch == "-" for ch in suffix):
                    reason = f"{token}:{suffix}"
                else:
                    reason = token
                break
            if reason.startswith(f"{token}:"):
                reason = token
                break
    ledger_ready = False
    ledger_site = ""
    ledger_trigger = ""
    ledger_step = ""
    ledger_phase = ""
    ledger_dispatcher = "ship-pr"
    ledger_exit_code: int | None = None
    ledger_failure_detail_log = ""
    ledger_triggers = {
        config.NEEDS_USER_CI_FIX_EXHAUSTED,
        config.NEEDS_USER_FIRST_FIXER_NON_HEALTH,
        config.NEEDS_USER_LOCAL_UNFIXABLE,
        config.NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX,
    }
    if step.ledger_ready:
        ledger_ready = True
        ledger_site = step.ledger_site
        ledger_trigger = step.ledger_trigger or reason
        if ledger_site.startswith("ship-pr-ci-") and ledger_trigger in {
            "main-agent-required",
            config.NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX,
        }:
            ledger_site = "ship-pr-internal"
            ledger_trigger = config.NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX
        ledger_step = step.ledger_step
        ledger_phase = step.ledger_phase or default_ledger_phase
        ledger_dispatcher = step.ledger_dispatcher or ledger_dispatcher
        ledger_exit_code = step.ledger_exit_code
        ledger_failure_detail_log = step.ledger_failure_detail_log or default_ledger_failure_detail_log
    elif step.outcome is Outcome.NEEDS_USER_INPUT and (
        reason in ledger_triggers or reason.startswith(f"{config.NEEDS_USER_CI_LOCAL_UNFIXABLE}:")
    ):
        ledger_ready = True
        ledger_site = "ship-pr"
        ledger_trigger = reason
        ledger_step = "8"
        ledger_phase = default_ledger_phase
        ledger_exit_code = config.OUTCOME_EXIT_MAP[Outcome.NEEDS_USER_INPUT]
        ledger_failure_detail_log = default_ledger_failure_detail_log
    return ShipResult(
        step.outcome,
        needs_user_reason=reason,
        failed_run_id=failed_run_id,
        pr_number=pr_number,
        pr_url=pr_url,
        merge_result=merge_result,
        detail=detail,
        ledger_ready=ledger_ready,
        ledger_site=ledger_site,
        ledger_trigger=ledger_trigger,
        ledger_step=ledger_step,
        ledger_phase=ledger_phase,
        ledger_dispatcher=ledger_dispatcher if ledger_ready else "",
        ledger_exit_code=ledger_exit_code,
        ledger_failure_detail_log=ledger_failure_detail_log,
    )


def _is_infrastructure_ship_error(exc: Exception) -> bool:
    text = str(exc)
    return any(
        token in text
        for token in (
            "cannot read existing ship state",
            "invalid ship state",
            "invalid newline in ship state value",
            "refusing to write symlinked ship state path",
            "refusing to write symlinked finalize-state path",
            "refusing to replace symlinked finalize-state path",
            "refusing to write symlinked finalize-state temp path",
            "finalize-state value",
            "invalid finalize-state key",
            "state_file",
        )
    )


def _is_active_pre_push_handoff(ctx: RunContext) -> bool:
    if not ctx.state_file:
        return False
    resume_phase = run_logs.read_state_kv(state_file=ctx.state_file, key="RESUME_PHASE")
    caller_kind = run_logs.read_state_kv(state_file=ctx.state_file, key="CALLER_KIND")
    return (
        resume_phase == config.SHIP_PR_RRR_RESUME_PHASE
        and caller_kind == config.SHIP_PR_PRE_PUSH_CALLER_KIND
    )


def _error_to_result(exc: Exception) -> ShipResult:
    if isinstance(exc, TransientNetworkError):
        return ShipResult(Outcome.TRANSIENT, detail=str(exc))
    if isinstance(exc, NeedsUserInput):
        return ShipResult(Outcome.NEEDS_USER_INPUT, needs_user_reason=str(exc), detail=str(exc))
    if isinstance(exc, Stalled):
        return ShipResult(Outcome.STALLED, detail=str(exc))
    if isinstance(exc, ShipError):
        if _is_infrastructure_ship_error(exc):
            return ShipResult(Outcome.INTERNAL_ERROR, detail=str(exc))
        return ShipResult(Outcome.STALLED, detail=str(exc))
    raise exc


def _breadcrumb(*, step: str, detail: str = "") -> None:
    suffix = f": {detail}" if detail else ""
    logging_util.BreadcrumbWriter().emit(f"ship.py: {step}{suffix}")


def _summary_from_manifest(ctx: RunContext) -> str:
    if ctx.summary:
        return ctx.summary
    manifest_path = Path(ctx.manifest_path)
    if manifest_path.is_file():
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            loaded = {}
        if isinstance(loaded, dict):
            data = cast("dict[str, object]", loaded)
            bullets_obj = data.get("summary_bullets")
            if isinstance(bullets_obj, list) and bullets_obj:
                bullets = [item for item in cast("list[object]", bullets_obj) if isinstance(item, str)]
                return "\n".join(f"- {item}" for item in bullets) + "\n"
    return "- Implement requested changes.\n"


def _write_ci_fix_detail_log(*, ctx: RunContext, detail: str) -> str:
    """Write the ci-fix exhaustion detail text to a tmpdir file; return path or empty."""
    if not detail or not ctx.tmpdir or not _tmpdir_under_allowed_root(ctx.tmpdir):
        return ""
    try:
        path = Path(ctx.tmpdir) / "ci-fix-exhausted-detail.log"
        _ = path.write_text(detail, encoding="utf-8")
        return str(path)
    except OSError:
        return ""


def _pr_title(*, ctx: RunContext, runner: Runner, cwd: str | None) -> str:
    issue = ctx.issue_number or ctx.issue
    prefix = f"Fixes #{issue}: " if issue and str(issue).isdigit() else ""
    if ctx.pr_title:
        title = ctx.pr_title
        return title if not prefix or title.startswith(prefix) else f"{prefix}{title}"
    subject = git.log_subject(runner, "HEAD", cwd=cwd)
    if subject.startswith(config.FLUSH_COMMIT_SUBJECT_PREFIX):
        subject = ""
    title = subject or f"Implement issue #{issue or ctx.issue}"
    return title if not prefix or title.startswith(prefix) else f"{prefix}{title}"



def _postmerge_should_flush(ctx: RunContext) -> bool:
    return bool(
        run_logs.effective_run_id(ctx)
        and ctx.pr_number is not None
        and not ctx.repo_unavailable
        and ctx.pr_closed
    )


def _write_terminal_state(
    *,
    ctx: RunContext,
    result: Outcome,
    step: str,
    iteration: int = 0,
    rebase_count: int = 0,
    fix_attempts: int = 0,
    transient_retries: int = 0,
    failed_run_id: str = "",
    bail_failure_detail_log: str = "",
    last_monitored_head: str | None = None,
) -> None:
    if not _tmpdir_under_allowed_root(ctx.tmpdir):
        return
    terminal_ctx = ctx.with_(stall_tracking=result is Outcome.STALLED, stall_step=step)
    _write_terminal_finalize_if_terminal(
        ctx=terminal_ctx,
        result=result,
        step=step,
        failed_run_id=failed_run_id,
        bail_failure_detail_log=bail_failure_detail_log,
    )
    phase = "done" if result is Outcome.OK else "stalled"
    _write_ship_state(
        terminal_ctx,
        phase=phase,
        iteration=iteration,
        rebase_count=rebase_count,
        fix_attempts=fix_attempts,
        transient_retries=transient_retries,
        terminal_outcome=result,
        failed_run_id=failed_run_id,
        bail_failure_detail_log=bail_failure_detail_log,
        last_monitored_head=last_monitored_head,
    )


def _publish_post_pr_terminal_snapshot(
    *,
    runner: Runner,
    ctx: RunContext,
    cwd: str,
) -> None:
    if ctx.pr_number is None:
        return
    with suppress(Exception):
        refresh = run_logs.flush_logs_pre(
            runner=runner,
            ctx=ctx.with_(state_file=None),
            cwd=cwd,
            strict_final_report=True,
        )
        if not refresh.skipped:
            with suppress(ShipError):
                _ = push.push_branch(runner=runner, ctx=ctx, cwd=cwd)


def _log_guidelines_ship_warning(*, implement_tmpdir: Path, message: str) -> None:
    issue_log = implement_tmpdir / "execution-issues.md"
    with suppress(Exception):
        run_logs.append_execution_issue(log_file=issue_log, category="Warnings", entry=message)


def _invalidate_guidelines_note(implement_tmpdir: str) -> None:
    if not implement_tmpdir:
        return
    tmpdir = Path(implement_tmpdir)
    should_persist = (
        architectural_guidelines.staged_assessment_present(tmpdir)
        or architectural_guidelines.durable_note_present(tmpdir)
    )
    try:
        persisted = architectural_guidelines.maybe_persist_dropped_note_before_invalidate(
            tmpdir,
            redact_fn=pr_body.redact_pr_body,
        )
        if should_persist and not persisted:
            _log_guidelines_ship_warning(
                implement_tmpdir=tmpdir,
                message="architectural-guidelines drop notice persist failed before invalidate",
            )
        architectural_guidelines.invalidate_implement_note(tmpdir)
    except OSError as exc:
        _log_guidelines_ship_warning(implement_tmpdir=tmpdir, message=f"architectural-guidelines invalidate failed: {exc}")


def _read_persisted_guidelines_drop_notice(tmpdir: Path) -> str:
    return architectural_guidelines.read_dropped_note_notice(tmpdir).strip()


def _persist_guidelines_drop_notice(tmpdir: Path) -> str:
    try:
        redacted = pr_body.redact_pr_body(architectural_guidelines.dropped_note_message()).strip()
    except ShipError as exc:
        _log_guidelines_ship_warning(implement_tmpdir=tmpdir, message=f"architectural-guidelines drop notice redaction failed: {exc}")
        return ""
    if not redacted:
        return ""
    if architectural_guidelines.persist_dropped_note_notice(tmpdir, notice_text=redacted):
        return redacted
    return _read_persisted_guidelines_drop_notice(tmpdir)


def _handle_unconsumable_guidelines_note(*, tmpdir: Path, staged_present: bool) -> str:
    notice = _read_persisted_guidelines_drop_notice(tmpdir)
    if notice:
        return notice
    if not staged_present:
        return ""
    notice = _persist_guidelines_drop_notice(tmpdir)
    if notice:
        return notice
    _log_guidelines_ship_warning(
        implement_tmpdir=tmpdir,
        message="architectural-guidelines drop notice persist failed after pin skip",
    )
    return ""


def _handle_stale_guidelines_note(*, tmpdir: Path, staged_present: bool) -> str:
    should_persist = staged_present or architectural_guidelines.durable_note_present(tmpdir)
    persisted = False
    if should_persist:
        persisted = architectural_guidelines.maybe_persist_dropped_note_before_invalidate(
            tmpdir,
            redact_fn=pr_body.redact_pr_body,
        )
    try:
        architectural_guidelines.invalidate_implement_note(tmpdir)
    except OSError as exc:
        _log_guidelines_ship_warning(implement_tmpdir=tmpdir, message=f"architectural-guidelines invalidate failed: {exc}")
    if persisted:
        return _read_persisted_guidelines_drop_notice(tmpdir)
    notice = _read_persisted_guidelines_drop_notice(tmpdir)
    return notice or ""


def _pin_and_load_guidelines_note(
    *,
    implement_tmpdir: str,
    head_sha: str,
    base_ref: str,
    repo_root: str | None = None,
) -> str:
    if not implement_tmpdir or not head_sha:
        return ""
    tmpdir = Path(implement_tmpdir)
    staged_present = architectural_guidelines.staged_assessment_present(tmpdir)
    if architectural_guidelines.staged_assessment_path(tmpdir).is_file():
        pinned_now = architectural_guidelines.pin_note_from_staged(
            tmpdir,
            head_sha=head_sha,
            base_ref=base_ref,
            repo_root=repo_root,
        )
        if not pinned_now:
            _log_guidelines_ship_warning(
                implement_tmpdir=tmpdir,
                message="architectural-guidelines pin-note-from-staged skipped or failed fingerprint validation",
            )
    if not architectural_guidelines.note_consumable(implement_tmpdir=tmpdir, head_sha=head_sha):
        return _handle_unconsumable_guidelines_note(tmpdir=tmpdir, staged_present=staged_present)
    meta: dict[str, str] = architectural_guidelines.durable_note_metadata(tmpdir)
    note_base_ref = base_ref or meta.get("BASE_REF", "")
    if architectural_guidelines.note_fingerprint_stale(
        tmpdir,
        base_ref=note_base_ref,
        repo_root=repo_root,
    ):
        return _handle_stale_guidelines_note(tmpdir=tmpdir, staged_present=staged_present)
    try:
        note = architectural_guidelines.durable_note_path(tmpdir).read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        _log_guidelines_ship_warning(implement_tmpdir=tmpdir, message=f"architectural-guidelines note read failed: {exc}")
        return ""
    try:
        return pr_body.redact_pr_body(note).strip()
    except ShipError as exc:
        _log_guidelines_ship_warning(implement_tmpdir=tmpdir, message=f"architectural-guidelines note redaction failed: {exc}")
        return ""


def _state_bool(*, value: bool) -> str:
    return "true" if value else "false"


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


def _write_terminal_finalize_if_terminal(
    *,
    ctx: RunContext,
    result: Outcome,
    step: str,
    failed_run_id: str = "",
    bail_failure_detail_log: str = "",
) -> None:
    if result in {Outcome.TRANSIENT, Outcome.NEEDS_USER_INPUT}:
        return
    if not _tmpdir_under_allowed_root(ctx.tmpdir):
        return
    path = Path(ctx.tmpdir) / "finalize-state.sh"
    finalize.write_finalize_state(ctx=ctx, path=path)
    data: dict[str, str] = finalize.read_finalize_state(path) if path.is_file() else {}
    data.update(
        _terminal_overlay_fields(
            ctx=ctx,
            result=result,
            step=step,
            failed_run_id=failed_run_id,
            bail_failure_detail_log=bail_failure_detail_log,
        ),
    )
    finalize.write_finalize_state_merged(path=path, data=data)
    _breadcrumb(step="finalize-state-written", detail=f"path={path} outcome={result.value} step={step or ''}")


def _valid_repo_slug(value: str) -> bool:
    return bool(value and not value.startswith("-") and _REPO_SLUG_RE.fullmatch(value))


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


def _context_with_state_overlay(ctx: RunContext) -> RunContext:
    state: dict[str, str] = _state_file_kv(ctx.state_file)
    changes: dict[str, object] = {}
    for key in ("BRANCH_NAME", "PR_URL"):
        value = state.get(key, "")
        if value:
            _validate_ship_state_value(key=key, value=value)
    for key, field in (
        ("BRANCH_NAME", "branch_name"),
        ("ISSUE_NUMBER", "issue_number"),
        ("RUN_ID", "run_id"),
        ("REPO", "repo"),
        ("PR_URL", "pr_url"),
        ("PR_TITLE", "pr_title"),
        ("MERGE_RESULT", "merge_result"),
        ("STALL_STEP", "stall_step"),
    ):
        value = state.get(key, "")
        if value:
            changes[field] = value
    pr_number: int | None = run_logs.parse_pr_number(state_file=ctx.state_file, ctx_pr_number=ctx.pr_number)
    if pr_number is not None:
        changes["pr_number"] = pr_number
    for key, field in (
        ("FORKED_TARGET", "forked_target"),
        ("REPO_UNAVAILABLE", "repo_unavailable"),
        ("DRAFT", "draft"),
        ("MERGE", "merge"),
        ("STALL_TRACKING", "stall_tracking"),
        ("BAIL_NEEDS_USER_INPUT", "bail_needs_user_input"),
        ("PR_CLOSED", "pr_closed"),
        ("CI_FIX_REBASE_PENDING", "ci_fix_rebase_pending"),
        ("OOS_PENDING", "oos_pending"),
    ):
        value = state.get(key, "")
        if value:
            changes[field] = _truthy(value)
    return ctx.with_(**changes) if changes else ctx


def _try_current_branch(runner: Runner, *, cwd: str | None) -> str:
    try:
        return git.current_branch(runner, cwd=cwd)
    except Exception:  # pylint: disable=broad-except
        return ""


def _seed_last_monitored_head(
    *,
    ctx: RunContext,
    runner: Runner,
    cwd: str,
    fix_attempts: int,
) -> str | None:
    """Resume seed for post-push empty-checks grace (issue #4867).

    When the merge loop restarts after a head-changing push, the in-process
    ``last_monitored_head`` is lost. Rehydrate from durable state so the first
    monitor poll after resume still uses ``CI_WAIT_POST_FIX_EMPTY_CHECKS_GRACE_SEC``.
    """
    current: str | None = git.try_rev_parse(runner, "HEAD", cwd=cwd)
    state: dict[str, str] = _state_file_kv(ctx.state_file)
    persisted = state.get("LAST_MONITORED_HEAD", "")
    pending_head = state.get("CI_FIX_REBASE_PENDING_HEAD", "")
    if persisted and current and persisted != current:
        return persisted
    if ctx.ci_fix_rebase_pending and current:
        if pending_head and pending_head != current:
            return pending_head
        return ""
    if fix_attempts > 0 and current and (not persisted or persisted == current):
        return ""
    return current


def _empty_checks_params_for_monitor(
    *,
    current_head: str | None,
    last_monitored_head: str | None,
    initial_startup_deadline_available: bool,
) -> tuple[int, int]:
    # Grant the full poll-based startup deadline both on the first poll and
    # whenever the head changed (rebase / force-push / CI-fix): a new head must
    # re-register checks from scratch, exactly like a brand-new PR head, so the
    # shorter post-fix grace expired before GitHub attached checks and produced a
    # false no-ci-checks-observed stall (issue #5217).
    if current_head != last_monitored_head or initial_startup_deadline_available:
        return 0, config.CI_WAIT_INITIAL_EMPTY_CHECKS_GRACE_SEC
    return 0, 0


def _fresh_resume_plan(
    durable: run_logs.DurableFlags,
    *,
    branch_name: str = "",
    repo: str = "",
    counters: run_logs.ResumeCounters | None = None,
    detail: str = "",
) -> ResumePlan:
    if counters is None:
        counters = run_logs.ResumeCounters(0, 0, 0, 0)
    return ResumePlan(
        start="fresh",
        iteration=counters.iteration,
        rebase_count=counters.rebase_count,
        fix_attempts=counters.fix_attempts,
        transient_retries=counters.transient_retries,
        pr_number=None,
        pr_url="",
        merge_result="",
        branch_name=branch_name,
        repo=repo,
        durable=durable,
        detail=detail,
    )


def _resume_from_state(
    *,
    start: str,
    counters: run_logs.ResumeCounters,
    durable: run_logs.DurableFlags,
    pr_number: int | None,
    pr_url: str,
    merge_result: str,
    branch_name: str,
    repo: str,
    detail: str = "",
) -> ResumePlan:
    return ResumePlan(
        start=start,
        iteration=counters.iteration,
        rebase_count=counters.rebase_count,
        fix_attempts=counters.fix_attempts,
        transient_retries=counters.transient_retries,
        pr_number=pr_number,
        pr_url=pr_url,
        merge_result=merge_result,
        branch_name=branch_name,
        repo=repo,
        durable=durable,
        detail=detail,
    )


def _state_bool_text(value: str) -> bool:
    return value.strip() == "true"


def _valid_merge_result(value: str) -> str:
    return value if value in config.POST_MERGE_MERGE_RESULTS else config.MERGE_RESULT_DRIVER_ALREADY_MERGED


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


def _valid_state_merge_result(value: str) -> bool:
    return not value or value in config.MERGE_RESULTS or value in config.POST_MERGE_MERGE_RESULTS


def _invalid_state_plan(
    *,
    counters: run_logs.ResumeCounters,
    durable: run_logs.DurableFlags,
    branch_name: str,
    repo: str,
    detail: str,
) -> ResumePlan:
    return _resume_from_state(
        start="blocked-checkout-mismatch",
        counters=counters,
        durable=durable,
        pr_number=None,
        pr_url="",
        merge_result="",
        branch_name=branch_name,
        repo=repo,
        detail=detail,
    )


def _resume_plan(*, ctx: RunContext, runner: Runner, cwd: str | None) -> ResumePlan:
    counters: run_logs.ResumeCounters = run_logs.read_resume_counters(ctx.state_file)
    durable: run_logs.DurableFlags = run_logs.read_durable_flags(state_file=ctx.state_file, ctx=ctx)
    if not ctx.state_file or not Path(ctx.state_file).is_file():
        return _fresh_resume_plan(durable, repo=ctx.repo)

    state_phase = run_logs.read_state_kv(state_file=ctx.state_file, key="PHASE")
    resume_phase = run_logs.read_state_kv(state_file=ctx.state_file, key="RESUME_PHASE")
    state_branch = run_logs.read_state_kv(state_file=ctx.state_file, key="BRANCH_NAME").strip()
    state_repo = run_logs.read_state_kv(state_file=ctx.state_file, key="REPO").strip() or ctx.repo
    state_pr_url = run_logs.read_state_kv(state_file=ctx.state_file, key="PR_URL")
    pr_url = (state_pr_url if _valid_pr_url(state_pr_url) else "") or (ctx.pr_url if _valid_pr_url(ctx.pr_url) else "")
    merge_result = run_logs.read_state_kv(state_file=ctx.state_file, key="MERGE_RESULT")

    caller_kind = run_logs.read_state_kv(state_file=ctx.state_file, key="CALLER_KIND")
    phase14_flag = Path(ctx.tmpdir) / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME
    if (
        resume_phase == config.SHIP_PR_RRR_RESUME_PHASE
        and caller_kind == config.SHIP_PR_PRE_PUSH_CALLER_KIND
        and not phase14_flag.is_file()
        and not phase14_flag.is_symlink()
    ):
        with suppress(OSError):
            _ = phase14_flag.write_text("RESUME_PHASE=ship-pr-rrr-phase14\n", encoding="utf-8")
    if resume_phase == config.SHIP_PR_RRR_RESUME_PHASE and not phase14_flag.is_file():
        if not _valid_repo_slug(state_repo):
            state_repo = ctx.repo
        return _resume_from_state(
            start="blocked-rebase-continuation",
            counters=counters,
            durable=durable,
            pr_number=run_logs.parse_pr_number(state_file=ctx.state_file, ctx_pr_number=ctx.pr_number),
            pr_url=pr_url,
            merge_result=merge_result,
            branch_name=state_branch or ctx.branch_name or ctx.branch,
            repo=state_repo,
            detail="Python ship driver cannot resume rebase-conflict continuation",
        )

    fallback_branch = ctx.branch_name or ctx.branch
    if state_branch and not _valid_branch_name(state_branch):
        return _invalid_state_plan(
            counters=counters,
            durable=durable,
            branch_name=fallback_branch,
            repo=ctx.repo,
            detail="invalid state BRANCH_NAME",
        )
    if state_pr_url and not _valid_pr_url(state_pr_url):
        return _invalid_state_plan(
            counters=counters,
            durable=durable,
            branch_name=state_branch or fallback_branch,
            repo=ctx.repo,
            detail="invalid state PR_URL",
        )
    if not _valid_state_merge_result(merge_result):
        return _invalid_state_plan(
            counters=counters,
            durable=durable,
            branch_name=state_branch or fallback_branch,
            repo=ctx.repo,
            detail="invalid state MERGE_RESULT",
        )
    if not _valid_repo_slug(state_repo):
        return _invalid_state_plan(
            counters=counters,
            durable=durable,
            branch_name=state_branch or fallback_branch,
            repo=ctx.repo,
            detail="invalid state REPO",
        )
    if state_repo != ctx.repo:
        return _invalid_state_plan(
            counters=counters,
            durable=durable,
            branch_name=state_branch or fallback_branch,
            repo=ctx.repo,
            detail="state REPO does not match context repo",
        )

    current_branch = _try_current_branch(runner, cwd=cwd)
    expected_branch = state_branch or ctx.branch_name or ctx.branch
    if not current_branch:
        return _resume_from_state(
            start="blocked-checkout-mismatch",
            counters=counters,
            durable=durable,
            pr_number=None,
            pr_url=pr_url,
            merge_result=merge_result,
            branch_name=expected_branch,
            repo=state_repo,
            detail=f"cannot verify current checkout branch; expected {expected_branch or '<unknown>'}",
        )
    if expected_branch and current_branch != expected_branch:
        return _resume_from_state(
            start="blocked-checkout-mismatch",
            counters=counters,
            durable=durable,
            pr_number=None,
            pr_url=pr_url,
            merge_result=merge_result,
            branch_name=expected_branch,
            repo=state_repo,
            detail=f"checkout branch mismatch: expected {expected_branch}, current {current_branch}",
        )
    if current_branch in {"main", "master"} and not durable.forked_target and not durable.forked:
        return _resume_from_state(
            start="blocked-checkout-mismatch",
            counters=counters,
            durable=durable,
            pr_number=None,
            pr_url=pr_url,
            merge_result=merge_result,
            branch_name=current_branch,
            repo=state_repo,
            detail=f"refusing to resume on protected branch {current_branch}",
        )
    gh_skipped = durable.repo_unavailable or durable.forked or durable.forked_target
    if not expected_branch and gh_skipped:
        return _resume_from_state(
            start="blocked-checkout-mismatch",
            counters=counters,
            durable=durable,
            pr_number=None,
            pr_url=pr_url,
            merge_result=merge_result,
            branch_name=current_branch,
            repo=state_repo,
            detail="cannot verify gh-skipped resume branch anchor",
        )
    branch_name = current_branch
    pr_number: int | None = run_logs.parse_pr_number(state_file=ctx.state_file, ctx_pr_number=ctx.pr_number)
    if gh_skipped and pr_number is not None and not pr_url:
        return _resume_from_state(
            start="blocked-checkout-mismatch",
            counters=counters,
            durable=durable,
            pr_number=None,
            pr_url="",
            merge_result=merge_result,
            branch_name=branch_name,
            repo=state_repo,
            detail="cannot verify gh-skipped resume PR identity anchor",
        )
    if pr_number is None and not durable.repo_unavailable:
        return _fresh_resume_plan(
            durable,
            branch_name=branch_name,
            repo=state_repo,
            counters=counters,
            detail="missing or invalid PR_NUMBER",
        )

    if not gh_skipped:
        if pr_number is None:
            return _fresh_resume_plan(durable, branch_name=branch_name, repo=state_repo, counters=counters)
        try:
            viewed: gh.PullRequest = gh.pr_view(runner, pr_number, repo=state_repo, cwd=cwd)
        except Exception:  # pylint: disable=broad-except
            return _fresh_resume_plan(
                durable,
                branch_name=branch_name,
                repo=state_repo,
                counters=counters,
                detail="gh pr view failed",
            )
        state = viewed.state.upper()
        if state == "MERGED":
            start = "done" if state_phase == "done" else "merged"
            return _resume_from_state(
                start=start,
                counters=counters,
                durable=durable,
                pr_number=viewed.number,
                pr_url=viewed.url or pr_url,
                merge_result=_valid_merge_result(merge_result),
                branch_name=branch_name,
                repo=state_repo,
            )
        if viewed.head_ref != branch_name:
            return _fresh_resume_plan(
                durable,
                branch_name=branch_name,
                repo=state_repo,
                counters=counters,
                detail=f"PR head {viewed.head_ref} does not match checkout {branch_name}",
            )
        if state == "OPEN":
            return _resume_from_state(
                start="open-pr",
                counters=counters,
                durable=durable,
                pr_number=viewed.number,
                pr_url=viewed.url or pr_url,
                merge_result=merge_result,
                branch_name=branch_name,
                repo=state_repo,
            )
        return _fresh_resume_plan(
            durable,
            branch_name=branch_name,
            repo=state_repo,
            counters=counters,
            detail=f"PR state {viewed.state} is not resumable",
        )

    pr_closed_signal = _state_bool_text(run_logs.read_state_kv(state_file=ctx.state_file, key="PR_CLOSED"))
    postmerge_phase_signal = state_phase == "postmerge"
    merge_result_signal = merge_result in config.POST_MERGE_MERGE_RESULTS
    postmerge_sentinel_signal = (Path(ctx.tmpdir) / "post-merge-sentinel").is_file()
    manifest_done_signal = run_logs.manifest_status(ctx) == config.MANIFEST_STATUS_DONE and postmerge_sentinel_signal
    local_merged_signal_count = sum(
        bool(signal)
        for signal in (
            pr_closed_signal,
            postmerge_phase_signal,
            merge_result_signal,
            manifest_done_signal,
        )
    )
    local_merged = local_merged_signal_count >= _MIN_GH_SKIPPED_MERGE_SIGNALS
    if state_phase == "done":
        if local_merged:
            return _resume_from_state(
                start="done",
                counters=counters,
                durable=durable,
                pr_number=pr_number,
                pr_url=pr_url,
                merge_result=_valid_merge_result(merge_result),
                branch_name=branch_name,
                repo=state_repo,
            )
        state_phase = "ci-initial"
    if local_merged:
        return _resume_from_state(
            start="merged",
            counters=counters,
            durable=durable,
            pr_number=pr_number,
            pr_url=pr_url,
            merge_result=_valid_merge_result(merge_result),
            branch_name=branch_name,
            repo=state_repo,
        )
    if pr_number is not None or durable.repo_unavailable:
        return _resume_from_state(
            start="open-pr",
            counters=counters,
            durable=durable,
            pr_number=pr_number,
            pr_url=pr_url,
            merge_result=merge_result,
            branch_name=branch_name,
            repo=state_repo,
        )
    return _fresh_resume_plan(durable, branch_name=branch_name, repo=state_repo, counters=counters)


def _hydrate_resume_context(*, ctx: RunContext, resume: ResumePlan) -> RunContext:
    run_id = run_logs.effective_run_id(ctx) or ctx.run_id
    return ctx.with_(
        run_id=run_id,
        branch=resume.branch_name or ctx.branch,
        branch_name=resume.branch_name or ctx.branch_name or ctx.branch,
        repo=resume.repo or ctx.repo,
        pr_number=resume.pr_number,
        pr_url=resume.pr_url,
        merge_result=resume.merge_result,
        repo_unavailable=resume.durable.repo_unavailable,
        forked_target=resume.durable.forked_target,
        forked=resume.durable.forked,
        merge=resume.durable.merge,
        draft=resume.durable.draft,
    )


def _merge_loop_uses_resume_counters(resume: ResumePlan) -> bool:
    if resume.start == "open-pr":
        return True
    if resume.start == "fresh":
        return bool(
            resume.iteration
            or resume.rebase_count
            or resume.fix_attempts
            or resume.transient_retries
        )
    return False


def _hydrate_fresh_context(*, ctx: RunContext, resume: ResumePlan) -> RunContext:
    changes: dict[str, object] = {
        "repo": resume.repo or ctx.repo,
        "pr_number": None,
        "pr_url": "",
        "merge_result": "",
        "pr_closed": False,
        "repo_unavailable": resume.durable.repo_unavailable,
        "forked_target": resume.durable.forked_target,
        "forked": resume.durable.forked,
        "merge": resume.durable.merge,
        "draft": resume.durable.draft,
    }
    if resume.branch_name:
        changes["branch"] = resume.branch_name
        changes["branch_name"] = resume.branch_name
    return ctx.with_(**changes)


def _monitor_persisted_counters(
    *,
    iteration: int,
    rebase_count: int,
    fix_attempts: int,
    transient_retries: int,
    monitor: ci_monitor.MonitorResult,
) -> tuple[int, int, int, int]:
    monitor_ok = monitor.result.outcome is Outcome.OK
    return (
        iteration,
        rebase_count + (1 if monitor_ok and monitor.goto_rebase else 0),
        fix_attempts + (1 if monitor.did_fixing else 0),
        transient_retries + (1 if monitor.transient_rerun_attempted else 0),
    )


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


def run_postmerge_phase(
    *,
    runner: Runner,
    ctx: RunContext,
    cwd: str | None = None,
) -> ShipResult:
    if not ctx.merge or not ctx.pr_closed:
        return ShipResult(Outcome.STALLED, detail="postmerge requires a closed merge PR")
    sentinel = Path(ctx.tmpdir) / "post-merge-sentinel"
    if ctx.pr_closed:
        _ = sentinel.write_text(f"MERGE_RESULT={ctx.merge_result}\n", encoding="utf-8")
    post: finalize.FinalizeResult = finalize.postmerge(runner=runner, ctx=ctx, cwd=cwd)
    state_ctx = ctx.with_(
        pr_closed=ctx.pr_closed,
        stall_tracking=post.outcome is Outcome.STALLED,
        stall_step=post.status if post.outcome is Outcome.STALLED else ctx.stall_step,
    )
    if post.outcome is Outcome.OK:
        _write_terminal_finalize_if_terminal(ctx=state_ctx, result=Outcome.OK, step="")
    if post.outcome is Outcome.OK and _postmerge_should_flush(state_ctx):
        skip: run_logs.RefreshSkip = run_logs.finalize_postmerge_logs(state_ctx, merge_result=state_ctx.merge_result, runner=runner)
        if skip.skipped:
            _breadcrumb(step="warning", detail=f"post-merge flush skipped: {skip.reason}")
            stall_ctx = state_ctx.with_(stall_tracking=True, stall_step="postmerge-flush")
            _write_terminal_finalize_if_terminal(ctx=stall_ctx, result=Outcome.STALLED, step="postmerge-flush")
            _write_ship_state(stall_ctx, phase="postmerge", terminal_outcome=Outcome.STALLED)
            return ShipResult(Outcome.STALLED, detail=f"post-merge flush skipped: {skip.reason}")
    if post.outcome is not Outcome.OK:
        _write_terminal_finalize_if_terminal(ctx=state_ctx, result=post.outcome, step=post.status)
        _write_ship_state(state_ctx, phase="postmerge", terminal_outcome=post.outcome)
        return ShipResult(post.outcome, detail=post.detail or post.status)
    _write_ship_state(state_ctx, phase="done", terminal_outcome=Outcome.OK)
    return ShipResult(
        Outcome.OK,
        pr_number=ctx.pr_number,
        pr_url=ctx.pr_url,
        merge_result=ctx.merge_result,
    )


def _ship_postmerge_phase(
    *,
    runner: Runner,
    working: RunContext,
    cwd: str,
    iteration: int,
    rebase_count: int,
    fix_attempts: int,
    transient_retries: int,
) -> ShipResult:
    _breadcrumb(step="post-merge")
    post = run_postmerge_phase(runner=runner, ctx=working, cwd=cwd)
    if post.outcome is Outcome.OK:
        _write_ship_state(
            working,
            phase="done",
            iteration=iteration,
            rebase_count=rebase_count,
            fix_attempts=fix_attempts,
            transient_retries=transient_retries,
        )
    return ShipResult(
        post.outcome,
        pr_number=working.pr_number,
        pr_url=working.pr_url,
        merge_result=working.merge_result,
        detail=post.detail,
    )


def _ship_rebase_phase(
    *,
    runner: Runner,
    working: RunContext,
    cwd: str,
    base_remote: str,
    base_ref: str,
    iteration: int,
    rebase_count: int,
    fix_attempts: int,
    transient_retries: int,
    variant: ShipRebaseVariant,
) -> ShipRebasePhaseResult:
    _ = variant
    _write_ship_state(
        working,
        phase="rebase",
        iteration=iteration,
        rebase_count=rebase_count,
        fix_attempts=fix_attempts,
        transient_retries=transient_retries,
    )
    _breadcrumb(step="rebase", detail="Flush+Push")
    pre_rebase: run_logs.RefreshSkip = run_logs.flush_logs_pre(runner=runner, ctx=working.with_(state_file=None), cwd=cwd)
    if (
        pre_rebase.skipped
        and pre_rebase.reason != run_logs.REFRESH_SKIP_RECOVERY_FAILED
        and pre_rebase.reason not in config.REFRESH_SKIP_POST_ENSURE_PR_OK
    ):
        _write_terminal_state(
            ctx=working,
            result=Outcome.STALLED,
            step="pre-rebase",
            iteration=iteration,
            rebase_count=rebase_count,
            fix_attempts=fix_attempts,
            transient_retries=transient_retries,
        )
        _publish_post_pr_terminal_snapshot(runner=runner, ctx=working, cwd=cwd)
        return ShipRebasePhaseResult(
            rebase_count,
            ShipResult(
                Outcome.STALLED,
                detail=f"pre-rebase flush skipped: {pre_rebase.reason}",
            ),
        )
    try:
        _ = rebase.rebase_and_push(
            runner=runner,
            repo=working.repo,
            run_id=working.run_id,
            cwd=cwd,
            tmpdir=working.tmpdir,
            base_remote=base_remote,
            base_ref=base_ref,
            allow_conflict_fix=True,
            enable_pre_push_handoff=True,
        )
    except PrePushConflictHandoff as exc:
        _write_ship_state(
            working,
            phase="rebase",
            iteration=iteration,
            rebase_count=rebase_count,
            fix_attempts=fix_attempts,
            transient_retries=transient_retries,
            resume_phase=exc.resume_phase,
            caller_kind=exc.caller_kind,
            extra_fields={"CONFLICT_FILES": exc.conflict_csv},
        )
        raise
    rebase_count += 1
    _invalidate_guidelines_note(working.tmpdir)
    return ShipRebasePhaseResult(rebase_count)


def _ship_phase14_rebase(
    *,
    runner: Runner,
    working: RunContext,
    cwd: str,
    base_remote: str,
    base_ref: str,
    phase14_flag: Path,
    iteration: int,
    rebase_count: int,
    fix_attempts: int,
    transient_retries: int,
    last_monitored_head: str | None,
) -> int:
    try:
        _ = rebase.rebase_and_push(
            runner=runner,
            repo=working.repo,
            run_id=working.run_id,
            cwd=cwd,
            tmpdir=working.tmpdir,
            base_remote=base_remote,
            base_ref=base_ref,
            allow_conflict_fix=True,
            enable_pre_push_handoff=True,
        )
        phase14_flag.unlink(missing_ok=True)
        rebase_count += 1
        _invalidate_guidelines_note(working.tmpdir)
        _write_ship_state(
            working,
            phase="ci-initial",
            iteration=iteration,
            rebase_count=rebase_count,
            fix_attempts=fix_attempts,
            transient_retries=transient_retries,
            resume_phase="",
            caller_kind="",
            last_monitored_head=last_monitored_head or "",
        )
        return rebase_count
    except PrePushConflictHandoff as exc:
        _write_ship_state(
            working,
            phase="rebase",
            iteration=iteration,
            rebase_count=rebase_count,
            fix_attempts=fix_attempts,
            transient_retries=transient_retries,
            resume_phase=exc.resume_phase,
            caller_kind=exc.caller_kind,
            extra_fields={"CONFLICT_FILES": exc.conflict_csv},
        )
        raise
    except Exception:
        phase14_flag.unlink(missing_ok=True)
        raise


def _post_ensure_flush_and_push(
    runner: Runner,
    *,
    working: RunContext,
    resume: ResumePlan,
    repo_root: str,
) -> ShipResult | None:
    """Push the post-PR head without re-flushing run logs.

    The run logs are flushed exactly once, before the PR is created (the
    ``pr-prep`` phase), so ``final-summary.md`` with placeholder PR fields plus
    the token/timing/transcript data ride the PR's initial push in a single
    commit and land in the squash merge. The live PR URL is refreshed into the
    tracking issue via API only (``write_final_report_comment``), per the Step 7a
    "Pre-ship log flush" contract in ``skills/implement/SKILL.md`` ("no second
    commit, no second push").

    Re-flushing here would commit a brand-new log-churn commit, move HEAD, and
    re-trigger CI: a redundant head-moving push on a fresh run (issue #5217) and
    the perpetual no-ci-checks-observed loop on open-pr resume (issue #5186). So
    this step never re-flushes; it only pushes. The push is idempotent (a no-op
    when the remote already has this head, a one-time reconcile when a prior
    invocation committed but failed to push), so first-try CI success yields
    exactly one push for the whole run and CI converges on a stable head.

    Returns a terminal ``ShipResult`` on push failure, or ``None`` to continue
    into the merge loop.
    """
    _breadcrumb(step="post-ensure-pr", detail="Push")
    try:
        post_ensure_push = push.push_branch(runner=runner, ctx=working, cwd=repo_root)
    except ShipError as exc:
        _write_terminal_state(
            ctx=working,
            result=Outcome.STALLED,
            step="post-ensure-pr-push",
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        return ShipResult(
            Outcome.STALLED,
            pr_number=working.pr_number,
            pr_url=working.pr_url,
            detail=f"post-ensure-pr push failed: {str(exc).strip()}",
        )
    if post_ensure_push.status != "pushed":
        _write_terminal_state(
            ctx=working,
            result=Outcome.STALLED,
            step="post-ensure-pr-push",
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        return ShipResult(
            Outcome.STALLED,
            pr_number=working.pr_number,
            pr_url=working.pr_url,
            detail=f"post-ensure-pr push failed: {post_ensure_push.status}",
        )
    return None


def run_ship(
    ctx: RunContext,
    *,
    runner: Runner = proc,
    cwd: str | None = None,
) -> ShipResult:
    try:
        repo_root = cwd or str(Path.cwd())
        if not _tmpdir_under_allowed_root(ctx.tmpdir):
            return ShipResult(Outcome.STALLED, detail="invalid tmpdir")
        if not _state_file_under_tmpdir(ctx):
            return ShipResult(Outcome.STALLED, detail="invalid state_file")
        base_ref = "main"
        resume = _resume_plan(ctx=ctx, runner=runner, cwd=repo_root)
        if resume.start == "blocked-rebase-continuation":
            return ShipResult(
                Outcome.NEEDS_USER_INPUT,
                needs_user_reason="unsupported-rebase-continuation",
                detail=resume.detail,
                pr_number=resume.pr_number,
                pr_url=resume.pr_url,
            )
        if resume.start == "blocked-checkout-mismatch":
            return ShipResult(
                Outcome.NEEDS_USER_INPUT,
                needs_user_reason="checkout-mismatch",
                detail=resume.detail,
            )
        if "\n" in ctx.pr_url or "\r" in ctx.pr_url:
            raise Stalled("invalid newline in ship state value: PR_URL")
        if resume.start == "done":
            done_ctx = _hydrate_resume_context(ctx=ctx, resume=resume).with_(pr_closed=True)
            _write_terminal_finalize_if_terminal(ctx=done_ctx, result=Outcome.OK, step="done")
            return ShipResult(
                Outcome.OK,
                pr_number=resume.pr_number,
                pr_url=resume.pr_url,
                merge_result=resume.merge_result,
                detail="already done",
            )
        if resume.start == "merged":
            working = _hydrate_resume_context(ctx=ctx, resume=resume).with_(pr_closed=True)
            _write_ship_state(
                working,
                phase="postmerge",
                iteration=resume.iteration,
                rebase_count=resume.rebase_count,
                fix_attempts=resume.fix_attempts,
                transient_retries=resume.transient_retries,
            )
            return _ship_postmerge_phase(
                runner=runner,
                working=working,
                cwd=repo_root,
                iteration=resume.iteration,
                rebase_count=resume.rebase_count,
                fix_attempts=resume.fix_attempts,
                transient_retries=resume.transient_retries,
            )

        if resume.start == "fresh":
            fresh_context = _hydrate_fresh_context(ctx=ctx, resume=resume)
            # Upfront local lint/tests phase removed by request: open the PR
            # immediately and let CI surface failures (no pre-PR `make py-test`
            # / relevant-checks run). The post-CI fix path is unaffected; only
            # this fresh-run pre-PR checks gate is skipped.
            _write_ship_state(
                fresh_context,
                phase="pr-prep",
                iteration=resume.iteration,
                rebase_count=resume.rebase_count,
                fix_attempts=resume.fix_attempts,
                transient_retries=resume.transient_retries,
            )
            _breadcrumb(step="pr-prep", detail="postbump/Flush+Push")
            preflight: finalize.PostbumpPreflight = finalize.postbump_preflight(runner=runner, ctx=fresh_context, cwd=repo_root)
            if not preflight.ok:
                postbump = finalize.FinalizeResult(Outcome.STALLED, preflight.status, preflight.detail)
            else:
                refresh: run_logs.RefreshSkip = run_logs.flush_logs_pre(runner=runner, ctx=fresh_context.with_(state_file=None), cwd=repo_root)
                if refresh.skipped and refresh.reason not in config.REFRESH_SKIP_MERGE_OK:
                    _breadcrumb(step="warning", detail=f"postbump refresh skipped: {refresh.reason}")
                postbump = finalize.postbump(runner=runner, ctx=fresh_context, cwd=repo_root)
            if postbump.outcome is not Outcome.OK:
                postbump_ctx = fresh_context.with_(
                    stall_tracking=postbump.outcome is Outcome.STALLED,
                    stall_step=postbump.status if postbump.outcome is Outcome.STALLED else "",
                )
                _write_terminal_finalize_if_terminal(ctx=postbump_ctx, result=postbump.outcome, step=postbump.status)
                _write_ship_state(
                    postbump_ctx,
                    phase=postbump.status,
                    iteration=resume.iteration,
                    rebase_count=resume.rebase_count,
                    fix_attempts=resume.fix_attempts,
                    transient_retries=resume.transient_retries,
                    terminal_outcome=postbump.outcome,
                )
                return ShipResult(postbump.outcome, detail=postbump.detail or postbump.status)

            tmp_path = Path(fresh_context.tmpdir)
            for manifest in (
                tmp_path / "manifest-raw.json",
                tmp_path / "manifest.json",
                Path(fresh_context.manifest_path) if fresh_context.manifest_path else None,
            ):
                if manifest and manifest.is_file():
                    with suppress(Exception):
                        _ = file_oos.materialize_manifest_oos(manifest, tmp_path)
                    break

            security_sidecar = tmp_path / "security-oos-observations.md"
            if (
                not fresh_context.forked_target
                and not fresh_context.repo_unavailable
                and security_sidecar.is_file()
                and security_sidecar.stat().st_size > 0
            ):
                return ShipResult(
                    Outcome.NEEDS_USER_INPUT, needs_user_reason="oos-filing"
                )

            pr_context = fresh_context
        else:
            pr_context = _hydrate_resume_context(ctx=ctx, resume=resume)

        _write_ship_state(
            pr_context,
            phase="pr-create",
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        _breadcrumb(step="pr-create", detail="PR")
        compose_head_sha = git.try_rev_parse(runner, "HEAD", cwd=repo_root) or ""
        compose_base_ref = f"{'upstream' if pr_context.forked or pr_context.forked_target else 'origin'}/{base_ref}"
        architectural_guidelines_note = _pin_and_load_guidelines_note(
            implement_tmpdir=pr_context.tmpdir,
            head_sha=compose_head_sha,
            base_ref=compose_base_ref,
            repo_root=repo_root,
        )
        body = pr_body.compose_pr_body(
            summary=_summary_from_manifest(pr_context),
            mermaid=pr_context.mermaid,
            test_plan=pr_context.test_plan or "- [ ] `make py-lint`\n- [ ] `make py-test`\n",
            issue_number=int(pr_context.issue_number or pr_context.issue) if (pr_context.issue_number or pr_context.issue).isdigit() else None,
            architectural_guidelines_note=architectural_guidelines_note,
        )
        title = _pr_title(ctx=pr_context, runner=runner, cwd=repo_root)
        ensured: pr.PrResult = pr.ensure_pr(runner=runner, ctx=pr_context, body=body, title=title, cwd=repo_root, base=base_ref)
        working = pr_context.with_(
            pr_number=ensured.number or pr_context.pr_number,
            pr_url=ensured.url or pr_context.pr_url,
            pr_title=title,
            pr_closed=False,
        )
        _write_ship_state(
            working,
            phase="ci-initial" if working.merge and not working.draft else "done",
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        if resume.start == "fresh":
            try:
                run_logs.write_final_report_comment(runner=runner, ctx=working)
            except ShipError as exc:
                _breadcrumb(step="warning", detail=str(exc))
        if not working.merge or working.draft or working.forked or working.forked_target or working.repo_unavailable:
            _write_terminal_finalize_if_terminal(ctx=working, result=Outcome.OK, step="")
            _write_ship_state(
                working,
                phase="done",
                iteration=resume.iteration,
                rebase_count=resume.rebase_count,
                fix_attempts=resume.fix_attempts,
                transient_retries=resume.transient_retries,
                terminal_outcome=Outcome.OK,
            )
            return ShipResult(
                Outcome.OK,
                pr_number=working.pr_number,
                pr_url=working.pr_url,
                detail=ensured.status,
            )

        post_ensure_terminal = _post_ensure_flush_and_push(runner, working=working, resume=resume, repo_root=repo_root)
        if post_ensure_terminal is not None:
            return post_ensure_terminal

        base_remote = "upstream" if working.forked or working.forked_target else "origin"
        preserve_counters = _merge_loop_uses_resume_counters(resume)
        iteration = resume.iteration if preserve_counters else 0
        rebase_count = resume.rebase_count if preserve_counters else 0
        fix_attempts = resume.fix_attempts if preserve_counters else 0
        transient_retries = resume.transient_retries if preserve_counters else 0
        initial_startup_deadline_available = (
            iteration == rebase_count == fix_attempts == transient_retries == 0
        )
        # Head observed by the previous monitor poll. When a loop iteration pushes
        # a new head (CI-fix or rebase) the next monitor expects a fresh CI run; if
        # none starts we must detect it within a bounded window rather than poll the
        # full budget (issue #4867). Seed from durable state on resume so a
        # head-changing push before restart still gets bounded empty-checks grace.
        last_monitored_head = _seed_last_monitored_head(
            ctx=working,
            runner=runner,
            cwd=repo_root,
            fix_attempts=fix_attempts,
        )
        while True:
            if iteration > config.SHIP_MERGE_LOOP_MAX_ITERATIONS:
                _write_terminal_state(
                    ctx=working,
                    result=Outcome.STALLED,
                    step="merge-loop-iteration-cap",
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                )
                _publish_post_pr_terminal_snapshot(runner=runner, ctx=working, cwd=repo_root)
                return ShipResult(
                    Outcome.STALLED,
                    pr_number=working.pr_number,
                    pr_url=working.pr_url,
                    detail="merge loop iteration cap reached",
                )
            _write_ship_state(
                working,
                phase="ci-initial",
                iteration=iteration,
                rebase_count=rebase_count,
                fix_attempts=fix_attempts,
                transient_retries=transient_retries,
                ci_fix_rebase_pending_head=(git.try_rev_parse(runner, "HEAD", cwd=repo_root) or "")
                if working.ci_fix_rebase_pending
                else "",
                last_monitored_head=last_monitored_head or "",
            )
            phase14_flag = Path(working.tmpdir) / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME
            if phase14_flag.is_file():
                rebase_count = _ship_phase14_rebase(
                    runner=runner,
                    working=working,
                    cwd=repo_root,
                    base_remote=base_remote,
                    base_ref=base_ref,
                    phase14_flag=phase14_flag,
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                    last_monitored_head=last_monitored_head,
                )
                continue
            pre_monitor_head = last_monitored_head
            current_head = git.try_rev_parse(runner, "HEAD", cwd=repo_root)
            empty_checks_grace, empty_checks_startup_deadline_sec = (
                _empty_checks_params_for_monitor(
                    current_head=current_head,
                    last_monitored_head=last_monitored_head,
                    initial_startup_deadline_available=initial_startup_deadline_available,
                )
            )
            monitor: ci_monitor.MonitorResult = ci_monitor.monitor(
                runner,
                pr=working.pr_number or 0,
                repo=working.repo,
                iteration=iteration,
                rebase_count=rebase_count,
                fix_attempts=fix_attempts,
                base_remote=base_remote,
                base_ref=base_ref,
                empty_checks_grace=empty_checks_grace,
                empty_checks_startup_deadline_sec=empty_checks_startup_deadline_sec,
                ci_fix_rebase_pending=working.ci_fix_rebase_pending,
                cwd=repo_root,
            )
            initial_startup_deadline_available = False
            last_monitored_head = current_head
            monitor_pending = getattr(monitor, "ci_fix_rebase_pending", working.ci_fix_rebase_pending)
            if monitor_pending != working.ci_fix_rebase_pending:
                working = working.with_(ci_fix_rebase_pending=monitor_pending)
                pending_head = git.try_rev_parse(runner, "HEAD", cwd=repo_root) if monitor_pending else ""
                _write_ship_state(
                    working,
                    phase="ci-initial",
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                    ci_fix_rebase_pending_head=pending_head or "",
                    last_monitored_head=last_monitored_head or "",
                )
            if monitor.result.outcome is not Outcome.OK:
                persisted = _monitor_persisted_counters(
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                    monitor=monitor,
                )
                if (
                    monitor.result.outcome is Outcome.TRANSIENT
                    and persisted[3] >= _PYTHON_TRANSIENT_STALL_ATTEMPT
                    and not working.expected_session_id
                ):
                    _write_terminal_state(
                        ctx=working,
                        result=Outcome.STALLED,
                        step="transient-retry-cap",
                        iteration=persisted[0],
                        rebase_count=persisted[1],
                        fix_attempts=persisted[2],
                        transient_retries=persisted[3],
                        failed_run_id=monitor.failed_run_id or "",
                    )
                    _publish_post_pr_terminal_snapshot(runner=runner, ctx=working, cwd=repo_root)
                    return ShipResult(
                        Outcome.STALLED,
                        failed_run_id=monitor.failed_run_id or "",
                        pr_number=working.pr_number,
                        pr_url=working.pr_url,
                        detail=monitor.result.detail or "transient retry cap",
                    )
                _bail_ctx = working
                _bail_detail_log = ""
                _bail_step = monitor.result.detail or "ci-monitor"
                if (
                    monitor.result.outcome is Outcome.NEEDS_USER_INPUT
                    and (monitor.result.detail or "").startswith("ci-fix-exhausted")
                ):
                    _bail_ctx = working.with_(final_bail_reason=config.NEEDS_USER_CI_FIX_EXHAUSTED)
                    _bail_detail_log = _write_ci_fix_detail_log(ctx=working, detail=monitor.result.detail or "")
                    _bail_step = "10"
                terminal_last_head: str | None = None
                bounded_empty_checks = (
                    empty_checks_grace > 0 or empty_checks_startup_deadline_sec > 0
                )
                no_checks_stall = (
                    (monitor.result.detail or "") == config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED
                    and bounded_empty_checks
                )
                if no_checks_stall:
                    terminal_last_head = pre_monitor_head or ""
                _write_terminal_state(
                    ctx=_bail_ctx,
                    result=monitor.result.outcome,
                    step=_bail_step,
                    iteration=persisted[0],
                    rebase_count=persisted[1],
                    fix_attempts=persisted[2],
                    transient_retries=persisted[3],
                    failed_run_id=monitor.failed_run_id or "",
                    bail_failure_detail_log=_bail_detail_log,
                    last_monitored_head=terminal_last_head,
                )
                # A no-ci-checks-observed stall is recoverable: the main agent
                # re-invokes ship-pr, which re-monitors the same head. Publishing a
                # terminal snapshot here would flush a fresh larch-logs commit and
                # push it, moving HEAD and re-triggering CI before checks can attach
                # -- the perpetual stall loop of issue #5186. Skip the snapshot so
                # HEAD stays put and CI converges on a stable head; it is published
                # once the run reaches a genuinely terminal state.
                if not no_checks_stall:
                    _publish_post_pr_terminal_snapshot(runner=runner, ctx=_bail_ctx, cwd=repo_root)
                return _step_result_to_ship(
                    monitor.result,
                    failed_run_id=monitor.failed_run_id or "",
                    pr_number=working.pr_number,
                    pr_url=working.pr_url,
                    default_ledger_phase="ci-initial",
                    default_ledger_failure_detail_log=_bail_detail_log,
                )
            if monitor.action not in {"merge", "already_merged"}:
                if iteration > config.SHIP_MERGE_LOOP_MAX_ITERATIONS:
                    _write_terminal_state(
                        ctx=working,
                        result=Outcome.STALLED,
                        step="merge-loop-iteration-cap",
                        iteration=iteration,
                        rebase_count=rebase_count,
                        fix_attempts=fix_attempts,
                        transient_retries=transient_retries,
                    )
                    _publish_post_pr_terminal_snapshot(runner=runner, ctx=working, cwd=repo_root)
                    return ShipResult(
                        Outcome.STALLED,
                        pr_number=working.pr_number,
                        pr_url=working.pr_url,
                        detail="merge loop iteration cap reached",
                    )
                if monitor.goto_rebase:
                    rebase_phase = _ship_rebase_phase(
                        runner=runner,
                        working=working,
                        cwd=repo_root,
                        base_remote=base_remote,
                        base_ref=base_ref,
                        iteration=iteration,
                        rebase_count=rebase_count,
                        fix_attempts=fix_attempts,
                        transient_retries=transient_retries,
                        variant=ShipRebaseVariant.GOTO_REBASE,
                    )
                    rebase_count = rebase_phase.rebase_count
                    if rebase_phase.terminal is not None:
                        return rebase_phase.terminal
                if monitor.transient_rerun_attempted:
                    transient_retries += 1
                if monitor.did_fixing:
                    _invalidate_guidelines_note(working.tmpdir)
                    fix_attempts += 1
                if monitor.action == "wait" or monitor.goto_rebase:
                    iteration += 1
                _write_ship_state(
                    working,
                    phase="ci-initial",
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                    last_monitored_head=last_monitored_head or "",
                )
                continue

            _breadcrumb(step="merge")
            merged: merge.MergeResult = merge.merge_pr(runner=runner, ctx=working, cwd=repo_root, post_flush=False)
            if merged.result == config.MERGE_RESULT_CI_NOT_READY:
                review_decision = gh.pr_review_decision(
                    runner,
                    working.pr_number or 0,
                    repo=working.repo,
                    cwd=repo_root,
                )
                if review_decision == "REVIEW_REQUIRED":
                    merged = merge.MergeResult(
                        result=config.MERGE_RESULT_REVIEW_REQUIRED,
                        error=(
                            f"PR requires approving review (mergeStateStatus=BLOCKED): "
                            f"approve the PR or merge manually with --admin. "
                            f"Original: {merged.error}"
                        ),
                    )
                else:
                    iteration += 1
                    _write_ship_state(
                        working,
                        phase="ci-initial",
                        iteration=iteration,
                        rebase_count=rebase_count,
                        fix_attempts=fix_attempts,
                        transient_retries=transient_retries,
                    )
                    continue
            if merged.result == config.MERGE_RESULT_MAIN_ADVANCED:
                rebase_phase = _ship_rebase_phase(
                    runner=runner,
                    working=working,
                    cwd=repo_root,
                    base_remote=base_remote,
                    base_ref=base_ref,
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                    variant=ShipRebaseVariant.MAIN_ADVANCED,
                )
                rebase_count = rebase_phase.rebase_count
                if rebase_phase.terminal is not None:
                    return rebase_phase.terminal
                iteration += 1
                _write_ship_state(
                    working,
                    phase="ci-initial",
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                )
                continue
            if merged.result == config.MERGE_RESULT_REVIEW_REQUIRED:
                _write_terminal_state(
                    ctx=working.with_(
                        stall_tracking=True,
                        stall_step="merge",
                        final_bail_reason=config.NEEDS_USER_REVIEW_REQUIRED,
                    ),
                    result=Outcome.NEEDS_USER_INPUT,
                    step="merge",
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                )
                _publish_post_pr_terminal_snapshot(
                    runner=runner,
                    ctx=working.with_(
                        stall_tracking=True,
                        stall_step="merge",
                        final_bail_reason=config.NEEDS_USER_REVIEW_REQUIRED,
                    ),
                    cwd=repo_root,
                )
                return ShipResult(
                    Outcome.NEEDS_USER_INPUT,
                    needs_user_reason=config.NEEDS_USER_REVIEW_REQUIRED,
                    pr_number=working.pr_number,
                    pr_url=working.pr_url,
                    detail=merged.error or "PR requires approving review",
                )
            pr_closed = merged.result in config.POST_MERGE_MERGE_RESULTS
            working = working.with_(
                merge_result=merged.result,
                pr_closed=pr_closed,
            )
            _write_ship_state(
                working,
                phase="postmerge" if pr_closed else "merge",
                iteration=iteration,
                rebase_count=rebase_count,
                fix_attempts=fix_attempts,
                transient_retries=transient_retries,
            )
            if merged.result == config.MERGE_RESULT_ERROR:
                _write_terminal_state(
                    ctx=working.with_(stall_tracking=True, stall_step="merge"),
                    result=Outcome.STALLED,
                    step="merge",
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                )
                _publish_post_pr_terminal_snapshot(runner=runner, ctx=working, cwd=repo_root)
                return ShipResult(
                    Outcome.STALLED,
                    pr_number=working.pr_number,
                    pr_url=working.pr_url,
                    merge_result=merged.result,
                    detail=merged.error,
                )
            if merged.result not in config.POST_MERGE_MERGE_RESULTS:
                _write_terminal_state(
                    ctx=working.with_(stall_tracking=True, stall_step="merge"),
                    result=Outcome.STALLED,
                    step="merge",
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                )
                _publish_post_pr_terminal_snapshot(runner=runner, ctx=working, cwd=repo_root)
                return ShipResult(
                    Outcome.STALLED,
                    pr_number=working.pr_number,
                    pr_url=working.pr_url,
                    merge_result=merged.result,
                    detail=merged.error or f"merge did not complete: {merged.result}",
                )
            return _ship_postmerge_phase(
                runner=runner,
                working=working,
                cwd=repo_root,
                iteration=iteration,
                rebase_count=rebase_count,
                fix_attempts=fix_attempts,
                transient_retries=transient_retries,
            )
    except (NeedsUserInput, ShipError, Stalled, TransientNetworkError) as exc:
        result = _error_to_result(exc)
        if result.outcome is Outcome.STALLED and not isinstance(exc, PrePushConflictHandoff):
            latest_ctx = _context_with_state_overlay(ctx)
            if "\n" in latest_ctx.pr_url or "\r" in latest_ctx.pr_url:
                latest_ctx = latest_ctx.with_(pr_url="")
            step = latest_ctx.stall_step or _slug_from_detail(result.detail)
            _write_terminal_state(ctx=latest_ctx.with_(stall_tracking=True, stall_step=step), result=Outcome.STALLED, step=step)
        return result


def _journal_path(ctx: RunContext) -> Path:
    return Path(
        config.PATH_JSONL_JOURNAL_TEMPLATE.format(
            tmpdir=ctx.tmpdir or ".",
            run_id=ctx.run_id or "unknown",
        ),
    )


def _close_contract_stream(stream: TextIO) -> None:
    if stream is not sys.stdout:
        with suppress(Exception):
            stream.close()


def emit_result(*, ctx: RunContext, result: ShipResult) -> None:
    payload = _redacted_result_payload(result)
    stream = logging_util.contract_stream()
    try:
        print(json.dumps(payload, sort_keys=True), file=stream)
        stream.flush()
    finally:
        _close_contract_stream(stream)
    if ctx.run_id and _tmpdir_under_allowed_root(ctx.tmpdir):
        try:
            journal = logging_util.JsonlJournal(_journal_path(ctx), ctx.run_id)
            _ = journal.append(config.JOURNAL_EVENT_SHIP_RESULT, **payload)
        except OSError as exc:
            logging_util.BreadcrumbWriter().emit(f"ship.py: journal append skipped: {exc}")


def _redacted_result_payload(result: ShipResult) -> dict[str, Any]:
    payload = result.to_json_dict()
    for key in ("needs_user_reason", "failed_run_id", "pr_url", "merge_result", "detail"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            redacted = redact.redact_outbound(value)
            payload[key] = "redacted" if "[content truncated" in redacted else redacted
    return payload



def _bool_arg(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


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


def _validate_seed_identity_args(args: argparse.Namespace) -> None:
    branch = (args.branch or "").strip()
    issue = (args.issue or "").strip()
    repo = (args.repo or "").strip()
    run_id = (args.run_id or "").strip()
    if not branch or not _valid_branch_name(branch):
        raise ShipError("--branch must be a non-empty valid branch name")
    if not issue or not issue.isdigit():
        raise ShipError("--issue must be a non-empty digit issue number")
    if not repo or not _valid_repo_slug(repo):
        raise ShipError("--repo must be a non-empty owner/repo slug")
    if not run_id:
        raise ShipError("--run-id must be non-empty")


def _validate_seed_manifest(path_text: str) -> None:
    if not path_text:
        return
    path = Path(path_text)
    if path.name.endswith(".env"):
        raise ShipError("MANIFEST_PATH must point at a readable JSON manifest, not a shell env file")
    try:
        with path.open("r", encoding="utf-8") as handle:
            parsed = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ShipError("MANIFEST_PATH must point at a readable JSON manifest") from exc
    if not isinstance(parsed, dict):
        raise ShipError("MANIFEST_PATH JSON manifest must be an object")


def _seed_initial_state_fields(args: argparse.Namespace) -> dict[str, str]:
    stall_step = args.stall_step or ""
    merge = _bool_arg(args.merge)
    draft = False if stall_step else _bool_arg(args.draft)
    fields = {
        "PHASE": "checks",
        "BRANCH_NAME": args.branch or "",
        "ISSUE_NUMBER": args.issue or "",
        "RUN_ID": args.run_id or "",
        "REPO": args.repo or "",
        "REPO_UNAVAILABLE": _state_bool(value=_bool_arg(args.repo_unavailable)),
        "FORKED_TARGET": _state_bool(value=_bool_arg(args.forked)),
        "MERGE": _state_bool(value=merge),
        "DRAFT": _state_bool(value=draft),
        "DEFERRED": _state_bool(value=_bool_arg(args.deferred)),
        "PR_CLOSED": "false",
        "DONE_RENAME_APPLIED": "false",
        "STALL_TRACKING": _state_bool(value=_bool_arg(args.stall_tracking)),
        "STALL_STEP": stall_step,
        "BAIL_NEEDS_USER_INPUT": "false",
        "BAIL_REASON": args.bail_reason or "",
        "BAIL_FAILURE_DETAIL_LOG": args.bail_failure_detail_log or "",
        "CI_PASSED": "false",
        "PR_NUMBER": "",
        "PR_URL": "",
        "PR_TITLE": "",
        "RESUME_PHASE": "",
        "CALLER_KIND": "",
        "REBASE_COUNT": "0",
        "FIX_ATTEMPTS": "0",
        "ITERATION": "0",
        "TRANSIENT_RETRIES": "0",
        "FAILED_RUN_ID": "",
        "MANIFEST_PATH": args.manifest_path or "",
        "TOOL_LABEL": args.tool_label or "",
        "DESIGN_ONLY_DONE": "false",
        "EXPECTED_SESSION_ID": args.expected_session_id or "",
        "EXPECTED_TMPDIR_BASENAME_PREFIX": args.expected_tmpdir_basename_prefix or "",
        "NO_ADMIN_FALLBACK": _state_bool(value=_bool_arg(args.no_admin_fallback)),
        "NO_LOGS_COMMIT": _state_bool(value=_bool_arg(args.no_logs_commit)),
        "IMPLEMENT_TMPDIR": args.tmpdir or "",
        "CI_FIX_REBASE_PENDING": "false",
        "OOS_PENDING": "false",
    }
    return {key: fields[key] for key in INITIAL_SHIP_STATE_KEYS}


def _write_initial_ship_state(args: argparse.Namespace) -> None:
    tmpdir = Path(args.tmpdir or "")
    if not _tmpdir_under_allowed_root(str(tmpdir)):
        raise ShipError("--tmpdir is not an allowed implement tmpdir")
    state_file = Path(args.state_file or (tmpdir / "ship-pr-state.sh"))
    if not _path_under(parent=tmpdir, child=state_file):
        raise ShipError("--state-file must stay under --tmpdir")
    if state_file.is_symlink():
        raise ShipError(f"refusing to write symlinked ship state path: {state_file}")
    if _state_file_has_kv(state_file):
        raise ShipError("ship initial state is create-if-absent only; refusing to overwrite existing state")
    _validate_seed_identity_args(args)
    fields = _seed_initial_state_fields(args)
    _validate_seed_manifest(fields["MANIFEST_PATH"])
    for key, value in fields.items():
        if key != key.upper() or "=" in key:
            raise ShipError(f"invalid ship state key: {key}")
        _validate_ship_state_value(key=key, value=value)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_file.with_suffix(state_file.suffix + ".tmp")
    if tmp.is_symlink():
        raise ShipError(f"refusing to write symlinked ship state temp path: {tmp}")
    with suppress(FileNotFoundError):
        tmp.unlink()
    data = "".join(f"{key}={fields[key]}\n" for key in INITIAL_SHIP_STATE_KEYS)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd: int | None = None
    try:
        fd = os.open(tmp, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = None
            _ = handle.write(data)
        _ = tmp.replace(state_file)
    except FileExistsError as exc:
        raise ShipError(f"refusing to overwrite existing ship state temp file: {tmp}") from exc
    finally:
        if fd is not None:
            os.close(fd)
        with suppress(OSError):
            if tmp.exists() and not tmp.is_symlink():
                tmp.unlink()


def build_seed_initial_state_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed initial ship-pr state")
    _ = parser.add_argument("--tmpdir", required=True)
    _ = parser.add_argument("--state-file")
    _ = parser.add_argument("--branch", required=True)
    _ = parser.add_argument("--issue", required=True)
    _ = parser.add_argument("--repo", required=True)
    _ = parser.add_argument("--run-id", required=True)
    _ = parser.add_argument("--manifest-path", default="")
    _ = parser.add_argument("--tool-label", default="")
    _ = parser.add_argument("--merge", default="false")
    _ = parser.add_argument("--draft", default="false")
    _ = parser.add_argument("--forked", default="false")
    _ = parser.add_argument("--repo-unavailable", default="false")
    _ = parser.add_argument("--deferred", default="false")
    _ = parser.add_argument("--no-admin-fallback", default="false")
    _ = parser.add_argument("--no-logs-commit", default="false")
    _ = parser.add_argument("--expected-session-id", default="")
    _ = parser.add_argument("--expected-tmpdir-basename-prefix", default="")
    _ = parser.add_argument("--stall-tracking", default="false")
    _ = parser.add_argument("--stall-step", default="")
    _ = parser.add_argument("--bail-reason", default="")
    _ = parser.add_argument("--bail-failure-detail-log", default="")
    return parser


def seed_initial_state_main(argv: list[str] | None = None) -> int:
    parser = build_seed_initial_state_parser()
    try:
        args = parser.parse_args(argv)
        _write_initial_ship_state(args)
        return 0
    except SystemExit as exc:
        return int(exc.code or 1)
    except ShipError as exc:
        print(f"ship seed-initial-state: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Python ship-pr driver")
    _ = parser.add_argument("--branch")
    _ = parser.add_argument("--issue")
    _ = parser.add_argument("--repo")
    _ = parser.add_argument("--run-id")
    _ = parser.add_argument("--tmpdir")
    _ = parser.add_argument("--manifest-path")
    _ = parser.add_argument("--state-file")
    _ = parser.add_argument("--tool-label")
    _ = parser.add_argument("--merge")
    _ = parser.add_argument("--draft")
    _ = parser.add_argument("--forked")
    _ = parser.add_argument("--repo-unavailable")
    _ = parser.add_argument("--no-admin-fallback")
    _ = parser.add_argument("--no-logs-commit", nargs="?", const="true", default=None)
    _ = parser.add_argument("--expected-session-id")
    _ = parser.add_argument("--expected-tmpdir-basename-prefix")
    return parser


def _state_file_kv(path: str | None) -> dict[str, str]:
    if not path:
        return {}
    if Path(path).is_symlink():
        return {}
    try:
        return finalize.read_finalize_state(path)
    except ShipError:
        return {}


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _first_present(*values: object) -> str:
    for value in values:
        if value is None:
            continue
        if isinstance(value, int):
            if value != 0:
                return str(value)
            continue
        text = str(value)
        if text:
            return text
    return ""


def _slug_from_detail(detail: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", detail.strip().lower()).strip("-")
    return slug[:80] or "stalled"


def _fill_if_empty(data: dict[str, str], key: str, *values: object) -> None:  # lint-keyword-only: ok *values vararg prevents bare-star separator
    if data.get(key):
        return
    value = _first_present(*values)
    if value:
        data[key] = value


def _persist_stall_metadata_if_needed(*, ctx: RunContext, result: ShipResult, tmpdir: Path) -> None:
    if result.outcome is not Outcome.STALLED:
        return
    if _is_active_pre_push_handoff(ctx):
        return
    if not _tmpdir_under_allowed_root(str(tmpdir)):
        return
    path = tmpdir / "finalize-state.sh"
    try:
        data: dict[str, str] = finalize.read_finalize_state(path)
        if _truthy(data.get("STALL_TRACKING", "")):
            return
        state = _state_file_kv(ctx.state_file)
        _fill_if_empty(data, "BRANCH_NAME", state.get("BRANCH_NAME"), ctx.branch)
        _fill_if_empty(data, "ISSUE_NUMBER", state.get("ISSUE_NUMBER"), ctx.issue_number, ctx.issue)
        _fill_if_empty(data, "REPO", state.get("REPO"), ctx.repo)
        _fill_if_empty(data, "RUN_ID", state.get("RUN_ID"), ctx.run_id)
        _fill_if_empty(data, "PR_NUMBER", result.pr_number, state.get("PR_NUMBER"), ctx.pr_number)
        state_pr_url = state.get("PR_URL", "")
        if state_pr_url and not _valid_pr_url(state_pr_url):
            state_pr_url = ""
        _fill_if_empty(data, "PR_URL", result.pr_url, state_pr_url, ctx.pr_url)
        _fill_if_empty(data, "PR_TITLE", state.get("PR_TITLE"), ctx.pr_title)
        _fill_if_empty(data, "MERGE_RESULT", result.merge_result, state.get("MERGE_RESULT"), ctx.merge_result)
        _fill_if_empty(data, "FORKED_TARGET", state.get("FORKED_TARGET"), "true" if ctx.forked else "false")
        _fill_if_empty(data, "REPO_UNAVAILABLE", state.get("REPO_UNAVAILABLE"), "true" if ctx.repo_unavailable else "false")
        _fill_if_empty(data, "DRAFT", state.get("DRAFT"), "true" if ctx.draft else "false")
        _fill_if_empty(data, "MERGE", state.get("MERGE"), "true" if ctx.merge else "false")
        data["STALL_TRACKING"] = "true"
        _fill_if_empty(data, "STALL_STEP", state.get("STALL_STEP"), ctx.stall_step, _slug_from_detail(result.detail))
        finalize.write_finalize_state_merged(path=path, data=data)
    except Exception as exc:
        logging_util.BreadcrumbWriter().emit(f"ship.py: stall metadata gap-fill failed: {exc}")


def _ctx_from_args(args: argparse.Namespace) -> RunContext:
    env_ctx = RunContext.from_env()
    changes: dict[str, object] = {}
    for arg_name, field_name in (
        ("branch", "branch"),
        ("issue", "issue"),
        ("issue", "issue_number"),
        ("repo", "repo"),
        ("run_id", "run_id"),
        ("tmpdir", "tmpdir"),
        ("manifest_path", "manifest_path"),
        ("state_file", "state_file"),
        ("tool_label", "tool_label"),
        ("expected_session_id", "expected_session_id"),
        ("expected_tmpdir_basename_prefix", "expected_tmpdir_basename_prefix"),
    ):
        value = getattr(args, arg_name)
        if value not in (None, ""):
            changes[field_name] = value
    for arg_name, field_name in (
        ("merge", "merge"),
        ("draft", "draft"),
        ("forked", "forked"),
        ("repo_unavailable", "repo_unavailable"),
        ("no_admin_fallback", "no_admin_fallback"),
    ):
        value = getattr(args, arg_name)
        if value is not None:
            changes[field_name] = str(value).strip().lower() in {"1", "true", "yes", "on"}
    if args.no_logs_commit is not None:
        changes["no_logs_commit"] = str(args.no_logs_commit).strip().lower() in {"1", "true", "yes", "on"}
    ctx = env_ctx.with_(**changes)
    if ctx.state_file:
        ctx = _context_with_state_overlay(ctx)
    return ctx


def main(argv: list[str] | None = None) -> int:
    ctx = RunContext.from_env(env={})
    result: ShipResult
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        if code == 0:
            return 0
        result = ShipResult(Outcome.INTERNAL_ERROR, detail=f"argparse failed with exit {code}")
        with suppress(Exception):
            emit_result(ctx=ctx, result=result)
        return config.OUTCOME_EXIT_MAP[Outcome.INTERNAL_ERROR]
    try:
        ctx = _ctx_from_args(args)
        if _tmpdir_under_allowed_root(ctx.tmpdir):
            os.environ[config.ENV_IMPLEMENT_TMPDIR] = ctx.tmpdir
            logging_util.quiet_init(argv0="ship.py")
        result = run_ship(ctx, runner=proc, cwd=str(Path.cwd()))
    except Exception as exc:  # top-level contract envelope
        logging_util.BreadcrumbWriter().emit(
            f"ship.py: internal error\n{traceback.format_exc()}",
        )
        result = ShipResult(Outcome.INTERNAL_ERROR, detail=f"{type(exc).__name__}: {exc}")
    _persist_stall_metadata_if_needed(ctx=ctx, result=result, tmpdir=Path(ctx.tmpdir))
    emit_result(ctx=ctx, result=result)
    return config.OUTCOME_EXIT_MAP[result.outcome]


if __name__ == "__main__":
    raise SystemExit(main())
