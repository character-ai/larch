"""Tests for harness_shard_packer."""

from __future__ import annotations

import pytest

from harness_shard_packer import pack


def test_pack_basic_round_robin() -> None:
    # 4 tests, 2 shards — sorted slowest-first: a(10), b(8), c(6), d(4)
    # round-robin: a→1, b→2, c→1, d→2
    medians = {"test-a": 10.0, "test-b": 8.0, "test-c": 6.0, "test-d": 4.0}
    shards = pack(medians, 2, guard="")
    assert "test-a" in shards[1]
    assert "test-b" in shards[2]
    assert "test-c" in shards[1]
    assert "test-d" in shards[2]


def test_pack_slowest_tests_in_different_shards() -> None:
    medians = {
        "test-slow1": 100.0,
        "test-slow2": 90.0,
        "test-fast1": 1.0,
        "test-fast2": 0.5,
    }
    shards = pack(medians, 2, guard="")
    shard_s1 = next(n for n, ts in shards.items() if "test-slow1" in ts)
    shard_s2 = next(n for n, ts in shards.items() if "test-slow2" in ts)
    assert shard_s1 != shard_s2, "two slowest tests must land in different shards"


def test_pack_guard_is_first() -> None:
    medians = {"test-a": 10.0, "test-guard": 0.1, "test-b": 5.0}
    shards = pack(medians, 2, guard="test-guard")
    for shard_n, targets in shards.items():
        if "test-guard" in targets:
            assert targets[0] == "test-guard", f"guard must be first in shard {shard_n}"
            return
    pytest.fail("guard not found in any shard")


def test_pack_guard_not_in_medians_still_placed() -> None:
    # guard appears only as an extra (no timing data)
    medians = {"test-a": 5.0, "test-b": 3.0}
    shards = pack(medians, 2, guard="test-guard", extras=["test-guard", "test-c"])
    guard_shards = [n for n, ts in shards.items() if "test-guard" in ts]
    assert len(guard_shards) == 1
    shard_n = guard_shards[0]
    assert shards[shard_n][0] == "test-guard"


def test_pack_extras_all_distributed() -> None:
    medians = {"test-a": 5.0}
    extras = ["test-new-1", "test-new-2", "test-new-3"]
    shards = pack(medians, 2, extras=extras, guard="")
    all_targets = [t for ts in shards.values() for t in ts]
    for e in extras:
        assert e in all_targets


def test_pack_all_targets_covered() -> None:
    medians = {f"test-{i}": float(i) for i in range(40)}
    shards = pack(medians, 20, guard="")
    all_targets = [t for ts in shards.values() for t in ts]
    assert sorted(all_targets) == sorted(medians.keys())


def test_pack_correct_shard_count() -> None:
    medians = {f"test-{i}": float(i) for i in range(40)}
    shards = pack(medians, 20, guard="")
    assert set(shards.keys()) == set(range(1, 21))


def test_pack_no_duplicates() -> None:
    medians = {f"test-{i}": float(i) for i in range(60)}
    shards = pack(medians, 20, guard="")
    all_targets = [t for ts in shards.values() for t in ts]
    assert len(all_targets) == len(set(all_targets))


def test_pack_single_shard() -> None:
    medians = {"test-a": 2.0, "test-b": 1.0}
    shards = pack(medians, 1, guard="")
    assert set(shards.keys()) == {1}
    assert sorted(shards[1]) == ["test-a", "test-b"]


def test_pack_invalid_n_shards() -> None:
    with pytest.raises(ValueError, match="n_shards"):
        _ = pack({"test-a": 1.0}, 0, guard="")


def test_pack_real_guard_name() -> None:
    # Smoke test with the actual guard name used in production
    guard = "test-harness-shards-coverage"
    medians = {f"test-{i}": float(100 - i) for i in range(20)}
    medians[guard] = 0.3
    shards = pack(medians, 5, guard=guard)
    guard_shard = next(n for n, ts in shards.items() if guard in ts)
    assert shards[guard_shard][0] == guard


def test_pack_extras_empty_list() -> None:
    medians = {"test-a": 1.0}
    shards = pack(medians, 2, extras=[], guard="")
    all_targets = [t for ts in shards.values() for t in ts]
    assert all_targets == ["test-a"]


def test_pack_guard_empty_string_disabled() -> None:
    # guard="" means no guard pinning — all items are assigned by round-robin only
    medians = {"test-a": 10.0, "test-b": 5.0}
    shards = pack(medians, 2, guard="")
    all_targets = [t for ts in shards.values() for t in ts]
    assert sorted(all_targets) == ["test-a", "test-b"]
