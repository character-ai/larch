"""Tests for harness_makefile."""

from __future__ import annotations

import tempfile
from pathlib import Path

from harness_makefile import read_shards, write_shards

_SAMPLE = """\
.PHONY: test-harnesses test-harnesses-1 test-harnesses-2 test-alpha test-beta test-gamma
test-harnesses: test-harnesses-1 test-harnesses-2
test-harnesses-1: test-alpha test-beta
test-harnesses-2: test-gamma
test-alpha:
\tpython3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-alpha.sh
test-beta:
\tpython3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-beta.sh
test-gamma:
\tpython3 python/cli.py timing harness-mark --label $@ -- bash scripts/test-gamma.sh
"""


def _write(content: str) -> str:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".mk", delete=False, encoding="utf-8"
    ) as f:
        _ = f.write(content)
        return f.name


def test_read_shards_basic() -> None:
    path = _write(content=_SAMPLE)
    shards = read_shards(path)
    assert shards[1] == ["test-alpha", "test-beta"]
    assert shards[2] == ["test-gamma"]


def test_read_shards_only_shard_lines() -> None:
    path = _write(content=_SAMPLE)
    shards = read_shards(path)
    assert set(shards.keys()) == {1, 2}


def test_read_shards_empty_prereqs() -> None:
    content = "test-harnesses-3:\n"
    path = _write(content=content)
    shards = read_shards(path)
    assert shards[3] == []


def test_write_shards_updates_target_lines() -> None:
    path = _write(content=_SAMPLE)
    new_shards = {1: ["test-gamma", "test-alpha"], 2: ["test-beta"]}
    write_shards(makefile_path=path, shards=new_shards)
    text = Path(path).read_text(encoding="utf-8")
    assert "test-harnesses-1: test-gamma test-alpha\n" in text
    assert "test-harnesses-2: test-beta\n" in text


def test_write_shards_preserves_other_lines() -> None:
    path = _write(content=_SAMPLE)
    original_shards = read_shards(path)
    write_shards(makefile_path=path, shards=original_shards)
    text = Path(path).read_text(encoding="utf-8")
    assert ".PHONY:" in text
    assert "python3 python/cli.py timing harness-mark" in text
    assert "test-harnesses: test-harnesses-1 test-harnesses-2\n" in text


def test_write_shards_roundtrip() -> None:
    path = _write(content=_SAMPLE)
    original = read_shards(path)
    write_shards(makefile_path=path, shards=original)
    assert read_shards(path) == original


def test_write_shards_partial_update() -> None:
    # Only update shard 1; shard 2 is untouched
    path = _write(content=_SAMPLE)
    write_shards(makefile_path=path, shards={1: ["test-gamma"]})
    text = Path(path).read_text(encoding="utf-8")
    assert "test-harnesses-1: test-gamma\n" in text
    assert "test-harnesses-2: test-gamma\n" in text  # unchanged


def test_read_shards_ignores_non_shard_lines() -> None:
    content = "all: foo\ntest-harnesses-4: test-something\nfoo:\n\techo hi\n"
    path = _write(content=content)
    shards = read_shards(path)
    assert list(shards.keys()) == [4]


def test_write_shards_large_shard_number() -> None:
    content = "test-harnesses-20: test-last\n"
    path = _write(content=content)
    write_shards(makefile_path=path, shards={20: ["test-first", "test-last"]})
    text = Path(path).read_text(encoding="utf-8")
    assert "test-harnesses-20: test-first test-last\n" in text
