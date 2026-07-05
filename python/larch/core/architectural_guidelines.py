"""ARCHITECTURAL_GUIDELINES.md reader and implement note helpers."""
# pyright: reportUnusedCallResult=false

from __future__ import annotations

import argparse
import hashlib
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
from pathlib import Path

from larch.core import config
from larch.issue import issue_wire
from larch.state import session_env

GUIDELINES_FILENAME = "ARCHITECTURAL_GUIDELINES.md"
CLEAN_PRESENTATION_NOTE = "Consulted ARCHITECTURAL_GUIDELINES.md; no deviations identified."
GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED = "GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED=true"
DESIGN_ASSESSMENT = "architectural-guideline-assessment.md"
STAGED_ASSESSMENT = "architectural-guideline-staged-assessment.md"
STAGED_ASSESSMENT_ENV = "architectural-guideline-staged-assessment.env"
MATERIALIZED_DIFF = "architectural-guideline-materialized-diff.txt"
DURABLE_NOTE = "architectural-guideline-note.md"
DURABLE_NOTE_ENV = "architectural-guideline-note.meta.env"
DROPPED_NOTE_ARTIFACT = "architectural-guideline-drop-notice.txt"
LEGACY_WARNING = "architectural-guideline-warnings.md"
LEGACY_WARNING_ENV = "architectural-guideline-warnings.meta.env"
MATERIALIZE_ENV = "architectural-guideline-materialize.env"
_STATUS_VALUES = {"present", "absent", "invalid"}
_HEADING_RE = re.compile(r"^###\s+(G-[A-Za-z0-9-]+-\d+):\s*(.+?)\s*$")
_MARKDOWN_HEADING_RE = re.compile(r"^#{1,6}\s+\S")
_WHY_RE = re.compile(r"^\s*-\s*Why:\s*(.+?)\s*$")
_DEVIATE_RE = re.compile(r"^\s*-\s*Deviate when:\s*(.+?)\s*$")


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
    warning: str = ""


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
    """Return normalized G-* entries with only Why and Deviate bullets."""
    entries: list[list[str]] = []
    current: list[str] | None = None
    for raw_line in raw_text.splitlines():
        heading = _HEADING_RE.match(raw_line)
        if heading:
            if current is not None:
                entries.append(current)
            current = [f"### {heading.group(1)}: {heading.group(2).strip()}"]
            continue
        if _MARKDOWN_HEADING_RE.match(raw_line):
            if current is not None:
                entries.append(current)
                current = None
            continue
        if current is None:
            continue
        why = _WHY_RE.match(raw_line)
        if why:
            current.append(f"- Why: {why.group(1).strip()}")
            continue
        deviate = _DEVIATE_RE.match(raw_line)
        if deviate:
            current.append(f"- Deviate when: {deviate.group(1).strip()}")
    if current is not None:
        entries.append(current)
    return "\n\n".join("\n".join(entry) for entry in entries).strip()


def _invalid(*, repo_root: Path | None, path: Path | None, warning: str) -> ArchitecturalGuidelinesResult:
    return ArchitecturalGuidelinesResult("invalid", repo_root, path, "", warning)


def _validate_guidelines_file(*, root: Path, path: Path) -> str | None:
    """Return an invalid-reason for a present guidelines path, or None when it is a readable regular file."""
    if path.is_symlink():
        return f"{GUIDELINES_FILENAME} is invalid: symlinks are not read"
    try:
        resolved = path.resolve(strict=False)
        _ = resolved.relative_to(root.resolve())
    except (OSError, ValueError):
        return f"{GUIDELINES_FILENAME} is invalid: path escapes repo root"
    if path.is_dir():
        return f"{GUIDELINES_FILENAME} is invalid: expected a regular file, found a directory"
    if not path.is_file():
        return f"{GUIDELINES_FILENAME} is invalid: expected a regular file"
    return None


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


def resolve_diff_base(*, forked_target: bool) -> tuple[str, str]:
    """Return the remote and ref used for implementation diff materialization."""
    return ("upstream", "main") if forked_target else ("origin", "main")


def materialize_implementation_diff(repo_root: Path, *, base_remote: str, base_ref: str) -> str:
    """Return a merge-base..HEAD diff for orchestrator assessment."""
    target = f"{base_remote}/{base_ref}"
    head_errors: list[str] = []
    head_sha = _current_head(repo_root, verify_commit=True, error_out=head_errors)
    if not head_sha:
        msg = head_errors[0] if head_errors else "could not resolve HEAD"
        raise RuntimeError(msg)
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


def diff_fingerprint(diff_text: str) -> str:
    return hashlib.sha256(diff_text.encode("utf-8", errors="surrogateescape")).hexdigest()


def staged_assessment_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / STAGED_ASSESSMENT


def durable_note_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / DURABLE_NOTE


def design_assessment_path(design_tmpdir: Path) -> Path:
    return design_tmpdir / DESIGN_ASSESSMENT


def dropped_note_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / DROPPED_NOTE_ARTIFACT


def _validate_design_tmpdir_arg(candidate: str) -> Path:
    ok, message = session_env.validate_design_tmpdir(candidate)
    if not ok:
        raise ValueError(message)
    if Path(candidate).is_symlink():
        raise ValueError("design-tmpdir: path must not be a symlink")
    return Path(candidate).resolve(strict=False)


def _sidecar_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / STAGED_ASSESSMENT_ENV


def _durable_meta_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / DURABLE_NOTE_ENV


def _diff_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / MATERIALIZED_DIFF


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


def note_readable_any_head(implement_tmpdir: Path) -> bool:
    """Return true when a present durable note is readable regardless of HEAD."""
    return durable_note_present(implement_tmpdir)


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


def write_implement_note(*, implement_tmpdir: Path, note_text: str, head_sha: str, metadata: dict[str, str], base_ref: str) -> None:
    """Write the durable compose-time note and HEAD-pinned metadata."""
    _write_text_atomic(path=durable_note_path(implement_tmpdir), text=note_text)
    diff_snapshot = metadata.get("DIFF_SNAPSHOT", "")
    meta = "\n".join(
        [
            "STATUS=present",
            f"HEAD_SHA={_env_escape(head_sha)}",
            f"ASSESSED_HEAD_SHA={_env_escape(metadata.get('ASSESSED_HEAD_SHA', ''))}",
            f"DIFF_FINGERPRINT={_env_escape(metadata.get('DIFF_FINGERPRINT', ''))}",
            f"BASE_REF={_env_escape(base_ref or metadata.get('BASE_REF', ''))}",
            f"DIFF_SNAPSHOT={_env_escape(diff_snapshot)}",
            f"WRITTEN_AT={datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')}",
            "",
        ]
    )
    _write_text_atomic(path=_durable_meta_path(implement_tmpdir), text=meta)
    clear_staged_and_dropped_artifacts(implement_tmpdir)


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


def durable_note_metadata(implement_tmpdir: Path) -> dict[str, str]:
    """Return durable-note sidecar metadata when present."""
    return _read_env(_durable_meta_path(implement_tmpdir))


def note_consumable(*, implement_tmpdir: Path, head_sha: str) -> bool:
    """Return true when the durable note is safe to surface for head_sha."""
    note = durable_note_path(implement_tmpdir)
    meta = _durable_meta_path(implement_tmpdir)
    if not note.is_file() or note.is_symlink() or not meta.is_file() or meta.is_symlink():
        return False
    metadata = _read_env(meta)
    return metadata.get("STATUS") == "present" and metadata.get("HEAD_SHA") == head_sha


def note_fingerprint_stale(
    implement_tmpdir: Path,
    *,
    base_ref: str,
    repo_root: str | Path | None = None,
) -> bool:
    """Return true when the durable note fingerprint no longer matches the implementation diff."""
    meta = _read_env(_durable_meta_path(implement_tmpdir))
    stored_fp = meta.get("DIFF_FINGERPRINT", "")
    if not stored_fp or not base_ref:
        return False
    diff_path = _diff_path(implement_tmpdir)
    if diff_path.is_file() and not diff_path.is_symlink():
        try:
            snapshot_text = diff_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return True
        if diff_fingerprint(snapshot_text) == stored_fp:
            return False
    root = Path(repo_root).resolve() if repo_root is not None else None
    live_fp = _live_fingerprint(repo_root=root, resolved_base=base_ref)
    if live_fp is None:
        return True
    return live_fp != stored_fp


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
                f"DIFF_FINGERPRINT={_env_escape(materialized.diff_fingerprint)}",
                f"DIFF_SNAPSHOT={_env_escape(str(diff_path))}",
                f"GUIDELINES_STATUS={_env_escape(materialized.guidelines_status)}",
                f"GUIDELINES_PATH={_env_escape(materialized.guidelines_path)}",
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
    if current_head and note_consumable(implement_tmpdir=implement_tmpdir, head_sha=current_head):
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
    if result.status == "absent":
        return None, ComposeMaterializationResult(status="absent", head_sha=current_head, guidelines_status="absent")
    if result.status == "invalid":
        return None, ComposeMaterializationResult(
            status="invalid",
            head_sha=current_head,
            guidelines_status="invalid",
            warning=result.warning,
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
    base_remote, base_ref = resolve_diff_base(forked_target=forked_target)
    base_label = f"{base_remote}/{base_ref}"
    try:
        diff_text = materialize_implementation_diff(root, base_remote=base_remote, base_ref=base_ref)
    except (OSError, RuntimeError) as exc:
        return ComposeMaterializationResult(
            status="failed",
            head_sha=current_head,
            base_ref=base_label,
            guidelines_status=result.status,
            warning=str(exc).replace("\n", " "),
        )
    materialized = ComposeMaterializationResult(
        status="assessment-required",
        head_sha=current_head,
        base_ref=base_label,
        diff_fingerprint=diff_fingerprint(diff_text),
        diff_path=_diff_path(implement_tmpdir),
        guidelines_status=result.status,
        guidelines_path=str(result.path or ""),
    )
    try:
        _write_text_atomic(path=_diff_path(implement_tmpdir), text=diff_text)
        _write_compose_materialization_metadata(
            implement_tmpdir=implement_tmpdir,
            materialized=materialized,
        )
    except OSError as exc:
        return ComposeMaterializationResult(
            status="failed",
            head_sha=current_head,
            base_ref=base_label,
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


def persist_design_assessment_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-guidelines persist-design-assessment")
    parser.add_argument("--repo-root")
    parser.add_argument("--design-tmpdir", default=os.environ.get("DESIGN_TMPDIR", ""))
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
    flag_error: str | None = None
    if result.status == "present":
        if has_clean == has_file:
            flag_error = "present architectural guidelines require exactly one of --assessment clean or --assessment-file"
    elif has_clean or has_file:
        flag_error = "absent or invalid architectural guidelines do not accept assessment source flags"
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
        return persist_design_assessment(
            repo_root=args.repo_root,
            design_tmpdir=str(design_tmpdir),
            assessment=args.assessment or "",
            assessment_text=assessment_text,
        )
    except (OSError, ValueError) as exc:
        print(f"persist-design-assessment: {exc}", file=sys.stderr)
        return 1


def read_main(argv: list[str]) -> int:
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


def _emit_present_guidelines(result: ArchitecturalGuidelinesResult) -> None:
    assert result.path is not None
    print(f"ARCHITECTURAL_GUIDELINES_PATH={result.path}")
    if result.content:
        sys.stdout.write(issue_wire.emit_untrusted_content_block(tag="architectural_guidelines", text=result.content))


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


def _emit_materialized_diff(
    repo_root: Path,
    *,
    forked_target: bool,
    output: str = "",
    implement_tmpdir: str = "",
) -> int:
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
    parser.add_argument("--implement-tmpdir", default=os.environ.get("IMPLEMENT_TMPDIR", ""))
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


def prepare_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-guidelines prepare")
    parser.add_argument("--repo-root")
    parser.add_argument("--forked-target", default="false")
    parser.add_argument("--output")
    parser.add_argument("--implement-tmpdir", default=os.environ.get("IMPLEMENT_TMPDIR", ""))
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


def _emit_compose_prepare_result(*, result: ComposeMaterializationResult, implement_tmpdir: Path, repo_root: str | Path | None) -> None:
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


def write_staged_assessment_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-guidelines write-staged-assessment")
    parser.add_argument("--implement-tmpdir", default=os.environ.get("IMPLEMENT_TMPDIR", ""))
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


def pin_note_from_staged_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-guidelines pin-note-from-staged")
    parser.add_argument("--implement-tmpdir", default=os.environ.get("IMPLEMENT_TMPDIR", ""))
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


def invalidate_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="architectural-guidelines invalidate")
    parser.add_argument("--implement-tmpdir", default=os.environ.get("IMPLEMENT_TMPDIR", ""))
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
# pyright: reportArgumentType=false
# lint-env-via-config-constant: IMPLEMENT_TMPDIR is read in CLI entry points.
