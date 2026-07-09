# pyright: reportPrivateUsage=false, reportUnusedCallResult=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path

import pytest

from larch.report import progress_file
from larch.report import statusline
from larch.report import statusline_install
from larch.report import timing
from larch import cli


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

    assert progress_file.deactivate_run(repo)

    assert not progress_file.current_run_path(repo).exists()
    assert run_dir.is_dir()
    assert log_path.read_text(encoding="utf-8") == "[implement 5] review round 1 running\n"


def test_deactivate_run_missing_clone_dir_is_no_create(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    clone_dir = progress_file.progress_clone_dir(repo)

    assert not progress_file.deactivate_run(repo)
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

    assert not progress_file.deactivate_run(repo)

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

    assert not progress_file.deactivate_run(repo)
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

    assert not progress_file.deactivate_run(repo)
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


def test_progress_note_run_id_writes_only_explicit_run_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    seed_run_id = "design-20260708.1"
    run_id = "implement-20260708.1"

    progress_file.activate_run(repo, seed_run_id)
    current_path = progress_file.current_run_path(repo)
    current_before = current_path.read_text(encoding="utf-8")

    assert progress_file.progress_note_main(
        ["--repo-root", str(repo), "--run-id", run_id, "--skill", "implement", "--step", "5", "reviewers", "done"]
    ) == 0

    assert progress_file.run_progress_path(repo, run_id).read_text(encoding="utf-8") == "[implement 5] reviewers done\n"
    assert current_path.read_text(encoding="utf-8") == current_before
    assert not progress_file.progress_path(repo).exists()


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


def test_default_progress_requires_current_pointer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()

    assert not progress_file.append_breadcrumb(repo, "implement", "5", "review round 1 running")
    assert statusline.render_statusline(stdin_text=json.dumps({"cwd": str(repo)})) == ""
    assert progress_file.read_active_run_id(repo) is None
    assert not progress_file.progress_path(repo).exists()


def test_invalid_current_pointer_blocks_default_progress(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    clone_dir = progress_file.progress_clone_dir(repo)
    clone_dir.mkdir(parents=True)
    progress_file.current_run_path(repo).write_text("bad id\n", encoding="utf-8")

    assert not progress_file.append_breadcrumb(repo, "implement", "5", "review round 1 running")
    assert statusline.render_statusline(stdin_text=json.dumps({"cwd": str(repo)})) == ""
    assert progress_file.read_active_run_id(repo) is None
    assert not progress_file.progress_path(repo).exists()


def test_legacy_flat_logs_are_ignored_by_statusline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    flat_path = progress_file.progress_path(repo)
    flat_path.parent.mkdir(parents=True)
    flat_path.write_text("[implement 5] old flat row\n", encoding="utf-8")
    payload = json.dumps({"cwd": str(repo)})

    assert statusline.render_statusline(stdin_text=payload) == ""

    progress_file.activate_run(repo, "implement-20260708.1")
    assert statusline.render_statusline(stdin_text=payload) == ""


def test_new_run_starts_empty_and_old_run_never_renders(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = json.dumps({"cwd": str(repo)})
    env = {"LARCH_TEST_STATUSLINE_NOW": "1700000000", "LARCH_STATUSLINE_STALE_AFTER_S": "999999"}

    progress_file.activate_run(repo, "old-20260708.1")
    assert progress_file.append_breadcrumb(repo, "implement", "5", "old run row")
    progress_file.activate_run(repo, "new-20260708.1")

    assert statusline.render_statusline(stdin_text=payload, env=env) == ""

    assert progress_file.append_breadcrumb(repo, "implement", "5", "new run row")
    rendered = statusline.render_statusline(stdin_text=payload, env=env)

    assert "new run row" in rendered
    assert "old run row" not in rendered


def test_statusline_staleness_uses_active_run_mtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    progress_file.append_breadcrumb_for_run(repo, "old-20260708.1", "implement", "5", "old run row")
    progress_file.append_breadcrumb_for_run(repo, "active-20260708.1", "implement", "5", "active run row")
    old_log = progress_file.run_progress_path(repo, "old-20260708.1")
    active_log = progress_file.run_progress_path(repo, "active-20260708.1")
    _ = os.utime(old_log, (1000, 1000))
    _ = os.utime(active_log, (1900, 1900))
    progress_file.activate_run(repo, "active-20260708.1")

    rendered = statusline.render_statusline(
        stdin_text=json.dumps({"cwd": str(repo)}),
        env={"LARCH_TEST_STATUSLINE_NOW": "2000", "LARCH_STATUSLINE_STALE_AFTER_S": "60", "LARCH_STATUSLINE_HIDE_AFTER_S": "1000"},
    )

    assert "(stale 1m)" in rendered
    assert "active run row" in rendered
    assert "old run row" not in rendered


def test_default_append_refuses_symlinked_active_pointer_and_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    target_current = tmp_path / "outside-current"
    target_log = tmp_path / "outside.log"
    repo.mkdir()
    target_current.write_text("implement-20260708.1\n", encoding="utf-8")
    target_log.write_text("", encoding="utf-8")
    progress_file.activate_run(repo, "implement-20260708.1")
    progress_file.current_run_path(repo).unlink()
    progress_file.current_run_path(repo).symlink_to(target_current)

    assert not progress_file.append_breadcrumb(repo, "implement", "5", "review round 1 running")
    assert target_current.read_text(encoding="utf-8") == "implement-20260708.1\n"

    progress_file.current_run_path(repo).unlink()
    progress_file.current_run_path(repo).write_text("implement-20260708.1\n", encoding="utf-8")
    progress_file.run_progress_path(repo, "implement-20260708.1").symlink_to(target_log)

    assert not progress_file.append_breadcrumb(repo, "implement", "5", "review round 1 running")
    assert target_log.read_text(encoding="utf-8") == ""


def test_default_append_refuses_symlinked_clone_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    outside_clone = tmp_path / "outside-clone"
    repo.mkdir()
    outside_clone.mkdir()
    progress_file.progress_clone_dir(repo).parent.mkdir(parents=True)
    progress_file.progress_clone_dir(repo).symlink_to(outside_clone, target_is_directory=True)
    (outside_clone / progress_file.CURRENT_RUN_FILENAME).write_text("implement-20260708.1\n", encoding="utf-8")

    assert not progress_file.append_breadcrumb(repo, "implement", "5", "review round 1 running")
    assert not (outside_clone / "implement-20260708.1" / progress_file.RUN_BREADCRUMB_FILENAME).exists()


def test_statusline_fail_silent_empty_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    progress_file.activate_run(repo, "implement-20260708.1")
    assert progress_file.append_breadcrumb(repo, "implement", "5", "review round 1 running")

    assert statusline.render_statusline(stdin_text="") == ""
    assert statusline.render_statusline(stdin_text="not json") == ""
    assert statusline.render_statusline(stdin_text=json.dumps({"cwd": str(tmp_path)})) == ""
    assert statusline.render_statusline(stdin_text="not json", env={"PWD": str(repo)}) == ""


def test_statusline_renders_yellow_line_and_is_calm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(cache))
    progress_file.activate_run(repo, "implement-20260708.1")
    assert progress_file.append_breadcrumb(repo, "implement", "5", "review round 1 running")
    payload = json.dumps({"workspace": {"current_dir": str(repo)}})
    env = {"LARCH_TEST_STATUSLINE_NOW": "1700000000", "LARCH_STATUSLINE_STALE_AFTER_S": "999999"}

    first = statusline.render_statusline(stdin_text=payload, env=env)
    second = statusline.render_statusline(stdin_text=payload, env={**env, "LARCH_TEST_STATUSLINE_NOW": "1700000061"})

    assert first == second
    assert first.startswith("\033[33mlarch ")
    assert "[implement 5] review round 1 running" in first
    assert first.endswith("\033[0m\n")


def test_statusline_refuses_symlinked_active_pointer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    target = tmp_path / "outside-current"
    repo.mkdir()
    target.write_text("implement-20260708.1\n", encoding="utf-8")
    progress_file.activate_run(repo, "implement-20260708.1")
    assert progress_file.append_breadcrumb(repo, "implement", "5", "review round 1 running")
    progress_file.current_run_path(repo).unlink()
    progress_file.current_run_path(repo).symlink_to(target)

    rendered = statusline.render_statusline(stdin_text=json.dumps({"cwd": str(repo)}))

    assert rendered == ""


def test_statusline_refuses_symlinked_active_run_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    target = tmp_path / "outside.log"
    repo.mkdir()
    target.write_text("[implement 5] outside row\n", encoding="utf-8")
    progress_file.activate_run(repo, "implement-20260708.1")
    progress_file.run_progress_path(repo, "implement-20260708.1").symlink_to(target)

    rendered = statusline.render_statusline(stdin_text=json.dumps({"cwd": str(repo)}))

    assert rendered == ""


def test_statusline_refuses_symlinked_progress_ancestors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "cache"
    cache_target = tmp_path / "cache-target"
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(cache))
    run_id = "implement-20260708.1"
    progress_file.activate_run(repo, run_id)
    assert progress_file.append_breadcrumb(repo, "implement", "5", "review round 1 running")
    real_larch = tmp_path / "real-larch"
    (cache / "larch").rename(real_larch)
    cache_target.mkdir()
    (cache / "larch").symlink_to(cache_target)

    rendered = statusline.render_statusline(stdin_text=json.dumps({"cwd": str(repo)}))

    assert rendered == ""


def test_statusline_stale_and_far_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(cache))
    run_id = "implement-20260708.1"
    progress_file.activate_run(repo, run_id)
    assert progress_file.append_breadcrumb(repo, "implement", "8", "PR #1234 created")
    path = progress_file.run_progress_path(repo, run_id)
    _ = os.utime(path, (1000, 1000))
    payload = json.dumps({"cwd": str(repo)})

    stale = statusline.render_statusline(
        stdin_text=payload,
        env={"LARCH_TEST_STATUSLINE_NOW": "1600", "LARCH_STATUSLINE_STALE_AFTER_S": "60", "LARCH_STATUSLINE_HIDE_AFTER_S": "1000"},
    )
    hidden = statusline.render_statusline(
        stdin_text=payload,
        env={"LARCH_TEST_STATUSLINE_NOW": "3000", "LARCH_STATUSLINE_STALE_AFTER_S": "60", "LARCH_STATUSLINE_HIDE_AFTER_S": "1000"},
    )

    assert "(stale 10m)" in stale
    assert hidden == ""


def test_statusline_columns_truncation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    progress_file.activate_run(repo, "design-20260708.1")
    assert progress_file.append_breadcrumb(repo, "design", "3", "reviewers 12/12 done and voting launched")

    rendered = statusline.render_statusline(
        stdin_text=json.dumps({"cwd": str(repo)}),
        env={"LARCH_TEST_STATUSLINE_NOW": "1700000000", "COLUMNS": "30", "LARCH_STATUSLINE_STALE_AFTER_S": "999999"},
    )

    inner = rendered.removeprefix("\033[33m").removesuffix("\033[0m\n")
    assert len(inner) == 30
    assert inner.endswith("…")


def test_statusline_cli_registered_as_machine_stdout() -> None:
    assert ("progress", "statusline") in cli._REGISTRY
    assert ("progress", "statusline") in cli._MACHINE_STDOUT_KEYS
    assert ("progress", "session-reset") in cli._REGISTRY
    assert ("progress", "session-reset") not in cli._MACHINE_STDOUT_KEYS
    assert ("progress", "activate") in cli._REGISTRY
    assert ("progress", "activate") not in cli._MACHINE_STDOUT_KEYS
    assert ("progress", "report") not in cli._REGISTRY


def test_session_reset_progress_clears_startup_statusline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id = "implement-20260708.1"
    payload = json.dumps({"source": "startup", "cwd": str(repo)})
    env = {"LARCH_TEST_STATUSLINE_NOW": "1700000000", "LARCH_STATUSLINE_STALE_AFTER_S": "999999"}
    progress_file.activate_run(repo, run_id)
    assert progress_file.append_breadcrumb(repo, "implement", "5", "old run row")
    assert "old run row" in statusline.render_statusline(stdin_text=payload, env=env)

    assert statusline.session_reset_progress(payload)

    assert statusline.render_statusline(stdin_text=payload, env=env) == ""
    assert progress_file.run_progress_path(repo, run_id).read_text(encoding="utf-8") == "[implement 5] old run row\n"


def test_session_reset_progress_clears_clear_statusline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = json.dumps({"source": "clear", "cwd": str(repo)})
    progress_file.activate_run(repo, "implement-20260708.1")
    assert progress_file.append_breadcrumb(repo, "implement", "5", "old run row")

    assert statusline.session_reset_progress(payload)
    assert progress_file.read_active_run_id(repo) is None


@pytest.mark.parametrize("source", ["resume", "compact"])
def test_session_reset_progress_skips_resume_and_compact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id = "implement-20260708.1"
    progress_file.activate_run(repo, run_id)

    assert not statusline.session_reset_progress(json.dumps({"source": source, "cwd": str(repo)}))
    assert progress_file.read_active_run_id(repo) == run_id


def test_session_reset_progress_skips_missing_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id = "implement-20260708.1"
    progress_file.activate_run(repo, run_id)

    assert not statusline.session_reset_progress(json.dumps({"cwd": str(repo)}))
    assert progress_file.read_active_run_id(repo) == run_id


def test_session_reset_progress_skips_malformed_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id = "implement-20260708.1"
    progress_file.activate_run(repo, run_id)

    assert not statusline.session_reset_progress("not json")
    assert progress_file.read_active_run_id(repo) == run_id


def test_session_reset_progress_skips_opt_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id = "implement-20260708.1"
    progress_file.activate_run(repo, run_id)

    assert not statusline.session_reset_progress(
        json.dumps({"source": "startup", "cwd": str(repo)}),
        env={"LARCH_STATUSLINE_DISABLE": "1"},
    )
    assert progress_file.read_active_run_id(repo) == run_id


def test_session_reset_progress_skips_live_bgjob(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id = "implement-20260708.1"
    progress_file.activate_run(repo, run_id)

    def clone_has_live_bgjob(_repo_root: Path) -> bool:
        return True

    monkeypatch.setattr(statusline, "_clone_has_live_bgjob", clone_has_live_bgjob)

    assert not statusline.session_reset_progress(json.dumps({"source": "startup", "cwd": str(repo)}))
    assert progress_file.read_active_run_id(repo) == run_id


def test_timing_mark_appends_progress_breadcrumb(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    ledger = tmp_path / "timing.tsv"
    monkeypatch.chdir(repo)
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("LARCH_TIMING_SKILL", "design")
    progress_file.activate_run(repo, "design-20260708.1")

    assert timing.timing_mark_main(["--ledger", str(ledger), "design Step 2b: plan"]) == 0

    assert progress_file.run_progress_path(repo, "design-20260708.1").read_text(encoding="utf-8") == (
        "[design 2b] design Step 2b: plan started\n"
    )
    assert not progress_file.progress_path(repo).exists()


def test_install_statusline_creates_settings_and_launcher(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    plugin = tmp_path / "plugin"
    repo.mkdir()
    (repo / ".claude").mkdir()
    (plugin / "python").mkdir(parents=True)
    _ = (plugin / "python" / "cli.py").write_text("", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))

    assert statusline_install.install_statusline(repo_root=repo, plugin_root=plugin)

    settings = json.loads((repo / ".claude" / "settings.local.json").read_text(encoding="utf-8"))
    assert settings["statusLine"]["refreshInterval"] == 2
    assert settings["statusLine"]["command"].endswith("/.cache/larch/statusline.sh")
    launcher = home / ".cache" / "larch" / "statusline.sh"
    assert "progress statusline" in launcher.read_text(encoding="utf-8")
    assert "sh -c" in launcher.read_text(encoding="utf-8")


def test_install_statusline_preserves_local_non_larch_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    plugin = tmp_path / "plugin"
    (repo / ".claude").mkdir(parents=True)
    (plugin / "python").mkdir(parents=True)
    settings_path = repo / ".claude" / "settings.local.json"
    original = '{"statusLine":{"type":"command","command":"custom"},"x":1}\n'
    _ = settings_path.write_text(original, encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))

    assert not statusline_install.install_statusline(repo_root=repo, plugin_root=plugin)
    assert settings_path.read_text(encoding="utf-8") == original


def test_install_statusline_invalid_json_untouched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    plugin = tmp_path / "plugin"
    (repo / ".claude").mkdir(parents=True)
    (plugin / "python").mkdir(parents=True)
    settings_path = repo / ".claude" / "settings.local.json"
    _ = settings_path.write_text("{bad", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))

    assert not statusline_install.install_statusline(repo_root=repo, plugin_root=plugin)
    assert settings_path.read_text(encoding="utf-8") == "{bad"


def test_install_statusline_opt_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    plugin = tmp_path / "plugin"
    repo.mkdir()
    plugin.mkdir()
    monkeypatch.setenv("LARCH_STATUSLINE_DISABLE", "1")

    assert statusline_install.install_statusline_main(["--repo-root", str(repo), "--plugin-root", str(plugin)]) == 0
    assert not (repo / ".claude" / "settings.local.json").exists()



def test_install_statusline_refuses_symlinked_settings_ancestor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    plugin = tmp_path / "plugin"
    target = tmp_path / "claude-target"
    repo.mkdir()
    target.mkdir()
    (plugin / "python").mkdir(parents=True)
    (repo / ".claude").symlink_to(target)
    monkeypatch.setenv("HOME", str(home))

    assert not statusline_install.install_statusline(repo_root=repo, plugin_root=plugin)
    assert not (target / "settings.local.json").exists()


def test_install_statusline_chains_user_scope_statusline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    plugin = tmp_path / "plugin"
    (home / ".claude").mkdir(parents=True)
    (repo / ".claude").mkdir(parents=True)
    (plugin / "python").mkdir(parents=True)
    _ = (home / ".claude" / "settings.json").write_text(
        json.dumps({"statusLine": {"type": "command", "command": "printf user"}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))

    assert statusline_install.install_statusline(repo_root=repo, plugin_root=plugin)

    launcher = (home / ".cache" / "larch" / "statusline.sh").read_text(encoding="utf-8")
    assert "printf user" in launcher
    assert "progress statusline" in launcher
    assert "timeout 2s" in launcher
    assert "bash -lc" not in launcher


def test_install_statusline_prefers_direct_exec_for_single_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    plugin = tmp_path / "plugin"
    (home / ".claude").mkdir(parents=True)
    (repo / ".claude").mkdir(parents=True)
    (plugin / "python").mkdir(parents=True)
    _ = (home / ".claude" / "settings.json").write_text(
        json.dumps({"statusLine": {"type": "command", "command": "/bin/true"}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))

    assert statusline_install.install_statusline(repo_root=repo, plugin_root=plugin)

    launcher = (home / ".cache" / "larch" / "statusline.sh").read_text(encoding="utf-8")
    assert "timeout 2s" in launcher
    assert ' "$USER_STATUSLINE_CMD" 2>/dev/null || true' in launcher


def test_install_statusline_skips_symlinked_user_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    plugin = tmp_path / "plugin"
    settings_target = tmp_path / "settings-target.json"
    (home / ".claude").mkdir(parents=True)
    (repo / ".claude").mkdir(parents=True)
    (plugin / "python").mkdir(parents=True)
    _ = settings_target.write_text(json.dumps({"statusLine": {"type": "command", "command": "printf user"}}), encoding="utf-8")
    (home / ".claude" / "settings.json").symlink_to(settings_target)
    monkeypatch.setenv("HOME", str(home))

    assert statusline_install.install_statusline(repo_root=repo, plugin_root=plugin)

    launcher = (home / ".cache" / "larch" / "statusline.sh").read_text(encoding="utf-8")
    assert "printf user" not in launcher
    assert "progress statusline" in launcher


def test_install_statusline_main_skips_stdin_when_roots_supplied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    plugin = tmp_path / "plugin"
    (repo / ".claude").mkdir(parents=True)
    (plugin / "python").mkdir(parents=True)
    _ = (plugin / "python" / "cli.py").write_text("", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(statusline_install.sys.stdin, "read", lambda: (_ for _ in ()).throw(AssertionError("stdin should not be read")))

    assert statusline_install.install_statusline_main(["--repo-root", str(repo), "--plugin-root", str(plugin)]) == 0

def test_sessionstart_statusline_harness() -> None:
    result = subprocess.run(
        ["bash", "scripts/test-sessionstart-statusline.sh"],
        cwd=Path(__file__).resolve().parents[3],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
