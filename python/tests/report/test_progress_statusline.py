# pyright: reportPrivateUsage=false, reportUnusedCallResult=false
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
    assert not progress_file.append_breadcrumb(repo, "implement", "5", "see https://example.test")

    assert progress_file.progress_path(repo).read_text(encoding="utf-8") == "[implement 5] reviewers 7/12 done\n"


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


def test_statusline_fail_silent_empty_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(tmp_path / "cache"))

    assert statusline.render_statusline(stdin_text="") == ""
    assert statusline.render_statusline(stdin_text="not json") == ""
    assert statusline.render_statusline(stdin_text=json.dumps({"cwd": str(tmp_path)})) == ""


def test_statusline_renders_yellow_line_and_is_calm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("LARCH_TEST_CACHE_HOME", str(cache))
    assert progress_file.append_breadcrumb(repo, "implement", "5", "review round 1 running")
    payload = json.dumps({"workspace": {"current_dir": str(repo)}})
    env = {"LARCH_TEST_STATUSLINE_NOW": "1700000000", "LARCH_STATUSLINE_STALE_AFTER_S": "999999"}

    first = statusline.render_statusline(stdin_text=payload, env=env)
    second = statusline.render_statusline(stdin_text=payload, env=env)

    assert first == second
    assert first.startswith("\033[33mlarch ")
    assert "[implement 5] review round 1 running" in first
    assert first.endswith("\033[0m\n")


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

def test_sessionstart_statusline_harness() -> None:
    result = subprocess.run(
        ["bash", "scripts/test-sessionstart-statusline.sh"],
        cwd=Path(__file__).resolve().parents[3],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
