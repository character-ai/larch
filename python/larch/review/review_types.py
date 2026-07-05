"""Shared review-domain value types and finding-file parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal

_FINDING_HEADING_RE = re.compile(r"^### (FINDING_[0-9]+):(.*)$", re.MULTILINE)
_ANY_HEADING_RE = re.compile(r"^### ", re.MULTILINE)


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


def read_finding_text(path: Path | str) -> str:
    finding_path = Path(path)
    if not finding_path.is_file():
        return ""
    return finding_path.read_text(encoding="utf-8", errors="replace")


def _next_boundary(*, text: str, start: int, boundary: Literal["finding_heading", "any_heading"]) -> int:
    pattern = _FINDING_HEADING_RE if boundary == "finding_heading" else _ANY_HEADING_RE
    match = pattern.search(text, start)
    return match.start() if match else len(text)


def parse_findings_text(
    text: str,
    *,
    boundary: Literal["finding_heading", "any_heading"] = "any_heading",
) -> list[Finding]:
    if boundary not in {"finding_heading", "any_heading"}:
        raise ValueError(f"unsupported finding boundary: {boundary}")
    findings: list[Finding] = []
    starts = list(_FINDING_HEADING_RE.finditer(text))
    for idx, match in enumerate(starts):
        search_from = match.end()
        if boundary == "finding_heading" and idx + 1 < len(starts):
            end = starts[idx + 1].start()
        else:
            end = _next_boundary(text=text, start=search_from, boundary=boundary)
        findings.append(
            Finding(
                finding_id=match.group(1),
                title=match.group(2).strip(),
                block=text[match.start() : end],
            ),
        )
    return findings


def parse_findings(
    path: Path | str,
    *,
    boundary: Literal["finding_heading", "any_heading"] = "any_heading",
) -> list[Finding]:
    return parse_findings_text(read_finding_text(path), boundary=boundary)
