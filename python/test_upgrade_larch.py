# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Tests for upgrade-larch helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import config
import upgrade_larch
import proc


def _result(argv: list[str], returncode: int = 0, stdout: str = "", stderr: str = "") -> proc.CommandResult:
    return proc.CommandResult(tuple(argv), returncode, stdout, stderr, 0.0)


def test_release_step7_resolves_active_cache(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    home = tmp_path / "home"
    root = home / ".claude/plugins/cache/larch-local/larch/1.2.3"
    root.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(root))
    assert upgrade_larch.release_step7_root_main([]) == 0
    assert f"RESOLVED_ROOT={root}" in capsys.readouterr().out


def test_prune_keeps_target_and_recent(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    for index in range(10):
        version = f"1.0.{index}"
        path = cache / version
        path.mkdir(parents=True)
        (path / ".larch-installed-at").write_text(f"{1000 + index}\n", encoding="utf-8")
    upgrade_larch.prune_cached_versions(cache, "1.0.0", "1.0.1")
    remaining = {path.name for path in cache.iterdir() if path.is_dir()}
    assert "1.0.0" in remaining
    assert "1.0.1" in remaining
    assert len(remaining) == 8


def test_run_stale_active_cache_root_emits_restart(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    home = tmp_path / "home"
    stale_root = home / ".claude/plugins/cache/larch-local/larch/1.0.0"
    stale_root.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(stale_root))
    monkeypatch.setenv("LARCH_EXPECTED_STABLE_VERSION", "2.0.0")
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv[:3] == ["claude", "plugin", "list"]:
            return _result(argv, stdout="larch@larch-local\n  Version: 2.0.0\n")
        if argv[:2] == ["git", "-C"]:
            return _result(argv, returncode=1)
        return _result(argv)

    monkeypatch.setattr(upgrade_larch.proc, "run", fake_run)
    assert upgrade_larch.run_main([]) == 0
    err = capsys.readouterr().err
    assert "LARCH_RESTART_REQUIRED=true" in err
    assert "still running cached larch 1.0.0" in err
    assert any(call[:3] == ["claude", "plugin", "install"] for call in calls)


def test_run_marketplace_failure_returns_nonzero(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    plugin_root = tmp_path / "cache/1.0.0"
    plugin_root.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin_root))
    monkeypatch.setenv("LARCH_EXPECTED_STABLE_VERSION", "2.0.0")

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["claude", "plugin", "list"]:
            return _result(argv, stdout="larch@larch-local\n  Version: 1.0.0\n")
        if argv[:4] == ["claude", "plugin", "marketplace", "add"]:
            return _result(argv, returncode=1, stderr="add failed")
        if argv[:2] == ["git", "-C"]:
            return _result(argv, returncode=1)
        return _result(argv)

    monkeypatch.setattr(upgrade_larch.proc, "run", fake_run)
    assert upgrade_larch.run_main([]) == 1
    err = capsys.readouterr().err
    assert "Recovery: run these commands manually to reinstall:" in err
    assert "LARCH_RESTART_REQUIRED=true" in err


def test_marketplace_sparse_cone_matches(monkeypatch: Any, tmp_path: Path) -> None:
    home = tmp_path / "home"
    clone = home / ".claude/plugins/marketplaces/larch-local"
    clone.mkdir(parents=True)
    (clone / ".git").mkdir()
    sparse_dirs = upgrade_larch.normalize_sparse_dirs()

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:5] == ["git", "-C", str(clone), "sparse-checkout", "list"]:
            return _result(argv, stdout=sparse_dirs + "\n")
        return _result(argv)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(upgrade_larch.proc, "run", fake_run)
    assert upgrade_larch._marketplace_sparse_cone_matches() is True  # pyright: ignore[reportPrivateUsage]


def test_backfill_install_stamps(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    version_dir = cache / "1.0.0"
    version_dir.mkdir(parents=True)
    old_time = 12345
    os.utime(version_dir, (old_time, old_time))
    upgrade_larch.backfill_install_stamps(cache)
    assert (version_dir / ".larch-installed-at").read_text(encoding="utf-8").strip() == str(old_time)


def test_run_main_initializes_quiet_mode(monkeypatch: Any, tmp_path: Path) -> None:
    plugin_root = tmp_path / "cache/1.0.0"
    plugin_root.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin_root))
    monkeypatch.setenv("LARCH_EXPECTED_STABLE_VERSION", "1.0.0")
    quiet_calls: list[str] = []

    def fake_quiet_init(**kwargs: object) -> None:
        quiet_calls.append(str(kwargs.get("argv0")))

    monkeypatch.setattr(upgrade_larch.logging_util, "quiet_init", fake_quiet_init)
    monkeypatch.setattr(
        upgrade_larch.proc,
        "run",
        lambda argv, **_: _result(argv, stdout="larch@larch-local\n  Version: 1.0.0\n"),
    )
    assert upgrade_larch.run_main([]) == 0
    assert quiet_calls == ["upgrade-larch.sh"]


def test_restore_operator_stdout_when_quiet(monkeypatch: Any) -> None:
    calls: list[tuple[int, int]] = []

    def fake_dup2(src: int, dst: int) -> None:
        calls.append((src, dst))

    monkeypatch.setenv(config.ENV_LARCH_QUIET_PID, str(os.getpid()))
    monkeypatch.setattr(upgrade_larch.os, "dup2", fake_dup2)
    upgrade_larch._restore_operator_stdout()  # pyright: ignore[reportPrivateUsage]
    assert calls == [(3, 1)]


def test_run_same_version_cone_reconciles(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    plugin_root = tmp_path / "cache/1.0.0"
    plugin_root.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin_root))
    monkeypatch.setenv("LARCH_EXPECTED_STABLE_VERSION", "1.0.0")
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv[:3] == ["claude", "plugin", "list"]:
            return _result(argv, stdout="larch@larch-local\n  Version: 1.0.0\n")
        if argv[:2] == ["git", "-C"]:
            return _result(argv, returncode=1)
        return _result(argv)

    monkeypatch.setattr(upgrade_larch.proc, "run", fake_run)
    assert upgrade_larch.run_main([]) == 0
    assert "LARCH_CONE_RECONCILED=false" in capsys.readouterr().err
    assert any(call[:3] == ["claude", "plugin", "install"] for call in calls)
