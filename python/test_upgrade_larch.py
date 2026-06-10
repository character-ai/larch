# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Tests for upgrade-larch helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
