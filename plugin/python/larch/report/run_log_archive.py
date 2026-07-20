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
import stat
import tarfile
import tempfile
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from larch import io as larch_io
from larch.report.run_log_batch import validate_run_id_slug


ARCHIVE_FORMAT: str = "larch-run-archive"
ARCHIVE_MANIFEST_NAME: str = "archive-manifest.json"
ARCHIVE_SCHEMA_VERSION: int = 1
_CHUNK_SIZE: int = 1024 * 1024
_RESERVED_MEMBER_NAMES: frozenset[str] = frozenset({ARCHIVE_MANIFEST_NAME})


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
    normalized_names: set[str] = set()
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


def _add_member_name(name: str, known_names: set[str]) -> None:
    if name in known_names:
        raise ValueError(f"ambiguous archive member path after Unicode normalization: {name}")
    known_names.add(name)


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
