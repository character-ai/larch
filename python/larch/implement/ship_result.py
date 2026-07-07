"""ShipResult dataclass, result helpers, and emit/journal utilities."""
# pyright: reportUnusedFunction=false, reportPrivateUsage=false

from __future__ import annotations

import json
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from larch.core import config
from larch.core import logging_util
from larch.core import redact
from larch.core.run_context import RunContext
from larch.errors import NeedsUserInput, ShipError, Stalled, TransientNetworkError
from larch.outcomes import Outcome, StepResult
from larch.state import finalize
from larch.implement.ship_state import _tmpdir_under_allowed_root, _terminal_overlay_fields, _breadcrumb


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
        config.NEEDS_USER_MAIN_CI_FAIL,
        config.NEEDS_USER_FLAKY_DEFECT_UNFIXED,
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
