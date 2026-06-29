from __future__ import annotations

# pylint: disable=unused-argument

import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from larch.core.proc import CommandResult
from larch.report.report_tokens_cost import (
    CODEX_CURSOR_BLENDED_FLEET_MIX,
    CODEX_MINI_MODEL,
    DEFAULT_CLAUDE_BLENDED_PER_M,
    DEFAULT_RATE_TABLE_PER_M,
    DEFAULT_VENDOR_MODEL,
    display_rates,
    env_rate,
    price_run,
    rate_row,
    render_cost_line_main,
    token_cost_argv,
    token_cost_from_args,
    token_cost_main,
)
from larch.report.report_tokens_models import RunRecord, VendorTotals


def _calls() -> list[list[str]]:
    return []


@dataclass
class Runner:
    response: CommandResult
    calls: list[list[str]] = field(default_factory=_calls)

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> CommandResult:
        self.calls.append(list(argv))
        return self.response


def _record() -> RunRecord:
    return RunRecord(
        number=1,
        title="t",
        url="u",
        started_at="2026-01-01T00:00:00Z",
        closed_at="2026-01-01T00:00:00Z",
        workflow="",
        claude=VendorTotals(total=100),
        codex=VendorTotals(total=200),
        cursor=VendorTotals(total=300),
        phase_rows=(),
        raw_report={"BUCKETS_claude": {"input": 1, "output": 2}},
    )


def _parsed_cost(argv: list[str], env: Mapping[str, str] | None = None) -> dict[str, str]:
    out = token_cost_from_args(argv, env=env)
    return dict(line.split("=", 1) for line in out.strip().splitlines() if "=" in line)


def test_mixed_bucket_and_blended_argv() -> None:
    argv = token_cost_argv(_record(), plugin_root=Path("/repo"))
    assert "--claude-input-tokens" in argv
    assert "--codex-tokens" in argv
    assert "--cursor-tokens" in argv


def test_zero_bucket_uses_aggregate_tokens() -> None:
    record = RunRecord(
        number=1,
        title="t",
        url="u",
        started_at="2026-01-01T00:00:00Z",
        closed_at="2026-01-01T00:00:00Z",
        workflow="",
        claude=VendorTotals(total=123),
        codex=VendorTotals(total=0),
        cursor=VendorTotals(total=0),
        phase_rows=(),
        raw_report={"BUCKETS_claude": {"input": 0, "malformed": "x"}},
    )
    argv = token_cost_argv(record, plugin_root=Path("/repo"))
    assert "--claude-tokens" in argv
    assert "--claude-input-tokens" not in argv


def test_price_run_uses_python_pricing() -> None:
    runner = Runner(CommandResult(("unused",), 1, "", "ignored", 0.01))
    priced = price_run(runner, record=_record(), plugin_root=Path.cwd().parent)
    assert priced.priced_by_token_cost is True
    assert not runner.calls


def test_python_pricing_includes_claude_sub_cost() -> None:
    rates = display_rates(environ={})
    record = RunRecord(
        number=1,
        title="t",
        url="u",
        started_at="2026-01-01T00:00:00Z",
        closed_at="2026-01-01T00:00:00Z",
        workflow="",
        claude=VendorTotals(),
        codex=VendorTotals(),
        cursor=VendorTotals(),
        phase_rows=(),
        raw_report={"BUCKETS_claude_sub": {"input": 1_000_000}},
    )
    priced = price_run(Runner(CommandResult(("unused",), 0, "", "", 0.01)), record=record, plugin_root=Path.cwd().parent)
    assert priced.claude_sub_cost == rates.claude_input
    assert priced.total_cost == rates.claude_input


def test_real_token_cost_override() -> None:
    old = os.environ.get("LARCH_CLAUDE_INPUT_RATE_PER_M")
    os.environ["LARCH_CLAUDE_INPUT_RATE_PER_M"] = "10"
    try:
        record = RunRecord(
            number=1,
            title="t",
            url="u",
            started_at="2026-01-01T00:00:00Z",
            closed_at="2026-01-01T00:00:00Z",
            workflow="",
            claude=VendorTotals(),
            codex=VendorTotals(),
            cursor=VendorTotals(),
            phase_rows=(),
            raw_report={"BUCKETS_claude": {"input": 1_000_000}},
        )
        priced = price_run(Runner(CommandResult(("unused",), 0, "", "", 0.01)), record=record, plugin_root=Path.cwd().parent)
        assert priced.claude_cost == 10.0
    finally:
        if old is None:
            _ = os.environ.pop("LARCH_CLAUDE_INPUT_RATE_PER_M", None)
        else:
            os.environ["LARCH_CLAUDE_INPUT_RATE_PER_M"] = old


def test_claude_blended_argv_uses_component_sum() -> None:
    record = RunRecord(
        number=1,
        title="t",
        url="u",
        started_at="2026-01-01T00:00:00Z",
        closed_at="2026-01-01T00:00:00Z",
        workflow="",
        claude=VendorTotals(input=10, cache_read=20, cache_create=5, cache_create_5m=30, cache_create_1h=40, output=50, total=999),
        codex=VendorTotals(input=1, cached_input=2, output=3, total=999),
        cursor=VendorTotals(input=4, cache_read=5, output=6, total=999),
        phase_rows=(),
        raw_report={},
    )
    argv = token_cost_argv(record, plugin_root=Path("/repo"))
    assert argv[argv.index("--claude-tokens") + 1] == "150"
    assert argv[argv.index("--codex-tokens") + 1] == "6"
    assert argv[argv.index("--cursor-tokens") + 1] == "15"


def test_legacy_claude_cache_create_bucket_prices_as_cache_write_5m() -> None:
    record = RunRecord(
        number=1,
        title="t",
        url="u",
        started_at="2026-01-01T00:00:00Z",
        closed_at="2026-01-01T00:00:00Z",
        workflow="",
        claude=VendorTotals(),
        codex=VendorTotals(),
        cursor=VendorTotals(),
        phase_rows=(),
        raw_report={"BUCKETS_claude": {"cache_create": 123}},
    )
    argv = token_cost_argv(record, plugin_root=Path("/repo"))
    assert argv[argv.index("--claude-cache-write-5m-tokens") + 1] == "123"
    assert argv[argv.index("--claude-cache-write-1h-tokens") + 1] == "0"



def test_claude_rate_rows_include_cache_tiers_and_default_opus() -> None:
    required = {"input", "cache_read", "cache_create_5m", "cache_create_1h", "output"}
    for model in ("claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5", "claude-fable-5"):
        assert required <= set(rate_row("claude", model=model))
    assert rate_row("claude", model="unknown") == rate_row("claude", model="claude-opus-4-8")


def test_display_rates_can_select_sonnet_main_lane() -> None:
    rates = display_rates(environ={}, claude_model="claude-sonnet-4-6")
    assert rates.claude_input == 3.0
    assert rates.claude_output == 15.0


def test_claude_model_flag_prices_main_lane_and_is_parsed_before_counts() -> None:
    parsed = _parsed_cost([
        "--claude-model", "claude-sonnet-4-6",
        "--claude-input-tokens", "1000000",
        "--claude-output-tokens", "1000000",
    ])
    assert parsed["CLAUDE_COST"] == "18.00"


def test_claude_model_does_not_reprice_aggregate_claude_sub() -> None:
    parsed = _parsed_cost([
        "--claude-model", "claude-sonnet-4-6",
        "--claude-sub-input-tokens", "1000000",
    ])
    assert parsed["CLAUDE_SUB_COST"] == "5.00"


def test_mixed_claude_sub_model_flags_price_by_family() -> None:
    parsed = _parsed_cost([
        "--claude-sub-input-tokens", "1000000",
        "--claude-sub-sonnet-input-tokens", "1000000",
        "--claude-sub-haiku-input-tokens", "1000000",
        "--claude-sub-fable-input-tokens", "1000000",
    ])
    assert parsed["CLAUDE_SUB_COST"] == "19.00"
    assert parsed["CLAUDE_SUB_TOKENS"] == "4000000"


def test_token_cost_argv_emits_main_model_and_claude_sub_model_buckets() -> None:
    record = RunRecord(
        number=1,
        title="t",
        url="u",
        started_at="2026-01-01T00:00:00Z",
        closed_at="2026-01-01T00:00:00Z",
        workflow="",
        claude=VendorTotals(),
        codex=VendorTotals(),
        cursor=VendorTotals(),
        phase_rows=(),
        raw_report={
            "BUCKETS_claude_sub": {"input": 2000000},
            "BUCKETS_claude_sub_by_model": {
                "claude-sonnet-4-6": {"input": 1000000},
                "claude-opus-4-8": {"input": 1000000},
            },
        },
        main_model="claude-sonnet-4-6",
    )
    argv = token_cost_argv(record, plugin_root=Path("/repo"))
    assert argv[4:6] == ["--claude-model", "claude-sonnet-4-6"]
    assert argv[argv.index("--claude-sub-sonnet-input-tokens") + 1] == "1000000"
    assert argv[argv.index("--claude-sub-input-tokens") + 1] == "1000000"


@dataclass
class SubprocessRunner:
    calls: list[list[str]] = field(default_factory=_calls)

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> CommandResult:
        self.calls.append(list(argv))
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, check=False)
        return CommandResult(tuple(argv), result.returncode, result.stdout, result.stderr, 0.01)


def test_real_token_cost_script_receives_rate_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_CLAUDE_INPUT_RATE_PER_M", "10")
    record = RunRecord(
        number=1,
        title="t",
        url="u",
        started_at="2026-01-01T00:00:00Z",
        closed_at="2026-01-01T00:00:00Z",
        workflow="",
        claude=VendorTotals(),
        codex=VendorTotals(),
        cursor=VendorTotals(),
        phase_rows=(),
        raw_report={"BUCKETS_claude": {"input": 1_000_000}},
    )
    priced = price_run(SubprocessRunner(), record=record, plugin_root=Path.cwd().parent)
    assert priced.claude_cost == 10.0


def test_python_pricing_blended_warning(capsys: pytest.CaptureFixture[str]) -> None:
    _ = price_run(Runner(CommandResult(("unused",), 1, "", "bad", 0.01)), record=_record(), plugin_root=Path.cwd().parent)
    captured = capsys.readouterr()
    assert "using blended rate" in captured.err


def test_fallback_cost_uses_component_sums(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_CODEX_RATE_PER_M", "1")
    monkeypatch.setenv("LARCH_CURSOR_RATE_PER_M", "1")
    runner = Runner(CommandResult(("token-cost",), 1, "", "bad", 0.01))
    record = RunRecord(
        number=1,
        title="t",
        url="u",
        started_at="2026-01-01T00:00:00Z",
        closed_at="2026-01-01T00:00:00Z",
        workflow="",
        claude=VendorTotals(),
        codex=VendorTotals(input=1_000_000, output=1_000_000, total=0),
        cursor=VendorTotals(input=1_000_000, cache_read=1_000_000, output=1_000_000, total=0),
        phase_rows=(),
        raw_report={},
    )
    priced = price_run(runner, record=record, plugin_root=Path.cwd().parent)
    assert priced.codex_cost == 2.0
    assert priced.cursor_cost == 3.0


def test_token_cost_cli_emits_kv_grammar(capsys: pytest.CaptureFixture[str]) -> None:
    rates = display_rates(environ={})
    rc = token_cost_main(["--codex-input-tokens", "1000000", "--codex-output-tokens", "1000000"])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = dict(line.split("=", 1) for line in out.strip().splitlines() if "=" in line)
    assert parsed["CLAUDE_COST"] == "0.00"
    expected = f"{rates.codex_input + rates.codex_output:.2f}"
    assert parsed["CODEX_COST"] == expected
    # gpt-5.5-flagged tokens land entirely in the 5.5 split; mini split is zero.
    assert parsed["CODEX_GPT_5_5_COST"] == expected
    assert parsed["CODEX_GPT_5_4_MINI_COST"] == "0.00"
    assert parsed["TOTAL_COST"] == expected
    assert parsed["TOTAL_TOKENS"] == "2000000"
    lines = out.strip().splitlines()
    assert lines[0].startswith("CLAUDE_COST=")
    assert lines[1].startswith("CODEX_COST=")
    assert lines[2].startswith("CODEX_GPT_5_5_COST=")
    assert lines[3].startswith("CODEX_GPT_5_4_MINI_COST=")
    assert lines[6].startswith("TOTAL_COST=")


def test_token_cost_cli_prices_mini_at_mini_rates(capsys: pytest.CaptureFixture[str]) -> None:
    rates = display_rates(environ={})
    rc = token_cost_main(["--codex-mini-input-tokens", "1000000", "--codex-mini-output-tokens", "1000000"])
    assert rc == 0
    parsed = dict(line.split("=", 1) for line in capsys.readouterr().out.strip().splitlines() if "=" in line)
    expected = f"{rates.codex_mini_input + rates.codex_mini_output:.2f}"
    assert parsed["CODEX_COST"] == expected
    assert parsed["CODEX_GPT_5_4_MINI_COST"] == expected
    assert parsed["CODEX_GPT_5_5_COST"] == "0.00"


def test_render_cost_line_cli_emits_terminal_grammar(capsys: pytest.CaptureFixture[str]) -> None:
    rc = render_cost_line_main(["--codex-input-tokens", "1000", "--codex-output-tokens", "500"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("💰 Cost: TOTAL ~$")
    assert "Codex-5.5 $" in out
    assert "Codex-mini $" in out
    assert "Tokens:" in out


def test_display_rates_shipped_defaults_snapshot() -> None:
    assert DEFAULT_VENDOR_MODEL == {
        "codex": "gpt-5.5",
        "cursor": "composer-2.5",
        "claude": "claude-opus-4-8",
    }
    rates = display_rates(environ={})
    codex = DEFAULT_RATE_TABLE_PER_M[("codex", DEFAULT_VENDOR_MODEL["codex"])]
    cursor = DEFAULT_RATE_TABLE_PER_M[("cursor", DEFAULT_VENDOR_MODEL["cursor"])]
    claude = DEFAULT_RATE_TABLE_PER_M[("claude", DEFAULT_VENDOR_MODEL["claude"])]
    assert rates.codex_input == codex["input"]
    assert rates.codex_cached_input == codex["cache_read"]
    assert rates.codex_output == codex["output"]
    assert rates.cursor_input == cursor["input"]
    assert rates.cursor_cache_read == cursor["cache_read"]
    assert rates.cursor_output == cursor["output"]
    assert rates.claude_input == claude["input"]
    assert rates.claude_cache_read == claude["cache_read"]
    assert rates.claude_cache_create_5m == claude["cache_create_5m"]
    assert rates.claude_cache_create_1h == claude["cache_create_1h"]
    assert rates.claude_output == claude["output"]
    assert rates.claude_blended == DEFAULT_CLAUDE_BLENDED_PER_M
    assert rates.codex_blended == sum(codex[key] * weight for key, weight in CODEX_CURSOR_BLENDED_FLEET_MIX.items())
    assert rates.cursor_blended == sum(cursor[key] * weight for key, weight in CODEX_CURSOR_BLENDED_FLEET_MIX.items())


def test_env_rate_alias_precedence() -> None:
    env = {"OLD": "1.5", "NEW": "2.5"}
    assert env_rate(names=("NEW", "OLD"), default=0.1, environ=env) == 2.5
    assert env_rate(names=("BAD", "OLD"), default=0.1, environ={"BAD": "no", "OLD": "3"}) == 3.0
    assert env_rate(names=("BAD", "ZERO", "NEG", "OLD"), default=0.1, environ={"BAD": "no", "ZERO": "0", "NEG": "-1", "OLD": "4"}) == 4.0


@pytest.mark.parametrize(
    ("field_name", "aliases"),
    [
        ("claude_input", ("LARCH_CLAUDE_INPUT_RATE_PER_M", "LARCH_RATE_CLAUDE_INPUT")),
        ("claude_cache_read", ("LARCH_CLAUDE_CACHE_READ_RATE_PER_M", "LARCH_RATE_CLAUDE_CACHE_READ")),
        (
            "claude_cache_create_5m",
            (
                "LARCH_CLAUDE_CACHE_WRITE_5M_RATE_PER_M",
                "LARCH_RATE_CLAUDE_CACHE_CREATE",
                "LARCH_RATE_CLAUDE_CACHE_CREATE_5M",
            ),
        ),
        ("claude_cache_create_1h", ("LARCH_CLAUDE_CACHE_WRITE_1H_RATE_PER_M", "LARCH_RATE_CLAUDE_CACHE_CREATE_1H")),
        ("claude_output", ("LARCH_CLAUDE_OUTPUT_RATE_PER_M", "LARCH_RATE_CLAUDE_OUTPUT")),
        ("codex_input", ("LARCH_CODEX_INPUT_RATE_PER_M", "LARCH_RATE_CODEX_INPUT")),
        (
            "codex_cached_input",
            ("LARCH_CODEX_CACHED_INPUT_RATE_PER_M", "LARCH_RATE_CODEX_CACHE_READ", "LARCH_RATE_CODEX_CACHED_INPUT"),
        ),
        ("codex_output", ("LARCH_CODEX_OUTPUT_RATE_PER_M", "LARCH_RATE_CODEX_OUTPUT")),
        ("cursor_input", ("LARCH_CURSOR_INPUT_RATE_PER_M", "LARCH_RATE_CURSOR_INPUT")),
        ("cursor_cache_read", ("LARCH_CURSOR_CACHE_READ_RATE_PER_M", "LARCH_RATE_CURSOR_CACHE_READ")),
        ("cursor_output", ("LARCH_CURSOR_OUTPUT_RATE_PER_M", "LARCH_RATE_CURSOR_OUTPUT")),
        (
            "claude_blended",
            ("LARCH_CLAUDE_RATE_PER_M", "LARCH_TOKEN_RATE_PER_M", "LARCH_RATE_CLAUDE_AGGREGATE"),
        ),
        ("codex_blended", ("LARCH_CODEX_RATE_PER_M", "LARCH_RATE_CODEX_AGGREGATE")),
        ("cursor_blended", ("LARCH_CURSOR_RATE_PER_M", "LARCH_RATE_CURSOR_AGGREGATE")),
    ],
)
def test_display_rates_alias_ladder(field_name: str, aliases: tuple[str, ...]) -> None:
    for idx, alias in enumerate(aliases, start=1):
        env = {alias: str(40 + idx)}
        assert getattr(display_rates(environ=env), field_name) == 40 + idx


def test_codex_and_cursor_blended_defaults_derive_from_fleet_mix() -> None:
    rates = display_rates(environ={})
    assert CODEX_CURSOR_BLENDED_FLEET_MIX == {"input": 0.07, "cache_read": 0.92, "output": 0.01}
    assert rates.codex_blended == (
        rates.codex_input * CODEX_CURSOR_BLENDED_FLEET_MIX["input"]
        + rates.codex_cached_input * CODEX_CURSOR_BLENDED_FLEET_MIX["cache_read"]
        + rates.codex_output * CODEX_CURSOR_BLENDED_FLEET_MIX["output"]
    )
    assert rates.cursor_blended == (
        rates.cursor_input * CODEX_CURSOR_BLENDED_FLEET_MIX["input"]
        + rates.cursor_cache_read * CODEX_CURSOR_BLENDED_FLEET_MIX["cache_read"]
        + rates.cursor_output * CODEX_CURSOR_BLENDED_FLEET_MIX["output"]
    )


def test_bucket_pricing_ignores_blended_override_ladder() -> None:
    parsed = _parsed_cost(
        [
            "--claude-input-tokens", "1000000",
            "--codex-input-tokens", "1000000",
            "--cursor-input-tokens", "1000000",
        ],
        env={
            "LARCH_TOKEN_RATE_PER_M": "99",
            "LARCH_CLAUDE_RATE_PER_M": "88",
            "LARCH_CODEX_RATE_PER_M": "77",
            "LARCH_CURSOR_RATE_PER_M": "66",
            "LARCH_CLAUDE_INPUT_RATE_PER_M": "11",
            "LARCH_CODEX_INPUT_RATE_PER_M": "22",
            "LARCH_CURSOR_INPUT_RATE_PER_M": "33",
        },
    )
    assert parsed["CLAUDE_COST"] == "11.00"
    assert parsed["CODEX_COST"] == "22.00"
    assert parsed["CURSOR_COST"] == "33.00"


def test_blended_pricing_override_ladder_uses_vendor_before_legacy_token_rate() -> None:
    parsed = _parsed_cost(
        ["--claude-tokens", "1000000", "--codex-tokens", "1000000", "--cursor-tokens", "1000000"],
        env={
            "LARCH_TOKEN_RATE_PER_M": "99",
            "LARCH_CLAUDE_RATE_PER_M": "88",
            "LARCH_CODEX_RATE_PER_M": "77",
            "LARCH_CURSOR_RATE_PER_M": "66",
        },
    )
    assert parsed["CLAUDE_COST"] == "88.00"
    assert parsed["CODEX_COST"] == "77.00"
    assert parsed["CURSOR_COST"] == "66.00"

    legacy_claude = _parsed_cost(
        ["--claude-tokens", "1000000", "--codex-tokens", "1000000"],
        env={"LARCH_TOKEN_RATE_PER_M": "55", "LARCH_CODEX_RATE_PER_M": "44"},
    )
    assert legacy_claude["CLAUDE_COST"] == "55.00"
    assert legacy_claude["CODEX_COST"] == "44.00"


def test_4b3c1a5a_repricing_regression(capsys: pytest.CaptureFixture[str]) -> None:
    rates = display_rates(environ={})
    rc = token_cost_main([
        "--codex-input-tokens", "4580000",
        "--codex-cached-input-tokens", "77100000",
        "--codex-output-tokens", "475000",
        "--cursor-input-tokens", "8000000",
        "--cursor-cache-read-tokens", "89100000",
        "--cursor-output-tokens", "425000",
    ])
    assert rc == 0
    parsed = dict(line.split("=", 1) for line in capsys.readouterr().out.strip().splitlines() if "=" in line)
    expected_codex = round(
        ((4_580_000 / 1_000_000) * rates.codex_input)
        + ((77_100_000 / 1_000_000) * rates.codex_cached_input)
        + ((475_000 / 1_000_000) * rates.codex_output),
        2,
    )
    expected_cursor = round(
        ((8_000_000 / 1_000_000) * rates.cursor_input)
        + ((89_100_000 / 1_000_000) * rates.cursor_cache_read)
        + ((425_000 / 1_000_000) * rates.cursor_output),
        2,
    )
    assert abs(float(parsed["CODEX_COST"]) - expected_codex) < 0.01
    assert abs(float(parsed["CURSOR_COST"]) - expected_cursor) < 0.01


def test_default_vendor_models_match_agent_model_args(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("LARCH_CODEX_MODEL", "CLAUDE_PLUGIN_OPTION_CODEX_MODEL", "LARCH_CURSOR_MODEL", "CLAUDE_PLUGIN_OPTION_CURSOR_MODEL"):
        monkeypatch.delenv(key, raising=False)

    def resolved(tool: str, flag: str) -> str:
        cli = Path(__file__).resolve().parents[2] / "cli.py"
        result = subprocess.run(
            [sys.executable, str(cli), "agent", "model-args", "--tool", tool],
            capture_output=True,
            text=True,
            check=True,
        )
        args = result.stdout.splitlines()
        return args[args.index(flag) + 1]

    assert resolved("codex", "-m") == DEFAULT_VENDOR_MODEL["codex"]
    assert resolved("cursor", "--model") == DEFAULT_VENDOR_MODEL["cursor"]


def test_codex_mini_rate_row_is_available() -> None:
    row = DEFAULT_RATE_TABLE_PER_M[("codex", "gpt-5.4-mini")]
    assert row["input"] == 0.75
    assert row["cache_read"] == 0.075
    assert row["output"] == 4.50


def test_rate_row_resolves_by_vendor_and_model() -> None:
    assert rate_row("codex", model="gpt-5.4-mini") == DEFAULT_RATE_TABLE_PER_M[("codex", CODEX_MINI_MODEL)]
    assert rate_row("codex", model="gpt-5.5") == DEFAULT_RATE_TABLE_PER_M[("codex", "gpt-5.5")]


def test_rate_row_unknown_and_missing_model_fall_back_to_vendor_default() -> None:
    default = DEFAULT_RATE_TABLE_PER_M[("codex", DEFAULT_VENDOR_MODEL["codex"])]
    assert rate_row("codex", model="gpt-9-imaginary") == default
    assert rate_row("codex", model="") == default
    assert rate_row("codex", model=None) == default
    assert rate_row("codex") == default


def test_codex_mini_env_overrides_apply() -> None:
    rates = display_rates(environ={"LARCH_CODEX_MINI_INPUT_RATE_PER_M": "9.0"})
    assert rates.codex_mini_input == 9.0
    # The gpt-5.5 codex rate is unaffected by the mini override.
    assert rates.codex_input == DEFAULT_RATE_TABLE_PER_M[("codex", "gpt-5.5")]["input"]


def test_token_cost_argv_splits_codex_by_model() -> None:
    report = {
        "BUCKETS_codex": {"input": 1_100_000, "cached_input": 2_200_000, "output": 330_000, "total": 3_630_000},
        "BUCKETS_codex_by_model": {
            "gpt-5.5": {"input": 100_000, "cached_input": 200_000, "output": 30_000, "total": 330_000},
            "gpt-5.4-mini": {"input": 1_000_000, "cached_input": 2_000_000, "output": 300_000, "total": 3_300_000},
        },
    }
    record = RunRecord(
        number=0, title="t", url="", started_at="", closed_at="", workflow="design",
        claude=VendorTotals(), codex=VendorTotals(total=3_630_000), cursor=VendorTotals(),
        phase_rows=(), raw_report=report,
    )
    argv = token_cost_argv(record)
    # gpt-5.5 portion routes to --codex-*, mini portion to --codex-mini-*.
    assert argv[argv.index("--codex-input-tokens") + 1] == "100000"
    assert argv[argv.index("--codex-cached-input-tokens") + 1] == "200000"
    assert argv[argv.index("--codex-output-tokens") + 1] == "30000"
    assert argv[argv.index("--codex-mini-input-tokens") + 1] == "1000000"
    assert argv[argv.index("--codex-mini-cached-input-tokens") + 1] == "2000000"
    assert argv[argv.index("--codex-mini-output-tokens") + 1] == "300000"
    # End-to-end: the two model costs sum to CODEX_COST.
    kv = dict(line.split("=", 1) for line in token_cost_from_args(argv[4:]).strip().splitlines())
    assert round(float(kv["CODEX_GPT_5_5_COST"]) + float(kv["CODEX_GPT_5_4_MINI_COST"]), 2) == float(kv["CODEX_COST"])
    assert float(kv["CODEX_GPT_5_4_MINI_COST"]) > 0.0


def test_token_cost_argv_without_by_model_prices_as_default() -> None:
    report = {"BUCKETS_codex": {"input": 100, "cached_input": 200, "output": 30, "total": 330}}
    record = RunRecord(
        number=0, title="t", url="", started_at="", closed_at="", workflow="implement",
        claude=VendorTotals(), codex=VendorTotals(total=330), cursor=VendorTotals(),
        phase_rows=(), raw_report=report,
    )
    argv = token_cost_argv(record)
    assert "--codex-mini-input-tokens" not in argv
    assert argv[argv.index("--codex-input-tokens") + 1] == "100"
