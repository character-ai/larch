"""Fetch and parse pytest ``--durations=0`` rows from CI logs."""

from __future__ import annotations

import re
import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from ci_timing_fetch import fetch_parsed_timing_rows
from larch.core.proc import Runner


@dataclass(frozen=True)
class PytestTimingRow:
    run_id: int
    shard: int
    nodeid: str
    seconds: float
    attempt: int
    shard_total: int | None = None


_DURATION_RE = re.compile(r"^(\d+(?:\.\d+)?)s\s+(call|setup|teardown)\s+(.+)$")
_SLOWEST_BANNER_RE = re.compile(r"slowest\s+(?:\d+\s+)?durations", re.IGNORECASE)
_JOB_PYTHON_RE = re.compile(r"\bpython-tests\b")
_JOB_SHARD_RE = re.compile(r"python-tests\s*\([^)]*,\s*(\d+)\)")
_STEP_SHARD_RE = re.compile(r"shard\s+(\d+)\s+of\s+(\d+)", re.IGNORECASE)
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\S+Z\s+")


def _split_log_line(line: str) -> tuple[str, str, str]:
    parts = line.split("\t", 2)
    if len(parts) == 3:  # noqa: PLR2004
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:  # noqa: PLR2004
        return parts[0], "", parts[1]
    return "", "", line


def _parse_shard(*, job_name: str, step_name: str) -> tuple[int | None, int | None]:
    step_match: re.Match[str] | None = _STEP_SHARD_RE.search(step_name)
    if step_match:
        return int(step_match.group(1)), int(step_match.group(2))
    job_match: re.Match[str] | None = _JOB_SHARD_RE.search(job_name)
    if job_match:
        return int(job_match.group(1)), None
    return None, None


def parse_log(log: str, run_id: int) -> list[PytestTimingRow]:  # lint-keyword-only: ok callback passed to fetch_parsed_timing_rows
    """Parse pytest ``call`` duration rows from a combined ``gh run --log`` blob."""
    rows: list[PytestTimingRow] = []
    attempts: dict[tuple[str, str], int] = {}
    for line in log.splitlines():
        job_name, step_name, content = _split_log_line(line)
        if not _JOB_PYTHON_RE.search(job_name):
            continue
        shard, shard_total = _parse_shard(job_name=job_name, step_name=step_name)
        if shard is None:
            continue
        key = (job_name, step_name)
        content = _TIMESTAMP_RE.sub("", content.strip())
        if _SLOWEST_BANNER_RE.search(content):
            attempts[key] = attempts.get(key, 0) + 1
            continue
        match: re.Match[str] | None = _DURATION_RE.match(content)
        if match is None or match.group(2) != "call":
            continue
        current_attempt = attempts.get(key, 0)
        if current_attempt == 0:
            continue
        rows.append(
            PytestTimingRow(
                run_id=run_id,
                shard=shard,
                nodeid=match.group(3).strip(),
                seconds=float(match.group(1)),
                attempt=current_attempt,
                shard_total=shard_total,
            )
        )
    return rows


def fetch_timing_rows(
    runner: Runner,
    *,
    n_runs: int = 5,
    workflow: str = "ci.yaml",
    branch: str = "main",
    repo: str,
) -> list[PytestTimingRow]:
    """Fetch pytest timing rows from recent successful CI runs."""
    return fetch_parsed_timing_rows(
        runner,
        parse_log=parse_log,
        n_runs=n_runs,
        workflow=workflow,
        branch=branch,
        repo=repo,
    )


def compute_medians(rows: Sequence[PytestTimingRow]) -> dict[str, float]:
    """Return ``{nodeid: median_call_seconds}`` across timing rows."""
    by_nodeid: dict[str, list[float]] = {}
    for row in rows:
        by_nodeid.setdefault(row.nodeid, []).append(row.seconds)
    return {nodeid: statistics.median(times) for nodeid, times in by_nodeid.items()}


def observed_shard_count(rows: Sequence[PytestTimingRow]) -> int | None:
    """Return the observed CI shard count, or ``None`` on conflicting totals."""
    totals = {row.shard_total for row in rows if row.shard_total is not None}
    if len(totals) == 1:
        return next(iter(totals))
    if len(totals) > 1:
        return None
    if not rows:
        return None
    return max(row.shard for row in rows)


def _split_pytest_shard_attempts(
    shard_rows: Sequence[PytestTimingRow],
) -> list[list[PytestTimingRow]]:
    """Split ordered rows for one shard by duration-section attempt number."""
    attempts: list[list[PytestTimingRow]] = []
    current_attempt: int | None = None
    for row in shard_rows:
        if current_attempt is None or row.attempt != current_attempt:
            attempts.append([row])
            current_attempt = row.attempt
        else:
            attempts[-1].append(row)
    return attempts


def rows_latest_attempt_per_shard(
    rows: Sequence[PytestTimingRow],
) -> list[PytestTimingRow]:
    """Keep only the latest duration-section attempt per ``(run_id, shard)``."""
    by_run_shard: dict[tuple[int, int], list[PytestTimingRow]] = {}
    for row in rows:
        by_run_shard.setdefault((row.run_id, row.shard), []).append(row)
    latest: list[PytestTimingRow] = []
    for shard_rows in by_run_shard.values():
        attempts = _split_pytest_shard_attempts(shard_rows)
        if attempts:
            latest.extend(attempts[-1])
    return latest


def shard_totals_per_run(rows: Sequence[PytestTimingRow]) -> dict[int, dict[int, float]]:
    """Return ``{run_id: {shard: total_call_seconds}}`` using latest attempts."""
    by_run_shard: dict[tuple[int, int], list[PytestTimingRow]] = {}
    for row in rows:
        by_run_shard.setdefault((row.run_id, row.shard), []).append(row)

    result: dict[int, dict[int, float]] = {}
    for (run_id, shard), shard_rows in by_run_shard.items():
        attempts = _split_pytest_shard_attempts(shard_rows)
        total = sum(row.seconds for row in attempts[-1]) if attempts else 0.0
        result.setdefault(run_id, {})[shard] = total
    return result


def median_shard_totals(rows: Sequence[PytestTimingRow]) -> dict[int, float]:
    """Return ``{shard: median_total_seconds}`` across CI runs."""
    per_run = shard_totals_per_run(rows)
    by_shard: dict[int, list[float]] = {}
    for run_data in per_run.values():
        for shard, total in run_data.items():
            by_shard.setdefault(shard, []).append(total)
    return {shard: statistics.median(totals) for shard, totals in by_shard.items()}
