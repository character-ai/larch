"""Greedy LPT (Longest-Processing-Time) bin packer for test harness shards.

The classic LPT heuristic sorts jobs slowest-first and assigns each to the
currently lightest bin (min-heap over cumulative shard totals).  This
guarantees the two slowest tests are never in the same shard, and minimises
the makespan (max shard total) across all heterogeneous job sizes.

Public surface:

- ``pack(medians, n_shards, *, guard, extras)`` → ``{shard_n: [target, ...]}``
"""

from __future__ import annotations

import heapq


def pack(
    *, medians: dict[str, float],
    n_shards: int,
    guard: str = "test-harness-shards-coverage",
    extras: list[str] | None = None,
) -> dict[int, list[str]]:
    """Distribute test targets across *n_shards* using greedy LPT.

    Algorithm
    ---------
    1. Sort all *measured* targets slowest-to-fastest by their median seconds.
    2. Maintain a min-heap of ``(cumulative_total, shard_id)`` initialised to
       zero for every shard.
    3. For each target (slowest first), pop the lightest shard, assign the
       target to it, push ``(total + target_seconds, shard_id)`` back.
    4. Append *extras* (targets with no timing data) using the same heap so
       they fill the lightest shards rather than always landing at the tail.
    5. Move *guard* to position 0 in whichever shard it lands in.  This
       satisfies the ``test-harness-shards-coverage`` first-prerequisite
       invariant enforced by the partition checker.

    Parameters
    ----------
    medians:
        ``{target: median_seconds}`` from ``harness_ci_timing.compute_medians``.
    n_shards:
        Number of output shards (must be ≥ 1).
    guard:
        Target that must appear first in its shard.  Pass ``""`` to disable.
    extras:
        Targets that have no timing data (e.g. newly added tests).

    Returns
    -------
    ``{shard_n (1-based): [target, ...]}``

    """
    if n_shards < 1:
        msg = f"n_shards must be ≥ 1, got {n_shards}"
        raise ValueError(msg)

    sorted_targets = sorted(medians, key=lambda t: medians[t], reverse=True)
    all_targets = sorted_targets + (extras or [])

    shards: dict[int, list[str]] = {i: [] for i in range(1, n_shards + 1)}
    # heap entries: (cumulative_seconds, item_count, shard_id). The item_count
    # secondary key makes zero-weight targets (extras with no timing data) fan
    # out round-robin instead of avalanching onto one shard: a 0.0-weight target
    # leaves the popped shard's total unchanged, so without the count tiebreak
    # that shard stays lightest and every subsequent 0-weight target piles onto
    # it. shard_id remains the final tiebreak for determinism.
    heap: list[tuple[float, int, int]] = [(0.0, 0, i) for i in range(1, n_shards + 1)]
    heapq.heapify(heap)

    for target in all_targets:
        total, count, shard_id = heapq.heappop(heap)
        shards[shard_id].append(target)
        heapq.heappush(heap, (total + medians.get(target, 0.0), count + 1, shard_id))

    # Ensure guard is first in its assigned shard (structural invariant)
    if guard:
        for shard_list in shards.values():
            if guard in shard_list:
                shard_list.remove(guard)
                shard_list.insert(0, guard)
                break

    return shards
