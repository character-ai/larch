"""Shared issue-title predicates and mutation helpers."""

from __future__ import annotations

import re
from typing import Final

from larch.core import config

BUG_PREFIX: Final = "[BUG]"
BUG_TITLE_LIFECYCLE_PREFIXES: Final = (
    config.TRACKING_ISSUE_PREFIX_BY_STATE["done"],
    config.TRACKING_ISSUE_PREFIX_BY_STATE["designed"],
    config.TRACKING_ISSUE_PREFIX_BY_STATE["implementing"],
    config.TRACKING_ISSUE_PREFIX_BY_STATE["stalled"],
)
LIFECYCLE_PREFIXES: Final = (
    *config.TRACKING_ISSUE_PREFIX_BY_STATE.values(),
    "[IN PROGRESS] ",
    "[PLANNED] ",
)
SQUARE_BRACKET_PREFIX_RE: Final = re.compile(r"^\s*((?:\[[A-Za-z0-9 _.-]+\]\s*)+)")


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


def strip_lifecycle_prefix(title: str) -> str:
    """Strip exactly one managed or legacy tracking lifecycle prefix."""
    for prefix in LIFECYCLE_PREFIXES:
        if title.startswith(prefix):
            return title[len(prefix) :]
    return title


def detect_lifecycle_prefix(title: str) -> str:
    """Return the first managed or legacy lifecycle prefix in ``title``."""
    for prefix in LIFECYCLE_PREFIXES:
        if title.startswith(prefix):
            return prefix
    return ""


def leading_square_bracket_prefix(title: str) -> str:
    """Return the joined leading ``[TAG]`` token(s) from a title, or "".

    ``"[BUG] foo"`` -> ``"[BUG]"``; ``"[FEATURE][A] x"`` -> ``"[FEATURE][A]"``;
    ``"foo"`` -> ``""``. Whitespace between tokens is dropped so the caller can
    re-join with single spaces.
    """
    match = SQUARE_BRACKET_PREFIX_RE.match(title or "")
    if not match:
        return ""
    tokens = re.findall(r"\[[A-Za-z0-9 _.-]+\]", match.group(1))
    return "".join(tokens)


def insert_tag_after_bug_prefix(title: str, tag: str) -> str:
    """Insert ``tag`` after a leading bug prefix, or prepend it."""
    if re.search(re.escape(tag), title, re.IGNORECASE):
        return title
    match = re.match(r"^" + re.escape(BUG_PREFIX) + r"\s*", title, re.IGNORECASE)
    if match:
        return f"{BUG_PREFIX} {tag} {title[match.end():]}"
    return f"{tag} {title}"
