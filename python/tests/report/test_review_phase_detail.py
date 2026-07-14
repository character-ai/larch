"""Tests for shared review phase detail final-report helpers."""

# Progress-report coverage exercises private helpers, pytest monkeypatch fakes,
# and fixture writes whose byte counts are intentionally ignored.
# pyright: reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownLambdaType=false, reportUnusedCallResult=false, reportMissingParameterType=false, reportUnknownParameterType=false

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest  # noqa: TC002

from larch.core import config
from larch.review import plan_review
from larch.report import progress_report
from larch.report import review_phase_detail
from tests.support.review_wire import panel_manifest_ndjson, panel_manifest_row


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


def _write_slot_manifest(manifest: Path, outputs: list[Path]) -> None:
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        panel_manifest_ndjson([panel_manifest_row(f"slot-{idx}", "codex", output) for idx, output in enumerate(outputs, start=1)]),
        encoding="utf-8",
    )


def _write_vendor_timing(
    ledger: Path,
    output: str,
    start_s: int,
    end_s: int,
    *,
    vendor: str = "codex",
    kind: str = "codex-review",
    status: str = "complete",
    skill: str = "implement",
) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0, end_s - start_s)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(
            f"v1\tvendor\t{end_s}\t{skill}\t-\t{vendor}\t{kind}\t{start_s}\t{end_s}\t"
            f"{duration}\t{output}\t0\t{status}\n"
        )


def _write_round_timing(
    ledger: Path,
    *,
    skill: str,
    round_num: int,
    start_s: int,
    end_s: int,
    attempt: int | None = None,
) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0, end_s - start_s)
    # Issue #5504: trailing column holds the 1-based attempt index; None reproduces legacy
    # rows (written "-") to keep backward-compat coverage honest.
    attempt_col = "-" if attempt is None else str(attempt)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(
            f"v1\tround\t{start_s}\t{skill}\t-\t{round_num}\t{start_s}\t{end_s}\t"
            f"{duration}\t0\t0\t0\t{attempt_col}\n"
        )


def _write_over_cap_plain_codex_review_rows(ledger: Path) -> tuple[int, str]:
    over_cap = progress_report.PROGRESS_GANTT_ROW_CAP + 2
    for index in range(over_cap):
        _write_vendor_timing(
            ledger,
            f"codex-specialist-row-{index}-output.txt",
            100 + index,
            150,
        )
    return over_cap, f"codex/row-{over_cap - 1}"


def _write_round_meta(round_dir: Path, accepted: int = 2, rejected: int = 1, reviewers: int = 3, collector: str = "") -> None:
    round_dir.mkdir(parents=True, exist_ok=True)
    (round_dir / "round-meta.json").write_text(
        json.dumps({
            "tally": {
                "ACCEPTED_COUNT": str(accepted),
                "REJECTED_COUNT": str(rejected),
                "EXONERATED_COUNT": "0",
                "NEUTRAL_COUNT": "1",
                "OOS_PROPOSED_COUNT": "1",
                "OOS_ACCEPTED_COUNT": "1",
                "OOS_REJECTED_COUNT": "1",
            },
            "summary": {"panel": {"total_slot_count": reviewers}},
            "collector": collector,
        }) + "\n",
        encoding="utf-8",
    )


def test_round_vendor_cost_prices_claude_sub_by_model(tmp_path: Path) -> None:
    ledger = tmp_path / "larch-tokens.jsonl"
    rows = [
        {"type": "vendor", "vendor": "claude_sub", "input": 1_000_000, "model": "claude-sonnet-4-6", "ts": "2026-06-25T00:00:05Z"},
        {"type": "vendor", "vendor": "claude_sub", "input": 1_000_000, "model": "claude-haiku-4-5", "ts": "2026-06-25T00:00:06Z"},
        {"type": "vendor", "vendor": "claude_sub", "input": 1_000_000, "model": "claude-fable-5", "ts": "2026-06-25T00:00:07Z"},
    ]
    ledger.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    assert progress_report._round_vendor_cost(token_ledger=ledger, start_s=1782345600, end_s=1782345610) == "$14.00"


def test_round_vendor_cost_uses_claude_sub_raw_fallback(tmp_path: Path) -> None:
    ledger = tmp_path / "larch-tokens.jsonl"
    rows = [
        {"type": "vendor", "vendor": "claude_sub", "input": 1_000_000, "raw": "claude_review", "ts": "2026-06-25T00:00:05Z"},
        {"type": "vendor", "vendor": "claude_sub", "input": 1_000_000, "raw": "claude_ci_fix", "ts": "2026-06-25T00:00:06Z"},
    ]
    ledger.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    assert progress_report._round_vendor_cost(token_ledger=ledger, start_s=1782345600, end_s=1782345610) == "$6.00"


def test_round_vendor_cost_prices_cursor_grok_by_model(tmp_path: Path) -> None:
    """Per-round cost prices cursor grok at grok rates, not composer (issue #7257)."""
    ledger = tmp_path / "larch-tokens.jsonl"
    rows = [
        {"type": "vendor", "vendor": "cursor", "input": 1_000_000, "model": config.CURSOR_GROK_4_5_HIGH_MODEL, "ts": "2026-06-25T00:00:05Z"},
        {"type": "vendor", "vendor": "cursor", "input": 1_000_000, "model": config.CURSOR_DEFAULT_MODEL, "ts": "2026-06-25T00:00:06Z"},
    ]
    ledger.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    # Grok input prices at $2.00/M (not composer $0.75/M): grok $2.00 + composer $0.75 = $2.75.
    assert progress_report._round_vendor_cost(token_ledger=ledger, start_s=1782345600, end_s=1782345610) == "$2.75"


def test_fallback_label_remap_annotates_executing_tool(tmp_path: Path) -> None:
    """_fallback_label_remap maps a slot's human label to a ``(via <Tool>)`` label
    when collector-results.env shows the slot was executed by a tool other than its
    nominal vendor; same-vendor slots produce no entry (issue #5838).
    """
    design = tmp_path
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    arch = round_dir / "cursor-plan-arch-output.txt"
    pragmatic = round_dir / "codex-plan-pragmatic-output.txt"
    (round_dir / "panel-manifest.ndjson").write_text(
        json.dumps({"slot": "cursor-plan-arch", "tool": "cursor", "output": str(arch)}) + "\n"
        + json.dumps({"slot": "codex-plan-pragmatic", "tool": "codex", "output": str(pragmatic)}) + "\n",
        encoding="utf-8",
    )
    (design / "collector-results.env").write_text(
        f"REVIEWER_FILE={arch}\nTOOL=codex\nSTATUS=OK\n\n"
        f"REVIEWER_FILE={pragmatic}\nTOOL=codex\nSTATUS=OK\n\n",
        encoding="utf-8",
    )

    remap = progress_report._fallback_label_remap([round_dir])

    assert remap == {"Cursor-Arch": "Cursor-Arch (via Codex)"}


def test_fallback_label_remap_annotates_code_review_parent_collector(tmp_path: Path) -> None:
    root = tmp_path / "review"
    round_dir = root / "round-1"
    round_dir.mkdir(parents=True)
    output = "cursor-specialist-arch-output.txt"
    (round_dir / "panel-manifest.ndjson").write_text(
        json.dumps({"slot": "arch", "tool": "cursor", "output": output}) + "\n",
        encoding="utf-8",
    )
    (root / "collector-results.env").write_text(
        f"REVIEWER_FILE={output}\nTOOL=codex\nSTATUS=OK\n\n",
        encoding="utf-8",
    )

    remap = progress_report._fallback_label_remap([round_dir])

    assert not (round_dir / "collector-results.env").exists()
    assert remap == {"cursor/arch": "cursor/arch (via Codex)"}


def test_fallback_label_remap_prefers_round_local_collector(tmp_path: Path) -> None:
    root = tmp_path / "review"
    round_dir = root / "round-1"
    round_dir.mkdir(parents=True)
    output = "cursor-specialist-arch-output.txt"
    (round_dir / "panel-manifest.ndjson").write_text(
        json.dumps({"slot": "arch", "tool": "cursor", "output": output}) + "\n",
        encoding="utf-8",
    )
    (round_dir / "collector-results.env").write_text(
        f"REVIEWER_FILE={output}\nTOOL=codex\nSTATUS=OK\n\n",
        encoding="utf-8",
    )
    (root / "collector-results.env").write_text(
        f"REVIEWER_FILE={output}\nTOOL=cursor\nSTATUS=OK\n\n",
        encoding="utf-8",
    )

    remap = progress_report._fallback_label_remap([round_dir])

    assert remap == {"cursor/arch": "cursor/arch (via Codex)"}


def test_fallback_label_remap_empty_without_collector(tmp_path: Path) -> None:
    """No collector-results.env -> no remap (issue #5838)."""
    round_dir = tmp_path / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "panel-manifest.ndjson").write_text(
        json.dumps({"slot": "cursor-plan-arch", "tool": "cursor", "output": str(round_dir / "cursor-plan-arch-output.txt")}) + "\n",
        encoding="utf-8",
    )
    assert not progress_report._fallback_label_remap([round_dir])


def test_progress_label_fallbacks_and_manifest_precedence(tmp_path: Path) -> None:
    assert progress_report._is_chart_vendor_fallback_output("codex-validity-vote-output-phase2.txt") is True
    assert progress_report._is_chart_vendor_fallback_output("codex-validity-vote-output-phase3.txt") is True
    assert progress_report._is_chart_vendor_fallback_output("codex-validity-vote-output-retry.txt") is False
    assert progress_report._is_chart_vendor_fallback_output("cursor-plan-requirements-output-ns-retry.txt") is False

    assert progress_report._derive_progress_label(output="aggregator-output.txt") == "aggregator"
    assert progress_report._derive_progress_label(output="scout-plan-manifest.json.raw") == "scout"
    assert (
        progress_report._derive_progress_label(
            output="codex-output.txt",
            vendor="codex",
            kind="codex-plan-autofix",
        )
        == "codex/apply"
    )
    assert (
        progress_report._derive_progress_label(
            output="cursor-output.txt",
            vendor="cursor",
            kind="cursor-plan-autofix",
        )
        == "cursor/apply"
    )
    assert progress_report._derive_progress_label(output="coder-codex.log", vendor="codex", kind="codex-review-fix") == "codex/apply"
    assert progress_report._derive_progress_label(output="coder-cursor.log", vendor="cursor", kind="cursor-review-fix") == "cursor/apply"
    # Issue #7166: the synthetic voter pre-dispatch row keeps its label from the task kind
    # regardless of the neutral claude vendor stamped on the row.
    assert progress_report._derive_progress_label(output="voter-dispatch-prep-round-1.out", vendor="claude", kind="voter-dispatch-prep") == "voter-dispatch-prep"
    # Issue #7179: the synthetic reviewer-collect row likewise labels from the task kind.
    assert progress_report._derive_progress_label(output="reviewer-collect-round-1.out", vendor="claude", kind="reviewer-collect") == "reviewer-collect"

    output = tmp_path / "codex-output.txt"
    manifest = tmp_path / "panel-manifest.ndjson"
    manifest.write_text(f'{{"slot":"mapped","tool":"tool","output":"{output}"}}\n', encoding="utf-8")
    label_map = progress_report._progress_label_map_from_manifests([manifest])
    assert progress_report._derive_progress_label(output=str(output), vendor="codex", kind="codex-plan-autofix", label_map=label_map) == "codex/apply"

    fallback_map = {
        "codex-validity-vote-output.txt": "codex/validity-vote",
        "codex-validity-vote-output-phase2.txt": "raw/exact",
    }
    assert (
        progress_report._derive_progress_label(
            output="codex-validity-vote-output-phase2.txt",
            vendor="cursor",
            kind="cursor-phase2-voter-1",
            label_map=fallback_map,
        )
        == "raw/exact"
    )
    assert (
        progress_report._derive_progress_label(
            output="codex-validity-vote-output-phase3.txt",
            vendor="codex",
            kind="codex-phase3-voter-1",
            label_map=fallback_map,
        )
        == "codex/validity-vote (via fallback)"
    )
    assert (
        progress_report._derive_progress_label(
            output="cursor-specialist-validity-vote-output-phase2.txt",
            vendor="cursor",
            kind="cursor-phase2-voter-1",
        )
        == "cursor/validity-vote (via fallback)"
    )
    assert (
        progress_report._derive_progress_label(
            output="codex-validity-vote-output-phase2.txt",
            vendor="cursor",
            kind="cursor-phase2-voter-1",
        )
        == "cursor/validity-vote (via fallback)"
    )
    assert (
        progress_report._derive_progress_label(
            output="cursor-plan-requirements-output-ns-retry.txt",
            vendor="cursor",
            kind="cursor-plan-requirements",
        )
        == "cursor/plan-requirements"
    )


def test_progress_vendor_rows_use_apply_task_kind_priority(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _write_vendor_timing(
        ledger,
        "codex-output.txt",
        110,
        140,
        vendor="codex",
        kind="codex-plan-autofix",
    )
    _write_vendor_timing(
        ledger,
        "coder-cursor.log",
        141,
        170,
        vendor="cursor",
        kind="cursor-review-fix",
    )
    _write_vendor_timing(
        ledger,
        "coder-codex.log",
        171,
        190,
        vendor="codex",
        kind="codex-review-fix",
    )

    rows = progress_report._progress_vendor_rows(timing_ledger=ledger, window_start_s=100, window_end_s=200, label_map={})

    assert [row.label for row in rows] == ["codex/apply", "cursor/apply", "codex/apply"]


def test_progress_vendor_rows_skip_ci_rows_when_requested(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _write_vendor_timing(ledger, "codex-specialist-correctness-output.txt", 110, 140)
    _write_vendor_timing(ledger, "reviewer-output.txt", 111, 141, kind="codex-ci")
    _write_vendor_timing(ledger, "reviewer-output.txt", 112, 142, kind="cursor-ci-fix")
    _write_vendor_timing(ledger, "reviewer-output.txt", 113, 143, kind="vendor-ci-test")
    _write_vendor_timing(ledger, "ci.out", 114, 144)
    _write_vendor_timing(ledger, "codex-ci.out", 115, 145)
    _write_vendor_timing(ledger, "ci-fix-codex.out", 116, 146)
    _write_vendor_timing(ledger, "claude.out", 117, 147)
    _write_vendor_timing(ledger, str(tmp_path / "nested" / "cursor-ci.out"), 118, 148)

    rows = progress_report._progress_vendor_rows(timing_ledger=ledger, window_start_s=100, window_end_s=200, label_map={}, skip_ci=True)

    assert len(rows) == 1
    assert rows[0].label == "codex/correctness"


def test_progress_vendor_rows_include_distinct_failed_primary_and_phase2_fallback(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _write_vendor_timing(
        ledger,
        "codex-validity-vote-output.txt",
        100,
        110,
        vendor="codex",
        kind="codex-validity-vote",
        status="failed",
    )
    _write_vendor_timing(
        ledger,
        "codex-validity-vote-output-phase2.txt",
        111,
        200,
        vendor="cursor",
        kind="cursor-phase2-voter-1",
        status="complete",
    )

    rows = progress_report._progress_vendor_rows(
        timing_ledger=ledger,
        window_start_s=90,
        window_end_s=220,
        label_map={"codex-validity-vote-output.txt": "codex/validity-vote"},
        require_complete_status=False,
    )

    assert [row.label for row in rows] == [
        "codex/validity-vote",
        "cursor/validity-vote (via fallback)",
    ]


def test_render_phase_detail_no_rounds(tmp_path: Path) -> None:
    root = tmp_path / "rounds"
    root.mkdir()
    assert progress_report.render_phase_detail(rounds_root=root, skill="implement") == "## Review Phase Detail\n\nNo review rounds completed.\n"


def test_render_phase_detail_table_top_failures_and_gantt(tmp_path: Path) -> None:
    root = tmp_path / "rounds"
    r1 = root / "round-1"
    collector = "TOOL=codex\nSTATUS=FAILED\nREVIEWER_FILE=codex-specialist-arch-output.txt\n"
    _write_round_meta(r1, collector=collector)
    _write_slot_manifest(r1 / "panel-manifest.ndjson", [r1 / "codex-specialist-arch-output.txt"])
    findings = tmp_path / "review-findings-full.jsonl"
    findings.write_text(
        '{"outcome":"accepted","round_num":1,"reviewer_slots":["codex-specialist-arch-output.txt"]}\n',
        encoding="utf-8",
    )
    timing = tmp_path / "timing-ledger.tsv"
    _write_round_timing(timing, skill="implement", round_num=1, start_s=100, end_s=200)
    _write_vendor_timing(timing, "codex-specialist-arch-output.txt", 110, 190)
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement", timing_ledger=timing, findings_file=findings)
    assert "| 1 | 4 | 2 | 1 | 1 | 1m 40s | N/A | 3 |" in rendered
    assert "| **Total (round-sum)** | **4** | **2** | **1** | **1** | **1m 40s** | **N/A** | **3** |" in rendered
    assert "1. codex/slot-1: 1" in rendered
    assert "**Reviewer slot failures**: 1" in rendered
    assert "- codex/slot-1: 1" in rendered
    assert "### Round 1 reviewer timing" in rendered
    # Issue #4882: round-meta without a canonical block emits no decomposition footnote (backward compat).
    assert "Finding decomposition (canonical, scope-aware)" not in rendered


def test_render_phase_detail_splits_oos_proposed_and_fileable_from_classification(tmp_path: Path) -> None:
    root = tmp_path / "review"
    r1 = root / "round-1"
    r1.mkdir(parents=True)
    (r1 / "round-meta.json").write_text(
        json.dumps({
            "tally": {
                "ACCEPTED_COUNT": "0",
                "REJECTED_COUNT": "0",
                "EXONERATED_COUNT": "0",
                "NEUTRAL_COUNT": "0",
                "OOS_ACCEPTED_COUNT": "1",
                "OOS_REJECTED_COUNT": "0",
            },
            "summary": {"panel": {"total_slot_count": 1}},
        }) + "\n",
        encoding="utf-8",
    )
    header = progress_report.voting.code_review_classification_header().split("\t")
    cols = dict.fromkeys(header, "")
    cols.update({
        "finding_id": "OOS_1",
        "voting_result": "accepted",
        "v1_vote": "YES",
        "v1_severity": "minor",
        "scope": "oos",
    })
    (r1 / "findings-classification.tsv").write_text(
        "\t".join(header) + "\n" + "\t".join(cols[name] for name in header) + "\n",
        encoding="utf-8",
    )

    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement")

    assert "| Round | Suggestions | Accepted | OOS proposed | OOS fileable |" in rendered
    assert "| 1 | 0 | 0 | 1 | 0 |" in rendered


def test_render_phase_detail_prefers_review_tally_env_for_oos_fileable(tmp_path: Path) -> None:
    root = tmp_path / "review"
    r1 = root / "round-1"
    r1.mkdir(parents=True)
    (r1 / "round-meta.json").write_text(
        json.dumps({
            "tally": {
                "ACCEPTED_COUNT": "0",
                "REJECTED_COUNT": "0",
                "EXONERATED_COUNT": "0",
                "NEUTRAL_COUNT": "0",
                "OOS_PROPOSED_COUNT": "3",
                "OOS_ACCEPTED_COUNT": "9",
                "OOS_REJECTED_COUNT": "1",
            },
            "summary": {"panel": {"total_slot_count": 1}},
        }) + "\n",
        encoding="utf-8",
    )
    (r1 / "review-tally.env").write_text("OOS_ACCEPTED_COUNT=1\n", encoding="utf-8")

    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement")

    assert "| 1 | 0 | 0 | 3 | 1 |" in rendered


def test_write_implement_round_meta_prefers_review_tally_env_for_oos_fileable(tmp_path: Path) -> None:
    round_dir = tmp_path / "review" / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "review-tally.env").write_text(
        "ACCEPTED_COUNT=0\nREJECTED_COUNT=0\nNEUTRAL_COUNT=0\nOOS_ACCEPTED_COUNT=2\n",
        encoding="utf-8",
    )
    header = progress_report.voting.findings_classification_header().split("\t")
    cols = dict.fromkeys(header, "")
    cols.update({
        "finding_id": "OOS_1",
        "voting_result": "accepted",
        "v1_vote": "YES",
        "v1_severity": "minor",
        "scope": "oos",
    })
    (round_dir / "findings-classification.tsv").write_text(
        "\t".join(header) + "\n" + "\t".join(cols[name] for name in header) + "\n",
        encoding="utf-8",
    )

    assert progress_report.write_implement_round_meta(round_dir) == 0
    meta = json.loads((round_dir / "round-meta.json").read_text(encoding="utf-8"))

    assert meta["tally"]["OOS_PROPOSED_COUNT"] == "1"
    assert meta["tally"]["OOS_ACCEPTED_COUNT"] == "2"
    assert meta["tally_canonical"]["OOS_PROPOSED_COUNT"] == "1"
    assert meta["tally_canonical"]["OOS_ACCEPTED_COUNT"] == "2"


def test_render_phase_detail_merges_collector_and_dynamic_dropped_failures(tmp_path: Path) -> None:
    root = tmp_path / "rounds"
    r1 = root / "round-1"
    _write_round_meta(r1)
    (r1 / "panel-manifest.ndjson").write_text(
        json.dumps(
            {
                "slot": "arch",
                "tool": "codex",
                "output": str(r1 / "codex-specialist-arch-output.txt"),
            }
        )
        + "\n"
        + json.dumps(
            {
                "slot": "dyn-dyn-lint-escalation",
                "tool": "cursor",
                "output": str(r1 / "dyn-dyn-lint-escalation-output.txt"),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "collector-results.env").write_text(
        f"REVIEWER_FILE={r1 / 'codex-specialist-arch-output.txt'}\n"
        "TOOL=codex\n"
        "STATUS=ERROR\n\n",
        encoding="utf-8",
    )
    (r1 / "panel-manifest.ndjson.output-files.dropped-slots").write_text(
        "dyn-dyn-lint-escalation\tcursor\tstraggler-dropped\tcut\n",
        encoding="utf-8",
    )

    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement")

    assert "**Reviewer slot failures**: 2" in rendered
    assert "- codex/arch: 1" in rendered
    assert "- cursor/dyn-dyn-lint-escalation: 1" in rendered


def test_render_phase_detail_treats_cap_hit_as_success(tmp_path: Path) -> None:
    root = tmp_path / "rounds"
    r1 = root / "round-1"
    _write_round_meta(r1)
    (r1 / "collector-results.env").write_text(
        "REVIEWER_FILE=codex-specialist-arch-output.txt\n"
        "TOOL=codex\n"
        "STATUS=cap_hit\n\n",
        encoding="utf-8",
    )

    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement")

    assert "**Reviewer slot failures**: 0" in rendered


def test_render_phase_detail_suppresses_dropped_row_when_collector_ok(tmp_path: Path) -> None:
    root = tmp_path / "rounds"
    r1 = root / "round-1"
    _write_round_meta(r1)
    output = r1 / "dyn-dyn-lint-escalation-output.txt"
    (r1 / "panel-manifest.ndjson").write_text(
        json.dumps(
            {
                "slot": "dyn-dyn-lint-escalation",
                "tool": "cursor",
                "output": str(output),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (r1 / "collector-results.env").write_text(
        f"REVIEWER_FILE={output}\n"
        "TOOL=cursor\n"
        "STATUS=OK\n\n",
        encoding="utf-8",
    )
    (r1 / "panel-manifest.ndjson.output-files.dropped-slots").write_text(
        "dyn-dyn-lint-escalation\tcursor\tstraggler-dropped\tcut\n",
        encoding="utf-8",
    )

    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement")

    assert "**Reviewer slot failures**: 0" in rendered


def test_render_phase_detail_ignores_stale_grandparent_collector_for_implement(tmp_path: Path) -> None:
    root = tmp_path / "impl"
    r1 = root / "round-1"
    _write_round_meta(r1)
    (tmp_path / "collector-results.env").write_text(
        "REVIEWER_FILE=stale-output.txt\n"
        "TOOL=codex\n"
        "STATUS=ERROR\n\n",
        encoding="utf-8",
    )
    (r1 / "collector-results.env").write_text(
        "REVIEWER_FILE=good-output.txt\n"
        "TOOL=codex\n"
        "STATUS=OK\n\n",
        encoding="utf-8",
    )

    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement")

    assert "**Reviewer slot failures**: 0" in rendered


def test_render_phase_detail_shows_canonical_decomposition_footnote(tmp_path: Path) -> None:
    # Issue #4882: when round-meta carries the canonical decomposition, the table footnote reconciles
    # the raw "Suggestions" count with the in-scope headline (e.g. 18 raw -> 3 in-scope + 13 OOS).
    root = tmp_path / "review"
    r1 = root / "round-1"
    r1.mkdir(parents=True)
    (r1 / "round-meta.json").write_text(
        json.dumps({
            "tally": {
                "ACCEPTED_COUNT": "0", "REJECTED_COUNT": "18", "EXONERATED_COUNT": "0",
                "NEUTRAL_COUNT": "0", "OOS_ACCEPTED_COUNT": "0", "OOS_REJECTED_COUNT": "0",
            },
            "tally_canonical": {
                "ACCEPTED_COUNT": "0", "REJECTED_COUNT": "3", "EXONERATED_COUNT": "0",
                "NEUTRAL_COUNT": "0", "OOS_ACCEPTED_COUNT": "0", "OOS_REJECTED_COUNT": "13",
            },
            "nit_pruned_count": "8",
            "summary": {"panel": {"total_slot_count": 3}},
            "collector": "",
        }) + "\n",
        encoding="utf-8",
    )
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement")
    # The Suggestions column still shows the raw round-sum (18) so no data is hidden.
    assert "| 1 | 18 | 0 |" in rendered
    # The decomposition footnote reconciles raw 18 with the in-scope 3 + 13 OOS (8 nit-pruned).
    assert "Finding decomposition (canonical, scope-aware)" in rendered
    assert "round 1: 16 finding(s) = 3 in-scope" in rendered
    assert "13 out-of-scope" in rendered
    assert "8 nit-pruned" in rendered
    assert "tally_canonical" in rendered


def test_render_phase_detail_footnote_includes_oos_proposed_and_fileable_split(tmp_path: Path) -> None:
    root = tmp_path / "review"
    r1 = root / "round-1"
    r1.mkdir(parents=True)
    (r1 / "round-meta.json").write_text(
        json.dumps({
            "tally": {
                "ACCEPTED_COUNT": "1", "REJECTED_COUNT": "0", "EXONERATED_COUNT": "0",
                "NEUTRAL_COUNT": "0", "OOS_PROPOSED_COUNT": "3", "OOS_ACCEPTED_COUNT": "1",
                "OOS_REJECTED_COUNT": "1",
            },
            "tally_canonical": {
                "ACCEPTED_COUNT": "1", "REJECTED_COUNT": "0", "EXONERATED_COUNT": "0",
                "NEUTRAL_COUNT": "0", "OOS_PROPOSED_COUNT": "3", "OOS_ACCEPTED_COUNT": "1",
                "OOS_REJECTED_COUNT": "1",
            },
            "nit_pruned_count": "0",
            "summary": {"panel": {"total_slot_count": 3}},
        }) + "\n",
        encoding="utf-8",
    )

    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement")

    assert "Finding decomposition (canonical, scope-aware)" in rendered
    assert "4 out-of-scope (3 OOS proposed, 1 OOS fileable)" in rendered


def test_render_phase_detail_dual_timing_windows(tmp_path: Path) -> None:
    root = tmp_path / "rounds"
    _write_round_meta(root / "round-1")
    timing = tmp_path / "timing-ledger.tsv"
    _write_round_timing(timing, skill="design", round_num=1, start_s=0, end_s=1800)
    _write_round_timing(timing, skill="implement", round_num=1, start_s=100, end_s=200)
    _write_vendor_timing(timing, "codex-specialist-arch-output.txt", 10, 500)
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement", timing_ledger=timing)
    assert "1m 40s" in rendered
    assert "window 0:00-30:00 (1800s)" in rendered


def test_write_round_meta_helpers(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    (round_dir / "voting-tally.md").write_text(
        "## Findings\n\n| Item | Result |\n|--|--|\n| FINDING_1 | accepted |\n| FINDING_2 | rejected |\n| OOS_1 | accepted |\n",
        encoding="utf-8",
    )
    (round_dir / "panel-manifest.ndjson").write_text('{"slot":"a","tool":"codex","output":"a.txt"}\n', encoding="utf-8")
    assert progress_report.write_implement_round_meta(round_dir) == 0
    meta = (round_dir / "round-meta.json").read_text(encoding="utf-8")
    assert '"ACCEPTED_COUNT": "1"' in meta
    assert '"OOS_PROPOSED_COUNT": "1"' in meta
    assert '"OOS_ACCEPTED_COUNT": "0"' in meta
    assert '"total_slot_count": 1' in meta
    # Issue #4882: no classification TSV present, so only the raw tally is recorded (backward compat).
    assert "tally_canonical" not in meta


def test_write_implement_round_meta_records_canonical_decomposition(tmp_path: Path) -> None:
    # Issue #4882: a finding reclassified out-of-scope after voting keeps its FINDING_ id, so the raw
    # id-prefix tally over-counts it as in-scope rejected. write_implement_round_meta must also record
    # the canonical scope-aware split (from the classification TSV) plus the nit-pruned count.
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    (round_dir / "voting-tally.md").write_text(
        "## Findings\n\n| Item | Result |\n|--|--|\n"
        "| FINDING_1 | accepted |\n| FINDING_2 | rejected |\n| FINDING_3 | rejected |\n",
        encoding="utf-8",
    )
    header = progress_report.voting.findings_classification_header().split("\t")

    def row(finding_id: str, result: str, scope: str, severity: str = "") -> str:
        cols = dict.fromkeys(header, "")
        cols.update({"finding_id": finding_id, "voting_result": result, "scope": scope})
        if result == "accepted":
            cols.update({"v1_vote": "YES", "v1_severity": severity or "minor"})
        return "\t".join(cols[name] for name in header)

    # FINDING_3 voted rejected but is scope=oos: the raw tally counts it in-scope, canonical counts OOS.
    # OOS_1 is accepted with only minor YES severity: proposed, but not fileable.
    (round_dir / "findings-classification.tsv").write_text(
        "\t".join(header) + "\n"
        + row("FINDING_1", "accepted", "in_scope") + "\n"
        + row("FINDING_2", "rejected", "in_scope") + "\n"
        + row("FINDING_3", "rejected", "oos") + "\n"
        + row("OOS_1", "accepted", "oos", "minor") + "\n",
        encoding="utf-8",
    )
    (round_dir / "prune-nit.env").write_text("PRUNED_COUNT=1\nINSCOPE_REMAINING=2\n", encoding="utf-8")

    assert progress_report.write_implement_round_meta(round_dir) == 0
    meta = json.loads((round_dir / "round-meta.json").read_text(encoding="utf-8"))
    # Raw tally counts FINDING_3 by id-prefix as an in-scope rejection (the #4882 over-count).
    assert meta["tally"]["REJECTED_COUNT"] == "2"
    assert meta["tally"]["OOS_PROPOSED_COUNT"] == "1"
    assert meta["tally"]["OOS_ACCEPTED_COUNT"] == "0"
    # Canonical (scope-aware) splits it out: 1 in-scope rejected, 1 OOS rejected.
    assert meta["tally_canonical"]["ACCEPTED_COUNT"] == "1"
    assert meta["tally_canonical"]["REJECTED_COUNT"] == "1"
    assert meta["tally_canonical"]["OOS_PROPOSED_COUNT"] == "1"
    assert meta["tally_canonical"]["OOS_ACCEPTED_COUNT"] == "0"
    assert meta["tally_canonical"]["OOS_REJECTED_COUNT"] == "1"
    assert meta["nit_pruned_count"] == "1"


def test_write_design_round_meta_security_oos_and_panel(tmp_path: Path) -> None:
    round_dir = tmp_path / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "voting-tally.md").write_text(
        "## Findings\n\n| Item | Result |\n|--|--|\n| OOS_1 | accepted |\n",
        encoding="utf-8",
    )
    (round_dir / "findings-oos.md").write_text(
        "### OOS_1: security item\nfocus-area=security\n",
        encoding="utf-8",
    )
    (round_dir / "plan-review-slots.ndjson").write_text(
        '{"slot":"slot-1","tool":"codex","output":"codex-out.txt"}\n',
        encoding="utf-8",
    )
    (round_dir / "round-summary.env").write_text("COLLECT_FAILURE_COUNT=2\n", encoding="utf-8")
    (round_dir / "revise").mkdir()
    (round_dir / "revise" / "revise.env").write_text("REVISE_STATUS=ok-fallback\nREVISE_TIER=primary\n", encoding="utf-8")
    assert progress_report.write_design_round_meta(round_dir) == 0
    meta = json.loads((round_dir / "round-meta.json").read_text(encoding="utf-8"))
    assert meta["tally"]["OOS_PROPOSED_COUNT"] == "0"
    assert meta["tally"]["OOS_ACCEPTED_COUNT"] == "0"
    assert meta["summary"]["panel"]["total_slot_count"] == 1
    assert "collector-failure-1" in meta["collector"]
    assert meta["revise"]["status"] == "ok-fallback"
    assert meta["revise"]["tier"] == "primary"


def test_write_design_round_meta_records_oos_proposed_and_fileable_split(tmp_path: Path) -> None:
    round_dir = tmp_path / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "voting-tally.md").write_text(
        "## Findings\n\n| Item | Result |\n|--|--|\n| OOS_1 | accepted |\n",
        encoding="utf-8",
    )
    header = progress_report.voting.findings_classification_header().split("\t")
    cols = dict.fromkeys(header, "")
    cols.update({
        "finding_id": "OOS_1",
        "finding_reviewers": "Cursor-Arch",
        "voting_result": "accepted",
        "v1_vote": "YES",
        "v1_severity": "minor",
        "scope": "oos",
    })
    (round_dir / "findings-classification.tsv").write_text(
        "\t".join(header) + "\n" + "\t".join(cols[name] for name in header) + "\n",
        encoding="utf-8",
    )

    assert progress_report.write_design_round_meta(round_dir) == 0
    meta = json.loads((round_dir / "round-meta.json").read_text(encoding="utf-8"))

    assert meta["tally"]["OOS_PROPOSED_COUNT"] == "1"
    assert meta["tally"]["OOS_ACCEPTED_COUNT"] == "0"


def test_render_phase_detail_top_reviewers_from_classification(tmp_path: Path) -> None:
    # Issue #4733 Bug 1: /design records per-round attribution in findings-classification.tsv
    # but never emits review-findings-full.jsonl, so Top reviewers must aggregate from the TSV
    # (the same data behind the Reviewer Competition Scoreboard) instead of rendering empty.
    root = tmp_path / "plan-review"
    r1 = root / "round-1"
    _write_round_meta(r1)
    header = progress_report.voting.findings_classification_header().split("\t")

    def row(finding_id: str, reviewer: str, result: str, severity: str = "minor", scope: str = "in_scope") -> str:
        cols = dict.fromkeys(header, "")
        cols.update({
            "finding_id": finding_id,
            "finding_reviewers": reviewer,
            "voting_result": result,
            "v1_vote": "YES" if result == "accepted" else "NO",
            "v1_severity": severity,
            "v2_vote": "YES" if result == "accepted" and severity in {"blocker", "major"} else "",
            "v2_severity": severity if result == "accepted" and severity in {"blocker", "major"} else "",
            "scope": scope,
        })
        return "\t".join(cols[name] for name in header)

    (r1 / "findings-classification.tsv").write_text(
        "\t".join(header) + "\n"
        + row("FINDING_1", "Cursor-Requirements", "accepted", "major") + "\n"
        + row("FINDING_2", "Cursor-Requirements", "accepted") + "\n"
        + row("FINDING_3", "Codex-Generic", "accepted") + "\n"
        + row("FINDING_4", "Codex-Generic", "rejected") + "\n"
        + row("OOS_1", "Cursor-Arch", "accepted", "major", "oos") + "\n",
        encoding="utf-8",
    )
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="design")
    assert "1. Cursor-Requirements: 3" in rendered
    assert "2. Codex-Generic: 1" in rendered
    assert "- (no accepted-point score attributed to a reviewer slot)" not in rendered
    # OOS rows are excluded so Top reviewers matches the in-scope Accepted column.
    assert "Cursor-Arch" not in rendered


def test_render_phase_detail_top_reviewers_implement_from_classification(tmp_path: Path) -> None:
    root = tmp_path / "review"
    r1 = root / "round-1"
    _write_round_meta(r1)
    (r1 / "panel-manifest.ndjson").write_text(
        '{"slot":"arch","tool":"cursor","output":"cursor-specialist-arch-output.txt"}\n'
        '{"slot":"generalist","tool":"codex","output":"codex-generalist-output.txt"}\n',
        encoding="utf-8",
    )
    (root / "review-findings-full.jsonl").write_text(
        '{"outcome":"accepted","reviewer":"flat-jsonl-output.txt"}\n',
        encoding="utf-8",
    )
    header = progress_report.voting.code_review_classification_header().split("\t")

    def row(finding_id: str, reviewer: str, result: str, severity: str, scope: str) -> str:
        cols = dict.fromkeys(header, "")
        cols.update({
            "finding_id": finding_id,
            "reviewer_slots": reviewer,
            "voting_result": result,
            "v1_vote": "YES" if result == "accepted" else "NO",
            "v1_severity": severity,
            "v2_vote": "YES" if result == "accepted" and severity in {"blocker", "major"} else "",
            "v2_severity": severity if result == "accepted" and severity in {"blocker", "major"} else "",
            "scope": scope,
        })
        return "\t".join(cols[name] for name in header)

    (r1 / "findings-classification.tsv").write_text(
        "\t".join(header) + "\n"
        + row("FINDING_1", "cursor-specialist-arch-output.txt", "accepted", "major", "in_scope") + "\n"
        + row("FINDING_2", "codex-generalist-output.txt", "accepted", "minor", "in_scope") + "\n"
        + row("FINDING_3", "cursor-specialist-oos-output.txt", "accepted", "major", "oos") + "\n",
        encoding="utf-8",
    )
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement", findings_file=root / "review-findings-full.jsonl")
    assert "1. cursor/arch: 2" in rendered
    assert "2. codex/generalist: 1" in rendered
    assert "flat-jsonl" not in rendered
    assert "cursor-specialist-oos" not in rendered


def test_render_phase_detail_top_reviewers_implement_from_classification_vendor_fallback(
    tmp_path: Path,
) -> None:
    root = tmp_path / "review"
    r1 = root / "round-1"
    _write_round_meta(r1, accepted=1, rejected=0, reviewers=1)
    output = "cursor-specialist-arch-output.txt"
    (r1 / "panel-manifest.ndjson").write_text(
        json.dumps({"slot": "arch", "tool": "cursor", "output": output}) + "\n",
        encoding="utf-8",
    )
    (root / "collector-results.env").write_text(
        f"REVIEWER_FILE={output}\nTOOL=codex\nSTATUS=OK\n\n",
        encoding="utf-8",
    )
    header = progress_report.voting.code_review_classification_header().split("\t")
    cols = dict.fromkeys(header, "")
    cols.update({
        "finding_id": "FINDING_1",
        "reviewer_slots": output,
        "voting_result": "accepted",
        "v1_vote": "YES",
        "v1_severity": "minor",
        "scope": "in_scope",
    })
    (r1 / "findings-classification.tsv").write_text(
        "\t".join(header) + "\n" + "\t".join(cols[name] for name in header) + "\n",
        encoding="utf-8",
    )

    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement")

    assert not (r1 / "collector-results.env").exists()
    assert "1. cursor/arch (via Codex): 1" in rendered


def test_render_phase_detail_total_relabeled_round_sum_under_recurrence(tmp_path: Path) -> None:
    # Issue #4809: when the plan-review loop re-raises and re-accepts the same finding across
    # rounds (the #4808 non-convergence condition), the Total Suggestions/Accepted is a naive
    # per-round sum that exceeds the distinct-finding count, and Top reviewers inflates the same
    # way. The per-round artifacts carry no stable cross-round finding identity (only per-round
    # FINDING_N), so distinct-finding dedup is not reliably achievable; instead the Total stays a
    # round-sum but is labeled and captioned so it cannot be misread as a distinct-finding count.
    root = tmp_path / "plan-review"
    header = progress_report.voting.findings_classification_header().split("\t")
    cols = dict.fromkeys(header, "")
    cols.update({
        "finding_id": "FINDING_1",
        "finding_reviewers": "Cursor-Arch",
        "voting_result": "accepted",
        "v1_vote": "YES",
        "v1_severity": "minor",
        "scope": "in_scope",
    })
    line = "\t".join(cols[name] for name in header)
    for round_num in (1, 2, 3):
        round_dir = root / f"round-{round_num}"
        _write_round_meta(round_dir)
        # Identical single finding accepted every round: the #4808 recurrence signature.
        (round_dir / "findings-classification.tsv").write_text(
            "\t".join(header) + "\n" + line + "\n",
            encoding="utf-8",
        )
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="design")
    # The Total row is explicitly labeled a round-sum, never a bare "Total" implying distinct work.
    assert "| **Total (round-sum)** |" in rendered
    assert "| **Total** |" not in rendered
    # The caption spells out the round-sum semantics so the inflated numbers cannot silently mislead.
    assert "round-sum" in rendered
    assert "counted once per round" in rendered
    # One finding accepted in all three rounds is counted once per round (round-sum => "— 3"),
    # not deduplicated to 1; the label and caption are what prevent misreading it as distinct work.
    assert "1. Cursor-Arch: 3" in rendered


def test_parse_classification_tsv_counts_neutral_oos(tmp_path: Path) -> None:
    header = progress_report.voting.findings_classification_header().split("\t")

    def row(finding_id: str, result: str, scope: str = "oos") -> str:
        cols = dict.fromkeys(header, "")
        cols.update({
            "finding_id": finding_id,
            "finding_reviewers": "Cursor-Arch",
            "voting_result": result,
            "scope": scope,
        })
        return "\t".join(cols[name] for name in header)

    path = tmp_path / "findings-classification.tsv"
    path.write_text(
        "\t".join(header) + "\n"
        + row("OOS_1", "accepted") + "\n"
        + row("OOS_2", "neutral") + "\n"
        + row("OOS_3", "rejected") + "\n",
        encoding="utf-8",
    )
    accepted, rejected, neutral, exonerated, oos_accepted, oos_rejected = progress_report._parse_classification_tsv(path)
    assert accepted == rejected == neutral == exonerated == 0
    assert oos_accepted == 1
    assert oos_rejected == 2


def test_top_reviewers_whitespace_coproposers_and_comma_fallback(tmp_path: Path) -> None:
    root = tmp_path / "plan-review"
    r1 = root / "round-1"
    _write_round_meta(r1)
    (r1 / "plan-review-prune-label-map.tsv").write_text(
        "slot\thuman_label\nplan-requirements\tCursor-Pragmatic\nplan-architecture\tCodex-Arch\n",
        encoding="utf-8",
    )
    header = progress_report.voting.findings_classification_header().split("\t")

    def row(finding_id: str, reviewer: str, result: str, severity: str = "major") -> str:
        cols = dict.fromkeys(header, "")
        cols.update({
            "finding_id": finding_id,
            "finding_reviewers": reviewer,
            "voting_result": result,
            "v1_vote": "YES" if result == "accepted" else "NO",
            "v1_severity": severity,
            "v2_vote": "YES" if result == "accepted" and severity in {"blocker", "major"} else "",
            "v2_severity": severity if result == "accepted" and severity in {"blocker", "major"} else "",
            "scope": "in_scope",
        })
        return "\t".join(cols[name] for name in header)

    (r1 / "findings-classification.tsv").write_text(
        "\t".join(header) + "\n"
        + row("FINDING_1", "Cursor-Pragmatic Codex-Arch", "accepted") + "\n"
        + row("FINDING_2", "Unknown-Label", "accepted") + "\n",
        encoding="utf-8",
    )
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="design")
    assert "1. Codex-Arch: 2" in rendered
    assert "2. Cursor-Pragmatic: 2" in rendered
    assert "3. Unknown-Label: 2" in rendered
    assert "Cursor-Pragmatic Codex-Arch" not in rendered


def test_top_reviewers_classification_unique_finder_bonus(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("LARCH_UNIQUE_FINDER_BONUS", "0.25")
    root = tmp_path / "plan-review"
    r1 = root / "round-1"
    _write_round_meta(r1)
    (r1 / "plan-review-prune-label-map.tsv").write_text(
        "slot\thuman_label\nplan-requirements\tCursor-Pragmatic\nplan-architecture\tCodex-Arch\n",
        encoding="utf-8",
    )
    header = progress_report.voting.findings_classification_header().split("\t")

    def row(finding_id: str, reviewer: str, scope: str = "in_scope") -> str:
        cols = dict.fromkeys(header, "")
        cols.update({
            "finding_id": finding_id,
            "finding_reviewers": reviewer,
            "voting_result": "accepted",
            "v1_vote": "YES",
            "v1_severity": "minor",
            "scope": scope,
        })
        return "\t".join(cols[name] for name in header)

    (r1 / "findings-classification.tsv").write_text(
        "\t".join(header) + "\n"
        + row("FINDING_SOLE", "Solo-Reviewer") + "\n"
        + row("FINDING_MULTI", "Multi-A, Multi-B") + "\n"
        + row("FINDING_WHITESPACE", "Cursor-Pragmatic Codex-Arch") + "\n"
        + row("OOS_1", "Oos-Reviewer", "oos") + "\n",
        encoding="utf-8",
    )
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="design")
    assert "1. Solo-Reviewer: 1.25" in rendered
    assert "2. Codex-Arch: 1" in rendered
    assert "3. Cursor-Pragmatic: 1" in rendered
    assert "4. Multi-A: 1" in rendered
    assert "5. Multi-B: 1" in rendered
    assert ": 1.0" not in rendered
    assert "Oos-Reviewer" not in rendered


def test_write_design_round_meta_collector_from_real_records(tmp_path: Path) -> None:
    # Issue #4733 Bug 2: the collector field is built from real per-slot collector-results.env
    # records (KEY=VALUE blocks: REVIEWER_FILE/TOOL/STATUS/...), not count-based placeholders.
    design = tmp_path
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "voting-tally.md").write_text(
        "## Findings\n\n| Item | Result |\n|--|--|\n| FINDING_1 | accepted |\n",
        encoding="utf-8",
    )
    (round_dir / "plan-review-slots.ndjson").write_text(
        '{"slot":"cursor-plan-requirements","tool":"cursor","output":"cursor-plan-requirements-output.txt"}\n',
        encoding="utf-8",
    )
    (round_dir / "round-summary.env").write_text("COLLECT_FAILURE_COUNT=1\n", encoding="utf-8")
    # collector-results.env is written at the design tmpdir root (round_dir.parent.parent).
    (design / "collector-results.env").write_text(
        "REVIEWER_FILE=ok-output.txt\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\nSTRUCTURED_SIDECAR=\nFAILURE_REASON=\n"
        "\n"
        "REVIEWER_FILE=cursor-plan-requirements-output.txt\nTOOL=cursor\nSTATUS=FAILED\nEXIT_CODE=1\nSTRUCTURED_SIDECAR=\nFAILURE_REASON=timeout\n",
        encoding="utf-8",
    )
    assert progress_report.write_design_round_meta(round_dir) == 0
    collector = json.loads((round_dir / "round-meta.json").read_text(encoding="utf-8"))["collector"]
    assert "TOOL=cursor" in collector
    assert "REVIEWER_FILE=cursor-plan-requirements-output.txt" in collector
    assert "collector-failure" not in collector
    assert "ok-output.txt" not in collector  # OK records are not failures.


def test_design_failure_label_resolves_real_slot_end_to_end(tmp_path: Path) -> None:
    # Issue #4733 Bug 2: a failed cursor-plan-requirements slot renders as cursor/...,
    # not unknown/collector-failure-N, once the writer emits real records.
    design = tmp_path
    root = design / "plan-review"
    round_dir = root / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "voting-tally.md").write_text(
        "## Findings\n\n| Item | Result |\n|--|--|\n| FINDING_1 | accepted |\n",
        encoding="utf-8",
    )
    (round_dir / "plan-review-slots.ndjson").write_text(
        '{"slot":"cursor-plan-requirements","tool":"cursor","output":"cursor-plan-requirements-output.txt"}\n',
        encoding="utf-8",
    )
    (round_dir / "round-summary.env").write_text("COLLECT_FAILURE_COUNT=1\n", encoding="utf-8")
    (design / "collector-results.env").write_text(
        "REVIEWER_FILE=cursor-plan-requirements-output.txt\nTOOL=cursor\nSTATUS=FAILED\nEXIT_CODE=1\nSTRUCTURED_SIDECAR=\nFAILURE_REASON=timeout\n",
        encoding="utf-8",
    )
    assert progress_report.write_design_round_meta(round_dir) == 0
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="design")
    assert "**Reviewer slot failures**: 1" in rendered
    assert "unknown/collector-failure" not in rendered
    assert "cursor/" in rendered


def test_render_phase_detail_gantt_includes_signal_vendor_rows(tmp_path: Path) -> None:
    root = tmp_path / "rounds"
    _write_round_meta(root / "round-1")
    timing = tmp_path / "timing-ledger.tsv"
    _write_round_timing(timing, skill="implement", round_num=1, start_s=100, end_s=200)
    _write_vendor_timing(timing, "codex-output.txt", 120, 150, status="signal")
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement", timing_ledger=timing)
    assert "## Review Phase Detail" in rendered
    assert "| 1 | 4 | 2 | 1 | 1 | 1m 40s | N/A | 3 |" in rendered
    assert "### Round 1 reviewer timing" in rendered
    assert "```" in rendered
    assert "codex/codex-review" in rendered
    assert "│" in rendered
    assert "█" in rendered
    assert "30s" in rendered
    assert "No reviewer timing tasks overlapped this round." not in rendered


def test_render_phase_detail_gantt_shows_all_rows_when_over_cap(tmp_path: Path) -> None:
    root = tmp_path / "rounds"
    _write_round_meta(root / "round-1")
    timing = tmp_path / "timing-ledger.tsv"
    _write_round_timing(timing, skill="implement", round_num=1, start_s=100, end_s=200)
    over_cap, latest_label = _write_over_cap_plain_codex_review_rows(timing)

    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement", timing_ledger=timing)

    assert "### Round 1 reviewer timing" in rendered
    assert latest_label in rendered
    assert sum(1 for line in rendered.splitlines() if "│" in line and "█" in line) >= over_cap


def test_render_phase_detail_design_gantt_labels_gate_b_apply(tmp_path: Path) -> None:
    root = tmp_path / "rounds"
    _write_round_meta(root / "round-1")
    timing = tmp_path / "timing-ledger.tsv"
    _write_round_timing(timing, skill="design", round_num=1, start_s=100, end_s=240)
    _write_vendor_timing(
        timing,
        "codex-plan-requirements-output.txt",
        110,
        180,
        kind="codex-plan-requirements",
        skill="design",
    )
    _write_vendor_timing(
        timing,
        "gate-b-apply-round-1.out",
        180,
        240,
        vendor="claude",
        kind="gate-b-apply",
        skill="design",
    )

    rendered = progress_report.render_phase_detail(rounds_root=root, skill="design", timing_ledger=timing)

    assert "### Round 1 reviewer timing" in rendered
    assert "gate-b/apply" in rendered
    assert "window 0:00-2:20 (140s)" in rendered


def test_render_phase_detail_gantt_labels_voter_dispatch_prep(tmp_path: Path) -> None:
    # Issue #7166: the serial pre-dispatch render window is recorded as a voter-dispatch-prep
    # vendor row so the Gantt fills the band between the aggregator bar and the voter bars
    # instead of leaving it blank.
    root = tmp_path / "rounds"
    _write_round_meta(root / "round-1")
    timing = tmp_path / "timing-ledger.tsv"
    _write_round_timing(timing, skill="implement", round_num=1, start_s=100, end_s=300)
    _write_vendor_timing(timing, "aggregator-output.txt", 120, 160, vendor="claude", kind="claude-phase3-aggregator")
    _write_vendor_timing(timing, "voter-dispatch-prep-round-1.out", 160, 260, vendor="claude", kind="voter-dispatch-prep")
    _write_vendor_timing(timing, "codex-validity-vote-output.txt", 260, 290, vendor="codex", kind="codex-review-voter")

    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement", timing_ledger=timing)

    assert "### Round 1 reviewer timing" in rendered
    assert "aggregator" in rendered
    assert "voter-dispatch-prep" in rendered
    assert "codex/validity-vote" in rendered
    prep_line = next(line for line in rendered.splitlines() if "voter-dispatch-prep" in line)
    assert "█" in prep_line


def test_render_phase_detail_gantt_labels_reviewer_collect(tmp_path: Path) -> None:
    # Issue #7179: the reviewers-to-aggregator window is recorded as a reviewer-collect vendor
    # row so the Gantt fills the band between the reviewer bars and the aggregator bar instead
    # of leaving it blank. Reviewers finish at 160, aggregator starts at 260, and the
    # reviewer-collect bar fills the [160, 260] gap that would otherwise be empty.
    root = tmp_path / "rounds"
    _write_round_meta(root / "round-1")
    timing = tmp_path / "timing-ledger.tsv"
    _write_round_timing(timing, skill="implement", round_num=1, start_s=100, end_s=320)
    _write_vendor_timing(timing, "codex-correctness-output.txt", 100, 160, vendor="codex", kind="codex-review")
    _write_vendor_timing(timing, "reviewer-collect-round-1.out", 160, 260, vendor="claude", kind="reviewer-collect")
    _write_vendor_timing(timing, "aggregator-output.txt", 260, 300, vendor="claude", kind="claude-phase3-aggregator")

    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement", timing_ledger=timing)

    assert "### Round 1 reviewer timing" in rendered
    assert "reviewer-collect" in rendered
    assert "aggregator" in rendered
    collect_line = next(line for line in rendered.splitlines() if "reviewer-collect" in line)
    assert "█" in collect_line


def test_render_phase_detail_splits_gantt_per_attempt(tmp_path: Path) -> None:
    # Issue #5504: a stall recovery reruns round 1 in the same session, leaving two round rows
    # for round 1. The Gantt must render one section per attempt, each with its own tight
    # window, so each attempt's reviewers and post-aggregation probes stay next to their own
    # aggregator instead of intermixing across a single merged session-spanning window.
    root = tmp_path / "rounds"
    _write_round_meta(root / "round-1")
    timing = tmp_path / "timing-ledger.tsv"
    _write_round_timing(timing, skill="implement", round_num=1, start_s=100, end_s=200, attempt=1)
    _write_round_timing(timing, skill="implement", round_num=1, start_s=400, end_s=520, attempt=2)
    _write_vendor_timing(timing, "codex-specialist-correctness-output.txt", 110, 190)
    _write_vendor_timing(timing, "codex-specialist-edge-cases-output.txt", 410, 510)
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement", timing_ledger=timing)
    assert "### Round 1 reviewer timing (attempt 1)" in rendered
    assert "### Round 1 reviewer timing (attempt 2)" in rendered
    # Each attempt renders its own tight window (100s, 120s), never the merged 100..520 span.
    assert "(100s)" in rendered
    assert "(120s)" in rendered
    assert "(420s)" not in rendered
    # The bare single-attempt header must not appear once a round is split per attempt.
    assert "### Round 1 reviewer timing\n" not in rendered


def test_render_phase_detail_single_attempt_keeps_bare_header(tmp_path: Path) -> None:
    # Issue #5504: an explicit attempt=1 (no rerun) renders the bare header identical to
    # pre-attempt ledgers, so the "(attempt N)" suffix shows up only when a round truly reran.
    root = tmp_path / "rounds"
    _write_round_meta(root / "round-1")
    timing = tmp_path / "timing-ledger.tsv"
    _write_round_timing(timing, skill="implement", round_num=1, start_s=100, end_s=200, attempt=1)
    _write_vendor_timing(timing, "codex-specialist-correctness-output.txt", 110, 190)
    rendered = progress_report.render_phase_detail(rounds_root=root, skill="implement", timing_ledger=timing)
    assert "### Round 1 reviewer timing\n" in rendered
    assert "(attempt 1)" not in rendered


def test_render_phase_detail_token_ledger_dual_window(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    root = tmp_path / "rounds"
    _write_round_meta(root / "round-1")
    timing = tmp_path / "timing-ledger.tsv"
    _write_round_timing(timing, skill="design", round_num=1, start_s=0, end_s=1800)
    _write_round_timing(timing, skill="implement", round_num=1, start_s=100, end_s=200)
    _write_vendor_timing(timing, "codex-specialist-arch-output.txt", 10, 500)
    token_ledger = tmp_path / "tokens.jsonl"
    in_window_ts = datetime.fromtimestamp(150, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_window_ts = datetime.fromtimestamp(50, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    token_ledger.write_text(
        json.dumps({"type": "vendor", "vendor": "codex", "input": 1000, "output": 0, "cache_read": 0, "cache_create": 0, "ts": in_window_ts})
        + "\n"
        + json.dumps({"type": "vendor", "vendor": "codex", "input": 1_000_000, "output": 0, "cache_read": 0, "cache_create": 0, "ts": out_window_ts})
        + "\n",
        encoding="utf-8",
    )
    def fake_cost(argv: list[str], **_kwargs: object) -> str:
        tokens = "0"
        for index, arg in enumerate(argv[:-1]):
            if arg == "--codex-input-tokens":
                tokens = argv[index + 1]
                break
        return f"TOTAL_COST={tokens}\n"

    monkeypatch.setattr(progress_report.report_tokens_cost, "token_cost_from_args", fake_cost)
    rendered = progress_report.render_phase_detail(
        rounds_root=root,
        skill="implement",
        timing_ledger=timing,
        token_ledger=token_ledger,
    )
    assert "| 1 |" in rendered
    assert "$1000" in rendered
    assert "window 0:00-30:00 (1800s)" in rendered


def test_render_phase_detail_token_ledger_codex_mini_model_split(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    # gpt-5.4-mini tokens must use --codex-mini-* flags, not --codex-* (gpt-5.5 rates).
    root = tmp_path / "rounds"
    _write_round_meta(root / "round-1")
    timing = tmp_path / "timing-ledger.tsv"
    _write_round_timing(timing, skill="implement", round_num=1, start_s=100, end_s=200)
    token_ledger = tmp_path / "tokens.jsonl"
    in_window_ts = datetime.fromtimestamp(150, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    token_ledger.write_text(
        json.dumps({"type": "vendor", "vendor": "codex", "model": "gpt-5.5", "input": 1000, "output": 0, "cache_read": 0, "cache_create": 0, "ts": in_window_ts})
        + "\n"
        + json.dumps({"type": "vendor", "vendor": "codex", "model": "gpt-5.4-mini", "input": 0, "output": 2000, "cache_read": 0, "cache_create": 0, "ts": in_window_ts})
        + "\n",
        encoding="utf-8",
    )
    captured: dict[str, list[str]] = {}

    def fake_cost(argv: list[str], **_kwargs: object) -> str:
        captured["argv"] = list(argv)
        return "TOTAL_COST=0.00\n"

    monkeypatch.setattr(progress_report.report_tokens_cost, "token_cost_from_args", fake_cost)
    progress_report.render_phase_detail(
        rounds_root=root,
        skill="implement",
        timing_ledger=timing,
        token_ledger=token_ledger,
    )
    argv = captured.get("argv", [])
    # gpt-5.5 tokens go to --codex-input-tokens / --codex-output-tokens
    assert "--codex-input-tokens" in argv
    i = argv.index("--codex-input-tokens")
    assert argv[i + 1] == "1000"
    assert "--codex-output-tokens" in argv
    o = argv.index("--codex-output-tokens")
    assert argv[o + 1] == "0"
    # gpt-5.4-mini tokens go to --codex-mini-* flags, not lumped into gpt-5.5
    assert "--codex-mini-output-tokens" in argv
    mo = argv.index("--codex-mini-output-tokens")
    assert argv[mo + 1] == "2000"


def test_render_phase_detail_best_effort_timeout(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    # Block the core renderer past the wall-clock budget via a real Event wait
    # (conftest no-ops time.sleep, so a sleep-based block would not actually block).
    release = threading.Event()

    def blocking_render(*_args: object, **_kwargs: object) -> str:
        release.wait(timeout=10)
        return "should never be returned"

    monkeypatch.setattr(progress_report, "render_phase_detail", blocking_render)
    monkeypatch.setattr(progress_report, "RENDER_PHASE_DETAIL_TIMEOUT_SECONDS", 0.05)
    try:
        assert progress_report._render_phase_detail_best_effort(Path("/missing"), skill="implement") == ""
    finally:
        release.set()


def test_write_implement_round_meta_records_difficulty(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    (round_dir / "review-tally.env").write_text("ACCEPTED_COUNT=0\nREJECTED_COUNT=0\nNEUTRAL_COUNT=0\nEXONERATED_COUNT=0\n", encoding="utf-8")
    (round_dir / "panel-manifest.ndjson").write_text(
        json.dumps({"slot": "dyn-risk", "tool": "codex", "output": "out.txt", "vendor": "codex", "resolved_model": "gpt"}) + "\n",
        encoding="utf-8",
    )
    (round_dir / "difficulty-rating.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "rater": "review",
                "rater_tool": "claude",
                "rater_model": "gpt",
                "predicted_tier": "MODERATE",
                "confidence": "high",
                "rationale": "persisted review record",
                "design_tier": None,
                "implement_tier": None,
                "applied_tier": "HARD",
                "override_source": "operator",
                "floors_applied": [],
                "audit_upgrade": "true",
                "escalations": [{"round": 2, "from_tier": "MODERATE", "to_tier": "HARD", "trigger": "escalated-high-accepted"}],
                "panel_skipped": None,
                "panel_tier": "HARD",
                "round_cap": 3,
                "codex_model_role": "default",
                "audit_evaluated": True,
                "escalated_round": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (round_dir / "scout-difficulty-rating.raw.json").write_text(
        json.dumps({"predicted_tier": "TRIVIAL", "confidence": "low", "rationale": "unclear small diff"}) + "\n",
        encoding="utf-8",
    )

    assert progress_report.write_implement_round_meta(round_dir) == 0
    data = json.loads((round_dir / "round-meta.json").read_text(encoding="utf-8"))

    assert data["difficulty"]["tier_in_effect"] == "HARD"
    assert data["difficulty"]["ceiling_in_effect"] == 2
    assert data["difficulty"]["override_source"] == "operator"
    assert data["difficulty"]["audit_upgrade"] == "true"
    assert data["difficulty"]["codex_model_role"] == "default"
    assert data["difficulty"]["panel_tier"] == "HARD"
    assert data["difficulty"]["round_cap"] == 2
    assert data["difficulty"]["escalations"]
    assert data["difficulty"]["scout"]["confidence"] == "low"


def test_materialize_design_panel_manifest_keeps_model_fields(tmp_path: Path) -> None:
    round_dir = tmp_path / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    (tmp_path / "plan-review-slots.ndjson").write_text(
        json.dumps({"slot": "arch", "tool": "cursor", "output": "arch.txt", "vendor": "cursor", "resolved_model": "cursor-model"}) + "\n",
        encoding="utf-8",
    )

    assert progress_report._materialize_design_panel_manifest(round_dir) == 1
    row = json.loads((round_dir / "panel-manifest.ndjson").read_text(encoding="utf-8"))

    assert row["vendor"] == "cursor"
    assert row["resolved_model"] == "cursor-model"
