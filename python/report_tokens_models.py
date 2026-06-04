"""Typed data model for /report-tokens analysis."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Literal
from collections.abc import Mapping, Sequence

Skill = Literal["design", "implement"]
VendorName = Literal["claude", "codex", "cursor"]
VENDORS: tuple[VendorName, ...] = ("claude", "codex", "cursor")
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


def safe_int(value: object, default: int = 0) -> int:
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


def workflow_groups(skill: Skill, records: tuple[RunRecord, ...]) -> dict[str, list[RunRecord]]:
    groups: dict[str, list[RunRecord]] = {}
    labels = ("All runs",) if skill == "implement" else ("SIMPLE", "HARD")
    for label in labels:
        groups[label] = []
    for record in records:
        workflow = record.workflow if record.workflow in ("SIMPLE", "HARD") else "unknown"
        if skill == "design":
            if workflow in groups:
                groups[workflow].append(record)
        else:
            groups["All runs"].append(record)
    return {label: items for label, items in groups.items() if items or skill == "design"}


def env_rate(
    names: str | Sequence[str],
    default: float,
    *,
    environ: Mapping[str, str] | None = None,
) -> float:
    env = os.environ if environ is None else environ
    keys = (names,) if isinstance(names, str) else tuple(names)
    for key in keys:
        raw = env.get(key, "").strip()
        if not raw:
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        if value > 0:
            return value
    return default


def display_rates(*, environ: Mapping[str, str] | None = None) -> DisplayRates:
    env = os.environ if environ is None else environ
    return DisplayRates(
        claude_input=env_rate(("LARCH_CLAUDE_INPUT_RATE_PER_M", "LARCH_RATE_CLAUDE_INPUT"), 5.00, environ=env),
        claude_cache_read=env_rate(("LARCH_CLAUDE_CACHE_READ_RATE_PER_M", "LARCH_RATE_CLAUDE_CACHE_READ"), 0.50, environ=env),
        claude_cache_create_5m=env_rate(("LARCH_CLAUDE_CACHE_WRITE_5M_RATE_PER_M", "LARCH_RATE_CLAUDE_CACHE_CREATE", "LARCH_RATE_CLAUDE_CACHE_CREATE_5M"), 6.25, environ=env),
        claude_cache_create_1h=env_rate(("LARCH_CLAUDE_CACHE_WRITE_1H_RATE_PER_M", "LARCH_RATE_CLAUDE_CACHE_CREATE_1H"), 10.00, environ=env),
        claude_output=env_rate(("LARCH_CLAUDE_OUTPUT_RATE_PER_M", "LARCH_RATE_CLAUDE_OUTPUT"), 25.00, environ=env),
        codex_input=env_rate(("LARCH_CODEX_INPUT_RATE_PER_M", "LARCH_RATE_CODEX_INPUT"), 0.44, environ=env),
        codex_cached_input=env_rate(("LARCH_CODEX_CACHED_INPUT_RATE_PER_M", "LARCH_RATE_CODEX_CACHE_READ", "LARCH_RATE_CODEX_CACHED_INPUT"), 0.04, environ=env),
        codex_output=env_rate(("LARCH_CODEX_OUTPUT_RATE_PER_M", "LARCH_RATE_CODEX_OUTPUT"), 3.50, environ=env),
        cursor_input=env_rate(("LARCH_CURSOR_INPUT_RATE_PER_M", "LARCH_RATE_CURSOR_INPUT"), 1.25, environ=env),
        cursor_cache_read=env_rate(("LARCH_CURSOR_CACHE_READ_RATE_PER_M", "LARCH_RATE_CURSOR_CACHE_READ"), 0.25, environ=env),
        cursor_output=env_rate(("LARCH_CURSOR_OUTPUT_RATE_PER_M", "LARCH_RATE_CURSOR_OUTPUT"), 6.00, environ=env),
        claude_blended=env_rate(("LARCH_CLAUDE_RATE_PER_M", "LARCH_TOKEN_RATE_PER_M", "LARCH_RATE_CLAUDE_AGGREGATE"), 0.80, environ=env),
        codex_blended=env_rate(("LARCH_CODEX_RATE_PER_M", "LARCH_RATE_CODEX_AGGREGATE"), 2.00, environ=env),
        cursor_blended=env_rate(("LARCH_CURSOR_RATE_PER_M", "LARCH_RATE_CURSOR_AGGREGATE"), 1.50, environ=env),
    )
