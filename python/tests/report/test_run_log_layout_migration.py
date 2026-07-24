"""Tests for the create-only tool-first run-log layout migration."""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import cast

import pytest

from larch.report import run_log_archive, run_log_layout_migration
from larch.report.object_store import (
    ObjectStoreError,
    ObjectStoreErrorKind,
    RemoteObject,
)
from larch.report.storage_config import LegacyMigrationDescriptor, StorageBase


class _Store:
    def __init__(self, objects: dict[str, bytes] | None = None) -> None:
        self.objects = {} if objects is None else dict(objects)
        self.uploaded: list[str] = []

    def list_objects(self, prefix: str = "") -> tuple[RemoteObject, ...]:
        return tuple(
            RemoteObject(
                key,
                len(value),
                hashlib.sha256(value).hexdigest(),
                None,
            )
            for key, value in sorted(self.objects.items())
            if key.startswith(prefix)
        )

    def download(self, key: str, destination: Path) -> None:
        _ = destination.write_bytes(self.objects[key])

    def upload_create(self, key: str, source: Path) -> RemoteObject:
        if key in self.objects:
            raise ObjectStoreError(
                ObjectStoreErrorKind.ALREADY_EXISTS,
                "s3",
                "upload",
            )
        value = source.read_bytes()
        self.objects[key] = value
        self.uploaded.append(key)
        return RemoteObject(
            key,
            len(value),
            hashlib.sha256(value).hexdigest(),
            None,
        )

    def metadata(self, key: str) -> RemoteObject:
        value = self.objects[key]
        return RemoteObject(
            key,
            len(value),
            hashlib.sha256(value).hexdigest(),
            None,
        )


def _modern_archive(
    tmp_path: Path, *, skill: str, run_id: str, content: bytes
) -> bytes:
    staging = tmp_path / f"staging-{run_id}"
    staging.mkdir()
    _ = (staging / "result.txt").write_bytes(content)
    output = tmp_path / f"output-{run_id}"
    output.mkdir()
    result = run_log_archive.create_run_archive(
        staging_root=staging,
        output_dir=output,
        skill=skill,
        run_id=run_id,
    )
    return result.archive_path.read_bytes()


def _legacy_archive(content: bytes) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        info = tarfile.TarInfo("result.txt")
        info.size = len(content)
        info.mode = 0o644
        archive.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


def _legacy_inventory(*, archive: bytes, content: bytes) -> bytes:
    archive_key = "larch/run-logs/design/legacy-run.tar.gz"
    payload = {
        "archives": [
            {
                "archive_bytes": len(archive),
                "kind": "run",
                "member_count": 1,
                "object_key": archive_key,
                "run_id": "legacy-run",
                "sha256": hashlib.sha256(archive).hexdigest(),
                "skill": "design",
                "uncompressed_bytes": len(content),
            }
        ],
        "schema": "larch-run-log-migration-inventory-v1",
        "source_commit": "1" * 40,
        "source_files": [
            {
                "archive_member_path": "result.txt",
                "archive_object_key": archive_key,
                "bytes": len(content),
                "git_oid": "2" * 40,
                "mode": "100644",
                "path": "larch-logs/design/legacy-run/result.txt",
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        ],
        "storage_root": "s3://test/larch",
        "totals": {
            "archive_bytes": len(archive),
            "archive_objects": 1,
            "members": 1,
            "run_directories": 1,
            "source_paths": 1,
            "uncompressed_bytes": len(content),
        },
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def _fixture(
    tmp_path: Path,
) -> tuple[
    tuple[run_log_layout_migration.LayoutMapping, ...],
    dict[str, _Store],
]:
    legacy_content = b"legacy\n"
    legacy = _legacy_archive(legacy_content)
    inventory = _legacy_inventory(archive=legacy, content=legacy_content)
    modern = _modern_archive(
        tmp_path,
        skill="issue",
        run_id="modern-run",
        content=b"modern\n",
    )
    larch_source = _Store(
        {
            "migration/inventory.json": inventory,
            "run-logs/design/legacy-run.tar.gz": legacy,
            "run-logs/issue/modern-run.tar.gz": modern,
        }
    )
    larch_target = _Store(
        {"run-logs/issue/modern-run.tar.gz": modern}
    )
    agent = _modern_archive(
        tmp_path,
        skill="triage",
        run_id="agent-run",
        content=b"agent\n",
    )
    agent_source = _Store({"run-logs/triage/agent-run.tar.gz": agent})
    agent_target = _Store()
    stores = {
        "s3://test/larch": larch_source,
        "s3://test/larch/larch": larch_target,
        "s3://test/agent-lint": agent_source,
        "s3://test/larch/agent-lint": agent_target,
    }
    descriptor = LegacyMigrationDescriptor(
        schema="larch-run-log-migration-inventory-v1",
        source_commit="1" * 40,
        storage_root="s3://test/larch",
        inventory_key="migration/inventory.json",
        inventory_sha256=hashlib.sha256(inventory).hexdigest(),
    )
    mappings = (
        run_log_layout_migration.LayoutMapping(
            "larch",
            StorageBase("s3", "test", "larch"),
            StorageBase("s3", "test", "larch/larch"),
            descriptor,
        ),
        run_log_layout_migration.LayoutMapping(
            "agent-lint",
            StorageBase("s3", "test", "agent-lint"),
            StorageBase("s3", "test", "larch/agent-lint"),
        ),
    )
    return mappings, stores


def test_plan_apply_verify_normalizes_legacy_and_preserves_modern(
    tmp_path: Path,
) -> None:
    mappings, stores = _fixture(tmp_path)

    def factory(root: StorageBase) -> _Store:
        return stores[root.uri]

    plan_path = tmp_path / "plan.json"
    report_path = tmp_path / "report.json"
    final_path = tmp_path / "final.json"
    work_dir = tmp_path / "work"

    plan = run_log_layout_migration.plan_layout_migration(
        mappings=mappings,
        output=plan_path,
        work_dir=work_dir,
        operator="test-operator",
        tool_version="test",
        source_commit="a" * 40,
        store_factory=factory,
        live=False,
    )
    report = run_log_layout_migration.apply_layout_migration(
        plan_path=plan_path,
        report_path=report_path,
        work_dir=work_dir,
        authorized=True,
        store_factory=factory,
        live=False,
    )
    final = run_log_layout_migration.verify_layout_migration(
        plan_path=plan_path,
        report_path=report_path,
        final_report_path=final_path,
        work_dir=work_dir,
        publish_report_key="migration-reports/final.json",
        authorized_publication=True,
        store_factory=factory,
        live=False,
    )

    assert plan["schema"] == run_log_layout_migration.PLAN_SCHEMA
    report_rows = cast("list[object]", report["rows"])
    verification = cast("dict[str, object]", final["independent_verification"])
    assert len(report_rows) == 3
    assert verification["verified_archives"] == 3
    assert not stores["s3://test/larch"].uploaded
    assert not stores["s3://test/agent-lint"].uploaded
    larch_target = stores["s3://test/larch/larch"]
    assert "run-logs/design/legacy-run.tar.gz" in larch_target.uploaded
    assert "run-logs/issue/modern-run.tar.gz" not in larch_target.uploaded
    assert (
        larch_target.objects["run-logs/design/legacy-run.tar.gz"]
        != stores["s3://test/larch"].objects[
            "run-logs/design/legacy-run.tar.gz"
        ]
    )
    assert (
        larch_target.objects["run-logs/issue/modern-run.tar.gz"]
        == stores["s3://test/larch"].objects[
            "run-logs/issue/modern-run.tar.gz"
        ]
    )
    assert "migration-reports/final.json" in larch_target.objects


def test_plan_rejects_target_only_archive(tmp_path: Path) -> None:
    mappings, stores = _fixture(tmp_path)
    stores["s3://test/larch/larch"].objects[
        "run-logs/release/target-only.tar.gz"
    ] = _modern_archive(
        tmp_path,
        skill="release",
        run_id="target-only",
        content=b"target\n",
    )

    with pytest.raises(
        run_log_layout_migration.LayoutMigrationError,
        match="absent from source",
    ):
        _ = run_log_layout_migration.plan_layout_migration(
            mappings=mappings,
            output=tmp_path / "plan.json",
            work_dir=tmp_path / "work",
            operator="test-operator",
            tool_version="test",
            source_commit="a" * 40,
            store_factory=lambda root: stores[root.uri],
            live=False,
        )


def test_apply_requires_authorization(tmp_path: Path) -> None:
    mappings, stores = _fixture(tmp_path)
    plan_path = tmp_path / "plan.json"
    _ = run_log_layout_migration.plan_layout_migration(
        mappings=mappings,
        output=plan_path,
        work_dir=tmp_path / "work",
        operator="test-operator",
        tool_version="test",
        source_commit="a" * 40,
        store_factory=lambda root: stores[root.uri],
        live=False,
    )

    with pytest.raises(
        run_log_layout_migration.LayoutMigrationError,
        match="requires authorization",
    ):
        _ = run_log_layout_migration.apply_layout_migration(
            plan_path=plan_path,
            report_path=tmp_path / "report.json",
            work_dir=tmp_path / "work",
            authorized=False,
            store_factory=lambda root: stores[root.uri],
            live=False,
        )
