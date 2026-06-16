"""Tests for the dev-only rebalance.py helper surface."""

from __future__ import annotations

import contextlib
import importlib.util
import io
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


_REPO_ROOT = Path(__file__).resolve().parents[1]
_REBALANCE_PATH = (
    _REPO_ROOT / ".claude" / "skills" / "rebalance-test-harnesses" / "scripts" / "rebalance.py"
)


def _load_rebalance() -> ModuleType:
    spec = importlib.util.spec_from_file_location("rebalance_script", _REBALANCE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rebalance = _load_rebalance()


def _feasibility_output(
    shards: dict[int, list[str]],
    medians: dict[str, float],
    *,
    balance_threshold: float = 4.0,
) -> str:
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        rebalance._check_feasibility(shards, medians, balance_threshold)
    return stream.getvalue()


def test_packed_spread_over_threshold_emits_warning() -> None:
    medians = {
        "test-a": 10.0,
        "test-b": 10.0,
        "test-c": 10.0,
        "test-d": 10.0,
    }
    shards = rebalance.pack(medians, 3, guard="")
    output = _feasibility_output(
        shards,
        medians,
        balance_threshold=5.0,
    )

    assert "WARNING: packed workload may be infeasible" in output
    assert "Estimated packed spread: 10.0s" in output
    assert "Balance threshold: 5.0s" in output
    assert "Heaviest shard:" in output
    assert "Lightest shard:" in output


def test_dominant_target_with_packed_spread_within_threshold_emits_no_warning() -> None:
    medians = {
        "test-slow": 20.0,
        "test-medium-a": 14.0,
        "test-medium-b": 14.0,
    }
    shards = rebalance.pack(medians, 3, guard="")
    output = _feasibility_output(
        shards,
        medians,
        balance_threshold=6.0,
    )

    assert output == ""


def test_empty_measured_workload_emits_no_warning() -> None:
    output = _feasibility_output({}, {})

    assert output == ""


def test_zero_shards_emits_no_warning() -> None:
    output = _feasibility_output({}, {"test-slow": 20.0})

    assert output == ""


def test_orphan_medians_are_excluded_from_packed_shard_totals() -> None:
    medians = {
        "test-a": 6.0,
        "test-b": 6.0,
        "orphan-heavy": 100.0,
    }
    shards = {1: ["test-a"], 2: ["test-b"]}

    assert _feasibility_output(shards, medians) == ""


def _wall_clock_output(
    wall_clock: dict[int, float],
    *,
    max_shard_wall_clock: float,
) -> tuple[str, bool]:
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        result = rebalance._report_wall_clock_balance(
            wall_clock,
            max_shard_wall_clock=max_shard_wall_clock,
            n_verify_runs=3,
        )
    return stream.getvalue(), result


def test_wall_clock_within_budget_is_verified() -> None:
    # PR #4492 scenario from issue #4493: worst 54s, fastest 37s, 0 shards over 60s.
    output, balanced = _wall_clock_output(
        {1: 54.0, 2: 37.0, 3: 48.0},
        max_shard_wall_clock=60.0,
    )
    assert balanced is True
    assert "✓ Shard balance VERIFIED" in output
    assert "Slowest shard: 1 (54.0s)" in output
    assert "Spread (max-min): 17.0s" in output


def test_wall_clock_over_budget_fails_and_lists_offenders() -> None:
    output, balanced = _wall_clock_output(
        {1: 72.0, 2: 40.0, 3: 65.0},
        max_shard_wall_clock=60.0,
    )
    assert balanced is False
    assert "⚠ Shard balance FAILED" in output
    assert "[1, 3]" in output


def test_collect_wall_clock_takes_per_shard_median_across_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    durations_by_run = {
        101: {1: 50.0, 2: 40.0},
        102: {1: 54.0, 2: 42.0},
        103: {1: 58.0, 2: 38.0},
    }

    def fake_job_durations(runner: object, run_id: int, *, repo: str) -> dict[int, float]:
        assert runner is rebalance._RUNNER
        assert repo == "o/r"
        return durations_by_run[run_id]

    monkeypatch.setattr(rebalance.gh, "job_durations", fake_job_durations)
    result = rebalance._collect_wall_clock(rebalance._RUNNER, [101, 102, 103], repo="o/r")
    assert result == {1: 54.0, 2: 40.0}


def test_collect_wall_clock_skips_runs_whose_jobs_api_read_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_job_durations(runner: object, run_id: int, *, repo: str) -> dict[int, float]:
        assert runner is rebalance._RUNNER
        assert repo == "o/r"
        if run_id == 102:
            raise rebalance.ShipError("jobs api boom")
        return {1: 50.0}

    monkeypatch.setattr(rebalance.gh, "job_durations", fake_job_durations)
    result = rebalance._collect_wall_clock(rebalance._RUNNER, [101, 102], repo="o/r")
    assert result == {1: 50.0}
