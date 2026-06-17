"""Tests for shared review phase detail final-report helpers."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

import review_phase_detail


def test_invoke_renderer_returns_empty_on_nonzero_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rounds_root = tmp_path / "rounds"
    rounds_root.mkdir()

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["renderer"], 1, stdout="## Review Phase Detail\n", stderr="boom")

    monkeypatch.setattr(review_phase_detail.subprocess, "run", fake_run)
    assert review_phase_detail._invoke_renderer(rounds_root, skill="implement") == ""


def test_invoke_renderer_returns_empty_on_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rounds_root = tmp_path / "rounds"
    rounds_root.mkdir()

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(["renderer"], timeout=1)

    monkeypatch.setattr(review_phase_detail.subprocess, "run", fake_run)
    assert review_phase_detail._invoke_renderer(rounds_root, skill="implement") == ""


def test_invoke_renderer_returns_empty_on_whitespace_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rounds_root = tmp_path / "rounds"
    rounds_root.mkdir()

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["renderer"], 0, stdout=" \n\t", stderr="")

    monkeypatch.setattr(review_phase_detail.subprocess, "run", fake_run)
    assert review_phase_detail._invoke_renderer(rounds_root, skill="implement") == ""


def test_invoke_renderer_returns_empty_on_post_redact_truncation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rounds_root = tmp_path / "rounds"
    rounds_root.mkdir()

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["renderer"], 0, stdout="raw detail", stderr="")

    def fake_redact_outbound(_text: str) -> str:
        return "[content truncated for test]"

    monkeypatch.setattr(review_phase_detail.subprocess, "run", fake_run)
    monkeypatch.setattr(review_phase_detail.redact, "redact_outbound", fake_redact_outbound)
    assert review_phase_detail._invoke_renderer(rounds_root, skill="implement") == ""


def test_invoke_renderer_redacts_and_returns_detail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rounds_root = tmp_path / "rounds"
    rounds_root.mkdir()

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["renderer"], 0, stdout="## Review Phase Detail\nsecret\n", stderr="")

    def fake_redact_outbound(text: str) -> str:
        return text.replace("secret", "<redacted>")

    monkeypatch.setattr(review_phase_detail.subprocess, "run", fake_run)
    monkeypatch.setattr(review_phase_detail.redact, "redact_outbound", fake_redact_outbound)
    assert review_phase_detail._invoke_renderer(rounds_root, skill="implement") == "## Review Phase Detail\n<redacted>\n"


def test_append_review_phase_detail_normalizes_spacing() -> None:
    assert review_phase_detail.append_review_phase_detail("body\n", "detail\n") == "body\n\ndetail\n"
    assert review_phase_detail.append_review_phase_detail("body\n", "") == "body\n"


@pytest.mark.skipif(shutil.which("jq") is None, reason="render-review-phase-detail.sh requires jq")
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

    detail = review_phase_detail.render_implement_review_detail(tmp_path, run_id)

    assert "## Review Phase Detail" in detail
    assert "No review rounds completed." in detail
    assert "| 1 | 2 | 2 | 0 | 0 |" not in detail
