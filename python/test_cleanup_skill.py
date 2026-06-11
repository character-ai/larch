# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Tests for cleanup skill helper."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import cleanup_skill
import proc


def _result(argv: list[str], returncode: int = 0, stdout: str = "", stderr: str = "") -> proc.CommandResult:
    return proc.CommandResult(tuple(argv), returncode, stdout, stderr, 0.0)


def test_cleanup_removes_old_entries(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    cache = tmp_path / "cache"
    sessions = cache / "larch/sessions"
    old = sessions / "old"
    old.mkdir(parents=True)
    pointer = sessions / "current-implement-env-1.sh"
    pointer.write_text("IMPLEMENT_TMPDIR=/missing\n", encoding="utf-8")
    dangling = sessions / "current-design-env-1.sh"
    dangling.symlink_to(tmp_path / "missing")
    tmp_root = tmp_path / "tmp"
    stale_tmp = tmp_root / "larch-stale"
    stale_tmp.mkdir(parents=True)
    old_time = time.time() - 10 * 86400
    os.utime(old, (old_time, old_time))
    os.utime(stale_tmp, (old_time, old_time))
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    monkeypatch.setenv("LARCH_TEST_TMP_ROOT", str(tmp_root))
    monkeypatch.setattr(cleanup_skill.proc, "run", lambda argv, **_: _result(argv, stdout=""))
    assert cleanup_skill.run_main([]) == 0
    out = capsys.readouterr().out
    assert "CACHE_REMOVED=1" in out
    assert "TMP_REMOVED=1" in out
    assert "SYMLINKS_REMOVED=1" in out
    assert "IMPLEMENT_POINTERS_REMOVED=1" in out


def test_cleanup_invalid_retention_warns(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("LARCH_CLEANUP_RETENTION_DAYS", "bad")
    monkeypatch.setattr(cleanup_skill.proc, "run", lambda argv, **_: _result(argv, stdout=""))
    assert cleanup_skill.run_main([]) == 0
    assert "invalid LARCH_CLEANUP_RETENTION_DAYS" in capsys.readouterr().err


def test_cleanup_reports_session_count(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setattr(cleanup_skill.proc, "run", lambda argv, **_: _result(argv, stdout="100\n101\n"))
    assert cleanup_skill.run_main([]) == 0
    assert "SESSION_COUNT=2" in capsys.readouterr().out


def test_cleanup_keeps_fresh_nested_activity(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    cache = tmp_path / "cache"
    parent = cache / "larch/sessions/stale-parent"
    parent.mkdir(parents=True)
    child = parent / "child.txt"
    child.write_text("fresh\n", encoding="utf-8")
    old_time = time.time() - 10 * 86400
    fresh_time = time.time()
    os.utime(parent, (old_time, old_time))
    os.utime(child, (fresh_time, fresh_time))
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    monkeypatch.setattr(cleanup_skill.proc, "run", lambda argv, **_: _result(argv, stdout="fresh\n"))
    assert cleanup_skill.run_main([]) == 0
    out = capsys.readouterr().out
    assert parent.is_dir()
    assert "CACHE_REMOVED=0" in out


def test_cleanup_find_failure_skips_deletion(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    cache = tmp_path / "cache"
    stale = cache / "larch/sessions/stale-scan-fail"
    stale.mkdir(parents=True)
    old_time = time.time() - 10 * 86400
    os.utime(stale, (old_time, old_time))
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:2] == ["find", str(stale)]:
            return _result(argv, returncode=2)
        return _result(argv, stdout="")

    monkeypatch.setattr(cleanup_skill.proc, "run", fake_run)
    assert cleanup_skill.run_main([]) == 0
    captured = capsys.readouterr()
    assert stale.is_dir()
    assert "failed to scan session activity" in captured.err
    assert "CACHE_REMOVED=0" in captured.out


def test_cleanup_uses_tmp_fallback_root(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    tmp_root = tmp_path / "tmp"
    tmp_root.mkdir()
    stale = tmp_root / "larch-stale"
    stale.mkdir()
    old_time = time.time() - 10 * 86400
    os.utime(stale, (old_time, old_time))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("LARCH_TEST_TMP_ROOT", str(tmp_root))
    monkeypatch.setattr(cleanup_skill.proc, "run", lambda argv, **_: _result(argv, stdout=""))
    assert cleanup_skill.run_main([]) == 0
    out = capsys.readouterr().out
    assert "TMP_REMOVED=1" in out
