"""Typed data model for /report-tokens analysis."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Literal
from collections.abc import Mapping

Skill = Literal["design", "implement"]
# claude_sub = spawned-process Claude (reviewer/voter/CI/scout), distinct from
# the transcript-derived main-agent `claude` lane. Priced at Claude rates; the
# distinct name avoids colliding with the transcript `claude` key (issue #3637).
VendorName = Literal["claude", "codex", "cursor", "claude_sub"]
VENDORS: tuple[VendorName, ...] = ("claude", "codex", "cursor", "claude_sub")
DATE_LEN = 10
_INT_RE = re.compile(r"^[+-]?[0-9]+$")


class SectionPriority(IntEnum):
    """Lower values are retained longer when issue bodies are trimmed."""

    BANNER = 0
    SUMMARY = 10
    AGGREGATE = 20
    BREAKDOWN = 30
    TRENDS = 40
    SUGGESTIONS = 50
    CACHE = 60


@dataclass(frozen=True)
class VendorTotals:
    input: int = 0
    cache_read: int = 0
    cache_create: int = 0
    cache_create_5m: int = 0
    cache_create_1h: int = 0
    cached_input: int = 0
    output: int = 0
    total: int = 0


@dataclass(frozen=True)
class PhaseRow:
    vendor: VendorName
    step: str
    input: int = 0
    cache_read: int = 0
    cache_create: int = 0
    output: int = 0
    total: int = 0


@dataclass(frozen=True)
class RunRecord:
    number: int
    title: str
    url: str
    started_at: str
    closed_at: str
    workflow: str
    claude: VendorTotals
    codex: VendorTotals
    cursor: VendorTotals
    phase_rows: tuple[PhaseRow, ...]
    raw_report: Mapping[str, object]
    claude_cost: float = 0.0
    codex_cost: float = 0.0
    cursor_cost: float = 0.0
    total_cost: float = 0.0
    priced_by_token_cost: bool = False
    # Defaulted (empty) so historical runs and call sites that predate the
    # spawned-Claude lane keep working; populated from the claude_sub lane when
    # present (issue #3637). Frozen VendorTotals is safe as a shared default.
    claude_sub: VendorTotals = VendorTotals()
    claude_sub_cost: float = 0.0


@dataclass(frozen=True)
class ReportSection:
    title: str
    body: str
    priority: SectionPriority


@dataclass(frozen=True)
class DisplayRates:
    claude_input: float
    claude_cache_read: float
    claude_cache_create_5m: float
    claude_cache_create_1h: float
    claude_output: float
    codex_input: float
    codex_cached_input: float
    codex_output: float
    cursor_input: float
    cursor_cache_read: float
    cursor_output: float
    claude_blended: float
    codex_blended: float
    cursor_blended: float


def safe_int(*, value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip().replace(",", "")
        if _INT_RE.fullmatch(stripped):
            return int(stripped)
        try:
            return int(float(stripped))
        except ValueError:
            pass
    return default


def record_date(record: RunRecord) -> str | None:
    value = record.started_at or record.closed_at
    return value[:DATE_LEN] if len(value) >= DATE_LEN else None


def workflow_groups(*, _skill: Skill, records: tuple[RunRecord, ...]) -> dict[str, list[RunRecord]]:
    groups: dict[str, list[RunRecord]] = {"All runs": []}
    for record in records:
        groups["All runs"].append(record)
    return {label: items for label, items in groups.items() if items}
