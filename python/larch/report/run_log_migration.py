"""Strict parser for repository-pinned legacy run-log migration inventories."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol, cast

from larch.core import config
from larch.report import run_log_archive
from larch.report.run_log_batch import validate_run_id_slug
from larch.report.storage_config import (
    LegacyMigrationDescriptor,
    StorageBase,
)

_INVENTORY_KEYS: frozenset[str] = frozenset(
    {"archives", "schema", "source_commit", "source_files", "storage_root", "totals"}
)
_ARCHIVE_KEYS: frozenset[str] = frozenset(
    {
        "archive_bytes",
        "kind",
        "member_count",
        "object_key",
        "run_id",
        "sha256",
        "skill",
        "uncompressed_bytes",
    }
)
_SOURCE_FILE_KEYS: frozenset[str] = frozenset(
    {
        "archive_member_path",
        "archive_object_key",
        "bytes",
        "git_oid",
        "mode",
        "path",
        "sha256",
    }
)
_TOTAL_KEYS: frozenset[str] = frozenset(
    {
        "archive_bytes",
        "archive_objects",
        "members",
        "run_directories",
        "source_paths",
        "uncompressed_bytes",
    }
)
_SHA256_LENGTH = 64
_GIT_OID_LENGTH = 40


class MigrationObjectStore(Protocol):
    """Object operation needed for the lazy inventory download."""

    def download(self, key: str, destination: Path) -> None: ...


@dataclass(frozen=True)
class _ArchiveRow:
    object_key: str
    relative_key: str
    kind: str
    skill: str | None
    run_id: str | None
    archive_bytes: int
    sha256: str
    member_count: int
    uncompressed_bytes: int


@dataclass(frozen=True)
class LegacyMigrationInventory:
    """Validated legacy run records keyed by remote run-archive path."""

    run_archives: tuple[tuple[str, run_log_archive.LegacyRunArchive], ...]

    def archive_for(self, remote_key: str) -> run_log_archive.LegacyRunArchive | None:
        return next(
            (record for key, record in self.run_archives if key == remote_key),
            None,
        )


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate migration inventory key: {key}")
        result[key] = value
    return result


def _strict_nonnegative_int(value: object, *, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"migration inventory {label} must be a non-negative integer")
    return value


def _strict_positive_int(value: object, *, label: str) -> int:
    number: int = _strict_nonnegative_int(value, label=label)
    if number == 0:
        raise ValueError(f"migration inventory {label} must be positive")
    return number


def _lower_hex(value: object, *, length: int, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"migration inventory {label} is malformed")
    return value


def _canonical_path(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("/")
        or "\\" in value
        or "\0" in value
    ):
        raise ValueError(f"migration inventory {label} is unsafe")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"migration inventory {label} is unsafe")
    normalized: str = str(
        PurePosixPath(*(unicodedata.normalize("NFC", part) for part in path.parts))
    )
    if normalized != value:
        raise ValueError(f"migration inventory {label} is non-canonical")
    return value


def _validated_archive_row(  # noqa: C901 - strict row validation stays transactional
    raw: object, *, storage_root: StorageBase
) -> _ArchiveRow:
    if not isinstance(raw, dict):
        raise TypeError("migration inventory archive row must be an object")
    row = cast("dict[str, object]", raw)
    if frozenset(row) != _ARCHIVE_KEYS:
        raise ValueError("migration inventory archive row has invalid fields")
    object_key: str = _canonical_path(row["object_key"], label="archive object key")
    root_prefix: str = f"{storage_root.prefix}/"
    if not object_key.startswith(root_prefix):
        raise ValueError("migration inventory archive object is outside storage root")
    relative_key: str = object_key.removeprefix(root_prefix)
    kind: object = row["kind"]
    if kind not in {"residual", "run"}:
        raise ValueError("migration inventory archive kind is invalid")
    archive_bytes: int = _strict_positive_int(
        row["archive_bytes"], label="archive bytes"
    )
    member_count: int = _strict_positive_int(
        row["member_count"], label="archive member count"
    )
    uncompressed_bytes: int = _strict_nonnegative_int(
        row["uncompressed_bytes"], label="archive uncompressed bytes"
    )
    if member_count > config.RUN_LOG_ARCHIVE_MAX_MEMBERS:
        raise ValueError("migration inventory archive exceeds member-count limit")
    if archive_bytes > config.RUN_LOG_ARCHIVE_MAX_EXPANDED_BYTES:
        raise ValueError("migration inventory archive exceeds compressed-size limit")
    if uncompressed_bytes > config.RUN_LOG_ARCHIVE_MAX_EXPANDED_BYTES:
        raise ValueError("migration inventory archive exceeds expanded-size limit")
    digest: str = _lower_hex(
        row["sha256"], length=_SHA256_LENGTH, label="archive digest"
    )
    raw_skill: object = row["skill"]
    raw_run_id: object = row["run_id"]
    skill: str | None = raw_skill if isinstance(raw_skill, str) else None
    run_id: str | None = raw_run_id if isinstance(raw_run_id, str) else None
    if kind == "run":
        expected_relative: str = f"run-logs/{skill}/{run_id}.tar.gz"
        if (
            skill is None
            or run_id is None
            or object_key != f"{storage_root.prefix}/{expected_relative}"
        ):
            raise ValueError("migration inventory run archive identity is invalid")
        valid_identity: bool = validate_run_id_slug(skill) and validate_run_id_slug(
            run_id
        )
        if not valid_identity:
            raise ValueError("migration inventory run archive identity is invalid")
    elif (
        skill is not None
        or run_id is not None
        or not relative_key.startswith("migration/")
    ):
        raise ValueError("migration inventory residual archive identity is invalid")
    return _ArchiveRow(
        object_key=object_key,
        relative_key=relative_key,
        kind=cast("str", kind),
        skill=skill,
        run_id=run_id,
        archive_bytes=archive_bytes,
        sha256=digest,
        member_count=member_count,
        uncompressed_bytes=uncompressed_bytes,
    )


def _validated_source_member(
    raw: object,
    *,
    archives: dict[str, _ArchiveRow],
) -> tuple[str, run_log_archive.LegacyArchiveMember, str]:
    if not isinstance(raw, dict):
        raise TypeError("migration inventory source-file row must be an object")
    row = cast("dict[str, object]", raw)
    if frozenset(row) != _SOURCE_FILE_KEYS:
        raise ValueError("migration inventory source-file row has invalid fields")
    archive_key: str = _canonical_path(
        row["archive_object_key"], label="source archive object key"
    )
    archive: _ArchiveRow | None = archives.get(archive_key)
    if archive is None:
        raise ValueError(
            "migration inventory source file references an unknown archive"
        )
    member_path: str = _canonical_path(
        row["archive_member_path"], label="archive member path"
    )
    if member_path == run_log_archive.ARCHIVE_MANIFEST_NAME:
        raise ValueError("migration inventory source file uses a reserved member path")
    source_path: str = _canonical_path(row["path"], label="source path")
    expected_source: str = (
        f"larch-logs/{archive.skill}/{archive.run_id}/{member_path}"
        if archive.kind == "run"
        else f"larch-logs/{member_path}"
    )
    if source_path != expected_source:
        raise ValueError(
            "migration inventory source path does not match archive identity"
        )
    size: int = _strict_nonnegative_int(row["bytes"], label="source-file bytes")
    if size > config.RUN_LOG_ARCHIVE_MAX_MEMBER_BYTES:
        raise ValueError("migration inventory source file exceeds member-size limit")
    digest: str = _lower_hex(
        row["sha256"], length=_SHA256_LENGTH, label="source-file digest"
    )
    _ = _lower_hex(row["git_oid"], length=_GIT_OID_LENGTH, label="Git object ID")
    raw_mode: object = row["mode"]
    if raw_mode not in {"100644", "100755"}:
        raise ValueError("migration inventory source-file mode is unsupported")
    mode: int = 0o644 if raw_mode == "100644" else 0o755
    return (
        archive_key,
        run_log_archive.LegacyArchiveMember(member_path, size, digest, mode),
        source_path,
    )


def parse_inventory(  # noqa: C901,PLR0912,PLR0915 - strict schema cross-checks stay transactional
    encoded: bytes,
    *,
    descriptor: LegacyMigrationDescriptor,
    storage_root: StorageBase,
) -> LegacyMigrationInventory:
    """Parse and cross-check a hash-verified migration inventory."""
    if len(encoded) > config.RUN_LOG_MIGRATION_INVENTORY_MAX_BYTES:
        raise ValueError("migration inventory exceeds byte limit")
    try:
        decoded: str = encoded.decode("utf-8", "strict")
        raw_payload: object = json.loads(decoded, object_pairs_hook=_unique_json_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("migration inventory is not valid UTF-8 JSON") from exc
    if not isinstance(raw_payload, dict):
        raise TypeError("migration inventory must be an object")
    payload = cast("dict[str, object]", raw_payload)
    if frozenset(payload) != _INVENTORY_KEYS:
        raise ValueError("migration inventory has invalid fields")
    if payload["schema"] != descriptor.schema:
        raise ValueError("migration inventory schema is not pinned by the repository")
    if payload["source_commit"] != descriptor.source_commit:
        raise ValueError(
            "migration inventory source commit is not pinned by the repository"
        )
    if (
        payload["storage_root"] != descriptor.storage_root
        or descriptor.storage_root != storage_root.uri
    ):
        raise ValueError(
            "migration inventory storage root is not pinned by the repository"
        )
    raw_archives: object = payload["archives"]
    raw_sources: object = payload["source_files"]
    raw_totals: object = payload["totals"]
    if not isinstance(raw_archives, list) or not isinstance(raw_sources, list):
        raise TypeError(
            "migration inventory archive and source-file rows must be lists"
        )
    archive_values = cast("list[object]", raw_archives)
    source_values = cast("list[object]", raw_sources)
    if (
        not archive_values
        or len(archive_values) > config.RUN_LOG_MIGRATION_INVENTORY_MAX_ARCHIVES
    ):
        raise ValueError("migration inventory archive count is outside limits")
    if (
        not source_values
        or len(source_values) > config.RUN_LOG_MIGRATION_INVENTORY_MAX_SOURCE_FILES
    ):
        raise ValueError("migration inventory source-file count is outside limits")
    archive_rows: tuple[_ArchiveRow, ...] = tuple(
        _validated_archive_row(raw, storage_root=storage_root) for raw in archive_values
    )
    archives: dict[str, _ArchiveRow] = {}
    archive_casefold: dict[str, str] = {}
    for row in archive_rows:
        previous: str | None = archive_casefold.get(row.object_key.casefold())
        if previous is not None:
            raise ValueError(
                f"duplicate or case-colliding migration archive keys: {previous!r} and {row.object_key!r}"
            )
        archive_casefold[row.object_key.casefold()] = row.object_key
        archives[row.object_key] = row
    members_by_archive: dict[str, list[run_log_archive.LegacyArchiveMember]] = {
        key: [] for key in archives
    }
    member_names: dict[tuple[str, str], str] = {}
    source_paths: dict[str, str] = {}
    for raw in source_values:
        archive_key, member, source_path = _validated_source_member(
            raw, archives=archives
        )
        member_identity: tuple[str, str] = (archive_key, member.path.casefold())
        previous_member: str | None = member_names.get(member_identity)
        if previous_member is not None:
            raise ValueError(
                f"duplicate or case-colliding migration members: {previous_member!r} and {member.path!r}"
            )
        previous_source: str | None = source_paths.get(source_path.casefold())
        if previous_source is not None:
            raise ValueError(
                f"duplicate or case-colliding migration source paths: {previous_source!r} and {source_path!r}"
            )
        member_names[member_identity] = member.path
        source_paths[source_path.casefold()] = source_path
        members_by_archive[archive_key].append(member)
    for members in members_by_archive.values():
        members.sort(key=lambda member: member.path)
    for key, row in archives.items():
        members = members_by_archive[key]
        if (
            len(members) != row.member_count
            or sum(member.size for member in members) != row.uncompressed_bytes
        ):
            raise ValueError("migration inventory per-archive totals are inconsistent")
    if not isinstance(raw_totals, dict):
        raise TypeError("migration inventory totals must be an object")
    totals = cast("dict[str, object]", raw_totals)
    if frozenset(totals) != _TOTAL_KEYS:
        raise ValueError("migration inventory totals have invalid fields")
    expected_totals: dict[str, int] = {
        "archive_bytes": sum(row.archive_bytes for row in archive_rows),
        "archive_objects": len(archive_rows),
        "members": len(source_values),
        "run_directories": sum(row.kind == "run" for row in archive_rows),
        "source_paths": len(source_paths),
        "uncompressed_bytes": sum(row.uncompressed_bytes for row in archive_rows),
    }
    actual_totals: dict[str, int] = {
        key: _strict_nonnegative_int(totals[key], label=f"total {key}")
        for key in _TOTAL_KEYS
    }
    if actual_totals != expected_totals:
        raise ValueError("migration inventory global totals are inconsistent")
    run_archives: list[tuple[str, run_log_archive.LegacyRunArchive]] = []
    for row in archive_rows:
        if row.kind != "run":
            continue
        run_archives.append(
            (
                row.relative_key,
                run_log_archive.LegacyRunArchive(
                    archive_size=row.archive_bytes,
                    archive_sha256=row.sha256,
                    member_count=row.member_count,
                    expanded_size=row.uncompressed_bytes,
                    members=tuple(members_by_archive[row.object_key]),
                ),
            )
        )
    return LegacyMigrationInventory(run_archives=tuple(sorted(run_archives)))


def _read_inventory_bytes(path: Path) -> bytes:
    flags: int = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int = os.open(path, flags)
    try:
        opened: os.stat_result = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError("downloaded migration inventory is not a regular file")
        if opened.st_size > config.RUN_LOG_MIGRATION_INVENTORY_MAX_BYTES:
            raise ValueError("migration inventory exceeds byte limit")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            encoded: bytes = handle.read(
                config.RUN_LOG_MIGRATION_INVENTORY_MAX_BYTES + 1
            )
        if len(encoded) != opened.st_size:
            raise ValueError("migration inventory changed while reading")
        return encoded
    finally:
        os.close(descriptor)


def download_and_parse_inventory(
    *,
    store: MigrationObjectStore,
    descriptor: LegacyMigrationDescriptor,
    storage_root: StorageBase,
    temporary_dir: Path,
) -> LegacyMigrationInventory:
    """Download one pinned inventory, verify its hash, and parse it strictly."""
    with tempfile.NamedTemporaryFile(
        dir=temporary_dir,
        prefix=".legacy-migration-inventory-",
        suffix=".json",
        delete=False,
    ) as handle:
        inventory_path: Path = Path(handle.name)
    try:
        store.download(descriptor.inventory_key, inventory_path)
        encoded: bytes = _read_inventory_bytes(inventory_path)
        if hashlib.sha256(encoded).hexdigest() != descriptor.inventory_sha256:
            raise ValueError("migration inventory digest does not match repository pin")
        return parse_inventory(
            encoded,
            descriptor=descriptor,
            storage_root=storage_root,
        )
    finally:
        inventory_path.unlink(missing_ok=True)
