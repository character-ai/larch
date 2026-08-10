"""Tests for the dev-only rebalance.py helper surface."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from larch.core.proc import CommandResult


_REPO_ROOT = Path(__file__).resolve().parents[2]
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


def _skip_write_shards(_makefile_path: Path, _shards: dict[int, list[str]]) -> None:
    """Leave the Makefile fixture unchanged when testing later failure paths."""


def _complete_harness_report(
    shards: dict[int, list[str]] | None = None,
    *,
    run_ids: tuple[int, ...] = (11, 12),
) -> object:
    shards = shards or {1: ["test-a", "test-b"], 2: ["test-c"]}
    target_seconds = {"test-a": 20.0, "test-b": 10.0, "test-c": 15.0}
    rows: list[object] = []
    bootstrap_rows: list[object] = []
    for run_id in run_ids:
        for shard, targets in shards.items():
            for index, target in enumerate(targets):
                rows.append(
                    rebalance.HarnessTimingRow(
                        run_id=run_id,
                        shard=shard,
                        target=target,
                        seconds=target_seconds[target],
                    )
                )
                bootstrap_rows.append(
                    rebalance.HarnessBootstrapRow(
                        run_id=run_id,
                        shard=shard,
                        target=target,
                        bootstrap_kind="cold" if index == 0 else "warm",
                        seconds=10.0 if index == 0 else 1.0,
                    )
                )
    return _ci_report(
        "harness",
        row_count=len(rows),
        target_medians={target: target_seconds[target] for target in target_seconds},
        shard_medians={1: 30.0, 2: 15.0},
        sampled_run_ids=list(run_ids),
        harness_rows=tuple(rows),
        bootstrap_rows=tuple(bootstrap_rows),
    )


def _complete_jobs_report(
    *,
    run_ids: tuple[int, ...] = (11, 12),
    shard_one_seconds: float = 141.0,
    shard_two_seconds: float = 125.0,
) -> object:
    rows = tuple(
        rebalance.JobTimingRow(run_id=run_id, shard=shard, seconds=seconds)
        for run_id in run_ids
        for shard, seconds in ((1, shard_one_seconds), (2, shard_two_seconds))
    )
    return _ci_report(
        "jobs",
        row_count=len(rows),
        shard_medians={1: shard_one_seconds, 2: shard_two_seconds},
        sampled_run_ids=list(run_ids),
        job_rows=rows,
    )


def test_harness_cost_model_charges_fixed_and_shared_setup_once() -> None:
    report = _complete_harness_report()
    jobs = _complete_jobs_report()

    assert rebalance._validate_harness_cohort(
        report,
        expected_shards={1: ["test-a", "test-b"], 2: ["test-c"]},
        expected_run_count=2,
    ) == [11, 12]
    model = rebalance._harness_cost_model(
        report,
        jobs,
        expected_targets=["test-a", "test-b", "test-c"],
        affinities={},
    )

    assert model.fixed_startup_seconds == 100.0
    assert model.shared_setup_seconds == 9.0
    assert model.target_seconds == {"test-a": 21.0, "test-b": 11.0, "test-c": 16.0}
    assert rebalance._predicted_shard_times(
        {1: ["test-a", "test-b"], 2: ["test-c"]}, model
    ) == {1: 141.0, 2: 125.0}


def test_predicted_time_charges_named_affinity_once_per_shard() -> None:
    model = rebalance.HarnessCostModel(
        fixed_startup_seconds=100.0,
        shared_setup_seconds=9.0,
        target_seconds={"test-a": 21.0, "test-b": 11.0, "test-c": 16.0},
        affinities={
            "test-a": rebalance.AffinityCost("compile", 30.0),
            "test-b": rebalance.AffinityCost("compile", 30.0),
        },
    )

    assert rebalance._predicted_shard_times(
        {1: ["test-a", "test-b"], 2: ["test-c"]}, model
    ) == {1: 171.0, 2: 125.0}


def test_harness_model_accepts_stable_multi_mark_target_costs() -> None:
    rows: list[object] = []
    bootstrap_rows: list[object] = []
    for run_id in (11, 12):
        rows.extend(
            [
                rebalance.HarnessTimingRow(run_id, 1, "test-a", 10.0),
                rebalance.HarnessTimingRow(run_id, 1, "test-a", 10.0),
                rebalance.HarnessTimingRow(run_id, 1, "test-b", 10.0),
                rebalance.HarnessTimingRow(run_id, 2, "test-c", 15.0),
            ]
        )
        bootstrap_rows.extend(
            [
                rebalance.HarnessBootstrapRow(run_id, 1, "test-a", "cold", 10.0),
                rebalance.HarnessBootstrapRow(run_id, 1, "test-a", "warm", 1.0),
                rebalance.HarnessBootstrapRow(run_id, 1, "test-b", "warm", 1.0),
                rebalance.HarnessBootstrapRow(run_id, 2, "test-c", "cold", 10.0),
            ]
        )
    report = _ci_report(
        "harness",
        row_count=len(rows),
        target_medians={"test-a": 20.0, "test-b": 10.0, "test-c": 15.0},
        sampled_run_ids=[11, 12],
        harness_rows=tuple(rows),
        bootstrap_rows=tuple(bootstrap_rows),
    )
    jobs = _complete_jobs_report(shard_one_seconds=142.0)

    assert rebalance._validate_harness_cohort(
        report,
        expected_shards={1: ["test-a", "test-b"], 2: ["test-c"]},
        expected_run_count=2,
    ) == [11, 12]
    model = rebalance._harness_cost_model(
        report,
        jobs,
        expected_targets=["test-a", "test-b", "test-c"],
        affinities={},
    )

    assert model.target_seconds["test-a"] == 22.0
    assert model.target_seconds["test-b"] == 11.0


def test_harness_cohort_rejects_missing_bootstrap_measurement() -> None:
    report = _complete_harness_report()
    report = rebalance.CiTimingReport(
        **{
            **report.__dict__,
            "bootstrap_rows": report.bootstrap_rows[1:],
        }
    )

    with pytest.raises(rebalance.ShipError, match="bootstrap evidence"):
        rebalance._validate_harness_cohort(
            report,
            expected_shards={1: ["test-a", "test-b"], 2: ["test-c"]},
            expected_run_count=2,
        )


def test_harness_cohort_rejects_target_inventory_drift() -> None:
    report = _complete_harness_report()
    first = report.harness_rows[0]
    report = rebalance.CiTimingReport(
        **{
            **report.__dict__,
            "harness_rows": (
                rebalance.HarnessTimingRow(
                    run_id=first.run_id,
                    shard=first.shard,
                    target="test-drifted",
                    seconds=first.seconds,
                ),
                *report.harness_rows[1:],
            ),
        }
    )

    with pytest.raises(rebalance.ShipError, match="inventory drift"):
        rebalance._validate_harness_cohort(
            report,
            expected_shards={1: ["test-a", "test-b"], 2: ["test-c"]},
            expected_run_count=2,
        )


def test_harness_cohort_rejects_incompatible_target_mark_counts() -> None:
    report = _complete_harness_report()
    extra_timing = rebalance.HarnessTimingRow(12, 1, "test-a", 20.0)
    extra_bootstrap = rebalance.HarnessBootstrapRow(12, 1, "test-a", "warm", 1.0)
    report = rebalance.CiTimingReport(
        **{
            **report.__dict__,
            "harness_rows": (*report.harness_rows, extra_timing),
            "bootstrap_rows": (*report.bootstrap_rows, extra_bootstrap),
        }
    )

    with pytest.raises(rebalance.ShipError, match="incompatible target-mark counts"):
        rebalance._validate_harness_cohort(
            report,
            expected_shards={1: ["test-a", "test-b"], 2: ["test-c"]},
            expected_run_count=2,
        )


def test_predicted_regression_requires_documented_experimental_override() -> None:
    args = rebalance._parse_args(argv=["--kind", "harness"])

    with pytest.raises(rebalance.ShipError, match="predicted slowest shard"):
        rebalance._require_predicted_harness_layout(
            args,
            current={1: 120.0, 2: 110.0},
            proposed={1: 121.0, 2: 109.0},
            approved_slowest_wall_clock=120.0,
        )

    overridden = rebalance._parse_args(
        argv=[
            "--kind",
            "harness",
            "--experimental-wall-clock-override",
            "measure runner-image migration",
        ]
    )
    rebalance._require_predicted_harness_layout(
        overridden,
        current={1: 120.0, 2: 110.0},
        proposed={1: 121.0, 2: 109.0},
        approved_slowest_wall_clock=120.0,
    )


def test_layout_selection_does_not_open_extra_cold_setup_runners(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = {
        1: [],
        2: [],
        3: ["test-a", "test-b"],
        4: ["test-c"],
        5: ["test-d", "test-e"],
    }
    model = rebalance.HarnessCostModel(
        fixed_startup_seconds=100.0,
        shared_setup_seconds=20.0,
        target_seconds={
            "test-a": 30.0,
            "test-b": 30.0,
            "test-c": 10.0,
            "test-d": 10.0,
            "test-e": 0.0,
        },
        affinities={},
    )

    def fake_pack(
        _model: object,
        _targets: object,
        _n_shards: int,
        *,
        guard: str,
        active_shard_ids: list[int],
    ) -> dict[int, list[str]]:
        assert guard == rebalance._GUARD
        if len(active_shard_ids) == 3:
            return {
                1: [],
                2: [],
                3: ["test-a", "test-c"],
                4: ["test-b", "test-d"],
                5: ["test-e"],
            }
        if len(active_shard_ids) == 5:
            return {
                1: ["test-a"],
                2: ["test-b"],
                3: ["test-c"],
                4: ["test-d"],
                5: ["test-e"],
            }
        return current

    monkeypatch.setattr(rebalance, "_pack_harness_shards", fake_pack)
    args = rebalance._parse_args(argv=["--kind", "harness"])

    selected = rebalance._select_harness_layout(
        args,
        model=model,
        targets=list(model.target_seconds),
        current_shards=current,
        approved_slowest_wall_clock=180.0,
    )

    assert selected[3] == ["test-a", "test-c"]
    assert selected[4] == ["test-b", "test-d"]
    assert selected[5] == ["test-e"]


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


def test_collect_wall_clock_retains_raw_jobs_api_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run_ci_timing(
        runner: object, kind: str, *, repo: str, run_ids: list[int]
    ) -> object:
        assert runner is rebalance._RUNNER
        assert kind == "jobs"
        assert repo == "o/r"
        assert run_ids == [101, 102, 103]
        return _ci_report("jobs", row_count=6, shard_medians={1: 54.0, 2: 40.0})

    monkeypatch.setattr(rebalance, "_run_ci_timing", fake_run_ci_timing)
    result = rebalance._collect_wall_clock(
        rebalance._RUNNER, [101, 102, 103], repo="o/r"
    )
    assert result.kind == "jobs"
    assert result.shard_medians == {1: 54.0, 2: 40.0}


def test_collect_wall_clock_propagates_jobs_api_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run_ci_timing(
        runner: object, kind: str, *, repo: str, run_ids: list[int]
    ) -> object:
        assert runner is rebalance._RUNNER
        assert kind == "jobs"
        assert repo == "o/r"
        assert run_ids == [101, 102]
        raise rebalance.ShipError("jobs api boom")

    monkeypatch.setattr(rebalance, "_run_ci_timing", fake_run_ci_timing)
    with pytest.raises(rebalance.ShipError, match="jobs api boom"):
        rebalance._collect_wall_clock(rebalance._RUNNER, [101, 102], repo="o/r")


def _cr(stdout: str = "", rc: int = 0) -> CommandResult:
    return CommandResult((), rc, stdout, "", 0.01)


def _ci_report(
    kind: str,
    *,
    row_count: int = 0,
    target_medians: dict[str, float] | None = None,
    nodeid_medians: dict[str, float] | None = None,
    shard_medians: dict[int, float] | None = None,
    observed_shard_count: int | None = None,
    untimed_targets: list[str] | None = None,
    skipped_run_ids: list[int] | None = None,
    sampled_run_ids: list[int] | None = None,
    harness_rows: tuple[object, ...] = (),
    bootstrap_rows: tuple[object, ...] = (),
    job_rows: tuple[object, ...] = (),
) -> object:
    return rebalance.CiTimingReport(
        kind=kind,
        row_count=row_count,
        target_medians=target_medians or {},
        nodeid_medians=nodeid_medians or {},
        shard_medians=shard_medians or {},
        observed_shard_count=observed_shard_count,
        untimed_targets=untimed_targets or [],
        skipped_run_ids=skipped_run_ids or [],
        sampled_run_ids=sampled_run_ids or [],
        harness_rows=harness_rows,
        bootstrap_rows=bootstrap_rows,
        job_rows=job_rows,
    )


def test_ci_timing_parser_preserves_harness_contract() -> None:
    wire = (
        '{"schema_version":2,"kind":"harness","sampled_run_ids":[9],"rows":['
        '{"run_id":9,"shard":2,"target":"test-a","seconds":3.5}],'
        '"bootstrap_rows":[{"run_id":9,"shard":2,"target":"test-a",'
        '"bootstrap_kind":"cold","seconds":0.5}],'
        '"target_medians":[{"target":"test-a","seconds":3.5}],'
        '"shard_medians":[{"shard":2,"seconds":3.5}],'
        '"untimed_targets":["test-b"],"skipped_run_ids":[8]}\n'
    )

    report = rebalance._parse_ci_timing_report(wire, expected_kind="harness")

    assert report.row_count == 1
    assert report.target_medians == {"test-a": 3.5}
    assert report.shard_medians == {2: 3.5}
    assert report.untimed_targets == ["test-b"]
    assert report.skipped_run_ids == [8]
    assert report.sampled_run_ids == [9]
    assert report.bootstrap_rows[0].bootstrap_kind == "cold"


def test_ci_timing_parser_rejects_reordered_report_fields() -> None:
    wire = (
        '{"kind":"jobs","schema_version":2,"sampled_run_ids":[],"rows":[],'
        '"shard_medians":[],"skipped_run_ids":[]}\n'
    )

    with pytest.raises(rebalance.ShipError, match="keys must be exactly"):
        _ = rebalance._parse_ci_timing_report(wire, expected_kind="jobs")


def test_ci_timing_parser_rejects_duplicate_object_keys() -> None:
    wire = (
        '{"schema_version":2,"kind":"jobs","sampled_run_ids":[],"rows":[],"rows":[],'
        '"shard_medians":[],"skipped_run_ids":[]}\n'
    )

    with pytest.raises(rebalance.ShipError, match="duplicate object key 'rows'"):
        _ = rebalance._parse_ci_timing_report(wire, expected_kind="jobs")


def test_run_ci_timing_uses_verified_bootstrap_and_repeated_flags() -> None:
    calls: list[tuple[list[str], str, dict[str, str]]] = []

    class Runner:
        def run(
            self,
            argv: list[str],
            *,
            cwd: str,
            env: dict[str, str],
        ) -> CommandResult:
            calls.append((argv, cwd, env))
            return _cr(
                '{"schema_version":2,"kind":"harness","sampled_run_ids":[11,12],"rows":[],'
                '"bootstrap_rows":[],'
                '"target_medians":[],"shard_medians":[],'
                '"untimed_targets":[],"skipped_run_ids":[]}\n'
            )

    _ = rebalance._run_ci_timing(
        Runner(),
        "harness",
        repo="o/r",
        run_ids=[11, 12],
        required_targets=["test-a", "test-b"],
    )

    argv, cwd, env = calls[0]
    assert argv[:3] == [
        str(rebalance._REPO_ROOT / "scripts" / "larch.sh"),
        "ci-timing",
        "harness",
    ]
    assert argv.count("--run-id") == 2
    assert argv.count("--required-target") == 2
    assert cwd == str(rebalance._REPO_ROOT)
    assert env["CLAUDE_PLUGIN_ROOT"] == str(rebalance._REPO_ROOT)


def test_test_shard_uses_verified_bootstrap_and_removes_json_input() -> None:
    calls: list[tuple[list[str], str, dict[str, str]]] = []

    class Runner:
        def run(
            self,
            argv: list[str],
            *,
            cwd: str,
            env: dict[str, str],
        ) -> CommandResult:
            calls.append((argv, cwd, env))
            input_path = Path(argv[argv.index("--input") + 1])
            assert json.loads(input_path.read_text(encoding="utf-8")) == [
                {"target": "test-a", "seconds": 3.5}
            ]
            return _cr('{"1":["test-a"]}\n')

    output = rebalance._run_test_shard(
        Runner(),
        ["pack", "--n-shards", "1"],
        input_payload=[{"target": "test-a", "seconds": 3.5}],
    )

    argv, cwd, env = calls[0]
    assert output == '{"1":["test-a"]}\n'
    assert argv[:3] == [
        str(rebalance._REPO_ROOT / "scripts" / "larch.sh"),
        "test-shard",
        "pack",
    ]
    input_path = Path(argv[argv.index("--input") + 1])
    assert not input_path.exists()
    assert cwd == str(rebalance._REPO_ROOT)
    assert env["CLAUDE_PLUGIN_ROOT"] == str(rebalance._REPO_ROOT)


def test_pack_nodeids_returns_assignments_covering_shards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_pack(
        medians: dict[str, float], n_shards: int, *, guard: str
    ) -> dict[int, list[str]]:
        assert medians == {"slow": 10.0, "mid": 5.0, "fast": 1.0, "tiny": 0.5}
        assert n_shards == 2
        assert guard == ""
        return {1: ["slow", "tiny"], 2: ["mid", "fast"]}

    monkeypatch.setattr(rebalance, "_pack_shards", fake_pack)
    assignments = rebalance._pack_nodeids(
        {"slow": 10.0, "mid": 5.0, "fast": 1.0, "tiny": 0.5}, 2
    )

    assert set(assignments) == {"slow", "mid", "fast", "tiny"}
    assert set(assignments.values()) == {1, 2}


def test_pack_harness_maps_a_selected_active_runner_subset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], object]] = []
    model = rebalance.HarnessCostModel(
        fixed_startup_seconds=10.0,
        shared_setup_seconds=3.0,
        target_seconds={"test-a": 4.0, "test-b": 2.0, "test-c": 1.0},
        affinities={
            "test-a": rebalance.AffinityCost("compile", 5.0),
            "test-b": rebalance.AffinityCost("compile", 5.0),
        },
    )

    def fake_run_test_shard(
        _runner: object,
        command: list[str],
        *,
        input_payload: object,
    ) -> str:
        calls.append((command, input_payload))
        return '{"1":["test-a","test-b"],"2":["test-c"]}\n'

    monkeypatch.setattr(rebalance, "_run_test_shard", fake_run_test_shard)
    packed = rebalance._pack_harness_shards(
        model,
        ["test-a", "test-b", "test-c"],
        5,
        guard="test-a",
        active_shard_ids=[3, 5],
    )

    assert packed == {
        1: [],
        2: [],
        3: ["test-a", "test-b"],
        4: [],
        5: ["test-c"],
    }
    command, payload = calls[0]
    assert command == [
        "pack",
        "--n-shards",
        "2",
        "--fixed-startup-seconds",
        "13.0",
        "--guard",
        "test-a",
    ]
    assert payload == [
        {
            "target": "test-a",
            "seconds": 4.0,
            "affinity_group": "compile",
            "affinity_setup_seconds": 5.0,
        },
        {
            "target": "test-b",
            "seconds": 2.0,
            "affinity_group": "compile",
            "affinity_setup_seconds": 5.0,
        },
        {"target": "test-c", "seconds": 1.0},
    ]


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
    assert rebalance._parse_args(argv=["--kind", "harness"]).kind == "harness"
    assert rebalance._parse_args(argv=["--kind", "python"]).kind == "python"
    assert rebalance._parse_args(argv=["--kind", "all"]).kind == "all"
    with pytest.raises(SystemExit):
        _ = rebalance._parse_args(argv=["--kind", "bad"])


def test_n_python_shards_rejects_zero() -> None:
    with pytest.raises(SystemExit):
        _ = rebalance._parse_args(argv=["--n-python-shards", "0"])


def test_harness_wall_clock_flags_have_enforced_defaults() -> None:
    assert rebalance._parse_args(argv=[]).max_shard_wall_clock == 300.0
    with pytest.raises(SystemExit):
        _ = rebalance._parse_args(argv=["--max-shard-wall-clock", "0"])
    with pytest.raises(SystemExit):
        _ = rebalance._parse_args(argv=["--experimental-wall-clock-override", "   "])


def test_observed_job_run_tables_keep_each_raw_verification_sample(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rebalance._print_observed_job_runs(
        (
            rebalance.JobTimingRow(302, 2, 12.0),
            rebalance.JobTimingRow(301, 1, 10.0),
            rebalance.JobTimingRow(302, 1, 11.0),
            rebalance.JobTimingRow(301, 2, 9.0),
        )
    )

    output = capsys.readouterr().out
    assert "OBSERVED run 301 (real CI job wall-clock):" in output
    assert "OBSERVED run 302 (real CI job wall-clock):" in output
    assert output.index("OBSERVED run 301") < output.index("OBSERVED run 302")
    assert "      1        10.0" in output
    assert "      2        12.0" in output


def test_compile_affinity_contracts_are_explicit_and_inventory_bound() -> None:
    args = rebalance._parse_args(
        argv=[
            "--compile-affinity",
            "test-a=cargo-workspace:12.5",
            "--compile-affinity",
            "test-b=cargo-workspace:12.5",
            "--compile-affinity",
            "test-c=other:0",
        ]
    )

    assert rebalance._compile_affinities(
        args.compile_affinity,
        expected_targets=["test-a", "test-b", "test-c"],
    ) == {
        "test-a": rebalance.AffinityCost("cargo-workspace", 12.5),
        "test-b": rebalance.AffinityCost("cargo-workspace", 12.5),
        "test-c": rebalance.AffinityCost("other", 0.0),
    }
    with pytest.raises(rebalance.ShipError, match="not in the current Makefile"):
        _ = rebalance._compile_affinities(
            args.compile_affinity,
            expected_targets=["test-a", "test-b"],
        )
    conflicting = rebalance._parse_args(
        argv=[
            "--compile-affinity",
            "test-a=compile:1",
            "--compile-affinity",
            "test-b=compile:2",
        ]
    )
    with pytest.raises(rebalance.ShipError, match="inconsistent setup"):
        _ = rebalance._compile_affinities(
            conflicting.compile_affinity,
            expected_targets=["test-a", "test-b"],
        )
    with pytest.raises(SystemExit):
        _ = rebalance._parse_args(argv=["--compile-affinity", "test-a=compile"])


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
    def fake_run_ci_timing(
        _runner: object, kind: str, *, repo: str, run_ids: list[int]
    ) -> object:
        assert kind == "pytest"
        assert run_ids == [1]
        assert repo == "o/r"
        return _ci_report("pytest")

    monkeypatch.setattr(rebalance, "_run_ci_timing", fake_run_ci_timing)
    args = rebalance._parse_args(argv=["--kind", "python", "--repo", "o/r"])

    result = rebalance._verify_python(
        args,
        [1],
        repo="o/r",
        pr_url="https://pr",
        plan=_sample_python_plan(),
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "https://pr" in captured.err
    assert "zero parseable python-tests" in captured.err


def test_python_verification_incomplete_coverage_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run_ci_timing(
        _runner: object, kind: str, *, repo: str, run_ids: list[int]
    ) -> object:
        assert kind == "pytest"
        assert repo == "o/r"
        assert run_ids == [1]
        return _ci_report("pytest", row_count=2, shard_medians={1: 1.0, 2: 1.0})

    monkeypatch.setattr(rebalance, "_run_ci_timing", fake_run_ci_timing)
    args = rebalance._parse_args(argv=["--kind", "python", "--repo", "o/r"])

    assert rebalance._verify_python(
        args,
        [1],
        repo="o/r",
        pr_url="https://pr",
        plan=_sample_python_plan(n_shards=3),
    ) == 1
    assert "missing shard ids" in capsys.readouterr().err


def test_python_verification_spread_over_threshold_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run_ci_timing(
        _runner: object, kind: str, *, repo: str, run_ids: list[int]
    ) -> object:
        assert kind == "pytest"
        assert repo == "o/r"
        assert run_ids == [1]
        return _ci_report("pytest", row_count=2, shard_medians={1: 20.0, 2: 1.0})

    monkeypatch.setattr(rebalance, "_run_ci_timing", fake_run_ci_timing)
    args = rebalance._parse_args(
        argv=[
            "--kind",
            "python",
            "--repo",
            "o/r",
            "--n-python-shards",
            "2",
            "--balance-threshold",
            "5",
        ]
    )

    assert rebalance._verify_python(
        args,
        [1],
        repo="o/r",
        pr_url="https://pr",
        plan=_sample_python_plan(),
    ) == 1
    assert "exceeds" in capsys.readouterr().err


def test_python_verification_within_threshold_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run_ci_timing(
        _runner: object, kind: str, *, repo: str, run_ids: list[int]
    ) -> object:
        assert kind == "pytest"
        assert repo == "o/r"
        assert run_ids == [1]
        return _ci_report("pytest", row_count=2, shard_medians={1: 4.0, 2: 3.0})

    monkeypatch.setattr(rebalance, "_run_ci_timing", fake_run_ci_timing)
    args = rebalance._parse_args(
        argv=["--kind", "python", "--repo", "o/r", "--n-python-shards", "2"]
    )

    assert rebalance._verify_python(
        args,
        [1],
        repo="o/r",
        pr_url="https://pr",
        plan=_sample_python_plan(),
    ) == 0


def _sample_harness_plan() -> object:
    current = {1: ["test-a"], 2: ["test-b"]}
    new = {1: ["test-b"], 2: ["test-a"]}
    medians = {"test-a": 1.0, "test-b": 2.0}
    model = rebalance.HarnessCostModel(
        fixed_startup_seconds=10.0,
        shared_setup_seconds=1.0,
        target_seconds=medians,
        affinities={},
    )
    return rebalance.HarnessPlan(
        current_shards=current,
        new_shards=new,
        medians=medians,
        n_shards=2,
        baseline_spread=1.0,
        cost_model=model,
        predicted_current={1: 12.0, 2: 13.0},
        predicted_new={1: 13.0, 2: 12.0},
        baseline_wall_clock={1: 12.0, 2: 13.0},
        baseline_slowest_wall_clock=13.0,
        baseline_runner_seconds=25.0,
        approved_slowest_wall_clock=13.0,
    )


def _verification_harness_report(
    *, run_id: int = 301, include_bootstrap: bool = True
) -> object:
    rows = (
        rebalance.HarnessTimingRow(run_id, 1, "test-b", 2.0),
        rebalance.HarnessTimingRow(run_id, 2, "test-a", 1.0),
    )
    bootstrap_rows: tuple[object, ...] = ()
    if include_bootstrap:
        bootstrap_rows = (
            rebalance.HarnessBootstrapRow(run_id, 1, "test-b", "cold", 1.0),
            rebalance.HarnessBootstrapRow(run_id, 2, "test-a", "cold", 1.0),
        )
    return _ci_report(
        "harness",
        row_count=len(rows),
        target_medians={"test-b": 2.0, "test-a": 1.0},
        shard_medians={1: 2.0, 2: 1.0},
        sampled_run_ids=[run_id],
        harness_rows=rows,
        bootstrap_rows=bootstrap_rows,
    )


def _verification_jobs_report(*, shard_one_seconds: float = 20.0) -> object:
    rows = (
        rebalance.JobTimingRow(301, 1, shard_one_seconds),
        rebalance.JobTimingRow(301, 2, 10.0),
    )
    return _ci_report(
        "jobs",
        row_count=2,
        shard_medians={1: shard_one_seconds, 2: 10.0},
        sampled_run_ids=[301],
        job_rows=rows,
    )


def test_harness_verification_fails_on_measured_wall_clock_regression(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        rebalance,
        "_collect_wall_clock",
        lambda *_args, **_kwargs: _verification_jobs_report(),
    )
    monkeypatch.setattr(
        rebalance,
        "_run_ci_timing",
        lambda *_args, **_kwargs: _verification_harness_report(),
    )
    args = rebalance._parse_args(argv=["--kind", "harness", "--repo", "o/r"])

    assert rebalance._verify_harness(
        args,
        [301],
        repo="o/r",
        pr_url="https://pr",
        plan=_sample_harness_plan(),
    ) == 1
    assert "regresses the approved" in capsys.readouterr().err


def test_harness_evidence_failure_cannot_use_experimental_override(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        rebalance,
        "_collect_wall_clock",
        lambda *_args, **_kwargs: _verification_jobs_report(shard_one_seconds=10.0),
    )
    monkeypatch.setattr(
        rebalance,
        "_run_ci_timing",
        lambda *_args, **_kwargs: _verification_harness_report(include_bootstrap=False),
    )
    args = rebalance._parse_args(
        argv=[
            "--kind",
            "harness",
            "--repo",
            "o/r",
            "--experimental-wall-clock-override",
            "test an image change",
        ]
    )

    assert rebalance._verify_harness(
        args,
        [301],
        repo="o/r",
        pr_url="https://pr",
        plan=_sample_harness_plan(),
    ) == 1
    assert "complete harness verification evidence is unavailable" in capsys.readouterr().err


def test_harness_verification_rejects_a_different_complete_timing_cohort(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        rebalance,
        "_collect_wall_clock",
        lambda *_args, **_kwargs: _verification_jobs_report(shard_one_seconds=10.0),
    )
    monkeypatch.setattr(
        rebalance,
        "_run_ci_timing",
        lambda *_args, **_kwargs: _verification_harness_report(run_id=302),
    )
    args = rebalance._parse_args(argv=["--kind", "harness", "--repo", "o/r"])

    assert rebalance._verify_harness(
        args,
        [301],
        repo="o/r",
        pr_url="https://pr",
        plan=_sample_harness_plan(),
    ) == 1
    assert "requested verification cohort" in capsys.readouterr().err


def _sample_python_plan(*, n_shards: int = 2):
    return rebalance.PythonPlan(
        assignments={"pkg/test_a.py::test_x": 1, "pkg/test_b.py::test_y": 2},
        medians={"pkg/test_a.py::test_x": 1.0, "pkg/test_b.py::test_y": 2.0},
        n_shards=n_shards,
    )


def _stub_clean_git(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_current_branch(_runner: object, *, cwd: str | None = None) -> str:
        assert cwd == str(rebalance._REPO_ROOT)
        return "main"

    def fake_status(_runner: object, _path: str, *, cwd: str | None = None) -> CommandResult:
        assert cwd == str(rebalance._REPO_ROOT)
        return _cr("")

    monkeypatch.setattr(rebalance.git, "try_current_branch", fake_current_branch)
    monkeypatch.setattr(rebalance.git, "status_porcelain_paths", fake_status)


def test_cleanliness_gate_raises_on_git_status_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_status(_runner: object, _path: str, *, cwd: str) -> CommandResult:
        assert cwd == str(rebalance._REPO_ROOT)
        return _cr("", rc=128)

    monkeypatch.setattr(rebalance.git, "status_porcelain_paths", fake_status)

    with pytest.raises(rebalance.ShipError, match="git status failed for Makefile"):
        rebalance._assert_artifact_paths_clean(["Makefile"])


def test_revert_written_paths_raises_on_restore_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_restore(_runner: object, _path: str, *, cwd: str) -> CommandResult:
        assert cwd == str(rebalance._REPO_ROOT)
        return _cr(rc=1)

    monkeypatch.setattr(rebalance.git, "restore_staged", fake_restore)

    with pytest.raises(rebalance.ShipError, match="git restore --staged failed for Makefile"):
        rebalance._revert_written_paths(["Makefile"])


def test_main_python_zero_rows_aborts_before_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_calls: list[str] = []

    def track_write_shards(*_args: object, **_kwargs: object) -> None:
        write_calls.append("write_shards")

    def track_write_assignments(*_args: object, **_kwargs: object) -> None:
        write_calls.append("_write_assignments_json")

    _stub_clean_git(monkeypatch)

    def fake_run_ci_timing(*_args: object, **_kwargs: object) -> object:
        return _ci_report("pytest")

    monkeypatch.setattr(rebalance, "_run_ci_timing", fake_run_ci_timing)
    monkeypatch.setattr(rebalance, "_write_shards", track_write_shards)
    monkeypatch.setattr(rebalance, "_write_assignments_json", track_write_assignments)

    result = rebalance.main(["--kind", "python", "--repo", "o/r"])

    assert result == 1
    assert not write_calls


def test_main_dirty_artifact_aborts_before_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_calls: list[str] = []

    def track_write_shards(*_args: object, **_kwargs: object) -> None:
        write_calls.append("write_shards")

    def fake_status(_runner: object, path: str, *, cwd: str) -> CommandResult:
        assert cwd == str(rebalance._REPO_ROOT)
        stdout = " M " + path + "\n" if path == "python/shard-assignments.json" else ""
        return _cr(stdout)

    def fake_current_branch(_runner: object, *, cwd: str | None = None) -> str:
        assert cwd == str(rebalance._REPO_ROOT)
        return "main"

    monkeypatch.setattr(rebalance.git, "try_current_branch", fake_current_branch)
    monkeypatch.setattr(rebalance.git, "status_porcelain_paths", fake_status)

    def fake_prepare_python_plan(*_args: object, **_kwargs: object) -> object:
        return _sample_python_plan()

    monkeypatch.setattr(
        rebalance,
        "_prepare_python_plan",
        fake_prepare_python_plan,
    )
    monkeypatch.setattr(rebalance, "_write_shards", track_write_shards)

    result = rebalance.main(["--kind", "python", "--repo", "o/r"])

    assert result == 1
    assert not write_calls


def test_main_partition_failure_skips_assignments_writer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    assignments_path = tmp_path / "shard-assignments.json"
    baseline = "{}\n"
    _ = assignments_path.write_text(baseline, encoding="utf-8")
    makefile_path = tmp_path / "Makefile"
    _ = makefile_path.write_text("test-harnesses-1: test-a\n", encoding="utf-8")

    assignment_calls: list[str] = []

    def track_write_assignments(*_args: object, **_kwargs: object) -> None:
        assignment_calls.append("_write_assignments_json")

    def fake_validate_partition() -> bool:
        return False

    def fake_revert_written_paths(_paths: list[str]) -> None:
        return None

    monkeypatch.setattr(rebalance, "_ASSIGNMENTS_PATH", assignments_path)
    monkeypatch.setattr(rebalance, "_write_shards", _skip_write_shards)
    monkeypatch.setattr(rebalance, "_validate_partition", fake_validate_partition)
    monkeypatch.setattr(rebalance, "_write_assignments_json", track_write_assignments)
    monkeypatch.setattr(rebalance, "_revert_written_paths", fake_revert_written_paths)

    plan = rebalance.RebalancePlan(harness=_sample_harness_plan(), python=_sample_python_plan())

    with pytest.raises(rebalance.ShipError, match="harness partition validation failed"):
        rebalance._write_selected_artifacts(plan, makefile_path)

    assert not assignment_calls
    assert assignments_path.read_text(encoding="utf-8") == baseline


def test_main_assignments_write_failure_reverts_makefile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    assignments_path = tmp_path / "shard-assignments.json"
    baseline = "{}\n"
    _ = assignments_path.write_text(baseline, encoding="utf-8")
    makefile_path = tmp_path / "Makefile"
    _ = makefile_path.write_text("test-harnesses-1: test-a\n", encoding="utf-8")

    reverted: list[list[str]] = []

    def fail_write_assignments(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    def fake_validate_partition() -> bool:
        return True

    def track_revert_written_paths(paths: list[str]) -> None:
        reverted.append(list(paths))

    monkeypatch.setattr(rebalance, "_ASSIGNMENTS_PATH", assignments_path)
    monkeypatch.setattr(rebalance, "_write_shards", _skip_write_shards)
    monkeypatch.setattr(rebalance, "_validate_partition", fake_validate_partition)
    monkeypatch.setattr(rebalance, "_write_assignments_json", fail_write_assignments)
    monkeypatch.setattr(rebalance, "_revert_written_paths", track_revert_written_paths)

    plan = rebalance.RebalancePlan(harness=_sample_harness_plan(), python=_sample_python_plan())

    with pytest.raises(rebalance.ShipError, match="assignments JSON write failed"):
        rebalance._write_selected_artifacts(plan, makefile_path)

    assert reverted == [["Makefile"]]
    assert assignments_path.read_text(encoding="utf-8") == baseline


def test_main_python_dispatches_verification_after_pr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_order: list[str] = []

    class _Pr:
        number = 42
        url = "https://pr/42"

    _stub_clean_git(monkeypatch)

    def fake_prepare_python_plan(*_args: object, **_kwargs: object) -> object:
        return _sample_python_plan()

    def fake_plan_is_noop(*_args: object, **_kwargs: object) -> bool:
        return False

    def fake_write_selected_artifacts(*_args: object, **_kwargs: object) -> list[str]:
        return ["python/shard-assignments.json"]

    def fake_commit_push_and_pr(*_args: object, **_kwargs: object) -> _Pr:
        call_order.append("pr")
        return _Pr()

    def fake_trigger_verification_runs(*_args: object, **_kwargs: object) -> list[int]:
        call_order.append("verify")
        return [101]

    def fake_verify_python(*_args: object, **_kwargs: object) -> int:
        return 0

    monkeypatch.setattr(rebalance, "_prepare_python_plan", fake_prepare_python_plan)
    monkeypatch.setattr(rebalance, "_plan_is_noop", fake_plan_is_noop)
    monkeypatch.setattr(rebalance, "_write_selected_artifacts", fake_write_selected_artifacts)
    monkeypatch.setattr(rebalance, "_commit_push_and_pr", fake_commit_push_and_pr)
    monkeypatch.setattr(rebalance, "_trigger_verification_runs", fake_trigger_verification_runs)
    monkeypatch.setattr(rebalance, "_verify_python", fake_verify_python)

    result = rebalance.main(["--kind", "python", "--repo", "o/r", "--n-verify-runs", "1"])

    assert result == 0
    assert call_order == ["pr", "verify"]


def test_main_all_dispatches_verification_after_pr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_order: list[str] = []

    class _Pr:
        number = 7
        url = "https://pr/7"

    _stub_clean_git(monkeypatch)

    def fake_prepare_harness_plan(*_args: object, **_kwargs: object) -> object:
        return _sample_harness_plan()

    def fake_prepare_python_plan(*_args: object, **_kwargs: object) -> object:
        return _sample_python_plan()

    def fake_plan_is_noop(*_args: object, **_kwargs: object) -> bool:
        return False

    def fake_write_selected_artifacts(*_args: object, **_kwargs: object) -> list[str]:
        return ["Makefile", "python/shard-assignments.json"]

    def fake_commit_push_and_pr(*_args: object, **_kwargs: object) -> _Pr:
        call_order.append("pr")
        return _Pr()

    def fake_trigger_verification_runs(*_args: object, **_kwargs: object) -> list[int]:
        call_order.append("verify")
        return [201]

    def fake_verify_harness(*_args: object, **_kwargs: object) -> int:
        return 0

    def fake_verify_python(*_args: object, **_kwargs: object) -> int:
        return 0

    monkeypatch.setattr(rebalance, "_prepare_harness_plan", fake_prepare_harness_plan)
    monkeypatch.setattr(rebalance, "_prepare_python_plan", fake_prepare_python_plan)
    monkeypatch.setattr(rebalance, "_plan_is_noop", fake_plan_is_noop)
    monkeypatch.setattr(rebalance, "_write_selected_artifacts", fake_write_selected_artifacts)
    monkeypatch.setattr(rebalance, "_commit_push_and_pr", fake_commit_push_and_pr)
    monkeypatch.setattr(rebalance, "_trigger_verification_runs", fake_trigger_verification_runs)
    monkeypatch.setattr(rebalance, "_verify_harness", fake_verify_harness)
    monkeypatch.setattr(rebalance, "_verify_python", fake_verify_python)

    result = rebalance.main(["--kind", "all", "--repo", "o/r", "--n-verify-runs", "1"])

    assert result == 0
    assert call_order == ["pr", "verify"]


def test_main_harness_verification_failure_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Pr:
        number = 3
        url = "https://pr/3"

    _stub_clean_git(monkeypatch)

    def fake_prepare_harness_plan(*_args: object, **_kwargs: object) -> object:
        return _sample_harness_plan()

    def fake_plan_is_noop(*_args: object, **_kwargs: object) -> bool:
        return False

    def fake_write_selected_artifacts(*_args: object, **_kwargs: object) -> list[str]:
        return ["Makefile"]

    def fake_commit_push_and_pr(*_args: object, **_kwargs: object) -> _Pr:
        return _Pr()

    def fake_trigger_verification_runs(*_args: object, **_kwargs: object) -> list[int]:
        return [301]

    def fake_verify_harness(*_args: object, **_kwargs: object) -> int:
        return 1

    monkeypatch.setattr(rebalance, "_prepare_harness_plan", fake_prepare_harness_plan)
    monkeypatch.setattr(rebalance, "_plan_is_noop", fake_plan_is_noop)
    monkeypatch.setattr(rebalance, "_write_selected_artifacts", fake_write_selected_artifacts)
    monkeypatch.setattr(rebalance, "_commit_push_and_pr", fake_commit_push_and_pr)
    monkeypatch.setattr(rebalance, "_trigger_verification_runs", fake_trigger_verification_runs)
    monkeypatch.setattr(rebalance, "_verify_harness", fake_verify_harness)

    result = rebalance.main(["--kind", "harness", "--repo", "o/r", "--n-verify-runs", "1"])

    assert result == 1


def test_main_harness_noop_rejects_an_over_budget_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_clean_git(monkeypatch)
    plan = _sample_harness_plan()
    over_budget = rebalance.HarnessPlan(
        **{**plan.__dict__, "baseline_slowest_wall_clock": 301.0}
    )

    monkeypatch.setattr(
        rebalance, "_prepare_harness_plan", lambda *_args, **_kwargs: over_budget
    )
    monkeypatch.setattr(rebalance, "_plan_is_noop", lambda *_args, **_kwargs: True)

    assert rebalance.main(["--kind", "harness", "--repo", "o/r"]) == 1
