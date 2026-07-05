"""Tests for shared review phase detail final-report helpers."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest  # noqa: TC002

from larch.review import plan_review
from larch.report import progress_report
from larch.report import review_phase_detail


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


def _write_rejected_oos(path: Path, *, title: str, severity: str = "minor", concern: str = "Needs a follow-up.") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(
        f"### OOS_1: {title}\n"
        "- **Reviewer(s)**: codex-specialist-correctness\n"
        f"- **Severity**: {severity}\n"
        f"- **Concern**: {concern}\n"
        "- **Suggested revisions (informational for voters; coder decides)**:\n"
        "Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected\n",
        encoding="utf-8",
    )


def _write_classification(path: Path, *, finding_id: str = "OOS_1", result: str = "rejected") -> None:
    _ = path.write_text(
        "finding_id\treviewer_slots\tvoting_result\tscope\n"
        f"{finding_id}\tcodex-specialist-correctness\t{result}\toos\n",
        encoding="utf-8",
    )


def test_render_rejected_oos_audit_section_lists_public_candidates(tmp_path: Path) -> None:
    _write_rejected_oos(
        tmp_path / "round-1" / "oos.md",
        title="[OUT_OF_SCOPE] retry gap",
        severity="major",
        concern="`python/example.py:10` misses the retry branch. It predates this diff.",
    )

    section = review_phase_detail.render_rejected_oos_audit_section(tmp_path)

    assert "## Rejected OOS audit" in section
    assert "These OOS observations reached the vote but were not accepted for filing." in section
    assert "- **Round 1 OOS_1** (rejected, major): retry gap." in section
    assert "Concern: `python/example.py:10` misses the retry branch." in section


def test_render_rejected_oos_audit_section_prefers_tsv_without_footer(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    _ = (round_dir / "oos.md").write_text(
        "### OOS_1: [OUT_OF_SCOPE] retry gap\n"
        "- **Reviewer(s)**: codex-specialist-correctness\n"
        "- **Severity**: major\n"
        "- **Concern**: footer drift removed the result line.\n",
        encoding="utf-8",
    )
    _write_classification(round_dir / "findings-classification.tsv", result="rejected")

    section = review_phase_detail.render_rejected_oos_audit_section(tmp_path)

    assert "- **Round 1 OOS_1** (rejected, major): retry gap." in section


def test_render_rejected_oos_audit_section_tsv_accepted_beats_footer(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-1"
    _write_rejected_oos(round_dir / "oos.md", title="[OUT_OF_SCOPE] stale rejected footer")
    _write_classification(round_dir / "findings-classification.tsv", result="accepted")

    section = review_phase_detail.render_rejected_oos_audit_section(tmp_path)

    assert section == ""


def test_render_rejected_oos_audit_section_falls_back_on_malformed_tsv(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    _ = (round_dir / "oos.md").write_text(
        "### OOS_1: [OUT_OF_SCOPE] fallback candidate\n"
        "- **Reviewer(s)**: codex-specialist-correctness\n"
        "- **Severity**: major\n"
        "- **Concern**: footer fallback remains available.\n"
        "Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected\n",
        encoding="utf-8",
    )
    _ = (round_dir / "findings-classification.tsv").write_bytes(b"\xff\xfe\x80")

    section = review_phase_detail.render_rejected_oos_audit_section(tmp_path)

    assert "- **Round 1 OOS_1** (rejected, major): fallback candidate." in section


def test_render_rejected_oos_audit_section_skips_security_candidates(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    _ = (round_dir / "oos.md").write_text(
        "### OOS_1: [OUT_OF_SCOPE] [security] token leak\n"
        "- **Reviewer(s)**: codex-specialist-security\n"
        "- **Severity**: major\n"
        "- **Concern**: private detail.\n"
        "Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected\n\n"
        "### OOS_2: [OUT_OF_SCOPE] public follow-up\n"
        "- **Reviewer(s)**: codex-specialist-correctness\n"
        "- **Severity**: minor\n"
        "- **Concern**: public detail.\n"
        "Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral\n",
        encoding="utf-8",
    )
    _write_classification(round_dir / "findings-classification.tsv", finding_id="OOS_1", result="rejected")

    section = review_phase_detail.render_rejected_oos_audit_section(tmp_path)

    assert "public follow-up" in section
    assert "private detail" not in section
    assert "Round 1 OOS_1" not in section


def test_render_rejected_oos_audit_section_keeps_security_md_titled_public_candidates(tmp_path: Path) -> None:
    # A title that merely starts with "SECURITY.md" (documentation-drift, not a
    # security-sensitive finding) must not be misclassified as security-routed.
    _write_rejected_oos(
        tmp_path / "round-1" / "oos.md",
        title="[OUT_OF_SCOPE] SECURITY.md still documents REDACTED_LOG_FILE-only failure consumption",
        severity="major",
        concern="docs/linting.md moved to DIGEST_FILE-first consumption but SECURITY.md was not updated.",
    )

    section = review_phase_detail.render_rejected_oos_audit_section(tmp_path)

    assert "SECURITY.md still documents REDACTED_LOG_FILE-only failure consumption" in section


def test_render_rejected_oos_audit_section_lists_legacy_finding_block(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    _ = (round_dir / "oos.md").write_text(
        "### FINDING_1: legacy scope drift\n"
        "- **Reviewer(s)**: codex-specialist-correctness\n"
        "- **Severity**: minor\n"
        "- **Concern**: moved into oos.md without an OOS tag.\n"
        "Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected\n",
        encoding="utf-8",
    )

    section = review_phase_detail.render_rejected_oos_audit_section(tmp_path)

    assert "Round 1 FINDING_1" in section
    assert "legacy scope drift" in section


def test_render_rejected_oos_audit_section_caps_candidates(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    blocks: list[str] = []
    for idx in range(review_phase_detail.REJECTED_OOS_AUDIT_LIMIT + 1):
        blocks.append(
            f"### OOS_{idx + 1}: [OUT_OF_SCOPE] item {idx + 1}\n"
            "- **Reviewer(s)**: codex-specialist-correctness\n"
            "- **Severity**: nit\n"
            f"- **Concern**: concern {idx + 1}.\n"
            "Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected\n"
        )
    _ = (round_dir / "oos.md").write_text("\n".join(blocks), encoding="utf-8")

    section = review_phase_detail.render_rejected_oos_audit_section(tmp_path)

    assert f"Round 1 OOS_{review_phase_detail.REJECTED_OOS_AUDIT_LIMIT}" in section
    assert f"Round 1 OOS_{review_phase_detail.REJECTED_OOS_AUDIT_LIMIT + 1}" not in section
    assert "- **Additional audit rows**: 1 omitted by the final-summary cap." in section


def test_render_implement_review_detail_omits_rejected_oos_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = "run-3794"
    run_dir = tmp_path / "larch-logs" / "implement" / run_id
    _write_rejected_oos(run_dir / "round-1" / "oos.md", title="[OUT_OF_SCOPE] closeout gap")

    def fake_render(*_args: object, **_kwargs: object) -> str:
        return "## Review Phase Detail\nreview detail\n"

    monkeypatch.setattr(progress_report, "_render_phase_detail_best_effort", fake_render)

    detail = review_phase_detail.render_implement_review_detail(implement_tmpdir=tmp_path, run_id=run_id)

    assert detail == "## Review Phase Detail\nreview detail\n"
    assert "Rejected OOS audit" not in detail
    assert "closeout gap" not in detail
