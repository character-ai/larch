"""Architectural guidelines note pin/load/invalidate helpers for ship-pr."""
# pyright: reportUnusedFunction=false

from __future__ import annotations

from contextlib import suppress
from pathlib import Path

from larch.core import architectural_guidelines
from larch.errors import ShipError
from larch.git import pr_body
from larch.report import run_logs


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
        pinned_now = architectural_guidelines.pin_note_from_staged_for_current_head(
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
