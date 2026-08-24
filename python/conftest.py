"""Temporary pytest sharding hook for the remaining Python tooling tests."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest_sharding

if TYPE_CHECKING:
    import pytest


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Keep only tests assigned to the active CI shard."""
    parsed = pytest_sharding.read_shard_env(os.environ)
    if parsed is None:
        return

    shard_id, shard_count = parsed
    nodeids = [item.nodeid for item in items]
    assignments = pytest_sharding.load_shard_assignments()
    keep = pytest_sharding.select_shard_nodeids(
        nodeids=nodeids,
        shard_id=shard_id,
        shard_count=shard_count,
        assignments=assignments,
    )
    selected = [item for index, item in enumerate(items) if index in keep]
    deselected = [item for index, item in enumerate(items) if index not in keep]
    if deselected:
        config.hook.pytest_deselected(items=deselected)
    items[:] = selected
