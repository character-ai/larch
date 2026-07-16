"""Focused offline coverage for analyze-bugs runtime verification."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from larch.core.proc import CommandResult
from larch.issue import analyze_bugs

from test_support import RecordingRunner


SHA_A = "a" * 40
SHA_B = "b" * 40


def _result(stdout: str = "", rc: int = 0, stderr: str = "") -> CommandResult:
    return CommandResult(("test",), rc, stdout, stderr, 0.01)


def _bundle(*, issue: int, cache_key: str, sha: str, files: tuple[str, ...] = (), fix_time: int = 1) -> analyze_bugs.BundleRecord:
    return analyze_bugs.BundleRecord(
        issue_number=issue,
        title="[BUG] runtime",
        state="CLOSED",
        state_reason="COMPLETED",
        url="",
        body_path="",
        bundle_path="",
        fix_sha=sha,
        fix_source="git-log",
        touched_files=files,
        later_history_hash="history",
        mechanical_verdict="",
        mechanical_reason="",
        cache_key=cache_key,
        fix_time=fix_time,
    )


def test_discover_runtime_tests_keeps_only_live_added_or_modified_tests(tmp_path: Path) -> None:
    test_file = tmp_path / "python/tests/issue/test_live.py"
    test_file.parent.mkdir(parents=True)
    _ = test_file.write_text("def test_live(): pass\n", encoding="utf-8")
    runner = RecordingRunner(responses=[_result("A\tpython/tests/issue/test_live.py\nM\tpython/tests/issue/missing.py\nD\tpython/tests/issue/deleted.py\nM\tpython/larch/issue/analyze_bugs.py\nA\t../unsafe.py\n")], strict=True)

    assert analyze_bugs.discover_runtime_tests(runner=runner, fix_sha=SHA_A, repo_root=tmp_path) == ("python/tests/issue/test_live.py",)


def test_harness_resolution_and_zone_labels_are_deterministic() -> None:
    paths = ("skills/implement/SKILL.md", "scripts/test-implement-anti-halt.sh", "scripts/other.sh")

    assert analyze_bugs.resolve_runtime_harnesses(paths) == (
        "test-architectural-guidelines-step",
        "test-implement-anti-halt",
        "test-lint-bash32",
    )
    assert analyze_bugs.runtime_zone_label("python/larch/implement/dispatch.py") == "python/larch/implement"
    assert analyze_bugs._runtime_uncovered_zones(("skills/other/SKILL.md",)) == ("skills",)  # pyright: ignore[reportPrivateUsage]  # pure coverage helper


def test_runtime_verify_never_runs_pytest_without_discovered_paths(tmp_path: Path) -> None:
    runner = RecordingRunner(responses=[_result("")], strict=True)
    results, skipped = analyze_bugs.runtime_verify(
        runner=runner,
        run_dir=tmp_path,
        bundles=[_bundle(issue=1, cache_key="one", sha=SHA_A)],
        runtime_max=10,
        repo_root=tmp_path,
    )

    assert skipped == 0
    assert results[0].components == (analyze_bugs.RuntimeComponent("pytest", "absent", "no runnable commit test files"),)
    assert all(call.argv[:3] != ("python3", "-m", "pytest") for call in runner.records)


def test_runtime_max_zero_replaces_artifact_without_running_commands(tmp_path: Path) -> None:
    artifact = tmp_path / analyze_bugs.RUNTIME_RESULTS_NAME
    _ = artifact.write_text("stale\n", encoding="utf-8")
    runner = RecordingRunner(responses=[], strict=True)

    results, skipped = analyze_bugs.runtime_verify(
        runner=runner,
        run_dir=tmp_path,
        bundles=[_bundle(issue=1, cache_key="one", sha=SHA_A)],
        runtime_max=0,
        repo_root=tmp_path,
    )

    assert not results
    assert skipped == 1
    assert artifact.read_text(encoding="utf-8") == ""
    assert not runner.calls



def test_runtime_verify_runs_exact_pytest_argv_and_fans_out_same_sha(tmp_path: Path) -> None:
    test_file = tmp_path / "python/tests/issue/test_live.py"
    test_file.parent.mkdir(parents=True)
    _ = test_file.write_text("def test_live(): pass\n", encoding="utf-8")
    runner = RecordingRunner(responses=[_result("M\tpython/tests/issue/test_live.py\n"), _result(), _result()], strict=True)
    bundles = [
        _bundle(issue=1, cache_key="one", sha=SHA_A, files=("skills/implement/SKILL.md",), fix_time=2),
        _bundle(issue=2, cache_key="two", sha=SHA_A, files=("skills/implement/SKILL.md",), fix_time=1),
    ]

    results, skipped = analyze_bugs.runtime_verify(runner=runner, run_dir=tmp_path, bundles=bundles, runtime_max=1, repo_root=tmp_path)

    assert skipped == 0
    assert [binding.issue for binding in results[0].bindings] == [1, 2]
    pytest_argv = runner.records[1].argv
    assert pytest_argv[:7] == ("python3", "-m", "pytest", "-p", "no:cacheprovider", "--basetemp", str(tmp_path / "runtime-pytest-tmp" / SHA_A))
    assert pytest_argv[7:] == ("--", "python/tests/issue/test_live.py")
    assert runner.records[2].argv == ("make", "test-architectural-guidelines-step")


@pytest.mark.parametrize("status", ["failed", "timeout"])
def test_runtime_failure_overrides_static_and_keeps_uncovered_annotation(status: str) -> None:
    result = analyze_bugs.RuntimeResult(
        fix_sha=SHA_A,
        bindings=(),
        components=(analyze_bugs.RuntimeComponent("pytest", status, "bad\noutput"),),
        uncovered_zones=("skills",),
    )

    verdict, tier, reason, annotations = analyze_bugs._runtime_overlay("CONFIRMED_FIXED", "DEEP", "deep pass", result)  # pyright: ignore[reportPrivateUsage]  # final verdict integration

    assert (verdict, tier) == ("SUSPECT", "RUNTIME")
    assert "bad\noutput" in reason
    assert annotations == ("UNVERIFIED_RUNTIME: no harness covers skills",)
    assert not analyze_bugs._verified_issue(verdict, tier)  # pyright: ignore[reportPrivateUsage]  # verified predicate coverage


def test_stale_runtime_binding_is_ignored_and_malformed_artifact_fails(tmp_path: Path) -> None:
    bundle = _bundle(issue=1, cache_key="one", sha=SHA_A)
    stale = analyze_bugs.RuntimeResult(SHA_B, (analyze_bugs.RuntimeBinding(1, "one", SHA_B),), (), ())
    _ = (tmp_path / analyze_bugs.RUNTIME_RESULTS_NAME).write_text(json.dumps(analyze_bugs._runtime_result_json(stale)) + "\n", encoding="utf-8")  # pyright: ignore[reportPrivateUsage]  # artifact fixture serialization

    assert not analyze_bugs.load_runtime_results(tmp_path / analyze_bugs.RUNTIME_RESULTS_NAME, [bundle])
    _ = (tmp_path / analyze_bugs.RUNTIME_RESULTS_NAME).write_text("not-json\n", encoding="utf-8")
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="malformed runtime"):
        _ = analyze_bugs.load_runtime_results(tmp_path / analyze_bugs.RUNTIME_RESULTS_NAME, [bundle])
