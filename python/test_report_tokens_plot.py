from __future__ import annotations

# pylint: disable=unused-argument

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from proc import CommandResult
from report_tokens_models import RunRecord, VendorTotals
from report_tokens_plot import plot


def _calls() -> list[list[str]]:
    return []


def _envs() -> list[Mapping[str, str] | None]:
    return []


@dataclass
class Runner:
    result: CommandResult
    calls: list[list[str]] = field(default_factory=_calls)
    envs: list[Mapping[str, str] | None] = field(default_factory=_envs)

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
        self.envs.append(env)
        return self.result


def _record() -> RunRecord:
    return RunRecord(1, "t", "u", "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z", "SIMPLE", VendorTotals(), VendorTotals(), VendorTotals(), (), {}, total_cost=5)


def test_plot_contract_and_mplconfig(tmp_path: Path) -> None:
    png = tmp_path / "x.png"
    _ = png.write_text("png", encoding="utf-8")
    runner = Runner(CommandResult(("python",), 0, json.dumps([str(png)]), "", 0.01))
    paths = plot(runner, skill="implement", records=(_record(),), plot_parent_dir=tmp_path, plugin_root=Path.cwd())
    assert paths == [png]
    env = runner.envs[0]
    assert env is not None
    assert "MPLCONFIGDIR" in env


def test_no_plot_returns_empty(tmp_path: Path) -> None:
    runner = Runner(CommandResult(("python",), 0, "[]", "", 0.01))
    assert plot(runner, skill="design", records=(), plot_parent_dir=tmp_path, no_plot=True) == []
    assert not runner.calls
