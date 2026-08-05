from __future__ import annotations

import pytest

from larch.issue import title_match


@pytest.mark.parametrize(
    ("title", "prefix", "stripped"),
    [
        ("[PLANNED] [DONE] Work", "[PLANNED] ", "[DONE] Work"),
        ("[DONE] Work", "[DONE] ", "Work"),
        ("[DEBATING] Work", "[DEBATING] ", "Work"),
        ("[DEBATED] Work", "[DEBATED] ", "Work"),
        ("[done] Work", "", "[done] Work"),
        ("Work", "", "Work"),
    ],
)
def test_lifecycle_prefix_mutation_helpers_preserve_case_and_single_strip(
    title: str, prefix: str, stripped: str
) -> None:
    assert title_match.detect_lifecycle_prefix(title) == prefix
    assert title_match.strip_lifecycle_prefix(title) == stripped


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("[BUG] foo", "[BUG]"),
        ("[FEATURE][A] x", "[FEATURE][A]"),
        (" [FEATURE] [A] x", "[FEATURE][A]"),
        ("foo", ""),
    ],
)
def test_leading_square_bracket_prefix(title: str, expected: str) -> None:
    assert title_match.leading_square_bracket_prefix(title) == expected


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("[BUG] Crash", "[BUG] [TRIAGED] Crash"),
        ("[BUG]  Extra space", "[BUG] [TRIAGED] Extra space"),
        ("Plain issue", "[TRIAGED] Plain issue"),
        ("[BUG] [triaged] Done", "[BUG] [triaged] Done"),
    ],
)
def test_insert_tag_after_bug_prefix(title: str, expected: str) -> None:
    assert title_match.insert_tag_after_bug_prefix(title, "[TRIAGED]") == expected


def test_bug_match_strips_debate_lifecycle_prefixes() -> None:
    assert title_match.bug_title_match("[DEBATING] [BUG] active")
    assert title_match.bug_title_match("[DEBATED] [BUG] complete")
