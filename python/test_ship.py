# pyright: reportUnknownLambdaType=false, reportUnknownArgumentType=false
"""Tests for ship.py."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

import config
import run_logs
import ship
from outcomes import Outcome, StepResult
from proc import CommandResult
from run_context import RunContext


def _empty_calls() -> list[list[str]]:
    return []


@dataclass
class RecordingRunner:
    calls: list[list[str]] = field(default_factory=_empty_calls)

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,  # pylint: disable=unused-argument
        cwd: str | None = None,  # pylint: disable=unused-argument
        env: Mapping[str, str] | None = None,  # pylint: disable=unused-argument
        check: bool = False,  # pylint: disable=unused-argument
        stdout: int | None = None,  # pylint: disable=unused-argument
        stderr: int | None = None,  # pylint: disable=unused-argument
    ) -> CommandResult:
        self.calls.append(list(argv))
        return CommandResult(tuple(argv), 0, "", "", 0.01)


def _ctx(tmp_path: Path, **kwargs: object) -> RunContext:
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text(
        json.dumps({"summary_bullets": ["Add driver", "Add finalize"]}),
        encoding="utf-8",
    )
    base = RunContext(
        branch="feat",
        issue="1",
        repo="o/r",
        run_id="run-abc",
        tmpdir=str(tmp_path),
        merge=True,
        draft=False,
        forked=False,
        manifest_path=str(manifest),
        tool_label="codex",
        no_admin_fallback=False,
        repo_unavailable=False,
        pr_title="Implement driver",
        issue_number="1",
    )
    return base.with_(**kwargs)


def test_outcome_exit_map_matches_bash_contract() -> None:
    assert config.OUTCOME_EXIT_MAP == {
        Outcome.OK: 0,
        Outcome.NEEDS_USER_INPUT: 3,
        Outcome.STALLED: 4,
        Outcome.TRANSIENT: 6,
    }


def test_happy_path_stage_order(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    order: list[str] = []
    flush_args: list[tuple[str | None, str | None]] = []

    monkeypatch.setattr(
        ship.checks,
        "run_checks_phase",
        lambda *_a, **_k: order.append("checks") or StepResult(Outcome.OK),
    )
    monkeypatch.setattr(
        ship.finalize,
        "postbump",
        lambda *_a, **_k: order.append("postbump") or type("R", (), {"outcome": Outcome.OK})(),
    )
    monkeypatch.setattr(
        ship.pr_body,
        "compose_pr_body",
        lambda **_k: order.append("pr-body") or "body",
    )
    monkeypatch.setattr(
        ship.oos,
        "disposition_ok",
        lambda *_a, **_k: order.append("oos") or type("D", (), {"ok": True})(),
    )

    def fake_flush(_runner: RecordingRunner, ctx: RunContext, *, cwd: str | None = None) -> run_logs.RefreshSkip:
        order.append("flush-pre")
        flush_args.append((ctx.state_file, cwd))
        return run_logs.RefreshSkip(skipped=False, reason="")

    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", fake_flush)
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: order.append("ensure-pr") or type("P", (), {"number": 5, "url": "u", "status": "created"})(),
    )
    monkeypatch.setattr(
        ship.ci_monitor,
        "monitor",
        lambda *_a, **_k: order.append("monitor") or type(
            "M",
            (),
            {
                "result": StepResult(Outcome.OK),
                "action": "merge",
                "goto_rebase": False,
                "did_fixing": False,
                "failed_run_id": None,
            },
        )(),
    )

    def fake_merge(*_args: object, **kwargs: object) -> object:
        order.append("merge")
        assert kwargs["post_flush"] is False
        return type("MR", (), {"result": config.MERGE_RESULT_MERGED, "error": ""})()

    monkeypatch.setattr(ship.merge, "merge_pr", fake_merge)
    monkeypatch.setattr(
        ship.finalize,
        "postmerge",
        lambda *_a, **_k: order.append("postmerge") or type("PM", (), {"outcome": Outcome.OK, "detail": "", "status": "ok"})(),
    )
    monkeypatch.setattr(
        ship.run_logs,
        "flush_logs_post",
        lambda *_a, **_k: order.append("flush-post") or run_logs.RefreshSkip(skipped=False, reason=""),
    )
    monkeypatch.setattr(ship.run_logs, "load_or_recover_manifest", lambda *_a, **_k: object())
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: order.append("state"))
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")

    result = ship.run_ship(_ctx(tmp_path), runner=RecordingRunner(), cwd=str(tmp_path))
    assert result.outcome is Outcome.OK
    assert order == [
        "checks",
        "postbump",
        "pr-body",
        "oos",
        "flush-pre",
        "ensure-pr",
        "monitor",
        "merge",
        "postmerge",
        "flush-post",
        "state",
    ]
    assert flush_args == [(None, str(tmp_path))]


def test_oos_gate_before_pr_create(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    accepted = tmp_path / "oos-accepted-main-agent.md"
    _ = accepted.write_text("### OOS_1\nbody\n", encoding="utf-8")
    monkeypatch.setattr(ship.checks, "run_checks_phase", lambda *_a, **_k: StepResult(Outcome.OK))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.oos,
        "disposition_ok",
        lambda *_a, **_k: type("D", (), {"ok": False})(),
    )

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("ensure_pr must not run before OOS filing")

    monkeypatch.setattr(ship.pr, "ensure_pr", forbidden)
    result = ship.run_ship(_ctx(tmp_path), runner=RecordingRunner(), cwd=str(tmp_path))
    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == config.NEEDS_USER_OOS_FILING


def test_failed_run_id_surfaces_for_ci_fix_handback() -> None:
    step = StepResult(Outcome.NEEDS_USER_INPUT, "first-fixer-non-health")
    result = ship._step_result_to_ship(step, failed_run_id="123")  # pyright: ignore[reportPrivateUsage]
    assert result.failed_run_id == "123"
    assert result.needs_user_reason == "first-fixer-non-health"


def test_emit_result_prints_json(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    ship.emit_result(ctx, ship.ShipResult(Outcome.OK, pr_number=2, pr_url="u"))
    payload = json.loads(capsys.readouterr().out)
    assert payload["outcome"] == "OK"
    assert payload["pr_number"] == 2
