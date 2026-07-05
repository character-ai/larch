"""Architectural guidelines compose-time note helpers for ship-pr."""
# pyright: reportUnusedFunction=false

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from larch.core import architectural_guidelines
from larch.core import logging_util
from larch.errors import ShipError
from larch.git import pr_body
from larch.report import run_logs


@dataclass(frozen=True)
class GuidelinesGateResult:
    note: str = ""
    needs_assessment: bool = False
    warning_logged: bool = False
    detail: str = ""


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
    """Legacy no-drop invalidation helper kept for compatibility tests."""
    if not implement_tmpdir:
        return False
    tmpdir = Path(implement_tmpdir)
    try:
        architectural_guidelines.invalidate_implement_note(tmpdir)
    except OSError as exc:
        return _log_guidelines_ship_warning(
            implement_tmpdir=tmpdir,
            message=f"architectural-guidelines invalidate failed: {exc}",
        )
    return False


def _pin_or_invalidate_guidelines_note(
    *,
    implement_tmpdir: str,
    head_sha: str,
    base_ref: str,
    repo_root: str | None = None,
) -> bool:
    """Legacy no-op pre-push hook.

    Compose-time assessment owns note freshness. Rebase, merge, and CI-fix paths
    must not pin, invalidate, or emit a fallback note outside the compose gate.
    """
    _ = (head_sha, base_ref, repo_root)
    if implement_tmpdir:
        try:
            architectural_guidelines.clear_staged_and_dropped_artifacts(Path(implement_tmpdir))
        except OSError as exc:
            return _log_guidelines_ship_warning(
                implement_tmpdir=Path(implement_tmpdir),
                message=f"architectural-guidelines stale-artifact cleanup failed: {exc}",
            )
    return False


def _read_current_guidelines_note(*, tmpdir: Path, head_sha: str) -> GuidelinesGateResult:
    if not architectural_guidelines.note_consumable(implement_tmpdir=tmpdir, head_sha=head_sha):
        return GuidelinesGateResult()
    try:
        note = architectural_guidelines.durable_note_path(tmpdir).read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        warning_logged = _log_guidelines_ship_warning(
            implement_tmpdir=tmpdir,
            message=f"architectural-guidelines note read failed: {exc}",
        )
        return GuidelinesGateResult(warning_logged=warning_logged)
    try:
        return GuidelinesGateResult(note=pr_body.redact_pr_body(note).strip())
    except ShipError as exc:
        warning_logged = _log_guidelines_ship_warning(
            implement_tmpdir=tmpdir,
            message=f"architectural-guidelines note redaction failed: {exc}",
        )
        return GuidelinesGateResult(warning_logged=warning_logged)


def load_or_prepare_guidelines_note(
    *,
    implement_tmpdir: str,
    head_sha: str,
    base_ref: str,
    repo_root: str | None = None,
    forked_target: bool = False,
) -> GuidelinesGateResult:
    """Return the current durable note or prepare compose-time assessment input."""
    _ = base_ref
    if not implement_tmpdir or not head_sha:
        return GuidelinesGateResult()
    tmpdir = Path(implement_tmpdir)
    current = _read_current_guidelines_note(tmpdir=tmpdir, head_sha=head_sha)
    if current.note or current.warning_logged:
        return current
    prepared = architectural_guidelines.prepare_compose_assessment(
        implement_tmpdir=tmpdir,
        repo_root=repo_root,
        forked_target=forked_target,
        expected_head_sha=head_sha,
    )
    if prepared.status == "current":
        return _read_current_guidelines_note(tmpdir=tmpdir, head_sha=head_sha)
    if prepared.status == "assessment-required":
        return GuidelinesGateResult(
            needs_assessment=True,
            detail="architectural-guidelines assessment required before PR body compose",
        )
    if prepared.warning:
        warning_logged = _log_guidelines_ship_warning(
            implement_tmpdir=tmpdir,
            message=f"architectural-guidelines compose materialization skipped: {prepared.warning}",
        )
        return GuidelinesGateResult(warning_logged=warning_logged)
    return GuidelinesGateResult()


# Backward-compatible alias for old unit tests. It no longer pins staged notes.
def _pin_and_load_guidelines_note(
    *,
    implement_tmpdir: str,
    head_sha: str,
    base_ref: str,
    repo_root: str | None = None,
) -> tuple[str, bool]:
    result = load_or_prepare_guidelines_note(
        implement_tmpdir=implement_tmpdir,
        head_sha=head_sha,
        base_ref=base_ref,
        repo_root=repo_root,
    )
    return result.note, result.warning_logged
