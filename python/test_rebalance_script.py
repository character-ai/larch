"""Tests for the dev-only rebalance.py helper surface."""

from __future__ import annotations

import contextlib
import importlib.util
import io
from pathlib import Path
from types import ModuleType


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
