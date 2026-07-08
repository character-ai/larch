"""Shared issue-title predicates for bug mining workflows."""

from __future__ import annotations

from typing import Final

from larch.core import config

BUG_PREFIX: Final = "[BUG]"
BUG_TITLE_LIFECYCLE_PREFIXES: Final = (
    config.TRACKING_ISSUE_PREFIX_BY_STATE["done"],
    config.TRACKING_ISSUE_PREFIX_BY_STATE["designed"],
    config.TRACKING_ISSUE_PREFIX_BY_STATE["implementing"],
    config.TRACKING_ISSUE_PREFIX_BY_STATE["stalled"],
)


def bug_title_match(title: str) -> bool:
    """Return whether a title is a normalized ``[BUG]`` title."""
    normalized: str = title.lstrip()
    while normalized:
        stripped_lifecycle_prefix: bool = False
        for lifecycle_prefix in BUG_TITLE_LIFECYCLE_PREFIXES:
            if normalized[: len(lifecycle_prefix)].casefold() == lifecycle_prefix.casefold():
                normalized = normalized[len(lifecycle_prefix) :].lstrip()
                stripped_lifecycle_prefix = True
                break
        if not stripped_lifecycle_prefix:
            break
    return normalized.casefold().startswith(BUG_PREFIX.casefold())
