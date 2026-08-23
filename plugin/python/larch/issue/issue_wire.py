# pyright: reportUnusedCallResult=false
"""Retained title and untrusted-content helpers for Python renderers."""

from __future__ import annotations

import html
import re
from pathlib import Path

from larch.core import config
from larch.core import redact

_LIFECYCLE_REJECT_STATES = (
    "IMPLEMENTING",
    "DONE",
    "DESIGNING",
    "DESIGNED",
    *config.DEBATE_TITLE_STATES,
)
LIFECYCLE_REJECT_RE = re.compile(
    rf"^\[({'|'.join(_LIFECYCLE_REJECT_STATES)})\]",
    re.IGNORECASE,
)
_LIFECYCLE_INSERT_PREFIXES = (
    *config.DEBATE_TITLE_STATES,
    "DESIGNING",
    "DESIGNED",
    "IMPLEMENTING",
    "DONE",
    "STALLED",
    "IN PROGRESS",
    "PLANNED",
)


def title_lifecycle_reject_marker(title: str) -> str | None:
    """Return the normalized lifecycle marker that rejects a title mutation."""
    match = LIFECYCLE_REJECT_RE.match(title.lstrip())
    if match is None:
        return None
    return f"[{match.group(1).upper()}]"


def insert_signal_marker(*, title: str, marker: str) -> str:
    """Insert one signal marker after any lifecycle prefix."""
    marker_block = f"[{marker}]"
    if not title:
        return marker_block
    rest = title
    while rest.startswith("["):
        close_space = rest.find("] ")
        if close_space < 0:
            break
        block = rest[: close_space + 1]
        if block == marker_block:
            return title
        rest = rest[close_space + 2 :]
    for prefix in _LIFECYCLE_INSERT_PREFIXES:
        block = f"[{prefix}] "
        if title[: len(block)].casefold() == block.casefold():
            return f"{title[: len(block) - 1]} [{marker}] {title[len(block) :]}"
    return f"[{marker}] {title}"


def redact_untrusted_stream(text: str) -> str:
    """Redact secrets and XML-escape untrusted text."""
    return html.escape(redact.redact(text), quote=False)


def emit_untrusted_file_block(*, tag: str, path: Path) -> str:
    """Render one literal-redacted envelope from a file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return emit_untrusted_content_block(tag=tag, text=text)


def emit_untrusted_content_block(*, tag: str, text: str) -> str:
    """Render one literal-redacted envelope from text."""
    return (
        f'<{tag} encoding="literal-redacted">\n'
        f"{redact_untrusted_stream(text)}\n"
        f"</{tag}>\n\n"
    )
