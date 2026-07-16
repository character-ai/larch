"""ARCHITECTURAL_GUIDELINES.md reader and implement note helpers."""
# pyright: reportUnusedCallResult=false, reportPrivateUsage=false
# pylint: disable=cyclic-import  # accepted: function-level imports of ship_guidelines (validator needs outcome constants) and run_log_flush (chunker) create mutual deps with modules that import this module at top level; documented via lint-layering ok comments.

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import stat
import subprocess
import sys
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from pathlib import Path, PurePosixPath
from typing import cast

from larch import io as larch_io
from larch.core import config
from larch.core.assessment_kind import AssessmentKind, GUIDELINES, INVARIANTS, _MARKDOWN_HEADING_RE  # noqa: F401  # pylint: disable=unused-import  # pyright: ignore[reportUnusedImport]  # re-export: lint consumers import _MARKDOWN_HEADING_RE from this module
from larch.errors import ShipError
from larch.core.repo_roots import consumer_repo_root

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
LEGACY_WARNING = "architectural-guideline-warnings.md"
LEGACY_WARNING_ENV = "architectural-guideline-warnings.meta.env"
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
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_EXECUTION_WARNINGS_CATEGORY = "Warnings"
_APPEND_DEVIATION_OK = "ok"
_APPEND_DEVIATION_DUPLICATE = "duplicate"
_APPEND_DEVIATION_FAILED = "failed"


@dataclass(frozen=True)
class ArchitecturalGuidelinesResult:
    """Result of reading the repo-local architectural guidelines file."""

    status: str
    repo_root: Path | None
    path: Path | None
    content: str
    warning: str = ""

    def __post_init__(self) -> None:
        if self.status not in _STATUS_VALUES:
            msg = f"unsupported architectural guideline status: {self.status}"
            raise ValueError(msg)


@dataclass(frozen=True)
class ComposeMaterializationResult:
    """Result of the Step 8 compose-time guideline materialization gate."""

    status: str
    head_sha: str = ""
    base_ref: str = ""
    diff_fingerprint: str = ""
    diff_path: Path | None = None
    guidelines_status: str = ""
    guidelines_path: str = ""
    assessment_kind: str = ""
    warning: str = ""


@dataclass(frozen=True)
class ComposeAssessmentSnapshot:
    """Frozen Step 8 compose-time diff evidence shared across assessment kinds."""

    head_sha: str
    base_ref: str
    diff_text: str
    diff_fingerprint: str


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


def _run_git_toplevel(candidate: Path) -> Path | None:
    return consumer_repo_root(candidate)


def _resolve_repo_root(explicit_repo_root: str | Path | None = None) -> Path | None:
    if explicit_repo_root is not None:
        try:
            return Path(explicit_repo_root).resolve()
        except OSError:
            return None
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    if project_dir:
        root = _run_git_toplevel(Path(project_dir))
        if root is not None:
            return root
    return _run_git_toplevel(Path.cwd())


parse_guideline_entries = GUIDELINES.parse_entries
parse_invariant_entries = INVARIANTS.parse_entries


def _invalid(*, repo_root: Path | None, path: Path | None, warning: str) -> ArchitecturalGuidelinesResult:
    return ArchitecturalGuidelinesResult("invalid", repo_root, path, "", warning)


def _validate_architectural_file(*, root: Path, path: Path, filename: str) -> str | None:
    """Return an invalid-reason for a present architecture path, or None when readable."""
    if path.is_symlink():
        return f"{filename} is invalid: symlinks are not read"
    try:
        resolved = path.resolve(strict=False)
        _ = resolved.relative_to(root.resolve())
    except (OSError, ValueError):
        return f"{filename} is invalid: path escapes repo root"
    if path.is_dir():
        return f"{filename} is invalid: expected a regular file, found a directory"
    if not path.is_file():
        return f"{filename} is invalid: expected a regular file"
    return None


def _read_assessment_kind(
    *, kind: AssessmentKind, repo_root: str | Path | None = None
) -> ArchitecturalGuidelinesResult:
    root = _resolve_repo_root(repo_root)
    if root is None:
        return ArchitecturalGuidelinesResult("absent", None, None, "")
    path = root / kind.filename
    if not path.exists() and not path.is_symlink():
        return ArchitecturalGuidelinesResult("absent", root, path, "")
    warning = _validate_architectural_file(root=root, path=path, filename=kind.filename)
    if warning is not None:
        return _invalid(repo_root=root, path=path, warning=warning)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _invalid(repo_root=root, path=path, warning=f"{kind.filename} is invalid: unreadable file ({exc})")
    return ArchitecturalGuidelinesResult(
        "present", root, path.resolve(strict=False), kind.parse_entries(raw_text), ""
    )


read_guidelines = partial(_read_assessment_kind, kind=GUIDELINES)
read_invariants = partial(_read_assessment_kind, kind=INVARIANTS)


def architectural_knowledge_required(repo_root: str | Path | None = None) -> bool:
    """Return true when any valid architectural knowledge file is present."""
    return read_invariants(repo_root=repo_root).status == "present" or read_guidelines(repo_root=repo_root).status == "present"


def resolve_diff_base(*, forked_target: bool) -> tuple[str, str]:
    """Return the remote and ref used for implementation diff materialization."""
    return ("upstream", "main") if forked_target else ("origin", "main")


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


def materialize_compose_assessment_snapshot(
    *,
    repo_root: str | Path | None,
    forked_target: bool,
    expected_head_sha: str,
) -> ComposeAssessmentSnapshot:
    """Materialize one frozen diff snapshot for compose-time assessments."""
    root = _resolve_repo_root(repo_root)
    if root is None:
        raise RuntimeError("could not resolve repo root")
    head_errors: list[str] = []
    head_sha = _current_head(root, verify_commit=True, error_out=head_errors)
    if not head_sha:
        msg = head_errors[0] if head_errors else "could not resolve HEAD"
        raise RuntimeError(msg)
    if expected_head_sha and expected_head_sha != head_sha:
        raise RuntimeError("HEAD changed before architectural compose materialization")
    base_remote, base_ref = resolve_diff_base(forked_target=forked_target)
    diff_text = _materialize_implementation_diff_for_head(
        root,
        head_sha=head_sha,
        base_remote=base_remote,
        base_ref=base_ref,
    )
    return ComposeAssessmentSnapshot(
        head_sha=head_sha,
        base_ref=f"{base_remote}/{base_ref}",
        diff_text=diff_text,
        diff_fingerprint=diff_fingerprint(diff_text),
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


def _validate_design_tmpdir_arg(candidate: str) -> Path:
    from larch.state import session_env  # noqa: PLC0415  # lint-layering: ok validate-design-tmpdir must stay co-located with arg-parsing logic.
    ok, message = session_env.validate_design_tmpdir(candidate)
    if not ok:
        raise ValueError(message)
    if Path(candidate).is_symlink():
        raise ValueError("design-tmpdir: path must not be a symlink")
    return Path(candidate).resolve(strict=False)


def _env_escape(value: str) -> str:
    return value.replace("\n", " ").replace("\r", " ")


def _write_text_atomic(*, path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _safe_unlink_assessment(path: Path) -> None:
    if path.is_file() and not path.is_symlink():
        path.unlink()


def _write_kind_design_assessment_atomic(
    *, design_tmpdir: Path, text: str, kind: AssessmentKind
) -> None:
    design_tmpdir.mkdir(parents=True, exist_ok=True)
    path = _artifact_path(design_tmpdir, kind, "design_assessment")
    tmp = path.with_name(path.name + ".tmp")
    if path.is_symlink():
        raise OSError(f"{kind.design_assessment}: target must not be a symlink")
    if path.exists() and not path.is_file():
        raise OSError(f"{kind.design_assessment}: target must be a regular file")
    if tmp.is_symlink():
        raise OSError(f"{tmp.name}: temp path must not be a symlink")
    if tmp.exists() and not tmp.is_file():
        raise OSError(f"{tmp.name}: temp path must be a regular file")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _normalize_assessment_text(text: str) -> str:
    return text.rstrip("\n") + "\n"


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


def staged_assessment_present(implement_tmpdir: Path) -> bool:
    staged = staged_assessment_path(implement_tmpdir)
    sidecar = _artifact_path(implement_tmpdir, GUIDELINES, "staged_assessment_env")
    if not _regular_file(staged) or not _regular_file(sidecar):
        return False
    return _read_env(sidecar).get("STATUS") == "present"


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


def dropped_note_message() -> str:
    """Return legacy drop-note text.

    Compose-time assessment no longer surfaces a fallback notice when HEAD
    changes. Keep the function for temporary legacy callers, but make it inert.
    """
    return ""


def persist_dropped_note_notice(implement_tmpdir: Path, *, notice_text: str) -> bool:
    path = dropped_note_path(implement_tmpdir)
    try:
        if path.is_symlink():
            return False
        if path.exists() and not path.is_file():
            return False
        if path.is_file() and path.read_text(encoding="utf-8", errors="replace").strip():
            return False
        if path.with_name(path.name + ".tmp").is_symlink():
            return False
        _write_text_atomic(path=path, text=notice_text.strip() + "\n")
    except OSError:
        return False
    return True


def read_dropped_note_notice(implement_tmpdir: Path) -> str:
    path = dropped_note_path(implement_tmpdir)
    if not _regular_file(path):
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
    return text


def clear_dropped_note_notice(implement_tmpdir: Path) -> None:
    path = dropped_note_path(implement_tmpdir)
    try:
        if _regular_file(path):
            path.unlink()
    except OSError:
        pass


def maybe_persist_dropped_note_before_invalidate(implement_tmpdir: Path, *, redact_fn: Callable[[str], str]) -> bool:
    _ = implement_tmpdir, redact_fn
    return False


def _clear_staged_and_dropped_artifacts(
    implement_tmpdir: Path, *, kind: AssessmentKind
) -> None:
    names = [
        kind.staged_assessment,
        kind.staged_assessment_env,
        kind.dropped_note_artifact,
        kind.ship_outcome_sidecar,
    ]
    if kind is GUIDELINES:
        names[:0] = [LEGACY_WARNING, LEGACY_WARNING_ENV]
    for name in names:
        path = implement_tmpdir / name
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            elif _artifact_still_present(path):
                path.unlink()
        except OSError:
            pass


clear_staged_and_dropped_artifacts = partial(
    _clear_staged_and_dropped_artifacts, kind=GUIDELINES
)
clear_invariant_staged_and_dropped_artifacts = partial(
    _clear_staged_and_dropped_artifacts, kind=INVARIANTS
)


def _write_staged_assessment(  # noqa: PLR0913 - cohesive artifact writer
    *, implement_tmpdir: Path,
    assessment_text: str,
    assessed_head_sha: str,
    diff_fingerprint_value: str,
    base_ref: str,
    outcome: str,
    kind: AssessmentKind,
    diff_text: str = "",
) -> None:
    validated_outcome = _validate_authored_outcome(note=assessment_text, outcome=outcome, kind=kind)
    implement_tmpdir.mkdir(parents=True, exist_ok=True)
    diff_path = _artifact_path(implement_tmpdir, kind, "materialized_diff")
    _write_text_atomic(
        path=_artifact_path(implement_tmpdir, kind, "staged_assessment"), text=assessment_text
    )
    _write_text_atomic(path=diff_path, text=diff_text)
    written_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    sidecar = "\n".join(
        [
            "STATUS=present",
            f"ASSESSED_HEAD_SHA={_env_escape(assessed_head_sha)}",
            f"DIFF_FINGERPRINT={_env_escape(diff_fingerprint_value)}",
            f"BASE_REF={_env_escape(base_ref)}",
            f"DIFF_SNAPSHOT={_env_escape(str(diff_path))}",
            *([f"{kind.status_env_key}=present"] if kind.is_invariant else []),
            f"ASSESSMENT_KIND={_env_escape(validated_outcome)}",
            f"WRITTEN_AT={written_at}",
            "",
        ]
    )
    _write_text_atomic(
        path=_artifact_path(implement_tmpdir, kind, "staged_assessment_env"), text=sidecar
    )


write_staged_assessment = partial(_write_staged_assessment, kind=GUIDELINES)
write_invariant_staged_assessment = partial(_write_staged_assessment, kind=INVARIANTS)


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


def _write_implement_note(  # noqa: PLR0913 - compatibility writer carries the complete note identity
    *, implement_tmpdir: Path, note_text: str, head_sha: str,
    metadata: dict[str, str], base_ref: str, kind: AssessmentKind
) -> None:
    _write_text_atomic(path=_artifact_path(implement_tmpdir, kind, "durable_note"), text=note_text)
    _write_text_atomic(
        path=_artifact_path(implement_tmpdir, kind, "durable_note_env"),
        text=_durable_metadata_text(
            head_sha=head_sha,
            metadata=metadata,
            base_ref=base_ref,
            status_key=kind.status_env_key,
            status_default="present",
        ),
    )
    _clear_staged_and_dropped_artifacts(implement_tmpdir, kind=kind)


write_implement_note = partial(_write_implement_note, kind=GUIDELINES)
write_invariant_implement_note = partial(_write_implement_note, kind=INVARIANTS)


def write_deterministic_clean_note(
    *,
    implement_tmpdir: Path,
    head_sha: str,
    base_ref: str,
    diff_text: str,
    kind: AssessmentKind = GUIDELINES,
) -> None:
    """Persist a deterministic clean note backed by validated diff evidence."""
    fingerprint = diff_fingerprint(diff_text)
    diff_path = _artifact_path(implement_tmpdir, kind, "materialized_diff")
    _write_text_atomic(path=diff_path, text=diff_text)
    metadata = {
        "NOTE_STATE": config.NOTE_STATE_DETERMINISTIC_CLEAN,
        "ASSESSED_HEAD_SHA": head_sha,
        "DIFF_FINGERPRINT": fingerprint,
        "AUTHORED_DIFF_FINGERPRINT": fingerprint,
        "COVERED_DIFF_FINGERPRINT": fingerprint,
        "DIFF_SNAPSHOT": str(diff_path),
        "ASSESSMENT_KIND": "clean",
    }
    _write_implement_note(
        implement_tmpdir=implement_tmpdir,
        note_text=kind.clean_presentation_note,
        head_sha=head_sha,
        metadata=metadata,
        base_ref=base_ref,
        kind=kind,
    )


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


def _kind_staged_fingerprint_valid(
    *, implement_tmpdir: Path,
    metadata: dict[str, str],
    base_ref: str,
    kind: AssessmentKind,
    repo_root: Path | None = None,
) -> bool:
    stored_fp = metadata.get("DIFF_FINGERPRINT", "")
    if not stored_fp:
        return False
    resolved_base = (base_ref or metadata.get("BASE_REF", "")).strip()
    if repo_root is not None and resolved_base:
        live_fp = _live_fingerprint(repo_root=repo_root, resolved_base=resolved_base)
        if live_fp is not None:
            return live_fp == stored_fp
    diff_path = _artifact_path(implement_tmpdir, kind, "materialized_diff")
    if diff_path.is_file() and not diff_path.is_symlink():
        try:
            snapshot_text = diff_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False
        return diff_fingerprint(snapshot_text) == stored_fp
    return False


def refresh_staged_assessment_for_current_head(  # noqa: PLR0911 - fail-closed artifact refresh has distinct validation exits
    implement_tmpdir: Path,
    *,
    head_sha: str,
    base_ref: str = "",
    repo_root: str | Path | None = None,
) -> bool:
    """Refresh staged assessment metadata against the current live implementation diff."""
    if repo_root is None or not head_sha.strip():
        return False
    staged = staged_assessment_path(implement_tmpdir)
    sidecar = _artifact_path(implement_tmpdir, GUIDELINES, "staged_assessment_env")
    if not _regular_file(staged) or not _regular_file(sidecar):
        return False
    metadata = _read_env(sidecar)
    if metadata.get("STATUS") != "present":
        return False
    resolved_base = (base_ref or metadata.get("BASE_REF", "")).strip()
    if not resolved_base:
        return False
    try:
        root = Path(repo_root).resolve()
    except OSError:
        return False
    live_diff = _materialize_live_diff(repo_root=root, resolved_base=resolved_base)
    if live_diff is None:
        return False
    diff_text, fingerprint = live_diff
    stored_fp = metadata.get("DIFF_FINGERPRINT", "")
    if not stored_fp:
        return False
    try:
        assessment_text = _read_regular_text_no_follow(staged)
        write_staged_assessment(
            implement_tmpdir=implement_tmpdir,
            assessment_text=assessment_text,
            assessed_head_sha=head_sha,
            diff_fingerprint_value=fingerprint,
            base_ref=resolved_base,
            outcome=metadata.get("ASSESSMENT_KIND", ""),
            diff_text=diff_text,
        )
    except (OSError, UnicodeDecodeError, AssessmentReauthorRequired):
        return False
    return True


def _pin_note_from_live_diff(
    *,
    implement_tmpdir: Path,
    head_sha: str,
    resolved_base: str,
    live_diff: tuple[str, str],
) -> bool:
    pinned = False
    staged = staged_assessment_path(implement_tmpdir)
    sidecar = _artifact_path(implement_tmpdir, GUIDELINES, "staged_assessment_env")
    try:
        assessment_text = _read_regular_text_no_follow(staged)
        diff_text, fingerprint = live_diff
        write_staged_assessment(
            implement_tmpdir=implement_tmpdir,
            assessment_text=assessment_text,
            assessed_head_sha=head_sha,
            diff_fingerprint_value=fingerprint,
            base_ref=resolved_base,
            outcome=_read_env(sidecar).get("ASSESSMENT_KIND", ""),
            diff_text=diff_text,
        )
        refreshed_metadata = _read_env(sidecar)
        metadata_valid = refreshed_metadata.get("STATUS") == "present" and refreshed_metadata.get("DIFF_FINGERPRINT") == fingerprint
        if metadata_valid:
            write_implement_note(
                implement_tmpdir=implement_tmpdir,
                note_text=assessment_text,
                head_sha=head_sha,
                metadata=refreshed_metadata,
                base_ref=resolved_base,
            )
            pinned = True
    except (OSError, UnicodeDecodeError, AssessmentReauthorRequired):
        pinned = False
    return pinned


def pin_note_from_staged_for_current_head(
    implement_tmpdir: Path,
    *,
    head_sha: str,
    base_ref: str = "",
    repo_root: str | Path | None = None,
) -> bool:
    """Pin the staged assessment, using one live diff materialization when available."""
    staged = staged_assessment_path(implement_tmpdir)
    sidecar = _artifact_path(implement_tmpdir, GUIDELINES, "staged_assessment_env")
    pinned = False
    if _regular_file(staged) and _regular_file(sidecar):
        metadata = _read_env(sidecar)
        resolved_base = (base_ref or metadata.get("BASE_REF", "")).strip()
        if metadata.get("STATUS") == "present" and (repo_root is None or not resolved_base):
            pinned = pin_note_from_staged(
                implement_tmpdir,
                head_sha=head_sha,
                base_ref=base_ref,
                repo_root=None,
            )
        elif metadata.get("STATUS") == "present" and repo_root is not None and resolved_base:
            root: Path | None = None
            with suppress(OSError):
                root = Path(repo_root).resolve()
            if root is not None:
                live_diff = _materialize_live_diff(repo_root=root, resolved_base=resolved_base)
                if live_diff is None:
                    pinned = pin_note_from_staged(
                        implement_tmpdir,
                        head_sha=head_sha,
                        base_ref=resolved_base,
                        repo_root=None,
                    )
                elif metadata.get("DIFF_FINGERPRINT", ""):
                    pinned = _pin_note_from_live_diff(
                        implement_tmpdir=implement_tmpdir,
                        head_sha=head_sha,
                        resolved_base=resolved_base,
                        live_diff=live_diff,
                    )
    return pinned


def _pin_kind_note_from_staged(
    implement_tmpdir: Path,
    *,
    head_sha: str,
    kind: AssessmentKind,
    base_ref: str = "",
    repo_root: str | Path | None = None,
) -> bool:
    staged = _artifact_path(implement_tmpdir, kind, "staged_assessment")
    sidecar = _artifact_path(implement_tmpdir, kind, "staged_assessment_env")
    if not staged.is_file() or staged.is_symlink() or not sidecar.is_file() or sidecar.is_symlink():
        return False
    metadata = _read_env(sidecar)
    if metadata.get("STATUS") != "present":
        return False
    if not _kind_staged_fingerprint_valid(
        implement_tmpdir=implement_tmpdir,
        metadata=metadata,
        base_ref=base_ref,
        kind=kind,
        repo_root=Path(repo_root).resolve() if repo_root is not None else None,
    ):
        return False
    try:
        note_text = staged.read_text(encoding="utf-8")
    except OSError:
        return False
    try:
        _write_implement_note(
            implement_tmpdir=implement_tmpdir, note_text=note_text, head_sha=head_sha,
            metadata=metadata, base_ref=base_ref, kind=kind,
        )
    except OSError:
        return False
    return True


pin_note_from_staged = partial(_pin_kind_note_from_staged, kind=GUIDELINES)


def _invalidate_artifacts(kind: AssessmentKind) -> tuple[str, ...]:
    common = (
        kind.staged_assessment,
        kind.staged_assessment_env,
        kind.durable_note,
        kind.durable_note_env,
        kind.dropped_note_artifact,
        kind.ship_outcome_sidecar,
    )
    return (LEGACY_WARNING, LEGACY_WARNING_ENV, *common) if kind is GUIDELINES else common


def _artifact_still_present(path: Path) -> bool:
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False


def _invalidate_implement_note(implement_tmpdir: Path, *, kind: AssessmentKind) -> None:
    artifacts = _invalidate_artifacts(kind)
    for name in artifacts:
        path = implement_tmpdir / name
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            elif _artifact_still_present(path):
                path.unlink()
        except FileNotFoundError:
            pass
    surviving = [name for name in artifacts if _artifact_still_present(implement_tmpdir / name)]
    if surviving:
        raise OSError("artifact(s) survived invalidation: " + ", ".join(surviving))


invalidate_implement_note = partial(_invalidate_implement_note, kind=GUIDELINES)
invalidate_invariant_implement_note = partial(_invalidate_implement_note, kind=INVARIANTS)


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


def _write_compose_materialization_metadata(
    *,
    implement_tmpdir: Path,
    materialized: ComposeMaterializationResult,
    kind: AssessmentKind = GUIDELINES,
) -> None:
    written_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    diff_path = materialized.diff_path or _artifact_path(implement_tmpdir, kind, "materialized_diff")
    _write_text_atomic(
        path=_artifact_path(implement_tmpdir, kind, "materialize_env"),
        text="\n".join(
            [
                "STATUS=present",
                f"HEAD_SHA={_env_escape(materialized.head_sha)}",
                f"ASSESSED_HEAD_SHA={_env_escape(materialized.head_sha)}",
                f"BASE_REF={_env_escape(materialized.base_ref)}",
                f"NOTE_STATE={config.NOTE_STATE_AUTHORED}",
                f"DIFF_FINGERPRINT={_env_escape(materialized.diff_fingerprint)}",
                f"AUTHORED_DIFF_FINGERPRINT={_env_escape(materialized.diff_fingerprint)}",
                f"COVERED_DIFF_FINGERPRINT={_env_escape(materialized.diff_fingerprint)}",
                f"DIFF_SNAPSHOT={_env_escape(str(diff_path))}",
                f"{kind.status_env_key}={_env_escape(materialized.guidelines_status)}",
                f"{kind.path_env_key}={_env_escape(materialized.guidelines_path)}",
                f"ASSESSMENT_KIND={_env_escape(materialized.assessment_kind)}",
                f"WRITTEN_AT={written_at}",
                "",
            ]
        ),
    )


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


# A Gate C guideline deviation publishes only when its persisted assessment note
# carries exactly one *active* documented-exception line: a top-level
# `Exception:` line (outside every code fence) recording a non-empty rationale,
# `author: main-agent`, and a real calendar date. Exception-looking text inside a
# backtick or tilde fence has no authority, and duplicate active lines fail closed
# (#7196.2; the /design mirror of the #7193 /implement ladder).
_EXCEPTION_LEAD_RE = re.compile(r"^\s*Exception:")
_DESIGN_EXCEPTION_RE = re.compile(
    r"^\s*Exception:\s+(?P<rationale>\S[^\n]*?)\s+"
    r"\(author:\s*main-agent,\s+date:\s*"
    r"(?P<date>\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]))\)\s*$"
)


@dataclass(frozen=True)
class GuidelineException:
    """A validated active documented-exception recovered from a deviation note."""

    rationale: str
    date: str
    line: str


def _exception_date_plausible(date_text: str) -> bool:
    """True when ``date_text`` parses as a real calendar date (rejects Feb 30, etc.)."""
    try:
        year_text, month_text, day_text = date_text.split("-")
        _ = datetime(int(year_text), int(month_text), int(day_text), tzinfo=UTC)
    except ValueError:
        return False
    return True


def _active_exception_lines(note: str) -> list[str]:
    """Return the note's non-fenced lines that lead with ``Exception:``.

    Lines inside a balanced code fence carry no authority (G-Md-3).
    """
    from larch.design import plan_grammar  # noqa: PLC0415 - deferred function-level import keeps larch.core import-time free of larch.design  # lint-layering: ok reuse the balanced fenced-code-block scanner (G-Md-3) instead of re-deriving fence state.
    lines = note.splitlines()
    fenced = plan_grammar.balanced_fence_line_indices(lines)
    return [
        line
        for index, line in enumerate(lines)
        if index not in fenced and _EXCEPTION_LEAD_RE.match(line) is not None
    ]


def guideline_active_exception(note: str) -> GuidelineException | None:
    """Return the sole valid active documented-exception, or ``None`` (fail closed).

    Recognizes exactly one active ``Exception:`` line outside code fences with a
    non-empty rationale, ``author: main-agent``, and a real calendar date. Missing,
    malformed, empty-rationale, wrong-author, impossible-date, duplicate, and
    fenced-only notes return ``None``.
    """
    active = _active_exception_lines(note)
    if len(active) != 1:
        return None
    match = _DESIGN_EXCEPTION_RE.match(active[0])
    if match is None:
        return None
    rationale = match.group("rationale").strip()
    if not rationale or not _exception_date_plausible(match.group("date")):
        return None
    return GuidelineException(rationale=rationale, date=match.group("date"), line=active[0].strip())


def guideline_exception_present(note: str) -> bool:
    """True when the note carries any active (non-fenced) ``Exception:`` line."""
    return bool(_active_exception_lines(note))


def guideline_exception_valid(note: str) -> bool:
    """True when the note carries exactly one valid active documented-exception."""
    return guideline_active_exception(note) is not None


def _compose_precheck_result(
    *,
    implement_tmpdir: Path,
    root: Path | None,
    current_head: str,
    expected_head_sha: str,
    kind: AssessmentKind,
) -> tuple[ArchitecturalGuidelinesResult | None, ComposeMaterializationResult | None]:
    if expected_head_sha and current_head and expected_head_sha != current_head:
        return None, ComposeMaterializationResult(
            status="failed",
            head_sha=current_head,
            warning=f"HEAD changed before architectural-{kind.key} compose materialization",
        )
    metadata = _read_env(_artifact_path(implement_tmpdir, kind, "durable_note_env"))
    if current_head and _note_consumable(
        implement_tmpdir=implement_tmpdir,
        head_sha=current_head,
        repo_root=root,
        base_ref=metadata.get("BASE_REF", ""),
        kind=kind,
    ):
        current_result: ComposeMaterializationResult | None = None
        if root is None:
            current_result = ComposeMaterializationResult(status="current", head_sha=current_head)
        else:
            stored_base_ref = metadata.get("BASE_REF", "")
            if stored_base_ref and not _note_fingerprint_stale(
                implement_tmpdir=implement_tmpdir,
                base_ref=stored_base_ref,
                repo_root=root,
                kind=kind,
            ):
                current_result = ComposeMaterializationResult(status="current", head_sha=current_head)
        if current_result is not None:
            return None, current_result
    result = _read_assessment_kind(kind=kind, repo_root=root)
    if result.status in {"absent", "invalid"}:
        return None, ComposeMaterializationResult(
            status=result.status,
            head_sha=current_head,
            guidelines_status=result.status,
            warning=result.warning if result.status == "invalid" else "",
        )
    if kind.ship_present_empty and not result.content.strip():
        return None, ComposeMaterializationResult(
            status="present-empty",
            head_sha=current_head,
            guidelines_status=result.status,
            guidelines_path=str(result.path or ""),
            assessment_kind=config.ASSESSMENT_OUTCOME_CLEAN,
        )
    if root is None:
        return None, ComposeMaterializationResult(
            status="failed",
            head_sha=current_head,
            guidelines_status=result.status,
            warning="could not resolve repo root",
        )
    return result, None


def _prepare_compose_assessment(  # noqa: PLR0913 - compose snapshot seam preserves the public lifecycle contract
    *,
    implement_tmpdir: Path,
    kind: AssessmentKind,
    repo_root: str | Path | None = None,
    forked_target: bool = False,
    expected_head_sha: str = "",
    compose_snapshot_factory: Callable[[], ComposeAssessmentSnapshot] | None = None,
) -> ComposeMaterializationResult:
    implement_tmpdir.mkdir(parents=True, exist_ok=True)
    _clear_staged_and_dropped_artifacts(implement_tmpdir, kind=kind)
    root = _resolve_repo_root(repo_root)
    current_head = _current_head(root, verify_commit=True) if root is not None else ""
    result, precheck = _compose_precheck_result(
        implement_tmpdir=implement_tmpdir,
        root=root,
        current_head=current_head,
        expected_head_sha=expected_head_sha,
        kind=kind,
    )
    if precheck is not None:
        return precheck
    if result is None:
        return ComposeMaterializationResult(
            status="failed", head_sha=current_head, warning=f"{kind.key} precheck failed"
        )
    try:
        materialized_snapshot = (
            compose_snapshot_factory()
            if compose_snapshot_factory is not None
            else materialize_compose_assessment_snapshot(
                repo_root=root,
                forked_target=forked_target,
                expected_head_sha=current_head,
            )
        )
    except (OSError, RuntimeError) as exc:
        return ComposeMaterializationResult(
            status="failed",
            head_sha=current_head,
            guidelines_status=result.status,
            warning=str(exc).replace("\n", " "),
        )
    if materialized_snapshot.head_sha != current_head:
        return ComposeMaterializationResult(
            status="failed",
            head_sha=current_head,
            base_ref=materialized_snapshot.base_ref,
            guidelines_status=result.status,
            warning=f"HEAD changed before architectural-{kind.key} compose materialization",
        )
    materialized = ComposeMaterializationResult(
        status="assessment-required",
        head_sha=materialized_snapshot.head_sha,
        base_ref=materialized_snapshot.base_ref,
        diff_fingerprint=materialized_snapshot.diff_fingerprint,
        diff_path=_artifact_path(implement_tmpdir, kind, "materialized_diff"),
        guidelines_status=result.status,
        guidelines_path=str(result.path or ""),
    )
    try:
        _write_text_atomic(
            path=_artifact_path(implement_tmpdir, kind, "materialized_diff"),
            text=materialized_snapshot.diff_text,
        )
        _write_compose_materialization_metadata(
            implement_tmpdir=implement_tmpdir,
            materialized=materialized,
            kind=kind,
        )
    except OSError as exc:
        return ComposeMaterializationResult(
            status="failed",
            head_sha=current_head,
            base_ref=materialized.base_ref,
            guidelines_status=result.status,
            warning=str(exc).replace("\n", " "),
        )
    return materialized


prepare_compose_assessment = partial(_prepare_compose_assessment, kind=GUIDELINES)
prepare_invariant_compose_assessment = partial(_prepare_compose_assessment, kind=INVARIANTS)


def _write_compose_assessment(
    *,
    implement_tmpdir: Path,
    assessment_text: str,
    outcome: str,
    kind: AssessmentKind,
    repo_root: str | Path | None = None,
) -> None:
    normalized = _normalize_assessment_text(assessment_text)
    if not normalized.strip():
        raise ValueError("assessment-file: content must not be empty")
    validated_outcome: str = _validate_authored_outcome(
        note=normalized, outcome=outcome, kind=kind
    )
    metadata = _read_env(_artifact_path(implement_tmpdir, kind, "materialize_env"))
    materialized_head = metadata.get("HEAD_SHA", "")
    if not materialized_head:
        raise ValueError("compose materialization metadata is missing HEAD_SHA")
    root = _resolve_repo_root(repo_root)
    current_head = _current_head(root, verify_commit=True)
    if current_head != materialized_head:
        raise ValueError("HEAD changed after compose materialization; rerun Step 8")
    if metadata.get("STATUS") != "present":
        raise ValueError("compose materialization metadata is not present")
    metadata = dict(metadata)
    metadata["ASSESSMENT_KIND"] = validated_outcome
    _write_implement_note(
        implement_tmpdir=implement_tmpdir,
        note_text=normalized,
        head_sha=materialized_head,
        metadata=metadata,
        base_ref=metadata.get("BASE_REF", ""),
        kind=kind,
    )


write_compose_assessment = partial(_write_compose_assessment, kind=GUIDELINES)
write_invariant_compose_assessment = partial(_write_compose_assessment, kind=INVARIANTS)


def _format_deviation_warning_entry(note: str) -> str:
    lines: list[str] = []
    for raw_line in note.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        lines.append(stripped if stripped.startswith("- ") else f"- {stripped}")
    if not lines:
        raise ValueError("note-file: content must not be empty")
    return "\n".join(lines)


def _warning_chunk_keys(body: str) -> set[str]:
    from larch.report import exec_issue_detail  # noqa: PLC0415  # lint-layering: ok append helper must match run-log flush warning dedupe.
    from larch.issue.execution_issues import _execution_issue_chunks as execution_issue_chunks  # noqa: PLC0415  # lint-layering: ok append helper must match run-log flush chunking and dedupe.
    keys: set[str] = set()
    for chunk_body in execution_issue_chunks(body):
        for key in exec_issue_detail.structured_body_dedupe_keys(chunk_body, _EXECUTION_WARNINGS_CATEGORY):
            keys.add(f"{_EXECUTION_WARNINGS_CATEGORY}\0{key}")
    return keys


def _warning_chunk_source_shas(body: str) -> set[str]:
    from larch.report.run_log_batch import _normalize_body_for_hash  # noqa: PLC0415  # lint-layering: ok append helper must match run-log flush redaction and append behavior.
    from larch.issue.execution_issues import _execution_issue_chunks as execution_issue_chunks  # noqa: PLC0415  # lint-layering: ok append helper must match run-log flush chunking and dedupe.
    shas: set[str] = set()
    for chunk_body in execution_issue_chunks(body):
        normalized = _normalize_body_for_hash(chunk_body)
        if normalized:
            shas.add(hashlib.sha256(normalized.encode("utf-8")).hexdigest())
    return shas


def _section_body_lines(markdown: str, category: str) -> list[str]:
    lines: list[str] = []
    in_target = False
    for line in markdown.splitlines():
        if line.startswith("### "):
            if in_target:
                break
            in_target = line == f"### {category}"
            continue
        if in_target:
            lines.append(line)
    return lines


def _existing_warning_keys_from_markdown(path: Path) -> set[str]:
    from larch.report.run_log_batch import _redact_batch_payload  # noqa: PLC0415  # lint-layering: ok append helper must match run-log flush redaction and append behavior.
    if not path.is_file() or path.is_symlink():
        return set()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    body = "\n".join(_section_body_lines(text, _EXECUTION_WARNINGS_CATEGORY))
    if not body.strip():
        return set()
    return _warning_chunk_keys(_redact_batch_payload(body))


def _valid_run_id(run_id: str) -> bool:
    return bool(run_id and ".." not in run_id and "/" not in run_id and "\\" not in run_id and _RUN_ID_RE.fullmatch(run_id))


def _read_session_run_id(implement_tmpdir: Path) -> str:
    run_id = larch_io.read_kv(
        path=implement_tmpdir / "parent-issue.md",
        key="RUN_ID",
        default="",
        first_match=True,
        cr_strip="strip",
        on_error_default=True,
        reject_symlink=True,
    ).strip()
    if _valid_run_id(run_id):
        return run_id
    session_id = implement_tmpdir / "session-id"
    if not session_id.is_file() or session_id.is_symlink():
        return ""
    try:
        run_id = session_id.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
    return run_id if _valid_run_id(run_id) else ""


def _existing_warning_source_shas(batch_text: str) -> set[str]:
    shas: set[str] = set()
    for raw in batch_text.splitlines():
        try:
            parsed: object = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue
        row = cast("dict[str, object]", parsed)
        sha = row.get("source_sha256")
        if row.get("category") == _EXECUTION_WARNINGS_CATEGORY and isinstance(sha, str):
            shas.add(sha)
    return shas


def _existing_warning_keys_and_shas_from_ndjson(implement_tmpdir: Path) -> tuple[set[str], set[str]]:
    run_id = _read_session_run_id(implement_tmpdir)
    if not run_id:
        return set(), set()
    batch_path = implement_tmpdir / "larch-logs" / "implement" / run_id / "execution-issues.ndjson"
    if not batch_path.is_file() or batch_path.is_symlink():
        return set(), set()
    try:
        batch_text = batch_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set(), set()
    from larch.issue.execution_issues import _existing_execution_issue_keys as existing_execution_issue_keys  # noqa: PLC0415  # lint-layering: ok append helper must match run-log flush chunking and dedupe.
    return existing_execution_issue_keys(batch_text), _existing_warning_source_shas(batch_text)


def append_deviation_note(implement_tmpdir: Path, note: str) -> str:
    """Append a guideline deviation warning unless the run already has the same warning."""
    from larch.report.run_log_batch import _redact_batch_payload, append_execution_issue  # noqa: PLC0415  # lint-layering: ok append helper must match run-log flush redaction and append behavior.
    entry = _format_deviation_warning_entry(note)
    redacted_entry = _redact_batch_payload(entry)
    issue_log = implement_tmpdir / "execution-issues.md"
    existing_keys = _existing_warning_keys_from_markdown(issue_log)
    ndjson_keys, ndjson_shas = _existing_warning_keys_and_shas_from_ndjson(implement_tmpdir)
    known_keys = existing_keys | ndjson_keys
    from larch.issue.execution_issues import _execution_issue_chunks as execution_issue_chunks  # noqa: PLC0415  # lint-layering: ok append helper must match run-log flush chunking and dedupe.
    kept_chunks: list[str] = []
    for chunk_body in execution_issue_chunks(redacted_entry):
        chunk_keys = _warning_chunk_keys(chunk_body)
        chunk_shas = _warning_chunk_source_shas(chunk_body)
        if chunk_keys <= known_keys or (chunk_shas and chunk_shas <= ndjson_shas):
            continue
        kept_chunks.append(chunk_body)
        known_keys.update(chunk_keys)
        ndjson_shas.update(chunk_shas)
    if not kept_chunks:
        return _APPEND_DEVIATION_DUPLICATE
    try:
        append_execution_issue(log_file=issue_log, category=_EXECUTION_WARNINGS_CATEGORY, entry="\n".join(kept_chunks))
    except OSError:
        return _APPEND_DEVIATION_FAILED
    return _APPEND_DEVIATION_OK


def _append_deviation_note_main(argv: list[str], *, kind: AssessmentKind) -> int:
    parser = argparse.ArgumentParser(prog=f"architectural-{kind.key} append-deviation-note")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    parser.add_argument("--note-file", required=True)
    args = parser.parse_args(argv)
    if not args.implement_tmpdir:
        print(f"{kind.env_prefix}_APPEND_STATUS={_APPEND_DEVIATION_FAILED}")
        print(f"{kind.env_prefix}_WARNING=missing implement tmpdir")
        return 2
    try:
        note_text = _read_regular_text_no_follow(Path(args.note_file))
        status = append_deviation_note(Path(args.implement_tmpdir), note_text)
    except (OSError, UnicodeDecodeError, ValueError, ShipError) as exc:
        print(f"{kind.env_prefix}_APPEND_STATUS={_APPEND_DEVIATION_FAILED}")
        print(f"{kind.env_prefix}_WARNING={str(exc).replace(chr(10), ' ')}")
        return 1
    print(f"{kind.env_prefix}_APPEND_STATUS={status}")
    return 1 if status == _APPEND_DEVIATION_FAILED else 0


def _bool_arg(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


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


def _persist_design_assessment(
    *,
    repo_root: str | Path | None,
    design_tmpdir: str,
    kind: AssessmentKind,
    assessment: str = "",
    assessment_text: str | None = None,
) -> int:
    design_tmpdir_path = _validate_design_tmpdir_arg(design_tmpdir)
    result = _read_assessment_kind(kind=kind, repo_root=repo_root)
    path = _artifact_path(design_tmpdir_path, kind, "design_assessment")
    requires_assessment = result.status == "present" and (
        not kind.design_requires_nonempty or bool(result.content.strip())
    )
    if not requires_assessment:
        remove_stale = result.status != "present" or kind.design_empty_removes
        if remove_stale:
            _safe_unlink_assessment(path)
            if path.exists() or path.is_symlink():
                raise OSError(
                    f"{kind.design_assessment}: stale entry could not be removed (not a regular file)"
                )
        return 0
    if assessment == config.ASSESSMENT_OUTCOME_CLEAN:
        text = kind.clean_presentation_note + "\n"
    elif assessment_text is not None:
        text = _normalize_assessment_text(assessment_text)
    else:
        raise ValueError(f"present {kind.key} require exactly one assessment source")
    _write_kind_design_assessment_atomic(design_tmpdir=design_tmpdir_path, text=text, kind=kind)
    return 0


persist_design_assessment = partial(_persist_design_assessment, kind=GUIDELINES)
persist_invariant_design_assessment = partial(_persist_design_assessment, kind=INVARIANTS)


def _emit_design_assessment_persist_result(
    *,
    guidelines_status: str,
    persist_result: str,
    reason: str,
) -> None:
    print("ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_ATTEMPTED=true")
    print(f"ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_GUIDELINES_STATUS={guidelines_status}")
    print(f"ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_RESULT={persist_result}")
    print(f"ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_REASON={_env_escape(reason)}")
    print(f"ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_ARTIFACT={DESIGN_ASSESSMENT}")


def _design_assessment_flag_error(
    *,
    result: ArchitecturalGuidelinesResult,
    has_clean: bool,
    has_file: bool,
    kind: AssessmentKind,
) -> str | None:
    requires_assessment = result.status == "present" and (
        not kind.design_requires_nonempty or bool(result.content.strip())
    )
    if requires_assessment:
        if has_clean == has_file:
            return (
                f"present architectural {kind.key} require exactly one of "
                "--assessment clean or --assessment-file"
            )
        return None
    if has_clean or has_file:
        states = "absent, empty, or invalid" if kind.design_requires_nonempty else "absent or invalid"
        return f"{states} architectural {kind.key} do not accept assessment source flags"
    return None


def _design_exception_flag_error(
    *, note: str, allow_exception: bool, kind: AssessmentKind
) -> tuple[str, str] | None:
    """Validate a guideline deviation note's documented-exception state.

    Without ``--allow-exception`` any active exception line fails closed. With the
    flag, the note must carry exactly one valid active documented-exception.
    """
    if kind.is_invariant:
        return None
    if not allow_exception:
        if guideline_exception_present(note):
            return (
                "unexpected-exception",
                "guideline note carries a documented-exception line; pass "
                "--allow-exception only to persist a Gate C decline",
            )
        return None
    if not guideline_exception_valid(note):
        return (
            "invalid-exception",
            "--allow-exception requires exactly one active documented-exception line "
            "(Exception: <rationale> (author: main-agent, date: YYYY-MM-DD))",
        )
    return None


def _emit_guideline_persist_result(
    *, kind: AssessmentKind, status: str, result: str, reason: str
) -> None:
    if not kind.is_invariant:
        _emit_design_assessment_persist_result(
            guidelines_status=status, persist_result=result, reason=reason
        )


def _persist_prevalidate(  # noqa: PLR0911 - fail-closed persistence validates each flag, source, and exception boundary with a distinct machine reason
    *,
    args: argparse.Namespace,
    result: ArchitecturalGuidelinesResult,
    kind: AssessmentKind,
) -> tuple[str | None, tuple[str, str] | None]:
    """Validate persist flags and read/validate the assessment file.

    Returns ``(assessment_text, None)`` on success, where ``assessment_text`` is
    ``None`` (no source file) or the file text; or ``(None, (reason, message))``
    on a rejected flag combination or exception state. An empty reason suppresses
    the guideline machine line (the invariant path emits none).
    """
    has_clean = args.assessment == "clean"
    has_file = bool(args.assessment_file)
    if args.allow_exception and kind.is_invariant:
        return None, ("", "--allow-exception is not valid for architectural invariants")
    flag_error = _design_assessment_flag_error(result=result, has_clean=has_clean, has_file=has_file, kind=kind)
    if flag_error is not None:
        return None, ("invalid-flags", flag_error)
    if args.allow_exception and not has_file:
        return None, ("allow-exception-requires-file", "--allow-exception requires a guideline deviation --assessment-file")
    if not has_file:
        return None, None
    try:
        assessment_text = _read_regular_text_no_follow(Path(args.assessment_file))
    except OSError as exc:
        return None, ("assessment-file-unreadable", f"assessment-file: {exc}")
    if not assessment_text.strip():
        return None, ("assessment-file-empty", "assessment-file: content must not be empty")
    exception_error = _design_exception_flag_error(note=assessment_text, allow_exception=args.allow_exception, kind=kind)
    if exception_error is not None:
        return None, exception_error
    return assessment_text, None


def _persist_design_assessment_main(argv: list[str], *, kind: AssessmentKind) -> int:
    parser = argparse.ArgumentParser(prog=f"architectural-{kind.key} persist-design-assessment")
    parser.add_argument("--repo-root")
    parser.add_argument("--design-tmpdir", default=os.environ.get(config.ENV_DESIGN_TMPDIR, ""))
    parser.add_argument("--assessment", choices=("clean",))
    parser.add_argument("--assessment-file")
    parser.add_argument(
        "--allow-exception", action="store_true",
        help="permit a guideline deviation note carrying one documented-exception "
        "block (Gate C decline persistence only)",
    )
    args = parser.parse_args(argv)
    try:
        design_tmpdir = _validate_design_tmpdir_arg(args.design_tmpdir)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    result = _read_assessment_kind(kind=kind, repo_root=args.repo_root)
    assessment_text, error = _persist_prevalidate(args=args, result=result, kind=kind)
    if error is not None:
        reason, message = error
        if reason:
            _emit_guideline_persist_result(kind=kind, status=result.status, result="failed", reason=reason)
        print(message, file=sys.stderr)
        return 1
    try:
        rc = _persist_design_assessment(
            repo_root=args.repo_root,
            design_tmpdir=str(design_tmpdir),
            assessment=args.assessment or "",
            assessment_text=assessment_text,
            kind=kind,
        )
        reason = "not-required" if result.status in {"absent", "invalid"} else "persisted"
        _emit_guideline_persist_result(
            kind=kind, status=result.status, result="ok", reason=reason
        )
        return rc
    except (OSError, ValueError) as exc:
        _emit_guideline_persist_result(
            kind=kind, status=result.status, result="failed", reason="persist-failed"
        )
        print(f"persist-design-assessment: {exc}", file=sys.stderr)
        return 1


def _read_main(argv: list[str], *, kind: AssessmentKind) -> int:
    from larch.issue import issue_wire  # noqa: PLC0415  # lint-layering: ok content blocks must match issue-wire format.
    parser = argparse.ArgumentParser(prog=f"architectural-{kind.key} read")
    parser.add_argument("--repo-root")
    args = parser.parse_args(argv)
    result = _read_assessment_kind(kind=kind, repo_root=args.repo_root)
    print(f"{kind.env_prefix}_STATUS={result.status}")
    if result.status == "present":
        assert result.path is not None
        print(f"{kind.env_prefix}_PATH={result.path}")
        if result.content:
            sys.stdout.write(
                issue_wire.emit_untrusted_content_block(
                    tag=f"architectural_{kind.key}", text=result.content
                )
            )
    elif result.status == "invalid":
        print(f"{kind.env_prefix}_WARNING={result.warning}")
    return 0


def _emit_present_assessment(
    result: ArchitecturalGuidelinesResult, *, kind: AssessmentKind
) -> None:
    from larch.issue import issue_wire  # noqa: PLC0415  # lint-layering: ok content blocks must match issue-wire format.
    assert result.path is not None
    print(f"{kind.env_prefix}_PATH={result.path}")
    if result.content:
        sys.stdout.write(
            issue_wire.emit_untrusted_content_block(
                tag=f"architectural_{kind.key}", text=result.content
            )
        )


def _present_note_main(argv: list[str], *, kind: AssessmentKind) -> int:
    parser = argparse.ArgumentParser(prog=f"architectural-{kind.key} present-note")
    parser.add_argument("--repo-root")
    parser.add_argument("--assessment", choices=("pending", "clean"), default="pending")
    args = parser.parse_args(argv)
    result = _read_assessment_kind(kind=kind, repo_root=args.repo_root)
    if result.status == "absent":
        return 0
    if result.status == "invalid":
        print(f"{kind.env_prefix}_WARNING={result.warning}")
        return 0
    if args.assessment == "clean":
        if not kind.design_requires_nonempty or result.content.strip():
            print(kind.clean_presentation_note)
        return 0
    _emit_present_assessment(result, kind=kind)
    if not kind.design_requires_nonempty or result.content.strip():
        print(kind.assessment_required_line)
    return 0


def _emit_materialized_diff(
    repo_root: Path,
    *,
    forked_target: bool,
    output: str = "",
    implement_tmpdir: str = "",
    kind: AssessmentKind = GUIDELINES,
) -> int:
    from larch.issue import issue_wire  # noqa: PLC0415  # lint-layering: ok content blocks must match issue-wire format.
    base_remote, base_ref = resolve_diff_base(forked_target=forked_target)
    base_label = f"{base_remote}/{base_ref}"
    try:
        diff_text = materialize_implementation_diff(repo_root, base_remote=base_remote, base_ref=base_ref)
    except RuntimeError as exc:
        print(f"{kind.env_prefix}_DIFF_STATUS=failed")
        print(f"{kind.env_prefix}_WARNING={str(exc).replace(chr(10), ' ')}")
        return 1
    fingerprint = diff_fingerprint(diff_text)
    output_path: Path | None = Path(output) if output else None
    try:
        if implement_tmpdir:
            tmpdir = Path(implement_tmpdir)
            output_path = output_path or _artifact_path(tmpdir, kind, "materialized_diff")
            meta_path = _artifact_path(tmpdir, kind, "materialize_env")
            _write_text_atomic(
                path=meta_path,
                text="\n".join(
                    [
                        f"BASE_REF={_env_escape(base_label)}",
                        f"DIFF_FINGERPRINT={_env_escape(fingerprint)}",
                        "",
                    ]
                ),
            )
        if output_path is not None:
            _write_text_atomic(path=output_path, text=diff_text)
    except OSError as exc:
        print(f"{kind.env_prefix}_DIFF_STATUS=failed")
        print(f"{kind.env_prefix}_WARNING={str(exc).replace(chr(10), ' ')}")
        return 1
    print(f"{kind.env_prefix}_DIFF_STATUS=ok")
    print(f"{kind.env_prefix}_BASE_REF={base_label}")
    print(f"{kind.env_prefix}_DIFF_FINGERPRINT={fingerprint}")
    sys.stdout.write(
        issue_wire.emit_untrusted_content_block(
            tag=f"architectural_{kind.key}_diff", text=diff_text
        )
    )
    return 0


def _materialize_diff_main(argv: list[str], *, kind: AssessmentKind) -> int:
    parser = argparse.ArgumentParser(prog=f"architectural-{kind.key} materialize-diff")
    parser.add_argument("--repo-root")
    parser.add_argument("--forked-target", default="false")
    parser.add_argument("--output")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    args = parser.parse_args(argv)
    repo_root = _resolve_repo_root(args.repo_root)
    if repo_root is None:
        print(f"{kind.env_prefix}_DIFF_STATUS=absent")
        return 0
    return _emit_materialized_diff(
        repo_root,
        forked_target=_bool_arg(args.forked_target),
        output=args.output or "",
        implement_tmpdir=args.implement_tmpdir,
        kind=kind,
    )


def _prepare_main(argv: list[str], *, kind: AssessmentKind) -> int:
    parser = argparse.ArgumentParser(prog=f"architectural-{kind.key} prepare")
    parser.add_argument("--repo-root")
    parser.add_argument("--forked-target", default="false")
    parser.add_argument("--output")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    args = parser.parse_args(argv)
    if args.implement_tmpdir:
        try:
            invalidator = (
                invalidate_invariant_implement_note if kind.is_invariant else invalidate_implement_note
            )
            invalidator(Path(args.implement_tmpdir))
        except OSError as exc:
            print(f"{kind.env_prefix}_INVALIDATE_STATUS=failed")
            print(f"{kind.env_prefix}_WARNING={exc}")
            return 2
    result = _read_assessment_kind(kind=kind, repo_root=args.repo_root)
    print(f"{kind.env_prefix}_STATUS={result.status}")
    if result.status == "absent":
        return 0
    if result.status == "invalid":
        print(f"{kind.env_prefix}_WARNING={result.warning}")
        return 0
    assert result.repo_root is not None
    _emit_present_assessment(result, kind=kind)
    if kind.design_requires_nonempty and not result.content.strip():
        return 0
    return _emit_materialized_diff(
        result.repo_root,
        forked_target=_bool_arg(args.forked_target),
        output=args.output or "",
        implement_tmpdir=args.implement_tmpdir,
        kind=kind,
    )


def _emit_compose_prepare_result(
    *, result: ComposeMaterializationResult, implement_tmpdir: Path,
    repo_root: str | Path | None, kind: AssessmentKind = GUIDELINES
) -> None:
    from larch.issue import issue_wire  # noqa: PLC0415  # lint-layering: ok content blocks must match issue-wire format.
    print(f"{kind.env_prefix}_COMPOSE_STATUS={result.status}")
    for key, value in (
        (f"{kind.env_prefix}_HEAD_SHA", result.head_sha),
        (f"{kind.env_prefix}_BASE_REF", result.base_ref),
        (f"{kind.env_prefix}_DIFF_FINGERPRINT", result.diff_fingerprint),
        (f"{kind.env_prefix}_DIFF_PATH", str(result.diff_path) if result.diff_path is not None else ""),
        (f"{kind.env_prefix}_WARNING", result.warning),
    ):
        if value:
            print(f"{key}={value}")
    assessment = _read_assessment_kind(kind=kind, repo_root=repo_root)
    print(f"{kind.env_prefix}_STATUS={assessment.status}")
    if assessment.status != "present":
        return
    _emit_present_assessment(assessment, kind=kind)
    diff_path = result.diff_path or _artifact_path(implement_tmpdir, kind, "materialized_diff")
    if not diff_path.is_file() or diff_path.is_symlink():
        return
    try:
        diff_text = diff_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    if diff_text:
        sys.stdout.write(
            issue_wire.emit_untrusted_content_block(
                tag=f"architectural_{kind.key}_diff", text=diff_text
            )
        )


def _prepare_compose_main(argv: list[str], *, kind: AssessmentKind) -> int:
    parser = argparse.ArgumentParser(prog=f"architectural-{kind.key} prepare-compose")
    parser.add_argument("--repo-root")
    parser.add_argument("--forked-target", default="false")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    parser.add_argument("--expected-head-sha", default="")
    args = parser.parse_args(argv)
    if not args.implement_tmpdir:
        print(f"{kind.env_prefix}_COMPOSE_STATUS=failed")
        print(f"{kind.env_prefix}_WARNING=missing implement tmpdir")
        return 2
    result = _prepare_compose_assessment(
        implement_tmpdir=Path(args.implement_tmpdir),
        repo_root=args.repo_root,
        forked_target=_bool_arg(args.forked_target),
        expected_head_sha=args.expected_head_sha,
        kind=kind,
    )
    _emit_compose_prepare_result(
        result=result,
        implement_tmpdir=Path(args.implement_tmpdir),
        repo_root=args.repo_root,
        kind=kind,
    )
    return 1 if result.status == "failed" else 0


def _write_compose_assessment_main(argv: list[str], *, kind: AssessmentKind) -> int:
    parser = argparse.ArgumentParser(prog=f"architectural-{kind.key} write-compose-assessment")
    parser.add_argument("--outcome", default="")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    parser.add_argument("--repo-root")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--assessment-file")
    source.add_argument("--assessment-text")
    args = parser.parse_args(argv)
    if not args.implement_tmpdir:
        print(f"{kind.env_prefix}_WRITE_STATUS=failed")
        print(f"{kind.env_prefix}_WARNING=missing implement tmpdir")
        return 2
    try:
        if args.assessment_file:
            assessment_path = Path(args.assessment_file)
            implement_tmpdir = Path(args.implement_tmpdir)
            if not assessment_path.is_absolute():
                assessment_path = implement_tmpdir / assessment_path
            assessment_text = _read_regular_text_no_follow(assessment_path)
        else:
            assessment_text = str(args.assessment_text or "")
        _write_compose_assessment(
            implement_tmpdir=Path(args.implement_tmpdir),
            assessment_text=assessment_text,
            outcome=args.outcome,
            repo_root=args.repo_root,
            kind=kind,
        )
    except AssessmentReauthorRequired as exc:
        print(f"{kind.env_prefix}_WRITE_STATUS={config.ASSESSMENT_RESULT_REAUTHOR_REQUIRED}")
        print(f"{kind.env_prefix}_WARNING={str(exc).replace(chr(10), ' ')}")
        return config.EXIT_REAUTHOR_REQUIRED
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"{kind.env_prefix}_WRITE_STATUS=failed")
        print(f"{kind.env_prefix}_WARNING={str(exc).replace(chr(10), ' ')}")
        return 1
    print(f"{kind.env_prefix}_WRITE_STATUS=ok")
    return 0


def _write_staged_assessment_main(argv: list[str], *, kind: AssessmentKind) -> int:
    parser = argparse.ArgumentParser(prog=f"architectural-{kind.key} write-staged-assessment")
    parser.add_argument("--outcome", default="")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--assessment-file")
    source.add_argument("--assessment-text")
    parser.add_argument("--assessed-head-sha", default="")
    parser.add_argument("--diff-fingerprint", default="")
    parser.add_argument("--base-ref", default="")
    parser.add_argument("--diff-file")
    args = parser.parse_args(argv)
    if not args.implement_tmpdir:
        print(f"{kind.env_prefix}_WRITE_STATUS=failed")
        print(f"{kind.env_prefix}_WARNING=missing implement tmpdir")
        return 2
    if args.assessment_file:
        assessment_text = Path(args.assessment_file).read_text(encoding="utf-8")
    else:
        assessment_text = args.assessment_text
    diff_text = ""
    if args.diff_file:
        diff_path = Path(args.diff_file)
        if not diff_path.is_file() or diff_path.is_symlink():
            print(f"{kind.env_prefix}_WRITE_STATUS=failed")
            print(f"{kind.env_prefix}_WARNING=missing diff file")
            return 1
        try:
            diff_text = diff_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"{kind.env_prefix}_WRITE_STATUS=failed")
            print(f"{kind.env_prefix}_WARNING=unreadable diff file ({exc})")
            return 1
    fingerprint = args.diff_fingerprint or diff_fingerprint(diff_text)
    head_sha = args.assessed_head_sha or _current_head()
    try:
        _write_staged_assessment(
            implement_tmpdir=Path(args.implement_tmpdir),
            assessment_text=assessment_text,
            assessed_head_sha=head_sha,
            diff_fingerprint_value=fingerprint,
            base_ref=args.base_ref,
            outcome=args.outcome,
            diff_text=diff_text,
            kind=kind,
        )
    except AssessmentReauthorRequired as exc:
        print(f"{kind.env_prefix}_WRITE_STATUS={config.ASSESSMENT_RESULT_REAUTHOR_REQUIRED}")
        print(f"{kind.env_prefix}_WARNING={str(exc).replace(chr(10), ' ')}")
        return config.EXIT_REAUTHOR_REQUIRED
    print(f"{kind.env_prefix}_WRITE_STATUS=ok")
    return 0


def _pin_note_from_staged_main(argv: list[str], *, kind: AssessmentKind) -> int:
    parser = argparse.ArgumentParser(prog=f"architectural-{kind.key} pin-note-from-staged")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    parser.add_argument("--head-sha", default="")
    parser.add_argument("--base-ref", default="")
    parser.add_argument("--repo-root")
    args = parser.parse_args(argv)
    if not args.implement_tmpdir:
        print(f"{kind.env_prefix}_PIN_STATUS=failed")
        print(f"{kind.env_prefix}_WARNING=missing implement tmpdir")
        return 2
    head_sha = args.head_sha or _current_head()
    pin = pin_invariant_note_from_staged if kind.is_invariant else pin_note_from_staged
    pinned = pin(
        Path(args.implement_tmpdir),
        head_sha=head_sha,
        base_ref=args.base_ref,
        repo_root=args.repo_root,
    )
    print(f"{kind.env_prefix}_PIN_STATUS={'ok' if pinned else 'skipped'}")
    return 0


pin_invariant_note_from_staged = partial(_pin_kind_note_from_staged, kind=INVARIANTS)


def _invalidate_main(argv: list[str], *, kind: AssessmentKind) -> int:
    parser = argparse.ArgumentParser(prog=f"architectural-{kind.key} invalidate")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    args = parser.parse_args(argv)
    if not args.implement_tmpdir:
        print(f"{kind.env_prefix}_INVALIDATE_STATUS=failed")
        print(f"{kind.env_prefix}_WARNING=missing implement tmpdir")
        return 2
    invalidate = invalidate_invariant_implement_note if kind.is_invariant else invalidate_implement_note
    try:
        invalidate(Path(args.implement_tmpdir))
    except OSError as exc:
        print(f"{kind.env_prefix}_INVALIDATE_STATUS=failed")
        print(f"{kind.env_prefix}_WARNING={exc}")
        return 2
    print(f"{kind.env_prefix}_INVALIDATE_STATUS=ok")
    return 0


for _guideline_cli, _invariant_cli, _handler in (
    ("append_deviation_note_main", "invariants_append_deviation_note_main", _append_deviation_note_main),
    ("persist_design_assessment_main", "invariants_persist_design_assessment_main", _persist_design_assessment_main),
    ("read_main", "invariants_read_main", _read_main),
    ("present_note_main", "invariants_present_note_main", _present_note_main),
    ("materialize_diff_main", "invariants_materialize_diff_main", _materialize_diff_main),
    ("prepare_main", "invariants_prepare_main", _prepare_main),
    ("prepare_compose_main", "invariants_prepare_compose_main", _prepare_compose_main),
    ("write_compose_assessment_main", "invariants_write_compose_assessment_main", _write_compose_assessment_main),
    ("write_staged_assessment_main", "invariants_write_staged_assessment_main", _write_staged_assessment_main),
    ("pin_note_from_staged_main", "invariants_pin_note_from_staged_main", _pin_note_from_staged_main),
    ("invalidate_main", "invariants_invalidate_main", _invalidate_main),
):
    globals()[_guideline_cli] = partial(_handler, kind=GUIDELINES)
    globals()[_invariant_cli] = partial(_handler, kind=INVARIANTS)
# pyright: reportArgumentType=false
# lint-env-via-config-constant: IMPLEMENT_TMPDIR is read in CLI entry points.
# larch-lint: allow-subprocess-run
