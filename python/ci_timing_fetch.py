"""Shared fetch loop for CI timing log parsers."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

from larch.git import gh
from larch.core.proc import Runner

T = TypeVar("T")


def fetch_parsed_timing_rows(
    runner: Runner,
    *,
    parse_log: Callable[[str, int], Sequence[T]],
    n_runs: int = 5,
    workflow: str = "ci.yaml",
    branch: str = "main",
    repo: str,
) -> list[T]:
    """Fetch and parse timing rows from recent successful CI runs.

    A failed log read is skipped so one transient ``gh run view --log`` failure
    does not discard the whole baseline sample.
    """
    runs = gh.run_list_successful(
        runner, repo=repo, branch=branch, workflow=workflow, limit=n_runs
    )
    rows: list[T] = []
    for run in runs:
        result = gh.run_log_read(runner, run.database_id, repo=repo)
        if result.returncode != 0:
            continue
        rows.extend(parse_log(result.stdout, run.database_id))
    return rows
