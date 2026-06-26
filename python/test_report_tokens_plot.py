from __future__ import annotations

# pylint: disable=unused-argument

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

from larch.core.proc import CommandResult
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
        if self.result.stdout == "__PLOT_DIR__" and len(argv) > 3:
            path = Path(argv[3]) / "x.png"
            _ = path.write_text("png", encoding="utf-8")
            return CommandResult(tuple(argv), 0, json.dumps([str(path)]), "", 0.01)
        return self.result


def _record() -> RunRecord:
    return RunRecord(1, "t", "u", "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z", "", VendorTotals(), VendorTotals(), VendorTotals(), (), {}, total_cost=5)


def test_plot_contract_and_mplconfig(tmp_path: Path) -> None:
    runner = Runner(CommandResult(("python",), 0, "__PLOT_DIR__", "", 0.01))
    paths = plot(runner, skill="implement", records=(_record(),), plot_parent_dir=tmp_path, plugin_root=Path.cwd())
    assert paths
    assert paths[0].name == "x.png"
    input_payload = json.loads(Path(runner.calls[0][2]).read_text(encoding="utf-8"))
    assert input_payload["version"] == 1
    assert input_payload["skill"] == "implement"
    assert [item["label"] for item in input_payload["series"]] == ["All runs"]
    env = runner.envs[0]
    assert env is not None
    assert "MPLCONFIGDIR" in env


def test_plot_design_contract_uses_all_runs_series(tmp_path: Path) -> None:
    runner = Runner(CommandResult(("python",), 0, "__PLOT_DIR__", "", 0.01))
    rec2 = RunRecord(2, "t", "u", "2026-01-02T00:00:00Z", "2026-01-03T00:00:00Z", "", VendorTotals(), VendorTotals(), VendorTotals(), (), {}, total_cost=7)
    paths = plot(runner, skill="design", records=(_record(), rec2), plot_parent_dir=tmp_path, plugin_root=Path.cwd())
    assert paths[0].is_file()
    input_payload = json.loads(Path(runner.calls[0][2]).read_text(encoding="utf-8"))
    assert [item["label"] for item in input_payload["series"]] == ["All runs"]
    assert [len(item["points"]) for item in input_payload["series"]] == [2]


def test_no_plot_returns_empty(tmp_path: Path) -> None:
    runner = Runner(CommandResult(("python",), 0, "[]", "", 0.01))
    assert not plot(runner, skill="design", records=(), plot_parent_dir=tmp_path, no_plot=True)
    assert not runner.calls


def test_no_plot_zero_env_does_not_disable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_REPORT_TOKENS_NO_PLOT", "0")
    runner = Runner(CommandResult(("python",), 0, "__PLOT_DIR__", "", 0.01))
    assert plot(runner, skill="implement", records=(_record(),), plot_parent_dir=tmp_path, plugin_root=Path.cwd())
    assert runner.calls


def test_plot_rejects_child_path_outside_plot_dir(tmp_path: Path) -> None:
    outside = tmp_path / "outside.png"
    _ = outside.write_text("png", encoding="utf-8")
    runner = Runner(CommandResult(("python",), 0, json.dumps([str(outside)]), "", 0.01))
    assert not plot(runner, skill="implement", records=(_record(),), plot_parent_dir=tmp_path, plugin_root=Path.cwd())


def test_plot_child_failure_gracefully_skips(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = Runner(CommandResult(("python",), 2, "", "schema bad", 0.01))
    assert not plot(runner, skill="implement", records=(_record(),), plot_parent_dir=tmp_path, plugin_root=Path.cwd())
    assert "No plots generated (plot child failed: schema bad)." in capsys.readouterr().err
