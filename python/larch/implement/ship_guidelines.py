"""Architectural guidelines compose-time note helpers for ship-pr."""
# pyright: reportUnusedFunction=false

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from larch.core import architectural_guidelines
from larch.core import logging_util
from larch.core import redact
from larch.errors import ShipError
from larch.git import pr_body
from larch.report import run_logs

OUTCOME_PINNED = "pinned"
OUTCOME_CLEAN = "clean"
OUTCOME_VIOLATION = "violation"
OUTCOME_DROPPED = "dropped"
GUIDELINE_SHIP_OUTCOMES = frozenset({OUTCOME_PINNED, OUTCOME_CLEAN, OUTCOME_DROPPED})
INVARIANT_SHIP_OUTCOMES = frozenset({OUTCOME_CLEAN, OUTCOME_VIOLATION, OUTCOME_DROPPED})

REASON_NOTE_PINNED = "note-pinned"
REASON_CLEAN_NOTE = "clean-note"
REASON_GUIDELINES_ABSENT = "guidelines-absent"
REASON_GUIDELINES_INVALID = "guidelines-invalid"
REASON_INVARIANTS_ABSENT = "invariants-absent"
REASON_INVARIANTS_EMPTY = "invariants-empty"
REASON_INVARIANTS_INVALID = "invariants-invalid"
REASON_VIOLATION_NOTE = "violation-note"
REASON_NOTE_READ_FAILED = "note-read-failed"
REASON_NOTE_REDACTION_FAILED = "note-redaction-failed"
REASON_COMPOSE_MATERIALIZATION_FAILED = "compose-materialization-failed"
REASON_UNKNOWN = "unknown"
GUIDELINE_SHIP_REASON_TOKENS = frozenset(
    {
        REASON_NOTE_PINNED,
        REASON_CLEAN_NOTE,
        REASON_GUIDELINES_ABSENT,
        REASON_GUIDELINES_INVALID,
        REASON_NOTE_READ_FAILED,
        REASON_NOTE_REDACTION_FAILED,
        REASON_COMPOSE_MATERIALIZATION_FAILED,
        REASON_UNKNOWN,
    }
)
INVARIANT_SHIP_REASON_TOKENS = frozenset(
    {
        REASON_CLEAN_NOTE,
        REASON_INVARIANTS_ABSENT,
        REASON_INVARIANTS_EMPTY,
        REASON_INVARIANTS_INVALID,
        REASON_NOTE_READ_FAILED,
        REASON_NOTE_REDACTION_FAILED,
        REASON_COMPOSE_MATERIALIZATION_FAILED,
        REASON_VIOLATION_NOTE,
        REASON_UNKNOWN,
    }
)


@dataclass(frozen=True)
class GuidelinesGateResult:
    note: str = ""
    needs_assessment: bool = False
    warning_logged: bool = False
    detail: str = ""
    guidelines_status: str = ""
    assessment_kind: str = ""
    reason: str = ""


@dataclass(frozen=True)
class GuidelinesShipOutcome:
    schema_version: str
    phase: str
    step: str
    outcome: str
    reason: str
    detail: str
    guidelines_status: str
    head_sha: str
    base_ref: str
    assessment_kind: str

    def as_json(self) -> dict[str, str]:
        return {
            "schema_version": self.schema_version,
            "phase": self.phase,
            "step": self.step,
            "outcome": self.outcome,
            "reason": self.reason,
            "detail": self.detail,
            "guidelines_status": self.guidelines_status,
            "head_sha": self.head_sha,
            "base_ref": self.base_ref,
            "assessment_kind": self.assessment_kind,
        }


@dataclass(frozen=True)
class InvariantsGateResult:
    note: str = ""
    needs_assessment: bool = False
    warning_logged: bool = False
    detail: str = ""
    invariants_status: str = ""
    assessment_kind: str = ""
    reason: str = ""


@dataclass(frozen=True)
class InvariantsShipOutcome:
    schema_version: str
    phase: str
    step: str
    outcome: str
    reason: str
    detail: str
    invariants_status: str
    head_sha: str
    base_ref: str
    assessment_kind: str

    def as_json(self) -> dict[str, str]:
        return {
            "schema_version": self.schema_version,
            "phase": self.phase,
            "step": self.step,
            "outcome": self.outcome,
            "reason": self.reason,
            "detail": self.detail,
            "invariants_status": self.invariants_status,
            "head_sha": self.head_sha,
            "base_ref": self.base_ref,
            "assessment_kind": self.assessment_kind,
        }


def _assessment_kind(note: str) -> str:
    if not note.strip():
        return ""
    if note.rstrip("\n") == architectural_guidelines.CLEAN_PRESENTATION_NOTE:
        return "clean"
    return "deviation"


def _invariant_assessment_kind(note: str) -> str:
    if not note.strip():
        return ""
    if note.rstrip("\n") == architectural_guidelines.CLEAN_INVARIANT_PRESENTATION_NOTE:
        return "clean"
    return "violation"


def _bounded_detail(text: str) -> str:
    clean = logging_util.sanitize_diagnostic_line(redact.redact_outbound(text or ""))
    return clean[:500]


def _write_json_atomic(*, path: Path, data: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    _ = tmp.write_text(json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    _ = tmp.replace(path)


def _classify_ship_outcome(
    *,
    result: GuidelinesGateResult,
    head_sha: str,
    base_ref: str,
) -> GuidelinesShipOutcome:
    guidelines_status = result.guidelines_status
    if guidelines_status not in {"present", "absent", "invalid"}:
        guidelines_status = "absent"
    assessment_kind = result.assessment_kind or _assessment_kind(result.note)
    reason = result.reason
    if guidelines_status == "absent":
        outcome = OUTCOME_CLEAN
        reason = REASON_GUIDELINES_ABSENT
        assessment_kind = ""
    elif guidelines_status == "invalid":
        outcome = OUTCOME_CLEAN
        reason = REASON_GUIDELINES_INVALID
        assessment_kind = ""
    elif result.note and assessment_kind == "clean":
        outcome = OUTCOME_CLEAN
        reason = reason or REASON_CLEAN_NOTE
    elif result.note:
        outcome = OUTCOME_PINNED
        reason = reason or REASON_NOTE_PINNED
    else:
        outcome = OUTCOME_DROPPED
        reason = reason or REASON_COMPOSE_MATERIALIZATION_FAILED
    if reason not in GUIDELINE_SHIP_REASON_TOKENS:
        reason = REASON_UNKNOWN
    return GuidelinesShipOutcome(
        schema_version="1",
        phase="implement",
        step="8",
        outcome=outcome,
        reason=reason,
        detail=_bounded_detail(result.detail),
        guidelines_status=guidelines_status,
        head_sha=_bounded_detail(head_sha),
        base_ref=_bounded_detail(base_ref),
        assessment_kind=assessment_kind if assessment_kind in {"clean", "deviation"} else "",
    )


def clear_guideline_ship_outcome_sidecar(*, implement_tmpdir: str) -> None:
    if not implement_tmpdir:
        return
    architectural_guidelines.clear_guideline_ship_outcome(Path(implement_tmpdir))


def write_guideline_ship_outcome(
    *,
    implement_tmpdir: str,
    result: GuidelinesGateResult,
    head_sha: str,
    base_ref: str,
) -> GuidelinesShipOutcome | None:
    """Write the durable Step 8 guideline outcome sidecar for terminal gate results."""
    if result.needs_assessment or not implement_tmpdir:
        return None
    if not head_sha.strip():
        message = "architectural-guidelines outcome head_sha is empty"
        _log_guidelines_ship_warning(implement_tmpdir=Path(implement_tmpdir), message=message)
        raise OSError(message)
    outcome = _classify_ship_outcome(result=result, head_sha=head_sha, base_ref=base_ref)
    _write_json_atomic(
        path=architectural_guidelines.guideline_ship_outcome_path(Path(implement_tmpdir)),
        data=outcome.as_json(),
    )
    return outcome


def _classify_invariant_ship_outcome(
    *,
    result: InvariantsGateResult,
    head_sha: str,
    base_ref: str,
) -> InvariantsShipOutcome:
    invariants_status = result.invariants_status
    if invariants_status not in {"present", "absent", "invalid"}:
        invariants_status = "absent"
    assessment_kind = result.assessment_kind or _invariant_assessment_kind(result.note)
    reason = result.reason
    if invariants_status == "absent":
        outcome = OUTCOME_CLEAN
        reason = REASON_INVARIANTS_ABSENT
        assessment_kind = ""
    elif invariants_status == "invalid":
        outcome = OUTCOME_CLEAN
        reason = REASON_INVARIANTS_INVALID
        assessment_kind = ""
    elif result.note and assessment_kind == "clean":
        outcome = OUTCOME_CLEAN
        reason = reason or REASON_CLEAN_NOTE
    elif result.note:
        outcome = OUTCOME_VIOLATION
        reason = reason or REASON_VIOLATION_NOTE
        assessment_kind = "violation"
    else:
        outcome = OUTCOME_DROPPED
        reason = reason or REASON_COMPOSE_MATERIALIZATION_FAILED
        assessment_kind = ""
    if reason not in INVARIANT_SHIP_REASON_TOKENS:
        reason = REASON_UNKNOWN
    return InvariantsShipOutcome(
        schema_version="1",
        phase="implement",
        step="8",
        outcome=outcome,
        reason=reason,
        detail=_bounded_detail(result.detail),
        invariants_status=invariants_status,
        head_sha=_bounded_detail(head_sha),
        base_ref=_bounded_detail(base_ref),
        assessment_kind=assessment_kind if assessment_kind in {"clean", "violation"} else "",
    )


def clear_invariant_ship_outcome_sidecar(*, implement_tmpdir: str) -> None:
    if not implement_tmpdir:
        return
    architectural_guidelines.clear_invariant_ship_outcome(Path(implement_tmpdir))


def write_invariant_ship_outcome(
    *,
    implement_tmpdir: str,
    result: InvariantsGateResult,
    head_sha: str,
    base_ref: str,
) -> InvariantsShipOutcome | None:
    """Write the durable Step 8 invariant outcome sidecar for terminal gate results."""
    if result.needs_assessment or not implement_tmpdir:
        return None
    if not head_sha.strip():
        message = "architectural-invariants outcome head_sha is empty"
        _log_guidelines_ship_warning(implement_tmpdir=Path(implement_tmpdir), message=message)
        raise OSError(message)
    outcome = _classify_invariant_ship_outcome(result=result, head_sha=head_sha, base_ref=base_ref)
    _write_json_atomic(
        path=architectural_guidelines.invariant_ship_outcome_path(Path(implement_tmpdir)),
        data=outcome.as_json(),
    )
    return outcome


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


def _read_current_guidelines_note(
    *,
    tmpdir: Path,
    head_sha: str,
    base_ref: str = "",
    repo_root: str | None = None,
) -> GuidelinesGateResult:
    if not architectural_guidelines.note_consumable(
        implement_tmpdir=tmpdir,
        head_sha=head_sha,
        base_ref=base_ref,
        repo_root=repo_root,
    ):
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
        return GuidelinesGateResult(
            needs_assessment=False,
            warning_logged=warning_logged,
            detail=f"architectural-guidelines note read failed: {exc}",
            guidelines_status="present",
            reason=REASON_NOTE_READ_FAILED,
        )
    try:
        redacted_note = pr_body.redact_pr_body(note).strip()
        metadata = architectural_guidelines.durable_note_metadata(tmpdir)
        return GuidelinesGateResult(
            note=redacted_note,
            guidelines_status=metadata.get("GUIDELINES_STATUS", "present") or "present",
            assessment_kind=metadata.get("ASSESSMENT_KIND", "") or _assessment_kind(redacted_note),
        )
    except ShipError as exc:
        warning_logged = _log_guidelines_ship_warning(
            implement_tmpdir=tmpdir,
            message=f"architectural-guidelines note redaction failed: {exc}",
        )
        return GuidelinesGateResult(
            needs_assessment=False,
            warning_logged=warning_logged,
            detail=f"architectural-guidelines note redaction failed: {exc}",
            guidelines_status="present",
            reason=REASON_NOTE_REDACTION_FAILED,
        )


def _current_guidelines_result(
    *,
    current: GuidelinesGateResult,
    tmpdir: Path,
    base_ref: str,
    repo_root: str | None,
) -> GuidelinesGateResult | None:
    if current.note:
        if repo_root is not None and base_ref and architectural_guidelines.note_fingerprint_stale(
            tmpdir,
            base_ref=base_ref,
            repo_root=repo_root,
        ):
            return None
        return current
    if current.needs_assessment or current.reason:
        return current
    return None


def _warning_for_prepared(*, tmpdir: Path, warning: str) -> bool:
    if not warning:
        return False
    return _log_guidelines_ship_warning(
        implement_tmpdir=tmpdir,
        message=f"architectural-guidelines compose materialization skipped: {warning}",
    )


def _prepared_guidelines_result(
    *,
    prepared: architectural_guidelines.ComposeMaterializationResult,
    tmpdir: Path,
    head_sha: str,
    base_ref: str,
    repo_root: str | None,
) -> GuidelinesGateResult:
    if prepared.status == "current":
        return _read_current_guidelines_note(
            tmpdir=tmpdir,
            head_sha=head_sha,
            base_ref=base_ref,
            repo_root=repo_root,
        )
    if prepared.status == "assessment-required":
        return GuidelinesGateResult(
            needs_assessment=True,
            detail="architectural-guidelines assessment required before PR body compose",
            guidelines_status=prepared.guidelines_status,
        )
    if prepared.status in {"absent", "invalid"}:
        return GuidelinesGateResult(
            warning_logged=_warning_for_prepared(tmpdir=tmpdir, warning=prepared.warning),
            detail=prepared.warning,
            guidelines_status=prepared.guidelines_status or prepared.status,
            reason=REASON_GUIDELINES_INVALID if prepared.status == "invalid" else REASON_GUIDELINES_ABSENT,
        )
    return GuidelinesGateResult(
        warning_logged=_warning_for_prepared(tmpdir=tmpdir, warning=prepared.warning),
        detail=prepared.warning,
        guidelines_status=prepared.guidelines_status or "present",
        reason=REASON_COMPOSE_MATERIALIZATION_FAILED,
    )


def load_or_prepare_guidelines_note(
    *,
    implement_tmpdir: str,
    head_sha: str,
    base_ref: str,
    repo_root: str | None = None,
    forked_target: bool = False,
) -> GuidelinesGateResult:
    """Return the current durable note or prepare compose-time assessment input."""
    if not implement_tmpdir or not head_sha:
        return GuidelinesGateResult()
    tmpdir = Path(implement_tmpdir)
    current = _current_guidelines_result(
        current=_read_current_guidelines_note(
            tmpdir=tmpdir,
            head_sha=head_sha,
            base_ref=base_ref,
            repo_root=repo_root,
        ),
        tmpdir=tmpdir,
        base_ref=base_ref,
        repo_root=repo_root,
    )
    if current is not None:
        return current
    prepared = architectural_guidelines.prepare_compose_assessment(
        implement_tmpdir=tmpdir,
        repo_root=repo_root,
        forked_target=forked_target,
        expected_head_sha=head_sha,
    )
    return _prepared_guidelines_result(
        prepared=prepared,
        tmpdir=tmpdir,
        head_sha=head_sha,
        base_ref=base_ref,
        repo_root=repo_root,
    )


def _read_current_invariant_note(
    *,
    tmpdir: Path,
    head_sha: str,
    base_ref: str = "",
    repo_root: str | None = None,
) -> InvariantsGateResult:
    if not architectural_guidelines.invariant_note_consumable(
        implement_tmpdir=tmpdir,
        head_sha=head_sha,
        base_ref=base_ref,
        repo_root=repo_root,
    ):
        return InvariantsGateResult()
    try:
        note = architectural_guidelines.invariant_durable_note_path(tmpdir).read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        warning_logged = _log_guidelines_ship_warning(
            implement_tmpdir=tmpdir,
            message=f"architectural-invariants note read failed: {exc}",
        )
        return InvariantsGateResult(
            warning_logged=warning_logged,
            detail=f"architectural-invariants note read failed: {exc}",
            invariants_status="present",
            reason=REASON_NOTE_READ_FAILED,
        )
    try:
        redacted_note = pr_body.redact_pr_body(note).strip()
        metadata = architectural_guidelines.invariant_durable_note_metadata(tmpdir)
        return InvariantsGateResult(
            note=redacted_note,
            invariants_status=metadata.get("INVARIANTS_STATUS", "present") or "present",
            assessment_kind=metadata.get("ASSESSMENT_KIND", "") or _invariant_assessment_kind(redacted_note),
        )
    except ShipError as exc:
        warning_logged = _log_guidelines_ship_warning(
            implement_tmpdir=tmpdir,
            message=f"architectural-invariants note redaction failed: {exc}",
        )
        return InvariantsGateResult(
            warning_logged=warning_logged,
            detail=f"architectural-invariants note redaction failed: {exc}",
            invariants_status="present",
            reason=REASON_NOTE_REDACTION_FAILED,
        )


def _current_invariant_result(
    *,
    current: InvariantsGateResult,
    tmpdir: Path,
    base_ref: str,
    repo_root: str | None,
) -> InvariantsGateResult | None:
    if current.note:
        if repo_root is not None and base_ref and architectural_guidelines.invariant_note_fingerprint_stale(
            tmpdir,
            base_ref=base_ref,
            repo_root=repo_root,
        ):
            return None
        return current
    if current.needs_assessment or current.reason:
        return current
    return None


def _prepared_invariant_result(
    *,
    prepared: architectural_guidelines.ComposeMaterializationResult,
    tmpdir: Path,
    head_sha: str,
    base_ref: str,
    repo_root: str | None,
) -> InvariantsGateResult:
    if prepared.status == "current":
        return _read_current_invariant_note(
            tmpdir=tmpdir,
            head_sha=head_sha,
            base_ref=base_ref,
            repo_root=repo_root,
        )
    if prepared.status == "assessment-required":
        return InvariantsGateResult(
            needs_assessment=True,
            detail="architectural-invariants assessment required before PR body compose",
            invariants_status=prepared.guidelines_status,
        )
    if prepared.status == "present-empty":
        return InvariantsGateResult(
            invariants_status=prepared.guidelines_status or "present",
            assessment_kind="clean",
            reason=REASON_INVARIANTS_EMPTY,
        )
    if prepared.status in {"absent", "invalid"}:
        return InvariantsGateResult(
            warning_logged=_warning_for_prepared(tmpdir=tmpdir, warning=prepared.warning),
            detail=prepared.warning,
            invariants_status=prepared.guidelines_status or prepared.status,
            reason=REASON_INVARIANTS_INVALID if prepared.status == "invalid" else REASON_INVARIANTS_ABSENT,
        )
    return InvariantsGateResult(
        warning_logged=_warning_for_prepared(tmpdir=tmpdir, warning=prepared.warning),
        detail=prepared.warning,
        invariants_status=prepared.guidelines_status or "present",
        reason=REASON_COMPOSE_MATERIALIZATION_FAILED,
    )


def load_or_prepare_invariants_note(
    *,
    implement_tmpdir: str,
    head_sha: str,
    base_ref: str,
    repo_root: str | None = None,
    forked_target: bool = False,
) -> InvariantsGateResult:
    """Return the current durable invariant note or prepare compose-time assessment input."""
    if not implement_tmpdir or not head_sha:
        return InvariantsGateResult()
    tmpdir = Path(implement_tmpdir)
    current = _current_invariant_result(
        current=_read_current_invariant_note(
            tmpdir=tmpdir,
            head_sha=head_sha,
            base_ref=base_ref,
            repo_root=repo_root,
        ),
        tmpdir=tmpdir,
        base_ref=base_ref,
        repo_root=repo_root,
    )
    if current is not None:
        return current
    prepared = architectural_guidelines.prepare_invariant_compose_assessment(
        implement_tmpdir=tmpdir,
        repo_root=repo_root,
        forked_target=forked_target,
        expected_head_sha=head_sha,
    )
    return _prepared_invariant_result(
        prepared=prepared,
        tmpdir=tmpdir,
        head_sha=head_sha,
        base_ref=base_ref,
        repo_root=repo_root,
    )


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
# pyright: reportUnusedCallResult=false
