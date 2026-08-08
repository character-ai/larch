# pyright: reportPrivateUsage=false, reportUnusedCallResult=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false
from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from larch.report import progress_file


def test_resolve_persisted_run_returns_frozen_named_fields(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _ = (tmp_path / "session-env.sh").write_text("LARCH_RUN_ID=design-20260714.1\n", encoding="utf-8")
    _ = (tmp_path / "source-env.sh").write_text(f"REPO_ROOT={repo}\n", encoding="utf-8")

    result = progress_file.resolve_persisted_run(tmpdir=tmp_path, env={})

    assert result.run_id == "design-20260714.1"
    assert result.repo_root == repo.resolve()
    with pytest.raises(FrozenInstanceError):
        result.run_id = "other"  # type: ignore[misc]


def test_progress_path_uses_repo_realpath_and_short_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    link = tmp_path / "repo-link"
    link.symlink_to(repo)
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(cache))

    path = progress_file.progress_path(link)

    assert path.parent == cache / "larch" / "progress"
    assert re.fullmatch(r"[0-9a-f]{16}\.log", path.name)
    assert path == progress_file.progress_path(repo)


def test_append_breadcrumb_rejects_tabs_and_newlines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id = "implement-20260708.1"
    progress_file.activate_run(repo, run_id)

    assert progress_file.append_breadcrumb(repo, "implement", "5", "reviewers 7/12 done")
    assert not progress_file.append_breadcrumb(repo, "implement", "5", "bad\nrow")
    assert not progress_file.append_breadcrumb(repo, "implement", "5", "bad\ttab")
    assert not progress_file.append_breadcrumb(repo, "implement", "5", "bad\x1b[31mrow")
    assert not progress_file.append_breadcrumb(repo, "implement", "5", "bad\x9b31mrow")
    assert not progress_file.append_breadcrumb(repo, "implement", "5", "see https://example.test")
    assert not progress_file.append_breadcrumb(repo, "implement", "5", "osc \x1b]8;;https://example.test\x07 link")

    assert progress_file.run_progress_path(repo, run_id).read_text(encoding="utf-8") == "[implement 5] reviewers 7/12 done\n"
    assert not progress_file.progress_path(repo).exists()


def test_append_breadcrumb_pins_run_dir_after_fd_acquisition(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    target = tmp_path / "outside-run"
    repo.mkdir()
    target.mkdir()
    run_id = "implement-20260708.1"
    progress_file.activate_run(repo, run_id)
    run_dir = progress_file.run_progress_dir(repo, run_id)
    real_run_dir = tmp_path / "real-run"
    original_subdir = progress_file._open_or_create_subdir
    swapped = False

    def swapping_subdir(parent_fd: int, name: str) -> int:
        nonlocal swapped
        fd = original_subdir(parent_fd, name)
        if not swapped and name == run_id and run_dir.is_dir():
            run_dir.rename(real_run_dir)
            run_dir.symlink_to(target, target_is_directory=True)
            swapped = True
        return fd

    monkeypatch.setattr(progress_file, "_open_or_create_subdir", swapping_subdir)

    assert progress_file.append_breadcrumb(repo, "implement", "5", "reviewers 7/12 done")
    assert swapped
    assert not (target / progress_file.RUN_BREADCRUMB_FILENAME).exists()
    assert (real_run_dir / progress_file.RUN_BREADCRUMB_FILENAME).read_text(encoding="utf-8") == (
        "[implement 5] reviewers 7/12 done\n"
    )


def test_progress_path_uses_consumer_repo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    subdir = repo / "nested" / "leaf"
    subdir.mkdir(parents=True)
    _ = subprocess.run(["git", "init"], cwd=repo, check=False, capture_output=True, text=True)
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(cache))

    assert progress_file.progress_path(subdir) == progress_file.progress_path(repo)


def test_cleanup_old_progress_files(tmp_path: Path) -> None:
    root = tmp_path / "progress"
    root.mkdir()
    old = root / "old.log"
    fresh = root / "fresh.log"
    old.write_text("old\n", encoding="utf-8")
    fresh.write_text("fresh\n", encoding="utf-8")
    now = time.time()
    _ = os.utime(old, (now - 9 * 86400, now - 9 * 86400))

    assert progress_file.cleanup_old_progress_files(retention_days=7, root=root, now=now) == 1
    assert not old.exists()
    assert fresh.exists()


def test_run_scoped_path_helpers_validate_reserved_names(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id = "design-20260708.1"

    clone_dir = progress_file.progress_clone_dir(repo)

    assert clone_dir == progress_file.progress_path(repo).with_suffix("")
    assert progress_file.current_run_path(repo) == clone_dir / progress_file.CURRENT_RUN_FILENAME
    assert progress_file.run_progress_dir(repo, run_id) == clone_dir / run_id
    assert progress_file.run_progress_path(repo, run_id) == clone_dir / run_id / progress_file.RUN_BREADCRUMB_FILENAME
    assert progress_file.validate_run_id(run_id) == run_id


@pytest.mark.parametrize("run_id", ["", ".", "..", "current", "bad/id", "bad\\id", "bad\nid", "bad id", "bad\tid"])
def test_validate_run_id_rejects_unsafe_values(run_id: str) -> None:
    with pytest.raises(ValueError, match=r"run ID|reserved"):
        progress_file.validate_run_id(run_id)


@pytest.mark.parametrize("run_id", ["", "current"])
def test_append_breadcrumb_for_run_rejects_invalid_run_id_before_creating_dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, run_id: str
) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    clone_dir = progress_file.progress_clone_dir(repo)

    assert not progress_file.append_breadcrumb_for_run(repo, run_id, "design", "3", "reviewers done")
    assert not clone_dir.exists()


def test_activate_run_writes_current_with_fd_anchored_helpers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id = "implement-20260708.1"
    ensure_calls: list[Path] = []
    subdir_calls: list[str] = []
    write_calls: list[tuple[str, str, int, str]] = []
    original_ensure = progress_file._ensure_directory_fd
    original_subdir = progress_file._open_or_create_subdir
    original_write = progress_file._atomic_write_in_dir

    def traced_ensure(path: Path) -> int:
        ensure_calls.append(path)
        return original_ensure(path)

    def traced_subdir(parent_fd: int, name: str) -> int:
        subdir_calls.append(name)
        return original_subdir(parent_fd, name)

    def traced_write(dir_fd: int, name: str, text: str, *, mode: int = 0o600, temp_prefix: str = ".current.") -> None:
        write_calls.append((name, text, mode, temp_prefix))
        original_write(dir_fd, name, text, mode=mode, temp_prefix=temp_prefix)

    monkeypatch.setattr(progress_file, "_ensure_directory_fd", traced_ensure)
    monkeypatch.setattr(progress_file, "_open_or_create_subdir", traced_subdir)
    monkeypatch.setattr(progress_file, "_atomic_write_in_dir", traced_write)

    progress_file.activate_run(repo, run_id)

    assert progress_file.current_run_path(repo).read_text(encoding="utf-8") == f"{run_id}\n"
    assert progress_file.run_progress_dir(repo, run_id).is_dir()
    assert ensure_calls == [progress_file.progress_clone_dir(repo)]
    assert subdir_calls[-1] == run_id
    assert write_calls == [(progress_file.CURRENT_RUN_FILENAME, f"{run_id}\n", 0o600, ".current.")]


def test_activate_run_pins_clone_dir_after_fd_acquisition(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id = "design-20260708.1"
    clone_dir = progress_file.progress_clone_dir(repo)
    real_clone_dir = tmp_path / "real-clone"
    target = tmp_path / "outside"
    target.mkdir()
    original_subdir = progress_file._open_or_create_subdir
    swapped = False

    def swapping_subdir(parent_fd: int, name: str) -> int:
        nonlocal swapped
        fd = original_subdir(parent_fd, name)
        if not swapped and name == run_id and clone_dir.is_dir():
            clone_dir.rename(real_clone_dir)
            clone_dir.symlink_to(target, target_is_directory=True)
            swapped = True
        return fd

    monkeypatch.setattr(progress_file, "_open_or_create_subdir", swapping_subdir)

    progress_file.activate_run(repo, run_id)

    assert swapped
    assert not (target / progress_file.CURRENT_RUN_FILENAME).exists()
    assert (real_clone_dir / progress_file.CURRENT_RUN_FILENAME).read_text(encoding="utf-8") == f"{run_id}\n"
    assert (real_clone_dir / run_id).is_dir()


def test_activate_run_uses_anchored_directory_creation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id = "implement-20260708.1"

    def forbid_path_mkdir(self: Path, *_args: object, **_kwargs: object) -> None:
        raise AssertionError(f"path.mkdir unexpectedly used for {self}")

    monkeypatch.setattr(Path, "mkdir", forbid_path_mkdir)

    progress_file.activate_run(repo, run_id)

    assert progress_file.current_run_path(repo).read_text(encoding="utf-8") == f"{run_id}\n"
    assert progress_file.run_progress_dir(repo, run_id).is_dir()
    assert progress_file.progress_clone_dir(repo).is_dir()


def test_read_active_run_id_normalizes_activate_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id = "design-20260708.1"
    progress_file.activate_run(repo, run_id)

    assert progress_file.read_active_run_id(repo) == run_id
    assert progress_file._read_active_run_id(progress_file.progress_clone_dir(repo)) == run_id

    progress_file.current_run_path(repo).write_text("bad id\n", encoding="utf-8")
    assert progress_file.read_active_run_id(repo) is None
    assert progress_file._read_active_run_id(progress_file.progress_clone_dir(repo)) is None

    progress_file.current_run_path(repo).write_text(" \t\n", encoding="utf-8")
    assert progress_file.read_active_run_id(repo) is None
    assert progress_file._read_active_run_id(progress_file.progress_clone_dir(repo)) is None


def test_read_active_run_id_missing_clone_dir_is_no_create(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    clone_dir = progress_file.progress_clone_dir(repo)

    assert progress_file.read_active_run_id(repo) is None
    assert not clone_dir.exists()


def test_deactivate_run_removes_current_and_preserves_run_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id = "implement-20260708.1"
    progress_file.activate_run(repo, run_id)
    assert progress_file.append_breadcrumb(repo, "implement", "5", "review round 1 running")
    run_dir = progress_file.run_progress_dir(repo, run_id)
    log_path = progress_file.run_progress_path(repo, run_id)

    assert progress_file.deactivate_run(repo, "implement-20260708.1")

    assert not progress_file.current_run_path(repo).exists()
    assert run_dir.is_dir()
    assert log_path.read_text(encoding="utf-8") == "[implement 5] review round 1 running\n"


def test_deactivate_run_missing_clone_dir_is_no_create(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    clone_dir = progress_file.progress_clone_dir(repo)

    assert not progress_file.deactivate_run(repo, "implement-20260708.1")
    assert not clone_dir.exists()


def test_deactivate_run_refuses_symlinked_current(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    target = tmp_path / "outside-current"
    repo.mkdir()
    target.write_text("implement-20260708.1\n", encoding="utf-8")
    clone_dir = progress_file.progress_clone_dir(repo)
    clone_dir.mkdir(parents=True)
    progress_file.current_run_path(repo).symlink_to(target)

    assert not progress_file.deactivate_run(repo, "implement-20260708.1")

    assert progress_file.current_run_path(repo).is_symlink()
    assert target.read_text(encoding="utf-8") == "implement-20260708.1\n"


def test_deactivate_run_refuses_invalid_current(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    clone_dir = progress_file.progress_clone_dir(repo)
    clone_dir.mkdir(parents=True)
    current_path = progress_file.current_run_path(repo)
    current_path.write_text("bad run id\n", encoding="utf-8")

    assert not progress_file.deactivate_run(repo, "implement-20260708.1")
    assert current_path.read_text(encoding="utf-8") == "bad run id\n"


def test_deactivate_run_refuses_symlinked_clone_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    outside_clone = tmp_path / "outside-clone"
    repo.mkdir()
    outside_clone.mkdir()
    progress_file.progress_clone_dir(repo).parent.mkdir(parents=True)
    progress_file.progress_clone_dir(repo).symlink_to(outside_clone, target_is_directory=True)
    (outside_clone / progress_file.CURRENT_RUN_FILENAME).write_text("implement-20260708.1\n", encoding="utf-8")

    assert not progress_file.deactivate_run(repo, "implement-20260708.1")
    assert (outside_clone / progress_file.CURRENT_RUN_FILENAME).read_text(encoding="utf-8") == "implement-20260708.1\n"


def test_read_active_run_id_from_dirfd_is_best_effort_on_invalid_utf8_and_fifo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    clone_dir = progress_file.progress_clone_dir(repo)
    clone_dir.mkdir(parents=True)
    current_path = progress_file.current_run_path(repo)

    current_path.write_bytes(b"\xff\xfe\n")
    dir_fd = progress_file._open_verified_dir(clone_dir)
    try:
        assert progress_file._read_active_run_id_from_dirfd(dir_fd) is None
    finally:
        os.close(dir_fd)

    if not hasattr(os, "mkfifo"):
        pytest.skip("fifo support unavailable")

    current_path.unlink()
    os.mkfifo(current_path)
    open_flags: list[int] = []
    original_open = progress_file.os.open

    def traced_open(path, flags, *args, **kwargs):
        if path == progress_file.CURRENT_RUN_FILENAME:
            open_flags.append(flags)
            assert flags & os.O_NONBLOCK
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(progress_file.os, "open", traced_open)

    dir_fd = progress_file._open_verified_dir(clone_dir)
    try:
        assert progress_file._read_active_run_id_from_dirfd(dir_fd) is None
    finally:
        os.close(dir_fd)
    assert open_flags


def test_append_breadcrumb_for_run_refuses_symlinked_run_dir_ancestor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    target = tmp_path / "outside"
    repo.mkdir()
    target.mkdir()
    progress_file.progress_clone_dir(repo).parent.mkdir(parents=True)
    progress_file.progress_clone_dir(repo).symlink_to(target, target_is_directory=True)

    assert not progress_file.append_breadcrumb_for_run(repo, "design-20260708.1", "design", "3", "reviewers done")
    assert not (target / "design-20260708.1" / progress_file.RUN_BREADCRUMB_FILENAME).exists()


def test_append_breadcrumb_for_run_refuses_symlinked_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    target = tmp_path / "outside.log"
    repo.mkdir()
    target.write_text("", encoding="utf-8")
    run_dir = progress_file.run_progress_dir(repo, "design-20260708.1")
    run_dir.mkdir(parents=True)
    progress_file.run_progress_path(repo, "design-20260708.1").symlink_to(target)

    assert not progress_file.append_breadcrumb_for_run(repo, "design-20260708.1", "design", "3", "reviewers done")
    assert target.read_text(encoding="utf-8") == ""


def test_append_breadcrumb_for_run_uses_nonblocking_open_on_fifo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id = "design-20260708.1"
    run_dir = progress_file.run_progress_dir(repo, run_id)
    run_dir.mkdir(parents=True)
    log_path = progress_file.run_progress_path(repo, run_id)
    if not hasattr(os, "mkfifo"):
        pytest.skip("fifo support unavailable")
    os.mkfifo(log_path)
    open_flags: list[int] = []
    original_open = progress_file.os.open

    def traced_open(path, flags, *args, **kwargs):
        if path == progress_file.RUN_BREADCRUMB_FILENAME:
            open_flags.append(flags)
            assert flags & os.O_NONBLOCK
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(progress_file.os, "open", traced_open)

    assert not progress_file.append_breadcrumb_for_run(repo, run_id, "design", "3", "reviewers done")
    assert open_flags


def test_append_breadcrumb_for_run_pins_run_dir_after_fd_acquisition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    target = tmp_path / "outside-run"
    repo.mkdir()
    target.mkdir()
    run_id = "design-20260708.1"
    run_dir = progress_file.run_progress_dir(repo, run_id)
    real_run_dir = tmp_path / "real-run"
    original_subdir = progress_file._open_or_create_subdir
    swapped = False

    def swapping_subdir(parent_fd: int, name: str) -> int:
        nonlocal swapped
        fd = original_subdir(parent_fd, name)
        if not swapped and name == run_id and run_dir.is_dir():
            run_dir.rename(real_run_dir)
            run_dir.symlink_to(target, target_is_directory=True)
            swapped = True
        return fd

    monkeypatch.setattr(progress_file, "_open_or_create_subdir", swapping_subdir)

    assert progress_file.append_breadcrumb_for_run(repo, run_id, "design", "3", "reviewers done")
    assert swapped
    assert not (target / progress_file.RUN_BREADCRUMB_FILENAME).exists()
    assert (real_run_dir / progress_file.RUN_BREADCRUMB_FILENAME).read_text(encoding="utf-8") == "[design 3] reviewers done\n"


def test_activate_run_refuses_symlinked_run_dir_and_current(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    target_dir = tmp_path / "outside-run"
    target_file = tmp_path / "outside-current"
    repo.mkdir()
    target_dir.mkdir()
    target_file.write_text("", encoding="utf-8")
    clone_dir = progress_file.progress_clone_dir(repo)
    clone_dir.mkdir(parents=True)
    progress_file.run_progress_dir(repo, "design-20260708.1").symlink_to(target_dir, target_is_directory=True)

    with pytest.raises(OSError, match=r"refusing|symbolic links|symlink|not a directory|Not a directory"):
        progress_file.activate_run(repo, "design-20260708.1")
    assert not (target_dir / progress_file.CURRENT_RUN_FILENAME).exists()

    progress_file.run_progress_dir(repo, "design-20260708.1").unlink()
    progress_file.current_run_path(repo).symlink_to(target_file)
    with pytest.raises(OSError, match=r"refusing|symbolic links|symlink|not a directory|Not a directory"):
        progress_file.activate_run(repo, "design-20260708.1")
    assert target_file.read_text(encoding="utf-8") == ""


def test_cleanup_old_progress_files_reaps_run_dirs_and_legacy_logs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    active_run_id = "active-20260708.1"
    progress_file.activate_run(repo, active_run_id)
    root = progress_file.progress_root()
    clone_dir = progress_file.progress_clone_dir(repo)
    now = time.time()
    old_time = now - 9 * 86400

    old_run = clone_dir / "old-20260708.1"
    fresh_run = clone_dir / "fresh-20260708.1"
    fresh_log_run = clone_dir / "logfresh-20260708.1"
    for run_dir in [old_run, fresh_run, fresh_log_run]:
        run_dir.mkdir()
        (run_dir / progress_file.RUN_BREADCRUMB_FILENAME).write_text("row\n", encoding="utf-8")
    _ = os.utime(old_run / progress_file.RUN_BREADCRUMB_FILENAME, (old_time, old_time))
    _ = os.utime(old_run, (old_time, old_time))
    _ = os.utime(fresh_log_run, (old_time, old_time))
    _ = os.utime(progress_file.run_progress_dir(repo, active_run_id), (old_time, old_time))

    old_flat = root / f"{'b' * 16}.log"
    old_flat.write_text("old\n", encoding="utf-8")
    _ = os.utime(old_flat, (old_time, old_time))
    outside_flat = tmp_path / "outside-flat.log"
    outside_flat.write_text("outside\n", encoding="utf-8")
    symlink_flat = root / f"{'c' * 16}.log"
    symlink_flat.symlink_to(outside_flat)
    outside_clone = tmp_path / "outside-clone"
    outside_clone.mkdir()
    outside_run = outside_clone / "old-20260708.1"
    outside_run.mkdir()
    symlink_clone = root / ("d" * 16)
    symlink_clone.symlink_to(outside_clone, target_is_directory=True)

    assert progress_file.cleanup_old_progress_files(retention_days=7, root=root, now=now) == 2

    assert not old_run.exists()
    assert fresh_run.exists()
    assert fresh_log_run.exists()
    assert progress_file.run_progress_dir(repo, active_run_id).exists()
    assert not old_flat.exists()
    assert symlink_flat.is_symlink()
    assert outside_flat.exists()
    assert outside_run.exists()


def test_cleanup_old_progress_files_pins_clone_dir_before_enumeration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    root = progress_file.progress_root()
    clone_dir = progress_file.progress_clone_dir(repo)
    clone_dir.mkdir(parents=True)
    current_path = progress_file.current_run_path(repo)
    current_path.write_text("active-20260708.1\n", encoding="utf-8")

    now = time.time()
    old_time = now - 9 * 86400

    original_run = clone_dir / "old-20260708.1"
    original_run.mkdir()
    original_log = original_run / progress_file.RUN_BREADCRUMB_FILENAME
    original_log.write_text("row\n", encoding="utf-8")
    _ = os.utime(original_run, (old_time, old_time))
    _ = os.utime(original_log, (old_time, old_time))

    outside_clone = tmp_path / "outside-clone"
    outside_clone.mkdir()
    outside_run = outside_clone / "old-20260708.1"
    outside_run.mkdir()
    outside_log = outside_run / progress_file.RUN_BREADCRUMB_FILENAME
    outside_log.write_text("outside\n", encoding="utf-8")
    _ = os.utime(outside_run, (old_time, old_time))
    _ = os.utime(outside_log, (old_time, old_time))

    real_clone_dir = tmp_path / "real-clone"
    swapped = False
    opened_clone_fd: int | None = None
    original_iterdir = Path.iterdir
    original_listdir = progress_file.os.listdir
    original_open_verified_dir = progress_file._open_verified_dir

    def swap_clone_dir() -> None:
        nonlocal swapped
        if swapped:
            return
        clone_dir.rename(real_clone_dir)
        clone_dir.symlink_to(outside_clone, target_is_directory=True)
        swapped = True

    def traced_open_verified_dir(path: Path) -> int:
        fd = original_open_verified_dir(path)
        nonlocal opened_clone_fd
        if path == clone_dir:
            opened_clone_fd = fd
        return fd

    def patched_iterdir(self: Path):
        if self == clone_dir:
            swap_clone_dir()
        yield from original_iterdir(self)

    def patched_listdir(path):
        if opened_clone_fd is not None and path == opened_clone_fd:
            swap_clone_dir()
        return original_listdir(path)

    monkeypatch.setattr(progress_file, "_open_verified_dir", traced_open_verified_dir)
    monkeypatch.setattr(Path, "iterdir", patched_iterdir)
    monkeypatch.setattr(progress_file.os, "listdir", patched_listdir)

    assert progress_file.cleanup_old_progress_files(retention_days=7, root=root, now=now) == 1
    assert not (real_clone_dir / "old-20260708.1").exists()
    assert (outside_clone / "old-20260708.1").exists()


def test_clear_active_run_removes_prior_pointer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    progress_file.activate_run(repo, "prior-run")

    assert progress_file.clear_active_run(repo)
    assert progress_file.read_active_run_id(repo) is None


def test_sessionstart_statusline_harness() -> None:
    result = subprocess.run(
        ["bash", "scripts/test-sessionstart-statusline.sh"],
        cwd=Path(__file__).resolve().parents[3],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
