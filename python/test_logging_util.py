"""Tests for logging_util.py."""

from __future__ import annotations

import contextlib
import json
import os
from io import StringIO
from pathlib import Path

import pytest

import config
import logging_util


def test_jsonl_journal_roundtrip(tmp_path: Path) -> None:
    journal_path = tmp_path / "journal.jsonl"
    journal = logging_util.JsonlJournal(journal_path, run_id="run-abc")
    record = journal.append("phase", step="2")
    line = journal_path.read_text(encoding="utf-8").strip()
    parsed = json.loads(line)
    assert parsed["event"] == "phase"
    assert parsed["run_id"] == "run-abc"
    assert parsed["step"] == record["step"]


def test_breadcrumb_suppressed_when_quiet(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
    stream = StringIO()
    writer = logging_util.BreadcrumbWriter(stream=stream)
    writer.emit("hidden", quiet=True)
    assert stream.getvalue() == ""


def test_breadcrumb_routes_to_quiet_log_when_active(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    log_file = tmp_path / "quiet.log"
    monkeypatch.setenv(config.ENV_LARCH_QUIET_ACTIVE, "1")
    monkeypatch.setenv(config.ENV_LARCH_QUIET_PID, "12345")
    monkeypatch.setenv(config.ENV_LARCH_QUIET_LOG_FILE, str(log_file))
    monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
    stream = StringIO()
    writer = logging_util.BreadcrumbWriter(stream=stream)
    writer.emit("ship.py: checks", quiet=None)
    assert stream.getvalue() == ""
    assert "ship.py: checks" in log_file.read_text(encoding="utf-8")


def test_breadcrumb_ignores_unbound_quiet_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(config.ENV_LARCH_QUIET_ACTIVE, "1")
    monkeypatch.delenv(config.ENV_LARCH_QUIET_PID, raising=False)
    monkeypatch.delenv(config.ENV_LARCH_QUIET_LOG_FILE, raising=False)
    stream = StringIO()
    writer = logging_util.BreadcrumbWriter(stream=stream)
    writer.emit("visible", quiet=None)
    assert stream.getvalue() == "visible\n"


def test_emit_writes_newline_terminated_line(capsys: pytest.CaptureFixture[str]) -> None:
    logging_util.reset_quiet_state()
    logging_util.emit("RESULT=42")
    captured = capsys.readouterr()
    assert captured.out == "RESULT=42\n"


def test_emit_already_newline_terminated(capsys: pytest.CaptureFixture[str]) -> None:
    logging_util.reset_quiet_state()
    logging_util.emit("RESULT=42\n")
    captured = capsys.readouterr()
    assert captured.out == "RESULT=42\n"


def test_emit_kv_writes_key_equals_value(capsys: pytest.CaptureFixture[str]) -> None:
    logging_util.reset_quiet_state()
    logging_util.emit_kv(key="STATUS", value="ok")
    captured = capsys.readouterr()
    assert captured.out == "STATUS=ok\n"


def test_emit_kv_uses_inherited_quiet_fd3(monkeypatch: pytest.MonkeyPatch) -> None:
    logging_util.reset_quiet_state()
    read_fd, write_fd = os.pipe()
    backup_fd: int | None = None
    with contextlib.suppress(OSError):
        backup_fd = os.dup(3)
    try:
        _ = os.dup2(write_fd, 3)
        os.close(write_fd)
        monkeypatch.setenv(config.ENV_LARCH_QUIET_ACTIVE, "1")
        monkeypatch.setenv(config.ENV_LARCH_QUIET_PID, "12345")
        monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
        logging_util.emit_kv(key="STATUS", value="ok")
        assert os.read(read_fd, 1024).decode("utf-8") == "STATUS=ok\n"
    finally:
        if backup_fd is not None:
            _ = os.dup2(backup_fd, 3)
            os.close(backup_fd)
        else:
            with contextlib.suppress(OSError):
                os.close(3)
        os.close(read_fd)
        logging_util.reset_quiet_state()


def test_emit_kv_rejects_newline_in_value() -> None:
    with pytest.raises(ValueError, match="newline"):
        logging_util.emit_kv(key="KEY", value="bad\nvalue")


def test_emit_kv_rejects_carriage_return_in_value() -> None:
    with pytest.raises(ValueError, match="newline"):
        logging_util.emit_kv(key="KEY", value="bad\rvalue")


def test_quiet_init_prefers_design_tmpdir_over_implement_tmpdir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    logging_util.reset_quiet_state()
    design_tmpdir = tmp_path / "design"
    implement_tmpdir = tmp_path / "implement"
    design_tmpdir.mkdir()
    implement_tmpdir.mkdir()
    captured: list[Path] = []

    def fake_open(path: str | bytes | os.PathLike[str] | os.PathLike[bytes], flags: int, mode: int = 0o777) -> int:
        _ = flags
        _ = mode
        captured.append(Path(os.fsdecode(path)))
        return 12345

    def fake_dup2(src: int, dst: int) -> int:
        _ = src
        return dst

    def fake_close(fd: int) -> None:
        _ = fd

    monkeypatch.setenv(config.ENV_DESIGN_TMPDIR, str(design_tmpdir))
    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(implement_tmpdir))
    _ = os.environ.pop(config.ENV_LARCH_QUIET_LOG_FILE, None)
    _ = os.environ.pop(config.ENV_LARCH_QUIET_ACTIVE, None)
    _ = os.environ.pop(config.ENV_LARCH_QUIET_PID, None)
    monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
    monkeypatch.setattr(os, "open", fake_open)
    monkeypatch.setattr(os, "dup2", fake_dup2)
    monkeypatch.setattr(os, "close", fake_close)
    try:
        logging_util.quiet_init(argv0="design-log-ship.py")
        assert captured
        assert captured[0].parent == design_tmpdir
    finally:
        _ = os.environ.pop(config.ENV_LARCH_QUIET_LOG_FILE, None)
        _ = os.environ.pop(config.ENV_LARCH_QUIET_ACTIVE, None)
        _ = os.environ.pop(config.ENV_LARCH_QUIET_PID, None)
        logging_util.reset_quiet_state()
