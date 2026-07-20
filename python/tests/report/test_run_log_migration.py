"""Tests for the repository-pinned legacy migration inventory parser."""

from __future__ import annotations

import copy
import json
from typing import cast

import pytest

from larch.report import run_log_migration
from larch.report.storage_config import LegacyMigrationDescriptor, StorageRoot


def _descriptor() -> LegacyMigrationDescriptor:
    return LegacyMigrationDescriptor(
        schema="larch-run-log-migration-inventory-v1",
        source_commit="a" * 40,
        storage_root="s3://bucket/larch",
        inventory_key="migration/inventory.json",
        inventory_sha256="b" * 64,
    )


def _payload() -> dict[str, object]:
    archive_key = "larch/run-logs/implement/legacy-run.tar.gz"
    return {
        "archives": [
            {
                "archive_bytes": 100,
                "kind": "run",
                "member_count": 1,
                "object_key": archive_key,
                "run_id": "legacy-run",
                "sha256": "c" * 64,
                "skill": "implement",
                "uncompressed_bytes": 7,
            }
        ],
        "schema": "larch-run-log-migration-inventory-v1",
        "source_commit": "a" * 40,
        "source_files": [
            {
                "archive_member_path": "result.txt",
                "archive_object_key": archive_key,
                "bytes": 7,
                "git_oid": "d" * 40,
                "mode": "100644",
                "path": "larch-logs/implement/legacy-run/result.txt",
                "sha256": "e" * 64,
            }
        ],
        "storage_root": "s3://bucket/larch",
        "totals": {
            "archive_bytes": 100,
            "archive_objects": 1,
            "members": 1,
            "run_directories": 1,
            "source_paths": 1,
            "uncompressed_bytes": 7,
        },
    }


def _parse(payload: dict[str, object]) -> run_log_migration.LegacyMigrationInventory:
    return run_log_migration.parse_inventory(
        json.dumps(payload).encode(),
        descriptor=_descriptor(),
        storage_root=StorageRoot("s3", "bucket", "larch"),
    )


def test_parse_inventory_accepts_exact_bounded_schema() -> None:
    inventory = _parse(_payload())

    record = inventory.archive_for("run-logs/implement/legacy-run.tar.gz")

    assert record is not None
    assert record.archive_size == 100
    assert record.member_count == 1
    assert record.members[0].path == "result.txt"


def test_parse_inventory_rejects_duplicate_json_keys() -> None:
    encoded = json.dumps(_payload()).encode()
    duplicate = encoded.replace(b'"schema":', b'"schema":"duplicate","schema":', 1)

    with pytest.raises(ValueError, match="duplicate migration inventory key"):
        _ = run_log_migration.parse_inventory(
            duplicate,
            descriptor=_descriptor(),
            storage_root=StorageRoot("s3", "bucket", "larch"),
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("path", "archive member path is unsafe"),
        ("source_commit", "source commit"),
        ("storage_root", "storage root"),
        ("digest", "source-file digest"),
        ("size", "source-file bytes"),
        ("archive_limit", "member-count limit"),
        ("totals", "global totals"),
        ("duplicate_member", "duplicate or case-colliding migration members"),
    ],
)
def test_parse_inventory_rejects_malformed_or_inconsistent_rows(
    mutation: str,
    message: str,
) -> None:
    payload = copy.deepcopy(_payload())
    archives = cast("list[dict[str, object]]", payload["archives"])
    sources = cast("list[dict[str, object]]", payload["source_files"])
    totals = cast("dict[str, object]", payload["totals"])
    source: dict[str, object] = sources[0]
    if mutation == "path":
        source["archive_member_path"] = "../escape.txt"
    elif mutation == "source_commit":
        payload["source_commit"] = "f" * 40
    elif mutation == "storage_root":
        payload["storage_root"] = "s3://other/larch"
    elif mutation == "digest":
        source["sha256"] = "z" * 64
    elif mutation == "size":
        source["bytes"] = -1
    elif mutation == "archive_limit":
        archives[0]["member_count"] = 10_001
    elif mutation == "totals":
        totals["members"] = 2
    elif mutation == "duplicate_member":
        sources.append(copy.deepcopy(source))
        totals["members"] = 2
        totals["source_paths"] = 2
        archives[0]["member_count"] = 2
        archives[0]["uncompressed_bytes"] = 14
        totals["uncompressed_bytes"] = 14
    else:
        pytest.fail(f"unhandled mutation: {mutation}")

    with pytest.raises(ValueError, match=message):
        _ = _parse(payload)
