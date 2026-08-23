"""Frozen named-block reader for pre-cutover parity processes.

Production named-block parsing is Rust-owned. This fixture preserves only the
retired pure reader needed by frozen design-router references.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from larch.design import plan_grammar


def named_block_marker_re(*, marker: str, kind: str) -> re.Pattern[str]:
    r"""Compile a case-sensitive, line-anchored named-block marker pattern."""
    return re.compile(
        rf"^[ \t]*<!--[ \t]+larch:{re.escape(marker)}:{kind}[ \t]+-->[ \t]*\r?$",
        re.MULTILINE,
    )


def _line_is_marker(*, line: str, marker: str, kind: str) -> bool:
    return (
        named_block_marker_re(marker=marker, kind=kind).match(line.rstrip("\r\n"))
        is not None
    )


@dataclass(frozen=True)
class _BlockSpan:
    start: int | None
    end: int | None
    malformed: str


def classify_named_block_lines(  # noqa: PLR0911 - frozen branch contract.
    *, lines: Sequence[str], marker: str
) -> _BlockSpan:
    fenced_lines = plan_grammar.balanced_fence_line_indices(list(lines))
    start_indexes = [
        index
        for index, line in enumerate(lines)
        if index not in fenced_lines
        and _line_is_marker(line=line, marker=marker, kind="start")
    ]
    end_indexes = [
        index
        for index, line in enumerate(lines)
        if index not in fenced_lines
        and _line_is_marker(line=line, marker=marker, kind="end")
    ]
    if not start_indexes and not end_indexes:
        return _BlockSpan(None, None, "")
    if len(start_indexes) > 1:
        return _BlockSpan(None, None, "multiple-start")
    if len(end_indexes) > 1:
        return _BlockSpan(None, None, "multiple-end")
    if start_indexes and not end_indexes:
        return _BlockSpan(None, None, "start-without-end")
    if end_indexes and not start_indexes:
        return _BlockSpan(None, None, "end-without-start")
    start = start_indexes[0]
    end = end_indexes[0]
    if end < start:
        return _BlockSpan(None, None, "end-before-start")
    return _BlockSpan(start, end, "")


def parse_named_block(*, body: str, marker: str) -> tuple[str | None, str]:
    """Return the requested larch named block and malformed token."""
    lines = body.splitlines(keepends=True)
    span = classify_named_block_lines(lines=lines, marker=marker)
    if span.malformed:
        return None, span.malformed
    if span.start is None or span.end is None:
        return None, ""
    return "".join(lines[span.start + 1 : span.end]), ""
