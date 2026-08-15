# pyright: reportUnusedFunction=false
# The standalone fluff-analysis script imports these private compatibility helpers.
"""Shared finding-id joins retained for the Python fluff-analysis consumer.

The production ``rejected-analysis`` commands are Rust-owned. This narrow
module keeps the legacy run-log join helpers that fluff-analysis imports until
that separate Python consumer migrates.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any, Literal

from larch.core.findings import parse_canonical_heading


def _first_canonical_heading(text: str) -> tuple[str, str] | None:
    """Return (item_id, title) from the first canonical heading, if present."""
    for line in text.splitlines():
        heading = parse_canonical_heading(line)
        if heading is not None:
            return (heading.item_id, heading.title)
    return None


def _finding_tokens(value: str, prose_body: str = "") -> set[str]:
    """Return the shared finding-id aliases used by fluff-analysis joins."""
    heading = _first_canonical_heading(prose_body or "")
    tokens: set[str] = set()
    for raw in (value, heading[0] if heading is not None else ""):
        text = (raw or "").strip().upper()
        if not text:
            continue
        tokens.add(text)
        match = re.match(r"REJ_CR\d+_(\d+)$", text)
        if match:
            tokens.add(f"FINDING_{match.group(1)}")
        match = re.match(r"FINDING_(\d+)$", text)
        if match:
            tokens.add(f"REJ_CR1_{match.group(1)}")
    return tokens


def _lookup_jsonl_record(
    *,
    by_token: Mapping[tuple[str, str], Mapping[str, Any]],
    round_num: str,
    row_id: str,
    allow_unscoped: bool,
) -> Mapping[str, Any] | None | Literal["ambiguous"]:
    matches: list[Mapping[str, Any]] = []
    for token in _finding_tokens(row_id):
        keyed = by_token.get((round_num, token))
        if keyed is not None:
            matches.append(keyed)
        elif allow_unscoped:
            unscoped = by_token.get(("", token))
            if unscoped is not None:
                matches.append(unscoped)
    unique: dict[int, Mapping[str, Any]] = {id(item): item for item in matches}
    if len(unique) > 1:
        return "ambiguous"
    return next(iter(unique.values()), None) if unique else None


def _records_by_round_and_token(
    records: Iterable[Mapping[str, Any]], *, default_round: str = ""
) -> dict[tuple[str, str], Mapping[str, Any]]:
    out: dict[tuple[str, str], Mapping[str, Any]] = {}
    for record in records:
        prose = str(record.get("prose_body") or record.get("body") or record.get("text") or "")
        round_num = str(record.get("round_num") or default_round or "")
        for token in _finding_tokens(str(record.get("id") or ""), prose):
            out[(round_num, token)] = record
    return out
