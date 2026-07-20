"""Deterministic, versioned archive format for one sanitized run-log tree.

The archive contains regular files and explicit directories from a completed
staging tree plus ``archive-manifest.json``.  The manifest is canonical JSON
and records the normalized path, type, size, and SHA-256 digest of every
source-tree member.  It deliberately excludes itself, avoiding a recursive
digest while preserving an independently verifiable description of the run.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import stat
import tarfile
import tempfile
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO, cast

from larch import io as larch_io
from larch.core import config
from larch.report.run_log_batch import validate_run_id_slug


ARCHIVE_FORMAT: str = "larch-run-archive"
ARCHIVE_MANIFEST_NAME: str = "archive-manifest.json"
ARCHIVE_SCHEMA_VERSION: int = 1
_CHUNK_SIZE: int = 1024 * 1024
_SHA256_HEX_LENGTH: int = 64
_RESERVED_MEMBER_NAMES: frozenset[str] = frozenset({ARCHIVE_MANIFEST_NAME})
_MANIFEST_KEYS: frozenset[str] = frozenset(
    {"archive_format", "member_count", "members", "run_id", "schema_version", "skill"}
)
_MANIFEST_MEMBER_KEYS: frozenset[str] = frozenset({"kind", "path", "sha256", "size"})


@dataclass(frozen=True)
class ArchiveMember:
    """One normalized source-tree member represented in the archive."""

    path: str
    kind: str
    size: int
    sha256: str | None
    source: Path
    mode: int

    def manifest_record(self) -> dict[str, int | str | None]:
        return {
            "kind": self.kind,
            "path": self.path,
            "sha256": self.sha256,
            "size": self.size,
        }


@dataclass(frozen=True)
class RunArchiveManifest:
    """Versioned, canonical description of archived source-tree members."""

    skill: str
    run_id: str
    members: tuple[ArchiveMember, ...]

    def to_bytes(self) -> bytes:
        payload: dict[str, object] = {
            "archive_format": ARCHIVE_FORMAT,
            "member_count": len(self.members),
            "members": [member.manifest_record() for member in self.members],
            "run_id": self.run_id,
            "schema_version": ARCHIVE_SCHEMA_VERSION,
            "skill": self.skill,
        }
        return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


@dataclass(frozen=True)
class RunArchiveResult:
    """Paths and digests emitted by :func:`create_run_archive`."""

    archive_path: Path
    archive_sha256: str
    manifest_sha256: str
    member_count: int


@dataclass(frozen=True)
class ArchiveExtractionLimits:
    """Resource limits applied before and during archive extraction."""

    max_members: int = config.RUN_LOG_ARCHIVE_MAX_MEMBERS
    max_member_bytes: int = config.RUN_LOG_ARCHIVE_MAX_MEMBER_BYTES
    max_expanded_bytes: int = config.RUN_LOG_ARCHIVE_MAX_EXPANDED_BYTES
    max_compression_ratio: int = config.RUN_LOG_ARCHIVE_MAX_COMPRESSION_RATIO

    def validate(self) -> None:
        values: tuple[object, ...] = (self.max_members, self.max_member_bytes, self.max_expanded_bytes, self.max_compression_ratio)
        if any(type(value) is not int or value <= 0 for value in values):  # pylint: disable=unidiomatic-typecheck  # exact type rejects bool and non-integers
            raise ValueError("archive extraction limits must be positive integers")


@dataclass(frozen=True)
class ManifestMember:
    """Validated manifest metadata for one extracted tree member."""  # noqa: D204 - compact wire record keeps the leaf within its size bound
    path: str
    kind: str
    size: int
    sha256: str | None


@dataclass(frozen=True)
class ValidatedRunArchiveManifest:
    """Strictly parsed archive manifest ready for verification."""  # noqa: D204 - compact wire record keeps the leaf within its size bound
    skill: str
    run_id: str
    members: tuple[ManifestMember, ...]
    encoded: bytes


@dataclass(frozen=True)
class RunArchiveMaterializationResult:
    """Verified local run directory produced from one run archive."""

    run_dir: Path
    manifest_sha256: str
    member_count: int
    expanded_size: int


@dataclass(frozen=True)
class _ValidatedArchive:
    manifest: ValidatedRunArchiveManifest
    members: tuple[tarfile.TarInfo, ...]
    expanded_size: int


class _HashingReader:
    """Binary reader wrapper that records exactly the bytes tarfile consumes."""

    def __init__(self, handle: BinaryIO) -> None:
        self._handle = handle
        self._digest = hashlib.sha256()

    def read(self, size: int = -1) -> bytes:
        chunk: bytes = self._handle.read(size)
        self._digest.update(chunk)
        return chunk

    def hexdigest(self) -> str:
        return self._digest.hexdigest()


def _normalized_member_path(relative: Path) -> str:
    raw_parts: tuple[str, ...] = relative.parts
    if not raw_parts:
        raise ValueError("archive member path is empty")
    normalized_parts: list[str] = []
    for part in raw_parts:
        normalized: str = unicodedata.normalize("NFC", part)
        if not normalized or normalized in {".", ".."} or "/" in normalized or "\\" in normalized:
            raise ValueError(f"ambiguous archive member path: {relative}")
        try:
            _ = normalized.encode("utf-8", "strict")
        except UnicodeError as exc:
            raise ValueError(f"archive member path is not UTF-8 encodable: {relative}") from exc
        normalized_parts.append(normalized)
    name: str = str(PurePosixPath(*normalized_parts))
    if name in _RESERVED_MEMBER_NAMES:
        raise ValueError(f"archive member path is reserved: {name}")
    return name


def _normalized_file_mode(mode: int) -> int:
    return 0o755 if mode & 0o111 else 0o644


def _digest_regular_file(path: Path, *, root: Path, expected: os.stat_result) -> str:
    with _open_regular_member(path, root=root, expected=expected) as handle:
        digest = hashlib.sha256()
        while chunk := handle.read(_CHUNK_SIZE):
            digest.update(chunk)
    _assert_unchanged(path, expected=expected)
    return digest.hexdigest()


def _assert_unchanged(path: Path, *, expected: os.stat_result) -> None:
    current: os.stat_result = path.stat(follow_symlinks=False)
    if (
        current.st_dev,
        current.st_ino,
        current.st_size,
        current.st_mtime_ns,
    ) != (
        expected.st_dev,
        expected.st_ino,
        expected.st_size,
        expected.st_mtime_ns,
    ):
        raise OSError(f"archive source changed while reading: {path}")


def _open_regular_member(path: Path, *, root: Path, expected: os.stat_result) -> BinaryIO:
    _ = larch_io.validate_trusted_directory(path.parent, root=root)
    flags: int = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd: int = os.open(path, flags)
    try:
        opened: os.stat_result = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise OSError(f"unsupported archive member type: {path}")
        if (opened.st_dev, opened.st_ino, opened.st_size) != (
            expected.st_dev,
            expected.st_ino,
            expected.st_size,
        ):
            raise OSError(f"archive source changed while opening: {path}")
        return os.fdopen(fd, "rb")
    except OSError:
        os.close(fd)
        raise


def _collect_members(staging_root: Path) -> tuple[ArchiveMember, ...]:
    members: list[ArchiveMember] = []
    normalized_names: dict[str, str] = {}
    for directory, child_dirs, child_files in os.walk(staging_root, topdown=True, followlinks=False):
        directory_path: Path = Path(directory)
        _ = larch_io.validate_trusted_directory(directory_path, root=staging_root)
        child_dirs.sort()
        child_files.sort()
        for child_name in child_dirs:
            source: Path = directory_path / child_name
            entry: os.stat_result = source.stat(follow_symlinks=False)
            if not stat.S_ISDIR(entry.st_mode):
                raise OSError(f"unsupported archive member type: {source}")
            relative: Path = source.relative_to(staging_root)
            member_path: str = _normalized_member_path(relative)
            _add_member_name(member_path, normalized_names)
            members.append(ArchiveMember(member_path, "directory", 0, None, source, 0o755))
        for child_name in child_files:
            source = directory_path / child_name
            entry = source.stat(follow_symlinks=False)
            if not stat.S_ISREG(entry.st_mode):
                raise OSError(f"unsupported archive member type: {source}")
            relative = source.relative_to(staging_root)
            member_path = _normalized_member_path(relative)
            _add_member_name(member_path, normalized_names)
            digest: str = _digest_regular_file(source, root=staging_root, expected=entry)
            members.append(
                ArchiveMember(
                    member_path,
                    "file",
                    entry.st_size,
                    digest,
                    source,
                    _normalized_file_mode(entry.st_mode),
                )
            )
    return tuple(sorted(members, key=lambda member: member.path))


def _add_member_name(name: str, known_names: dict[str, str]) -> None:
    collision_key: str = name.casefold()
    previous: str | None = known_names.get(collision_key)
    if previous is not None:
        raise ValueError(f"ambiguous archive member path after Unicode normalization: {previous} and {name}")
    known_names[collision_key] = name


def _tar_info(*, name: str, size: int, mode: int, kind: bytes) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.type = kind
    info.size = size
    info.mode = mode
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    return info


def _add_manifest_member(*, archive: tarfile.TarFile, manifest_bytes: bytes) -> None:
    manifest_info: tarfile.TarInfo = _tar_info(
        name=ARCHIVE_MANIFEST_NAME,
        size=len(manifest_bytes),
        mode=0o644,
        kind=tarfile.REGTYPE,
    )
    archive.addfile(manifest_info, fileobj=_BytesReader(manifest_bytes))


def _write_archive(*, archive_path: Path, manifest: RunArchiveManifest, staging_root: Path) -> None:
    manifest_bytes: bytes = manifest.to_bytes()
    with tempfile.NamedTemporaryFile(
        dir=archive_path.parent,
        prefix=f".{archive_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        temporary_path: Path = Path(temporary.name)
        try:
            with gzip.GzipFile(
                filename="",
                mode="wb",
                fileobj=temporary,
                mtime=0,
                compresslevel=9,
            ) as compressed:
                with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                    manifest_written = False
                    for member in manifest.members:
                        if not manifest_written and member.path > ARCHIVE_MANIFEST_NAME:
                            _add_manifest_member(archive=archive, manifest_bytes=manifest_bytes)
                            manifest_written = True
                        if member.kind == "directory":
                            archive.addfile(
                                _tar_info(name=member.path, size=0, mode=member.mode, kind=tarfile.DIRTYPE)
                            )
                            continue
                        expected: os.stat_result = member.source.stat(follow_symlinks=False)
                        with _open_regular_member(member.source, root=staging_root, expected=expected) as handle:
                            reader = _HashingReader(handle)
                            archive.addfile(
                                _tar_info(name=member.path, size=member.size, mode=member.mode, kind=tarfile.REGTYPE),
                                fileobj=reader,
                            )
                            if reader.hexdigest() != member.sha256:
                                raise OSError(f"archive source changed while packaging: {member.source}")
                        _assert_unchanged(member.source, expected=expected)
                    if not manifest_written:
                        _add_manifest_member(archive=archive, manifest_bytes=manifest_bytes)
            temporary.flush()
            os.fsync(temporary.fileno())
            if archive_path.is_symlink():
                raise OSError(f"refusing symlinked archive destination: {archive_path}")
            _ = temporary_path.replace(archive_path)
        finally:
            temporary_path.unlink(missing_ok=True)


class _BytesReader:
    """Minimal deterministic byte reader for ``tarfile.addfile``."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._offset = 0

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._data) - self._offset
        chunk = self._data[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


def _sha256_file(path: Path) -> str:
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
    """Create ``<run-id>.tar.gz`` from one final, sanitized staging tree.

    The source tree is never modified.  Symlinks and every non-file,
    non-directory source entry are rejected before an archive is published.
    """
    if not validate_run_id_slug(skill):
        raise ValueError(f"invalid skill: {skill}")
    if not validate_run_id_slug(run_id):
        raise ValueError(f"invalid run-id: {run_id}")
    root: Path = larch_io.validate_trusted_directory(staging_root)
    requested_destination: Path = output_dir if output_dir.is_absolute() else Path.cwd() / output_dir
    try:
        _ = requested_destination.relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError("archive output directory must not be inside the staging tree")
    destination_dir: Path = larch_io.ensure_trusted_directory(output_dir)
    members: tuple[ArchiveMember, ...] = _collect_members(root)
    manifest = RunArchiveManifest(skill=skill, run_id=run_id, members=members)
    archive_path: Path = destination_dir / f"{run_id}.tar.gz"
    _write_archive(archive_path=archive_path, manifest=manifest, staging_root=root)
    return RunArchiveResult(
        archive_path=archive_path,
        archive_sha256=_sha256_file(archive_path),
        manifest_sha256=hashlib.sha256(manifest.to_bytes()).hexdigest(),
        member_count=len(members),
    )


def _canonical_input_member_path(raw_name: str, *, allow_manifest: bool = False) -> str:
    if not raw_name or raw_name.startswith("/") or "\\" in raw_name or "\0" in raw_name:
        raise ValueError(f"unsafe archive member path: {raw_name!r}")
    path = PurePosixPath(raw_name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe archive member path: {raw_name!r}")
    normalized_parts: tuple[str, ...] = tuple(unicodedata.normalize("NFC", part) for part in path.parts)
    canonical: str = str(PurePosixPath(*normalized_parts))
    if canonical != raw_name:
        raise ValueError(f"non-canonical archive member path: {raw_name!r}")
    if canonical in _RESERVED_MEMBER_NAMES and not allow_manifest:
        raise ValueError(f"archive member path is reserved: {canonical}")
    return canonical


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate archive manifest key: {key}")
        result[key] = value
    return result


def _validated_manifest_member(raw: object, *, limits: ArchiveExtractionLimits) -> ManifestMember:
    if not isinstance(raw, dict):
        raise TypeError("archive manifest member must be an object")
    record = cast("dict[str, object]", raw)
    if frozenset(record) != _MANIFEST_MEMBER_KEYS:
        raise ValueError("archive manifest member has invalid fields")
    raw_path: object = record["path"]
    raw_kind: object = record["kind"]
    raw_size: object = record["size"]
    raw_digest: object = record["sha256"]
    if not isinstance(raw_path, str):
        raise TypeError("archive manifest member path must be a string")
    path: str = _canonical_input_member_path(raw_path)
    if raw_kind not in {"directory", "file"}:
        raise ValueError(f"archive manifest member has invalid kind: {path}")
    if not isinstance(raw_size, int) or isinstance(raw_size, bool) or raw_size < 0:
        raise ValueError(f"archive manifest member has invalid size: {path}")
    if raw_size > limits.max_member_bytes:
        raise ValueError(f"archive member exceeds individual size limit: {path}")
    if raw_kind == "directory":
        if raw_size != 0 or raw_digest is not None:
            raise ValueError(f"archive directory manifest record is invalid: {path}")
        return ManifestMember(path=path, kind="directory", size=0, sha256=None)
    if not isinstance(raw_digest, str) or len(raw_digest) != _SHA256_HEX_LENGTH or any(
        character not in "0123456789abcdef" for character in raw_digest
    ):
        raise ValueError(f"archive file manifest digest is invalid: {path}")
    return ManifestMember(path=path, kind="file", size=raw_size, sha256=raw_digest)


def _validate_member_paths(members: Sequence[ManifestMember]) -> None:
    names: list[str] = [member.path for member in members]
    if names != sorted(names):
        raise ValueError("archive manifest members are not in canonical order")
    known_names: dict[str, str] = {}
    kinds: dict[str, str] = {}
    for member in members:
        _add_member_name(member.path, known_names)
        kinds[member.path] = member.kind
    for member in members:
        parent = PurePosixPath(member.path).parent
        while str(parent) != ".":
            parent_name: str = str(parent)
            if kinds.get(parent_name) != "directory":
                raise ValueError(f"archive member path collision or missing directory: {member.path}")
            parent = parent.parent


def _parse_manifest(  # noqa: C901,PLR0912 - strict manifest schema is validated as one transaction
    manifest_bytes: bytes,
    *,
    expected_skill: str,
    expected_run_id: str,
    limits: ArchiveExtractionLimits,
) -> ValidatedRunArchiveManifest:
    if len(manifest_bytes) > limits.max_member_bytes:
        raise ValueError("archive manifest exceeds individual size limit")
    try:
        decoded: str = manifest_bytes.decode("utf-8", "strict")
        raw_payload: object = json.loads(decoded, object_pairs_hook=_unique_json_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("archive manifest is not valid canonical UTF-8 JSON") from exc
    if not isinstance(raw_payload, dict):
        raise TypeError("archive manifest must be an object")
    payload = cast("dict[str, object]", raw_payload)
    if frozenset(payload) != _MANIFEST_KEYS:
        raise ValueError("archive manifest has invalid fields")
    if not isinstance(payload["archive_format"], str) or payload["archive_format"] != ARCHIVE_FORMAT:
        raise ValueError("unsupported archive manifest format or schema version")
    if (
        not isinstance(payload["schema_version"], int)
        or isinstance(payload["schema_version"], bool)
        or payload["schema_version"] != ARCHIVE_SCHEMA_VERSION
    ):
        raise ValueError("unsupported archive manifest format or schema version")
    raw_skill: object = payload["skill"]
    raw_run_id: object = payload["run_id"]
    if not isinstance(raw_skill, str) or not validate_run_id_slug(raw_skill):
        raise ValueError("archive manifest skill is invalid")
    if not isinstance(raw_run_id, str) or not validate_run_id_slug(raw_run_id):
        raise ValueError("archive manifest run-id is invalid")
    if raw_skill != expected_skill or raw_run_id != expected_run_id:
        raise ValueError("archive manifest identity does not match the requested run")
    raw_members: object = payload["members"]
    raw_count: object = payload["member_count"]
    if not isinstance(raw_members, list):
        raise TypeError("archive manifest members must be a list")
    member_values = cast("list[object]", raw_members)
    if not isinstance(raw_count, int) or isinstance(raw_count, bool) or raw_count != len(member_values):
        raise ValueError("archive manifest member count is invalid")
    if len(member_values) + 1 > limits.max_members:
        raise ValueError("archive exceeds member-count limit")
    members: tuple[ManifestMember, ...] = tuple(
        _validated_manifest_member(raw_member, limits=limits) for raw_member in member_values
    )
    _validate_member_paths(members)
    canonical: bytes = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    if manifest_bytes != canonical:
        raise ValueError("archive manifest is not canonical JSON")
    return ValidatedRunArchiveManifest(
        skill=raw_skill,
        run_id=raw_run_id,
        members=members,
        encoded=manifest_bytes,
    )


def _validate_tar_member(member: tarfile.TarInfo, *, limits: ArchiveExtractionLimits) -> tuple[str, str]:
    name: str = _canonical_input_member_path(
        member.name,
        allow_manifest=member.name == ARCHIVE_MANIFEST_NAME,
    )
    if member.type == tarfile.DIRTYPE:
        kind = "directory"
        expected_mode = 0o755
        if member.size != 0:
            raise ValueError(f"archive directory has nonzero size: {name}")
    elif member.type == tarfile.REGTYPE:
        kind = "file"
        expected_mode = 0o644 if name == ARCHIVE_MANIFEST_NAME else member.mode
        if member.size < 0 or member.size > limits.max_member_bytes:
            raise ValueError(f"archive member exceeds individual size limit: {name}")
        if name != ARCHIVE_MANIFEST_NAME and member.mode not in {0o644, 0o755}:
            raise ValueError(f"archive file mode is not normalized: {name}")
    else:
        raise ValueError(f"unsupported archive member type: {name}")
    if member.mode != expected_mode:
        raise ValueError(f"archive member mode is not normalized: {name}")
    if member.mtime != 0 or member.uid != 0 or member.gid != 0 or member.uname or member.gname:
        raise ValueError(f"archive member metadata is not normalized: {name}")
    return name, kind


def _read_tar_member(archive: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
    extracted = archive.extractfile(member)
    if extracted is None:
        raise ValueError(f"archive regular member cannot be read: {member.name}")
    with extracted:
        content: bytes = extracted.read(member.size + 1)
    if len(content) != member.size:
        raise ValueError(f"archive member is truncated: {member.name}")
    return content


def _inspect_archive(
    archive: tarfile.TarFile,
    *,
    compressed_size: int,
    expected_skill: str,
    expected_run_id: str,
    limits: ArchiveExtractionLimits,
) -> _ValidatedArchive:
    members: list[tarfile.TarInfo] = []
    member_rows: list[tuple[str, str, int]] = []
    known_names: dict[str, str] = {}
    for member in archive:
        if len(members) >= limits.max_members:
            raise ValueError("archive exceeds member-count limit")
        name, kind = _validate_tar_member(member, limits=limits)
        _add_member_name(name, known_names)
        members.append(member)
        member_rows.append((name, kind, member.size))
    names: list[str] = [row[0] for row in member_rows]
    if names != sorted(names):
        raise ValueError("archive members are not in canonical order")
    manifest_members: list[tarfile.TarInfo] = [
        member for member, row in zip(members, member_rows, strict=True) if row[0] == ARCHIVE_MANIFEST_NAME
    ]
    if len(manifest_members) != 1:
        raise ValueError("archive must contain exactly one root archive-manifest.json")
    manifest_info: tarfile.TarInfo = manifest_members[0]
    if manifest_info.type != tarfile.REGTYPE:
        raise ValueError("archive manifest must be a regular file")
    manifest_bytes: bytes = _read_tar_member(archive, manifest_info)
    manifest: ValidatedRunArchiveManifest = _parse_manifest(
        manifest_bytes,
        expected_skill=expected_skill,
        expected_run_id=expected_run_id,
        limits=limits,
    )
    actual_rows: tuple[tuple[str, str, int], ...] = tuple(
        row for row in member_rows if row[0] != ARCHIVE_MANIFEST_NAME
    )
    expected_rows: tuple[tuple[str, str, int], ...] = tuple(
        (member.path, member.kind, member.size) for member in manifest.members
    )
    if actual_rows != expected_rows:
        raise ValueError("archive members do not match archive manifest")
    expanded_size: int = sum(row[2] for row in member_rows)
    if expanded_size > limits.max_expanded_bytes:
        raise ValueError("archive exceeds total expanded-size limit")
    if compressed_size <= 0 or expanded_size > compressed_size * limits.max_compression_ratio:
        raise ValueError("archive exceeds compression-ratio limit")
    return _ValidatedArchive(
        manifest=manifest,
        members=tuple(members),
        expanded_size=expanded_size,
    )


def _new_materialized_file(path: Path, *, root: Path, mode: int) -> BinaryIO:
    _ = larch_io.validate_trusted_directory(path.parent, root=root)
    flags: int = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd: int = os.open(path, flags, mode)
    try:
        opened: os.stat_result = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise OSError(f"materialized archive member is not regular: {path}")
        os.fchmod(fd, mode)
        return os.fdopen(fd, "wb")
    except OSError:
        os.close(fd)
        raise


def _write_materialized_bytes(path: Path, content: bytes, *, root: Path, mode: int) -> None:
    with _new_materialized_file(path, root=root, mode=mode) as handle:
        _ = handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _extract_regular_member(
    archive: tarfile.TarFile,
    tar_member: tarfile.TarInfo,
    manifest_member: ManifestMember,
    *,
    temporary_root: Path,
) -> None:
    source = archive.extractfile(tar_member)
    if source is None:
        raise ValueError(f"archive regular member cannot be read: {tar_member.name}")
    destination: Path = temporary_root.joinpath(*PurePosixPath(manifest_member.path).parts)
    digest = hashlib.sha256()
    written = 0
    with source, _new_materialized_file(destination, root=temporary_root, mode=tar_member.mode) as output:
        while chunk := source.read(_CHUNK_SIZE):
            written += len(chunk)
            if written > manifest_member.size:
                raise ValueError(f"archive member exceeds declared size: {manifest_member.path}")
            _ = output.write(chunk)
            digest.update(chunk)
        output.flush()
        os.fsync(output.fileno())
    if written != manifest_member.size:
        raise ValueError(f"archive member is truncated: {manifest_member.path}")
    if digest.hexdigest() != manifest_member.sha256:
        raise ValueError(f"archive member digest mismatch: {manifest_member.path}")


def _read_bounded_regular_file(path: Path, *, root: Path, limit: int) -> bytes:
    entry: os.stat_result = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(entry.st_mode) or entry.st_size > limit:
        raise ValueError(f"materialized archive member is invalid or oversized: {path}")
    with _open_regular_member(path, root=root, expected=entry) as handle:
        content: bytes = handle.read(limit + 1)
    if len(content) != entry.st_size:
        raise ValueError(f"materialized archive member changed while reading: {path}")
    return content


def _materialized_tree_members(
    run_dir: Path, *, limits: ArchiveExtractionLimits
) -> tuple[ManifestMember, ...]:
    members: list[ManifestMember] = []
    known_names: dict[str, str] = {}
    expanded_size: int = 0
    for directory, child_dirs, child_files in os.walk(run_dir, topdown=True, followlinks=False):
        directory_path: Path = Path(directory)
        _ = larch_io.validate_trusted_directory(directory_path, root=run_dir)
        child_dirs.sort()
        child_files.sort()
        if len(members) + len(child_dirs) + len(child_files) > limits.max_members:
            raise ValueError("materialized run directory exceeds member-count limit")
        for child_name in child_dirs:
            source: Path = directory_path / child_name
            entry: os.stat_result = source.stat(follow_symlinks=False)
            if not stat.S_ISDIR(entry.st_mode):
                raise ValueError(f"unsupported materialized archive member type: {source}")
            member_path: str = _normalized_member_path(source.relative_to(run_dir))
            _add_member_name(member_path, known_names)
            members.append(ManifestMember(member_path, "directory", 0, None))
        for child_name in child_files:
            source = directory_path / child_name
            relative: Path = source.relative_to(run_dir)
            if str(PurePosixPath(*relative.parts)) == ARCHIVE_MANIFEST_NAME:
                continue
            entry = source.stat(follow_symlinks=False)
            if not stat.S_ISREG(entry.st_mode):
                raise ValueError(f"unsupported materialized archive member type: {source}")
            if entry.st_size > limits.max_member_bytes:
                raise ValueError(f"materialized archive member exceeds size limit: {source}")
            expanded_size += entry.st_size
            if expanded_size > limits.max_expanded_bytes:
                raise ValueError("materialized run directory exceeds expanded-size limit")
            member_path = _normalized_member_path(relative)
            _add_member_name(member_path, known_names)
            members.append(
                ManifestMember(
                    member_path,
                    "file",
                    entry.st_size,
                    _digest_regular_file(source, root=run_dir, expected=entry),
                )
            )
    return tuple(sorted(members, key=lambda member: member.path))


def verify_materialized_run_directory(
    *,
    run_dir: Path,
    expected_skill: str,
    expected_run_id: str,
    limits: ArchiveExtractionLimits | None = None,
) -> RunArchiveMaterializationResult:
    """Verify one unpacked cache directory against its embedded manifest."""
    active_limits = ArchiveExtractionLimits() if limits is None else limits
    active_limits.validate()
    root: Path = larch_io.validate_trusted_directory(run_dir)
    manifest_path: Path = root / ARCHIVE_MANIFEST_NAME
    manifest_bytes: bytes = _read_bounded_regular_file(
        manifest_path,
        root=root,
        limit=active_limits.max_member_bytes,
    )
    manifest: ValidatedRunArchiveManifest = _parse_manifest(
        manifest_bytes,
        expected_skill=expected_skill,
        expected_run_id=expected_run_id,
        limits=active_limits,
    )
    actual_members: tuple[ManifestMember, ...] = _materialized_tree_members(root, limits=active_limits)
    if actual_members != manifest.members:
        raise ValueError("materialized run directory does not match archive manifest")
    expanded_size: int = len(manifest_bytes) + sum(member.size for member in actual_members)
    if expanded_size > active_limits.max_expanded_bytes:
        raise ValueError("materialized run directory exceeds expanded-size limit")
    return RunArchiveMaterializationResult(
        run_dir=root,
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        member_count=len(actual_members),
        expanded_size=expanded_size,
    )


def _extract_validated_archive(
    archive: tarfile.TarFile,
    validated: _ValidatedArchive,
    *,
    temporary_root: Path,
) -> None:
    manifest_by_path: dict[str, ManifestMember] = {
        member.path: member for member in validated.manifest.members
    }
    directories: list[ManifestMember] = [
        member for member in validated.manifest.members if member.kind == "directory"
    ]
    for member in sorted(directories, key=lambda item: (item.path.count("/"), item.path)):
        destination: Path = temporary_root.joinpath(*PurePosixPath(member.path).parts)
        destination.mkdir(mode=0o700)
        _ = larch_io.validate_trusted_directory(destination, root=temporary_root)
    _write_materialized_bytes(
        temporary_root / ARCHIVE_MANIFEST_NAME,
        validated.manifest.encoded,
        root=temporary_root,
        mode=0o644,
    )
    for tar_member in validated.members:
        if tar_member.name == ARCHIVE_MANIFEST_NAME or tar_member.type == tarfile.DIRTYPE:
            continue
        manifest_member: ManifestMember = manifest_by_path[tar_member.name]
        _extract_regular_member(
            archive,
            tar_member,
            manifest_member,
            temporary_root=temporary_root,
        )
    for member in sorted(directories, key=lambda item: item.path.count("/"), reverse=True):
        temporary_root.joinpath(*PurePosixPath(member.path).parts).chmod(0o755)


def materialize_run_archive(
    *,
    archive_path: Path,
    run_dir: Path,
    expected_skill: str,
    expected_run_id: str,
    limits: ArchiveExtractionLimits | None = None,
) -> RunArchiveMaterializationResult:
    """Validate, privately extract, and atomically promote one run archive."""
    if not validate_run_id_slug(expected_skill):
        raise ValueError(f"invalid expected skill: {expected_skill}")
    if not validate_run_id_slug(expected_run_id):
        raise ValueError(f"invalid expected run-id: {expected_run_id}")
    active_limits = ArchiveExtractionLimits() if limits is None else limits
    active_limits.validate()
    requested_run_dir: Path = run_dir if run_dir.is_absolute() else Path.cwd() / run_dir
    if requested_run_dir.name != expected_run_id:
        raise ValueError("materialized run directory name must match the expected run-id")
    parent: Path = larch_io.ensure_trusted_directory(requested_run_dir.parent)
    destination: Path = parent / requested_run_dir.name
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to merge archive into existing run directory: {destination}")
    archive_entry: os.stat_result = archive_path.stat(follow_symlinks=False)
    if not stat.S_ISREG(archive_entry.st_mode):
        raise ValueError(f"run archive is not a regular file: {archive_path}")
    temporary_root: Path | None = None
    try:
        with _open_regular_member(archive_path, root=archive_path.parent, expected=archive_entry) as handle:
            with tarfile.open(fileobj=handle, mode="r:gz") as archive:
                validated: _ValidatedArchive = _inspect_archive(
                    archive,
                    compressed_size=archive_entry.st_size,
                    expected_skill=expected_skill,
                    expected_run_id=expected_run_id,
                    limits=active_limits,
                )
                temporary_root = Path(
                    tempfile.mkdtemp(
                        dir=parent,
                        prefix=f".{destination.name}.materialize-",
                    )
                )
                temporary_root.chmod(0o700)
                _extract_validated_archive(archive, validated, temporary_root=temporary_root)
        _ = verify_materialized_run_directory(
            run_dir=temporary_root,
            expected_skill=expected_skill,
            expected_run_id=expected_run_id,
            limits=active_limits,
        )
        _ = temporary_root.rename(destination)
        temporary_root = None
        try:
            return verify_materialized_run_directory(
                run_dir=destination,
                expected_skill=expected_skill,
                expected_run_id=expected_run_id,
                limits=active_limits,
            )
        except (OSError, TypeError, ValueError):
            shutil.rmtree(destination)
            raise
    finally:
        if temporary_root is not None:
            shutil.rmtree(temporary_root)


def materialize_main(argv: Sequence[str]) -> int:
    """Materialize one run archive and emit its machine envelope."""
    parser = argparse.ArgumentParser(prog="cli.py run-log materialize")
    _ = parser.add_argument("--archive-path", required=True)
    _ = parser.add_argument("--run-dir", required=True)
    _ = parser.add_argument("--skill", required=True)
    _ = parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    try:
        result: RunArchiveMaterializationResult = materialize_run_archive(
            archive_path=Path(args.archive_path),
            run_dir=Path(args.run_dir),
            expected_skill=args.skill,
            expected_run_id=args.run_id,
        )
    except (EOFError, OSError, tarfile.TarError, TypeError, ValueError) as exc:
        print(f"ERROR={exc}")
        return 1
    print(f"RUN_DIR={result.run_dir}")
    print(f"MANIFEST_SHA256={result.manifest_sha256}")
    print(f"MEMBER_COUNT={result.member_count}")
    print(f"EXPANDED_SIZE={result.expanded_size}")
    return 0


def main(argv: Sequence[str]) -> int:
    """Create one deterministic run archive and emit its machine envelope."""
    parser = argparse.ArgumentParser(prog="cli.py run-log archive")
    _ = parser.add_argument("--staging-root", required=True)
    _ = parser.add_argument("--output-dir", required=True)
    _ = parser.add_argument("--skill", required=True)
    _ = parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    try:
        result = create_run_archive(
            staging_root=Path(args.staging_root),
            output_dir=Path(args.output_dir),
            skill=args.skill,
            run_id=args.run_id,
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR={exc}")
        return 1
    print(f"ARCHIVE_PATH={result.archive_path}")
    print(f"ARCHIVE_SHA256={result.archive_sha256}")
    print(f"MANIFEST_SHA256={result.manifest_sha256}")
    print(f"MEMBER_COUNT={result.member_count}")
    return 0
