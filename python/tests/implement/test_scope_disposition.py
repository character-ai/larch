from __future__ import annotations

import json
from pathlib import Path
from collections.abc import Mapping, Sequence

import pytest

from larch.core import config
from larch.core.proc import CommandResult
from larch.errors import ShipError
from larch.implement import scope_disposition


class FakeRunner:
    """Test double with independent symbolic-ref and merge-base controls.

    Defaults model a successful live base: ``origin/main`` symbolic-ref and a
    non-empty merge-base SHA. Explicit failure flags are required for
    symbolic-ref or merge-base failure paths.
    """

    def __init__(
        self,
        *,
        diff_paths: Sequence[str] = (),
        status_z: str = "",
        merge_base: str = "LIVEBASE",
        head: str = "a" * 40,
        remote_heads: Mapping[str, str] | None = None,
        fail_symbolic_refs: frozenset[str] | None = None,
        fail_merge_base: bool = False,
        fail_diff: bool = False,
    ) -> None:
        self.diff_paths = tuple(diff_paths)
        self.status_z = status_z
        self.merge_base = merge_base
        self.head = head
        self.remote_heads = dict(remote_heads or {})
        self.fail_symbolic_refs = fail_symbolic_refs or frozenset()
        self.fail_merge_base = fail_merge_base
        self.fail_diff = fail_diff
        self.calls: list[tuple[str, ...]] = []

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
        self.calls.append(args)
        if args[:3] == ("git", "symbolic-ref", "--short") and len(args) >= 4:
            ref = args[3]
            remote = ""
            if ref.startswith("refs/remotes/") and ref.endswith("/HEAD"):
                remote = ref[len("refs/remotes/") : -len("/HEAD")]
            if remote in self.fail_symbolic_refs:
                return CommandResult(args, 1, "", f"missing {ref}", 0.0)
            if remote in self.remote_heads:
                value = self.remote_heads[remote]
                if not value:
                    return CommandResult(args, 1, "", f"missing {ref}", 0.0)
                return CommandResult(args, 0, f"{value}\n", "", 0.0)
            if remote == "origin":
                return CommandResult(args, 0, "origin/main\n", "", 0.0)
            if remote == "upstream":
                return CommandResult(args, 0, "upstream/main\n", "", 0.0)
            return CommandResult(args, 1, "", f"missing {ref}", 0.0)
        if args[:3] == ("git", "diff", "--name-only"):
            if self.fail_diff:
                return CommandResult(args, 1, "", "invalid revision range", 0.0)
            return CommandResult(
                args, 0, "".join(f"{path}\n" for path in self.diff_paths), "", 0.0
            )
        if args[:3] == ("git", "status", "--porcelain=v1"):
            return CommandResult(args, 0, self.status_z, "", 0.0)
        if args[:2] == ("git", "merge-base"):
            if self.fail_merge_base or not self.merge_base:
                return CommandResult(args, 1, "", "no merge-base", 0.0)
            return CommandResult(args, 0, f"{self.merge_base}\n", "", 0.0)
        if args[:3] == ("git", "rev-parse", "HEAD"):
            return CommandResult(args, 0, f"{self.head}\n", "", 0.0)
        return CommandResult(args, 1, "", "unexpected", 0.0)


def _plan(paths: Sequence[str], *, may_update: Sequence[str] = ()) -> str:
    lines = ["## Files to modify/create"]
    for path in paths:
        lines.append(f"### UPDATED: {path}")
    for path in may_update:
        lines.append(f"### MAY_UPDATE: {path}")
    return "\n".join(lines) + "\n"


def _porcelain_z(records: Sequence[str]) -> str:
    """Build porcelain -z stdout from status records.

    Each record is either ``"XY path"`` or, for rename/copy, provide the old
    path as the next record without a status prefix (matching git -z layout
    when callers pass ``["R  new.py", "old.py"]``).
    """
    return "\0".join(records) + "\0"


def _write_state(path: Path, **keys: str) -> None:
    _ = path.write_text(
        "".join(f"{key}={value}\n" for key, value in keys.items()),
        encoding="utf-8",
    )


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


@pytest.mark.parametrize(
    "todo",
    [
        "make py-lint and make py-test (full suites) were not completed; focused tests passed",
        "make py-lint / make py-test (full suites) were not completed; focused tests passed",
    ],
)
def test_compute_ignores_nonblocking_full_suite_validation_todo(
    tmp_path: Path, todo: str
) -> None:
    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(_plan(["src/a.py"]), encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text(f'{{"todos_left":["{todo}"]}}\n', encoding="utf-8")
    _ = (tmp_path / "step2-baseline.txt").write_text("BASE\n", encoding="utf-8")

    coverage = scope_disposition.compute_and_write_coverage(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        plan_file=plan_file,
        manifest_path=manifest,
        runner=FakeRunner(diff_paths=["src/a.py"]),
    )

    assert coverage.todos_left_count == 0
    assert not coverage.todos_left
    assert coverage.disposition_required is False


def test_compute_blocks_mutated_full_suite_validation_todo(
    tmp_path: Path,
) -> None:
    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(_plan(["src/a.py"]), encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text(
        '{"todos_left":["make py-lint and make py-test (full suites) were not completed; remaining cleanup is needed"]}\n',
        encoding="utf-8",
    )
    _ = (tmp_path / "step2-baseline.txt").write_text("BASE\n", encoding="utf-8")

    coverage = scope_disposition.compute_and_write_coverage(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        plan_file=plan_file,
        manifest_path=manifest,
        runner=FakeRunner(diff_paths=["src/a.py"]),
    )

    assert coverage.todos_left_count == 1
    assert coverage.todos_left == (
        "make py-lint and make py-test (full suites) were not completed; remaining cleanup is needed",
    )
    assert coverage.disposition_required is True


@pytest.mark.parametrize(
    "todo",
    [
        "full make py-test suite failed and was not completed",
        "full make py-test suite was not completed because a test is unimplemented",
    ],
)
def test_compute_keeps_actionable_validation_todos_blocking(
    tmp_path: Path, todo: str
) -> None:
    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(_plan(["src/a.py"]), encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text(f'{{"todos_left":["{todo}"]}}\n', encoding="utf-8")
    _ = (tmp_path / "step2-baseline.txt").write_text("BASE\n", encoding="utf-8")

    coverage = scope_disposition.compute_and_write_coverage(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        plan_file=plan_file,
        manifest_path=manifest,
        runner=FakeRunner(diff_paths=["src/a.py"]),
    )

    assert coverage.todos_left_count == 1
    assert coverage.todos_left == (todo,)
    assert coverage.disposition_required is True


def test_manifest_todo_non_string_after_ignored_todo_fails_closed(
    tmp_path: Path,
) -> None:
    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(_plan(["src/a.py"]), encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text(
        '{"todos_left":["make py-lint and make py-test (full suites) were not completed",1]}\n',
        encoding="utf-8",
    )
    _ = (tmp_path / "step2-baseline.txt").write_text("BASE\n", encoding="utf-8")

    with pytest.raises(ShipError, match="schema-invalid"):
        _ = scope_disposition.compute_and_write_coverage(
            tmpdir=tmp_path,
            repo_root=tmp_path,
            plan_file=plan_file,
            manifest_path=manifest,
            runner=FakeRunner(diff_paths=["src/a.py"]),
        )


def test_compute_requires_step2_baseline_on_frozen_fallback(tmp_path: Path) -> None:
    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(_plan(["src/a.py"]), encoding="utf-8")

    with pytest.raises(ShipError, match="step2 baseline missing or unreadable"):
        _ = scope_disposition.compute_and_write_coverage(
            tmpdir=tmp_path,
            repo_root=tmp_path,
            plan_file=plan_file,
            runner=FakeRunner(diff_paths=[], fail_symbolic_refs=frozenset({"origin"})),
        )


def test_live_base_computes_without_step2_baseline(tmp_path: Path) -> None:
    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(_plan(["src/a.py"]), encoding="utf-8")

    coverage = scope_disposition.compute_and_write_coverage(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        plan_file=plan_file,
        runner=FakeRunner(diff_paths=["src/a.py"]),
    )

    assert coverage.touched_paths == ("src/a.py",)
    assert not (tmp_path / "step2-baseline.txt").exists()


def test_compute_coverage_ignores_non_plan_and_run_log_paths(tmp_path: Path) -> None:
    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(_plan(["src/a.py", "src/b.py"]), encoding="utf-8")
    _ = (tmp_path / "step2-baseline.txt").write_text("BASE\n", encoding="utf-8")
    noisy = [
        "src/a.py",
        "src/b.py",
        "larch-logs/run-9A845BA3/implement/scope-disposition.json",
        "python/larch/implement/origin_main_evolution.py",
        "docs/changelog-upstream.md",
    ]
    coverage = scope_disposition.compute_and_write_coverage(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        plan_file=plan_file,
        runner=FakeRunner(diff_paths=noisy),
    )

    assert coverage.touched_paths == ("src/a.py", "src/b.py")
    assert coverage.total == 2
    assert coverage.untouched == 0
    clean = scope_disposition.compute_coverage(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        plan_file=plan_file,
        runner=FakeRunner(diff_paths=["src/a.py", "src/b.py"]),
    )
    assert clean.fingerprint == coverage.fingerprint


def test_baseline_uses_resolved_origin_trunk_merge_base(tmp_path: Path) -> None:
    _ = (tmp_path / "step2-baseline.txt").write_text("STEP2BASE\n", encoding="utf-8")
    runner = FakeRunner(
        diff_paths=["src/a.py"],
        merge_base="FRESHMB",
        remote_heads={"origin": "origin/trunk"},
    )

    _ = scope_disposition.touched_paths_since_baseline(
        tmpdir=tmp_path, repo_root=tmp_path, runner=runner
    )

    symbolic_calls = [
        call for call in runner.calls if call[:3] == ("git", "symbolic-ref", "--short")
    ]
    assert symbolic_calls
    assert symbolic_calls[0][3] == "refs/remotes/origin/HEAD"
    merge_base_calls = [
        call for call in runner.calls if call[:2] == ("git", "merge-base")
    ]
    assert merge_base_calls
    assert merge_base_calls[0][2:] == ("origin/trunk", "HEAD")
    diff_calls = [
        call for call in runner.calls if call[:3] == ("git", "diff", "--name-only")
    ]
    assert diff_calls
    assert diff_calls[0][3] == "FRESHMB..HEAD"


def test_forked_target_selects_upstream_default_branch(tmp_path: Path) -> None:
    _write_state(tmp_path / "session-env.sh", FORKED_TARGET="true")
    runner = FakeRunner(
        diff_paths=["src/a.py"],
        merge_base="UPMB",
        remote_heads={"upstream": "upstream/develop", "origin": "origin/main"},
    )

    _ = scope_disposition.touched_paths_since_baseline(
        tmpdir=tmp_path, repo_root=tmp_path, runner=runner
    )

    symbolic_calls = [
        call for call in runner.calls if call[:3] == ("git", "symbolic-ref", "--short")
    ]
    assert symbolic_calls[0][3] == "refs/remotes/upstream/HEAD"
    merge_base_calls = [
        call for call in runner.calls if call[:2] == ("git", "merge-base")
    ]
    assert merge_base_calls[0][2] == "upstream/develop"
    assert not any(
        call[3] == "refs/remotes/origin/HEAD"
        for call in runner.calls
        if call[:3] == ("git", "symbolic-ref", "--short")
    )


@pytest.mark.parametrize(
    ("ship", "session", "expected_remote"),
    [
        (None, {"FORKED_TARGET": "true"}, "upstream"),
        ({"FORKED_TARGET": "true"}, None, "upstream"),
        ({"FORKED_TARGET": "false"}, {"FORKED_TARGET": "true"}, "origin"),
        ({"FORKED_TARGET": "true"}, {"FORKED_TARGET": "false"}, "upstream"),
        ({"FORKED_TARGET": "yes"}, None, "origin"),
        ({}, {"FORKED_TARGET": "true"}, "origin"),
        (None, None, "origin"),
    ],
)
def test_forked_target_state_precedence(
    tmp_path: Path,
    ship: dict[str, str] | None,
    session: dict[str, str] | None,
    expected_remote: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FORKED_TARGET", "true")
    if ship is not None:
        _write_state(tmp_path / "ship-pr-state.sh", **ship)
    if session is not None:
        _write_state(tmp_path / "session-env.sh", **session)
    runner = FakeRunner(diff_paths=[], merge_base="MB")

    resolution = scope_disposition.resolve_baseline(
        tmpdir=tmp_path, repo_root=tmp_path, runner=runner
    )

    assert resolution.remote == expected_remote
    symbolic_calls = [
        call for call in runner.calls if call[:3] == ("git", "symbolic-ref", "--short")
    ]
    assert symbolic_calls[0][3] == f"refs/remotes/{expected_remote}/HEAD"


def test_normal_run_ignores_unrelated_upstream_head(tmp_path: Path) -> None:
    runner = FakeRunner(
        diff_paths=[],
        merge_base="MB",
        remote_heads={"origin": "origin/main", "upstream": "upstream/other"},
    )
    resolution = scope_disposition.resolve_baseline(
        tmpdir=tmp_path, repo_root=tmp_path, runner=runner
    )
    assert resolution.remote == "origin"
    assert not any(
        "upstream" in call[3]
        for call in runner.calls
        if len(call) > 3 and call[1] == "symbolic-ref"
    )


@pytest.mark.parametrize(
    "remote_head",
    [
        "",
        "upstream/main",
        "-origin/main",
        "origin/",
        "origin",
        "other/main",
        "origin/main^",
        "origin/main:path",
        "origin/main@{1}",
    ],
)
def test_malformed_symbolic_ref_uses_frozen_fallback(
    tmp_path: Path, remote_head: str, capsys: pytest.CaptureFixture[str]
) -> None:
    _ = (tmp_path / "step2-baseline.txt").write_text("STEP2BASE\n", encoding="utf-8")
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    plan = tmp_path / "src"
    plan.mkdir()
    target = plan / "a.py"
    _ = target.write_text("edited\n", encoding="utf-8")
    runner = FakeRunner(
        diff_paths=["src/a.py", "src/upstream_only.py"],
        status_z=_porcelain_z([" M src/a.py"]),
        remote_heads={"origin": remote_head},
        fail_diff=True,
    )

    touched = scope_disposition.touched_paths_since_baseline(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        runner=runner,
        plan_paths=["src/a.py", "src/upstream_only.py"],
    )

    assert touched == ("src/a.py",)
    assert not any(call[:2] == ("git", "merge-base") for call in runner.calls)
    assert not any(call[:3] == ("git", "diff", "--name-only") for call in runner.calls)
    err = capsys.readouterr().err
    assert "unresolved origin/HEAD" in err
    assert "STEP2BASE" in err


def test_merge_base_failure_raises_not_frozen_fallback(tmp_path: Path) -> None:
    _ = (tmp_path / "step2-baseline.txt").write_text("STEP2BASE\n", encoding="utf-8")
    runner = FakeRunner(
        diff_paths=["src/a.py"],
        remote_heads={"origin": "origin/main"},
        fail_merge_base=True,
    )

    with pytest.raises(ShipError, match="merge-base failed for origin/main"):
        _ = scope_disposition.touched_paths_since_baseline(
            tmpdir=tmp_path, repo_root=tmp_path, runner=runner
        )

    assert not any(call[:3] == ("git", "diff", "--name-only") for call in runner.calls)


def test_frozen_fallback_skips_baseline_diff_and_uses_porcelain(
    tmp_path: Path,
) -> None:
    _ = (tmp_path / "step2-baseline.txt").write_text("STEP2BASE\n", encoding="utf-8")
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    _ = (src / "a.py").write_text("mod\n", encoding="utf-8")
    _ = (src / "new.py").write_text("new\n", encoding="utf-8")
    _ = (src / "renamed.py").write_text("renamed\n", encoding="utf-8")
    runner = FakeRunner(
        diff_paths=["src/churn.py"],
        status_z=_porcelain_z(
            [
                " M src/a.py",
                "?? src/new.py",
                "R  src/renamed.py",
                "src/old.py",
                "C  src/copied.py",
                "src/template.py",
            ]
        ),
        fail_symbolic_refs=frozenset({"origin"}),
        fail_diff=True,
    )
    # Create remaining paths referenced by rename/copy for signatures.
    _ = (src / "copied.py").write_text("copied\n", encoding="utf-8")

    touched = scope_disposition.touched_paths_since_baseline(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        runner=runner,
        plan_paths=[
            "src/a.py",
            "src/new.py",
            "src/renamed.py",
            "src/old.py",
            "src/copied.py",
            "src/template.py",
            "src/churn.py",
        ],
    )

    assert "src/churn.py" not in touched
    assert "src/a.py" in touched
    assert "src/new.py" in touched
    assert "src/renamed.py" in touched
    assert "src/old.py" in touched
    assert "src/copied.py" in touched
    assert "src/template.py" in touched
    assert not any(call[:3] == ("git", "diff", "--name-only") for call in runner.calls)


def test_frozen_fallback_ignores_committed_upstream_churn(tmp_path: Path) -> None:
    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(_plan(["src/a.py", "src/churn.py"]), encoding="utf-8")
    _ = (tmp_path / "step2-baseline.txt").write_text("STEP2BASE\n", encoding="utf-8")
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    _ = (src / "a.py").write_text("local\n", encoding="utf-8")

    coverage = scope_disposition.compute_and_write_coverage(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        plan_file=plan_file,
        runner=FakeRunner(
            diff_paths=["src/churn.py", "src/a.py"],
            status_z=_porcelain_z([" M src/a.py"]),
            fail_symbolic_refs=frozenset({"origin"}),
        ),
    )

    assert coverage.touched_paths == ("src/a.py",)
    assert "src/churn.py" in coverage.untouched_paths


def test_frozen_fallback_invalid_range_still_returns_porcelain(
    tmp_path: Path,
) -> None:
    _ = (tmp_path / "step2-baseline.txt").write_text("STEP2BASE\n", encoding="utf-8")
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    _ = (src / "a.py").write_text("local\n", encoding="utf-8")
    runner = FakeRunner(
        diff_paths=[],
        status_z=_porcelain_z([" M src/a.py"]),
        fail_symbolic_refs=frozenset({"origin"}),
        fail_diff=True,
    )

    touched = scope_disposition.touched_paths_since_baseline(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        runner=runner,
        plan_paths=["src/a.py"],
    )

    assert touched == ("src/a.py",)


def test_frozen_fallback_ignores_external_commit_before_run_provenance(
    tmp_path: Path,
) -> None:
    _ = (tmp_path / "step2-baseline.txt").write_text("STEP2BASE\n", encoding="utf-8")
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    runner = FakeRunner(
        diff_paths=["src/a.py"],
        status_z="",
        head="b" * 40,
        fail_symbolic_refs=frozenset({"origin"}),
    )

    touched = scope_disposition.touched_paths_since_baseline(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        runner=runner,
        plan_paths=["src/a.py"],
    )

    assert not touched


def test_frozen_fallback_post_commit_provenance_retained(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(_plan(["src/a.py", "src/b.py"]), encoding="utf-8")
    _ = (tmp_path / "step2-baseline.txt").write_text("STEP2BASE\n", encoding="utf-8")
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    _ = (src / "a.py").write_text("implemented\n", encoding="utf-8")
    runner = FakeRunner(
        diff_paths=["src/churn.py"],
        status_z=_porcelain_z([" M src/a.py"]),
        fail_symbolic_refs=frozenset({"origin"}),
    )
    coverage = scope_disposition.compute_and_write_coverage(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        plan_file=plan_file,
        runner=runner,
    )
    assert coverage.touched_paths == ("src/a.py",)

    # Simulate dispatcher commit: clean porcelain, content unchanged.
    runner.status_z = ""
    runner.head = "b" * 40
    runner.diff_paths = ("src/a.py",)

    def fake_run_cli(argv: Sequence[str]) -> CommandResult:
        return CommandResult(tuple(argv), 0, "OK=true\n", "", 0.0)

    monkeypatch.setattr(scope_disposition, "_run_cli", fake_run_cli)
    # `run-log write` is Rust-owned and routes through the bootstrap runner.
    monkeypatch.setattr(scope_disposition, "_run_larch", fake_run_cli, raising=False)
    record = scope_disposition.record_disposition(
        tmpdir=tmp_path,
        disposition="bail-rescope",
        repo_root=tmp_path,
        runner=runner,
    )
    assert record.fingerprint == coverage.fingerprint
    live = scope_disposition.compute_coverage(
        tmpdir=tmp_path, repo_root=tmp_path, plan_file=plan_file, runner=runner
    )
    assert live.touched_paths == ("src/a.py",)
    assert live.fingerprint == coverage.fingerprint


def test_frozen_fallback_ignores_preexisting_provenance(tmp_path: Path) -> None:
    _ = (tmp_path / "step2-baseline.txt").write_text("STEP2BASE\n", encoding="utf-8")
    _ = (tmp_path / "session-id").write_text("run-2\n", encoding="utf-8")
    _ = (tmp_path / scope_disposition.FALLBACK_PROVENANCE).write_text(
        '{"schema_version":"2","session_id":"run-1","anchor_head":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}\n',
        encoding="utf-8",
    )
    src = tmp_path / "src"
    src.mkdir()
    _ = (src / "a.py").write_text("pre-existing\n", encoding="utf-8")

    touched = scope_disposition.touched_paths_since_baseline(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        runner=FakeRunner(status_z="", fail_symbolic_refs=frozenset({"origin"})),
        plan_paths=["src/a.py"],
    )

    assert not touched


def test_frozen_fallback_stale_provenance_pruned_after_revert(
    tmp_path: Path,
) -> None:
    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(_plan(["src/a.py"]), encoding="utf-8")
    _ = (tmp_path / "step2-baseline.txt").write_text("STEP2BASE\n", encoding="utf-8")
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    target = src / "a.py"
    _ = target.write_text("edited\n", encoding="utf-8")
    runner = FakeRunner(
        status_z=_porcelain_z([" M src/a.py"]),
        fail_symbolic_refs=frozenset({"origin"}),
    )
    first = scope_disposition.compute_and_write_coverage(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        plan_file=plan_file,
        runner=runner,
    )
    assert first.touched_paths == ("src/a.py",)

    # Commit the observed change, then revert it in a second commit.
    runner.status_z = ""
    runner.head = "b" * 40
    runner.diff_paths = ("src/a.py",)
    committed = scope_disposition.compute_coverage(
        tmpdir=tmp_path, repo_root=tmp_path, plan_file=plan_file, runner=runner
    )
    assert committed.touched_paths == ("src/a.py",)

    _ = target.write_text("original\n", encoding="utf-8")
    runner.head = "c" * 40
    runner.diff_paths = ()
    second = scope_disposition.compute_coverage(
        tmpdir=tmp_path, repo_root=tmp_path, plan_file=plan_file, runner=runner
    )
    assert not second.touched_paths
    assert second.untouched_paths == ("src/a.py",)


def test_frozen_fallback_anchor_diff_failure_raises_after_provenance(
    tmp_path: Path,
) -> None:
    _ = (tmp_path / "step2-baseline.txt").write_text("STEP2BASE\n", encoding="utf-8")
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    _ = (src / "a.py").write_text("implemented\n", encoding="utf-8")
    runner = FakeRunner(
        status_z=_porcelain_z([" M src/a.py"]),
        fail_symbolic_refs=frozenset({"origin"}),
    )
    assert scope_disposition.touched_paths_since_baseline(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        runner=runner,
        plan_paths=["src/a.py"],
    ) == ("src/a.py",)

    runner.status_z = ""
    runner.head = "b" * 40
    runner.fail_diff = True
    with pytest.raises(ShipError, match="frozen fallback anchor-to-HEAD diff failed"):
        _ = scope_disposition.touched_paths_since_baseline(
            tmpdir=tmp_path,
            repo_root=tmp_path,
            runner=runner,
            plan_paths=["src/a.py"],
        )


def test_frozen_fallback_diagnostic_does_not_alter_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(_plan(["src/a.py"]), encoding="utf-8")
    _ = (tmp_path / "step2-baseline.txt").write_text("STEP2BASE\n", encoding="utf-8")
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    _ = (src / "a.py").write_text("x\n", encoding="utf-8")

    coverage = scope_disposition.compute_and_write_coverage(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        plan_file=plan_file,
        runner=FakeRunner(
            status_z=_porcelain_z([" M src/a.py"]),
            fail_symbolic_refs=frozenset({"origin"}),
        ),
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unresolved origin/HEAD" in captured.err
    assert coverage.touched == 1


def test_slashy_remote_default_branch_passed_to_merge_base(tmp_path: Path) -> None:
    runner = FakeRunner(
        diff_paths=[],
        merge_base="MB",
        remote_heads={"origin": "origin/releases/stable"},
    )
    resolution = scope_disposition.resolve_baseline(
        tmpdir=tmp_path, repo_root=tmp_path, runner=runner
    )
    assert resolution.committed_paths_trustworthy is True
    merge_base_calls = [
        call for call in runner.calls if call[:2] == ("git", "merge-base")
    ]
    assert merge_base_calls[0][2] == "origin/releases/stable"


def test_malformed_fallback_provenance_is_ignored(tmp_path: Path) -> None:
    _ = (tmp_path / "step2-baseline.txt").write_text("STEP2BASE\n", encoding="utf-8")
    _ = (tmp_path / scope_disposition.FALLBACK_PROVENANCE).write_text(
        '{"schema_version":"1","paths":{"src/a.py":"bad"}}\n',
        encoding="utf-8",
    )
    runner = FakeRunner(
        status_z="",
        fail_symbolic_refs=frozenset({"origin"}),
    )
    touched = scope_disposition.touched_paths_since_baseline(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        runner=runner,
        plan_paths=["src/a.py"],
    )
    assert not touched


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
    # `run-log write` is Rust-owned and routes through the bootstrap runner.
    monkeypatch.setattr(scope_disposition, "_run_larch", fake_run_cli, raising=False)

    record = scope_disposition.record_disposition(
        tmpdir=tmp_path,
        disposition="proceed-partial",
        repo_root=tmp_path,
        coverage=coverage,
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
    # `run-log write` is Rust-owned and routes through the bootstrap runner.
    monkeypatch.setattr(scope_disposition, "_run_larch", fake_run_cli, raising=False)

    with pytest.raises(ShipError):
        _ = scope_disposition.record_disposition(
            tmpdir=tmp_path,
            disposition="proceed-partial",
            repo_root=tmp_path,
            coverage=coverage,
            repo="owner/repo",
            tracking_issue_number="12",
            run_id="run-xyz",
        )

    assert not scope_disposition.disposition_path(tmp_path).exists()


def test_record_proceed_partial_dedups_followup_on_matching_fingerprint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    coverage = _coverage_fixture(tmp_path, required=True)
    scope_disposition.write_coverage(coverage, tmpdir=tmp_path)
    _ = (tmp_path / "scope-disposition.json").write_text(
        json.dumps(
            {
                "disposition": "proceed-partial",
                "fingerprint": coverage.fingerprint,
                "followup_issue_number": "99",
                "followup_issue_url": "https://example.test/issues/99",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    calls: list[tuple[str, ...]] = []

    def fake_run_cli(argv: Sequence[str]) -> CommandResult:
        args = tuple(argv)
        calls.append(args)
        return CommandResult(args, 0, "OK=true\n", "", 0.0)

    monkeypatch.setattr(scope_disposition, "_run_cli", fake_run_cli)
    # `run-log write` is Rust-owned and routes through the bootstrap runner.
    monkeypatch.setattr(scope_disposition, "_run_larch", fake_run_cli, raising=False)

    record = scope_disposition.record_disposition(
        tmpdir=tmp_path,
        disposition="proceed-partial",
        repo_root=tmp_path,
        coverage=coverage,
        repo="owner/repo",
        tracking_issue_number="12",
        run_id="run-xyz",
    )

    assert record.followup_issue_number == "99"
    assert record.followup_issue_url == "https://example.test/issues/99"
    assert not any(call[:2] == ("issue", "create-one") for call in calls)
    assert not any(call[:2] == ("tracking-issue", "append-comment") for call in calls)
    assert not any(call[:2] == ("issue", "add-blocked-by") for call in calls)


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
        tmpdir=tmp_path,
        disposition="bail-rescope",
        repo_root=tmp_path,
        coverage=coverage,
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
    with pytest.raises(ShipError):
        _ = scope_disposition.disposition_link_kind(tmp_path, repo_root=tmp_path)


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


def test_non_regular_reserved_artifact_still_makes_pr_mutation_gate_relevant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_dir = tmp_path / "plan.txt"
    plan_dir.mkdir()
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

    assert scope_disposition.is_pr_mutation_gate_relevant(tmpdir=tmp_path) is True
    scope_disposition.require_pr_mutation_scope_disposition(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        runner=FakeRunner(diff_paths=[]),
    )
    assert calls == [None]


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


def test_validate_manifest_todos_schema_invalid_fails_closed(tmp_path: Path) -> None:
    _ = (tmp_path / "plan.txt").write_text(_plan(["a.py"]), encoding="utf-8")
    _ = (tmp_path / "step2-baseline.txt").write_text("BASE\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text('{"todos_left": "finish docs"}\n', encoding="utf-8")

    result = scope_disposition.validate_disposition_for_ship(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        manifest_path=manifest,
        runner=FakeRunner(diff_paths=["a.py"]),
    )

    assert result.ok is False
    assert result.required is True
    assert result.reason.startswith("coverage-recompute-failed")


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


def test_validate_non_gate_recompute_failure_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coverage = _coverage_fixture(tmp_path, required=False)

    def fake_load(_tmpdir: Path) -> scope_disposition.PlanCoverage:
        return coverage

    def fake_gate_relevant(**_kwargs: object) -> bool:
        return False

    monkeypatch.setattr(scope_disposition, "load_coverage", fake_load)
    monkeypatch.setattr(
        scope_disposition, "is_pr_mutation_gate_relevant", fake_gate_relevant
    )

    result = scope_disposition.validate_disposition_for_ship(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        runner=FakeRunner(diff_paths=[]),
    )

    assert result.ok is False
    assert result.required is False
    assert result.reason.startswith("coverage-recompute-failed")


def test_load_coverage_rejects_partial_and_symlinked_sets(tmp_path: Path) -> None:
    _ = (tmp_path / scope_disposition.COVERAGE_JSON).write_text(
        "{}\n", encoding="utf-8"
    )
    with pytest.raises(ShipError, match="partial"):
        _ = scope_disposition.load_coverage(tmp_path)

    (tmp_path / scope_disposition.COVERAGE_JSON).unlink()
    outside = tmp_path.parent / f"{tmp_path.name}-outside.json"
    _ = outside.write_text("{}\n", encoding="utf-8")
    (tmp_path / scope_disposition.COVERAGE_JSON).symlink_to(outside)
    with pytest.raises(ShipError, match="unsafe"):
        _ = scope_disposition.load_coverage(tmp_path)


def test_load_coverage_rejects_companion_mismatch(tmp_path: Path) -> None:
    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(_plan(["src/a.py"]), encoding="utf-8")
    _ = (tmp_path / "step2-baseline.txt").write_text("BASE\n", encoding="utf-8")
    _ = scope_disposition.compute_and_write_coverage(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        plan_file=plan_file,
        runner=FakeRunner(diff_paths=[]),
    )
    _ = (tmp_path / scope_disposition.UNTOUCHED_PATHS).write_text(
        "tampered\n", encoding="utf-8"
    )

    with pytest.raises(ShipError, match="inventory mismatch"):
        _ = scope_disposition.load_coverage(tmp_path)


def test_create_followup_issue_passes_context_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_create_followup_issue must pass --context-file when session-env.sh exists."""
    senv = tmp_path / "session-env.sh"
    _ = senv.write_text(
        f"{config.LIVE_MUTATION_AUTH_KEY}=true\nLARCH_RUN_ID=run-1\n", encoding="utf-8"
    )

    captured_args: list[list[str]] = []

    def fake_run_cli(argv: Sequence[str]) -> CommandResult:
        captured_args.append(list(argv))
        return CommandResult(
            tuple(argv),
            0,
            "ISSUE_NUMBER=123\nISSUE_URL=https://github.com/o/r/issues/123\n",
            "",
            0.0,
        )

    monkeypatch.setattr(scope_disposition, "_run_cli", fake_run_cli)
    # `run-log write` is Rust-owned and routes through the bootstrap runner.
    monkeypatch.setattr(scope_disposition, "_run_larch", fake_run_cli, raising=False)

    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(
        "### UPDATED: src/a.py\ndiff_lines: 10\n", encoding="utf-8"
    )
    _ = (tmp_path / "step2-baseline.txt").write_text("BASE\n", encoding="utf-8")
    coverage = scope_disposition.compute_and_write_coverage(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        plan_file=plan_file,
        runner=FakeRunner(diff_paths=[]),
    )

    _ = scope_disposition._create_followup_issue(  # pyright: ignore[reportPrivateUsage]
        tmpdir=tmp_path,
        repo="owner/repo",
        tracking_issue_number="42",
        coverage=coverage,
    )
    assert captured_args, "no CLI call was made"
    first_call = captured_args[0]
    assert "--context-file" in first_call
    ctx_idx = first_call.index("--context-file")
    assert first_call[ctx_idx + 1] == str(senv)


def test_live_coverage_maps_directory_descendant_to_firm_path(
    tmp_path: Path,
) -> None:
    """Trailing-slash firm dirs credit nested touches once; siblings stay exact-only."""
    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(
        _plan(
            [
                "python/tests/support/",
                "python/tests/support_helpers.py",
                "src/exact.py",
            ]
        ),
        encoding="utf-8",
    )
    _ = (tmp_path / "step2-baseline.txt").write_text("BASE\n", encoding="utf-8")
    runner = FakeRunner(
        diff_paths=[
            "python/tests/support/helpers.py",
            "python/tests/support/nested/util.py",
            "python/tests/support_helpers.py",
            "src/exact.py/not_a_descendant.py",
            "unrelated/other.py",
        ]
    )

    coverage = scope_disposition.compute_and_write_coverage(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        plan_file=plan_file,
        runner=runner,
    )

    assert coverage.touched_paths == (
        "python/tests/support/",
        "python/tests/support_helpers.py",
    )
    assert "python/tests/support/" not in coverage.untouched_paths
    assert coverage.untouched_paths == ("src/exact.py",)
    assert coverage.untouched == 1
    assert coverage.disposition_required is False

    reloaded = scope_disposition.load_coverage(tmp_path)
    assert reloaded is not None
    assert reloaded == coverage
    assert reloaded.fingerprint == coverage.fingerprint


def test_frozen_fallback_keeps_raw_descendant_for_provenance(
    tmp_path: Path,
) -> None:
    """Frozen fallback retains nested porcelain paths; coverage maps to firm dir."""
    plan_file = tmp_path / "plan.txt"
    _ = plan_file.write_text(
        _plan(["python/tests/support/", "src/sibling_support.py"]),
        encoding="utf-8",
    )
    _ = (tmp_path / "step2-baseline.txt").write_text("STEP2BASE\n", encoding="utf-8")
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    nested = tmp_path / "python" / "tests" / "support"
    nested.mkdir(parents=True)
    _ = (nested / "helpers.py").write_text("helpers\n", encoding="utf-8")
    sibling = tmp_path / "src"
    sibling.mkdir()
    _ = (sibling / "sibling_support.py").write_text("sibling\n", encoding="utf-8")

    runner = FakeRunner(
        diff_paths=["python/tests/support/helpers.py"],
        status_z=_porcelain_z(
            [
                " M python/tests/support/helpers.py",
                " M src/sibling_support.py",
                "?? python/tests/support_extra.py",
            ]
        ),
        fail_symbolic_refs=frozenset({"origin"}),
        fail_diff=True,
    )

    coverage = scope_disposition.compute_and_write_coverage(
        tmpdir=tmp_path,
        repo_root=tmp_path,
        plan_file=plan_file,
        runner=runner,
    )

    provenance = json.loads(
        (tmp_path / scope_disposition.FALLBACK_PROVENANCE).read_text(encoding="utf-8")
    )
    assert "python/tests/support/helpers.py" in provenance["path_signatures"]
    assert "src/sibling_support.py" in provenance["path_signatures"]
    assert "python/tests/support/" not in provenance["path_signatures"]
    assert "python/tests/support_extra.py" not in provenance["path_signatures"]

    assert coverage.touched_paths == (
        "python/tests/support/",
        "src/sibling_support.py",
    )
    assert not coverage.untouched_paths
    assert coverage.disposition_required is False

    reloaded = scope_disposition.load_coverage(tmp_path)
    assert reloaded is not None
    assert reloaded == coverage
