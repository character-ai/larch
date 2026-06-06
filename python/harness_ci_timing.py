"""Fetch and parse LARCH_HARNESS_TIMING rows from GitHub CI run logs.

Uses ``gh.run_log_read`` and ``gh.run_list_successful`` from the existing
gh.py library.  Exposes three public helpers:

- ``fetch_timing_rows`` — download log data for the last N successful CI runs
- ``compute_medians``   — {target: median_seconds} across all rows
- ``median_shard_totals`` — {shard: median_total_seconds} across all runs
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from collections.abc import Sequence

import gh
from proc import Runner


@dataclass(frozen=True)
class TimingRow:
    run_id: int
    shard: int
    target: str
    seconds: float


_JOB_SHARD_RE = re.compile(r"test-harnesses \((\d+)\)")
_TIMING_SENTINEL = "LARCH_HARNESS_TIMING\t"
_SECONDS_RE = re.compile(r"^(\d+(?:\.\d+)?)s$")


def fetch_timing_rows(
    runner: Runner,
    *,
    n_runs: int = 5,
    workflow: str = "ci.yaml",
    branch: str = "main",
    repo: str,
) -> list[TimingRow]:
    """Fetch LARCH_HARNESS_TIMING rows from the last *n_runs* successful CI runs.

    Downloads ``gh run view --log`` for each run and parses every
    ``LARCH_HARNESS_TIMING`` sentinel line emitted by ``harness-timer.sh``.
    Returns an empty list (not an exception) when a run's log cannot be
    fetched so a single transient failure does not abort the whole pass.
    """
    runs = gh.run_list_successful(
        runner, repo=repo, branch=branch, workflow=workflow, limit=n_runs
    )
    rows: list[TimingRow] = []
    for run in runs:
        result = gh.run_log_read(runner, run.database_id, repo=repo)
        if result.returncode != 0:
            continue
        rows.extend(parse_log(result.stdout, run.database_id))
    return rows


def parse_log(log: str, run_id: int) -> list[TimingRow]:
    r"""Parse ``LARCH_HARNESS_TIMING`` sentinel lines from a combined ``gh run --log`` blob.

    The combined log format from GitHub CLI is::

        <job_name>\t<step_name>\t[<timestamp> ]<log_content>

    ``harness-timer.sh`` emits::

        LARCH_HARNESS_TIMING\t<test-name>\t<N.NNs>

    so the timing tokens appear somewhere after the second tab, possibly
    preceded by a timestamp.  We search for the sentinel substring rather
    than relying on a fixed column count so the parser is robust to format
    variations.
    """
    rows: list[TimingRow] = []
    for line in log.splitlines():
        idx = line.find(_TIMING_SENTINEL)
        if idx == -1:
            continue

        # Job name is everything before the first tab
        first_tab = line.find("\t")
        job_name = line[:first_tab] if first_tab >= 0 else ""
        shard_m = _JOB_SHARD_RE.search(job_name)
        if not shard_m:
            continue
        shard = int(shard_m.group(1))

        # Parse target and seconds from after the sentinel
        rest = line[idx + len(_TIMING_SENTINEL):]
        rest_parts = rest.split("\t", 1)
        if len(rest_parts) < 2:  # noqa: PLR2004
            continue
        target = rest_parts[0].strip()
        seconds_raw = rest_parts[1].strip()
        seconds_m = _SECONDS_RE.match(seconds_raw)
        if not seconds_m:
            continue

        rows.append(
            TimingRow(
                run_id=run_id,
                shard=shard,
                target=target,
                seconds=float(seconds_m.group(1)),
            )
        )
    return rows


def compute_medians(rows: Sequence[TimingRow]) -> dict[str, float]:
    """Return ``{target: median_seconds}`` across all timing rows."""
    by_target: dict[str, list[float]] = {}
    for row in rows:
        by_target.setdefault(row.target, []).append(row.seconds)
    return {t: statistics.median(times) for t, times in by_target.items()}


def shard_totals_per_run(rows: Sequence[TimingRow]) -> dict[int, dict[int, float]]:
    """Return ``{run_id: {shard: total_seconds}}`` — per-run shard wall times."""
    result: dict[int, dict[int, float]] = {}
    for row in rows:
        run_data = result.setdefault(row.run_id, {})
        run_data[row.shard] = run_data.get(row.shard, 0.0) + row.seconds
    return result


def median_shard_totals(rows: Sequence[TimingRow]) -> dict[int, float]:
    """Return ``{shard: median_total_seconds}`` across all runs.

    First computes per-run shard totals, then takes the median of those totals
    across runs so a single outlier run does not dominate the result.
    """
    per_run = shard_totals_per_run(rows)
    by_shard: dict[int, list[float]] = {}
    for run_data in per_run.values():
        for shard, total in run_data.items():
            by_shard.setdefault(shard, []).append(total)
    return {shard: statistics.median(totals) for shard, totals in by_shard.items()}
