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
    measured: dict[str, float],
    *,
    n_shards: int = 2,
    balance_threshold: float = 4.0,
) -> str:
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        rebalance._check_feasibility(measured, n_shards, balance_threshold)
    return stream.getvalue()


def test_infeasible_packed_workload_emits_warning() -> None:
    output = _feasibility_output(
        {
            "test-slow": 20.0,
            "test-medium": 2.0,
            "test-fast": 2.0,
        }
    )

    assert "WARNING: packed workload may be infeasible" in output
    assert "Heaviest packed target: test-slow (20.0s)" in output
    assert "Ideal shard time: 12.0s" in output
    assert "Balance threshold: 4.0s" in output
    assert "Threshold half: 2.0s" in output
    assert "Top 5 heaviest packed targets:" in output
    assert "test-medium: 2.0s" in output


def test_feasible_packed_workload_emits_no_warning() -> None:
    output = _feasibility_output(
        {
            "test-a": 6.0,
            "test-b": 6.0,
            "test-c": 6.0,
            "test-d": 6.0,
        }
    )

    assert output == ""


def test_empty_measured_workload_emits_no_warning() -> None:
    output = _feasibility_output({})

    assert output == ""


def test_zero_shards_emits_no_warning() -> None:
    output = _feasibility_output({"test-slow": 20.0}, n_shards=0)

    assert output == ""


def test_orphan_medians_are_excluded_before_feasibility() -> None:
    medians = {
        "test-a": 6.0,
        "test-b": 6.0,
        "orphan-heavy": 100.0,
    }
    measured = rebalance._select_packed_workload(medians, ["test-a", "test-b"])

    assert measured == {"test-a": 6.0, "test-b": 6.0}
    assert _feasibility_output(measured) == ""
