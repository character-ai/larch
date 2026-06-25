"""Tests for analysis.codex_role_costs model-aware Codex pricing."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
from pathlib import Path

from analysis import codex_role_costs as crc
from report_tokens_cost import display_rates

_RATES = display_rates(environ={})


def test_codex_cost_prices_mini_below_default() -> None:
    bucket: dict[str, object] = {"input": 1_000_000, "cached_input": 0, "output": 0}
    assert crc._codex_cost(bucket, _RATES) == _RATES.codex_input
    assert crc._codex_cost(bucket, _RATES, model="gpt-5.4-mini") == _RATES.codex_mini_input
    assert crc._codex_cost(bucket, _RATES, model="gpt-5.4-mini") < crc._codex_cost(bucket, _RATES)


def test_codex_run_cost_sums_per_model_buckets() -> None:
    report: dict[str, object] = {
        "BUCKETS_codex_by_model": {
            "gpt-5.5": {"input": 1_000_000, "cached_input": 0, "output": 0},
            "gpt-5.4-mini": {"input": 1_000_000, "cached_input": 0, "output": 0},
        }
    }
    expected = _RATES.codex_input + _RATES.codex_mini_input
    assert crc._codex_run_cost(report, _RATES) == expected


def test_design_roles_prices_each_row_at_its_own_model(tmp_path: Path) -> None:
    # One review role (codex_review) mixing the generic gpt-5.5 reviewer and the
    # mirrored gpt-5.4-mini reviewer in the same run (issue #5321).
    ledger = tmp_path / "larch-tokens-abc.jsonl"
    _ = ledger.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {"type": "vendor", "vendor": "codex", "raw": "codex_review", "model": "gpt-5.5", "input": 1_000_000, "cache_read": 2_000_000, "output": 500_000},
                {"type": "vendor", "vendor": "codex", "raw": "codex_review", "model": "gpt-5.4-mini", "input": 1_000_000, "cache_read": 2_000_000, "output": 500_000},
            )
        )
        + "\n",
        encoding="utf-8",
    )
    coder, reviewer, other = crc._design_roles(tmp_path, _RATES)
    assert coder == 0.0
    assert other == 0.0

    def at(model: str) -> float:
        bucket: dict[str, object] = {"input": 1_000_000, "cache_read": 2_000_000, "output": 500_000}
        return crc._codex_cost(bucket, _RATES, model=model)

    # Reviewer cost prices each row at its own model rate, not both at gpt-5.5.
    assert abs(reviewer - (at("gpt-5.5") + at("gpt-5.4-mini"))) < 1e-9
    assert reviewer < 2 * at("gpt-5.5")


def test_implement_roles_distribute_model_aware_eff_rate(tmp_path: Path) -> None:
    # per_step totals carry no model; the run-level model-aware effective rate keeps
    # the total correct. A mini-dominated run prices well below the all-gpt-5.5 figure.
    mini_bucket: dict[str, object] = {"input": 1_000_000, "cached_input": 2_000_000, "output": 500_000, "total": 3_500_000}
    summed_bucket: dict[str, object] = {"input": 1_000_000, "cached_input": 2_000_000, "output": 500_000, "total": 3_500_000}
    report: dict[str, object] = {
        "BUCKETS_codex": summed_bucket,
        "BUCKETS_codex_by_model": {"gpt-5.4-mini": mini_bucket},
        "codex": {"per_step": [
            {"step": "Step 2 - implement", "totals": {"input": 1_000_000, "cache_read": 2_000_000, "output": 500_000, "total": 3_500_000}},
        ]},
    }
    coder, reviewer, other = crc._implement_roles(tmp_path, report, _RATES)
    # All tokens are in Step 2 (coder); reviewer/other are zero.
    assert reviewer == 0.0
    assert other == 0.0
    mini_cost = crc._codex_cost(mini_bucket, _RATES, model="gpt-5.4-mini")
    gpt55_cost = crc._codex_cost(summed_bucket, _RATES)
    assert abs(coder - mini_cost) < 1e-6
    assert coder < gpt55_cost
