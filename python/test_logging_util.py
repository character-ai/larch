"""Tests for logging_util.py."""

from __future__ import annotations

import json
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
    logging_util.emit_kv("STATUS", "ok")
    captured = capsys.readouterr()
    assert captured.out == "STATUS=ok\n"


def test_emit_kv_rejects_newline_in_value() -> None:
    with pytest.raises(ValueError, match="newline"):
        logging_util.emit_kv("KEY", "bad\nvalue")


def test_emit_kv_rejects_carriage_return_in_value() -> None:
    with pytest.raises(ValueError, match="newline"):
        logging_util.emit_kv("KEY", "bad\rvalue")
