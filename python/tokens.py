"""Token/timing scraping into typed NDJSON records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import config


@dataclass(frozen=True)
class TokenRecord:
    tool: str
    total_tokens: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_create_tokens: int


@dataclass(frozen=True)
class TimingRecord:
    tool: str
    duration_ms: int


def _int_field(data: dict[str, Any], key: str) -> int:
    value = data.get(key, 0)
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def normalize_sidecar(data: dict[str, Any], *, tool: str) -> TokenRecord | None:
    """Normalize codex/cursor sidecar payloads into a TokenRecord."""
    if not data:
        return None
    total = _int_field(data, "total_tokens")
    if total == 0:
        total = (
            _int_field(data, "input_tokens")
            + _int_field(data, "output_tokens")
            + _int_field(data, "cache_read_tokens")
            + _int_field(data, "cache_create_tokens")
        )
    if total == 0 and not any(key in data for key in config.TOKEN_SIDECAR_KEYS):
        return None
    return TokenRecord(
        tool=tool,
        total_tokens=total,
        input_tokens=_int_field(data, "input_tokens"),
        output_tokens=_int_field(data, "output_tokens"),
        cache_read_tokens=_int_field(data, "cache_read_tokens"),
        cache_create_tokens=_int_field(data, "cache_create_tokens"),
    )


def append_token_record(path: Path, record: TokenRecord) -> None:
    """Append one typed NDJSON line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "tool": record.tool,
        "total_tokens": record.total_tokens,
        "input_tokens": record.input_tokens,
        "output_tokens": record.output_tokens,
        "cache_read_tokens": record.cache_read_tokens,
        "cache_create_tokens": record.cache_create_tokens,
    }
    with path.open("a", encoding="utf-8") as handle:
        _ = handle.write(json.dumps(payload, sort_keys=True) + "\n")


def normalize_timing_sidecar(data: dict[str, Any], *, tool: str) -> TimingRecord | None:
    duration = data.get("duration_ms", data.get("elapsed_ms", 0))
    try:
        duration_ms = int(duration)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if duration_ms <= 0:
        return None
    return TimingRecord(tool=tool, duration_ms=duration_ms)


def scrape_run(
    *,
    sidecar_paths: tuple[tuple[str, Path], ...] = (),
    timing_sidecar_paths: tuple[tuple[str, Path], ...] = (),
    output_path: Path | None = None,
    timing_output_path: Path | None = None,
) -> tuple[TokenRecord, ...]:
    """Aggregate token (and optional timing) records from sidecar JSON files."""
    records: list[TokenRecord] = []
    for tool, path in sidecar_paths:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        record = normalize_sidecar(cast("dict[str, Any]", data), tool=tool)
        if record is None:
            continue
        records.append(record)
        if output_path is not None:
            append_token_record(output_path, record)
    if timing_output_path is not None:
        timing_output_path.parent.mkdir(parents=True, exist_ok=True)
        timing_lines: list[str] = []
        for tool, path in timing_sidecar_paths:
            if not path.is_file():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                continue
            timing = normalize_timing_sidecar(cast("dict[str, Any]", data), tool=tool)
            if timing is None:
                continue
            timing_lines.append(
                json.dumps(
                    {"tool": timing.tool, "duration_ms": timing.duration_ms},
                    sort_keys=True,
                ),
            )
        if timing_lines:
            _ = timing_output_path.write_text(
                "\n".join(timing_lines) + "\n",
                encoding="utf-8",
            )
    return tuple(records)
