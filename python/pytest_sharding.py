"""Round-robin sharding for the pytest suite (issue #4407).

The ``python-tests`` CI job fans out into several matrix sub-jobs, each running
about ``1/PYTEST_SHARD_COUNT`` of the unit tests, to speed up CI. ``conftest.py``
calls into this module from ``pytest_collection_modifyitems`` to keep only the
tests assigned to the current shard.

Sharding is controlled by two environment variables:

- ``PYTEST_SHARD_COUNT`` -- total number of shards (>= 1).
- ``PYTEST_SHARD_ID``    -- 1-based index of this shard, in [1, PYTEST_SHARD_COUNT].

When neither is set (the default for local ``make py-test`` and for targeted
harness runs) the full collection runs. Assignment is round-robin by collection
index, which keeps shard sizes within one test of each other by count; the
per-test timing output (``make py-test`` runs pytest with ``--durations=0``)
provides the data to repartition by wall time later.
"""

from __future__ import annotations

from collections.abc import Mapping

ENV_SHARD_ID = "PYTEST_SHARD_ID"
ENV_SHARD_COUNT = "PYTEST_SHARD_COUNT"


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


def select_shard_indices(num_items: int, shard_id: int, shard_count: int) -> set[int]:
    """Return the 0-based collection indices assigned to this shard.

    Round-robin: collected item ``i`` belongs to shard ``(i % shard_count) + 1``.
    """
    return {i for i in range(num_items) if i % shard_count == shard_id - 1}
