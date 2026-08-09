"""Executable lifecycle coverage for Rust-policy candidate staging."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest

from larch import cli
from larch.implement import rust_policy_candidate as candidate


SOURCE_SHA = "a" * 40
RUST_INPUTS_SHA256 = "b" * 64
VERSION = "larch 0.1.0\n"


def _write_larch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(
        "#!/bin/sh\n"
        'if [ "${1:-}" = "--version" ]; then\n'
        "  printf '%s\\n' 'larch 0.1.0'\n"
        "  exit 0\n"
        "fi\n"
        "exit 64\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _prepare_artifact(tmp_path: Path) -> tuple[Path, Path]:
    coverage_larch = tmp_path / "workspace" / "target" / "llvm-cov-target" / "debug" / "larch"
    _write_larch(coverage_larch)
    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir()
    artifact_dir = runner_temp / "larch-linux-test-binary"
    assert cli.main([
        "ci",
        "prepare-rust-integration-artifact",
        "--coverage-larch",
        str(coverage_larch),
        "--artifact-dir",
        str(artifact_dir),
        "--source-sha",
        SOURCE_SHA,
        "--rust-inputs-sha256",
        RUST_INPUTS_SHA256,
    ]) == 0
    return coverage_larch, artifact_dir


def test_prepare_prune_and_post_prune_candidate_stage_uses_preserved_artifact(tmp_path: Path) -> None:
    coverage_larch, artifact_dir = _prepare_artifact(tmp_path)
    coverage_target = coverage_larch.parents[1]

    # Mirror the coverage action's product prune: the workspace executable is
    # gone, while the already-prepared integration artifact remains intact.
    shutil.rmtree(coverage_target)
    assert not coverage_larch.exists()

    policy_dir = tmp_path / "runner-temp" / "trusted-main-rust-policy"
    assert cli.main([
        "ci",
        "stage-rust-policy-candidate",
        "--artifact-dir",
        str(artifact_dir),
        "--policy-dir",
        str(policy_dir),
        "--event-name",
        "pull_request",
        "--ref",
        "refs/pull/8319/merge",
        "--source-sha",
        SOURCE_SHA,
        "--rust-inputs-sha256",
        RUST_INPUTS_SHA256,
    ]) == 0

    expected_checksum = hashlib.sha256((policy_dir / "larch").read_bytes()).hexdigest()
    assert (artifact_dir / "larch.sha256").read_text(encoding="utf-8") == f"{expected_checksum}  larch\n"
    assert (policy_dir / "larch.sha256").read_text(encoding="utf-8") == f"{expected_checksum}  larch\n"
    assert (policy_dir / "producer-ref").read_text(encoding="utf-8") == "current-checkout\n"
    assert (policy_dir / "version").read_text(encoding="utf-8") == VERSION
    for filename in ("larch", "larch.sha256", "producer-ref", "rust-inputs-sha256", "source-sha", "version"):
        assert not (policy_dir / filename).is_symlink()


@pytest.mark.parametrize(
    ("event_name", "ref", "expected"),
    [
        ("push", "refs/heads/main", "refs/heads/main"),
        ("pull_request", "refs/pull/8319/merge", "current-checkout"),
        ("merge_group", "refs/heads/gh-readonly-queue/main/pr-8319", "current-checkout"),
        ("workflow_dispatch", "refs/heads/main", "current-checkout"),
    ],
)
def test_candidate_provenance_only_labels_successful_main_push_as_trusted(
    event_name: str,
    ref: str,
    expected: str,
) -> None:
    assert candidate.candidate_producer_ref(event_name=event_name, ref=ref) == expected


def test_stage_rejects_a_modified_integration_artifact_before_copying(tmp_path: Path) -> None:
    _coverage_larch, artifact_dir = _prepare_artifact(tmp_path)
    _ = (artifact_dir / "larch").write_text("modified\n", encoding="utf-8")

    with pytest.raises(candidate.CandidateError, match="checksum"):
        _ = candidate.stage_policy_candidate(
            candidate.PolicyCandidateRequest(
                artifact_dir=artifact_dir,
                policy_dir=tmp_path / "runner-temp" / "trusted-main-rust-policy",
                event_name="push",
                ref="refs/heads/main",
                source_sha=SOURCE_SHA,
                rust_inputs_sha256=RUST_INPUTS_SHA256,
            )
        )


def test_rust_policy_candidate_cli_entries_are_registered() -> None:
    assert cli._REGISTRY[("ci", "prepare-rust-integration-artifact")] == (  # pyright: ignore[reportPrivateUsage]
        "larch.implement.rust_policy_candidate",
        "prepare_integration_artifact_main",
        False,
    )
    assert cli._REGISTRY[("ci", "stage-rust-policy-candidate")] == (  # pyright: ignore[reportPrivateUsage]
        "larch.implement.rust_policy_candidate",
        "stage_policy_candidate_main",
        False,
    )
