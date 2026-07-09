# pyright: reportUnusedCallResult=false
"""Per-clone progress breadcrumb writer for larch statuslines."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import os
import stat
import time
from pathlib import Path

from larch.git.repo_roots import consumer_repo_root
from larch import io as larch_io


PROGRESS_DIRNAME = "progress"
PROGRESS_SUFFIX = ".log"
_HASH_HEX_CHARS = 16
_NEWLINE_CHARS = "\n\r"


def _cache_home() -> Path:
    override = os.environ.get("LARCH_TEST_CACHE_HOME")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".cache"


def progress_root() -> Path:
    return _cache_home() / "larch" / PROGRESS_DIRNAME


def _canonical_repo_root(repo_root: str | Path) -> Path:
    path = Path(repo_root).expanduser()
    try:
        return path.resolve()
    except OSError:
        return path.absolute()


def progress_path(repo_root: str | Path) -> Path:
    """Return the clone-scoped breadcrumb path for ``repo_root``."""
    canonical_root = consumer_repo_root(Path(repo_root).expanduser()) or _canonical_repo_root(repo_root)
    canonical = str(canonical_root)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:_HASH_HEX_CHARS]
    return progress_root() / f"{digest}{PROGRESS_SUFFIX}"


def _reject_line_part(value: object, *, label: str) -> str:
    text = str(value).strip()
    if not text:
        msg = f"{label} must be non-empty"
        raise ValueError(msg)
    if "\t" in text or any(ch in text for ch in _NEWLINE_CHARS):
        msg = f"{label} must be one line without tabs"
        raise ValueError(msg)
    if label == "text" and "://" in text:
        msg = "text must identify entities by number, not URL"
        raise ValueError(msg)
    return text


def breadcrumb_line(*, skill: str, step: str, text: str) -> str:
    skill_text = _reject_line_part(skill, label="skill")
    step_text = _reject_line_part(step, label="step")
    body = _reject_line_part(text, label="text")
    return f"[{skill_text} {step_text}] {body}\n"


def append_breadcrumb(repo_root: str | Path, skill: str, step: str, text: str) -> bool:
    """Append one breadcrumb, returning ``False`` on any best-effort failure."""
    try:
        line = breadcrumb_line(skill=skill, step=step, text=text)
        path = progress_path(repo_root)
        larch_io.assert_no_symlink_path_or_ancestors(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(path, flags, 0o600)
        try:
            stat_result = os.fstat(fd)
            if not stat.S_ISREG(stat_result.st_mode):
                raise OSError(f"refusing non-regular breadcrumb target: {path}")
            with os.fdopen(fd, "a", encoding="utf-8") as handle:
                fd = -1
                _ = handle.write(line)
        finally:
            if fd >= 0:
                with contextlib.suppress(OSError):
                    os.close(fd)
        with contextlib.suppress(OSError):
            path.chmod(0o600)
    except (OSError, TypeError, ValueError):
        return False
    return True


def cleanup_old_progress_files(*, retention_days: int, root: Path | None = None, now: float | None = None) -> int:
    progress_dir = progress_root() if root is None else root
    if retention_days <= 0 or not progress_dir.is_dir() or progress_dir.is_symlink():
        return 0
    cutoff = (time.time() if now is None else now) - (retention_days * 86400)
    removed = 0
    for entry in progress_dir.glob(f"*{PROGRESS_SUFFIX}"):
        try:
            if entry.is_symlink() or not entry.is_file() or entry.stat().st_mtime >= cutoff:
                continue
            entry.unlink()
            removed += 1
        except OSError:
            continue
    return removed


def progress_note_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py progress note")
    _ = parser.add_argument("--repo-root", default=str(Path.cwd()))
    _ = parser.add_argument("--skill", required=True)
    _ = parser.add_argument("--step", required=True)
    _ = parser.add_argument("text", nargs="+")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    _ = append_breadcrumb(args.repo_root, args.skill, args.step, " ".join(args.text))
    return 0
