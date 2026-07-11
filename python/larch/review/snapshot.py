"""Pre-coder and self-review snapshot management for the review-and-fix subsystem.

All functions here operate on git working-tree state snapshots taken before
an external coder runs, so that coder edits can be distinguished from
pre-existing dirty state and reverted cleanly on failure.
"""
# ruff: noqa: PLR2004, S108, PERF401

from __future__ import annotations

import contextlib
import os
import zlib
from pathlib import Path
from typing import Literal

from larch import io as larch_io
from larch.core import config
from larch.review._raf_util import (
    _git_head,
    _git_output,
    _git_status_porcelain,
    _git_stdout,
    _run,
    _append_text,
)


def _read_text(path: Path) -> str:
    """Read a snapshot artifact without following symlinks."""
    return larch_io.read_trusted_text(path, root=path.parent, errors="replace")


def _write_text(*, path: Path, text: str) -> None:
    """Publish a snapshot artifact through the trusted writer."""
    larch_io.ensure_trusted_directory(path.parent)
    larch_io.trusted_atomic_write(path, text, root=path.parent)


def _write_post_coder_head(round_dir: Path, head: str) -> None:
    """Persist the post-coder commit through the trusted round artifact writer."""
    path = round_dir / "post-coder-head.txt"
    larch_io.ensure_trusted_directory(round_dir)
    larch_io.trusted_atomic_write(path, head + "\n", root=round_dir, mode=0o444)
    path.chmod(0o444)


def _read_post_coder_head(round_dir: Path) -> str:
    path = round_dir / "post-coder-head.txt"
    if not larch_io.trusted_file_present(path, root=round_dir):
        return ""
    return larch_io.read_trusted_text(path, root=round_dir, errors="replace").strip()


def _validate_snapshot_root(path: Path) -> Path:
    return larch_io.validate_trusted_directory(path)


def pre_coder_snapshot_dir(round_dir: Path) -> Path:
    round_dir = round_dir.resolve()
    parent_abs = round_dir.parent.resolve()
    pwd_abs = Path.cwd().resolve()
    under_pwd = parent_abs == pwd_abs
    if not under_pwd:
        try:
            parent_abs.relative_to(pwd_abs)
            under_pwd = True
        except ValueError:
            under_pwd = False
    if under_pwd:
        tmp = Path(os.environ.get(config.ENV_TMPDIR, "/tmp")).resolve()
        hash_val = zlib.crc32(str(parent_abs).encode()) & 0xFFFFFFFF
        return tmp / "larch-pre-coder-snapshots" / str(hash_val) / round_dir.name
    return parent_abs / ".pre-coder-snapshots" / round_dir.name


def _clear_stale_pre_coder_snapshot_artifacts(snap_dir: Path) -> None:
    _validate_snapshot_root(snap_dir)
    for name in (
        "pre-coder-head.txt",
        "pre-coder-tracked-paths.txt",
        "pre-coder-untracked-paths.txt",
        "attempt-pre-tracked-paths.txt",
        "attempt-pre-untracked-paths.txt",
    ):
        artifact = snap_dir / name
        if artifact.exists() or artifact.is_symlink():
            if not larch_io.trusted_file_present(artifact, root=snap_dir):
                raise OSError(
                    f"snapshot artifact disappeared during cleanup: {artifact}"
                )
            artifact.unlink()
    for dirname in ("pre-coder-path-diffs", "attempt-pre-path-diffs"):
        diffs = snap_dir / dirname
        if diffs.exists() or diffs.is_symlink():
            larch_io.validate_trusted_directory(diffs, root=snap_dir)
            for artifact in diffs.iterdir():
                if not larch_io.trusted_file_present(artifact, root=diffs):
                    raise OSError(f"unsafe snapshot patch artifact: {artifact}")
                artifact.unlink()
            diffs.rmdir()


def _harden_pre_coder_snapshot_perms(snap_dir: Path) -> None:
    for path in snap_dir.rglob("*"):
        if path.is_file():
            with contextlib.suppress(OSError):
                path.chmod(0o444)


def _capture_round_tracked_paths() -> list[str]:
    seen: set[str] = set()
    paths: list[str] = []
    for subargs in (["diff", "--name-only"], ["diff", "--name-only", "--cached"]):
        for line in _git_output(subargs).splitlines():
            if line and line not in seen:
                seen.add(line)
                paths.append(line)
    return paths


def _capture_round_untracked_paths() -> list[str]:
    result = _run(["git", "ls-files", "--others", "--exclude-standard", "-z"])
    if result.returncode == 0:
        return [path for path in result.stdout.split("\0") if path]
    paths: list[str] = []
    for line in _git_output(["status", "--porcelain"]).splitlines():
        if line.startswith("??"):
            path = line[3:].strip()
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            if path and not path.endswith("/"):
                paths.append(path)
    return paths


def _snapshot_mode(round_dir: Path) -> Literal["full", "head_untracked", "missing"]:
    snap_dir = pre_coder_snapshot_dir(round_dir)
    if not snap_dir.exists() and not snap_dir.is_symlink():
        return "missing"
    _validate_snapshot_root(snap_dir)
    tracked = larch_io.trusted_file_present(
        snap_dir / "pre-coder-tracked-paths.txt", root=snap_dir
    )
    head = larch_io.trusted_file_present(snap_dir / "pre-coder-head.txt", root=snap_dir)
    untracked = larch_io.trusted_file_present(
        snap_dir / "pre-coder-untracked-paths.txt", root=snap_dir
    )
    if tracked and head and untracked:
        snapshot_head = _read_text(snap_dir / "pre-coder-head.txt").strip()
        if not snapshot_head:
            raise OSError(f"invalid pre-coder snapshot head: {snap_dir}")
        paths = [
            line
            for line in _read_text(snap_dir / "pre-coder-tracked-paths.txt").splitlines()
            if line
        ]
        safe_names = [_safe_patch_name(path) for path in paths]
        if len(paths) != len(set(paths)) or len(safe_names) != len(set(safe_names)):
            raise OSError(f"invalid pre-coder snapshot inventory: {snap_dir}")
        diffs = larch_io.validate_trusted_directory(
            snap_dir / "pre-coder-path-diffs", root=snap_dir
        )
        expected = {
            f"{_safe_patch_name(path)}{suffix}"
            for path in paths
            for suffix in (".patch", ".cached.patch")
        }
        actual: set[str] = set()
        for artifact in diffs.iterdir():
            if not larch_io.trusted_file_present(artifact, root=diffs):
                raise OSError(f"unsafe snapshot patch artifact: {artifact}")
            actual.add(artifact.name)
            _ = larch_io.read_trusted_text(artifact, root=diffs, errors="strict")
        if actual != expected:
            raise OSError(f"incomplete pre-coder snapshot patches: {snap_dir}")
        return "full"
    if head and untracked and not tracked:
        return "head_untracked"
    if tracked or head or untracked:
        raise OSError(f"incomplete pre-coder snapshot: {snap_dir}")
    return "missing"


def _read_pre_coder_untracked_baseline(snap_dir: Path) -> set[str]:
    baseline = snap_dir / "pre-coder-untracked-paths.txt"
    if not baseline.is_file():
        return set()
    return {line for line in _read_text(baseline).splitlines() if line}


def _ensure_pre_coder_untracked_baseline(round_dir: Path, *, mode: str) -> None:
    if mode != "head_untracked":
        return
    snap_dir = pre_coder_snapshot_dir(round_dir)
    baseline = snap_dir / "pre-coder-untracked-paths.txt"
    if baseline.exists():
        return
    larch_io.ensure_trusted_directory(snap_dir)
    _write_text(path=baseline, text="")
    with contextlib.suppress(OSError):
        baseline.chmod(0o444)


def _safe_patch_name(path: str) -> str:
    return path.replace("/", "__").replace("\\", "__")


def _path_exists_at_ref(*, pre_head: str, path: str) -> bool:
    if not pre_head:
        return False
    return _run(["git", "cat-file", "-e", f"{pre_head}:{path}"]).returncode == 0


def _tracked_paths_vs_ref(pre_head: str) -> list[str]:
    if not pre_head:
        return _capture_round_tracked_paths()
    seen: set[str] = set()
    paths: list[str] = []
    for subargs in (
        ["diff", "--name-only", pre_head],
        ["diff", "--cached", "--name-only", pre_head],
    ):
        for path in _git_output(subargs).splitlines():
            if path and path not in seen:
                seen.add(path)
                paths.append(path)
    return paths


def _restore_path_to_ref(*, pre_head: str, path: str) -> None:
    if not pre_head:
        return
    if _path_exists_at_ref(pre_head=pre_head, path=path):
        _run(["git", "checkout", pre_head, "--", path])
        return
    _run(["git", "restore", "--staged", "--", path])
    target = Path(path)
    if target.exists() or target.is_symlink():
        with contextlib.suppress(OSError):
            target.unlink()


def _apply_patch_file(
    path: Path, *, cached: bool = False, log: Path | None = None
) -> bool:
    if not path.is_file() or not path.stat().st_size:
        return True
    argv = ["git", "apply"]
    if cached:
        argv.append("--cached")
    argv.append(str(path))
    result = _run(argv)
    if result.returncode != 0:
        if log is not None:
            _append_text(
                path=log,
                text=f"git apply failed ({path.name}): {result.stderr}{result.stdout}\n",
            )
        return False
    return True


def _remove_untracked_delta_paths(paths: list[str]) -> None:
    repo = Path.cwd().resolve()
    parents: set[Path] = set()
    for raw in paths:
        if not raw:
            continue
        rel = Path(raw)
        if rel.is_absolute():
            try:
                rel = rel.relative_to(repo)
            except ValueError:
                continue
        if not rel.parts or ".git" in rel.parts:
            continue
        candidate = repo / rel
        try:
            candidate.parent.resolve().relative_to(repo)
        except (OSError, ValueError):
            continue
        if candidate.is_symlink() or candidate.exists():
            with contextlib.suppress(OSError):
                candidate.unlink()
        parent = candidate.parent
        while parent != repo and repo in (parent, *parent.parents):
            parents.add(parent)
            parent = parent.parent
    for parent in sorted(parents, key=lambda item: len(item.parts), reverse=True):
        if parent == repo or parent.name == ".git":
            continue
        with contextlib.suppress(OSError):
            parent.rmdir()


def _snapshot_pre_coder_tracked_state(
    *, _round_dir: Path, pre_head: str, snap_dir: Path
) -> None:
    paths_file = snap_dir / "pre-coder-tracked-paths.txt"
    diffs_dir = snap_dir / "pre-coder-path-diffs"
    larch_io.ensure_trusted_directory(diffs_dir)
    tracked = _capture_round_tracked_paths()
    _write_text(path=paths_file, text="\n".join(tracked) + ("\n" if tracked else ""))
    untracked = _capture_round_untracked_paths()
    _write_text(
        path=snap_dir / "pre-coder-untracked-paths.txt",
        text="\n".join(untracked) + ("\n" if untracked else ""),
    )
    for path in tracked:
        safe = _safe_patch_name(path)
        wt = diffs_dir / f"{safe}.patch"
        idx = diffs_dir / f"{safe}.cached.patch"
        _write_text(path=wt, text=_git_stdout(["diff", pre_head, "--", path]))
        _write_text(
            path=idx, text=_git_stdout(["diff", "--cached", pre_head, "--", path])
        )


def _write_attempt_pre_tracked_paths(
    *, round_dir: Path, pre_head: str, mode: str
) -> None:
    snap_dir = pre_coder_snapshot_dir(round_dir)
    larch_io.ensure_trusted_directory(snap_dir)
    tracked = _capture_round_tracked_paths()
    _write_text(
        path=snap_dir / "attempt-pre-tracked-paths.txt",
        text="\n".join(tracked) + ("\n" if tracked else ""),
    )
    diffs_dir = snap_dir / "attempt-pre-path-diffs"
    if diffs_dir.exists() or diffs_dir.is_symlink():
        larch_io.validate_trusted_directory(diffs_dir, root=snap_dir)
        for artifact in diffs_dir.iterdir():
            if not larch_io.trusted_file_present(artifact, root=diffs_dir):
                raise OSError(f"unsafe snapshot patch artifact: {artifact}")
            artifact.unlink()
    else:
        larch_io.ensure_trusted_directory(diffs_dir)
    for path in tracked:
        safe = _safe_patch_name(path)
        _write_text(
            path=diffs_dir / f"{safe}.patch",
            text=_git_stdout(["diff", pre_head, "--", path]),
        )
        _write_text(
            path=diffs_dir / f"{safe}.cached.patch",
            text=_git_stdout(["diff", "--cached", pre_head, "--", path]),
        )
    if mode == "head_untracked":
        untracked = _capture_round_untracked_paths()
        _write_text(
            path=snap_dir / "attempt-pre-untracked-paths.txt",
            text="\n".join(untracked) + ("\n" if untracked else ""),
        )


def _path_matches_pre_coder_snapshot(
    *, round_dir: Path, pre_head: str, path: str
) -> bool:
    snap_dir = pre_coder_snapshot_dir(round_dir)
    safe = _safe_patch_name(path)
    wt_snap = snap_dir / "pre-coder-path-diffs" / f"{safe}.patch"
    idx_snap = snap_dir / "pre-coder-path-diffs" / f"{safe}.cached.patch"
    if not wt_snap.is_file() or not idx_snap.is_file():
        return False
    wt_diff = _git_stdout(["diff", pre_head, "--", path])
    idx_diff = _git_stdout(["diff", "--cached", pre_head, "--", path])
    return wt_diff == _read_text(wt_snap) and idx_diff == _read_text(idx_snap)


def _path_matches_attempt_snapshot(
    *, round_dir: Path, pre_head: str, path: str
) -> bool:
    snap_dir = pre_coder_snapshot_dir(round_dir)
    safe = _safe_patch_name(path)
    wt_snap = snap_dir / "attempt-pre-path-diffs" / f"{safe}.patch"
    idx_snap = snap_dir / "attempt-pre-path-diffs" / f"{safe}.cached.patch"
    if not wt_snap.is_file() or not idx_snap.is_file():
        return False
    wt_diff = _git_stdout(["diff", pre_head, "--", path])
    idx_diff = _git_stdout(["diff", "--cached", pre_head, "--", path])
    return wt_diff == _read_text(wt_snap) and idx_diff == _read_text(idx_snap)


def _round_coder_delta_paths(
    *, round_dir: Path, diff_base: str, snapshot_head: str | None = None
) -> list[str]:
    snap_dir = pre_coder_snapshot_dir(round_dir)
    pre_tracked = snap_dir / "pre-coder-tracked-paths.txt"
    pre_tracked_set: set[str] = (
        {line for line in _read_text(pre_tracked).splitlines() if line}
        if pre_tracked.is_file()
        else set()
    )
    compare_head = snapshot_head if snapshot_head is not None else diff_base
    deltas: list[str] = []
    seen: set[str] = set()
    for path in _tracked_paths_vs_ref(diff_base):
        if not path or path in seen:
            continue
        if path in pre_tracked_set and _path_matches_pre_coder_snapshot(
            round_dir=round_dir, pre_head=compare_head, path=path
        ):
            continue
        seen.add(path)
        deltas.append(path)
    return deltas


def _round_coder_untracked_delta_paths(round_dir: Path) -> list[str]:
    snap_dir = pre_coder_snapshot_dir(round_dir)
    pre_untracked = _read_pre_coder_untracked_baseline(snap_dir)
    return [
        path for path in _capture_round_untracked_paths() if path not in pre_untracked
    ]


def _round_attempt_untracked_delta_paths(round_dir: Path) -> list[str]:
    snap_dir = pre_coder_snapshot_dir(round_dir)
    baseline = snap_dir / "attempt-pre-untracked-paths.txt"
    if not baseline.is_file():
        return (
            _round_coder_untracked_delta_paths(round_dir)
            if _snapshot_mode(round_dir) == "full"
            else []
        )
    pre_untracked = {line for line in _read_text(baseline).splitlines() if line}
    return [
        path for path in _capture_round_untracked_paths() if path not in pre_untracked
    ]


def _round_attempt_tracked_delta_paths(*, round_dir: Path, pre_head: str) -> list[str]:
    snap_dir = pre_coder_snapshot_dir(round_dir)
    paths_file = snap_dir / "attempt-pre-tracked-paths.txt"
    diffs_dir = snap_dir / "attempt-pre-path-diffs"
    if not paths_file.is_file() or not diffs_dir.is_dir():
        return []
    attempt_set = {line for line in _read_text(paths_file).splitlines() if line}
    deltas: list[str] = []
    seen: set[str] = set()
    for path in sorted(attempt_set):
        if path in seen:
            continue
        if not _path_matches_attempt_snapshot(
            round_dir=round_dir, pre_head=pre_head, path=path
        ):
            seen.add(path)
            deltas.append(path)
    for path in _tracked_paths_vs_ref(pre_head):
        if path in seen or path in attempt_set:
            continue
        seen.add(path)
        deltas.append(path)
    return deltas


def _restore_path_from_patches(
    *,
    pre_head: str,
    path: str,
    wt_patch: Path,
    idx_patch: Path,
    log: Path | None = None,
) -> bool:
    _restore_path_to_ref(pre_head=pre_head, path=path)
    wt_ok = _apply_patch_file(wt_patch, log=log)
    idx_ok = _apply_patch_file(idx_patch, cached=True, log=log)
    return wt_ok and idx_ok


def _restore_pre_coder_tracked_state(*, round_dir: Path, pre_head: str) -> None:
    snap_dir = pre_coder_snapshot_dir(round_dir)
    paths_file = snap_dir / "pre-coder-tracked-paths.txt"
    diffs_dir = snap_dir / "pre-coder-path-diffs"
    restore_log = round_dir / "coder-cleanup.log"
    if not paths_file.is_file() or not diffs_dir.is_dir():
        return
    tracked_set = {line for line in _read_text(paths_file).splitlines() if line}
    current = set(_tracked_paths_vs_ref(pre_head))
    for path in current - tracked_set:
        _restore_path_to_ref(pre_head=pre_head, path=path)
    for path in tracked_set:
        safe = _safe_patch_name(path)
        wt_snap = diffs_dir / f"{safe}.patch"
        idx_snap = diffs_dir / f"{safe}.cached.patch"
        if not _path_matches_pre_coder_snapshot(
            round_dir=round_dir, pre_head=pre_head, path=path
        ):
            _restore_path_from_patches(
                pre_head=pre_head,
                path=path,
                wt_patch=wt_snap,
                idx_patch=idx_snap,
                log=restore_log,
            )


def _restore_attempt_baseline_tracked_state(*, round_dir: Path, pre_head: str) -> None:
    snap_dir = pre_coder_snapshot_dir(round_dir)
    paths_file = snap_dir / "attempt-pre-tracked-paths.txt"
    diffs_dir = snap_dir / "attempt-pre-path-diffs"
    restore_log = round_dir / "coder-cleanup.log"
    if not paths_file.is_file() or not diffs_dir.is_dir():
        _restore_pre_coder_tracked_state(round_dir=round_dir, pre_head=pre_head)
        return
    attempt_set = {line for line in _read_text(paths_file).splitlines() if line}
    current = set(_tracked_paths_vs_ref(pre_head))
    for path in current - attempt_set:
        _restore_path_to_ref(pre_head=pre_head, path=path)
    for path in attempt_set:
        safe = _safe_patch_name(path)
        wt_snap = diffs_dir / f"{safe}.patch"
        idx_snap = diffs_dir / f"{safe}.cached.patch"
        if not _path_matches_attempt_snapshot(
            round_dir=round_dir, pre_head=pre_head, path=path
        ):
            _restore_path_from_patches(
                pre_head=pre_head,
                path=path,
                wt_patch=wt_snap,
                idx_patch=idx_snap,
                log=restore_log,
            )


def _has_coder_worktree_deltas(round_dir: Path, *, pre_head: str, mode: str) -> bool:
    return bool(
        _round_coder_delta_paths(round_dir=round_dir, diff_base=pre_head)
        or (
            mode in {"full", "head_untracked"}
            and _round_coder_untracked_delta_paths(round_dir)
        )
    )


def _verify_post_cleanup_state(
    round_dir: Path, *, pre_head: str, mode: str
) -> tuple[bool, str]:
    snap_dir = pre_coder_snapshot_dir(round_dir)
    details: list[str] = []
    if mode == "full":
        tracked_file = snap_dir / "pre-coder-tracked-paths.txt"
        pre_tracked: set[str] = (
            {line for line in _read_text(tracked_file).splitlines() if line}
            if tracked_file.is_file()
            else set()
        )
        for path in sorted(pre_tracked):
            if not _path_matches_pre_coder_snapshot(
                round_dir=round_dir, pre_head=pre_head, path=path
            ):
                details.append(f"pre-coder snapshot mismatch: {path}")
        coder_deltas = _round_coder_delta_paths(round_dir=round_dir, diff_base=pre_head)
        if coder_deltas:
            details.append("tracked coder deltas remain: " + ", ".join(coder_deltas))
        untracked = _round_coder_untracked_delta_paths(round_dir)
        if untracked:
            details.append("untracked coder deltas remain: " + ", ".join(untracked))
        for path in _git_output(
            ["diff", "--cached", "--name-only", pre_head]
        ).splitlines():
            if not path:
                continue
            safe = _safe_patch_name(path)
            expected = snap_dir / "pre-coder-path-diffs" / f"{safe}.cached.patch"
            if path not in pre_tracked or _git_stdout(
                ["diff", "--cached", pre_head, "--", path]
            ) != _read_text(expected):
                details.append(f"unexpected cached delta remains: {path}")
        return (not details, "\n".join(details))
    if mode == "head_untracked":
        _ensure_pre_coder_untracked_baseline(round_dir, mode=mode)
        attempt_file = snap_dir / "attempt-pre-tracked-paths.txt"
        attempt_paths: set[str] = (
            {line for line in _read_text(attempt_file).splitlines() if line}
            if attempt_file.is_file()
            else set()
        )
        for path in sorted(attempt_paths):
            if not _path_matches_attempt_snapshot(
                round_dir=round_dir, pre_head=pre_head, path=path
            ):
                details.append(f"attempt snapshot mismatch: {path}")
        untracked = _round_attempt_untracked_delta_paths(round_dir)
        if untracked:
            details.append("attempt untracked deltas remain: " + ", ".join(untracked))
        outside = [
            path
            for path in _round_attempt_tracked_delta_paths(
                round_dir=round_dir, pre_head=pre_head
            )
            if path not in attempt_paths
        ]
        if outside:
            details.append(
                "tracked deltas outside attempt remain: " + ", ".join(outside)
            )
        return (not details, "\n".join(details))
    dirty = _git_status_porcelain()
    if dirty:
        details.append("missing snapshot dirty tree remains: " + dirty)
    return (not details, "\n".join(details))


def _finalize_failed_cleanup(
    round_dir: Path, *, pre_head: str, mode: str, reason: str
) -> bool:
    log = round_dir / "coder-cleanup.log"
    _append_text(path=log, text=f"cleanup failure: {reason}\n")
    ok, detail = _verify_post_cleanup_state(round_dir, pre_head=pre_head, mode=mode)
    if not ok and detail:
        _append_text(path=log, text=detail + "\n")
    if mode == "full":
        _run(["git", "restore", "--staged", "."])
        _restore_pre_coder_tracked_state(round_dir=round_dir, pre_head=pre_head)
        _remove_untracked_delta_paths(_round_coder_untracked_delta_paths(round_dir))
    elif mode == "head_untracked":
        _ensure_pre_coder_untracked_baseline(round_dir, mode=mode)
        _run(["git", "restore", "--staged", "."])
        _remove_untracked_delta_paths(_round_attempt_untracked_delta_paths(round_dir))
        _restore_attempt_baseline_tracked_state(round_dir=round_dir, pre_head=pre_head)
    elif mode == "missing":
        restore = _run(["git", "restore", "--staged", "."])
        if restore.returncode != 0:
            _append_text(
                path=log,
                text="git restore --staged failed:\n" + restore.stderr + restore.stdout,
            )
        tracked = _run(["git", "restore", "."])
        if tracked.returncode != 0:
            _append_text(
                path=log, text="git restore failed:\n" + tracked.stderr + tracked.stdout
            )
    ok, detail = _verify_post_cleanup_state(round_dir, pre_head=pre_head, mode=mode)
    if not ok and detail:
        _append_text(
            path=log, text="post-finalize verification failed:\n" + detail + "\n"
        )
    status = _git_status_porcelain()
    if status:
        _append_text(
            path=log, text="remaining porcelain after finalize:\n" + status + "\n"
        )
    return False


def _cleanup_failed_coder_attempt(round_dir: Path) -> bool:
    mode = _snapshot_mode(round_dir)
    snap_dir = pre_coder_snapshot_dir(round_dir)
    pre_head = _read_text(snap_dir / "pre-coder-head.txt").strip()
    current_head = _git_head()
    if pre_head and current_head and current_head != pre_head:
        _append_text(
            path=round_dir / "coder-cleanup.log",
            text=f"stale pre-coder snapshot: pre_head={pre_head} current={current_head}\n",
        )
        return _finalize_failed_cleanup(
            round_dir,
            pre_head=pre_head,
            mode=mode,
            reason="stale pre-coder snapshot",
        )
    if mode == "missing" or not pre_head:
        return _finalize_failed_cleanup(
            round_dir, pre_head=pre_head, mode=mode, reason="missing pre-coder snapshot"
        )
    _ensure_pre_coder_untracked_baseline(round_dir, mode=mode)
    if not _has_coder_worktree_deltas(round_dir, pre_head=pre_head, mode=mode):
        return True
    _run(["git", "restore", "--staged", "."])
    if mode == "full":
        _restore_pre_coder_tracked_state(round_dir=round_dir, pre_head=pre_head)
        _remove_untracked_delta_paths(_round_coder_untracked_delta_paths(round_dir))
    elif mode == "head_untracked":
        _remove_untracked_delta_paths(_round_attempt_untracked_delta_paths(round_dir))
        _restore_attempt_baseline_tracked_state(round_dir=round_dir, pre_head=pre_head)
    ok, detail = _verify_post_cleanup_state(round_dir, pre_head=pre_head, mode=mode)
    if ok:
        return True
    if detail:
        _append_text(path=round_dir / "coder-cleanup.log", text=detail + "\n")
    return _finalize_failed_cleanup(
        round_dir, pre_head=pre_head, mode=mode, reason="verification failed"
    )


def _round_diff_base(round_dir: Path, *, since_committed: bool) -> str:
    if since_committed:
        return _read_post_coder_head(round_dir)
    return _validated_pre_coder_snapshot_head(round_dir)


def _validated_pre_coder_snapshot_head(round_dir: Path) -> str:
    snap_dir = pre_coder_snapshot_dir(round_dir)
    if _snapshot_mode(round_dir) == "missing":
        return ""
    head = larch_io.read_trusted_text(
        snap_dir / "pre-coder-head.txt", root=snap_dir, errors="replace"
    ).strip()
    if not head:
        raise OSError(f"invalid pre-coder snapshot head: {snap_dir}")
    return head


def _round_has_full_pre_coder_snapshot(round_dir: Path) -> bool:
    snap_dir = pre_coder_snapshot_dir(round_dir)
    return (snap_dir / "pre-coder-tracked-paths.txt").is_file() and (
        snap_dir / "pre-coder-untracked-paths.txt"
    ).is_file()


def _collect_round_stage_paths(
    round_dir: Path, *, since_committed: bool = False
) -> list[str]:
    mode = _snapshot_mode(round_dir)
    if mode not in {"full", "head_untracked"}:
        return []
    diff_base = _round_diff_base(round_dir, since_committed=since_committed)
    if not diff_base:
        return []
    if mode == "full" and not _round_has_full_pre_coder_snapshot(round_dir):
        return []
    snapshot_head = _validated_pre_coder_snapshot_head(round_dir)
    snapshot_kw: dict[str, str] = {}
    if snapshot_head and snapshot_head != diff_base:
        snapshot_kw["snapshot_head"] = snapshot_head
    paths: list[str] = []
    seen: set[str] = set()
    tracked = (
        _round_coder_delta_paths(
            round_dir=round_dir, diff_base=diff_base, **snapshot_kw
        )
        if mode == "full"
        else _round_attempt_tracked_delta_paths(round_dir=round_dir, pre_head=diff_base)
    )
    for path in tracked:
        if path not in seen:
            seen.add(path)
            paths.append(path)
    untracked = (
        _round_coder_untracked_delta_paths(round_dir)
        if mode == "full"
        else _round_attempt_untracked_delta_paths(round_dir)
    )
    for path in untracked:
        if path not in seen:
            seen.add(path)
            paths.append(path)
    return paths


# --- self-review snapshot ---


def _self_review_snapshot_dir(implement_tmpdir: Path) -> Path:
    return implement_tmpdir / "self-review-snapshot"


def _write_pre_self_review_snapshot(implement_tmpdir: Path) -> str:
    snap_dir = _self_review_snapshot_dir(implement_tmpdir)
    larch_io.ensure_trusted_directory(snap_dir, root=implement_tmpdir)
    for name in (
        "pre-self-review-head.txt",
        "pre-self-review-tracked-paths.txt",
        "pre-self-review-untracked-paths.txt",
    ):
        with contextlib.suppress(FileNotFoundError):
            (snap_dir / name).unlink()
    diffs_dir = snap_dir / "pre-self-review-path-diffs"
    if diffs_dir.exists() or diffs_dir.is_symlink():
        larch_io.validate_trusted_directory(diffs_dir, root=snap_dir)
        for artifact in diffs_dir.iterdir():
            if not larch_io.trusted_file_present(artifact, root=diffs_dir):
                raise OSError(f"unsafe self-review patch artifact: {artifact}")
            artifact.unlink()
    head = _git_head()
    if not head:
        return ""
    _write_text(path=snap_dir / "pre-self-review-head.txt", text=head + "\n")
    tracked = _capture_round_tracked_paths()
    _write_text(
        path=snap_dir / "pre-self-review-tracked-paths.txt",
        text="\n".join(tracked) + ("\n" if tracked else ""),
    )
    untracked = _capture_round_untracked_paths()
    _write_text(
        path=snap_dir / "pre-self-review-untracked-paths.txt",
        text="\n".join(untracked) + ("\n" if untracked else ""),
    )
    if not diffs_dir.exists():
        larch_io.ensure_trusted_directory(diffs_dir, root=snap_dir)
    for path in tracked:
        safe = path.replace("/", "__").replace("\\", "__")
        _write_text(
            path=diffs_dir / f"{safe}.patch",
            text=_git_output(["diff", head, "--", path]),
        )
        _write_text(
            path=diffs_dir / f"{safe}.cached.patch",
            text=_git_output(["diff", "--cached", head, "--", path]),
        )
    return head


def _path_matches_pre_self_review_snapshot(
    *, implement_tmpdir: Path, pre_head: str, path: str
) -> bool:
    snap_dir = _self_review_snapshot_dir(implement_tmpdir)
    safe = path.replace("/", "__").replace("\\", "__")
    wt_snap = snap_dir / "pre-self-review-path-diffs" / f"{safe}.patch"
    idx_snap = snap_dir / "pre-self-review-path-diffs" / f"{safe}.cached.patch"
    if not wt_snap.is_file() or not idx_snap.is_file():
        return False
    wt_diff = _git_output(["diff", pre_head, "--", path])
    idx_diff = _git_output(["diff", "--cached", pre_head, "--", path])
    return wt_diff == _read_text(wt_snap) and idx_diff == _read_text(idx_snap)


def _validated_self_review_snapshot_head(implement_tmpdir: Path) -> str:
    snap_dir = _self_review_snapshot_dir(implement_tmpdir)
    larch_io.validate_trusted_directory(snap_dir, root=implement_tmpdir)
    head = larch_io.read_trusted_text(
        snap_dir / "pre-self-review-head.txt", root=snap_dir, errors="replace"
    ).strip()
    tracked = larch_io.read_trusted_text(
        snap_dir / "pre-self-review-tracked-paths.txt", root=snap_dir, errors="replace"
    ).splitlines()
    _ = larch_io.read_trusted_text(
        snap_dir / "pre-self-review-untracked-paths.txt", root=snap_dir, errors="replace"
    )
    if not head or any(not path for path in tracked):
        raise OSError(f"invalid self-review snapshot: {snap_dir}")
    safe_names = [_safe_patch_name(path) for path in tracked]
    if len(tracked) != len(set(tracked)) or len(safe_names) != len(set(safe_names)):
        raise OSError(f"invalid self-review snapshot inventory: {snap_dir}")
    diffs = larch_io.validate_trusted_directory(
        snap_dir / "pre-self-review-path-diffs", root=snap_dir
    )
    expected = {
        f"{_safe_patch_name(path)}{suffix}"
        for path in tracked
        for suffix in (".patch", ".cached.patch")
    }
    actual: set[str] = set()
    for artifact in diffs.iterdir():
        if not larch_io.trusted_file_present(artifact, root=diffs):
            raise OSError(f"unsafe self-review patch artifact: {artifact}")
        actual.add(artifact.name)
        _ = larch_io.read_trusted_text(artifact, root=diffs, errors="strict")
    if actual != expected:
        raise OSError(f"incomplete self-review snapshot patches: {snap_dir}")
    return head


def _self_review_delta_paths(*, implement_tmpdir: Path, pre_head: str) -> list[str]:
    snap_dir = _self_review_snapshot_dir(implement_tmpdir)
    pre_tracked = snap_dir / "pre-self-review-tracked-paths.txt"
    pre_tracked_set: set[str] = (
        {line for line in _read_text(pre_tracked).splitlines() if line}
        if pre_tracked.is_file()
        else set()
    )
    deltas: list[str] = []
    seen: set[str] = set()
    for path in _git_output(["diff", "--name-only", pre_head]).splitlines():
        if not path or path in seen:
            continue
        if path in pre_tracked_set and _path_matches_pre_self_review_snapshot(
            implement_tmpdir=implement_tmpdir, pre_head=pre_head, path=path
        ):
            continue
        seen.add(path)
        deltas.append(path)
    return deltas


def _self_review_untracked_delta_paths(implement_tmpdir: Path) -> list[str]:
    snap_dir = _self_review_snapshot_dir(implement_tmpdir)
    pre_untracked = {
        line
        for line in _read_text(
            snap_dir / "pre-self-review-untracked-paths.txt"
        ).splitlines()
        if line
    }
    return [
        path for path in _capture_round_untracked_paths() if path not in pre_untracked
    ]


def _collect_self_review_stage_paths(implement_tmpdir: Path) -> list[str]:
    if not (implement_tmpdir / "self-review-accepted.md").is_file():
        return []
    try:
        pre_head = _validated_self_review_snapshot_head(implement_tmpdir)
    except OSError:
        return []
    paths: list[str] = []
    seen: set[str] = set()
    for path in _self_review_delta_paths(
        implement_tmpdir=implement_tmpdir, pre_head=pre_head
    ):
        if path not in seen:
            seen.add(path)
            paths.append(path)
    for path in _self_review_untracked_delta_paths(implement_tmpdir):
        if path not in seen:
            seen.add(path)
            paths.append(path)
    return paths


# --- pre-coder snapshot write ---


def _write_pre_coder_snapshot(round_dir: Path) -> str:
    snap_dir = pre_coder_snapshot_dir(round_dir)
    larch_io.ensure_trusted_directory(snap_dir)
    _clear_stale_pre_coder_snapshot_artifacts(snap_dir)
    head = _git_head()
    pre_head = snap_dir / "pre-coder-head.txt"
    if head:
        _write_text(path=pre_head, text=head + "\n")
        _snapshot_pre_coder_tracked_state(
            _round_dir=round_dir, pre_head=head, snap_dir=snap_dir
        )
        pre_head.chmod(0o444)
        _harden_pre_coder_snapshot_perms(snap_dir)
    else:
        with contextlib.suppress(FileNotFoundError):
            pre_head.unlink()
    return head


def _ensure_pre_coder_snapshot(round_dir: Path) -> None:
    if _snapshot_mode(round_dir) == "missing":
        _write_pre_coder_snapshot(round_dir)


def _structural_loc(*, pre_head_file: Path, post_head_file: Path) -> int:
    if not pre_head_file.is_file() or not post_head_file.is_file():
        return 0
    pre_head = _read_text(pre_head_file).strip()
    post_head = _read_text(post_head_file).strip()
    if not pre_head or not post_head:
        return 0
    result = _run(["git", "diff", "--numstat", pre_head, post_head])
    if result.returncode != 0:
        return 0
    total = 0
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            total += int(parts[0]) + int(parts[1])
    return total


# pyright: reportPrivateUsage=false, reportUnusedFunction=false, reportUnusedCallResult=false
