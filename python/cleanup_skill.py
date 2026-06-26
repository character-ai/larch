# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Python entrypoint for /cleanup."""

from __future__ import annotations

import fnmatch
import os
import shutil
import sys
import time
from pathlib import Path

import env_file
from larch.core import proc

TMP_PATTERNS = (
    "claude-implement-*",
    "claude-fix-issue-*",
    "claude-review-*",
    "claudin-review-*",
    "claude-issue-test",
    "wait-reviewers-*",
    "test-health-empty-caller-env-*",
    "test-health-explicit-false-*",
    "test-health-explicit-true-*",
    "test-session-setup-*",
    "larch-*",
    "larch3-fresh",
    "larch3-plan-review-prompts.sh",
    "larch4-review.diff",
    "check-review-bogus.err",
    "commit-msg-*-review.txt",
    "commit-msg-review-*.txt",
    "cr-debug-design",
    "issue-*-design-comment.md",
)
SECONDS_PER_DAY = 86400
TMP_FALLBACK = "/tmp"  # noqa: S108 - parity with cleanup.sh preserved /tmp root


def _emit(*, key: str, value: object) -> None:
    print(f"{key}={value}")


def _warn(message: str) -> None:
    print(message, file=sys.stderr)


def _retention_days() -> int:
    raw = os.environ.get("LARCH_CLEANUP_RETENTION_DAYS", "7")
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    _warn(f"Warning: invalid LARCH_CLEANUP_RETENTION_DAYS='{raw}'; using 7.")
    return 7


def _session_count() -> int:
    result = proc.run(["pgrep", "-x", "claude"])
    if result.returncode != 0 or not result.stdout.strip():
        return 0
    return len([line for line in result.stdout.splitlines() if line.strip()])


def _should_remove_by_age(*, entry: Path, retention_days: int) -> bool:
    if not entry.is_dir() or entry.is_symlink():
        return False
    result = proc.run(["find", str(entry), "-maxdepth", "5", "-mtime", f"-{retention_days}", "-print", "-quit"])
    if result.returncode != 0:
        _warn(f"Warning: failed to scan session activity for '{entry}'; skipping deletion.")
        return False
    return not result.stdout.strip()


def _older_than(*, path: Path, days: int) -> bool:
    try:
        return path.stat().st_mtime < time.time() - (days * SECONDS_PER_DAY)
    except OSError:
        return False


def _cache_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / "larch" / "sessions"
    return Path.home() / ".cache" / "larch" / "sessions"


def _remove_entry(path: Path) -> bool:
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
    except OSError:
        return False
    return True


def _read_design_tmpdir(env_path: Path) -> str:
    values = env_file.read_env_file(env_path)
    return values.get("DESIGN_TMPDIR") or values.get("SESSION_TMPDIR") or ""


def run_main(argv: list[str]) -> int:
    if argv:
        _warn(f"Warning: cleanup run ignores arguments: {' '.join(argv)}")
    retention = _retention_days()
    _emit(key="SESSION_COUNT", value=_session_count())
    sessions_parent = _cache_dir()
    cache_removed = 0
    if sessions_parent.is_dir():
        try:
            entries: list[Path] = [entry for entry in sessions_parent.iterdir() if not entry.is_symlink()]
        except OSError:
            entries = []
            _warn(f"Warning: failed to enumerate '{sessions_parent}'; skipping cache cleanup.")
        for entry in entries:
            if _should_remove_by_age(entry=entry, retention_days=retention) and _remove_entry(entry):
                cache_removed += 1
    _emit(key="CACHE_REMOVED", value=cache_removed)
    tmp_removed = 0
    tmp_root = Path(os.environ.get("LARCH_TEST_TMP_ROOT") or TMP_FALLBACK)
    if tmp_root.is_dir():
        try:
            tmp_entries: list[Path] = list(tmp_root.iterdir())
        except OSError:
            tmp_entries = []
            _warn(f"Warning: failed to enumerate '{tmp_root}'; skipping /tmp cleanup.")
        for entry in tmp_entries:
            if entry.is_symlink() or not any(fnmatch.fnmatch(entry.name, pattern) for pattern in TMP_PATTERNS):
                continue
            remove_file = entry.is_file() and _older_than(path=entry, days=retention)
            remove_dir = entry.is_dir() and _older_than(path=entry, days=retention) and _should_remove_by_age(entry=entry, retention_days=retention)
            if (remove_file or remove_dir) and _remove_entry(entry):
                tmp_removed += 1
    _emit(key="TMP_REMOVED", value=tmp_removed)
    symlinks_removed = 0
    if sessions_parent.is_dir():
        for link in sessions_parent.glob("current-design-env-*.sh"):
            if not link.is_symlink():
                continue
            try:
                target = link.resolve(strict=True)
            except OSError:
                if _remove_entry(link):
                    symlinks_removed += 1
                continue
            design_tmpdir = _read_design_tmpdir(target)
            if (not design_tmpdir or not Path(design_tmpdir).is_dir()) and _remove_entry(link):
                symlinks_removed += 1
    _emit(key="SYMLINKS_REMOVED", value=symlinks_removed)
    pointers_removed = 0
    if sessions_parent.is_dir():
        for pointer in sessions_parent.glob("current-implement-env-*.sh"):
            if not pointer.is_file() or pointer.is_symlink():
                continue
            impl_tmpdir = ""
            try:
                for line in pointer.read_text(encoding="utf-8").splitlines():
                    if line.startswith("IMPLEMENT_TMPDIR="):
                        impl_tmpdir = line.removeprefix("IMPLEMENT_TMPDIR=")
                        break
            except OSError:
                impl_tmpdir = ""
            if (not impl_tmpdir or not Path(impl_tmpdir).is_dir()) and _remove_entry(pointer):
                pointers_removed += 1
    _emit(key="IMPLEMENT_POINTERS_REMOVED", value=pointers_removed)
    _warn("")
    _warn("Cleanup complete:")
    _warn(f"  ~/.cache/larch/sessions/: {cache_removed} entries removed")
    _warn(f"  /tmp (larch patterns):    {tmp_removed} entries removed")
    _warn(f"  dangling design-env links: {symlinks_removed} removed")
    _warn(f"  stale implement-env files: {pointers_removed} removed")
    return 0
