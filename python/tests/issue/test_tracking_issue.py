"""Tests for the pure tracking-issue helpers retained in Python."""

from __future__ import annotations

import pytest

from larch.issue import tracking_issue


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("Summary", "Summary\n\nCloses #42\n"),
        ("Summary\n", "Summary\n\nCloses #42\n"),
        ("Summary\n\nPart of #42\n", "Summary\n\nCloses #42\n"),
        ("Summary\n\nCloses #42\n", "Summary\n\nCloses #42\n"),
    ],
)
def test_link_pr_closes_is_idempotent(body: str, expected: str) -> None:
    assert tracking_issue.link_pr_closes(body=body, issue_number=42) == expected


@pytest.mark.parametrize(
    "body",
    [
        "Summary says Closes #42 should be added as a footer.\n",
        "```mermaid\nflowchart LR\n  A[Closes #42] --> B\n```\n",
        "```text\nCloses #42\n```\n",
        "Closes #42\n\n## Test plan\n\n- [x] passed\n",
        "Summary\n\nCloses #421\n",
    ],
)
def test_link_pr_closes_only_recognizes_the_exact_final_footer(body: str) -> None:
    linked = tracking_issue.link_pr_closes(body=body, issue_number=42)
    assert linked.count("Closes #42") == 2
    assert linked.rstrip().endswith("Closes #42")


def test_link_pr_disposition_keeps_partial_work_nonclosing() -> None:
    linked = tracking_issue.link_pr_for_disposition(
        body="Summary", issue_number=42, partial=True
    )
    assert linked == "Summary\n\nPart of #42\n"


def test_link_pr_part_of_is_idempotent() -> None:
    body = "Summary\n\nPart of #42\n"
    assert tracking_issue.link_pr_part_of(body=body, issue_number=42) == body
