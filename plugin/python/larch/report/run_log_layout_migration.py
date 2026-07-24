"""Plan, apply, and verify the one-time tool-first run-log migration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Protocol, cast

from larch.core import config
from larch.report import run_log_archive, run_log_migration, run_log_sync
from larch.report.object_store import (
    ObjectStoreError,
    ObjectStoreErrorKind,
    RemoteObject,
    object_store_for,
)
from larch.report.storage_config import (
    LegacyMigrationDescriptor,
    StorageBase,
    parse_storage_base_uri,
    validate_client_repo,
)

PLAN_SCHEMA: Final = "larch-run-log-layout-plan-v1"
REPORT_SCHEMA: Final = "larch-run-log-layout-report-v1"
FINAL_REPORT_SCHEMA: Final = "larch-run-log-layout-final-report-v1"
_RUN_LOG_PREFIX: Final = "run-logs/"
_MANIFEST_NAME: Final = run_log_archive.ARCHIVE_MANIFEST_NAME
_LIVE_MAPPINGS: Final = {
    "larch": (
        "s3://zhupanov/larch",
        "s3://zhupanov/larch/larch",
    ),
    "agent-lint": (
        "s3://zhupanov/agent-lint",
        "s3://zhupanov/larch/agent-lint",
    ),
}
_PLAN_KEYS: Final = frozenset(
    {
        "created_at",
        "mappings",
        "operator",
        "plan_sha256",
        "schema",
        "source_commit",
        "tool",
        "tool_version",
    }
)
_GIT_COMMIT_HEX_LENGTH: Final = 40


class LayoutMigrationError(RuntimeError):
    """A migration invariant failed without mutating source objects."""


class MigrationStore(Protocol):
    """Object operations needed by plan, apply, and verify."""

    def list_objects(self, prefix: str = "") -> tuple[RemoteObject, ...]: ...

    def download(self, key: str, destination: Path) -> None: ...

    def upload_create(self, key: str, source: Path) -> RemoteObject: ...

    def metadata(self, key: str) -> RemoteObject: ...


@dataclass(frozen=True)
class LayoutMapping:
    """One old-root to tool-first-root migration."""

    client_repo: str
    source: StorageBase
    target: StorageBase
    legacy_descriptor: LegacyMigrationDescriptor | None = None

    def validate(self, *, live: bool) -> None:
        client_repo = validate_client_repo(self.client_repo)
        if client_repo != self.client_repo:
            raise LayoutMigrationError("client repository identity is not canonical")
        source_logs = f"{self.source.uri}/{_RUN_LOG_PREFIX}"
        target_logs = f"{self.target.uri}/{_RUN_LOG_PREFIX}"
        if source_logs == target_logs:
            raise LayoutMigrationError("source and target run-log prefixes are identical")
        if source_logs.startswith(f"{target_logs}/") or target_logs.startswith(
            f"{source_logs}/"
        ):
            raise LayoutMigrationError("source and target run-log prefixes overlap")
        if live and _LIVE_MAPPINGS.get(client_repo) != (
            self.source.uri,
            self.target.uri,
        ):
            raise LayoutMigrationError(
                f"live mapping is not allowlisted for {client_repo}"
            )
        if self.source.scheme != "s3" or self.target.scheme != "s3":
            raise LayoutMigrationError("live layout migration supports S3 only")
        if self.source.bucket != self.target.bucket:
            raise LayoutMigrationError("source and target buckets differ")
        if client_repo == "larch" and self.legacy_descriptor is None:
            raise LayoutMigrationError("larch mapping requires a legacy descriptor")
        if client_repo != "larch" and self.legacy_descriptor is not None:
            raise LayoutMigrationError(
                "only the larch mapping may use a legacy descriptor"
            )


StoreFactory = Callable[[StorageBase], MigrationStore]


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise LayoutMigrationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _canonical_bytes(payload: Mapping[str, object]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _self_hashed_payload(
    payload: Mapping[str, object], *, digest_field: str
) -> dict[str, object]:
    unsigned = dict(payload)
    _ = unsigned.pop(digest_field, None)
    digest = hashlib.sha256(_canonical_bytes(unsigned)).hexdigest()
    return {**unsigned, digest_field: digest}


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    parent = path.parent
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if parent.is_symlink() or path.is_symlink():
        raise LayoutMigrationError("refusing unsafe JSON output path")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            _ = handle.write(_canonical_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        _ = temporary.replace(path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, object]:
    try:
        entry = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise LayoutMigrationError("migration JSON file is unavailable") from exc
    if not stat.S_ISREG(entry.st_mode) or path.is_symlink():
        raise LayoutMigrationError("migration JSON path is not a regular file")
    try:
        raw = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LayoutMigrationError("migration JSON is invalid") from exc
    if not isinstance(raw, dict):
        raise LayoutMigrationError("migration JSON root must be an object")
    return cast("dict[str, object]", raw)


def _verified_plan(path: Path) -> dict[str, object]:
    payload = _read_json(path)
    if frozenset(payload) != _PLAN_KEYS or payload.get("schema") != PLAN_SCHEMA:
        raise LayoutMigrationError("migration plan schema is invalid")
    expected = payload.get("plan_sha256")
    if not isinstance(expected, str):
        raise LayoutMigrationError("migration plan digest is invalid")
    unsigned = dict(payload)
    del unsigned["plan_sha256"]
    if hashlib.sha256(_canonical_bytes(unsigned)).hexdigest() != expected:
        raise LayoutMigrationError("migration plan digest does not match content")
    return payload


def _validated_remote_inventory(
    objects: tuple[RemoteObject, ...],
) -> tuple[run_log_sync.RemoteRunArchive, ...]:
    try:
        return run_log_sync.validated_remote_inventory(objects)
    except (TypeError, ValueError, run_log_sync.RunLogSyncError) as exc:
        raise LayoutMigrationError("remote run-log inventory is invalid") from exc


def _remote_map(
    store: MigrationStore,
) -> dict[str, tuple[run_log_sync.RemoteRunArchive, RemoteObject]]:
    listed = store.list_objects(_RUN_LOG_PREFIX)
    archives = _validated_remote_inventory(listed)
    raw_by_key = {item.key: item for item in listed}
    return {
        archive.remote_key: (archive, raw_by_key[archive.remote_key])
        for archive in archives
    }


def _safe_snapshot_path(root: Path, *, client_repo: str, key: str) -> Path:
    if not key.startswith(_RUN_LOG_PREFIX):
        raise LayoutMigrationError("snapshot key is outside run-logs")
    relative = Path(*key.split("/"))
    path = root / client_repo / relative
    resolved_parent = path.parent.resolve()
    expected_parent = (root / client_repo).resolve()
    try:
        _ = resolved_parent.relative_to(expected_parent)
    except ValueError as exc:
        raise LayoutMigrationError("snapshot path escapes its client root") from exc
    return path


def _ensure_snapshot(
    *,
    store: MigrationStore,
    remote: run_log_sync.RemoteRunArchive,
    destination: Path,
) -> Path:
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if destination.is_symlink():
        raise LayoutMigrationError("snapshot archive path is a symlink")
    if destination.exists():
        entry = destination.stat(follow_symlinks=False)
        if stat.S_ISREG(entry.st_mode) and entry.st_size == remote.size:
            return destination
        destination.unlink()
    store.download(remote.remote_key, destination)
    entry = destination.stat(follow_symlinks=False)
    if not stat.S_ISREG(entry.st_mode) or entry.st_size != remote.size:
        raise LayoutMigrationError("downloaded snapshot size differs from listing")
    destination.chmod(0o600)
    return destination


def _materialize_modern(
    *, archive: Path, skill: str, run_id: str, parent: Path
) -> run_log_archive.RunArchiveMaterializationResult:
    run_dir = parent / run_id
    return run_log_archive.materialize_run_archive(
        archive_path=archive,
        run_dir=run_dir,
        expected_skill=skill,
        expected_run_id=run_id,
    )


def _materialize_legacy(
    *,
    archive: Path,
    skill: str,
    run_id: str,
    legacy: run_log_archive.LegacyRunArchive,
    parent: Path,
) -> run_log_archive.RunArchiveMaterializationResult:
    run_dir = parent / run_id
    return run_log_archive.materialize_legacy_run_archive(
        archive_path=archive,
        run_dir=run_dir,
        expected_skill=skill,
        expected_run_id=run_id,
        legacy=legacy,
    )


def _descriptor_json(
    descriptor: LegacyMigrationDescriptor | None,
) -> dict[str, str] | None:
    if descriptor is None:
        return None
    return {
        "inventory_key": descriptor.inventory_key,
        "inventory_sha256": descriptor.inventory_sha256,
        "schema": descriptor.schema,
        "source_commit": descriptor.source_commit,
        "storage_root": descriptor.storage_root,
    }


def _descriptor_from_json(raw: object) -> LegacyMigrationDescriptor | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise LayoutMigrationError("legacy descriptor is invalid")
    data = cast("dict[str, object]", raw)
    fields = (
        "schema",
        "source_commit",
        "storage_root",
        "inventory_key",
        "inventory_sha256",
    )
    if frozenset(data) != frozenset(fields) or any(
        not isinstance(data[field], str) for field in fields
    ):
        raise LayoutMigrationError("legacy descriptor fields are invalid")
    return LegacyMigrationDescriptor(
        schema=cast("str", data["schema"]),
        source_commit=cast("str", data["source_commit"]),
        storage_root=cast("str", data["storage_root"]),
        inventory_key=cast("str", data["inventory_key"]),
        inventory_sha256=cast("str", data["inventory_sha256"]),
    )


def _load_legacy_inventory(
    *,
    mapping: LayoutMapping,
    source_store: MigrationStore,
    work_dir: Path,
) -> run_log_migration.LegacyMigrationInventory | None:
    if mapping.legacy_descriptor is None:
        return None
    inventory_dir = work_dir / "inventory" / mapping.client_repo
    inventory_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    return run_log_migration.download_and_parse_inventory(
        store=source_store,
        descriptor=mapping.legacy_descriptor,
        storage_root=mapping.source,
        temporary_dir=inventory_dir,
    )


def _mapping_json(
    *,
    mapping: LayoutMapping,
    rows: list[dict[str, object]],
    target_existing: list[str],
) -> dict[str, object]:
    return {
        "archives": rows,
        "client_repo": mapping.client_repo,
        "legacy_descriptor": _descriptor_json(mapping.legacy_descriptor),
        "source_run_logs_uri": f"{mapping.source.uri}/{_RUN_LOG_PREFIX}",
        "source_uri": mapping.source.uri,
        "target_existing_keys": target_existing,
        "target_run_logs_uri": f"{mapping.target.uri}/{_RUN_LOG_PREFIX}",
        "target_uri": mapping.target.uri,
    }


def plan_layout_migration(  # noqa: PLR0913 - explicit operator inputs stay visible
    *,
    mappings: Sequence[LayoutMapping],
    output: Path,
    work_dir: Path,
    operator: str,
    tool_version: str,
    source_commit: str,
    store_factory: StoreFactory = object_store_for,
    live: bool = True,
) -> dict[str, object]:
    """Download, classify, and hash every frozen source archive."""
    if not operator.strip() or not tool_version.strip():
        raise LayoutMigrationError("operator and tool version are required")
    if (
        len(source_commit) != _GIT_COMMIT_HEX_LENGTH
        or any(character not in "0123456789abcdef" for character in source_commit)
    ):
        raise LayoutMigrationError("source commit must be lowercase 40-hex")
    work_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    rendered_mappings: list[dict[str, object]] = []
    for mapping in mappings:
        mapping.validate(live=live)
        source_store = store_factory(mapping.source)
        target_store = store_factory(mapping.target)
        source = _remote_map(source_store)
        target = _remote_map(target_store)
        extra_target = sorted(set(target) - set(source))
        if extra_target:
            raise LayoutMigrationError(
                f"target contains {len(extra_target)} key(s) absent from source"
            )
        inventory = _load_legacy_inventory(
            mapping=mapping,
            source_store=source_store,
            work_dir=work_dir,
        )
        legacy_by_key = (
            dict(inventory.run_archives) if inventory is not None else {}
        )
        missing_legacy = sorted(set(legacy_by_key) - set(source))
        if missing_legacy:
            raise LayoutMigrationError(
                f"legacy inventory has {len(missing_legacy)} missing source archive(s)"
            )
        rows: list[dict[str, object]] = []
        for index, key in enumerate(sorted(source), start=1):
            archive, remote = source[key]
            snapshot = _ensure_snapshot(
                store=source_store,
                remote=archive,
                destination=_safe_snapshot_path(
                    work_dir / "source",
                    client_repo=mapping.client_repo,
                    key=key,
                ),
            )
            digest = run_log_archive.sha256_file(snapshot)
            legacy = legacy_by_key.get(key)
            with tempfile.TemporaryDirectory(
                dir=work_dir,
                prefix=f".plan-{mapping.client_repo}-",
            ) as temporary:
                parent = Path(temporary)
                if legacy is None:
                    materialized = _materialize_modern(
                        archive=snapshot,
                        skill=archive.skill,
                        run_id=archive.run_id,
                        parent=parent,
                    )
                    kind = "modern"
                    transformation = "byte-copy"
                else:
                    materialized = _materialize_legacy(
                        archive=snapshot,
                        skill=archive.skill,
                        run_id=archive.run_id,
                        legacy=legacy,
                        parent=parent,
                    )
                    kind = "legacy"
                    transformation = "normalize-manifest"
            rows.append(
                {
                    "archive_kind": kind,
                    "expanded_bytes": materialized.expanded_size,
                    "member_count": materialized.member_count,
                    "run_id": archive.run_id,
                    "skill": archive.skill,
                    "source_etag": remote.etag,
                    "source_key": key,
                    "source_sha256": digest,
                    "source_size": archive.size,
                    "source_version": remote.version,
                    "target_key": key,
                    "transformation": transformation,
                }
            )
            if index % 100 == 0:
                print(
                    f"plan {mapping.client_repo}: validated {index}/{len(source)}",
                    file=sys.stderr,
                )
        rendered_mappings.append(
            _mapping_json(
                mapping=mapping,
                rows=rows,
                target_existing=sorted(target),
            )
        )
    payload = _self_hashed_payload(
        {
            "created_at": _now(),
            "mappings": rendered_mappings,
            "operator": operator.strip(),
            "schema": PLAN_SCHEMA,
            "source_commit": source_commit,
            "tool": config.LARCH_TOOL_NAME,
            "tool_version": tool_version.strip(),
        },
        digest_field="plan_sha256",
    )
    _write_json_atomic(output, payload)
    return payload


def _mappings_from_plan(
    plan: Mapping[str, object], *, live: bool
) -> tuple[tuple[LayoutMapping, tuple[dict[str, object], ...]], ...]:
    raw_mappings = plan.get("mappings")
    if not isinstance(raw_mappings, list) or not raw_mappings:
        raise LayoutMigrationError("migration plan mappings are invalid")
    result: list[tuple[LayoutMapping, tuple[dict[str, object], ...]]] = []
    for raw in cast("list[object]", raw_mappings):
        if not isinstance(raw, dict):
            raise LayoutMigrationError("migration plan mapping is invalid")
        data = cast("dict[str, object]", raw)
        client = data.get("client_repo")
        source_uri = data.get("source_uri")
        target_uri = data.get("target_uri")
        rows = data.get("archives")
        if (
            not isinstance(client, str)
            or not isinstance(source_uri, str)
            or not isinstance(target_uri, str)
            or not isinstance(rows, list)
        ):
            raise LayoutMigrationError("migration plan mapping fields are invalid")
        mapping = LayoutMapping(
            client_repo=client,
            source=parse_storage_base_uri(source_uri),
            target=parse_storage_base_uri(target_uri),
            legacy_descriptor=_descriptor_from_json(data.get("legacy_descriptor")),
        )
        mapping.validate(live=live)
        typed_rows: list[dict[str, object]] = []
        seen: set[str] = set()
        for row in cast("list[object]", rows):
            if not isinstance(row, dict):
                raise LayoutMigrationError("migration plan archive row is invalid")
            typed = cast("dict[str, object]", row)
            key = typed.get("source_key")
            if not isinstance(key, str) or key in seen:
                raise LayoutMigrationError("migration plan archive key is invalid")
            seen.add(key)
            typed_rows.append(typed)
        result.append((mapping, tuple(typed_rows)))
    return tuple(result)


def _row_string(row: Mapping[str, object], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value:
        raise LayoutMigrationError(f"migration row field is invalid: {field}")
    return value


def _row_int(row: Mapping[str, object], field: str) -> int:
    value = row.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise LayoutMigrationError(f"migration row field is invalid: {field}")
    return value


def _validate_frozen_source(
    *,
    store: MigrationStore,
    rows: Sequence[Mapping[str, object]],
) -> dict[str, tuple[run_log_sync.RemoteRunArchive, RemoteObject]]:
    source = _remote_map(store)
    planned = {_row_string(row, "source_key"): row for row in rows}
    if set(source) != set(planned):
        raise LayoutMigrationError("source inventory changed after planning")
    for key, row in planned.items():
        archive, remote = source[key]
        if archive.size != _row_int(row, "source_size"):
            raise LayoutMigrationError("source size changed after planning")
        for field, actual in (
            ("source_etag", remote.etag),
            ("source_version", remote.version),
        ):
            expected = row.get(field)
            if expected is not None and expected != actual:
                raise LayoutMigrationError(
                    f"source {field.removeprefix('source_')} changed after planning"
                )
    return source


def _candidate_archive(
    *,
    mapping: LayoutMapping,
    row: Mapping[str, object],
    source_archive: Path,
    inventory: run_log_migration.LegacyMigrationInventory | None,
    work_dir: Path,
) -> tuple[Path, run_log_archive.RunArchiveMaterializationResult]:
    skill = _row_string(row, "skill")
    run_id = _row_string(row, "run_id")
    kind = _row_string(row, "archive_kind")
    if kind == "modern":
        with tempfile.TemporaryDirectory(
            dir=work_dir,
            prefix=f".candidate-check-{mapping.client_repo}-",
        ) as temporary:
            materialized = _materialize_modern(
                archive=source_archive,
                skill=skill,
                run_id=run_id,
                parent=Path(temporary),
            )
        return source_archive, materialized
    if kind != "legacy" or inventory is None:
        raise LayoutMigrationError("migration row archive kind is invalid")
    legacy = inventory.archive_for(_row_string(row, "source_key"))
    if legacy is None:
        raise LayoutMigrationError("legacy migration row is absent from inventory")
    output_dir = (
        work_dir
        / "candidates"
        / mapping.client_repo
        / _RUN_LOG_PREFIX
        / skill
    )
    output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    candidate = output_dir / f"{run_id}.tar.gz"
    with tempfile.TemporaryDirectory(
        dir=work_dir,
        prefix=f".legacy-convert-{mapping.client_repo}-",
    ) as temporary:
        parent = Path(temporary)
        source_result = _materialize_legacy(
            archive=source_archive,
            skill=skill,
            run_id=run_id,
            legacy=legacy,
            parent=parent,
        )
        manifest = source_result.run_dir / _MANIFEST_NAME
        manifest.unlink()
        created = run_log_archive.create_run_archive(
            staging_root=source_result.run_dir,
            output_dir=output_dir,
            skill=skill,
            run_id=run_id,
        )
        if created.archive_path != candidate:
            raise LayoutMigrationError("legacy candidate path is unexpected")
    with tempfile.TemporaryDirectory(
        dir=work_dir,
        prefix=f".legacy-candidate-check-{mapping.client_repo}-",
    ) as temporary:
        target_result = _materialize_modern(
            archive=candidate,
            skill=skill,
            run_id=run_id,
            parent=Path(temporary),
        )
    return candidate, target_result


def _download_fresh(
    *,
    store: MigrationStore,
    key: str,
    destination: Path,
    expected_size: int,
) -> Path:
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)
    store.download(key, destination)
    entry = destination.stat(follow_symlinks=False)
    if not stat.S_ISREG(entry.st_mode) or entry.st_size != expected_size:
        raise LayoutMigrationError("downloaded target size differs from metadata")
    destination.chmod(0o600)
    return destination


def _verified_target(  # noqa: PLR0913 - verification binds all expected identities
    *,
    store: MigrationStore,
    key: str,
    candidate: Path,
    skill: str,
    run_id: str,
    work_dir: Path,
    client_repo: str,
) -> tuple[RemoteObject, str, run_log_archive.RunArchiveMaterializationResult]:
    metadata = store.metadata(key)
    expected_size = candidate.stat(follow_symlinks=False).st_size
    expected_digest = run_log_archive.sha256_file(candidate)
    if metadata.size != expected_size:
        raise LayoutMigrationError("target size differs from candidate")
    downloaded = _download_fresh(
        store=store,
        key=key,
        destination=_safe_snapshot_path(
            work_dir / "target",
            client_repo=client_repo,
            key=key,
        ),
        expected_size=metadata.size,
    )
    digest = run_log_archive.sha256_file(downloaded)
    if digest != expected_digest:
        raise LayoutMigrationError("target digest differs from candidate")
    with tempfile.TemporaryDirectory(
        dir=work_dir,
        prefix=f".target-check-{client_repo}-",
    ) as temporary:
        materialized = _materialize_modern(
            archive=downloaded,
            skill=skill,
            run_id=run_id,
            parent=Path(temporary),
        )
    return metadata, digest, materialized


def _report_base(plan: Mapping[str, object]) -> dict[str, object]:
    return {
        "completed_at": None,
        "plan_sha256": plan["plan_sha256"],
        "rows": [],
        "schema": REPORT_SCHEMA,
        "source_commit": plan["source_commit"],
        "source_objects_retained": True,
        "started_at": _now(),
        "target_writes_create_only": True,
        "tool_version": plan["tool_version"],
    }


def _load_or_create_report(
    *, path: Path, plan: Mapping[str, object]
) -> dict[str, object]:
    if not path.exists():
        return _report_base(plan)
    report = _read_json(path)
    if (
        report.get("schema") != REPORT_SCHEMA
        or report.get("plan_sha256") != plan.get("plan_sha256")
        or not isinstance(report.get("rows"), list)
    ):
        raise LayoutMigrationError("existing migration report is incompatible")
    return report


def _update_aggregate(
    values: dict[str, int], *, source_size: int, target_size: int
) -> None:
    values["archives"] = values.get("archives", 0) + 1
    values["source_bytes"] = values.get("source_bytes", 0) + source_size
    values["target_bytes"] = values.get("target_bytes", 0) + target_size


def _report_aggregates(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    by_client: dict[str, dict[str, int]] = {}
    by_client_skill: dict[str, dict[str, dict[str, int]]] = {}
    by_kind: dict[str, dict[str, int]] = {}
    by_status: dict[str, int] = {}
    for row in rows:
        client = _row_string(row, "client_repo")
        skill = _row_string(row, "skill")
        kind = _row_string(row, "archive_kind")
        status = _row_string(row, "status")
        source_size = _row_int(row, "source_size")
        target_size = _row_int(row, "target_size")

        for values in (
            by_client.setdefault(client, {}),
            by_client_skill.setdefault(client, {}).setdefault(skill, {}),
            by_kind.setdefault(kind, {}),
        ):
            _update_aggregate(
                values,
                source_size=source_size,
                target_size=target_size,
            )
        by_status[status] = by_status.get(status, 0) + 1
    return {
        "by_archive_kind": by_kind,
        "by_client": by_client,
        "by_client_and_skill": by_client_skill,
        "by_status": by_status,
        "total_archives": len(rows),
    }


def apply_layout_migration(  # noqa: C901,PLR0912,PLR0913,PLR0915 - one auditable transaction
    *,
    plan_path: Path,
    report_path: Path,
    work_dir: Path,
    authorized: bool,
    store_factory: StoreFactory = object_store_for,
    live: bool = True,
) -> dict[str, object]:
    """Create and verify every target archive without changing a source."""
    if not authorized:
        raise LayoutMigrationError("live migration apply requires authorization")
    plan = _verified_plan(plan_path)
    mappings = _mappings_from_plan(plan, live=live)
    work_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    report = _load_or_create_report(path=report_path, plan=plan)
    completed_rows: dict[tuple[str, str], dict[str, object]] = {}
    for raw in cast("list[object]", report["rows"]):
        if not isinstance(raw, dict):
            raise LayoutMigrationError("existing report row is invalid")
        row = cast("dict[str, object]", raw)
        completed_rows[
            (_row_string(row, "client_repo"), _row_string(row, "source_key"))
        ] = row
    for mapping, rows in mappings:
        source_store = store_factory(mapping.source)
        target_store = store_factory(mapping.target)
        source = _validate_frozen_source(store=source_store, rows=rows)
        target = _remote_map(target_store)
        planned_keys = {_row_string(row, "target_key") for row in rows}
        if not set(target).issubset(planned_keys):
            raise LayoutMigrationError("target contains an unplanned archive")
        inventory = _load_legacy_inventory(
            mapping=mapping,
            source_store=source_store,
            work_dir=work_dir,
        )
        for index, row in enumerate(rows, start=1):
            source_key = _row_string(row, "source_key")
            target_key = _row_string(row, "target_key")
            archive, _ = source[source_key]
            source_snapshot = _ensure_snapshot(
                store=source_store,
                remote=archive,
                destination=_safe_snapshot_path(
                    work_dir / "source",
                    client_repo=mapping.client_repo,
                    key=source_key,
                ),
            )
            if run_log_archive.sha256_file(source_snapshot) != _row_string(
                row, "source_sha256"
            ):
                raise LayoutMigrationError("source digest changed after planning")
            candidate, candidate_result = _candidate_archive(
                mapping=mapping,
                row=row,
                source_archive=source_snapshot,
                inventory=inventory,
                work_dir=work_dir,
            )
            status = "present"
            if target_key not in target:
                try:
                    _ = target_store.upload_create(target_key, candidate)
                    status = "created"
                except ObjectStoreError as exc:
                    if exc.kind is not ObjectStoreErrorKind.ALREADY_EXISTS:
                        raise
            metadata, target_digest, target_result = _verified_target(
                store=target_store,
                key=target_key,
                candidate=candidate,
                skill=_row_string(row, "skill"),
                run_id=_row_string(row, "run_id"),
                work_dir=work_dir,
                client_repo=mapping.client_repo,
            )
            report_row: dict[str, object] = {
                **row,
                "client_repo": mapping.client_repo,
                "error_token": None,
                "status": status,
                "target_etag": metadata.etag,
                "target_expanded_bytes": target_result.expanded_size,
                "target_member_count": target_result.member_count,
                "target_sha256": target_digest,
                "target_size": metadata.size,
                "target_version": metadata.version,
                "verified": True,
            }
            if (
                candidate_result.member_count != target_result.member_count
                or candidate_result.expanded_size != target_result.expanded_size
            ):
                raise LayoutMigrationError(
                    "target materialization differs from candidate"
                )
            completed_rows[(mapping.client_repo, source_key)] = report_row
            report["rows"] = [
                completed_rows[key] for key in sorted(completed_rows)
            ]
            report["completed_at"] = None
            _write_json_atomic(report_path, report)
            if index % 100 == 0:
                print(
                    f"apply {mapping.client_repo}: verified {index}/{len(rows)}",
                    file=sys.stderr,
                )
    final_rows = [
        completed_rows[key] for key in sorted(completed_rows)
    ]
    expected_count = sum(len(rows) for _, rows in mappings)
    if len(final_rows) != expected_count:
        raise LayoutMigrationError("migration report is incomplete")
    report["rows"] = final_rows
    report["aggregates"] = _report_aggregates(final_rows)
    report["completed_at"] = _now()
    _write_json_atomic(report_path, report)
    return report


def _verify_legacy_equivalence(
    *,
    run_dir: Path,
    legacy: run_log_archive.LegacyRunArchive,
) -> None:
    expected = {member.path: member for member in legacy.members}
    actual_files: dict[str, Path] = {}
    for path in run_dir.rglob("*"):
        relative = path.relative_to(run_dir).as_posix()
        if relative == _MANIFEST_NAME:
            continue
        entry = path.stat(follow_symlinks=False)
        if stat.S_ISREG(entry.st_mode):
            actual_files[relative] = path
        elif not stat.S_ISDIR(entry.st_mode):
            raise LayoutMigrationError("target contains an unsupported member type")
    if set(actual_files) != set(expected):
        raise LayoutMigrationError("legacy target members differ from inventory")
    for relative, path in actual_files.items():
        member = expected[relative]
        entry = path.stat(follow_symlinks=False)
        if (
            entry.st_size != member.size
            or stat.S_IMODE(entry.st_mode) != member.mode
            or run_log_archive.sha256_file(path) != member.sha256
        ):
            raise LayoutMigrationError(
                "legacy target member metadata differs from inventory"
            )


def _publish_exact_report(
    *,
    store: MigrationStore,
    key: str,
    report_path: Path,
    work_dir: Path,
) -> None:
    try:
        target = store.upload_create(key, report_path)
    except ObjectStoreError as exc:
        if exc.kind is not ObjectStoreErrorKind.ALREADY_EXISTS:
            raise
        target = store.metadata(key)
    if target.size != report_path.stat(follow_symlinks=False).st_size:
        raise LayoutMigrationError("published report size differs from local report")
    downloaded = work_dir / "published-report.json"
    downloaded.unlink(missing_ok=True)
    store.download(key, downloaded)
    if run_log_archive.sha256_file(downloaded) != run_log_archive.sha256_file(
        report_path
    ):
        raise LayoutMigrationError("published report digest differs from local report")


def verify_layout_migration(  # noqa: C901,PLR0912,PLR0913,PLR0915 - complete independent verification
    *,
    plan_path: Path,
    report_path: Path,
    final_report_path: Path,
    work_dir: Path,
    publish_report_key: str,
    authorized_publication: bool,
    store_factory: StoreFactory = object_store_for,
    live: bool = True,
) -> dict[str, object]:
    """Independently verify all sources, targets, transforms, and report rows."""
    if not authorized_publication:
        raise LayoutMigrationError("final report publication requires authorization")
    plan = _verified_plan(plan_path)
    mappings = _mappings_from_plan(plan, live=live)
    report = _read_json(report_path)
    if (
        report.get("schema") != REPORT_SCHEMA
        or report.get("plan_sha256") != plan.get("plan_sha256")
        or report.get("completed_at") is None
        or not isinstance(report.get("rows"), list)
    ):
        raise LayoutMigrationError("migration report is incomplete or incompatible")
    report_rows: dict[tuple[str, str], dict[str, object]] = {}
    for raw in cast("list[object]", report["rows"]):
        if not isinstance(raw, dict):
            raise LayoutMigrationError("migration report row is invalid")
        row = cast("dict[str, object]", raw)
        report_rows[
            (_row_string(row, "client_repo"), _row_string(row, "source_key"))
        ] = row
    verified_rows: list[dict[str, object]] = []
    publication_store: MigrationStore | None = None
    for mapping, rows in mappings:
        source_store = store_factory(mapping.source)
        target_store = store_factory(mapping.target)
        if mapping.client_repo == "larch":
            publication_store = target_store
        _ = _validate_frozen_source(store=source_store, rows=rows)
        target = _remote_map(target_store)
        planned_keys = {_row_string(row, "target_key") for row in rows}
        if set(target) != planned_keys:
            raise LayoutMigrationError("target inventory differs from plan")
        inventory = _load_legacy_inventory(
            mapping=mapping,
            source_store=source_store,
            work_dir=work_dir,
        )
        for index, row in enumerate(rows, start=1):
            source_key = _row_string(row, "source_key")
            report_row = report_rows.get((mapping.client_repo, source_key))
            if report_row is None or report_row.get("verified") is not True:
                raise LayoutMigrationError("migration report lacks a verified row")
            target_key = _row_string(row, "target_key")
            archive, remote = target[target_key]
            expected_size = _row_int(report_row, "target_size")
            if archive.size != expected_size:
                raise LayoutMigrationError("target size differs from migration report")
            snapshot = _download_fresh(
                store=target_store,
                key=target_key,
                destination=_safe_snapshot_path(
                    work_dir / "verify-target",
                    client_repo=mapping.client_repo,
                    key=target_key,
                ),
                expected_size=remote.size,
            )
            target_digest = run_log_archive.sha256_file(snapshot)
            if target_digest != _row_string(report_row, "target_sha256"):
                raise LayoutMigrationError(
                    "target digest differs from migration report"
                )
            skill = _row_string(row, "skill")
            run_id = _row_string(row, "run_id")
            with tempfile.TemporaryDirectory(
                dir=work_dir,
                prefix=f".verify-{mapping.client_repo}-",
            ) as temporary:
                materialized = _materialize_modern(
                    archive=snapshot,
                    skill=skill,
                    run_id=run_id,
                    parent=Path(temporary),
                )
                if _row_string(row, "archive_kind") == "legacy":
                    if inventory is None:
                        raise LayoutMigrationError(
                            "legacy target has no pinned inventory"
                        )
                    legacy = inventory.archive_for(source_key)
                    if legacy is None:
                        raise LayoutMigrationError(
                            "legacy target is absent from pinned inventory"
                        )
                    _verify_legacy_equivalence(
                        run_dir=materialized.run_dir,
                        legacy=legacy,
                    )
                elif target_digest != _row_string(row, "source_sha256"):
                    raise LayoutMigrationError(
                        "modern target is not byte-identical to source"
                    )
            verified_rows.append(
                {
                    "archive_kind": _row_string(row, "archive_kind"),
                    "client_repo": mapping.client_repo,
                    "run_id": run_id,
                    "skill": skill,
                    "source_key": source_key,
                    "target_key": target_key,
                    "target_sha256": target_digest,
                    "target_size": remote.size,
                    "verified": True,
                }
            )
            if index % 100 == 0:
                print(
                    f"verify {mapping.client_repo}: validated {index}/{len(rows)}",
                    file=sys.stderr,
                )
    if len(verified_rows) != sum(len(rows) for _, rows in mappings):
        raise LayoutMigrationError("independent verification is incomplete")
    final = _self_hashed_payload(
        {
            "apply_completed_at": report["completed_at"],
            "independent_verification": {
                "completed_at": _now(),
                "rows": verified_rows,
                "target_manifestless_archives": 0,
                "verified_archives": len(verified_rows),
            },
            "migration_aggregates": report.get("aggregates"),
            "migration_plan_sha256": plan["plan_sha256"],
            "schema": FINAL_REPORT_SCHEMA,
            "source_commit": plan["source_commit"],
            "source_objects_retained": True,
            "target_writes_create_only": True,
            "tool_version": plan["tool_version"],
        },
        digest_field="report_sha256",
    )
    _write_json_atomic(final_report_path, final)
    if publication_store is None:
        raise LayoutMigrationError("larch target store is absent")
    if (
        not publish_report_key.startswith("migration-reports/")
        or publish_report_key.endswith("/")
        or not publish_report_key.endswith(".json")
    ):
        raise LayoutMigrationError("published report key is invalid")
    _publish_exact_report(
        store=publication_store,
        key=publish_report_key,
        report_path=final_report_path,
        work_dir=work_dir,
    )
    return final


def _live_mappings(args: argparse.Namespace) -> tuple[LayoutMapping, LayoutMapping]:
    descriptor = LegacyMigrationDescriptor(
        schema=args.legacy_schema,
        source_commit=args.legacy_source_commit,
        storage_root=args.larch_source_uri,
        inventory_key=args.legacy_inventory_key,
        inventory_sha256=args.legacy_inventory_sha256,
    )
    return (
        LayoutMapping(
            "larch",
            parse_storage_base_uri(args.larch_source_uri),
            parse_storage_base_uri(args.larch_target_uri),
            descriptor,
        ),
        LayoutMapping(
            "agent-lint",
            parse_storage_base_uri(args.agent_lint_source_uri),
            parse_storage_base_uri(args.agent_lint_target_uri),
        ),
    )


def _add_live_roots(parser: argparse.ArgumentParser) -> None:
    _ = parser.add_argument("--larch-source-uri", required=True)
    _ = parser.add_argument("--larch-target-uri", required=True)
    _ = parser.add_argument("--agent-lint-source-uri", required=True)
    _ = parser.add_argument("--agent-lint-target-uri", required=True)
    _ = parser.add_argument("--legacy-schema", required=True)
    _ = parser.add_argument("--legacy-source-commit", required=True)
    _ = parser.add_argument("--legacy-inventory-key", required=True)
    _ = parser.add_argument("--legacy-inventory-sha256", required=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cli.py run-log migrate-layout")
    subparsers = parser.add_subparsers(dest="phase", required=True)
    plan = subparsers.add_parser("plan")
    _add_live_roots(plan)
    _ = plan.add_argument("--output", type=Path, required=True)
    _ = plan.add_argument("--work-dir", type=Path, required=True)
    _ = plan.add_argument("--operator", required=True)
    _ = plan.add_argument("--tool-version", required=True)
    _ = plan.add_argument("--source-commit", required=True)
    apply = subparsers.add_parser("apply")
    _ = apply.add_argument("--plan", type=Path, required=True)
    _ = apply.add_argument("--report", type=Path, required=True)
    _ = apply.add_argument("--work-dir", type=Path, required=True)
    _ = apply.add_argument("--authorize-live-migration", action="store_true")
    verify = subparsers.add_parser("verify")
    _ = verify.add_argument("--plan", type=Path, required=True)
    _ = verify.add_argument("--report", type=Path, required=True)
    _ = verify.add_argument("--final-report", type=Path, required=True)
    _ = verify.add_argument("--work-dir", type=Path, required=True)
    _ = verify.add_argument("--publish-report-key", required=True)
    _ = verify.add_argument("--authorize-report-publication", action="store_true")
    return parser


def main(argv: Sequence[str]) -> int:
    """Run one migration phase and emit a closed machine envelope."""
    try:
        args = _parser().parse_args(argv)
        if args.phase == "plan":
            plan = plan_layout_migration(
                mappings=_live_mappings(args),
                output=args.output,
                work_dir=args.work_dir,
                operator=args.operator,
                tool_version=args.tool_version,
                source_commit=args.source_commit,
            )
            mappings = cast("list[dict[str, object]]", plan["mappings"])
            archives = sum(
                len(cast("list[object]", mapping["archives"]))
                for mapping in mappings
            )
            print(f"PLAN_PATH={args.output}")
            print(f"PLAN_SHA256={plan['plan_sha256']}")
            print(f"PLANNED_ARCHIVES={archives}")
            print("MIGRATION_PLAN_OK=true")
            return config.EXIT_OK
        if args.phase == "apply":
            report = apply_layout_migration(
                plan_path=args.plan,
                report_path=args.report,
                work_dir=args.work_dir,
                authorized=args.authorize_live_migration,
            )
            rows = cast("list[object]", report["rows"])
            print(f"REPORT_PATH={args.report}")
            print(f"MIGRATED_ARCHIVES={len(rows)}")
            print("SOURCES_RETAINED=true")
            print("MIGRATION_APPLY_OK=true")
            return config.EXIT_OK
        final = verify_layout_migration(
            plan_path=args.plan,
            report_path=args.report,
            final_report_path=args.final_report,
            work_dir=args.work_dir,
            publish_report_key=args.publish_report_key,
            authorized_publication=args.authorize_report_publication,
        )
        verified = cast(
            "dict[str, object]", final["independent_verification"]
        )["verified_archives"]
        print(f"FINAL_REPORT_PATH={args.final_report}")
        print(f"FINAL_REPORT_SHA256={final['report_sha256']}")
        print(f"VERIFIED_ARCHIVES={verified}")
        print(f"PUBLISHED_REPORT_KEY={args.publish_report_key}")
        print("MIGRATION_VERIFY_OK=true")
        return config.EXIT_OK
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else config.EXIT_USAGE
    except (
        EOFError,
        LayoutMigrationError,
        ObjectStoreError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"run-log migrate-layout failed: {exc}", file=sys.stderr)
        return config.EXIT_INTERNAL_ERROR
