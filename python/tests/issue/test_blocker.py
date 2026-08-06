"""Tests for the surviving prose blocker parser.

Issue #8059 moved discovery and the `blocker all-open` entrypoint to the Rust
owner; the parity matrix in crates/larch-cli/tests/parity.rs and the larch-core
admission tests cover them now.
"""

from __future__ import annotations

import pytest

from larch.issue import blocker


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Depends on #150", [150]),
        ("blocked by #151", [151]),
        ("Blocked on #152", [152]),
        ("Requires #153", [153]),
        ("Needs #154", [154]),
        ("DEPENDS ON #155", [155]),
        ("Depends on **#156**", [156]),
        ("Depends on [#150](https://example.test)", []),
        ("[Depends on #150](https://example.test)", [150]),
        ("Depends on#150", []),
        ("Depends on #1502", [1502]),
        ("Depends on #150a", [150]),
        ("Depends on\n#150", []),
        ("`Depends on #1`\nDepends on #2", [2]),
        ("`Depends on #1\nDepends on #2`", [1, 2]),
        ("Depends on owner/repo#150", []),
    ],
)
def test_parse_prose_blockers(text: str, expected: list[int]) -> None:
    assert blocker.parse_prose_blockers(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("This does not affect release. Depends on #150", [150]),
        ("This is not a blocker, but blocked by #151", [151]),
        ("Not blocked by #152", []),
        ("No longer needs #153", []),
    ],
)
def test_parse_prose_blockers_scopes_negation(text: str, expected: list[int]) -> None:
    assert blocker.parse_prose_blockers(text) == expected
