"""ARCHITECTURAL_GUIDELINES.md reader and implement note helpers."""
# pyright: reportUnusedCallResult=false, reportPrivateUsage=false
# pylint: disable=cyclic-import  # accepted: function-level imports of ship_guidelines (validator needs outcome constants) and run_log_flush (chunker) create mutual deps with modules that import this module at top level; documented via lint-layering ok comments.

from __future__ import annotations

import argparse
import hashlib
import json
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
from pathlib import Path, PurePosixPath
from typing import cast

from larch import io as larch_io
from larch.core import config
from larch.errors import ShipError

GUIDELINES_FILENAME = "ARCHITECTURAL_GUIDELINES.md"
INVARIANTS_FILENAME = "ARCHITECTURAL_INVARIANTS.md"
CLEAN_PRESENTATION_NOTE = "Consulted ARCHITECTURAL_GUIDELINES.md; no deviations identified."
CLEAN_INVARIANT_PRESENTATION_NOTE = "Consulted ARCHITECTURAL_INVARIANTS.md; no violations identified."
GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED = "GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED=true"
INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED = "INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED=true"
DESIGN_ASSESSMENT = "architectural-guideline-assessment.md"
INVARIANT_DESIGN_ASSESSMENT = "architectural-invariant-assessment.md"
STAGED_ASSESSMENT = "architectural-guideline-staged-assessment.md"
INVARIANT_STAGED_ASSESSMENT = "architectural-invariant-staged-assessment.md"
STAGED_ASSESSMENT_ENV = "architectural-guideline-staged-assessment.env"
INVARIANT_STAGED_ASSESSMENT_ENV = "architectural-invariant-staged-assessment.env"
MATERIALIZED_DIFF = "architectural-guideline-materialized-diff.txt"
INVARIANT_MATERIALIZED_DIFF = "architectural-invariant-materialized-diff.txt"
DURABLE_NOTE = "architectural-guideline-note.md"
INVARIANT_DURABLE_NOTE = "architectural-invariant-note.md"
DURABLE_NOTE_ENV = "architectural-guideline-note.meta.env"
INVARIANT_DURABLE_NOTE_ENV = "architectural-invariant-note.meta.env"
DROPPED_NOTE_ARTIFACT = "architectural-guideline-drop-notice.txt"
INVARIANT_DROPPED_NOTE_ARTIFACT = "architectural-invariant-drop-notice.txt"
GUIDELINE_SHIP_OUTCOME_SIDECAR = "architectural-guideline-outcome.json"
INVARIANT_SHIP_OUTCOME_SIDECAR = "architectural-invariant-outcome.json"
LEGACY_WARNING = "architectural-guideline-warnings.md"
LEGACY_WARNING_ENV = "architectural-guideline-warnings.meta.env"
MATERIALIZE_ENV = "architectural-guideline-materialize.env"
INVARIANT_MATERIALIZE_ENV = "architectural-invariant-materialize.env"
_STATUS_VALUES = {"present", "absent", "invalid"}
GUIDELINE_HEADING_RE = re.compile(r"^###\s+(G-[A-Za-z0-9-]+-\d+):\s*(.+?)\s*$", re.MULTILINE)
INVARIANT_HEADING_RE = re.compile(r"^#{1,6}\s+(I-[A-Za-z0-9-]+-\d+):\s*(.+?)\s*$", re.MULTILINE)
_MARKDOWN_HEADING_RE = re.compile(r"^#{1,6}\s+\S")
_WHY_RE = re.compile(r"^\s*-\s*Why:\s*(.+?)\s*$")
_DEVIATE_RE = re.compile(r"^\s*-\s*Deviate when:\s*(.+?)\s*$")
_MECHANIZED_RE = re.compile(r"^\s*-\s*Mechanized:\s*(.+?)\s*$")
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_EXECUTION_WARNINGS_CATEGORY = "Warnings"
_APPEND_DEVIATION_OK = "ok"
_APPEND_DEVIATION_DUPLICATE = "duplicate"
_APPEND_DEVIATION_FAILED = "failed"


def _append_guideline_entry(
    entries: list[list[str]],
    *,
    heading: str | None,
    detail: list[str],
    mechanized: str | None,
) -> None:
    if heading is None:
        return
    if mechanized is not None:
        entries.append([heading, mechanized])
        return
    entries.append([heading, *detail])


def _normalized_guideline_detail(raw_line: str) -> tuple[bool, str] | None:
    mechanized = _MECHANIZED_RE.match(raw_line)
    if mechanized:
        return True, f"- Mechanized: {mechanized.group(1).strip()}"
    why = _WHY_RE.match(raw_line)
    if why:
        return False, f"- Why: {why.group(1).strip()}"
    deviate = _DEVIATE_RE.match(raw_line)
    if deviate:
        return False, f"- Deviate when: {deviate.group(1).strip()}"
    return None


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


def validate_guideline_ship_outcome_record(data: object) -> str | None:  # noqa: C901, PLR0911, PLR0912
    from larch.implement.ship_guidelines import (  # noqa: PLC0415  # lint-layering: ok validator needs ship_guidelines constants; function-level import avoids circular import (ship_guidelines imports from this module)
        GUIDELINE_SHIP_OUTCOMES,
        GUIDELINE_SHIP_REASON_TOKENS,
        OUTCOME_CLEAN,
        OUTCOME_DROPPED,
        OUTCOME_PINNED,
        REASON_CLEAN_NOTE,
        REASON_COMPOSE_MATERIALIZATION_FAILED,
        REASON_DETERMINISTIC_CLEAN,
        REASON_UNAVAILABLE,
        REASON_GUIDELINES_ABSENT,
        REASON_GUIDELINES_INVALID,
        REASON_NOTE_PINNED,
        REASON_NOTE_READ_FAILED,
        REASON_NOTE_REDACTION_FAILED,
        REASON_UNKNOWN,
    )

    if not isinstance(data, dict):
        return "guideline outcome artifact must be a JSON object"
    d: dict[str, object] = data  # type: ignore[assignment]
    if str(d.get("schema_version") or "") != "1":
        return "guideline outcome schema_version must be 1"
    phase = str(d.get("phase") or "")
    step = str(d.get("step") or "")
    base_ref = str(d.get("base_ref") or "")
    head_sha = str(d.get("head_sha") or "")
    outcome = str(d.get("outcome") or "")
    reason = str(d.get("reason") or "")
    guidelines_status = str(d.get("guidelines_status") or "")
    assessment_kind = str(d.get("assessment_kind") or "")
    if phase != "implement":
        return "guideline outcome phase must be implement"
    if step != "8":
        return "guideline outcome step must be 8"
    if not base_ref:
        return "guideline outcome base_ref is empty"
    if not head_sha.strip():
        return "guideline outcome head_sha is empty"
    if outcome not in GUIDELINE_SHIP_OUTCOMES:
        return "guideline outcome token is unknown"
    if guidelines_status not in {"present", "absent", "invalid"}:
        return "guideline outcome guidelines_status is unknown"
    if reason not in GUIDELINE_SHIP_REASON_TOKENS:
        return "guideline outcome reason token is unknown"
    if assessment_kind not in {"", "clean", "deviation"}:
        return "guideline outcome assessment_kind is unknown"
    if guidelines_status == "absent":
        if outcome != OUTCOME_CLEAN or reason != REASON_GUIDELINES_ABSENT or assessment_kind:
            return "guideline outcome fields are inconsistent for absent guidelines"
        return None
    if guidelines_status == "invalid":
        if outcome != OUTCOME_CLEAN or reason != REASON_GUIDELINES_INVALID or assessment_kind:
            return "guideline outcome fields are inconsistent for invalid guidelines"
        return None
    if outcome == OUTCOME_CLEAN:
        if reason not in {REASON_CLEAN_NOTE, REASON_DETERMINISTIC_CLEAN} or assessment_kind != "clean":
            return "guideline outcome fields are inconsistent for clean guidelines"
        return None
    if outcome == OUTCOME_PINNED:
        if reason != REASON_NOTE_PINNED or assessment_kind != "deviation":
            return "guideline outcome fields are inconsistent for pinned guidelines"
        return None
    if outcome == OUTCOME_DROPPED:
        if assessment_kind:
            return "guideline outcome fields are inconsistent for dropped guidelines"
        if guidelines_status != "present" or reason not in {
            REASON_NOTE_READ_FAILED,
            REASON_NOTE_REDACTION_FAILED,
            REASON_COMPOSE_MATERIALIZATION_FAILED,
            REASON_UNAVAILABLE,
            REASON_UNKNOWN,
        }:
            return "guideline outcome fields are inconsistent for dropped guidelines"
        return None
    return "guideline outcome fields are inconsistent"


def validate_invariant_ship_outcome_record(data: object) -> str | None:  # noqa: C901, PLR0911, PLR0912
    """Return an error string unless data is a valid invariant Step 8 outcome."""
    if not isinstance(data, dict):
        return "invariant outcome artifact must be a JSON object"
    d: dict[str, object] = data  # type: ignore[assignment]
    if str(d.get("schema_version") or "") != "1":
        return "invariant outcome schema_version must be 1"
    phase = str(d.get("phase") or "")
    step = str(d.get("step") or "")
    base_ref = str(d.get("base_ref") or "")
    head_sha = str(d.get("head_sha") or "")
    outcome = str(d.get("outcome") or "")
    reason = str(d.get("reason") or "")
    invariants_status = str(d.get("invariants_status") or "")
    assessment_kind = str(d.get("assessment_kind") or "")
    if phase != "implement":
        return "invariant outcome phase must be implement"
    if step != "8":
        return "invariant outcome step must be 8"
    if not base_ref:
        return "invariant outcome base_ref is empty"
    if not head_sha.strip():
        return "invariant outcome head_sha is empty"
    if outcome not in {"clean", "violation", "dropped"}:
        return "invariant outcome token is unknown"
    if invariants_status not in {"present", "absent", "invalid"}:
        return "invariant outcome invariants_status is unknown"
    if assessment_kind not in {"", "clean", "violation"}:
        return "invariant outcome assessment_kind is unknown"
    if invariants_status in {"absent", "invalid"}:
        expected_reason = "invariants-absent" if invariants_status == "absent" else "invariants-invalid"
        if outcome != "clean" or reason != expected_reason or assessment_kind:
            return f"invariant outcome fields are inconsistent for {invariants_status} invariants"
        return None
    if outcome == "clean":
        if reason not in {"clean-note", "invariants-empty", config.REASON_DETERMINISTIC_CLEAN} or assessment_kind != "clean":
            return "invariant outcome fields are inconsistent for clean invariants"
        return None
    if outcome == "violation":
        if reason != "violation-note" or assessment_kind != "violation":
            return "invariant outcome fields are inconsistent for invariant violations"
        return None
    if outcome == "dropped":
        if assessment_kind or reason not in {
            "note-read-failed",
            "note-redaction-failed",
            "compose-materialization-failed",
            config.REASON_UNAVAILABLE,
            "unknown",
        }:
            return "invariant outcome fields are inconsistent for dropped invariants"
        return None
    return "invariant outcome fields are inconsistent"


def _run_git_toplevel(candidate: Path) -> Path | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(candidate), "rev-parse", "--show-toplevel"],  # noqa: S607
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    text = completed.stdout.strip()
    if not text:
        return None
    try:
        return Path(text).resolve()
    except OSError:
        return None


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


def parse_guideline_entries(raw_text: str) -> str:
    """Return normalized G-* entries for prompt consumption.

    Guidance and other bullets are intentionally omitted from the normalized
    architectural knowledge snapshot. Mechanized entries retain only the
    heading and the mechanization marker.
    """
    entries: list[list[str]] = []
    current_heading: str | None = None
    current_detail: list[str] = []
    current_mechanized: str | None = None

    for raw_line in raw_text.splitlines():
        heading = GUIDELINE_HEADING_RE.match(raw_line)
        if heading:
            _append_guideline_entry(entries, heading=current_heading, detail=current_detail, mechanized=current_mechanized)
            current_heading = f"### {heading.group(1)}: {heading.group(2).strip()}"
            current_detail = []
            current_mechanized = None
            continue
        if _MARKDOWN_HEADING_RE.match(raw_line):
            _append_guideline_entry(entries, heading=current_heading, detail=current_detail, mechanized=current_mechanized)
            current_heading = None
            current_detail = []
            current_mechanized = None
            continue
        if current_heading is None:
            continue
        normalized_detail = _normalized_guideline_detail(raw_line)
        if normalized_detail is None:
            continue
        is_mechanized, line = normalized_detail
        if is_mechanized:
            current_mechanized = line
        else:
            current_detail.append(line)
    _append_guideline_entry(entries, heading=current_heading, detail=current_detail, mechanized=current_mechanized)
    return "\n\n".join("\n".join(entry) for entry in entries).strip()


def parse_invariant_entries(raw_text: str) -> str:
    """Return normalized I-* invariant headings with verbatim entry bodies.

    Each I-* Markdown heading is normalized to ``### <id>: <title>``. Body
    lines are retained verbatim until the next Markdown heading, with only
    leading and trailing blank body lines trimmed per entry.
    """
    entries: list[list[str]] = []
    current_heading: str | None = None
    current_body: list[str] = []

    def append_current_entry() -> None:
        nonlocal current_heading, current_body
        if current_heading is None:
            return
        trimmed_body: list[str] = current_body[:]
        while trimmed_body and trimmed_body[0].strip() == "":
            del trimmed_body[0]
        while trimmed_body and trimmed_body[-1].strip() == "":
            trimmed_body.pop()
        entries.append([current_heading, *trimmed_body])
        current_heading = None
        current_body = []

    for raw_line in raw_text.splitlines():
        heading = INVARIANT_HEADING_RE.match(raw_line)
        if heading:
            append_current_entry()
            current_heading = f"### {heading.group(1)}: {heading.group(2).strip()}"
            continue
        if _MARKDOWN_HEADING_RE.match(raw_line):
            append_current_entry()
            continue
        if current_heading is None:
            continue
        current_body.append(raw_line)
    append_current_entry()
    return "\n\n".join("\n".join(entry) for entry in entries).strip()


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


def _validate_guidelines_file(*, root: Path, path: Path) -> str | None:
    """Return an invalid-reason for a present guidelines path, or None when readable."""
    return _validate_architectural_file(root=root, path=path, filename=GUIDELINES_FILENAME)


def read_guidelines(*, repo_root: str | Path | None = None) -> ArchitecturalGuidelinesResult:
    """Read and normalize ARCHITECTURAL_GUIDELINES.md for the active repo."""
    root = _resolve_repo_root(repo_root)
    if root is None:
        return ArchitecturalGuidelinesResult("absent", None, None, "")
    path = root / GUIDELINES_FILENAME
    if not path.exists() and not path.is_symlink():
        return ArchitecturalGuidelinesResult("absent", root, path, "")
    warning = _validate_guidelines_file(root=root, path=path)
    if warning is not None:
        return _invalid(repo_root=root, path=path, warning=warning)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _invalid(repo_root=root, path=path, warning=f"{GUIDELINES_FILENAME} is invalid: unreadable file ({exc})")
    return ArchitecturalGuidelinesResult("present", root, path.resolve(strict=False), parse_guideline_entries(raw_text), "")


def read_invariants(*, repo_root: str | Path | None = None) -> ArchitecturalGuidelinesResult:
    """Read and normalize ARCHITECTURAL_INVARIANTS.md for the active repo."""
    root = _resolve_repo_root(repo_root)
    if root is None:
        return ArchitecturalGuidelinesResult("absent", None, None, "")
    path = root / INVARIANTS_FILENAME
    if not path.exists() and not path.is_symlink():
        return ArchitecturalGuidelinesResult("absent", root, path, "")
    warning = _validate_architectural_file(root=root, path=path, filename=INVARIANTS_FILENAME)
    if warning is not None:
        return _invalid(repo_root=root, path=path, warning=warning)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _invalid(repo_root=root, path=path, warning=f"{INVARIANTS_FILENAME} is invalid: unreadable file ({exc})")
    return ArchitecturalGuidelinesResult("present", root, path.resolve(strict=False), parse_invariant_entries(raw_text), "")


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


def staged_assessment_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / STAGED_ASSESSMENT


def invariant_staged_assessment_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / INVARIANT_STAGED_ASSESSMENT


def durable_note_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / DURABLE_NOTE


def invariant_durable_note_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / INVARIANT_DURABLE_NOTE


def design_assessment_path(design_tmpdir: Path) -> Path:
    return design_tmpdir / DESIGN_ASSESSMENT


def invariant_design_assessment_path(design_tmpdir: Path) -> Path:
    return design_tmpdir / INVARIANT_DESIGN_ASSESSMENT


def dropped_note_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / DROPPED_NOTE_ARTIFACT


def invariant_dropped_note_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / INVARIANT_DROPPED_NOTE_ARTIFACT


def guideline_ship_outcome_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / GUIDELINE_SHIP_OUTCOME_SIDECAR


def invariant_ship_outcome_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / INVARIANT_SHIP_OUTCOME_SIDECAR


def _validate_design_tmpdir_arg(candidate: str) -> Path:
    from larch.state import session_env  # noqa: PLC0415  # lint-layering: ok validate-design-tmpdir must stay co-located with arg-parsing logic.
    ok, message = session_env.validate_design_tmpdir(candidate)
    if not ok:
        raise ValueError(message)
    if Path(candidate).is_symlink():
        raise ValueError("design-tmpdir: path must not be a symlink")
    return Path(candidate).resolve(strict=False)


def _sidecar_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / STAGED_ASSESSMENT_ENV


def _invariant_sidecar_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / INVARIANT_STAGED_ASSESSMENT_ENV


def _durable_meta_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / DURABLE_NOTE_ENV


def _invariant_durable_meta_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / INVARIANT_DURABLE_NOTE_ENV


def _diff_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / MATERIALIZED_DIFF


def _invariant_diff_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / INVARIANT_MATERIALIZED_DIFF


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


def _write_design_assessment_atomic(*, design_tmpdir: Path, text: str) -> None:
    design_tmpdir.mkdir(parents=True, exist_ok=True)
    path = design_assessment_path(design_tmpdir)
    tmp = path.with_name(path.name + ".tmp")
    if path.is_symlink():
        raise OSError(f"{DESIGN_ASSESSMENT}: target must not be a symlink")
    if path.exists() and not path.is_file():
        raise OSError(f"{DESIGN_ASSESSMENT}: target must be a regular file")
    if tmp.is_symlink():
        raise OSError(f"{tmp.name}: temp path must not be a symlink")
    if tmp.exists() and not tmp.is_file():
        raise OSError(f"{tmp.name}: temp path must be a regular file")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _write_invariant_design_assessment_atomic(*, design_tmpdir: Path, text: str) -> None:
    design_tmpdir.mkdir(parents=True, exist_ok=True)
    path = invariant_design_assessment_path(design_tmpdir)
    tmp = path.with_name(path.name + ".tmp")
    if path.is_symlink():
        raise OSError(f"{INVARIANT_DESIGN_ASSESSMENT}: target must not be a symlink")
    if path.exists() and not path.is_file():
        raise OSError(f"{INVARIANT_DESIGN_ASSESSMENT}: target must be a regular file")
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
    except (OSError, UnicodeDecodeError):
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
    sidecar = _sidecar_path(implement_tmpdir)
    if not _regular_file(staged) or not _regular_file(sidecar):
        return False
    return _read_env(sidecar).get("STATUS") == "present"


def durable_note_present(implement_tmpdir: Path) -> bool:
    note = durable_note_path(implement_tmpdir)
    meta = _durable_meta_path(implement_tmpdir)
    if not _regular_file(note) or not _regular_file(meta):
        return False
    return _read_env(meta).get("STATUS") == "present"


def invariant_durable_note_present(implement_tmpdir: Path) -> bool:
    note = invariant_durable_note_path(implement_tmpdir)
    meta = _invariant_durable_meta_path(implement_tmpdir)
    if not _regular_file(note) or not _regular_file(meta):
        return False
    return _read_env(meta).get("STATUS") == "present"


def note_readable_any_head(implement_tmpdir: Path) -> bool:
    """Return true when a present durable note is readable regardless of HEAD."""
    return durable_note_present(implement_tmpdir)


def invariant_note_readable_any_head(implement_tmpdir: Path) -> bool:
    """Return true when a present invariant durable note is readable regardless of HEAD."""
    return invariant_durable_note_present(implement_tmpdir)


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


def clear_staged_and_dropped_artifacts(implement_tmpdir: Path) -> None:
    """Clear retired staged-assessment and drop-notice artifacts."""
    for name in (
        LEGACY_WARNING,
        LEGACY_WARNING_ENV,
        STAGED_ASSESSMENT,
        STAGED_ASSESSMENT_ENV,
        DROPPED_NOTE_ARTIFACT,
        GUIDELINE_SHIP_OUTCOME_SIDECAR,
    ):
        path = implement_tmpdir / name
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            elif _artifact_still_present(path):
                path.unlink()
        except OSError:
            pass


def clear_invariant_staged_and_dropped_artifacts(implement_tmpdir: Path) -> None:
    """Clear retired invariant staged-assessment and drop-notice artifacts."""
    for name in (
        INVARIANT_STAGED_ASSESSMENT,
        INVARIANT_STAGED_ASSESSMENT_ENV,
        INVARIANT_DROPPED_NOTE_ARTIFACT,
        INVARIANT_SHIP_OUTCOME_SIDECAR,
    ):
        path = implement_tmpdir / name
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            elif _artifact_still_present(path):
                path.unlink()
        except OSError:
            pass


def write_staged_assessment(  # noqa: PLR0913 - cohesive Phase A artifact writer; bundling its pin-metadata fields would churn 14 call sites
    *, implement_tmpdir: Path,
    assessment_text: str,
    assessed_head_sha: str,
    diff_fingerprint_value: str,
    base_ref: str,
    diff_text: str = "",
) -> None:
    """Persist orchestrator-authored Phase A assessment artifacts."""
    implement_tmpdir.mkdir(parents=True, exist_ok=True)
    _write_text_atomic(path=staged_assessment_path(implement_tmpdir), text=assessment_text)
    _write_text_atomic(path=_diff_path(implement_tmpdir), text=diff_text)
    written_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    sidecar = "\n".join(
        [
            "STATUS=present",
            f"ASSESSED_HEAD_SHA={_env_escape(assessed_head_sha)}",
            f"DIFF_FINGERPRINT={_env_escape(diff_fingerprint_value)}",
            f"BASE_REF={_env_escape(base_ref)}",
            f"DIFF_SNAPSHOT={_env_escape(str(_diff_path(implement_tmpdir)))}",
            f"WRITTEN_AT={written_at}",
            "",
        ]
    )
    _write_text_atomic(path=_sidecar_path(implement_tmpdir), text=sidecar)


def write_invariant_staged_assessment(  # noqa: PLR0913 - mirrors guideline artifact writer
    *, implement_tmpdir: Path,
    assessment_text: str,
    assessed_head_sha: str,
    diff_fingerprint_value: str,
    base_ref: str,
    diff_text: str = "",
) -> None:
    """Persist orchestrator-authored invariant assessment artifacts."""
    implement_tmpdir.mkdir(parents=True, exist_ok=True)
    _write_text_atomic(path=invariant_staged_assessment_path(implement_tmpdir), text=assessment_text)
    _write_text_atomic(path=_invariant_diff_path(implement_tmpdir), text=diff_text)
    written_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    sidecar = "\n".join(
        [
            "STATUS=present",
            f"ASSESSED_HEAD_SHA={_env_escape(assessed_head_sha)}",
            f"DIFF_FINGERPRINT={_env_escape(diff_fingerprint_value)}",
            f"BASE_REF={_env_escape(base_ref)}",
            f"DIFF_SNAPSHOT={_env_escape(str(_invariant_diff_path(implement_tmpdir)))}",
            "INVARIANTS_STATUS=present",
            f"ASSESSMENT_KIND={_env_escape(_invariant_assessment_kind(assessment_text))}",
            f"WRITTEN_AT={written_at}",
            "",
        ]
    )
    _write_text_atomic(path=_invariant_sidecar_path(implement_tmpdir), text=sidecar)


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


def write_implement_note(*, implement_tmpdir: Path, note_text: str, head_sha: str, metadata: dict[str, str], base_ref: str) -> None:
    """Write the durable compose-time note and HEAD-pinned metadata."""
    _write_text_atomic(path=durable_note_path(implement_tmpdir), text=note_text)
    _write_text_atomic(
        path=_durable_meta_path(implement_tmpdir),
        text=_durable_metadata_text(
            head_sha=head_sha,
            metadata=metadata,
            base_ref=base_ref,
            status_key="GUIDELINES_STATUS",
            status_default="present",
        ),
    )
    clear_staged_and_dropped_artifacts(implement_tmpdir)


def write_invariant_implement_note(*, implement_tmpdir: Path, note_text: str, head_sha: str, metadata: dict[str, str], base_ref: str) -> None:
    """Write the durable invariant compose-time note and HEAD-pinned metadata."""
    _write_text_atomic(path=invariant_durable_note_path(implement_tmpdir), text=note_text)
    _write_text_atomic(
        path=_invariant_durable_meta_path(implement_tmpdir),
        text=_durable_metadata_text(
            head_sha=head_sha,
            metadata=metadata,
            base_ref=base_ref,
            status_key="INVARIANTS_STATUS",
            status_default="present",
        ),
    )
    clear_invariant_staged_and_dropped_artifacts(implement_tmpdir)


def write_deterministic_clean_note(
    *,
    implement_tmpdir: Path,
    head_sha: str,
    base_ref: str,
    diff_text: str,
    invariant: bool = False,
) -> None:
    """Persist a deterministic clean note backed by validated diff evidence."""
    fingerprint = diff_fingerprint(diff_text)
    diff_path = _invariant_diff_path(implement_tmpdir) if invariant else _diff_path(implement_tmpdir)
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
    writer = write_invariant_implement_note if invariant else write_implement_note
    writer(
        implement_tmpdir=implement_tmpdir,
        note_text=CLEAN_INVARIANT_PRESENTATION_NOTE if invariant else CLEAN_PRESENTATION_NOTE,
        head_sha=head_sha,
        metadata=metadata,
        base_ref=base_ref,
    )


def write_unavailable_note(
    *,
    implement_tmpdir: Path,
    head_sha: str,
    base_ref: str,
    invariant: bool = False,
) -> None:
    """Persist a non-violating note when assessment input is unavailable."""
    if invariant:
        existing_metadata = invariant_durable_note_metadata(implement_tmpdir)
        existing_note_path = invariant_durable_note_path(implement_tmpdir)
        if (
            existing_metadata.get("NOTE_STATE", config.NOTE_STATE_AUTHORED) == config.NOTE_STATE_AUTHORED
            and _regular_file(existing_note_path)
        ):
            try:
                existing_note = _read_regular_text_no_follow(existing_note_path)
            except (OSError, UnicodeDecodeError):
                existing_note = ""
            if _invariant_assessment_kind(existing_note) == "violation":
                return
    metadata = {"NOTE_STATE": config.NOTE_STATE_UNAVAILABLE, "ASSESSMENT_KIND": ""}
    writer = write_invariant_implement_note if invariant else write_implement_note
    writer(
        implement_tmpdir=implement_tmpdir,
        note_text="Architectural assessment unavailable.",
        head_sha=head_sha,
        metadata=metadata,
        base_ref=base_ref,
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


def _staged_fingerprint_valid(
    *, implement_tmpdir: Path,
    metadata: dict[str, str],
    base_ref: str,
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
    diff_path = _diff_path(implement_tmpdir)
    if diff_path.is_file() and not diff_path.is_symlink():
        try:
            snapshot_text = diff_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False
        return diff_fingerprint(snapshot_text) == stored_fp
    return False


def _invariant_staged_fingerprint_valid(
    *, implement_tmpdir: Path,
    metadata: dict[str, str],
    base_ref: str,
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
    diff_path = _invariant_diff_path(implement_tmpdir)
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
    sidecar = _sidecar_path(implement_tmpdir)
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
            diff_text=diff_text,
        )
    except (OSError, UnicodeDecodeError):
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
    sidecar = _sidecar_path(implement_tmpdir)
    try:
        assessment_text = _read_regular_text_no_follow(staged)
        diff_text, fingerprint = live_diff
        write_staged_assessment(
            implement_tmpdir=implement_tmpdir,
            assessment_text=assessment_text,
            assessed_head_sha=head_sha,
            diff_fingerprint_value=fingerprint,
            base_ref=resolved_base,
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
    except (OSError, UnicodeDecodeError):
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
    sidecar = _sidecar_path(implement_tmpdir)
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


def pin_note_from_staged(
    implement_tmpdir: Path,
    *,
    head_sha: str,
    base_ref: str = "",
    repo_root: str | Path | None = None,
) -> bool:
    """Copy the staged assessment into a durable note pinned to head_sha."""
    staged = staged_assessment_path(implement_tmpdir)
    sidecar = _sidecar_path(implement_tmpdir)
    if not staged.is_file() or staged.is_symlink() or not sidecar.is_file() or sidecar.is_symlink():
        return False
    metadata = _read_env(sidecar)
    if metadata.get("STATUS") != "present":
        return False
    if not _staged_fingerprint_valid(
        implement_tmpdir=implement_tmpdir,
        metadata=metadata,
        base_ref=base_ref,
        repo_root=Path(repo_root).resolve() if repo_root is not None else None,
    ):
        return False
    try:
        note_text = staged.read_text(encoding="utf-8")
    except OSError:
        return False
    try:
        write_implement_note(implement_tmpdir=implement_tmpdir, note_text=note_text, head_sha=head_sha, metadata=metadata, base_ref=base_ref)
    except OSError:
        return False
    return True


_INVALIDATE_ARTIFACTS = (
    LEGACY_WARNING,
    LEGACY_WARNING_ENV,
    STAGED_ASSESSMENT,
    STAGED_ASSESSMENT_ENV,
    DURABLE_NOTE,
    DURABLE_NOTE_ENV,
    DROPPED_NOTE_ARTIFACT,
    GUIDELINE_SHIP_OUTCOME_SIDECAR,
)


_INVARIANT_INVALIDATE_ARTIFACTS = (
    INVARIANT_STAGED_ASSESSMENT,
    INVARIANT_STAGED_ASSESSMENT_ENV,
    INVARIANT_DURABLE_NOTE,
    INVARIANT_DURABLE_NOTE_ENV,
    INVARIANT_DROPPED_NOTE_ARTIFACT,
    INVARIANT_SHIP_OUTCOME_SIDECAR,
)


def _artifact_still_present(path: Path) -> bool:
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False


def invalidate_implement_note(implement_tmpdir: Path) -> None:
    """Clear staged and durable guideline note artifacts."""
    for name in _INVALIDATE_ARTIFACTS:
        path = implement_tmpdir / name
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            elif _artifact_still_present(path):
                path.unlink()
        except FileNotFoundError:
            pass
    surviving = [name for name in _INVALIDATE_ARTIFACTS if _artifact_still_present(implement_tmpdir / name)]
    if surviving:
        raise OSError("artifact(s) survived invalidation: " + ", ".join(surviving))


def invalidate_invariant_implement_note(implement_tmpdir: Path) -> None:
    """Clear staged and durable invariant note artifacts."""
    for name in _INVARIANT_INVALIDATE_ARTIFACTS:
        path = implement_tmpdir / name
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            elif _artifact_still_present(path):
                path.unlink()
        except FileNotFoundError:
            pass
    surviving = [name for name in _INVARIANT_INVALIDATE_ARTIFACTS if _artifact_still_present(implement_tmpdir / name)]
    if surviving:
        raise OSError("artifact(s) survived invalidation: " + ", ".join(surviving))


def durable_note_metadata(implement_tmpdir: Path) -> dict[str, str]:
    """Return durable-note sidecar metadata when present."""
    return _read_env(_durable_meta_path(implement_tmpdir))


def invariant_durable_note_metadata(implement_tmpdir: Path) -> dict[str, str]:
    """Return invariant durable-note sidecar metadata when present."""
    return _read_env(_invariant_durable_meta_path(implement_tmpdir))


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


def _validated_note_metadata(  # noqa: PLR0911 - fail-closed metadata validator has distinct early exits per invariant check
    *,
    metadata: dict[str, str],
    expected_snapshot: Path,
) -> tuple[str, str, str, str] | None:
    if metadata.get("STATUS") != "present":
        return None
    identity = _note_identity(metadata)
    if identity is None:
        return None
    note_state, authored_fingerprint, covered_fingerprint = identity
    base_ref = metadata.get("BASE_REF", "").strip()
    if note_state == config.NOTE_STATE_UNAVAILABLE:
        return note_state, authored_fingerprint, covered_fingerprint, base_ref
    declared_snapshot = metadata.get("DIFF_SNAPSHOT", "")
    prior_format = not metadata.get("NOTE_STATE") and not metadata.get("AUTHORED_DIFF_FINGERPRINT") and not metadata.get("COVERED_DIFF_FINGERPRINT")
    if prior_format:
        return note_state, authored_fingerprint, covered_fingerprint, base_ref
    if not declared_snapshot or Path(declared_snapshot) != expected_snapshot:
        return None
    if not _snapshot_matches(snapshot_path=expected_snapshot, covered_fingerprint=covered_fingerprint):
        return None
    return note_state, authored_fingerprint, covered_fingerprint, base_ref


def _advance_note_coverage(  # noqa: C901, PLR0911, PLR0912, PLR0913, PLR0915 - fail-closed coverage advancement validates each independent safety boundary
    *,
    implement_tmpdir: Path,
    metadata: dict[str, str],
    head_sha: str,
    base_ref: str,
    repo_root: Path,
    invariant: bool,
) -> bool:
    stored_head = metadata.get("HEAD_SHA", "").strip()
    identity = _note_identity(metadata)
    if identity is None:
        return False
    note_state, authored_fingerprint, covered_fingerprint = identity
    if note_state == config.NOTE_STATE_UNAVAILABLE:
        return False
    snapshot_path = _invariant_diff_path(implement_tmpdir) if invariant else _diff_path(implement_tmpdir)
    if not _valid_commit(repo_root=repo_root, revision=stored_head):
        return False
    remote, ref = base_ref.split("/", 1) if "/" in base_ref else ("origin", base_ref)
    try:
        stored_diff = _materialize_implementation_diff_for_head(
            repo_root,
            head_sha=stored_head,
            base_remote=remote,
            base_ref=ref,
        )
    except (OSError, RuntimeError):
        return False
    if diff_fingerprint(stored_diff) != covered_fingerprint or not _snapshot_matches(
        snapshot_path=snapshot_path,
        covered_fingerprint=covered_fingerprint,
    ):
        return False
    if not _incremental_paths_out_of_scope(repo_root=repo_root, old_head=stored_head, new_head=head_sha):
        return False
    if _current_head(repo_root, verify_commit=True) != head_sha:
        return False
    live_diff = _materialize_live_diff(repo_root=repo_root, resolved_base=base_ref)
    if live_diff is None or _current_head(repo_root, verify_commit=True) != head_sha:
        return False
    diff_text, covered_fingerprint = live_diff
    refreshed = dict(metadata)
    refreshed["NOTE_STATE"] = note_state
    refreshed["AUTHORED_DIFF_FINGERPRINT"] = authored_fingerprint
    refreshed["COVERED_DIFF_FINGERPRINT"] = covered_fingerprint
    refreshed["DIFF_FINGERPRINT"] = covered_fingerprint
    refreshed["DIFF_SNAPSHOT"] = str(snapshot_path)
    meta_path = _invariant_durable_meta_path(implement_tmpdir) if invariant else _durable_meta_path(implement_tmpdir)
    status_key = "INVARIANTS_STATUS" if invariant else "GUIDELINES_STATUS"
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
            return False
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
            return False
    except (OSError, UnicodeDecodeError):
        return False
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
    base_ref: str,
    repo_root: str | Path | None,
    invariant: bool,
) -> bool:
    note_path = invariant_durable_note_path(implement_tmpdir) if invariant else durable_note_path(implement_tmpdir)
    meta_path = _invariant_durable_meta_path(implement_tmpdir) if invariant else _durable_meta_path(implement_tmpdir)
    snapshot_path = _invariant_diff_path(implement_tmpdir) if invariant else _diff_path(implement_tmpdir)
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
            invariant=invariant,
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


def note_consumable(
    *,
    implement_tmpdir: Path,
    head_sha: str,
    base_ref: str = "",
    repo_root: str | Path | None = None,
) -> bool:
    """Return true when the durable note is safe to surface for head_sha."""
    return _note_consumable(
        implement_tmpdir=implement_tmpdir,
        head_sha=head_sha,
        base_ref=base_ref,
        repo_root=repo_root,
        invariant=False,
    )


def invariant_note_consumable(
    *,
    implement_tmpdir: Path,
    head_sha: str,
    base_ref: str = "",
    repo_root: str | Path | None = None,
) -> bool:
    """Return true when the durable invariant note is safe to surface for head_sha."""
    return _note_consumable(
        implement_tmpdir=implement_tmpdir,
        head_sha=head_sha,
        base_ref=base_ref,
        repo_root=repo_root,
        invariant=True,
    )


def _note_fingerprint_stale(
    *,
    implement_tmpdir: Path,
    base_ref: str,
    repo_root: str | Path | None,
    invariant: bool,
) -> bool:
    meta_path = _invariant_durable_meta_path(implement_tmpdir) if invariant else _durable_meta_path(implement_tmpdir)
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


def note_fingerprint_stale(
    implement_tmpdir: Path,
    *,
    base_ref: str,
    repo_root: str | Path | None = None,
) -> bool:
    """Return true when the durable note fingerprint no longer matches the live diff."""
    return _note_fingerprint_stale(
        implement_tmpdir=implement_tmpdir,
        base_ref=base_ref,
        repo_root=repo_root,
        invariant=False,
    )


def invariant_note_fingerprint_stale(
    implement_tmpdir: Path,
    *,
    base_ref: str,
    repo_root: str | Path | None = None,
) -> bool:
    """Return true when the durable invariant note fingerprint no longer matches the live diff."""
    return _note_fingerprint_stale(
        implement_tmpdir=implement_tmpdir,
        base_ref=base_ref,
        repo_root=repo_root,
        invariant=True,
    )


def clear_guideline_ship_outcome(implement_tmpdir: Path) -> None:
    path = guideline_ship_outcome_path(implement_tmpdir)
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif _artifact_still_present(path):
            path.unlink()
    except OSError:
        pass


def clear_invariant_ship_outcome(implement_tmpdir: Path) -> None:
    path = invariant_ship_outcome_path(implement_tmpdir)
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif _artifact_still_present(path):
            path.unlink()
    except OSError:
        pass


def _write_compose_materialization_metadata(
    *,
    implement_tmpdir: Path,
    materialized: ComposeMaterializationResult,
) -> None:
    written_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    diff_path = materialized.diff_path or _diff_path(implement_tmpdir)
    _write_text_atomic(
        path=implement_tmpdir / MATERIALIZE_ENV,
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
                f"GUIDELINES_STATUS={_env_escape(materialized.guidelines_status)}",
                f"GUIDELINES_PATH={_env_escape(materialized.guidelines_path)}",
                f"ASSESSMENT_KIND={_env_escape(materialized.assessment_kind)}",
                f"WRITTEN_AT={written_at}",
                "",
            ]
        ),
    )


def _invariant_assessment_kind(note: str) -> str:
    if not note.strip():
        return ""
    if note.rstrip("\n") == CLEAN_INVARIANT_PRESENTATION_NOTE:
        return "clean"
    return "violation"


def _write_invariant_compose_materialization_metadata(
    *,
    implement_tmpdir: Path,
    materialized: ComposeMaterializationResult,
) -> None:
    written_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    diff_path = materialized.diff_path or _invariant_diff_path(implement_tmpdir)
    _write_text_atomic(
        path=implement_tmpdir / INVARIANT_MATERIALIZE_ENV,
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
                f"INVARIANTS_STATUS={_env_escape(materialized.guidelines_status)}",
                f"INVARIANTS_PATH={_env_escape(materialized.guidelines_path)}",
                f"ASSESSMENT_KIND={_env_escape(materialized.assessment_kind)}",
                f"WRITTEN_AT={written_at}",
                "",
            ]
        ),
    )


def _compose_precheck_result(
    *,
    implement_tmpdir: Path,
    root: Path | None,
    current_head: str,
    expected_head_sha: str,
) -> tuple[ArchitecturalGuidelinesResult | None, ComposeMaterializationResult | None]:
    if expected_head_sha and current_head and expected_head_sha != current_head:
        return None, ComposeMaterializationResult(
            status="failed",
            head_sha=current_head,
            warning="HEAD changed before architectural-guidelines compose materialization",
        )
    if current_head and note_consumable(
        implement_tmpdir=implement_tmpdir,
        head_sha=current_head,
        repo_root=root,
        base_ref=durable_note_metadata(implement_tmpdir).get("BASE_REF", ""),
    ):
        if root is None:
            return None, ComposeMaterializationResult(status="current", head_sha=current_head)
        metadata = durable_note_metadata(implement_tmpdir)
        stored_base_ref = metadata.get("BASE_REF", "")
        if stored_base_ref and not note_fingerprint_stale(
            implement_tmpdir,
            base_ref=stored_base_ref,
            repo_root=root,
        ):
            return None, ComposeMaterializationResult(status="current", head_sha=current_head)
    result = read_guidelines(repo_root=root)
    if result.status in {"absent", "invalid"}:
        return None, ComposeMaterializationResult(
            status=result.status,
            head_sha=current_head,
            guidelines_status=result.status,
            warning=result.warning if result.status == "invalid" else "",
        )
    if root is None:
        return None, ComposeMaterializationResult(
            status="failed",
            head_sha=current_head,
            guidelines_status=result.status,
            warning="could not resolve repo root",
        )
    return result, None


def prepare_compose_assessment(
    *,
    implement_tmpdir: Path,
    repo_root: str | Path | None = None,
    forked_target: bool = False,
    expected_head_sha: str = "",
    compose_snapshot_factory: Callable[[], ComposeAssessmentSnapshot] | None = None,
) -> ComposeMaterializationResult:
    """Prepare Step 8 compose-time evidence for prompt-authored assessment."""
    implement_tmpdir.mkdir(parents=True, exist_ok=True)
    clear_staged_and_dropped_artifacts(implement_tmpdir)
    root = _resolve_repo_root(repo_root)
    current_head = _current_head(root, verify_commit=True) if root is not None else ""
    result, precheck = _compose_precheck_result(
        implement_tmpdir=implement_tmpdir,
        root=root,
        current_head=current_head,
        expected_head_sha=expected_head_sha,
    )
    if precheck is not None:
        return precheck
    if result is None:
        return ComposeMaterializationResult(status="failed", head_sha=current_head, warning="guidelines precheck failed")
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
            warning="HEAD changed before architectural-guidelines compose materialization",
        )
    materialized = ComposeMaterializationResult(
        status="assessment-required",
        head_sha=materialized_snapshot.head_sha,
        base_ref=materialized_snapshot.base_ref,
        diff_fingerprint=materialized_snapshot.diff_fingerprint,
        diff_path=_diff_path(implement_tmpdir),
        guidelines_status=result.status,
        guidelines_path=str(result.path or ""),
    )
    try:
        _write_text_atomic(
            path=_diff_path(implement_tmpdir),
            text=materialized_snapshot.diff_text,
        )
        _write_compose_materialization_metadata(
            implement_tmpdir=implement_tmpdir,
            materialized=materialized,
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


def _invariant_compose_precheck_result(  # noqa: PLR0911 - fail-closed precheck mirrors guideline gate exits.
    *,
    implement_tmpdir: Path,
    root: Path | None,
    current_head: str,
    expected_head_sha: str,
) -> tuple[ArchitecturalGuidelinesResult | None, ComposeMaterializationResult | None]:
    if expected_head_sha and current_head and expected_head_sha != current_head:
        return None, ComposeMaterializationResult(
            status="failed",
            head_sha=current_head,
            warning="HEAD changed before architectural-invariants compose materialization",
        )
    if current_head and invariant_note_consumable(
        implement_tmpdir=implement_tmpdir,
        head_sha=current_head,
        repo_root=root,
        base_ref=invariant_durable_note_metadata(implement_tmpdir).get("BASE_REF", ""),
    ):
        if root is None:
            return None, ComposeMaterializationResult(status="current", head_sha=current_head)
        metadata = invariant_durable_note_metadata(implement_tmpdir)
        stored_base_ref = metadata.get("BASE_REF", "")
        if stored_base_ref and not invariant_note_fingerprint_stale(
            implement_tmpdir,
            base_ref=stored_base_ref,
            repo_root=root,
        ):
            return None, ComposeMaterializationResult(status="current", head_sha=current_head)
    result = read_invariants(repo_root=root)
    if result.status in {"absent", "invalid"}:
        return None, ComposeMaterializationResult(
            status=result.status,
            head_sha=current_head,
            guidelines_status=result.status,
            warning=result.warning if result.status == "invalid" else "",
        )
    if not result.content.strip():
        return None, ComposeMaterializationResult(
            status="present-empty",
            head_sha=current_head,
            guidelines_status=result.status,
            guidelines_path=str(result.path or ""),
            assessment_kind="clean",
        )
    if root is None:
        return None, ComposeMaterializationResult(
            status="failed",
            head_sha=current_head,
            guidelines_status=result.status,
            warning="could not resolve repo root",
        )
    return result, None


def prepare_invariant_compose_assessment(
    *,
    implement_tmpdir: Path,
    repo_root: str | Path | None = None,
    forked_target: bool = False,
    expected_head_sha: str = "",
    compose_snapshot_factory: Callable[[], ComposeAssessmentSnapshot] | None = None,
) -> ComposeMaterializationResult:
    """Prepare Step 8 compose-time invariant evidence for prompt-authored assessment."""
    implement_tmpdir.mkdir(parents=True, exist_ok=True)
    clear_invariant_staged_and_dropped_artifacts(implement_tmpdir)
    root = _resolve_repo_root(repo_root)
    current_head = _current_head(root, verify_commit=True) if root is not None else ""
    result, precheck = _invariant_compose_precheck_result(
        implement_tmpdir=implement_tmpdir,
        root=root,
        current_head=current_head,
        expected_head_sha=expected_head_sha,
    )
    if precheck is not None:
        return precheck
    if result is None:
        return ComposeMaterializationResult(status="failed", head_sha=current_head, warning="invariants precheck failed")
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
            warning="HEAD changed before architectural-invariants compose materialization",
        )
    materialized = ComposeMaterializationResult(
        status="assessment-required",
        head_sha=materialized_snapshot.head_sha,
        base_ref=materialized_snapshot.base_ref,
        diff_fingerprint=materialized_snapshot.diff_fingerprint,
        diff_path=_invariant_diff_path(implement_tmpdir),
        guidelines_status=result.status,
        guidelines_path=str(result.path or ""),
    )
    try:
        _write_text_atomic(
            path=_invariant_diff_path(implement_tmpdir),
            text=materialized_snapshot.diff_text,
        )
        _write_invariant_compose_materialization_metadata(
            implement_tmpdir=implement_tmpdir,
            materialized=materialized,
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


def write_compose_assessment(
    *,
    implement_tmpdir: Path,
    assessment_text: str,
    repo_root: str | Path | None = None,
) -> None:
    """Write a prompt-authored compose-time assessment as the durable note."""
    normalized = _normalize_assessment_text(assessment_text)
    if not normalized.strip():
        raise ValueError("assessment-file: content must not be empty")
    metadata = _read_env(implement_tmpdir / MATERIALIZE_ENV)
    materialized_head = metadata.get("HEAD_SHA", "")
    if not materialized_head:
        raise ValueError("compose materialization metadata is missing HEAD_SHA")
    root = _resolve_repo_root(repo_root)
    current_head = _current_head(root, verify_commit=True)
    if current_head != materialized_head:
        raise ValueError("HEAD changed after compose materialization; rerun Step 8")
    if metadata.get("STATUS") != "present":
        raise ValueError("compose materialization metadata is not present")
    write_implement_note(
        implement_tmpdir=implement_tmpdir,
        note_text=normalized,
        head_sha=materialized_head,
        metadata=metadata,
        base_ref=metadata.get("BASE_REF", ""),
    )


def write_invariant_compose_assessment(
    *,
    implement_tmpdir: Path,
    assessment_text: str,
    repo_root: str | Path | None = None,
) -> None:
    """Write a prompt-authored invariant compose-time assessment as the durable note."""
    normalized = _normalize_assessment_text(assessment_text)
    if not normalized.strip():
        raise ValueError("assessment-file: content must not be empty")
    metadata = _read_env(implement_tmpdir / INVARIANT_MATERIALIZE_ENV)
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
    metadata["ASSESSMENT_KIND"] = metadata.get("ASSESSMENT_KIND") or _invariant_assessment_kind(normalized)
    write_invariant_implement_note(
        implement_tmpdir=implement_tmpdir,
        note_text=normalized,
        head_sha=materialized_head,
        metadata=metadata,
        base_ref=metadata.get("BASE_REF", ""),
    )


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
    from larch.report.run_log_flush import _execution_issue_chunks as execution_issue_chunks  # noqa: PLC0415  # lint-layering: ok append helper must match run-log flush chunking and dedupe.
    keys: set[str] = set()
    for chunk in execution_issue_chunks(body.splitlines()):
        chunk_body = "\n".join(chunk)
        for key in exec_issue_detail.structured_body_dedupe_keys(chunk_body, _EXECUTION_WARNINGS_CATEGORY):
            keys.add(f"{_EXECUTION_WARNINGS_CATEGORY}\0{key}")
    return keys


def _warning_chunk_source_shas(body: str) -> set[str]:
    from larch.report.run_log_batch import _normalize_body_for_hash  # noqa: PLC0415  # lint-layering: ok append helper must match run-log flush redaction and append behavior.
    from larch.report.run_log_flush import _execution_issue_chunks as execution_issue_chunks  # noqa: PLC0415  # lint-layering: ok append helper must match run-log flush chunking and dedupe.
    shas: set[str] = set()
    for chunk in execution_issue_chunks(body.splitlines()):
        chunk_body = "\n".join(chunk)
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
    from larch.report.run_log_flush import _existing_execution_issue_keys as existing_execution_issue_keys  # noqa: PLC0415  # lint-layering: ok append helper must match run-log flush chunking and dedupe.
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
    from larch.report.run_log_flush import _execution_issue_chunks as execution_issue_chunks  # noqa: PLC0415  # lint-layering: ok append helper must match run-log flush chunking and dedupe.
    kept_chunks: list[str] = []
    for chunk in execution_issue_chunks(redacted_entry.splitlines()):
        chunk_body = "\n".join(chunk)
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


def append_deviation_note_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-guidelines append-deviation-note")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    parser.add_argument("--note-file", required=True)
    args = parser.parse_args(argv)
    if not args.implement_tmpdir:
        print(f"ARCHITECTURAL_GUIDELINES_APPEND_STATUS={_APPEND_DEVIATION_FAILED}")
        print("ARCHITECTURAL_GUIDELINES_WARNING=missing implement tmpdir")
        return 2
    try:
        note_text = _read_regular_text_no_follow(Path(args.note_file))
        status = append_deviation_note(Path(args.implement_tmpdir), note_text)
    except (OSError, UnicodeDecodeError, ValueError, ShipError) as exc:
        print(f"ARCHITECTURAL_GUIDELINES_APPEND_STATUS={_APPEND_DEVIATION_FAILED}")
        print(f"ARCHITECTURAL_GUIDELINES_WARNING={str(exc).replace(chr(10), ' ')}")
        return 1
    print(f"ARCHITECTURAL_GUIDELINES_APPEND_STATUS={status}")
    return 1 if status == _APPEND_DEVIATION_FAILED else 0


def invariants_append_deviation_note_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-invariants append-deviation-note")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    parser.add_argument("--note-file", required=True)
    args = parser.parse_args(argv)
    if not args.implement_tmpdir:
        print(f"ARCHITECTURAL_INVARIANTS_APPEND_STATUS={_APPEND_DEVIATION_FAILED}")
        print("ARCHITECTURAL_INVARIANTS_WARNING=missing implement tmpdir")
        return 2
    try:
        note_text = _read_regular_text_no_follow(Path(args.note_file))
        status = append_deviation_note(Path(args.implement_tmpdir), note_text)
    except (OSError, UnicodeDecodeError, ValueError, ShipError) as exc:
        print(f"ARCHITECTURAL_INVARIANTS_APPEND_STATUS={_APPEND_DEVIATION_FAILED}")
        print(f"ARCHITECTURAL_INVARIANTS_WARNING={str(exc).replace(chr(10), ' ')}")
        return 1
    print(f"ARCHITECTURAL_INVARIANTS_APPEND_STATUS={status}")
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


def persist_design_assessment(
    *,
    repo_root: str | Path | None,
    design_tmpdir: str,
    assessment: str = "",
    assessment_text: str | None = None,
) -> int:
    design_tmpdir_path = _validate_design_tmpdir_arg(design_tmpdir)
    result = read_guidelines(repo_root=repo_root)
    path = design_assessment_path(design_tmpdir_path)
    if result.status in {"absent", "invalid"}:
        _safe_unlink_assessment(path)
        if path.exists() or path.is_symlink():
            raise OSError(f"{DESIGN_ASSESSMENT}: stale entry could not be removed (not a regular file)")
        return 0
    if assessment == "clean":
        text = CLEAN_PRESENTATION_NOTE + "\n"
    elif assessment_text is not None:
        text = _normalize_assessment_text(assessment_text)
    else:
        raise ValueError("present guidelines require exactly one assessment source")
    _write_design_assessment_atomic(design_tmpdir=design_tmpdir_path, text=text)
    return 0


def persist_invariant_design_assessment(
    *,
    repo_root: str | Path | None,
    design_tmpdir: str,
    assessment: str = "",
    assessment_text: str | None = None,
) -> int:
    design_tmpdir_path = _validate_design_tmpdir_arg(design_tmpdir)
    result = read_invariants(repo_root=repo_root)
    path = invariant_design_assessment_path(design_tmpdir_path)
    if result.status in {"absent", "invalid"} or not result.content.strip():
        _safe_unlink_assessment(path)
        if path.exists() or path.is_symlink():
            raise OSError(f"{INVARIANT_DESIGN_ASSESSMENT}: stale entry could not be removed (not a regular file)")
        return 0
    if assessment == "clean":
        text = CLEAN_INVARIANT_PRESENTATION_NOTE + "\n"
    elif assessment_text is not None:
        text = _normalize_assessment_text(assessment_text)
    else:
        raise ValueError("present invariants require exactly one assessment source")
    _write_invariant_design_assessment_atomic(design_tmpdir=design_tmpdir_path, text=text)
    return 0


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
    guidelines_status: str,
    has_clean: bool,
    has_file: bool,
) -> str | None:
    if guidelines_status == "present":
        if has_clean == has_file:
            return "present architectural guidelines require exactly one of --assessment clean or --assessment-file"
        return None
    if has_clean or has_file:
        return "absent or invalid architectural guidelines do not accept assessment source flags"
    return None


def persist_design_assessment_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-guidelines persist-design-assessment")
    parser.add_argument("--repo-root")
    parser.add_argument("--design-tmpdir", default=os.environ.get(config.ENV_DESIGN_TMPDIR, ""))
    parser.add_argument("--assessment", choices=("clean",))
    parser.add_argument("--assessment-file")
    args = parser.parse_args(argv)
    try:
        design_tmpdir = _validate_design_tmpdir_arg(args.design_tmpdir)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    result = read_guidelines(repo_root=args.repo_root)
    has_clean = args.assessment == "clean"
    has_file = bool(args.assessment_file)
    flag_error = _design_assessment_flag_error(
        guidelines_status=result.status,
        has_clean=has_clean,
        has_file=has_file,
    )
    if flag_error is not None:
        _emit_design_assessment_persist_result(
            guidelines_status=result.status,
            persist_result="failed",
            reason="invalid-flags",
        )
        print(flag_error, file=sys.stderr)
        return 1
    assessment_text: str | None = None
    if has_file:
        try:
            assessment_text = _read_regular_text_no_follow(Path(args.assessment_file))
        except OSError as exc:
            _emit_design_assessment_persist_result(
                guidelines_status=result.status,
                persist_result="failed",
                reason="assessment-file-unreadable",
            )
            print(f"assessment-file: {exc}", file=sys.stderr)
            return 1
        if not assessment_text.strip():
            _emit_design_assessment_persist_result(
                guidelines_status=result.status,
                persist_result="failed",
                reason="assessment-file-empty",
            )
            print("assessment-file: content must not be empty", file=sys.stderr)
            return 1
    try:
        rc = persist_design_assessment(
            repo_root=args.repo_root,
            design_tmpdir=str(design_tmpdir),
            assessment=args.assessment or "",
            assessment_text=assessment_text,
        )
        reason = "not-required" if result.status in {"absent", "invalid"} else "persisted"
        _emit_design_assessment_persist_result(
            guidelines_status=result.status,
            persist_result="ok",
            reason=reason,
        )
        return rc
    except (OSError, ValueError) as exc:
        _emit_design_assessment_persist_result(
            guidelines_status=result.status,
            persist_result="failed",
            reason="persist-failed",
        )
        print(f"persist-design-assessment: {exc}", file=sys.stderr)
        return 1


def invariants_persist_design_assessment_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-invariants persist-design-assessment")
    parser.add_argument("--repo-root")
    parser.add_argument("--design-tmpdir", default=os.environ.get(config.ENV_DESIGN_TMPDIR, ""))
    parser.add_argument("--assessment", choices=("clean",))
    parser.add_argument("--assessment-file")
    args = parser.parse_args(argv)
    try:
        design_tmpdir = _validate_design_tmpdir_arg(args.design_tmpdir)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    result = read_invariants(repo_root=args.repo_root)
    has_clean = args.assessment == "clean"
    has_file = bool(args.assessment_file)
    flag_error: str | None = None
    requires_assessment = result.status == "present" and bool(result.content.strip())
    if requires_assessment:
        if has_clean == has_file:
            flag_error = "present architectural invariants require exactly one of --assessment clean or --assessment-file"
    elif has_clean or has_file:
        flag_error = "absent, empty, or invalid architectural invariants do not accept assessment source flags"
    if flag_error is not None:
        print(flag_error, file=sys.stderr)
        return 1
    assessment_text: str | None = None
    if has_file:
        try:
            assessment_text = _read_regular_text_no_follow(Path(args.assessment_file))
        except OSError as exc:
            print(f"assessment-file: {exc}", file=sys.stderr)
            return 1
        if not assessment_text.strip():
            print("assessment-file: content must not be empty", file=sys.stderr)
            return 1
    try:
        return persist_invariant_design_assessment(
            repo_root=args.repo_root,
            design_tmpdir=str(design_tmpdir),
            assessment=args.assessment or "",
            assessment_text=assessment_text,
        )
    except (OSError, ValueError) as exc:
        print(f"persist-design-assessment: {exc}", file=sys.stderr)
        return 1


def read_main(argv: list[str]) -> int:
    from larch.issue import issue_wire  # noqa: PLC0415  # lint-layering: ok content blocks must match issue-wire format.
    parser = argparse.ArgumentParser(prog="architectural-guidelines read")
    parser.add_argument("--repo-root")
    args = parser.parse_args(argv)
    result = read_guidelines(repo_root=args.repo_root)
    print(f"ARCHITECTURAL_GUIDELINES_STATUS={result.status}")
    if result.status == "present":
        assert result.path is not None
        print(f"ARCHITECTURAL_GUIDELINES_PATH={result.path}")
        if result.content:
            sys.stdout.write(issue_wire.emit_untrusted_content_block(tag="architectural_guidelines", text=result.content))
    elif result.status == "invalid":
        print(f"ARCHITECTURAL_GUIDELINES_WARNING={result.warning}")
    return 0


def invariants_read_main(argv: list[str]) -> int:
    from larch.issue import issue_wire  # noqa: PLC0415  # lint-layering: ok content blocks must match issue-wire format.
    parser = argparse.ArgumentParser(prog="architectural-invariants read")
    parser.add_argument("--repo-root")
    args = parser.parse_args(argv)
    result = read_invariants(repo_root=args.repo_root)
    print(f"ARCHITECTURAL_INVARIANTS_STATUS={result.status}")
    if result.status == "present":
        assert result.path is not None
        print(f"ARCHITECTURAL_INVARIANTS_PATH={result.path}")
        if result.content:
            sys.stdout.write(issue_wire.emit_untrusted_content_block(tag="architectural_invariants", text=result.content))
    elif result.status == "invalid":
        print(f"ARCHITECTURAL_INVARIANTS_WARNING={result.warning}")
    return 0


def _emit_present_guidelines(result: ArchitecturalGuidelinesResult) -> None:
    from larch.issue import issue_wire  # noqa: PLC0415  # lint-layering: ok content blocks must match issue-wire format.
    assert result.path is not None
    print(f"ARCHITECTURAL_GUIDELINES_PATH={result.path}")
    if result.content:
        sys.stdout.write(issue_wire.emit_untrusted_content_block(tag="architectural_guidelines", text=result.content))


def _emit_present_invariants(result: ArchitecturalGuidelinesResult) -> None:
    from larch.issue import issue_wire  # noqa: PLC0415  # lint-layering: ok content blocks must match issue-wire format.
    assert result.path is not None
    print(f"ARCHITECTURAL_INVARIANTS_PATH={result.path}")
    if result.content:
        sys.stdout.write(issue_wire.emit_untrusted_content_block(tag="architectural_invariants", text=result.content))


def present_note_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-guidelines present-note")
    parser.add_argument("--repo-root")
    parser.add_argument("--assessment", choices=("pending", "clean"), default="pending")
    args = parser.parse_args(argv)
    result = read_guidelines(repo_root=args.repo_root)
    if result.status == "absent":
        return 0
    if result.status == "invalid":
        print(f"ARCHITECTURAL_GUIDELINES_WARNING={result.warning}")
        return 0
    if args.assessment == "clean":
        print(CLEAN_PRESENTATION_NOTE)
        return 0
    _emit_present_guidelines(result)
    print(GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED)
    return 0


def invariants_present_note_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-invariants present-note")
    parser.add_argument("--repo-root")
    parser.add_argument("--assessment", choices=("pending", "clean"), default="pending")
    args = parser.parse_args(argv)
    result = read_invariants(repo_root=args.repo_root)
    if result.status == "absent":
        return 0
    if result.status == "invalid":
        print(f"ARCHITECTURAL_INVARIANTS_WARNING={result.warning}")
        return 0
    if args.assessment == "clean":
        if result.content.strip():
            print(CLEAN_INVARIANT_PRESENTATION_NOTE)
        return 0
    _emit_present_invariants(result)
    if result.content.strip():
        print(INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED)
    return 0


def _emit_materialized_diff(
    repo_root: Path,
    *,
    forked_target: bool,
    output: str = "",
    implement_tmpdir: str = "",
) -> int:
    from larch.issue import issue_wire  # noqa: PLC0415  # lint-layering: ok content blocks must match issue-wire format.
    base_remote, base_ref = resolve_diff_base(forked_target=forked_target)
    base_label = f"{base_remote}/{base_ref}"
    try:
        diff_text = materialize_implementation_diff(repo_root, base_remote=base_remote, base_ref=base_ref)
    except RuntimeError as exc:
        print("ARCHITECTURAL_GUIDELINES_DIFF_STATUS=failed")
        print(f"ARCHITECTURAL_GUIDELINES_WARNING={str(exc).replace(chr(10), ' ')}")
        return 1
    fingerprint = diff_fingerprint(diff_text)
    output_path: Path | None = Path(output) if output else None
    try:
        if implement_tmpdir:
            tmpdir = Path(implement_tmpdir)
            output_path = output_path or _diff_path(tmpdir)
            meta_path = tmpdir / MATERIALIZE_ENV
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
        print("ARCHITECTURAL_GUIDELINES_DIFF_STATUS=failed")
        print(f"ARCHITECTURAL_GUIDELINES_WARNING={str(exc).replace(chr(10), ' ')}")
        return 1
    print("ARCHITECTURAL_GUIDELINES_DIFF_STATUS=ok")
    print(f"ARCHITECTURAL_GUIDELINES_BASE_REF={base_label}")
    print(f"ARCHITECTURAL_GUIDELINES_DIFF_FINGERPRINT={fingerprint}")
    sys.stdout.write(issue_wire.emit_untrusted_content_block(tag="architectural_guidelines_diff", text=diff_text))
    return 0


def materialize_diff_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-guidelines materialize-diff")
    parser.add_argument("--repo-root")
    parser.add_argument("--forked-target", default="false")
    parser.add_argument("--output")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    args = parser.parse_args(argv)
    repo_root = _resolve_repo_root(args.repo_root)
    if repo_root is None:
        print("ARCHITECTURAL_GUIDELINES_DIFF_STATUS=absent")
        return 0
    return _emit_materialized_diff(
        repo_root,
        forked_target=_bool_arg(args.forked_target),
        output=args.output or "",
        implement_tmpdir=args.implement_tmpdir,
    )


def _emit_invariant_materialized_diff(
    repo_root: Path,
    *,
    forked_target: bool,
    output: str = "",
    implement_tmpdir: str = "",
) -> int:
    from larch.issue import issue_wire  # noqa: PLC0415  # lint-layering: ok content blocks must match issue-wire format.
    base_remote, base_ref = resolve_diff_base(forked_target=forked_target)
    base_label = f"{base_remote}/{base_ref}"
    try:
        diff_text = materialize_implementation_diff(repo_root, base_remote=base_remote, base_ref=base_ref)
    except RuntimeError as exc:
        print("ARCHITECTURAL_INVARIANTS_DIFF_STATUS=failed")
        print(f"ARCHITECTURAL_INVARIANTS_WARNING={str(exc).replace(chr(10), ' ')}")
        return 1
    fingerprint = diff_fingerprint(diff_text)
    output_path: Path | None = Path(output) if output else None
    try:
        if implement_tmpdir:
            tmpdir = Path(implement_tmpdir)
            output_path = output_path or _invariant_diff_path(tmpdir)
            meta_path = tmpdir / INVARIANT_MATERIALIZE_ENV
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
        print("ARCHITECTURAL_INVARIANTS_DIFF_STATUS=failed")
        print(f"ARCHITECTURAL_INVARIANTS_WARNING={str(exc).replace(chr(10), ' ')}")
        return 1
    print("ARCHITECTURAL_INVARIANTS_DIFF_STATUS=ok")
    print(f"ARCHITECTURAL_INVARIANTS_BASE_REF={base_label}")
    print(f"ARCHITECTURAL_INVARIANTS_DIFF_FINGERPRINT={fingerprint}")
    sys.stdout.write(issue_wire.emit_untrusted_content_block(tag="architectural_invariants_diff", text=diff_text))
    return 0


def invariants_materialize_diff_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-invariants materialize-diff")
    parser.add_argument("--repo-root")
    parser.add_argument("--forked-target", default="false")
    parser.add_argument("--output")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    args = parser.parse_args(argv)
    repo_root = _resolve_repo_root(args.repo_root)
    if repo_root is None:
        print("ARCHITECTURAL_INVARIANTS_DIFF_STATUS=absent")
        return 0
    return _emit_invariant_materialized_diff(
        repo_root,
        forked_target=_bool_arg(args.forked_target),
        output=args.output or "",
        implement_tmpdir=args.implement_tmpdir,
    )


def prepare_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-guidelines prepare")
    parser.add_argument("--repo-root")
    parser.add_argument("--forked-target", default="false")
    parser.add_argument("--output")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    args = parser.parse_args(argv)
    if args.implement_tmpdir:
        try:
            invalidate_implement_note(Path(args.implement_tmpdir))
        except OSError as exc:
            print("ARCHITECTURAL_GUIDELINES_INVALIDATE_STATUS=failed")
            print(f"ARCHITECTURAL_GUIDELINES_WARNING={exc}")
            return 2
    result = read_guidelines(repo_root=args.repo_root)
    print(f"ARCHITECTURAL_GUIDELINES_STATUS={result.status}")
    if result.status == "absent":
        return 0
    if result.status == "invalid":
        print(f"ARCHITECTURAL_GUIDELINES_WARNING={result.warning}")
        return 0
    assert result.repo_root is not None
    _emit_present_guidelines(result)
    return _emit_materialized_diff(
        result.repo_root,
        forked_target=_bool_arg(args.forked_target),
        output=args.output or "",
        implement_tmpdir=args.implement_tmpdir,
    )


def invariants_prepare_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-invariants prepare")
    parser.add_argument("--repo-root")
    parser.add_argument("--forked-target", default="false")
    parser.add_argument("--output")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    args = parser.parse_args(argv)
    if args.implement_tmpdir:
        try:
            invalidate_invariant_implement_note(Path(args.implement_tmpdir))
        except OSError as exc:
            print("ARCHITECTURAL_INVARIANTS_INVALIDATE_STATUS=failed")
            print(f"ARCHITECTURAL_INVARIANTS_WARNING={exc}")
            return 2
    result = read_invariants(repo_root=args.repo_root)
    print(f"ARCHITECTURAL_INVARIANTS_STATUS={result.status}")
    if result.status == "absent":
        return 0
    if result.status == "invalid":
        print(f"ARCHITECTURAL_INVARIANTS_WARNING={result.warning}")
        return 0
    assert result.repo_root is not None
    _emit_present_invariants(result)
    if not result.content.strip():
        return 0
    return _emit_invariant_materialized_diff(
        result.repo_root,
        forked_target=_bool_arg(args.forked_target),
        output=args.output or "",
        implement_tmpdir=args.implement_tmpdir,
    )


def _emit_compose_prepare_result(*, result: ComposeMaterializationResult, implement_tmpdir: Path, repo_root: str | Path | None) -> None:
    from larch.issue import issue_wire  # noqa: PLC0415  # lint-layering: ok content blocks must match issue-wire format.
    print(f"ARCHITECTURAL_GUIDELINES_COMPOSE_STATUS={result.status}")
    for key, value in (
        ("ARCHITECTURAL_GUIDELINES_HEAD_SHA", result.head_sha),
        ("ARCHITECTURAL_GUIDELINES_BASE_REF", result.base_ref),
        ("ARCHITECTURAL_GUIDELINES_DIFF_FINGERPRINT", result.diff_fingerprint),
        ("ARCHITECTURAL_GUIDELINES_DIFF_PATH", str(result.diff_path) if result.diff_path is not None else ""),
        ("ARCHITECTURAL_GUIDELINES_WARNING", result.warning),
    ):
        if value:
            print(f"{key}={value}")
    guidelines = read_guidelines(repo_root=repo_root)
    print(f"ARCHITECTURAL_GUIDELINES_STATUS={guidelines.status}")
    if guidelines.status != "present":
        return
    _emit_present_guidelines(guidelines)
    diff_path = result.diff_path or _diff_path(implement_tmpdir)
    if not diff_path.is_file() or diff_path.is_symlink():
        return
    try:
        diff_text = diff_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    if diff_text:
        sys.stdout.write(issue_wire.emit_untrusted_content_block(tag="architectural_guidelines_diff", text=diff_text))


def prepare_compose_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-guidelines prepare-compose")
    parser.add_argument("--repo-root")
    parser.add_argument("--forked-target", default="false")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    parser.add_argument("--expected-head-sha", default="")
    args = parser.parse_args(argv)
    if not args.implement_tmpdir:
        print("ARCHITECTURAL_GUIDELINES_COMPOSE_STATUS=failed")
        print("ARCHITECTURAL_GUIDELINES_WARNING=missing implement tmpdir")
        return 2
    result = prepare_compose_assessment(
        implement_tmpdir=Path(args.implement_tmpdir),
        repo_root=args.repo_root,
        forked_target=_bool_arg(args.forked_target),
        expected_head_sha=args.expected_head_sha,
    )
    _emit_compose_prepare_result(
        result=result,
        implement_tmpdir=Path(args.implement_tmpdir),
        repo_root=args.repo_root,
    )
    return 1 if result.status == "failed" else 0


def _emit_invariant_compose_prepare_result(*, result: ComposeMaterializationResult, implement_tmpdir: Path, repo_root: str | Path | None) -> None:
    from larch.issue import issue_wire  # noqa: PLC0415  # lint-layering: ok content blocks must match issue-wire format.
    print(f"ARCHITECTURAL_INVARIANTS_COMPOSE_STATUS={result.status}")
    for key, value in (
        ("ARCHITECTURAL_INVARIANTS_HEAD_SHA", result.head_sha),
        ("ARCHITECTURAL_INVARIANTS_BASE_REF", result.base_ref),
        ("ARCHITECTURAL_INVARIANTS_DIFF_FINGERPRINT", result.diff_fingerprint),
        ("ARCHITECTURAL_INVARIANTS_DIFF_PATH", str(result.diff_path) if result.diff_path is not None else ""),
        ("ARCHITECTURAL_INVARIANTS_WARNING", result.warning),
    ):
        if value:
            print(f"{key}={value}")
    invariants = read_invariants(repo_root=repo_root)
    print(f"ARCHITECTURAL_INVARIANTS_STATUS={invariants.status}")
    if invariants.status != "present":
        return
    _emit_present_invariants(invariants)
    diff_path = result.diff_path or _invariant_diff_path(implement_tmpdir)
    if not diff_path.is_file() or diff_path.is_symlink():
        return
    try:
        diff_text = diff_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    if diff_text:
        sys.stdout.write(issue_wire.emit_untrusted_content_block(tag="architectural_invariants_diff", text=diff_text))


def invariants_prepare_compose_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-invariants prepare-compose")
    parser.add_argument("--repo-root")
    parser.add_argument("--forked-target", default="false")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    parser.add_argument("--expected-head-sha", default="")
    args = parser.parse_args(argv)
    if not args.implement_tmpdir:
        print("ARCHITECTURAL_INVARIANTS_COMPOSE_STATUS=failed")
        print("ARCHITECTURAL_INVARIANTS_WARNING=missing implement tmpdir")
        return 2
    result = prepare_invariant_compose_assessment(
        implement_tmpdir=Path(args.implement_tmpdir),
        repo_root=args.repo_root,
        forked_target=_bool_arg(args.forked_target),
        expected_head_sha=args.expected_head_sha,
    )
    _emit_invariant_compose_prepare_result(
        result=result,
        implement_tmpdir=Path(args.implement_tmpdir),
        repo_root=args.repo_root,
    )
    return 1 if result.status == "failed" else 0


def write_compose_assessment_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-guidelines write-compose-assessment")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    parser.add_argument("--repo-root")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--assessment-file")
    source.add_argument("--assessment-text")
    args = parser.parse_args(argv)
    if not args.implement_tmpdir:
        print("ARCHITECTURAL_GUIDELINES_WRITE_STATUS=failed")
        print("ARCHITECTURAL_GUIDELINES_WARNING=missing implement tmpdir")
        return 2
    try:
        if args.assessment_file:
            assessment_text = _read_regular_text_no_follow(Path(args.assessment_file))
        else:
            assessment_text = str(args.assessment_text or "")
        write_compose_assessment(
            implement_tmpdir=Path(args.implement_tmpdir),
            assessment_text=assessment_text,
            repo_root=args.repo_root,
        )
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print("ARCHITECTURAL_GUIDELINES_WRITE_STATUS=failed")
        print(f"ARCHITECTURAL_GUIDELINES_WARNING={str(exc).replace(chr(10), ' ')}")
        return 1
    print("ARCHITECTURAL_GUIDELINES_WRITE_STATUS=ok")
    return 0


def invariants_write_compose_assessment_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-invariants write-compose-assessment")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    parser.add_argument("--repo-root")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--assessment-file")
    source.add_argument("--assessment-text")
    args = parser.parse_args(argv)
    if not args.implement_tmpdir:
        print("ARCHITECTURAL_INVARIANTS_WRITE_STATUS=failed")
        print("ARCHITECTURAL_INVARIANTS_WARNING=missing implement tmpdir")
        return 2
    try:
        if args.assessment_file:
            assessment_text = _read_regular_text_no_follow(Path(args.assessment_file))
        else:
            assessment_text = str(args.assessment_text or "")
        write_invariant_compose_assessment(
            implement_tmpdir=Path(args.implement_tmpdir),
            assessment_text=assessment_text,
            repo_root=args.repo_root,
        )
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print("ARCHITECTURAL_INVARIANTS_WRITE_STATUS=failed")
        print(f"ARCHITECTURAL_INVARIANTS_WARNING={str(exc).replace(chr(10), ' ')}")
        return 1
    print("ARCHITECTURAL_INVARIANTS_WRITE_STATUS=ok")
    return 0


def write_staged_assessment_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-guidelines write-staged-assessment")
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
        print("ARCHITECTURAL_GUIDELINES_WRITE_STATUS=failed")
        print("ARCHITECTURAL_GUIDELINES_WARNING=missing implement tmpdir")
        return 2
    if args.assessment_file:
        assessment_text = Path(args.assessment_file).read_text(encoding="utf-8")
    else:
        assessment_text = args.assessment_text
    diff_text = ""
    if args.diff_file:
        diff_path = Path(args.diff_file)
        if not diff_path.is_file() or diff_path.is_symlink():
            print("ARCHITECTURAL_GUIDELINES_WRITE_STATUS=failed")
            print("ARCHITECTURAL_GUIDELINES_WARNING=missing diff file")
            return 1
        try:
            diff_text = diff_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print("ARCHITECTURAL_GUIDELINES_WRITE_STATUS=failed")
            print(f"ARCHITECTURAL_GUIDELINES_WARNING=unreadable diff file ({exc})")
            return 1
    fingerprint = args.diff_fingerprint or diff_fingerprint(diff_text)
    head_sha = args.assessed_head_sha or _current_head()
    write_staged_assessment(
        implement_tmpdir=Path(args.implement_tmpdir),
        assessment_text=assessment_text,
        assessed_head_sha=head_sha,
        diff_fingerprint_value=fingerprint,
        base_ref=args.base_ref,
        diff_text=diff_text,
    )
    print("ARCHITECTURAL_GUIDELINES_WRITE_STATUS=ok")
    return 0


def invariants_write_staged_assessment_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-invariants write-staged-assessment")
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
        print("ARCHITECTURAL_INVARIANTS_WRITE_STATUS=failed")
        print("ARCHITECTURAL_INVARIANTS_WARNING=missing implement tmpdir")
        return 2
    if args.assessment_file:
        assessment_text = Path(args.assessment_file).read_text(encoding="utf-8")
    else:
        assessment_text = args.assessment_text
    diff_text = ""
    if args.diff_file:
        diff_path = Path(args.diff_file)
        if not diff_path.is_file() or diff_path.is_symlink():
            print("ARCHITECTURAL_INVARIANTS_WRITE_STATUS=failed")
            print("ARCHITECTURAL_INVARIANTS_WARNING=missing diff file")
            return 1
        try:
            diff_text = diff_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print("ARCHITECTURAL_INVARIANTS_WRITE_STATUS=failed")
            print(f"ARCHITECTURAL_INVARIANTS_WARNING=unreadable diff file ({exc})")
            return 1
    fingerprint = args.diff_fingerprint or diff_fingerprint(diff_text)
    head_sha = args.assessed_head_sha or _current_head()
    write_invariant_staged_assessment(
        implement_tmpdir=Path(args.implement_tmpdir),
        assessment_text=assessment_text,
        assessed_head_sha=head_sha,
        diff_fingerprint_value=fingerprint,
        base_ref=args.base_ref,
        diff_text=diff_text,
    )
    print("ARCHITECTURAL_INVARIANTS_WRITE_STATUS=ok")
    return 0


def pin_note_from_staged_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-guidelines pin-note-from-staged")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    parser.add_argument("--head-sha", default="")
    parser.add_argument("--base-ref", default="")
    parser.add_argument("--repo-root")
    args = parser.parse_args(argv)
    if not args.implement_tmpdir:
        print("ARCHITECTURAL_GUIDELINES_PIN_STATUS=failed")
        print("ARCHITECTURAL_GUIDELINES_WARNING=missing implement tmpdir")
        return 2
    head_sha = args.head_sha or _current_head()
    pinned = pin_note_from_staged(
        Path(args.implement_tmpdir),
        head_sha=head_sha,
        base_ref=args.base_ref,
        repo_root=args.repo_root,
    )
    print(f"ARCHITECTURAL_GUIDELINES_PIN_STATUS={'ok' if pinned else 'skipped'}")
    return 0


def pin_invariant_note_from_staged(
    implement_tmpdir: Path,
    *,
    head_sha: str,
    base_ref: str = "",
    repo_root: str | Path | None = None,
) -> bool:
    """Copy the staged invariant assessment into a durable note pinned to head_sha."""
    staged = invariant_staged_assessment_path(implement_tmpdir)
    sidecar = _invariant_sidecar_path(implement_tmpdir)
    if not staged.is_file() or staged.is_symlink() or not sidecar.is_file() or sidecar.is_symlink():
        return False
    metadata = _read_env(sidecar)
    if metadata.get("STATUS") != "present":
        return False
    if not _invariant_staged_fingerprint_valid(
        implement_tmpdir=implement_tmpdir,
        metadata=metadata,
        base_ref=base_ref,
        repo_root=Path(repo_root).resolve() if repo_root is not None else None,
    ):
        return False
    try:
        note_text = staged.read_text(encoding="utf-8")
    except OSError:
        return False
    try:
        write_invariant_implement_note(implement_tmpdir=implement_tmpdir, note_text=note_text, head_sha=head_sha, metadata=metadata, base_ref=base_ref)
    except OSError:
        return False
    return True


def invariants_pin_note_from_staged_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-invariants pin-note-from-staged")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    parser.add_argument("--head-sha", default="")
    parser.add_argument("--base-ref", default="")
    parser.add_argument("--repo-root")
    args = parser.parse_args(argv)
    if not args.implement_tmpdir:
        print("ARCHITECTURAL_INVARIANTS_PIN_STATUS=failed")
        print("ARCHITECTURAL_INVARIANTS_WARNING=missing implement tmpdir")
        return 2
    head_sha = args.head_sha or _current_head()
    pinned = pin_invariant_note_from_staged(
        Path(args.implement_tmpdir),
        head_sha=head_sha,
        base_ref=args.base_ref,
        repo_root=args.repo_root,
    )
    print(f"ARCHITECTURAL_INVARIANTS_PIN_STATUS={'ok' if pinned else 'skipped'}")
    return 0


def invalidate_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-guidelines invalidate")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    args = parser.parse_args(argv)
    if not args.implement_tmpdir:
        print("ARCHITECTURAL_GUIDELINES_INVALIDATE_STATUS=failed")
        print("ARCHITECTURAL_GUIDELINES_WARNING=missing implement tmpdir")
        return 2
    try:
        invalidate_implement_note(Path(args.implement_tmpdir))
    except OSError as exc:
        print("ARCHITECTURAL_GUIDELINES_INVALIDATE_STATUS=failed")
        print(f"ARCHITECTURAL_GUIDELINES_WARNING={exc}")
        return 2
    print("ARCHITECTURAL_GUIDELINES_INVALIDATE_STATUS=ok")
    return 0


def invariants_invalidate_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-invariants invalidate")
    parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    args = parser.parse_args(argv)
    if not args.implement_tmpdir:
        print("ARCHITECTURAL_INVARIANTS_INVALIDATE_STATUS=failed")
        print("ARCHITECTURAL_INVARIANTS_WARNING=missing implement tmpdir")
        return 2
    try:
        invalidate_invariant_implement_note(Path(args.implement_tmpdir))
    except OSError as exc:
        print("ARCHITECTURAL_INVARIANTS_INVALIDATE_STATUS=failed")
        print(f"ARCHITECTURAL_INVARIANTS_WARNING={exc}")
        return 2
    print("ARCHITECTURAL_INVARIANTS_INVALIDATE_STATUS=ok")
    return 0
# pyright: reportArgumentType=false
# lint-env-via-config-constant: IMPLEMENT_TMPDIR is read in CLI entry points.
# larch-lint: allow-subprocess-run
