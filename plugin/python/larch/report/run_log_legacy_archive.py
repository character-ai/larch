"""Legacy archive materialization retained for the historical migration.

The archive contains regular files and explicit directories from a completed
staging tree plus ``archive-manifest.json``.  The manifest is canonical JSON
and records the normalized path, type, size, and SHA-256 digest of every
source-tree member.  It deliberately excludes itself, avoiding a recursive
digest while preserving an independently verifiable description of the run.
"""

from __future__ import annotations

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
from larch.report.run_log_archive import RunArchiveMaterializationResult
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
class ArchiveExtractionLimits:
    """Resource limits applied before and during archive extraction."""

    max_members: int = config.RUN_LOG_ARCHIVE_MAX_MEMBERS
    max_member_bytes: int = config.RUN_LOG_ARCHIVE_MAX_MEMBER_BYTES
    max_expanded_bytes: int = config.RUN_LOG_ARCHIVE_MAX_EXPANDED_BYTES
    max_compression_ratio: int = config.RUN_LOG_ARCHIVE_MAX_COMPRESSION_RATIO

    def validate(self) -> None:
        values: tuple[object, ...] = (
            self.max_members,
            self.max_member_bytes,
            self.max_expanded_bytes,
            self.max_compression_ratio,
        )
        if any(type(value) is not int or value <= 0 for value in values):  # pylint: disable=unidiomatic-typecheck  # exact type rejects bool and non-integers
            raise ValueError("archive extraction limits must be positive integers")


@dataclass(frozen=True)
class ManifestMember:
    """Validated manifest metadata for one extracted tree member."""

    path: str
    kind: str
    size: int
    sha256: str | None


@dataclass(frozen=True)
class ValidatedRunArchiveManifest:
    """Strictly parsed archive manifest ready for verification."""

    skill: str
    run_id: str
    members: tuple[ManifestMember, ...]
    encoded: bytes


@dataclass(frozen=True)
class LegacyArchiveMember:
    """One inventory-pinned regular member in a legacy migration archive."""

    path: str
    size: int
    sha256: str
    mode: int


@dataclass(frozen=True)
class LegacyRunArchive:
    """Verified inventory metadata needed to materialize one legacy run."""

    archive_size: int
    archive_sha256: str
    member_count: int
    expanded_size: int
    members: tuple[LegacyArchiveMember, ...]


@dataclass(frozen=True)
class _ValidatedArchive:
    manifest: ValidatedRunArchiveManifest
    members: tuple[tarfile.TarInfo, ...]
    expanded_size: int


def _normalized_member_path(relative: Path) -> str:
    raw_parts: tuple[str, ...] = relative.parts
    if not raw_parts:
        raise ValueError("archive member path is empty")
    normalized_parts: list[str] = []
    for part in raw_parts:
        normalized: str = unicodedata.normalize("NFC", part)
        if (
            not normalized
            or normalized in {".", ".."}
            or "/" in normalized
            or "\\" in normalized
        ):
            raise ValueError(f"ambiguous archive member path: {relative}")
        try:
            _ = normalized.encode("utf-8", "strict")
        except UnicodeError as exc:
            raise ValueError(
                f"archive member path is not UTF-8 encodable: {relative}"
            ) from exc
        normalized_parts.append(normalized)
    name: str = str(PurePosixPath(*normalized_parts))
    if name in _RESERVED_MEMBER_NAMES:
        raise ValueError(f"archive member path is reserved: {name}")
    return name


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


def _open_regular_member(
    path: Path, *, root: Path, expected: os.stat_result
) -> BinaryIO:
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


def _add_member_name(name: str, known_names: dict[str, str]) -> None:
    collision_key: str = name.casefold()
    previous: str | None = known_names.get(collision_key)
    if previous is not None:
        raise ValueError(
            f"ambiguous archive member path after Unicode normalization: {previous} and {name}"
        )
    known_names[collision_key] = name


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of one regular file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_input_member_path(raw_name: str, *, allow_manifest: bool = False) -> str:
    if not raw_name or raw_name.startswith("/") or "\\" in raw_name or "\0" in raw_name:
        raise ValueError(f"unsafe archive member path: {raw_name!r}")
    path = PurePosixPath(raw_name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe archive member path: {raw_name!r}")
    normalized_parts: tuple[str, ...] = tuple(
        unicodedata.normalize("NFC", part) for part in path.parts
    )
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


def _validated_manifest_member(
    raw: object, *, limits: ArchiveExtractionLimits
) -> ManifestMember:
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
    if (
        not isinstance(raw_digest, str)
        or len(raw_digest) != _SHA256_HEX_LENGTH
        or any(character not in "0123456789abcdef" for character in raw_digest)
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
                raise ValueError(
                    f"archive member path collision or missing directory: {member.path}"
                )
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
    if (
        not isinstance(payload["archive_format"], str)
        or payload["archive_format"] != ARCHIVE_FORMAT
    ):
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
    if (
        not isinstance(raw_count, int)
        or isinstance(raw_count, bool)
        or raw_count != len(member_values)
    ):
        raise ValueError("archive manifest member count is invalid")
    if len(member_values) + 1 > limits.max_members:
        raise ValueError("archive exceeds member-count limit")
    members: tuple[ManifestMember, ...] = tuple(
        _validated_manifest_member(raw_member, limits=limits)
        for raw_member in member_values
    )
    _validate_member_paths(members)
    canonical: bytes = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    if manifest_bytes != canonical:
        raise ValueError("archive manifest is not canonical JSON")
    return ValidatedRunArchiveManifest(
        skill=raw_skill,
        run_id=raw_run_id,
        members=members,
        encoded=manifest_bytes,
    )


def _validate_tar_member(
    member: tarfile.TarInfo, *, limits: ArchiveExtractionLimits
) -> tuple[str, str]:
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
    if (
        member.mtime != 0
        or member.uid != 0
        or member.gid != 0
        or member.uname
        or member.gname
    ):
        raise ValueError(f"archive member metadata is not normalized: {name}")
    return name, kind


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


def _write_materialized_bytes(
    path: Path, content: bytes, *, root: Path, mode: int
) -> None:
    with _new_materialized_file(path, root=root, mode=mode) as handle:
        _ = handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    directory: Path = larch_io.validate_trusted_directory(path)
    flags: int = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int = os.open(directory, flags)
    try:
        opened: os.stat_result = os.fstat(descriptor)
        if not stat.S_ISDIR(opened.st_mode):
            raise OSError(f"archive directory changed while opening: {directory}")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


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
    destination: Path = temporary_root.joinpath(
        *PurePosixPath(manifest_member.path).parts
    )
    digest = hashlib.sha256()
    written = 0
    with (
        source,
        _new_materialized_file(
            destination, root=temporary_root, mode=tar_member.mode
        ) as output,
    ):
        while chunk := source.read(_CHUNK_SIZE):
            written += len(chunk)
            if written > manifest_member.size:
                raise ValueError(
                    f"archive member exceeds declared size: {manifest_member.path}"
                )
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
    for directory, child_dirs, child_files in os.walk(
        run_dir, topdown=True, followlinks=False
    ):
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
                raise ValueError(
                    f"unsupported materialized archive member type: {source}"
                )
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
                raise ValueError(
                    f"unsupported materialized archive member type: {source}"
                )
            if entry.st_size > limits.max_member_bytes:
                raise ValueError(
                    f"materialized archive member exceeds size limit: {source}"
                )
            expanded_size += entry.st_size
            if expanded_size > limits.max_expanded_bytes:
                raise ValueError(
                    "materialized run directory exceeds expanded-size limit"
                )
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


def _verify_legacy_materialized_run_directory(
    *,
    run_dir: Path,
    expected_skill: str,
    expected_run_id: str,
    limits: ArchiveExtractionLimits | None = None,
) -> RunArchiveMaterializationResult:
    """Verify a synthesized legacy cache directory against its manifest."""
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
    actual_members: tuple[ManifestMember, ...] = _materialized_tree_members(
        root, limits=active_limits
    )
    if actual_members != manifest.members:
        raise ValueError("materialized run directory does not match archive manifest")
    expanded_size: int = len(manifest_bytes) + sum(
        member.size for member in actual_members
    )
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
    for member in sorted(
        directories, key=lambda item: (item.path.count("/"), item.path)
    ):
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
        if (
            tar_member.name == ARCHIVE_MANIFEST_NAME
            or tar_member.type == tarfile.DIRTYPE
        ):
            continue
        manifest_member: ManifestMember = manifest_by_path[tar_member.name]
        _extract_regular_member(
            archive,
            tar_member,
            manifest_member,
            temporary_root=temporary_root,
        )
    for member in sorted(
        directories, key=lambda item: item.path.count("/"), reverse=True
    ):
        directory: Path = temporary_root.joinpath(*PurePosixPath(member.path).parts)
        directory.chmod(0o755)
        _fsync_directory(directory)
    _fsync_directory(temporary_root)


def _legacy_manifest(  # noqa: C901 - inventory and synthesized manifest validate as one transaction
    *,
    expected_skill: str,
    expected_run_id: str,
    legacy: LegacyRunArchive,
    limits: ArchiveExtractionLimits,
) -> ValidatedRunArchiveManifest:
    if legacy.member_count != len(legacy.members):
        raise ValueError("legacy archive inventory member count is inconsistent")
    if legacy.member_count > limits.max_members:
        raise ValueError("legacy archive exceeds member-count limit")
    if legacy.expanded_size != sum(member.size for member in legacy.members):
        raise ValueError("legacy archive inventory expanded size is inconsistent")
    if legacy.expanded_size > limits.max_expanded_bytes:
        raise ValueError("legacy archive exceeds total expanded-size limit")
    known_names: dict[str, str] = {}
    file_members: list[ManifestMember] = []
    directory_names: set[str] = set()
    for member in legacy.members:
        path: str = _canonical_input_member_path(member.path)
        _add_member_name(path, known_names)
        if member.size < 0 or member.size > limits.max_member_bytes:
            raise ValueError(f"legacy archive member has invalid size: {path}")
        if member.mode not in {0o644, 0o755}:
            raise ValueError(f"legacy archive member has unsupported mode: {path}")
        if len(member.sha256) != _SHA256_HEX_LENGTH or any(
            character not in "0123456789abcdef" for character in member.sha256
        ):
            raise ValueError(f"legacy archive member digest is invalid: {path}")
        parent: PurePosixPath = PurePosixPath(path).parent
        while str(parent) != ".":
            directory_names.add(str(parent))
            parent = parent.parent
        file_members.append(ManifestMember(path, "file", member.size, member.sha256))
    if len(file_members) + len(directory_names) + 1 > limits.max_members:
        raise ValueError(
            "legacy archive exceeds member-count limit after directory synthesis"
        )
    manifest_members: tuple[ManifestMember, ...] = tuple(
        sorted(
            [
                *(
                    ManifestMember(path, "directory", 0, None)
                    for path in directory_names
                ),
                *file_members,
            ],
            key=lambda member: member.path,
        )
    )
    _validate_member_paths(manifest_members)
    records: list[dict[str, int | str | None]] = [
        {
            "kind": member.kind,
            "path": member.path,
            "sha256": member.sha256,
            "size": member.size,
        }
        for member in manifest_members
    ]
    payload: dict[str, object] = {
        "archive_format": ARCHIVE_FORMAT,
        "member_count": len(records),
        "members": records,
        "run_id": expected_run_id,
        "schema_version": ARCHIVE_SCHEMA_VERSION,
        "skill": expected_skill,
    }
    encoded: bytes = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    if legacy.expanded_size + len(encoded) > limits.max_expanded_bytes:
        raise ValueError("legacy archive exceeds total expanded-size limit")
    return ValidatedRunArchiveManifest(
        skill=expected_skill,
        run_id=expected_run_id,
        members=manifest_members,
        encoded=encoded,
    )


def _inspect_legacy_archive(
    archive: tarfile.TarFile,
    *,
    expected_skill: str,
    expected_run_id: str,
    legacy: LegacyRunArchive,
    limits: ArchiveExtractionLimits,
) -> _ValidatedArchive:
    manifest: ValidatedRunArchiveManifest = _legacy_manifest(
        expected_skill=expected_skill,
        expected_run_id=expected_run_id,
        legacy=legacy,
        limits=limits,
    )
    expected: tuple[tuple[str, int, int], ...] = tuple(
        (member.path, member.size, member.mode) for member in legacy.members
    )
    members: list[tarfile.TarInfo] = []
    actual: list[tuple[str, int, int]] = []
    known_names: dict[str, str] = {}
    for tar_member in archive:
        if len(members) >= limits.max_members:
            raise ValueError("legacy archive exceeds member-count limit")
        name, kind = _validate_tar_member(tar_member, limits=limits)
        if kind != "file" or name == ARCHIVE_MANIFEST_NAME:
            raise ValueError(f"unsupported legacy archive member type: {name}")
        _add_member_name(name, known_names)
        members.append(tar_member)
        actual.append((name, tar_member.size, tar_member.mode))
    if tuple(actual) != expected:
        raise ValueError("legacy archive members do not match migration inventory")
    return _ValidatedArchive(
        manifest=manifest,
        members=tuple(members),
        expanded_size=legacy.expanded_size + len(manifest.encoded),
    )


def materialize_legacy_run_archive(  # noqa: C901,PLR0913 - security-critical validation stays transactional
    *,
    archive_path: Path,
    run_dir: Path,
    expected_skill: str,
    expected_run_id: str,
    legacy: LegacyRunArchive,
    limits: ArchiveExtractionLimits | None = None,
) -> RunArchiveMaterializationResult:
    """Validate and atomically materialize one inventory-pinned legacy archive."""
    if not validate_run_id_slug(expected_skill):
        raise ValueError(f"invalid expected skill: {expected_skill}")
    if not validate_run_id_slug(expected_run_id):
        raise ValueError(f"invalid expected run-id: {expected_run_id}")
    active_limits = ArchiveExtractionLimits() if limits is None else limits
    active_limits.validate()
    requested_run_dir: Path = run_dir if run_dir.is_absolute() else Path.cwd() / run_dir
    if requested_run_dir.name != expected_run_id:
        raise ValueError(
            "materialized run directory name must match the expected run-id"
        )
    parent: Path = larch_io.ensure_trusted_directory(requested_run_dir.parent)
    destination: Path = parent / requested_run_dir.name
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(
            f"refusing to merge archive into existing run directory: {destination}"
        )
    archive_entry: os.stat_result = archive_path.stat(follow_symlinks=False)
    if not stat.S_ISREG(archive_entry.st_mode):
        raise ValueError(f"run archive is not a regular file: {archive_path}")
    if archive_entry.st_size != legacy.archive_size:
        raise ValueError("legacy archive size does not match migration inventory")
    if (
        archive_entry.st_size <= 0
        or legacy.expanded_size
        > archive_entry.st_size * active_limits.max_compression_ratio
    ):
        raise ValueError("legacy archive exceeds compression-ratio limit")
    temporary_root: Path | None = None
    try:
        with _open_regular_member(
            archive_path, root=archive_path.parent, expected=archive_entry
        ) as handle:
            digest = hashlib.sha256()
            while chunk := handle.read(_CHUNK_SIZE):
                digest.update(chunk)
            if digest.hexdigest() != legacy.archive_sha256:
                raise ValueError(
                    "legacy archive digest does not match migration inventory"
                )
            _ = handle.seek(0)
            with tarfile.open(fileobj=handle, mode="r:gz") as archive:
                validated: _ValidatedArchive = _inspect_legacy_archive(
                    archive,
                    expected_skill=expected_skill,
                    expected_run_id=expected_run_id,
                    legacy=legacy,
                    limits=active_limits,
                )
                temporary_root = Path(
                    tempfile.mkdtemp(
                        dir=parent,
                        prefix=f".{destination.name}.materialize-",
                    )
                )
                temporary_root.chmod(0o700)
                _extract_validated_archive(
                    archive, validated, temporary_root=temporary_root
                )
        _ = _verify_legacy_materialized_run_directory(
            run_dir=temporary_root,
            expected_skill=expected_skill,
            expected_run_id=expected_run_id,
            limits=active_limits,
        )
        _ = temporary_root.rename(destination)
        _fsync_directory(parent)
        temporary_root = None
        try:
            return _verify_legacy_materialized_run_directory(
                run_dir=destination,
                expected_skill=expected_skill,
                expected_run_id=expected_run_id,
                limits=active_limits,
            )
        except (OSError, TypeError, ValueError):
            shutil.rmtree(destination)
            _fsync_directory(parent)
            raise
    finally:
        if temporary_root is not None:
            shutil.rmtree(temporary_root)
