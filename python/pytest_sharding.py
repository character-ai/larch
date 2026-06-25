"""Round-robin and assignment-map sharding for the pytest suite (issue #4407)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

ENV_SHARD_ID = "PYTEST_SHARD_ID"
ENV_SHARD_COUNT = "PYTEST_SHARD_COUNT"
DEFAULT_ASSIGNMENTS_PATH = Path(__file__).with_name("shard-assignments.json")


def read_shard_env(environ: Mapping[str, str]) -> tuple[int, int] | None:
    """Parse the shard assignment from ``environ``.

    Returns ``(shard_id, shard_count)`` when both variables are set, or ``None``
    when neither is set (run the full suite). Raises ``ValueError`` when only
    one is set or a value is non-numeric or out of range.
    """
    raw_id = environ.get(ENV_SHARD_ID)
    raw_count = environ.get(ENV_SHARD_COUNT)
    if raw_id is None and raw_count is None:
        return None
    if raw_id is None or raw_count is None:
        raise ValueError(
            f"{ENV_SHARD_ID} and {ENV_SHARD_COUNT} must both be set or both be unset"
        )
    shard_count = int(raw_count)
    shard_id = int(raw_id)
    if shard_count < 1:
        raise ValueError(f"{ENV_SHARD_COUNT} must be >= 1, got {shard_count}")
    if not 1 <= shard_id <= shard_count:
        raise ValueError(
            f"{ENV_SHARD_ID} must be in [1, {shard_count}], got {shard_id}"
        )
    return shard_id, shard_count


def select_shard_indices(*, num_items: int, shard_id: int, shard_count: int) -> set[int]:
    """Return the 0-based collection indices assigned to this shard.

    Round-robin: collected item ``i`` belongs to shard ``(i % shard_count) + 1``.
    """
    return {i for i in range(num_items) if i % shard_count == shard_id - 1}


def load_shard_assignments(path: Path = DEFAULT_ASSIGNMENTS_PATH) -> dict[str, int]:
    """Load a checked-in ``nodeid -> shard_id`` assignment map."""
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"malformed shard assignments JSON: {exc}"
        raise ValueError(msg) from exc
    if not isinstance(raw, dict):
        msg = "shard assignments JSON must be an object"
        raise ValueError(msg)  # noqa: TRY004
    raw_map = cast("dict[object, object]", raw)
    assignments: dict[str, int] = {}
    for key, value in raw_map.items():
        if not isinstance(key, str):
            msg = "shard assignment keys must be strings"
            raise ValueError(msg)  # noqa: TRY004
        if isinstance(value, bool) or type(value) is not int:  # pylint: disable=unidiomatic-typecheck
            msg = f"shard id for {key!r} must be a JSON integer"
            raise ValueError(msg)
        if value < 1:
            msg = f"shard id for {key!r} must be >= 1"
            raise ValueError(msg)
        assignments[key] = value
    return assignments


def select_shard_nodeids(
    *, nodeids: list[str],
    shard_id: int,
    shard_count: int,
    assignments: Mapping[str, int],
) -> set[int]:
    """Return collection indices assigned to this shard.

    A non-empty map whose maximum shard id does not match the runtime shard
    count is ignored so checked-in maps can never reduce coverage.
    """
    if assignments and max(assignments.values()) != shard_count:
        return select_shard_indices(num_items=len(nodeids), shard_id=shard_id, shard_count=shard_count)

    keep: set[int] = set()
    for index, nodeid in enumerate(nodeids):
        assigned = assignments.get(nodeid)
        if assigned is None:
            if index % shard_count == shard_id - 1:
                keep.add(index)
        elif assigned == shard_id:
            keep.add(index)
    return keep
