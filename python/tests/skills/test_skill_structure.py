"""Parameterized skill-structure checker for the seven migrated harnesses."""
from __future__ import annotations

import importlib
import os
import re
import subprocess
import sys
from collections.abc import Iterator
from typing import cast
from functools import cache
from pathlib import Path

import pytest
from pytest_sharding import ENV_SHARD_COUNT, ENV_SHARD_ID

from .skill_structure_pins import (
    ALL_PINS,
    DESIGN_PINS,
    FOCUSED_SELECTION,
    FOCUSED_TARGETS,
    SPECIALIZED_MODULES,
    StructurePin,
    validate_pin_table,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


@cache
def _read_text(path: str) -> str:
    full = REPO_ROOT / path
    if not full.is_file():
        raise FileNotFoundError(path)
    return full.read_text(encoding="utf-8")


def _clear_read_cache() -> None:
    _read_text.cache_clear()


def _match_lines(text: str, needle: str, *, match: str) -> list[int]:
    """1-based physical line numbers that match needle."""
    lines = text.splitlines()
    out: list[int] = []
    if match == "regex":
        cre = re.compile(needle)
        for i, line in enumerate(lines, 1):
            if cre.search(line) is not None:
                out.append(i)
    else:
        for i, line in enumerate(lines, 1):
            if needle in line:
                out.append(i)
    return out


def _count(text: str, needle: str, *, match: str, unit: str) -> int:
    if unit == "physical_line":
        return len(_match_lines(text, needle, match=match))
    if unit == "matching_line":
        return len(_match_lines(text, needle, match=match))
    if unit == "substring":
        if match == "regex":
            return len(re.findall(needle, text))
        # non-overlapping fixed substring count
        count = 0
        start = 0
        while True:
            idx = text.find(needle, start)
            if idx < 0:
                return count
            count += 1
            start = idx + max(len(needle), 1)
        return count
    raise ValueError(f"unknown count unit {unit!r}")


def _first_exact_line(text: str, needle: str) -> int | None:
    for i, line in enumerate(text.splitlines(), 1):
        if line == needle:
            return i
    return None


def _first_contains_line(text: str, needle: str) -> int | None:
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return None


def _adjacent_pair_count(text: str, first: str, second: str) -> int:
    lines = text.splitlines()
    count = 0
    for i, line in enumerate(lines):
        if line == first and i + 1 < len(lines) and lines[i + 1] == second:
            count += 1
    return count


def evaluate_pin(pin: StructurePin, *, repo_root: Path | None = None) -> None:
    """Raise AssertionError with a deterministic diagnostic on failure."""
    root = REPO_ROOT if repo_root is None else repo_root
    full = root / pin.path
    prefix = (
        f"skill={pin.skill} label={pin.label!r} path={pin.path} predicate={pin.kind}"
    )
    if not full.is_file():
        raise AssertionError(f"{prefix}: missing target file")

    text = full.read_text(encoding="utf-8")

    if pin.kind == "contains":
        if pin.match == "regex":
            if re.search(pin.needle, text) is None:
                raise AssertionError(f"{prefix}: missing regex {pin.needle!r}")
        elif pin.needle not in text:
            raise AssertionError(f"{prefix}: missing {pin.needle!r}")
        return

    if pin.kind == "absent":
        if pin.match == "regex":
            if re.search(pin.needle, text) is not None:
                raise AssertionError(f"{prefix}: forbidden regex {pin.needle!r} present")
        elif pin.needle in text:
            raise AssertionError(f"{prefix}: forbidden {pin.needle!r} present")
        return

    if pin.kind in {"exact_count", "count_at_least"}:
        assert pin.expected is not None
        observed = _count(
            text, pin.needle, match=pin.match, unit=pin.count_unit
        )
        if pin.kind == "exact_count":
            if observed != pin.expected:
                raise AssertionError(
                    f"{prefix}: expected exactly {pin.expected} "
                    f"({pin.count_unit}), observed {observed}, needle={pin.needle!r}"
                )
        elif observed < pin.expected:
            raise AssertionError(
                f"{prefix}: expected at least {pin.expected} "
                f"({pin.count_unit}), observed {observed}, needle={pin.needle!r}"
            )
        return

    if pin.kind == "ordered":
        if pin.match_mode == "exact_line":
            early = _first_exact_line(text, pin.needle)
            late = _first_exact_line(text, pin.needle2)
        else:
            early = _first_contains_line(text, pin.needle)
            late = _first_contains_line(text, pin.needle2)
        if early is None:
            raise AssertionError(
                f"{prefix}: missing first anchor {pin.needle!r}"
            )
        if late is None:
            raise AssertionError(
                f"{prefix}: missing second anchor {pin.needle2!r}"
            )
        if early >= late:
            raise AssertionError(
                f"{prefix}: reversed order "
                f"(first_line={early} second_line={late})"
            )
        return

    if pin.kind == "same_line":
        for line in text.splitlines():
            if all(tok in line for tok in pin.tokens):
                return
        raise AssertionError(
            f"{prefix}: no physical line contains all tokens {pin.tokens!r}"
        )

    if pin.kind == "adjacent_pair_count_at_least":
        assert pin.expected is not None
        observed = _adjacent_pair_count(text, pin.needle, pin.needle2)
        if observed < pin.expected:
            raise AssertionError(
                f"{prefix}: expected at least {pin.expected} adjacent pair(s), "
                f"found {observed}; first={pin.needle!r} second={pin.needle2!r}"
            )
        return

    if pin.kind == "cross_file_bound":
        other = root / pin.path2
        if not other.is_file():
            raise AssertionError(f"{prefix}: missing second target {pin.path2}")
        other_text = other.read_text(encoding="utf-8")
        assert pin.bound is not None
        anchor_lines = _match_lines(text, pin.needle, match=pin.match)
        if not anchor_lines:
            raise AssertionError(f"{prefix}: missing anchor {pin.needle!r} in {pin.path}")
        token_lines = _match_lines(other_text, pin.needle2, match=pin.match)
        if not token_lines:
            raise AssertionError(
                f"{prefix}: missing token {pin.needle2!r} in {pin.path2}"
            )
        if any(abs(anchor - token) <= pin.bound for anchor in anchor_lines for token in token_lines):
            return
        raise AssertionError(
            f"{prefix}: token {pin.needle2!r} not within bound={pin.bound} "
            f"of anchor {pin.needle!r} across {pin.path} / {pin.path2}"
        )

    raise AssertionError(f"{prefix}: unknown predicate")


@pytest.fixture(autouse=True)
def _clear_caches() -> Iterator[None]:  # pyright: ignore[reportUnusedFunction]
    _clear_read_cache()
    yield
    _clear_read_cache()


@pytest.mark.parametrize(
    "pin",
    DESIGN_PINS,
    ids=[p.param_id for p in DESIGN_PINS],
)
def test_design_structure_pin(pin: StructurePin) -> None:
    evaluate_pin(pin)


def _run_specialized(skill: str) -> list[str]:
    mod_name = SPECIALIZED_MODULES[skill]
    mod = importlib.import_module(f".{mod_name}", package=__package__)
    return list(mod.run(REPO_ROOT))


def test_alias_structure_specialized() -> None:
    fails = _run_specialized("alias")
    assert not fails, fails


def test_bug_structure_specialized() -> None:
    fails = _run_specialized("bug")
    assert not fails, fails


def test_learn_from_bugs_structure_specialized() -> None:
    fails = _run_specialized("learn-from-bugs")
    assert not fails, fails


def test_design_structure_specialized() -> None:
    fails = _run_specialized("design")
    assert not fails, fails


def test_implement_structure_specialized() -> None:
    fails = _run_specialized("implement")
    assert not fails, fails


def test_research_structure_specialized() -> None:
    fails = _run_specialized("research")
    assert not fails, fails


def test_review_structure_specialized() -> None:
    fails = _run_specialized("review")
    assert not fails, fails


# ---------------------------------------------------------------------------
# Legacy-label inventory
# ---------------------------------------------------------------------------

SPECIALIZED_LABEL_OWNERS: dict[str, str] = {
    "alias": "test_alias_structure_specialized",
    "bug": "test_bug_structure_specialized",
    "design": "test_design_structure_specialized",
    "implement": "test_implement_structure_specialized",
    "learn-from-bugs": "test_learn_from_bugs_structure_specialized",
    "research": "test_research_structure_specialized",
    "review": "test_review_structure_specialized",
}


def _collect_node_ids(*, selection: str | None = None) -> set[str]:
    command = [sys.executable, "-m", "pytest", "--collect-only", "-q", __file__]
    if selection is not None:
        command.extend(("-k", selection))
    env = os.environ.copy()
    _ = env.pop(ENV_SHARD_ID, None)
    _ = env.pop(ENV_SHARD_COUNT, None)
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return {
        line.removeprefix("python/")
        for line in result.stdout.splitlines()
        if "::test_" in line
    }


def _skill_nodes(skill: str) -> set[str]:
    nodes = {
        f"tests/skills/test_skill_structure.py::{SPECIALIZED_LABEL_OWNERS[skill]}",
    }
    nodes.update(
        f"tests/skills/test_skill_structure.py::test_design_structure_pin[{pin.param_id}]"
        for pin in ALL_PINS
        if pin.skill == skill
    )
    return nodes


def test_legacy_label_inventory_maps_every_label_to_one_collected_node() -> None:
    """Each legacy assertion has one owning pytest node."""
    validate_pin_table(ALL_PINS)
    all_nodes = _collect_node_ids()
    label_owners: dict[tuple[str, str], list[str]] = {}
    for pin in ALL_PINS:
        label_owners.setdefault((pin.skill, pin.label), []).append(
            f"tests/skills/test_skill_structure.py::test_design_structure_pin[{pin.param_id}]"
        )
    for skill, mod_name in SPECIALIZED_MODULES.items():
        mod = importlib.import_module(f".{mod_name}", package=__package__)
        labels = getattr(mod, "LEGACY_LABELS", None)
        assert isinstance(labels, frozenset), skill
        labels = cast("frozenset[str]", labels)
        assert labels, f"{skill} specialized module has empty LEGACY_LABELS"
        expected_count = getattr(mod, "LEGACY_ASSERTION_LABEL_COUNT", None)
        if expected_count is not None:
            assert len(labels) == expected_count, (
                f"{skill} specialized assertion inventory changed: "
                f"expected {expected_count}, found {len(labels)}"
            )
        owner = f"tests/skills/test_skill_structure.py::{SPECIALIZED_LABEL_OWNERS[skill]}"
        for label in labels:
            label_owners.setdefault((skill, label), []).append(owner)
    for label_id, owners in label_owners.items():
        assert len(owners) == 1, f"legacy label {label_id!r} has owners {owners!r}"
        assert owners[0] in all_nodes, f"legacy label {label_id!r} owner not collected: {owners[0]}"


def test_focused_selection_registry_covers_all_structure_nodes() -> None:
    for skill in SPECIALIZED_MODULES:
        assert skill in FOCUSED_SELECTION
        target = FOCUSED_TARGETS[skill]
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        command = re.search(
            rf"^{re.escape(target)}:\n(?:.*\n)*?\t.* -k '([^']+)'",
            makefile,
            re.MULTILINE,
        )
        assert command is not None, f"{target} must run a focused pytest selection"
        assert command.group(1) == FOCUSED_SELECTION[skill]
        selected = _collect_node_ids(selection=FOCUSED_SELECTION[skill])
        assert selected == _skill_nodes(skill), (
            f"{skill} focused selection {FOCUSED_SELECTION[skill]!r} selects "
            f"{sorted(selected)!r}, expected {sorted(_skill_nodes(skill))!r}"
        )


# ---------------------------------------------------------------------------
# Checker self-tests
# ---------------------------------------------------------------------------


def test_evaluator_contains_and_absent(tmp_path: Path) -> None:
    _ = (tmp_path / "sample.md").write_text("alpha\nbeta gamma\nalpha\n", encoding="utf-8")
    rel = "sample.md"
    evaluate_pin(
        StructurePin(skill="t", label="c1", path=rel, kind="contains", needle="beta"),
        repo_root=tmp_path,
    )
    with pytest.raises(AssertionError, match="missing"):
        evaluate_pin(
            StructurePin(skill="t", label="c2", path=rel, kind="contains", needle="nope"),
            repo_root=tmp_path,
        )
    evaluate_pin(
        StructurePin(skill="t", label="a1", path=rel, kind="absent", needle="nope"),
        repo_root=tmp_path,
    )
    with pytest.raises(AssertionError, match="forbidden"):
        evaluate_pin(
            StructurePin(skill="t", label="a2", path=rel, kind="absent", needle="alpha"),
            repo_root=tmp_path,
        )
    with pytest.raises(AssertionError, match="missing target file"):
        evaluate_pin(
            StructurePin(skill="t", label="a3", path="missing.md", kind="absent", needle="nope"),
            repo_root=tmp_path,
        )
    evaluate_pin(
        StructurePin(skill="t", label="regex", path=rel, kind="contains", needle=r"beta\s+gamma", match="regex"),
        repo_root=tmp_path,
    )
    with pytest.raises(AssertionError, match="forbidden regex"):
        evaluate_pin(
            StructurePin(skill="t", label="regex-absent", path=rel, kind="absent", needle=r"beta\s+gamma", match="regex"),
            repo_root=tmp_path,
        )


def test_evaluator_counts_and_ordered(tmp_path: Path) -> None:
    _ = (tmp_path / "c.md").write_text("one\ntwo\none\n", encoding="utf-8")
    evaluate_pin(
        StructurePin(
            skill="t",
            label="exact",
            path="c.md",
            kind="exact_count",
            needle="one",
            expected=2,
            count_unit="matching_line",
            comparator="exact",
        ),
        repo_root=tmp_path,
    )
    evaluate_pin(
        StructurePin(
            skill="t", label="atleast-default", path="c.md", kind="count_at_least",
            needle="one", expected=1, count_unit="matching_line", comparator="at_least",
        ),
        repo_root=tmp_path,
    )
    evaluate_pin(
        StructurePin(
            skill="t", label="substring-regex", path="c.md", kind="exact_count",
            needle=r"o.e", expected=2, count_unit="substring", comparator="exact", match="regex",
        ),
        repo_root=tmp_path,
    )
    evaluate_pin(
        StructurePin(
            skill="t",
            label="atleast",
            path="c.md",
            kind="count_at_least",
            needle="one",
            expected=1,
            count_unit="matching_line",
            comparator="at_least",
        ),
        repo_root=tmp_path,
    )
    with pytest.raises(AssertionError, match="exactly"):
        evaluate_pin(
            StructurePin(
                skill="t",
                label="exact-fail",
                path="c.md",
                kind="exact_count",
                needle="one",
                expected=1,
                count_unit="matching_line",
                comparator="exact",
            ),
            repo_root=tmp_path,
        )
    evaluate_pin(
        StructurePin(
            skill="t",
            label="ord",
            path="c.md",
            kind="ordered",
            needle="one",
            needle2="two",
            match_mode="exact_line",
        ),
        repo_root=tmp_path,
    )
    with pytest.raises(AssertionError, match=r"reversed|missing"):
        evaluate_pin(
            StructurePin(
                skill="t",
                label="ord-rev",
                path="c.md",
                kind="ordered",
                needle="two",
                needle2="one",
                match_mode="exact_line",
            ),
            repo_root=tmp_path,
        )
    evaluate_pin(
        StructurePin(
            skill="t",
            label="ord-contains",
            path="c.md",
            kind="ordered",
            needle="one",
            needle2="two",
            match_mode="contains",
        ),
        repo_root=tmp_path,
    )


def test_evaluator_adjacent_pair_and_same_line(tmp_path: Path) -> None:
    _ = (tmp_path / "p.md").write_text("A\nB\nX\nA\nB\n", encoding="utf-8")
    evaluate_pin(
        StructurePin(
            skill="t",
            label="adj",
            path="p.md",
            kind="adjacent_pair_count_at_least",
            needle="A",
            needle2="B",
            expected=2,
            count_unit="adjacent_pair",
            comparator="at_least",
        ),
        repo_root=tmp_path,
    )
    with pytest.raises(AssertionError, match="adjacent"):
        evaluate_pin(
            StructurePin(
                skill="t",
                label="adj-fail",
                path="p.md",
                kind="adjacent_pair_count_at_least",
                needle="A",
                needle2="B",
                expected=3,
                count_unit="adjacent_pair",
                comparator="at_least",
            ),
            repo_root=tmp_path,
        )
    _ = (tmp_path / "other.md").write_text("A\nX\nY\n", encoding="utf-8")
    evaluate_pin(
        StructurePin(
            skill="t",
            label="cross-file",
            path="p.md",
            path2="other.md",
            kind="cross_file_bound",
            needle="A",
            needle2="A",
            bound=1,
        ),
        repo_root=tmp_path,
    )
    with pytest.raises(AssertionError, match="within bound"):
        evaluate_pin(
            StructurePin(
                skill="t",
                label="cross-file-fail",
                path="p.md",
                path2="other.md",
                kind="cross_file_bound",
                needle="B",
                needle2="A",
                bound=0,
            ),
            repo_root=tmp_path,
        )
    _ = (tmp_path / "s.md").write_text("foo bar baz\nfoo only\n", encoding="utf-8")
    evaluate_pin(
        StructurePin(
            skill="t",
            label="same",
            path="s.md",
            kind="same_line",
            tokens=("foo", "bar", "baz"),
        ),
        repo_root=tmp_path,
    )
    with pytest.raises(AssertionError, match="physical line"):
        evaluate_pin(
            StructurePin(
                skill="t",
                label="same-fail",
                path="s.md",
                kind="same_line",
                tokens=("foo", "missing"),
            ),
            repo_root=tmp_path,
        )


def test_validate_pin_table_rejects_duplicates() -> None:
    bad = (
        StructurePin(skill="t", label="x", path="a", kind="contains", needle="n"),
        StructurePin(skill="t", label="x", path="b", kind="contains", needle="n"),
    )
    with pytest.raises(ValueError, match="duplicate"):
        validate_pin_table(bad)


def test_validate_pin_table_rejects_empty_needle() -> None:
    bad = (
        StructurePin(skill="t", label="x", path="a", kind="contains", needle=""),
    )
    with pytest.raises(ValueError, match="empty needle"):
        validate_pin_table(bad)


@pytest.mark.parametrize(
    ("pin", "message"),
    [
        (StructurePin(skill="t", label="kind", path="a", kind="invalid"), "unknown predicate"),  # type: ignore[arg-type]
        (StructurePin(skill="t", label="match", path="a", kind="contains", needle="n", match="invalid"), "unknown match kind"),  # type: ignore[arg-type]
        (StructurePin(skill="t", label="unit", path="a", kind="exact_count", needle="n", expected=1, count_unit="invalid"), "unknown count unit"),  # type: ignore[arg-type]
        (StructurePin(skill="t", label="compare", path="a", kind="exact_count", needle="n", expected=1, comparator="invalid"), "unknown comparator"),  # type: ignore[arg-type]
        (StructurePin(skill="t", label="mode", path="a", kind="ordered", needle="n", needle2="m", match_mode="invalid"), "unknown match mode"),  # type: ignore[arg-type]
        (StructurePin(skill="t", label="bound", path="a", kind="count_at_least", needle="n", expected=-1, comparator="at_least"), "non-negative"),
        (StructurePin(skill="t", label="compat", path="a", kind="count_at_least", needle="n", expected=1), "requires comparator"),
        (StructurePin(skill="t", label="adj-count", path="a", kind="adjacent_pair_count_at_least", needle="a", needle2="b", expected=True, count_unit="adjacent_pair", comparator="at_least"), "non-negative"),
        (StructurePin(skill="t", label="adj-unit", path="a", kind="adjacent_pair_count_at_least", needle="a", needle2="b", expected=1, comparator="at_least"), "count_unit"),
        (StructurePin(skill="t", label="adj-compare", path="a", kind="adjacent_pair_count_at_least", needle="a", needle2="b", expected=1, count_unit="adjacent_pair"), "comparator"),
        (StructurePin(skill="t", label="cross-bound", path="a", path2="b", kind="cross_file_bound", needle="a", needle2="b", bound=-1), "non-negative"),  # type: ignore[arg-type]
    ],
)
def test_validate_pin_table_rejects_invalid_modes_and_bounds(pin: StructurePin, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_pin_table((pin,))


def test_missing_target_file_is_assertion_not_collection(tmp_path: Path) -> None:
    with pytest.raises(AssertionError, match="missing target file"):
        evaluate_pin(
            StructurePin(
                skill="t",
                label="missing",
                path="nope.md",
                kind="contains",
                needle="x",
            ),
            repo_root=tmp_path,
        )
