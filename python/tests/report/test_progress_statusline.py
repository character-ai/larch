# pyright: reportPrivateUsage=false, reportUnusedCallResult=false
from __future__ import annotations

import json
import os
import re
import shutil
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

    assert progress_file.append_breadcrumb(repo, "implement", "5", "reviewers 7/12 done")
    assert not progress_file.append_breadcrumb(repo, "implement", "5", "bad\nrow")
    assert not progress_file.append_breadcrumb(repo, "implement", "5", "bad\ttab")
    assert not progress_file.append_breadcrumb(repo, "implement", "5", "bad\x1b[31mrow")
    assert not progress_file.append_breadcrumb(repo, "implement", "5", "bad\x9b31mrow")
    assert not progress_file.append_breadcrumb(repo, "implement", "5", "see https://example.test")
    assert not progress_file.append_breadcrumb(repo, "implement", "5", "osc \x1b]8;;https://example.test\x07 link")

    assert progress_file.progress_path(repo).read_text(encoding="utf-8") == "[implement 5] reviewers 7/12 done\n"


def test_append_breadcrumb_rechecks_after_mkdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    calls = 0

    def fake_assert(_path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("swapped ancestor")

    monkeypatch.setattr(progress_file.larch_io, "assert_no_symlink_path_or_ancestors", fake_assert)

    assert not progress_file.append_breadcrumb(repo, "implement", "5", "reviewers 7/12 done")
    assert calls == 2


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


def test_activate_run_writes_current_with_fd_anchored_helpers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id = "implement-20260708.1"
    open_calls: list[Path] = []
    write_calls: list[tuple[str, str, int, str]] = []
    original_open = progress_file._open_verified_dir
    original_write = progress_file._atomic_write_in_dir

    def traced_open(path: Path) -> int:
        open_calls.append(path)
        return original_open(path)

    def traced_write(dir_fd: int, name: str, text: str, *, mode: int = 0o600, temp_prefix: str = ".current.") -> None:
        write_calls.append((name, text, mode, temp_prefix))
        original_write(dir_fd, name, text, mode=mode, temp_prefix=temp_prefix)

    monkeypatch.setattr(progress_file, "_open_verified_dir", traced_open)
    monkeypatch.setattr(progress_file, "_atomic_write_in_dir", traced_write)

    progress_file.activate_run(repo, run_id)

    assert progress_file.current_run_path(repo).read_text(encoding="utf-8") == f"{run_id}\n"
    assert progress_file.run_progress_dir(repo, run_id).is_dir()
    assert open_calls == [progress_file.progress_clone_dir(repo)]
    assert write_calls == [(progress_file.CURRENT_RUN_FILENAME, f"{run_id}\n", 0o600, ".current.")]


def test_activate_run_refuses_clone_dir_swap_before_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    clone_dir = progress_file.progress_clone_dir(repo)
    pointer_path = progress_file.current_run_path(repo)
    target = tmp_path / "outside"
    target.mkdir()
    original_assert = progress_file.larch_io.assert_no_symlink_path_or_ancestors
    swapped = False

    def swapping_assert(path: Path) -> None:
        nonlocal swapped
        original_assert(path)
        if not swapped and path == pointer_path and clone_dir.is_dir():
            shutil.rmtree(clone_dir)
            clone_dir.symlink_to(target, target_is_directory=True)
            swapped = True

    monkeypatch.setattr(progress_file.larch_io, "assert_no_symlink_path_or_ancestors", swapping_assert)

    with pytest.raises(OSError, match="symlink"):
        progress_file.activate_run(repo, "design-20260708.1")
    assert swapped
    assert not (target / progress_file.CURRENT_RUN_FILENAME).exists()


def test_read_active_run_id_normalizes_activate_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id = "design-20260708.1"
    progress_file.activate_run(repo, run_id)

    assert progress_file._read_active_run_id(progress_file.progress_clone_dir(repo)) == run_id

    progress_file.current_run_path(repo).write_text("bad id\n", encoding="utf-8")
    assert progress_file._read_active_run_id(progress_file.progress_clone_dir(repo)) is None

    progress_file.current_run_path(repo).write_text(" \t\n", encoding="utf-8")
    assert progress_file._read_active_run_id(progress_file.progress_clone_dir(repo)) is None


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


def test_append_breadcrumb_for_run_refuses_parent_swap_before_open(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    target = tmp_path / "outside-run"
    repo.mkdir()
    target.mkdir()
    run_id = "design-20260708.1"
    run_dir = progress_file.run_progress_dir(repo, run_id)
    log_path = progress_file.run_progress_path(repo, run_id)
    original_assert = progress_file.larch_io.assert_no_symlink_path_or_ancestors
    checked_once = False

    def swapping_assert(path: Path) -> None:
        nonlocal checked_once
        original_assert(path)
        if checked_once and path == log_path and run_dir.is_dir():
            run_dir.rmdir()
            run_dir.symlink_to(target, target_is_directory=True)
        if path == log_path:
            checked_once = True

    monkeypatch.setattr(progress_file.larch_io, "assert_no_symlink_path_or_ancestors", swapping_assert)

    assert not progress_file.append_breadcrumb_for_run(repo, run_id, "design", "3", "reviewers done")
    assert not (target / progress_file.RUN_BREADCRUMB_FILENAME).exists()


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

    with pytest.raises(OSError, match="symlink"):
        progress_file.activate_run(repo, "design-20260708.1")

    progress_file.run_progress_dir(repo, "design-20260708.1").unlink()
    progress_file.current_run_path(repo).symlink_to(target_file)
    with pytest.raises(OSError, match="symlink"):
        progress_file.activate_run(repo, "design-20260708.1")


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


def test_statusline_fail_silent_empty_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    repo.mkdir()
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
    assert progress_file.append_breadcrumb(repo, "implement", "5", "review round 1 running")
    payload = json.dumps({"workspace": {"current_dir": str(repo)}})
    env = {"LARCH_TEST_STATUSLINE_NOW": "1700000000", "LARCH_STATUSLINE_STALE_AFTER_S": "999999"}

    first = statusline.render_statusline(stdin_text=payload, env=env)
    second = statusline.render_statusline(stdin_text=payload, env={**env, "LARCH_TEST_STATUSLINE_NOW": "1700000061"})

    assert first == second
    assert first.startswith("\033[33mlarch ")
    assert "[implement 5] review round 1 running" in first
    assert first.endswith("\033[0m\n")


def test_statusline_refuses_symlinked_progress_ancestors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "cache"
    cache_target = tmp_path / "cache-target"
    repo = tmp_path / "repo"
    repo.mkdir()
    cache_target.mkdir()
    (cache / "larch").parent.mkdir(parents=True, exist_ok=True)
    (cache / "larch").symlink_to(cache_target)
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(cache))
    path = progress_file.progress_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[implement 5] review round 1 running\n", encoding="utf-8")

    rendered = statusline.render_statusline(stdin_text=json.dumps({"cwd": str(repo)}))

    assert rendered == ""


def test_statusline_stale_and_far_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(cache))
    assert progress_file.append_breadcrumb(repo, "implement", "8", "PR #1234 created")
    path = progress_file.progress_path(repo)
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
    assert ("progress", "activate") in cli._REGISTRY
    assert ("progress", "activate") not in cli._MACHINE_STDOUT_KEYS
    assert ("progress", "report") not in cli._REGISTRY


def test_timing_mark_appends_progress_breadcrumb(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    ledger = tmp_path / "timing.tsv"
    monkeypatch.chdir(repo)
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("LARCH_TIMING_SKILL", "design")

    assert timing.timing_mark_main(["--ledger", str(ledger), "design Step 2b: plan"]) == 0

    assert progress_file.progress_path(repo).read_text(encoding="utf-8") == "[design 2b] design Step 2b: plan started\n"


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
