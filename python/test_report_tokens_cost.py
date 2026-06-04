from __future__ import annotations

# pylint: disable=unused-argument

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from proc import CommandResult
from report_tokens_cost import price_run, token_cost_argv
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
        workflow="HARD",
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
        workflow="HARD",
        claude=VendorTotals(total=123),
        codex=VendorTotals(total=0),
        cursor=VendorTotals(total=0),
        phase_rows=(),
        raw_report={"BUCKETS_claude": {"input": 0, "malformed": "x"}},
    )
    argv = token_cost_argv(record, plugin_root=Path("/repo"))
    assert "--claude-tokens" in argv
    assert "--claude-input-tokens" not in argv


def test_kv_parse_into_cost_fields() -> None:
    runner = Runner(CommandResult(("token-cost",), 0, "CLAUDE_COST=1.00\nCODEX_COST=2.00\nCURSOR_COST=3.00\nTOTAL_COST=6.00\n", "", 0.01))
    priced = price_run(runner, record=_record(), plugin_root=Path.cwd().parent)
    assert priced.total_cost == 6.0
    assert priced.priced_by_token_cost is True


def test_real_token_cost_override() -> None:
    old = os.environ.get("LARCH_CLAUDE_RATE_PER_M")
    os.environ["LARCH_CLAUDE_RATE_PER_M"] = "10"
    try:
        runner = Runner(CommandResult(("unused",), 0, "CLAUDE_COST=0.01\nCODEX_COST=0.00\nCURSOR_COST=0.00\nTOTAL_COST=0.01\n", "", 0.01))
        priced = price_run(runner, record=_record(), plugin_root=Path.cwd().parent)
        assert priced.claude_cost == 0.01
    finally:
        if old is None:
            _ = os.environ.pop("LARCH_CLAUDE_RATE_PER_M", None)
        else:
            os.environ["LARCH_CLAUDE_RATE_PER_M"] = old


def test_claude_blended_argv_uses_component_sum() -> None:
    record = RunRecord(
        number=1,
        title="t",
        url="u",
        started_at="2026-01-01T00:00:00Z",
        closed_at="2026-01-01T00:00:00Z",
        workflow="HARD",
        claude=VendorTotals(input=10, cache_read=20, cache_create=5, cache_create_5m=30, cache_create_1h=40, output=50, total=999),
        codex=VendorTotals(input=1, cached_input=2, output=3, total=999),
        cursor=VendorTotals(input=4, cache_read=5, output=6, total=999),
        phase_rows=(),
        raw_report={},
    )
    argv = token_cost_argv(record, plugin_root=Path("/repo"))
    assert argv[argv.index("--claude-tokens") + 1] == "155"
    assert argv[argv.index("--codex-tokens") + 1] == "6"
    assert argv[argv.index("--cursor-tokens") + 1] == "15"


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
        workflow="HARD",
        claude=VendorTotals(),
        codex=VendorTotals(),
        cursor=VendorTotals(),
        phase_rows=(),
        raw_report={"BUCKETS_claude": {"input": 1_000_000}},
    )
    priced = price_run(SubprocessRunner(), record=record, plugin_root=Path.cwd().parent)
    assert priced.claude_cost == 10.0


def test_token_cost_failure_warns_and_uses_fallback(capsys: pytest.CaptureFixture[str]) -> None:
    runner = Runner(CommandResult(("token-cost",), 1, "", "bad", 0.01))
    priced = price_run(runner, record=_record(), plugin_root=Path.cwd().parent)
    captured = capsys.readouterr()
    assert "token-cost.sh failed" in captured.err
    assert priced.priced_by_token_cost is False


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
        workflow="HARD",
        claude=VendorTotals(),
        codex=VendorTotals(input=1_000_000, output=1_000_000, total=0),
        cursor=VendorTotals(input=1_000_000, cache_read=1_000_000, output=1_000_000, total=0),
        phase_rows=(),
        raw_report={},
    )
    priced = price_run(runner, record=record, plugin_root=Path.cwd().parent)
    assert priced.codex_cost == 2.0
    assert priced.cursor_cost == 3.0
