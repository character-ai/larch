from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import conftest
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
    assert pytest_sharding.select_shard_indices(num_items=10, shard_id=1, shard_count=4) == {0, 4, 8}
    assert pytest_sharding.select_shard_indices(num_items=10, shard_id=2, shard_count=4) == {1, 5, 9}
    assert pytest_sharding.select_shard_indices(num_items=10, shard_id=3, shard_count=4) == {2, 6}
    assert pytest_sharding.select_shard_indices(num_items=10, shard_id=4, shard_count=4) == {3, 7}


def test_select_shard_indices_complete_and_disjoint() -> None:
    num_items = 37
    shard_count = 4
    seen: set[int] = set()
    for shard_id in range(1, shard_count + 1):
        indices = pytest_sharding.select_shard_indices(num_items=num_items, shard_id=shard_id, shard_count=shard_count)
        assert seen.isdisjoint(indices)
        seen |= indices
    assert seen == set(range(num_items))


def test_select_shard_indices_balanced_within_one() -> None:
    num_items = 111
    shard_count = 4
    sizes = [
        len(pytest_sharding.select_shard_indices(num_items=num_items, shard_id=shard_id, shard_count=shard_count))
        for shard_id in range(1, shard_count + 1)
    ]
    assert max(sizes) - min(sizes) <= 1


def test_select_shard_indices_single_shard_keeps_all() -> None:
    assert pytest_sharding.select_shard_indices(num_items=5, shard_id=1, shard_count=1) == {0, 1, 2, 3, 4}


def test_load_shard_assignments_absent_and_empty(tmp_path: Path) -> None:
    assert not pytest_sharding.load_shard_assignments(tmp_path / "missing.json")
    path = tmp_path / "assignments.json"
    _ = path.write_text("{}\n", encoding="utf-8")
    assert not pytest_sharding.load_shard_assignments(path)


def test_load_shard_assignments_valid_map(tmp_path: Path) -> None:
    path = tmp_path / "assignments.json"
    _ = path.write_text(json.dumps({"test_a.py::test_b": 2}), encoding="utf-8")
    assert pytest_sharding.load_shard_assignments(path) == {"test_a.py::test_b": 2}


@pytest.mark.parametrize(
    "content",
    [
        "{bad",
        "[]",
        json.dumps({"a": 1.5}),
        json.dumps({"a": "1"}),
        json.dumps({"a": 0}),
        json.dumps({"a": -1}),
        json.dumps({"a": True}),
        json.dumps({"a": False}),
    ],
)
def test_load_shard_assignments_rejects_invalid_values(
    tmp_path: Path, content: str
) -> None:
    path = tmp_path / "assignments.json"
    _ = path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match=r"shard|malformed|JSON"):
        _ = pytest_sharding.load_shard_assignments(path)


def test_select_shard_nodeids_uses_assignments_and_round_robin_fallback() -> None:
    nodeids = ["a", "b", "c", "d", "e"]
    assignments = {"a": 2, "c": 1, "e": 2}

    assert pytest_sharding.select_shard_nodeids(nodeids=nodeids, shard_id=1, shard_count=2, assignments=assignments) == {2}
    assert pytest_sharding.select_shard_nodeids(nodeids=nodeids, shard_id=2, shard_count=2, assignments=assignments) == {0, 1, 3, 4}


def test_select_shard_nodeids_complete_and_disjoint() -> None:
    nodeids = ["a", "b", "c", "d", "e", "f"]
    assignments = {"a": 3, "b": 1, "c": 2}
    seen: set[int] = set()
    for shard_id in range(1, 4):
        selected = pytest_sharding.select_shard_nodeids(nodeids=nodeids, shard_id=shard_id, shard_count=3, assignments=assignments)
        assert seen.isdisjoint(selected)
        seen |= selected
    assert seen == set(range(len(nodeids)))


def test_select_shard_nodeids_ignores_mismatched_map() -> None:
    nodeids = ["a", "b", "c", "d"]
    assignments = {"a": 1, "b": 2, "c": 5}

    assert pytest_sharding.select_shard_nodeids(nodeids=nodeids, shard_id=1, shard_count=4, assignments=assignments) == {0}
    assert pytest_sharding.select_shard_nodeids(nodeids=nodeids, shard_id=4, shard_count=4, assignments=assignments) == {3}


def test_select_shard_nodeids_single_shard_keeps_all() -> None:
    assert pytest_sharding.select_shard_nodeids(nodeids=["a", "b"], shard_id=1, shard_count=1, assignments={}) == {0, 1}


class _Hook:
    def __init__(self) -> None:
        self.deselected: list[Any] = []

    def pytest_deselected(self, *, items: list[Any]) -> None:
        self.deselected.extend(items)


class _Config:
    def __init__(self) -> None:
        self.hook = _Hook()


def _item(nodeid: str) -> Any:
    return SimpleNamespace(nodeid=nodeid)


def test_collection_hook_uses_assignments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTEST_SHARD_ID", "2")
    monkeypatch.setenv("PYTEST_SHARD_COUNT", "2")

    def load_assignments() -> dict[str, int]:
        return {"a": 2, "c": 1}

    monkeypatch.setattr(pytest_sharding, "load_shard_assignments", load_assignments)
    items = [_item("a"), _item("b"), _item("c"), _item("d")]
    config = _Config()

    config_any: Any = config
    conftest.pytest_collection_modifyitems(config_any, items)

    assert [item.nodeid for item in items] == ["a", "b", "d"]
    assert [item.nodeid for item in config.hook.deselected] == ["c"]


def test_collection_hook_unset_env_does_not_load_assignments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PYTEST_SHARD_ID", raising=False)
    monkeypatch.delenv("PYTEST_SHARD_COUNT", raising=False)

    def fail_load_assignments() -> dict[str, int]:
        raise AssertionError("should not load assignments when sharding is disabled")

    monkeypatch.setattr(pytest_sharding, "load_shard_assignments", fail_load_assignments)
    items = [_item("a"), _item("b")]
    config_any: Any = _Config()
    conftest.pytest_collection_modifyitems(config_any, items)

    assert [item.nodeid for item in items] == ["a", "b"]
