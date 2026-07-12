from __future__ import annotations

import pytest

from larch.design import plan_grammar


@pytest.mark.parametrize("level", ["##", "###"])
@pytest.mark.parametrize("kind", plan_grammar.HEADING_KINDS)
@pytest.mark.parametrize("shape", ["{level} {kind}: path/to/file.py", "{level} {kind} [path/to/file.py]"])
def test_all_heading_forms(level: str, kind: str, shape: str) -> None:
    match = plan_grammar.match_heading(shape.format(level=level, kind=kind))
    assert match is not None
    assert (match.kind, match.path, match.level) == (kind, "path/to/file.py", len(level))


@pytest.mark.parametrize("line", ["# NEW: x", "#### NEW: x", "## NEW:", "## UNKNOWN: x", "## NEW [x"])
def test_malformed_headings_rejected(line: str) -> None:
    assert plan_grammar.match_heading(line) is None


def test_fenced_headings_and_boundaries_are_ignored() -> None:
    text = "## Files to modify/create\n```md\n## NEW: hidden.py\n## Stop\n```\n## NEW: shown.py\n## Stop\n"
    events = list(plan_grammar.iter_heading_events(text))
    assert [event.heading.path for event in events if event.heading] == ["shown.py"]
    assert [event.text for event in events if event.generic_level_two] == ["## Files to modify/create", "## Stop"]


def test_shorter_fence_does_not_close_a_longer_fence() -> None:
    text = "````md\n```\n## NEW: hidden.py\n````\n## NEW: shown.py\n"
    assert [heading.path for heading in plan_grammar.iter_plan_headings(text)] == ["shown.py"]


def test_balanced_fence_helper_covers_backtick_tilde_and_unclosed() -> None:
    backtick = ["before", "```md", "## NEW: hidden.py", "```", "after"]
    tilde = ["before", "~~~~md", "## NEW: hidden.py", "~~~~", "after"]
    longer = ["````md", "```", "## NEW: still-hidden.py", "````"]
    invalid_closer = ["```md", "## NEW: still-open.py", "```not-a-close"]
    unclosed = ["```md", "## NEW: after-unclosed.py"]
    mismatched = ["```md", "## NEW: still-open.py", "~~~"]

    assert plan_grammar.balanced_fence_line_indices(backtick) == {2}
    assert plan_grammar.balanced_fence_line_indices(tilde) == {2}
    assert plan_grammar.balanced_fence_line_indices(longer) == {1, 2}
    assert plan_grammar.balanced_fence_line_indices(invalid_closer) == set()
    assert plan_grammar.balanced_fence_line_indices(unclosed) == set()
    assert plan_grammar.balanced_fence_line_indices(mismatched) == set()


def test_iter_heading_events_preserves_headings_after_unmatched_opener() -> None:
    text = "```md\n## NEW: hidden-if-balanced.py\n## NEW: visible-after-unclosed.py\n"
    assert [heading.path for heading in plan_grammar.iter_plan_headings(text)] == [
        "hidden-if-balanced.py",
        "visible-after-unclosed.py",
    ]
    text_closed = "~~~\n## NEW: hidden.py\n~~~\n## NEW: shown.py\n"
    assert [heading.path for heading in plan_grammar.iter_plan_headings(text_closed)] == ["shown.py"]


def test_registry_and_subsets() -> None:
    assert plan_grammar.TRAILER_KEYS == (
        "review_status", "rounds_completed", "difficulty", "diff_added", "diff_deleted",
        "mechanical_churn", "oversize_override", "diff_lines",
    )
    assert plan_grammar.OPTIONAL_SIZE_TRAILER_KEYS == (
        "diff_added", "diff_deleted", "mechanical_churn", "oversize_override",
    )
    assert frozenset({"NEW", "UPDATED", "REWRITTEN"}) == plan_grammar.FIRM_HEADING_KINDS


@pytest.mark.parametrize(
    ("line", "parsed"),
    [
        ("review_status: complete", "complete"), ("rounds_completed: 00", 0),
        ("difficulty: HARD", "HARD"), ("diff_added: 007", 7),
        ("diff_deleted: 0", 0), ("mechanical_churn: true", True),
        ("oversize_override: operator", "operator"), ("diff_lines: 09", 9),
    ],
)
def test_typed_trailer_recognition(line: str, parsed: object) -> None:
    match = plan_grammar.match_trailer_line(line)
    assert match is not None
    assert match.parsed_value == parsed


@pytest.mark.parametrize("line", ["diff_added: 08", "diff_deleted: 09", "mechanical_churn: yes", "oversize_override: model", "difficulty: hard"])
def test_malformed_trailers_rejected(line: str) -> None:
    assert plan_grammar.match_trailer_line(line) is None


def test_final_contiguous_block_boundaries_duplicates_and_terminal_requirement() -> None:
    text = "body\ndifficulty: HARD\nconfidence: high\ndiff_added: 1\ndiff_added: 2\ndiff_lines: 3\n"
    trailers = plan_grammar.parse_final_trailers(text, require_diff_lines=True)
    assert trailers.lines == ("diff_added: 1", "diff_added: 2", "diff_lines: 3")
    assert trailers.duplicates == ("diff_added",)
    assert trailers.diff_lines == 3
    assert plan_grammar.terminal_diff_lines("body\ndiff_lines: 1\nmore\n") is None
    assert plan_grammar.parse_final_trailers("body\ndiff_added: 1\n\ndiff_lines: 2\n").lines == ("diff_lines: 2",)


def test_registry_drives_recognition_and_composition() -> None:
    values = {
        "review_status": "complete", "rounds_completed": 2, "difficulty": "MODERATE",
        "diff_added": 3, "diff_deleted": 4, "mechanical_churn": False,
        "oversize_override": "operator", "diff_lines": 7,
    }
    lines = plan_grammar.compose_trailer_lines(values)  # type: ignore[arg-type]
    assert tuple(match.key for match in map(plan_grammar.match_trailer_line, lines) if match) == plan_grammar.TRAILER_KEYS
    assert lines[-2:] == ("oversize_override: operator", "diff_lines: 7")
