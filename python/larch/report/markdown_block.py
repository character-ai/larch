"""Shared marker-delimited Markdown block upsert for report renderers.

The token and timing report renderers each replace a begin/end marker-delimited
Markdown block in a target file under the same state machine (a valid pair, a
lone begin, a lone end, or absent markers). This module owns that state machine
once; each caller supplies its own markers and a diagnostic label so the helper
never references token or timing terminology.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from larch import io as larch_io

WarnFn = Callable[[str], None]


def _stderr_warn(message: str) -> None:
    print(message, file=sys.stderr)


def _marker_line_re(marker: str) -> re.Pattern[str]:
    return re.compile(rf"^\s*<!-- {re.escape(marker)} -->\s*$")


@dataclass(frozen=True)
class BlockMarkers:
    """A validated begin/end marker pair for :func:`replace_markdown_block`."""

    begin: str
    end: str

    def __post_init__(self) -> None:
        if not self.begin or not self.end:
            msg = "block markers must be non-empty"
            raise ValueError(msg)
        if self.begin == self.end:
            msg = "block markers must be distinct"
            raise ValueError(msg)


def replace_markdown_block(
    *,
    target: Path,
    block: str,
    markers: BlockMarkers,
    label: str,
    warn: WarnFn | None = None,
) -> None:
    """Replace the marker-delimited block in ``target`` with ``block``.

    Preserves the historical recovery state machine: a valid begin/end pair is
    replaced in place; a lone begin truncates from the marker; a lone end drops
    the head through the marker; absent markers append. Diagnostic warnings use
    ``label`` as the prefix (e.g. ``"token report"``) so this helper stays free
    of caller terminology. The write goes through ``larch.io.atomic_write`` with
    a same-directory temporary file, preserves the existing file mode, and
    leaves the original file intact if the write fails.
    """
    begin_re = _marker_line_re(markers.begin)
    end_re = _marker_line_re(markers.end)
    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    lines = existing.splitlines(keepends=True)
    begin_idx: int | None = None
    end_idx: int | None = None
    has_begin = False
    has_end = False
    for idx, line in enumerate(lines):
        stripped = line.rstrip("\r\n")
        if begin_re.match(stripped):
            has_begin = True
            if begin_idx is None:
                begin_idx = idx
        if end_re.match(stripped):
            has_end = True
            if begin_idx is not None and end_idx is None:
                end_idx = idx
    emit = warn or _stderr_warn
    if has_begin and has_end and begin_idx is not None and end_idx is not None:
        text = "".join(lines[:begin_idx]) + block + "".join(lines[end_idx + 1 :])
    elif has_begin and not has_end:
        emit(
            f"{label}: warning: {target} has lone <!-- {markers.begin} --> marker; "
            "truncating from marker and rewriting block"
        )
        kept: list[str] = []
        for line in lines:
            if begin_re.match(line.rstrip("\r\n")):
                break
            kept.append(line)
        text = "".join(kept)
        if text and not text.endswith("\n"):
            text += "\n"
        text += block
    elif has_end and not has_begin:
        emit(
            f"{label}: warning: {target} has lone <!-- {markers.end} --> marker; "
            "dropping head through marker and rewriting block"
        )
        kept_tail: list[str] = []
        past = False
        for line in lines:
            if end_re.match(line.rstrip("\r\n")):
                past = True
                continue
            if past:
                kept_tail.append(line)
        text = "".join(kept_tail)
        if text and not text.endswith("\n"):
            text += "\n"
        text += block
    else:
        text = existing + ("\n" if existing else "") + block
    mode = _existing_mode(target)
    larch_io.atomic_write(target, text, mode=mode)


def _existing_mode(path: Path) -> int | None:
    try:
        return path.stat().st_mode & 0o777 if path.is_file() else None
    except OSError:
        return None
