# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Tests for upgrade-larch helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import config
import upgrade_larch
import proc

# Intentional literal guard: keep in sync with python/upgrade_larch.py LARCH_SPARSE_DIRS.
EXPECTED_LARCH_SPARSE_DIRS = ".claude-plugin agents docs hooks python scripts skills"


def _expected_normalized_sparse_dirs() -> str:
    return "\n".join(sorted(part for part in EXPECTED_LARCH_SPARSE_DIRS.split() if part))


def _result(argv: list[str], returncode: int = 0, stdout: str = "", stderr: str = "") -> proc.CommandResult:
    return proc.CommandResult(tuple(argv), returncode, stdout, stderr, 0.0)


def _canonical_cache_root(home: Path, version: str = "1.2.3") -> Path:
    return home / ".claude/plugins/cache/larch-local/larch" / version


def _touch(path: Path, text: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _populate_cleanup_fixture(version_root: Path) -> None:
    for path in (
        version_root / "python/test_cleanup.py",
        version_root / "python/conftest.py",
        version_root / "python/pyproject.toml",
        version_root / "python/ruff.toml",
        version_root / "python/requirements-test.txt",
        version_root / "python/requirements-dev.txt",
        version_root / "python/pyrightconfig.json",
        version_root / "python/.pylintrc",
        version_root / "python/review_test_support.py",
        version_root / "python/harness_makefile.py",
        version_root / "scripts/test-upgrade.sh",
        version_root / "scripts/test-upgrade.md",
        version_root / "skills/design/scripts/test-design-step5c.sh",
        version_root / "skills/design/scripts/test-design-step5c.md",
        version_root / "parallel-tests.py",
        version_root / "Makefile",
        version_root / ".pre-commit-config.yaml",
        version_root / ".markdownlint.json",
        version_root / ".markdownlintignore",
        version_root / "agent-lint.toml",
        version_root / ".agnix.toml",
        version_root / ".gitleaks.toml",
    ):
        _touch(path)
    for path in (
        version_root / "python/cli.py",
        version_root / "python/checks.py",
        version_root / "skills/design/SKILL.md",
        version_root / "docs/installation-and-setup.md",
        version_root / "python/tester.py",
    ):
        _touch(path, "runtime")
    for dirname in (".claude", ".github", ".gemini", "tests"):
        _touch(version_root / dirname / "fixture.txt")


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
    upgrade_larch.prune_cached_versions(cache_dir=cache, target_version="1.0.0", installed_version="1.0.1")
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


def test_larch_sparse_dirs_matches_bash_literal() -> None:
    assert upgrade_larch.LARCH_SPARSE_DIRS == EXPECTED_LARCH_SPARSE_DIRS


def test_clean_test_files_from_cache_removes_dev_test_infrastructure(monkeypatch: Any, tmp_path: Path) -> None:
    home = tmp_path / "home"
    version_root = _canonical_cache_root(home)
    _populate_cleanup_fixture(version_root)
    monkeypatch.setenv("HOME", str(home))

    upgrade_larch.clean_test_files_from_cache("1.2.3")

    removed = (
        "python/test_cleanup.py",
        "python/conftest.py",
        "python/pyproject.toml",
        "python/ruff.toml",
        "python/requirements-test.txt",
        "python/requirements-dev.txt",
        "python/pyrightconfig.json",
        "python/.pylintrc",
        "python/review_test_support.py",
        "python/harness_makefile.py",
        "scripts/test-upgrade.sh",
        "scripts/test-upgrade.md",
        "skills/design/scripts/test-design-step5c.sh",
        "skills/design/scripts/test-design-step5c.md",
        "parallel-tests.py",
        "Makefile",
        ".pre-commit-config.yaml",
        ".markdownlint.json",
        ".markdownlintignore",
        "agent-lint.toml",
        ".agnix.toml",
        ".gitleaks.toml",
    )
    kept = (
        "python/cli.py",
        "python/checks.py",
        "skills/design/SKILL.md",
        "docs/installation-and-setup.md",
        "python/tester.py",
    )
    for path in removed:
        assert not (version_root / path).exists()
    for dirname in (".claude", ".github", ".gemini", "tests"):
        assert not (version_root / dirname).exists()
    for path in kept:
        assert (version_root / path).exists()


def test_clean_test_files_from_cache_skips_symlink_version_dir(monkeypatch: Any, tmp_path: Path) -> None:
    home = tmp_path / "home"
    version_root = _canonical_cache_root(home)
    target = tmp_path / "outside-version"
    _touch(target / "python/test_escape.py")
    version_root.parent.mkdir(parents=True)
    version_root.symlink_to(target, target_is_directory=True)
    monkeypatch.setenv("HOME", str(home))

    upgrade_larch.clean_test_files_from_cache("1.2.3")

    assert (target / "python/test_escape.py").exists()
    assert version_root.is_symlink()


def test_clean_test_files_from_cache_confines_directory_cleanup(monkeypatch: Any, tmp_path: Path) -> None:
    home = tmp_path / "home"
    version_root = _canonical_cache_root(home)
    version_root.mkdir(parents=True)
    outside = tmp_path / "outside-dir"
    outside.mkdir()
    (version_root / ".github").symlink_to(outside, target_is_directory=True)
    _touch(version_root / "docs/tests/fixture.txt")
    _touch(version_root / "nested/.claude/fixture.txt")
    _touch(version_root / "tests/fixture.txt")
    monkeypatch.setenv("HOME", str(home))

    upgrade_larch.clean_test_files_from_cache("1.2.3")

    assert (version_root / ".github").is_symlink()
    assert outside.exists()
    assert (version_root / "docs/tests/fixture.txt").exists()
    assert (version_root / "nested/.claude/fixture.txt").exists()
    assert not (version_root / "tests").exists()


def test_clean_test_files_from_cache_skips_resolved_escapes(monkeypatch: Any, tmp_path: Path) -> None:
    home = tmp_path / "home"
    version_root = _canonical_cache_root(home)
    outside = tmp_path / "outside-python"
    _touch(outside / "test_escape.py")
    version_root.mkdir(parents=True)
    (version_root / "python").symlink_to(outside, target_is_directory=True)
    monkeypatch.setenv("HOME", str(home))

    upgrade_larch.clean_test_files_from_cache("1.2.3")

    assert (outside / "test_escape.py").exists()
    assert (version_root / "python").is_symlink()


def test_clean_test_files_from_cache_unlinks_confined_symlink_leaf(monkeypatch: Any, tmp_path: Path) -> None:
    home = tmp_path / "home"
    version_root = _canonical_cache_root(home)
    target = _touch(version_root / "python/target.py")
    link = version_root / "python/test_link.py"
    link.symlink_to(target)
    monkeypatch.setenv("HOME", str(home))

    upgrade_larch.clean_test_files_from_cache("1.2.3")

    assert not link.exists()
    assert target.exists()


def test_marketplace_sparse_cone_matches(monkeypatch: Any, tmp_path: Path) -> None:
    home = tmp_path / "home"
    clone = home / ".claude/plugins/marketplaces/larch-local"
    clone.mkdir(parents=True)
    (clone / ".git").mkdir()
    sparse_dirs = _expected_normalized_sparse_dirs()

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


def test_run_already_latest_cleans_cache_without_reinstall(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    home = tmp_path / "home"
    version_root = _canonical_cache_root(home)
    _touch(version_root / "python/test_cleanup.py")
    _touch(version_root / ".claude/fixture.txt")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(version_root))
    monkeypatch.setenv("LARCH_EXPECTED_STABLE_VERSION", "1.2.3")
    monkeypatch.setattr(upgrade_larch, "_marketplace_sparse_cone_matches", lambda: True)
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv[:3] == ["claude", "plugin", "list"]:
            return _result(argv, stdout="larch@larch-local\n  Version: 1.2.3\n")
        return _result(argv)

    monkeypatch.setattr(upgrade_larch.proc, "run", fake_run)

    assert upgrade_larch.run_main([]) == 0
    err = capsys.readouterr().err
    assert "No upgrade needed." in err
    assert not (version_root / "python/test_cleanup.py").exists()
    assert not (version_root / ".claude").exists()
    assert not any(call[:3] == ["claude", "plugin", "install"] for call in calls)


def test_run_post_install_cleanup_runs_before_unverified_failure(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    home = tmp_path / "home"
    running_root = _canonical_cache_root(home, "1.0.0")
    actual_root = _canonical_cache_root(home, "1.5.0")
    running_root.mkdir(parents=True)
    _touch(actual_root / "python/test_cleanup.py")
    _touch(actual_root / ".github/fixture.txt")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(running_root))
    monkeypatch.setenv("LARCH_EXPECTED_STABLE_VERSION", "2.0.0")
    monkeypatch.setattr(upgrade_larch, "_marketplace_sparse_cone_matches", lambda: True)
    calls: list[list[str]] = []
    list_versions = iter(("1.0.0", "1.5.0", "1.5.0"))

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv[:3] == ["claude", "plugin", "list"]:
            version = next(list_versions)
            return _result(argv, stdout=f"larch@larch-local\n  Version: {version}\n")
        return _result(argv)

    monkeypatch.setattr(upgrade_larch.proc, "run", fake_run)

    assert upgrade_larch.run_main([]) == 1
    err = capsys.readouterr().err
    assert "Upgrade incomplete: expected stable version 2.0.0 was not verified." in err
    assert not (actual_root / "python/test_cleanup.py").exists()
    assert not (actual_root / ".github").exists()
    assert any(call[:3] == ["claude", "plugin", "install"] for call in calls)


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
