from __future__ import annotations

# pylint: disable=unused-argument

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from proc import CommandResult
from report_tokens_cost import price_run, token_cost_argv
from report_tokens_models import RunRecord, VendorTotals


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
