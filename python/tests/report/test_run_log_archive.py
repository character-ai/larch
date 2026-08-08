"""Tests for the Rust-owned run-log archive consumer."""

from __future__ import annotations

from pathlib import Path

import pytest

from larch.core import proc
from larch.report import run_log_archive


def _command_result(
    *, returncode: int, stdout: str = "", stderr: str = ""
) -> proc.CommandResult:
    return proc.CommandResult(
        argv=("larch",),
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        duration=0.0,
    )


def test_archive_consumer_parses_the_rust_machine_envelope(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def invoke(arguments: list[str], **_kwargs: object) -> proc.CommandResult:
        calls.append(arguments)
        return _command_result(
            returncode=0,
            stdout=(
                f"ARCHIVE_PATH={tmp_path / 'out' / 'run-1.tar.gz'}\nARCHIVE_SHA256="
                + "a" * 64
                + "\n"
                + "MANIFEST_SHA256="
                + "b" * 64
                + "\n"
                + "MEMBER_COUNT=2\n"
            ),
        )

    monkeypatch.setattr(run_log_archive, "_invoke", invoke)
    result = run_log_archive.create_run_archive(
        staging_root=tmp_path / "staging",
        output_dir=tmp_path / "out",
        skill="design",
        run_id="run-1",
    )

    assert result.archive_path == tmp_path / "out" / "run-1.tar.gz"
    assert result.member_count == 2
    assert len(calls) == 1
    assert Path(calls[0][0]).name == "larch.sh"
    assert calls[0][1:] == [
        "run-log",
        "archive",
        "--staging-root",
        str(tmp_path / "staging"),
        "--output-dir",
        str(tmp_path / "out"),
        "--skill",
        "design",
        "--run-id",
        "run-1",
    ]


def test_materialization_consumer_uses_each_typed_rust_route(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def invoke(arguments: list[str], **_kwargs: object) -> proc.CommandResult:
        calls.append(arguments)
        return _command_result(
            returncode=0,
            stdout=(
                f"RUN_DIR={tmp_path / 'cache' / 'run-1'}\n"
                "MANIFEST_SHA256=" + "c" * 64 + "\nMEMBER_COUNT=3\nEXPANDED_SIZE=99\n"
            ),
        )

    monkeypatch.setattr(run_log_archive, "_invoke", invoke)
    archive = tmp_path / "archive.tar.gz"
    run_dir = tmp_path / "cache" / "run-1"
    materialized = run_log_archive.materialize_run_archive(
        archive_path=archive,
        run_dir=run_dir,
        expected_skill="review",
        expected_run_id="run-1",
    )
    verified = run_log_archive.verify_materialized_run_directory(
        run_dir=run_dir,
        expected_skill="review",
        expected_run_id="run-1",
    )
    promoted = run_log_archive.promote_staging_run_directory(
        staging_root=tmp_path / "staging",
        run_dir=run_dir,
        expected_skill="review",
        expected_run_id="run-1",
        expected_manifest_sha256="d" * 64,
    )

    assert materialized == verified == promoted
    assert [Path(call[0]).name for call in calls] == ["larch.sh"] * 3
    assert [call[1:] for call in calls] == [
        [
            "run-log",
            "materialize",
            "--archive-path",
            str(archive),
            "--run-dir",
            str(run_dir),
            "--skill",
            "review",
            "--run-id",
            "run-1",
        ],
        [
            "run-log",
            "materialize",
            "--verify-existing",
            "--run-dir",
            str(run_dir),
            "--skill",
            "review",
            "--run-id",
            "run-1",
        ],
        [
            "run-log",
            "materialize",
            "--staging-root",
            str(tmp_path / "staging"),
            "--run-dir",
            str(run_dir),
            "--skill",
            "review",
            "--run-id",
            "run-1",
            "--expected-manifest-sha256",
            "d" * 64,
        ],
    ]


def test_consumer_rejects_failed_or_malformed_rust_envelopes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def failed_invoke(_command: list[str]) -> proc.CommandResult:
        return _command_result(
            returncode=1,
            stdout="ERROR=archive member path is unsafe\n",
        )

    monkeypatch.setattr(
        run_log_archive,
        "_invoke",
        failed_invoke,
    )
    with pytest.raises(run_log_archive.RunLogArchiveError, match="path is unsafe"):
        _ = run_log_archive.materialize_run_archive(
            archive_path=tmp_path / "archive.tar.gz",
            run_dir=tmp_path / "cache" / "run-1",
            expected_skill="review",
            expected_run_id="run-1",
        )

    def malformed_invoke(_command: list[str]) -> proc.CommandResult:
        return _command_result(returncode=0, stdout="RUN_DIR=/tmp/run\n")

    monkeypatch.setattr(run_log_archive, "_invoke", malformed_invoke)
    with pytest.raises(
        run_log_archive.RunLogArchiveError, match="invalid machine envelope"
    ):
        _ = run_log_archive.verify_materialized_run_directory(
            run_dir=tmp_path / "cache" / "run-1",
            expected_skill="review",
            expected_run_id="run-1",
        )


def test_consumer_preserves_the_staging_drift_error_type(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def drifted_invoke(_command: list[str]) -> proc.CommandResult:
        return _command_result(
            returncode=1,
            stdout="ERROR=staging tree no longer matches the pending archive manifest\n",
        )

    monkeypatch.setattr(
        run_log_archive,
        "_invoke",
        drifted_invoke,
    )
    with pytest.raises(run_log_archive.StagingManifestMismatchError):
        _ = run_log_archive.promote_staging_run_directory(
            staging_root=tmp_path / "staging",
            run_dir=tmp_path / "cache" / "run-1",
            expected_skill="review",
            expected_run_id="run-1",
            expected_manifest_sha256="a" * 64,
        )
