"""Frozen difficulty trailer helpers for pre-cutover parity fixtures."""

from __future__ import annotations

import re

from larch.design import plan_grammar

_PLAN_LEGACY_CONFIDENCE_RE = re.compile(r"^confidence: .+$")


def _trailing_metadata_span(lines: list[str]) -> tuple[int, int] | None:
    trailers = plan_grammar.parse_final_trailers("\n".join(lines))
    if not trailers.matches:
        return None
    end = len(lines)
    while end > 0 and not lines[end - 1].strip():
        end -= 1
    return trailers.start_line - 1, end


def trailing_plan_metadata_lines(text: str) -> tuple[str, ...]:
    lines = text.splitlines()
    span = _trailing_metadata_span(lines)
    if span is None:
        return ()
    start, end = span
    return tuple(lines[start:end])


def trailing_plan_difficulty(text: str) -> str:
    for line in reversed(trailing_plan_metadata_lines(text)):
        match = plan_grammar.match_trailer_line(line.strip())
        if match is not None and match.key == "difficulty":
            return match.value
    return ""


def _last_plan_difficulty_line(text: str) -> str:
    for line in reversed(text.splitlines()):
        match = plan_grammar.match_trailer_line(line.strip())
        if match is not None and match.key == "difficulty":
            return match.value
    return ""


def _adjacent_invalid_difficulty(text: str) -> bool:
    lines = text.splitlines()
    span = _trailing_metadata_span(lines)
    index = span[0] if span is not None else len(lines)
    while index > 0:
        line = lines[index - 1].strip()
        if (
            not line
            or plan_grammar.match_trailer_line(line) is not None
            or _PLAN_LEGACY_CONFIDENCE_RE.fullmatch(line)
        ):
            index -= 1
            continue
        if line.startswith("difficulty:"):
            match = plan_grammar.match_trailer_line(line)
            return match is None or match.key != "difficulty"
        return False
    return False


def plan_difficulty(text: str) -> str:
    trailing = trailing_plan_difficulty(text)
    if trailing:
        return trailing
    if _adjacent_invalid_difficulty(text):
        return ""
    return _last_plan_difficulty_line(text)
