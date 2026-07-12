"""Normative plan heading and trailer grammar.

This module owns syntax only. Consumers retain policy and authority checks, such
as deciding whether an operator-authored oversize override is trusted.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from typing import Final, Literal

HeadingKind = Literal["NEW", "UPDATED", "REWRITTEN", "MAY_UPDATE"]
TrailerKey = Literal[
    "review_status",
    "rounds_completed",
    "difficulty",
    "diff_added",
    "diff_deleted",
    "mechanical_churn",
    "oversize_override",
    "diff_lines",
]

HEADING_KINDS: Final[tuple[HeadingKind, ...]] = ("NEW", "UPDATED", "REWRITTEN", "MAY_UPDATE")
FIRM_HEADING_KINDS: Final[frozenset[HeadingKind]] = frozenset({"NEW", "UPDATED", "REWRITTEN"})
TRAILER_KEYS: Final[tuple[TrailerKey, ...]] = (
    "review_status",
    "rounds_completed",
    "difficulty",
    "diff_added",
    "diff_deleted",
    "mechanical_churn",
    "oversize_override",
    "diff_lines",
)
OPTIONAL_SIZE_TRAILER_KEYS: Final[tuple[TrailerKey, ...]] = (
    "diff_added",
    "diff_deleted",
    "mechanical_churn",
    "oversize_override",
)
CANONICAL_TRAILER_ORDER: Final[tuple[TrailerKey, ...]] = TRAILER_KEYS

HEADING_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<level>##|###)[ \t]+(?P<kind>NEW|UPDATED|REWRITTEN|MAY_UPDATE)(?:[ \t]*:[ \t]*(?P<colon>.+?)|[ \t]+\[(?P<bracket>[^]\r\n]+)\][ \t]*:?)[ \t]*$"
)
TRAILER_LINE_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<key>review_status|rounds_completed|difficulty|diff_added|diff_deleted|mechanical_churn|oversize_override|diff_lines): (?P<value>[^\r\n]+)$"
)
_GENERIC_LEVEL_TWO_RE: Final[re.Pattern[str]] = re.compile(r"^##(?:[ \t]+|$)(?!#)")
_FENCE_MARKER_RE: Final[re.Pattern[str]] = re.compile(r"^(`{3,}|~{3,})(.*)$")
_SIZE_INTEGER_RE: Final[re.Pattern[str]] = re.compile(r"(?:0[0-7]*|[1-9][0-9]*)")
_DIGITS_RE: Final[re.Pattern[str]] = re.compile(r"[0-9]+")


def _balanced_fence_line_indices(lines: list[str]) -> set[int]:
    """Return 0-based indices of lines strictly inside balanced code fences.

    An unmatched opener does not fence later lines, so headings after a truncated
    fence remain visible. A closer must use the same marker character, be at least
    as long as the opener, and carry only a whitespace suffix.
    """
    fenced_lines: set[int] = set()
    stack: list[tuple[int, str, int]] = []
    for index, line in enumerate(lines):
        match = _FENCE_MARKER_RE.match(line.strip())
        if match is None:
            continue
        marker = match.group(1)
        marker_char = marker[0]
        marker_len = len(marker)
        suffix = match.group(2)
        if not stack:
            stack.append((index, marker_char, marker_len))
            continue
        top_index, top_char, top_len = stack[-1]
        if marker_char == top_char and marker_len >= top_len and suffix.strip() == "":
            _ = stack.pop()
            fenced_lines.update(range(top_index + 1, index))
    return fenced_lines


@dataclass(frozen=True)
class HeadingMatch:
    kind: HeadingKind
    path: str
    level: int
    line_number: int = 0

    @property
    def firm(self) -> bool:
        return self.kind in FIRM_HEADING_KINDS


@dataclass(frozen=True)
class HeadingEvent:
    line_number: int
    text: str
    heading: HeadingMatch | None
    generic_level_two: bool


@dataclass(frozen=True)
class TrailerMatch:
    key: TrailerKey
    value: str
    parsed_value: str | int | bool


@dataclass(frozen=True)
class PlanTrailers:
    lines: tuple[str, ...]
    matches: tuple[TrailerMatch, ...]
    start_line: int
    duplicates: tuple[TrailerKey, ...]

    def get(self, key: TrailerKey) -> TrailerMatch | None:
        return next((match for match in reversed(self.matches) if match.key == key), None)

    @property
    def diff_lines(self) -> int | None:
        match = self.get("diff_lines")
        return match.parsed_value if match is not None and isinstance(match.parsed_value, int) else None


def match_heading(line: str, *, line_number: int = 0) -> HeadingMatch | None:
    """Match one accepted whole-line plan heading."""
    match = HEADING_RE.fullmatch(line.rstrip("\r\n"))
    if match is None:
        return None
    path = (match.group("colon") or match.group("bracket") or "").strip()
    if not path:
        return None
    return HeadingMatch(
        kind=match.group("kind"),  # type: ignore[arg-type]  # regex restricts the literal set
        path=path,
        level=len(match.group("level")),
        line_number=line_number,
    )


def iter_heading_events(text: str) -> Iterator[HeadingEvent]:
    """Yield non-fenced heading events, with recognized headings taking precedence."""
    lines = text.splitlines()
    fenced_lines = _balanced_fence_line_indices(lines)
    for line_number, line in enumerate(lines, start=1):
        index = line_number - 1
        if index in fenced_lines or _FENCE_MARKER_RE.match(line.strip()) is not None:
            continue
        heading = match_heading(line, line_number=line_number)
        yield HeadingEvent(
            line_number=line_number,
            text=line,
            heading=heading,
            generic_level_two=heading is None and _GENERIC_LEVEL_TWO_RE.match(line) is not None,
        )


def iter_plan_headings(text: str, *, kinds: frozenset[HeadingKind] | None = None) -> Iterator[HeadingMatch]:
    for event in iter_heading_events(text):
        if event.heading is not None and (kinds is None or event.heading.kind in kinds):
            yield event.heading


def iter_firm_headings(text: str) -> Iterator[HeadingMatch]:
    return iter_plan_headings(text, kinds=FIRM_HEADING_KINDS)


def _parse_trailer_value(key: TrailerKey, value: str) -> str | int | bool | None:
    parsed: str | int | bool | None = value
    if key in {"rounds_completed", "diff_lines"}:
        parsed = int(value, 10) if _DIGITS_RE.fullmatch(value) is not None else None
    elif key in {"diff_added", "diff_deleted"}:
        parsed = None if _SIZE_INTEGER_RE.fullmatch(value) is None else (
            int(value, 8) if len(value) > 1 and value.startswith("0") else int(value, 10)
        )
    elif key == "difficulty" and value not in {"TRIVIAL", "MODERATE", "HARD"}:
        parsed = None
    elif key == "mechanical_churn":
        parsed = {"true": True, "false": False}.get(value)
    elif (key == "oversize_override" and value != "operator") or (key == "review_status" and not value.strip()):
        parsed = None
    return parsed


def match_trailer_line(line: str) -> TrailerMatch | None:
    """Return a typed whole-line trailer match, or ``None`` for malformed input."""
    match = TRAILER_LINE_RE.fullmatch(line.rstrip("\r\n"))
    if match is None:
        return None
    key: TrailerKey = match.group("key")  # type: ignore[assignment]  # regex restricts the literal set
    value = match.group("value")
    parsed = _parse_trailer_value(key, value)
    return None if parsed is None else TrailerMatch(key=key, value=value, parsed_value=parsed)


def iter_trailer_lines(text: str, *, keys: Iterable[TrailerKey] | None = None) -> Iterator[TrailerMatch]:
    """Scan the whole document for valid trailer lines.

    This is the compatibility API for consumers whose historical behavior is a
    whole-document scan. Terminal consumers should use :func:`parse_final_trailers`.
    """
    allowed = frozenset(keys) if keys is not None else None
    for line in text.splitlines():
        match = match_trailer_line(line)
        if match is not None and (allowed is None or match.key in allowed):
            yield match


def parse_final_trailers(text: str, *, require_diff_lines: bool = False) -> PlanTrailers:
    """Parse the final contiguous valid trailer block.

    Blank lines and registry-excluded lines such as ``confidence:`` end the
    block. Duplicate keys are retained and reported for consumer policy.
    """
    lines = text.splitlines()
    while lines and not lines[-1].strip():
        _ = lines.pop()
    matches: list[TrailerMatch] = []
    raw_lines: list[str] = []
    for line in reversed(lines):
        match = match_trailer_line(line)
        if match is None:
            break
        matches.append(match)
        raw_lines.append(line)
    matches.reverse()
    raw_lines.reverse()
    seen: set[TrailerKey] = set()
    duplicates: list[TrailerKey] = []
    for match in matches:
        if match.key in seen and match.key not in duplicates:
            duplicates.append(match.key)
        seen.add(match.key)
    result = PlanTrailers(
        lines=tuple(raw_lines),
        matches=tuple(matches),
        start_line=len(lines) - len(matches) + 1 if matches else len(lines) + 1,
        duplicates=tuple(duplicates),
    )
    if require_diff_lines and (not matches or matches[-1].key != "diff_lines"):
        return PlanTrailers(lines=(), matches=(), start_line=len(lines) + 1, duplicates=())
    return result


def terminal_diff_lines(text: str) -> int | None:
    trailers = parse_final_trailers(text, require_diff_lines=True)
    return trailers.diff_lines


def compose_trailer_lines(values: Mapping[TrailerKey, str | int | bool | None]) -> tuple[str, ...]:
    """Compose validated trailers in canonical order."""
    rendered: list[str] = []
    for key in CANONICAL_TRAILER_ORDER:
        value = values.get(key)
        if value is None:
            continue
        token = str(value).lower() if isinstance(value, bool) else str(value)
        match = match_trailer_line(f"{key}: {token}")
        if match is None:
            raise ValueError(f"invalid {key} trailer value")
        rendered.append(f"{key}: {match.value}")
    return tuple(rendered)


def grammar_prompt() -> str:
    """Return compact drafting guidance from the shared registries."""
    kinds = ", ".join(f"`### {kind}:`" for kind in HEADING_KINDS)
    optional = ", ".join(f"`{key}: <value>`" for key in OPTIONAL_SIZE_TRAILER_KEYS)
    return f"Use per-file headings {kinds}. End with `difficulty: <TRIVIAL|MODERATE|HARD>`, optional {optional}, and terminal `diff_lines: <N>`."
