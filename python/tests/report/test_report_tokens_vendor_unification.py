from __future__ import annotations

import pytest

from larch.report.report_tokens_cost import aggregate_vendor_tokens
from larch.report.report_tokens_models import (
    VendorName,
    VendorTotals,
    effective_vendor_total,
    vendor_totals_from_report,
)
from larch.report.report_tokens_models import RunRecord


def _record(report: dict[str, object]) -> RunRecord:
    """Build a RunRecord the way scan does: per-vendor totals come from the
    canonical BUCKETS-vs-totals fallback over ``report``.
    """
    return RunRecord(
        number=0,
        title="t",
        url="",
        started_at="",
        closed_at="",
        workflow="implement",
        claude=vendor_totals_from_report(report, vendor="claude"),
        codex=vendor_totals_from_report(report, vendor="codex"),
        cursor=vendor_totals_from_report(report, vendor="cursor"),
        claude_sub=vendor_totals_from_report(report, vendor="claude_sub"),
        phase_rows=(),
        raw_report=report,
    )


def _scan_total(report: dict[str, object], vendor: VendorName) -> int:
    """Token total scan stores on the record (and render displays)."""
    return effective_vendor_total(
        totals=vendor_totals_from_report(report, vendor=vendor),
        vendor=vendor,
    )


def _cost_total(report: dict[str, object], vendor: VendorName) -> int:
    """Displayed-cost total the render table emits for one vendor lane."""
    return aggregate_vendor_tokens(record=_record(report), vendor=vendor)


# Shared fixture table: each row names a report shape and the expected effective
# total per vendor present in it. The same report feeds scan and cost so both
# must agree on bucket membership and fallback totals.
FIXTURES: list[tuple[str, dict[str, object], dict[VendorName, int]]] = [
    (
        "bucket-only-claude",
        {"BUCKETS_claude": {"input": 100, "cache_read": 10, "cache_create_5m": 20, "cache_create_1h": 5, "output": 50, "total": 185}},
        {"claude": 185},
    ),
    (
        "totals-only-codex-cached-input",
        {"codex": {"totals": {"input": 100, "cached_input": 200, "output": 50, "total": 350}}},
        {"codex": 350},
    ),
    (
        "partial-totals-bucket-fallback",
        {
            "codex": {"totals": {"input": 1372678, "output": 136032, "total": 31941606}},
            "BUCKETS_codex": {"input": 1372678, "cached_input": 30432896, "output": 136032, "total": 31941606},
            "cursor": {"totals": {"input": 7274822, "output": 446446, "total": 88537990}},
            "BUCKETS_cursor": {"input": 7274822, "cache_read": 80816722, "output": 446446, "total": 88537990},
        },
        {"codex": 31941606, "cursor": 88537990},
    ),
    (
        "claude-split-cache-create-wins-over-explicit-total",
        {"claude": {"totals": {"input": 10, "cache_read": 5, "cache_create_5m": 30, "cache_create_1h": 70, "output": 20, "total": 999}}},
        {"claude": 135},
    ),
    (
        "claude-legacy-cache-create",
        {"claude": {"totals": {"input": 10, "cache_read": 5, "cache_create": 100, "output": 20, "total": 135}}},
        {"claude": 135},
    ),
    (
        "explicit-total-fallback-when-components-zero",
        {"claude": {"totals": {"input": 0, "output": 0, "total": 777}}},
        {"claude": 777},
    ),
    (
        "zero-and-malformed-values",
        {
            "codex": {"totals": {"input": 0, "cached_input": "not-a-number", "output": 0}},
            "BUCKETS_codex": {"input": 0, "cached_input": 0, "output": 0, "total": 0},
            "BUCKETS_claude": {"input": 0},
        },
        {"codex": 0, "claude": 0},
    ),
    (
        "claude-sub-lane",
        {"BUCKETS_claude_sub": {"input": 5000, "cache_read": 80000, "cache_create": 0, "cache_create_5m": 0, "cache_create_1h": 0, "output": 1000, "total": 86000}},
        {"claude_sub": 86000},
    ),
    (
        "cursor-cache-read",
        {"cursor": {"totals": {"input": 100, "cache_read": 500, "output": 50, "total": 650}}},
        {"cursor": 650},
    ),
]


@pytest.mark.parametrize(("name", "report", "expected_per_vendor"), FIXTURES, ids=[row[0] for row in FIXTURES])
def test_scan_and_cost_agree_on_vendor_totals(
    name: str,
    report: dict[str, object],
    expected_per_vendor: dict[VendorName, int],
) -> None:
    # Per-vendor: scan-stored total and displayed-cost total must match the
    # expected value and each other.
    for vendor, expected in expected_per_vendor.items():
        assert _scan_total(report, vendor) == expected, f"{name}: scan total for {vendor}"
        assert _cost_total(report, vendor) == expected, f"{name}: cost total for {vendor}"


def test_claude_split_and_legacy_cache_create_resolve_via_shared_helper() -> None:
    # Split present: legacy cache_create is ignored for the effective total.
    split = VendorTotals(input=1, cache_read=2, cache_create=999, cache_create_5m=10, cache_create_1h=20, output=5, total=0)
    assert effective_vendor_total(totals=split, vendor="claude") == 1 + 2 + 10 + 20 + 5
    # claude_sub shares the Claude shape.
    assert effective_vendor_total(totals=split, vendor="claude_sub") == 1 + 2 + 10 + 20 + 5
    # Legacy only: cache_create folds into the component sum.
    legacy = VendorTotals(input=1, cache_read=2, cache_create=100, output=5, total=0)
    assert effective_vendor_total(totals=legacy, vendor="claude") == 1 + 2 + 100 + 5
