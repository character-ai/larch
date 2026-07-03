"""Architectural guidelines note pin/load/invalidate helpers for ship-pr."""
# pyright: reportUnusedFunction=false

from __future__ import annotations

from pathlib import Path

from larch.core import architectural_guidelines
from larch.core import logging_util
from larch.errors import ShipError
from larch.git import pr_body
from larch.report import run_logs


def _log_guidelines_ship_warning(*, implement_tmpdir: Path, message: str) -> bool:
    issue_log = implement_tmpdir / "execution-issues.md"
    try:
        run_logs.append_execution_issue(log_file=issue_log, category="Warnings", entry=message)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        detail = logging_util.sanitize_diagnostic_line(str(exc))
        logging_util.BreadcrumbWriter().emit(
            f"ship-pr: architectural-guidelines warning append failed: {detail}",
        )
        return False
    return True


def _invalidate_guidelines_note(implement_tmpdir: str) -> bool:
    if not implement_tmpdir:
        return False
    tmpdir = Path(implement_tmpdir)
    warning_logged = False
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
            warning_logged = _log_guidelines_ship_warning(
                implement_tmpdir=tmpdir,
                message="architectural-guidelines drop notice persist failed before invalidate",
            ) or warning_logged
        architectural_guidelines.invalidate_implement_note(tmpdir)
    except OSError as exc:
        warning_logged = _log_guidelines_ship_warning(
            implement_tmpdir=tmpdir,
            message=f"architectural-guidelines invalidate failed: {exc}",
        ) or warning_logged
    return warning_logged


def _read_persisted_guidelines_drop_notice(tmpdir: Path) -> str:
    return architectural_guidelines.read_dropped_note_notice(tmpdir).strip()


def _persist_guidelines_drop_notice(tmpdir: Path) -> tuple[str, bool]:
    try:
        redacted = pr_body.redact_pr_body(architectural_guidelines.dropped_note_message()).strip()
    except ShipError as exc:
        warning_logged = _log_guidelines_ship_warning(
            implement_tmpdir=tmpdir,
            message=f"architectural-guidelines drop notice redaction failed: {exc}",
        )
        return "", warning_logged
    if not redacted:
        return "", False
    if architectural_guidelines.persist_dropped_note_notice(tmpdir, notice_text=redacted):
        return redacted, False
    return _read_persisted_guidelines_drop_notice(tmpdir), False


def _handle_unconsumable_guidelines_note(*, tmpdir: Path, staged_present: bool) -> tuple[str, bool]:
    notice = _read_persisted_guidelines_drop_notice(tmpdir)
    if notice:
        return notice, False
    if not staged_present:
        return "", False
    notice, warning_logged = _persist_guidelines_drop_notice(tmpdir)
    if notice:
        return notice, warning_logged
    warning_logged = _log_guidelines_ship_warning(
        implement_tmpdir=tmpdir,
        message="architectural-guidelines drop notice persist failed after pin skip",
    ) or warning_logged
    return "", warning_logged


def _handle_stale_guidelines_note(*, tmpdir: Path, staged_present: bool) -> tuple[str, bool]:
    should_persist = staged_present or architectural_guidelines.durable_note_present(tmpdir)
    persisted = False
    warning_logged = False
    if should_persist:
        persisted = architectural_guidelines.maybe_persist_dropped_note_before_invalidate(
            tmpdir,
            redact_fn=pr_body.redact_pr_body,
        )
    try:
        architectural_guidelines.invalidate_implement_note(tmpdir)
    except OSError as exc:
        warning_logged = _log_guidelines_ship_warning(
            implement_tmpdir=tmpdir,
            message=f"architectural-guidelines invalidate failed: {exc}",
        )
    if persisted:
        return _read_persisted_guidelines_drop_notice(tmpdir), warning_logged
    notice = _read_persisted_guidelines_drop_notice(tmpdir)
    return notice or "", warning_logged


def _pin_and_load_guidelines_note(
    *,
    implement_tmpdir: str,
    head_sha: str,
    base_ref: str,
    repo_root: str | None = None,
) -> tuple[str, bool]:
    if not implement_tmpdir or not head_sha:
        return "", False
    tmpdir = Path(implement_tmpdir)
    warning_logged = False
    staged_present = architectural_guidelines.staged_assessment_present(tmpdir)
    if architectural_guidelines.staged_assessment_path(tmpdir).is_file():
        pinned_now = architectural_guidelines.pin_note_from_staged_for_current_head(
            tmpdir,
            head_sha=head_sha,
            base_ref=base_ref,
            repo_root=repo_root,
        )
        if not pinned_now:
            warning_logged = _log_guidelines_ship_warning(
                implement_tmpdir=tmpdir,
                message="architectural-guidelines pin-note-from-staged skipped or failed fingerprint validation",
            ) or warning_logged
    if not architectural_guidelines.note_consumable(implement_tmpdir=tmpdir, head_sha=head_sha):
        note, logged = _handle_unconsumable_guidelines_note(
            tmpdir=tmpdir,
            staged_present=staged_present,
        )
        return note, warning_logged or logged
    meta: dict[str, str] = architectural_guidelines.durable_note_metadata(tmpdir)
    note_base_ref = base_ref or meta.get("BASE_REF", "")
    if architectural_guidelines.note_fingerprint_stale(
        tmpdir,
        base_ref=note_base_ref,
        repo_root=repo_root,
    ):
        note, logged = _handle_stale_guidelines_note(tmpdir=tmpdir, staged_present=staged_present)
        return note, warning_logged or logged
    try:
        note = architectural_guidelines.durable_note_path(tmpdir).read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        warning_logged = _log_guidelines_ship_warning(
            implement_tmpdir=tmpdir,
            message=f"architectural-guidelines note read failed: {exc}",
        ) or warning_logged
        return "", warning_logged
    try:
        return pr_body.redact_pr_body(note).strip(), warning_logged
    except ShipError as exc:
        warning_logged = _log_guidelines_ship_warning(
            implement_tmpdir=tmpdir,
            message=f"architectural-guidelines note redaction failed: {exc}",
        ) or warning_logged
        return "", warning_logged
