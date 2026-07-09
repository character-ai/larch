from __future__ import annotations

from pathlib import Path
from collections.abc import Sequence

import pytest

from larch.core.proc import CommandResult
from larch.errors import ShipError
from larch.implement import scope_disposition


class FakeRunner:
    def __init__(self, *, diff_paths: Sequence[str], status_z: str = "") -> None:
        self.diff_paths = tuple(diff_paths)
        self.status_z = status_z

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: object = None,
        check: bool = False,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> CommandResult:
        _ = timeout, cwd, env, check, stdout, stderr
        args = tuple(argv)
        if args[:3] == ("git", "diff", "--name-only"):
            return CommandResult(
                args, 0, "".join(f"{path}\n" for path in self.diff_paths), "", 0.0
            )
        if args[:3] == ("git", "status", "--porcelain=v1"):
            return CommandResult(args, 0, self.status_z, "", 0.0)
        if args[:3] == ("git", "merge-base", "HEAD"):
            return CommandResult(args, 1, "", "no origin", 0.0)
        if args[:3] == ("git", "rev-parse", "HEAD"):
            return CommandResult(args, 0, "HEADSHA\n", "", 0.0)
        return CommandResult(args, 1, "", "unexpected", 0.0)


def _plan(paths: Sequence[str], *, may_update: Sequence[str] = ()) -> str:
    lines = ["## Files to modify/create"]
    for path in paths:
        lines.append(f"### UPDATED: {path}")
    for path in may_update:
        lines.append(f"### MAY_UPDATE: {path}")
    return "\n".join(lines) + "\n"


def test_compute_high_band_requires_disposition_and_forces_plan_fidelity(
    tmp_path: Path,
) -> None:
    paths = [f"pkg/file_{idx}.py" for idx in range(85)]
    touched = paths[:24]
    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(_plan(paths), encoding="utf-8")
    _ = (tmp_path / "step2-baseline.txt").write_text("BASE\n", encoding="utf-8")

    coverage = scope_disposition.compute_and_write_coverage(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        plan_file=plan_file,
        runner=FakeRunner(diff_paths=touched),
    )

    assert coverage.total == 85
    assert coverage.untouched == 61
    assert coverage.band == "high"
    assert coverage.disposition_required is True
    assert coverage.plan_fidelity_forced is True
    env = (tmp_path / "plan-coverage.env").read_text(encoding="utf-8")
    assert "PLAN_COVERAGE_DISPOSITION_REQUIRED=true" in env
    assert "PLAN_FIDELITY_FORCED=true" in env


def test_compute_excludes_may_update_and_todos_require_disposition(
    tmp_path: Path,
) -> None:
    paths = ["src/a.py", "src/b.py"]
    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(_plan(paths, may_update=["optional.py"]), encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text('{"todos_left":["finish docs"]}\n', encoding="utf-8")
    _ = (tmp_path / "step2-baseline.txt").write_text("BASE\n", encoding="utf-8")

    coverage = scope_disposition.compute_and_write_coverage(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        plan_file=plan_file,
        manifest_path=manifest,
        runner=FakeRunner(diff_paths=paths),
    )

    assert coverage.total == 2
    assert coverage.untouched == 0
    assert "optional.py" not in coverage.plan_paths
    assert coverage.todos_left_count == 1
    assert coverage.disposition_required is True


def test_compute_requires_step2_baseline(tmp_path: Path) -> None:
    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(_plan(["src/a.py"]), encoding="utf-8")

    with pytest.raises(ShipError, match="step2 baseline missing or unreadable"):
        _ = scope_disposition.compute_and_write_coverage(
            tmpdir=tmp_path,
            repo_root=tmp_path,
            plan_file=plan_file,
            runner=FakeRunner(diff_paths=[]),
        )


def test_record_proceed_partial_is_durable_after_all_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    coverage = scope_disposition.PlanCoverage(
        total=2,
        touched=1,
        untouched=1,
        untouched_percent=50,
        band="high",
        plan_paths=("a.py", "b.py"),
        touched_paths=("a.py",),
        untouched_paths=("b.py",),
        todos_left_count=0,
        todos_left=(),
        fingerprint="fp1",
        disposition_required=True,
        plan_fidelity_forced=True,
        coverage_file=str(tmp_path / "plan-coverage.json"),
        untouched_file=str(tmp_path / "untouched.txt"),
        todos_file=str(tmp_path / "todos.txt"),
    )
    scope_disposition.write_coverage(coverage, tmpdir=tmp_path)
    calls: list[tuple[str, ...]] = []

    def fake_run_cli(argv: Sequence[str]) -> CommandResult:
        args = tuple(argv)
        calls.append(args)
        if args[:2] == ("issue", "create-one"):
            return CommandResult(
                args,
                0,
                "ISSUE_NUMBER=77\nISSUE_URL=https://example.test/issues/77\n",
                "",
                0.0,
            )
        if args[:2] == ("tracking-issue", "append-comment"):
            return CommandResult(
                args,
                0,
                "COMMENT_ID=1\nCOMMENT_URL=https://example.test/comment\n",
                "",
                0.0,
            )
        if args[:2] == ("issue", "add-blocked-by"):
            return CommandResult(args, 0, "BLOCKED_BY_ADDED=true\n", "", 0.0)
        if args[:2] == ("run-log", "write"):
            return CommandResult(args, 0, "LOG_WRITTEN=true\n", "", 0.0)
        return CommandResult(args, 1, "", "unexpected", 0.0)

    monkeypatch.setattr(scope_disposition, "_run_cli", fake_run_cli)

    record = scope_disposition.record_disposition(
        tmpdir=tmp_path,
        disposition="proceed-partial",
        repo="owner/repo",
        tracking_issue_number="12",
        run_id="run-xyz",
    )

    assert record.followup_issue_number == "77"
    assert scope_disposition.disposition_path(tmp_path).is_file()
    blocked = [call for call in calls if call[:2] == ("issue", "add-blocked-by")]
    assert blocked
    assert blocked[0][blocked[0].index("--client-issue") + 1] == "12"
    assert blocked[0][blocked[0].index("--blocker-issue") + 1] == "77"
    assert calls[-1][:2] == ("run-log", "write")


def test_record_proceed_partial_failure_leaves_no_disposition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    coverage = scope_disposition.PlanCoverage(
        total=1,
        touched=0,
        untouched=1,
        untouched_percent=100,
        band="high",
        plan_paths=("a.py",),
        touched_paths=(),
        untouched_paths=("a.py",),
        todos_left_count=0,
        todos_left=(),
        fingerprint="fp1",
        disposition_required=True,
        plan_fidelity_forced=True,
        coverage_file=str(tmp_path / "plan-coverage.json"),
        untouched_file=str(tmp_path / "untouched.txt"),
        todos_file=str(tmp_path / "todos.txt"),
    )
    scope_disposition.write_coverage(coverage, tmpdir=tmp_path)

    def fake_run_cli(argv: Sequence[str]) -> CommandResult:
        args = tuple(argv)
        if args[:2] == ("issue", "create-one"):
            return CommandResult(
                args,
                0,
                "ISSUE_NUMBER=77\nISSUE_URL=https://example.test/issues/77\n",
                "",
                0.0,
            )
        if args[:2] == ("tracking-issue", "append-comment"):
            return CommandResult(args, 1, "FAILED=true\nERROR=nope\n", "", 0.0)
        return CommandResult(args, 0, "OK=true\n", "", 0.0)

    monkeypatch.setattr(scope_disposition, "_run_cli", fake_run_cli)

    with pytest.raises(ShipError):
        _ = scope_disposition.record_disposition(
            tmpdir=tmp_path,
            disposition="proceed-partial",
            repo="owner/repo",
            tracking_issue_number="12",
            run_id="run-xyz",
        )

    assert not scope_disposition.disposition_path(tmp_path).exists()


def test_validate_detects_stale_fingerprint(tmp_path: Path) -> None:
    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(
        _plan(["src/a.py", "src/b.py", "src/c.py"]), encoding="utf-8"
    )
    _ = (tmp_path / "step2-baseline.txt").write_text("BASE\n", encoding="utf-8")
    coverage = scope_disposition.compute_and_write_coverage(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        plan_file=plan_file,
        runner=FakeRunner(diff_paths=[]),
    )
    _ = scope_disposition.record_disposition(
        tmpdir=tmp_path, disposition="bail-rescope", coverage=coverage
    )

    result = scope_disposition.validate_disposition_for_ship(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        runner=FakeRunner(diff_paths=["src/a.py"]),
    )

    assert result.ok is False
    assert result.required is True
    assert result.reason == "scope-disposition-stale"


def test_validate_rejects_stale_partial_record_when_coverage_becomes_complete(
    tmp_path: Path,
) -> None:
    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(_plan(["src/a.py"]), encoding="utf-8")
    _ = (tmp_path / "step2-baseline.txt").write_text("BASE\n", encoding="utf-8")
    _ = (tmp_path / "scope-disposition.json").write_text(
        '{"disposition":"proceed-partial","fingerprint":"old","followup_issue_number":"77"}\n',
        encoding="utf-8",
    )

    result = scope_disposition.validate_disposition_for_ship(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        runner=FakeRunner(diff_paths=["src/a.py"]),
    )

    assert result.ok is False
    assert result.required is True
    assert result.reason == "scope-disposition-stale"
    assert scope_disposition.disposition_path(tmp_path).exists()
    assert scope_disposition.disposition_link_kind(tmp_path) == "part-of"


def _coverage_fixture(
    tmp_path: Path, *, required: bool
) -> scope_disposition.PlanCoverage:
    return scope_disposition.PlanCoverage(
        total=1,
        touched=1,
        untouched=0,
        untouched_percent=0,
        band="advisory",
        plan_paths=("a.py",),
        touched_paths=("a.py",),
        untouched_paths=(),
        todos_left_count=0,
        todos_left=(),
        fingerprint="fp-current",
        disposition_required=required,
        plan_fidelity_forced=False,
        coverage_file=str(tmp_path / "plan-coverage.json"),
        untouched_file=str(tmp_path / "untouched.txt"),
        todos_file=str(tmp_path / "todos.txt"),
    )


def test_pr_mutation_scope_gate_no_tmpdir_noops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("IMPLEMENT_TMPDIR", raising=False)
    scope_disposition.require_pr_mutation_scope_disposition(
        tmpdir=None,
        repo_root=tmp_path,
        runner=FakeRunner(diff_paths=[]),
    )


def test_pr_mutation_scope_gate_empty_tmpdir_noops(tmp_path: Path) -> None:
    assert scope_disposition.is_pr_mutation_gate_relevant(tmpdir=tmp_path) is False
    scope_disposition.require_pr_mutation_scope_disposition(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        runner=FakeRunner(diff_paths=[]),
    )


def test_manifest_alone_makes_pr_mutation_gate_relevant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text('{"todos_left": []}\n', encoding="utf-8")
    calls: list[Path | None] = []

    def fake_require(
        *,
        tmpdir: Path,
        repo_root: Path,
        manifest_path: Path | None = None,
        runner: object = None,
    ) -> None:
        _ = tmpdir, repo_root, runner
        calls.append(manifest_path)

    monkeypatch.setattr(
        scope_disposition, "require_valid_disposition_for_ship", fake_require
    )

    assert scope_disposition.resolve_implement_manifest(tmp_path) == manifest
    assert scope_disposition.is_pr_mutation_gate_relevant(tmpdir=tmp_path) is True
    scope_disposition.require_pr_mutation_scope_disposition(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        runner=FakeRunner(diff_paths=[]),
    )
    assert calls == [manifest]


def test_validate_manifest_todos_require_disposition_without_persisted_coverage(
    tmp_path: Path,
) -> None:
    _ = (tmp_path / "plan.txt").write_text(_plan(["a.py"]), encoding="utf-8")
    _ = (tmp_path / "step2-baseline.txt").write_text("BASE\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text(
        '{"todos_left": ["finish the deferred item"]}\n', encoding="utf-8"
    )

    result = scope_disposition.validate_disposition_for_ship(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        manifest_path=manifest,
        runner=FakeRunner(diff_paths=["a.py"]),
    )

    assert result.ok is False
    assert result.required is True
    assert result.reason == "scope-disposition-missing"
    assert result.coverage is not None
    assert result.coverage.todos_left_count == 1


def test_pr_mutation_gate_required_coverage_missing_plan_raises(tmp_path: Path) -> None:
    scope_disposition.write_coverage(
        _coverage_fixture(tmp_path, required=True), tmpdir=tmp_path
    )

    with pytest.raises(scope_disposition.NeedsUserInput):
        scope_disposition.require_pr_mutation_scope_disposition(
            tmpdir=tmp_path,
            repo_root=tmp_path,
            runner=FakeRunner(diff_paths=[]),
        )


def test_validate_stale_disposition_missing_plan_fails_closed(tmp_path: Path) -> None:
    scope_disposition.write_coverage(
        _coverage_fixture(tmp_path, required=False), tmpdir=tmp_path
    )
    _ = (tmp_path / "scope-disposition.json").write_text(
        '{"disposition":"proceed-partial","fingerprint":"old"}\n',
        encoding="utf-8",
    )

    result = scope_disposition.validate_disposition_for_ship(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        runner=FakeRunner(diff_paths=[]),
    )

    assert result.ok is False
    assert result.required is True
    assert result.reason.startswith("coverage-recompute-failed")


def test_validate_nonrequired_coverage_with_disposition_recompute_failure_fails_closed(
    tmp_path: Path,
) -> None:
    scope_disposition.write_coverage(
        _coverage_fixture(tmp_path, required=False), tmpdir=tmp_path
    )
    _ = (tmp_path / "scope-disposition.json").write_text(
        '{"disposition":"bail-rescope","fingerprint":"fp-current"}\n',
        encoding="utf-8",
    )

    result = scope_disposition.validate_disposition_for_ship(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        runner=FakeRunner(diff_paths=[]),
    )

    assert result.ok is False
    assert result.required is True
    assert result.reason.startswith("coverage-recompute-failed")


def test_validate_gate_relevant_coverage_recompute_failure_fails_closed(
    tmp_path: Path,
) -> None:
    scope_disposition.write_coverage(
        _coverage_fixture(tmp_path, required=False), tmpdir=tmp_path
    )

    result = scope_disposition.validate_disposition_for_ship(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        runner=FakeRunner(diff_paths=[]),
    )

    assert result.ok is False
    assert result.required is True
    assert result.reason.startswith("coverage-recompute-failed")


def test_validate_non_gate_recompute_failure_keeps_nonrequired_coverage_advisory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coverage = _coverage_fixture(tmp_path, required=False)

    def fake_load(_tmpdir: Path) -> scope_disposition.PlanCoverage:
        return coverage

    monkeypatch.setattr(scope_disposition, "load_coverage", fake_load)
    monkeypatch.setattr(
        scope_disposition, "is_pr_mutation_gate_relevant", lambda **_kwargs: False
    )

    result = scope_disposition.validate_disposition_for_ship(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        runner=FakeRunner(diff_paths=[]),
    )

    assert result.ok is True
    assert result.required is False
    assert result.reason.startswith("coverage-recompute-failed-advisory")
