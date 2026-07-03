"""Tests for final_report.py extraction surface."""

# pyright: reportUnusedCallResult=false, reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownLambdaType=false


from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from larch.core import config
from larch.report import final_report

if TYPE_CHECKING:
    import pytest


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
    assert "No review rounds completed." not in summary
    assert "No reviewer timing tasks overlapped this round." not in summary
    assert "No reviewer timing tasks overlapped" not in summary


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
        assert "## Exec Issues and Warnings" in body
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


def test_write_final_report_counts_committed_ndjson_over_live_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_minimal_state(tmp_path)
    _stub_cost_and_assessment(monkeypatch)
    (tmp_path / "execution-issues.md").write_text("### Warnings\n- stale live warning\n", encoding="utf-8")
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    (run_dir / "execution-issues.ndjson").write_text(
        json.dumps({"category": "Tool Failures", "body": "- committed failure\n"}) + "\n",
        encoding="utf-8",
    )

    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)

    assert (rc, err) == (0, "")
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "**Exec issues**: 1" in body
    assert "**Warnings**: 0" in body
    assert "committed failure" in body
    assert "stale live warning" not in body


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


def test_architectural_guidelines_section_head_mismatch_renders_durable_note(
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
    assert "## Architectural guidelines" in section
    assert "note" in section
    assert final_report.architectural_guidelines.dropped_note_message() not in section
    assert final_report.architectural_guidelines.read_dropped_note_notice(tmp_path) == ""


def test_architectural_guidelines_section_head_mismatch_clears_stale_drop_marker(
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

    assert "durable note" in section
    assert "old marker" not in section
    assert final_report.architectural_guidelines.read_dropped_note_notice(tmp_path) == ""


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


def test_architectural_guidelines_section_reads_persisted_drop_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(final_report, "_current_head_sha", lambda: "head")
    assert final_report.architectural_guidelines.persist_dropped_note_notice(tmp_path, notice_text="persisted notice\n")

    section = final_report._architectural_guidelines_section(tmp_path)

    assert section == "## Architectural guidelines\n\npersisted notice\n"


def test_architectural_guidelines_section_stale_note_persists_then_invalidates(
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

    assert final_report.architectural_guidelines.dropped_note_message() in section
    assert (
        final_report.architectural_guidelines.read_dropped_note_notice(tmp_path)
        == final_report.architectural_guidelines.dropped_note_message()
    )
    assert not (tmp_path / final_report.architectural_guidelines.DURABLE_NOTE).exists()


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


def test_architectural_guidelines_section_persist_failure_on_stale_path_invalidates(
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

    assert final_report._architectural_guidelines_section(tmp_path) == ""
    assert not (tmp_path / final_report.architectural_guidelines.DURABLE_NOTE).exists()


def test_architectural_guidelines_section_invalidation_error_after_persist_still_renders(
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
    assert final_report.architectural_guidelines.dropped_note_message() in section

    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)
    assert (rc, err) == (0, "")
    assert final_report.architectural_guidelines.dropped_note_message() in (
        tmp_path / "summary-final.md"
    ).read_text(encoding="utf-8")


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
