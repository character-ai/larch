"""Shared review-domain value types and canonical reviewer-item parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal, TypeAlias

ItemKind: TypeAlias = Literal["FINDING", "OOS"]
BoundaryMode: TypeAlias = Literal[
    "finding-heading",
    "oos-heading",
    "item-heading",
    "level-three-heading",
]
CompatibilityBoundary: TypeAlias = Literal["finding_heading", "any_heading"]

_CANONICAL_HEADING_RE = re.compile(r"^###[ \t]+(FINDING|OOS)_([0-9]+):(.*)$")
_LEVEL_THREE_HEADING_RE = re.compile(r"^###(?:[ \t]+|$)")
_FENCE_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
_FENCED_CODE_RE = re.compile(r"(?ms)^[ \t]{0,3}(`{3,}|~{3,}).*?^[ \t]{0,3}\1[ \t]*$")
_SECURITY_TOKEN_RE = re.compile(r"focus-area\s*=\s*security", re.IGNORECASE)
_SECURITY_HEADER_RE = re.compile(
    r"^###[ \t]+(?:OOS|FINDING)_\d+:\s*(?:\[(?:OUT_OF_SCOPE|OOS)\]\s*)?"
    r"`?(?:\[security\]|<security>)`?(?:\s|$|[:-])",
    re.IGNORECASE,
)
_SECURITY_FIELD_RE = re.compile(
    r"^[ \t-]*focus[- ]area[ \t]*[:=][ \t]*security(?:[-a-z0-9 _]*)(?:[ \t]|$|\(|#|\.|,)",
    re.IGNORECASE,
)
_OOS_TAG_RE = re.compile(r"(?:^|\s)\[(?:OUT_OF_SCOPE|OOS)\](?:\s|$|[:-])", re.IGNORECASE)
_FINDING_HEADER_STRIP_RE = re.compile(r"(?m)^### FINDING_[0-9]+:.*$")


@dataclass(frozen=True)
class CanonicalHeading:
    """A canonical reviewer-item heading parsed from one Markdown line."""

    item_id: str
    kind: ItemKind
    number: int
    title: str


@dataclass(frozen=True)
class ParsedBlock:
    """One canonical reviewer-item block with its exact source slice."""

    item_id: str
    kind: ItemKind
    title: str
    block: str
    start: int
    end: int


@dataclass(frozen=True)
class Finding:
    finding_id: str
    title: str
    block: str


class ReviewCoreStatus(StrEnum):
    ok = "ok"
    fix_required = "fix-required"
    cap_reached = "cap-reached"
    zero_findings = "zero-findings"
    panel_failed = "panel-failed"
    aggregator_validation_exhausted = "aggregator-validation-exhausted"
    main_agent_vote_required = "main-agent-vote-required"
    prune_skipped = "prune-skipped"
    error = "error"
    exception = "exception"
    unknown = "unknown"

    @classmethod
    def from_wire(cls, value: str) -> ReviewCoreStatus | str:
        try:
            return cls(value)
        except ValueError:
            return value


class ReviewVote(StrEnum):
    yes = "YES"
    no = "NO"
    judge_error = "JUDGE_ERROR"

    @classmethod
    def from_wire(cls, value: str) -> ReviewVote | str:
        try:
            return cls(value)
        except ValueError:
            return value


class JudgeSeverity(StrEnum):
    major = "major"
    minor = "minor"
    nit = "nit"

    @classmethod
    def from_wire(cls, value: str) -> JudgeSeverity | str:
        try:
            return cls(value)
        except ValueError:
            return value


def parse_canonical_heading(line: str) -> CanonicalHeading | None:
    """Parse an exact ``### FINDING_N:`` or ``### OOS_N:`` heading line."""
    match = _CANONICAL_HEADING_RE.fullmatch(line.rstrip("\r\n"))
    if match is None:
        return None
    kind: ItemKind = "FINDING" if match.group(1) == "FINDING" else "OOS"
    number = int(match.group(2), 10)
    return CanonicalHeading(
        item_id=f"{kind}_{match.group(2)}",
        kind=kind,
        number=number,
        title=match.group(3).strip(),
    )


def is_canonical_heading(line: str, *, kind: ItemKind | None = None) -> bool:
    """Return whether a line is a canonical item heading of the optional kind."""
    heading = parse_canonical_heading(line)
    return heading is not None and (kind is None or heading.kind == kind)


def _line_records(text: str) -> list[tuple[int, int, str, CanonicalHeading | None, bool]]:
    records: list[tuple[int, int, str, CanonicalHeading | None, bool]] = []
    offset = 0
    fence_char = ""
    fence_length = 0
    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        fence_match = _FENCE_RE.match(line)
        in_fence = bool(fence_char)
        if fence_match is not None:
            marker = fence_match.group(1)
            if not in_fence:
                fence_char = marker[0]
                fence_length = len(marker)
                in_fence = True
            elif marker[0] == fence_char and len(marker) >= fence_length and not line[len(fence_match.group(0)) :].strip():
                fence_char = ""
                fence_length = 0
        heading = None if in_fence else parse_canonical_heading(line)
        records.append((offset, offset + len(raw_line), line, heading, not in_fence and bool(_LEVEL_THREE_HEADING_RE.match(line))))
        offset += len(raw_line)
    if offset < len(text):
        line = text[offset:]
        heading = None if fence_char else parse_canonical_heading(line)
        records.append((offset, len(text), line, heading, not fence_char and bool(_LEVEL_THREE_HEADING_RE.match(line))))
    return records


def parse_blocks(text: str, *, boundary: BoundaryMode = "item-heading") -> list[ParsedBlock]:
    """Parse canonical blocks using an explicit Markdown boundary policy."""
    if boundary not in {"finding-heading", "oos-heading", "item-heading", "level-three-heading"}:
        raise ValueError(f"unsupported block boundary: {boundary}")
    records = _line_records(text)
    starts = [(index, record) for index, record in enumerate(records) if record[3] is not None]
    blocks: list[ParsedBlock] = []
    for _start_position, (record_index, record) in enumerate(starts):
        start, _, _, heading, _ = record
        if heading is None:  # pragma: no cover - starts contains headings only
            continue
        end = len(text)
        for next_record in records[record_index + 1 :]:
            next_start, _, _, next_heading, is_level_three = next_record
            is_boundary = (
                (boundary == "finding-heading" and next_heading is not None and next_heading.kind == "FINDING")
                or (boundary == "oos-heading" and next_heading is not None and next_heading.kind == "OOS")
                or (boundary == "item-heading" and next_heading is not None)
                or (boundary == "level-three-heading" and is_level_three)
            )
            if is_boundary:
                end = next_start
                break
        blocks.append(
            ParsedBlock(
                item_id=heading.item_id,
                kind=heading.kind,
                title=heading.title,
                block=text[start:end],
                start=start,
                end=end,
            )
        )
    return blocks


def read_finding_text(path: Path | str) -> str:
    finding_path = Path(path)
    if not finding_path.is_file():
        return ""
    return finding_path.read_text(encoding="utf-8", errors="replace")


def parse_findings_text(
    text: str,
    *,
    boundary: CompatibilityBoundary = "any_heading",
) -> list[Finding]:
    """Compatibility FINDING-only parser backed by canonical block parsing."""
    boundary_map: dict[CompatibilityBoundary, BoundaryMode] = {
        "finding_heading": "finding-heading",
        "any_heading": "level-three-heading",
    }
    if boundary not in boundary_map:
        raise ValueError(f"unsupported finding boundary: {boundary}")
    return [
        Finding(finding_id=block.item_id, title=block.title, block=block.block)
        for block in parse_blocks(text, boundary=boundary_map[boundary])
        if block.kind == "FINDING"
    ]


def parse_findings(
    path: Path | str,
    *,
    boundary: CompatibilityBoundary = "any_heading",
) -> list[Finding]:
    return parse_findings_text(read_finding_text(path), boundary=boundary)


def is_security_block_text(text: str) -> bool:
    """Return whether a reviewer-item block carries an explicit security tag."""
    text_no_fence = _FENCED_CODE_RE.sub("", text)
    text_no_backtick = _INLINE_CODE_RE.sub("", text_no_fence)
    if _SECURITY_TOKEN_RE.search(text_no_backtick):
        return True
    lines = text_no_fence.splitlines()
    if lines and _SECURITY_HEADER_RE.search(lines[0]):
        return True
    return any(_SECURITY_FIELD_RE.search(line.replace("`", "").replace("*", "").strip()) for line in lines)


def is_oos_eligible_block(block: ParsedBlock) -> bool:
    """Return whether a canonical block is eligible for OOS filing."""
    if block.kind == "OOS":
        return True
    first_line = block.block.splitlines()[0] if block.block else ""
    return bool(_OOS_TAG_RE.search(first_line))


def count_non_security_blocks(text: str) -> int:
    """Count fileable OOS items after excluding security-tagged blocks."""
    return sum(
        1
        for block in parse_blocks(text, boundary="item-heading")
        if is_oos_eligible_block(block) and not is_security_block_text(block.block)
    )


def finding_dedup_key(block: str) -> str:
    """Return the stable Location/Concern identity used across review rounds."""

    def field(label: str) -> str:
        match = re.search(rf"(?mi)^- \*\*{label}\*\*:\s*(.*?)\s*$", block)
        return match.group(1) if match else ""

    location = field("Location")
    concern = field("Concern")
    raw = f"{location}\x1f{concern}" if location or concern else _FINDING_HEADER_STRIP_RE.sub("", block)
    return re.sub(r"\s+", " ", raw).strip().lower()
