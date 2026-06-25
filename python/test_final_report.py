"""Tests for final_report.py extraction surface."""

# pyright: reportUnusedCallResult=false, reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownLambdaType=false


from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

import config
import final_report

if TYPE_CHECKING:
    import pytest


def _write_minimal_state(tmp_path: Path) -> None:
    (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=0\nRUN_ID=run1\n", encoding="utf-8")
    (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")
    (tmp_path / "ship-pr-state.sh").write_text("PR_NUMBER=1\nPR_URL=https://github.com/o/r/pull/1\n", encoding="utf-8")
    (tmp_path / "finalize-state.sh").write_text("", encoding="utf-8")
    (tmp_path / "run-flags.sh").write_text("FORCE_REQUESTED=false\n", encoding="utf-8")


def _stub_cost_and_assessment(monkeypatch: Any) -> None:
    def fake_token_fields(_implement_tmpdir: Path, _run_id: str) -> dict[str, object]:
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
    assert final_report._refresh_issue_counts(tmp_path, "run1") == (0, 1)


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


def test_write_final_report_bailed_does_not_set_in_progress(
    tmp_path: Path,
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
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
        tmp_path,
        f"note {token}\n",
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


def test_architectural_guidelines_section_stale_or_symlink_skipped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diff_text = "implementation diff"
    final_report.architectural_guidelines.write_staged_assessment(
        tmp_path,
        "note\n",
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
    assert final_report._architectural_guidelines_section(tmp_path) == ""

    final_report.architectural_guidelines.invalidate_implement_note(tmp_path)
    target = tmp_path / "target.md"
    target.write_text("note\n", encoding="utf-8")
    (tmp_path / final_report.architectural_guidelines.DURABLE_NOTE).symlink_to(target)
    (tmp_path / final_report.architectural_guidelines.DURABLE_NOTE_ENV).write_text(
        "STATUS=present\nHEAD_SHA=head\n",
        encoding="utf-8",
    )
    assert final_report._architectural_guidelines_section(tmp_path) == ""
