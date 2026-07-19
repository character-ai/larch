# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""Tests for upgrade-larch helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from larch.core import config, proc, upgrade_larch

EXPECTED_LARCH_SPARSE_DIRS = ".claude-plugin"


def _result(
    argv: list[str], returncode: int = 0, stdout: str = "", stderr: str = ""
) -> proc.CommandResult:
    return proc.CommandResult(tuple(argv), returncode, stdout, stderr, 0.0)


def _root(home: Path, version: str) -> Path:
    return home / ".claude/plugins/cache/larch-local/larch" / version


def _install_root(root: Path, version: str) -> None:
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin/plugin.json").write_text(
        json.dumps({"version": version}), encoding="utf-8"
    )
    (root / "scripts").mkdir()
    (root / "scripts/larch.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (root / "scripts/larch.sh").chmod(0o755)
    (root / "bin").mkdir()
    (root / "bin/larch").write_text("binary", encoding="utf-8")
    (root / "bin/larch").chmod(0o755)


def _plugin_json(root: Path, version: str) -> str:
    return json.dumps(
        [
            {
                "id": "larch@larch-local",
                "version": version,
                "scope": "user",
                "installPath": str(root),
            }
        ]
    )


def test_release_step7_resolves_active_cache(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    home = tmp_path / "home"
    root = _root(home, "1.2.3")
    root.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(root))
    assert upgrade_larch.release_step7_root_main([]) == 0
    assert f"RESOLVED_ROOT={root}" in capsys.readouterr().out


def test_resolve_installed_root_uses_claude_json_metadata(
    monkeypatch: Any, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    root = _root(home, "1.2.3")
    _install_root(root, "1.2.3")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(
        upgrade_larch.proc,
        "run",
        lambda argv, **_: _result(argv, stdout=_plugin_json(root, "1.2.3")),
    )
    assert upgrade_larch.resolve_installed_larch_root("1.2.3") == root


def test_resolve_installed_root_rejects_manifest_mismatch(
    monkeypatch: Any, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    root = _root(home, "1.2.3")
    _install_root(root, "1.2.2")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(
        upgrade_larch.proc,
        "run",
        lambda argv, **_: _result(argv, stdout=_plugin_json(root, "1.2.3")),
    )
    assert upgrade_larch.resolve_installed_larch_root("1.2.3") is None


def test_larch_sparse_dirs_matches_literal() -> None:
    assert upgrade_larch.LARCH_SPARSE_DIRS == EXPECTED_LARCH_SPARSE_DIRS


def test_marketplace_source_matches_runtime_only_url(monkeypatch: Any) -> None:
    payload = json.dumps(
        [
            {
                "name": "larch-local",
                "source": "url",
                "url": upgrade_larch.LARCH_MARKETPLACE_SOURCE,
            }
        ]
    )
    monkeypatch.setattr(
        upgrade_larch.proc, "run", lambda argv, **_: _result(argv, stdout=payload)
    )
    assert upgrade_larch._marketplace_source_matches() is True  # pyright: ignore[reportPrivateUsage]


def test_refresh_marketplace_migrates_to_runtime_only_url(
    monkeypatch: Any, tmp_path: Path
) -> None:
    calls: list[list[str]] = []
    source_checks = iter((False, True))

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        return _result(argv)

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(
        upgrade_larch, "_marketplace_source_matches", lambda: next(source_checks)
    )
    monkeypatch.setattr(upgrade_larch.proc, "run", fake_run)

    assert upgrade_larch._refresh_marketplace() == "install"  # pyright: ignore[reportPrivateUsage]
    assert [
        "claude",
        "plugin",
        "marketplace",
        "add",
        upgrade_larch.LARCH_MARKETPLACE_SOURCE,
    ] in calls


def test_run_already_latest_repairs_and_verifies_binary(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    home = tmp_path / "home"
    root = _root(home, "1.2.3")
    _install_root(root, "1.2.3")
    plugin_json = _plugin_json(root, "1.2.3")
    identity = (
        '{"schema_version":1,"version":"1.2.3","target":"aarch64-apple-darwin"}\n'
    )
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv == ["claude", "plugin", "list", "--json"]:
            return _result(argv, stdout=plugin_json)
        if argv[-2:] == ["bootstrap", "self-check"]:
            return _result(argv, stdout=identity)
        return _result(argv)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(root))
    monkeypatch.setenv(
        "CLAUDE_PLUGIN_DATA", str(home / ".claude/plugins/data/larch-local/larch")
    )
    monkeypatch.setenv("LARCH_EXPECTED_STABLE_VERSION", "1.2.3")
    monkeypatch.setattr(upgrade_larch, "_marketplace_source_matches", lambda: True)
    monkeypatch.setattr(upgrade_larch.proc, "run", fake_run)
    assert upgrade_larch.run_main([]) == 0
    assert "Binary verification passed. No upgrade needed." in capsys.readouterr().err
    assert not any(call[:3] == ["claude", "plugin", "update"] for call in calls)


def test_run_upgrade_preflights_then_updates_and_bootstraps_new_root(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    home = tmp_path / "home"
    old_root = _root(home, "1.0.0")
    new_root = _root(home, "2.0.0")
    _install_root(old_root, "1.0.0")
    _install_root(new_root, "2.0.0")
    versions = iter(
        (
            _plugin_json(old_root, "1.0.0"),
            _plugin_json(new_root, "2.0.0"),
            _plugin_json(new_root, "2.0.0"),
        )
    )
    identity = (
        '{"schema_version":1,"version":"2.0.0","target":"aarch64-apple-darwin"}\n'
    )
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv == ["claude", "plugin", "list", "--json"]:
            return _result(argv, stdout=next(versions))
        if "--preflight-release" in argv:
            return _result(argv, stdout="LARCH_PREFLIGHT_VERSION=2.0.0\n")
        if argv[-2:] == ["bootstrap", "self-check"]:
            return _result(argv, stdout=identity)
        return _result(argv)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(old_root))
    monkeypatch.setenv(
        "CLAUDE_PLUGIN_DATA", str(home / ".claude/plugins/data/larch-local/larch")
    )
    monkeypatch.setenv("LARCH_EXPECTED_STABLE_VERSION", "2.0.0")
    monkeypatch.setattr(upgrade_larch, "_marketplace_source_matches", lambda: True)
    monkeypatch.setattr(upgrade_larch.proc, "run", fake_run)
    assert upgrade_larch.run_main([]) == 0
    preflight_index = next(
        index for index, call in enumerate(calls) if "--preflight-release" in call
    )
    assert preflight_index < calls.index(
        ["claude", "plugin", "marketplace", "update", "larch-local"]
    )
    assert ["claude", "plugin", "update", "larch@larch-local"] in calls
    assert "LARCH_RESTART_REQUIRED=true" in capsys.readouterr().err


def test_run_marketplace_failure_leaves_cache_roots_untouched(
    monkeypatch: Any, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    old_root = _root(home, "1.0.0")
    _install_root(old_root, "1.0.0")
    marker = old_root / "keep-me"
    marker.write_text("old", encoding="utf-8")

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv == ["claude", "plugin", "list", "--json"]:
            return _result(argv, stdout=_plugin_json(old_root, "1.0.0"))
        if "--preflight-release" in argv:
            return _result(argv, stdout="LARCH_PREFLIGHT_VERSION=2.0.0\n")
        if argv[:4] == ["claude", "plugin", "marketplace", "update"]:
            return _result(argv, returncode=1)
        return _result(argv)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(old_root))
    monkeypatch.setenv(
        "CLAUDE_PLUGIN_DATA", str(home / ".claude/plugins/data/larch-local/larch")
    )
    monkeypatch.setenv("LARCH_EXPECTED_STABLE_VERSION", "2.0.0")
    monkeypatch.setattr(upgrade_larch, "_marketplace_source_matches", lambda: True)
    monkeypatch.setattr(upgrade_larch.proc, "run", fake_run)
    assert upgrade_larch.run_main([]) == 1
    assert marker.read_text(encoding="utf-8") == "old"


def test_run_plugin_update_failure_keeps_prior_root_and_prints_retry(
    monkeypatch: Any,
    tmp_path: Path,
    capsys: Any,
) -> None:
    home = tmp_path / "home"
    old_root = _root(home, "1.0.0")
    _install_root(old_root, "1.0.0")
    marker = old_root / "keep-me"
    marker.write_text("old", encoding="utf-8")

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv == ["claude", "plugin", "list", "--json"]:
            return _result(argv, stdout=_plugin_json(old_root, "1.0.0"))
        if "--preflight-release" in argv:
            return _result(argv, stdout="LARCH_PREFLIGHT_VERSION=2.0.0\n")
        if argv == ["claude", "plugin", "update", "larch@larch-local"]:
            return _result(argv, returncode=7)
        return _result(argv)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(old_root))
    monkeypatch.setenv(
        "CLAUDE_PLUGIN_DATA", str(home / ".claude/plugins/data/larch-local/larch")
    )
    monkeypatch.setenv("LARCH_EXPECTED_STABLE_VERSION", "2.0.0")
    monkeypatch.setattr(upgrade_larch, "_marketplace_source_matches", lambda: True)
    monkeypatch.setattr(upgrade_larch.proc, "run", fake_run)

    assert upgrade_larch.run_main([]) == 7
    assert marker.read_text(encoding="utf-8") == "old"
    assert upgrade_larch.LARCH_MARKETPLACE_SOURCE in capsys.readouterr().err


def test_run_new_root_bootstrap_failure_is_retryable(
    monkeypatch: Any, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    old_root = _root(home, "1.0.0")
    new_root = _root(home, "2.0.0")
    _install_root(old_root, "1.0.0")
    _install_root(new_root, "2.0.0")
    marker = old_root / "keep-me"
    marker.write_text("old", encoding="utf-8")
    versions = iter(
        (
            _plugin_json(old_root, "1.0.0"),
            _plugin_json(new_root, "2.0.0"),
            _plugin_json(new_root, "2.0.0"),
        )
    )

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv == ["claude", "plugin", "list", "--json"]:
            return _result(argv, stdout=next(versions))
        if "--preflight-release" in argv:
            return _result(argv, stdout="LARCH_PREFLIGHT_VERSION=2.0.0\n")
        if argv[-2:] == ["bootstrap", "self-check"]:
            return _result(argv, returncode=1)
        return _result(argv)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(old_root))
    monkeypatch.setenv(
        "CLAUDE_PLUGIN_DATA", str(home / ".claude/plugins/data/larch-local/larch")
    )
    monkeypatch.setenv("LARCH_EXPECTED_STABLE_VERSION", "2.0.0")
    monkeypatch.setattr(upgrade_larch, "_marketplace_source_matches", lambda: True)
    monkeypatch.setattr(upgrade_larch.proc, "run", fake_run)

    assert upgrade_larch.run_main([]) == 1
    assert marker.read_text(encoding="utf-8") == "old"
    assert new_root.is_dir()


def test_restore_operator_stdout_when_quiet(monkeypatch: Any) -> None:
    calls: list[tuple[int, int]] = []
    monkeypatch.setenv(config.ENV_LARCH_QUIET_PID, str(os.getpid()))
    monkeypatch.setattr(
        upgrade_larch.os, "dup2", lambda src, dst: calls.append((src, dst))
    )
    upgrade_larch._restore_operator_stdout()  # pyright: ignore[reportPrivateUsage]
    assert calls == [(3, 1)]
