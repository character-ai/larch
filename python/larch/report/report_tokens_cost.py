# pylint: disable=all
"""Shared token pricing and display-rate authority."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast
from collections.abc import Mapping

from larch.core import config
from larch.core.proc import Runner
from larch.report.report_tokens_models import DisplayRates, RunRecord, VendorName, VENDORS, VendorTotals, safe_int

DEFAULT_VENDOR_MODEL = {
    "codex": config.CODEX_DEFAULT_MODEL,
    "cursor": config.CURSOR_DEFAULT_MODEL,
    "claude": config.CLAUDE_OPUS_4_8_MODEL,
}

# Pricing sources, verified as of 2026-06-11:
# - OpenAI Codex pricing credits for gpt-5.5 at $0.04/credit.
# - Cursor docs models-and-pricing composer-2.5 row + Teams surcharge (see below).
# - Anthropic Claude Opus/Sonnet/Haiku/Fable list-price buckets.

# Teams plan per-token surcharge for non-Auto Cursor agent requests.
# Applies to input, cache-read, and output for composer-2.5 (pinned-model) invocations.
# Source: cursor.com/docs/account/teams/pricing — "Cursor Token Rate $0.25/1M tokens".
# Empirically confirmed via June 2026 usage export (R²=0.998, no per-request fee).
# Override with LARCH_CURSOR_TEAMS_SURCHARGE_PER_M.
CURSOR_TEAMS_TOKEN_RATE_SURCHARGE_PER_M = config.CURSOR_TEAMS_TOKEN_RATE_SURCHARGE_PER_M

# Published Cursor composer-2.5 list rates before the Teams surcharge.
CURSOR_COMPOSER_BASE = {"input": 0.50, "cache_read": 0.20, "output": 2.50}

DEFAULT_RATE_TABLE_PER_M = {
    ("codex", "gpt-5.5"): {
        "input": 5.00,
        "cache_read": 0.50,
        "output": 30.00,
    },
    ("codex", "gpt-5.4-mini"): {
        "input": 0.75,
        "cache_read": 0.075,
        "output": 4.50,
    },
    # Effective non-auto rates include the $0.25/M Teams surcharge per token.
    ("cursor", "composer-2.5"): {
        "input": CURSOR_COMPOSER_BASE["input"] + CURSOR_TEAMS_TOKEN_RATE_SURCHARGE_PER_M,
        "cache_read": CURSOR_COMPOSER_BASE["cache_read"] + CURSOR_TEAMS_TOKEN_RATE_SURCHARGE_PER_M,
        "output": CURSOR_COMPOSER_BASE["output"] + CURSOR_TEAMS_TOKEN_RATE_SURCHARGE_PER_M,
    },
    # Auto mode: flat rate card, no Teams surcharge. Auto bundles input+cache-write.
    ("cursor", config.CURSOR_AUTO_MODEL): {
        "input": 1.25,
        "cache_read": 0.25,
        "output": 6.00,
    },
    ("claude", config.CLAUDE_OPUS_4_8_MODEL): {
        "input": 5.00,
        "cache_read": 0.50,
        "cache_create_5m": 6.25,
        "cache_create_1h": 10.00,
        "output": 25.00,
    },
    ("claude", config.CLAUDE_SONNET_4_6_MODEL): {
        "input": 3.00,
        "cache_read": 0.30,
        "cache_create_5m": 3.75,
        "cache_create_1h": 6.00,
        "output": 15.00,
    },
    ("claude", config.CLAUDE_HAIKU_4_5_MODEL): {
        "input": 1.00,
        "cache_read": 0.10,
        "cache_create_5m": 1.25,
        "cache_create_1h": 2.00,
        "output": 5.00,
    },
    ("claude", config.CLAUDE_FABLE_5_MODEL): {
        "input": 10.00,
        "cache_read": 1.00,
        "cache_create_5m": 12.50,
        "cache_create_1h": 20.00,
        "output": 50.00,
    },
}

CODEX_CURSOR_BLENDED_FLEET_MIX = {
    "input": 0.07,
    "cache_read": 0.92,
    "output": 0.01,
}
DEFAULT_CLAUDE_BLENDED_PER_M = 0.80

# Codex can run two models in one workflow: default-role gpt-5.5 reviewers and
# cheaper gpt-5.4-mini coder/fixer rows. The pricing/display split is keyed on
# these two model ids; every other Codex model (and model-less legacy rows)
# falls back to the vendor default rate via rate_row.
CODEX_MINI_MODEL = config.CODEX_REVIEW_MODEL_DEFAULT
CLAUDE_SUB_MODEL_FLAG_PREFIXES = {
    config.CLAUDE_SONNET_4_6_MODEL: "claude-sub-sonnet",
    config.CLAUDE_HAIKU_4_5_MODEL: "claude-sub-haiku",
    config.CLAUDE_FABLE_5_MODEL: "claude-sub-fable",
}


def rate_row(vendor: str, *, model: str | None = None) -> Mapping[str, float]:
    """Resolve the per-1M rate row for ``(vendor, model)``.

    Falls back to the vendor's ``DEFAULT_VENDOR_MODEL`` row when ``model`` is empty
    or absent from the table. Model-less legacy ledger rows therefore price at the
    vendor default (gpt-5.5 for codex), which is correct for the pre-mini era.
    """
    if model:
        row = DEFAULT_RATE_TABLE_PER_M.get((vendor, model))
        if row is not None:
            return row
    return DEFAULT_RATE_TABLE_PER_M[(vendor, DEFAULT_VENDOR_MODEL[vendor])]


def _default_row(vendor: str) -> Mapping[str, float]:
    return rate_row(vendor)


def _blended_default(vendor: str) -> float:
    row = _default_row(vendor)
    return sum(row[key] * CODEX_CURSOR_BLENDED_FLEET_MIX[key] for key in CODEX_CURSOR_BLENDED_FLEET_MIX)


@dataclass(frozen=True)
class CostBreakdown:
    claude_cost: str
    codex_cost: str
    cursor_cost: str
    claude_sub_cost: str
    total_cost: str
    bucket_costs: dict[str, str]


def env_rate(
    *, names: str | tuple[str, ...],
    default: float,
    environ: Mapping[str, str] | None = None,
) -> float:
    env: Mapping[str, str] = os.environ if environ is None else environ
    keys = (names,) if isinstance(names, str) else names
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


def display_rates(*, environ: Mapping[str, str] | None = None, claude_model: str | None = None) -> DisplayRates:
    env: Mapping[str, str] = os.environ if environ is None else environ
    claude: Mapping[str, float] = rate_row("claude", model=claude_model)
    codex: Mapping[str, float] = _default_row("codex")
    codex_mini: Mapping[str, float] = rate_row("codex", model=CODEX_MINI_MODEL)
    _surcharge = env_rate(names=config.ENV_LARCH_CURSOR_TEAMS_SURCHARGE_PER_M, default=CURSOR_TEAMS_TOKEN_RATE_SURCHARGE_PER_M, environ=env)
    cursor_auto: Mapping[str, float] = rate_row("cursor", model=config.CURSOR_AUTO_MODEL)
    return DisplayRates(
        claude_input=env_rate(names=("LARCH_CLAUDE_INPUT_RATE_PER_M", "LARCH_RATE_CLAUDE_INPUT"), default=claude["input"], environ=env),
        claude_cache_read=env_rate(names=("LARCH_CLAUDE_CACHE_READ_RATE_PER_M", "LARCH_RATE_CLAUDE_CACHE_READ"), default=claude["cache_read"], environ=env),
        claude_cache_create_5m=env_rate(names=("LARCH_CLAUDE_CACHE_WRITE_5M_RATE_PER_M", "LARCH_RATE_CLAUDE_CACHE_CREATE", "LARCH_RATE_CLAUDE_CACHE_CREATE_5M"), default=claude["cache_create_5m"], environ=env),
        claude_cache_create_1h=env_rate(names=("LARCH_CLAUDE_CACHE_WRITE_1H_RATE_PER_M", "LARCH_RATE_CLAUDE_CACHE_CREATE_1H"), default=claude["cache_create_1h"], environ=env),
        claude_output=env_rate(names=("LARCH_CLAUDE_OUTPUT_RATE_PER_M", "LARCH_RATE_CLAUDE_OUTPUT"), default=claude["output"], environ=env),
        codex_input=env_rate(names=("LARCH_CODEX_INPUT_RATE_PER_M", "LARCH_RATE_CODEX_INPUT"), default=codex["input"], environ=env),
        codex_cached_input=env_rate(names=("LARCH_CODEX_CACHED_INPUT_RATE_PER_M", "LARCH_RATE_CODEX_CACHE_READ", "LARCH_RATE_CODEX_CACHED_INPUT"), default=codex["cache_read"], environ=env),
        codex_output=env_rate(names=("LARCH_CODEX_OUTPUT_RATE_PER_M", "LARCH_RATE_CODEX_OUTPUT"), default=codex["output"], environ=env),
        codex_mini_input=env_rate(names=("LARCH_CODEX_MINI_INPUT_RATE_PER_M", "LARCH_RATE_CODEX_MINI_INPUT"), default=codex_mini["input"], environ=env),
        codex_mini_cached_input=env_rate(names=("LARCH_CODEX_MINI_CACHED_INPUT_RATE_PER_M", "LARCH_RATE_CODEX_MINI_CACHE_READ", "LARCH_RATE_CODEX_MINI_CACHED_INPUT"), default=codex_mini["cache_read"], environ=env),
        codex_mini_output=env_rate(names=("LARCH_CODEX_MINI_OUTPUT_RATE_PER_M", "LARCH_RATE_CODEX_MINI_OUTPUT"), default=codex_mini["output"], environ=env),
        cursor_input=env_rate(names=("LARCH_CURSOR_INPUT_RATE_PER_M", "LARCH_RATE_CURSOR_INPUT"), default=CURSOR_COMPOSER_BASE["input"] + _surcharge, environ=env),
        cursor_cache_read=env_rate(names=("LARCH_CURSOR_CACHE_READ_RATE_PER_M", "LARCH_RATE_CURSOR_CACHE_READ"), default=CURSOR_COMPOSER_BASE["cache_read"] + _surcharge, environ=env),
        cursor_output=env_rate(names=("LARCH_CURSOR_OUTPUT_RATE_PER_M", "LARCH_RATE_CURSOR_OUTPUT"), default=CURSOR_COMPOSER_BASE["output"] + _surcharge, environ=env),
        claude_blended=env_rate(names=("LARCH_CLAUDE_RATE_PER_M", "LARCH_TOKEN_RATE_PER_M", "LARCH_RATE_CLAUDE_AGGREGATE"), default=DEFAULT_CLAUDE_BLENDED_PER_M, environ=env),
        codex_blended=env_rate(names=("LARCH_CODEX_RATE_PER_M", "LARCH_RATE_CODEX_AGGREGATE"), default=_blended_default("codex"), environ=env),
        cursor_blended=env_rate(names=("LARCH_CURSOR_RATE_PER_M", "LARCH_RATE_CURSOR_AGGREGATE"), default=_blended_default("cursor"), environ=env),
        cursor_auto_input=env_rate(names="LARCH_CURSOR_AUTO_INPUT_RATE_PER_M", default=cursor_auto["input"], environ=env),
        cursor_auto_cache_read=env_rate(names="LARCH_CURSOR_AUTO_CACHE_READ_RATE_PER_M", default=cursor_auto["cache_read"], environ=env),
        cursor_auto_output=env_rate(names="LARCH_CURSOR_AUTO_OUTPUT_RATE_PER_M", default=cursor_auto["output"], environ=env),
    )


def _as_mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, dict):
        return cast("Mapping[str, object]", value)
    empty: Mapping[str, object] = {}
    return empty


def _bucket(*, record: RunRecord, vendor: VendorName) -> Mapping[str, object]:
    return _as_mapping(record.raw_report.get(f"BUCKETS_{vendor}"))


def _vendor_totals(*, record: RunRecord, vendor: VendorName) -> VendorTotals:
    if vendor == "claude":
        return record.claude
    if vendor == "codex":
        return record.codex
    if vendor == "claude_sub":
        return record.claude_sub
    return record.cursor


def _bucket_total(*, bucket: Mapping[str, object], vendor: VendorName) -> int:
    if vendor in ("claude", "claude_sub"):
        keys = ("input", "cache_read", "cache_create", "cache_create_5m", "cache_create_1h", "output")
    elif vendor == "codex":
        keys = ("input", "cached_input", "output")
    else:
        keys = ("input", "cache_read", "output")
    return sum(safe_int(value=bucket.get(key)) for key in keys)


def _aggregate_tokens(*, totals: VendorTotals, vendor: VendorName) -> int:
    if vendor in ("claude", "claude_sub"):
        split_cache_create = totals.cache_create_5m + totals.cache_create_1h
        cache_create = split_cache_create if split_cache_create > 0 else totals.cache_create
        component_total = totals.input + totals.cache_read + cache_create + totals.output
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


def aggregate_vendor_tokens(*, record: RunRecord, vendor: VendorName) -> int:
    bucket = _bucket(record=record, vendor=vendor)
    bucket_total = _bucket_total(bucket=bucket, vendor=vendor)
    if bucket_total > 0:
        return bucket_total
    return _aggregate_tokens(totals=_vendor_totals(record=record, vendor=vendor), vendor=vendor)


def _codex_argv(*, record: RunRecord, bucket: Mapping[str, object]) -> list[str]:
    """Codex token flags, split by model when the report carries a per-model split.

    Reads ``BUCKETS_codex_by_model`` (added by tokens.py report building); gpt-5.4-mini
    rows route to ``--codex-mini-*`` flags, every other model (gpt-5.5, unknown, and
    model-less legacy) folds into the gpt-5.5 ``--codex-*`` flags. Falls back to the
    model-summed ``BUCKETS_codex`` (priced as gpt-5.5) when no per-model split exists.
    """
    by_model = _as_mapping(record.raw_report.get("BUCKETS_codex_by_model"))
    if not by_model:
        return [
            "--codex-input-tokens", str(safe_int(value=bucket.get("input"))),
            "--codex-cached-input-tokens", str(safe_int(value=bucket.get("cached_input"))),
            "--codex-output-tokens", str(safe_int(value=bucket.get("output"))),
        ]
    main_in = main_cached = main_out = 0
    mini_in = mini_cached = mini_out = 0
    for model, raw_mb in by_model.items():
        mb = _as_mapping(raw_mb)
        if model == CODEX_MINI_MODEL:
            mini_in += safe_int(value=mb.get("input"))
            mini_cached += safe_int(value=mb.get("cached_input"))
            mini_out += safe_int(value=mb.get("output"))
        else:
            main_in += safe_int(value=mb.get("input"))
            main_cached += safe_int(value=mb.get("cached_input"))
            main_out += safe_int(value=mb.get("output"))
    return [
        "--codex-input-tokens", str(main_in),
        "--codex-cached-input-tokens", str(main_cached),
        "--codex-output-tokens", str(main_out),
        "--codex-mini-input-tokens", str(mini_in),
        "--codex-mini-cached-input-tokens", str(mini_cached),
        "--codex-mini-output-tokens", str(mini_out),
    ]


def _cursor_argv(*, record: RunRecord, bucket: Mapping[str, object]) -> list[str]:
    """Cursor token flags, split by model when BUCKETS_cursor_by_model is present.

    Auto-model rows route to --cursor-auto-* flags; all other models (composer-2.5,
    unknown, and model-less legacy) fold into --cursor-* flags priced at surcharged
    non-auto rates. Falls back to BUCKETS_cursor (priced as composer-2.5) when no
    per-model split exists.
    """
    by_model = _as_mapping(record.raw_report.get("BUCKETS_cursor_by_model"))
    if not by_model:
        return [
            "--cursor-input-tokens", str(safe_int(value=bucket.get("input"))),
            "--cursor-cache-read-tokens", str(safe_int(value=bucket.get("cache_read"))),
            "--cursor-output-tokens", str(safe_int(value=bucket.get("output"))),
        ]
    non_auto_in = non_auto_cr = non_auto_out = 0
    auto_in = auto_cr = auto_out = 0
    for model, raw_mb in by_model.items():
        mb = _as_mapping(raw_mb)
        if model == config.CURSOR_AUTO_MODEL:
            auto_in += safe_int(value=mb.get("input"))
            auto_cr += safe_int(value=mb.get("cache_read"))
            auto_out += safe_int(value=mb.get("output"))
        else:
            non_auto_in += safe_int(value=mb.get("input"))
            non_auto_cr += safe_int(value=mb.get("cache_read"))
            non_auto_out += safe_int(value=mb.get("output"))
    return [
        "--cursor-input-tokens", str(non_auto_in),
        "--cursor-cache-read-tokens", str(non_auto_cr),
        "--cursor-output-tokens", str(non_auto_out),
        "--cursor-auto-input-tokens", str(auto_in),
        "--cursor-auto-cache-read-tokens", str(auto_cr),
        "--cursor-auto-output-tokens", str(auto_out),
    ]


def _claude_bucket_argv(*, flag_prefix: str, bucket: Mapping[str, object]) -> list[str]:
    legacy_cache_create = safe_int(value=bucket.get("cache_create"))
    cache_create_5m = safe_int(value=bucket.get("cache_create_5m"))
    cache_create_1h = safe_int(value=bucket.get("cache_create_1h"))
    if legacy_cache_create > 0 and cache_create_5m == 0 and cache_create_1h == 0:
        cache_create_5m = legacy_cache_create
    return [
        f"--{flag_prefix}-input-tokens", str(safe_int(value=bucket.get("input"))),
        f"--{flag_prefix}-cache-read-tokens", str(safe_int(value=bucket.get("cache_read"))),
        f"--{flag_prefix}-cache-write-5m-tokens", str(cache_create_5m),
        f"--{flag_prefix}-cache-write-1h-tokens", str(cache_create_1h),
        f"--{flag_prefix}-output-tokens", str(safe_int(value=bucket.get("output"))),
    ]


def claude_sub_argv_from_buckets(*, by_model: Mapping[str, object], bucket: Mapping[str, object]) -> list[str]:
    if not by_model:
        return _claude_bucket_argv(flag_prefix="claude-sub", bucket=bucket)
    aggregate = {"input": 0, "cache_read": 0, "cache_create_5m": 0, "cache_create_1h": 0, "output": 0}
    families: dict[str, dict[str, int]] = {
        prefix: {"input": 0, "cache_read": 0, "cache_create_5m": 0, "cache_create_1h": 0, "output": 0}
        for prefix in CLAUDE_SUB_MODEL_FLAG_PREFIXES.values()
    }
    for model, raw_mb in by_model.items():
        mb = _as_mapping(raw_mb)
        prefix = CLAUDE_SUB_MODEL_FLAG_PREFIXES.get(str(model))
        target = families[prefix] if prefix is not None else aggregate
        target["input"] += safe_int(value=mb.get("input"))
        target["cache_read"] += safe_int(value=mb.get("cache_read"))
        cache_create_5m = safe_int(value=mb.get("cache_create_5m"))
        cache_create_1h = safe_int(value=mb.get("cache_create_1h"))
        legacy_cache_create = safe_int(value=mb.get("cache_create"))
        if legacy_cache_create > 0 and cache_create_5m == 0 and cache_create_1h == 0:
            cache_create_5m = legacy_cache_create
        target["cache_create_5m"] += cache_create_5m
        target["cache_create_1h"] += cache_create_1h
        target["output"] += safe_int(value=mb.get("output"))
    argv = _claude_bucket_argv(flag_prefix="claude-sub", bucket=aggregate)
    for prefix in CLAUDE_SUB_MODEL_FLAG_PREFIXES.values():
        argv.extend(_claude_bucket_argv(flag_prefix=prefix, bucket=families[prefix]))
    return argv


def _claude_sub_argv(*, record: RunRecord, bucket: Mapping[str, object]) -> list[str]:
    return claude_sub_argv_from_buckets(
        by_model=_as_mapping(record.raw_report.get("BUCKETS_claude_sub_by_model")),
        bucket=bucket,
    )


def token_cost_argv(record: RunRecord, *, plugin_root: Path | None = None) -> list[str]:
    root = plugin_root or Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[3]))
    argv = ["python3", str(root / "python" / "cli.py"), "token", "cost"]
    if record.main_model:
        argv.extend(["--claude-model", record.main_model])
    for vendor in VENDORS:
        bucket = _bucket(record=record, vendor=vendor)
        totals = _vendor_totals(record=record, vendor=vendor)
        flag_prefix = "claude-sub" if vendor == "claude_sub" else vendor
        if bucket and _bucket_total(bucket=bucket, vendor=vendor) > 0:
            if vendor == "claude":
                argv.extend(_claude_bucket_argv(flag_prefix=flag_prefix, bucket=bucket))
            elif vendor == "claude_sub":
                argv.extend(_claude_sub_argv(record=record, bucket=bucket))
            elif vendor == "codex":
                argv.extend(_codex_argv(record=record, bucket=bucket))
            else:
                argv.extend(_cursor_argv(record=record, bucket=bucket))
        else:
            argv.extend([f"--{flag_prefix}-tokens", str(_aggregate_tokens(totals=totals, vendor=vendor))])
    return argv


def _uint(raw: str | None) -> int:
    if raw is None or raw == "":
        return 0
    if not raw.isdigit():
        raise ValueError(f"invalid non-integer token count: {raw}")
    return int(raw)


def _cost_bucket(*, tokens: int, rate: float) -> float:
    if tokens <= 0:
        return 0.0
    return round((tokens / 1_000_000) * rate, 6)


def _cost_blend(*, tokens: int, rate: float) -> float:
    if tokens <= 0:
        return 0.0
    return round((tokens / 1_000_000) * rate, 2)


def _fmt_money(value: float) -> str:
    return f"{value:.2f}"


_FLAG_NAMES = {
    "--claude-tokens": "claude_t",
    "--codex-tokens": "codex_t",
    "--cursor-tokens": "cursor_t",
    "--claude-sub-tokens": "claude_sub_t",
    "--claude-input-tokens": "c_in",
    "--claude-cache-read-tokens": "c_cr",
    "--claude-cache-write-5m-tokens": "c_cw5",
    "--claude-cache-write-1h-tokens": "c_cw1",
    "--claude-output-tokens": "c_out",
    "--codex-input-tokens": "d_in",
    "--codex-cached-input-tokens": "d_cached",
    "--codex-output-tokens": "d_out",
    "--codex-mini-input-tokens": "d_mini_in",
    "--codex-mini-cached-input-tokens": "d_mini_cached",
    "--codex-mini-output-tokens": "d_mini_out",
    "--cursor-input-tokens": "u_in",
    "--cursor-cache-read-tokens": "u_cr",
    "--cursor-output-tokens": "u_out",
    "--cursor-auto-input-tokens": "u_auto_in",
    "--cursor-auto-cache-read-tokens": "u_auto_cr",
    "--cursor-auto-output-tokens": "u_auto_out",
    "--claude-sub-input-tokens": "cs_in",
    "--claude-sub-cache-read-tokens": "cs_cr",
    "--claude-sub-cache-write-5m-tokens": "cs_cw5",
    "--claude-sub-cache-write-1h-tokens": "cs_cw1",
    "--claude-sub-output-tokens": "cs_out",
}

_CLAUDE_SUB_COUNT_KEYS_BY_MODEL = {
    config.CLAUDE_SONNET_4_6_MODEL: ("cs_sonnet_in", "cs_sonnet_cr", "cs_sonnet_cw5", "cs_sonnet_cw1", "cs_sonnet_out"),
    config.CLAUDE_HAIKU_4_5_MODEL: ("cs_haiku_in", "cs_haiku_cr", "cs_haiku_cw5", "cs_haiku_cw1", "cs_haiku_out"),
    config.CLAUDE_FABLE_5_MODEL: ("cs_fable_in", "cs_fable_cr", "cs_fable_cw5", "cs_fable_cw1", "cs_fable_out"),
}

for _model, _keys in _CLAUDE_SUB_COUNT_KEYS_BY_MODEL.items():
    _prefix = CLAUDE_SUB_MODEL_FLAG_PREFIXES[_model]
    _FLAG_NAMES.update({
        f"--{_prefix}-input-tokens": _keys[0],
        f"--{_prefix}-cache-read-tokens": _keys[1],
        f"--{_prefix}-cache-write-5m-tokens": _keys[2],
        f"--{_prefix}-cache-write-1h-tokens": _keys[3],
        f"--{_prefix}-output-tokens": _keys[4],
    })


def _parse_count_args(argv: list[str]) -> dict[str, int]:
    counts: dict[str, int] = dict.fromkeys(_FLAG_NAMES.values(), 0)
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in {"-h", "--help"}:
            raise SystemExit(0)
        if arg not in _FLAG_NAMES or i + 1 >= len(argv):
            raise ValueError(f"unknown or incomplete flag: {arg}")
        counts[_FLAG_NAMES[arg]] = _uint(argv[i + 1])
        i += 2
    return counts


def _parse_pricing_argv(argv: list[str]) -> tuple[list[str], str | None]:
    filtered: list[str] = []
    claude_model: str | None = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--claude-model":
            if i + 1 >= len(argv):
                raise ValueError(f"unknown or incomplete flag: {arg}")
            claude_model = argv[i + 1]
            i += 2
            continue
        filtered.append(arg)
        i += 1
    return filtered, claude_model


def _claude_sub_rates_for_model(model: str) -> Mapping[str, float]:
    return rate_row("claude", model=model)


def _claude_sub_cost_for_counts(*, counts: dict[str, int], keys: tuple[str, str, str, str, str], rates: Mapping[str, float]) -> tuple[int, float]:
    tokens = sum(counts[key] for key in keys)
    cost = round(
        _cost_bucket(tokens=counts[keys[0]], rate=rates["input"])
        + _cost_bucket(tokens=counts[keys[1]], rate=rates["cache_read"])
        + _cost_bucket(tokens=counts[keys[2]], rate=rates["cache_create_5m"])
        + _cost_bucket(tokens=counts[keys[3]], rate=rates["cache_create_1h"])
        + _cost_bucket(tokens=counts[keys[4]], rate=rates["output"]),
        2,
    )
    return tokens, cost


def _pricing_from_counts(
    counts: dict[str, int],
    *,
    env: Mapping[str, str] | None = None,
    claude_model: str | None = None,
) -> tuple[dict[str, str], bool]:
    rates = display_rates(environ=env, claude_model=claude_model)
    c_bucket = any(counts[k] > 0 for k in ("c_in", "c_cr", "c_cw5", "c_cw1", "c_out"))
    d_bucket = any(counts[k] > 0 for k in ("d_in", "d_cached", "d_out"))
    d_mini_bucket = any(counts[k] > 0 for k in ("d_mini_in", "d_mini_cached", "d_mini_out"))
    u_bucket = any(counts[k] > 0 for k in ("u_in", "u_cr", "u_out"))
    u_auto_bucket = any(counts[k] > 0 for k in ("u_auto_in", "u_auto_cr", "u_auto_out"))
    cs_bucket = any(counts[k] > 0 for k in ("cs_in", "cs_cr", "cs_cw5", "cs_cw1", "cs_out"))
    cs_model_buckets = [
        (model, keys)
        for model, keys in _CLAUDE_SUB_COUNT_KEYS_BY_MODEL.items()
        if any(counts[key] > 0 for key in keys)
    ]
    warn = False
    if c_bucket:
        c_tokens = counts["c_in"] + counts["c_cr"] + counts["c_cw5"] + counts["c_cw1"] + counts["c_out"]
        claude = round(
            _cost_bucket(tokens=counts["c_in"], rate=rates.claude_input)
            + _cost_bucket(tokens=counts["c_cr"], rate=rates.claude_cache_read)
            + _cost_bucket(tokens=counts["c_cw5"], rate=rates.claude_cache_create_5m)
            + _cost_bucket(tokens=counts["c_cw1"], rate=rates.claude_cache_create_1h)
            + _cost_bucket(tokens=counts["c_out"], rate=rates.claude_output),
            2,
        )
    else:
        c_tokens = counts["claude_t"]
        warn = warn or c_tokens > 0
        claude = _cost_blend(tokens=c_tokens, rate=rates.claude_blended)
    if d_bucket or d_mini_bucket:
        # gpt-5.5 (default) and gpt-5.4-mini Codex tokens are priced at their own
        # model rates and summed; the lane can mix both models within one round.
        d_tokens = (
            counts["d_in"] + counts["d_cached"] + counts["d_out"]
            + counts["d_mini_in"] + counts["d_mini_cached"] + counts["d_mini_out"]
        )
        codex_5_5 = round(
            _cost_bucket(tokens=counts["d_in"], rate=rates.codex_input)
            + _cost_bucket(tokens=counts["d_cached"], rate=rates.codex_cached_input)
            + _cost_bucket(tokens=counts["d_out"], rate=rates.codex_output),
            2,
        )
        codex_mini = round(
            _cost_bucket(tokens=counts["d_mini_in"], rate=rates.codex_mini_input)
            + _cost_bucket(tokens=counts["d_mini_cached"], rate=rates.codex_mini_cached_input)
            + _cost_bucket(tokens=counts["d_mini_out"], rate=rates.codex_mini_output),
            2,
        )
        codex = round(codex_5_5 + codex_mini, 2)
    else:
        d_tokens = counts["codex_t"]
        warn = warn or d_tokens > 0
        codex = _cost_blend(tokens=d_tokens, rate=rates.codex_blended)
        # Blended fallback has no model breakdown; attribute to the default model.
        codex_5_5 = codex
        codex_mini = 0.0
    if u_bucket or u_auto_bucket:
        u_tokens = (counts["u_in"] + counts["u_cr"] + counts["u_out"]
                    + counts["u_auto_in"] + counts["u_auto_cr"] + counts["u_auto_out"])
        cursor = round(
            _cost_bucket(tokens=counts["u_in"], rate=rates.cursor_input)
            + _cost_bucket(tokens=counts["u_cr"], rate=rates.cursor_cache_read)
            + _cost_bucket(tokens=counts["u_out"], rate=rates.cursor_output)
            + _cost_bucket(tokens=counts["u_auto_in"], rate=rates.cursor_auto_input)
            + _cost_bucket(tokens=counts["u_auto_cr"], rate=rates.cursor_auto_cache_read)
            + _cost_bucket(tokens=counts["u_auto_out"], rate=rates.cursor_auto_output),
            2,
        )
    else:
        u_tokens = counts["cursor_t"]
        warn = warn or u_tokens > 0
        cursor = _cost_blend(tokens=u_tokens, rate=rates.cursor_blended)
    if cs_bucket or cs_model_buckets:
        opus_sub_rates = _claude_sub_rates_for_model(config.CLAUDE_OPUS_4_8_MODEL)
        cs_tokens, claude_sub = _claude_sub_cost_for_counts(
            counts=counts,
            keys=("cs_in", "cs_cr", "cs_cw5", "cs_cw1", "cs_out"),
            rates=opus_sub_rates,
        )
        for model, keys in cs_model_buckets:
            model_tokens, model_cost = _claude_sub_cost_for_counts(
                counts=counts,
                keys=keys,
                rates=_claude_sub_rates_for_model(model),
            )
            cs_tokens += model_tokens
            claude_sub = round(claude_sub + model_cost, 2)
    else:
        cs_tokens = counts["claude_sub_t"]
        warn = warn or cs_tokens > 0
        claude_sub = _cost_blend(tokens=cs_tokens, rate=rates.claude_blended)
    total = round(claude + codex + cursor + claude_sub, 2)
    values: dict[str, str] = {
        "CLAUDE_COST": _fmt_money(claude),
        "CODEX_COST": _fmt_money(codex),
        "CODEX_GPT_5_5_COST": _fmt_money(codex_5_5),
        "CODEX_GPT_5_4_MINI_COST": _fmt_money(codex_mini),
        "CURSOR_COST": _fmt_money(cursor),
        "CLAUDE_SUB_COST": _fmt_money(claude_sub),
        "TOTAL_COST": _fmt_money(total),
        "CLAUDE_TOKENS": str(c_tokens),
        "CODEX_TOKENS": str(d_tokens),
        "CURSOR_TOKENS": str(u_tokens),
        "CLAUDE_SUB_TOKENS": str(cs_tokens),
        "TOTAL_TOKENS": str(c_tokens + d_tokens + u_tokens + cs_tokens),
    }
    return values, warn


def token_cost_from_args(argv: list[str], *, env: Mapping[str, str] | None = None) -> str:
    count_argv, claude_model = _parse_pricing_argv(argv)
    counts = _parse_count_args(count_argv)
    values, warn = _pricing_from_counts(counts, env=env, claude_model=claude_model)
    if warn:
        print(
            "token cost: WARNING: per-bucket counts unavailable; using blended rate (may overstate by ~3-10x)",
            file=sys.stderr,
        )
    order = (
        "CLAUDE_COST", "CODEX_COST", "CODEX_GPT_5_5_COST", "CODEX_GPT_5_4_MINI_COST",
        "CURSOR_COST", "CLAUDE_SUB_COST", "TOTAL_COST",
        "CLAUDE_TOKENS", "CODEX_TOKENS", "CURSOR_TOKENS", "CLAUDE_SUB_TOKENS", "TOTAL_TOKENS",
    )
    return "\n".join(f"{key}={values[key]}" for key in order) + "\n"


def _read_cost_value(*, lines: str, key: str) -> str:
    for line in lines.splitlines():
        name, sep, value = line.partition("=")
        if sep and name == key:
            return value
    return "0.00"


def _emit_cost_line(*, total: str, claude: str, codex_5_5: str, codex_mini: str, cursor: str, total_tokens: str, claude_sub: str) -> str:
    def money(raw: str) -> str:
        try:
            return f"${float(raw):.2f}"
        except ValueError:
            return "$0.00"
    try:
        tok_k = int((int(total_tokens) + 500) / 1000)
    except ValueError:
        tok_k = 0
    return (
        f"💰 Cost: TOTAL ~{money(total)}: Claude {money(claude)}, Codex-5.5 {money(codex_5_5)}, "
        f"Codex-mini {money(codex_mini)}, Cursor {money(cursor)}, Claude (subprocess) {money(claude_sub)}  |  Tokens: {tok_k}k\n"
    )


def render_cost_line_from_args(argv: list[str], *, env: Mapping[str, str] | None = None) -> str:
    quiet = False
    filtered: list[str] = []
    for arg in argv:
        if arg == "--quiet-on-empty":
            quiet = True
        else:
            filtered.append(arg)
    count_argv, _claude_model = _parse_pricing_argv(filtered)
    counts = _parse_count_args(count_argv)
    if quiet and all(value == 0 for value in counts.values()):
        return ""
    # Prefer per-bucket groups when any bucket count is present, matching the shell wrapper.
    cost_lines = token_cost_from_args(filtered, env=env)
    return _emit_cost_line(
        total=_read_cost_value(lines=cost_lines, key="TOTAL_COST"),
        claude=_read_cost_value(lines=cost_lines, key="CLAUDE_COST"),
        codex_5_5=_read_cost_value(lines=cost_lines, key="CODEX_GPT_5_5_COST"),
        codex_mini=_read_cost_value(lines=cost_lines, key="CODEX_GPT_5_4_MINI_COST"),
        cursor=_read_cost_value(lines=cost_lines, key="CURSOR_COST"),
        total_tokens=_read_cost_value(lines=cost_lines, key="TOTAL_TOKENS"),
        claude_sub=_read_cost_value(lines=cost_lines, key="CLAUDE_SUB_COST"),
    )


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
    claude_cost = (aggregate_vendor_tokens(record=record, vendor="claude") / 1_000_000) * rates.claude_blended
    codex_cost = (aggregate_vendor_tokens(record=record, vendor="codex") / 1_000_000) * rates.codex_blended
    cursor_cost = (aggregate_vendor_tokens(record=record, vendor="cursor") / 1_000_000) * rates.cursor_blended
    claude_sub_cost = (aggregate_vendor_tokens(record=record, vendor="claude_sub") / 1_000_000) * rates.claude_blended
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
    _ = runner
    argv = token_cost_argv(record, plugin_root=plugin_root)[4:]
    try:
        parsed = _parse_kv(token_cost_from_args(argv))
    except (SystemExit, ValueError) as exc:
        print(f"Warning: Python token pricing failed for issue #{record.number}; using blended fallback: {exc}", file=sys.stderr)
        return _fallback_cost(record)
    return replace(
        record,
        claude_cost=parsed["CLAUDE_COST"],
        codex_cost=parsed["CODEX_COST"],
        cursor_cost=parsed["CURSOR_COST"],
        claude_sub_cost=parsed.get("CLAUDE_SUB_COST", 0.0),
        total_cost=parsed["TOTAL_COST"],
        priced_by_token_cost=True,
    )


def token_cost_main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    try:
        _ = sys.stdout.write(token_cost_from_args(args))
    except SystemExit as exc:
        code = 0 if exc.code is None else int(str(exc.code))
        if code == 0:
            print("Usage: cli.py token cost [--per-bucket flags...] [--claude-tokens N ...]", file=sys.stderr)
            return 0
        return code
    except ValueError as exc:
        print(f"token cost: {exc}", file=sys.stderr)
        return 2
    return 0


def render_cost_line_main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    try:
        _ = sys.stdout.write(render_cost_line_from_args(args))
    except SystemExit as exc:
        code = 0 if exc.code is None else int(str(exc.code))
        if code == 0:
            print("Usage: cli.py token render-cost-line [--per-bucket flags...] [--quiet-on-empty]", file=sys.stderr)
            return 0
        return code
    except ValueError as exc:
        print(f"token render-cost-line: {exc}", file=sys.stderr)
        return 2
    return 0
