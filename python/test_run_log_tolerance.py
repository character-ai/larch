"""Tests for run_log_tolerance.py."""

from __future__ import annotations

from pathlib import Path

import run_log_tolerance


def test_manifest_pr_evidence_matches_rejects_non_digit() -> None:
    manifest = {"pr_number": "N/A"}
    assert run_log_tolerance.manifest_pr_evidence_matches(manifest, 7) is False


def test_stale_bail_tolerance_requires_matching_digit_pr(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _ = (run_dir / "final-summary.md").write_text("## /implement run RUN1 — bailed\n", encoding="utf-8")
    assert run_log_tolerance.stale_bail_heading_with_pr_evidence(run_dir, {"pr_number": "pending"}, 7) is False
    assert run_log_tolerance.stale_bail_heading_with_pr_evidence(run_dir, {"pr_number": 7}, 7) is True


def test_terminal_bail_skip_signal_keeps_stalled_heading_with_pr_evidence(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _ = (run_dir / "final-summary.md").write_text("## /implement run RUN1 — stalled\n", encoding="utf-8")
    manifest = {"pr_number": 7}
    assert run_log_tolerance.terminal_bail_skip_signal(run_dir, manifest, 7) is True
