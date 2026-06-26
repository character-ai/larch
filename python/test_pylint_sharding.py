from __future__ import annotations

from pathlib import Path

import pytest

import pylint_sharding as ps


def _repo_root() -> Path:
    return Path(ps.__file__).resolve().parents[1]


def _write_py(path: Path) -> None:
    _ = path.write_text("x = 1\n", encoding="utf-8")


def test_assign_shard_lexicographic() -> None:
    cuts = ("h", "q")
    assert ps.assign_shard("agents.py", cut_points=cuts) == 1
    assert ps.assign_shard("design.py", cut_points=cuts) == 1
    assert ps.assign_shard("h", cut_points=cuts) == 2  # boundary is exclusive on the left
    assert ps.assign_shard("issue.py", cut_points=cuts) == 2
    assert ps.assign_shard("review.py", cut_points=cuts) == 3
    assert ps.assign_shard("zebra.py", cut_points=cuts) == 3


def test_assign_shard_single_cut_two_shards() -> None:
    assert ps.assign_shard("apple.py", cut_points=("m",)) == 1
    assert ps.assign_shard("mango.py", cut_points=("m",)) == 2


def test_files_for_shard_rejects_bad_shard_id() -> None:
    with pytest.raises(ValueError, match="shard_id"):
        _ = ps.files_for_shard(["a.py"], shard_id=0, shard_count=3)
    with pytest.raises(ValueError, match="shard_id"):
        _ = ps.files_for_shard(["a.py"], shard_id=4, shard_count=3)


def test_files_for_shard_rejects_cutpoint_count_mismatch() -> None:
    # Two shards need exactly one cut point; the default three-cut config is wrong.
    with pytest.raises(ValueError, match="cut points"):
        _ = ps.files_for_shard(
            ["a.py"], shard_id=1, shard_count=2, cut_points=("h", "q")
        )


def test_partition_is_total_and_disjoint_synthetic() -> None:
    files = [f"{name}.py" for name in ("alpha", "hotel", "india", "tango", "zulu")]
    cuts = ("h", "t")
    seen: list[str] = []
    for shard_id in (1, 2, 3):
        seen.extend(
            ps.files_for_shard(
                files, shard_id=shard_id, shard_count=3, cut_points=cuts
            )
        )
    assert sorted(seen) == sorted(files)  # total
    assert len(seen) == len(set(seen))  # disjoint


def test_enumerate_excludes_ignored_files(tmp_path: Path) -> None:
    _write_py(tmp_path / "keep.py")
    _write_py(tmp_path / "models.py")
    _write_py(tmp_path / "thing_pb2.py")
    pkg = tmp_path / "sub"
    pkg.mkdir()
    _write_py(pkg / "nested.py")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    _write_py(cache / "cached.py")

    found = ps.enumerate_py_files(tmp_path)

    assert found == ["keep.py", "sub/nested.py"]


def test_real_tree_three_way_split_is_total_disjoint_nonempty() -> None:
    source_dir = ps.source_dir_for(_repo_root())
    all_files = ps.enumerate_py_files(source_dir)
    assert all_files, "expected a non-empty python tree"

    shard_count = len(ps.CUT_POINTS) + 1
    covered: list[str] = []
    for shard_id in range(1, shard_count + 1):
        shard = ps.files_for_shard(
            all_files, shard_id=shard_id, shard_count=shard_count
        )
        assert shard, f"shard {shard_id} is empty; re-tune CUT_POINTS"
        covered.extend(shard)

    assert sorted(covered) == sorted(all_files)  # no file dropped
    assert len(covered) == len(set(covered))  # no file double-linted
