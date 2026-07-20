"""Shared safe helpers for larch run-log corpus walks."""

from __future__ import annotations

import json
import os
import re
import stat
import tarfile
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, cast

from larch.report import run_log_sync, storage_config
from larch.report.report_tokens_models import safe_int

DEFAULT_MANIFEST_CANDIDATES: tuple[str, ...] = ("manifest.json", "run-manifest.json")
RoundSort = Literal["numeric", "lexical"]
_ROUND_DIR_RE = re.compile(r"^round-(\d+)$")
_ROUND_IN_NAME_RE = re.compile(r"round-(\d+)")
_DESIGN_CLASSIFICATION_PARTS = 3
_IMPLEMENT_CLASSIFICATION_PARTS = 2


class WalkWarningKind(StrEnum):
    """Structured warning kinds for ``safe_child_run_dirs`` callers."""

    ROOT_MISSING = "root_missing"
    ROOT_UNREADABLE = "root_unreadable"
    CHILD_SYMLINK = "child_symlink"
    CHILD_UNRESOLVABLE = "child_unresolvable"
    CHILD_ESCAPES = "child_escapes"
    CHILD_NOT_DIR = "child_not_dir"


class RunLogCorpusError(RuntimeError):
    """A repository analyzer could not prepare its synchronized corpus."""


@dataclass(frozen=True)
class WalkWarning:
    kind: WalkWarningKind
    message: str
    path: Path | None = None


def _warn(warn: Callable[[str], None] | None, message: str) -> None:
    if warn is not None:
        warn(message)


def _emit_walk_warning(
    warning: WalkWarning,
    *,
    warn: Callable[[str], None] | None,
    on_warning: Callable[[WalkWarning], None] | None,
) -> None:
    if on_warning is not None:
        on_warning(warning)
    _warn(warn, warning.message)


def _raise_walk_error(exc: OSError) -> None:
    raise exc


def _is_safe_log_root(
    log_base: Path,
    *,
    warn: Callable[[str], None] | None,
    on_warning: Callable[[WalkWarning], None] | None,
) -> bool:
    try:
        unsafe_root = log_base.is_symlink() or not log_base.is_dir()
    except (OSError, RuntimeError) as exc:
        unsafe_root = True
        root_error = str(exc)
    else:
        root_error = ""
    if not unsafe_root:
        return True
    detail = f": {root_error}" if root_error else ""
    _emit_walk_warning(
        WalkWarning(
            kind=WalkWarningKind.ROOT_MISSING,
            message=f"log root {log_base} is missing, not a directory, or a symlink{detail}; no run logs scanned",
            path=log_base,
        ),
        warn=warn,
        on_warning=on_warning,
    )
    return False


def load_run_manifest(run_dir: Path, warn: Callable[[str], None] | None = None) -> dict[str, Any] | None:
    """Return an accepted run manifest, or ``None`` after optional warnings.

    Acceptance is limited to a non-symlink ``manifest.json`` with a positive
    numeric ``issue_number``. A ``run-manifest.json`` alone never satisfies this
    gate.
    """
    manifest_path = run_dir / "manifest.json"
    parsed: object | None = None
    message = ""
    if manifest_path.is_symlink():
        message = f"manifest.json at {manifest_path} is a symlink; skipping"
    elif not manifest_path.is_file():
        message = f"manifest for {run_dir} is missing; skipping"
    else:
        try:
            parsed = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            message = f"invalid manifest.json at {manifest_path}: {exc}; skipping"
    if message:
        _warn(warn, message)
        return None
    if not isinstance(parsed, dict):
        _warn(warn, f"manifest for {run_dir} is not a JSON object; skipping")
        return None
    manifest = cast("dict[str, object]", parsed)
    accepted = bool(manifest) and safe_int(value=manifest.get("issue_number")) > 0
    if accepted:
        return {str(key): value for key, value in manifest.items()}
    if not manifest:
        _warn(warn, f"manifest for {run_dir} is empty and lacks numeric issue_number; skipping")
    else:
        _warn(warn, f"manifest for {run_dir} lacks numeric issue_number; skipping")
    return None


def is_valid_run_dir(run_dir: Path, warn: Callable[[str], None] | None = None) -> bool:
    """Return True when ``run_dir`` has an accepted run manifest."""
    return load_run_manifest(run_dir, warn=warn) is not None


def safe_child_run_dirs(
    log_base: Path,
    warn: Callable[[str], None] | None = None,
    *,
    on_warning: Callable[[WalkWarning], None] | None = None,
) -> list[Path]:
    """Return symlink-safe, contained child directories under ``log_base``.

    Distinguishes root resolution failures (``ROOT_MISSING``) from child
    enumeration ``OSError`` (``ROOT_UNREADABLE``) so callers can preserve
    distinct counters. Does not require an accepted ``manifest.json``.
    """
    dirs: list[Path] = []
    if not _is_safe_log_root(log_base, warn=warn, on_warning=on_warning):
        return []
    try:
        resolved_base = log_base.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        _emit_walk_warning(
            WalkWarning(
                kind=WalkWarningKind.ROOT_MISSING,
                message=f"log root {log_base} is missing or unreadable: {exc}; no run logs scanned",
                path=log_base,
            ),
            warn=warn,
            on_warning=on_warning,
        )
        return []
    try:
        children = sorted(log_base.glob("*"))
    except (OSError, RuntimeError) as exc:
        _emit_walk_warning(
            WalkWarning(
                kind=WalkWarningKind.ROOT_UNREADABLE,
                message=f"log root {log_base} could not be enumerated: {exc}; no run logs scanned",
                path=log_base,
            ),
            warn=warn,
            on_warning=on_warning,
        )
        return []
    for path in children:
        try:
            is_symlink = path.is_symlink()
            is_dir = path.is_dir()
        except (OSError, RuntimeError) as exc:
            _emit_walk_warning(
                WalkWarning(
                    kind=WalkWarningKind.CHILD_UNRESOLVABLE,
                    message=f"could not inspect run directory {path}: {exc}; skipping",
                    path=path,
                ),
                warn=warn,
                on_warning=on_warning,
            )
            continue
        if is_symlink:
            _emit_walk_warning(
                WalkWarning(
                    kind=WalkWarningKind.CHILD_SYMLINK,
                    message=f"run directory {path} is a symlink; skipping",
                    path=path,
                ),
                warn=warn,
                on_warning=on_warning,
            )
            continue
        if not is_dir:
            continue
        try:
            resolved = path.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            _emit_walk_warning(
                WalkWarning(
                    kind=WalkWarningKind.CHILD_UNRESOLVABLE,
                    message=f"could not resolve run directory {path}: {exc}; skipping",
                    path=path,
                ),
                warn=warn,
                on_warning=on_warning,
            )
            continue
        if not (resolved == resolved_base or resolved_base in resolved.parents):
            _emit_walk_warning(
                WalkWarning(
                    kind=WalkWarningKind.CHILD_ESCAPES,
                    message=f"run directory {path} resolves outside {log_base}; skipping",
                    path=path,
                ),
                warn=warn,
                on_warning=on_warning,
            )
            continue
        dirs.append(path)
    return dirs


def run_dirs(log_base: Path, warn: Callable[[str], None] | None = None) -> list[Path]:
    """Return symlink-safe, manifest-accepted child run directories."""
    return [path for path in safe_child_run_dirs(log_base, warn=warn) if is_valid_run_dir(path, warn=warn)]


def synchronize_run_log_corpus(
    *,
    request: run_log_sync.RunLogSyncRequest,
    store: run_log_sync.SyncObjectStore | None = None,
    environ: Mapping[str, str] | None = None,
) -> run_log_sync.RepositorySyncResult:
    """Synchronize once and return the repository's ordinary local-file corpus."""
    return run_log_sync.sync_repository_run_logs(
        request=request,
        store=store,
        environ=environ,
    )


def synchronized_run_log_root(
    *,
    request: run_log_sync.RunLogSyncRequest,
    store: run_log_sync.SyncObjectStore | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Synchronize once and expose the unpacked root for all later read waves."""
    return synchronize_run_log_corpus(
        request=request,
        store=store,
        environ=environ,
    ).corpus_root


def synchronized_repository_log_root(
    *,
    repo_root: Path,
    store: run_log_sync.SyncObjectStore | None = None,
    environ: Mapping[str, str] | None = None,
    cache_home: Path | None = None,
    state_home: Path | None = None,
) -> Path:
    """Load repository config, synchronize once, and return the cache log root."""
    try:
        storage_root: storage_config.StorageRoot = storage_config.load_storage_root(
            repo_root=repo_root,
            environ=environ,
        )
        return synchronized_run_log_root(
            request=run_log_sync.RunLogSyncRequest(
                repo_root=repo_root,
                storage_root=storage_root,
                cache_home=cache_home,
                state_home=state_home,
            ),
            store=store,
            environ=environ,
        )
    except (
        EOFError,
        OSError,
        RuntimeError,
        tarfile.TarError,
        TypeError,
        ValueError,
    ) as exc:
        raise RunLogCorpusError(f"run-log corpus sync failed: {exc}") from exc


def review_transcript_dirs(log_base: Path, warn: Callable[[str], None] | None = None) -> list[Path]:
    """Return review run directories with a safe transcript and no manifest requirement."""
    return [path for path in safe_child_run_dirs(log_base, warn=warn) if safe_transcript_path(path) is not None]


def safe_transcript_path(run_dir: Path) -> Path | None:
    """Return a contained regular session transcript path for an accepted run."""
    transcript = run_dir / "session-transcript.jsonl"
    if transcript.is_symlink() or not transcript.is_file():
        return None
    try:
        resolved_run = run_dir.resolve(strict=True)
        resolved_transcript = transcript.resolve(strict=True)
    except OSError:
        return None
    if resolved_transcript == resolved_run or resolved_run in resolved_transcript.parents:
        return transcript
    return None


def _normalize_manifest_candidates(manifest_candidates: Sequence[str] | None) -> tuple[str, ...]:
    if manifest_candidates is None:
        return DEFAULT_MANIFEST_CANDIDATES
    names = tuple(str(name) for name in manifest_candidates if str(name))
    return names or DEFAULT_MANIFEST_CANDIDATES


def _load_metadata_candidate(path: Path) -> dict[str, Any] | None:
    """Return a JSON object from a regular non-symlink candidate, else ``None``."""
    if path.is_symlink() or not path.is_file():
        return None
    try:
        parsed: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    return {str(key): value for key, value in cast("dict[str, object]", parsed).items()}


def _iter_metadata_objects(
    run_dir: Path,
    *,
    manifest_candidates: Sequence[str] | None,
) -> Iterator[dict[str, Any]]:
    for name in _normalize_manifest_candidates(manifest_candidates):
        data = _load_metadata_candidate(run_dir / name)
        if data is not None:
            yield data


def _timestamp_field(data: Mapping[str, Any], *keys: str) -> tuple[str, bool]:
    """Return a valid timestamp and whether a populated value was invalid."""
    for key in keys:
        value = data.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        if not isinstance(value, str):
            return "", True
        text = value.strip()
        try:
            _ = datetime.fromisoformat(text)
        except ValueError:
            return "", True
        return text, False
    return "", False


def run_started_at(
    run_dir: Path,
    *,
    allow_updated_at_fallback: bool = False,
    continue_on_empty: bool = False,
    manifest_candidates: Sequence[str] | None = None,
) -> str:
    """Return a started-at timestamp string from allowed manifest candidates.

    By default reads only ``started_at`` from the first valid manifest object.
    When ``allow_updated_at_fallback`` is true, an empty ``started_at`` may fall
    back to ``updated_at`` within that same object. When ``continue_on_empty`` is
    true, an empty result from a valid preferred object consults later allowed
    candidates; otherwise the first valid object stops the search.
    """
    for data in _iter_metadata_objects(run_dir, manifest_candidates=manifest_candidates):
        started, invalid_started = _timestamp_field(data, "started_at")
        if started:
            return started
        if allow_updated_at_fallback:
            updated, invalid_updated = _timestamp_field(data, "updated_at")
            if updated:
                return updated
            if invalid_started or invalid_updated:
                continue
        elif invalid_started:
            continue
        if not continue_on_empty:
            return ""
    return ""


def run_ended_at(
    run_dir: Path,
    *,
    continue_on_empty: bool = False,
    manifest_candidates: Sequence[str] | None = None,
) -> str:
    """Return an ended-at timestamp preserving ended/completed/updated precedence."""
    for data in _iter_metadata_objects(run_dir, manifest_candidates=manifest_candidates):
        ended, invalid_ended = _timestamp_field(data, "ended_at", "completed_at")
        if ended:
            return ended
        updated, invalid_updated = _timestamp_field(data, "updated_at")
        if updated:
            return updated
        if invalid_ended or invalid_updated:
            continue
        if not continue_on_empty:
            return ""
    return ""


def larch_version(
    run_dir: Path,
    *,
    continue_on_empty: bool = False,
    manifest_candidates: Sequence[str] | None = None,
) -> str:
    """Return ``larch_version`` text, or ``""`` when absent or invalid."""
    for data in _iter_metadata_objects(run_dir, manifest_candidates=manifest_candidates):
        value = data.get("larch_version")
        text = value.strip() if isinstance(value, str) else ""
        if text:
            if re.fullmatch(r"[vV]?\d+(?:\.\d+){0,2}(?:[-+][0-9A-Za-z.-]+)?", text):
                return text
            continue
        if not continue_on_empty:
            return ""
    return ""


def round_num_from_path(path: Path) -> int | None:
    """Return the round number embedded in a path, or ``None`` when absent."""
    for part in reversed(path.parts):
        match = _ROUND_DIR_RE.fullmatch(part)
        if match:
            return int(match.group(1))
    match = _ROUND_IN_NAME_RE.search(path.name)
    return int(match.group(1)) if match else None


def _sort_classification_paths(paths: list[Path], *, round_sort: RoundSort) -> list[Path]:
    if round_sort == "lexical":
        return sorted(paths)
    return sorted(
        paths,
        key=lambda path: (
            round_num_from_path(path) is None,
            round_num_from_path(path) if round_num_from_path(path) is not None else 0,
            path.as_posix(),
        ),
    )


def _is_classification_tsv_path(skill: str, relative: Path) -> bool:
    if skill == "design":
        return (
            len(relative.parts) == _DESIGN_CLASSIFICATION_PARTS
            and relative.parts[0] == "plan-review"
            and _ROUND_DIR_RE.fullmatch(relative.parts[1]) is not None
        )
    if skill == "implement":
        return (
            len(relative.parts) == _IMPLEMENT_CLASSIFICATION_PARTS
            and _ROUND_DIR_RE.fullmatch(relative.parts[0]) is not None
        )
    return False


def classification_tsv_paths(
    skill: str,
    run_dir: Path,
    *,
    round_sort: RoundSort = "numeric",
) -> list[Path]:
    """Return canonical classification TSV paths for one contained run directory."""
    if skill not in {"design", "implement", "review"}:
        return []
    paths: list[Path] = []
    try:
        canonical_run = run_dir.resolve(strict=True)
    except (OSError, RuntimeError):
        return []
    for path in iter_validated_run_files(run_dir, name="findings-classification.tsv", contain_root=run_dir.parent):
        try:
            relative = path.relative_to(canonical_run)
        except ValueError:
            continue
        if _is_classification_tsv_path(skill, relative):
            paths.append(path)
    if skill == "review":
        paths.extend(
            path
            for path in iter_validated_run_files(run_dir, name="", contain_root=run_dir.parent)
            if re.fullmatch(r"review-findings-classification-round-.*\.tsv", path.name) and path.parent == canonical_run
        )
    return _sort_classification_paths(paths, round_sort=round_sort)


def discover_classifications(
    log_root: Path,
    *,
    skills: Sequence[str] = ("design", "implement", "review"),
    round_sort: RoundSort = "numeric",
    warn: Callable[[str], None] | None = None,
    on_warning: Callable[[WalkWarning], None] | None = None,
) -> list[tuple[str, Path]]:
    """Discover canonical classification TSVs under safe child run directories.

    Returns stable ``(skill, path)`` pairs in skill order, then safe-child order,
    then the selected round sort. Does not recurse into non-canonical layouts.
    """
    rows: list[tuple[str, Path]] = []
    for skill in skills:
        skill_root = log_root / skill
        for run_dir in safe_child_run_dirs(skill_root, warn=warn, on_warning=on_warning):
            rows.extend(
                (skill, path)
                for path in classification_tsv_paths(skill, run_dir, round_sort=round_sort)
            )
    return rows


def discover_design_classification_paths(
    design_root: Path,
    *,
    warn: Callable[[str], None] | None = None,
    on_warning: Callable[[WalkWarning], None] | None = None,
) -> list[Path]:
    """Safely discover design classification TSVs, including non-canonical layouts.

    Walks only directories returned by ``safe_child_run_dirs``, then recursively
    inspects each validated run for ``findings-classification.tsv`` files.
    """
    paths: list[Path] = []
    for run_dir in safe_child_run_dirs(design_root, warn=warn, on_warning=on_warning):
        paths.extend(iter_validated_run_files(run_dir, name="findings-classification.tsv", contain_root=design_root))
    return sorted(paths)


def _assert_validated_run_dir(run_dir: Path, *, contain_root: Path) -> Path:
    """Resolve ``run_dir`` and require it to be a real directory (not a symlink)."""
    if run_dir.is_symlink():
        raise ValueError(f"validated run walk rejected symlink run directory: {run_dir}")
    try:
        resolved = run_dir.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"validated run walk could not resolve run directory {run_dir}: {exc}") from exc
    if not resolved.is_dir():
        raise ValueError(f"validated run walk requires a directory: {run_dir}")
    try:
        resolved_contain = contain_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"validated run walk could not resolve contain_root {contain_root}: {exc}") from exc
    if resolved.parent != resolved_contain:
        raise ValueError(f"validated run walk requires a direct safe child of {contain_root}: {run_dir}")
    if not any(child.resolve(strict=True) == resolved for child in safe_child_run_dirs(contain_root)):
        raise ValueError(f"validated run walk requires safe-child selection from {contain_root}: {run_dir}")
    return resolved


def iter_validated_run_walk(
    run_dir: Path,
    *,
    contain_root: Path,
) -> Iterator[tuple[Path, list[str], list[str]]]:
    """Yield ``(root, dirnames, filenames)`` under a validated run directory.

    ``contain_root`` must be the parent corpus directory used with
    ``safe_child_run_dirs``. Escaping descendants are omitted from the walk.
    This is not a corpus-root traversal API.
    """
    resolved_run = _assert_validated_run_dir(run_dir, contain_root=contain_root)
    try:
        resolved_contain = contain_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"validated run walk could not resolve contain_root {contain_root}: {exc}") from exc

    def _under_contain(path: Path) -> bool:
        try:
            resolved = path.resolve(strict=False)
            _ = resolved.relative_to(resolved_contain)
        except (OSError, RuntimeError, ValueError):
            return False
        return True

    if not _under_contain(resolved_run):
        raise ValueError(f"validated run walk rejected escaping run directory: {run_dir}")

    for root, dirnames, filenames in os.walk(resolved_run, followlinks=False, onerror=_raise_walk_error):
        root_path = Path(root)
        keep_dirs: list[str] = []
        for name in list(dirnames):
            child = root_path / name
            if child.is_symlink() or not _under_contain(child):
                continue
            keep_dirs.append(name)
        dirnames[:] = keep_dirs
        keep_files: list[str] = []
        for name in filenames:
            child = root_path / name
            if child.is_symlink() or not _under_contain(child):
                continue
            keep_files.append(name)
        yield root_path, dirnames, keep_files


def iter_validated_run_files(run_dir: Path, *, name: str, contain_root: Path) -> Iterator[Path]:
    """Yield regular contained files named ``name`` under a validated run directory."""
    for root_path, _dirnames, filenames in iter_validated_run_walk(run_dir, contain_root=contain_root):
        if name:
            if name in filenames:
                candidate = root_path / name
                try:
                    if stat.S_ISREG(candidate.lstat().st_mode):
                        yield candidate
                except OSError:
                    continue
        else:
            for filename in filenames:
                candidate = root_path / filename
                try:
                    if stat.S_ISREG(candidate.lstat().st_mode):
                        yield candidate
                except OSError:
                    continue


def validated_run_has_escape_symlink(run_dir: Path, *, contain_root: Path) -> bool:
    """Return True when a validated run contains a symlink that escapes ``contain_root``."""
    try:
        resolved_run = _assert_validated_run_dir(run_dir, contain_root=contain_root)
        resolved_contain = contain_root.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return True

    def _under_contain(path: Path) -> bool:
        try:
            _ = path.resolve(strict=False).relative_to(resolved_contain)
        except (OSError, RuntimeError, ValueError):
            return False
        return True

    if not _under_contain(resolved_run):
        return True
    try:
        for root, dirs, files in os.walk(run_dir, followlinks=False, onerror=_raise_walk_error):
            root_path = Path(root)
            for entry_name in list(dirs) + files:
                child = root_path / entry_name
                if child.is_symlink() and not _under_contain(child):
                    return True
    except (OSError, RuntimeError):
        return True
    return False


def validated_run_dir_bytes(run_dir: Path) -> int:
    """Return total bytes under a validated run directory, skipping escaping links."""
    total = 0
    for root_path, _dirnames, filenames in iter_validated_run_walk(run_dir, contain_root=run_dir.parent):
        for name in filenames:
            child = root_path / name
            try:
                total += child.stat().st_size
            except OSError:
                continue
    return total


# Back-compat private alias used by older in-tree call sites during migration.
_safe_child_run_dirs = safe_child_run_dirs
