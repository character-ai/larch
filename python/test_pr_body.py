"""Tests for pr_body.py."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import config
import pr_body
from errors import ShipError
from proc import CommandResult


class _NoopRunner:
    def run(self, *args: object, **kwargs: object) -> CommandResult:  # pylint: disable=unused-argument
        return CommandResult((), 0, "", "", 0.0)



def test_stamp_skipped_steps_for_terminal_report_marks_ndjson_only_step9a1_false(
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

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)
    rc, err = pr_body._stamp_skipped_steps_for_terminal_report(tmp_path, run_id="run-1", outcome="bailed")
    assert (rc, err) == (0, "")
    flat = [arg for call in calls for arg in call]
    assert "steps_ran.step9a1=false" in flat


def test_stamp_skipped_steps_for_terminal_report_run_statistics_suppresses_step9a1_false(
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

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)
    rc, err = pr_body._stamp_skipped_steps_for_terminal_report(tmp_path, run_id="run-1", outcome="bailed")
    assert (rc, err) == (0, "")
    flat = [arg for call in calls for arg in call]
    assert "steps_ran.step9a1=false" not in flat

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


def test_update_pr_body_rejects_unsafe_mermaid() -> None:
    bad = "```mermaid\nflowchart LR\n  A[x|y] --> B\n```\n"
    with pytest.raises(ShipError, match="mermaid in PR body rejected"):
        pr_body.update_pr_body(_NoopRunner(), 3, bad, repo="o/r")


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
    pr_body.update_pr_body(runner, 3, "body", repo="o/r")  # type: ignore[arg-type]
    assert runner.calls
    assert runner.calls[0][1] == "pr"


def test_write_final_report_counts_warnings_and_exec(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _ = (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=0\nRUN_ID=run1\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")
    _ = (tmp_path / "ship-pr-state.sh").write_text("PR_NUMBER=1\nPR_URL=https://github.com/o/r/pull/1\n", encoding="utf-8")
    _ = (tmp_path / "run-flags.sh").write_text("EMERGENCY_REQUESTED=false\n", encoding="utf-8")
    _ = (tmp_path / "execution-issues.md").write_text(
        "### Tool Failures\n- **step5**: failed\n\n### Warnings\n- **warn**: one\n",
        encoding="utf-8",
    )

    def fake_final_report_token_fields(implement_tmpdir: Path, run_id: str) -> dict[str, object]:
        _ = (implement_tmpdir, run_id)
        return {"cost_unavailable": True}

    monkeypatch.setattr(pr_body, "_final_report_token_fields", fake_final_report_token_fields)
    rc, _url, _err = pr_body.write_final_report(tmp_path, comment_only=True)
    assert rc == 0
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "**Exec issues**: 1" in body
    assert "**Warnings**: 1" in body


def _write_minimal_final_report_state(tmp_path: Path, *, issue: str = "0", run_id: str = "run1") -> None:
    _ = (tmp_path / "parent-issue.md").write_text(f"ISSUE_NUMBER={issue}\nRUN_ID={run_id}\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")
    _ = (tmp_path / "ship-pr-state.sh").write_text("PR_NUMBER=1\nPR_URL=https://github.com/o/r/pull/1\n", encoding="utf-8")
    _ = (tmp_path / "finalize-state.sh").write_text("", encoding="utf-8")
    _ = (tmp_path / "run-flags.sh").write_text("EMERGENCY_REQUESTED=false\n", encoding="utf-8")


def _stub_final_report_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_final_report_token_fields(implement_tmpdir: Path, run_id: str) -> dict[str, object]:
        _ = (implement_tmpdir, run_id)
        return {"cost_unavailable": True}

    monkeypatch.setattr(pr_body, "_final_report_token_fields", fake_final_report_token_fields)


def test_write_final_report_appends_review_detail_in_comment_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_minimal_final_report_state(tmp_path)
    _stub_final_report_cost(monkeypatch)

    def fake_render_implement_review_detail(implement_tmpdir: Path, run_id: str) -> str:
        _ = (implement_tmpdir, run_id)
        return "## Review Phase Detail\nfrom helper\n"

    monkeypatch.setattr(pr_body.review_phase_detail, "render_implement_review_detail", fake_render_implement_review_detail)

    rc, _url, _err = pr_body.write_final_report(tmp_path, comment_only=True)

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

    monkeypatch.setattr(pr_body.review_phase_detail, "render_implement_review_detail", fake_render_implement_review_detail)

    rc, _url, _err = pr_body.write_final_report(tmp_path, comment_only=True)

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

    monkeypatch.setattr(pr_body.review_phase_detail, "render_implement_review_detail", fake_render_implement_review_detail)

    rc, _url, _err = pr_body.write_final_report(tmp_path, comment_only=True)

    assert rc == 0
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "<!-- larch:run-summary v=1 -->" in body
    assert "## Review Phase Detail" not in body


@pytest.mark.skipif(shutil.which("jq") is None, reason="render-review-phase-detail.sh requires jq")
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
    original_run = subprocess.run
    upsert_bodies: list[str] = []

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if argv and argv[0].endswith("render-review-phase-detail.sh"):
            timeout = kwargs.get("timeout")
            return original_run(
                argv,
                text=True,
                capture_output=True,
                timeout=timeout if isinstance(timeout, (int, float)) else None,
                check=False,
            )
        if "tracking-issue" in argv and "upsert-summary" in argv:
            content_file = Path(argv[argv.index("--content-file") + 1])
            upsert_bodies.append(content_file.read_text(encoding="utf-8"))
            return subprocess.CompletedProcess(argv, 0, stdout="COMMENT_URL=https://github.com/o/r/issues/42#issuecomment-1\n", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)

    rc, _url, _err = pr_body.write_final_report(tmp_path, comment_only=True)

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

    assert pr_body._refresh_issue_counts(tmp_path, "run1") == (2, 0)


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

    assert pr_body._refresh_issue_counts(tmp_path, "run1") == (2, 2)


def test_refresh_issue_counts_structured_row_without_bullets_counts_once(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "execution-issues.ndjson").write_text(
        json.dumps({"category": "Tool Failures", "body": "plain row"}) + "\n",
        encoding="utf-8",
    )

    assert pr_body._refresh_issue_counts(tmp_path, "run1") == (1, 0)


def test_refresh_issue_counts_ignores_fenced_diagnostic_bullets(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    row = {
        "category": "Tool Failures",
        "body": "```text\n- failed check\n```\n- real issue\n",
    }
    _ = (run_dir / "execution-issues.ndjson").write_text(json.dumps(row) + "\n", encoding="utf-8")

    assert pr_body._refresh_issue_counts(tmp_path, "run1") == (1, 0)


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

    assert pr_body._refresh_issue_counts(tmp_path, "run1") == (2, 1)


def test_refresh_issue_counts_section_heading_inside_fence_is_boundary(tmp_path: Path) -> None:
    _ = (tmp_path / "execution-issues.md").write_text(
        "### Tool Failures\n- exec1\n```\nlog line\n### Warnings\n- warn1\n",
        encoding="utf-8",
    )

    assert pr_body._refresh_issue_counts(tmp_path, "run1") == (1, 1)


def test_step18b_emits_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=1\nRUN_ID=run1\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")
    _ = (tmp_path / "ship-pr-state.sh").write_text("", encoding="utf-8")
    _ = (tmp_path / "run-flags.sh").write_text("EMERGENCY_REQUESTED=false\n", encoding="utf-8")

    def fake_final_report_token_fields(implement_tmpdir: Path, run_id: str) -> dict[str, object]:
        _ = (implement_tmpdir, run_id)
        return {"cost_unavailable": True}

    def fake_write_final_report(implement_tmpdir: Path) -> tuple[int, str, str]:
        _ = implement_tmpdir
        _ = (tmp_path / "summary-final.md").write_text("# Summary\n", encoding="utf-8")
        return 0, "", ""

    monkeypatch.setattr(pr_body, "_final_report_token_fields", fake_final_report_token_fields)
    monkeypatch.setattr(pr_body, "write_final_report", fake_write_final_report)
    rc = pr_body.step18b_final_report_main(["--implement-tmpdir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "EMIT_BODY=" in out
    assert "WFR_RC=" in out


def test_step18b_returns_write_failure_rc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=1\nRUN_ID=run1\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")

    monkeypatch.setattr(pr_body, "write_final_report", lambda _tmpdir: (1, "", "write failed"))  # type: ignore[arg-type]
    rc = pr_body.step18b_final_report_main(["--implement-tmpdir", str(tmp_path)])
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


def test_post_tracking_issue_writes_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _ = (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=42\nRUN_ID=run-z\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=o/r\nAGENT=claude\nCODER=claude\n", encoding="utf-8")
    _ = (tmp_path / "run-flags.sh").write_text("EMERGENCY_REQUESTED=false\n", encoding="utf-8")

    def fake_run(_cmd: list[str], **kwargs: object) -> object:
        _ = kwargs
        class Result:
            returncode = 0
            stdout = "COMMENT_URL=https://github.com/o/r/issues/42#issuecomment-1\n"
            stderr = ""
        return Result()

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)
    rc, posted, url, err = pr_body.post_tracking_issue(tmp_path)
    assert rc == 0
    assert posted is True
    assert "issues/42" in url
    assert (tmp_path / "summary-metadata.md").is_file()
    assert err == ""


def test_generate_code_flow_diagram_uses_launcher_not_stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    launcher = tmp_path / "fake-launcher.sh"
    _ = launcher.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    launcher.chmod(0o755)
    monkeypatch.setenv("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS", str(launcher))

    def fake_run(*_args: object, **_kwargs: object) -> object:
        return type("R", (), {"returncode": 1, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)
    rc, status, _diagram, reason = pr_body.generate_code_flow_diagram(tmp_path)
    assert rc == 1
    assert status == "failed"
    assert reason == "generation-failed"
    assert (tmp_path / "code-flow-prompt.md").is_file()


def _write_tally(run_dir: Path, filename: str, payload: object) -> None:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    _ = (run_dir / filename).write_text(text, encoding="utf-8")


def test_derive_review_line_absent_tally_returns_na(tmp_path: Path) -> None:
    assert pr_body._derive_review_line(tmp_path, "code-review-tally.json") == "N/A"


def test_derive_review_line_malformed_tally_returns_na(tmp_path: Path) -> None:
    _write_tally(tmp_path, "code-review-tally.json", "{not valid json")
    assert pr_body._derive_review_line(tmp_path, "code-review-tally.json") == "N/A"


def test_derive_review_line_non_object_json_returns_na(tmp_path: Path) -> None:
    _write_tally(tmp_path, "code-review-tally.json", "[1, 2, 3]")
    assert pr_body._derive_review_line(tmp_path, "code-review-tally.json") == "N/A"


def test_derive_review_line_invalid_counts_return_na(tmp_path: Path) -> None:
    _write_tally(tmp_path, "code-review-tally.json", {"phase": "code-review", "accepted_count": "abc", "rejected_count": 0})
    assert pr_body._derive_review_line(tmp_path, "code-review-tally.json") == "N/A"


def test_derive_review_line_negative_counts_return_na(tmp_path: Path) -> None:
    _write_tally(tmp_path, "code-review-tally.json", {"phase": "code-review", "accepted_count": -1, "rejected_count": 0})
    assert pr_body._derive_review_line(tmp_path, "code-review-tally.json") == "N/A"


def test_derive_review_line_self_review_zero_findings(tmp_path: Path) -> None:
    _write_tally(
        tmp_path,
        "code-review-tally.json",
        {"phase": "code-review", "batch": "code-review-tally", "mode": "self-review", "accepted_count": 0, "rejected_count": 0},
    )
    assert pr_body._derive_review_line(tmp_path, "code-review-tally.json") == "self-review: 0 findings"


def test_derive_review_line_code_review_zero_findings(tmp_path: Path) -> None:
    _write_tally(tmp_path, "code-review-tally.json", {"phase": "code-review", "mode": "hard", "accepted_count": 0, "rejected_count": 0})
    assert pr_body._derive_review_line(tmp_path, "code-review-tally.json") == "0 findings"


def test_derive_review_line_plan_review_zero_stays_na(tmp_path: Path) -> None:
    _write_tally(tmp_path, "plan-review-tally.json", {"phase": "plan-review", "mode": "hard", "accepted_count": 0, "rejected_count": 0})
    assert pr_body._derive_review_line(tmp_path, "plan-review-tally.json") == "N/A"


def test_derive_review_line_non_code_review_phase_zero_stays_na(tmp_path: Path) -> None:
    _write_tally(tmp_path, "plan-review-tally.json", {"phase": "design-review", "accepted_count": 0, "rejected_count": 0})
    assert pr_body._derive_review_line(tmp_path, "plan-review-tally.json") == "N/A"


def test_derive_review_line_positive_counts(tmp_path: Path) -> None:
    _write_tally(tmp_path, "code-review-tally.json", {"phase": "code-review", "mode": "hard", "accepted_count": 2, "rejected_count": 3})
    assert pr_body._derive_review_line(tmp_path, "code-review-tally.json") == "2/5 accepted"
