"""Typed data model for /report-tokens analysis."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Literal, cast
from collections.abc import Mapping

Skill = Literal["design", "implement"]
# claude_sub = spawned-process Claude (reviewer/voter/CI/scout), distinct from
# the transcript-derived main-agent `claude` lane. Priced at Claude rates; the
# distinct name avoids colliding with the transcript `claude` key (issue #3637).
VendorName = Literal["claude", "codex", "cursor", "claude_sub"]
VENDORS: tuple[VendorName, ...] = ("claude", "codex", "cursor", "claude_sub")
DATE_LEN = 10

# Canonical per-vendor bucket-component descriptors. The single source of truth
# for which fields belong to each vendor lane, so scan, cost, and calibration
# share the same bucket membership. claude_sub shares the Claude shape (it is
# priced at Claude rates; the distinct name avoids colliding with the
# transcript-derived `claude` key, issue #3637).
CLAUDE_COMPONENTS: tuple[str, ...] = (
    "input", "cache_read", "cache_create",
    "cache_create_5m", "cache_create_1h", "output",
)
CODEX_COMPONENTS: tuple[str, ...] = ("input", "cached_input", "output")
CURSOR_COMPONENTS: tuple[str, ...] = ("input", "cache_read", "output")
VENDOR_COMPONENTS: Mapping[VendorName, tuple[str, ...]] = {
    "claude": CLAUDE_COMPONENTS,
    "codex": CODEX_COMPONENTS,
    "cursor": CURSOR_COMPONENTS,
    "claude_sub": CLAUDE_COMPONENTS,
}
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
    main_model: str = ""
    cursor_composer_cost: float | None = None
    cursor_grok_cost: float | None = None


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
    codex_mini_input: float
    codex_mini_cached_input: float
    codex_mini_output: float
    cursor_input: float
    cursor_cache_read: float
    cursor_output: float
    claude_blended: float
    codex_blended: float
    cursor_blended: float
    cursor_grok_input: float = 0.0
    cursor_grok_cache_read: float = 0.0
    cursor_grok_output: float = 0.0


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


def _as_mapping(value: object) -> Mapping[str, object]:
    return cast("Mapping[str, object]", value) if isinstance(value, dict) else {}


def vendor_totals_from_report(report: Mapping[str, object], *, vendor: VendorName) -> VendorTotals:
    """Build ``VendorTotals`` for ``vendor`` from a raw token report.

    A present ``<vendor>.totals.<key>`` field wins; a missing (or null) field
    falls back to ``BUCKETS_<vendor>.<key>`` (issue #5852: the legacy Bash
    report builder only emitted ``{input, output, total}`` for external vendor
    lanes, so cache fields are recovered from the always-correct bucket).
    """
    vendor_obj = _as_mapping(report.get(vendor))
    totals = _as_mapping(vendor_obj.get("totals"))
    buckets = _as_mapping(report.get(f"BUCKETS_{vendor}"))

    def field(key: str) -> int:
        value = totals.get(key)
        if value is not None:
            return safe_int(value=value)
        return safe_int(value=buckets.get(key, 0))

    return VendorTotals(
        input=field("input"),
        cache_read=field("cache_read"),
        cache_create=field("cache_create"),
        cache_create_5m=field("cache_create_5m"),
        cache_create_1h=field("cache_create_1h"),
        cached_input=field("cached_input"),
        output=field("output"),
        total=field("total"),
    )


def claude_effective_cache_create(totals: VendorTotals) -> tuple[int, int]:
    """Return the ``(5m, 1h)`` cache-create counts for a Claude-shaped lane.

    Uses the split values when either is present; otherwise folds the legacy
    ``cache_create`` into the 5m tier (legacy cache creation is priced at the
    5m rate). The single source for the split-or-legacy rule shared by the
    effective-total and pricing paths.
    """
    if totals.cache_create_5m or totals.cache_create_1h:
        return totals.cache_create_5m, totals.cache_create_1h
    return totals.cache_create, 0


def effective_vendor_total(totals: VendorTotals, *, vendor: VendorName) -> int:
    """Canonical per-vendor token total.

    Prefer the nonzero component sum (using ``VENDOR_COMPONENTS`` membership);
    for Claude-shaped lanes use the split cache-create values when either split
    is present, otherwise legacy ``cache_create``; fall back to the explicit
    ``total`` only when every component is zero.
    """
    if vendor in ("claude", "claude_sub"):
        cache_create_5m, cache_create_1h = claude_effective_cache_create(totals)
        component = totals.input + totals.cache_read + cache_create_5m + cache_create_1h + totals.output
    elif vendor == "codex":
        component = totals.input + totals.cached_input + totals.output
    else:
        component = totals.input + totals.cache_read + totals.output
    return component if component > 0 else totals.total


def record_date(record: RunRecord) -> str | None:
    value = record.started_at or record.closed_at
    return value[:DATE_LEN] if len(value) >= DATE_LEN else None


def workflow_groups(*, _skill: Skill, records: tuple[RunRecord, ...]) -> dict[str, list[RunRecord]]:
    groups: dict[str, list[RunRecord]] = {"All runs": []}
    for record in records:
        groups["All runs"].append(record)
    return {label: items for label, items in groups.items() if items}
