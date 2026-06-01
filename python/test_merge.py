"""Tests for merge.py."""

from __future__ import annotations

import config
import merge as merge_module


def test_redact_merge_diagnostic_truncates() -> None:
    text = "x" * 1000
    out = merge_module.redact_merge_diagnostic(text)
    assert len(out) <= config.MERGE_DIAGNOSTIC_MAX_LEN


def test_merge_results_table_is_exhaustive() -> None:
    assert len(config.MERGE_RESULTS) == 8
    assert "already_merged" not in config.MERGE_RESULTS
