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

from ci_timing_fetch import fetch_parsed_timing_rows
from larch.core.proc import Runner


@dataclass(frozen=True)
class TimingRow:
    run_id: int
    shard: int
    target: str
    seconds: float


_JOB_SLICE_RE = re.compile(r"test-harnesses \((\d+)\)")
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
    ``LARCH_HARNESS_TIMING`` sentinel line emitted by ``python3 python/cli.py timing harness-mark``.
    Returns an empty list (not an exception) when a run's log cannot be
    fetched so a single transient failure does not abort the whole pass.
    """
    return fetch_parsed_timing_rows(
        runner,
        parse_log=parse_log,
        n_runs=n_runs,
        workflow=workflow,
        branch=branch,
        repo=repo,
    )


def parse_log(log: str, run_id: int) -> list[TimingRow]:  # lint-keyword-only: ok callback passed to fetch_parsed_timing_rows
    r"""Parse ``LARCH_HARNESS_TIMING`` sentinel lines from a combined ``gh run --log`` blob.

    The combined log format from GitHub CLI is::

        <job_name>\t<step_name>\t[<timestamp> ]<log_content>

    ``python3 python/cli.py timing harness-mark`` emits::

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
        shard_m: re.Match[str] | None = _JOB_SLICE_RE.search(job_name)
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
        seconds_m: re.Match[str] | None = _SECONDS_RE.match(seconds_raw)
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


def _split_shard_attempts(shard_rows: Sequence[TimingRow]) -> list[list[TimingRow]]:
    """Split ordered rows for one ``(run_id, shard)`` into job attempts.

    Multi-bash Makefile targets emit consecutive rows with the same target
    label.  A retried matrix job replays the shard from the first target, so a
    non-consecutive repeat of the opening target starts a new attempt.

    A *single-target* shard (one heavy target given its own slice, e.g.
    ``test-harnesses-1``) is the exception: its retry replays that lone target,
    so the opening target reappears *consecutively* and the
    non-consecutive-repeat heuristic never fires — every repeat would otherwise
    be misread as a multi-bash continuation and summed.  Treat each row of a
    single-target shard as its own attempt so the caller keeps only the latest
    (dedupes the retry) instead of summing every attempt.  Single-target shards
    in this repo run single-bash targets; a hypothetical single-target
    *multi-bash* shard would be mis-split here, but heavy multi-bash targets
    always share a slice with sibling targets.
    """
    if not shard_rows:
        return []
    if len({row.target for row in shard_rows}) == 1:
        return [[row] for row in shard_rows]
    attempts: list[list[TimingRow]] = [[shard_rows[0]]]
    first_target = shard_rows[0].target
    for row in shard_rows[1:]:
        prev = attempts[-1][-1]
        if row.target == prev.target:
            attempts[-1].append(row)
        elif row.target == first_target:
            attempts.append([row])
            first_target = row.target
        else:
            attempts[-1].append(row)
    return attempts


def shard_totals_per_run(rows: Sequence[TimingRow]) -> dict[int, dict[int, float]]:
    """Return ``{run_id: {shard: total_seconds}}`` — per-run shard wall times.

    Sums every timing row in the latest job attempt for each shard.  Multi-bash
    Makefile targets emit consecutive rows with the same label (for example
    ``test-harness-shards-coverage``); those rows are all counted.  When
    ``gh run view --log`` includes retried matrix job output, only the latest
    attempt is kept so targets are not double-counted across retries.
    """
    by_run_shard: dict[tuple[int, int], list[TimingRow]] = {}
    for row in rows:
        by_run_shard.setdefault((row.run_id, row.shard), []).append(row)

    result: dict[int, dict[int, float]] = {}
    for (run_id, shard), shard_rows in by_run_shard.items():
        attempts = _split_shard_attempts(shard_rows)
        total = sum(r.seconds for r in attempts[-1])
        result.setdefault(run_id, {})[shard] = total
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


def untimed_targets(
    *, all_shard_targets: Sequence[str],
    medians: dict[str, float],
) -> list[str]:
    """Return shard targets with no timing data, de-duplicated, order-preserving.

    A target is *untimed* when no ``LARCH_HARNESS_TIMING`` row yielded a median
    for it across the sampled runs — either its Makefile recipe is missing the
    ``timing harness-mark`` wrapper, or it has never run in the sampled CI.

    The rebalancer refuses to proceed when this list is non-empty: an untimed
    target is invisible to the LPT packer, which assigns it zero weight and
    piles it onto whichever shard it believes is lightest, producing an
    unbalanced "monster" shard whose real wall-clock the balancer never sees.
    """
    seen: set[str] = set()
    out: list[str] = []
    for target in all_shard_targets:
        if target not in medians and target not in seen:
            seen.add(target)
            out.append(target)
    return out
