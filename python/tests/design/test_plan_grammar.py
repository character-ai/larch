from __future__ import annotations

from pathlib import Path

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


def _valid_plan(*, path: str = "python/larch/design/plan_grammar.py") -> str:
    return (
        "## Plan\n\n"
        "### Closed decisions and ownership\n\n"
        "- Extend plan_grammar only.\n\n"
        "### Ordered implementation\n\n"
        "1. Validate the contract.\n"
        "2. Wire callers.\n\n"
        "## Files to modify/create\n\n"
        f"### UPDATED: {path}\n\n"
        "## Acceptance\n\n"
        "- Contract holds.\n\n"
        "## Breaking changes and migration\n\n"
        "Force no longer accepts raw bodies.\n\n"
        "diff_lines: 42\n"
    )


def test_valid_plan_contract_has_no_defects(repo_root: Path) -> None:
    result = plan_grammar.validate_plan_contract(plan_text=_valid_plan(), repo_root=repo_root)
    assert result.ok
    assert result.defects == ()


def test_missing_plan_block_and_multiple_blocks(repo_root: Path) -> None:
    from larch.issue import issue_wire

    assert plan_grammar.validate_issue_plan(issue_body="requirements only", repo_root=repo_root).defects == (
        "missing-plan-block",
    )
    inner = _valid_plan()
    one = issue_wire.compose_named_block(marker="plan", inner=inner)
    two = one + "\n" + issue_wire.compose_named_block(marker="plan", inner=inner)
    assert plan_grammar.validate_issue_plan(issue_body=two, repo_root=repo_root).defects == (
        "multiple-plan-blocks",
    )
    malformed = "<!-- larch:plan:start -->\nonly start\n"
    assert plan_grammar.validate_issue_plan(issue_body=malformed, repo_root=repo_root).defects == (
        "missing-plan-block",
    )


def test_each_m1_facet_token(repo_root: Path) -> None:
    base = _valid_plan()
    cases = {
        "missing-firm-scope": base.replace("### UPDATED: python/larch/design/plan_grammar.py\n", ""),
        "missing-ordered-implementation": base.replace("### Ordered implementation\n\n1. Validate the contract.\n2. Wire callers.\n\n", ""),
        "missing-acceptance": base.replace("## Acceptance\n\n- Contract holds.\n\n", ""),
        "missing-closed-decisions": base.replace("### Closed decisions and ownership\n\n- Extend plan_grammar only.\n\n", ""),
        "missing-breaking-migration": base.replace("## Breaking changes and migration\n\nForce no longer accepts raw bodies.\n\n", ""),
        "missing-diff-lines": base.replace("diff_lines: 42\n", "difficulty: HARD\n"),
    }
    for token, text in cases.items():
        result = plan_grammar.validate_plan_contract(plan_text=text, repo_root=repo_root)
        assert token in result.defects, (token, result.defects)


def test_m1_multi_defect_order_is_deterministic(repo_root: Path) -> None:
    text = "## Plan\n\njust prose\n"
    result = plan_grammar.validate_plan_contract(plan_text=text, repo_root=repo_root)
    assert result.defects == (
        "missing-firm-scope",
        "missing-ordered-implementation",
        "missing-acceptance",
        "missing-closed-decisions",
        "missing-breaking-migration",
        "missing-diff-lines",
    )


def test_crlf_and_fenced_headings_do_not_count_as_scope(repo_root: Path) -> None:
    text = (
        "## Plan\r\n\r\n"
        "### Closed decisions and ownership\r\n\r\n"
        "- Keep CRLF safe.\r\n\r\n"
        "### Ordered implementation\r\n\r\n"
        "1. Handle CRLF.\r\n\r\n"
        "## Files to modify/create\r\n\r\n"
        "```md\r\n"
        "### UPDATED: python/larch/design/plan_grammar.py\r\n"
        "```\r\n"
        "### UPDATED: python/larch/design/plan_grammar.py\r\n\r\n"
        "## Acceptance\r\n\r\n"
        "- ok\r\n\r\n"
        "## Breaking changes and migration\r\n\r\n"
        "None.\r\n\r\n"
        "diff_lines: 9\r\n"
    )
    assert plan_grammar.validate_plan_contract(plan_text=text, repo_root=repo_root).ok


def test_m2_empty_glob_and_missing_updated(repo_root: Path) -> None:
    missing = _valid_plan(path="does/not/exist.py")
    assert "missing-updated-plan-path" in plan_grammar.validate_plan_contract(
        plan_text=missing, repo_root=repo_root
    ).defects
    empty_glob = _valid_plan(path="does/not/match-any-*.zzz")
    assert "empty-plan-glob" in plan_grammar.validate_plan_contract(
        plan_text=empty_glob, repo_root=repo_root
    ).defects


def test_m2_existing_new_and_unsafe_paths(repo_root: Path, tmp_path: Path) -> None:
    existing_new = _valid_plan().replace(
        "### UPDATED: python/larch/design/plan_grammar.py\n",
        "### NEW: python/larch/design/plan_grammar.py\n",
    )
    assert "existing-new-plan-path" in plan_grammar.validate_plan_contract(
        plan_text=existing_new, repo_root=repo_root
    ).defects

    absolute = _valid_plan(path="/etc/passwd")
    assert "unsafe-plan-path" in plan_grammar.validate_plan_contract(
        plan_text=absolute, repo_root=repo_root
    ).defects

    traversal = _valid_plan(path="../outside.py")
    assert "unsafe-plan-path" in plan_grammar.validate_plan_contract(
        plan_text=traversal, repo_root=repo_root
    ).defects

    outside = tmp_path / "outside"
    outside.mkdir()
    link_parent = repo_root / "python" / "larch" / "_symlink_parent_test"
    if link_parent.exists() or link_parent.is_symlink():
        link_parent.unlink()
    try:
        link_parent.symlink_to(outside, target_is_directory=True)
        symlink_plan = (
            "## Plan\n\n"
            "### Closed decisions and ownership\n\n- x\n\n"
            "### Ordered implementation\n\n1. x\n\n"
            "## Files to modify/create\n\n"
            "### NEW: python/larch/_symlink_parent_test/child.py\n\n"
            "## Acceptance\n\n- x\n\n"
            "## Breaking changes and migration\n\nNone.\n\n"
            "diff_lines: 3\n"
        )
        assert "unsafe-plan-path" in plan_grammar.validate_plan_contract(
            plan_text=symlink_plan, repo_root=repo_root
        ).defects
    finally:
        if link_parent.is_symlink() or link_parent.exists():
            link_parent.unlink()


def test_tracked_glob_and_new_under_safe_parent(repo_root: Path) -> None:
    glob_plan = _valid_plan(path="python/larch/design/plan_grammar.py")
    # Use a real tracked glob that matches at least one file.
    glob_plan = glob_plan.replace(
        "### UPDATED: python/larch/design/plan_grammar.py\n",
        "### UPDATED: python/larch/design/plan_*.py\n",
    )
    assert plan_grammar.validate_plan_contract(plan_text=glob_plan, repo_root=repo_root).ok

    new_plan = _valid_plan().replace(
        "### UPDATED: python/larch/design/plan_grammar.py\n",
        "### NEW: python/larch/design/_issue_7780_new_only.py\n",
    )
    assert plan_grammar.validate_plan_contract(plan_text=new_plan, repo_root=repo_root).ok


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]
