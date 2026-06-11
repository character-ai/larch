"""Tests for timing.py."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

import timing


def test_timing_vendor_task_accepts_claude_and_basename(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    timing.TimingLedger(ledger).record_vendor_task(
        vendor="claude",
        task_kind="claude-review",
        start_s=10,
        end_s=15,
        output="/tmp/secret/out.txt",
    )
    text = ledger.read_text(encoding="utf-8")
    assert "\tclaude\tclaude-review\t" in text
    assert "\tout.txt\t" in text
    assert "/tmp/secret" not in text


def test_timing_report_json_and_design_workflow_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _ = ledger.write_text(
        "v1\tmark\t10\tdesign\tdesign Step 0\t-\t-\t-\t-\t-\t-\t-\t-\n"
        "v1\tmark\t20\tdesign\tdesign Step 1\t-\t-\t-\t-\t-\t-\t-\t-\n"
        "v1\tvendor\t18\tdesign\t-\tcodex\tcodex-review\t11\t18\t7\tout.log\t0\tcomplete\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "run-params.json").write_text('{"workflow_path":"HARD"}', encoding="utf-8")
    monkeypatch.setenv("LARCH_TIMING_SKILL", "design")
    monkeypatch.setenv("LARCH_TEST_TIMING_NOW", "30")
    data = timing.TimingReport(ledger).render_json()
    assert data["workflow_path"] == "HARD"
    assert data["total_seconds"] == 10
    assert data["vendor_task_averages"]


def test_timing_rejects_symlink_ledger(tmp_path: Path) -> None:
    target = tmp_path / "target.tsv"
    _ = target.write_text("", encoding="utf-8")
    link = tmp_path / "link.tsv"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        timing.TimingLedger(link).mark("bad")


def test_timing_rejects_non_regular_ledger(tmp_path: Path) -> None:
    fifo = tmp_path / "fifo"
    if hasattr(stat, "S_IFIFO"):
        os.mkfifo(fifo)
        with pytest.raises(ValueError, match="not a regular file"):
            timing.TimingLedger(fifo).mark("bad")
