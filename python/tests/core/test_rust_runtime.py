"""Tests for thin Python consumers of Rust-owned commands."""

from __future__ import annotations

from larch.core import rust_runtime
from larch.core.proc import CommandResult
from larch.core.rust_runtime import (
    dirty_tree_baseline,
    dirty_tree_checkpoint,
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
