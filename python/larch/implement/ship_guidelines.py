"""Architectural guidelines compose-time note helpers for ship-pr."""
# pyright: reportUnusedFunction=false

from __future__ import annotations

import json
import stat
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import ClassVar, cast

from larch import io as larch_io
from larch.core import architectural_guidelines
from larch.core import config
from larch.core import logging_util
from larch.core import redact
from larch.core.assessment_kind import AssessmentKind, GUIDELINES, INVARIANTS
from larch.errors import ShipError
from larch.git import pr_body
from larch.report import run_logs

OUTCOME_PINNED = GUIDELINES.non_clean_ship_outcome
OUTCOME_CLEAN = config.ASSESSMENT_OUTCOME_CLEAN
OUTCOME_VIOLATION = INVARIANTS.non_clean_ship_outcome
OUTCOME_DROPPED = "dropped"
GUIDELINE_SHIP_OUTCOMES = GUIDELINES.ship_outcomes
INVARIANT_SHIP_OUTCOMES = INVARIANTS.ship_outcomes

REASON_NOTE_PINNED = GUIDELINES.non_clean_note_reason
REASON_CLEAN_NOTE = "clean-note"
REASON_GUIDELINES_ABSENT = GUIDELINES.absent_reason
REASON_GUIDELINES_INVALID = GUIDELINES.invalid_reason
REASON_INVARIANTS_ABSENT = INVARIANTS.absent_reason
REASON_INVARIANTS_EMPTY = INVARIANTS.empty_reason
REASON_INVARIANTS_INVALID = INVARIANTS.invalid_reason
REASON_VIOLATION_NOTE = INVARIANTS.non_clean_note_reason
REASON_NOTE_READ_FAILED = "note-read-failed"
REASON_NOTE_REDACTION_FAILED = "note-redaction-failed"
REASON_COMPOSE_MATERIALIZATION_FAILED = "compose-materialization-failed"
REASON_UNKNOWN = "unknown"
REASON_DETERMINISTIC_CLEAN = config.REASON_DETERMINISTIC_CLEAN
REASON_UNAVAILABLE = config.REASON_UNAVAILABLE
GUIDELINE_SHIP_REASON_TOKENS = GUIDELINES.ship_reason_tokens
INVARIANT_SHIP_REASON_TOKENS = INVARIANTS.ship_reason_tokens


@dataclass(frozen=True)
class GuidelinesGateResult:
    note: str = ""
    needs_assessment: bool = False
    warning_logged: bool = False
    detail: str = ""
    guidelines_status: str = ""
    assessment_kind: str = ""
    reason: str = ""
    note_state: str = config.NOTE_STATE_AUTHORED


class _ShipOutcomeJson:
    """Shared serializer for the two public compatibility records."""

    status_field: ClassVar[str]

    def as_json(self) -> dict[str, object]:
        return {
            name: getattr(self, name)
            for name in (
                "schema_version", "phase", "step", "outcome", "reason", "detail",
                self.status_field, "head_sha", "base_ref", "assessment_kind", "operator_waived",
            )
        }


@dataclass(frozen=True)
class GuidelinesShipOutcome(_ShipOutcomeJson):
    status_field: ClassVar[str] = "guidelines_status"
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
    operator_waived: bool = False

@dataclass(frozen=True)
class InvariantsGateResult:
    note: str = ""
    needs_assessment: bool = False
    warning_logged: bool = False
    detail: str = ""
    invariants_status: str = ""
    assessment_kind: str = ""
    reason: str = ""
    note_state: str = config.NOTE_STATE_AUTHORED


@dataclass(frozen=True)
class InvariantsShipOutcome(_ShipOutcomeJson):
    status_field: ClassVar[str] = "invariants_status"
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
    operator_waived: bool = False

GateResult = GuidelinesGateResult | InvariantsGateResult
ShipOutcome = GuidelinesShipOutcome | InvariantsShipOutcome


def _status(result: GateResult, *, kind: AssessmentKind) -> str:
    if kind.is_invariant != isinstance(result, InvariantsGateResult):
        raise TypeError(f"{kind.singular} descriptor requires its matching gate result")
    return str(getattr(result, kind.status_field))


def _gate(*, kind: AssessmentKind, status: str = "", **values: object) -> GateResult:
    result_type = InvariantsGateResult if kind.is_invariant else GuidelinesGateResult
    return result_type(**values, **{kind.status_field: status})  # type: ignore[arg-type]  # reason: descriptor selects the matching compatibility dataclass and status keyword


def _outcome(*, kind: AssessmentKind, status: str, **values: object) -> ShipOutcome:
    result_type = InvariantsShipOutcome if kind.is_invariant else GuidelinesShipOutcome
    return result_type(  # type: ignore[arg-type]  # reason: descriptor selects the matching compatibility dataclass and status keyword
        schema_version="1", phase="implement", step="8",
        **values, **{kind.status_field: status},  # type: ignore[arg-type]  # reason: values dict is untyped; descriptor-driven constructor validates correctness
    )


_CONSUMABLE_BY_KIND = {
    GUIDELINES: architectural_guidelines.note_consumable,
    INVARIANTS: architectural_guidelines.invariant_note_consumable,
}
_DURABLE_PATH_BY_KIND = {
    GUIDELINES: architectural_guidelines.durable_note_path,
    INVARIANTS: architectural_guidelines.invariant_durable_note_path,
}
_METADATA_BY_KIND = {
    GUIDELINES: architectural_guidelines.durable_note_metadata,
    INVARIANTS: architectural_guidelines.invariant_durable_note_metadata,
}
_STALE_BY_KIND = {
    GUIDELINES: architectural_guidelines.note_fingerprint_stale,
    INVARIANTS: architectural_guidelines.invariant_note_fingerprint_stale,
}
_CLEAR_OUTCOME_BY_KIND = {
    GUIDELINES: architectural_guidelines.clear_guideline_ship_outcome,
    INVARIANTS: architectural_guidelines.clear_invariant_ship_outcome,
}
_OUTCOME_PATH_BY_KEY = {
    GUIDELINES.key: architectural_guidelines.guideline_ship_outcome_path,
    INVARIANTS.key: architectural_guidelines.invariant_ship_outcome_path,
}
_OUTCOME_VALIDATOR_BY_KEY = {
    GUIDELINES.key: architectural_guidelines.validate_guideline_ship_outcome_record,
    INVARIANTS.key: architectural_guidelines.validate_invariant_ship_outcome_record,
}


def _bounded_detail(text: str) -> str:
    clean = logging_util.sanitize_diagnostic_line(redact.redact_outbound(text or ""))
    return clean[:500]


def read_unavailable_outcome_detail(
    *, implement_tmpdir: str, kind: str, head_sha: str, base_ref: str
) -> str:
    """Read diagnostic detail from a current, valid unavailable outcome."""
    path_fn = _OUTCOME_PATH_BY_KEY.get(kind)
    validator = _OUTCOME_VALIDATOR_BY_KEY.get(kind)
    if path_fn is None or validator is None:
        return ""
    path = path_fn(Path(implement_tmpdir))
    try:
        mode: int = path.lstat().st_mode
        if path.is_symlink() or not stat.S_ISREG(mode):
            return ""
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ""
    if validator(decoded) is not None or not isinstance(decoded, dict):
        return ""
    record: dict[str, object] = decoded  # type: ignore[assignment]  # reason: isinstance narrowed the JSON object
    detail = record.get("detail", "")
    if (
        record.get("reason") != REASON_UNAVAILABLE
        or record.get("head_sha") != head_sha
        or record.get("base_ref") != base_ref
        or not isinstance(detail, str)
    ):
        return ""
    return _bounded_detail(detail)


def mark_operator_waived_outcomes(
    *, implement_tmpdir: str, kinds: frozenset[str]
) -> frozenset[str]:
    """Mark existing unavailable outcome sidecars for the waived kinds."""
    if not implement_tmpdir or not kinds:
        return frozenset()
    tmpdir = Path(implement_tmpdir)
    marked: set[str] = set()
    for kind in kinds:
        path_fn = _OUTCOME_PATH_BY_KEY.get(kind)
        validator = _OUTCOME_VALIDATOR_BY_KEY.get(kind)
        if path_fn is None or validator is None:
            continue
        path = path_fn(tmpdir)
        try:
            if not larch_io.trusted_file_present(path, root=tmpdir):
                continue
            raw = json.loads(
                larch_io.read_trusted_text(path, root=tmpdir, reject_cr=True)
            )
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        data = cast("dict[str, object]", raw)
        if validator(data) is not None:
            continue
        if (
            data.get("outcome") != OUTCOME_DROPPED
            or data.get("reason") != REASON_UNAVAILABLE
        ):
            continue
        data["operator_waived"] = True
        try:
            larch_io.trusted_atomic_write(
                path,
                json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n",
                root=tmpdir,
            )
        except OSError:
            continue
        marked.add(kind)
    return frozenset(marked)


def _classify_assessment_ship_outcome(  # noqa: C901 - descriptor policies preserve each legacy outcome branch
    *,
    result: GateResult,
    head_sha: str,
    base_ref: str,
    kind: AssessmentKind,
) -> ShipOutcome:
    result_status = _status(result, kind=kind)
    status = result_status if result_status in {"present", "absent", "invalid"} else "absent"
    assessment_kind = result.assessment_kind
    reason = result.reason
    if result.note_state == config.NOTE_STATE_DETERMINISTIC_CLEAN:
        outcome = OUTCOME_CLEAN
        reason = REASON_DETERMINISTIC_CLEAN
        assessment_kind = "clean"
    elif result.note_state == config.NOTE_STATE_UNAVAILABLE:
        outcome = OUTCOME_DROPPED
        reason = REASON_UNAVAILABLE
        assessment_kind = ""
    elif status == "absent":
        outcome = OUTCOME_CLEAN
        reason = kind.absent_reason
        assessment_kind = ""
    elif status == "invalid":
        outcome = OUTCOME_CLEAN
        reason = kind.invalid_reason
        assessment_kind = ""
    elif kind.empty_reason and reason == kind.empty_reason:
        outcome = OUTCOME_CLEAN
        assessment_kind = config.ASSESSMENT_OUTCOME_CLEAN
    elif result.note and assessment_kind == "clean":
        outcome = OUTCOME_CLEAN
        reason = reason or REASON_CLEAN_NOTE
    elif result.note:
        outcome = kind.non_clean_ship_outcome
        reason = reason or kind.non_clean_note_reason
        if kind.is_invariant:
            assessment_kind = kind.non_clean_authored_outcome
    else:
        outcome = OUTCOME_DROPPED
        reason = reason or REASON_COMPOSE_MATERIALIZATION_FAILED
        if kind.is_invariant:
            assessment_kind = ""
    if reason not in kind.ship_reason_tokens:
        reason = REASON_UNKNOWN
    allowed_kinds = {config.ASSESSMENT_OUTCOME_CLEAN, kind.non_clean_authored_outcome}
    return _outcome(
        kind=kind,
        outcome=outcome,
        reason=reason,
        detail=_bounded_detail(result.detail),
        status=status,
        head_sha=_bounded_detail(head_sha),
        base_ref=_bounded_detail(base_ref),
        assessment_kind=assessment_kind if assessment_kind in allowed_kinds else "",
    )


def _clear_ship_outcome_sidecar(*, implement_tmpdir: str, kind: AssessmentKind) -> None:
    if implement_tmpdir:
        _CLEAR_OUTCOME_BY_KIND[kind](Path(implement_tmpdir))


clear_guideline_ship_outcome_sidecar = partial(_clear_ship_outcome_sidecar, kind=GUIDELINES)
clear_invariant_ship_outcome_sidecar = partial(_clear_ship_outcome_sidecar, kind=INVARIANTS)


def _write_ship_outcome(
    *,
    implement_tmpdir: str,
    result: GateResult,
    head_sha: str,
    base_ref: str,
    kind: AssessmentKind,
) -> ShipOutcome | None:
    if result.needs_assessment or not implement_tmpdir:
        return None
    if not head_sha.strip():
        message = f"architectural-{kind.key} outcome head_sha is empty"
        _log_guidelines_ship_warning(implement_tmpdir=Path(implement_tmpdir), message=message)
        raise OSError(message)
    outcome = _classify_assessment_ship_outcome(
        result=result, head_sha=head_sha, base_ref=base_ref, kind=kind
    )
    tmpdir = Path(implement_tmpdir)
    larch_io.trusted_atomic_write(
        tmpdir / kind.ship_outcome_sidecar,
        json.dumps(outcome.as_json(), sort_keys=True, separators=(",", ":")) + "\n",
        root=tmpdir,
    )
    return outcome


def _exported_ship_writer(
    kind: AssessmentKind, outcome_type: type[ShipOutcome]
) -> Callable[..., ShipOutcome | None]:
    def write(
        *, implement_tmpdir: str, result: GateResult, head_sha: str, base_ref: str
    ) -> ShipOutcome | None:
        outcome = _write_ship_outcome(
            implement_tmpdir=implement_tmpdir,
            result=result,
            head_sha=head_sha,
            base_ref=base_ref,
            kind=kind,
        )
        if outcome is None:
            return None
        assert isinstance(outcome, outcome_type)
        return outcome

    return write


write_guideline_ship_outcome = _exported_ship_writer(GUIDELINES, GuidelinesShipOutcome)
write_invariant_ship_outcome = _exported_ship_writer(INVARIANTS, InvariantsShipOutcome)


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


def _read_current_note(
    *, tmpdir: Path, head_sha: str, kind: AssessmentKind,
    base_ref: str = "", repo_root: str | None = None,
) -> GateResult:
    if not _CONSUMABLE_BY_KIND[kind](
        implement_tmpdir=tmpdir, head_sha=head_sha, base_ref=base_ref, repo_root=repo_root
    ):
        return _gate(kind=kind)
    note_path = _DURABLE_PATH_BY_KIND[kind](tmpdir)
    try:
        note = note_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        message = f"architectural-{kind.key} note read failed: {exc}"
        return _gate(
            kind=kind,
            warning_logged=_log_guidelines_ship_warning(
                implement_tmpdir=tmpdir, message=message
            ),
            detail=message, status="present", reason=REASON_NOTE_READ_FAILED,
        )
    try:
        redacted_note = pr_body.redact_pr_body(note).strip()
        metadata = _METADATA_BY_KIND[kind](tmpdir)
        note_state = metadata.get("NOTE_STATE", "") or config.NOTE_STATE_AUTHORED
        assessment_kind = metadata.get("ASSESSMENT_KIND", "")
        if note_state == config.NOTE_STATE_AUTHORED and not architectural_guidelines.authored_outcome_valid(
            note=redacted_note, outcome=assessment_kind, invariant=kind.is_invariant
        ):
            return _gate(
                kind=kind,
                needs_assessment=True,
                detail=config.ASSESSMENT_REAUTHOR_REASON_MISSING_METADATA,
                status=metadata.get(kind.status_env_key, "present") or "present",
                reason=config.ASSESSMENT_RESULT_REAUTHOR_REQUIRED,
            )
        reason = ""
        if note_state == config.NOTE_STATE_DETERMINISTIC_CLEAN:
            reason = REASON_DETERMINISTIC_CLEAN
        elif note_state == config.NOTE_STATE_UNAVAILABLE:
            reason = REASON_UNAVAILABLE
        return _gate(
            kind=kind,
            note=redacted_note,
            status=metadata.get(kind.status_env_key, "present") or "present",
            assessment_kind=assessment_kind, note_state=note_state, reason=reason,
        )
    except ShipError as exc:
        message = f"architectural-{kind.key} note redaction failed: {exc}"
        return _gate(
            kind=kind,
            warning_logged=_log_guidelines_ship_warning(
                implement_tmpdir=tmpdir, message=message
            ),
            detail=message, status="present", reason=REASON_NOTE_REDACTION_FAILED,
        )


def _current_note_result(
    *, current: GateResult, tmpdir: Path, base_ref: str,
    repo_root: str | None, kind: AssessmentKind,
) -> GateResult | None:
    if current.note:
        stale = _STALE_BY_KIND[kind]
        if repo_root is not None and base_ref and stale(
            tmpdir, base_ref=base_ref, repo_root=repo_root
        ):
            return None
        return current
    if current.needs_assessment or current.reason:
        return current
    return None


def _warning_for_prepared(
    *, tmpdir: Path, warning: str, kind: AssessmentKind = GUIDELINES
) -> bool:
    if not warning:
        return False
    return _log_guidelines_ship_warning(
        implement_tmpdir=tmpdir,
        message=f"architectural-{kind.key} compose materialization skipped: {warning}",
    )


def _prepared_result(  # noqa: PLR0913 - prepared evidence carries the complete note identity
    *, prepared: architectural_guidelines.ComposeMaterializationResult,
    tmpdir: Path, head_sha: str, base_ref: str, repo_root: str | None,
    kind: AssessmentKind,
) -> GateResult:
    if prepared.status == "current":
        return _read_current_note(
            tmpdir=tmpdir, head_sha=head_sha, base_ref=base_ref,
            repo_root=repo_root, kind=kind,
        )
    if prepared.status == "assessment-required":
        return _gate(
            kind=kind,
            needs_assessment=True,
            detail=f"architectural-{kind.key} assessment required before PR body compose",
            status=prepared.guidelines_status,
        )
    if prepared.status == "present-empty" and kind.ship_present_empty:
        return _gate(
            kind=kind,
            status=prepared.guidelines_status or "present",
            assessment_kind=config.ASSESSMENT_OUTCOME_CLEAN,
            reason=kind.empty_reason,
        )
    if prepared.status in {"absent", "invalid"}:
        return _gate(
            kind=kind,
            warning_logged=_warning_for_prepared(
                tmpdir=tmpdir, warning=prepared.warning, kind=kind
            ),
            detail=prepared.warning,
            status=prepared.guidelines_status or prepared.status,
            reason=kind.invalid_reason if prepared.status == "invalid" else kind.absent_reason,
        )
    return _gate(
        kind=kind,
        warning_logged=_warning_for_prepared(
            tmpdir=tmpdir, warning=prepared.warning, kind=kind
        ),
        detail=prepared.warning,
        status=prepared.guidelines_status or "present",
        reason=REASON_COMPOSE_MATERIALIZATION_FAILED,
    )


def _load_or_prepare_note(  # noqa: PLR0913 - snapshot factory is the compose-time seam
    *, implement_tmpdir: str, head_sha: str, base_ref: str, kind: AssessmentKind,
    repo_root: str | None = None, forked_target: bool = False,
    compose_snapshot_factory: Callable[[], architectural_guidelines.ComposeAssessmentSnapshot] | None = None,
) -> GateResult:
    if not implement_tmpdir or not head_sha:
        return _gate(kind=kind)
    tmpdir = Path(implement_tmpdir)
    current = _current_note_result(
        current=_read_current_note(
            tmpdir=tmpdir, head_sha=head_sha, base_ref=base_ref,
            repo_root=repo_root, kind=kind,
        ),
        tmpdir=tmpdir, base_ref=base_ref, repo_root=repo_root, kind=kind,
    )
    if current is not None:
        return current
    prepare = (
        architectural_guidelines.prepare_invariant_compose_assessment
        if kind.is_invariant
        else architectural_guidelines.prepare_compose_assessment
    )
    prepared = prepare(
        implement_tmpdir=tmpdir, repo_root=repo_root, forked_target=forked_target,
        expected_head_sha=head_sha, compose_snapshot_factory=compose_snapshot_factory,
    )
    return _prepared_result(
        prepared=prepared, tmpdir=tmpdir, head_sha=head_sha, base_ref=base_ref,
        repo_root=repo_root, kind=kind,
    )


def _load_or_prepare_typed(
    kind: AssessmentKind, result_type: type[GateResult]
) -> Callable[..., GateResult]:
    def loader(  # noqa: PLR0913 - compatibility API
        *, implement_tmpdir: str, head_sha: str, base_ref: str, repo_root: str | None = None,
        forked_target: bool = False,
        compose_snapshot_factory: Callable[[], architectural_guidelines.ComposeAssessmentSnapshot] | None = None,
    ) -> GateResult:
        result = _load_or_prepare_note(
            implement_tmpdir=implement_tmpdir, head_sha=head_sha, base_ref=base_ref,
            repo_root=repo_root, forked_target=forked_target,
            compose_snapshot_factory=compose_snapshot_factory, kind=kind,
        )
        assert isinstance(result, result_type)
        return result

    return loader


load_or_prepare_guidelines_note = _load_or_prepare_typed(GUIDELINES, GuidelinesGateResult)
load_or_prepare_invariants_note = _load_or_prepare_typed(INVARIANTS, InvariantsGateResult)


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
