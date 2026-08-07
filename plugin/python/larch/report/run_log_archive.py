"""Typed Python consumer for Rust-owned run-log archive commands."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from larch.core import config, proc
from larch.core.repo_roots import larch_entrypoint


ARCHIVE_FORMAT: str = "larch-run-archive"
ARCHIVE_MANIFEST_NAME: str = "archive-manifest.json"
ARCHIVE_SCHEMA_VERSION: int = 1
_CHUNK_SIZE = 1024 * 1024


class RunLogArchiveError(ValueError):
    """The Rust archive command rejected an input or machine envelope."""


class StagingManifestMismatchError(RunLogArchiveError):
    """The live staging tree differs from an already pinned pending archive."""


@dataclass(frozen=True)
class RunArchiveResult:
    """Paths and digests emitted by the Rust archive command."""

    archive_path: Path
    archive_sha256: str
    manifest_sha256: str
    member_count: int


@dataclass(frozen=True)
class RunArchiveMaterializationResult:
    """Verified local run directory emitted by the Rust materialize command."""

    run_dir: Path
    manifest_sha256: str
    member_count: int
    expanded_size: int


def _invoke(command: list[str]) -> proc.CommandResult:
    """Run one fully specified archive command through the verified bootstrap."""
    plugin_root = Path(__file__).resolve().parents[3]
    environment = dict(os.environ)
    environment[config.ENV_CLAUDE_PLUGIN_ROOT] = str(plugin_root)
    return proc.run(
        command,
        env=environment,
        check=False,
    )


def _kv(stdout: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator and key:
            values[key] = value
    return values


def _command_values(
    result: proc.CommandResult,
    *,
    required: tuple[str, ...],
) -> dict[str, str]:
    values = _kv(result.stdout)
    if result.returncode != 0:
        detail = values.get("ERROR") or result.stderr.strip()
        raise RunLogArchiveError(detail or "Rust run-log archive command failed")
    if any(not values.get(key) for key in required):
        raise RunLogArchiveError(
            "Rust run-log archive command returned an invalid machine envelope"
        )
    return values


def _nonnegative_int(values: Mapping[str, str], key: str) -> int:
    raw = values[key]
    if not raw.isascii() or not raw.isdecimal():
        raise RunLogArchiveError(f"Rust run-log archive returned invalid {key}")
    return int(raw)


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of one regular file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def create_run_archive(
    *,
    staging_root: Path,
    output_dir: Path,
    skill: str,
    run_id: str,
) -> RunArchiveResult:
    """Create one deterministic archive through the Rust command owner."""
    plugin_root = Path(__file__).resolve().parents[3]
    values = _command_values(
        _invoke(
            [
                str(larch_entrypoint(plugin_root, use_env=False)),
                "run-log",
                "archive",
                "--staging-root",
                str(staging_root),
                "--output-dir",
                str(output_dir),
                "--skill",
                skill,
                "--run-id",
                run_id,
            ]
        ),
        required=("ARCHIVE_PATH", "ARCHIVE_SHA256", "MANIFEST_SHA256", "MEMBER_COUNT"),
    )
    return RunArchiveResult(
        archive_path=Path(values["ARCHIVE_PATH"]),
        archive_sha256=values["ARCHIVE_SHA256"],
        manifest_sha256=values["MANIFEST_SHA256"],
        member_count=_nonnegative_int(values, "MEMBER_COUNT"),
    )


def _materialization_result(
    arguments: list[str],
) -> RunArchiveMaterializationResult:
    plugin_root = Path(__file__).resolve().parents[3]
    values = _command_values(
        _invoke(
            [
                str(larch_entrypoint(plugin_root, use_env=False)),
                "run-log",
                "materialize",
                *arguments,
            ]
        ),
        required=("RUN_DIR", "MANIFEST_SHA256", "MEMBER_COUNT", "EXPANDED_SIZE"),
    )
    return RunArchiveMaterializationResult(
        run_dir=Path(values["RUN_DIR"]),
        manifest_sha256=values["MANIFEST_SHA256"],
        member_count=_nonnegative_int(values, "MEMBER_COUNT"),
        expanded_size=_nonnegative_int(values, "EXPANDED_SIZE"),
    )


def materialize_run_archive(
    *,
    archive_path: Path,
    run_dir: Path,
    expected_skill: str,
    expected_run_id: str,
) -> RunArchiveMaterializationResult:
    """Verify and atomically materialize one archive through Rust."""
    return _materialization_result(
        [
            "--archive-path",
            str(archive_path),
            "--run-dir",
            str(run_dir),
            "--skill",
            expected_skill,
            "--run-id",
            expected_run_id,
        ]
    )


def verify_materialized_run_directory(
    *,
    run_dir: Path,
    expected_skill: str,
    expected_run_id: str,
) -> RunArchiveMaterializationResult:
    """Verify one unpacked run directory through the Rust archive owner."""
    return _materialization_result(
        [
            "--verify-existing",
            "--run-dir",
            str(run_dir),
            "--skill",
            expected_skill,
            "--run-id",
            expected_run_id,
        ]
    )


def promote_staging_run_directory(
    *,
    staging_root: Path,
    run_dir: Path,
    expected_skill: str,
    expected_run_id: str,
    expected_manifest_sha256: str,
) -> RunArchiveMaterializationResult:
    """Copy a manifest-pinned staging tree through the Rust archive owner."""
    try:
        return _materialization_result(
            [
                "--staging-root",
                str(staging_root),
                "--run-dir",
                str(run_dir),
                "--skill",
                expected_skill,
                "--run-id",
                expected_run_id,
                "--expected-manifest-sha256",
                expected_manifest_sha256,
            ]
        )
    except RunLogArchiveError as exc:
        if str(exc) == "staging tree no longer matches the pending archive manifest":
            raise StagingManifestMismatchError(str(exc)) from exc
        raise
