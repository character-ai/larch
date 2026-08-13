"""Stage and verify merge-group artifacts for trusted main cache publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast


_CACHE_CLASS_RE: Final = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_CACHE_KEY_RE: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,511}$")
_ARTIFACT_NAME_RE: Final = re.compile(r"^main-cache-[a-z][a-z0-9-]{0,63}-candidate$")
# Cargo's registry contains package build metadata and generated source names,
# so a cache payload cannot use a fragile crate-name filename allowlist. The
# security boundary is structural instead: every member stays below `payload`,
# each component is nonempty and not `.` or `..`, and portable path separators,
# control characters, and Windows-reserved filename characters are refused.
_MEMBER_PATH_RE: Final = re.compile(
    r"^payload/"
    r'(?:(?!\.{1,2}(?:/|$))[^/\x00-\x1f\x7f\\:*?"<>|]+)'
    r'(?:/(?:(?!\.{1,2}(?:/|$))[^/\x00-\x1f\x7f\\:*?"<>|]+))*$'
)
_PRODUCER_REF_RE: Final = re.compile(r"^refs/heads/gh-readonly-queue/main/[A-Za-z0-9._/-]+$")
_SHA256_RE: Final = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_NAME_RE: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_SOURCE_SHA_RE: Final = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_MANIFEST_FILENAME: Final = "manifest.json"
_PAYLOAD_DIRECTORY: Final = "payload"
_SCHEMA_VERSION: Final = 2
_HASH_CHUNK_BYTES: Final = 1024 * 1024
# Cargo's registry cache produces a manifest above 4 MiB on a clean, full
# Rust lane. Keep the untrusted-artifact parser bounded while allowing the
# reviewed registry inventory and its per-file integrity records.
_MAX_MANIFEST_BYTES: Final = 32 * 1024 * 1024
_MAX_FILE_MODE: Final = 0o777
# Keep untrusted timestamps inside the signed nanosecond range accepted by
# common runner filesystems and Python's descriptor-based os.utime boundary.
_MAX_MTIME_NS: Final = (1 << 63) - 1


class CandidateError(ValueError):
    """A cache-publication candidate does not meet its integrity contract."""


@dataclass(frozen=True)
class CandidateSource:
    """One named regular file or directory included in a candidate payload."""

    name: str
    path: Path


@dataclass(frozen=True)
class CandidateMember:
    """A content-addressed regular file inside a staged payload."""

    mode: int
    mtime_ns: int
    path: str
    sha256: str
    size: int


@dataclass(frozen=True)
class CandidateRequest:
    """Inputs that bind a staged artifact to one cache class and producer."""

    artifact_name: str
    cache_class: str
    cache_key: str
    candidate_dir: Path
    maximum_bytes: int
    producer_event: str
    producer_job: str
    producer_ref: str
    source_sha: str
    sources: tuple[CandidateSource, ...]
    tool_versions: dict[str, str]


@dataclass(frozen=True)
class CandidateContract:
    """The publisher's exact identity and tool-version contract for a candidate."""

    artifact_name: str
    cache_class: str
    cache_key: str
    maximum_bytes: int
    producer_job: str
    source_sha: str
    expected_tool_versions: dict[str, str]


@dataclass(frozen=True)
class VerifiedCandidate:
    """Metadata proven before a publisher may save the payload to a cache."""

    artifact_name: str
    artifact_sha256: str
    cache_class: str
    cache_key: str
    key_input_digest: str
    members: tuple[CandidateMember, ...]
    maximum_bytes: int
    producer_event: str
    producer_job: str
    producer_ref: str
    source_sha: str
    total_bytes: int
    tool_versions: dict[str, str]


def stage_candidate(request: CandidateRequest) -> VerifiedCandidate:
    """Copy and manifest a regular-file candidate without granting save authority."""
    _validate_stage_request(request)
    tool_versions = _validated_tool_versions(request.tool_versions, label="candidate tool versions")
    _create_empty_directory(request.candidate_dir, label="candidate directory")
    payload = request.candidate_dir / _PAYLOAD_DIRECTORY
    _create_empty_directory(payload, label="candidate payload")
    for source in request.sources:
        _copy_source(source.path, payload / source.name, label=f"candidate source {source.name}")

    members = _collect_members(payload)
    total_bytes = sum(member.size for member in members)
    if request.maximum_bytes > 0 and total_bytes > request.maximum_bytes:
        raise CandidateError(
            f"candidate exceeds its maximum size: {total_bytes} > {request.maximum_bytes}"
        )

    manifest: dict[str, object] = {
        "artifact_name": request.artifact_name,
        "artifact_sha256": _artifact_sha256(members),
        "cache_class": request.cache_class,
        "cache_key": request.cache_key,
        "key_input_digest": _sha256_text(request.cache_key),
        "maximum_bytes": request.maximum_bytes,
        "members": [
            {
                "mode": member.mode,
                "mtime_ns": member.mtime_ns,
                "path": member.path,
                "sha256": member.sha256,
                "size": member.size,
            }
            for member in members
        ],
        "producer_event": request.producer_event,
        "producer_job": request.producer_job,
        "producer_ref": request.producer_ref,
        "schema_version": _SCHEMA_VERSION,
        "source_sha": request.source_sha,
        "total_bytes": total_bytes,
        "tool_versions": tool_versions,
    }
    _write_manifest(request.candidate_dir / _MANIFEST_FILENAME, manifest)
    return verify_candidate(
        candidate_dir=request.candidate_dir,
        contract=CandidateContract(
            artifact_name=request.artifact_name,
            cache_class=request.cache_class,
            cache_key=request.cache_key,
            maximum_bytes=request.maximum_bytes,
            producer_job=request.producer_job,
            source_sha=request.source_sha,
            expected_tool_versions=tool_versions,
        ),
    )


def verify_candidate(
    *,
    candidate_dir: Path,
    contract: CandidateContract,
) -> VerifiedCandidate:
    """Verify an untrusted merge-group artifact before it reaches a cache."""
    expected_versions = _validate_contract(contract)
    _ = _require_regular_directory(candidate_dir, label="candidate directory")
    _verify_candidate_root(candidate_dir)
    manifest = _read_manifest(candidate_dir / _MANIFEST_FILENAME)
    _require_manifest_shape(manifest)
    verified = _parse_verified_manifest(manifest)
    _require_manifest_contract(verified, contract, expected_versions)
    actual_members = _collect_members(candidate_dir / _PAYLOAD_DIRECTORY)
    if not _members_match_content(actual_members, verified.members):
        raise CandidateError("candidate payload members do not match its manifest")
    total_bytes = sum(member.size for member in verified.members)
    if total_bytes != verified.total_bytes:
        raise CandidateError("candidate payload size does not match its manifest")
    if contract.maximum_bytes > 0 and total_bytes > contract.maximum_bytes:
        raise CandidateError("candidate payload exceeds its size bound")
    return verified


def promote_candidate(
    *,
    candidate_dir: Path,
    output_dir: Path,
    contract: CandidateContract,
) -> VerifiedCandidate:
    """Validate an artifact, then copy its payload to a new publication directory."""
    verified = verify_candidate(
        candidate_dir=candidate_dir,
        contract=contract,
    )
    _create_empty_directory(output_dir, label="publication directory")
    _copy_payload_contents(candidate_dir / _PAYLOAD_DIRECTORY, output_dir)
    _reject_tree_symlinks(output_dir)
    _restore_member_metadata(output_dir, verified.members)
    _reject_tree_symlinks(output_dir)
    return verified


def stage_main_cache_candidate_main(argv: list[str]) -> int:
    """CLI entrypoint used by merge-group producer jobs."""
    parser = _stage_parser()
    args = parser.parse_args(argv)
    try:
        request = CandidateRequest(
            artifact_name=str(args.artifact_name),
            cache_class=str(args.cache_class),
            cache_key=str(args.cache_key),
            candidate_dir=Path(str(args.candidate_dir)),
            maximum_bytes=_parse_maximum_bytes(str(args.maximum_bytes)),
            producer_event=str(args.producer_event),
            producer_job=str(args.producer_job),
            producer_ref=str(args.producer_ref),
            source_sha=str(args.source_sha),
            sources=tuple(_parse_source(value) for value in args.source),
            tool_versions=_parse_tool_versions(args.tool_version),
        )
        verified = stage_candidate(request)
    except CandidateError as exc:
        print(f"Main cache candidate staging failed: {exc}", file=sys.stderr)
        return 1
    print(f"CACHE_CLASS={verified.cache_class}")
    print(f"TOTAL_BYTES={verified.total_bytes}")
    return 0


def verify_main_cache_candidate_main(argv: list[str]) -> int:
    """CLI entrypoint used by the trusted main publication workflow."""
    parser = _verify_parser()
    args = parser.parse_args(argv)
    try:
        verified = promote_candidate(
            candidate_dir=Path(str(args.candidate_dir)),
            output_dir=Path(str(args.output_dir)),
            contract=CandidateContract(
                artifact_name=str(args.artifact_name),
                cache_class=str(args.cache_class),
                cache_key=str(args.cache_key),
                maximum_bytes=_parse_maximum_bytes(str(args.maximum_bytes)),
                producer_job=str(args.producer_job),
                source_sha=str(args.source_sha),
                expected_tool_versions=_parse_tool_versions(args.expected_tool_version),
            ),
        )
    except CandidateError as exc:
        print(f"Main cache candidate verification failed: {exc}", file=sys.stderr)
        return 1
    print(f"CACHE_CLASS={verified.cache_class}")
    print(f"TOTAL_BYTES={verified.total_bytes}")
    return 0


def _stage_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cli.py ci stage-main-cache-candidate")
    _add_common_candidate_arguments(parser)
    _ = parser.add_argument("--candidate-dir", required=True)
    _ = parser.add_argument("--producer-event", required=True)
    _ = parser.add_argument("--producer-ref", required=True)
    _ = parser.add_argument("--source", action="append", required=True)
    _ = parser.add_argument("--tool-version", action="append", default=[])
    return parser


def _verify_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cli.py ci verify-main-cache-candidate")
    _add_common_candidate_arguments(parser)
    _ = parser.add_argument("--candidate-dir", required=True)
    _ = parser.add_argument("--output-dir", required=True)
    _ = parser.add_argument("--expected-tool-version", action="append", required=True)
    return parser


def _add_common_candidate_arguments(parser: argparse.ArgumentParser) -> None:
    _ = parser.add_argument("--artifact-name", required=True)
    _ = parser.add_argument("--cache-class", required=True)
    _ = parser.add_argument("--cache-key", required=True)
    _ = parser.add_argument("--maximum-bytes", required=True)
    _ = parser.add_argument("--producer-job", required=True)
    _ = parser.add_argument("--source-sha", required=True)


def _parse_source(value: str) -> CandidateSource:
    name, separator, raw_path = value.partition("=")
    if separator != "=" or not raw_path:
        raise CandidateError("candidate source must use NAME=PATH")
    if _SOURCE_NAME_RE.fullmatch(name) is None:
        raise CandidateError("candidate source name is invalid")
    return CandidateSource(name=name, path=Path(raw_path))


def _parse_maximum_bytes(value: str) -> int:
    if not value.isdigit():
        raise CandidateError("maximum bytes is invalid")
    return int(value)


def _parse_tool_versions(values: list[str]) -> dict[str, str]:
    tool_versions: dict[str, str] = {}
    for value in values:
        name, separator, version = value.partition("=")
        if separator != "=" or _SOURCE_NAME_RE.fullmatch(name) is None or not version:
            raise CandidateError("candidate tool version must use NAME=VALUE")
        if "\n" in version or "\r" in version:
            raise CandidateError("candidate tool version is invalid")
        if name in tool_versions:
            raise CandidateError("candidate tool version names must be unique")
        tool_versions[name] = version
    return dict(sorted(tool_versions.items()))


def _validate_stage_request(request: CandidateRequest) -> None:
    _require_artifact_name(request.artifact_name)
    _require_cache_class(request.cache_class)
    _require_cache_key(request.cache_key)
    _require_non_negative_int(request.maximum_bytes, label="maximum bytes")
    _require_producer_job(request.producer_job)
    _require_source_sha(request.source_sha)
    if request.producer_event != "merge_group":
        raise CandidateError("candidate producer event must be merge_group")
    if _PRODUCER_REF_RE.fullmatch(request.producer_ref) is None:
        raise CandidateError("candidate producer ref must be a merge-queue ref")
    if not request.sources:
        raise CandidateError("candidate has no payload sources")
    source_names = tuple(source.name for source in request.sources)
    if len(set(source_names)) != len(source_names):
        raise CandidateError("candidate source names must be unique")
    _ = _validated_tool_versions(request.tool_versions, label="candidate tool versions")


def _validate_contract(contract: CandidateContract) -> dict[str, str]:
    _require_artifact_name(contract.artifact_name)
    _require_cache_class(contract.cache_class)
    _require_cache_key(contract.cache_key)
    _require_non_negative_int(contract.maximum_bytes, label="maximum bytes")
    _require_producer_job(contract.producer_job)
    _require_source_sha(contract.source_sha)
    return _validated_tool_versions(
        contract.expected_tool_versions, label="expected candidate tool versions"
    )


def _require_artifact_name(value: str) -> None:
    if _ARTIFACT_NAME_RE.fullmatch(value) is None:
        raise CandidateError("candidate artifact name is invalid")


def _require_cache_class(value: str) -> None:
    if _CACHE_CLASS_RE.fullmatch(value) is None:
        raise CandidateError("cache class is invalid")


def _require_cache_key(value: str) -> None:
    if _CACHE_KEY_RE.fullmatch(value) is None:
        raise CandidateError("cache key is invalid")


def _require_non_negative_int(value: int, *, label: str) -> None:
    if value < 0:
        raise CandidateError(f"{label} is invalid")


def _require_producer_job(value: str) -> None:
    if not value or "\n" in value or "\r" in value:
        raise CandidateError("producer job is invalid")


def _require_source_sha(value: str) -> None:
    if _SOURCE_SHA_RE.fullmatch(value) is None:
        raise CandidateError("source SHA is invalid")


def _require_sha256(value: str, *, label: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise CandidateError(f"{label} is invalid")


def _create_empty_directory(path: Path, *, label: str) -> None:
    _ = _require_regular_directory(path.parent, label=f"{label} parent")
    if path.exists() or path.is_symlink():
        raise CandidateError(f"{label} already exists")
    try:
        path.mkdir(mode=0o755)
    except OSError as exc:
        raise CandidateError(f"could not create {label}") from exc


def _copy_source(source: Path, destination: Path, *, label: str) -> None:
    source_status = _lstat(source, label=label)
    if stat.S_ISLNK(source_status.st_mode):
        raise CandidateError(f"{label} is a symlink")
    if stat.S_ISREG(source_status.st_mode):
        _copy_regular_file(source, destination, label=label)
        return
    if not stat.S_ISDIR(source_status.st_mode):
        raise CandidateError(f"{label} is not a regular file or directory")
    _copy_directory(source, destination, label=label)


def _copy_directory(source: Path, destination: Path, *, label: str) -> None:
    try:
        destination.mkdir(mode=stat.S_IMODE(_lstat(source, label=label).st_mode))
    except OSError as exc:
        raise CandidateError(f"could not create {label} destination") from exc
    for child in sorted(source.iterdir(), key=lambda item: item.name):
        _copy_source(child, destination / child.name, label=label)


def _copy_payload_contents(source: Path, destination: Path) -> None:
    _ = _require_regular_directory(source, label="verified candidate payload")
    for child in sorted(source.iterdir(), key=lambda item: item.name):
        _copy_source(child, destination / child.name, label="verified candidate payload")


def _copy_regular_file(source: Path, destination: Path, *, label: str) -> None:
    status = _lstat(source, label=label)
    if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
        raise CandidateError(f"{label} is not a regular file")
    try:
        _ = shutil.copy2(source, destination, follow_symlinks=False)
    except OSError as exc:
        raise CandidateError(f"could not copy {label}") from exc


def _collect_members(payload: Path) -> tuple[CandidateMember, ...]:
    _ = _require_regular_directory(payload, label="candidate payload")
    _reject_tree_symlinks(payload)
    members: list[CandidateMember] = []
    for path in _walk_regular_files(payload):
        relative = path.relative_to(payload.parent).as_posix()
        if _MEMBER_PATH_RE.fullmatch(relative) is None:
            raise CandidateError("candidate payload path is invalid")
        status = _lstat(path, label="candidate payload member")
        mtime_ns = _validated_mtime_ns(status.st_mtime_ns)
        members.append(
            CandidateMember(
                mode=stat.S_IMODE(status.st_mode),
                mtime_ns=mtime_ns,
                path=relative,
                sha256=_sha256_file(path),
                size=status.st_size,
            )
        )
    return tuple(sorted(members, key=lambda member: member.path))


def _walk_regular_files(directory: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for child in sorted(directory.iterdir(), key=lambda item: item.name):
        status = _lstat(child, label="candidate payload entry")
        if stat.S_ISLNK(status.st_mode):
            raise CandidateError("candidate payload contains a symlink")
        if stat.S_ISREG(status.st_mode):
            files.append(child)
            continue
        if stat.S_ISDIR(status.st_mode):
            files.extend(_walk_regular_files(child))
            continue
        raise CandidateError("candidate payload contains a non-regular entry")
    return tuple(files)


def _reject_tree_symlinks(directory: Path) -> None:
    _ = _walk_regular_files(directory)


def _verify_candidate_root(directory: Path) -> None:
    _reject_tree_symlinks(directory)
    for child in directory.iterdir():
        if child.name == _MANIFEST_FILENAME:
            status = _lstat(child, label="candidate directory")
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
                raise CandidateError("candidate directory manifest is not a regular file")
            continue
        if child.name == _PAYLOAD_DIRECTORY:
            continue
        raise CandidateError("candidate directory contains an unexpected entry")


def _write_manifest(path: Path, manifest: dict[str, object]) -> None:
    try:
        with path.open("x", encoding="utf-8") as handle:
            _ = handle.write(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
    except OSError as exc:
        raise CandidateError("could not write candidate manifest") from exc


def _read_manifest(path: Path) -> dict[str, object]:
    status = _lstat(path, label="candidate manifest")
    if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
        raise CandidateError("candidate manifest is not a regular file")
    if status.st_size > _MAX_MANIFEST_BYTES:
        raise CandidateError("candidate manifest exceeds its size limit")
    try:
        raw = path.read_text(encoding="utf-8")
        parsed: object = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateError("candidate manifest is unreadable") from exc
    if not isinstance(parsed, dict):
        raise CandidateError("candidate manifest is not an object")
    # json.loads returns an unparameterized dict; JSON object keys are strings.
    return cast("dict[str, object]", parsed)


def _require_manifest_shape(manifest: dict[str, object]) -> None:
    required = {
        "artifact_name",
        "artifact_sha256",
        "cache_class",
        "cache_key",
        "key_input_digest",
        "maximum_bytes",
        "members",
        "producer_event",
        "producer_job",
        "producer_ref",
        "schema_version",
        "source_sha",
        "total_bytes",
        "tool_versions",
    }
    if set(manifest) != required:
        raise CandidateError("candidate manifest has an unexpected schema")
    if manifest.get("schema_version") != _SCHEMA_VERSION:
        raise CandidateError("candidate manifest has an unsupported schema version")
    _ = _parse_manifest_tool_versions(manifest)


def _require_manifest_string(manifest: dict[str, object], key: str) -> str:
    value = manifest.get(key)
    if not isinstance(value, str):
        raise CandidateError(f"candidate manifest {key} is invalid")
    return value


def _require_manifest_int(manifest: dict[str, object], key: str) -> int:
    value = manifest.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise CandidateError(f"candidate manifest {key} is invalid")
    return value


def _parse_verified_manifest(manifest: dict[str, object]) -> VerifiedCandidate:
    artifact_name = _require_manifest_string(manifest, "artifact_name")
    artifact_sha256 = _require_manifest_string(manifest, "artifact_sha256")
    cache_class = _require_manifest_string(manifest, "cache_class")
    cache_key = _require_manifest_string(manifest, "cache_key")
    key_input_digest = _require_manifest_string(manifest, "key_input_digest")
    producer_event = _require_manifest_string(manifest, "producer_event")
    producer_job = _require_manifest_string(manifest, "producer_job")
    producer_ref = _require_manifest_string(manifest, "producer_ref")
    source_sha = _require_manifest_string(manifest, "source_sha")
    maximum_bytes = _require_manifest_int(manifest, "maximum_bytes")
    total_bytes = _require_manifest_int(manifest, "total_bytes")
    _require_artifact_name(artifact_name)
    _require_sha256(artifact_sha256, label="candidate artifact digest")
    _require_cache_class(cache_class)
    _require_cache_key(cache_key)
    _require_sha256(key_input_digest, label="candidate key-input digest")
    if key_input_digest != _sha256_text(cache_key):
        raise CandidateError("candidate cache key identity does not match")
    _require_source_sha(source_sha)
    _require_non_negative_int(maximum_bytes, label="candidate maximum bytes")
    _require_non_negative_int(total_bytes, label="candidate total bytes")
    members = _parse_members(manifest)
    if _artifact_sha256(members) != artifact_sha256:
        raise CandidateError("candidate artifact digest does not match its manifest")
    return VerifiedCandidate(
        artifact_name=artifact_name,
        artifact_sha256=artifact_sha256,
        cache_class=cache_class,
        cache_key=cache_key,
        key_input_digest=key_input_digest,
        members=members,
        maximum_bytes=maximum_bytes,
        producer_event=producer_event,
        producer_job=producer_job,
        producer_ref=producer_ref,
        source_sha=source_sha,
        total_bytes=total_bytes,
        tool_versions=_parse_manifest_tool_versions(manifest),
    )


def _require_manifest_contract(
    verified: VerifiedCandidate,
    contract: CandidateContract,
    expected_versions: dict[str, str],
) -> None:
    if verified.artifact_name != contract.artifact_name:
        raise CandidateError("candidate artifact name does not match")
    if verified.cache_class != contract.cache_class:
        raise CandidateError("candidate cache class does not match the requested cache class")
    if verified.cache_key != contract.cache_key:
        raise CandidateError("candidate cache key identity does not match")
    if verified.producer_event != "merge_group":
        raise CandidateError("candidate producer event is not merge_group")
    if verified.producer_job != contract.producer_job:
        raise CandidateError("candidate producer job does not match")
    if _PRODUCER_REF_RE.fullmatch(verified.producer_ref) is None:
        raise CandidateError("candidate producer ref is not a merge-queue ref")
    if verified.source_sha != contract.source_sha:
        raise CandidateError("candidate source SHA does not match the publisher SHA")
    if verified.maximum_bytes != contract.maximum_bytes:
        raise CandidateError("candidate size bound does not match the publisher contract")
    if verified.tool_versions != expected_versions:
        raise CandidateError("candidate tool versions do not match the publisher contract")


def _parse_members(manifest: dict[str, object]) -> tuple[CandidateMember, ...]:
    raw_members = manifest.get("members")
    if not isinstance(raw_members, list) or not raw_members:
        raise CandidateError("candidate manifest members are invalid")
    members: list[CandidateMember] = []
    manifest_members = cast("list[object]", raw_members)
    for raw_member_value in manifest_members:
        if not isinstance(raw_member_value, dict):
            raise CandidateError("candidate manifest member has an unexpected schema")
        # JSON object keys are strings; the exact schema is checked below.
        raw_member = cast("dict[str, object]", raw_member_value)
        if set(raw_member) != {
            "mode",
            "mtime_ns",
            "path",
            "sha256",
            "size",
        }:
            raise CandidateError("candidate manifest member has an unexpected schema")
        mode = raw_member.get("mode")
        mtime_ns = raw_member.get("mtime_ns")
        path = raw_member.get("path")
        sha256 = raw_member.get("sha256")
        size = raw_member.get("size")
        if not isinstance(mode, int) or isinstance(mode, bool) or mode < 0 or mode > _MAX_FILE_MODE:
            raise CandidateError("candidate manifest member mode is invalid")
        if not isinstance(path, str) or _MEMBER_PATH_RE.fullmatch(path) is None:
            raise CandidateError("candidate manifest member path is invalid")
        if not isinstance(sha256, str):
            raise CandidateError("candidate manifest member checksum is invalid")
        _require_sha256(sha256, label="candidate member checksum")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise CandidateError("candidate manifest member size is invalid")
        members.append(
            CandidateMember(
                mode=mode,
                mtime_ns=_validated_mtime_ns(mtime_ns),
                path=path,
                sha256=sha256,
                size=size,
            )
        )
    paths = tuple(member.path for member in members)
    if tuple(sorted(paths)) != paths or len(set(paths)) != len(paths):
        raise CandidateError("candidate manifest member paths are not unique and sorted")
    return tuple(members)


def _members_match_content(
    actual_members: tuple[CandidateMember, ...], expected_members: tuple[CandidateMember, ...]
) -> bool:
    # Artifact transport may rewrite modes and mtimes. The manifest digest binds
    # their declared values; promotion restores them after content verification.
    return tuple(
        (member.path, member.sha256, member.size) for member in actual_members
    ) == tuple((member.path, member.sha256, member.size) for member in expected_members)


def _validated_mtime_ns(value: object) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        or value > _MAX_MTIME_NS
    ):
        raise CandidateError("candidate manifest member mtime_ns is invalid")
    return value


def _restore_member_metadata(output_dir: Path, members: tuple[CandidateMember, ...]) -> None:
    for member in members:
        relative = Path(member.path).relative_to(_PAYLOAD_DIRECTORY)
        path = output_dir / relative
        before = _lstat(path, label="promoted candidate member")
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise CandidateError("promoted candidate member is not a regular file")
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            with ExitStack() as stack:
                descriptor = os.open(path, flags)
                _ = stack.callback(os.close, descriptor)
                opened = os.fstat(descriptor)
                current = _lstat(path, label="promoted candidate member")
                if (
                    not stat.S_ISREG(opened.st_mode)
                    or stat.S_ISLNK(current.st_mode)
                    or not stat.S_ISREG(current.st_mode)
                    or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
                    or (current.st_dev, current.st_ino)
                    != (opened.st_dev, opened.st_ino)
                ):
                    raise CandidateError(
                        "promoted candidate member changed while opening"
                    )
                os.fchmod(descriptor, member.mode)
                os.utime(
                    descriptor,
                    ns=(opened.st_atime_ns, member.mtime_ns),
                )
                restored = os.fstat(descriptor)
                visible = _lstat(path, label="promoted candidate member")
                if (
                    stat.S_IMODE(restored.st_mode) != member.mode
                    or restored.st_mtime_ns != member.mtime_ns
                    or stat.S_ISLNK(visible.st_mode)
                    or not stat.S_ISREG(visible.st_mode)
                    or (visible.st_dev, visible.st_ino)
                    != (restored.st_dev, restored.st_ino)
                    or stat.S_IMODE(visible.st_mode) != member.mode
                    or visible.st_mtime_ns != member.mtime_ns
                ):
                    raise CandidateError(
                        "candidate member metadata was not restored exactly"
                    )
        except (OSError, OverflowError) as exc:
            raise CandidateError("could not restore candidate member metadata") from exc


def _parse_manifest_tool_versions(manifest: dict[str, object]) -> dict[str, str]:
    raw_tool_versions = manifest.get("tool_versions")
    return _validated_tool_versions(raw_tool_versions, label="candidate manifest tool versions")


def _validated_tool_versions(raw_tool_versions: object, *, label: str) -> dict[str, str]:
    if not isinstance(raw_tool_versions, dict) or not raw_tool_versions:
        raise CandidateError(f"{label} are invalid")
    tool_versions: dict[str, str] = {}
    raw_versions = cast("dict[str, object]", raw_tool_versions)
    for raw_name, raw_version in raw_versions.items():
        if _SOURCE_NAME_RE.fullmatch(raw_name) is None:
            raise CandidateError(f"{label} name is invalid")
        if not isinstance(raw_version, str) or not raw_version or "\n" in raw_version or "\r" in raw_version:
            raise CandidateError(f"{label} value is invalid")
        tool_versions[raw_name] = raw_version
    if tuple(tool_versions) != tuple(sorted(tool_versions)):
        raise CandidateError(f"{label} are not sorted")
    return tool_versions


def _require_regular_directory(path: Path, *, label: str) -> Path:
    status = _lstat(path, label=label)
    if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
        raise CandidateError(f"{label} is not a regular directory")
    return path


def _lstat(path: Path, *, label: str) -> os.stat_result:
    try:
        return path.lstat()
    except OSError as exc:
        raise CandidateError(f"{label} is unavailable") from exc


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(_HASH_CHUNK_BYTES):
                digest.update(chunk)
    except OSError as exc:
        raise CandidateError("candidate payload member is unreadable") from exc
    return digest.hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _artifact_sha256(members: tuple[CandidateMember, ...]) -> str:
    """Return the deterministic digest of a candidate payload's member contract."""
    payload = [
        {
            "mode": member.mode,
            "mtime_ns": member.mtime_ns,
            "path": member.path,
            "sha256": member.sha256,
            "size": member.size,
        }
        for member in members
    ]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
