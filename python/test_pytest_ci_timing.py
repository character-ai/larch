"""Tests for pytest CI timing parsing."""

from __future__ import annotations

from proc import CommandResult
from pytest_ci_timing import (
    PytestTimingRow,
    compute_medians,
    fetch_timing_rows,
    median_shard_totals,
    observed_shard_count,
    parse_log,
    rows_latest_attempt_per_shard,
    shard_totals_per_run,
)
from test_support import RecordingRunner


def _cr(stdout: str = "", rc: int = 0) -> CommandResult:
    return CommandResult((), rc, stdout, "", 0.01)


def test_parse_log_python_test_rows_and_preserves_param_nodeid() -> None:
    log = (
        "python-tests (3.11, 2)\tRun Python tests (shard 2 of 4)\t"
        "============================= slowest durations =============================\n"
        "python-tests (3.11, 2)\tRun Python tests (shard 2 of 4)\t"
        "2026-01-01T00:00:00.000Z 1.25s call     test_x.py::test_y[param]\n"
        "python-tests (3.11, 2)\tRun Python tests (shard 2 of 4)\t"
        "0.50s setup    test_x.py::test_y[param]\n"
        "test-harnesses (2)\tRun\t9.99s call     ignored.py::test_no\n"
    )

    rows = parse_log(log=log, run_id=7)

    assert rows == [
        PytestTimingRow(
            run_id=7,
            shard=2,
            nodeid="test_x.py::test_y[param]",
            seconds=1.25,
            attempt=1,
            shard_total=4,
        )
    ]


def test_parse_log_accepts_integer_seconds_and_job_name_shard_fallback() -> None:
    log = (
        "python-tests (3.11, 3)\tRun Python tests\tslowest 1 durations\n"
        "python-tests (3.11, 3)\tRun Python tests\t7s call     test_a.py::test_b\n"
    )
    rows = parse_log(log=log, run_id=1)
    assert rows[0].shard == 3
    assert rows[0].seconds == 7.0
    assert rows[0].shard_total is None


def test_parse_log_ignores_malformed_duration_and_missing_shard() -> None:
    log = (
        "python-tests\tRun Python tests\tnotnum call     test_a.py::test_b\n"
        "python-tests\tRun Python tests\t1.0s call     test_a.py::test_b\n"
    )
    assert not parse_log(log=log, run_id=1)


def test_observed_shard_count_prefers_total_over_max_shard() -> None:
    rows = [
        PytestTimingRow(1, 1, "a", 1.0, 1, 4),
        PytestTimingRow(1, 3, "b", 1.0, 1, 4),
    ]
    assert observed_shard_count(rows) == 4


def test_observed_shard_count_conflict_and_fallback() -> None:
    assert observed_shard_count([]) is None
    assert observed_shard_count([PytestTimingRow(1, 3, "a", 1.0, 1, None)]) == 3
    assert observed_shard_count(
        [
            PytestTimingRow(1, 1, "a", 1.0, 1, 4),
            PytestTimingRow(1, 2, "b", 1.0, 1, 5),
        ]
    ) is None


def test_duration_banners_increment_attempts() -> None:
    log = (
        "python-tests (3.11, 1)\tRun Python tests (shard 1 of 4)\tslowest 5 durations\n"
        "python-tests (3.11, 1)\tRun Python tests (shard 1 of 4)\t1.0s call     first.py::test\n"
        "python-tests (3.11, 1)\tRun Python tests (shard 1 of 4)\tslowest 312 durations\n"
        "python-tests (3.11, 1)\tRun Python tests (shard 1 of 4)\t2.0s call     second.py::test\n"
    )
    assert [row.attempt for row in parse_log(log=log, run_id=1)] == [1, 2]


def test_parse_log_ignores_pre_banner_duration_rows() -> None:
    log = (
        "python-tests (3.11, 1)\tRun Python tests (shard 1 of 4)\t1.0s call     stale.py::test\n"
        "python-tests (3.11, 1)\tRun Python tests (shard 1 of 4)\tSlowest Durations\n"
        "python-tests (3.11, 1)\tRun Python tests (shard 1 of 4)\t2.0s call     fresh.py::test\n"
    )
    rows = parse_log(log=log, run_id=1)
    assert len(rows) == 1
    assert rows[0].nodeid == "fresh.py::test"
    assert rows[0].attempt == 1


def test_parse_log_retry_banner_splits_attempts_with_different_first_nodeid() -> None:
    log = (
        "python-tests (3.11, 1)\tRun Python tests (shard 1 of 4)\tslowest 5 durations\n"
        "python-tests (3.11, 1)\tRun Python tests (shard 1 of 4)\t10.0s call     test_a.py::test_old\n"
        "python-tests (3.11, 1)\tRun Python tests (shard 1 of 4)\tslowest 5 durations\n"
        "python-tests (3.11, 1)\tRun Python tests (shard 1 of 4)\t2.0s call     test_c.py::test_new\n"
    )
    rows = parse_log(log=log, run_id=1)
    assert [row.nodeid for row in rows] == ["test_a.py::test_old", "test_c.py::test_new"]
    assert [row.attempt for row in rows] == [1, 2]
    assert shard_totals_per_run(rows) == {1: {1: 2.0}}


def test_retry_dedup_uses_latest_attempt_even_with_different_first_nodeid() -> None:
    rows = [
        PytestTimingRow(1, 1, "test_a.py::test_old", 10.0, 1, 4),
        PytestTimingRow(1, 1, "test_b.py::test_old", 5.0, 1, 4),
        PytestTimingRow(1, 1, "test_c.py::test_new", 2.0, 2, 4),
        PytestTimingRow(1, 1, "test_d.py::test_new", 3.0, 2, 4),
    ]

    assert shard_totals_per_run(rows) == {1: {1: 5.0}}
    latest = rows_latest_attempt_per_shard(rows)
    assert [row.nodeid for row in latest] == ["test_c.py::test_new", "test_d.py::test_new"]
    assert compute_medians(latest) == {
        "test_c.py::test_new": 2.0,
        "test_d.py::test_new": 3.0,
    }


def test_median_shard_totals_uses_deduped_per_run_totals() -> None:
    rows = [
        PytestTimingRow(1, 1, "a", 10.0, 1, 2),
        PytestTimingRow(1, 1, "b", 2.0, 2, 2),
        PytestTimingRow(2, 1, "a", 4.0, 1, 2),
        PytestTimingRow(2, 2, "c", 8.0, 1, 2),
    ]
    assert median_shard_totals(rows) == {1: 3.0, 2: 8.0}


def test_fetch_timing_rows_happy_path_and_failed_log_skip() -> None:
    runner = RecordingRunner(
        responses=[
            _cr('[{"databaseId":1,"status":"completed","conclusion":"success"},{"databaseId":2,"status":"completed","conclusion":"success"}]'),
            _cr(
                "python-tests (3.11, 1)\tRun Python tests (shard 1 of 4)\tslowest 1 durations\n"
                "python-tests (3.11, 1)\tRun Python tests (shard 1 of 4)\t1.0s call     test_a.py::test\n"
            ),
            _cr("", rc=1),
        ]
    )

    rows = fetch_timing_rows(runner, repo="o/r", n_runs=2)

    assert len(rows) == 1
    assert rows[0].run_id == 1
