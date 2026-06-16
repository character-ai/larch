"""Tests for the dev-only rebalance.py helper surface."""

from __future__ import annotations

import contextlib
import importlib.util
import sys
import io
from pathlib import Path
from types import ModuleType

import pytest

from proc import CommandResult


_REPO_ROOT = Path(__file__).resolve().parents[1]
_REBALANCE_PATH = (
    _REPO_ROOT / ".claude" / "skills" / "rebalance-tests" / "scripts" / "rebalance.py"
)


def _load_rebalance() -> ModuleType:
    spec = importlib.util.spec_from_file_location("rebalance_script", _REBALANCE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
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



def _cr(stdout: str = "", rc: int = 0) -> CommandResult:
    return CommandResult((), rc, stdout, "", 0.01)


def test_pack_nodeids_returns_assignments_covering_shards() -> None:
    assignments = rebalance._pack_nodeids(
        {"slow": 10.0, "mid": 5.0, "fast": 1.0, "tiny": 0.5}, 2
    )

    assert set(assignments) == {"slow", "mid", "fast", "tiny"}
    assert set(assignments.values()) == {1, 2}


def test_write_assignments_json_sorts_keys_and_removes_temp(tmp_path: Path) -> None:
    path = tmp_path / "shard-assignments.json"

    rebalance._write_assignments_json(path, {"b": 2, "a": 1})

    assert path.read_text(encoding="utf-8") == '{\n  "a": 1,\n  "b": 2\n}\n'
    assert not list(tmp_path.glob("*.tmp"))


def test_assignments_noop_detection(tmp_path: Path) -> None:
    assignments_path = tmp_path / "shard-assignments.json"
    _ = assignments_path.write_text('{\n  "a": 1\n}\n', encoding="utf-8")

    assert rebalance._path_would_match(
        assignments_path, rebalance._assignments_json_text({"a": 1})
    )
    assert not rebalance._path_would_match(
        assignments_path, rebalance._assignments_json_text({"a": 2})
    )


def test_kind_parser_accepts_kinds_and_rejects_invalid() -> None:
    assert rebalance._parse_args(["--kind", "harness"]).kind == "harness"
    assert rebalance._parse_args(["--kind", "python"]).kind == "python"
    assert rebalance._parse_args(["--kind", "all"]).kind == "all"
    with pytest.raises(SystemExit):
        _ = rebalance._parse_args(["--kind", "bad"])


def test_n_python_shards_rejects_zero() -> None:
    with pytest.raises(SystemExit):
        _ = rebalance._parse_args(["--n-python-shards", "0"])


def test_paths_for_kind_are_kind_aware() -> None:
    assert rebalance._paths_for_kind("harness") == ["Makefile"]
    assert rebalance._paths_for_kind("python") == ["python/shard-assignments.json"]
    assert rebalance._paths_for_kind("all") == [
        "Makefile",
        "python/shard-assignments.json",
    ]


def test_cleanliness_gate_names_dirty_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_status(_runner: object, path: str, *, cwd: str) -> CommandResult:
        assert cwd == str(rebalance._REPO_ROOT)
        stdout = " M " + path + "\n" if path == "Makefile" else ""
        return _cr(stdout)

    monkeypatch.setattr(rebalance.git, "status_porcelain_paths", fake_status)

    with pytest.raises(rebalance.ShipError, match="Makefile"):
        rebalance._assert_artifact_paths_clean(["Makefile", "python/shard-assignments.json"])


def test_revert_written_paths_restores_staged_before_worktree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_restore(_runner: object, path: str, *, cwd: str) -> CommandResult:
        assert cwd == str(rebalance._REPO_ROOT)
        calls.append(("restore", path))
        return _cr()

    def fake_checkout(_runner: object, path: str, *, cwd: str) -> CommandResult:
        assert cwd == str(rebalance._REPO_ROOT)
        calls.append(("checkout", path))
        return _cr()

    monkeypatch.setattr(rebalance.git, "restore_staged", fake_restore)
    monkeypatch.setattr(rebalance.git, "checkout_paths", fake_checkout)

    rebalance._revert_written_paths(["Makefile", "python/shard-assignments.json"])

    assert calls == [
        ("restore", "Makefile"),
        ("checkout", "Makefile"),
        ("restore", "python/shard-assignments.json"),
        ("checkout", "python/shard-assignments.json"),
    ]


def test_python_verification_zero_rows_fails_with_pr_url(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_collect(_runner: object, run_id: int, *, repo: str) -> list[object]:
        assert run_id == 1
        assert repo == "o/r"
        return []

    monkeypatch.setattr(rebalance, "_collect_pytest_log_rows", fake_collect)
    args = rebalance._parse_args(["--kind", "python", "--repo", "o/r"])

    result = rebalance._verify_python(args, [1], repo="o/r", pr_url="https://pr")

    captured = capsys.readouterr()
    assert result == 1
    assert "https://pr" in captured.err
    assert "zero parseable python-tests" in captured.err


def test_python_verification_incomplete_coverage_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rows = [
        rebalance.pytest_ci_timing.PytestTimingRow(1, 1, "a", 1.0, 1, 4),
        rebalance.pytest_ci_timing.PytestTimingRow(1, 2, "b", 1.0, 1, 4),
    ]

    def fake_collect(_runner: object, _run_id: int, *, repo: str) -> list[object]:
        assert repo == "o/r"
        return rows

    monkeypatch.setattr(rebalance, "_collect_pytest_log_rows", fake_collect)
    args = rebalance._parse_args(["--kind", "python", "--repo", "o/r"])

    assert rebalance._verify_python(args, [1], repo="o/r", pr_url="https://pr") == 1
    assert "missing shard ids" in capsys.readouterr().err


def test_python_verification_spread_over_threshold_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rows = [
        rebalance.pytest_ci_timing.PytestTimingRow(1, 1, "a", 20.0, 1, 2),
        rebalance.pytest_ci_timing.PytestTimingRow(1, 2, "b", 1.0, 1, 2),
    ]

    def fake_collect(_runner: object, _run_id: int, *, repo: str) -> list[object]:
        assert repo == "o/r"
        return rows

    monkeypatch.setattr(rebalance, "_collect_pytest_log_rows", fake_collect)
    args = rebalance._parse_args(
        ["--kind", "python", "--repo", "o/r", "--n-python-shards", "2", "--balance-threshold", "5"]
    )

    assert rebalance._verify_python(args, [1], repo="o/r", pr_url="https://pr") == 1
    assert "exceeds" in capsys.readouterr().err


def test_python_verification_within_threshold_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        rebalance.pytest_ci_timing.PytestTimingRow(1, 1, "a", 4.0, 1, 2),
        rebalance.pytest_ci_timing.PytestTimingRow(1, 2, "b", 3.0, 1, 2),
    ]

    def fake_collect(_runner: object, _run_id: int, *, repo: str) -> list[object]:
        assert repo == "o/r"
        return rows

    monkeypatch.setattr(rebalance, "_collect_pytest_log_rows", fake_collect)
    args = rebalance._parse_args(["--kind", "python", "--repo", "o/r", "--n-python-shards", "2"])

    assert rebalance._verify_python(args, [1], repo="o/r", pr_url="https://pr") == 0
