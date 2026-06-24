"""ARCHITECTURAL_GUIDELINES.md reader and implement note helpers."""
# pyright: reportUnusedCallResult=false

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import issue_wire

GUIDELINES_FILENAME = "ARCHITECTURAL_GUIDELINES.md"
CLEAN_PRESENTATION_NOTE = "Consulted ARCHITECTURAL_GUIDELINES.md; no deviations identified."
GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED = "GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED=true"
STAGED_ASSESSMENT = "architectural-guideline-staged-assessment.md"
STAGED_ASSESSMENT_ENV = "architectural-guideline-staged-assessment.env"
MATERIALIZED_DIFF = "architectural-guideline-materialized-diff.txt"
DURABLE_NOTE = "architectural-guideline-note.md"
DURABLE_NOTE_ENV = "architectural-guideline-note.meta.env"
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


def _invalid(repo_root: Path | None, path: Path | None, warning: str) -> ArchitecturalGuidelinesResult:
    return ArchitecturalGuidelinesResult("invalid", repo_root, path, "", warning)


def _validate_guidelines_file(root: Path, path: Path) -> str | None:
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
    warning = _validate_guidelines_file(root, path)
    if warning is not None:
        return _invalid(root, path, warning)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _invalid(root, path, f"{GUIDELINES_FILENAME} is invalid: unreadable file ({exc})")
    return ArchitecturalGuidelinesResult("present", root, path.resolve(strict=False), parse_guideline_entries(raw_text), "")


def resolve_diff_base(*, forked_target: bool) -> tuple[str, str]:
    """Return the remote and ref used for implementation diff materialization."""
    return ("upstream", "main") if forked_target else ("origin", "main")


def materialize_implementation_diff(repo_root: Path, *, base_remote: str, base_ref: str) -> str:
    """Return a merge-base..HEAD diff for orchestrator assessment."""
    target = f"{base_remote}/{base_ref}"
    merge_base = subprocess.run(
        ["git", "merge-base", "HEAD", target],  # noqa: S607
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
        ["git", "diff", f"{base_sha}..HEAD", "--", ".", ":(exclude)larch-logs/**"],  # noqa: S607
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


def _sidecar_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / STAGED_ASSESSMENT_ENV


def _durable_meta_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / DURABLE_NOTE_ENV


def _diff_path(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / MATERIALIZED_DIFF


def _env_escape(value: str) -> str:
    return value.replace("\n", " ").replace("\r", " ")


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


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


def write_staged_assessment(  # noqa: PLR0913 - cohesive Phase A artifact writer; bundling its pin-metadata fields would churn 14 call sites
    implement_tmpdir: Path,
    assessment_text: str,
    *,
    assessed_head_sha: str,
    diff_fingerprint_value: str,
    base_ref: str,
    diff_text: str = "",
) -> None:
    """Persist orchestrator-authored Phase A assessment artifacts."""
    implement_tmpdir.mkdir(parents=True, exist_ok=True)
    _write_text_atomic(staged_assessment_path(implement_tmpdir), assessment_text)
    _write_text_atomic(_diff_path(implement_tmpdir), diff_text)
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
    _write_text_atomic(_sidecar_path(implement_tmpdir), sidecar)


def write_implement_note(implement_tmpdir: Path, note_text: str, *, head_sha: str, metadata: dict[str, str], base_ref: str) -> None:
    """Write the durable Phase B note and HEAD-pinned metadata."""
    _write_text_atomic(durable_note_path(implement_tmpdir), note_text)
    meta = "\n".join(
        [
            "STATUS=present",
            f"HEAD_SHA={_env_escape(head_sha)}",
            f"ASSESSED_HEAD_SHA={_env_escape(metadata.get('ASSESSED_HEAD_SHA', ''))}",
            f"DIFF_FINGERPRINT={_env_escape(metadata.get('DIFF_FINGERPRINT', ''))}",
            f"BASE_REF={_env_escape(base_ref or metadata.get('BASE_REF', ''))}",
            f"WRITTEN_AT={datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')}",
            "",
        ]
    )
    _write_text_atomic(_durable_meta_path(implement_tmpdir), meta)


def _live_fingerprint(repo_root: Path | None, resolved_base: str) -> str | None:
    """Materialize the live implementation diff and return its fingerprint, or None when it cannot be computed."""
    if repo_root is None or not resolved_base:
        return None
    remote, ref = resolved_base.split("/", 1) if "/" in resolved_base else ("origin", resolved_base)
    try:
        return diff_fingerprint(
            materialize_implementation_diff(repo_root, base_remote=remote, base_ref=ref),
        )
    except RuntimeError as exc:
        print(f"ARCHITECTURAL_GUIDELINES_WARNING={str(exc).replace(chr(10), ' ')}", file=sys.stderr)
        return None


def _staged_fingerprint_valid(
    implement_tmpdir: Path,
    metadata: dict[str, str],
    *,
    base_ref: str,
    repo_root: Path | None = None,
) -> bool:
    stored_fp = metadata.get("DIFF_FINGERPRINT", "")
    if not stored_fp:
        return False
    resolved_base = (base_ref or metadata.get("BASE_REF", "")).strip()
    if repo_root is not None and resolved_base:
        live_fp = _live_fingerprint(repo_root, resolved_base)
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
        implement_tmpdir,
        metadata,
        base_ref=base_ref,
        repo_root=Path(repo_root).resolve() if repo_root is not None else None,
    ):
        return False
    try:
        note_text = staged.read_text(encoding="utf-8")
    except OSError:
        return False
    try:
        write_implement_note(implement_tmpdir, note_text, head_sha=head_sha, metadata=metadata, base_ref=base_ref)
    except OSError:
        return False
    return True


def invalidate_implement_note(implement_tmpdir: Path) -> None:
    """Clear staged and durable guideline note artifacts."""
    for name in (
        LEGACY_WARNING,
        LEGACY_WARNING_ENV,
        STAGED_ASSESSMENT,
        STAGED_ASSESSMENT_ENV,
        MATERIALIZED_DIFF,
        MATERIALIZE_ENV,
        DURABLE_NOTE,
        DURABLE_NOTE_ENV,
    ):
        path = implement_tmpdir / name
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass


def durable_note_metadata(implement_tmpdir: Path) -> dict[str, str]:
    """Return durable-note sidecar metadata when present."""
    return _read_env(_durable_meta_path(implement_tmpdir))


def note_consumable(implement_tmpdir: Path, head_sha: str) -> bool:
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
    live_fp = _live_fingerprint(root, base_ref)
    if live_fp is None:
        return True
    return live_fp != stored_fp


def _bool_arg(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _current_head(repo_root: Path | None = None) -> str:
    cmd = ["git"]
    if repo_root is not None:
        cmd.extend(["-C", str(repo_root)])
    cmd.extend(["rev-parse", "HEAD"])
    completed = subprocess.run(cmd, text=True, capture_output=True, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


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
    base_remote, base_ref = resolve_diff_base(forked_target=_bool_arg(args.forked_target))
    base_label = f"{base_remote}/{base_ref}"
    try:
        diff_text = materialize_implementation_diff(repo_root, base_remote=base_remote, base_ref=base_ref)
    except RuntimeError as exc:
        print("ARCHITECTURAL_GUIDELINES_DIFF_STATUS=failed")
        print(f"ARCHITECTURAL_GUIDELINES_WARNING={str(exc).replace(chr(10), ' ')}")
        return 1
    fingerprint = diff_fingerprint(diff_text)
    output_path: Path | None = Path(args.output) if args.output else None
    if args.implement_tmpdir:
        tmpdir = Path(args.implement_tmpdir)
        output_path = output_path or _diff_path(tmpdir)
        meta_path = tmpdir / MATERIALIZE_ENV
        _write_text_atomic(
            meta_path,
            "\n".join(
                [
                    f"BASE_REF={_env_escape(base_label)}",
                    f"DIFF_FINGERPRINT={_env_escape(fingerprint)}",
                    "",
                ]
            ),
        )
    if output_path is not None:
        _write_text_atomic(output_path, diff_text)
    print("ARCHITECTURAL_GUIDELINES_DIFF_STATUS=ok")
    print(f"ARCHITECTURAL_GUIDELINES_BASE_REF={base_label}")
    print(f"ARCHITECTURAL_GUIDELINES_DIFF_FINGERPRINT={fingerprint}")
    sys.stdout.write(issue_wire.emit_untrusted_content_block(tag="architectural_guidelines_diff", text=diff_text))
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
        Path(args.implement_tmpdir),
        assessment_text,
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
    invalidate_implement_note(Path(args.implement_tmpdir))
    print("ARCHITECTURAL_GUIDELINES_INVALIDATE_STATUS=ok")
    return 0
