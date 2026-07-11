"""Tests for final_report.py extraction surface."""

# pyright: reportUnusedCallResult=false, reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownLambdaType=false


from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from larch.core import config
from larch.errors import ShipError
from larch.implement import scope_disposition
from larch.report import final_report, progress_report

def _write_minimal_state(tmp_path: Path) -> None:
    (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=0\nRUN_ID=run1\n", encoding="utf-8")
    (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")
    (tmp_path / "ship-pr-state.sh").write_text("PR_NUMBER=1\nPR_URL=https://github.com/o/r/pull/1\n", encoding="utf-8")
    (tmp_path / "finalize-state.sh").write_text("", encoding="utf-8")
    (tmp_path / "run-flags.sh").write_text("FORCE_REQUESTED=false\n", encoding="utf-8")


def _stub_cost_and_assessment(monkeypatch: Any) -> None:
    def fake_token_fields(**_kw: object) -> dict[str, object]:
        return {"cost_unavailable": True}

    def no_assess(
        _category: str,
        _details: tuple[final_report.exec_issue_detail.IssueDetail, ...],
    ) -> dict[str, str]:
        return {}

    monkeypatch.setattr(final_report, "_final_report_token_fields", fake_token_fields)
    monkeypatch.setattr(final_report.exec_issue_detail, "assess_issue_details", no_assess)


def _write_round_meta(round_dir: Path, *, reviewers: int) -> None:
    round_dir.mkdir(parents=True, exist_ok=True)
    (round_dir / "round-meta.json").write_text(
        json.dumps({
            "tally": {
                "ACCEPTED_COUNT": "2",
                "REJECTED_COUNT": "1",
                "EXONERATED_COUNT": "0",
                "NEUTRAL_COUNT": "1",
                "OOS_ACCEPTED_COUNT": "1",
                "OOS_REJECTED_COUNT": "1",
            },
            "summary": {"panel": {"total_slot_count": reviewers}},
        }),
        encoding="utf-8",
    )


def _write_round_timing(ledger: Path, *, round_num: int, start_s: int, end_s: int) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0, end_s - start_s)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(
            f"v1\tround\t{start_s}\timplement\t-\t{round_num}\t{start_s}\t{end_s}\t"
            f"{duration}\t0\t0\t0\t-\n"
        )


def _write_vendor_timing(ledger: Path, output: str, start_s: int, end_s: int) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0, end_s - start_s)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(
            f"v1\tvendor\t{end_s}\timplement\t-\tcodex\tcodex-review\t{start_s}\t{end_s}\t"
            f"{duration}\t{output}\t0\tcomplete\n"
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


def _visible_gantt_data_row_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if "│" in line and "█" in line)


def test_write_final_report_summary_final_write_failure_returns_error(
    tmp_path: Path,
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    _write_minimal_state(tmp_path)
    original_write_text = Path.write_text

    def patched_write_text(self: Path, data: str, *args: object, **kwargs: object) -> int:
        if self.name == "summary-final.md":
            raise OSError("disk full")
        return original_write_text(self, data, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "write_text", patched_write_text)

    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)

    assert rc == 1
    assert "summary-final write failed" in err


def test_write_final_report_module_renders_summary(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _write_minimal_state(tmp_path)
    _stub_cost_and_assessment(monkeypatch)
    rc, url, err = final_report.write_final_report(tmp_path, comment_only=True)
    assert (rc, url, err) == (0, "", "")
    assert "## /implement run run1" in (tmp_path / "summary-final.md").read_text(encoding="utf-8")


def test_write_final_report_renders_cursor_cost_lanes(tmp_path: Path) -> None:
    _write_minimal_state(tmp_path)
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    (run_dir / "token-report.json").write_text(
        json.dumps({
            "claude": {"totals": {"input": 1, "total": 1}},
            "BUCKETS_claude": {"input": 1},
            "BUCKETS_cursor": {"input": 300, "cache_read": 60, "output": 30},
            "BUCKETS_cursor_by_model": {
                "composer-2.5": {"input": 100, "cache_read": 20, "output": 10},
                "grok-4.5": {"input": 100, "cache_read": 20, "output": 10},
                "auto": {"input": 100, "cache_read": 20, "output": 10},
            },
        }),
        encoding="utf-8",
    )

    rc, url, err = final_report.write_final_report(tmp_path, comment_only=True)

    assert (rc, url, err) == (0, "", "")
    summary = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "Cursor $" in summary
    assert "Composer $" in summary
    assert "Grok $" in summary
    assert "Auto $" not in summary


def test_final_report_code_review_line_ignores_stale_ship_state(tmp_path: Path) -> None:
    _write_minimal_state(tmp_path)
    ship = tmp_path / "ship-pr-state.sh"
    ship.write_text(
        "PR_NUMBER=0\nPR_URL=N/A\nCODE_REVIEW_LINE=stale ship value\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    (run_dir / "code-review-tally.json").write_text(
        json.dumps({"accepted_count": 2, "rejected_count": 1}),
        encoding="utf-8",
    )

    fields = final_report._derive_final_report_fields(
        tmp_path,
        run_id="run1",
        repo="",
        repo_unavailable=True,
        pr_number="0",
        ship=ship,
    )

    assert fields["code_review_line"] == "2/3 accepted"


def test_write_final_report_includes_review_timing_gantt(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _write_minimal_state(tmp_path)
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    round_dir = run_dir / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "round-meta.json").write_text(
        json.dumps({
            "tally": {
                "ACCEPTED_COUNT": "2",
                "REJECTED_COUNT": "1",
                "EXONERATED_COUNT": "0",
                "NEUTRAL_COUNT": "1",
                "OOS_ACCEPTED_COUNT": "1",
                "OOS_REJECTED_COUNT": "1",
            },
            "summary": {"panel": {"total_slot_count": 3}},
        }),
        encoding="utf-8",
    )
    (tmp_path / "timing-ledger.tsv").write_text(
        "v1\tround\t100\timplement\t-\t1\t100\t200\t100\t0\t0\t0\t-\n"
        "v1\tvendor\t150\timplement\t-\tcodex\tcodex-review\t120\t150\t30\tcodex-output.txt\t0\tsignal\n",
        encoding="utf-8",
    )
    (tmp_path / "execution-issues.md").write_text(
        "### Warnings\n- review run warning\n",
        encoding="utf-8",
    )
    _stub_cost_and_assessment(monkeypatch)

    rc, url, err = final_report.write_final_report(
        tmp_path,
        comment_only=True,
        skip_tracking_upsert=True,
    )

    assert (rc, url, err) == (0, "", "")
    summary = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "codex/codex-review" in summary
    assert "█" in summary
    assert "│ 30s" in summary
    assert "<!-- larch:run-summary v=1 -->" in summary
    assert "## Exec Issues and Warnings" in summary
    assert summary.index("## Review Phase Detail") < summary.index("## Exec Issues and Warnings")
    assert summary.index("## Exec Issues and Warnings") < summary.index("<!-- larch:run-summary v=1 -->")
    assert "No review rounds completed." not in summary
    assert "No reviewer timing tasks overlapped this round." not in summary
    assert "No reviewer timing tasks overlapped" not in summary


def test_write_final_report_includes_uncapped_review_timing_gantt(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _write_minimal_state(tmp_path)
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    round_dir = run_dir / "round-1"
    timing = tmp_path / "timing-ledger.tsv"
    _write_round_timing(timing, round_num=1, start_s=100, end_s=200)
    over_cap, latest_label = _write_over_cap_plain_codex_review_rows(timing)
    _write_round_meta(round_dir, reviewers=over_cap)
    _stub_cost_and_assessment(monkeypatch)

    rc, url, err = final_report.write_final_report(
        tmp_path,
        comment_only=False,
        skip_tracking_upsert=True,
    )

    assert (rc, url, err) == (0, "", "")
    summary_paths = [
        tmp_path / "summary-final.md",
        run_dir / "final-summary.md",
    ]
    for summary_path in summary_paths:
        body = summary_path.read_text(encoding="utf-8")
        assert "<!-- larch:run-summary v=1 -->" in body
        assert "### Round 1 reviewer timing" in body
        assert body.index("## Review Phase Detail") < body.index("<!-- larch:run-summary v=1 -->")
        assert "```" in body
        assert "█" in body
        assert latest_label in body
        assert _visible_gantt_data_row_count(body) >= over_cap
        assert "codex/codex-review" not in body


def test_step18b_reports_write_failure(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(final_report, "write_final_report", lambda _tmpdir: (7, "", "boom"))
    emit, rc, _present, _snapshot = final_report.step18b_final_report(tmp_path)
    assert emit is False
    assert rc == 7


def test_refresh_issue_counts_counts_ndjson_urls_separately(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    (run_dir / "execution-issues.ndjson").write_text(
        json.dumps({"category": "Warnings", "body": "- warn\n"}) + "\n",
        encoding="utf-8",
    )
    assert final_report._refresh_issue_counts(implement_tmpdir=tmp_path, run_id="run1") == (0, 1)


def test_final_report_token_fields_uses_manifest_main_model_and_claude_sub_by_model(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps({"model_roster": {"main": "claude-sonnet-4-6"}}),
        encoding="utf-8",
    )
    (run_dir / "token-report.json").write_text(
        json.dumps({
            "claude": {"totals": {"input": 1_000_000, "total": 1_000_000}},
            "BUCKETS_claude": {"input": 1_000_000},
            "claude_sub": {"totals": {"input": 1_000_000, "total": 1_000_000}},
            "BUCKETS_claude_sub": {"input": 1_000_000},
            "BUCKETS_claude_sub_by_model": {"claude-haiku-4-5": {"input": 1_000_000}},
        }),
        encoding="utf-8",
    )

    fields = final_report._final_report_token_fields(implement_tmpdir=tmp_path, run_id="run1")

    assert fields["cost_unavailable"] is False
    assert fields["claude_cost"] == "3.00"
    assert fields["claude_sub_cost"] == "1.00"


def test_final_report_token_fields_glm_main_uses_glm_rates(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps({"model_roster": {"main": "glm-5.2"}}),
        encoding="utf-8",
    )
    (run_dir / "token-report.json").write_text(
        json.dumps({
            "claude": {"totals": {"input": 1_000_000, "output": 1_000_000, "total": 2_000_000}},
            "BUCKETS_claude": {"input": 1_000_000, "output": 1_000_000},
            "claude_sub": {"totals": {"input": 1_000_000, "total": 1_000_000}},
            "BUCKETS_claude_sub": {"input": 1_000_000},
        }),
        encoding="utf-8",
    )

    fields = final_report._final_report_token_fields(implement_tmpdir=tmp_path, run_id="run1")

    # GLM: 1M*$1.40 + 1M*$4.40 = $5.80 (not Opus $5+$25=$30)
    assert fields["claude_cost"] == "5.80"
    # Shared TOTAL stays token-based: 5.80 + opus-sub 5.00 = 10.80
    assert fields["total_cost"] == "10.80"
    assert fields["claude_sub_cost"] == "5.00"


def test_final_report_token_fields_glm_1m_alias_uses_glm_rates(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps({"model_roster": {"main": "glm-5.2[1m]"}}),
        encoding="utf-8",
    )
    (run_dir / "token-report.json").write_text(
        json.dumps({
            "claude": {"totals": {"input": 1_000_000, "total": 1_000_000}},
            "BUCKETS_claude": {"input": 1_000_000},
        }),
        encoding="utf-8",
    )

    fields = final_report._final_report_token_fields(implement_tmpdir=tmp_path, run_id="run1")
    assert fields["claude_cost"] == "1.40"


def test_write_final_report_glm_1m_alias_plan_estimate_in_summary(tmp_path: Path) -> None:
    _write_minimal_state(tmp_path)
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps({"model_roster": {"main": "glm-5.2[1m]"}, "larch_version": "1.0.0", "effort": "high"}),
        encoding="utf-8",
    )
    (run_dir / "token-report.json").write_text(
        json.dumps({
            "claude": {"totals": {"input": 1_000_000, "output": 1_000_000, "total": 2_000_000}},
            "BUCKETS_claude": {"input": 1_000_000, "output": 1_000_000},
            "claude_sub": {"totals": {"input": 1_000_000, "total": 1_000_000}},
            "BUCKETS_claude_sub": {"input": 1_000_000},
            "codex": {"totals": {"input": 0, "total": 0}},
            "cursor": {"totals": {"input": 0, "total": 0}},
        }),
        encoding="utf-8",
    )

    rc, url, err = final_report.write_final_report(tmp_path, comment_only=True)
    assert (rc, url, err) == (0, "", "")
    summary = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    # Token $5.80 → estimated $5.80/15 ≈ $0.39; TOTAL = 10.80 - 5.80 + 0.386... = 5.386... → $5.39
    assert "Claude/GLM-5.2 token $5.80 (estimated $0.39)" in summary
    assert "- **Main agent model**: glm-5.2[1m]" in summary
    assert "Claude (subprocess) $5.00" in summary
    assert "**Cost note**:" in summary
    # Subprocess not divided: estimated total uses full $5.00 sub + $0.39 main
    assert "TOTAL ~$5.39" in summary


def test_write_final_report_non_glm_keeps_plain_claude_segment(tmp_path: Path) -> None:
    _write_minimal_state(tmp_path)
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps({"model_roster": {"main": "claude-sonnet-4-6"}, "larch_version": "1.0.0"}),
        encoding="utf-8",
    )
    (run_dir / "token-report.json").write_text(
        json.dumps({
            "claude": {"totals": {"input": 1_000_000, "total": 1_000_000}},
            "BUCKETS_claude": {"input": 1_000_000},
        }),
        encoding="utf-8",
    )

    rc, url, err = final_report.write_final_report(tmp_path, comment_only=True)
    assert (rc, url, err) == (0, "", "")
    summary = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "Claude $3.00" in summary
    assert "Claude/GLM-5.2" not in summary
    assert "**Cost note**:" not in summary


def test_final_report_token_fields_cursor_lanes_require_valid_model_map(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    (run_dir / "token-report.json").write_text(
        json.dumps({
            "claude": {"totals": {"input": 1, "total": 1}},
            "BUCKETS_claude": {"input": 1},
            "BUCKETS_cursor": {"input": 300, "cache_read": 60, "output": 30},
            "BUCKETS_cursor_by_model": {
                "composer-2.5": {"input": 200, "cache_read": 40, "output": 20},
                "grok-4.5": {"input": 100, "cache_read": 20, "output": 10},
            },
        }),
        encoding="utf-8",
    )

    fields = final_report._final_report_token_fields(implement_tmpdir=tmp_path, run_id="run1")

    assert fields["cursor_composer_cost"] is not None
    assert fields["cursor_grok_cost"] is not None

    (run_dir / "token-report.json").write_text(
        json.dumps({
            "claude": {"totals": {"input": 1, "total": 1}},
            "BUCKETS_claude": {"input": 1},
            "BUCKETS_cursor": {"input": 300, "cache_read": 60, "output": 30},
            "BUCKETS_cursor_by_model": {"grok-4.5": "invalid"},
        }),
        encoding="utf-8",
    )

    fallback_fields = final_report._final_report_token_fields(implement_tmpdir=tmp_path, run_id="run1")

    assert fallback_fields["cursor_composer_cost"] is None
    assert fallback_fields["cursor_grok_cost"] is None

    (run_dir / "token-report.json").write_text(
        json.dumps({
            "claude": {"totals": {"input": 1, "total": 1}},
            "BUCKETS_claude": {"input": 1},
            "BUCKETS_cursor": {"input": 300, "cache_read": 60, "output": 30},
            "BUCKETS_cursor_by_model": "invalid",
        }),
        encoding="utf-8",
    )

    top_level_fallback_fields = final_report._final_report_token_fields(
        implement_tmpdir=tmp_path,
        run_id="run1",
    )

    assert top_level_fallback_fields["cursor_composer_cost"] is None
    assert top_level_fallback_fields["cursor_grok_cost"] is None


def test_final_report_token_fields_enriches_claude_sub_by_model_from_ledger(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps({"model_roster": {"main": "claude-sonnet-4-6"}}),
        encoding="utf-8",
    )
    (run_dir / "token-report.json").write_text(
        json.dumps({
            "claude": {"totals": {"input": 1_000_000, "total": 1_000_000}},
            "BUCKETS_claude": {"input": 1_000_000},
            "claude_sub": {"totals": {"input": 1_000_000, "total": 1_000_000}},
            "BUCKETS_claude_sub": {"input": 1_000_000},
        }),
        encoding="utf-8",
    )
    (run_dir / "larch-tokens-abc.jsonl").write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {"type": "mark", "step": "Step 5", "ts": "2026-06-25T00:00:00Z"},
                {
                    "type": "vendor",
                    "vendor": "claude_sub",
                    "input": 1_000_000,
                    "output": 0,
                    "total": 1_000_000,
                    "model": "claude-haiku-4-5",
                    "ts": "2026-06-25T00:00:01Z",
                },
            )
        )
        + "\n",
        encoding="utf-8",
    )

    fields = final_report._final_report_token_fields(implement_tmpdir=tmp_path, run_id="run1")

    assert fields["cost_unavailable"] is False
    assert fields["claude_sub_cost"] == "1.00"


def test_write_final_report_reconciles_step8_and_in_progress_for_pr_created(
    tmp_path: Path,
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    _write_minimal_state(tmp_path)
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "manifest.json").write_text(
        json.dumps({"schema_version": 2, "skill": "implement", "run_id": "run1", "status": "partial", "steps_ran": {"step8": False}}),
        encoding="utf-8",
    )

    _stub_cost_and_assessment(monkeypatch)
    rc, url, err = final_report.write_final_report(tmp_path)

    assert (rc, url, err) == (0, "", "")
    assert (run_dir / "final-summary.md").is_file()
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["steps_ran"]["step8"] is True
    assert manifest["status"] == config.MANIFEST_STATUS_IN_PROGRESS


def test_write_final_report_reconciles_step7a_true_from_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_minimal_state(tmp_path)
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "manifest.json").write_text(
        json.dumps({"schema_version": 2, "skill": "implement", "run_id": "run1", "status": "partial", "steps_ran": {"step7a": False}}),
        encoding="utf-8",
    )
    _ = (run_dir / "timing-report.json").write_text("{}", encoding="utf-8")

    _stub_cost_and_assessment(monkeypatch)
    rc, _url, err = final_report.write_final_report(tmp_path)

    assert (rc, err) == (0, "")
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["steps_ran"]["step7a"] is True


def test_write_final_report_shipping_sets_in_progress(
    tmp_path: Path,
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    # Pre-ship in-flight snapshot (no PR evidence, no bail reason) → "shipping"
    # outcome → manifest status promoted to in-progress.
    _write_minimal_state(tmp_path)
    _ = (tmp_path / "ship-pr-state.sh").write_text("PR_NUMBER=\nPR_URL=N/A\n", encoding="utf-8")
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "manifest.json").write_text(
        json.dumps({"schema_version": 2, "skill": "implement", "run_id": "run1", "status": "partial", "steps_ran": {"step8": False}}),
        encoding="utf-8",
    )

    _stub_cost_and_assessment(monkeypatch)
    rc, _url, err = final_report.write_final_report(tmp_path)

    assert rc == 0
    assert err == ""
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["steps_ran"]["step8"] is True
    assert manifest["status"] == config.MANIFEST_STATUS_IN_PROGRESS


def test_write_final_report_bailed_with_bail_reason_does_not_set_in_progress(
    tmp_path: Path,
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    # Genuine bail (bail reason present) keeps manifest status as partial.
    _write_minimal_state(tmp_path)
    _ = (tmp_path / "ship-pr-state.sh").write_text("PR_NUMBER=\nPR_URL=N/A\nBAIL_REASON=some-error\n", encoding="utf-8")
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "manifest.json").write_text(
        json.dumps({"schema_version": 2, "skill": "implement", "run_id": "run1", "status": "partial", "steps_ran": {"step8": False}}),
        encoding="utf-8",
    )

    _stub_cost_and_assessment(monkeypatch)
    rc, _url, err = final_report.write_final_report(tmp_path)

    assert rc == 0
    assert err == ""
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["steps_ran"]["step8"] is True
    assert manifest["status"] == config.MANIFEST_STATUS_PARTIAL


def test_write_final_report_skip_tracking_upsert_does_not_call_upsert(
    tmp_path: Path,
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    _write_minimal_state(tmp_path)
    _ = (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=1\nRUN_ID=run1\n", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="upsert failed")

    _stub_cost_and_assessment(monkeypatch)
    monkeypatch.setattr(final_report.subprocess, "run", fake_run)

    rc, url, err = final_report.write_final_report(tmp_path, skip_tracking_upsert=True)

    assert (rc, url, err) == (0, "", "")
    assert not any("tracking-issue" in call for call in calls)


def test_write_final_report_appends_exec_warning_detail_to_summary_and_run_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_minimal_state(tmp_path)
    _stub_cost_and_assessment(monkeypatch)
    (tmp_path / "execution-issues.md").write_text(
        "### Tool Failures\n- **step**: failed with suffix\n\n### Warnings\n- plain warning\n",
        encoding="utf-8",
    )

    rc, url, err = final_report.write_final_report(tmp_path, comment_only=False, skip_tracking_upsert=True)

    assert (rc, url, err) == (0, "", "")
    summary = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    run_summary = (tmp_path / "larch-logs" / "implement" / "run1" / "final-summary.md").read_text(encoding="utf-8")
    for body in (summary, run_summary):
        assert "<!-- larch:run-summary v=1 -->" in body
        assert "## Exec Issues and Warnings" in body
        assert body.index("## Exec Issues and Warnings") < body.index("<!-- larch:run-summary v=1 -->")
        assert "Exec Issues (1):" in body
        assert "step: failed with suffix" in body
        assert "Warnings (1):" in body
        assert "plain warning" in body


def test_write_final_report_ndjson_fallbacks_render_detail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_minimal_state(tmp_path)
    _stub_cost_and_assessment(monkeypatch)
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    (run_dir / "execution-issues.ndjson").write_text(
        json.dumps({"category": "Warnings", "body": "- **warn**: one\n- plain two\n"}) + "\n",
        encoding="utf-8",
    )

    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)

    assert (rc, err) == (0, "")
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "**Warnings**: 2" in body
    assert "Warnings (2):" in body
    assert "warn: one" in body
    assert "plain two" in body


def test_write_final_report_counts_committed_ndjson_and_live_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_minimal_state(tmp_path)
    _stub_cost_and_assessment(monkeypatch)
    (tmp_path / "execution-issues.md").write_text(
        "### Tool Failures\n- committed failure\n- post-flush failure\n### Warnings\n- live warning\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    (run_dir / "execution-issues.ndjson").write_text(
        json.dumps({"category": "Tool Failures", "body": "- committed failure\n"}) + "\n",
        encoding="utf-8",
    )

    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)

    assert (rc, err) == (0, "")
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "**Exec issues**: 2" in body
    assert "**Warnings**: 1" in body
    assert "committed failure" in body
    assert "post-flush failure" in body
    assert "live warning" in body


def test_write_final_report_legacy_string_count_header_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_minimal_state(tmp_path)
    _stub_cost_and_assessment(monkeypatch)
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    legacy = '{"category":"Tool Failures"}\n{"category":"External Reviewer Issues"}\n{"category":"Warnings"}'
    rows: list[object] = ["legacy", {"body": legacy}]
    (run_dir / "execution-issues.ndjson").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)

    assert (rc, err) == (0, "")
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "**Exec issues**: 2" in body
    assert "**Warnings**: 1" in body
    assert "Exec Issues (2):" in body
    assert "Warnings (1):" in body
    assert "  1." not in body


def test_write_final_report_exec_warning_detail_redacts_suffix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_minimal_state(tmp_path)
    _stub_cost_and_assessment(monkeypatch)
    raw_secret = "sk-" + "d" * 32
    (tmp_path / "execution-issues.md").write_text(
        f"### Warnings\n- **secret**: {raw_secret}\n",
        encoding="utf-8",
    )

    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)

    assert (rc, err) == (0, "")
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert raw_secret not in body
    assert "<REDACTED-TOKEN>" in body


def test_architectural_guidelines_section_absent_preserves_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(final_report, "_current_head_sha", lambda: "head")
    assert final_report._architectural_guidelines_section(tmp_path) == ""


def test_architectural_guidelines_section_consumable_redacted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = "sk-" + "A" * 24
    diff_text = "implementation diff"
    final_report.architectural_guidelines.write_staged_assessment(
        implement_tmpdir=tmp_path,
        assessment_text=f"note {token}\n",
        assessed_head_sha="old",
        diff_fingerprint_value=final_report.architectural_guidelines.diff_fingerprint(diff_text),
        base_ref="origin/main",
        diff_text=diff_text,
    )
    assert final_report.architectural_guidelines.pin_note_from_staged(
        tmp_path,
        head_sha="head",
        base_ref="origin/main",
    )
    monkeypatch.setattr(final_report, "_current_head_sha", lambda: "head")
    section = final_report._architectural_guidelines_section(tmp_path)
    assert "## Architectural guidelines" in section
    assert token not in section
    assert "<REDACTED-TOKEN>" in section


def test_architectural_guidelines_section_head_mismatch_skips_durable_note(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diff_text = "implementation diff"
    final_report.architectural_guidelines.write_staged_assessment(
        implement_tmpdir=tmp_path,
        assessment_text="note\n",
        assessed_head_sha="old",
        diff_fingerprint_value=final_report.architectural_guidelines.diff_fingerprint(diff_text),
        base_ref="origin/main",
        diff_text=diff_text,
    )
    assert final_report.architectural_guidelines.pin_note_from_staged(
        tmp_path,
        head_sha="other",
        base_ref="origin/main",
    )
    monkeypatch.setattr(final_report, "_current_head_sha", lambda: "head")
    section = final_report._architectural_guidelines_section(tmp_path)
    assert section == ""
    assert final_report.architectural_guidelines.read_dropped_note_notice(tmp_path) == ""


def test_architectural_guidelines_section_head_mismatch_ignores_drop_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diff_text = "implementation diff"
    final_report.architectural_guidelines.write_staged_assessment(
        implement_tmpdir=tmp_path,
        assessment_text="durable note\n",
        assessed_head_sha="old",
        diff_fingerprint_value=final_report.architectural_guidelines.diff_fingerprint(diff_text),
        base_ref="origin/main",
        diff_text=diff_text,
    )
    assert final_report.architectural_guidelines.pin_note_from_staged(
        tmp_path,
        head_sha="other",
        base_ref="origin/main",
    )
    (tmp_path / final_report.architectural_guidelines.DROPPED_NOTE_ARTIFACT).write_text(
        "old marker\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(final_report, "_current_head_sha", lambda: "head")

    section = final_report._architectural_guidelines_section(tmp_path)

    assert section == ""
    assert final_report.architectural_guidelines.read_dropped_note_notice(tmp_path) == "old marker"


def test_architectural_guidelines_section_symlinked_durable_note_skipped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(final_report, "_current_head_sha", lambda: "head")
    target = tmp_path / "target.md"
    target.write_text("note\n", encoding="utf-8")
    (tmp_path / final_report.architectural_guidelines.DURABLE_NOTE).symlink_to(target)
    (tmp_path / final_report.architectural_guidelines.DURABLE_NOTE_ENV).write_text(
        "STATUS=present\nHEAD_SHA=head\n",
        encoding="utf-8",
    )
    assert final_report._architectural_guidelines_section(tmp_path) == ""


def test_architectural_guidelines_section_ignores_persisted_drop_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(final_report, "_current_head_sha", lambda: "head")
    assert final_report.architectural_guidelines.persist_dropped_note_notice(tmp_path, notice_text="persisted notice\n")

    section = final_report._architectural_guidelines_section(tmp_path)

    assert section == ""


def test_architectural_guidelines_section_ignores_fingerprint_staleness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diff_text = "implementation diff"
    final_report.architectural_guidelines.write_staged_assessment(
        implement_tmpdir=tmp_path,
        assessment_text="note\n",
        assessed_head_sha="old",
        diff_fingerprint_value=final_report.architectural_guidelines.diff_fingerprint(diff_text),
        base_ref="origin/main",
        diff_text=diff_text,
    )
    assert final_report.architectural_guidelines.pin_note_from_staged(
        tmp_path,
        head_sha="head",
        base_ref="origin/main",
    )
    (tmp_path / final_report.architectural_guidelines.MATERIALIZED_DIFF).write_text("changed diff", encoding="utf-8")
    monkeypatch.setattr(final_report, "_current_head_sha", lambda: "head")

    section = final_report._architectural_guidelines_section(tmp_path)

    assert "note" in section
    assert final_report.architectural_guidelines.read_dropped_note_notice(tmp_path) == ""
    assert (tmp_path / final_report.architectural_guidelines.DURABLE_NOTE).exists()


def test_architectural_guidelines_section_happy_path_wins_over_drop_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diff_text = "implementation diff"
    final_report.architectural_guidelines.write_staged_assessment(
        implement_tmpdir=tmp_path,
        assessment_text="fresh note\n",
        assessed_head_sha="old",
        diff_fingerprint_value=final_report.architectural_guidelines.diff_fingerprint(diff_text),
        base_ref="origin/main",
        diff_text=diff_text,
    )
    assert final_report.architectural_guidelines.pin_note_from_staged(
        tmp_path,
        head_sha="head",
        base_ref="origin/main",
    )
    (tmp_path / final_report.architectural_guidelines.DROPPED_NOTE_ARTIFACT).write_text("old marker\n", encoding="utf-8")
    monkeypatch.setattr(final_report, "_current_head_sha", lambda: "head")

    section = final_report._architectural_guidelines_section(tmp_path)

    assert "fresh note" in section
    assert "old marker" not in section


def test_architectural_guidelines_section_current_note_ignores_stale_helpers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    final_report.architectural_guidelines.write_implement_note(
        implement_tmpdir=tmp_path,
        note_text="note\n",
        head_sha="head",
        metadata={
            "ASSESSED_HEAD_SHA": "old",
            "DIFF_FINGERPRINT": final_report.architectural_guidelines.diff_fingerprint("diff"),
        },
        base_ref="origin/main",
    )
    monkeypatch.setattr(final_report, "_current_head_sha", lambda: "head")

    def stale_fingerprint(
        _implement_tmpdir: Path,
        *,
        base_ref: str,
        repo_root: str | Path | None = None,
    ) -> bool:
        del base_ref, repo_root
        return True

    def fail_maybe_persist(
        _implement_tmpdir: Path,
        *,
        redact_fn: Callable[[str], str],
    ) -> bool:
        del redact_fn
        return False

    monkeypatch.setattr(final_report.architectural_guidelines, "note_fingerprint_stale", stale_fingerprint)
    monkeypatch.setattr(
        final_report.architectural_guidelines,
        "maybe_persist_dropped_note_before_invalidate",
        fail_maybe_persist,
    )

    assert "note" in final_report._architectural_guidelines_section(tmp_path)
    assert (tmp_path / final_report.architectural_guidelines.DURABLE_NOTE).exists()


def test_architectural_guidelines_section_current_note_does_not_invalidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_minimal_state(tmp_path)
    _stub_cost_and_assessment(monkeypatch)
    final_report.architectural_guidelines.write_implement_note(
        implement_tmpdir=tmp_path,
        note_text="note\n",
        head_sha="head",
        metadata={
            "ASSESSED_HEAD_SHA": "old",
            "DIFF_FINGERPRINT": final_report.architectural_guidelines.diff_fingerprint("diff"),
        },
        base_ref="origin/main",
    )
    monkeypatch.setattr(final_report, "_current_head_sha", lambda: "head")

    def stale_fingerprint(
        _implement_tmpdir: Path,
        *,
        base_ref: str,
        repo_root: str | Path | None = None,
    ) -> bool:
        del base_ref, repo_root
        return True

    monkeypatch.setattr(final_report.architectural_guidelines, "note_fingerprint_stale", stale_fingerprint)

    def fail_invalidate(_tmpdir: Path) -> None:
        raise OSError("blocked")

    monkeypatch.setattr(final_report.architectural_guidelines, "invalidate_implement_note", fail_invalidate)

    section = final_report._architectural_guidelines_section(tmp_path)
    assert "note" in section

    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)
    assert (rc, err) == (0, "")
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "note" in body
    assert body.index("## Architectural guidelines") < body.index("<!-- larch:run-summary v=1 -->")


def test_write_final_report_warn_count_dynamic_drop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_minimal_state(tmp_path)
    _stub_cost_and_assessment(monkeypatch)
    warning = (
        "- **code-review panel (round 1)**: dynamic reviewer slot drop/failure detected "
        "(failed=0, dropped=1, stragglers=1); review continued with the remaining panel output."
    )
    (tmp_path / "execution-issues.md").write_text(f"### Warnings\n{warning}\n", encoding="utf-8")

    _run_dir, _load_result, exec_count, warn_count = final_report._issue_load_result_for_run(
        implement_tmpdir=tmp_path,
        run_id="run1",
    )
    assert exec_count == 0
    assert warn_count == 1

    rc, url, err = final_report.write_final_report(tmp_path, comment_only=True, skip_tracking_upsert=True)
    assert (rc, url, err) == (0, "", "")
    summary = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "**Warnings**: 1" in summary
    assert "dynamic reviewer slot drop/failure" in summary


def test_write_final_report_warn_count_zero_for_static_straggler_suppression(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_minimal_state(tmp_path)
    _stub_cost_and_assessment(monkeypatch)
    (tmp_path / "execution-issues.md").write_text("### Warnings\n", encoding="utf-8")

    _run_dir, _load_result, exec_count, warn_count = final_report._issue_load_result_for_run(
        implement_tmpdir=tmp_path,
        run_id="run1",
    )
    assert (exec_count, warn_count) == (0, 0)

    rc, url, err = final_report.write_final_report(tmp_path, comment_only=True, skip_tracking_upsert=True)
    assert (rc, url, err) == (0, "", "")
    assert "**Warnings**: 0" in (tmp_path / "summary-final.md").read_text(encoding="utf-8")


def test_cursor_token_argv_splits_mixed_model_buckets() -> None:
    data: dict[str, object] = {
        "BUCKETS_cursor_by_model": {
            "grok-4.5": {"input": 1_000_000, "cache_read": 1_000_000, "output": 1_000_000},
            "composer-2.5": {"input": 1_000_000, "cache_read": 1_000_000, "output": 1_000_000},
        },
    }
    bucket: dict[str, object] = {
        "input": 2_000_000,
        "cache_read": 2_000_000,
        "output": 2_000_000,
    }

    argv = final_report._cursor_token_argv(data=data, bucket=bucket)
    cost = dict(
        line.split("=", 1)
        for line in final_report.report_tokens_cost.token_cost_from_args(argv).splitlines()
    )

    assert argv[argv.index("--cursor-grok-input-tokens") + 1] == "1000000"
    assert argv[argv.index("--cursor-input-tokens") + 1] == "1000000"
    assert cost["CURSOR_COST"] == "12.45"
    assert cost["CURSOR_TOKENS"] == "6000000"
    assert cost["CURSOR_COMPOSER_COST"] == "3.95"
    assert cost["CURSOR_GROK_COST"] == "8.50"
    assert "CURSOR_AUTO_COST" not in cost


def test_cursor_token_argv_aggregate_bucket_uses_composer_flags() -> None:
    bucket: dict[str, object] = {"input": 100, "cache_read": 20, "output": 10}

    argv = final_report._cursor_token_argv(data={}, bucket=bucket)

    assert argv == ["--cursor-tokens", "130"]
    assert "--cursor-grok-input-tokens" not in argv


def test_plan_coverage_summary_recovers_post_merge_stale_live_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "session-env.sh").write_text(
        f"REPO_ROOT={tmp_path}\n",
        encoding="utf-8",
    )
    (tmp_path / "post-merge-sentinel").write_text("", encoding="utf-8")

    def boom(*, tmpdir: Path, repo_root: Path, manifest_path: Path | None = None) -> None:
        _ = tmpdir, repo_root, manifest_path
        raise ShipError("coverage artifact does not match live repository inputs")

    monkeypatch.setattr(scope_disposition, "load_live_coverage", boom)
    monkeypatch.setattr(scope_disposition, "load_coverage", lambda _tmpdir: object())  # type: ignore[reportUnknownArgumentType]
    monkeypatch.setattr(
        scope_disposition,
        "load_disposition",
        lambda _tmpdir, *, coverage=None: None,  # type: ignore[reportUnknownArgumentType]  # noqa: ARG005
    )

    assert final_report._plan_coverage_summary_line(tmp_path) == ""


def test_plan_coverage_summary_propagates_non_mismatch_ship_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "session-env.sh").write_text(
        f"REPO_ROOT={tmp_path}\n",
        encoding="utf-8",
    )

    def boom(*, tmpdir: Path, repo_root: Path, manifest_path: Path | None = None) -> None:
        _ = tmpdir, repo_root, manifest_path
        raise ShipError("coverage artifact unreadable or malformed: bad json")

    monkeypatch.setattr(scope_disposition, "load_live_coverage", boom)

    with pytest.raises(ShipError, match="unreadable or malformed"):
        _ = final_report._plan_coverage_summary_line(tmp_path)


def test_write_final_report_omits_coverage_line_on_stale_mismatch_without_sentinel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stale post-merge coverage must not abort the final report (#6947).

    With no post-merge-sentinel, _plan_coverage_summary_line re-raises the
    stale-live mismatch; write_final_report degrades the optional coverage line
    to empty and still writes summary-final.md.
    """
    _write_minimal_state(tmp_path)
    (tmp_path / "session-env.sh").write_text(
        f"REPO=o/r\nMODE=N/A\nREPO_ROOT={tmp_path}\n",
        encoding="utf-8",
    )
    _stub_cost_and_assessment(monkeypatch)

    def boom(*, tmpdir: Path, repo_root: Path, manifest_path: Path | None = None) -> None:
        _ = tmpdir, repo_root, manifest_path
        raise ShipError("coverage artifact does not match live repository inputs")

    monkeypatch.setattr(scope_disposition, "load_live_coverage", boom)

    rc, url, err = final_report.write_final_report(tmp_path, comment_only=True)

    assert (rc, url, err) == (0, "", "")
    summary = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "## /implement run run1" in summary
    assert "**Plan coverage**" not in summary


def test_write_final_report_propagates_non_mismatch_coverage_ship_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Genuine coverage-integrity failures still fail the report loudly (#6947).

    Only the canonical stale-live mismatch degrades; a corrupt/unreadable
    coverage artifact must not be silently swallowed.
    """
    _write_minimal_state(tmp_path)
    (tmp_path / "session-env.sh").write_text(
        f"REPO=o/r\nMODE=N/A\nREPO_ROOT={tmp_path}\n",
        encoding="utf-8",
    )
    _stub_cost_and_assessment(monkeypatch)

    def boom(*, tmpdir: Path, repo_root: Path, manifest_path: Path | None = None) -> None:
        _ = tmpdir, repo_root, manifest_path
        raise ShipError("coverage artifact unreadable or malformed: bad json")

    monkeypatch.setattr(scope_disposition, "load_live_coverage", boom)

    with pytest.raises(ShipError, match="unreadable or malformed"):
        _ = final_report.write_final_report(tmp_path, comment_only=True)


def test_plan_coverage_summary_post_merge_stale_mismatch_requires_persisted_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "session-env.sh").write_text(
        f"REPO_ROOT={tmp_path}\n",
        encoding="utf-8",
    )
    (tmp_path / "post-merge-sentinel").write_text("", encoding="utf-8")

    def stale(*, tmpdir: Path, repo_root: Path, manifest_path: Path | None = None) -> None:
        _ = tmpdir, repo_root, manifest_path
        raise ShipError("coverage artifact does not match live repository inputs")

    monkeypatch.setattr(scope_disposition, "load_live_coverage", stale)
    monkeypatch.setattr(scope_disposition, "load_coverage", lambda _tmpdir: None)  # type: ignore[reportUnknownArgumentType]

    with pytest.raises(ShipError, match="coverage artifact does not match live repository inputs"):
        _ = final_report._plan_coverage_summary_line(tmp_path)


def test_plan_coverage_summary_stale_mismatch_propagates_invalid_persisted_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "session-env.sh").write_text(
        f"REPO_ROOT={tmp_path}\n",
        encoding="utf-8",
    )
    (tmp_path / "post-merge-sentinel").write_text("", encoding="utf-8")

    def stale(*, tmpdir: Path, repo_root: Path, manifest_path: Path | None = None) -> None:
        _ = tmpdir, repo_root, manifest_path
        raise ShipError("coverage artifact does not match live repository inputs")

    monkeypatch.setattr(scope_disposition, "load_live_coverage", stale)
    monkeypatch.setattr(
        scope_disposition,
        "load_coverage",
        lambda _tmpdir: (_ for _ in ()).throw(ShipError("coverage artifact unreadable or malformed")),  # type: ignore[reportUnknownArgumentType]
    )

    with pytest.raises(ShipError, match="unreadable or malformed"):
        _ = final_report._plan_coverage_summary_line(tmp_path)
