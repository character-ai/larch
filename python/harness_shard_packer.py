"""Round-robin LPT (Longest-Processing-Time) bin packer for test harness shards.

The classic LPT heuristic sorts jobs slowest-first and assigns each to the
currently lightest bin.  For N shards that naturally degenerates to simple
round-robin: slow[0]→shard[0], slow[1]→shard[1], …, slow[N-1]→shard[N-1],
slow[N]→shard[0], …  This guarantees the two slowest tests are never in the
same shard, and the spread is provably close to optimal for uniform machines.

Public surface:

- ``pack(medians, n_shards, *, guard, extras)`` → ``{shard_n: [target, ...]}``
"""

from __future__ import annotations


def pack(
    medians: dict[str, float],
    n_shards: int,
    *,
    guard: str = "test-harness-shards-coverage",
    extras: list[str] | None = None,
) -> dict[int, list[str]]:
    """Distribute test targets across *n_shards* using round-robin LPT.

    Algorithm
    ---------
    1. Sort all *measured* targets slowest-to-fastest by their median seconds.
    2. Assign ``sorted_targets[i]`` to shard ``(i % n_shards) + 1`` (1-based).
    3. Append *extras* (targets with no timing data) at the end, distributed
       the same way — they act as 0-second items and fill the tail evenly.
    4. Move *guard* to position 0 in whichever shard it lands in.  This
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
    for i, target in enumerate(all_targets):
        shards[(i % n_shards) + 1].append(target)

    # Ensure guard is first in its assigned shard (structural invariant)
    if guard:
        for shard_list in shards.values():
            if guard in shard_list:
                shard_list.remove(guard)
                shard_list.insert(0, guard)
                break

    return shards
