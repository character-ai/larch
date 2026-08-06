"""Tests for final_report.py extraction surface."""

# pyright: reportUnusedCallResult=false, reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownLambdaType=false, reportUnknownArgumentType=false


from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from larch.core import config, rust_runtime
from larch.errors import ShipError
from larch.implement import scope_disposition
from larch.report import final_report, run_log_manifest, tokens

from test_support import IMPLEMENT_BASELINE_KEYS, write_session_env


def test_derive_pr_line_counts_consumes_typed_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ship = tmp_path / "ship-pr-state.sh"
    _ = ship.write_text("PR_URL=https://example.test/pr/42\n", encoding="utf-8")
    monkeypatch.setattr(
        final_report.tokens,
        "compute_pr_line_counts",
        lambda **_kwargs: tokens.PrLineCountResult(
            status="ok", code_added=10, code_deleted=2, logs_added=3, logs_deleted=1,
        ),
    )

    values = final_report._derive_pr_line_counts(repo="owner/repo", repo_unavailable=False, pr_number="42", ship=ship)

    assert values == ("10", "2", "3", "1")
    assert "LINES_STATUS=ok" in ship.read_text(encoding="utf-8")


def _write_minimal_state(tmp_path: Path) -> None:
    (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=0\nRUN_ID=run1\n", encoding="utf-8")
    _ = write_session_env(
        tmp_path,
        omit=IMPLEMENT_BASELINE_KEYS,
        overrides={"REPO": "o/r", "MODE": "N/A"},
    )
    (tmp_path / "ship-pr-state.sh").write_text("PR_NUMBER=1\nPR_URL=https://github.com/o/r/pull/1\n", encoding="utf-8")
    (tmp_path / "finalize-state.sh").write_text("", encoding="utf-8")
    (tmp_path / "run-flags.sh").write_text("FORCE_REQUESTED=false\n", encoding="utf-8")


def _ok_pr_line_counts(**_kw: object) -> tokens.PrLineCountResult:
    return tokens.PrLineCountResult(
        status="ok", code_added=17, code_deleted=3, logs_added=5, logs_deleted=1,
    )


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
    original_run = final_report.subprocess.run

    def run_manifest_in_process(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if "run-log" not in argv or "manifest" not in argv:
            return original_run(argv, **kwargs)  # type: ignore[arg-type]
        root = Path(argv[argv.index("--log-root") + 1])
        skill = argv[argv.index("--skill") + 1]
        run_id = argv[argv.index("--run-id") + 1]
        updates: dict[str, object] = {}
        for index, value in enumerate(argv):
            if value != "--field":
                continue
            key, raw = argv[index + 1].split("=", 1)
            if raw == "true":
                updates[key] = True
            elif raw == "false":
                updates[key] = False
            elif raw == "null":
                updates[key] = None
            elif raw.lstrip("-").isdigit():
                updates[key] = int(raw)
            else:
                updates[key] = raw
        run_log_manifest._update_manifest_v2(  # pyright: ignore[reportPrivateUsage]  # unit-test boundary double; CLI parity is covered in Rust.
            path=root / skill / run_id / "manifest.json",
            updates=updates,
        )
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(final_report.subprocess, "run", run_manifest_in_process)
    monkeypatch.setattr(
        rust_runtime,
        "render_phase_detail",
        lambda *_args, **_kwargs: "## Review Phase Detail\n\nNo review rounds completed.\n",
    )


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
    over_cap = 27
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


def test_needs_user_ship_handoff_reader(tmp_path: Path) -> None:
    (tmp_path / ".ship-route-exit-handoff.env").write_text(
        "NEEDS_USER_REASON=architectural-assessments\nNEXT_ACTION=assessments\n", encoding="utf-8",
    )
    assert final_report._needs_user_ship_handoff(tmp_path, outcome="pr-created") == (
        "architectural-assessments",
        "assessments",
    )
    # #7074: a stale handoff must not override a merge-completed outcome.
    assert final_report._needs_user_ship_handoff(tmp_path, outcome="merged") is None


def test_needs_user_ship_handoff_absent_or_no_reason(tmp_path: Path) -> None:
    assert final_report._needs_user_ship_handoff(tmp_path, outcome="pr-created") is None
    # A plain (non-needs-user) handoff carries no NEEDS_USER_REASON.
    (tmp_path / ".ship-route-exit-handoff.env").write_text("NEXT_ACTION=reship\n", encoding="utf-8")
    assert final_report._needs_user_ship_handoff(tmp_path, outcome="pr-created") is None


def test_write_final_report_renders_needs_user_from_handoff(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    # #7074: a terminal needs-user ship handoff (merge + CI watch skipped) must
    # render a distinct outcome and an exec-issues row, not ✅ DONE.
    _write_minimal_state(tmp_path)
    _stub_cost_and_assessment(monkeypatch)
    (tmp_path / ".ship-route-exit-handoff.env").write_text(
        "NEEDS_USER_REASON=architectural-assessments\nNEXT_ACTION=assessments\nDETAIL=invariants,guidelines\n",
        encoding="utf-8",
    )
    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)
    assert (rc, err) == (0, "")
    summary = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    outcome_line = next(line for line in summary.splitlines() if "**Outcome**" in line)
    assert "NEEDS USER" in outcome_line
    assert "✅ DONE" not in outcome_line
    assert "merge and CI watch skipped" in summary
    assert "pending NEXT_ACTION=assessments" in summary


def test_write_final_report_resolves_persisted_needs_user_handoff_after_merge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_minimal_state(tmp_path)
    _stub_cost_and_assessment(monkeypatch)
    (tmp_path / "ship-pr-state.sh").write_text(
        "PR_NUMBER=1\nPR_URL=https://github.com/o/r/pull/1\nMERGE_RESULT=merged\n",
        encoding="utf-8",
    )
    (tmp_path / ".ship-route-exit-handoff.env").write_text(
        "NEEDS_USER_REASON=architectural-assessments\nNEXT_ACTION=assessments\n",
        encoding="utf-8",
    )
    entry = "- ship route: merge and CI watch skipped — needs user (reason: architectural-assessments; pending NEXT_ACTION=assessments)"
    issue_id = final_report.execution_issues.execution_issue_id(category="Tool Failures", body=entry)
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "execution-issues.ndjson").write_text(
        json.dumps({"category": "Tool Failures", "body": entry + "\n", "issue_id": issue_id}) + "\n",
        encoding="utf-8",
    )

    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)

    assert (rc, err) == (0, "")
    summary = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "merge and CI watch skipped" not in summary
    records = [json.loads(line) for line in (run_dir / "execution-issues.ndjson").read_text(encoding="utf-8").splitlines()]
    assert records[-1]["event"] == "resolved"


def test_write_final_report_no_handoff_keeps_normal_outcome(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _write_minimal_state(tmp_path)
    _stub_cost_and_assessment(monkeypatch)
    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)
    assert (rc, err) == (0, "")
    assert "NEEDS USER" not in (tmp_path / "summary-final.md").read_text(encoding="utf-8")


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
    monkeypatch.setattr(
        rust_runtime,
        "render_phase_detail",
        lambda *_args, **_kwargs: (
            "## Review Phase Detail\n\n"
            "### Round 1 reviewer timing\n\n"
            "```\n"
            "codex/codex-review │████│ 30s\n"
            "```\n"
        ),
    )

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
    gantt_rows = "\n".join(f"{latest_label} │█│ 1s" for _ in range(over_cap))
    monkeypatch.setattr(
        rust_runtime,
        "render_phase_detail",
        lambda *_args, **_kwargs: (
            "## Review Phase Detail\n\n"
            "### Round 1 reviewer timing\n\n"
            f"```\n{gantt_rows}\n```\n"
        ),
    )

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
    emit, rc, _present, _snapshot, err = final_report.step18b_final_report(tmp_path)
    assert emit is False
    assert rc == 7
    assert err == "boom"


def test_step18b_explicit_false_overrides_stale_sentinel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".step17-emitted").touch()
    (tmp_path / ".step16-16a-done").touch()

    def render(path: Path) -> tuple[int, str, str]:
        (path / "summary-final.md").write_text("merged\n", encoding="utf-8")
        return 0, "", ""

    monkeypatch.setattr(final_report, "write_final_report", render)

    emit, rc, present, _snapshot, _error = final_report.step18b_final_report(
        tmp_path,
        step17_emitted=False,
    )

    assert (emit, rc, present) == (True, 0, False)


def test_step18b_explicit_true_suppresses_unchanged_body(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".step16-16a-done").touch()
    (tmp_path / "summary-final.md").write_text("same\n", encoding="utf-8")
    monkeypatch.setattr(final_report, "write_final_report", lambda _path: (0, "", ""))

    emit, rc, present, _snapshot, _error = final_report.step18b_final_report(
        tmp_path,
        step17_emitted=True,
    )

    assert (emit, rc, present) == (False, 0, True)


def test_step18b_explicit_true_emits_changed_body(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".step16-16a-done").touch()
    (tmp_path / "summary-final.md").write_text("shipping\n", encoding="utf-8")

    def render(path: Path) -> tuple[int, str, str]:
        (path / "summary-final.md").write_text("merged\n", encoding="utf-8")
        return 0, "", ""

    monkeypatch.setattr(final_report, "write_final_report", render)

    emit, rc, present, _snapshot, _error = final_report.step18b_final_report(
        tmp_path,
        step17_emitted=True,
    )

    assert (emit, rc, present) == (True, 0, True)


def test_step18b_omitted_flag_uses_sentinel_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".step17-emitted").touch()
    (tmp_path / ".step16-16a-done").touch()
    (tmp_path / "summary-final.md").write_text("same\n", encoding="utf-8")
    monkeypatch.setattr(final_report, "write_final_report", lambda _path: (0, "", ""))

    emit, rc, present, _snapshot, _error = final_report.step18b_final_report(tmp_path)

    assert (emit, rc, present) == (False, 0, True)


def test_step18b_rejects_invalid_explicit_flag(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = final_report.step18b_final_report_main(
        ["--implement-tmpdir", str(tmp_path), "--step17-emitted", "maybe"],
    )

    assert rc == config.EXIT_USAGE
    assert capsys.readouterr().out == "ERROR=usage\n"


def test_step18b_emits_error_kv_on_render_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """#6979: a render failure must surface ERROR= alongside WFR_RC, not silence."""

    def boom(_tmpdir: Path) -> tuple[int, str, str]:
        return 1, "", "summary-final write failed: [Errno 28] No space left on device"

    monkeypatch.setattr(final_report, "write_final_report", boom)
    (tmp_path / ".step16-16a-done").touch()
    rc = final_report.step18b_final_report_main(["--implement-tmpdir", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "EMIT_BODY=false" in out
    assert "WFR_RC=1" in out
    assert "ERROR=summary-final write failed:" in out
    assert "No space left on device" in out


def test_step18b_catches_composition_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """#6979: an uncaught composition exception must not crash the terminal step.

    Previously write_final_report had no try/except at the step18b call site, so a
    composition exception escaped and produced a silent EMIT_BODY=false with no
    diagnosable cause. It must now surface as WFR_RC=1 + ERROR=.
    """

    def raise_exc(_tmpdir: Path) -> tuple[int, str, str]:
        raise RuntimeError("composition exploded")

    monkeypatch.setattr(final_report, "write_final_report", raise_exc)
    (tmp_path / ".step16-16a-done").touch()
    rc = final_report.step18b_final_report_main(["--implement-tmpdir", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "WFR_RC=1" in out
    assert "EMIT_BODY=false" in out
    assert "ERROR=final report render failed:" in out
    assert "composition exploded" in out


def test_write_final_report_runlog_copy_failure_surfaces_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#6979: a run-log final-summary.md copy failure is fatal but names itself.

    The CLI must surface bookkeeping/write failures as rc!=0 + reason (Step 17
    relies on this to log via _append_failure). The reason is also persisted via
    a breadcrumb so it survives teardown.
    """
    _write_minimal_state(tmp_path)
    _stub_cost_and_assessment(monkeypatch)
    original_write_text = Path.write_text

    def patched_write_text(self: Path, data: str, *args: object, **kwargs: object) -> int:
        if self.name == "final-summary.md":
            raise OSError("run-log copy blocked")
        return original_write_text(self, data, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "write_text", patched_write_text)

    rc, _url, err = final_report.write_final_report(tmp_path)

    assert rc == 1
    assert "final-summary write failed" in err
    assert "## /implement run run1" in (tmp_path / "summary-final.md").read_text(encoding="utf-8")


def test_write_final_report_tracking_upsert_failure_surfaces_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#6979: a tracking-issue upsert failure is fatal but names itself."""
    _write_minimal_state(tmp_path)
    (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=1\nRUN_ID=run1\n", encoding="utf-8")
    _stub_cost_and_assessment(monkeypatch)
    (tmp_path / "ship-pr-state.sh").write_text(
        "PR_NUMBER=0\nPR_URL=N/A\n",
        encoding="utf-8",
    )

    def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if "tracking-issue" in argv and "upsert-summary" in argv:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="upsert boom")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(final_report.subprocess, "run", fake_run)

    rc, _url, err = final_report.write_final_report(tmp_path)

    assert rc == 1
    assert "upsert boom" in err
    assert "## /implement run run1" in (tmp_path / "summary-final.md").read_text(encoding="utf-8")


def test_write_final_report_manifest_reconcile_failure_surfaces_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#6979: a manifest-reconcile failure is fatal but names itself."""
    _write_minimal_state(tmp_path)
    _stub_cost_and_assessment(monkeypatch)

    def fail_reconcile(*_args: object, **_kwargs: object) -> tuple[int, str]:
        return 1, "run-log manifest reconcile failed: boom"

    monkeypatch.setattr(final_report, "_reconcile_manifest_for_terminal_report", fail_reconcile)

    rc, _url, err = final_report.write_final_report(tmp_path)

    assert rc == 1
    assert "run-log manifest reconcile failed" in err
    assert "## /implement run run1" in (tmp_path / "summary-final.md").read_text(encoding="utf-8")


def test_write_final_report_summary_write_failure_persists_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#6979: the fatal summary-write failure still returns its reason (now durable)."""
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
        outcome="clean",
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
        outcome="clean",
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
        outcome="clean",
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
        outcome="clean",
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
        outcome="clean",
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
    _ = write_session_env(
        tmp_path,
        omit=IMPLEMENT_BASELINE_KEYS - {"REPO_ROOT"},
        overrides={"REPO_ROOT": str(tmp_path)},
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
    _ = write_session_env(
        tmp_path,
        omit=IMPLEMENT_BASELINE_KEYS - {"REPO_ROOT"},
        overrides={"REPO_ROOT": str(tmp_path)},
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
    _ = write_session_env(
        tmp_path,
        omit=IMPLEMENT_BASELINE_KEYS - {"REPO_ROOT"},
        overrides={"REPO": "o/r", "MODE": "N/A", "REPO_ROOT": str(tmp_path)},
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
    _ = write_session_env(
        tmp_path,
        omit=IMPLEMENT_BASELINE_KEYS - {"REPO_ROOT"},
        overrides={"REPO": "o/r", "MODE": "N/A", "REPO_ROOT": str(tmp_path)},
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
    _ = write_session_env(
        tmp_path,
        omit=IMPLEMENT_BASELINE_KEYS - {"REPO_ROOT"},
        overrides={"REPO_ROOT": str(tmp_path)},
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
    _ = write_session_env(
        tmp_path,
        omit=IMPLEMENT_BASELINE_KEYS - {"REPO_ROOT"},
        overrides={"REPO_ROOT": str(tmp_path)},
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


def test_write_final_report_coverage_line_not_fed_run_log_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Coverage line reads the dispatcher manifest, not the run-log manifest (#6995).

    The run-log manifest (larch-logs/implement/<RUN_ID>/manifest.json) legitimately
    omits todos_left; feeding it to the scope-disposition validator raises
    'resolved manifest schema-invalid' and aborts the whole final report. The
    render must let resolve_implement_manifest find the dispatcher manifest
    (implement_tmpdir/manifest.json), which carries todos_left.
    """
    _write_minimal_state(tmp_path)
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps({"schema_version": 2, "status": "partial"}),  # no todos_left
        encoding="utf-8",
    )
    _ = write_session_env(
        tmp_path,
        omit=IMPLEMENT_BASELINE_KEYS - {"REPO_ROOT"},
        overrides={"REPO": "o/r", "MODE": "N/A", "REPO_ROOT": str(tmp_path)},
    )
    _stub_cost_and_assessment(monkeypatch)

    seen_manifest_paths: list[object] = []

    def fake_load_live_coverage(
        *, tmpdir: Path, repo_root: Path, manifest_path: Path | None = None
    ) -> None:
        _ = tmpdir, repo_root
        seen_manifest_paths.append(manifest_path)
        # Mimic _load_manifest_todos_raw: the run-log manifest has no
        # todos_left, so it is schema-invalid for the coverage validator.
        if manifest_path is not None and manifest_path == run_dir / "manifest.json":
            raise ShipError(f"resolved manifest schema-invalid: {manifest_path}")

    monkeypatch.setattr(scope_disposition, "load_live_coverage", fake_load_live_coverage)

    rc, _url, _err = final_report.write_final_report(tmp_path, comment_only=True)

    assert rc == 0
    assert run_dir / "manifest.json" not in seen_manifest_paths
    summary = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "## /implement run run1" in summary


# ---------------------------------------------------------------------------
# Bash harness parity (ported from skills/implement/scripts/test-write-final-report.sh)
# ---------------------------------------------------------------------------

_TOKEN_REPORT_NONEMPTY: dict[str, object] = {
    "claude": {"totals": {"total": 1000}},
    "codex": {"totals": {"total": 2000}},
    "cursor": {"totals": {"total": 3000}},
    "BUCKETS_claude": {
        "input": 500,
        "cache_read": 100,
        "cache_create_5m": 50,
        "cache_create_1h": 50,
        "output": 300,
    },
    "BUCKETS_codex": {"input": 1000, "cached_input": 500, "output": 500},
    "BUCKETS_cursor": {"input": 1500, "cache_read": 500, "output": 1000},
}

_CORRUPT_WARNING = "**⚠ token-report.json appears corrupt; reporting Cost: N/A**"
_ZERO_DOLLAR_BREAKDOWN = "Claude $0.00, Codex-5.6 $0.00, Codex-mini $0.00, Cursor $0.00"


def _write_parity_fixture(
    tmp_path: Path,
    *,
    run_id: str,
    issue: str = "0",
    ship: str,
    finalize: str,
    session: str = "REPO=owner/repo\n",
    run_flags: str = "NO_ISSUES=false\n",
    token_report: dict[str, object] | str | None = None,
) -> Path:
    run_dir = tmp_path / "larch-logs" / "implement" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "parent-issue.md").write_text(
        f"ISSUE_NUMBER={issue}\nRUN_ID={run_id}\nADOPTED=true\n",
        encoding="utf-8",
    )
    (tmp_path / "session-env.sh").write_text(session, encoding="utf-8")
    (tmp_path / "ship-pr-state.sh").write_text(ship, encoding="utf-8")
    (tmp_path / "finalize-state.sh").write_text(finalize, encoding="utf-8")
    (tmp_path / "run-flags.sh").write_text(run_flags, encoding="utf-8")
    if token_report is None:
        token_report = _TOKEN_REPORT_NONEMPTY
    if isinstance(token_report, str):
        (run_dir / "token-report.json").write_text(token_report, encoding="utf-8")
    else:
        (run_dir / "token-report.json").write_text(
            json.dumps(token_report),
            encoding="utf-8",
        )
    return run_dir


def _cost_line(body: str) -> str:
    for line in body.splitlines():
        if line.startswith("- **Cost**:"):
            return line
    return ""


def test_write_final_report_comment_only_preserves_tracked_final_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = _write_parity_fixture(
        tmp_path,
        run_id="run-co",
        ship=(
            "PR_URL=https://example.test/pr/5\nPR_NUMBER=5\nSTALL_TRACKING=false\n"
            "MERGE_RESULT=merged\nMERGE=true\nDRAFT=false\nFORKED_TARGET=false\n"
        ),
        finalize="DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n",
    )
    marker = "legacy-stale-marker-do-not-touch\n"
    (run_dir / "final-summary.md").write_text(marker, encoding="utf-8")
    monkeypatch.setattr(final_report.tokens, "compute_pr_line_counts", _ok_pr_line_counts)
    _stub_cost_and_assessment(monkeypatch)

    rc, url, err = final_report.write_final_report(tmp_path, comment_only=True)

    assert (rc, url, err) == (0, "", "")
    assert (run_dir / "final-summary.md").read_text(encoding="utf-8") == marker
    summary = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "https://example.test/pr/5" in summary
    assert "## /implement run run-co: merged" in summary


def test_write_final_report_main_missing_tmpdir_emits_failed_envelope(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = final_report.write_final_report_main([])
    out = capsys.readouterr().out
    assert rc == 2
    assert "STATUS=failed" in out
    assert "COMMENT_URL=" in out
    assert "ERROR=usage" in out


def test_write_final_report_main_upsert_failure_emits_status_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_parity_fixture(
        tmp_path,
        run_id="run-up",
        issue="7",
        ship=(
            "PR_URL=https://example.test/pr/5\nPR_NUMBER=5\nSTALL_TRACKING=false\n"
            "MERGE_RESULT=merged\nMERGE=true\nDRAFT=false\nFORKED_TARGET=false\n"
        ),
        finalize="DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n",
    )
    _stub_cost_and_assessment(monkeypatch)
    monkeypatch.setattr(
        final_report.tokens,
        "compute_pr_line_counts",
        lambda **_kw: tokens.PrLineCountResult(status="unavailable", reason="gh-failed"),
    )

    def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if "tracking-issue" in argv and "upsert-summary" in argv:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="gh auth failed")
        if "run-log" in argv and "manifest" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(final_report.subprocess, "run", fake_run)

    rc = final_report.write_final_report_main(["--implement-tmpdir", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "STATUS=failed" in out
    assert "ERROR=" in out


@pytest.mark.parametrize(
    ("expected", "ship", "finalize", "outcome_display", "expect_pr"),
    [
        (
            "merged",
            "PR_URL=https://example.test/pr/5\nPR_NUMBER=5\nSTALL_TRACKING=false\n"
            "MERGE_RESULT=merged\nMERGE=true\nDRAFT=false\nFORKED_TARGET=false\n",
            "DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n",
            "✅ DONE",
            True,
        ),
        (
            "stalled",
            "PR_URL=https://example.test/pr/2\nPR_NUMBER=2\nSTALL_TRACKING=true\n"
            "PHASE=stalled\nMERGE_RESULT=\nMERGE=false\nDRAFT=false\nFORKED_TARGET=false\n",
            "DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\nSTALL_TRACKING=true\n",
            "❌ STALLED",
            True,
        ),
        (
            "design-only",
            "PR_URL=N/A\nPR_NUMBER=\nSTALL_TRACKING=false\nMERGE_RESULT=\n"
            "MERGE=false\nDRAFT=false\nFORKED_TARGET=false\n",
            "DESIGN_ONLY_DONE=true\nBAIL_NEEDS_USER_INPUT=false\n",
            "✅ DONE",
            False,
        ),
        (
            "bailed-needs-user-input",
            "PR_URL=N/A\nPR_NUMBER=\nSTALL_TRACKING=false\nBAIL_REASON=early-failure\n"
            "MERGE_RESULT=\nMERGE=false\nDRAFT=false\nFORKED_TARGET=false\n",
            "DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=true\n",
            "bailed-needs-user-input",
            False,
        ),
        (
            "bailed",
            "PR_URL=N/A\nPR_NUMBER=\nSTALL_TRACKING=false\nBAIL_REASON=early-failure\n"
            "MERGE_RESULT=\nMERGE=false\nDRAFT=false\nFORKED_TARGET=false\n",
            "DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n",
            "bailed",
            False,
        ),
        (
            "forked-dry-run",
            "PR_URL=https://example.test/pr/32\nPR_NUMBER=32\nSTALL_TRACKING=false\n"
            "MERGE_RESULT=\nMERGE=false\nDRAFT=false\nFORKED_TARGET=true\n",
            "DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n",
            "✅ DONE",
            True,
        ),
        (
            "pr-created",
            "PR_URL=https://example.test/pr/30\nPR_NUMBER=30\nSTALL_TRACKING=false\n"
            "MERGE_RESULT=\nMERGE=false\nDRAFT=false\nFORKED_TARGET=false\n",
            "DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n",
            "✅ DONE",
            True,
        ),
        (
            "pr-created-draft",
            "PR_URL=https://example.test/pr/31\nPR_NUMBER=31\nSTALL_TRACKING=false\n"
            "MERGE_RESULT=\nMERGE=false\nDRAFT=true\nFORKED_TARGET=false\n",
            "DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n",
            "✅ DONE",
            True,
        ),
        (
            "force-merged-externally",
            "PR_URL=https://example.test/pr/33\nPR_NUMBER=33\nSTALL_TRACKING=false\n"
            "MERGE_RESULT=already_merged\nMERGE=true\nDRAFT=false\nFORKED_TARGET=false\n",
            "DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n",
            "✅ DONE",
            True,
        ),
    ],
)
def test_write_final_report_outcome_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    expected: str,
    ship: str,
    finalize: str,
    outcome_display: str,
    expect_pr: bool,
) -> None:
    run_id = f"run-{expected}"
    _write_parity_fixture(
        tmp_path,
        run_id=run_id,
        ship=ship,
        finalize=finalize,
        token_report=_TOKEN_REPORT_NONEMPTY if expected != "bailed" else None,
    )
    if expected == "bailed":
        # Missing token data → Cost: N/A (bash bailed fixture has no token-report).
        (tmp_path / "larch-logs" / "implement" / run_id / "token-report.json").unlink(missing_ok=True)
    monkeypatch.setattr(final_report.tokens, "compute_pr_line_counts", _ok_pr_line_counts)
    monkeypatch.setattr(final_report.exec_issue_detail, "assess_issue_details", lambda *_a, **_k: {})

    rc, url, err = final_report.write_final_report(
        tmp_path,
        comment_only=False,
        skip_tracking_upsert=True,
        print_stdout=False,
    )
    assert (rc, url, err) == (0, "", "")
    summary = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    run_log = (
        tmp_path / "larch-logs" / "implement" / run_id / "final-summary.md"
    ).read_text(encoding="utf-8")
    for body in (summary, run_log):
        assert f"## /implement run {run_id}: {expected}" in body
        assert f"- **Outcome**: {outcome_display}" in body
        assert "- **Mode**:" not in body
        assert "- **Cost**:" in body
        assert "<!-- larch:run-summary v=1 -->" in body
        if expect_pr:
            assert "- **PR**:" in body
        else:
            assert "- **PR**:" not in body
        if expected != "bailed":
            cost = _cost_line(body)
            assert "💰 TOTAL" in cost
            assert ("Claude $" in cost) or ("Claude/GLM-5.2 token $" in cost)
            assert "Codex-5.6 $" in cost
            assert "Codex-mini $" in cost
            assert "Cursor $" in cost
            assert "Tokens: " in cost
        else:
            assert "- **Cost**: N/A" in body
            assert "- **Lines (PR diff)**: N/A" in body


def test_write_final_report_manifest_stamp_and_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = _write_parity_fixture(
        tmp_path,
        run_id="run-mfb",
        ship=(
            "PR_URL=N/A\nPR_NUMBER=\nSTALL_TRACKING=false\nBAIL_REASON=early-failure\n"
            "MERGE_RESULT=\nMERGE=false\nDRAFT=false\nFORKED_TARGET=false\n"
        ),
        finalize="DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n",
        token_report={"claude": {"totals": {"total": 0}}},
    )
    # No Step 7a artifact after unlink → steps_ran.step7a=false (bash mfb fixture).
    (run_dir / "token-report.json").unlink()
    (run_dir / "manifest.json").write_text(
        '{"schema_version":2,"steps_ran":{}}\n',
        encoding="utf-8",
    )
    (run_dir / "final-summary.md").write_text("prior\n", encoding="utf-8")
    captured: list[list[str]] = []
    environments: list[dict[str, str]] = []

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if "run-log" in argv and "manifest" in argv:
            captured.append(list(argv))
            environment = kwargs.get("env")
            if isinstance(environment, dict):
                environments.append(environment)
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(final_report.subprocess, "run", fake_run)
    monkeypatch.setattr(final_report.exec_issue_detail, "assess_issue_details", lambda *_a, **_k: {})

    rc, url, err = final_report.write_final_report(tmp_path, skip_tracking_upsert=False)
    assert (rc, url, err) == (0, "", "")
    assert captured
    assert environments[0][config.ENV_CLAUDE_PLUGIN_ROOT] == str(
        Path(final_report.__file__).resolve().parents[3]
    )
    argv = captured[0]
    assert argv[0].endswith("scripts/larch.sh")
    assert "run-log" in argv
    assert "manifest" in argv
    assert "--log-root" in argv
    assert "--skill" in argv
    assert "implement" in argv
    assert "--run-id" in argv
    assert "run-mfb" in argv
    fields = [argv[i + 1] for i, tok in enumerate(argv) if tok == "--field"]
    assert "steps_ran.step9a1=false" in fields
    assert "steps_ran.step8=true" in fields
    assert "steps_ran.step7a=false" in fields

    def fail_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if "run-log" in argv and "manifest" in argv:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="manifest stub failure")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(final_report.subprocess, "run", fail_run)
    rc_fail, _url, err_fail = final_report.write_final_report(tmp_path)
    assert rc_fail == 1
    assert "run-log manifest reconcile failed" in err_fail


def test_write_final_report_cost_unavailable_variants(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ship = (
        "PR_URL=N/A\nPR_NUMBER=\nSTALL_TRACKING=false\nBAIL_REASON=early-failure\n"
        "MERGE_RESULT=\nMERGE=false\nDRAFT=false\nFORKED_TARGET=false\n"
    )
    finalize = "DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n"
    monkeypatch.setattr(final_report.exec_issue_detail, "assess_issue_details", lambda *_a, **_k: {})

    # Malformed token-report.json
    _write_parity_fixture(
        tmp_path,
        run_id="run-badjson",
        ship=ship,
        finalize=finalize,
        token_report="{not-json\n",  # noqa: S106 - malformed JSON fixture, not a secret
    )
    rc, _url, err = final_report.write_final_report(
        tmp_path, comment_only=True, print_stdout=True
    )
    out = capsys.readouterr().out
    assert (rc, err) == (0, "")
    assert "- **Cost**: N/A" in out
    assert _ZERO_DOLLAR_BREAKDOWN not in out

    # All-zero buckets: cost N/A, no corrupt warning, no zero-dollar breakdown
    zero_report: dict[str, object] = {
        "claude": {"totals": {"total": 0}},
        "codex": {"totals": {"total": 0}},
        "cursor": {"totals": {"total": 0}},
        "claude_sub": {"totals": {"total": 0}},
        "BUCKETS_claude": {
            "input": 0,
            "cache_read": 0,
            "cache_create_5m": 0,
            "cache_create_1h": 0,
            "output": 0,
        },
        "BUCKETS_codex": {"input": 0, "cached_input": 0, "output": 0},
        "BUCKETS_cursor": {"input": 0, "cache_read": 0, "output": 0},
        "BUCKETS_claude_sub": {
            "input": 0,
            "cache_read": 0,
            "cache_create_5m": 0,
            "cache_create_1h": 0,
            "output": 0,
        },
    }
    _write_parity_fixture(
        tmp_path,
        run_id="run-zero",
        ship=ship,
        finalize=finalize,
        token_report=zero_report,
    )
    rc, _url, err = final_report.write_final_report(
        tmp_path, comment_only=True, print_stdout=True
    )
    out = capsys.readouterr().out
    summary = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert (rc, err) == (0, "")
    assert "- **Cost**: N/A" in out
    assert _CORRUPT_WARNING not in out
    assert _CORRUPT_WARNING not in summary
    assert _ZERO_DOLLAR_BREAKDOWN not in out

    # Claude-only zero totals keep cost unavailable
    _write_parity_fixture(
        tmp_path,
        run_id="run-claude-zero",
        ship=ship,
        finalize=finalize,
        token_report={
            "claude": {"totals": {"total": 0}},
            "BUCKETS_claude": {
                "input": 0,
                "cache_read": 0,
                "cache_create_5m": 0,
                "cache_create_1h": 0,
                "output": 0,
            },
        },
    )
    rc, _url, err = final_report.write_final_report(
        tmp_path, comment_only=True, print_stdout=True
    )
    out = capsys.readouterr().out
    assert (rc, err) == (0, "")
    assert "- **Cost**: N/A" in out
    assert _CORRUPT_WARNING not in out


def test_write_final_report_claude_sub_nonzero_cost_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_parity_fixture(
        tmp_path,
        run_id="run-sub-nonzero",
        ship=(
            "PR_URL=N/A\nPR_NUMBER=\nSTALL_TRACKING=false\nBAIL_REASON=early-failure\n"
            "MERGE_RESULT=\nMERGE=false\nDRAFT=false\nFORKED_TARGET=false\n"
        ),
        finalize="DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n",
        token_report={
            "claude": {"totals": {"total": 0}},
            "codex": {"totals": {"total": 0}},
            "cursor": {"totals": {"total": 0}},
            "claude_sub": {"totals": {"total": 100}},
            "BUCKETS_claude": {
                "input": 0,
                "cache_read": 0,
                "cache_create_5m": 0,
                "cache_create_1h": 0,
                "output": 0,
            },
            "BUCKETS_codex": {"input": 0, "cached_input": 0, "output": 0},
            "BUCKETS_cursor": {"input": 0, "cache_read": 0, "output": 0},
            "BUCKETS_claude_sub": {
                "input": 50,
                "cache_read": 10,
                "cache_create_5m": 20,
                "cache_create_1h": 0,
                "output": 20,
            },
        },
    )
    monkeypatch.setattr(final_report.exec_issue_detail, "assess_issue_details", lambda *_a, **_k: {})

    rc, _url, err = final_report.write_final_report(
        tmp_path, comment_only=True, print_stdout=True
    )
    out = capsys.readouterr().out
    summary = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert (rc, err) == (0, "")
    assert _CORRUPT_WARNING not in out
    assert _CORRUPT_WARNING not in summary
    cost = _cost_line(out)
    assert "Claude (subprocess)" in cost
    assert "💰 TOTAL" in cost


def test_write_final_report_force_flag_and_legacy_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ship = (
        "PR_URL=N/A\nPR_NUMBER=\nSTALL_TRACKING=false\nBAIL_REASON=early-failure\n"
        "MERGE_RESULT=\nMERGE=false\nDRAFT=false\nFORKED_TARGET=false\n"
    )
    finalize = "DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n"
    _stub_cost_and_assessment(monkeypatch)

    _write_parity_fixture(
        tmp_path,
        run_id="run-em",
        ship=ship,
        finalize=finalize,
        run_flags="NO_ISSUES=false\nWORKFLOW_PATH=\nFORCE_REQUESTED=true\n",
        token_report={"claude": {"totals": {"total": 0}}},
    )
    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)
    assert (rc, err) == (0, "")
    assert "- Force: true" in (tmp_path / "summary-final.md").read_text(encoding="utf-8")

    for flags, run_id in (
        ("NO_ISSUES=false\nWORKFLOW_PATH=\nFORCE_REQUESTED=false\n", "run-emf"),
        ("NO_ISSUES=false\n", "run-emo"),
        ("NO_ISSUES=false\nWORKFLOW_PATH=\nFORCE_REQUESTED=maybe\n", "run-emi"),
    ):
        _write_parity_fixture(
            tmp_path,
            run_id=run_id,
            ship=ship,
            finalize=finalize,
            run_flags=flags,
            token_report={"claude": {"totals": {"total": 0}}},
        )
        rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)
        body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
        assert (rc, err) == (0, "")
        assert "Force: true" not in body
        assert "Invalid `FORCE_REQUESTED` value" not in body
        assert not (tmp_path / "execution-issues.md").exists() or (
            "Invalid FORCE_REQUESTED value in run-flags.sh: maybe"
            not in (tmp_path / "execution-issues.md").read_text(encoding="utf-8")
        )

    _write_parity_fixture(
        tmp_path,
        run_id="run-legacy",
        ship=ship,
        finalize=finalize,
        session="REPO=owner/repo\nPOST_PLAN_WORKFLOW_PATH=\n",
        run_flags="NO_ISSUES=false\nWORKFLOW_PATH=\nFORCE_REQUESTED=false\n",
        token_report={"claude": {"totals": {"total": 0}}},
    )
    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert (rc, err) == (0, "")
    assert "- **Path**:" not in body


def test_write_final_report_line_counts_cache_and_repo_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    def fake_line_counts(**kwargs: object) -> tokens.PrLineCountResult:
        calls.append(kwargs)
        return _ok_pr_line_counts()

    monkeypatch.setattr(final_report.tokens, "compute_pr_line_counts", fake_line_counts)
    _stub_cost_and_assessment(monkeypatch)

    _write_parity_fixture(
        tmp_path,
        run_id="run-lines",
        ship=(
            "PR_URL=https://example.test/pr/40\nPR_NUMBER=40\nSTALL_TRACKING=false\n"
            "MERGE_RESULT=merged\nMERGE=true\nDRAFT=false\nFORKED_TARGET=false\n"
        ),
        finalize="DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n",
    )
    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert (rc, err) == (0, "")
    assert "- **Lines (PR diff)**: code +17/-3, larch-logs +5/-1" in body
    assert calls

    # REPO_UNAVAILABLE skips line-count helper
    calls.clear()
    _write_parity_fixture(
        tmp_path,
        run_id="run-runav",
        ship=(
            "PR_URL=https://example.test/pr/41\nPR_NUMBER=41\nSTALL_TRACKING=false\n"
            "MERGE_RESULT=merged\nMERGE=true\nDRAFT=false\nFORKED_TARGET=false\n"
        ),
        finalize="DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n",
        session="REPO=owner/repo\nREPO_UNAVAILABLE=true\n",
    )
    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert (rc, err) == (0, "")
    assert "- **Lines (PR diff)**: N/A" in body
    assert not calls

    # Helper failure → N/A
    monkeypatch.setattr(
        final_report.tokens,
        "compute_pr_line_counts",
        lambda **_kw: tokens.PrLineCountResult(status="unavailable", reason="gh-failed"),
    )
    _write_parity_fixture(
        tmp_path,
        run_id="run-ghfail",
        ship=(
            "PR_URL=https://example.test/pr/42\nPR_NUMBER=42\nSTALL_TRACKING=false\n"
            "MERGE_RESULT=merged\nMERGE=true\nDRAFT=false\nFORKED_TARGET=false\n"
        ),
        finalize="DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n",
    )
    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)
    assert (rc, err) == (0, "")
    assert "- **Lines (PR diff)**: N/A" in (tmp_path / "summary-final.md").read_text(
        encoding="utf-8"
    )

    # Unavailable cache is recomputed; stale PR cache is not reused
    monkeypatch.setattr(final_report.tokens, "compute_pr_line_counts", fake_line_counts)
    calls.clear()
    _write_parity_fixture(
        tmp_path,
        run_id="run-line-cache",
        ship=(
            "PR_URL=https://example.test/pr/43\nPR_NUMBER=43\nLINES_PR_NUMBER=43\n"
            "LINES_STATUS=unavailable\nCODE_ADDED=999\nCODE_DELETED=999\n"
            "LOGS_ADDED=999\nLOGS_DELETED=999\nSTALL_TRACKING=false\n"
            "MERGE_RESULT=merged\nMERGE=true\nDRAFT=false\nFORKED_TARGET=false\n"
        ),
        finalize="DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n",
    )
    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert (rc, err) == (0, "")
    assert "- **Lines (PR diff)**: code +17/-3, larch-logs +5/-1" in body
    assert calls

    calls.clear()
    _write_parity_fixture(
        tmp_path,
        run_id="run-line-stale",
        ship=(
            "PR_URL=https://example.test/pr/44\nPR_NUMBER=44\nLINES_PR_NUMBER=43\n"
            "LINES_STATUS=ok\nCODE_ADDED=999\nCODE_DELETED=999\n"
            "LOGS_ADDED=999\nLOGS_DELETED=999\nSTALL_TRACKING=false\n"
            "MERGE_RESULT=merged\nMERGE=true\nDRAFT=false\nFORKED_TARGET=false\n"
        ),
        finalize="DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n",
    )
    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    ship_text = (tmp_path / "ship-pr-state.sh").read_text(encoding="utf-8")
    assert (rc, err) == (0, "")
    assert "- **Lines (PR diff)**: code +17/-3, larch-logs +5/-1" in body
    assert "+999/-999" not in body
    assert ship_text.count("LINES_STATUS=") == 1
    assert "CODE_ADDED=17" in ship_text


def test_write_final_report_review_phase_live_dir_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#3794: round-meta only under live IMPLEMENT_TMPDIR/round-N is ignored."""
    _write_parity_fixture(
        tmp_path,
        run_id="run-rpd",
        ship=(
            "PR_URL=N/A\nPR_NUMBER=\nSTALL_TRACKING=false\nBAIL_REASON=early-failure\n"
            "MERGE_RESULT=\nMERGE=false\nDRAFT=false\nFORKED_TARGET=false\n"
        ),
        finalize="DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n",
        token_report={"claude": {"totals": {"total": 0}}},
    )
    live_round = tmp_path / "round-1"
    live_round.mkdir()
    (live_round / "round-meta.json").write_text(
        json.dumps({
            "tally": {
                "ACCEPTED_COUNT": "2",
                "REJECTED_COUNT": "0",
                "EXONERATED_COUNT": "0",
                "NEUTRAL_COUNT": "0",
                "OOS_ACCEPTED_COUNT": "0",
                "OOS_REJECTED_COUNT": "0",
            },
            "summary": {"panel": {"total_slot_count": 2}},
        }),
        encoding="utf-8",
    )
    (live_round / "panel-manifest.ndjson").write_text("{}\n", encoding="utf-8")
    findings = tmp_path / "larch-logs" / "implement" / "run-rpd" / "review-findings-full.jsonl"
    findings.write_text(
        json.dumps({
            "id": "FINDING_1",
            "outcome": "accepted",
            "reviewer_slots": ["cursor-specialist-correctness-output.txt"],
            "round_num": "1",
        })
        + "\n",
        encoding="utf-8",
    )
    _stub_cost_and_assessment(monkeypatch)

    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)
    body = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert (rc, err) == (0, "")
    assert "## Review Phase Detail" in body
    assert "No review rounds completed." in body
    assert "| 1 | 2 | 2 | 0 | 0 |" not in body


def test_write_final_report_happy_path_writes_final_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = _write_parity_fixture(
        tmp_path,
        run_id="run-5",
        ship=(
            "PR_URL=https://example.test/pr/5\nPR_NUMBER=5\nSTALL_TRACKING=false\n"
            "MERGE_RESULT=merged\nMERGE=true\nDRAFT=false\nFORKED_TARGET=false\n"
        ),
        finalize="DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n",
    )
    monkeypatch.setattr(final_report.tokens, "compute_pr_line_counts", _ok_pr_line_counts)
    monkeypatch.setattr(final_report.exec_issue_detail, "assess_issue_details", lambda *_a, **_k: {})
    monkeypatch.setattr(
        rust_runtime,
        "render_phase_detail",
        lambda *_args, **_kwargs: "## Review Phase Detail\n\nNo review rounds completed.\n",
    )

    rc, url, err = final_report.write_final_report(tmp_path, skip_tracking_upsert=True)
    assert (rc, url, err) == (0, "", "")
    summary = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    final = (run_dir / "final-summary.md").read_text(encoding="utf-8")
    assert final.strip()
    for body in (summary, final):
        assert "## /implement run run-5: merged" in body
        assert "- **Outcome**: ✅ DONE" in body
        assert "- **Mode**:" not in body
        assert "- **Lines (PR diff)**: code +17/-3, larch-logs +5/-1" in body
        assert "<!-- larch:run-summary v=1 -->" in body
        assert "## Review Phase Detail" in body
        assert "No review rounds completed." in body
