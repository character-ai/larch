"""Tests for shared CI timing fetch loop."""

from __future__ import annotations

from ci_timing_fetch import fetch_parsed_timing_rows
from larch.core.proc import CommandResult
from test_support import RecordingRunner


def _cr(stdout: str = "", rc: int = 0) -> CommandResult:
    return CommandResult((), rc, stdout, "", 0.01)


def test_fetch_parsed_timing_rows_aggregates_runs() -> None:
    runner = RecordingRunner(
        responses=[
            _cr('[{"databaseId":1,"status":"completed","conclusion":"success"},{"databaseId":2,"status":"completed","conclusion":"success"}]'),
            _cr("a"),
            _cr("bb"),
        ]
    )

    rows = fetch_parsed_timing_rows(
        runner,
        parse_log=lambda log, run_id: [f"{run_id}:{log}"],
        repo="o/r",
        n_runs=2,
    )

    assert rows == ["1:a", "2:bb"]


def test_fetch_parsed_timing_rows_skips_failed_log_fetch() -> None:
    runner = RecordingRunner(
        responses=[
            _cr('[{"databaseId":1,"status":"completed","conclusion":"success"},{"databaseId":2,"status":"completed","conclusion":"success"}]'),
            _cr("", rc=1),
            _cr("ok"),
        ]
    )

    rows = fetch_parsed_timing_rows(
        runner,
        parse_log=lambda log, run_id: [(run_id, log)],
        repo="o/r",
        n_runs=2,
    )

    assert rows == [(2, "ok")]


def test_fetch_parsed_timing_rows_passes_run_id_to_parser() -> None:
    seen: list[int] = []

    def parse_log(_log: str, run_id: int) -> list[int]:
        seen.append(run_id)
        return [run_id]

    runner = RecordingRunner(
        responses=[_cr('[{"databaseId":42,"status":"completed","conclusion":"success"}]'), _cr("log")]
    )

    assert fetch_parsed_timing_rows(runner, parse_log=parse_log, repo="o/r") == [42]
    assert seen == [42]
