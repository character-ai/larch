"""Parameterized skill-structure checker for the seven migrated harnesses."""
from __future__ import annotations

import importlib
import re
from collections.abc import Iterator
from functools import cache
from pathlib import Path

import pytest

from .skill_structure_pins import (
    ALL_PINS,
    DESIGN_PINS,
    FOCUSED_SELECTION,
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
    if pin.kind == "absent" and not full.exists():
        return  # missing file satisfies absence of content
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
        if pin.comparator == "exact" or pin.kind == "exact_count":
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
        # Anchor in first file; require token in second within bound lines of
        # the matching line index (legacy proximity across paired files).
        assert pin.bound is not None
        anchor_lines = _match_lines(text, pin.needle, match=pin.match)
        if not anchor_lines:
            raise AssertionError(f"{prefix}: missing anchor {pin.needle!r} in {pin.path}")
        token_lines = _match_lines(other_text, pin.needle2, match=pin.match)
        if not token_lines:
            raise AssertionError(
                f"{prefix}: missing token {pin.needle2!r} in {pin.path2}"
            )
        for a in anchor_lines:
            for t in token_lines:
                if abs(a - t) <= pin.bound:
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
    assert fails == [], fails


def test_bug_structure_specialized() -> None:
    fails = _run_specialized("bug")
    assert fails == [], fails


def test_learn_from_bugs_structure_specialized() -> None:
    fails = _run_specialized("learn-from-bugs")
    assert fails == [], fails


def test_design_structure_specialized() -> None:
    fails = _run_specialized("design")
    assert fails == [], fails


def test_implement_structure_specialized() -> None:
    fails = _run_specialized("implement")
    assert fails == [], fails


def test_research_structure_specialized() -> None:
    fails = _run_specialized("research")
    assert fails == [], fails


def test_review_structure_specialized() -> None:
    fails = _run_specialized("review")
    assert fails == [], fails


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


def test_legacy_label_inventory_covers_specialized_and_pins() -> None:
    """Every specialized module exposes LEGACY_LABELS; pin IDs are unique."""
    validate_pin_table(ALL_PINS)
    pin_ids = {p.param_id for p in ALL_PINS}
    assert len(pin_ids) == len(ALL_PINS)
    for skill, mod_name in SPECIALIZED_MODULES.items():
        mod = importlib.import_module(f".{mod_name}", package=__package__)
        labels = getattr(mod, "LEGACY_LABELS", None)
        assert isinstance(labels, frozenset), skill
        assert labels, f"{skill} specialized module has empty LEGACY_LABELS"
        assert skill in SPECIALIZED_LABEL_OWNERS


def test_focused_selection_registry_covers_all_skills() -> None:
    for skill in SPECIALIZED_MODULES:
        assert skill in FOCUSED_SELECTION
        assert FOCUSED_SELECTION[skill].strip()


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
