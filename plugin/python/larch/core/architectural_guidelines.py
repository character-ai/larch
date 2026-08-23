"""Architectural knowledge reads and retained design assessment helpers."""
# pyright: reportUnusedCallResult=false, reportPrivateUsage=false
# pylint: disable=cyclic-import  # accepted: function-level run-log batch imports create mutual dependencies with top-level consumers; documented via lint-layering ok comments.

from __future__ import annotations

import hashlib
import logging
import os
import re
import shutil
import stat
import subprocess
import sys
from contextlib import suppress
from datetime import UTC, datetime
from functools import partial
from pathlib import Path, PurePosixPath
from typing import cast

from larch.core import config
from larch.core.assessment_kind import AssessmentKind, GUIDELINES, INVARIANTS

_LOG = logging.getLogger(__name__)

GUIDELINES_FILENAME = GUIDELINES.filename
INVARIANTS_FILENAME = INVARIANTS.filename
CLEAN_PRESENTATION_NOTE = GUIDELINES.clean_presentation_note
CLEAN_INVARIANT_PRESENTATION_NOTE = INVARIANTS.clean_presentation_note
GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED = GUIDELINES.assessment_required_line
INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED = INVARIANTS.assessment_required_line
DESIGN_ASSESSMENT = GUIDELINES.design_assessment
INVARIANT_DESIGN_ASSESSMENT = INVARIANTS.design_assessment
STAGED_ASSESSMENT = GUIDELINES.staged_assessment
INVARIANT_STAGED_ASSESSMENT = INVARIANTS.staged_assessment
STAGED_ASSESSMENT_ENV = GUIDELINES.staged_assessment_env
INVARIANT_STAGED_ASSESSMENT_ENV = INVARIANTS.staged_assessment_env
MATERIALIZED_DIFF = GUIDELINES.materialized_diff
INVARIANT_MATERIALIZED_DIFF = INVARIANTS.materialized_diff
DURABLE_NOTE = GUIDELINES.durable_note
INVARIANT_DURABLE_NOTE = INVARIANTS.durable_note
DURABLE_NOTE_ENV = GUIDELINES.durable_note_env
INVARIANT_DURABLE_NOTE_ENV = INVARIANTS.durable_note_env
DROPPED_NOTE_ARTIFACT = GUIDELINES.dropped_note_artifact
INVARIANT_DROPPED_NOTE_ARTIFACT = INVARIANTS.dropped_note_artifact
GUIDELINE_SHIP_OUTCOME_SIDECAR = GUIDELINES.ship_outcome_sidecar
INVARIANT_SHIP_OUTCOME_SIDECAR = INVARIANTS.ship_outcome_sidecar
MATERIALIZE_ENV = GUIDELINES.materialize_env
INVARIANT_MATERIALIZE_ENV = INVARIANTS.materialize_env
_STATUS_VALUES = {"present", "absent", "invalid"}
GUIDELINE_HEADING_RE: re.Pattern[str] = GUIDELINES.heading_re
INVARIANT_HEADING_RE: re.Pattern[str] = INVARIANTS.heading_re
# Loose id matchers for assessment-note classification: any I-*/G-* entry referenced
# anywhere in a note's prose, not just as a Markdown heading. See issue #6882.
NOTE_INVARIANT_ID_RE = INVARIANTS.identifier_re
NOTE_GUIDELINE_ID_RE = GUIDELINES.identifier_re
# A note whose first sentence affirms "no violations/deviations" leads clean, so a
# supporting I-*/G-* reference in that same sentence must not flip it to non-clean.
# See issue #6955.
_CLEAN_ASSESSMENT_LEAD_RE = re.compile(r"^\W*no\b[^.;\n]*\b(?:violation|deviation)s?\b", re.IGNORECASE)


def _validate_ship_outcome_record(  # noqa: C901, PLR0911, PLR0912 - validator preserves distinct schema diagnostics
    data: object, *, kind: AssessmentKind
) -> str | None:
    label = kind.singular
    if not isinstance(data, dict):
        return f"{label} outcome artifact must be a JSON object"
    d = cast("dict[str, object]", data)
    if str(d.get("schema_version") or "") != "1":
        return f"{label} outcome schema_version must be 1"
    phase = str(d.get("phase") or "")
    step = str(d.get("step") or "")
    base_ref = str(d.get("base_ref") or "")
    head_sha = str(d.get("head_sha") or "")
    outcome = str(d.get("outcome") or "")
    reason = str(d.get("reason") or "")
    status = str(d.get(kind.status_field) or "")
    assessment_kind = str(d.get("assessment_kind") or "")
    operator_waived = d.get("operator_waived", False)
    if not isinstance(operator_waived, bool):
        return f"{label} outcome operator_waived must be boolean"
    if operator_waived and (outcome != "dropped" or reason != config.REASON_UNAVAILABLE):
        return f"{label} outcome operator_waived requires unavailable dropped outcome"
    if phase != "implement":
        return f"{label} outcome phase must be implement"
    if step != "8":
        return f"{label} outcome step must be 8"
    if not base_ref:
        return f"{label} outcome base_ref is empty"
    if not head_sha.strip():
        return f"{label} outcome head_sha is empty"
    if outcome not in kind.ship_outcomes:
        return f"{label} outcome token is unknown"
    if status not in _STATUS_VALUES:
        return f"{label} outcome {kind.status_field} is unknown"
    if reason not in kind.ship_reason_tokens:
        return f"{label} outcome reason token is unknown"
    allowed_assessment_kinds = {"", config.ASSESSMENT_OUTCOME_CLEAN, kind.non_clean_authored_outcome}
    if assessment_kind not in allowed_assessment_kinds:
        return f"{label} outcome assessment_kind is unknown"
    if status in {"absent", "invalid"}:
        expected_reason = kind.absent_reason if status == "absent" else kind.invalid_reason
        if outcome != "clean" or reason != expected_reason or assessment_kind:
            return f"{label} outcome fields are inconsistent for {status} {kind.key}"
        return None
    if outcome == "clean":
        clean_reasons = {"clean-note", config.REASON_DETERMINISTIC_CLEAN}
        if kind.empty_reason:
            clean_reasons.add(kind.empty_reason)
        if reason not in clean_reasons or assessment_kind != "clean":
            return f"{label} outcome fields are inconsistent for clean {kind.key}"
        return None
    if outcome == kind.non_clean_ship_outcome:
        if reason != kind.non_clean_note_reason or assessment_kind != kind.non_clean_authored_outcome:
            if kind.is_invariant:
                return "invariant outcome fields are inconsistent for invariant violations"
            return "guideline outcome fields are inconsistent for pinned guidelines"
        return None
    if outcome == "dropped":
        dropped_reasons = {
            "note-read-failed",
            "note-redaction-failed",
            "compose-materialization-failed",
            config.REASON_UNAVAILABLE,
            "unknown",
        }
        if assessment_kind or (not kind.is_invariant and status != "present") or reason not in dropped_reasons:
            return f"{label} outcome fields are inconsistent for dropped {kind.key}"
        return None
    return f"{label} outcome fields are inconsistent"


validate_guideline_ship_outcome_record = partial(_validate_ship_outcome_record, kind=GUIDELINES)
validate_invariant_ship_outcome_record = partial(_validate_ship_outcome_record, kind=INVARIANTS)


def _materialize_implementation_diff_for_head(
    repo_root: Path,
    *,
    head_sha: str,
    base_remote: str,
    base_ref: str,
) -> str:
    """Return a merge-base..HEAD diff for the already-resolved head."""
    target = f"{base_remote}/{base_ref}"
    merge_base = subprocess.run(
        ["git", "merge-base", head_sha, target],  # noqa: S607
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if merge_base.returncode != 0 or not merge_base.stdout.strip():
        msg = (merge_base.stderr or merge_base.stdout or f"could not resolve merge base for {target}").strip()
        raise RuntimeError(msg)
    base_sha = merge_base.stdout.strip()
    diff = subprocess.run(
        ["git", "diff", f"{base_sha}..{head_sha}", "--", ".", ":(exclude)larch-logs/**"],  # noqa: S607
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if diff.returncode != 0:
        msg = (diff.stderr or diff.stdout or "git diff failed").strip()
        raise RuntimeError(msg)
    return diff.stdout


def materialize_implementation_diff(repo_root: Path, *, base_remote: str, base_ref: str) -> str:
    """Return a merge-base..HEAD diff for orchestrator assessment."""
    head_errors: list[str] = []
    head_sha = _current_head(repo_root, verify_commit=True, error_out=head_errors)
    if not head_sha:
        msg = head_errors[0] if head_errors else "could not resolve HEAD"
        raise RuntimeError(msg)
    return _materialize_implementation_diff_for_head(
        repo_root,
        head_sha=head_sha,
        base_remote=base_remote,
        base_ref=base_ref,
    )


def diff_fingerprint(diff_text: str) -> str:
    return hashlib.sha256(diff_text.encode("utf-8", errors="surrogateescape")).hexdigest()


def _artifact_path(root: Path, kind: AssessmentKind, attribute: str) -> Path:
    return root / cast("str", getattr(kind, attribute))


staged_assessment_path = partial(_artifact_path, kind=GUIDELINES, attribute="staged_assessment")
invariant_staged_assessment_path = partial(_artifact_path, kind=INVARIANTS, attribute="staged_assessment")
durable_note_path = partial(_artifact_path, kind=GUIDELINES, attribute="durable_note")
invariant_durable_note_path = partial(_artifact_path, kind=INVARIANTS, attribute="durable_note")
design_assessment_path = partial(_artifact_path, kind=GUIDELINES, attribute="design_assessment")
invariant_design_assessment_path = partial(_artifact_path, kind=INVARIANTS, attribute="design_assessment")
dropped_note_path = partial(_artifact_path, kind=GUIDELINES, attribute="dropped_note_artifact")
invariant_dropped_note_path = partial(_artifact_path, kind=INVARIANTS, attribute="dropped_note_artifact")
guideline_ship_outcome_path = partial(_artifact_path, kind=GUIDELINES, attribute="ship_outcome_sidecar")
invariant_ship_outcome_path = partial(_artifact_path, kind=INVARIANTS, attribute="ship_outcome_sidecar")


def _env_escape(value: str) -> str:
    return value.replace("\n", " ").replace("\r", " ")


def _write_text_atomic(*, path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _read_regular_text_no_follow(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise OSError("assessment file must be a regular non-symlink file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise OSError("assessment file must be a regular file")
        with os.fdopen(fd, "r", encoding="utf-8") as handle:
            fd = -1
            return handle.read()
    finally:
        if fd >= 0:
            os.close(fd)


def _read_env(path: Path) -> dict[str, str]:
    if not path.is_file() or path.is_symlink():
        return {}
    try:
        raw_text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError, AssessmentReauthorRequired):
        return {}
    values: dict[str, str] = {}
    for line in raw_text.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            values[key] = value
    return values


def _regular_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _durable_note_present(implement_tmpdir: Path, *, kind: AssessmentKind) -> bool:
    note = _artifact_path(implement_tmpdir, kind, "durable_note")
    meta = _artifact_path(implement_tmpdir, kind, "durable_note_env")
    if not _regular_file(note) or not _regular_file(meta):
        return False
    return _read_env(meta).get("STATUS") == "present"


durable_note_present = partial(_durable_note_present, kind=GUIDELINES)
invariant_durable_note_present = partial(_durable_note_present, kind=INVARIANTS)
note_readable_any_head = durable_note_present
invariant_note_readable_any_head = invariant_durable_note_present


def _note_identity(metadata: dict[str, str]) -> tuple[str, str, str] | None:
    legacy_fingerprint = metadata.get("DIFF_FINGERPRINT", "").strip()
    new_format = any(key in metadata for key in ("NOTE_STATE", "AUTHORED_DIFF_FINGERPRINT", "COVERED_DIFF_FINGERPRINT"))
    note_state = metadata.get("NOTE_STATE", "").strip() or ("" if new_format else config.NOTE_STATE_AUTHORED)
    if note_state not in config.NOTE_STATE_TOKENS:
        return None
    authored_fingerprint = metadata.get("AUTHORED_DIFF_FINGERPRINT", "").strip()
    covered_fingerprint = metadata.get("COVERED_DIFF_FINGERPRINT", "").strip()
    if not new_format:
        authored_fingerprint = legacy_fingerprint
        covered_fingerprint = legacy_fingerprint
    if note_state == config.NOTE_STATE_UNAVAILABLE:
        return note_state, authored_fingerprint, covered_fingerprint
    if not authored_fingerprint or not covered_fingerprint:
        return None
    return note_state, authored_fingerprint, covered_fingerprint


def _durable_metadata_text(
    *,
    head_sha: str,
    metadata: dict[str, str],
    base_ref: str,
    status_key: str,
    status_default: str,
) -> str:
    new_format = any(
        metadata.get(key)
        for key in ("NOTE_STATE", "AUTHORED_DIFF_FINGERPRINT", "COVERED_DIFF_FINGERPRINT")
    )
    identity = _note_identity(metadata)
    note_state = identity[0] if identity is not None else metadata.get("NOTE_STATE", config.NOTE_STATE_AUTHORED)
    authored_fingerprint = identity[1] if identity is not None else metadata.get("AUTHORED_DIFF_FINGERPRINT", "")
    covered_fingerprint = identity[2] if identity is not None else metadata.get("COVERED_DIFF_FINGERPRINT", "")
    compatibility_fingerprint = covered_fingerprint or metadata.get("DIFF_FINGERPRINT", "")
    lines = ["STATUS=present"]
    if new_format:
        lines.extend(
            [
                f"NOTE_STATE={_env_escape(note_state)}",
                f"AUTHORED_DIFF_FINGERPRINT={_env_escape(authored_fingerprint)}",
                f"COVERED_DIFF_FINGERPRINT={_env_escape(covered_fingerprint)}",
            ]
        )
    lines.extend(
        [
            f"HEAD_SHA={_env_escape(head_sha)}",
            f"ASSESSED_HEAD_SHA={_env_escape(metadata.get('ASSESSED_HEAD_SHA', ''))}",
            f"DIFF_FINGERPRINT={_env_escape(compatibility_fingerprint)}",
            f"BASE_REF={_env_escape(base_ref or metadata.get('BASE_REF', ''))}",
            f"DIFF_SNAPSHOT={_env_escape(metadata.get('DIFF_SNAPSHOT', ''))}",
            f"{status_key}={_env_escape(metadata.get(status_key, status_default))}",
            f"ASSESSMENT_KIND={_env_escape(metadata.get('ASSESSMENT_KIND', ''))}",
            f"WRITTEN_AT={datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')}",
            "",
        ]
    )
    return "\n".join(lines)


def _materialize_live_diff(*, repo_root: Path | None, resolved_base: str) -> tuple[str, str] | None:
    """Materialize the live implementation diff and return diff text plus fingerprint."""
    if repo_root is None or not resolved_base:
        return None
    remote, ref = resolved_base.split("/", 1) if "/" in resolved_base else ("origin", resolved_base)
    try:
        diff_text = materialize_implementation_diff(repo_root, base_remote=remote, base_ref=ref)
    except (OSError, RuntimeError) as exc:
        print(f"ARCHITECTURAL_GUIDELINES_WARNING={str(exc).replace(chr(10), ' ')}", file=sys.stderr)
        return None
    return diff_text, diff_fingerprint(diff_text)


def _live_fingerprint(*, repo_root: Path | None, resolved_base: str) -> str | None:
    """Materialize the live implementation diff and return its fingerprint, or None when it cannot be computed."""
    live_diff = _materialize_live_diff(repo_root=repo_root, resolved_base=resolved_base)
    if live_diff is None:
        return None
    return live_diff[1]


def _artifact_still_present(path: Path) -> bool:
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False


def _durable_note_metadata(implement_tmpdir: Path, *, kind: AssessmentKind) -> dict[str, str]:
    """Return durable-note sidecar metadata when present."""
    return _read_env(_artifact_path(implement_tmpdir, kind, "durable_note_env"))


durable_note_metadata = partial(_durable_note_metadata, kind=GUIDELINES)
invariant_durable_note_metadata = partial(_durable_note_metadata, kind=INVARIANTS)


def _path_out_of_scope(path: str) -> bool:
    """Return true only for normalized paths outside architectural scope."""
    if not path or path.startswith("/") or "\\" in path or "//" in path:
        return False
    candidate = PurePosixPath(path)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        return False
    normalized = candidate.as_posix()
    if normalized != path:
        return False
    if len(candidate.parts) >= 2 and candidate.parts[0] == "larch-logs":  # noqa: PLR2004 - minimum path depth: top-level dir + filename
        return True
    return len(candidate.parts) >= 2 and candidate.parts[0] == "docs" and candidate.suffix == ".md"  # noqa: PLR2004 - minimum path depth: top-level dir + filename


def _valid_commit(*, repo_root: Path, revision: str) -> bool:
    if not revision or revision.startswith("-") or any(char.isspace() for char in revision):
        return False
    try:
        completed = subprocess.run(  # lint-subprocess-via-runner: ok read-only git revision validation mirrors sibling git helpers in this module
            ["git", "rev-parse", "--verify", f"{revision}^{{commit}}"],  # noqa: S607
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    return completed.returncode == 0 and bool(completed.stdout.strip())


def _incremental_paths_out_of_scope(*, repo_root: Path, old_head: str, new_head: str) -> bool:
    if not _valid_commit(repo_root=repo_root, revision=old_head) or not _valid_commit(repo_root=repo_root, revision=new_head):
        return False
    try:
        completed = subprocess.run(  # lint-subprocess-via-runner: ok read-only NUL-delimited git path inspection mirrors sibling git helpers in this module
            ["git", "diff", "--no-renames", "--name-only", "-z", f"{old_head}..{new_head}", "--"],  # noqa: S607 - read-only git path inspection; revisions validated by _valid_commit before this call
            cwd=repo_root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    if completed.returncode != 0 or completed.stderr or not completed.stdout or not completed.stdout.endswith(b"\0"):
        return False
    raw_paths = completed.stdout[:-1].split(b"\0")
    if not raw_paths or any(not raw_path for raw_path in raw_paths):
        return False
    try:
        paths = [raw_path.decode("utf-8") for raw_path in raw_paths]
    except UnicodeDecodeError:
        return False
    return all(_path_out_of_scope(path) for path in paths)


def _snapshot_matches(*, snapshot_path: Path, covered_fingerprint: str) -> bool:
    if not covered_fingerprint or not _regular_file(snapshot_path):
        return False
    try:
        snapshot_text = _read_regular_text_no_follow(snapshot_path)
    except (OSError, UnicodeDecodeError):
        return False
    return diff_fingerprint(snapshot_text) == covered_fingerprint


def _same_resolved_path(left: str | Path, right: Path) -> bool:
    """Compare paths after resolving symlinks so /tmp and /private/tmp forms match."""
    try:
        return Path(left).resolve() == Path(right).resolve()
    except (OSError, RuntimeError):
        # RuntimeError: symlink loops on Python <3.13 (fail closed like sibling resolve sites).
        return False


def _reject_note_metadata(reason: str) -> None:
    _LOG.debug(f"architectural note metadata rejected: {reason}")


def _reject_coverage_advance(reason: str) -> bool:
    _LOG.debug(f"architectural coverage advance rejected: {reason}")
    return False


def _validated_note_metadata(  # noqa: PLR0911 - fail-closed metadata validator has distinct early exits per invariant check
    *,
    metadata: dict[str, str],
    expected_snapshot: Path,
) -> tuple[str, str, str, str] | None:
    if metadata.get("STATUS") != "present":
        _reject_note_metadata("STATUS is not present")
        return None
    identity = _note_identity(metadata)
    if identity is None:
        _reject_note_metadata("note identity missing or incomplete")
        return None
    note_state, authored_fingerprint, covered_fingerprint = identity
    base_ref = metadata.get("BASE_REF", "").strip()
    if note_state == config.NOTE_STATE_UNAVAILABLE:
        return note_state, authored_fingerprint, covered_fingerprint, base_ref
    declared_snapshot = metadata.get("DIFF_SNAPSHOT", "")
    prior_format = not metadata.get("NOTE_STATE") and not metadata.get("AUTHORED_DIFF_FINGERPRINT") and not metadata.get("COVERED_DIFF_FINGERPRINT")
    if prior_format:
        return note_state, authored_fingerprint, covered_fingerprint, base_ref
    if not declared_snapshot:
        _reject_note_metadata("DIFF_SNAPSHOT missing")
        return None
    # Resolve both sides: callers disagree on $IMPLEMENT_TMPDIR form (raw vs
    # resolve()), and on macOS /tmp and /private/tmp coexist for the same file.
    if not _same_resolved_path(declared_snapshot, expected_snapshot):
        _reject_note_metadata(
            f"DIFF_SNAPSHOT path mismatch declared={declared_snapshot!r} expected={expected_snapshot!r}"
        )
        return None
    if not _snapshot_matches(snapshot_path=expected_snapshot, covered_fingerprint=covered_fingerprint):
        _reject_note_metadata("snapshot fingerprint does not match COVERED_DIFF_FINGERPRINT")
        return None
    return note_state, authored_fingerprint, covered_fingerprint, base_ref


def _advance_note_coverage(  # noqa: C901, PLR0911, PLR0912, PLR0913, PLR0915 - fail-closed coverage advancement validates each independent safety boundary
    *,
    implement_tmpdir: Path,
    metadata: dict[str, str],
    head_sha: str,
    base_ref: str,
    repo_root: Path,
    kind: AssessmentKind,
) -> bool:
    stored_head = metadata.get("HEAD_SHA", "").strip()
    identity = _note_identity(metadata)
    if identity is None:
        return _reject_coverage_advance("note identity missing or incomplete")
    note_state, authored_fingerprint, covered_fingerprint = identity
    if note_state == config.NOTE_STATE_UNAVAILABLE:
        return _reject_coverage_advance("NOTE_STATE is unavailable")
    snapshot_path = _artifact_path(implement_tmpdir, kind, "materialized_diff")
    if not _valid_commit(repo_root=repo_root, revision=stored_head):
        return _reject_coverage_advance(f"stored HEAD_SHA is not a valid commit: {stored_head}")
    remote, ref = base_ref.split("/", 1) if "/" in base_ref else ("origin", base_ref)
    try:
        stored_diff = _materialize_implementation_diff_for_head(
            repo_root,
            head_sha=stored_head,
            base_remote=remote,
            base_ref=ref,
        )
    except (OSError, RuntimeError) as exc:
        return _reject_coverage_advance(f"could not materialize stored-head diff: {exc}")
    if diff_fingerprint(stored_diff) != covered_fingerprint or not _snapshot_matches(
        snapshot_path=snapshot_path,
        covered_fingerprint=covered_fingerprint,
    ):
        return _reject_coverage_advance("stored-head diff or snapshot fingerprint mismatch")
    if not _incremental_paths_out_of_scope(repo_root=repo_root, old_head=stored_head, new_head=head_sha):
        return _reject_coverage_advance("incremental paths include in-scope files")
    if _current_head(repo_root, verify_commit=True) != head_sha:
        return _reject_coverage_advance("HEAD drifted before live rematerialize")
    live_diff = _materialize_live_diff(repo_root=repo_root, resolved_base=base_ref)
    if live_diff is None or _current_head(repo_root, verify_commit=True) != head_sha:
        return _reject_coverage_advance("live rematerialize failed or HEAD drifted")
    diff_text, covered_fingerprint = live_diff
    refreshed = dict(metadata)
    refreshed["NOTE_STATE"] = note_state
    refreshed["AUTHORED_DIFF_FINGERPRINT"] = authored_fingerprint
    refreshed["COVERED_DIFF_FINGERPRINT"] = covered_fingerprint
    refreshed["DIFF_FINGERPRINT"] = covered_fingerprint
    refreshed["DIFF_SNAPSHOT"] = str(snapshot_path)
    meta_path = _artifact_path(implement_tmpdir, kind, "durable_note_env")
    status_key = kind.status_env_key
    snapshot_tmp = snapshot_path.with_name(snapshot_path.name + ".coverage.tmp")
    meta_tmp = meta_path.with_name(meta_path.name + ".coverage.tmp")
    try:
        previous_snapshot = _read_regular_text_no_follow(snapshot_path)
        previous_metadata = _read_regular_text_no_follow(meta_path)
        snapshot_tmp.write_text(diff_text, encoding="utf-8")
        meta_tmp.write_text(
            _durable_metadata_text(
                head_sha=head_sha,
                metadata=refreshed,
                base_ref=base_ref,
                status_key=status_key,
                status_default="present",
            ),
            encoding="utf-8",
        )
        if diff_fingerprint(snapshot_tmp.read_text(encoding="utf-8")) != covered_fingerprint:
            return _reject_coverage_advance("coverage tmp snapshot fingerprint mismatch")
        snapshot_tmp.replace(snapshot_path)
        try:
            meta_tmp.replace(meta_path)
        except OSError:
            restored = False
            try:
                if _read_regular_text_no_follow(snapshot_path) != previous_snapshot:
                    _write_text_atomic(path=snapshot_path, text=previous_snapshot)
                if _read_regular_text_no_follow(meta_path) != previous_metadata:
                    _write_text_atomic(path=meta_path, text=previous_metadata)
                restored = (
                    _read_regular_text_no_follow(snapshot_path) == previous_snapshot
                    and _read_regular_text_no_follow(meta_path) == previous_metadata
                )
            except (OSError, UnicodeDecodeError):
                restored = False
            if not restored:
                raise RuntimeError("could not restore architectural assessment coverage artifacts") from None
            return _reject_coverage_advance("metadata replace failed; prior artifacts restored")
    except (OSError, UnicodeDecodeError) as exc:
        return _reject_coverage_advance(f"coverage artifact write failed: {exc}")
    finally:
        with suppress(OSError):
            snapshot_tmp.unlink()
        with suppress(OSError):
            meta_tmp.unlink()
    return True


def _note_consumable(  # noqa: C901, PLR0911 - fail-closed consumption logic has distinct validation exits for each safety check
    *,
    implement_tmpdir: Path,
    head_sha: str,
    kind: AssessmentKind,
    base_ref: str = "",
    repo_root: str | Path | None = None,
) -> bool:
    note_path = _artifact_path(implement_tmpdir, kind, "durable_note")
    meta_path = _artifact_path(implement_tmpdir, kind, "durable_note_env")
    snapshot_path = _artifact_path(implement_tmpdir, kind, "materialized_diff")
    if not _regular_file(note_path) or not _regular_file(meta_path):
        return False
    metadata = _read_env(meta_path)
    validated = _validated_note_metadata(
        metadata=metadata,
        expected_snapshot=snapshot_path,
    )
    if validated is None:
        return False
    note_state, _authored_fingerprint, covered_fingerprint, stored_base = validated
    resolved_base = (base_ref or stored_base).strip()
    if not resolved_base or (base_ref and resolved_base != stored_base):
        return False
    if note_state == config.NOTE_STATE_UNAVAILABLE:
        return metadata.get("HEAD_SHA") == head_sha
    if repo_root is None:
        return metadata.get("HEAD_SHA") == head_sha
    try:
        root = Path(repo_root).resolve()
    except OSError:
        return False
    if metadata.get("HEAD_SHA") != head_sha:
        if not _advance_note_coverage(
            implement_tmpdir=implement_tmpdir,
            metadata=metadata,
            head_sha=head_sha,
            base_ref=resolved_base,
            repo_root=root,
            kind=kind,
        ):
            return False
        metadata = _read_env(meta_path)
        validated = _validated_note_metadata(
            metadata=metadata,
            expected_snapshot=snapshot_path,
        )
        if validated is None:
            return False
        covered_fingerprint = validated[2]
    if _current_head(root, verify_commit=True) != head_sha:
        return False
    live_fingerprint = _live_fingerprint(repo_root=root, resolved_base=resolved_base)
    return live_fingerprint is not None and live_fingerprint == covered_fingerprint


note_consumable = partial(_note_consumable, kind=GUIDELINES)
invariant_note_consumable = partial(_note_consumable, kind=INVARIANTS)


def _note_fingerprint_stale(
    implement_tmpdir: Path,
    *,
    base_ref: str,
    kind: AssessmentKind,
    repo_root: str | Path | None = None,
) -> bool:
    meta_path = _artifact_path(implement_tmpdir, kind, "durable_note_env")
    metadata = _read_env(meta_path)
    identity = _note_identity(metadata)
    if identity is None or not base_ref or repo_root is None:
        return True
    if identity[0] == config.NOTE_STATE_UNAVAILABLE:
        return False
    try:
        root = Path(repo_root).resolve()
    except OSError:
        return True
    live_fingerprint = _live_fingerprint(repo_root=root, resolved_base=base_ref)
    return live_fingerprint is None or live_fingerprint != identity[2]


note_fingerprint_stale = partial(_note_fingerprint_stale, kind=GUIDELINES)
invariant_note_fingerprint_stale = partial(_note_fingerprint_stale, kind=INVARIANTS)


def _clear_ship_outcome(implement_tmpdir: Path, *, kind: AssessmentKind) -> None:
    path = _artifact_path(implement_tmpdir, kind, "ship_outcome_sidecar")
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif _artifact_still_present(path):
            path.unlink()
    except OSError:
        pass


clear_guideline_ship_outcome = partial(_clear_ship_outcome, kind=GUIDELINES)
clear_invariant_ship_outcome = partial(_clear_ship_outcome, kind=INVARIANTS)


class AssessmentReauthorRequired(ValueError):
    """The authored assessment must be revised before it can be persisted."""


def classify_assessment_prose(
    note: str,
    *,
    clean_lead: str,
    identifier_pattern: re.Pattern[str],
    non_clean_outcome: str,
) -> str:
    """Classify prose for a one-way explicit-clean consistency check."""
    if not note.strip():
        return ""
    first_line: str = note.split("\n", 1)[0].strip()
    if first_line == clean_lead or _CLEAN_ASSESSMENT_LEAD_RE.search(first_line):
        return config.ASSESSMENT_OUTCOME_CLEAN
    return non_clean_outcome if identifier_pattern.search(note) else config.ASSESSMENT_OUTCOME_CLEAN


def _validate_authored_outcome(*, note: str, outcome: str, kind: AssessmentKind) -> str:
    if outcome not in kind.authored_outcomes:
        raise AssessmentReauthorRequired(config.ASSESSMENT_REAUTHOR_REASON_INVALID_OUTCOME)
    classified: str = classify_assessment_prose(
        note,
        clean_lead=kind.clean_presentation_note,
        identifier_pattern=kind.identifier_re,
        non_clean_outcome=kind.non_clean_authored_outcome,
    )
    if outcome == config.ASSESSMENT_OUTCOME_CLEAN and classified != config.ASSESSMENT_OUTCOME_CLEAN:
        raise AssessmentReauthorRequired(config.ASSESSMENT_REAUTHOR_REASON_CLEAN_MISMATCH)
    return outcome


def authored_outcome_valid(*, note: str, outcome: str, invariant: bool) -> bool:
    """Return whether authored outcome metadata is consistent with its note."""
    try:
        _validate_authored_outcome(
            note=note, outcome=outcome, kind=INVARIANTS if invariant else GUIDELINES
        )
    except AssessmentReauthorRequired:
        return False
    return True


def classify_note_for_kind(note: str, *, kind: AssessmentKind) -> str:
    """Classify prose for one assessment kind's explicit-clean consistency check."""
    return classify_assessment_prose(
        note,
        clean_lead=kind.clean_presentation_note,
        identifier_pattern=kind.identifier_re,
        non_clean_outcome=kind.non_clean_authored_outcome,
    )


def _current_head(repo_root: Path | None = None, *, verify_commit: bool = False, error_out: list[str] | None = None) -> str:
    cmd = ["git"]
    if repo_root is not None:
        cmd.extend(["-C", str(repo_root)])
    cmd.append("rev-parse")
    if verify_commit:
        cmd.extend(["--verify", "HEAD^{commit}"])
    else:
        cmd.append("HEAD")
    completed = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if completed.returncode != 0 and error_out is not None:
        error_out.append((completed.stderr or completed.stdout or "could not resolve HEAD").strip())
    return completed.stdout.strip() if completed.returncode == 0 else ""


# pyright: reportArgumentType=false
# lint-env-via-config-constant: IMPLEMENT_TMPDIR is read in CLI entry points.
# larch-lint: allow-subprocess-run
