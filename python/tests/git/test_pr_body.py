"""Tests for pr_body.py."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Self

import pytest

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from larch.core import config
from larch.report import final_report
from larch.git import pr_body
from larch.errors import ShipError
from larch.core.proc import CommandResult


def _no_issue_assess(
    _category: str,
    _details: tuple[final_report.exec_issue_detail.IssueDetail, ...],
) -> dict[str, str]:
    return {}


class _NoopRunner:
    def run(self, *args: object, **kwargs: object) -> CommandResult:  # pylint: disable=unused-argument
        return CommandResult((), 0, "", "", 0.0)


def test_py_cli_resolves_to_repo_python_cli() -> None:
    expected = Path(__file__).resolve().parents[2] / "cli.py"
    assert expected == pr_body._PY_CLI
    assert pr_body._PY_CLI.is_file()



def test_reconcile_manifest_for_terminal_report_marks_ndjson_only_step9a1_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-1"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "manifest.json").write_text('{"steps_ran":{}}\n', encoding="utf-8")
    _ = (run_dir / "oos-issues.ndjson").write_text('{"phase":"implement"}\n', encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> CommandResult:
        calls.append(argv)
        return CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(final_report.subprocess, "run", fake_run)
    rc, err = final_report._reconcile_manifest_for_terminal_report(tmp_path, run_id="run-1", outcome="bailed")
    assert (rc, err) == (0, "")
    flat = [arg for call in calls for arg in call]
    assert "steps_ran.step9a1=false" in flat


def test_reconcile_manifest_for_terminal_report_run_statistics_suppresses_step9a1_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-1"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "manifest.json").write_text('{"steps_ran":{}}\n', encoding="utf-8")
    _ = (run_dir / "run-statistics.md").write_text("Run run-1: 0 OOS issue(s) filed.\n", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> CommandResult:
        calls.append(argv)
        return CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(final_report.subprocess, "run", fake_run)
    rc, err = final_report._reconcile_manifest_for_terminal_report(tmp_path, run_id="run-1", outcome="bailed")
    assert (rc, err) == (0, "")
    flat = [arg for call in calls for arg in call]
    assert "steps_ran.step9a1=false" not in flat


def test_reconcile_manifest_for_terminal_report_marks_present_summary_and_pr_created_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-1"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "manifest.json").write_text('{"steps_ran":{}}\n', encoding="utf-8")
    _ = (run_dir / "final-summary.md").write_text("## /implement run run-1: pr-created\n", encoding="utf-8")
    _ = (tmp_path / "ship-pr-state.sh").write_text("PR_NUMBER=42\n", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> CommandResult:
        calls.append(argv)
        return CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(final_report.subprocess, "run", fake_run)
    rc, err = final_report._reconcile_manifest_for_terminal_report(tmp_path, run_id="run-1", outcome="pr-created")
    assert (rc, err) == (0, "")
    flat = [arg for call in calls for arg in call]
    assert "steps_ran.step8=true" in flat
    assert f"status={config.MANIFEST_STATUS_IN_PROGRESS}" in flat
    assert "pr_number=42" in flat

def test_sanitize_rejects_pipe_in_node() -> None:
    fragment = "flowchart LR\n  A[foo|bar] --> B\n"
    result = pr_body.sanitize_fragment(fragment)
    assert result.status == "rejected"
    assert config.MERMAID_REASON_PIPE_IN_NODE in result.reason_tokens


def test_sanitize_rejects_unclosed_frontmatter() -> None:
    fragment = "---\ntitle: x\nflowchart LR\n  A --> B\n"
    result = pr_body.sanitize_fragment(fragment)
    assert result.status == "rejected"
    assert config.MERMAID_REASON_UNCLOSED_FRONTMATTER in result.reason_tokens


def test_compose_summary_rejects_absolute_path_without_cwd() -> None:
    with pytest.raises(ShipError, match="escapes repo root"):
        _ = pr_body.compose_summary_bullets(
            _NoopRunner(),  # type: ignore[arg-type]
            plan_goals_file="/etc/passwd",
            cwd=None,
        )


def test_compose_summary_rejects_relative_path_without_cwd() -> None:
    with pytest.raises(ShipError, match="escapes repo root"):
        _ = pr_body.compose_summary_bullets(
            _NoopRunner(),  # type: ignore[arg-type]
            plan_goals_file="docs/plan.md",
            cwd=None,
        )


def test_compose_summary_from_plan(tmp_path: Path) -> None:
    goals = tmp_path / "goals.md"
    _ = goals.write_text("## Goal\n\nShip Phase 5 modules.\n", encoding="utf-8")
    summary = pr_body.compose_summary_bullets(
        _NoopRunner(),  # type: ignore[arg-type]
        plan_goals_file=str(goals),
        cwd=str(tmp_path),
    )
    assert "Ship Phase 5" in summary


def test_sanitize_fenced_mermaid_auto_extracts() -> None:
    fenced = "```mermaid\nflowchart LR\n  A --> B\n```\n"
    result = pr_body.sanitize_fragment(fenced)
    assert result.status == "ok"


def test_compose_pr_body_rejects_bad_mermaid() -> None:
    with pytest.raises(ShipError, match="mermaid fragment rejected"):
        _ = pr_body.compose_pr_body(
            summary="- x",
            mermaid="flowchart LR\n  A[bad|pipe] --> B\n",
        )


def test_compose_pr_body_rejects_bad_mermaid_in_summary() -> None:
    bad_summary = "- x\n\n```mermaid\nflowchart LR\n  A[bad|pipe] --> B\n```\n"
    with pytest.raises(ShipError, match="mermaid in PR body rejected"):
        _ = pr_body.compose_pr_body(summary=bad_summary)


def test_compose_pr_body_appends_closes() -> None:
    body = pr_body.compose_pr_body(summary="- x", issue_number=42)
    assert body.count("Closes #42") == 1


def test_compose_pr_body_routes_closes_through_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, int]] = []

    def fake_link(body: str, issue_number: int) -> str:
        calls.append((body, issue_number))
        return body.rstrip() + "\n\nCloses #42\n"

    monkeypatch.setattr(pr_body.tracking_issue, "link_pr_closes", fake_link)
    body = pr_body.compose_pr_body(summary="- x", issue_number=42)
    assert calls
    assert calls[0][1] == 42
    assert body.rstrip().endswith("Closes #42")


def test_compose_pr_body_appends_closes_when_mermaid_mentions_closes() -> None:
    body = pr_body.compose_pr_body(
        summary="- x",
        mermaid="flowchart LR\n  A[Closes #42] --> B\n",
        issue_number=42,
    )
    assert body.count("Closes #42") == 2
    assert body.rstrip().endswith("Closes #42")


def test_compose_pr_body_does_not_inject_oos_issue_urls() -> None:
    body = pr_body.compose_pr_body(summary="- Implement the requested change.")
    assert re.search(r"https://github\.com/[^/\s]+/[^/\s]+/issues/\d+", body) is None


def test_compose_pr_body_fail_closed_on_truncation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_redact(_text: str) -> str:
        return "body [content truncated — safety]"

    monkeypatch.setattr(pr_body.redact, "redact", fake_redact)
    with pytest.raises(ShipError, match="redaction failed"):
        _ = pr_body.compose_pr_body(summary="- x")


def test_redact_pr_body_delegates_to_redact() -> None:
    raw = "See /tmp/claude-implement-abc123/plan.txt now"
    out = pr_body.redact_pr_body(raw)
    assert "claude-implement-abc123" not in out
    assert out == pr_body.redact.redact(raw)


def test_redact_pr_body_fail_closed_on_truncation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_redact(_text: str) -> str:
        return "x [content truncated — safety]"

    monkeypatch.setattr(pr_body.redact, "redact", fake_redact)
    with pytest.raises(ShipError, match="redaction failed"):
        _ = pr_body.redact_pr_body("x")


def test_update_pr_body_rejects_unsafe_mermaid() -> None:
    bad = "```mermaid\nflowchart LR\n  A[x|y] --> B\n```\n"
    with pytest.raises(ShipError, match="mermaid in PR body rejected"):
        pr_body.update_pr_body(runner=_NoopRunner(), number=3, body=bad, repo="o/r")


def test_update_pr_body_invokes_gh() -> None:
    def new_calls() -> list[list[str]]:
        return []

    @dataclass
    class Runner:
        calls: list[list[str]] = field(default_factory=new_calls)

        def run(
            self,
            argv: Sequence[str],
            *,
            timeout: float | None = None,  # pylint: disable=unused-argument
            cwd: str | None = None,  # pylint: disable=unused-argument
            env: Mapping[str, str] | None = None,  # pylint: disable=unused-argument
            check: bool = False,  # pylint: disable=unused-argument
            stdout: int | None = None,  # pylint: disable=unused-argument
            stderr: int | None = None,  # pylint: disable=unused-argument
        ) -> CommandResult:
            self.calls.append(list(argv))
            return CommandResult(tuple(argv), 0, "", "", 0.0)

    runner = Runner()
    pr_body.update_pr_body(runner=runner, number=3, body="body", repo="o/r")  # type: ignore[arg-type]
    assert runner.calls
    assert runner.calls[0][1] == "pr"


def test_write_final_report_counts_warnings_and_exec(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _ = (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=0\nRUN_ID=run1\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")
    _ = (tmp_path / "ship-pr-state.sh").write_text("PR_NUMBER=1\nPR_URL=https://github.com/o/r/pull/1\n", encoding="utf-8")
    _ = (tmp_path / "run-flags.sh").write_text("FORCE_REQUESTED=false\n", encoding="utf-8")
    _ = (tmp_path / "execution-issues.md").write_text(
        "### Tool Failures\n- **step5**: failed\n\n### Warnings\n- **warn**: one\n",
        encoding="utf-8",
    )

    def fake_final_report_token_fields(implement_tmpdir: Path, run_id: str) -> dict[str, object]:
        _ = (implement_tmpdir, run_id)
        return {"cost_unavailable": True}

    monkeypatch.setattr(final_report, "_final_report_token_fields", fake_final_report_token_fields)
    monkeypatch.setattr(final_report.exec_issue_detail, "assess_issue_details", _no_issue_assess)
    rc, _url, _err = final_report.write_final_report(tmp_path, comment_only=True)
    assert rc == 0
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "**Exec issues**: 1" in body
    assert "**Warnings**: 1" in body


def test_write_final_report_renders_panel_failed_merge_downgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=0\nRUN_ID=run1\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")
    _ = (tmp_path / "ship-seed-input.env").write_text("MERGE=true\n", encoding="utf-8")
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "PR_NUMBER=12\nPR_URL=https://github.com/o/r/pull/12\nSTALL_TRACKING=false\nMERGE=false\nDRAFT=false\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "finalize-state.sh").write_text("", encoding="utf-8")
    _ = (tmp_path / "run-flags.sh").write_text("FORCE_REQUESTED=false\n", encoding="utf-8")
    _ = (tmp_path / "stall-recovery-classification.env").write_text(
        "STALL_STEP=5\nRESUME_HINT=step8-shippr\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "execution-issues.md").write_text("Step 5 — wrapper stalled: panel-failed\n", encoding="utf-8")

    def fake_final_report_token_fields(implement_tmpdir: Path, run_id: str) -> dict[str, object]:
        _ = (implement_tmpdir, run_id)
        return {"cost_unavailable": True}

    monkeypatch.setattr(final_report, "_final_report_token_fields", fake_final_report_token_fields)
    rc, _url, _err = final_report.write_final_report(tmp_path, comment_only=True)

    assert rc == 0
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "## /implement run run1: pr-created" in body
    assert "**⚠ Merge downgraded**" in body


def _write_minimal_final_report_state(tmp_path: Path, *, issue: str = "0", run_id: str = "run1") -> None:
    _ = (tmp_path / "parent-issue.md").write_text(f"ISSUE_NUMBER={issue}\nRUN_ID={run_id}\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")
    _ = (tmp_path / "ship-pr-state.sh").write_text("PR_NUMBER=1\nPR_URL=https://github.com/o/r/pull/1\n", encoding="utf-8")
    _ = (tmp_path / "finalize-state.sh").write_text("", encoding="utf-8")
    _ = (tmp_path / "run-flags.sh").write_text("FORCE_REQUESTED=false\n", encoding="utf-8")


def _stub_final_report_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_final_report_token_fields(implement_tmpdir: Path, run_id: str) -> dict[str, object]:
        _ = (implement_tmpdir, run_id)
        return {"cost_unavailable": True}

    monkeypatch.setattr(final_report, "_final_report_token_fields", fake_final_report_token_fields)
    monkeypatch.setattr(final_report.exec_issue_detail, "assess_issue_details", _no_issue_assess)


def test_write_final_report_appends_review_detail_in_comment_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_minimal_final_report_state(tmp_path)
    _stub_final_report_cost(monkeypatch)

    def fake_render_implement_review_detail(implement_tmpdir: Path, run_id: str) -> str:
        _ = (implement_tmpdir, run_id)
        return "## Review Phase Detail\nfrom helper\n"

    monkeypatch.setattr(final_report.review_phase_detail, "render_implement_review_detail", fake_render_implement_review_detail)

    rc, _url, _err = final_report.write_final_report(tmp_path, comment_only=True)

    assert rc == 0
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "## Review Phase Detail" in body
    assert not (tmp_path / "larch-logs" / "implement" / "run1" / "final-summary.md").exists()


def test_write_final_report_keeps_compact_summary_when_review_detail_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_minimal_final_report_state(tmp_path)
    _stub_final_report_cost(monkeypatch)

    def fake_render_implement_review_detail(implement_tmpdir: Path, run_id: str) -> str:
        _ = (implement_tmpdir, run_id)
        return ""

    monkeypatch.setattr(final_report.review_phase_detail, "render_implement_review_detail", fake_render_implement_review_detail)

    rc, _url, _err = final_report.write_final_report(tmp_path, comment_only=True)

    assert rc == 0
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "<!-- larch:run-summary v=1 -->" in body
    assert "## Review Phase Detail" not in body


def test_write_final_report_keeps_compact_summary_when_review_detail_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_minimal_final_report_state(tmp_path)
    _stub_final_report_cost(monkeypatch)

    def fake_render_implement_review_detail(implement_tmpdir: Path, run_id: str) -> str:
        _ = (implement_tmpdir, run_id)
        raise RuntimeError("renderer boom")

    monkeypatch.setattr(final_report.review_phase_detail, "render_implement_review_detail", fake_render_implement_review_detail)

    rc, _url, _err = final_report.write_final_report(tmp_path, comment_only=True)

    assert rc == 0
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "<!-- larch:run-summary v=1 -->" in body
    assert "## Review Phase Detail" not in body


def test_write_final_report_uses_run_log_root_for_review_detail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = "run-3794"
    _write_minimal_final_report_state(tmp_path, issue="42", run_id=run_id)
    _stub_final_report_cost(monkeypatch)
    run_dir = tmp_path / "larch-logs" / "implement" / run_id
    run_dir.mkdir(parents=True)
    stale_round = tmp_path / "round-1"
    stale_round.mkdir()
    _ = (stale_round / "round-meta.json").write_text(
        '{"tally":{"ACCEPTED_COUNT":"2","REJECTED_COUNT":"0","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"0","OOS_REJECTED_COUNT":"0"},"summary":{"panel":{"total_slot_count":2}}}\n',
        encoding="utf-8",
    )
    upsert_bodies: list[str] = []

    def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if "tracking-issue" in argv and "upsert-summary" in argv:
            content_file = Path(argv[argv.index("--content-file") + 1])
            upsert_bodies.append(content_file.read_text(encoding="utf-8"))
            return subprocess.CompletedProcess(argv, 0, stdout="COMMENT_URL=https://github.com/o/r/issues/42#issuecomment-1\n", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(final_report.subprocess, "run", fake_run)

    rc, _url, _err = final_report.write_final_report(tmp_path, comment_only=True)

    assert rc == 0
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "## Review Phase Detail" in body
    assert "No review rounds completed." in body
    assert "| 1 | 2 | 2 | 0 | 0 |" not in body
    assert upsert_bodies
    assert "No review rounds completed." in upsert_bodies[0]


def test_refresh_issue_counts_counts_plain_markdown_bullets(tmp_path: Path) -> None:
    _ = (tmp_path / "execution-issues.md").write_text(
        "### Tool Failures\n- a\n- b\n",
        encoding="utf-8",
    )

    assert final_report._refresh_issue_counts(implement_tmpdir=tmp_path, run_id="run1") == (2, 0)


def test_refresh_issue_counts_counts_structured_rows_per_bullet(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    rows = [
        {"category": "Tool Failures", "body": "- a\n- b\n"},
        {"category": "Warnings", "body": "- **step5**: c\n- **step5**: d\n"},
    ]
    _ = (run_dir / "execution-issues.ndjson").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    assert final_report._refresh_issue_counts(implement_tmpdir=tmp_path, run_id="run1") == (2, 2)


def test_refresh_issue_counts_structured_row_without_bullets_counts_once(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "execution-issues.ndjson").write_text(
        json.dumps({"category": "Tool Failures", "body": "plain row"}) + "\n",
        encoding="utf-8",
    )

    assert final_report._refresh_issue_counts(implement_tmpdir=tmp_path, run_id="run1") == (1, 0)


def test_refresh_issue_counts_ignores_fenced_diagnostic_bullets(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    row = {
        "category": "Tool Failures",
        "body": "```text\n- failed check\n```\n- real issue\n",
    }
    _ = (run_dir / "execution-issues.ndjson").write_text(json.dumps(row) + "\n", encoding="utf-8")

    assert final_report._refresh_issue_counts(implement_tmpdir=tmp_path, run_id="run1") == (1, 0)


def test_refresh_issue_counts_body_text_fallback_counts_plain_bullets(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    rows: list[object] = [
        "legacy row",
        {"body": "### Tool Failures\n- a\n- b\n"},
        {"body": "### Warnings\n- c\n"},
    ]
    _ = (run_dir / "execution-issues.ndjson").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    assert final_report._refresh_issue_counts(implement_tmpdir=tmp_path, run_id="run1") == (2, 1)


def test_issue_detail_body_text_fallback_lists_rows(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    rows: list[object] = [
        "legacy row",
        {"body": "### Tool Failures\n- a\n- b\n"},
        {"body": "### Warnings\n- c\n"},
    ]
    _ = (run_dir / "execution-issues.ndjson").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    result = final_report.exec_issue_detail.load_issue_detail_groups(tmp_path, run_dir=run_dir)
    block = final_report.exec_issue_detail.render_issue_detail_block(result, assess=False)

    assert final_report.exec_issue_detail.count_load_result(result) == (2, 1)
    assert "Exec Issues (2):" in block
    assert "1. a" in block
    assert "2. b" in block
    assert "Warnings (1):" in block
    assert "1. c" in block


def test_issue_detail_degraded_string_count_header_only(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    legacy = '{"category":"Tool Failures"}\n{"category":"External Reviewer Issues"}\n{"category":"Warnings"}'
    rows: list[object] = ["legacy row", {"body": legacy}]
    _ = (run_dir / "execution-issues.ndjson").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    result = final_report.exec_issue_detail.load_issue_detail_groups(tmp_path, run_dir=run_dir)
    block = final_report.exec_issue_detail.render_issue_detail_block(result, assess=False)

    assert result.listing_degraded
    assert final_report.exec_issue_detail.count_load_result(result) == (2, 1)
    assert "Exec Issues (2):" in block
    assert "Warnings (1):" in block
    assert "  1." not in block


def test_refresh_issue_counts_section_heading_inside_fence_is_boundary(tmp_path: Path) -> None:
    _ = (tmp_path / "execution-issues.md").write_text(
        "### Tool Failures\n- exec1\n```\nlog line\n### Warnings\n- warn1\n",
        encoding="utf-8",
    )

    assert final_report._refresh_issue_counts(implement_tmpdir=tmp_path, run_id="run1") == (1, 1)


def test_step18b_emits_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=1\nRUN_ID=run1\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")
    _ = (tmp_path / "ship-pr-state.sh").write_text("", encoding="utf-8")
    _ = (tmp_path / "run-flags.sh").write_text("FORCE_REQUESTED=false\n", encoding="utf-8")

    def fake_final_report_token_fields(implement_tmpdir: Path, run_id: str) -> dict[str, object]:
        _ = (implement_tmpdir, run_id)
        return {"cost_unavailable": True}

    def fake_write_final_report(implement_tmpdir: Path) -> tuple[int, str, str]:
        _ = implement_tmpdir
        _ = (tmp_path / "summary-final.md").write_text("# Summary\n", encoding="utf-8")
        return 0, "", ""

    monkeypatch.setattr(final_report, "_final_report_token_fields", fake_final_report_token_fields)
    monkeypatch.setattr(final_report, "write_final_report", fake_write_final_report)
    rc = final_report.step18b_final_report_main(["--implement-tmpdir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "EMIT_BODY=" in out
    assert "WFR_RC=" in out


def test_step18b_returns_write_failure_rc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=1\nRUN_ID=run1\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")

    monkeypatch.setattr(final_report, "write_final_report", lambda _tmpdir: (1, "", "write failed"))  # type: ignore[arg-type]
    rc = final_report.step18b_final_report_main(["--implement-tmpdir", str(tmp_path)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "WFR_RC=1" in out


def test_render_run_summary_includes_cost_line() -> None:
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="completed",
        run_id="run1",
        total_cost="1.00",
        claude_cost="0.50",
        codex_cost="0.25",
        cursor_cost="0.10",
        claude_sub_cost="0.15",
        total_tokens=1000,
        cost_unavailable=False,
    )
    assert "💰 TOTAL" in body
    assert "**Cost**:" in body
    # Legacy callers passing only codex_cost still render the split (5.5 slot + $0.00 mini).
    assert "Codex-5.5 $0.25" in body
    assert "Codex-mini $0.00" in body


def test_render_run_summary_splits_codex_by_model() -> None:
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="completed",
        run_id="run1",
        total_cost="1.00",
        claude_cost="0.50",
        codex_cost="0.40",
        codex_gpt_5_5_cost="0.10",
        codex_gpt_5_4_mini_cost="0.30",
        cursor_cost="0.10",
        claude_sub_cost="0.00",
        total_tokens=1000,
        cost_unavailable=False,
    )
    assert "Codex-5.5 $0.10" in body
    assert "Codex-mini $0.30" in body
    assert "Codex $" not in body  # the old single-Codex slot is gone


def test_render_run_summary_main_emits_codex_model_split(capsys: pytest.CaptureFixture[str]) -> None:
    rc = pr_body.render_run_summary_main([
        "--skill", "design", "--outcome", "approved", "--run-id", "r1",
        "--codex-input-tokens", "1000000", "--codex-output-tokens", "1000000",
        "--codex-mini-input-tokens", "1000000", "--codex-mini-output-tokens", "1000000",
        "--print-stdout",
    ])
    assert rc == 0
    body = capsys.readouterr().out
    assert "Codex-5.5 $" in body
    assert "Codex-mini $" in body


def test_render_run_summary_main_prices_claude_from_manifest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text('{"model_roster":{"main":"claude-sonnet-4-6"}}\n', encoding="utf-8")
    rc = pr_body.render_run_summary_main([
        "--skill", "implement", "--outcome", "completed", "--run-id", "r1",
        "--manifest-path", str(manifest),
        "--claude-input-tokens", "1000000",
        "--print-stdout",
    ])
    assert rc == 0
    body = capsys.readouterr().out
    assert "Claude $3.00" in body
    assert "- **Main agent model**: claude-sonnet-4-6" in body


def test_render_run_summary_main_main_model_override_wins_for_pricing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text('{"model_roster":{"main":"claude-sonnet-4-6"}}\n', encoding="utf-8")
    rc = pr_body.render_run_summary_main([
        "--skill", "implement", "--outcome", "completed", "--run-id", "r1",
        "--manifest-path", str(manifest),
        "--main-model", "claude-haiku-4-5",
        "--claude-input-tokens", "1000000",
        "--print-stdout",
    ])
    assert rc == 0
    body = capsys.readouterr().out
    assert "Claude $1.00" in body
    assert "- **Main agent model**: claude-haiku-4-5" in body


def test_render_run_summary_includes_merge_downgrade_warning() -> None:
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="pr-created",
        run_id="run1",
        pr_number="12",
        merge_downgraded="true",
        cost_unavailable=True,
    )

    assert "**⚠ Merge downgraded**" in body
    assert "panel-failed recovery shipped a PR without merging" in body


def test_render_run_summary_includes_dynamic_archetypes_line() -> None:
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="pr-created",
        run_id="run1",
        dynamic_archetypes_line="static-only, pre-scouted-empty",
        cost_unavailable=True,
    )
    assert "- **Dynamic archetypes**: static-only, pre-scouted-empty" in body


def test_final_report_dynamic_archetypes_line_ok_count(tmp_path: Path) -> None:
    _ = (tmp_path / "step2-scout-coder-status.env").write_text("SCOUT_CODER_STATUS=ok\n", encoding="utf-8")
    _ = (tmp_path / "step2-external-scout-eligible.txt").write_text("eligible\n", encoding="utf-8")
    _ = (tmp_path / "scout-coder-manifest.json").write_text(
        '{"archetypes":[{"name":"dyn-api","focus_area":"correctness","weight":1,"rationale":"API changed.","prompt_body":"Check API."}]}\n',
        encoding="utf-8",
    )
    assert final_report._dynamic_archetypes_line(tmp_path) == "ok (1)"  # pyright: ignore[reportPrivateUsage]


def test_final_report_dynamic_archetypes_line_stale_ok_is_invalid(tmp_path: Path) -> None:
    _ = (tmp_path / "step2-scout-coder-status.env").write_text("SCOUT_CODER_STATUS=ok\n", encoding="utf-8")
    assert final_report._dynamic_archetypes_line(tmp_path) == "static-only, producer missing-or-invalid"  # pyright: ignore[reportPrivateUsage]


def test_final_report_dynamic_archetypes_line_producer_empty_not_pre_scouted(tmp_path: Path) -> None:
    _ = (tmp_path / "step2-scout-coder-status.env").write_text("SCOUT_CODER_STATUS=ok\n", encoding="utf-8")
    _ = (tmp_path / "step2-external-scout-eligible.txt").write_text("eligible\n", encoding="utf-8")
    _ = (tmp_path / "scout-coder-manifest.json").write_text('{"archetypes":[]}\n', encoding="utf-8")
    assert final_report._dynamic_archetypes_line(tmp_path) == "static-only, producer empty"  # pyright: ignore[reportPrivateUsage]


def test_final_report_dynamic_archetypes_line_self_review_na(tmp_path: Path) -> None:
    _ = (tmp_path / "run-flags.sh").write_text("SELF_REVIEW_REQUESTED=true\n", encoding="utf-8")
    _ = (tmp_path / "step2-scout-coder-status.env").write_text("SCOUT_CODER_STATUS=ok\n", encoding="utf-8")
    _ = (tmp_path / "step2-external-scout-eligible.txt").write_text("eligible\n", encoding="utf-8")
    _ = (tmp_path / "scout-coder-manifest.json").write_text('{"archetypes":[]}\n', encoding="utf-8")
    assert final_report._dynamic_archetypes_line(tmp_path) == "N/A"  # pyright: ignore[reportPrivateUsage]


def test_final_report_dynamic_archetypes_line_round_pre_scouted_overrides_stale_sidecar(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    _ = (round_dir / "scout-round1-status.env").write_text("SCOUT_STATUS=pre-scouted\n", encoding="utf-8")
    _ = (round_dir / "scout-round1-manifest.json").write_text(
        '{"archetypes":[{"name":"dyn-api","focus_area":"correctness","weight":1,"rationale":"API changed.","prompt_body":"Check API."}]}\n',
        encoding="utf-8",
    )
    _ = (tmp_path / "step2-scout-coder-status.env").write_text("SCOUT_CODER_STATUS=missing-or-invalid\n", encoding="utf-8")
    assert final_report._dynamic_archetypes_line(tmp_path) == "ok (1)"  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--skill", "implement"],
        ["--skill", "bad", "--outcome", "x", "--run-id", "r"],
    ],
)
def test_render_run_summary_main_usage_errors(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    rc = pr_body.render_run_summary_main(argv)
    assert rc == 2
    captured = capsys.readouterr()
    assert "STATUS=ok" not in captured.err


def test_render_run_summary_main_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_file = tmp_path / "summary.md"
    rc = pr_body.render_run_summary_main([
        "--skill",
        "implement",
        "--outcome",
        "completed",
        "--run-id",
        "run-1",
        "--output-file",
        str(out_file),
        "--cost-unavailable",
    ])
    assert rc == 0
    captured = capsys.readouterr()
    assert "STATUS=ok" in captured.err
    assert f"OUTPUT_FILE={out_file}" in captured.err
    assert out_file.is_file()
    assert "run-1" in out_file.read_text(encoding="utf-8")


def test_render_run_summary_main_cost_unavailable(capsys: pytest.CaptureFixture[str]) -> None:
    rc = pr_body.render_run_summary_main([
        "--skill",
        "design",
        "--outcome",
        "completed",
        "--run-id",
        "run-2",
        "--print-stdout",
        "--cost-unavailable",
    ])
    assert rc == 0
    captured = capsys.readouterr()
    assert "STATUS=ok" in captured.err
    assert "run-2" in captured.out


class _SlackFakeResponse:
    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        _ = (exc_type, exc, traceback)


def _write_slack_issue_state(tmp_path: Path, issue_number: str = "9") -> None:
    _ = (tmp_path / "parent-issue.md").write_text(
        f"ISSUE_NUMBER={issue_number}\nRUN_ID=run-4\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "PR_URL=https://example.test/pr/1\nPR_TITLE=A PR\n",
        encoding="utf-8",
    )


def test_slack_issue_announce_webhook_unset_skips(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_slack_issue_state(tmp_path)
    monkeypatch.delenv("LARCH_SLACK_WEBHOOK_URL", raising=False)

    assert pr_body.slack_issue_announce(tmp_path) == (0, "skipped", "webhook-not-set")


@pytest.mark.parametrize("issue_number", ["", "0"])
def test_slack_issue_announce_issue_unset_skips(tmp_path: Path, issue_number: str) -> None:
    if issue_number:
        _write_slack_issue_state(tmp_path, issue_number=issue_number)

    assert pr_body.slack_issue_announce(tmp_path) == (0, "skipped", "issue-not-set")


def test_slack_issue_announce_nonnumeric_issue_fails(tmp_path: Path) -> None:
    _write_slack_issue_state(tmp_path, issue_number="abc")

    rc, status, reason = pr_body.slack_issue_announce(tmp_path)

    assert rc != 0
    assert status == "failed"
    assert reason == "ISSUE_NUMBER must be numeric"


def test_slack_issue_announce_nonnumeric_issue_best_effort_exits_zero(tmp_path: Path) -> None:
    _write_slack_issue_state(tmp_path, issue_number="abc")

    rc, status, reason = pr_body.slack_issue_announce(tmp_path, best_effort=True)

    assert rc == 0
    assert status == "failed"
    assert reason == "ISSUE_NUMBER must be numeric"


def test_slack_issue_announce_posts_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_slack_issue_state(tmp_path)
    monkeypatch.setenv("LARCH_SLACK_WEBHOOK_URL", "https://hooks.example.test")
    requests: list[pr_body.urllib.request.Request] = []

    def fake_urlopen(request: object, timeout: int = 0) -> _SlackFakeResponse:
        assert isinstance(request, pr_body.urllib.request.Request)
        assert timeout == 10
        requests.append(request)
        return _SlackFakeResponse()

    monkeypatch.setattr(pr_body.urllib.request, "urlopen", fake_urlopen)

    assert pr_body.slack_issue_announce(tmp_path) == (0, "posted", "")

    assert len(requests) == 1
    request = requests[0]
    assert request.get_method() == "POST"
    assert request.full_url == "https://hooks.example.test"
    assert request.get_header("Content-type") == "application/json"
    assert isinstance(request.data, bytes)
    body = json.loads(request.data.decode())
    assert "run-4" in body["text"]
    assert "https://example.test/pr/1" in body["text"]
    assert "#9" in body["text"]
    assert "A PR" in body["text"]


def test_slack_issue_announce_urlopen_failure_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_slack_issue_state(tmp_path)
    monkeypatch.setenv("LARCH_SLACK_WEBHOOK_URL", "https://hooks.example.test")

    def fake_urlopen(_request: object, timeout: int = 0) -> _SlackFakeResponse:
        _ = timeout
        raise OSError("network down")

    monkeypatch.setattr(pr_body.urllib.request, "urlopen", fake_urlopen)

    rc, status, reason = pr_body.slack_issue_announce(tmp_path)

    assert rc != 0
    assert status == "failed"
    assert reason == "network down"


def test_slack_issue_announce_urlopen_failure_best_effort_exits_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_slack_issue_state(tmp_path)
    monkeypatch.setenv("LARCH_SLACK_WEBHOOK_URL", "https://hooks.example.test")

    def fake_urlopen(_request: object, timeout: int = 0) -> _SlackFakeResponse:
        _ = timeout
        raise OSError("network down")

    monkeypatch.setattr(pr_body.urllib.request, "urlopen", fake_urlopen)

    rc, status, reason = pr_body.slack_issue_announce(tmp_path, best_effort=True)

    assert rc == 0
    assert status == "failed"
    assert reason == "network down"


def test_slack_issue_announce_invalid_webhook_scheme_does_not_call_urlopen(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_slack_issue_state(tmp_path)
    monkeypatch.setenv("LARCH_SLACK_WEBHOOK_URL", "ftp://hooks.example.test")

    def fake_urlopen(_request: object, timeout: int = 0) -> _SlackFakeResponse:
        _ = timeout
        pytest.fail("urlopen should not be called")

    monkeypatch.setattr(pr_body.urllib.request, "urlopen", fake_urlopen)

    rc, status, reason = pr_body.slack_issue_announce(tmp_path)

    assert rc != 0
    assert status == "failed"
    assert reason == "webhook scheme must be http or https"


def test_slack_issue_announce_main_posted_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_slack_issue_state(tmp_path)
    monkeypatch.setenv("LARCH_SLACK_WEBHOOK_URL", "https://hooks.example.test")

    def fake_urlopen(_request: object, timeout: int = 0) -> _SlackFakeResponse:
        _ = timeout
        return _SlackFakeResponse()

    monkeypatch.setattr(pr_body.urllib.request, "urlopen", fake_urlopen)

    rc = pr_body.slack_issue_announce_main(["--implement-tmpdir", str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 0
    assert captured.out.splitlines() == ["STATUS=posted"]


def test_slack_issue_announce_main_skipped_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_slack_issue_state(tmp_path)
    monkeypatch.delenv("LARCH_SLACK_WEBHOOK_URL", raising=False)

    rc = pr_body.slack_issue_announce_main(["--implement-tmpdir", str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 0
    assert captured.out.splitlines() == ["STATUS=skipped", "REASON=webhook-not-set"]


def test_slack_issue_announce_main_failed_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_slack_issue_state(tmp_path)
    monkeypatch.setenv("LARCH_SLACK_WEBHOOK_URL", "ftp://hooks.example.test")

    rc = pr_body.slack_issue_announce_main(["--implement-tmpdir", str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 1
    assert captured.out.splitlines() == [
        "STATUS=failed",
        "ERROR=webhook scheme must be http or https",
    ]


def test_slack_issue_announce_main_normalizes_multiline_transport_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_slack_issue_state(tmp_path)
    monkeypatch.setenv("LARCH_SLACK_WEBHOOK_URL", "https://hooks.example.test")

    def fake_urlopen(_request: object, timeout: int = 0) -> _SlackFakeResponse:
        _ = timeout
        raise OSError("first\nsecond\rthird")

    monkeypatch.setattr(pr_body.urllib.request, "urlopen", fake_urlopen)

    rc = pr_body.slack_issue_announce_main(["--implement-tmpdir", str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 1
    assert captured.out.splitlines() == ["STATUS=failed", "ERROR=first second third"]


def test_slack_issue_announce_main_missing_tmpdir_arg_emits_envelope(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = pr_body.slack_issue_announce_main([])
    captured = capsys.readouterr()

    assert rc == 2
    assert captured.out.splitlines() == [
        "STATUS=failed",
        "ERROR=--implement-tmpdir is required",
    ]
    assert "usage:" not in captured.out


def test_slack_issue_announce_main_nonexistent_tmpdir_emits_envelope(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = pr_body.slack_issue_announce_main(["--implement-tmpdir", str(tmp_path / "missing")])
    captured = capsys.readouterr()

    assert rc == 2
    assert captured.out.splitlines() == [
        "STATUS=failed",
        "ERROR=--implement-tmpdir not found",
    ]
    assert "STATUS=skipped" not in captured.out
    assert "REASON=issue-not-set" not in captured.out


def test_post_tracking_issue_writes_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _ = (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=42\nRUN_ID=run-z\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=o/r\nAGENT=claude\nCODER=claude\n", encoding="utf-8")
    _ = (tmp_path / "run-flags.sh").write_text("FORCE_REQUESTED=false\n", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> object:
        _ = kwargs
        calls.append(cmd)

        class Result:
            returncode = 0
            stdout = "LARCH_PLUGIN_VERSION=99.0.0\n" if cmd[2:4] == ["plugin", "read-version"] else "COMMENT_URL=https://github.com/o/r/issues/42#issuecomment-1\n"
            stderr = ""
        return Result()

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)
    rc, posted, url, err = pr_body.post_tracking_issue(tmp_path)
    assert rc == 0
    assert posted is True
    assert "issues/42" in url
    assert (tmp_path / "summary-metadata.md").is_file()
    assert err == ""
    assert [cmd[1] for cmd in calls] == [str(pr_body._PY_CLI), str(pr_body._PY_CLI)]


def test_post_tracking_issue_warns_plugin_read_version_nonzero_on_stderr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _ = (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=42\nRUN_ID=run-z\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=o/r\nAGENT=claude\nCODER=claude\n", encoding="utf-8")
    _ = (tmp_path / "run-flags.sh").write_text("FORCE_REQUESTED=false\n", encoding="utf-8")

    def fake_run(cmd: list[str], **kwargs: object) -> object:
        _ = kwargs

        class Result:
            returncode = 7 if cmd[2:4] == ["plugin", "read-version"] else 0
            stdout = "" if cmd[2:4] == ["plugin", "read-version"] else "COMMENT_URL=https://github.com/o/r/issues/42#issuecomment-1\n"
            stderr = "read failed" if cmd[2:4] == ["plugin", "read-version"] else ""
        return Result()

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)
    rc, posted, _url, err = pr_body.post_tracking_issue(tmp_path)
    captured = capsys.readouterr()

    assert rc == 0
    assert posted is True
    assert err == ""
    assert "pr_body: plugin read-version failed rc=7" in captured.err
    assert "pr_body: plugin read-version" not in captured.out


def test_diagram_failure_capture_redacts_prefixed_mermaid_on_stderr_line() -> None:
    diagnostic, tail = pr_body._diagram_failure_capture(returncode=1, stderr="ERROR graph TD A-->B")
    assert "graph TD" not in tail
    assert "A-->B" not in tail
    assert "diagram-content-redacted" in tail
    assert "graph TD" not in diagnostic
    assert "A-->B" not in diagnostic


def test_generate_code_flow_diagram_uses_launcher_not_stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    launcher = tmp_path / "fake-launcher.sh"
    _ = launcher.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    launcher.chmod(0o755)
    monkeypatch.setenv("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS", str(launcher))
    raw_secret = "sk-abcdefghijklmnopqrstuvwxyz123456"
    raw_stderr = f"timeout after 600s token={raw_secret}"

    def fake_run(*_args: object, **_kwargs: object) -> object:
        return type("R", (), {"returncode": 1, "stdout": "stdout diagnostic\n## Code Flow Diagram\n```mermaid\ngraph TD\nA-->B\n```", "stderr": raw_stderr})()

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)
    rc, status, _diagram, reason = pr_body.generate_code_flow_diagram(tmp_path)
    assert rc == 1
    assert status == "failed"
    assert reason != "generation-failed"
    assert "generation-failed rc=1" in reason
    assert "tail=" in reason
    assert "timeout after 600s" in reason
    assert raw_secret not in reason
    failure_log = tmp_path / "code-flow-diagram.failure.log"
    assert failure_log.is_file()
    log_text = failure_log.read_text(encoding="utf-8")
    assert "exit-code=1" in log_text
    assert "timeout after 600s" in log_text
    assert "stdout diagnostic" in log_text
    assert "```" not in log_text
    assert "mermaid" not in log_text.lower()
    assert "A-->B" not in log_text
    assert raw_secret not in log_text
    assert not (tmp_path / "code-flow-diagram.raw-failure.log").exists()
    assert (tmp_path / "code-flow-prompt.md").is_file()


def test_generate_code_flow_diagram_labels_launcher_failure_class(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = tmp_path / "fake-launcher.sh"
    _ = launcher.write_text("#!/bin/sh\nexit 124\n", encoding="utf-8")
    launcher.chmod(0o755)
    monkeypatch.setenv("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS", str(launcher))
    monkeypatch.setattr(pr_body.time, "sleep", lambda _: None)  # type: ignore[arg-type]

    def fake_run(*_args: object, **_kwargs: object) -> object:
        return subprocess.CompletedProcess(
            [],
            config.EXIT_TIMEOUT,
            stdout="STATUS=TIMEOUT\nLAUNCHER_FAILURE_CLASS=health\nLAUNCHER_FAILURE_REASON=auth\n",
            stderr="claude subprocess timed out\n",
        )

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)
    rc, status, _diagram, reason = pr_body.generate_code_flow_diagram(tmp_path)

    assert rc == 1
    assert status == "failed"
    assert "generation-failed health/auth rc=124" in reason
    assert "tail=" in reason


def test_generate_code_flow_diagram_uses_py_cli_launcher(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS", raising=False)
    launch_argv: list[str] = []

    def fake_run(argv: list[str], **kwargs: object) -> object:
        _ = kwargs
        if argv[:2] == ["git", "merge-base"]:
            return subprocess.CompletedProcess(argv, 0, stdout="abc123\n", stderr="")
        if argv[:3] == ["git", "diff", "--name-only"]:
            return subprocess.CompletedProcess(argv, 0, stdout="python/larch/git/pr_body.py\n", stderr="")
        if argv[2:4] == ["agent", "launch-claude-subprocess"]:
            launch_argv.extend(argv)
            output_file = Path(argv[argv.index("--output-file") + 1])
            _ = output_file.write_text(
                "## Code Flow Diagram\n\n```mermaid\nflowchart LR\n  A --> B\n```\n",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unexpected argv")

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)
    rc, status, diagram, reason = pr_body.generate_code_flow_diagram(tmp_path)

    assert rc == 0
    assert status == "ok"
    assert diagram
    assert reason == ""
    assert launch_argv[1] == str(pr_body._PY_CLI)
    assert launch_argv[2:4] == ["agent", "launch-claude-subprocess"]
    timeout_idx = launch_argv.index("--timeout")
    assert launch_argv[timeout_idx + 1] == str(pr_body._CODE_FLOW_DIAGRAM_TIMEOUT_SECONDS)
    assert launch_argv[timeout_idx + 1] != "600"


def test_generate_code_flow_diagram_retries_on_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS", raising=False)
    monkeypatch.setattr(pr_body.time, "sleep", lambda _: None)  # type: ignore[arg-type]
    call_count = 0

    def fake_run(argv: list[str], **kwargs: object) -> object:
        nonlocal call_count
        _ = kwargs
        if argv[:2] == ["git", "merge-base"]:
            return subprocess.CompletedProcess(argv, 0, stdout="abc123\n", stderr="")
        if argv[:3] == ["git", "diff", "--name-only"] or argv[:3] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(argv, 0, stdout="file.py\n", stderr="")
        if argv[2:4] == ["agent", "launch-claude-subprocess"]:
            call_count += 1
            output_file = Path(argv[argv.index("--output-file") + 1])
            if call_count == 1:
                # First attempt: timeout — write empty file, return EXIT_TIMEOUT
                _ = output_file.write_text("", encoding="utf-8")
                return subprocess.CompletedProcess(argv, config.EXIT_TIMEOUT, stdout="", stderr="")
            # Second attempt (first retry): success
            _ = output_file.write_text(
                "## Code Flow Diagram\n\n```mermaid\nflowchart LR\n  A --> B\n```\n",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unexpected")

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)  # type: ignore[arg-type]
    rc, status, diagram, reason = pr_body.generate_code_flow_diagram(tmp_path)

    assert call_count == 2, "should succeed on first retry"
    assert rc == 0
    assert status == "ok"
    assert diagram
    assert reason == ""
    assert (tmp_path / "code-flow-diagram.retried").is_file()
    retried_text = (tmp_path / "code-flow-diagram.retried").read_text(encoding="utf-8")
    assert f"FIRST_RC={config.EXIT_TIMEOUT}" in retried_text
    assert "RETRY_1_RC=0" in retried_text
    assert "RETRIES=1" in retried_text


def test_generate_code_flow_diagram_retries_on_empty_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS", raising=False)
    monkeypatch.setattr(pr_body.time, "sleep", lambda _: None)  # type: ignore[arg-type]
    call_count = 0

    def fake_run(argv: list[str], **kwargs: object) -> object:
        nonlocal call_count
        _ = kwargs
        if argv[:2] == ["git", "merge-base"]:
            return subprocess.CompletedProcess(argv, 0, stdout="abc123\n", stderr="")
        if argv[:3] == ["git", "diff", "--name-only"] or argv[:3] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(argv, 0, stdout="file.py\n", stderr="")
        if argv[2:4] == ["agent", "launch-claude-subprocess"]:
            call_count += 1
            output_file = Path(argv[argv.index("--output-file") + 1])
            if call_count == 1:
                # First attempt: launcher ran but produced empty output (No messages)
                _ = output_file.write_text("", encoding="utf-8")
                return subprocess.CompletedProcess(argv, 1, stdout="", stderr="")
            # Second attempt (first retry): success
            _ = output_file.write_text(
                "## Code Flow Diagram\n\n```mermaid\nflowchart LR\n  A --> B\n```\n",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unexpected")

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)  # type: ignore[arg-type]
    rc, status, _diagram, reason = pr_body.generate_code_flow_diagram(tmp_path)

    assert call_count == 2, "should succeed on first retry"
    assert rc == 0
    assert status == "ok"
    assert reason == ""
    assert (tmp_path / "code-flow-diagram.retried").is_file()


def test_generate_code_flow_diagram_no_retry_on_hard_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS", raising=False)
    call_count = 0

    def fake_run(argv: list[str], **kwargs: object) -> object:
        nonlocal call_count
        _ = kwargs
        if argv[:2] == ["git", "merge-base"]:
            return subprocess.CompletedProcess(argv, 0, stdout="abc123\n", stderr="")
        if argv[:3] == ["git", "diff", "--name-only"] or argv[:3] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(argv, 0, stdout="file.py\n", stderr="")
        if argv[2:4] == ["agent", "launch-claude-subprocess"]:
            call_count += 1
            # Hard failure: exit 1, no output file written
            return subprocess.CompletedProcess(argv, 1, stdout="launcher-init-failed", stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unexpected")

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)  # type: ignore[arg-type]
    rc, status, _diagram, _reason = pr_body.generate_code_flow_diagram(tmp_path)

    assert call_count == 1, "should NOT retry when output file is absent"
    assert rc == 1
    assert status == "failed"
    assert not (tmp_path / "code-flow-diagram.retried").is_file()


def test_generate_code_flow_diagram_retries_up_to_max_on_persistent_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS", raising=False)
    monkeypatch.setattr(pr_body.time, "sleep", lambda _: None)  # type: ignore[arg-type]
    call_count = 0

    def fake_run(argv: list[str], **kwargs: object) -> object:
        nonlocal call_count
        _ = kwargs
        if argv[:2] == ["git", "merge-base"]:
            return subprocess.CompletedProcess(argv, 0, stdout="abc123\n", stderr="")
        if argv[:3] == ["git", "diff", "--name-only"] or argv[:3] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(argv, 0, stdout="file.py\n", stderr="")
        if argv[2:4] == ["agent", "launch-claude-subprocess"]:
            call_count += 1
            output_file = Path(argv[argv.index("--output-file") + 1])
            # Always fail with empty output (triggers retry)
            _ = output_file.write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(argv, config.EXIT_TIMEOUT, stdout="", stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unexpected")

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)  # type: ignore[arg-type]
    rc, status, _diagram, _reason = pr_body.generate_code_flow_diagram(tmp_path)

    expected_calls = 1 + pr_body._MAX_DIAGRAM_RETRIES
    assert call_count == expected_calls, f"should attempt {expected_calls} times total"
    assert rc == 1
    assert status == "failed"
    assert (tmp_path / "code-flow-diagram.retried").is_file()
    retried_text = (tmp_path / "code-flow-diagram.retried").read_text(encoding="utf-8")
    assert f"FIRST_RC={config.EXIT_TIMEOUT}" in retried_text
    assert f"RETRIES={pr_body._MAX_DIAGRAM_RETRIES}" in retried_text


def test_generate_code_flow_diagram_reads_stderr_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS", raising=False)

    auth_message = "takes precedence over your claude.ai login"
    raw_path = tmp_path / "code-flow-diagram.raw.md"

    def fake_run(argv: list[str], **kwargs: object) -> object:
        _ = kwargs
        if argv[:2] == ["git", "merge-base"]:
            return subprocess.CompletedProcess(argv, 0, stdout="abc123\n", stderr="")
        if argv[:3] == ["git", "diff", "--name-only"] or argv[:3] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(argv, 0, stdout="file.py\n", stderr="")
        if argv[2:4] == ["agent", "launch-claude-subprocess"]:
            # Write the .stderr sidecar as the real launcher would, leave stdout empty
            _ = raw_path.with_suffix(raw_path.suffix + ".stderr").write_text(auth_message + "\n", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 1, stdout="launcher-init-failed", stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unexpected")

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)  # type: ignore[arg-type]
    rc, status, _diagram, reason = pr_body.generate_code_flow_diagram(tmp_path)

    assert rc == 1
    assert status == "failed"
    # Sidecar content must appear in the reason; completed.stderr was empty so
    # without Fix 1 the tail would be "no-output" instead.
    assert "claude.ai login" in reason


def test_derive_oos_fields_reads_json_body_filed_url(tmp_path: Path) -> None:
    body = "- **Filed URL**: https://github.com/acme/repo/issues/123\nnext line\n"
    _ = (tmp_path / "oos-issues.ndjson").write_text(
        json.dumps({"body": body}) + "\n",
        encoding="utf-8",
    )

    count, urls = final_report._derive_oos_fields(tmp_path)

    assert count == "1"
    assert urls == "https://github.com/acme/repo/issues/123"
    assert not urls.endswith("/i")


def _write_tally(run_dir: Path, filename: str, payload: object) -> None:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    _ = (run_dir / filename).write_text(text, encoding="utf-8")


def _write_findings(run_dir: Path, records: list[object]) -> None:
    _ = (run_dir / "review-findings-full.jsonl").write_text(
        "".join((record if isinstance(record, str) else json.dumps(record)) + "\n" for record in records),
        encoding="utf-8",
    )


def test_derive_review_line_absent_tally_returns_na(tmp_path: Path) -> None:
    assert final_report._derive_review_line(run_dir=tmp_path, filename="code-review-tally.json") == "N/A"


def test_derive_review_line_absent_tally_uses_findings_counts(tmp_path: Path) -> None:
    _write_findings(
        tmp_path,
        [
            {"id": "FINDING_1", "phase": "code-review", "outcome": "accepted"},
            {"id": "FINDING_2", "phase": "code-review", "outcome": "rejected"},
        ],
    )

    assert final_report._derive_review_line(run_dir=tmp_path, filename="code-review-tally.json") == "1/2 accepted"


def test_derive_review_line_absent_tally_uses_self_review_findings_counts(tmp_path: Path) -> None:
    _write_findings(
        tmp_path,
        [
            {"schema_version": "2", "id": "SELF_REVIEW_ACCEPTED_1", "phase": "code-review", "outcome": "accepted", "round_num": "1"},
            {"schema_version": "2", "id": "SELF_REVIEW_REJECTED_1", "phase": "code-review", "outcome": "rejected", "round_num": "1"},
            {"schema_version": "2", "id": "SELF_REVIEW_REJECTED_2", "phase": "code-review", "outcome": "rejected", "round_num": "1"},
        ],
    )

    assert final_report._derive_review_line(run_dir=tmp_path, filename="code-review-tally.json") == "1/3 accepted"


def test_derive_review_line_absent_tally_zero_code_review_records_returns_zero_findings(tmp_path: Path) -> None:
    _write_findings(tmp_path, [{"id": "FINDING_1", "phase": "code-review", "outcome": "neutral"}])

    assert final_report._derive_review_line(run_dir=tmp_path, filename="code-review-tally.json") == "0 findings"


def test_derive_review_line_absent_tally_empty_findings_returns_na(tmp_path: Path) -> None:
    _write_findings(tmp_path, [])

    assert final_report._derive_review_line(run_dir=tmp_path, filename="code-review-tally.json") == "N/A"


def test_derive_review_line_existing_tally_wins_over_findings(tmp_path: Path) -> None:
    _write_tally(tmp_path, "code-review-tally.json", {"phase": "code-review", "mode": "hard", "accepted_count": 2, "rejected_count": 0})
    _write_findings(tmp_path, [{"id": "FINDING_1", "phase": "code-review", "outcome": "rejected"}])

    assert final_report._derive_review_line(run_dir=tmp_path, filename="code-review-tally.json") == "2/2 accepted"


def test_derive_review_line_plan_review_does_not_use_findings_fallback(tmp_path: Path) -> None:
    _write_findings(tmp_path, [{"id": "FINDING_1", "phase": "code-review", "outcome": "accepted"}])

    assert final_report._derive_review_line(run_dir=tmp_path, filename="plan-review-tally.json") == "N/A"


def test_derive_review_line_malformed_tally_returns_na(tmp_path: Path) -> None:
    _write_tally(tmp_path, "code-review-tally.json", "{not valid json")
    assert final_report._derive_review_line(run_dir=tmp_path, filename="code-review-tally.json") == "N/A"


def test_derive_review_line_non_object_json_returns_na(tmp_path: Path) -> None:
    _write_tally(tmp_path, "code-review-tally.json", "[1, 2, 3]")
    assert final_report._derive_review_line(run_dir=tmp_path, filename="code-review-tally.json") == "N/A"


def test_derive_review_line_invalid_counts_return_na(tmp_path: Path) -> None:
    _write_tally(tmp_path, "code-review-tally.json", {"phase": "code-review", "accepted_count": "abc", "rejected_count": 0})
    assert final_report._derive_review_line(run_dir=tmp_path, filename="code-review-tally.json") == "N/A"


def test_derive_review_line_negative_counts_return_na(tmp_path: Path) -> None:
    _write_tally(tmp_path, "code-review-tally.json", {"phase": "code-review", "accepted_count": -1, "rejected_count": 0})
    assert final_report._derive_review_line(run_dir=tmp_path, filename="code-review-tally.json") == "N/A"


def test_derive_review_line_self_review_zero_findings(tmp_path: Path) -> None:
    _write_tally(
        tmp_path,
        "code-review-tally.json",
        {"phase": "code-review", "batch": "code-review-tally", "mode": "self-review", "accepted_count": 0, "rejected_count": 0},
    )
    assert final_report._derive_review_line(run_dir=tmp_path, filename="code-review-tally.json") == "self-review: 0 findings"


def test_derive_review_line_code_review_zero_findings(tmp_path: Path) -> None:
    _write_tally(tmp_path, "code-review-tally.json", {"phase": "code-review", "mode": "hard", "accepted_count": 0, "rejected_count": 0})
    assert final_report._derive_review_line(run_dir=tmp_path, filename="code-review-tally.json") == "0 findings"


def test_derive_review_line_plan_review_zero_stays_na(tmp_path: Path) -> None:
    _write_tally(tmp_path, "plan-review-tally.json", {"phase": "plan-review", "mode": "hard", "accepted_count": 0, "rejected_count": 0})
    assert final_report._derive_review_line(run_dir=tmp_path, filename="plan-review-tally.json") == "N/A"


def test_derive_review_line_non_code_review_phase_zero_stays_na(tmp_path: Path) -> None:
    _write_tally(tmp_path, "plan-review-tally.json", {"phase": "design-review", "accepted_count": 0, "rejected_count": 0})
    assert final_report._derive_review_line(run_dir=tmp_path, filename="plan-review-tally.json") == "N/A"


def test_derive_review_line_positive_counts(tmp_path: Path) -> None:
    _write_tally(tmp_path, "code-review-tally.json", {"phase": "code-review", "mode": "hard", "accepted_count": 2, "rejected_count": 3})
    assert final_report._derive_review_line(run_dir=tmp_path, filename="code-review-tally.json") == "2/5 accepted"


def test_compose_pr_body_no_guideline_note_matches_existing_output() -> None:
    base = pr_body.compose_pr_body(summary="- x")
    with_empty = pr_body.compose_pr_body(summary="- x", architectural_guidelines_note="")
    assert with_empty == base


def test_compose_pr_body_includes_guideline_note_before_mermaid() -> None:
    body = pr_body.compose_pr_body(
        summary="- x",
        mermaid="flowchart LR\n  A --> B\n",
        architectural_guidelines_note="Consulted ARCHITECTURAL_GUIDELINES.md; no deviations identified.",
    )
    assert "## Architectural guidelines" in body
    assert body.index("## Architectural guidelines") < body.index("## Code Flow Diagram")


def test_compose_pr_body_includes_guideline_drop_notice() -> None:
    notice = "The architectural guideline note was dropped because HEAD drifted after staging."
    body = pr_body.compose_pr_body(summary="- x", architectural_guidelines_note=notice)
    assert "## Architectural guidelines" in body
    assert notice in body


def test_compose_pr_body_redacts_guideline_note() -> None:
    token = "sk-" + "A" * 24
    body = pr_body.compose_pr_body(summary="- x", architectural_guidelines_note=f"token {token}")
    assert token not in body
    assert "<REDACTED-TOKEN>" in body


def test_render_run_summary_identity_lines_from_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text(
        json.dumps({"larch_version": "51.3.9", "model_roster": {"main": "claude-opus-4-8"}, "effort": "max"}),
        encoding="utf-8",
    )
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="merged",
        run_id="R",
        manifest_path=str(manifest),
        cost_unavailable=True,
    )
    assert "- **Main agent model**: claude-opus-4-8" in body
    assert "- **Effort**: max" in body
    assert "- **Larch version**: 51.3.9" in body


def test_render_run_summary_identity_lines_explicit_override(tmp_path: Path) -> None:
    _ = tmp_path
    body = pr_body.render_run_summary(
        skill="design",
        outcome="planned",
        run_id="R",
        larch_version="50.0.0",
        main_model="claude-haiku-4-5",
        effort="high",
        cost_unavailable=True,
    )
    assert "- **Main agent model**: claude-haiku-4-5" in body
    assert "- **Effort**: high" in body
    assert "- **Larch version**: 50.0.0" in body
