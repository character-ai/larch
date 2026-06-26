"""Tests for shared review phase detail final-report helpers."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest  # noqa: TC002

import plan_review
import progress_report
import review_phase_detail


def test_invoke_renderer_returns_empty_on_wrapper_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rounds_root = tmp_path / "rounds"
    rounds_root.mkdir()

    def fake_render(*_args: object, **_kwargs: object) -> str:
        return ""

    monkeypatch.setattr(progress_report, "_render_phase_detail_best_effort", fake_render)
    assert review_phase_detail._invoke_renderer(rounds_root, skill="implement") == ""


def test_invoke_renderer_returns_empty_on_wrapper_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rounds_root = tmp_path / "rounds"
    rounds_root.mkdir()

    def fake_render(*_args: object, **_kwargs: object) -> str:
        raise TimeoutError("boom")

    monkeypatch.setattr(progress_report, "_render_phase_detail_best_effort", fake_render)
    assert review_phase_detail._invoke_renderer(rounds_root, skill="implement") == ""


def test_invoke_renderer_returns_empty_on_whitespace_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rounds_root = tmp_path / "rounds"
    rounds_root.mkdir()

    def fake_render(*_args: object, **_kwargs: object) -> str:
        return " \n\t"

    monkeypatch.setattr(progress_report, "_render_phase_detail_best_effort", fake_render)
    assert review_phase_detail._invoke_renderer(rounds_root, skill="implement") == ""


def test_invoke_renderer_returns_empty_on_post_redact_truncation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rounds_root = tmp_path / "rounds"
    rounds_root.mkdir()

    def fake_render(*_args: object, **_kwargs: object) -> str:
        return "raw detail"

    def fake_redact_outbound(_text: str) -> str:
        return "[content truncated for test]"

    monkeypatch.setattr(progress_report, "_render_phase_detail_best_effort", fake_render)
    monkeypatch.setattr(review_phase_detail.redact, "redact_outbound", fake_redact_outbound)
    assert review_phase_detail._invoke_renderer(rounds_root, skill="implement") == ""


def test_invoke_renderer_redacts_and_returns_detail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rounds_root = tmp_path / "rounds"
    rounds_root.mkdir()

    def fake_render(*_args: object, **_kwargs: object) -> str:
        return "## Review Phase Detail\nsecret\n"

    def fake_redact_outbound(text: str) -> str:
        return text.replace("secret", "<redacted>")

    monkeypatch.setattr(progress_report, "_render_phase_detail_best_effort", fake_render)
    monkeypatch.setattr(review_phase_detail.redact, "redact_outbound", fake_redact_outbound)
    assert review_phase_detail._invoke_renderer(rounds_root, skill="implement") == "## Review Phase Detail\n<redacted>\n"


def test_append_review_phase_detail_normalizes_spacing() -> None:
    assert review_phase_detail.append_review_phase_detail(body="body\n", detail="detail\n") == "body\n\ndetail\n"
    assert review_phase_detail.append_review_phase_detail(body="body\n", detail="") == "body\n"


def test_render_design_review_detail_populates_time_and_cost(tmp_path: Path) -> None:
    design_tmpdir = tmp_path
    round_dir = design_tmpdir / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    _ = (round_dir / "round-meta.json").write_text(
        '{"tally":{"ACCEPTED_COUNT":"1","REJECTED_COUNT":"0","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"0",'
        '"OOS_ACCEPTED_COUNT":"0","OOS_REJECTED_COUNT":"0"},"summary":{"panel":{"total_slot_count":3}}}\n',
        encoding="utf-8",
    )

    start_s = 1_700_000_000
    end_s = start_s + 125
    # Fix 2 path: the design round-timing recorder writes the canonical v1 row the
    # renderer reads (issue #5444).
    _ = plan_review.record_plan_review_round_timing(
        ["--design-tmpdir", str(design_tmpdir), "--round", "1", "--start-s", str(start_s), "--end-s", str(end_s)]
    )

    # A vendor token row inside the round window gives the Cost column a value.
    ts = datetime.fromtimestamp(start_s + 10, tz=UTC).isoformat()
    _ = (design_tmpdir / "larch-tokens-1.jsonl").write_text(
        json.dumps({"type": "vendor", "vendor": "codex", "ts": ts, "input": 200000, "output": 50000, "cache_read": 0}) + "\n",
        encoding="utf-8",
    )

    detail = review_phase_detail.render_design_review_detail(design_tmpdir)

    assert "## Review Phase Detail" in detail
    # 125s window renders a non-"—" Time cell, and a present token ledger + window
    # renders a non-"—" Cost cell.
    assert "2m 05s" in detail
    assert "$" in detail


def test_render_implement_review_detail_prefers_run_log_root_without_completed_rounds(tmp_path: Path) -> None:
    run_id = "run-3794"
    run_dir = tmp_path / "larch-logs" / "implement" / run_id
    run_dir.mkdir(parents=True)
    stale_round = tmp_path / "round-1"
    stale_round.mkdir()
    _ = (stale_round / "round-meta.json").write_text(
        '{"tally":{"ACCEPTED_COUNT":"2","REJECTED_COUNT":"0","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"0","OOS_REJECTED_COUNT":"0"},"summary":{"panel":{"total_slot_count":2}}}\n',
        encoding="utf-8",
    )

    detail = review_phase_detail.render_implement_review_detail(implement_tmpdir=tmp_path, run_id=run_id)

    assert "## Review Phase Detail" in detail
    assert "No review rounds completed." in detail
    assert "| 1 | 2 | 2 | 0 | 0 |" not in detail
