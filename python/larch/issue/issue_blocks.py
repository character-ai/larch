"""Low-level parsing for larch named issue-body blocks."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from larch.design import plan_grammar


_PLAN_RECEIPT_RE = re.compile(
    r"^[ \t]*<!--[ \t]+larch:plan-receipt[ \t]+v1[ \t]+plan_sha256=([0-9a-f]{64})[ \t]+base_sha=([0-9a-f]{40})[ \t]+blockers_sha256=([0-9a-f]{64})[ \t]+owners_sha256=([0-9a-f]{64})[ \t]+-->[ \t]*$"
)


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


def classify_named_block_lines(  # noqa: PLR0911 - each branch returns one malformed-wire diagnostic.
    *, lines: Sequence[str], marker: str
) -> _BlockSpan:
    fenced_lines = plan_grammar.balanced_fence_line_indices(list(lines))
    start_indexes = [
        idx
        for idx, line in enumerate(lines)
        if idx not in fenced_lines
        and _line_is_marker(line=line, marker=marker, kind="start")
    ]
    end_indexes = [
        idx
        for idx, line in enumerate(lines)
        if idx not in fenced_lines
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
    """Return the requested larch named block inner text and malformed token."""
    lines = body.splitlines(keepends=True)
    span = classify_named_block_lines(lines=lines, marker=marker)
    if span.malformed:
        return None, span.malformed
    if span.start is None or span.end is None:
        return None, ""
    return "".join(lines[span.start + 1 : span.end]), ""


def strip_named_block(*, body: str, marker: str) -> tuple[str, str]:
    """Remove only the requested named block, preserving unrelated larch blocks."""
    lines = body.splitlines(keepends=True)
    span = classify_named_block_lines(lines=lines, marker=marker)
    if span.malformed:
        return "", span.malformed
    if span.start is None or span.end is None:
        return body, ""
    return "".join([*lines[: span.start], *lines[span.end + 1 :]]), ""


def replace_named_block(*, body: str, marker: str, inner: str) -> tuple[str, str]:
    """Replace exactly one named block's inner text without moving its markers."""
    lines = body.splitlines(keepends=True)
    span = classify_named_block_lines(lines=lines, marker=marker)
    if span.malformed:
        return "", span.malformed
    if span.start is None or span.end is None:
        return "", "missing-block"
    inner_lines = inner.splitlines(keepends=True)
    if inner_lines and not inner_lines[-1].endswith(("\n", "\r")):
        marker_line = lines[span.start]
        suffix = "\r\n" if marker_line.endswith("\r\n") else "\n"
        inner_lines[-1] += suffix
    return "".join([*lines[: span.start + 1], *inner_lines, *lines[span.end :]]), ""


def strip_plan_receipt_lines(*, body: str) -> str:
    """Remove every unfenced plan-receipt line for named-block comparison."""
    lines = body.splitlines(keepends=True)
    fenced = plan_grammar.balanced_fence_line_indices(
        [line.rstrip("\r\n") for line in lines]
    )
    return "".join(
        line
        for index, line in enumerate(lines)
        if index in fenced or _PLAN_RECEIPT_RE.match(line.rstrip("\r\n")) is None
    )
