# pyright: reportUnknownLambdaType=false, reportUnknownArgumentType=false, reportPrivateUsage=false
"""Tests for ship.py."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

import config
import run_logs
import ship
from errors import PrePushConflictHandoff, ShipError
from outcomes import Outcome, StepResult
from proc import CommandResult
from run_context import RunContext


from test_support import RecordingRunner


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
        Outcome.INTERNAL_ERROR: 1,
        Outcome.NEEDS_USER_INPUT: 3,
        Outcome.STALLED: 4,
        Outcome.TRANSIENT: 6,
    }


def test_happy_path_stage_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
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
        lambda *_a, **_k: order.append("ensure-pr") or type("P", (), {"number": 5, "url": "https://example.test/pr/7", "status": "created"})(),
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
    monkeypatch.setattr(ship.run_logs, "write_final_report_comment", lambda *_a, **_k: order.append("comment"))
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: order.append("state"))
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")

    result = ship.run_ship(_ctx(tmp_path), runner=RecordingRunner(), cwd=str(tmp_path))
    assert result.outcome is Outcome.OK
    assert order == [
        "checks",
        "flush-pre",
        "postbump",
        "pr-body",
        "oos",
        "ensure-pr",
        "comment",
        "monitor",
        "merge",
        "postmerge",
        "state",
        "flush-post",
    ]
    assert order.count("monitor") == 1
    assert order.count("merge") == 1
    assert flush_args == [(None, str(tmp_path))]
    captured = capsys.readouterr()
    assert "ship.py: checks:" in captured.err
    assert "ship.py: pr-prep:" in captured.err
    assert "ship.py: pr-create:" in captured.err
    assert "ship.py: ci:" not in captured.err
    assert "ship.py: merge" in captured.err
    assert "ship.py: post-merge" in captured.err


def test_merge_loop_iteration_cap_stalls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(config, "SHIP_MERGE_LOOP_MAX_ITERATIONS", 2)
    monkeypatch.setattr(ship.checks, "run_checks_phase", lambda *_a, **_k: StepResult(Outcome.OK))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(ship.oos, "disposition_ok", lambda *_a, **_k: type("D", (), {"ok": True})())
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 5, "url": "https://example.test/pr/7", "status": "created"})(),
    )
    monkeypatch.setattr(ship.run_logs, "write_final_report_comment", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(
        ship.ci_monitor,
        "monitor",
        lambda *_a, **_k: type(
            "M",
            (),
            {
                "result": StepResult(Outcome.OK),
                "action": "wait",
                "goto_rebase": False,
                "did_fixing": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
            },
        )(),
    )

    result = ship.run_ship(_ctx(tmp_path), runner=RecordingRunner(), cwd=str(tmp_path))
    assert result.outcome is Outcome.STALLED
    assert result.detail == "merge loop iteration cap reached"


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
    result = ship.run_ship(_ctx(tmp_path, merge=False), runner=RecordingRunner(), cwd=str(tmp_path))
    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == config.NEEDS_USER_OOS_FILING



def test_design_export_oos_allows_pr_create_after_disposition(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    exported = tmp_path / "design-export" / "oos-accepted-design.md"
    exported.parent.mkdir()
    _ = exported.write_text("### OOS_1: exported design OOS\nbody\n", encoding="utf-8")
    monkeypatch.setattr(ship.checks, "run_checks_phase", lambda *_a, **_k: StepResult(Outcome.OK))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(ship.oos, "disposition_ok", lambda *_a, **_k: type("D", (), {"ok": True})())

    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 5, "url": "https://example.test/pr/5", "status": "created"})(),
    )
    monkeypatch.setattr(ship.run_logs, "write_final_report_comment", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    result = ship.run_ship(_ctx(tmp_path, merge=False), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.NEEDS_USER_INPUT


def test_design_tmpdir_oos_allows_pr_create_after_disposition(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    design_tmpdir = tmp_path / "design"
    design_tmpdir.mkdir()
    accepted = design_tmpdir / "oos-accepted-design.md"
    _ = accepted.write_text("### OOS_1: design tmpdir OOS\nbody\n", encoding="utf-8")
    monkeypatch.setenv("DESIGN_TMPDIR", str(design_tmpdir))
    monkeypatch.setattr(ship.checks, "run_checks_phase", lambda *_a, **_k: StepResult(Outcome.OK))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(ship.oos, "disposition_ok", lambda *_a, **_k: type("D", (), {"ok": True})())

    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 5, "url": "https://example.test/pr/5", "status": "created"})(),
    )
    monkeypatch.setattr(ship.run_logs, "write_final_report_comment", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    result = ship.run_ship(_ctx(tmp_path, merge=False), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.NEEDS_USER_INPUT


def test_stale_design_tmpdir_falls_back_to_design_export(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    stale_design = tmp_path / "stale-design"
    exported = tmp_path / "design-export" / "oos-accepted-design.md"
    exported.parent.mkdir()
    _ = exported.write_text("### OOS_1: exported design OOS\nbody\n", encoding="utf-8")
    monkeypatch.setenv("DESIGN_TMPDIR", str(stale_design))

    assert ship.resolve_oos_accepted_design_path(tmp_path) == exported


def test_oos_gate_uses_single_alternate_ndjson_when_run_id_path_missing(tmp_path: Path) -> None:
    accepted = tmp_path / "oos-accepted-main-agent.md"
    _ = accepted.write_text(
        "### OOS_1: Filed elsewhere\n- **Description**: already filed\n",
        encoding="utf-8",
    )
    alternate = tmp_path / "larch-logs" / "implement" / "other-run" / "oos-issues.ndjson"
    alternate.parent.mkdir(parents=True)
    _ = alternate.write_text(
        '{"body":"Created https://github.com/example/larch/issues/99"}\n',
        encoding="utf-8",
    )

    result = ship._oos_gate(RecordingRunner(), _ctx(tmp_path), cwd=str(tmp_path))  # pyright: ignore[reportPrivateUsage]

    assert result is None


def test_oos_gate_requires_ndjson_for_non_security_without_filed_evidence(tmp_path: Path) -> None:
    accepted = tmp_path / "oos-accepted-main-agent.md"
    _ = accepted.write_text(
        "### OOS_1: Needs ndjson\n- **Description**: unresolved\n",
        encoding="utf-8",
    )

    result = ship._oos_gate(RecordingRunner(), _ctx(tmp_path), cwd=str(tmp_path))  # pyright: ignore[reportPrivateUsage]

    assert result is not None
    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == config.NEEDS_USER_OOS_FILING


def test_run_ship_proceeds_when_disposition_satisfied_with_non_empty_accepted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    accepted = tmp_path / "oos-accepted-main-agent.md"
    _ = accepted.write_text(
        "### OOS_1: Filed\n- **Description**: already filed\n",
        encoding="utf-8",
    )
    ndjson = tmp_path / "larch-logs" / "implement" / "run-abc" / "oos-issues.ndjson"
    ndjson.parent.mkdir(parents=True)
    _ = ndjson.write_text(
        '{"body":"Created https://github.com/example/larch/issues/42"}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.checks, "run_checks_phase", lambda *_a, **_k: StepResult(Outcome.OK))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 9, "url": "https://example.test/pr/9", "status": "created"})(),
    )
    monkeypatch.setattr(ship.run_logs, "write_final_report_comment", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")

    ctx = _ctx(tmp_path, merge=False, oos_pending=True)
    result = ship.run_ship(ctx, runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK


def test_oos_gate_allows_inline_triage_without_ndjson(tmp_path: Path) -> None:
    class InlineRunner(RecordingRunner):
        def run(self, argv: Sequence[str], **_kwargs: object) -> CommandResult:  # type: ignore[override]
            self.calls.append(list(argv))
            if argv[:3] == ["git", "log", "--format=%B"]:
                return CommandResult(tuple(argv), 0, "Inline-triage rule 1: folded\n", "", 0.01)
            return CommandResult(tuple(argv), 0, "", "", 0.01)

    accepted = tmp_path / "oos-accepted-main-agent.md"
    _ = accepted.write_text(
        "### OOS_1: Folded\n- **Description**: fixed inline\n",
        encoding="utf-8",
    )
    ndjson = tmp_path / "larch-logs" / "implement" / "run-abc" / "oos-issues.ndjson"
    ndjson.parent.mkdir(parents=True)
    _ = ndjson.write_text("", encoding="utf-8")

    result = ship._oos_gate(InlineRunner(), _ctx(tmp_path), cwd=str(tmp_path))  # pyright: ignore[reportPrivateUsage]

    assert result is None


def test_oos_observation_count_matches_materializer_policy(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    _ = missing.write_text('{"summary_bullets":["x"]}', encoding="utf-8")
    empty = tmp_path / "empty.json"
    _ = empty.write_text('{"oos_observations":[]}', encoding="utf-8")
    invalid_type = tmp_path / "invalid-type.json"
    _ = invalid_type.write_text('{"oos_observations":"bad"}', encoding="utf-8")
    malformed = tmp_path / "malformed.json"
    _ = malformed.write_text("{", encoding="utf-8")

    assert ship.oos_observation_count(missing) == 0
    assert ship.oos_observation_count(empty) == 0
    assert ship.oos_observation_count(invalid_type) is None
    assert ship.oos_observation_count(malformed) is None


def test_manifest_materialize_failure_blocks_pr_create(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class FailingMaterializeRunner(RecordingRunner):
        def run(self, argv: Sequence[str], **_kwargs: object) -> CommandResult:  # type: ignore[override]
            self.calls.append(list(argv))
            if "materialize-manifest-oos.sh" in " ".join(argv):
                return CommandResult(tuple(argv), 1, "", "boom", 0.01)
            return CommandResult(tuple(argv), 0, "", "", 0.01)

    monkeypatch.setattr(ship.checks, "run_checks_phase", lambda *_a, **_k: StepResult(Outcome.OK))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(ship.oos, "disposition_ok", lambda *_a, **_k: type("D", (), {"ok": True})())

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("ensure_pr must not run after materialize failure")

    monkeypatch.setattr(ship.pr, "ensure_pr", forbidden)
    ctx = _ctx(tmp_path)
    _ = Path(ctx.manifest_path).write_text(
        json.dumps({"summary_bullets": ["x"], "oos_observations": [{"title": "OOS", "description": "x"}]}),
        encoding="utf-8",
    )
    runner = FailingMaterializeRunner()
    result = ship.run_ship(ctx, runner=runner, cwd=str(tmp_path))

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == config.NEEDS_USER_OOS_FILING
    assert any("materialize-manifest-oos.sh" in " ".join(call) for call in runner.calls)
    assert "materialize-manifest-oos.sh failed" in (tmp_path / "execution-issues.md").read_text(encoding="utf-8")


def test_manifest_materialize_empty_failure_does_not_block_pr_create(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class FailingMaterializeRunner(RecordingRunner):
        def run(self, argv: Sequence[str], **_kwargs: object) -> CommandResult:  # type: ignore[override]
            self.calls.append(list(argv))
            if "materialize-manifest-oos.sh" in " ".join(argv):
                return CommandResult(tuple(argv), 1, "", "boom", 0.01)
            return CommandResult(tuple(argv), 0, "", "", 0.01)

    monkeypatch.setattr(ship.checks, "run_checks_phase", lambda *_a, **_k: StepResult(Outcome.OK))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(ship.oos, "disposition_ok", lambda *_a, **_k: type("D", (), {"ok": True})())
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 5, "url": "https://example.test/pr/5", "status": "created"})(),
    )
    monkeypatch.setattr(ship.run_logs, "write_final_report_comment", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")

    ctx = _ctx(tmp_path, merge=False)
    _ = Path(ctx.manifest_path).write_text(
        json.dumps({"summary_bullets": ["x"], "oos_observations": []}),
        encoding="utf-8",
    )
    result = ship.run_ship(ctx, runner=FailingMaterializeRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK


def test_security_sidecar_blocks_pr_create(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ship.checks, "run_checks_phase", lambda *_a, **_k: StepResult(Outcome.OK))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("ensure_pr must not run with security sidecar")

    monkeypatch.setattr(ship.pr, "ensure_pr", forbidden)
    sidecar = tmp_path / "security-oos-observations.md"
    _ = sidecar.write_text("### Security OOS: audit\n", encoding="utf-8")

    result = ship.run_ship(_ctx(tmp_path), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == config.NEEDS_USER_OOS_FILING


def test_manifest_materialize_success_blocks_for_step9a1(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class MaterializingRunner(RecordingRunner):
        def run(self, argv: Sequence[str], **_kwargs: object) -> CommandResult:  # type: ignore[override]
            self.calls.append(list(argv))
            if "materialize-manifest-oos.sh" in " ".join(argv):
                _ = (tmp_path / "oos-accepted-main-agent.md").write_text(
                    "### OOS_1: Manifest OOS\n- **Description**: x\n",
                    encoding="utf-8",
                )
            return CommandResult(tuple(argv), 0, "", "", 0.01)

    monkeypatch.setattr(ship.checks, "run_checks_phase", lambda *_a, **_k: StepResult(Outcome.OK))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("ensure_pr must not run with materialized OOS")

    monkeypatch.setattr(ship.pr, "ensure_pr", forbidden)
    ctx = _ctx(tmp_path)
    _ = Path(ctx.manifest_path).write_text(
        json.dumps({"summary_bullets": ["x"], "oos_observations": [{"title": "OOS", "description": "x"}]}),
        encoding="utf-8",
    )
    result = ship.run_ship(ctx, runner=MaterializingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.NEEDS_USER_INPUT

def test_ship_writes_phase_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ship.checks, "run_checks_phase", lambda *_a, **_k: StepResult(Outcome.OK))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(ship.oos, "disposition_ok", lambda *_a, **_k: type("D", (), {"ok": True})())
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 5, "url": "https://example.test/pr/5", "status": "created"})(),
    )
    monkeypatch.setattr(ship.run_logs, "write_final_report_comment", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    state_file = tmp_path / "ship-pr-state.sh"

    result = ship.run_ship(
        _ctx(tmp_path, merge=False, state_file=str(state_file)),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.OK
    state = state_file.read_text(encoding="utf-8")
    assert "PHASE=done\n" in state
    assert "PR_NUMBER=5\n" in state
    assert "REBASE_COUNT=0\n" in state


def test_open_pr_resume_restores_counters_and_validated_branch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        """PHASE=done
BRANCH_NAME=feat
PR_NUMBER=7
PR_URL=https://example.test/pr/7
ITERATION=10
REBASE_COUNT=3
FIX_ATTEMPTS=4
TRANSIENT_RETRIES=1
MERGE=true
DRAFT=false
""",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("fresh-only phase must not run on open-pr resume")

    monkeypatch.setattr(ship.checks, "run_checks_phase", forbidden)
    monkeypatch.setattr(ship.finalize, "postbump", forbidden)
    monkeypatch.setattr(ship, "_materialize_manifest_oos", forbidden)
    monkeypatch.setattr(ship.oos, "disposition_ok", lambda *_a, **_k: type("D", (), {"ok": True})())
    monkeypatch.setattr(ship.run_logs, "write_final_report_comment", forbidden)
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")

    def fake_ensure(_runner: RecordingRunner, ctx: RunContext, *_args: object, **_kwargs: object) -> object:
        seen["ensure_branch"] = ctx.branch_name
        return type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "existing"})()

    def fake_monitor(*_args: object, **kwargs: object) -> object:
        seen["monitor"] = (
            kwargs["iteration"],
            kwargs["rebase_count"],
            kwargs["fix_attempts"],
            kwargs["transient_retries"],
        )
        return type(
            "M",
            (),
            {
                "result": StepResult(Outcome.STALLED, "ci-monitor"),
                "action": "wait",
                "goto_rebase": False,
                "did_fixing": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
            },
        )()

    monkeypatch.setattr(ship.pr, "ensure_pr", fake_ensure)
    monkeypatch.setattr(ship.ci_monitor, "monitor", fake_monitor)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(
        _ctx(tmp_path, branch="stale", branch_name="stale", state_file=str(state_file)),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.STALLED
    assert seen == {"ensure_branch": "feat", "monitor": (10, 3, 4, 1)}
    state = state_file.read_text(encoding="utf-8")
    assert "BRANCH_NAME=feat\n" in state
    assert "ITERATION=10\n" in state
    assert "REBASE_COUNT=3\n" in state
    assert "FIX_ATTEMPTS=4\n" in state
    assert "TRANSIENT_RETRIES=1\n" in state


def test_resume_branch_mismatch_safe_refuses_without_fresh_work(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text("PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\n", encoding="utf-8")
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "other")

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("fresh work must not run after checkout mismatch")

    monkeypatch.setattr(ship.checks, "run_checks_phase", forbidden)
    monkeypatch.setattr(ship.pr, "ensure_pr", forbidden)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == "checkout-mismatch"
    assert "expected feat, current other" in result.detail


def test_forked_target_main_resume_uses_pr_only_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=main\nPR_NUMBER=7\nFORKED_TARGET=true\nMERGE=false\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "main")
    monkeypatch.setattr(ship.gh, "pr_view", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("gh skipped")))
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "existing"})(),
    )
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    state = state_file.read_text(encoding="utf-8")
    assert "BRANCH_NAME=main\n" in state
    assert "FORKED_TARGET=true\n" in state
    assert "MERGE=false\n" in state


def test_merged_resume_writes_done_only_after_postmerge_ok(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=postmerge\nBRANCH_NAME=feat\nPR_NUMBER=7\nMERGE_RESULT=merged\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "MERGED", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(
        ship.finalize,
        "postmerge",
        lambda *_a, **_k: type("PM", (), {"outcome": Outcome.STALLED, "detail": "blocked", "status": "blocked"})(),
    )
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert "PHASE=postmerge\n" in state_file.read_text(encoding="utf-8")


def test_merged_resume_with_merge_disabled_does_not_mark_done(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=postmerge\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=false\nDRAFT=false\nMERGE_RESULT=merged\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "MERGED", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(
        ship.finalize,
        "postmerge",
        lambda *_a, **_k: type("PM", (), {"outcome": Outcome.OK, "detail": "", "status": "skipped"})(),
    )

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    state = state_file.read_text(encoding="utf-8")
    assert "PHASE=postmerge\n" in state
    assert "PHASE=done\n" not in state


def test_open_pr_resume_skips_pending_oos_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nOOS_PENDING=true\nMERGE=false\n"
        "ITERATION=10\nREBASE_COUNT=2\nFIX_ATTEMPTS=3\nTRANSIENT_RETRIES=4\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "existing"})(),
    )
    monkeypatch.setattr(
        ship.oos,
        "disposition_ok",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("OOS gate forbidden on open-pr resume")),
    )

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    state = state_file.read_text(encoding="utf-8")
    assert "ITERATION=10\n" in state
    assert "REBASE_COUNT=2\n" in state
    assert "FIX_ATTEMPTS=3\n" in state
    assert "TRANSIENT_RETRIES=4\n" in state


def test_open_pr_resume_skips_leftover_oos_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nOOS_PENDING=true\nMERGE=false\n"
        "ITERATION=10\nREBASE_COUNT=2\nFIX_ATTEMPTS=3\nTRANSIENT_RETRIES=4\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "accepted-design-oos.md").write_text("### OOS_1: leftover\n", encoding="utf-8")
    _ = (tmp_path / "security-oos-observations.md").write_text("### Security OOS: leftover\n", encoding="utf-8")
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "existing"})(),
    )
    monkeypatch.setattr(
        ship.oos,
        "disposition_ok",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("OOS gate forbidden on open-pr resume")),
    )
    monkeypatch.setattr(ship, "_materialize_manifest_oos", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("manifest OOS forbidden")))

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    state = state_file.read_text(encoding="utf-8")
    assert "OOS_PENDING=true\n" in state
    assert "ITERATION=10\n" in state


def test_blocked_rebase_continuation_sanitizes_untrusted_url(tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        f"PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=bad repo\nPR_URL=javascript:alert(1)\n"
        f"RESUME_PHASE={config.SHIP_PR_RRR_RESUME_PHASE}\n",
        encoding="utf-8",
    )

    result = ship.run_ship(
        _ctx(tmp_path, state_file=str(state_file), pr_url="file:///tmp/not-a-pr"),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == "unsupported-rebase-continuation"
    assert result.pr_url == ""


def test_terminal_monitor_goto_rebase_does_not_increment_rebase_count() -> None:
    monitor = ship.ci_monitor.MonitorResult(
        action="rebase",
        ci_status="failure",
        behind_count=0,
        failed_run_id=None,
        did_fixing=False,
        goto_rebase=True,
        iterations=0,
        result=StepResult(Outcome.STALLED, "terminal"),
        transient_rerun_attempted=False,
    )

    assert ship._monitor_persisted_counters(  # pyright: ignore[reportPrivateUsage]
        iteration=3,
        rebase_count=2,
        fix_attempts=4,
        transient_retries=5,
        monitor=monitor,
    ) == (3, 2, 4, 5)


def test_gh_skipped_resume_uses_done_manifest_as_merged_signal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    manifest = tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    _ = manifest.write_text(json.dumps({"status": config.MANIFEST_STATUS_DONE}), encoding="utf-8")
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nREPO_UNAVAILABLE=true\nMERGE=true\n",
        encoding="utf-8",
    )
    calls: list[str] = []
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.finalize,
        "postmerge",
        lambda *_a, **_k: calls.append("postmerge")
        or type("PM", (), {"outcome": Outcome.OK, "detail": "", "status": "ok"})(),
    )
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert calls == ["postmerge"]


def test_open_pr_resume_wrong_head_routes_through_fresh_checks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=done\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=false\nDRAFT=false\n",
        encoding="utf-8",
    )
    calls: list[str] = []
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "MERGED", "head_ref": "other"})(),
    )
    monkeypatch.setattr(ship.checks, "run_checks_phase", lambda *_a, **_k: calls.append("checks") or StepResult(Outcome.OK))
    monkeypatch.setattr(
        ship.finalize,
        "postbump",
        lambda *_a, **_k: calls.append("postbump") or type("R", (), {"outcome": Outcome.OK})(),
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 8, "url": "https://example.test/pr/8", "status": "created"})(),
    )
    monkeypatch.setattr(ship, "run_postmerge_phase", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("postmerge forbidden")))

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert calls == ["checks", "postbump"]


def test_non_forked_main_resume_refuses(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text("PHASE=ci-initial\nBRANCH_NAME=main\nPR_NUMBER=7\nREPO=o/r\nMERGE=false\n", encoding="utf-8")
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "main")

    result = ship.run_ship(_ctx(tmp_path, branch="main", branch_name="main", state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == "checkout-mismatch"


def test_closed_unmerged_pr_routes_through_fresh_checks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=postmerge\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=false\nDRAFT=false\nMERGE_RESULT=merged\n",
        encoding="utf-8",
    )
    calls: list[str] = []
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "CLOSED", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(ship.checks, "run_checks_phase", lambda *_a, **_k: calls.append("checks") or StepResult(Outcome.OK))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 8, "url": "https://example.test/pr/8", "status": "created"})(),
    )

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert calls == ["checks"]


def test_invalid_pr_identity_routes_through_fresh_checks_without_github(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=not-a-number\nREPO=o/r\nMERGE=false\nDRAFT=false\n",
        encoding="utf-8",
    )
    calls: list[str] = []
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(ship.gh, "pr_view", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("gh forbidden")))
    monkeypatch.setattr(ship.checks, "run_checks_phase", lambda *_a, **_k: calls.append("checks") or StepResult(Outcome.OK))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 8, "url": "https://example.test/pr/8", "status": "created"})(),
    )

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert calls == ["checks"]


def test_stale_merged_flags_with_open_pr_resume_open_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=postmerge\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=true\nDRAFT=false\nMERGE_RESULT=merged\n",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")

    def ensure_existing(*_args: object, **_kwargs: object) -> object:
        seen["ensure"] = True
        return type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "existing"})()

    monkeypatch.setattr(ship.pr, "ensure_pr", ensure_existing)
    monkeypatch.setattr(
        ship.ci_monitor,
        "monitor",
        lambda *_a, **_k: type(
            "M",
            (),
            {
                "result": StepResult(Outcome.STALLED, "ci-monitor"),
                "action": "wait",
                "goto_rebase": False,
                "did_fixing": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
            },
        )(),
    )
    monkeypatch.setattr(ship.run_logs, "write_final_report_comment", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("fresh report forbidden")))
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert seen == {"ensure": True}
    assert "PHASE=stalled\n" in state_file.read_text(encoding="utf-8")


def test_repo_unavailable_blank_pr_open_resume_skips_fresh_work(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text("PHASE=ci-initial\nBRANCH_NAME=feat\nREPO=o/r\nREPO_UNAVAILABLE=true\nMERGE=false\n", encoding="utf-8")
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(ship.checks, "run_checks_phase", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("checks forbidden")))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("postbump forbidden")))
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": None, "url": "", "status": "repo-unavailable"})(),
    )

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert "REPO=o/r\n" in state_file.read_text(encoding="utf-8")


def test_fresh_postmerge_stall_preserves_postmerge_phase(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    monkeypatch.setattr(ship.checks, "run_checks_phase", lambda *_a, **_k: StepResult(Outcome.OK))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(ship.oos, "disposition_ok", lambda *_a, **_k: type("D", (), {"ok": True})())
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "created"})(),
    )
    monkeypatch.setattr(
        ship.ci_monitor,
        "monitor",
        lambda *_a, **_k: type(
            "M",
            (),
            {"result": StepResult(Outcome.OK), "action": "merge", "goto_rebase": False, "did_fixing": False, "transient_rerun_attempted": False, "failed_run_id": None},
        )(),
    )
    monkeypatch.setattr(ship.merge, "merge_pr", lambda *_a, **_k: type("MR", (), {"result": config.MERGE_RESULT_MERGED, "error": ""})())
    monkeypatch.setattr(ship.finalize, "postmerge", lambda *_a, **_k: type("PM", (), {"outcome": Outcome.STALLED, "detail": "blocked", "status": "blocked"})())
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert "PHASE=postmerge\n" in state_file.read_text(encoding="utf-8")


def test_detached_head_resume_refuses(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text("PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=false\n", encoding="utf-8")
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "")

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == "checkout-mismatch"


def test_state_file_must_stay_under_tmpdir(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-state.sh"

    result = ship.run_ship(_ctx(tmp_path, state_file=str(outside)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert result.detail == "invalid state_file"


def test_state_file_cannot_be_tmpdir_itself(tmp_path: Path) -> None:
    result = ship.run_ship(_ctx(tmp_path, state_file=str(tmp_path)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert result.detail == "invalid state_file"


def test_ship_state_rejects_newline_values(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=false\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "", "state": "OPEN", "head_ref": "feat"})(),
    )
    ctx = _ctx(tmp_path, state_file=str(state_file), pr_url="https://example.test/pr/1\nBAD=true")

    result = ship.run_ship(ctx, runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert "invalid newline" in result.detail


def test_resume_rejects_state_repo_mismatch_before_github(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=state/repo\nMERGE=false\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(ship.gh, "pr_view", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("gh forbidden")))

    result = ship.run_ship(
        _ctx(tmp_path, repo="argv/repo", state_file=str(state_file)),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == "checkout-mismatch"
    assert result.detail == "state REPO does not match context repo"


def test_gh_skipped_resume_requires_persisted_branch_anchor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text("PHASE=ci-initial\nREPO_UNAVAILABLE=true\n", encoding="utf-8")
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "surprise")

    result = ship.run_ship(
        _ctx(tmp_path, branch="", branch_name="", state_file=str(state_file)),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == "checkout-mismatch"


def test_terminal_state_uses_canonical_stalled_phase(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(ship.checks, "run_checks_phase", lambda *_a, **_k: StepResult(Outcome.STALLED, "detail with spaces"))
    state_file = tmp_path / "ship-pr-state.sh"

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert "PHASE=stalled\n" in state_file.read_text(encoding="utf-8")


def test_pre_push_conflict_handoff_persists_resume_tokens(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nMERGE=true\nDRAFT=false\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "existing"})(),
    )
    monkeypatch.setattr(
        ship.ci_monitor,
        "monitor",
        lambda *_a, **_k: type(
            "M",
            (),
            {
                "result": StepResult(Outcome.OK),
                "action": "rebase",
                "goto_rebase": True,
                "did_fixing": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
            },
        )(),
    )
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", lambda *_a, **_k: type("S", (), {"skipped": False, "reason": ""})())

    def fake_rebase(*_args: object, **_kwargs: object) -> object:
        raise PrePushConflictHandoff(
            conflict_files=("a.txt",),
            resume_phase=config.SHIP_PR_RRR_RESUME_PHASE,
            caller_kind=config.SHIP_PR_PRE_PUSH_CALLER_KIND,
        )

    monkeypatch.setattr(ship.rebase, "rebase_and_push", fake_rebase)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    state = state_file.read_text(encoding="utf-8")
    assert result.outcome is Outcome.STALLED
    assert f"RESUME_PHASE={config.SHIP_PR_RRR_RESUME_PHASE}\n" in state
    assert f"CALLER_KIND={config.SHIP_PR_PRE_PUSH_CALLER_KIND}\n" in state
    assert "CONFLICT_FILES=a.txt\n" in state


def test_rebase_continuation_wins_over_state_repo_mismatch(tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        f"PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=state/repo\n"
        f"RESUME_PHASE={config.SHIP_PR_RRR_RESUME_PHASE}\n",
        encoding="utf-8",
    )

    result = ship.run_ship(
        _ctx(tmp_path, repo="argv/repo", state_file=str(state_file)),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == "unsupported-rebase-continuation"


def test_resume_rejects_invalid_state_strings_before_rewriting(
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat;bad\nPR_NUMBER=7\nREPO=o/r\nMERGE=false\n",
        encoding="utf-8",
    )

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == "checkout-mismatch"
    assert result.detail == "invalid state BRANCH_NAME"


def test_routine_state_write_preserves_resume_markers(tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        f"RESUME_PHASE={config.SHIP_PR_RRR_RESUME_PHASE}\nCALLER_KIND={config.SHIP_PR_PRE_PUSH_CALLER_KIND}\n",
        encoding="utf-8",
    )

    ship._write_ship_state(_ctx(tmp_path, state_file=str(state_file)), phase="ci-initial")  # pyright: ignore[reportPrivateUsage]

    state = state_file.read_text(encoding="utf-8")
    assert f"RESUME_PHASE={config.SHIP_PR_RRR_RESUME_PHASE}\n" in state
    assert f"CALLER_KIND={config.SHIP_PR_PRE_PUSH_CALLER_KIND}\n" in state


def test_resume_state_write_preserves_persisted_run_id(tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text("RUN_ID=state-run\n", encoding="utf-8")

    ship._write_ship_state(  # pyright: ignore[reportPrivateUsage]
        _ctx(tmp_path, run_id="ctx-run", state_file=str(state_file)),
        phase="ci-initial",
    )

    assert "RUN_ID=state-run\n" in state_file.read_text(encoding="utf-8")


def test_blocked_rebase_second_refusal_preserves_markers_and_counters(tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        f"PHASE=rebase\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\n"
        f"RESUME_PHASE={config.SHIP_PR_RRR_RESUME_PHASE}\nCALLER_KIND={config.SHIP_PR_PRE_PUSH_CALLER_KIND}\n"
        "ITERATION=8\nREBASE_COUNT=2\nFIX_ATTEMPTS=3\nTRANSIENT_RETRIES=4\n",
        encoding="utf-8",
    )

    first = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))
    second = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    state = state_file.read_text(encoding="utf-8")
    assert first.outcome is Outcome.NEEDS_USER_INPUT
    assert second.outcome is Outcome.NEEDS_USER_INPUT
    assert f"RESUME_PHASE={config.SHIP_PR_RRR_RESUME_PHASE}\n" in state
    assert f"CALLER_KIND={config.SHIP_PR_PRE_PUSH_CALLER_KIND}\n" in state
    assert "ITERATION=8\n" in state
    assert "REBASE_COUNT=2\n" in state
    assert "FIX_ATTEMPTS=3\n" in state
    assert "TRANSIENT_RETRIES=4\n" in state


def test_terminal_counter_persistence_counts_failed_fixing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nFIX_ATTEMPTS=4\nMERGE=true\nDRAFT=false\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "existing"})(),
    )
    monkeypatch.setattr(
        ship.ci_monitor,
        "monitor",
        lambda *_a, **_k: type(
            "M",
            (),
            {
                "result": StepResult(Outcome.NEEDS_USER_INPUT, "first-fixer-non-health"),
                "action": "evaluate_failure",
                "goto_rebase": False,
                "did_fixing": True,
                "transient_rerun_attempted": False,
                "failed_run_id": "99",
            },
        )(),
    )
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert "FIX_ATTEMPTS=5\n" in state_file.read_text(encoding="utf-8")


def test_terminal_counter_persistence_counts_failed_transient_rerun(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nTRANSIENT_RETRIES=2\nMERGE=true\nDRAFT=false\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "existing"})(),
    )
    monkeypatch.setattr(
        ship.ci_monitor,
        "monitor",
        lambda *_a, **_k: type(
            "M",
            (),
            {
                "result": StepResult(Outcome.TRANSIENT, "network"),
                "action": "rerun",
                "goto_rebase": False,
                "did_fixing": False,
                "transient_rerun_attempted": True,
                "failed_run_id": None,
            },
        )(),
    )
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.TRANSIENT
    assert "TRANSIENT_RETRIES=3\n" in state_file.read_text(encoding="utf-8")


def test_terminal_counter_round_trip_reuses_persisted_fix_attempts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nFIX_ATTEMPTS=4\nMERGE=true\nDRAFT=false\n",
        encoding="utf-8",
    )
    seen: list[int] = []
    outcomes = [Outcome.NEEDS_USER_INPUT, Outcome.STALLED]
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "existing"})(),
    )

    def monitor(*_args: object, **kwargs: object) -> object:
        fix_attempts = kwargs["fix_attempts"]
        assert isinstance(fix_attempts, int)
        seen.append(fix_attempts)
        outcome = outcomes.pop(0)
        return type(
            "M",
            (),
            {
                "result": StepResult(outcome, "terminal"),
                "action": "evaluate_failure",
                "goto_rebase": False,
                "did_fixing": outcome is Outcome.NEEDS_USER_INPUT,
                "transient_rerun_attempted": False,
                "failed_run_id": "99",
            },
        )()

    monkeypatch.setattr(ship.ci_monitor, "monitor", monitor)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    first = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))
    second = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert first.outcome is Outcome.NEEDS_USER_INPUT
    assert second.outcome is Outcome.STALLED
    assert seen == [4, 5]
    assert "FIX_ATTEMPTS=5\n" in state_file.read_text(encoding="utf-8")


def test_fresh_fallback_hydrates_modes_and_resets_counters(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nMERGE=false\nDRAFT=true\nITERATION=9\nFIX_ATTEMPTS=3\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(ship.gh, "pr_view", lambda *_a, **_k: (_ for _ in ()).throw(ShipError("gh down")))
    monkeypatch.setattr(ship.checks, "run_checks_phase", lambda *_a, **_k: StepResult(Outcome.STALLED, "checks failed"))

    result = ship.run_ship(
        _ctx(tmp_path, merge=True, draft=False, pr_number=99, pr_url="stale-url", state_file=str(state_file)),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    state = state_file.read_text(encoding="utf-8")
    assert result.outcome is Outcome.STALLED
    assert "MERGE=false\n" in state
    assert "DRAFT=true\n" in state
    assert "ITERATION=0\n" in state
    assert "FIX_ATTEMPTS=0\n" in state
    assert "PR_NUMBER=\n" in state
    assert "PR_URL=\n" in state


def test_done_merged_resume_is_idempotent_without_manifest_status(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=done\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=true\nDRAFT=false\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "MERGED", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(ship.finalize, "postmerge", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("postmerge forbidden")))
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert result.detail == "already done"


def test_open_pr_resume_at_iteration_cap_still_observes_monitor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=true\nDRAFT=false\nITERATION=50\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "existing"})(),
    )
    monkeypatch.setattr(
        ship.ci_monitor,
        "monitor",
        lambda *_a, **_k: type(
            "M",
            (),
            {
                "result": StepResult(Outcome.OK),
                "action": "already_merged",
                "goto_rebase": False,
                "did_fixing": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
            },
        )(),
    )
    monkeypatch.setattr(
        ship.merge,
        "merge_pr",
        lambda *_a, **_k: type("MR", (), {"result": config.MERGE_RESULT_DRIVER_ALREADY_MERGED, "error": ""})(),
    )
    monkeypatch.setattr(ship, "run_postmerge_phase", lambda *_a, **_k: ship.ShipResult(Outcome.OK))

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK


def test_open_pr_resume_at_iteration_cap_wait_stalls_after_monitor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=true\nDRAFT=false\nITERATION=50\n",
        encoding="utf-8",
    )
    calls: list[int] = []
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "existing"})(),
    )

    def monitor(*_args: object, **kwargs: object) -> object:
        iteration = kwargs["iteration"]
        assert isinstance(iteration, int)
        calls.append(iteration)
        return type(
            "M",
            (),
            {
                "result": StepResult(Outcome.OK),
                "action": "wait",
                "goto_rebase": False,
                "did_fixing": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
            },
        )()

    monkeypatch.setattr(ship.ci_monitor, "monitor", monitor)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert calls == [50]
    assert "ITERATION=51\n" in state_file.read_text(encoding="utf-8")


def test_fix_only_monitor_result_does_not_consume_iteration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=true\nDRAFT=false\nITERATION=49\n",
        encoding="utf-8",
    )
    actions = ["evaluate_failure", "already_merged"]
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "existing"})(),
    )

    def monitor(*_args: object, **_kwargs: object) -> object:
        action = actions.pop(0)
        return type(
            "M",
            (),
            {
                "result": StepResult(Outcome.OK),
                "action": action,
                "goto_rebase": False,
                "did_fixing": action == "evaluate_failure",
                "transient_rerun_attempted": False,
                "failed_run_id": None,
            },
        )()

    monkeypatch.setattr(ship.ci_monitor, "monitor", monitor)
    monkeypatch.setattr(
        ship.merge,
        "merge_pr",
        lambda *_a, **_k: type("MR", (), {"result": config.MERGE_RESULT_DRIVER_ALREADY_MERGED, "error": ""})(),
    )
    monkeypatch.setattr(ship, "run_postmerge_phase", lambda *_a, **_k: ship.ShipResult(Outcome.OK))

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    state = state_file.read_text(encoding="utf-8")
    assert "ITERATION=49\n" in state
    assert "FIX_ATTEMPTS=1\n" in state


def test_transient_rerun_monitor_result_does_not_consume_iteration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=true\nDRAFT=false\nITERATION=49\n",
        encoding="utf-8",
    )
    actions = ["rerun", "already_merged"]
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "existing"})(),
    )

    def monitor(*_args: object, **_kwargs: object) -> object:
        action = actions.pop(0)
        return type(
            "M",
            (),
            {
                "result": StepResult(Outcome.OK),
                "action": action,
                "goto_rebase": False,
                "did_fixing": False,
                "transient_rerun_attempted": action == "rerun",
                "failed_run_id": None,
            },
        )()

    monkeypatch.setattr(ship.ci_monitor, "monitor", monitor)
    monkeypatch.setattr(
        ship.merge,
        "merge_pr",
        lambda *_a, **_k: type("MR", (), {"result": config.MERGE_RESULT_DRIVER_ALREADY_MERGED, "error": ""})(),
    )
    monkeypatch.setattr(ship, "run_postmerge_phase", lambda *_a, **_k: ship.ShipResult(Outcome.OK))

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    state = state_file.read_text(encoding="utf-8")
    assert "ITERATION=49\n" in state
    assert "TRANSIENT_RETRIES=1\n" in state


def test_merge_retry_results_do_not_consume_iteration_budget(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=true\nDRAFT=false\nITERATION=49\n",
        encoding="utf-8",
    )
    merge_results = [
        config.MERGE_RESULT_CI_NOT_READY,
        config.MERGE_RESULT_DRIVER_ALREADY_MERGED,
    ]
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "existing"})(),
    )
    monkeypatch.setattr(
        ship.ci_monitor,
        "monitor",
        lambda *_a, **_k: type(
            "M",
            (),
            {
                "result": StepResult(Outcome.OK),
                "action": "merge",
                "goto_rebase": False,
                "did_fixing": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
            },
        )(),
    )
    monkeypatch.setattr(
        ship.merge,
        "merge_pr",
        lambda *_a, **_k: type("MR", (), {"result": merge_results.pop(0), "error": ""})(),
    )
    monkeypatch.setattr(ship, "run_postmerge_phase", lambda *_a, **_k: ship.ShipResult(Outcome.OK))

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert "ITERATION=49\n" in state_file.read_text(encoding="utf-8")


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


def test_ship_error_maps_to_stalled_result() -> None:
    result = ship._error_to_result(ShipError("operational failure"))  # pyright: ignore[reportPrivateUsage]
    assert result.outcome is Outcome.STALLED
    assert result.detail == "operational failure"


def test_run_ship_catches_ship_error_as_stalled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def raise_ship_error(*_a: object, **_k: object) -> StepResult:
        raise ShipError("checks failed operationally")

    monkeypatch.setattr(ship.checks, "run_checks_phase", raise_ship_error)
    result = ship.run_ship(_ctx(tmp_path), runner=RecordingRunner(), cwd=str(tmp_path))
    assert result.outcome is Outcome.STALLED
    assert result.detail == "checks failed operationally"


def test_main_emits_json_stdout_and_breadcrumb_stderr(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    def fake_run_ship(*_a: object, **_k: object) -> ship.ShipResult:
        ship._breadcrumb("checks", "Lint&Tests")  # pyright: ignore[reportPrivateUsage]
        return ship.ShipResult(Outcome.STALLED, detail="stalled")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ship, "run_ship", fake_run_ship)
    monkeypatch.setattr(ship.logging_util, "quiet_init", lambda **_: None)
    rc = ship.main(
        [
            "--tmpdir",
            str(tmp_path),
            "--manifest-path",
            str(tmp_path / "manifest.json"),
            "--run-id",
            "run-abc",
        ],
    )
    captured = capsys.readouterr()
    assert rc == 4
    payload = json.loads(captured.out)
    assert payload["outcome"] == "STALLED"
    assert captured.out.count("\n") == 1
    assert "ship.py: checks: Lint&Tests" in captured.err


def test_main_emits_json_stdout_on_unexpected_exception(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    def fake_run_ship(*_a: object, **_k: object) -> ship.ShipResult:
        raise RuntimeError("unexpected failure")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ship, "run_ship", fake_run_ship)
    monkeypatch.setattr(ship.logging_util, "quiet_init", lambda **_: None)
    rc = ship.main(
        [
            "--tmpdir",
            str(tmp_path),
            "--manifest-path",
            str(tmp_path / "manifest.json"),
            "--run-id",
            "run-abc",
        ],
    )
    captured = capsys.readouterr()
    assert rc == config.EXIT_INTERNAL_ERROR
    payload = json.loads(captured.out)
    assert payload["outcome"] == "INTERNAL_ERROR"
    assert payload["detail"] == "RuntimeError: unexpected failure"
    assert captured.out.count("\n") == 1
    assert "internal error" in captured.err
    assert "Traceback" in captured.err
    assert "RuntimeError" in captured.err


def _meets_python_ship_floor(major: int, minor: int) -> bool:
    return (major, minor) >= (3, 11)


def test_python_ship_driver_version_guard_probe() -> None:
    """Pin the /implement Step 8+ and ship.py runtime floor (Python >= 3.11)."""
    assert _meets_python_ship_floor(3, 11)
    assert not _meets_python_ship_floor(3, 10)


def test_python_ship_driver_version_guard_failure_contract(tmp_path: Path) -> None:
    """Runtime probe for the Step 8+ guard JSON/exit contract when python3 is too old."""
    real_python = shutil.which("python3")
    assert real_python is not None
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    stub = stub_dir / "python3"
    _ = stub.write_text(
        f"""#!/usr/bin/env bash
if [ "$1" = "-c" ] && printf '%s\\n' "$2" | grep -Fq 'sys.version_info >= (3, 11)'; then
  exit 1
fi
exec {real_python} "$@"
""",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    script = """
if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
  echo "ERROR: Python ship driver requires Python 3.11 or newer" >&2
  printf '%s\\n' '{"detail":"Python ship driver requires Python 3.11 or newer","failed_run_id":"","merge_result":"","needs_user_reason":"","outcome":"STALLED","pr_number":null,"pr_url":""}'
  exit 4
fi
exit 0
"""
    completed = subprocess.run(
        ["bash", "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PATH": f"{stub_dir}:{os.environ.get('PATH', '')}",
        },
    )
    assert completed.returncode == 4
    assert '"outcome":"STALLED"' in completed.stdout
    assert "Python ship driver requires Python 3.11 or newer" in completed.stderr


def test_version_supported_gate() -> None:
    assert ship._version_supported((3, 11))  # pylint: disable=protected-access
    assert not ship._version_supported((3, 10))  # pylint: disable=protected-access


def test_main_argparse_failure_emits_internal_error(capsys: pytest.CaptureFixture[str]) -> None:
    rc = ship.main(["--unknown-flag"])
    assert rc == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["outcome"] == "INTERNAL_ERROR"
    assert "argparse failed" in payload["detail"]
    assert "usage:" in captured.err


def test_main_argparse_failure_uses_empty_env_ctx(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stale = tmp_path / "stale"
    stale.mkdir()
    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(stale))
    monkeypatch.setenv("RUN_ID", "preparse")
    rc = ship.main(["--unknown-flag"])
    assert rc == config.EXIT_INTERNAL_ERROR
    assert json.loads(capsys.readouterr().out)["outcome"] == "INTERNAL_ERROR"
    assert not list(stale.glob("*.jsonl"))


def test_main_overwrites_implement_tmpdir_after_validation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stale = tmp_path / "stale"
    stale.mkdir()
    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(stale))
    monkeypatch.setattr(ship, "run_ship", lambda *_a, **_k: ship.ShipResult(Outcome.OK))

    def fake_quiet_init(**_kwargs: object) -> None:
        assert os.environ[config.ENV_IMPLEMENT_TMPDIR] == str(tmp_path)

    monkeypatch.setattr(ship.logging_util, "quiet_init", fake_quiet_init)
    rc = ship.main(["--tmpdir", str(tmp_path), "--manifest-path", str(tmp_path / "manifest.json")])
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["outcome"] == "OK"


def test_quiet_init_routes_contract_and_breadcrumb_fds(tmp_path: Path) -> None:
    script = """
import logging_util
import config
import os

os.environ.pop(config.ENV_LARCH_QUIET_DISABLE, None)
os.environ[config.ENV_IMPLEMENT_TMPDIR] = os.environ["QUIET_TMPDIR"]
logging_util.quiet_init(argv0="ship.py")
stream = logging_util.contract_stream()
print("contract", file=stream)
stream.close()
logging_util.BreadcrumbWriter().emit("crumb")
print(os.environ[config.ENV_LARCH_QUIET_LOG_FILE], file=logging_util.contract_stream())
"""
    _quiet_vars = {config.ENV_LARCH_QUIET_ACTIVE, config.ENV_LARCH_QUIET_PID, config.ENV_LARCH_QUIET_LOG_FILE, config.ENV_LARCH_QUIET_DISABLE}
    clean_env = {k: v for k, v in os.environ.items() if k not in _quiet_vars}
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
        env={**clean_env, "PYTHONPATH": str(Path.cwd()), "QUIET_TMPDIR": str(tmp_path)},
    )
    lines = completed.stdout.strip().splitlines()
    assert lines[0] == "contract"
    log_path = Path(lines[1])
    assert log_path.name.startswith("larch-quiet-ship.py-")
    assert log_path.parent == tmp_path
    assert "crumb" in completed.stderr
    assert "crumb" in log_path.read_text(encoding="utf-8")


def test_main_help_has_no_json(capsys: pytest.CaptureFixture[str]) -> None:
    rc = ship.main(["--help"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Run the Python ship-pr driver" in captured.out
    assert '"outcome"' not in captured.out


def test_emit_result_prints_before_journal_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    class FailingJournal:
        def __init__(self, *_args: object) -> None:
            pass

        def append(self, *_args: object, **_kwargs: object) -> object:
            raise OSError("journal blocked")

    monkeypatch.setattr(ship.logging_util, "JsonlJournal", FailingJournal)
    ctx = _ctx(tmp_path)
    ship.emit_result(ctx, ship.ShipResult(Outcome.OK, pr_number=1, pr_url="u"))
    captured = capsys.readouterr()
    assert json.loads(captured.out)["outcome"] == "OK"
    assert "journal append skipped" in captured.err


def test_emit_result_skips_journal_on_invalid_tmpdir(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ctx = _ctx(tmp_path, tmpdir="/not/allowed/larch")
    ship.emit_result(ctx, ship.ShipResult(Outcome.STALLED, detail="invalid tmpdir"))
    assert json.loads(capsys.readouterr().out)["outcome"] == "STALLED"
    assert not Path("/not/allowed/larch").exists()


def test_persist_stall_metadata_gap_fill_preserves_custom_key(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, pr_number=2, pr_url="u")
    target = tmp_path / "finalize-state.sh"
    finalize_data = {"CUSTOM_PIN": "keep", "PR_NUMBER": "7"}
    ship.finalize.write_finalize_state_merged(target, finalize_data)
    ship._persist_stall_metadata_if_needed(ctx, ship.ShipResult(Outcome.STALLED, detail="merge failed"), tmp_path)  # pylint: disable=protected-access
    data = ship.finalize.read_finalize_state(target)
    assert data["CUSTOM_PIN"] == "keep"
    assert data["PR_NUMBER"] == "7"
    assert data["STALL_TRACKING"] == "true"


def test_persist_stall_metadata_uses_state_file_before_ctx(tmp_path: Path) -> None:
    state = tmp_path / "ship-pr-state.sh"
    _ = state.write_text("PR_NUMBER=44\nPR_URL=https://example.invalid/pr/44\n", encoding="utf-8")
    ctx = _ctx(tmp_path, pr_number=None, pr_url="", state_file=str(state))
    ship._persist_stall_metadata_if_needed(ctx, ship.ShipResult(Outcome.STALLED, detail="rebase stalled"), tmp_path)  # pylint: disable=protected-access
    data = ship.finalize.read_finalize_state(tmp_path / "finalize-state.sh")
    assert data["PR_NUMBER"] == "44"
    assert data["PR_URL"] == "https://example.invalid/pr/44"
    assert data["STALL_TRACKING"] == "true"


def test_persist_stall_metadata_treats_zero_pr_number_as_absent(tmp_path: Path) -> None:
    state = tmp_path / "ship-pr-state.sh"
    _ = state.write_text("PR_NUMBER=44\n", encoding="utf-8")
    ctx = _ctx(tmp_path, pr_number=0, state_file=str(state))
    result = ship.ShipResult(Outcome.STALLED, pr_number=0, detail="rebase stalled")
    ship._persist_stall_metadata_if_needed(ctx, result, tmp_path)  # pylint: disable=protected-access
    data = ship.finalize.read_finalize_state(tmp_path / "finalize-state.sh")
    assert data["PR_NUMBER"] == "44"


def test_persist_stall_metadata_preserves_existing_tracking(tmp_path: Path) -> None:
    target = tmp_path / "finalize-state.sh"
    ship.finalize.write_finalize_state_merged(target, {"STALL_TRACKING": "true", "STALL_STEP": "existing"})
    ctx = _ctx(tmp_path, stall_step="new")
    ship._persist_stall_metadata_if_needed(ctx, ship.ShipResult(Outcome.STALLED, detail="new"), tmp_path)  # pylint: disable=protected-access
    data = ship.finalize.read_finalize_state(target)
    assert data == {"STALL_TRACKING": "true", "STALL_STEP": "existing"}


def test_main_stalled_json_survives_stall_metadata_write_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(ship.logging_util, "quiet_init", lambda **_: None)
    monkeypatch.setattr(ship, "run_ship", lambda *_a, **_k: ship.ShipResult(Outcome.STALLED, detail="ensure-pr"))

    def fail_write(*_args: object, **_kwargs: object) -> None:
        raise ShipError("blocked")

    monkeypatch.setattr(ship.finalize, "write_finalize_state_merged", fail_write)
    rc = ship.main(["--tmpdir", str(tmp_path), "--manifest-path", str(tmp_path / "manifest.json")])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert rc == config.OUTCOME_EXIT_MAP[Outcome.STALLED]
    assert payload["outcome"] == "STALLED"
    assert payload["detail"] == "ensure-pr"


def test_main_ensure_pr_stall_creates_finalize_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ship.logging_util, "quiet_init", lambda **_: None)
    monkeypatch.setattr(ship.checks, "run_checks_phase", lambda *_a, **_k: StepResult(Outcome.OK))
    monkeypatch.setattr(ship.finalize, "postbump_preflight", lambda *_a, **_k: ship.finalize.PostbumpPreflight(ok=True))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(ship.oos, "disposition_ok", lambda *_a, **_k: type("D", (), {"ok": True})())
    monkeypatch.setattr(ship.pr, "ensure_pr", lambda *_a, **_k: (_ for _ in ()).throw(ShipError("ensure-pr failed")))
    rc = ship.main(["--tmpdir", str(tmp_path), "--manifest-path", str(tmp_path / "manifest.json"), "--repo", "o/r"])
    assert rc == config.OUTCOME_EXIT_MAP[Outcome.STALLED]
    assert json.loads(capsys.readouterr().out)["outcome"] == "STALLED"
    data = ship.finalize.read_finalize_state(tmp_path / "finalize-state.sh")
    assert data["STALL_TRACKING"] == "true"
    assert data["STALL_STEP"] == "ensure-pr-failed"


def test_postmerge_flush_skip_stall_preserves_preseeded_pr_number(
    tmp_path: Path,
) -> None:
    target = tmp_path / "finalize-state.sh"
    ship.finalize.write_finalize_state_merged(target, {"PR_NUMBER": "88"})
    result = ship.ShipResult(Outcome.STALLED, pr_number=7, detail="post-merge flush skipped: blocked")
    ship._persist_stall_metadata_if_needed(_ctx(tmp_path, pr_number=7), result, tmp_path)  # pylint: disable=protected-access
    data = ship.finalize.read_finalize_state(target)
    assert data["PR_NUMBER"] == "88"
    assert data["STALL_TRACKING"] == "true"


def test_persist_stall_metadata_invalid_tmpdir_is_json_only(tmp_path: Path) -> None:
    invalid = Path("/not/allowed/larch")
    ctx = _ctx(tmp_path, tmpdir=str(invalid))
    ship._persist_stall_metadata_if_needed(ctx, ship.ShipResult(Outcome.STALLED, detail="invalid tmpdir"), invalid)  # pylint: disable=protected-access
    assert not (invalid / "finalize-state.sh").exists()
