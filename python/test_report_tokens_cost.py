from __future__ import annotations

# pylint: disable=unused-argument

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from proc import CommandResult
from report_tokens_cost import (
    CODEX_CURSOR_BLENDED_FLEET_MIX,
    DEFAULT_VENDOR_MODEL,
    display_rates,
    env_rate,
    price_run,
    render_cost_line_main,
    token_cost_argv,
    token_cost_main,
)
from report_tokens_models import RunRecord, VendorTotals

if TYPE_CHECKING:
    import pytest


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
    assert priced.claude_sub_cost == 5.00
    assert priced.total_cost == 5.00


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
    rc = token_cost_main(["--codex-input-tokens", "1000000", "--codex-output-tokens", "1000000"])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = dict(line.split("=", 1) for line in out.strip().splitlines() if "=" in line)
    assert parsed["CLAUDE_COST"] == "0.00"
    assert parsed["CODEX_COST"] == "35.00"
    assert parsed["TOTAL_COST"] == "35.00"
    assert parsed["TOTAL_TOKENS"] == "2000000"
    assert out.strip().splitlines()[0].startswith("CLAUDE_COST=")
    assert out.strip().splitlines()[4].startswith("TOTAL_COST=")


def test_render_cost_line_cli_emits_terminal_grammar(capsys: pytest.CaptureFixture[str]) -> None:
    rc = render_cost_line_main(["--codex-input-tokens", "1000", "--codex-output-tokens", "500"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("💰 Cost: TOTAL ~$")
    assert "Codex $" in out
    assert "Tokens:" in out


def test_display_rates_shipped_defaults_snapshot() -> None:
    assert DEFAULT_VENDOR_MODEL == {
        "codex": "gpt-5.5",
        "cursor": "composer-2.5",
        "claude": "claude-opus-4-8",
    }
    rates = display_rates(environ={})
    assert rates.codex_input == 5.00
    assert rates.codex_cached_input == 0.50
    assert rates.codex_output == 30.00
    assert rates.cursor_input == 0.50
    assert rates.cursor_cache_read == 0.20
    assert rates.cursor_output == 2.50
    assert rates.claude_input == 5.00
    assert rates.claude_cache_read == 0.50
    assert rates.claude_cache_create_5m == 6.25
    assert rates.claude_cache_create_1h == 10.00
    assert rates.claude_output == 25.00
    assert rates.claude_blended == 0.80
    assert rates.codex_blended == 1.11
    assert abs(rates.cursor_blended - 0.244) < 0.000001


def test_env_rate_alias_precedence() -> None:
    env = {"OLD": "1.5", "NEW": "2.5"}
    assert env_rate(("NEW", "OLD"), 0.1, environ=env) == 2.5
    assert env_rate(("BAD", "OLD"), 0.1, environ={"BAD": "no", "OLD": "3"}) == 3.0
    assert env_rate(("BAD", "ZERO", "NEG", "OLD"), 0.1, environ={"BAD": "no", "ZERO": "0", "NEG": "-1", "OLD": "4"}) == 4.0


def test_codex_and_cursor_blended_defaults_derive_from_fleet_mix() -> None:
    rates = display_rates(environ={})
    assert CODEX_CURSOR_BLENDED_FLEET_MIX == {"input": 0.07, "cache_read": 0.92, "output": 0.01}
    assert rates.codex_blended == (5.00 * 0.07) + (0.50 * 0.92) + (30.00 * 0.01)
    assert rates.cursor_blended == (0.50 * 0.07) + (0.20 * 0.92) + (2.50 * 0.01)


def test_4b3c1a5a_repricing_regression(capsys: pytest.CaptureFixture[str]) -> None:
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
    assert abs(float(parsed["CODEX_COST"]) - 75.70) < 0.01
    assert abs(float(parsed["CURSOR_COST"]) - 22.88) < 0.01


def test_default_vendor_models_match_agent_model_args(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("LARCH_CODEX_MODEL", "CLAUDE_PLUGIN_OPTION_CODEX_MODEL", "LARCH_CURSOR_MODEL", "CLAUDE_PLUGIN_OPTION_CURSOR_MODEL"):
        monkeypatch.delenv(key, raising=False)

    def resolved(tool: str, flag: str) -> str:
        result = subprocess.run(
            [str(Path(__file__).resolve().parents[1] / "scripts" / "agent-model-args.sh"), "--tool", tool],
            capture_output=True,
            text=True,
            check=True,
        )
        args = result.stdout.splitlines()
        return args[args.index(flag) + 1]

    assert resolved("codex", "-m") == DEFAULT_VENDOR_MODEL["codex"]
    assert resolved("cursor", "--model") == DEFAULT_VENDOR_MODEL["cursor"]
