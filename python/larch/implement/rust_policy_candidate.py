"""Prepare and verify Rust-policy cache candidates from CI integration artifacts."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final


_SHA256_RE: Final = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_SHA_RE: Final = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_CHECKSUM_RE: Final = re.compile(r"^([0-9a-f]{64})  larch\n$")
_CURRENT_CHECKOUT_PROVENANCE: Final = "current-checkout"
_TRUSTED_MAIN_PROVENANCE: Final = "refs/heads/main"
_VERSION_TIMEOUT_SECONDS: Final = 10
_HASH_CHUNK_BYTES: Final = 1024 * 1024


class CandidateError(ValueError):
    """A candidate artifact cannot safely be prepared or staged."""


@dataclass(frozen=True)
class IntegrationArtifactRequest:
    """Inputs needed to preserve a coverage-built Python integration artifact."""

    coverage_larch: Path
    artifact_dir: Path
    source_sha: str
    rust_inputs_sha256: str


@dataclass(frozen=True)
class PolicyCandidateRequest:
    """Inputs needed to stage a policy cache candidate from an artifact."""

    artifact_dir: Path
    policy_dir: Path
    event_name: str
    ref: str
    source_sha: str
    rust_inputs_sha256: str


@dataclass(frozen=True)
class VerifiedArtifact:
    """The integrity and identity fields proven for one executable bundle."""

    sha256: str
    version: str


VersionReader = Callable[[Path], str]


def _read_binary_version(binary: Path) -> str:
    try:
        completed = subprocess.run(
            [str(binary), "--version"],
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=_VERSION_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CandidateError("could not read bundle executable version") from exc
    if completed.returncode != 0 or not completed.stdout.strip():
        raise CandidateError("bundle executable version command failed")
    return completed.stdout


def prepare_integration_artifact(
    request: IntegrationArtifactRequest,
    *,
    version_reader: VersionReader = _read_binary_version,
) -> VerifiedArtifact:
    """Copy a coverage executable and prove the resulting integration artifact."""
    source_sha = _require_source_sha(request.source_sha)
    rust_inputs_sha256 = _require_sha256(request.rust_inputs_sha256, name="Rust-input digest")
    coverage_larch = _require_regular_file(request.coverage_larch, label="coverage executable")
    _require_executable(coverage_larch, label="coverage executable")
    version = version_reader(coverage_larch)

    _replace_directory(request.artifact_dir, label="integration artifact directory")
    artifact_larch = request.artifact_dir / "larch"
    _copy_executable(coverage_larch, artifact_larch)
    checksum = _sha256_file(artifact_larch)
    _write_text(request.artifact_dir / "larch.sha256", f"{checksum}  larch\n")
    _write_text(request.artifact_dir / "source-sha", f"{source_sha}\n")
    _write_text(request.artifact_dir / "rust-inputs-sha256", f"{rust_inputs_sha256}\n")
    _write_text(request.artifact_dir / "producer-ref", f"{_CURRENT_CHECKOUT_PROVENANCE}\n")
    _write_text(request.artifact_dir / "version", version)
    return _verify_bundle(
        request.artifact_dir,
        expected_producer_ref=_CURRENT_CHECKOUT_PROVENANCE,
        expected_source_sha=source_sha,
        expected_rust_inputs_sha256=rust_inputs_sha256,
        version_reader=version_reader,
    )


def stage_policy_candidate(
    request: PolicyCandidateRequest,
    *,
    version_reader: VersionReader = _read_binary_version,
) -> tuple[str, VerifiedArtifact]:
    """Stage and verify a cache candidate without granting publication authority."""
    source_sha = _require_source_sha(request.source_sha)
    rust_inputs_sha256 = _require_sha256(request.rust_inputs_sha256, name="Rust-input digest")
    artifact = _verify_bundle(
        request.artifact_dir,
        expected_producer_ref=_CURRENT_CHECKOUT_PROVENANCE,
        expected_source_sha=source_sha,
        expected_rust_inputs_sha256=rust_inputs_sha256,
        version_reader=version_reader,
    )
    producer_ref = candidate_producer_ref(event_name=request.event_name, ref=request.ref)

    _replace_directory(request.policy_dir, label="policy candidate directory")
    source_larch = request.artifact_dir / "larch"
    policy_larch = request.policy_dir / "larch"
    _copy_executable(source_larch, policy_larch)
    _copy_regular_file(request.artifact_dir / "larch.sha256", request.policy_dir / "larch.sha256")
    _write_text(request.policy_dir / "producer-ref", f"{producer_ref}\n")
    _write_text(request.policy_dir / "source-sha", f"{source_sha}\n")
    _write_text(request.policy_dir / "rust-inputs-sha256", f"{rust_inputs_sha256}\n")
    _write_text(request.policy_dir / "version", artifact.version)
    staged = _verify_bundle(
        request.policy_dir,
        expected_producer_ref=producer_ref,
        expected_source_sha=source_sha,
        expected_rust_inputs_sha256=rust_inputs_sha256,
        version_reader=version_reader,
    )
    if staged.sha256 != artifact.sha256:
        raise CandidateError("staged policy executable checksum does not match integration artifact")
    return producer_ref, staged


def candidate_producer_ref(*, event_name: str, ref: str) -> str:
    """Return a fixed provenance label; arbitrary refs never enter the cache."""
    if event_name == "push" and ref == _TRUSTED_MAIN_PROVENANCE:
        return _TRUSTED_MAIN_PROVENANCE
    return _CURRENT_CHECKOUT_PROVENANCE


def prepare_integration_artifact_main(argv: list[str]) -> int:
    """CLI entrypoint for the coverage action's integration-artifact writer."""
    parser = argparse.ArgumentParser(prog="cli.py ci prepare-rust-integration-artifact")
    _ = parser.add_argument("--coverage-larch", required=True)
    _ = parser.add_argument("--artifact-dir", required=True)
    _ = parser.add_argument("--source-sha", required=True)
    _ = parser.add_argument("--rust-inputs-sha256", required=True)
    args = parser.parse_args(argv)
    request = IntegrationArtifactRequest(
        coverage_larch=Path(str(args.coverage_larch)),
        artifact_dir=Path(str(args.artifact_dir)),
        source_sha=str(args.source_sha),
        rust_inputs_sha256=str(args.rust_inputs_sha256),
    )
    try:
        _ = prepare_integration_artifact(request)
    except CandidateError as exc:
        print(f"Rust integration artifact preparation failed: {exc}", file=sys.stderr)
        return 1
    return 0


def stage_policy_candidate_main(argv: list[str]) -> int:
    """CLI entrypoint for rust-full's post-prune candidate stage."""
    parser = argparse.ArgumentParser(prog="cli.py ci stage-rust-policy-candidate")
    _ = parser.add_argument("--artifact-dir", required=True)
    _ = parser.add_argument("--policy-dir", required=True)
    _ = parser.add_argument("--event-name", required=True)
    _ = parser.add_argument("--ref", required=True)
    _ = parser.add_argument("--source-sha", required=True)
    _ = parser.add_argument("--rust-inputs-sha256", required=True)
    args = parser.parse_args(argv)
    request = PolicyCandidateRequest(
        artifact_dir=Path(str(args.artifact_dir)),
        policy_dir=Path(str(args.policy_dir)),
        event_name=str(args.event_name),
        ref=str(args.ref),
        source_sha=str(args.source_sha),
        rust_inputs_sha256=str(args.rust_inputs_sha256),
    )
    try:
        _ = stage_policy_candidate(request)
    except CandidateError as exc:
        print(f"Rust policy candidate staging failed: {exc}", file=sys.stderr)
        return 1
    return 0


def _verify_bundle(
    directory: Path,
    *,
    expected_producer_ref: str,
    expected_source_sha: str,
    expected_rust_inputs_sha256: str,
    version_reader: VersionReader,
) -> VerifiedArtifact:
    _ = _require_regular_directory(directory, label="executable bundle directory")
    larch = _require_regular_file(directory / "larch", label="bundle executable")
    _require_executable(larch, label="bundle executable")
    checksum = _read_checksum(directory / "larch.sha256")
    actual_checksum = _sha256_file(larch)
    if checksum != actual_checksum:
        raise CandidateError("bundle executable checksum verification failed")
    _require_metadata(directory / "producer-ref", expected_producer_ref, label="producer provenance")
    _require_metadata(directory / "source-sha", expected_source_sha, label="source SHA")
    _require_metadata(directory / "rust-inputs-sha256", expected_rust_inputs_sha256, label="Rust-input digest")
    version = _read_text(directory / "version", label="bundle version")
    if not version.strip():
        raise CandidateError("bundle version is empty")
    if version_reader(larch) != version:
        raise CandidateError("bundle executable version verification failed")
    return VerifiedArtifact(sha256=checksum, version=version)


def _require_source_sha(value: str) -> str:
    if _SOURCE_SHA_RE.fullmatch(value) is None:
        raise CandidateError("source SHA is invalid")
    return value


def _require_sha256(value: str, *, name: str) -> str:
    if _SHA256_RE.fullmatch(value) is None:
        raise CandidateError(f"{name} is invalid")
    return value


def _replace_directory(path: Path, *, label: str) -> None:
    _ = _require_regular_directory(path.parent, label=f"{label} parent")
    if path.exists() or path.is_symlink():
        details = _lstat(path, label=label)
        if stat.S_ISLNK(details.st_mode) or not stat.S_ISDIR(details.st_mode):
            raise CandidateError(f"{label} is not a regular directory")
        try:
            shutil.rmtree(path)
        except OSError as exc:
            raise CandidateError(f"could not remove {label}") from exc
    try:
        path.mkdir(mode=0o755)
    except OSError as exc:
        raise CandidateError(f"could not create {label}") from exc


def _require_regular_directory(path: Path, *, label: str) -> Path:
    details = _lstat(path, label=label)
    if stat.S_ISLNK(details.st_mode) or not stat.S_ISDIR(details.st_mode):
        raise CandidateError(f"{label} is not a regular directory")
    return path


def _require_regular_file(path: Path, *, label: str) -> Path:
    details = _lstat(path, label=label)
    if stat.S_ISLNK(details.st_mode) or not stat.S_ISREG(details.st_mode):
        raise CandidateError(f"{label} is not a regular file")
    return path


def _lstat(path: Path, *, label: str) -> os.stat_result:
    try:
        return path.lstat()
    except OSError as exc:
        raise CandidateError(f"{label} is unavailable") from exc


def _require_executable(path: Path, *, label: str) -> None:
    details = _lstat(path, label=label)
    if not details.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
        raise CandidateError(f"{label} is not executable")


def _copy_executable(source: Path, destination: Path) -> None:
    _copy_regular_file(source, destination)
    try:
        destination.chmod(0o755)
    except OSError as exc:
        raise CandidateError("could not mark executable bundle file executable") from exc


def _copy_regular_file(source: Path, destination: Path) -> None:
    _ = _require_regular_file(source, label="source bundle file")
    try:
        _ = shutil.copyfile(source, destination, follow_symlinks=False)
    except OSError as exc:
        raise CandidateError("could not copy bundle file") from exc


def _write_text(path: Path, value: str) -> None:
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            _ = stream.write(value)
    except OSError as exc:
        raise CandidateError("could not write bundle metadata") from exc


def _read_checksum(path: Path) -> str:
    value = _read_text(path, label="bundle checksum")
    match = _CHECKSUM_RE.fullmatch(value)
    if match is None:
        raise CandidateError("bundle checksum has an invalid format")
    return match.group(1)


def _require_metadata(path: Path, expected: str, *, label: str) -> None:
    if _read_text(path, label=label) != f"{expected}\n":
        raise CandidateError(f"{label} verification failed")


def _read_text(path: Path, *, label: str) -> str:
    _ = _require_regular_file(path, label=label)
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CandidateError(f"could not read {label}") from exc


def _sha256_file(path: Path) -> str:
    _ = _require_regular_file(path, label="bundle executable")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(_HASH_CHUNK_BYTES):
                digest.update(chunk)
    except OSError as exc:
        raise CandidateError("could not hash bundle executable") from exc
    return digest.hexdigest()
