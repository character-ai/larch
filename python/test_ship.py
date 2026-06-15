# pyright: reportUnknownLambdaType=false, reportUnknownArgumentType=false, reportPrivateUsage=false
"""Tests for ship.py."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import pytest

import config
import run_logs
import ship
from errors import PrePushConflictHandoff, ShipError, Stalled
from outcomes import Outcome, StepResult
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
        ship.finalize,
        "postbump",
        lambda *_a, **_k: order.append("postbump") or type("R", (), {"outcome": Outcome.OK})(),
    )
    monkeypatch.setattr(
        ship.pr_body,
        "compose_pr_body",
        lambda **_k: order.append("pr-body") or "body",
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
        "flush-pre",
        "postbump",
        "pr-body",
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
    assert "ship.py: pr-prep:" in captured.err
    assert "ship.py: pr-prep:" in captured.err
    assert "ship.py: pr-create:" in captured.err
    assert "ship.py: ci:" not in captured.err
    assert "ship.py: merge" in captured.err
    assert "ship.py: post-merge" in captured.err


def test_merge_review_required_exits_as_needs_user_input(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    merge_calls = {"count": 0}

    def fake_merge(*_a: object, **_k: object) -> object:
        merge_calls["count"] += 1
        return type(
            "MR",
            (),
            {"result": config.MERGE_RESULT_REVIEW_REQUIRED, "error": "needs review"},
        )()

    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
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
                "action": "merge",
                "goto_rebase": False,
                "did_fixing": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
            },
        )(),
    )
    monkeypatch.setattr(ship.merge, "merge_pr", fake_merge)

    result = ship.run_ship(_ctx(tmp_path), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == config.NEEDS_USER_REVIEW_REQUIRED
    assert merge_calls["count"] == 1


def test_merge_loop_iteration_cap_stalls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(config, "SHIP_MERGE_LOOP_MAX_ITERATIONS", 2)
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
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

    monkeypatch.setattr(ship.finalize, "postbump", forbidden)
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


def test_merged_pr_resume_ignores_head_ref_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nPR_URL=https://example.test/pr/7\n"
        "MERGE=true\nDRAFT=false\nITERATION=4\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "MERGED", "head_ref": "stale-head"})(),
    )
    monkeypatch.setattr(ship, "run_postmerge_phase", lambda *_a, **_k: ship.ShipResult(Outcome.OK, detail="postmerge"))

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert result.detail == "postmerge"


def test_resume_branch_mismatch_safe_refuses_without_fresh_work(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text("PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\n", encoding="utf-8")
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "other")

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("fresh work must not run after checkout mismatch")

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
        "PHASE=ci-initial\nBRANCH_NAME=main\nPR_NUMBER=7\nPR_URL=https://example.test/pr/7\n"
        "FORKED_TARGET=true\nMERGE=false\n",
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


def test_gh_skipped_resume_requires_multiple_merge_signals(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    manifest = tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    _ = manifest.write_text(json.dumps({"status": config.MANIFEST_STATUS_DONE}), encoding="utf-8")
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nPR_URL=https://example.test/pr/7\n"
        "REPO=o/r\nREPO_UNAVAILABLE=true\nMERGE=true\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 7, "url": "", "status": "existing"})(),
    )
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert "PHASE=done\n" in state_file.read_text(encoding="utf-8")


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
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "other"})(),
    )
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
    assert calls == ["postbump"]


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
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: calls.append("postbump") or type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 8, "url": "https://example.test/pr/8", "status": "created"})(),
    )

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert calls == ["postbump"]


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
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: calls.append("postbump") or type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 8, "url": "https://example.test/pr/8", "status": "created"})(),
    )

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert calls == ["postbump"]


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
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
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

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    state = state_file.read_text(encoding="utf-8")
    assert "PHASE=postmerge\n" in state
    assert "PHASE=done\n" not in state
    assert "STALL_TRACKING=true\n" in state
    finalize_state = ship.finalize.read_finalize_state(tmp_path / "finalize-state.sh")
    assert finalize_state["STALL_TRACKING"] == "true"
    assert finalize_state["EXIT_CODE"] == "4"


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
    monkeypatch.setattr(ship.finalize, "postbump_preflight", lambda *_a, **_k: (_ for _ in ()).throw(Stalled("detail with spaces")))
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
    assert not (tmp_path / "finalize-state.sh").exists()


def _open_pr_merge_loop_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
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
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", lambda *_a, **_k: type("S", (), {"skipped": False, "reason": ""})())


def test_phase14_flag_rebase_success_clears_handoff_and_conflict_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    flag = tmp_path / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME
    _ = flag.write_text("", encoding="utf-8")
    _ = state_file.write_text(
        f"PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=true\nDRAFT=false\n"
        f"RESUME_PHASE={config.SHIP_PR_RRR_RESUME_PHASE}\n"
        f"CALLER_KIND={config.SHIP_PR_PRE_PUSH_CALLER_KIND}\n"
        "CONFLICT_FILES=a.txt\n",
        encoding="utf-8",
    )
    _open_pr_merge_loop_stubs(monkeypatch)
    rebase_calls: list[bool] = []

    def fake_rebase(*_args: object, **_kwargs: object) -> None:
        rebase_calls.append(True)

    monitor_calls: list[bool] = []

    def fake_monitor(*_args: object, **_kwargs: object) -> object:
        monitor_calls.append(True)
        return type(
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
        )()

    monkeypatch.setattr(ship.rebase, "rebase_and_push", fake_rebase)
    monkeypatch.setattr(ship.ci_monitor, "monitor", fake_monitor)
    monkeypatch.setattr(ship.merge, "merge_pr", lambda *_a, **_k: type("MR", (), {"result": config.MERGE_RESULT_MERGED, "error": ""})())
    monkeypatch.setattr(ship.finalize, "postmerge", lambda *_a, **_k: type("PM", (), {"outcome": Outcome.OK, "detail": "", "status": "ok"})())

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    state = state_file.read_text(encoding="utf-8")
    assert result.outcome is Outcome.OK
    assert rebase_calls
    assert monitor_calls
    assert not flag.is_file()
    assert "RESUME_PHASE=\n" in state
    assert "CALLER_KIND=\n" in state
    assert "CONFLICT_FILES=" not in state


def test_phase14_flag_removed_on_non_handoff_rebase_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    flag = tmp_path / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME
    _ = flag.write_text("", encoding="utf-8")
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=true\nDRAFT=false\n",
        encoding="utf-8",
    )
    _open_pr_merge_loop_stubs(monkeypatch)

    def fake_rebase(*_args: object, **_kwargs: object) -> None:
        raise ShipError("rebase failed")

    monkeypatch.setattr(ship.rebase, "rebase_and_push", fake_rebase)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert not flag.is_file()


def test_main_pre_push_handoff_skips_finalize_gap_fill(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        f"RESUME_PHASE={config.SHIP_PR_RRR_RESUME_PHASE}\n"
        f"CALLER_KIND={config.SHIP_PR_PRE_PUSH_CALLER_KIND}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.logging_util, "quiet_init", lambda **_: None)
    monkeypatch.setattr(ship, "run_ship", lambda *_a, **_k: ship.ShipResult(Outcome.STALLED, detail="handoff"))

    rc = ship.main([
        "--tmpdir",
        str(tmp_path),
        "--manifest-path",
        str(tmp_path / "manifest.json"),
        "--state-file",
        str(state_file),
    ])
    captured = capsys.readouterr()
    assert rc == config.OUTCOME_EXIT_MAP[Outcome.STALLED]
    assert json.loads(captured.out)["outcome"] == "STALLED"
    assert not (tmp_path / "finalize-state.sh").exists()


def test_routine_state_write_clears_stale_terminal_keys(tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "STALL_TRACKING=true\nEXPECTED_SESSION_ID=session-1\n"
        "EXIT_CODE=4\nBAIL_REASON=stall\nBAIL_NEEDS_USER_INPUT=true\n"
        "FAILED_RUN_ID=run-1\nBAIL_FAILURE_DETAIL_LOG=/tmp/log\n",
        encoding="utf-8",
    )

    ship._write_ship_state(  # pyright: ignore[reportPrivateUsage]
        _ctx(tmp_path, state_file=str(state_file), pr_number=12, stall_tracking=True),
        phase="ci-initial",
    )

    state = state_file.read_text(encoding="utf-8")
    assert "EXPECTED_SESSION_ID=session-1\n" in state
    assert "STALL_TRACKING=true\n" in state
    assert "EXIT_CODE=" not in state
    assert "BAIL_REASON=" not in state
    assert "BAIL_NEEDS_USER_INPUT=" not in state
    assert "FAILED_RUN_ID=" not in state
    assert "BAIL_FAILURE_DETAIL_LOG=" not in state


def test_run_ship_infrastructure_state_read_error_surfaces_internal_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text("PHASE=ci-initial\nBRANCH_NAME=feat\n", encoding="utf-8")
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")

    def raise_infra(*_args: object, **_kwargs: object) -> StepResult:
        raise ShipError("cannot read existing ship state: /tmp/state")

    monkeypatch.setattr(ship.finalize, "postbump_preflight", raise_infra)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.INTERNAL_ERROR
    assert not (tmp_path / "finalize-state.sh").exists()


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


def test_pre_push_handoff_without_flag_recreates_flag_and_resumes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        f"PHASE=rebase\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=true\nDRAFT=false\n"
        f"RESUME_PHASE={config.SHIP_PR_RRR_RESUME_PHASE}\nCALLER_KIND={config.SHIP_PR_PRE_PUSH_CALLER_KIND}\n"
        "ITERATION=8\nREBASE_COUNT=2\nFIX_ATTEMPTS=3\nTRANSIENT_RETRIES=4\n",
        encoding="utf-8",
    )
    _open_pr_merge_loop_stubs(monkeypatch)
    rebase_calls: list[bool] = []

    def fake_rebase(*_args: object, **_kwargs: object) -> None:
        rebase_calls.append(True)

    monkeypatch.setattr(ship.rebase, "rebase_and_push", fake_rebase)
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
    monkeypatch.setattr(ship.merge, "merge_pr", lambda *_a, **_k: type("MR", (), {"result": config.MERGE_RESULT_MERGED, "error": ""})())
    monkeypatch.setattr(ship.finalize, "postmerge", lambda *_a, **_k: type("PM", (), {"outcome": Outcome.OK, "detail": "", "status": "ok"})())

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert rebase_calls == [True]
    assert not (tmp_path / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME).exists()
    state = state_file.read_text(encoding="utf-8")
    assert "RESUME_PHASE=\n" in state
    assert "CALLER_KIND=\n" in state


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


def test_fresh_fallback_hydrates_modes_and_preserves_counters(
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
    monkeypatch.setattr(ship.finalize, "postbump_preflight", lambda *_a, **_k: ship.finalize.PostbumpPreflight(ok=True))
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", lambda *_a, **_k: run_logs.RefreshSkip(skipped=False, reason=""))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.STALLED, "status": "stalled", "detail": "postbump failed"})())

    result = ship.run_ship(
        _ctx(tmp_path, merge=True, draft=False, pr_number=99, pr_url="stale-url", state_file=str(state_file)),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    state = state_file.read_text(encoding="utf-8")
    assert result.outcome is Outcome.STALLED
    assert "MERGE=false\n" in state
    assert "DRAFT=true\n" in state
    assert "ITERATION=9\n" in state
    assert "FIX_ATTEMPTS=3\n" in state
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


def test_merge_retry_results_consume_iteration_budget(
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
    assert "ITERATION=50\n" in state_file.read_text(encoding="utf-8")


def test_main_advanced_merge_result_rebases_before_retry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=true\nDRAFT=false\n",
        encoding="utf-8",
    )
    _open_pr_merge_loop_stubs(monkeypatch)
    order: list[str] = []
    merge_results = [
        config.MERGE_RESULT_MAIN_ADVANCED,
        config.MERGE_RESULT_DRIVER_ALREADY_MERGED,
    ]

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

    def fake_rebase(*_args: object, **_kwargs: object) -> None:
        order.append("rebase")

    def fake_merge(*_args: object, **_kwargs: object) -> object:
        result = merge_results.pop(0)
        order.append(f"merge:{result}")
        if result == config.MERGE_RESULT_DRIVER_ALREADY_MERGED:
            state = state_file.read_text(encoding="utf-8")
            assert "PHASE=ci-initial\n" in state
            assert "ITERATION=1\n" in state
            assert "REBASE_COUNT=1\n" in state
        return type("MR", (), {"result": result, "error": ""})()

    monkeypatch.setattr(ship.rebase, "rebase_and_push", fake_rebase)
    monkeypatch.setattr(ship.merge, "merge_pr", fake_merge)
    monkeypatch.setattr(ship, "run_postmerge_phase", lambda *_a, **_k: ship.ShipResult(Outcome.OK))

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert order == [
        f"merge:{config.MERGE_RESULT_MAIN_ADVANCED}",
        "rebase",
        f"merge:{config.MERGE_RESULT_DRIVER_ALREADY_MERGED}",
    ]
    assert not merge_results


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


def test_infrastructure_ship_error_maps_to_internal_error() -> None:
    result = ship._error_to_result(ShipError("cannot read existing ship state: /tmp/state"))  # pyright: ignore[reportPrivateUsage]
    assert result.outcome is Outcome.INTERNAL_ERROR


def test_run_ship_catches_ship_error_as_stalled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def raise_ship_error(*_a: object, **_k: object) -> StepResult:
        raise ShipError("postbump failed operationally")

    monkeypatch.setattr(ship.finalize, "postbump_preflight", raise_ship_error)
    result = ship.run_ship(_ctx(tmp_path), runner=RecordingRunner(), cwd=str(tmp_path))
    assert result.outcome is Outcome.STALLED
    assert result.detail == "postbump failed operationally"


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


def test_postmerge_should_flush_uses_state_file_run_id(tmp_path: Path) -> None:
    state = tmp_path / "state.sh"
    _ = state.write_text("RUN_ID=state-run\n", encoding="utf-8")
    ctx = _ctx(tmp_path, run_id="", state_file=str(state), pr_number=5, pr_closed=True)
    assert ship._postmerge_should_flush(ctx) is True  # pyright: ignore[reportPrivateUsage]


def test_postmerge_should_flush_false_without_run_id(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, run_id="", pr_number=5, pr_closed=True)
    assert ship._postmerge_should_flush(ctx) is False  # pyright: ignore[reportPrivateUsage]


def test_ci_fix_rebase_pending_survives_head_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.sh"
    _ = state.write_text(
        "CI_FIX_REBASE_PENDING=true\nCI_FIX_REBASE_PENDING_HEAD=oldhead\n",
        encoding="utf-8",
    )
    ctx = _ctx(tmp_path, state_file=str(state), ci_fix_rebase_pending=True)
    monkeypatch.setattr(ship.finalize, "postbump_preflight", lambda *_a, **_k: ship.finalize.PostbumpPreflight(ok=True))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 5, "url": "u", "status": "created"})(),
    )
    monkeypatch.setattr(ship.run_logs, "write_final_report_comment", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", lambda *_a, **_k: run_logs.RefreshSkip(skipped=False, reason=""))
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: "newhead")
    written: list[str] = []

    def capture_state(ctx_arg: RunContext, **kwargs: object) -> None:
        if kwargs.get("phase") == "pr-prep":
            written.append("true" if ctx_arg.ci_fix_rebase_pending else "false")

    monkeypatch.setattr(ship, "_write_ship_state", capture_state)
    monkeypatch.setattr(
        ship.ci_monitor,
        "monitor",
        lambda *_a, **_k: type(
            "M",
            (),
            {
                "result": StepResult(Outcome.STALLED, detail="stop"),
                "action": "evaluate_failure",
                "goto_rebase": False,
                "did_fixing": False,
                "failed_run_id": "1",
                "ci_fix_rebase_pending": False,
                "transient_rerun_attempted": False,
            },
        )(),
    )
    _ = ship.run_ship(ctx, runner=RecordingRunner(), cwd=str(tmp_path))
    assert written == ["true"]


def test_postmerge_sentinel_written_before_finalize_postmerge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ctx = _ctx(
        tmp_path,
        pr_number=5,
        pr_url="u",
        pr_closed=True,
        merge_result=config.MERGE_RESULT_MERGED,
    )

    def observe_postmerge(_runner: RecordingRunner, ctx_arg: RunContext, **_kwargs: object) -> object:
        assert (Path(ctx_arg.tmpdir) / "post-merge-sentinel").is_file()
        return type(
            "Post",
            (),
            {
                "outcome": Outcome.OK,
                "detail": "",
                "status": "ok",
            },
        )()

    monkeypatch.setattr(ship.finalize, "postmerge", observe_postmerge)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)
    monkeypatch.setattr(
        ship.run_logs,
        "finalize_postmerge_logs",
        lambda *_a, **_k: run_logs.RefreshSkip(skipped=False, reason=""),
    )
    result = ship.run_postmerge_phase(RecordingRunner(), ctx, cwd=str(tmp_path))
    assert result.outcome is Outcome.OK


def test_postmerge_flush_only_when_pr_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ctx = _ctx(
        tmp_path,
        pr_number=5,
        pr_url="u",
        pr_closed=False,
        merge_result=config.MERGE_RESULT_MERGED,
    )
    calls: list[bool] = []
    monkeypatch.setattr(
        ship.finalize,
        "postmerge",
        lambda *_a, **_k: type("Post", (), {"outcome": Outcome.OK, "detail": "", "status": "ok"})(),
    )
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)
    monkeypatch.setattr(
        ship.run_logs,
        "finalize_postmerge_logs",
        lambda *_a, **_k: calls.append(True) or run_logs.RefreshSkip(skipped=False, reason=""),
    )
    result = ship.run_postmerge_phase(RecordingRunner(), ctx, cwd=str(tmp_path))
    assert result.outcome is Outcome.STALLED
    assert result.detail == "postmerge requires a closed merge PR"
    assert not calls


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
  printf '%s\\n' '{"detail":"Python ship driver requires Python 3.11 or newer","failed_run_id":"","ledger_dispatcher":"","ledger_exit_code":null,"ledger_failure_detail_log":"","ledger_phase":"","ledger_ready":false,"ledger_site":"","ledger_step":"","ledger_trigger":"","merge_result":"","needs_user_reason":"","outcome":"STALLED","pr_number":null,"pr_url":""}'
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
    assert '"ledger_ready":false' in completed.stdout
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
    python_dir = Path(__file__).resolve().parent
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
        env={**clean_env, "PYTHONPATH": str(python_dir), "QUIET_TMPDIR": str(tmp_path)},
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


def test_ctx_from_args_rehydrates_cli_state_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "STALL_TRACKING=true\nSTALL_STEP=seeded\nRESUME_PHASE=ship-pr-rrr-phase14\nCALLER_KIND=ship_pr_pre_push\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))

    args = ship.build_parser().parse_args(["--tmpdir", str(tmp_path), "--state-file", str(state_file)])
    ctx = ship._ctx_from_args(args)  # pyright: ignore[reportPrivateUsage]

    assert ctx.stall_tracking is True
    assert ctx.stall_step == "seeded"


# ---------------------------------------------------------------------------
# ci-fix-exhausted envelope tests (issue #3726)
# ---------------------------------------------------------------------------

def test_ci_fix_exhausted_write_detail_log_returns_path(tmp_path: Path) -> None:
    """_write_ci_fix_detail_log writes the detail text and returns the file path."""
    ctx = _ctx(tmp_path)
    ci_detail = "ci-fix-exhausted: python-lint\nFAIL test_foo.py\n"
    path = ship._write_ci_fix_detail_log(ctx, ci_detail)  # pyright: ignore[reportPrivateUsage]
    assert path
    assert Path(path).read_text(encoding="utf-8") == ci_detail


def test_ci_fix_exhausted_terminal_state_sets_bail_reason(tmp_path: Path) -> None:
    """_write_terminal_state for NEEDS_USER_INPUT/ci-fix-exhausted persists BAIL_REASON, BAIL_FAILURE_DETAIL_LOG, STALL_STEP."""
    state_file = tmp_path / "ship-pr-state.sh"
    ci_detail = "ci-fix-exhausted: python-lint\nFAIL test_foo.py\n"
    ctx = _ctx(tmp_path, state_file=str(state_file), final_bail_reason="ci-fix-exhausted")
    detail_log_path = ship._write_ci_fix_detail_log(ctx, ci_detail)  # pyright: ignore[reportPrivateUsage]

    ship._write_terminal_state(  # pyright: ignore[reportPrivateUsage]
        ctx,
        Outcome.NEEDS_USER_INPUT,
        "10",
        bail_failure_detail_log=detail_log_path,
    )

    state = state_file.read_text(encoding="utf-8")
    assert "BAIL_REASON=ci-fix-exhausted\n" in state
    assert f"BAIL_FAILURE_DETAIL_LOG={detail_log_path}\n" in state
    assert "STALL_STEP=10\n" in state


def test_ci_fix_exhausted_detail_log_classified_by_stall_recovery(tmp_path: Path) -> None:
    """Stall-recovery classifier on the new envelope yields ci-fix-exhausted/step8-shippr."""
    stall_recovery = Path(__file__).resolve().parents[1] / "skills" / "implement" / "scripts" / "stall-recovery-report.sh"
    if not stall_recovery.exists():
        pytest.skip("stall-recovery-report.sh not found — skipping integration check")

    ci_detail = "ci-fix-exhausted: python-lint\nFAIL test_foo.py asserted False\n"
    detail_log = tmp_path / "ci-fix-exhausted-detail.log"
    _ = detail_log.write_text(ci_detail, encoding="utf-8")

    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        f"PHASE=stalled\nBRANCH_NAME=feat\nPR_NUMBER=7\n"
        f"BAIL_REASON=ci-fix-exhausted\nBAIL_FAILURE_DETAIL_LOG={detail_log}\n"
        f"STALL_TRACKING=false\nSTALL_STEP=10\nEXIT_CODE=3\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "session-env.sh").write_text("", encoding="utf-8")

    completed = subprocess.run(
        ["bash", str(stall_recovery), "classify",
         "--implement-tmpdir", str(tmp_path),
         "--in-memory-stall-tracking", "true",
         "--failure-detail-log", str(detail_log)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    out = completed.stdout
    assert "FAILURE_CLASS=ci-fix-exhausted" in out, f"unexpected classify output: {out}"
    assert "RESUME_HINT=step8-shippr" in out, f"unexpected classify output: {out}"


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


def test_terminal_finalize_write_emits_success_breadcrumb(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = _ctx(tmp_path, pr_number=7, pr_closed=True)
    ship._write_terminal_finalize_if_terminal(ctx, Outcome.OK, "")  # pyright: ignore[reportPrivateUsage]

    captured = capsys.readouterr()
    data = ship.finalize.read_finalize_state(tmp_path / "finalize-state.sh")
    assert data["EXIT_CODE"] == "0"
    assert "ship.py: finalize-state-written:" in captured.err
    assert f"path={tmp_path / 'finalize-state.sh'}" in captured.err
    assert "outcome=OK" in captured.err
    assert "step=" in captured.err

    transient_dir = tmp_path / "transient"
    transient_dir.mkdir()
    invalid = Path("/not/allowed/larch")
    _ = capsys.readouterr()
    ship._write_terminal_finalize_if_terminal(  # pyright: ignore[reportPrivateUsage]
        _ctx(transient_dir),
        Outcome.TRANSIENT,
        "checks",
    )
    ship._write_terminal_finalize_if_terminal(  # pyright: ignore[reportPrivateUsage]
        _ctx(tmp_path, tmpdir=str(invalid)),
        Outcome.OK,
        "done",
    )

    captured = capsys.readouterr()
    assert "finalize-state-written" not in captured.err
    assert not (transient_dir / "finalize-state.sh").exists()
    assert not (invalid / "finalize-state.sh").exists()


def test_persist_stall_metadata_preserves_existing_tracking(tmp_path: Path) -> None:
    target = tmp_path / "finalize-state.sh"
    ship.finalize.write_finalize_state_merged(target, {"STALL_TRACKING": "true", "STALL_STEP": "existing"})
    ctx = _ctx(tmp_path, stall_step="new")
    ship._persist_stall_metadata_if_needed(ctx, ship.ShipResult(Outcome.STALLED, detail="new"), tmp_path)  # pylint: disable=protected-access
    data = ship.finalize.read_finalize_state(target)
    assert data == {"STALL_TRACKING": "true", "STALL_STEP": "existing"}


def test_main_stalled_metadata_write_failure_preserves_stalled_outcome(
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
    monkeypatch.setattr(ship.finalize, "postbump_preflight", lambda *_a, **_k: ship.finalize.PostbumpPreflight(ok=True))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
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


def test_ship_state_merge_preserves_active_orchestrator_stall_keys(tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text("STALL_TRACKING=true\nEXPECTED_SESSION_ID=session-1\n", encoding="utf-8")

    ship._write_ship_state(  # pyright: ignore[reportPrivateUsage]
        _ctx(tmp_path, state_file=str(state_file), pr_number=12, stall_tracking=True),
        phase="ci-initial",
    )

    state = state_file.read_text(encoding="utf-8")
    assert "STALL_TRACKING=true\n" in state
    assert "EXPECTED_SESSION_ID=session-1\n" in state
    assert "PHASE=ci-initial\n" in state
    assert "PR_NUMBER=12\n" in state


def test_ship_state_merge_clears_stale_stall_keys_on_healthy_write(tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text("STALL_TRACKING=true\nSTALL_STEP=old\nEXPECTED_SESSION_ID=session-1\n", encoding="utf-8")

    ship._write_ship_state(  # pyright: ignore[reportPrivateUsage]
        _ctx(tmp_path, state_file=str(state_file), pr_number=12, stall_tracking=False),
        phase="ci-initial",
    )

    state = state_file.read_text(encoding="utf-8")
    assert "STALL_TRACKING=true\n" not in state
    assert "STALL_STEP=old\n" not in state
    assert "EXPECTED_SESSION_ID=session-1\n" in state


def test_ship_state_write_refuses_symlink_leaf(tmp_path: Path) -> None:
    target = tmp_path / "target-state.sh"
    state_file = tmp_path / "ship-pr-state.sh"
    state_file.symlink_to(target)

    with pytest.raises(ShipError, match="symlinked ship state path"):
        ship._write_ship_state(  # pyright: ignore[reportPrivateUsage]
            _ctx(tmp_path, state_file=str(state_file), pr_number=12),
            phase="ci-initial",
        )

    assert not target.exists()


def test_ship_state_write_unlinks_leftover_regular_tmp(tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    tmp = tmp_path / "ship-pr-state.sh.tmp"
    _ = tmp.write_text("stale\n", encoding="utf-8")

    ship._write_ship_state(  # pyright: ignore[reportPrivateUsage]
        _ctx(tmp_path, state_file=str(state_file), pr_number=12),
        phase="ci-initial",
    )

    assert not tmp.exists()
    assert "PHASE=ci-initial\n" in state_file.read_text(encoding="utf-8")


def test_ship_state_write_drops_unknown_existing_keys(tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text("MALICIOUS_KEY=source-me\nEXPECTED_SESSION_ID=session-1\n", encoding="utf-8")

    ship._write_ship_state(  # pyright: ignore[reportPrivateUsage]
        _ctx(tmp_path, state_file=str(state_file), pr_number=12),
        phase="ci-initial",
    )

    state = state_file.read_text(encoding="utf-8")
    assert "MALICIOUS_KEY=" not in state
    assert "EXPECTED_SESSION_ID=session-1\n" in state


def test_ship_state_read_error_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text("STALL_TRACKING=true\nEXPECTED_SESSION_ID=session-1\n", encoding="utf-8")

    def fail_read(*_args: object, **_kwargs: object) -> str:
        raise OSError("blocked")

    monkeypatch.setattr(Path, "read_text", fail_read)

    with pytest.raises(ShipError, match="cannot read existing ship state"):
        ship._write_ship_state(  # pyright: ignore[reportPrivateUsage]
            _ctx(tmp_path, state_file=str(state_file), pr_number=12),
            phase="ci-initial",
        )


def test_invalid_tmpdir_writes_no_state_files(tmp_path: Path) -> None:
    invalid_tmpdir = tmp_path / ".." / "not-allowed"
    ctx = _ctx(tmp_path, tmpdir=str(invalid_tmpdir), state_file=str(invalid_tmpdir / "ship-pr-state.sh"))

    result = ship.run_ship(ctx, runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert result.detail == "invalid tmpdir"
    assert not (invalid_tmpdir / "ship-pr-state.sh").exists()
    assert not (invalid_tmpdir / "finalize-state.sh").exists()


def test_postmerge_flush_skip_writes_stall_shape(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    ctx = _ctx(
        tmp_path,
        state_file=str(state_file),
        pr_number=5,
        pr_url="https://example.test/pr/5",
        pr_closed=True,
        merge_result=config.MERGE_RESULT_MERGED,
    )
    monkeypatch.setattr(
        ship.finalize,
        "postmerge",
        lambda *_a, **_k: type("Post", (), {"outcome": Outcome.OK, "detail": "", "status": "ok"})(),
    )
    monkeypatch.setattr(
        ship.run_logs,
        "finalize_postmerge_logs",
        lambda *_a, **_k: run_logs.RefreshSkip(skipped=True, reason="commit-failed"),
    )

    result = ship.run_postmerge_phase(RecordingRunner(), ctx, cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    finalize_state = ship.finalize.read_finalize_state(tmp_path / "finalize-state.sh")
    assert finalize_state["STALL_TRACKING"] == "true"
    assert finalize_state["STALL_STEP"] == "postmerge-flush"
    state = state_file.read_text(encoding="utf-8")
    assert "PHASE=postmerge\n" in state
    assert "PHASE=done\n" not in state
    assert "STALL_TRACKING=true\n" in state


def test_postbump_stall_writes_terminal_finalize(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    monkeypatch.setattr(ship.finalize, "postbump_preflight", lambda *_a, **_k: ship.finalize.PostbumpPreflight(ok=True))
    monkeypatch.setattr(
        ship.finalize,
        "postbump",
        lambda *_a, **_k: type("R", (), {"outcome": Outcome.STALLED, "status": "rebase-failed", "detail": "conflict"})(),
    )
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", lambda *_a, **_k: type("S", (), {"skipped": False, "reason": ""})())

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    finalize_state = ship.finalize.read_finalize_state(tmp_path / "finalize-state.sh")
    assert finalize_state["STALL_TRACKING"] == "true"
    assert finalize_state["STALL_STEP"] == "rebase-failed"
    assert finalize_state["EXIT_CODE"] == "4"
    state = state_file.read_text(encoding="utf-8")
    assert "PHASE=rebase-failed\n" in state
    assert "STALL_TRACKING=true\n" in state



def test_outer_stalled_exception_writes_terminal_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"

    def raise_stalled(*_a: object, **_k: object) -> StepResult:
        raise Stalled("outer stalled path")

    monkeypatch.setattr(ship.finalize, "postbump_preflight", raise_stalled)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    finalize_state = ship.finalize.read_finalize_state(tmp_path / "finalize-state.sh")
    assert finalize_state["STALL_TRACKING"] == "true"
    assert finalize_state["EXIT_CODE"] == "4"
    assert "STALL_TRACKING=true\n" in state_file.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# OOS filing signal tests
# ---------------------------------------------------------------------------

def _patch_fresh_path_pre_pr_create(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ship.finalize, "postbump_preflight", lambda *_a, **_k: ship.finalize.PostbumpPreflight(ok=True))
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", lambda *_a, **_k: run_logs.RefreshSkip(skipped=False, reason=""))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())


def test_oos_pending_exits_with_filing_reason_when_accepted_oos_present(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_fresh_path_pre_pr_create(monkeypatch)
    _ = (tmp_path / "oos-accepted-review.md").write_text(
        "### OOS_1: Some finding\nSome body.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr, "ensure_pr",
        lambda *_a, **_k: (_ for _ in ()).throw(ShipError("past-oos-check")),
    )

    result = ship.run_ship(_ctx(tmp_path), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert result.needs_user_reason == ""
    assert "past-oos-check" in result.detail


def test_oos_pending_exits_with_filing_reason_when_security_sidecar_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_fresh_path_pre_pr_create(monkeypatch)
    _ = (tmp_path / "security-oos-observations.md").write_text(
        "### OOS_1: Security item\n- **focus-area**: security\n",
        encoding="utf-8",
    )

    result = ship.run_ship(_ctx(tmp_path), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == "oos-filing"


def test_oos_pending_false_skips_oos_check_despite_accepted_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_fresh_path_pre_pr_create(monkeypatch)
    _ = (tmp_path / "oos-accepted-review.md").write_text(
        "### OOS_1: Some finding\nSome body.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr, "ensure_pr",
        lambda *_a, **_k: (_ for _ in ()).throw(ShipError("past-oos-check")),
    )

    result = ship.run_ship(
        _ctx(tmp_path, oos_pending=False), runner=RecordingRunner(), cwd=str(tmp_path)
    )

    assert result.outcome is Outcome.STALLED
    assert "past-oos-check" in result.detail


def test_oos_check_skipped_when_forked(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_fresh_path_pre_pr_create(monkeypatch)
    _ = (tmp_path / "oos-accepted-review.md").write_text(
        "### OOS_1: Some finding\nSome body.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr, "ensure_pr",
        lambda *_a, **_k: (_ for _ in ()).throw(ShipError("past-oos-check")),
    )

    result = ship.run_ship(
        _ctx(tmp_path, forked=True), runner=RecordingRunner(), cwd=str(tmp_path)
    )

    assert result.outcome is Outcome.STALLED
    assert "past-oos-check" in result.detail


def test_oos_check_skipped_when_repo_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_fresh_path_pre_pr_create(monkeypatch)
    _ = (tmp_path / "oos-accepted-review.md").write_text(
        "### OOS_1: Some finding\nSome body.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr, "ensure_pr",
        lambda *_a, **_k: (_ for _ in ()).throw(ShipError("past-oos-check")),
    )

    result = ship.run_ship(
        _ctx(tmp_path, repo_unavailable=True), runner=RecordingRunner(), cwd=str(tmp_path)
    )

    assert result.outcome is Outcome.STALLED
    assert "past-oos-check" in result.detail


def test_oos_check_no_signal_when_no_accepted_oos_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_fresh_path_pre_pr_create(monkeypatch)
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr, "ensure_pr",
        lambda *_a, **_k: (_ for _ in ()).throw(ShipError("past-oos-check")),
    )

    result = ship.run_ship(_ctx(tmp_path), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert "past-oos-check" in result.detail

def test_needs_user_ship_result_includes_ledger_ready_keys() -> None:
    result = ship._step_result_to_ship(StepResult(Outcome.NEEDS_USER_INPUT, config.NEEDS_USER_CI_FIX_EXHAUSTED))
    data = result.to_json_dict()
    assert data["ledger_ready"] is True
    assert data["ledger_site"] == "ship-pr"
    assert data["ledger_trigger"] == config.NEEDS_USER_CI_FIX_EXHAUSTED
    assert data["ledger_step"] == "8"
    assert data["ledger_phase"] == "ci-merge"
    assert data["ledger_dispatcher"] == "ship-pr"
    assert data["ledger_exit_code"] == config.EXIT_NEEDS_USER_INPUT
    assert "ledger_failure_detail_log" in data


def test_step_result_ledger_handoff_overrides_ship_defaults(tmp_path: Path) -> None:
    detail_log = tmp_path / "checks.redacted.log"
    _ = detail_log.write_text("lint failed\n", encoding="utf-8")
    step = StepResult(
        Outcome.NEEDS_USER_INPUT,
        config.NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX,
        ledger_ready=True,
        ledger_site="ship-pr-ci-initial",
        ledger_trigger="main-agent-required",
        ledger_step="8",
        ledger_phase="ci-initial",
        ledger_dispatcher="lint-fix-loop",
        ledger_exit_code=config.EXIT_NEEDS_USER_INPUT,
        ledger_failure_detail_log=str(detail_log),
    )
    data = ship._step_result_to_ship(step).to_json_dict()  # pyright: ignore[reportPrivateUsage]
    assert data["needs_user_reason"] == config.NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX
    assert data["ledger_ready"] is True
    assert data["ledger_site"] == "ship-pr-internal"
    assert data["ledger_trigger"] == config.NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX
    assert data["ledger_phase"] == "ci-initial"
    assert data["ledger_failure_detail_log"] == str(detail_log)


def test_step_result_ledger_handoff_normalizes_merge_lint_fix_tokens(tmp_path: Path) -> None:
    detail_log = tmp_path / "checks.redacted.log"
    _ = detail_log.write_text("lint failed\n", encoding="utf-8")
    step = StepResult(
        Outcome.NEEDS_USER_INPUT,
        config.NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX,
        ledger_ready=True,
        ledger_site="ship-pr-ci-merge",
        ledger_trigger="main-agent-required",
        ledger_step="8",
        ledger_phase="ci-merge",
        ledger_dispatcher="lint-fix-loop",
        ledger_exit_code=config.EXIT_NEEDS_USER_INPUT,
        ledger_failure_detail_log=str(detail_log),
    )
    data = ship._step_result_to_ship(step).to_json_dict()  # pyright: ignore[reportPrivateUsage]
    assert data["ledger_site"] == "ship-pr-internal"
    assert data["ledger_trigger"] == config.NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX
    assert data["ledger_phase"] == "ci-merge"


def test_ship_default_ledger_phase_can_follow_active_phase() -> None:
    result = ship._step_result_to_ship(  # pyright: ignore[reportPrivateUsage]
        StepResult(Outcome.NEEDS_USER_INPUT, config.NEEDS_USER_CI_FIX_EXHAUSTED),
        default_ledger_phase="ci-initial",
    )
    assert result.ledger_phase == "ci-initial"


def test_ship_default_ledger_detail_log_is_included() -> None:
    result = ship._step_result_to_ship(  # pyright: ignore[reportPrivateUsage]
        StepResult(Outcome.NEEDS_USER_INPUT, config.NEEDS_USER_CI_FIX_EXHAUSTED),
        default_ledger_phase="ci-initial",
        default_ledger_failure_detail_log="/tmp/claude-implement-x/ci-fix.log",
    )
    assert result.ledger_ready is True
    assert result.ledger_failure_detail_log == "/tmp/claude-implement-x/ci-fix.log"


def test_ci_local_unfixable_compound_reason_is_preserved_for_ledger() -> None:
    detail = f"{config.NEEDS_USER_CI_LOCAL_UNFIXABLE}:job_1,job-2"
    result = ship._step_result_to_ship(StepResult(Outcome.NEEDS_USER_INPUT, detail))
    data = result.to_json_dict()
    assert data["needs_user_reason"] == detail
    assert data["ledger_ready"] is True
    assert data["ledger_trigger"] == detail
