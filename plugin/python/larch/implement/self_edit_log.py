"""Self-edit attribution log for ``/implement`` (issue #6876).

File-mutating subprocesses spawned by ``/implement`` — the ``checks repair-loop``
lint-fix tiers and the Step 3 pre-commit ruff autofix — edit tracked files in
place. Those edits carry no attribution the orchestrator can consult, so an
observed between-action file change can be misattributed to a concurrent or
external runner, producing a false alarm and an unnecessary operator halt.

Each mutating subprocess records the repo-relative paths it changed here (one
row per path: recorded epoch seconds, source, path, post-edit sha256). The
orchestrator consults the log via ``checks self-edit-log`` before ever
concluding that a working-tree change came from another runner: process
introspection (``ps``) and ``stat`` mtime cannot attribute an edit once the
spawning subprocess has exited, so the log is the authority.

Stdlib-only. Writes land under ``$IMPLEMENT_TMPDIR`` and are consumed by the same
session, so paths are stored verbatim (not routed through ``redact.redact``,
which would strip the tmpdir path literals the orchestrator needs to match).
"""

from __future__ import annotations

import contextlib
import hashlib
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

SELF_EDIT_LOG_NAME: Final = "self-edit-log.tsv"
_FIELDS: Final = ("recorded_epoch_s", "source", "path", "post_sha256")
_HEADER_LINE: Final = "\t".join(_FIELDS) + "\n"
_FIELD_COUNT: Final = len(_FIELDS)
_SOURCE_MAX_LEN: Final = 64
_SOURCE_SANITIZE_RE: Final = re.compile(r"[^A-Za-z0-9_.:@/-]")


@dataclass(frozen=True)
class SelfEditRecord:
    recorded_epoch_s: int
    source: str
    path: str
    post_sha256: str


def self_edit_log_path(tmpdir: str | Path) -> Path:
    return Path(tmpdir) / SELF_EDIT_LOG_NAME


def normalize_path(value: str) -> str:
    """Strip TSV-hostile control characters so a path round-trips exactly.

    Applied to every recorded path and to a ``show --path`` query so the two
    match on the same normalized form.
    """
    return value.replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()


def _sanitize_source(source: str) -> str:
    cleaned = _SOURCE_SANITIZE_RE.sub("-", source.strip())[:_SOURCE_MAX_LEN]
    return cleaned or "unknown"


def file_sha256(repo_root: str | Path, path: str) -> str:
    """sha256 of a repo-relative file, or a bounded sentinel when unreadable."""
    try:
        target = Path(repo_root) / path
        if not target.is_file() or target.is_symlink():
            return "missing"
        return hashlib.sha256(target.read_bytes()).hexdigest()
    except OSError:
        return "unreadable"


def digest_paths(repo_root: str | Path, paths: Iterable[str]) -> dict[str, str]:
    """Map each repo-relative path to its current sha256 (see ``file_sha256``)."""
    root = Path(repo_root)
    return {path: file_sha256(root, path) for path in paths}


def _append_rows(path: Path, rows: list[tuple[int, str, str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        return
    needs_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8") as handle:
        if needs_header:
            _ = handle.write(_HEADER_LINE)
        for epoch_s, source, rel_path, sha in rows:
            _ = handle.write(f"{epoch_s}\t{source}\t{rel_path}\t{sha}\n")
    with contextlib.suppress(OSError):
        path.chmod(0o600)


def record_self_edits(
    *,
    tmpdir: str | Path,
    source: str,
    paths: Iterable[str],
    repo_root: str | Path,
    now_epoch_s: int | None = None,
) -> int:
    """Append one attribution row per changed path. Returns the row count.

    Best-effort: never raises, so a checks/repair-loop caller is never disrupted
    by logging. Returns 0 (nothing recorded) when the tmpdir is unusable, no
    paths are supplied, or any write fails.
    """
    written = 0
    with contextlib.suppress(Exception):
        tmp = Path(tmpdir)
        if not tmp.is_dir() or tmp.is_symlink():
            return 0
        epoch_s = int(time.time()) if now_epoch_s is None else int(now_epoch_s)
        source_token = _sanitize_source(source)
        rows: list[tuple[int, str, str, str]] = []
        seen: set[str] = set()
        for raw in paths:
            rel = normalize_path(str(raw))
            if not rel or rel in seen:
                continue
            seen.add(rel)
            rows.append((epoch_s, source_token, rel, file_sha256(repo_root, rel)))
        if not rows:
            return 0
        _append_rows(self_edit_log_path(tmp), rows)
        written = len(rows)
    return written


def read_self_edits(tmpdir: str | Path) -> list[SelfEditRecord]:
    """Parse recorded attribution rows; tolerant of a missing/partial log."""
    path = self_edit_log_path(tmpdir)
    records: list[SelfEditRecord] = []
    try:
        if not path.is_file() or path.is_symlink():
            return []
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    header = _HEADER_LINE.rstrip("\n")
    for line in text.splitlines():
        if not line or line == header:
            continue
        parts = line.split("\t")
        if len(parts) != _FIELD_COUNT:
            continue
        epoch_raw, source, rel_path, sha = parts
        try:
            epoch_s = int(epoch_raw)
        except ValueError:
            continue
        records.append(
            SelfEditRecord(recorded_epoch_s=epoch_s, source=source, path=rel_path, post_sha256=sha)
        )
    return records
