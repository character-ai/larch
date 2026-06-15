from __future__ import annotations

import pytest

import pytest_sharding


def test_read_shard_env_unset_returns_none() -> None:
    assert pytest_sharding.read_shard_env({}) is None


def test_read_shard_env_valid() -> None:
    assert pytest_sharding.read_shard_env(
        {"PYTEST_SHARD_ID": "2", "PYTEST_SHARD_COUNT": "4"}
    ) == (2, 4)


def test_read_shard_env_partial_raises() -> None:
    with pytest.raises(ValueError, match="must both be set or both be unset"):
        _ = pytest_sharding.read_shard_env({"PYTEST_SHARD_ID": "1"})
    with pytest.raises(ValueError, match="must both be set or both be unset"):
        _ = pytest_sharding.read_shard_env({"PYTEST_SHARD_COUNT": "4"})


def test_read_shard_env_out_of_range_raises() -> None:
    with pytest.raises(ValueError, match="must be in"):
        _ = pytest_sharding.read_shard_env(
            {"PYTEST_SHARD_ID": "0", "PYTEST_SHARD_COUNT": "4"}
        )
    with pytest.raises(ValueError, match="must be in"):
        _ = pytest_sharding.read_shard_env(
            {"PYTEST_SHARD_ID": "5", "PYTEST_SHARD_COUNT": "4"}
        )


def test_read_shard_env_bad_count_raises() -> None:
    with pytest.raises(ValueError, match="must be >= 1"):
        _ = pytest_sharding.read_shard_env(
            {"PYTEST_SHARD_ID": "1", "PYTEST_SHARD_COUNT": "0"}
        )


def test_read_shard_env_non_numeric_raises() -> None:
    with pytest.raises(ValueError, match="invalid literal"):
        _ = pytest_sharding.read_shard_env(
            {"PYTEST_SHARD_ID": "x", "PYTEST_SHARD_COUNT": "4"}
        )


def test_select_shard_indices_round_robin() -> None:
    assert pytest_sharding.select_shard_indices(10, 1, 4) == {0, 4, 8}
    assert pytest_sharding.select_shard_indices(10, 2, 4) == {1, 5, 9}
    assert pytest_sharding.select_shard_indices(10, 3, 4) == {2, 6}
    assert pytest_sharding.select_shard_indices(10, 4, 4) == {3, 7}


def test_select_shard_indices_complete_and_disjoint() -> None:
    num_items = 37
    shard_count = 4
    seen: set[int] = set()
    for shard_id in range(1, shard_count + 1):
        indices = pytest_sharding.select_shard_indices(num_items, shard_id, shard_count)
        assert seen.isdisjoint(indices)
        seen |= indices
    assert seen == set(range(num_items))


def test_select_shard_indices_balanced_within_one() -> None:
    num_items = 111
    shard_count = 4
    sizes = [
        len(pytest_sharding.select_shard_indices(num_items, shard_id, shard_count))
        for shard_id in range(1, shard_count + 1)
    ]
    assert max(sizes) - min(sizes) <= 1


def test_select_shard_indices_single_shard_keeps_all() -> None:
    assert pytest_sharding.select_shard_indices(5, 1, 1) == {0, 1, 2, 3, 4}
