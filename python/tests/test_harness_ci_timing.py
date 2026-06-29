"""Tests for harness_ci_timing."""

from __future__ import annotations

from harness_ci_timing import (
    TimingRow,
    compute_medians,
    fetch_timing_rows,
    median_shard_totals,
    parse_log,
    shard_totals_per_run,
    untimed_targets,
)
from larch.core.proc import CommandResult
from test_support import RecordingRunner


def _cr(stdout: str = "", rc: int = 0) -> CommandResult:
    return CommandResult((), rc, stdout, "", 0.01)


# ---------------------------------------------------------------------------
# _parse_log
# ---------------------------------------------------------------------------


def test_parse_log_basic() -> None:
    log = (
        "test-harnesses (1)\tRun test harnesses (shard 1 of 20)\tLARCH_HARNESS_TIMING\ttest-foo\t1.23s\n"
        "test-harnesses (2)\tRun test harnesses (shard 2 of 20)\tLARCH_HARNESS_TIMING\ttest-bar\t2.00s\n"
    )
    rows = parse_log(log=log, run_id=42)
    assert len(rows) == 2
    assert rows[0] == TimingRow(run_id=42, shard=1, target="test-foo", seconds=1.23)
    assert rows[1] == TimingRow(run_id=42, shard=2, target="test-bar", seconds=2.00)


def test_parse_log_with_timestamp_prefix() -> None:
    # GitHub may prepend a timestamp to the log-content column.
    log = (
        "test-harnesses (3)\tRun test harnesses\t"
        "2024-01-01T00:00:00.0000000Z LARCH_HARNESS_TIMING\ttest-baz\t0.50s\n"
    )
    rows = parse_log(log=log, run_id=1)
    assert len(rows) == 1
    assert rows[0].target == "test-baz"
    assert rows[0].seconds == 0.50
    assert rows[0].shard == 3


def test_parse_log_integer_seconds() -> None:
    log = "test-harnesses (5)\tRun\tLARCH_HARNESS_TIMING\ttest-x\t7s\n"
    rows = parse_log(log=log, run_id=1)
    assert len(rows) == 1
    assert rows[0].seconds == 7.0


def test_parse_log_skips_non_timing_lines() -> None:
    log = "test-harnesses (1)\tRun test\tsome unrelated log line\n"
    assert not parse_log(log=log, run_id=1)


def test_parse_log_skips_unrecognised_shard_job() -> None:
    log = "unknown-job\tStep\tLARCH_HARNESS_TIMING\ttest-foo\t1.00s\n"
    assert not parse_log(log=log, run_id=1)


def test_parse_log_skips_malformed_seconds() -> None:
    log = "test-harnesses (1)\tRun\tLARCH_HARNESS_TIMING\ttest-foo\tnotanumber\n"
    assert not parse_log(log=log, run_id=1)


def test_parse_log_multi_bash_same_target_is_summed_via_compute() -> None:
    # harness-timer emits one row per bash invocation for multi-bash targets;
    # _parse_log returns all of them — compute_medians later aggregates.
    log = (
        "test-harnesses (1)\tRun\tLARCH_HARNESS_TIMING\ttest-multi\t1.00s\n"
        "test-harnesses (1)\tRun\tLARCH_HARNESS_TIMING\ttest-multi\t2.00s\n"
    )
    rows = parse_log(log=log, run_id=1)
    assert len(rows) == 2
    assert all(r.target == "test-multi" for r in rows)


# ---------------------------------------------------------------------------
# compute_medians
# ---------------------------------------------------------------------------


def test_compute_medians_single_value() -> None:
    rows = [TimingRow(run_id=1, shard=1, target="test-foo", seconds=5.0)]
    assert compute_medians(rows) == {"test-foo": 5.0}


def test_compute_medians_odd_count() -> None:
    rows = [
        TimingRow(run_id=1, shard=1, target="test-foo", seconds=2.0),
        TimingRow(run_id=2, shard=1, target="test-foo", seconds=4.0),
        TimingRow(run_id=3, shard=1, target="test-foo", seconds=3.0),
    ]
    assert compute_medians(rows)["test-foo"] == 3.0


def test_compute_medians_even_count() -> None:
    rows = [
        TimingRow(run_id=1, shard=1, target="test-foo", seconds=2.0),
        TimingRow(run_id=2, shard=1, target="test-foo", seconds=4.0),
    ]
    assert compute_medians(rows)["test-foo"] == 3.0


def test_compute_medians_multiple_targets() -> None:
    rows = [
        TimingRow(run_id=1, shard=1, target="test-a", seconds=10.0),
        TimingRow(run_id=1, shard=2, target="test-b", seconds=5.0),
    ]
    m = compute_medians(rows)
    assert m["test-a"] == 10.0
    assert m["test-b"] == 5.0


def test_compute_medians_empty() -> None:
    assert compute_medians([]) == {}


# ---------------------------------------------------------------------------
# shard_totals_per_run
# ---------------------------------------------------------------------------


def test_shard_totals_per_run_basic() -> None:
    rows = [
        TimingRow(run_id=1, shard=1, target="test-a", seconds=10.0),
        TimingRow(run_id=1, shard=1, target="test-b", seconds=5.0),
        TimingRow(run_id=1, shard=2, target="test-c", seconds=20.0),
    ]
    per_run = shard_totals_per_run(rows)
    assert per_run[1][1] == 15.0
    assert per_run[1][2] == 20.0


def test_shard_totals_per_run_retried_shard_uses_latest_attempt() -> None:
    # A retried matrix job replays the shard from its first target, so the
    # opening target reappears non-consecutively. Only the latest attempt
    # counts; summing both attempts would double the total to 35.0.
    rows = [
        TimingRow(run_id=1, shard=1, target="test-a", seconds=10.0),
        TimingRow(run_id=1, shard=1, target="test-b", seconds=5.0),
        TimingRow(run_id=1, shard=1, target="test-a", seconds=12.0),
        TimingRow(run_id=1, shard=1, target="test-b", seconds=8.0),
    ]
    per_run = shard_totals_per_run(rows)
    assert per_run[1][1] == 20.0


def test_shard_totals_per_run_multi_bash_rows_all_summed() -> None:
    # Multi-bash targets emit consecutive rows with the same label; a
    # consecutive repeat of the first target is NOT a retry, so every row
    # in the single attempt is summed (1+2+3+4 == 10.0).
    rows = [
        TimingRow(run_id=1, shard=1, target="test-multi", seconds=1.0),
        TimingRow(run_id=1, shard=1, target="test-multi", seconds=2.0),
        TimingRow(run_id=1, shard=1, target="test-multi", seconds=3.0),
        TimingRow(run_id=1, shard=1, target="test-other", seconds=4.0),
    ]
    per_run = shard_totals_per_run(rows)
    assert per_run[1][1] == 10.0


def test_shard_totals_per_run_retried_shard_with_multi_bash() -> None:
    # Retry + multi-bash combined: each attempt repeats a multi-bash target.
    # Only the latest attempt's rows count (4+5+6 == 15.0), not all six.
    rows = [
        TimingRow(run_id=1, shard=1, target="test-a", seconds=1.0),
        TimingRow(run_id=1, shard=1, target="test-a", seconds=2.0),
        TimingRow(run_id=1, shard=1, target="test-b", seconds=3.0),
        TimingRow(run_id=1, shard=1, target="test-a", seconds=4.0),
        TimingRow(run_id=1, shard=1, target="test-a", seconds=5.0),
        TimingRow(run_id=1, shard=1, target="test-b", seconds=6.0),
    ]
    per_run = shard_totals_per_run(rows)
    assert per_run[1][1] == 15.0


def test_shard_totals_per_run_single_target_retry_dedupes() -> None:
    # A single-target shard (one heavy target gets its own shard, e.g.
    # test-harnesses-1) replays that lone target on retry, so the rows repeat
    # *consecutively* and the non-consecutive-repeat retry heuristic never
    # fires. The retry must be deduped to the latest attempt (12.0), not
    # summed (10+12 == 22.0).
    rows = [
        TimingRow(run_id=1, shard=1, target="test-solo", seconds=10.0),
        TimingRow(run_id=1, shard=1, target="test-solo", seconds=12.0),
    ]
    per_run = shard_totals_per_run(rows)
    assert per_run[1][1] == 12.0


def test_shard_totals_per_run_single_target_multiple_retries_keeps_latest() -> None:
    # Several consecutive retries of a single-target shard keep only the most
    # recent attempt (13.0), never the sum of all three.
    rows = [
        TimingRow(run_id=1, shard=1, target="test-solo", seconds=10.0),
        TimingRow(run_id=1, shard=1, target="test-solo", seconds=11.0),
        TimingRow(run_id=1, shard=1, target="test-solo", seconds=13.0),
    ]
    per_run = shard_totals_per_run(rows)
    assert per_run[1][1] == 13.0


def test_shard_totals_per_run_single_target_no_retry_unchanged() -> None:
    # A single-target shard with no retry keeps its single timing untouched.
    rows = [TimingRow(run_id=1, shard=1, target="test-solo", seconds=9.0)]
    per_run = shard_totals_per_run(rows)
    assert per_run[1][1] == 9.0


# ---------------------------------------------------------------------------
# median_shard_totals
# ---------------------------------------------------------------------------


def test_median_shard_totals_two_runs() -> None:
    rows = [
        TimingRow(run_id=1, shard=1, target="test-a", seconds=10.0),
        TimingRow(run_id=1, shard=1, target="test-b", seconds=5.0),   # run1 shard1 = 15
        TimingRow(run_id=1, shard=2, target="test-c", seconds=20.0),  # run1 shard2 = 20
        TimingRow(run_id=2, shard=1, target="test-a", seconds=12.0),
        TimingRow(run_id=2, shard=1, target="test-b", seconds=8.0),   # run2 shard1 = 20
        TimingRow(run_id=2, shard=2, target="test-c", seconds=18.0),  # run2 shard2 = 18
    ]
    result = median_shard_totals(rows)
    assert result[1] == 17.5  # median([15, 20])
    assert result[2] == 19.0  # median([20, 18])


def test_median_shard_totals_single_run() -> None:
    rows = [TimingRow(run_id=1, shard=3, target="test-x", seconds=7.5)]
    assert median_shard_totals(rows) == {3: 7.5}


def test_median_shard_totals_empty() -> None:
    assert median_shard_totals([]) == {}


# ---------------------------------------------------------------------------
# fetch_timing_rows (integration smoke — uses RecordingRunner)
# ---------------------------------------------------------------------------


def test_fetch_timing_rows_happy_path() -> None:
    run_list_json = '[{"databaseId":99,"status":"completed","conclusion":"success"}]'
    timing_log = (
        "test-harnesses (1)\tRun test harnesses (shard 1 of 20)\t"
        "LARCH_HARNESS_TIMING\ttest-alpha\t3.14s\n"
    )
    runner = RecordingRunner(
        responses=[
            _cr(run_list_json),   # gh run list --status success ...
            _cr(timing_log),      # gh run view 99 --log ...
        ]
    )

    rows = fetch_timing_rows(runner, repo="owner/repo", n_runs=1)
    assert len(rows) == 1
    assert rows[0].target == "test-alpha"
    assert abs(rows[0].seconds - 3.14) < 1e-9
    assert rows[0].shard == 1
    assert rows[0].run_id == 99


def test_fetch_timing_rows_skips_failed_log_fetch() -> None:
    run_list_json = '[{"databaseId":7,"status":"completed","conclusion":"success"}]'
    runner = RecordingRunner(
        responses=[
            _cr(run_list_json),
            _cr("", rc=1),  # log fetch fails
        ]
    )
    rows = fetch_timing_rows(runner, repo="owner/repo", n_runs=1)
    assert not rows


def test_untimed_targets_flags_targets_absent_from_medians() -> None:
    all_targets = ["test-a", "test-b", "test-c", "test-d"]
    medians = {"test-a": 1.0, "test-c": 2.0}
    assert untimed_targets(all_shard_targets=all_targets, medians=medians) == ["test-b", "test-d"]


def test_untimed_targets_empty_when_all_present() -> None:
    all_targets = ["test-a", "test-b"]
    medians = {"test-a": 1.0, "test-b": 2.0}
    assert not untimed_targets(all_shard_targets=all_targets, medians=medians)


def test_untimed_targets_dedupes_preserving_first_seen_order() -> None:
    # A target repeated across shard lists must appear once, in first-seen order.
    all_targets = ["test-z", "test-a", "test-z", "test-a"]
    assert untimed_targets(all_shard_targets=all_targets, medians={}) == ["test-z", "test-a"]
