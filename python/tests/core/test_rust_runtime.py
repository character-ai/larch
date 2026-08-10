"""Tests for thin Python consumers of Rust-owned commands."""

from __future__ import annotations

import hashlib
from pathlib import Path

from larch.core import rust_runtime
from larch.core.proc import CommandResult
from larch.core.rust_runtime import (
    block_issue_dependency,
    dirty_tree_baseline,
    dirty_tree_checkpoint,
    issue_add_blocked_by,
    issue_info,
    issue_state,
    phantom_probe,
)
from test_support import RecordingRunner
from tests.support.foundation import make_run_context


def test_phantom_probe_relays_validated_rust_envelope() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("larch", "git", "phantom-probe"),
                0,
                "PHANTOM_STATUS=phantom\nPHANTOM_COUNT=2\n",
                "→ phantom-probe: step-1\n",
                0.01,
            ),
        ],
    )

    result = phantom_probe(runner, step="step-1")

    assert result.lines == ("PHANTOM_STATUS=phantom", "PHANTOM_COUNT=2")
    assert runner.calls[0][-4:] == ["git", "phantom-probe", "--step", "step-1"]


def test_phantom_probe_fails_closed_for_missing_envelope() -> None:
    runner = RecordingRunner(
        responses=[CommandResult(("larch",), 127, "", "missing", 0.01)],
    )

    result = phantom_probe(runner, step="step-2")

    assert result.lines == ("PHANTOM_STATUS=unknown", "PHANTOM_REASON=phantom-probe-failed")


def test_progress_mutations_enter_through_the_typed_rust_owner() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("larch",), 0, "", "", 0.01),
            CommandResult(("larch",), 0, "", "", 0.01),
            CommandResult(("larch",), 0, "", "", 0.01),
            CommandResult(("larch",), 0, "", "", 0.01),
            CommandResult(("larch",), 0, "PROGRESS_REMOVED=3\n", "", 0.01),
        ],
    )

    assert rust_runtime.progress_activate(runner, repo_root="/clone", run_id="run-1")
    assert rust_runtime.progress_clear(runner, repo_root="/clone")
    assert rust_runtime.progress_deactivate(runner, repo_root="/clone", run_id="run-1")
    assert rust_runtime.progress_note(
        runner,
        repo_root="/clone",
        run_id="run-1",
        skill="implement",
        step="8",
        text="checks running",
    )
    assert rust_runtime.progress_cleanup(runner, retention_days=7) == 3

    assert runner.calls[0][1:] == [
        "progress",
        "activate",
        "--repo-root",
        "/clone",
        "--run-id",
        "run-1",
    ]
    assert runner.calls[1][1:] == ["progress", "clear", "--repo-root", "/clone"]
    assert runner.calls[2][1:] == [
        "progress",
        "deactivate",
        "--repo-root",
        "/clone",
        "--run-id",
        "run-1",
    ]
    assert runner.calls[3][1:] == [
        "progress",
        "note",
        "--repo-root",
        "/clone",
        "--run-id",
        "run-1",
        "--skill",
        "implement",
        "--step",
        "8",
        "checks running",
    ]
    assert runner.calls[4][1:] == ["progress", "cleanup", "--retention-days", "7"]


def test_execution_issue_workflows_use_validated_rust_envelopes() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("larch",), 0, "APPEND_STATUS=appended\n", "", 0.01),
            CommandResult(
                ("larch",),
                0,
                "FLUSH_STATUS=ok\nRECORDS=2\nAPPEND_LOG_FILE=/tmp/append.log\n",
                "",
                0.01,
            ),
            CommandResult(("larch",), 0, "FLUSH_STATUS=rendered\nRECORDS=1\n", "", 0.01),
            CommandResult(("larch",), 0, "REFRESHED=true\nREASON=issue-not-set\n", "", 0.01),
        ],
    )

    appended = rust_runtime.execution_issues_append(
        runner,
        log="/tmp/execution-issues.md",
        category="Warnings",
        entry="- warning",
        existing_batch="/tmp/execution-issues.ndjson",
        redact_entry=True,
    )
    flushed = rust_runtime.execution_issues_flush(
        runner,
        log_root="/tmp/larch-logs",
        run_id="run-1",
        issue_log="/tmp/execution-issues.md",
        step_label="7a",
        source_label="checkpoint",
    )
    rendered = rust_runtime.execution_issues_flush_safety_net(
        runner,
        log_root="/tmp/larch-logs",
        run_id="run-1",
        record_file="/tmp/records.ndjson",
    )
    refreshed = rust_runtime.execution_issues_refresh(
        runner, implement_tmpdir="/tmp/session", best_effort=True
    )

    assert appended.status == "appended"
    assert not appended.failed
    assert flushed.status == "ok"
    assert flushed.records == 2
    assert not flushed.failed
    assert flushed.append_log_file == "/tmp/append.log"
    assert rendered.status == "rendered"
    assert rendered.records == 1
    assert refreshed.refreshed
    assert refreshed.reason == "issue-not-set"
    assert runner.calls[0][1:] == [
        "execution-issues",
        "append",
        "--log",
        "/tmp/execution-issues.md",
        "--category",
        "Warnings",
        "--entry",
        "- warning",
        "--report-status",
        "--spaced-section",
        "--existing-batch",
        "/tmp/execution-issues.ndjson",
        "--redact",
    ]
    assert runner.calls[1][1:3] == ["execution-issues", "flush"]
    assert runner.calls[2][1:3] == ["execution-issues", "flush-safety-net"]
    assert runner.calls[3][1:] == [
        "execution-issues",
        "refresh",
        "--implement-tmpdir",
        "/tmp/session",
        "--best-effort",
    ]


def test_execution_issue_facade_rejects_malformed_and_false_success_envelopes() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("larch",),
                0,
                "APPEND_STATUS=appended\nAPPEND_STATUS=duplicate\n",
                "",
                0.01,
            ),
            CommandResult(("larch",), 0, "FLUSH_STATUS=ok\nRECORDS=nope\n", "", 0.01),
            CommandResult(("larch",), 0, "REFRESHED=false\n", "", 0.01),
        ],
    )

    appended = rust_runtime.execution_issues_append(
        runner, log="/tmp/log", category="Warnings", entry="- warning"
    )
    flushed = rust_runtime.execution_issues_flush(
        runner, log_root="/tmp/larch-logs", run_id="run-1"
    )
    refreshed = rust_runtime.execution_issues_refresh(runner, implement_tmpdir="/tmp/session")

    assert appended.failed
    assert appended.error == "invalid execution-issues envelope"
    assert flushed.failed
    assert flushed.records == 0
    assert refreshed.failed
    assert not refreshed.refreshed


def test_execution_issue_facade_preserves_best_effort_refresh_failure() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("larch",),
                0,
                "REFRESHED=false\nERROR=tracking update failed\n",
                "",
                0.01,
            ),
            CommandResult(
                ("larch",),
                0,
                "diagnostic\nAPPEND_STATUS=appended\n",
                "",
                0.01,
            ),
        ],
    )

    refreshed = rust_runtime.execution_issues_refresh(
        runner, implement_tmpdir="/tmp/session", best_effort=True
    )
    appended = rust_runtime.execution_issues_append(
        runner, log="/tmp/log", category="Warnings", entry="- warning"
    )

    assert refreshed.failed
    assert not refreshed.refreshed
    assert refreshed.error == "tracking update failed"
    assert appended.failed
    assert appended.error == "invalid execution-issues envelope"


def test_timing_mutations_enter_through_the_typed_rust_owner() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("larch",), 0, "", "", 0.01),
            CommandResult(("larch",), 0, "", "", 0.01),
            CommandResult(("larch",), 0, "", "", 0.01),
            CommandResult(("larch",), 0, "", "", 0.01),
        ],
    )

    assert rust_runtime.timing_mark(
        runner,
        label="Step 0 — preflight",
        skill="implement",
        if_latest_differs=True,
    )
    assert rust_runtime.timing_record_vendor_task(
        runner,
        vendor="claude",
        task_kind="reviewer-collect",
        start_s=10,
        end_s=25,
        output="collector.out",
        skill="implement",
        ledger="/tmp/ledger.tsv",
        environment={"IMPLEMENT_TMPDIR": "/tmp"},
    )
    assert rust_runtime.timing_record_round(
        runner,
        skill="design",
        step="design Step 3 — plan review",
        round_num=2,
        start_s=30,
        end_s=45,
        accepted=1,
        rejected=0,
        oos=3,
        ledger="/tmp/ledger.tsv",
        environment={"DESIGN_TMPDIR": "/tmp"},
    )
    assert rust_runtime.timing_record_round(
        runner,
        skill="design",
        step="design Step 3 — plan review",
        round_num=3,
        start_s=50,
        end_s=65,
        accepted=0,
        rejected=0,
        ledger="/tmp/ledger.tsv",
        if_round_exists=True,
        environment={"DESIGN_TMPDIR": "/tmp"},
    )

    assert runner.calls[0][1:] == [
        "timing",
        "mark",
        "--if-latest-differs",
        "Step 0 — preflight",
    ]
    assert runner.calls[1][1:] == [
        "timing",
        "record-vendor-task",
        "--ledger",
        "/tmp/ledger.tsv",
        "--vendor",
        "claude",
        "--task-kind",
        "reviewer-collect",
        "--start-s",
        "10",
        "--end-s",
        "25",
        "--output",
        "collector.out",
        "--exit-code",
        "0",
        "--status",
        "complete",
    ]
    assert runner.calls[2][1:] == [
        "timing",
        "record-round",
        "--ledger",
        "/tmp/ledger.tsv",
        "--skill",
        "design",
        "--step",
        "design Step 3 — plan review",
        "--round",
        "2",
        "--start-s",
        "30",
        "--end-s",
        "45",
        "--accepted",
        "1",
        "--rejected",
        "0",
        "--oos",
        "3",
    ]
    assert runner.records[1].env is not None
    assert runner.records[1].env["LARCH_TIMING_SKILL"] == "implement"
    assert runner.records[1].env["LARCH_TIMING_LEDGER"] == "/tmp/ledger.tsv"
    assert "--oos" not in runner.calls[3]
    assert runner.calls[3][-1] == "--if-round-exists"


def test_dirty_tree_commands_relay_validated_rust_envelopes() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("larch", "dirty-tree", "checkpoint"),
                0,
                "STATUS=clean\nMODE=checkpoint\n",
                "",
                0.01,
            ),
            CommandResult(
                ("larch", "dirty-tree", "baseline"),
                0,
                "STATUS=clean\nMODE=baseline\nUNTRACKED_BASELINE=missing\n",
                "",
                0.01,
            ),
        ],
    )

    checkpoint = dirty_tree_checkpoint(runner, cwd="/consumer")
    baseline = dirty_tree_baseline(
        runner,
        baseline_path="missing.z",
        sidecar="result.dirty-tree",
        cwd="/consumer",
    )

    assert checkpoint.lines == ("STATUS=clean", "MODE=checkpoint")
    assert baseline.lines == (
        "STATUS=clean",
        "MODE=baseline",
        "UNTRACKED_BASELINE=missing",
    )
    assert runner.calls[0][-2:] == ["dirty-tree", "checkpoint"]
    assert runner.calls[1][-6:] == [
        "dirty-tree",
        "baseline",
        "--baseline",
        "missing.z",
        "--sidecar",
        "result.dirty-tree",
    ]


def test_issue_state_relays_the_validated_rust_envelope() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("larch", "issue", "state"),
                0,
                "STATE=OPEN\nURL=https://github.com/o/r/issues/7\nIS_PR=false\n",
                "",
                0.01,
            ),
            CommandResult(
                ("larch", "issue", "state"),
                0,
                "STATE=CLOSED\nURL=https://github.com/o/r/pull/8\nIS_PR=true\n",
                "",
                0.01,
            ),
        ],
    )

    issue = issue_state(runner, issue="7")
    pull_request = issue_state(runner, issue="8", repo="o/r")

    assert not issue.failed
    assert (issue.state, issue.url, issue.is_pr) == (
        "OPEN",
        "https://github.com/o/r/issues/7",
        False,
    )
    assert pull_request.is_pr is True
    assert runner.calls[0][-4:] == ["issue", "state", "--issue", "7"]
    assert runner.calls[1][-6:] == ["issue", "state", "--issue", "8", "--repo", "o/r"]


def test_issue_state_fails_closed_for_every_unusable_read() -> None:
    # A refusal envelope, a non-zero exit, and a truncated envelope must all read
    # as failed: an adopted issue is only entered when the state row is present.
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("larch", "issue", "state"),
                1,
                "FAILED=true\nERROR=gh issue view failed: could not resolve repo\n",
                "",
                0.01,
            ),
            CommandResult(("larch", "issue", "state"), 127, "", "missing", 0.01),
            CommandResult(("larch", "issue", "state"), 0, "URL=u\nIS_PR=false\n", "", 0.01),
        ],
    )

    for _ in range(3):
        result = issue_state(runner, issue="7")
        assert result.failed
        assert (result.state, result.url, result.is_pr) == ("", "", False)


def test_tracking_issue_wrappers_use_the_verified_runtime_and_type_each_envelope(
    tmp_path: Path,
) -> None:
    comment_file = tmp_path / "comment.md"
    _ = comment_file.write_text(
        "<!-- larch:diagrams v1 -->\n\nexisting\n", encoding="utf-8"
    )
    issue_body_file = tmp_path / "issue-body.md"
    issue_body = "# Plan\n\nbody\n"
    _ = issue_body_file.write_text(issue_body, encoding="utf-8")
    runner = RecordingRunner(
        responses=[
            CommandResult(("larch",), 0, "COMMENT_ID=11\nCOMMENT_URL=u#issuecomment-11\n", "", 0.01),
            CommandResult(("larch",), 0, "ISSUE_NUMBER=12\nISSUE_URL=https://example/issues/12\n", "", 0.01),
            CommandResult(("larch",), 0, "MARKED=true\nNEW_TITLE=[FALSE-POSITIVE] Work\n", "", 0.01),
            CommandResult(
                ("larch",),
                0,
                f"FOUND=true\nCOMMENT_ID=11\nCOMMENT_FILE={comment_file}\n",
                "",
                0.01,
            ),
            CommandResult(
                ("larch",),
                0,
                f"BODY_FILE={issue_body_file}\nBODY_SHA256={hashlib.sha256(issue_body.encode()).hexdigest()}\n",
                "",
                0.01,
            ),
            CommandResult(("larch",), 0, "RENAMED=true\nNEW_TITLE=[IMPLEMENTING] Work\n", "", 0.01),
            CommandResult(("larch",), 0, "COMMENT_ID=11\nCOMMENT_URL=u#issuecomment-11\nUPDATED=true\n", "", 0.01),
        ]
    )
    body = str(tmp_path / "body.md")

    comment = rust_runtime.tracking_issue_append_comment(
        runner, issue="7", body_file=body, repo="o/r", lifecycle_marker="started"
    )
    created = rust_runtime.tracking_issue_create(
        runner, title="Work", body_file=body, repo="o/r"
    )
    marked = rust_runtime.tracking_issue_mark_false_positive(
        runner, issue="7", repo="o/r"
    )
    read = rust_runtime.tracking_issue_read_marker(
        runner,
        issue="7",
        marker="<!-- larch:diagrams v1 -->",
        output_file=str(comment_file),
        repo="o/r",
    )
    body_read = rust_runtime.tracking_issue_read_body(
        runner,
        issue="7",
        output_file=str(issue_body_file),
        repo="o/r",
    )
    renamed = rust_runtime.tracking_issue_rename(
        runner,
        issue="7",
        state="implementing",
        repo="o/r",
        run_id="run-1",
        lease_branch="work",
        head_sha="a" * 40,
        expected_updated_at="2026-08-10T00:00:00Z",
        expected_body_sha256="b" * 64,
        expected_title_sha256="c" * 64,
        expected_labels_sha256="d" * 64,
    )
    upserted = rust_runtime.tracking_issue_upsert_summary(
        runner,
        issue="7",
        marker="<!-- larch:diagrams v1 -->",
        content_file=body,
        repo="o/r",
        run_id="run-1",
    )

    assert (comment.failed, comment.comment_id) == (False, "11")
    assert (created.failed, created.issue_number) == (False, "12")
    assert (marked.failed, marked.changed) == (False, True)
    assert not read.failed
    assert read.values["FOUND"] == "true"
    assert not body_read.failed
    assert (renamed.failed, renamed.changed) == (False, True)
    assert (upserted.failed, upserted.updated) == (False, True)
    assert all(Path(call[0]).name == "larch.sh" for call in runner.calls)
    assert runner.calls[5][1:] == [
        "tracking-issue",
        "rename",
        "--issue",
        "7",
        "--state",
        "implementing",
        "--repo",
        "o/r",
        "--run-id",
        "run-1",
        "--lease-branch",
        "work",
        "--head-sha",
        "a" * 40,
        "--expected-updated-at",
        "2026-08-10T00:00:00Z",
        "--expected-body-sha256",
        "b" * 64,
        "--expected-title-sha256",
        "c" * 64,
        "--expected-labels-sha256",
        "d" * 64,
    ]
    assert runner.records[6].env is not None
    assert runner.records[6].env["RUN_ID"] == "run-1"


def test_tracking_issue_wrappers_fail_closed_for_refusals_and_missing_rows() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("larch",), 5, "FAILED=true\nERROR=unauthorized-mutation\n", "", 0.01),
            CommandResult(("larch",), 0, "RENAMED=true\n", "", 0.01),
            CommandResult(("larch",), 2, "", "FAILED=true\nERROR=ambiguous-comment-replay\n", 0.01),
            CommandResult(
                ("larch",),
                0,
                "ISSUE_NUMBER=7\nISSUE_NUMBER=8\nISSUE_URL=https://example/issues/8\n",
                "",
                0.01,
            ),
            CommandResult(
                ("larch",),
                0,
                "ISSUE_NUMBER=7\nISSUE_URL=https://example/issues/7\nUNEXPECTED=row\n",
                "",
                0.01,
            ),
        ]
    )

    created = rust_runtime.tracking_issue_create(
        runner, title="Work", body_file="body.md"
    )
    renamed = rust_runtime.tracking_issue_rename(
        runner, issue="7", state="done"
    )
    upserted = rust_runtime.tracking_issue_upsert_summary(
        runner,
        issue="7",
        marker="<!-- larch:x -->",
        content_file="body.md",
    )
    duplicated = rust_runtime.tracking_issue_create(
        runner, title="Work", body_file="body.md"
    )
    unexpected = rust_runtime.tracking_issue_create(
        runner, title="Work", body_file="body.md"
    )

    assert created.failed
    assert created.error == "unauthorized-mutation"
    assert renamed.failed
    assert upserted.failed
    assert upserted.error == "ambiguous-comment-replay"
    assert duplicated.failed
    assert duplicated.error == "conflicting tracking-issue envelope"
    assert unexpected.failed
    assert unexpected.error == "invalid tracking-issue envelope"


def test_tracking_issue_delete_refusal_survives_non_utf8_content(tmp_path: Path) -> None:
    content = tmp_path / "invalid.md"
    _ = content.write_bytes(b"\xff")
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("larch",),
                2,
                "",
                "FAILED=true\nERROR=content file was not UTF-8\n",
                0.01,
            )
        ]
    )

    result = rust_runtime.tracking_issue_upsert_summary(
        runner,
        issue="7",
        marker="<!-- larch:x -->",
        content_file=str(content),
        delete_if_empty=True,
    )

    assert result.failed
    assert result.error == "content file was not UTF-8"


def test_tracking_issue_sentinel_reader_is_typed_and_fails_closed() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("larch",),
                0,
                "ISSUE_NUMBER=7\nRUN_ID=run-1\nADOPTED=true\n",
                "",
                0.01,
            ),
            CommandResult(("larch",), 0, "ISSUE_NUMBER=0\n", "", 0.01),
            CommandResult(
                ("larch",),
                0,
                "ISSUE_NUMBER=7\nRUN_ID=run-1\nADOPTED=true\nFAILED=false\n",
                "FAILED=true\nERROR=refused\n",
                0.01,
            ),
            CommandResult(
                ("larch",),
                0,
                "ISSUE_NUMBER=7\nRUN_ID=run-1\nADOPTED=true\nFAILED=false\n",
                "",
                0.01,
            ),
        ]
    )

    read = rust_runtime.tracking_issue_read_sentinel(
        runner,
        sentinel="/tmp/parent-issue.md",
    )
    malformed = rust_runtime.tracking_issue_read_sentinel(
        runner,
        sentinel="/tmp/parent-issue.md",
    )
    conflicted = rust_runtime.tracking_issue_read_sentinel(
        runner,
        sentinel="/tmp/parent-issue.md",
    )
    false_success = rust_runtime.tracking_issue_read_sentinel(
        runner,
        sentinel="/tmp/parent-issue.md",
    )

    assert (read.failed, read.issue_number, read.run_id, read.adopted) == (
        False,
        "7",
        "run-1",
        "true",
    )
    assert malformed.failed
    assert conflicted.failed
    assert conflicted.error == "conflicting tracking-issue envelope"
    assert false_success.failed
    assert false_success.error == "invalid tracking-issue envelope"
    assert runner.calls[0][1:] == [
        "tracking-issue",
        "read",
        "--sentinel",
        "/tmp/parent-issue.md",
    ]


def test_tracking_issue_read_selects_its_envelope_from_flag_positions() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("larch",),
                0,
                "BODY_FILE=--sentinel\nBODY_SHA256=digest\n",
                "",
                0.01,
            )
        ]
    )

    read = rust_runtime.tracking_issue_read(
        runner,
        arguments=["--issue", "7", "--body-out", "--sentinel"],
    )

    assert not read.failed
    assert read.values == {"BODY_FILE": "--sentinel", "BODY_SHA256": "digest"}


def test_issue_info_relays_the_value_row_and_absent_refusals() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("larch", "issue", "info"),
                0,
                "VALUE=https://github.com/o/r/issues/7\n",
                "",
                0.01,
            ),
            CommandResult(("larch", "issue", "info"), 0, "VALUE=\n", "", 0.01),
            CommandResult(("larch", "issue", "info"), 1, "", "", 0.01),
        ],
    )

    assert (
        issue_info(runner, issue="7", field="url", repo="o/r")
        == "https://github.com/o/r/issues/7"
    )
    assert issue_info(runner, issue="7", field="url") == ""
    assert issue_info(runner, issue="7", field="url") == ""
    assert runner.calls[0][-8:] == [
        "issue",
        "info",
        "--issue",
        "7",
        "--field",
        "url",
        "--repo",
        "o/r",
    ]
    assert runner.calls[1][-6:] == ["issue", "info", "--issue", "7", "--field", "url"]


def test_run_log_refresh_parser_preserves_composite_wire_fields() -> None:
    success = rust_runtime._refresh_skip_from_result(  # pyright: ignore[reportPrivateUsage]
        CommandResult(("larch",), 0, "REFRESH_COMMITTED=true\n", "", 0.01),
    )
    skipped = rust_runtime._refresh_skip_from_result(  # pyright: ignore[reportPrivateUsage]
        CommandResult(
            ("larch",),
            0,
            "REFRESH_SKIPPED=true REASON=no-logs-commit\n",
            "",
            0.01,
        ),
    )
    blocked = rust_runtime._refresh_skip_from_result(  # pyright: ignore[reportPrivateUsage]
        CommandResult(
            ("larch",),
            0,
            "REFRESH_COMMITTED=false REASON=preterminal-outcome ERROR=terminal label refused\n",
            "",
            0.01,
        ),
    )

    assert not success.skipped
    assert (skipped.skipped, skipped.reason, skipped.error) == (
        True,
        "no-logs-commit",
        "",
    )
    assert (blocked.skipped, blocked.reason, blocked.error) == (
        True,
        "preterminal-outcome",
        "terminal label refused",
    )


def test_state_backed_refresh_omits_stale_context_merge_result() -> None:
    ctx = make_run_context(
        state_file="/tmp/session/ship-state.env",
        merge_result="merged",
    )

    persisted_args = rust_runtime._run_log_refresh_args(ctx)  # pyright: ignore[reportPrivateUsage]
    explicit_args = rust_runtime._run_log_refresh_args(  # pyright: ignore[reportPrivateUsage]
        ctx,
        merge_result="admin_merged",
    )

    assert "--merge-result" not in persisted_args
    index = explicit_args.index("--merge-result")
    assert explicit_args[index + 1] == "admin_merged"


def test_issue_add_blocked_by_relays_the_added_row_and_its_session_options() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("larch", "issue", "add-blocked-by"),
                0,
                "BLOCKED_BY_ADDED=true\nCLIENT=12\nBLOCKER=7\n",
                "",
                0.01,
            ),
        ],
    )

    result = issue_add_blocked_by(
        runner,
        client="12",
        blocker="7",
        blocker_id="9001",
        repo="o/r",
        context_file="/tmp/session/source-env.sh",
        run_id="run-1",
        trusted_root="/tmp/session",
    )

    assert result.added
    assert result.exit_code == 0
    assert result.error == ""
    assert runner.calls[0][1:] == [
        "issue",
        "add-blocked-by",
        "--client-issue",
        "12",
        "--blocker-issue",
        "7",
        "--blocker-id",
        "9001",
        "--repo",
        "o/r",
        "--context-file",
        "/tmp/session/source-env.sh",
        "--run-id",
        "run-1",
        "--trusted-root",
        "/tmp/session",
    ]


def test_issue_add_blocked_by_fails_closed_without_its_added_row() -> None:
    """A refusal and a zero exit with no added row are both unapplied edges."""
    refused = RecordingRunner(
        responses=[
            CommandResult(
                ("larch",),
                2,
                "BLOCKED_BY_FAILED=true\nCLIENT=12\nBLOCKER=7\nERROR=could not determine repo\n",
                "",
                0.01,
            ),
        ],
    )
    result = issue_add_blocked_by(refused, client="12", blocker="7")
    assert not result.added
    assert result.exit_code == 2
    assert result.error == "could not determine repo"

    silent = RecordingRunner(responses=[CommandResult(("larch",), 0, "", "boom", 0.01)])
    result = issue_add_blocked_by(silent, client="12", blocker="7")
    assert not result.added
    assert result.exit_code == 1
    assert result.error == "boom"


def test_block_issue_dependency_requires_both_receipt_rows() -> None:
    verified = RecordingRunner(
        responses=[
            CommandResult(
                ("larch",),
                0,
                "SUCCESS=true\nRELATION_VERIFIED=true\n",
                "",
                0.01,
            ),
        ],
    )
    assert block_issue_dependency(verified, remove=True, issue="12", blocker="7", repo="o/r")
    assert verified.calls[0][1:] == [
        "block-issue",
        "remove-blocked-by",
        "12",
        "7",
        "--repo",
        "o/r",
        "--operator-invoked",
    ]

    unproven = RecordingRunner(
        responses=[CommandResult(("larch",), 0, "SUCCESS=true\n", "", 0.01)],
    )
    assert not block_issue_dependency(
        unproven, remove=False, issue="12", blocker="7", repo="o/r"
    )
    assert unproven.calls[0][2] == "add-blocked-by"
