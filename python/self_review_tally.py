"""Shared self-review tally expansion helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

_SELF_REVIEW_MODE = "self-review"
_ACCEPTED_COUNT_KEY = "accepted_count"
_REJECTED_COUNT_KEY = "rejected_count"
_SELF_REVIEW_ACCEPTED_PREFIX = "SELF_REVIEW_ACCEPTED"
_SELF_REVIEW_REJECTED_PREFIX = "SELF_REVIEW_REJECTED"


@dataclass(frozen=True)
class SelfReviewTallyItem:
    """Expanded self-review tally row."""

    outcome: str
    finding_id: str
    index: int


def _count(value: object) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def self_review_tally_items(data: object) -> list[SelfReviewTallyItem]:
    """Expand self-review accepted/rejected counts into ordered tally items."""
    if not isinstance(data, dict):
        return []
    typed = cast("dict[str, object]", data)
    if typed.get("mode") != _SELF_REVIEW_MODE:
        return []

    items: list[SelfReviewTallyItem] = []
    for outcome, count, prefix in (
        ("accepted", _count(typed.get(_ACCEPTED_COUNT_KEY)), _SELF_REVIEW_ACCEPTED_PREFIX),
        ("rejected", _count(typed.get(_REJECTED_COUNT_KEY)), _SELF_REVIEW_REJECTED_PREFIX),
    ):
        items.extend(
            SelfReviewTallyItem(outcome=outcome, finding_id=f"{prefix}_{idx}", index=idx)
            for idx in range(1, max(count, 0) + 1)
        )
    return items
