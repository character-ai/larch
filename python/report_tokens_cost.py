"""Price report-token runs by delegating to scripts/token-cost.sh."""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path
from typing import cast
from collections.abc import Mapping

from proc import Runner
import redact
from report_tokens_models import RunRecord, VendorName, VENDORS, VendorTotals, display_rates, safe_int


def _as_mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, dict):
        return cast("Mapping[str, object]", value)
    empty: Mapping[str, object] = {}
    return empty


def _bucket(record: RunRecord, vendor: VendorName) -> Mapping[str, object]:
    return _as_mapping(record.raw_report.get(f"BUCKETS_{vendor}"))


def _vendor_totals(record: RunRecord, vendor: VendorName) -> VendorTotals:
    if vendor == "claude":
        return record.claude
    if vendor == "codex":
        return record.codex
    if vendor == "claude_sub":
        return record.claude_sub
    return record.cursor


def _bucket_total(bucket: Mapping[str, object], vendor: VendorName) -> int:
    if vendor in ("claude", "claude_sub"):
        keys = ("input", "cache_read", "cache_create", "cache_create_5m", "cache_create_1h", "output")
    elif vendor == "codex":
        keys = ("input", "cached_input", "output")
    else:
        keys = ("input", "cache_read", "output")
    return sum(safe_int(bucket.get(key)) for key in keys)


def _aggregate_tokens(totals: VendorTotals, vendor: VendorName) -> int:
    if vendor in ("claude", "claude_sub"):
        split_cache_create = totals.cache_create_5m + totals.cache_create_1h
        cache_create = split_cache_create if split_cache_create > 0 else totals.cache_create
        component_total = (
            totals.input
            + totals.cache_read
            + cache_create
            + totals.output
        )
        if component_total > 0:
            return component_total
    elif vendor == "codex":
        component_total = totals.input + totals.cached_input + totals.output
        if component_total > 0:
            return component_total
    else:
        component_total = totals.input + totals.cache_read + totals.output
        if component_total > 0:
            return component_total
    return totals.total


def aggregate_vendor_tokens(record: RunRecord, vendor: VendorName) -> int:
    bucket = _bucket(record, vendor)
    bucket_total = _bucket_total(bucket, vendor)
    if bucket_total > 0:
        return bucket_total
    return _aggregate_tokens(_vendor_totals(record, vendor), vendor)


def token_cost_argv(record: RunRecord, *, plugin_root: Path | None = None) -> list[str]:
    root = plugin_root or Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[1]))
    argv = [str(root / "scripts" / "token-cost.sh")]
    for vendor in VENDORS:
        bucket = _bucket(record, vendor)
        totals = _vendor_totals(record, vendor)
        # token-cost.sh uses hyphenated flag prefixes; the claude_sub vendor key
        # maps to the --claude-sub-* flags (issue #3637).
        flag_prefix = "claude-sub" if vendor == "claude_sub" else vendor
        if bucket and _bucket_total(bucket, vendor) > 0:
            if vendor in ("claude", "claude_sub"):
                legacy_cache_create = safe_int(bucket.get("cache_create"))
                cache_create_5m = safe_int(bucket.get("cache_create_5m"))
                cache_create_1h = safe_int(bucket.get("cache_create_1h"))
                if legacy_cache_create > 0 and cache_create_5m == 0 and cache_create_1h == 0:
                    cache_create_5m = legacy_cache_create
                argv.extend([
                    f"--{flag_prefix}-input-tokens", str(safe_int(bucket.get("input"))),
                    f"--{flag_prefix}-cache-read-tokens", str(safe_int(bucket.get("cache_read"))),
                    f"--{flag_prefix}-cache-write-5m-tokens", str(cache_create_5m),
                    f"--{flag_prefix}-cache-write-1h-tokens", str(cache_create_1h),
                    f"--{flag_prefix}-output-tokens", str(safe_int(bucket.get("output"))),
                ])
            elif vendor == "codex":
                argv.extend([
                    "--codex-input-tokens", str(safe_int(bucket.get("input"))),
                    "--codex-cached-input-tokens", str(safe_int(bucket.get("cached_input"))),
                    "--codex-output-tokens", str(safe_int(bucket.get("output"))),
                ])
            else:
                argv.extend([
                    "--cursor-input-tokens", str(safe_int(bucket.get("input"))),
                    "--cursor-cache-read-tokens", str(safe_int(bucket.get("cache_read"))),
                    "--cursor-output-tokens", str(safe_int(bucket.get("output"))),
                ])
        else:
            argv.extend([f"--{flag_prefix}-tokens", str(_aggregate_tokens(totals, vendor))])
    return argv


def _cost_env() -> dict[str, str]:
    env = dict(os.environ)
    rates = display_rates(environ=env)
    env.update({
        "LARCH_CLAUDE_INPUT_RATE_PER_M": str(rates.claude_input),
        "LARCH_CLAUDE_CACHE_READ_RATE_PER_M": str(rates.claude_cache_read),
        "LARCH_CLAUDE_CACHE_WRITE_5M_RATE_PER_M": str(rates.claude_cache_create_5m),
        "LARCH_CLAUDE_CACHE_WRITE_1H_RATE_PER_M": str(rates.claude_cache_create_1h),
        "LARCH_CLAUDE_OUTPUT_RATE_PER_M": str(rates.claude_output),
        "LARCH_CODEX_INPUT_RATE_PER_M": str(rates.codex_input),
        "LARCH_CODEX_CACHED_INPUT_RATE_PER_M": str(rates.codex_cached_input),
        "LARCH_CODEX_OUTPUT_RATE_PER_M": str(rates.codex_output),
        "LARCH_CURSOR_INPUT_RATE_PER_M": str(rates.cursor_input),
        "LARCH_CURSOR_CACHE_READ_RATE_PER_M": str(rates.cursor_cache_read),
        "LARCH_CURSOR_OUTPUT_RATE_PER_M": str(rates.cursor_output),
        "LARCH_CLAUDE_RATE_PER_M": str(rates.claude_blended),
        "LARCH_CODEX_RATE_PER_M": str(rates.codex_blended),
        "LARCH_CURSOR_RATE_PER_M": str(rates.cursor_blended),
    })
    return env


def _parse_kv(stdout: str) -> dict[str, float]:
    values: dict[str, float] = {}
    for line in stdout.splitlines():
        key, sep, raw = line.partition("=")
        if not sep:
            continue
        try:
            values[key] = float(raw)
        except ValueError:
            continue
    return values


def _fallback_cost(record: RunRecord) -> RunRecord:
    rates = display_rates()
    claude_cost = (aggregate_vendor_tokens(record, "claude") / 1_000_000) * rates.claude_blended
    codex_cost = (aggregate_vendor_tokens(record, "codex") / 1_000_000) * rates.codex_blended
    cursor_cost = (aggregate_vendor_tokens(record, "cursor") / 1_000_000) * rates.cursor_blended
    # claude_sub uses the Claude blended rate in the fallback path (issue #3637).
    claude_sub_cost = (aggregate_vendor_tokens(record, "claude_sub") / 1_000_000) * rates.claude_blended
    total_cost = claude_cost + codex_cost + cursor_cost + claude_sub_cost
    return replace(
        record,
        claude_cost=round(claude_cost, 2),
        codex_cost=round(codex_cost, 2),
        cursor_cost=round(cursor_cost, 2),
        claude_sub_cost=round(claude_sub_cost, 2),
        total_cost=round(total_cost, 2),
        priced_by_token_cost=False,
    )


def price_run(runner: Runner, *, record: RunRecord, plugin_root: Path | None = None) -> RunRecord:
    argv = token_cost_argv(record, plugin_root=plugin_root)
    script = Path(argv[0])
    if not script.is_file():
        print(f"Warning: {script} missing; using blended Python fallback", file=sys.stderr)
        return _fallback_cost(record)
    result = runner.run(argv, env=_cost_env())
    if result.returncode != 0:
        detail = redact.redact(result.stderr.strip())
        suffix = f": {detail[:120]}" if detail else ""
        print(f"Warning: token-cost.sh failed for issue #{record.number}; using blended Python fallback{suffix}", file=sys.stderr)
        return _fallback_cost(record)
    parsed = _parse_kv(result.stdout)
    required = ("CLAUDE_COST", "CODEX_COST", "CURSOR_COST", "TOTAL_COST")
    if not all(key in parsed for key in required):
        print(f"Warning: token-cost.sh output incomplete for issue #{record.number}; using blended Python fallback", file=sys.stderr)
        return _fallback_cost(record)
    # CLAUDE_SUB_COST is parsed leniently (default 0.0) so a token-cost.sh that
    # predates the claude_sub lane still prices the other three lanes; TOTAL_COST
    # from a current token-cost.sh already includes claude_sub (issue #3637).
    return replace(
        record,
        claude_cost=parsed["CLAUDE_COST"],
        codex_cost=parsed["CODEX_COST"],
        cursor_cost=parsed["CURSOR_COST"],
        claude_sub_cost=parsed.get("CLAUDE_SUB_COST", 0.0),
        total_cost=parsed["TOTAL_COST"],
        priced_by_token_cost=True,
    )
