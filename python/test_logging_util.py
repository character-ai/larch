"""Tests for logging_util.py."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

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


def test_breadcrumb_suppressed_when_quiet() -> None:
    stream = StringIO()
    writer = logging_util.BreadcrumbWriter(stream=stream)
    writer.emit("hidden", quiet=True)
    assert stream.getvalue() == ""
