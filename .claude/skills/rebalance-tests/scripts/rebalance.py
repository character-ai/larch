#!/usr/bin/env python3
"""Rebalance CI test shards and verify the result.

Run from the repository root::

    python3 .claude/skills/rebalance-tests/scripts/rebalance.py [flags]

See .claude/skills/rebalance-tests/SKILL.md for full documentation.

NOTE: the final ``pr_merge`` call is intentionally commented out.
      Inspect the PR and merge manually once satisfied.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Bootstrap: add python/ to sys.path so the shared libraries are importable.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO_ROOT / "python"))

from larch.git import gh  # noqa: E402 — must come after sys.path is patched
from larch.git import git  # noqa: E402
from larch.core import proc  # noqa: E402
from larch.errors import ShipError  # noqa: E402


class _ProcRunner:
    """Adapter wrapping the module-level ``proc.run`` as a ``Runner`` instance."""

    def run(
        self,
        argv: Any,
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Any = None,
        check: bool = False,
        stdout: Any = None,
        stderr: Any = None,
    ) -> proc.CommandResult:
        return proc.run(
            list(argv),
            timeout=timeout,
            cwd=cwd,
            env=env,
            check=check,
            stdout=stdout,
            stderr=stderr,
        )


_RUNNER = _ProcRunner()
_GUARD = "test-harness-shards-coverage"
_ASSIGNMENTS_PATH = _REPO_ROOT / "python" / "shard-assignments.json"


@dataclass(frozen=True)
class HarnessPlan:
    current_shards: dict[int, list[str]]
    new_shards: dict[int, list[str]]
    medians: dict[str, float]
    n_shards: int
    baseline_spread: float
    cost_model: HarnessCostModel
    predicted_current: dict[int, float]
    predicted_new: dict[int, float]
    baseline_wall_clock: dict[int, float]
    baseline_slowest_wall_clock: float
    baseline_runner_seconds: float
    approved_slowest_wall_clock: float


@dataclass(frozen=True)
class PythonPlan:
    assignments: dict[str, int]
    medians: dict[str, float]
    n_shards: int


@dataclass(frozen=True)
class RebalancePlan:
    harness: HarnessPlan | None
    python: PythonPlan | None


@dataclass(frozen=True)
class HarnessTimingRow:
    run_id: int
    shard: int
    target: str
    seconds: float


@dataclass(frozen=True)
class HarnessBootstrapRow:
    run_id: int
    shard: int
    target: str
    bootstrap_kind: str
    seconds: float


@dataclass(frozen=True)
class JobTimingRow:
    run_id: int
    shard: int
    seconds: float


@dataclass(frozen=True)
class AffinityCost:
    group: str
    setup_seconds: float


@dataclass(frozen=True)
class CompileAffinitySpec:
    target: str
    group: str
    setup_seconds: float


@dataclass(frozen=True)
class HarnessCostModel:
    fixed_startup_seconds: float
    shared_setup_seconds: float
    target_seconds: dict[str, float]
    affinities: dict[str, AffinityCost]


@dataclass(frozen=True)
class CiTimingReport:
    kind: str
    row_count: int
    target_medians: dict[str, float]
    nodeid_medians: dict[str, float]
    shard_medians: dict[int, float]
    observed_shard_count: int | None
    untimed_targets: list[str]
    skipped_run_ids: list[int]
    sampled_run_ids: list[int] = field(default_factory=list)
    harness_rows: tuple[HarnessTimingRow, ...] = ()
    bootstrap_rows: tuple[HarnessBootstrapRow, ...] = ()
    job_rows: tuple[JobTimingRow, ...] = ()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        msg = f"must be >= 1, got {parsed}"
        raise argparse.ArgumentTypeError(msg)
    return parsed


def _positive_seconds(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0.0:
        msg = f"must be a positive finite number, got {value!r}"
        raise argparse.ArgumentTypeError(msg)
    return parsed


def _experiment_note(value: str) -> str:
    note = value.strip()
    if not note:
        raise argparse.ArgumentTypeError("must name the documented experiment")
    return note


def _compile_affinity(value: str) -> CompileAffinitySpec:
    """Parse one explicit ``TARGET=GROUP:SECONDS`` compile-affinity contract."""
    target, separator, remainder = value.partition("=")
    group, colon, raw_seconds = remainder.rpartition(":")
    if not separator or not target or not colon or not group:
        msg = "must have the form TARGET=GROUP:SECONDS"
        raise argparse.ArgumentTypeError(msg)
    if any(character.isspace() for character in target + group):
        msg = "target and group must not contain whitespace"
        raise argparse.ArgumentTypeError(msg)
    try:
        setup_seconds = float(raw_seconds)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"compile-affinity setup seconds {raw_seconds!r} are invalid"
        ) from exc
    if not math.isfinite(setup_seconds) or setup_seconds < 0.0:
        msg = f"compile-affinity setup seconds {raw_seconds!r} are invalid"
        raise argparse.ArgumentTypeError(msg)
    return CompileAffinitySpec(target, group, setup_seconds)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebalance test shards based on CI timing."
    )
    parser.add_argument("--repo", help="owner/name (auto-detected if omitted)")
    parser.add_argument("--kind", choices=("harness", "python", "all"), default="all")
    parser.add_argument("--n-runs", type=_positive_int, default=5, help="baseline CI runs to sample")
    parser.add_argument("--branch-prefix", default="rebalance-shards")
    parser.add_argument("--n-verify-runs", type=_positive_int, default=3)
    parser.add_argument(
        "--n-python-shards",
        type=_positive_int,
        default=None,
        help="expected python-tests shard count (auto-detected from CI when omitted)",
    )
    parser.add_argument("--balance-threshold", type=_positive_seconds, default=15.0)
    parser.add_argument(
        "--max-shard-wall-clock",
        type=_positive_seconds,
        default=300.0,
        help="real per-shard CI job wall-clock budget in seconds (jobs-API verdict)",
    )
    parser.add_argument(
        "--experimental-wall-clock-override",
        type=_experiment_note,
        default=None,
        metavar="NOTE",
        help=(
            "permit an otherwise-rejected measured harness regression for one "
            "documented experiment; missing or incompatible timing evidence still fails"
        ),
    )
    parser.add_argument(
        "--compile-affinity",
        action="append",
        type=_compile_affinity,
        default=[],
        metavar="TARGET=GROUP:SECONDS",
        help=(
            "declare a known shared compile group and its additional one-time "
            "setup cost; repeat for every grouped target"
        ),
    )
    parser.add_argument("--workflow", default="ci.yaml")
    parser.add_argument("--baseline-branch", default="main")
    return parser.parse_args(argv)


def _detect_repo(runner: _ProcRunner) -> str:
    """Return ``owner/name`` for the current git remote (origin)."""
    result = runner.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        cwd=str(_REPO_ROOT),
    )
    if result.returncode != 0:
        print(f"ERROR: could not detect repo name: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def _validate_partition() -> bool:
    """Run the structural partition checker; return True on success."""
    result = subprocess.run(
        ["bash", "scripts/test-harness-shards-coverage.sh"],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print("ERROR: partition validation failed:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


def _git_checkout_branch(branch: str) -> bool:
    """Switch to *branch*; return True on success."""
    result = _RUNNER.run(["git", "checkout", branch], cwd=str(_REPO_ROOT))
    if result.returncode != 0:
        print(
            f"ERROR: 'git checkout {branch}' failed (rc={result.returncode}):\n"
            f"{result.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def _wait_for_completed_run(
    runner: _ProcRunner,
    *,
    repo: str,
    branch: str,
    workflow: str,
    exclude: list[int],
    timeout_s: int = 1800,
    poll_s: int = 30,
) -> int:
    """Poll until a successful completed run appears that is not in *exclude*."""
    exclude_set = set(exclude)
    deadline = time.monotonic() + timeout_s
    start = time.monotonic()

    while True:
        elapsed = int(time.monotonic() - start)
        result = runner.run(
            [
                "gh", "run", "list",
                "--repo", repo,
                "--branch", branch,
                "--workflow", workflow,
                "--limit", "15",
                "--json", "databaseId,status,conclusion",
            ],
            cwd=str(_REPO_ROOT),
        )
        if result.returncode == 0:
            runs = json.loads(result.stdout or "[]")
            for run in runs:
                rid = int(run["databaseId"])
                if rid in exclude_set:
                    continue
                status = run.get("status", "")
                conclusion = run.get("conclusion") or ""
                if status == "completed":
                    if conclusion == "success":
                        return rid
                    msg = (
                        f"Run {rid} completed with conclusion={conclusion!r} "
                        f"on branch {branch!r}"
                    )
                    raise RuntimeError(msg)
            in_progress = [
                r["databaseId"]
                for r in runs
                if int(r["databaseId"]) not in exclude_set and r.get("status") != "completed"
            ]
            if in_progress:
                print(f"    [{elapsed}s] {len(in_progress)} run(s) in progress …", flush=True)
            else:
                print(f"    [{elapsed}s] no runs visible yet …", flush=True)
        else:
            print(f"    [{elapsed}s] gh run list failed (rc={result.returncode}); retrying …", flush=True)

        if time.monotonic() >= deadline:
            break
        time.sleep(poll_s)

    msg = f"No new successful CI run appeared within {timeout_s}s on branch {branch!r}"
    raise TimeoutError(msg)


def _trigger_and_wait(
    runner: _ProcRunner,
    *,
    repo: str,
    branch: str,
    workflow: str,
    exclude: list[int],
    run_label: str,
) -> int:
    """Trigger a workflow_dispatch run and wait for it to complete successfully."""
    print(f"  {run_label}: triggering workflow_dispatch on {branch!r} …")
    dispatch_result = gh.workflow_dispatch(runner, workflow, repo=repo, ref=branch)
    if dispatch_result.returncode != 0:
        msg = (
            f"workflow_dispatch failed (rc={dispatch_result.returncode}): "
            f"{dispatch_result.stderr.strip()}"
        )
        raise RuntimeError(msg)
    time.sleep(20)
    run_id = _wait_for_completed_run(
        runner,
        repo=repo,
        branch=branch,
        workflow=workflow,
        exclude=exclude,
    )
    print(f"    Completed run {run_id} ✓")
    return run_id


def _trigger_verification_runs(
    runner: _ProcRunner,
    *,
    repo: str,
    branch: str,
    workflow: str,
    n_verify_runs: int,
    exclude: Sequence[int] = (),
) -> list[int]:
    """Trigger verification CI runs and return their run ids."""
    verify_run_ids = list(exclude)
    new_run_ids: list[int] = []
    for i in range(n_verify_runs):
        run_id = _trigger_and_wait(
            runner,
            repo=repo,
            branch=branch,
            workflow=workflow,
            exclude=verify_run_ids,
            run_label=f"Run {i + 1}/{n_verify_runs}",
        )
        verify_run_ids.append(run_id)
        new_run_ids.append(run_id)
    return new_run_ids


_REPORT_KEYS = {
    "harness": (
        "schema_version",
        "kind",
        "sampled_run_ids",
        "rows",
        "bootstrap_rows",
        "target_medians",
        "shard_medians",
        "untimed_targets",
        "skipped_run_ids",
    ),
    "jobs": (
        "schema_version",
        "kind",
        "sampled_run_ids",
        "rows",
        "shard_medians",
        "skipped_run_ids",
    ),
    "pytest": (
        "schema_version",
        "kind",
        "sampled_run_ids",
        "rows",
        "nodeid_medians",
        "shard_medians",
        "observed_shard_count",
        "skipped_run_ids",
    ),
}
_ROW_KEYS = {
    "harness": ("run_id", "shard", "target", "seconds"),
    "jobs": ("run_id", "shard", "seconds"),
    "pytest": ("run_id", "shard", "nodeid", "seconds", "attempt", "shard_total"),
}


def _require_object_keys(
    value: object, expected: tuple[str, ...], *, context: str
) -> dict[str, object]:
    if not isinstance(value, dict) or tuple(value) != expected:
        raise ShipError(
            f"ci-timing {context} keys must be exactly {list(expected)!r} in order"
        )
    return value


def _require_list(value: object, *, context: str) -> list[object]:
    if not isinstance(value, list):
        raise ShipError(f"ci-timing {context} must be a list")
    return value


def _require_int(value: object, *, context: str, positive: bool = False) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or (positive and value < 1)
    ):
        qualifier = "positive " if positive else ""
        raise ShipError(f"ci-timing {context} must be a {qualifier}integer")
    return value


def _require_seconds(value: object, *, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ShipError(f"ci-timing {context} must be a finite number")
    seconds = float(value)
    if not math.isfinite(seconds) or seconds < 0:
        raise ShipError(f"ci-timing {context} must be a non-negative finite number")
    return seconds


def _require_string(value: object, *, context: str) -> str:
    if not isinstance(value, str):
        raise ShipError(f"ci-timing {context} must be a string")
    return value


def _parse_named_medians(
    payload: dict[str, object], *, field: str, name_field: str
) -> dict[str, float]:
    medians: dict[str, float] = {}
    for index, value in enumerate(_require_list(payload.get(field), context=field)):
        row = _require_object_keys(
            value,
            (name_field, "seconds"),
            context=f"{field}[{index}]",
        )
        name = _require_string(
            row[name_field], context=f"{field}[{index}].{name_field}"
        )
        if name in medians:
            raise ShipError(
                f"ci-timing {field} contains duplicate {name_field} {name!r}"
            )
        medians[name] = _require_seconds(
            row["seconds"], context=f"{field}[{index}].seconds"
        )
    return medians


def _parse_shard_medians(payload: dict[str, object]) -> dict[int, float]:
    medians: dict[int, float] = {}
    for index, value in enumerate(
        _require_list(payload.get("shard_medians"), context="shard_medians")
    ):
        row = _require_object_keys(
            value,
            ("shard", "seconds"),
            context=f"shard_medians[{index}]",
        )
        shard = _require_int(
            row["shard"], context=f"shard_medians[{index}].shard", positive=True
        )
        if shard in medians:
            raise ShipError(f"ci-timing shard_medians contains duplicate shard {shard}")
        medians[shard] = _require_seconds(
            row["seconds"], context=f"shard_medians[{index}].seconds"
        )
    return medians


def _strict_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key {key!r}")
        result[key] = value
    return result


def _parse_sampled_run_ids(payload: dict[str, object]) -> list[int]:
    run_ids: list[int] = []
    for index, value in enumerate(
        _require_list(payload["sampled_run_ids"], context="sampled_run_ids")
    ):
        run_id = _require_int(value, context=f"sampled_run_ids[{index}]", positive=True)
        if run_id in run_ids:
            raise ShipError(f"ci-timing sampled_run_ids contains duplicate run {run_id}")
        run_ids.append(run_id)
    return run_ids


def _parse_ci_timing_rows(
    payload: dict[str, object], *, expected_kind: str
) -> tuple[tuple[HarnessTimingRow, ...], tuple[JobTimingRow, ...]]:
    rows = _require_list(payload["rows"], context="rows")
    harness_rows: list[HarnessTimingRow] = []
    job_rows: list[JobTimingRow] = []
    for index, value in enumerate(rows):
        row = _require_object_keys(
            value, _ROW_KEYS[expected_kind], context=f"rows[{index}]"
        )
        run_id = _require_int(row["run_id"], context=f"rows[{index}].run_id", positive=True)
        shard = _require_int(row["shard"], context=f"rows[{index}].shard", positive=True)
        seconds = _require_seconds(row["seconds"], context=f"rows[{index}].seconds")
        if expected_kind == "harness":
            harness_rows.append(
                HarnessTimingRow(
                    run_id=run_id,
                    shard=shard,
                    target=_require_string(row["target"], context=f"rows[{index}].target"),
                    seconds=seconds,
                )
            )
        if expected_kind == "jobs":
            job_rows.append(JobTimingRow(run_id=run_id, shard=shard, seconds=seconds))
        if expected_kind == "pytest":
            _require_string(row["nodeid"], context=f"rows[{index}].nodeid")
            _require_int(
                row["attempt"], context=f"rows[{index}].attempt", positive=True
            )
            shard_total = row["shard_total"]
            if shard_total is not None:
                _require_int(
                    shard_total, context=f"rows[{index}].shard_total", positive=True
                )
    return tuple(harness_rows), tuple(job_rows)


def _parse_harness_bootstrap_rows(
    payload: dict[str, object],
) -> tuple[HarnessBootstrapRow, ...]:
    rows: list[HarnessBootstrapRow] = []
    expected = ("run_id", "shard", "target", "bootstrap_kind", "seconds")
    for index, value in enumerate(
        _require_list(payload["bootstrap_rows"], context="bootstrap_rows")
    ):
        row = _require_object_keys(
            value, expected, context=f"bootstrap_rows[{index}]"
        )
        bootstrap_kind = _require_string(
            row["bootstrap_kind"], context=f"bootstrap_rows[{index}].bootstrap_kind"
        )
        if bootstrap_kind not in {"cold", "warm", "unknown"}:
            raise ShipError(
                f"ci-timing bootstrap_rows[{index}].bootstrap_kind is invalid"
            )
        rows.append(
            HarnessBootstrapRow(
                run_id=_require_int(
                    row["run_id"], context=f"bootstrap_rows[{index}].run_id", positive=True
                ),
                shard=_require_int(
                    row["shard"], context=f"bootstrap_rows[{index}].shard", positive=True
                ),
                target=_require_string(
                    row["target"], context=f"bootstrap_rows[{index}].target"
                ),
                bootstrap_kind=bootstrap_kind,
                seconds=_require_seconds(
                    row["seconds"], context=f"bootstrap_rows[{index}].seconds"
                ),
            )
        )
    return tuple(rows)


def _parse_ci_timing_report(stdout: str, *, expected_kind: str) -> CiTimingReport:
    try:
        decoded = json.loads(stdout, object_pairs_hook=_strict_json_object)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ShipError(
            f"ci-timing {expected_kind} emitted invalid JSON: {exc}"
        ) from exc
    expected_keys = _REPORT_KEYS.get(expected_kind)
    if expected_keys is None:
        raise ShipError(f"unsupported ci-timing report kind {expected_kind!r}")
    payload = _require_object_keys(
        decoded, expected_keys, context=f"{expected_kind} report"
    )
    if _require_int(payload["schema_version"], context="schema_version") != 2:
        raise ShipError("ci-timing schema_version must be 2")
    if _require_string(payload["kind"], context="kind") != expected_kind:
        raise ShipError(f"ci-timing kind must be {expected_kind!r}")

    harness_rows, job_rows = _parse_ci_timing_rows(
        payload, expected_kind=expected_kind
    )
    row_count = len(_require_list(payload["rows"], context="rows"))

    target_medians = (
        _parse_named_medians(payload, field="target_medians", name_field="target")
        if expected_kind == "harness"
        else {}
    )
    nodeid_medians = (
        _parse_named_medians(payload, field="nodeid_medians", name_field="nodeid")
        if expected_kind == "pytest"
        else {}
    )
    observed_shard_count: int | None = None
    if expected_kind == "pytest" and payload["observed_shard_count"] is not None:
        observed_shard_count = _require_int(
            payload["observed_shard_count"],
            context="observed_shard_count",
            positive=True,
        )
    untimed_targets = []
    if expected_kind == "harness":
        untimed_targets = [
            _require_string(value, context=f"untimed_targets[{index}]")
            for index, value in enumerate(
                _require_list(payload["untimed_targets"], context="untimed_targets")
            )
        ]
    skipped_run_ids = [
        _require_int(value, context=f"skipped_run_ids[{index}]", positive=True)
        for index, value in enumerate(
            _require_list(payload["skipped_run_ids"], context="skipped_run_ids")
        )
    ]
    return CiTimingReport(
        kind=expected_kind,
        row_count=row_count,
        target_medians=target_medians,
        nodeid_medians=nodeid_medians,
        shard_medians=_parse_shard_medians(payload),
        observed_shard_count=observed_shard_count,
        untimed_targets=untimed_targets,
        skipped_run_ids=skipped_run_ids,
        sampled_run_ids=_parse_sampled_run_ids(payload),
        harness_rows=harness_rows,
        bootstrap_rows=(
            _parse_harness_bootstrap_rows(payload)
            if expected_kind == "harness"
            else ()
        ),
        job_rows=job_rows,
    )


def _run_ci_timing(
    runner: _ProcRunner,
    kind: str,
    *,
    repo: str,
    n_runs: int | None = None,
    workflow: str | None = None,
    branch: str | None = None,
    run_ids: Sequence[int] = (),
    required_targets: Sequence[str] = (),
) -> CiTimingReport:
    argv = [str(_REPO_ROOT / "scripts" / "larch.sh"), "ci-timing", kind, "--repo", repo]
    if run_ids:
        for run_id in run_ids:
            argv.extend(("--run-id", str(run_id)))
    else:
        if n_runs is not None:
            argv.extend(("--n-runs", str(n_runs)))
        if workflow is not None:
            argv.extend(("--workflow", workflow))
        if branch is not None:
            argv.extend(("--branch", branch))
    for target in required_targets:
        argv.extend(("--required-target", target))
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(_REPO_ROOT)
    result = runner.run(argv, cwd=str(_REPO_ROOT), env=env)
    if result.returncode != 0:
        detail = result.stderr.strip() or f"returncode {result.returncode}"
        raise ShipError(f"ci-timing {kind} failed: {detail}")
    if result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)
    return _parse_ci_timing_report(result.stdout, expected_kind=kind)


def _parse_shard_map(stdout: str, *, context: str) -> dict[int, list[str]]:
    """Parse the Rust test-shard JSON map without retaining a Python fallback."""
    try:
        decoded = json.loads(stdout, object_pairs_hook=_strict_json_object)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ShipError(f"test-shard {context} emitted invalid JSON: {exc}") from exc
    if not isinstance(decoded, dict):
        raise ShipError(f"test-shard {context} output must be a JSON object")
    shards: dict[int, list[str]] = {}
    for raw_shard, targets in decoded.items():
        if not isinstance(raw_shard, str) or not raw_shard.isdecimal():
            raise ShipError(f"test-shard {context} has an invalid shard id {raw_shard!r}")
        shard = int(raw_shard)
        if shard < 1 or str(shard) != raw_shard or shard in shards:
            raise ShipError(f"test-shard {context} has an invalid shard id {raw_shard!r}")
        if not isinstance(targets, list) or not all(isinstance(target, str) for target in targets):
            raise ShipError(f"test-shard {context} shard {shard} must contain only strings")
        shards[shard] = targets
    return shards


def _run_test_shard(
    runner: _ProcRunner,
    command: list[str],
    *,
    input_payload: object | None = None,
) -> str:
    """Run one Rust test-shard command through the verified bootstrap."""
    argv = [str(_REPO_ROOT / "scripts" / "larch.sh"), "test-shard", *command]
    input_path: Path | None = None
    try:
        if input_payload is not None:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as handle:
                input_path = Path(handle.name)
                json.dump(input_payload, handle, allow_nan=False, separators=(",", ":"))
            argv.extend(("--input", str(input_path)))
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(_REPO_ROOT)
        result = runner.run(argv, cwd=str(_REPO_ROOT), env=env)
    finally:
        if input_path is not None:
            input_path.unlink(missing_ok=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or f"returncode {result.returncode}"
        raise ShipError(f"test-shard {command[0]} failed: {detail}")
    if result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)
    return result.stdout


def _pack_shards(
    medians: dict[str, float],
    n_shards: int,
    *,
    guard: str,
    extras: Sequence[str] = (),
) -> dict[int, list[str]]:
    """Delegate LPT packing to the Rust owner while preserving timing order."""
    command = ["pack", "--n-shards", str(n_shards)]
    if guard:
        command.extend(("--guard", guard))
    for extra in extras:
        command.extend(("--extra", extra))
    payload = [
        {"target": target, "seconds": seconds}
        for target, seconds in medians.items()
    ]
    return _parse_shard_map(
        _run_test_shard(_RUNNER, command, input_payload=payload), context="pack"
    )


def _pack_harness_shards(
    model: HarnessCostModel,
    targets: Sequence[str],
    n_shards: int,
    *,
    guard: str,
    active_shard_ids: Sequence[int] | None = None,
) -> dict[int, list[str]]:
    """Pack through the Rust owner, keeping nonselected shards empty."""
    shard_ids = list(range(1, n_shards + 1))
    active = list(active_shard_ids) if active_shard_ids is not None else shard_ids
    if not active or len(set(active)) != len(active) or any(shard not in shard_ids for shard in active):
        raise ShipError("harness active shard ids must be a nonempty unique subset")
    command = [
        "pack",
        "--n-shards",
        str(len(active)),
        "--fixed-startup-seconds",
        str(model.fixed_startup_seconds + model.shared_setup_seconds),
    ]
    if guard:
        command.extend(("--guard", guard))
    payload: list[dict[str, object]] = []
    for target in targets:
        try:
            seconds = model.target_seconds[target]
        except KeyError as exc:
            raise ShipError(f"harness cost model has no timing for {target!r}") from exc
        row: dict[str, object] = {"target": target, "seconds": seconds}
        affinity = model.affinities.get(target)
        if affinity is not None:
            row["affinity_group"] = affinity.group
            row["affinity_setup_seconds"] = affinity.setup_seconds
        payload.append(row)
    packed = _parse_shard_map(
        _run_test_shard(_RUNNER, command, input_payload=payload),
        context="pack",
    )
    result = {shard: [] for shard in shard_ids}
    for virtual_shard, physical_shard in enumerate(active, start=1):
        result[physical_shard] = packed[virtual_shard]
    return result


def _read_shards(makefile_path: Path) -> dict[int, list[str]]:
    """Read Makefile shard lines through the Rust grammar owner."""
    return _parse_shard_map(
        _run_test_shard(
            _RUNNER, ["read-makefile", "--path", str(makefile_path)]
        ),
        context="read-makefile",
    )


def _write_shards(makefile_path: Path, shards: dict[int, list[str]]) -> None:
    """Rewrite Makefile shard lines through the Rust grammar owner."""
    payload = {str(shard): targets for shard, targets in shards.items()}
    _ = _run_test_shard(
        _RUNNER,
        ["write-makefile", "--path", str(makefile_path)],
        input_payload=payload,
    )


def _print_time_table(label: str, values: dict[int, float]) -> None:
    """Print a per-shard time table and its max-min spread."""
    rows = [(shard, values[shard]) for shard in sorted(values)]
    print(f"\n{label}")
    print(f"  {'Shard':>6}  {'Total (s)':>10}")
    for shard, total in rows:
        print(f"  {shard:>6}  {total:>10.1f}")
    totals = [t for _, t in rows]
    if totals:
        spread = max(totals) - min(totals)
        print(f"  Spread (max-min): {spread:.1f}s")


def _print_observed_job_runs(rows: Sequence[JobTimingRow]) -> None:
    """Print every jobs-API verification run as an independent shard table."""
    by_run: dict[int, dict[int, float]] = {}
    for row in rows:
        by_run.setdefault(row.run_id, {})[row.shard] = row.seconds
    for run_id in sorted(by_run):
        _print_time_table(
            f"OBSERVED run {run_id} (real CI job wall-clock):", by_run[run_id]
        )


def _median(samples: Sequence[float], *, context: str) -> float:
    if not samples:
        raise ShipError(f"no comparable {context} samples")
    ordered = sorted(samples)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2.0


def _validate_harness_cohort(
    report: CiTimingReport,
    *,
    expected_shards: dict[int, list[str]],
    expected_run_count: int,
) -> list[int]:
    """Require complete, bootstrap-paired timing from one stable inventory."""
    run_ids = report.sampled_run_ids
    if len(run_ids) != expected_run_count:
        raise ShipError(
            f"harness timing cohort has {len(run_ids)} sampled runs; expected {expected_run_count}"
        )
    if report.skipped_run_ids:
        raise ShipError(
            "harness timing cohort has unreadable runs: "
            + ", ".join(str(run_id) for run_id in report.skipped_run_ids)
        )
    n_shards = len(expected_shards)
    expected_shard_ids = set(range(1, n_shards + 1))
    if set(expected_shards) != expected_shard_ids:
        raise ShipError("current Makefile harness shard identifiers are not contiguous")
    expected_target_counts = Counter(
        target for targets in expected_shards.values() for target in targets
    )
    if any(count != 1 for count in expected_target_counts.values()):
        raise ShipError("current harness inventory contains duplicate targets")
    timing_by_run_shard: dict[tuple[int, int], list[HarnessTimingRow]] = {}
    bootstrap_by_run_shard: dict[tuple[int, int], list[HarnessBootstrapRow]] = {}
    for row in report.harness_rows:
        timing_by_run_shard.setdefault((row.run_id, row.shard), []).append(row)
    for row in report.bootstrap_rows:
        bootstrap_by_run_shard.setdefault((row.run_id, row.shard), []).append(row)
    actual_timing_runs = {run_id for run_id, _ in timing_by_run_shard}
    actual_bootstrap_runs = {run_id for run_id, _ in bootstrap_by_run_shard}
    if actual_timing_runs != set(run_ids) or actual_bootstrap_runs != set(run_ids):
        raise ShipError("harness timing cohort is missing target or bootstrap evidence")
    mark_counts_by_shard: dict[int, Counter[str]] = {}
    for run_id in run_ids:
        timing_shards = {
            shard for candidate_run, shard in timing_by_run_shard if candidate_run == run_id
        }
        bootstrap_shards = {
            shard for candidate_run, shard in bootstrap_by_run_shard if candidate_run == run_id
        }
        nonempty_shards = {
            shard for shard, targets in expected_shards.items() if targets
        }
        if timing_shards != nonempty_shards or bootstrap_shards != nonempty_shards:
            raise ShipError(f"harness timing cohort has incompatible shard coverage in run {run_id}")
        run_targets: Counter[str] = Counter()
        for shard in expected_shard_ids:
            target_rows = timing_by_run_shard.get((run_id, shard), [])
            bootstrap_rows = bootstrap_by_run_shard.get((run_id, shard), [])
            target_counts = Counter(row.target for row in target_rows)
            bootstrap_counts = Counter(row.target for row in bootstrap_rows)
            if set(target_counts) != set(expected_shards[shard]):
                raise ShipError(
                    f"harness target inventory drift detected in run {run_id}, shard {shard}"
                )
            if target_counts != bootstrap_counts:
                raise ShipError(
                    f"harness bootstrap evidence does not pair with target rows in run {run_id}, shard {shard}"
                )
            prior_mark_counts = mark_counts_by_shard.setdefault(shard, target_counts)
            if prior_mark_counts != target_counts:
                raise ShipError(
                    f"harness timing cohort has incompatible target-mark counts in run {run_id}, shard {shard}"
                )
            if not target_rows:
                continue
            bootstrap_kinds = Counter(row.bootstrap_kind for row in bootstrap_rows)
            if bootstrap_kinds.get("unknown", 0) or bootstrap_kinds.get("cold", 0) != 1:
                raise ShipError(
                    f"harness bootstrap evidence is incomplete in run {run_id}, shard {shard}"
                )
            if bootstrap_kinds.get("warm", 0) != len(bootstrap_rows) - 1:
                raise ShipError(
                    f"harness bootstrap evidence has an incompatible warm/cold cohort in run {run_id}, shard {shard}"
                )
            run_targets.update(target_counts)
        if set(run_targets) != set(expected_target_counts):
            raise ShipError(f"harness target inventory drift detected in run {run_id}")
    if set(report.target_medians) != set(expected_target_counts):
        raise ShipError("harness median inventory does not match the current Makefile")
    return list(run_ids)


def _validate_job_cohort(
    report: CiTimingReport,
    *,
    run_ids: Sequence[int],
    n_shards: int,
) -> None:
    """Require one real harness-job duration for each sampled run and shard."""
    if report.sampled_run_ids != list(run_ids):
        raise ShipError("jobs API report did not retain the requested timing cohort")
    if report.skipped_run_ids:
        raise ShipError(
            "jobs API timing cohort has unreadable runs: "
            + ", ".join(str(run_id) for run_id in report.skipped_run_ids)
        )
    expected = {(run_id, shard) for run_id in run_ids for shard in range(1, n_shards + 1)}
    observed = {(row.run_id, row.shard) for row in report.job_rows}
    if observed != expected or len(report.job_rows) != len(observed):
        raise ShipError("jobs API timing cohort has missing or duplicate harness shard rows")


def _compile_affinities(
    specs: Sequence[CompileAffinitySpec], *, expected_targets: Sequence[str]
) -> dict[str, AffinityCost]:
    """Validate explicit compile-affinity contracts against this inventory."""
    expected = set(expected_targets)
    affinities: dict[str, AffinityCost] = {}
    setup_by_group: dict[str, float] = {}
    for spec in specs:
        if spec.target not in expected:
            raise ShipError(
                f"compile-affinity target {spec.target!r} is not in the current Makefile"
            )
        if spec.target in affinities:
            raise ShipError(
                f"compile-affinity target {spec.target!r} is declared more than once"
            )
        prior_setup = setup_by_group.setdefault(spec.group, spec.setup_seconds)
        if prior_setup != spec.setup_seconds:
            raise ShipError(
                f"compile-affinity group {spec.group!r} has inconsistent setup seconds"
            )
        affinities[spec.target] = AffinityCost(spec.group, spec.setup_seconds)
    return affinities


def _harness_cost_model(
    report: CiTimingReport,
    jobs: CiTimingReport,
    *,
    expected_targets: Sequence[str],
    affinities: dict[str, AffinityCost],
) -> HarnessCostModel:
    """Derive fixed startup, target work, and one-time timer setup from evidence."""
    target_rows: dict[tuple[int, int], list[HarnessTimingRow]] = {}
    bootstrap_rows: dict[tuple[int, int], list[HarnessBootstrapRow]] = {}
    job_rows = {(row.run_id, row.shard): row.seconds for row in jobs.job_rows}
    for row in report.harness_rows:
        target_rows.setdefault((row.run_id, row.shard), []).append(row)
    for row in report.bootstrap_rows:
        bootstrap_rows.setdefault((row.run_id, row.shard), []).append(row)
    fixed_startup_samples: list[float] = []
    cold_samples: list[float] = []
    warm_samples: list[float] = []
    mark_count_samples: dict[str, list[int]] = {}
    for key, job_seconds in job_rows.items():
        shard_target_rows = target_rows.get(key, [])
        shard_bootstrap_rows = bootstrap_rows.get(key, [])
        target_total = sum(row.seconds for row in shard_target_rows)
        bootstrap_total = sum(row.seconds for row in shard_bootstrap_rows)
        fixed_startup = job_seconds - target_total - bootstrap_total
        if fixed_startup < 0.0:
            run_id, shard = key
            raise ShipError(
                f"jobs API wall-clock is below recorded harness work in run {run_id}, shard {shard}"
            )
        fixed_startup_samples.append(fixed_startup)
        for row in shard_bootstrap_rows:
            if row.bootstrap_kind == "cold":
                cold_samples.append(row.seconds)
            elif row.bootstrap_kind == "warm":
                warm_samples.append(row.seconds)
        for target, count in Counter(row.target for row in shard_bootstrap_rows).items():
            mark_count_samples.setdefault(target, []).append(count)
    warm_seconds = _median(warm_samples, context="warm timer-bootstrap")
    cold_seconds = _median(cold_samples, context="cold timer-bootstrap")
    if cold_seconds < warm_seconds:
        raise ShipError("cold timer-bootstrap median is below warm timer-bootstrap median")
    target_seconds: dict[str, float] = {}
    for target in expected_targets:
        counts = mark_count_samples.get(target, [])
        if not counts or len(set(counts)) != 1:
            raise ShipError(
                f"harness timing cohort has incompatible target-mark counts for {target!r}"
            )
        target_seconds[target] = report.target_medians[target] + counts[0] * warm_seconds
    return HarnessCostModel(
        fixed_startup_seconds=_median(fixed_startup_samples, context="fixed job-startup"),
        shared_setup_seconds=cold_seconds - warm_seconds,
        target_seconds=target_seconds,
        affinities=affinities,
    )


def _predicted_shard_times(
    shards: dict[int, list[str]], model: HarnessCostModel
) -> dict[int, float]:
    """Return wall-clock estimates with fixed and affinity setup costs included."""
    predicted: dict[int, float] = {}
    for shard, targets in shards.items():
        total = model.fixed_startup_seconds
        if targets:
            total += model.shared_setup_seconds
        charged_groups: set[str] = set()
        for target in targets:
            try:
                total += model.target_seconds[target]
            except KeyError as exc:
                raise ShipError(f"harness cost model has no timing for {target!r}") from exc
            affinity = model.affinities.get(target)
            if affinity is not None and affinity.group not in charged_groups:
                total += affinity.setup_seconds
                charged_groups.add(affinity.group)
        predicted[shard] = total
    return predicted


def _job_metrics(rows: Sequence[JobTimingRow]) -> tuple[float, float]:
    """Return median per-run slowest-shard and summed-runner durations."""
    by_run: dict[int, list[float]] = {}
    for row in rows:
        by_run.setdefault(row.run_id, []).append(row.seconds)
    slowest_samples = [max(values) for values in by_run.values()]
    runner_samples = [sum(values) for values in by_run.values()]
    return (
        _median(slowest_samples, context="slowest harness-job wall-clock"),
        _median(runner_samples, context="summed harness-runner"),
    )


def _permit_experimental_override(args: argparse.Namespace, reason: str) -> bool:
    """Return whether a documented experiment may continue after a measured regression."""
    note = args.experimental_wall_clock_override
    if note is None:
        return False
    print(
        "WARNING: documented experimental wall-clock override is active: "
        f"{note}\n  Override reason: {reason}",
        file=sys.stderr,
    )
    return True


def _predicted_harness_layout_violations(
    *,
    current: dict[int, float],
    proposed: dict[int, float],
    approved_slowest_wall_clock: float,
) -> list[str]:
    """List modeled slowest-shard and runner-cost regressions."""
    current_slowest = max(current.values())
    proposed_slowest = max(proposed.values())
    current_runner_seconds = sum(current.values())
    proposed_runner_seconds = sum(proposed.values())
    violations: list[str] = []
    if proposed_slowest > current_slowest:
        violations.append(
            f"predicted slowest shard {proposed_slowest:.1f}s exceeds current model "
            f"{current_slowest:.1f}s"
        )
    if proposed_slowest > approved_slowest_wall_clock:
        violations.append(
            f"predicted slowest shard {proposed_slowest:.1f}s exceeds approved "
            f"wall-clock {approved_slowest_wall_clock:.1f}s"
        )
    if proposed_runner_seconds > current_runner_seconds:
        violations.append(
            f"predicted summed harness runner time {proposed_runner_seconds:.1f}s exceeds "
            f"the current model {current_runner_seconds:.1f}s"
        )
    return violations


def _require_predicted_harness_layout(
    args: argparse.Namespace,
    *,
    current: dict[int, float],
    proposed: dict[int, float],
    approved_slowest_wall_clock: float,
) -> None:
    """Reject an in-memory layout that worsens measured or modeled wall-clock."""
    violations = _predicted_harness_layout_violations(
        current=current,
        proposed=proposed,
        approved_slowest_wall_clock=approved_slowest_wall_clock,
    )
    if not violations:
        return
    reason = "; ".join(violations)
    if _permit_experimental_override(args, reason):
        return
    raise ShipError(reason)


def _active_shard_ids(
    current_shards: dict[int, list[str]], active_count: int
) -> list[int]:
    """Choose stable physical runner ids for one active-shard candidate."""
    active = [shard for shard, targets in sorted(current_shards.items()) if targets]
    inactive = [shard for shard, targets in sorted(current_shards.items()) if not targets]
    if active_count <= len(active):
        return active[:active_count]
    return active + inactive[: active_count - len(active)]


def _select_harness_layout(
    args: argparse.Namespace,
    *,
    model: HarnessCostModel,
    targets: Sequence[str],
    current_shards: dict[int, list[str]],
    approved_slowest_wall_clock: float,
) -> dict[int, list[str]]:
    """Choose the lowest-latency model layout that does not raise runner cost."""
    n_shards = len(current_shards)
    current = _predicted_shard_times(current_shards, model)
    candidates: list[tuple[dict[int, list[str]], dict[int, float]]] = [
        (current_shards, current)
    ]
    for active_count in range(1, n_shards + 1):
        active_ids = _active_shard_ids(current_shards, active_count)
        layout = _pack_harness_shards(
            model,
            targets,
            n_shards,
            guard=_GUARD,
            active_shard_ids=active_ids,
        )
        candidates.append((layout, _predicted_shard_times(layout, model)))

    safe = [
        candidate
        for candidate in candidates
        if not _predicted_harness_layout_violations(
            current=current,
            proposed=candidate[1],
            approved_slowest_wall_clock=approved_slowest_wall_clock,
        )
    ]
    if safe:
        layout, _ = min(
            safe,
            key=lambda candidate: (
                max(candidate[1].values()),
                sum(candidate[1].values()),
                candidate[0] != current_shards,
            ),
        )
        active_count = sum(bool(targets) for targets in layout.values())
        print(f"  Selected {active_count} active runner(s) out of {n_shards}")
        return layout

    layout, predicted = min(
        candidates,
        key=lambda candidate: (max(candidate[1].values()), sum(candidate[1].values())),
    )
    _require_predicted_harness_layout(
        args,
        current=current,
        proposed=predicted,
        approved_slowest_wall_clock=approved_slowest_wall_clock,
    )
    return layout


def _collect_wall_clock(
    runner: _ProcRunner,
    run_ids: list[int],
    *,
    repo: str,
) -> CiTimingReport:
    """Return raw and median real CI wall-clock evidence for an exact cohort."""
    return _run_ci_timing(runner, "jobs", repo=repo, run_ids=run_ids)


def _report_wall_clock_balance(
    wall_clock: dict[int, float],
    *,
    max_shard_wall_clock: float,
    n_verify_runs: int,
) -> bool:
    """Print the real per-shard wall-clock table and verdict."""
    slowest_shard, slowest = max(wall_clock.items(), key=lambda item: item[1])
    fastest = min(wall_clock.values())
    spread = slowest - fastest
    over_budget = sorted(shard for shard, secs in wall_clock.items() if secs > max_shard_wall_clock)

    print(f"\nReal CI job wall-clock (jobs API, median of {n_verify_runs} verification runs):")
    print(f"  {'Shard':>6}  {'Wall-clock (s)':>14}")
    for shard_n in sorted(wall_clock):
        marker = "  <-- over budget" if wall_clock[shard_n] > max_shard_wall_clock else ""
        print(f"  {shard_n:>6}  {wall_clock[shard_n]:>14.1f}{marker}")
    print(f"  Slowest shard: {slowest_shard} ({slowest:.1f}s)")
    print(f"  Spread (max-min): {spread:.1f}s")
    print(f"  Budget (--max-shard-wall-clock): {max_shard_wall_clock:.1f}s")

    if over_budget:
        print(
            f"⚠ Shard balance FAILED: {len(over_budget)} shard(s) over the "
            f"{max_shard_wall_clock:.1f}s wall-clock budget: {over_budget}"
        )
        return False
    print(
        f"✓ Shard balance VERIFIED: slowest shard {slowest:.1f}s within "
        f"{max_shard_wall_clock:.1f}s budget"
    )
    return True


def _pack_nodeids(medians: dict[str, float], n_shards: int) -> dict[str, int]:
    """Pack pytest nodeids into ``1..n`` shard ids by LPT."""
    packed = _pack_shards(medians, n_shards, guard="")
    assignments: dict[str, int] = {}
    for shard_id, nodeids in packed.items():
        for nodeid in nodeids:
            assignments[nodeid] = shard_id
    return assignments


def _assignments_json_text(assignments: dict[str, int]) -> str:
    return json.dumps(assignments, sort_keys=True, indent=2) + "\n"


def _write_assignments_json(path: Path, assignments: dict[str, int]) -> None:
    """Atomically write pytest shard assignments."""
    tmp_path = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    try:
        tmp_path.write_text(_assignments_json_text(assignments), encoding="utf-8")
        os.replace(tmp_path, path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def _assert_artifact_paths_clean(paths: list[str]) -> None:
    """Raise when any selected artifact path has local git dirt."""
    dirty: list[str] = []
    for path in paths:
        result = git.status_porcelain_paths(_RUNNER, path, cwd=str(_REPO_ROOT))
        if result.returncode != 0:
            stderr = result.stderr.strip() or f"returncode {result.returncode}"
            raise ShipError(f"git status failed for {path}: {stderr}")
        if result.stdout.strip():
            dirty.append(path)
    if dirty:
        msg = "refusing to rebalance with dirty artifact path(s): " + ", ".join(dirty)
        raise ShipError(msg)


def _revert_written_paths(paths: list[str]) -> None:
    """Restore staged and working-tree state for written artifact paths."""
    for path in paths:
        restore = git.restore_staged(_RUNNER, path, cwd=str(_REPO_ROOT))
        if restore.returncode != 0:
            stderr = restore.stderr.strip() or f"returncode {restore.returncode}"
            raise ShipError(f"git restore --staged failed for {path}: {stderr}")
        checkout = git.checkout_paths(_RUNNER, path, cwd=str(_REPO_ROOT))
        if checkout.returncode != 0:
            stderr = checkout.stderr.strip() or f"returncode {checkout.returncode}"
            raise ShipError(f"git checkout -- failed for {path}: {stderr}")


def _paths_for_kind(kind: str) -> list[str]:
    paths: list[str] = []
    if kind in {"harness", "all"}:
        paths.append("Makefile")
    if kind in {"python", "all"}:
        paths.append("python/shard-assignments.json")
    return paths


def _path_would_match(path: Path, text: str) -> bool:
    return path.exists() and path.read_text(encoding="utf-8") == text


def _paths_to_stage(kind: str, plan: RebalancePlan) -> list[str]:
    paths: list[str] = []
    if kind in {"harness", "all"} and plan.harness is not None:
        paths.append("Makefile")
    if kind in {"python", "all"} and plan.python is not None:
        paths.append("python/shard-assignments.json")
    return paths


def _plan_is_noop(plan: RebalancePlan, makefile_path: Path) -> bool:
    harness_noop = plan.harness is None
    if plan.harness is not None:
        before = _read_shards(makefile_path)
        harness_noop = before == plan.harness.new_shards
    python_noop = plan.python is None
    if plan.python is not None:
        python_noop = _path_would_match(
            _ASSIGNMENTS_PATH, _assignments_json_text(plan.python.assignments)
        )
    return harness_noop and python_noop


def _require_noop_harness_budget(
    args: argparse.Namespace, plan: HarnessPlan
) -> None:
    """Do not let an unchanged over-budget harness layout exit successfully."""
    if plan.baseline_slowest_wall_clock <= args.max_shard_wall_clock:
        return
    reason = (
        f"baseline measured slowest shard {plan.baseline_slowest_wall_clock:.1f}s exceeds "
        f"--max-shard-wall-clock {args.max_shard_wall_clock:.1f}s"
    )
    if _permit_experimental_override(args, reason):
        return
    raise ShipError(reason)


def _commit_subject(kind: str) -> str:
    labels = {"all": "harness+python", "harness": "harness", "python": "python"}
    return f"chore: rebalance test shards ({labels[kind]})"


def _create_pr_body(args: argparse.Namespace, plan: RebalancePlan) -> str:
    legs: list[str] = []
    files: list[str] = []
    if plan.harness is not None:
        legs.append("harness")
        files.append("Makefile")
    if plan.python is not None:
        legs.append("python")
        files.append("python/shard-assignments.json")
    body = [
        "Automatically generated by `/rebalance-tests`.",
        "",
        f"- Legs: {', '.join(legs)}",
        f"- Files: {', '.join(files)}",
        f"- Baseline: {args.n_runs} successful runs on `{args.baseline_branch}`",
        "- Merge remains operator-owned.",
    ]
    if plan.harness is not None:
        harness = plan.harness
        body.extend(
            [
                f"- Harness predicted packed spread: {harness.baseline_spread:.1f}s",
                f"- Harness baseline observed slowest shard: {harness.baseline_slowest_wall_clock:.1f}s",
                f"- Harness baseline summed runner time: {harness.baseline_runner_seconds:.1f}s",
                f"- Harness approved slowest-shard threshold: {harness.approved_slowest_wall_clock:.1f}s",
            ]
        )
        if args.experimental_wall_clock_override is not None:
            body.append(
                "- Experimental wall-clock override: "
                + args.experimental_wall_clock_override
            )
    if plan.python is not None:
        body.append(
            f"- Python nodeids assigned: {len(plan.python.assignments)} across {plan.python.n_shards} shards"
        )
    return "\n".join(body) + "\n"


def _prepare_harness_plan(
    args: argparse.Namespace, repo: str, makefile_path: Path
) -> HarnessPlan:
    print("\n[gate:harness] Reading current Makefile shard layout …")
    current_shards = _read_shards(makefile_path)
    n_shards = len(current_shards)
    all_shard_targets: list[str] = []
    for targets in current_shards.values():
        all_shard_targets.extend(targets)
    print(f"  {n_shards} shards, {len(all_shard_targets)} total targets")

    print(
        f"\n[gate:harness] Fetching timing from last {args.n_runs} successful CI runs "
        f"on {args.baseline_branch!r} …"
    )
    report = _run_ci_timing(
        _RUNNER,
        "harness",
        repo=repo,
        branch=args.baseline_branch,
        workflow=args.workflow,
        n_runs=args.n_runs,
        required_targets=all_shard_targets,
    )
    if report.row_count == 0:
        raise ShipError("no LARCH_HARNESS_TIMING rows found in any CI run log")
    medians = report.target_medians
    print(f"  Medians computed for {len(medians)} targets")

    untimed = report.untimed_targets
    if untimed:
        print(
            f"\nERROR: refusing to rebalance — {len(untimed)} shard target(s) "
            "have NO timing data:",
            file=sys.stderr,
        )
        for target in sorted(untimed):
            print(f"  - {target}", file=sys.stderr)
        raise ShipError("untimed test-harness target(s) found")

    sampled_run_ids = _validate_harness_cohort(
        report,
        expected_shards=current_shards,
        expected_run_count=args.n_runs,
    )
    jobs = _collect_wall_clock(_RUNNER, sampled_run_ids, repo=repo)
    _validate_job_cohort(jobs, run_ids=sampled_run_ids, n_shards=n_shards)
    affinities = _compile_affinities(
        args.compile_affinity,
        expected_targets=all_shard_targets,
    )
    model = _harness_cost_model(
        report,
        jobs,
        expected_targets=all_shard_targets,
        affinities=affinities,
    )
    predicted_current = _predicted_shard_times(current_shards, model)

    print(f"\n[gate:harness] Packing {n_shards} shards with startup- and affinity-aware LPT …")
    baseline_slowest, baseline_runner_seconds = _job_metrics(jobs.job_rows)
    approved_slowest = min(args.max_shard_wall_clock, baseline_slowest)
    new_shards = _select_harness_layout(
        args,
        model=model,
        targets=all_shard_targets,
        current_shards=current_shards,
        approved_slowest_wall_clock=approved_slowest,
    )
    predicted_new = _predicted_shard_times(new_shards, model)
    _print_time_table("BASELINE (cost-model estimate):", predicted_current)
    _print_time_table("PROPOSED (cost-model estimate):", predicted_new)
    _print_time_table("BASELINE (real CI job wall-clock):", jobs.shard_medians)
    totals = list(predicted_new.values())
    spread = max(totals) - min(totals) if totals else 0.0
    return HarnessPlan(
        current_shards=current_shards,
        new_shards=new_shards,
        medians=medians,
        n_shards=n_shards,
        baseline_spread=spread,
        cost_model=model,
        predicted_current=predicted_current,
        predicted_new=predicted_new,
        baseline_wall_clock=jobs.shard_medians,
        baseline_slowest_wall_clock=baseline_slowest,
        baseline_runner_seconds=baseline_runner_seconds,
        approved_slowest_wall_clock=approved_slowest,
    )


def _prepare_python_plan(args: argparse.Namespace, repo: str) -> PythonPlan:
    print(
        f"\n[gate:python] Fetching pytest durations from last {args.n_runs} successful CI runs "
        f"on {args.baseline_branch!r} …"
    )
    report = _run_ci_timing(
        _RUNNER,
        "pytest",
        repo=repo,
        branch=args.baseline_branch,
        workflow=args.workflow,
        n_runs=args.n_runs,
    )
    if report.row_count == 0:
        raise ShipError("no parseable python-tests --durations=0 call rows found")
    observed = report.observed_shard_count
    if observed is None:
        raise ShipError(
            "conflicting or missing python-tests shard X of N totals in CI logs"
        )
    if args.n_python_shards is None:
        n_python_shards = observed
        print(f"  Auto-detected {n_python_shards} python-tests shards from CI")
    else:
        n_python_shards = args.n_python_shards
        if observed != n_python_shards:
            raise ShipError(
                f"--n-python-shards={n_python_shards} does not match observed CI shard count {observed}"
            )
    medians = report.nodeid_medians
    if not medians:
        raise ShipError("no pytest nodeid medians after latest-attempt dedup")
    assignments = _pack_nodeids(medians, n_python_shards)
    print(f"  Packed {len(assignments)} nodeids across {n_python_shards} shards")
    return PythonPlan(
        assignments=assignments, medians=medians, n_shards=n_python_shards
    )


def _write_selected_artifacts(plan: RebalancePlan, makefile_path: Path) -> list[str]:
    written: list[str] = []
    if plan.harness is not None:
        print("\n[write:harness] Writing updated shard lines to Makefile …")
        _write_shards(makefile_path, plan.harness.new_shards)
        written.append("Makefile")
        print("\n[write:harness] Validating partition with test-harness-shards-coverage.sh …")
        if not _validate_partition():
            print("ERROR: partition invalid — reverting Makefile changes", file=sys.stderr)
            _revert_written_paths(["Makefile"])
            raise ShipError("harness partition validation failed")
        print("  Partition valid ✓")
    if plan.python is not None:
        print("\n[write:python] Writing python/shard-assignments.json …")
        try:
            _write_assignments_json(_ASSIGNMENTS_PATH, plan.python.assignments)
        except Exception as exc:
            print(f"ERROR: writing assignments JSON failed: {exc}", file=sys.stderr)
            if written:
                _revert_written_paths(written)
            raise ShipError("assignments JSON write failed") from exc
        written.append("python/shard-assignments.json")
    return written


def _commit_push_and_pr(
    args: argparse.Namespace,
    *,
    repo: str,
    branch_name: str,
    original_branch: str,
    plan: RebalancePlan,
    paths_to_stage: list[str],
) -> gh.PullRequest:
    print(f"\n[git] Creating branch {branch_name!r} and pushing …")
    res = git.branch(_RUNNER, branch_name, cwd=str(_REPO_ROOT))
    if res.returncode != 0:
        raise ShipError(f"git branch failed: {res.stderr.strip()}")

    if not _git_checkout_branch(branch_name):
        _git_checkout_branch(original_branch)
        raise ShipError("git checkout branch failed")

    res = git.add(_RUNNER, *paths_to_stage, cwd=str(_REPO_ROOT))
    if res.returncode != 0:
        _git_checkout_branch(original_branch)
        raise ShipError(f"git add failed: {res.stderr.strip()}")
    res = git.commit(_RUNNER, _commit_subject(args.kind), cwd=str(_REPO_ROOT))
    if res.returncode != 0:
        _git_checkout_branch(original_branch)
        raise ShipError(f"git commit failed: {res.stderr.strip()}")

    res = git.push_set_upstream(_RUNNER, "origin", branch_name, cwd=str(_REPO_ROOT))
    if res.returncode != 0:
        _git_checkout_branch(original_branch)
        raise ShipError(f"git push failed: {res.stderr.strip()}")

    print(f"  Switching back to {original_branch!r} …")
    _git_checkout_branch(original_branch)

    print("\n[pr] Creating PR …")
    pr, created = gh.pr_create(
        _RUNNER,
        repo=repo,
        branch=branch_name,
        title=_commit_subject(args.kind),
        body=_create_pr_body(args, plan),
        base="main",
        draft=False,
    )
    print(f"  PR #{pr.number}: {pr.url} ({'created' if created else 'existing'})")
    return pr


def _verify_harness(
    args: argparse.Namespace,
    verify_run_ids: list[int],
    *,
    repo: str,
    pr_url: str,
    plan: HarnessPlan,
) -> int:
    print("\n[verify:harness] Collecting timing and verifying shard balance …")
    expected_targets = [
        target for targets in plan.new_shards.values() for target in targets
    ]
    try:
        jobs = _collect_wall_clock(_RUNNER, verify_run_ids, repo=repo)
        _validate_job_cohort(jobs, run_ids=verify_run_ids, n_shards=plan.n_shards)
        report = _run_ci_timing(
            _RUNNER,
            "harness",
            repo=repo,
            run_ids=verify_run_ids,
            required_targets=expected_targets,
        )
        if report.sampled_run_ids != verify_run_ids:
            raise ShipError(
                "harness timing report did not retain the requested verification cohort"
            )
        _ = _validate_harness_cohort(
            report,
            expected_shards=plan.new_shards,
            expected_run_count=len(verify_run_ids),
        )
    except ShipError as exc:
        print(
            f"ERROR: complete harness verification evidence is unavailable: {exc}",
            file=sys.stderr,
        )
        print(f"  PR is at {pr_url}", file=sys.stderr)
        return 1

    wall_clock = jobs.shard_medians
    budget_ok = _report_wall_clock_balance(
        wall_clock,
        max_shard_wall_clock=args.max_shard_wall_clock,
        n_verify_runs=len(verify_run_ids),
    )
    observed_slowest, observed_runner_seconds = _job_metrics(jobs.job_rows)
    _print_time_table("PREDICTED (cost model):", plan.predicted_new)
    _print_time_table("OBSERVED (real CI job wall-clock):", wall_clock)
    _print_observed_job_runs(jobs.job_rows)
    print(
        f"  Baseline median slowest: {plan.baseline_slowest_wall_clock:.1f}s\n"
        f"  Observed median slowest: {observed_slowest:.1f}s\n"
        f"  Baseline median runner sum: {plan.baseline_runner_seconds:.1f}s\n"
        f"  Observed median runner sum: {observed_runner_seconds:.1f}s"
    )

    violations: list[str] = []
    if not budget_ok:
        violations.append("measured slowest shard exceeds --max-shard-wall-clock")
    if observed_slowest > plan.approved_slowest_wall_clock:
        violations.append(
            f"measured slowest shard {observed_slowest:.1f}s regresses the approved "
            f"{plan.approved_slowest_wall_clock:.1f}s threshold"
        )
    if observed_runner_seconds > plan.baseline_runner_seconds:
        violations.append(
            f"measured summed harness runner time {observed_runner_seconds:.1f}s exceeds "
            f"the {plan.baseline_runner_seconds:.1f}s baseline"
        )
    if not violations:
        print("✓ Harness wall-clock and runner-cost verification passed")
        return 0
    reason = "; ".join(violations)
    if _permit_experimental_override(args, reason):
        return 0
    print(f"ERROR: harness verification failed: {reason}", file=sys.stderr)
    print(f"  PR is at {pr_url}", file=sys.stderr)
    return 1


def _verify_python(
    args: argparse.Namespace,
    verify_run_ids: list[int],
    *,
    repo: str,
    pr_url: str,
    plan: PythonPlan,
) -> int:
    print(
        "\n[verify:python] Collecting python-tests timing and verifying shard balance …"
    )
    try:
        report = _run_ci_timing(
            _RUNNER,
            "pytest",
            repo=repo,
            run_ids=verify_run_ids,
        )
    except ShipError as exc:
        print(f"ERROR: could not collect python-tests timing: {exc}", file=sys.stderr)
        print(f"  PR is at {pr_url}", file=sys.stderr)
        return 1
    if report.row_count == 0:
        print(
            "ERROR: zero parseable python-tests --durations=0 rows in verification runs.",
            file=sys.stderr,
        )
        print(f"  PR is at {pr_url}", file=sys.stderr)
        return 1

    totals = report.shard_medians
    expected = set(range(1, plan.n_shards + 1))
    missing = sorted(expected - set(totals))
    if missing:
        print(
            f"ERROR: python-tests verification missing shard ids: {missing}",
            file=sys.stderr,
        )
        print(f"  PR is at {pr_url}", file=sys.stderr)
        return 1

    spread = max(totals.values()) - min(totals.values())
    print(
        f"\nPython pytest duration spread: {spread:.1f}s (threshold: {args.balance_threshold}s)"
    )
    print(f"  {'Shard':>6}  {'Total (s)':>10}")
    for shard_n in sorted(totals):
        print(f"  {shard_n:>6}  {totals[shard_n]:>10.1f}")
    if spread > args.balance_threshold:
        print(
            f"ERROR: python-tests spread {spread:.1f}s exceeds {args.balance_threshold:.1f}s.",
            file=sys.stderr,
        )
        print(f"  PR is at {pr_url}", file=sys.stderr)
        return 1
    print("✓ Python shard balance within threshold")
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:  # noqa: C901
    args = _parse_args(argv)
    makefile_path = _REPO_ROOT / "Makefile"
    repo = args.repo or _detect_repo(_RUNNER)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    branch_name = f"{args.branch_prefix}-{timestamp}"
    original_branch = git.try_current_branch(_RUNNER, cwd=str(_REPO_ROOT)) or "main"

    print(f"Repo   : {repo}")
    print(f"Kind   : {args.kind}")
    print(f"Branch : {branch_name}")

    try:
        harness_plan = None
        python_plan = None
        if args.kind in {"harness", "all"}:
            harness_plan = _prepare_harness_plan(args, repo, makefile_path)
        if args.kind in {"python", "all"}:
            python_plan = _prepare_python_plan(args, repo)
        plan = RebalancePlan(harness=harness_plan, python=python_plan)

        artifact_paths = _paths_for_kind(args.kind)
        _assert_artifact_paths_clean(artifact_paths)
        if _plan_is_noop(plan, makefile_path):
            if plan.harness is not None:
                _require_noop_harness_budget(args, plan.harness)
            print("\nNo shard artifact changes needed; exiting before branch creation.")
            return 0

        written_paths = _write_selected_artifacts(plan, makefile_path)
        paths_to_stage = [path for path in _paths_to_stage(args.kind, plan) if path in written_paths]
        if not paths_to_stage:
            print("\nNo shard artifact changes needed after write; exiting before branch creation.")
            return 0

        try:
            pr = _commit_push_and_pr(
                args,
                repo=repo,
                branch_name=branch_name,
                original_branch=original_branch,
                plan=plan,
                paths_to_stage=paths_to_stage,
            )
        except ShipError:
            _git_checkout_branch(original_branch)
            _revert_written_paths(paths_to_stage)
            raise

        print(
            f"\n[verify] Triggering {args.n_verify_runs} verification CI runs via workflow_dispatch …"
        )
        try:
            verify_run_ids = _trigger_verification_runs(
                _RUNNER,
                repo=repo,
                branch=branch_name,
                workflow=args.workflow,
                n_verify_runs=args.n_verify_runs,
            )
        except (TimeoutError, RuntimeError) as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            print(f"  PR is at {pr.url} — investigate CI failure before retrying.", file=sys.stderr)
            return 1

        if plan.harness is not None:
            result = _verify_harness(
                args,
                verify_run_ids,
                repo=repo,
                pr_url=pr.url,
                plan=plan.harness,
            )
            if result != 0:
                return result
        if plan.python is not None:
            result = _verify_python(
                args,
                verify_run_ids,
                repo=repo,
                pr_url=pr.url,
                plan=plan.python,
            )
            if result != 0:
                return result

        print(f"\nPR #{pr.number} is ready for review: {pr.url}")
        print("Merge is commented out. Verify the PR and merge manually when satisfied.")
        return 0
    except ShipError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
