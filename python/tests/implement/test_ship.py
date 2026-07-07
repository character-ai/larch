# pyright: reportUnknownLambdaType=false, reportUnknownArgumentType=false, reportPrivateUsage=false, reportUnusedCallResult=false
"""Tests for ship.py."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast
import pytest

from larch.core import config
from larch.report import final_report
from larch.report import run_log_flush
from larch.report import run_logs
from larch.implement import ship
from larch.implement import ship_guidelines
from larch.implement import ship_pr
from larch.implement import ship_resume
from larch.errors import PrePushConflictHandoff, ShipError, Stalled
from larch.outcomes import Outcome, StepResult
from larch.core.proc import CommandResult, ProcRunner

from test_support import RecordingRunner, make_run_context

if TYPE_CHECKING:
    from larch.core.run_context import RunContext

_REAL_FLUSH_LOGS_PRE = run_logs.flush_logs_pre


@pytest.fixture(autouse=True)
def _default_try_rev_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide a non-empty HEAD SHA so tests without a real git repo pass the guidelines gate.

    Tests that explicitly test empty-SHA behavior override this via their own
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: "").
    """
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: "abc123")


def _ctx(tmp_path: Path, **kwargs: object) -> RunContext:
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text(
        json.dumps({"summary_bullets": ["Add driver", "Add finalize"]}),
        encoding="utf-8",
    )
    base = make_run_context(
        run_id="run-abc",
        tmpdir=str(tmp_path),
        manifest_path=str(manifest),
        tool_label="codex",
        pr_title="Implement driver",
        issue_number="1",
    )
    return base.with_(**kwargs)


def _pin_guidelines_note_text(
    *,
    implement_tmpdir: str,
    head_sha: str,
    base_ref: str,
    repo_root: str | None = None,
) -> str:
    note, _warning_logged = ship._pin_and_load_guidelines_note(
        implement_tmpdir=implement_tmpdir,
        head_sha=head_sha,
        base_ref=base_ref,
        repo_root=repo_root,
    )
    return note


def _successful_rebase_result(*, rebased: bool = False) -> ship.rebase.RebaseResult:
    return ship.rebase.RebaseResult(
        outcome=Outcome.OK,
        rebased=rebased,
        pushed=True,
        new_version=None,
        attempts=1,
        detail="",
    )


@pytest.fixture(autouse=True)
def _default_post_ensure_flush_and_push(monkeypatch: pytest.MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    def fake_flush_logs_pre(
        runner: RecordingRunner,
        ctx: RunContext,
        *,
        cwd: str | None = None,
        strict_final_report: bool = False,
    ) -> run_logs.RefreshSkip:
        _ = runner, ctx, cwd
        if strict_final_report:
            return run_logs.RefreshSkip(skipped=False, reason="")
        return run_logs.RefreshSkip(skipped=False, reason="")

    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", fake_flush_logs_pre)
    monkeypatch.setattr(
        ship.push,
        "push_branch",
        lambda *_a, **_k: ship.push.PushResult(remote="origin", attempts=1, status="pushed"),
    )




def _read_state(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, value = line.split("=", 1)
        data[key] = value
    return data


def _replace_guidelines_sidecar_value(tmpdir: Path, *, key: str, value: str) -> None:
    sidecar = tmpdir / ship.architectural_guidelines.STAGED_ASSESSMENT_ENV
    lines = [f"{key}={value}" if line.startswith(f"{key}=") else line for line in sidecar.read_text(encoding="utf-8").splitlines()]
    sidecar.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_ship_rebase_phase_stall_returns_terminal_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = tmp_path / "ship-pr-state.sh"
    ctx = _ctx(tmp_path, state_file=str(state), pr_number=7, pr_url="https://example.com/pr/7", merge=True)

    def fake_flush_logs_pre(**_kw: object) -> run_logs.RefreshSkip:
        return run_logs.RefreshSkip(skipped=True, reason="blocked")

    def fake_publish(*, runner: RecordingRunner, ctx: RunContext, cwd: str | None = None) -> None:  # noqa: ARG001  # pylint: disable=unused-argument
        del cwd

    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", fake_flush_logs_pre)
    monkeypatch.setattr(ship, "_publish_post_pr_terminal_snapshot", fake_publish)

    result = ship._ship_rebase_phase(
        runner=RecordingRunner(),
        working=ctx,
        cwd=str(tmp_path),
        base_remote="origin",
        base_ref="main",
        iteration=3,
        rebase_count=2,
        fix_attempts=1,
        transient_retries=0,
        variant=ship.ShipRebaseVariant.GOTO_REBASE,
    )

    assert result.rebase_count == 2
    assert result.terminal is not None
    assert result.terminal.outcome is Outcome.STALLED
    data = _read_state(state)
    assert data["PHASE"] == "stalled"
    assert data["STALL_STEP"] == "pre-rebase"
    assert data["ITERATION"] == "3"
    assert data["REBASE_COUNT"] == "2"


def test_ship_rebase_phase_success_increments_rebase_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = tmp_path / "ship-pr-state.sh"
    ctx = _ctx(tmp_path, state_file=str(state), pr_number=7, pr_url="https://example.com/pr/7", merge=True)

    def fake_flush_logs_pre(**_kw: object) -> run_logs.RefreshSkip:
        return run_logs.RefreshSkip(skipped=False, reason="")

    def fake_rebase_and_push(
        *,
        runner: RecordingRunner,  # noqa: ARG001  # pylint: disable=unused-argument
        repo: str,
        run_id: str,
        cwd: str,
        tmpdir: str,
        base_remote: str,
        base_ref: str,
        allow_conflict_fix: bool,
        enable_pre_push_handoff: bool,
    ) -> object:
        del repo, run_id, cwd, tmpdir, base_remote, base_ref, allow_conflict_fix, enable_pre_push_handoff
        return ship.rebase.RebaseResult(
            outcome=Outcome.OK,
            rebased=False,
            pushed=True,
            new_version=None,
            attempts=1,
            detail="",
        )

    pin_calls: list[dict[str, object]] = []

    def fake_pin_or_invalidate(**kwargs: object) -> bool:
        pin_calls.append(kwargs)
        return False

    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", fake_flush_logs_pre)
    monkeypatch.setattr(ship.rebase, "rebase_and_push", fake_rebase_and_push)
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: "post-rebase-head")
    monkeypatch.setitem(
        ship._ship_rebase_phase.__globals__,
        "_pin_or_invalidate_guidelines_note",
        fake_pin_or_invalidate,
    )

    result = ship._ship_rebase_phase(
        runner=RecordingRunner(),
        working=ctx,
        cwd=str(tmp_path),
        base_remote="origin",
        base_ref="main",
        iteration=0,
        rebase_count=4,
        fix_attempts=0,
        transient_retries=0,
        variant=ship.ShipRebaseVariant.MAIN_ADVANCED,
    )

    assert result.terminal is None
    assert result.rebase_count == 5
    assert not pin_calls
    assert _read_state(state)["PHASE"] == "rebase"


def test_ship_rebase_phase_rebased_retains_guidelines_note(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = tmp_path / "ship-pr-state.sh"
    ctx = _ctx(tmp_path, state_file=str(state), pr_number=7, pr_url="https://example.com/pr/7", merge=True)

    def fake_flush_logs_pre(**_kw: object) -> run_logs.RefreshSkip:
        return run_logs.RefreshSkip(skipped=False, reason="")

    def fake_rebase_and_push(
        *,
        runner: RecordingRunner,  # noqa: ARG001  # pylint: disable=unused-argument
        repo: str,
        run_id: str,
        cwd: str,
        tmpdir: str,
        base_remote: str,
        base_ref: str,
        allow_conflict_fix: bool,
        enable_pre_push_handoff: bool,
    ) -> object:
        del repo, run_id, cwd, tmpdir, base_remote, base_ref, allow_conflict_fix, enable_pre_push_handoff
        return ship.rebase.RebaseResult(
            outcome=Outcome.OK,
            rebased=True,
            pushed=True,
            new_version=None,
            attempts=1,
            detail="",
        )

    pin_calls: list[dict[str, object]] = []

    def fake_pin_or_invalidate(**kwargs: object) -> bool:
        pin_calls.append(kwargs)
        return False

    def fail_invalidate(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("invalidate helper should not be called after a clean rebase")

    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", fake_flush_logs_pre)
    monkeypatch.setattr(ship.rebase, "rebase_and_push", fake_rebase_and_push)
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: "post-rebase-head")
    monkeypatch.setitem(
        ship._ship_rebase_phase.__globals__,
        "_invalidate_guidelines_note",
        fail_invalidate,
    )
    monkeypatch.setitem(
        ship._ship_rebase_phase.__globals__,
        "_pin_or_invalidate_guidelines_note",
        fake_pin_or_invalidate,
    )

    result = ship._ship_rebase_phase(
        runner=RecordingRunner(),
        working=ctx,
        cwd=str(tmp_path),
        base_remote="origin",
        base_ref="main",
        iteration=0,
        rebase_count=4,
        fix_attempts=0,
        transient_retries=0,
        variant=ship.ShipRebaseVariant.MAIN_ADVANCED,
    )

    assert result.terminal is None
    assert result.rebase_count == 5
    assert not pin_calls
    assert _read_state(state)["PHASE"] == "rebase"


def test_ship_rebase_phase_defers_guidelines_refresh_to_compose_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    repo_root = str(repo)

    def git(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr or completed.stdout
        return completed.stdout.strip()

    git("init")
    git("config", "user.name", "Larch Test")
    git("config", "user.email", "larch@example.invalid")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-m", "base")
    (repo / ship.architectural_guidelines.GUIDELINES_FILENAME).write_text(
        "### G-python-1: Keep small\n- Why: minimal change.\n- Deviate when: never\n",
        encoding="utf-8",
    )
    git("branch", "-M", "main")
    git("remote", "add", "origin", str(repo))
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    git("switch", "-c", "feature")
    (repo / "README.md").write_text("base\nimplementation\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-m", "implementation")
    pre_rebase_head = git("rev-parse", "HEAD")
    initial_diff = ship.architectural_guidelines.materialize_implementation_diff(
        repo,
        base_remote="origin",
        base_ref="main",
    )
    ship.architectural_guidelines.write_staged_assessment(
        implement_tmpdir=tmp_path,
        assessment_text="Guideline deviation note\n",
        assessed_head_sha=pre_rebase_head,
        diff_fingerprint_value=ship.architectural_guidelines.diff_fingerprint(initial_diff),
        base_ref="origin/main",
        diff_text=initial_diff,
    )

    git("switch", "main")
    (repo / "unrelated.txt").write_text("main advanced\n", encoding="utf-8")
    git("add", "unrelated.txt")
    git("commit", "-m", "advance main")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    git("switch", "feature")

    def fake_flush_logs_pre(**_kw: object) -> run_logs.RefreshSkip:
        return run_logs.RefreshSkip(skipped=False, reason="")

    def fake_rebase_and_push(
        *,
        runner: RecordingRunner,  # noqa: ARG001  # pylint: disable=unused-argument
        repo: str,
        run_id: str,
        cwd: str,
        tmpdir: str,
        base_remote: str,
        base_ref: str,
        allow_conflict_fix: bool,
        enable_pre_push_handoff: bool,
    ) -> object:
        assert cwd == repo_root
        assert tmpdir == str(tmp_path)
        del repo, run_id, allow_conflict_fix, enable_pre_push_handoff
        git("rebase", f"{base_remote}/{base_ref}")
        return ship.rebase.RebaseResult(
            outcome=Outcome.OK,
            rebased=True,
            pushed=True,
            new_version=None,
            attempts=1,
            detail="",
        )

    def real_try_rev_parse(
        _runner: RecordingRunner,
        ref: str,
        *,
        cwd: str | None = None,
    ) -> str:
        assert cwd == repo_root
        return git("rev-parse", ref)

    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", fake_flush_logs_pre)
    monkeypatch.setattr(ship.rebase, "rebase_and_push", fake_rebase_and_push)
    monkeypatch.setattr(ship.git, "try_rev_parse", real_try_rev_parse)

    result = ship._ship_rebase_phase(
        runner=RecordingRunner(),
        working=_ctx(
            tmp_path,
            state_file=str(tmp_path / "ship-pr-state.sh"),
            pr_number=7,
            pr_url="https://example.com/pr/7",
            merge=True,
        ),
        cwd=repo_root,
        base_remote="origin",
        base_ref="main",
        iteration=0,
        rebase_count=0,
        fix_attempts=0,
        transient_retries=0,
        variant=ship.ShipRebaseVariant.MAIN_ADVANCED,
    )

    post_rebase_head = git("rev-parse", "HEAD")
    rebased_diff = ship.architectural_guidelines.materialize_implementation_diff(
        repo,
        base_remote="origin",
        base_ref="main",
    )
    assert result.terminal is None
    assert result.rebase_count == 1
    assert post_rebase_head != pre_rebase_head
    assert rebased_diff == initial_diff
    assert not ship.architectural_guidelines.note_consumable(
        implement_tmpdir=tmp_path,
        head_sha=post_rebase_head,
    )
    assert ship.architectural_guidelines.staged_assessment_present(tmp_path)
    assert ship.architectural_guidelines.read_dropped_note_notice(tmp_path) == ""


def test_ship_phase14_rebase_success_writes_ci_initial_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = tmp_path / "ship-pr-state.sh"
    flag = tmp_path / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME
    _ = flag.write_text(
        f"RESUME_PHASE={config.SHIP_PR_RRR_RESUME_PHASE}\nREASON=mergeStateStatus=DIRTY\n",
        encoding="utf-8",
    )
    _ = state.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\n"
        "RESUME_PHASE=ship-pr-rrr-phase14\nCALLER_KIND=ship_pr_pre_push\n"
        "LAST_MONITORED_HEAD=abc123\n",
        encoding="utf-8",
    )
    ctx = _ctx(tmp_path, state_file=str(state), pr_number=7, pr_url="https://example.com/pr/7", merge=True)

    def fake_rebase_and_push(
        *,
        runner: RecordingRunner,  # noqa: ARG001  # pylint: disable=unused-argument
        repo: str,
        run_id: str,
        cwd: str,
        tmpdir: str,
        base_remote: str,
        base_ref: str,
        allow_conflict_fix: bool,
        enable_pre_push_handoff: bool,
    ) -> object:
        del repo, run_id, cwd, tmpdir, base_remote, base_ref, allow_conflict_fix, enable_pre_push_handoff
        return ship.rebase.RebaseResult(
            outcome=Outcome.OK,
            rebased=False,
            pushed=True,
            new_version=None,
            attempts=1,
            detail="",
        )

    pin_calls: list[dict[str, object]] = []

    def fake_pin_or_invalidate(**kwargs: object) -> bool:
        pin_calls.append(kwargs)
        return False

    monkeypatch.setattr(ship.rebase, "rebase_and_push", fake_rebase_and_push)
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: "phase14-head")
    monkeypatch.setitem(
        ship._ship_phase14_rebase.__globals__,
        "_pin_or_invalidate_guidelines_note",
        fake_pin_or_invalidate,
    )

    new_count = ship._ship_phase14_rebase(  # pyright: ignore[reportPrivateUsage]
        runner=RecordingRunner(),
        working=ctx,
        cwd=str(tmp_path),
        base_remote="origin",
        base_ref="main",
        phase14_flag=flag,
        iteration=2,
        rebase_count=1,
        fix_attempts=0,
        transient_retries=0,
        last_monitored_head="abc123",
    )

    data = _read_state(state)
    assert new_count == 2
    assert not pin_calls
    assert not flag.is_file()
    assert data["PHASE"] == "ci-initial"
    assert data["REBASE_COUNT"] == "2"
    assert data.get("RESUME_PHASE", "") == ""
    assert data.get("CALLER_KIND", "") == ""
    assert data["LAST_MONITORED_HEAD"] == "abc123"


def test_ship_phase14_rebase_rebased_retains_guidelines_note(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = tmp_path / "ship-pr-state.sh"
    flag = tmp_path / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME
    _ = flag.write_text(
        f"RESUME_PHASE={config.SHIP_PR_RRR_RESUME_PHASE}\nREASON=mergeStateStatus=DIRTY\n",
        encoding="utf-8",
    )
    _ = state.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\n"
        "RESUME_PHASE=ship-pr-rrr-phase14\nCALLER_KIND=ship_pr_pre_push\n"
        "LAST_MONITORED_HEAD=abc123\n",
        encoding="utf-8",
    )
    ctx = _ctx(tmp_path, state_file=str(state), pr_number=7, pr_url="https://example.com/pr/7", merge=True)

    def fake_rebase_and_push(
        *,
        runner: RecordingRunner,  # noqa: ARG001  # pylint: disable=unused-argument
        repo: str,
        run_id: str,
        cwd: str,
        tmpdir: str,
        base_remote: str,
        base_ref: str,
        allow_conflict_fix: bool,
        enable_pre_push_handoff: bool,
    ) -> object:
        del repo, run_id, cwd, tmpdir, base_remote, base_ref, allow_conflict_fix, enable_pre_push_handoff
        return ship.rebase.RebaseResult(
            outcome=Outcome.OK,
            rebased=True,
            pushed=True,
            new_version=None,
            attempts=1,
            detail="",
        )

    pin_calls: list[dict[str, object]] = []

    def fake_pin_or_invalidate(**kwargs: object) -> bool:
        pin_calls.append(kwargs)
        return False

    def fail_invalidate(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("invalidate helper should not be called after a clean rebase")

    monkeypatch.setattr(ship.rebase, "rebase_and_push", fake_rebase_and_push)
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: "phase14-head")
    monkeypatch.setitem(
        ship._ship_phase14_rebase.__globals__,
        "_invalidate_guidelines_note",
        fail_invalidate,
    )
    monkeypatch.setitem(
        ship._ship_phase14_rebase.__globals__,
        "_pin_or_invalidate_guidelines_note",
        fake_pin_or_invalidate,
    )

    new_count = ship._ship_phase14_rebase(  # pyright: ignore[reportPrivateUsage]
        runner=RecordingRunner(),
        working=ctx,
        cwd=str(tmp_path),
        base_remote="origin",
        base_ref="main",
        phase14_flag=flag,
        iteration=2,
        rebase_count=1,
        fix_attempts=0,
        transient_retries=0,
        last_monitored_head="abc123",
    )

    data = _read_state(state)
    assert new_count == 2
    assert not pin_calls
    assert not flag.is_file()
    assert data["PHASE"] == "ci-initial"
    assert data["REBASE_COUNT"] == "2"
    assert data.get("RESUME_PHASE", "") == ""
    assert data.get("CALLER_KIND", "") == ""
    assert data["LAST_MONITORED_HEAD"] == "abc123"


def test_ship_postmerge_phase_writes_done_only_on_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = tmp_path / "ship-pr-state.sh"
    _ = state.write_text("PHASE=postmerge\nBRANCH_NAME=feat\nPR_NUMBER=7\n", encoding="utf-8")
    ctx = _ctx(tmp_path, state_file=str(state), pr_number=7, pr_url="https://example.com/pr/7", merge=True)

    monkeypatch.setattr(
        ship,
        "run_postmerge_phase",
        lambda *_a, **_k: ship.ShipResult(Outcome.STALLED, detail="blocked"),
    )
    stalled = ship._ship_postmerge_phase(  # pyright: ignore[reportPrivateUsage]
        runner=RecordingRunner(),
        working=ctx,
        cwd=str(tmp_path),
        iteration=1,
        rebase_count=0,
        fix_attempts=0,
        transient_retries=0,
    )

    assert stalled.outcome is Outcome.STALLED
    assert _read_state(state)["PHASE"] == "postmerge"

    monkeypatch.setattr(
        ship,
        "run_postmerge_phase",
        lambda *_a, **_k: ship.ShipResult(Outcome.OK, detail="ok"),
    )
    ok = ship._ship_postmerge_phase(  # pyright: ignore[reportPrivateUsage]
        runner=RecordingRunner(),
        working=ctx,
        cwd=str(tmp_path),
        iteration=1,
        rebase_count=0,
        fix_attempts=0,
        transient_retries=0,
    )

    assert ok.outcome is Outcome.OK
    assert _read_state(state)["PHASE"] == "done"


def test_main_advanced_ci_initial_write_omits_monitor_head_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=true\nDRAFT=false\n"
        "LAST_MONITORED_HEAD=tracked-head\nCI_FIX_REBASE_PENDING_HEAD=pending-head\n",
        encoding="utf-8",
    )
    _open_pr_merge_loop_stubs(monkeypatch)
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: "abc123")
    merge_results = [
        config.MERGE_RESULT_MAIN_ADVANCED,
        config.MERGE_RESULT_DRIVER_ALREADY_MERGED,
    ]
    ci_initial_writes: list[dict[str, str]] = []
    original_write = ship._write_ship_state  # pyright: ignore[reportPrivateUsage]

    def observe_write(ctx: RunContext, **kwargs: object) -> None:
        if kwargs.get("phase") == "ci-initial":
            ci_initial_writes.append({str(key): str(value) for key, value in kwargs.items()})
        original_write(ctx, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(ship, "_write_ship_state", observe_write)
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
    monkeypatch.setattr(ship.rebase, "rebase_and_push", lambda *_a, **_k: _successful_rebase_result())
    monkeypatch.setattr(ship, "run_postmerge_phase", lambda *_a, **_k: ship.ShipResult(Outcome.OK))

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert ci_initial_writes
    main_advanced_follow_up = next(
        write
        for write in ci_initial_writes
        if write.get("phase") == "ci-initial"
        and write.get("iteration") == "1"
        and "last_monitored_head" not in write
        and write.get("ci_fix_rebase_pending_head", "") == ""
    )
    assert main_advanced_follow_up["rebase_count"] == "1"


def test_seed_initial_state_writes_exact_ordered_key_set(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text('{"summary_bullets":["Ship"]}\n', encoding="utf-8")
    state = tmp_path / "ship-pr-state.sh"
    rc = ship.seed_initial_state_main([
        "--tmpdir", str(tmp_path),
        "--state-file", str(state),
        "--branch", "feature/ship",
        "--issue", "42",
        "--repo", "owner/repo",
        "--run-id", "run-42",
        "--manifest-path", str(manifest),
        "--tool-label", "Codex",
        "--merge", "true",
        "--draft", "true",
        "--forked", "true",
        "--repo-unavailable", "false",
        "--deferred", "true",
        "--no-admin-fallback", "true",
        "--no-logs-commit", "true",
        "--expected-session-id", "sid",
        "--expected-tmpdir-basename-prefix", "claude-implement-larch-",
    ])
    assert rc == 0
    lines = state.read_text(encoding="utf-8").splitlines()
    assert [line.split("=", 1)[0] for line in lines] == list(ship.INITIAL_SHIP_STATE_KEYS)
    data = _read_state(state)
    assert data["PHASE"] == "checks"
    assert data["BRANCH_NAME"] == "feature/ship"
    assert data["ISSUE_NUMBER"] == "42"
    assert data["RUN_ID"] == "run-42"
    assert data["REPO"] == "owner/repo"
    assert data["IMPLEMENT_TMPDIR"] == str(tmp_path)
    assert data["MANIFEST_PATH"] == str(manifest)
    assert data["TOOL_LABEL"] == "Codex"
    assert data["MERGE"] == "true"
    assert data["DRAFT"] == "true"
    assert data["FORKED_TARGET"] == "true"
    assert data["DEFERRED"] == "true"
    assert data["NO_ADMIN_FALLBACK"] == "true"
    assert data["NO_LOGS_COMMIT"] == "true"
    assert data["EXPECTED_SESSION_ID"] == "sid"
    assert data["EXPECTED_TMPDIR_BASENAME_PREFIX"] == "claude-implement-larch-"
    assert data["PR_CLOSED"] == "false"
    assert data["STALL_TRACKING"] == "false"
    assert data["OOS_PENDING"] == "false"
    assert data["PR_NUMBER"] == ""
    assert data["BAIL_REASON"] == ""
    assert data["REBASE_COUNT"] == "0"
    assert data["FIX_ATTEMPTS"] == "0"
    assert data["ITERATION"] == "0"
    assert data["TRANSIENT_RETRIES"] == "0"
    assert data["CI_FIX_REBASE_PENDING"] == "false"


def test_seed_initial_state_stall_profile_preserves_merge_forces_draft_false(tmp_path: Path) -> None:
    state = tmp_path / "ship-pr-state.sh"
    rc = ship.seed_initial_state_main([
        "--tmpdir", str(tmp_path),
        "--state-file", str(state),
        "--branch", "feature/ship",
        "--issue", "42",
        "--repo", "owner/repo",
        "--run-id", "run-42",
        "--merge", "true",
        "--draft", "true",
        "--stall-tracking", "true",
        "--stall-step", "5",
        "--bail-reason", "lint-fix-failed",
    ])
    assert rc == 0
    data = _read_state(state)
    assert data["STALL_TRACKING"] == "true"
    assert data["STALL_STEP"] == "5"
    assert data["BAIL_REASON"] == "lint-fix-failed"
    assert data["MERGE"] == "true"
    assert data["DRAFT"] == "false"
    assert data["OOS_PENDING"] == "false"


def test_seed_initial_state_manifest_guard_and_no_partial_file(tmp_path: Path) -> None:
    state = tmp_path / "ship-pr-state.sh"
    missing = tmp_path / "missing.json"
    rc = ship.seed_initial_state_main([
        "--tmpdir", str(tmp_path),
        "--state-file", str(state),
        "--branch", "feature/ship",
        "--issue", "42",
        "--repo", "owner/repo",
        "--run-id", "run-42",
        "--manifest-path", str(missing),
    ])
    assert rc == 2
    assert not state.exists()
    bad_env = tmp_path / "manifest.env"
    _ = bad_env.write_text("STATUS=complete\n", encoding="utf-8")
    rc = ship.seed_initial_state_main([
        "--tmpdir", str(tmp_path),
        "--state-file", str(state),
        "--branch", "feature/ship",
        "--issue", "42",
        "--repo", "owner/repo",
        "--run-id", "run-42",
        "--manifest-path", str(bad_env),
    ])
    assert rc == 2
    assert not state.exists()
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text('{"summary_bullets":["Ship"]}\n', encoding="utf-8")
    rc = ship.seed_initial_state_main([
        "--tmpdir", str(tmp_path),
        "--state-file", str(state),
        "--branch", "feature/ship",
        "--issue", "42",
        "--repo", "owner/repo",
        "--run-id", "run-42",
        "--manifest-path", str(manifest),
    ])
    assert rc == 0


def test_seed_initial_state_create_if_absent_refuses_existing_driver_keys(tmp_path: Path) -> None:
    state = tmp_path / "ship-pr-state.sh"
    _ = state.write_text("PHASE=checks\nPR_NUMBER=7\n", encoding="utf-8")
    before = state.read_text(encoding="utf-8")
    rc = ship.seed_initial_state_main([
        "--tmpdir", str(tmp_path),
        "--state-file", str(state),
        "--branch", "feature/ship",
        "--issue", "42",
        "--repo", "owner/repo",
        "--run-id", "run-42",
    ])
    assert rc == 2
    assert state.read_text(encoding="utf-8") == before


@pytest.mark.parametrize(
    ("extra_args", "field"),
    [
        (["--branch", "", "--issue", "42", "--repo", "owner/repo", "--run-id", "run-42"], "branch"),
        (["--branch", "feature/ship", "--issue", "", "--repo", "owner/repo", "--run-id", "run-42"], "issue"),
        (["--branch", "feature/ship", "--issue", "42", "--repo", "", "--run-id", "run-42"], "repo"),
        (["--branch", "feature/ship", "--issue", "42", "--repo", "owner/repo", "--run-id", ""], "run-id"),
        (["--branch", "-bad", "--issue", "42", "--repo", "owner/repo", "--run-id", "run-42"], "branch"),
        (["--branch", "feature/ship", "--issue", "abc", "--repo", "owner/repo", "--run-id", "run-42"], "issue"),
    ],
)
def test_seed_initial_state_rejects_empty_or_invalid_identity_fields(
    tmp_path: Path,
    extra_args: list[str],
    field: str,
) -> None:
    state = tmp_path / "ship-pr-state.sh"
    rc = ship.seed_initial_state_main(["--tmpdir", str(tmp_path), "--state-file", str(state), *extra_args])
    assert rc == 2, field
    assert not state.exists()


def test_ship_state_merge_preserves_no_admin_fallback(tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text("NO_ADMIN_FALLBACK=true\nEXPECTED_SESSION_ID=session-1\n", encoding="utf-8")

    ship._write_ship_state(  # pyright: ignore[reportPrivateUsage]
        _ctx(tmp_path, state_file=str(state_file), pr_number=12, no_admin_fallback=True),
        phase="ci-initial",
    )

    state = state_file.read_text(encoding="utf-8")
    assert "NO_ADMIN_FALLBACK=true\n" in state
    assert "EXPECTED_SESSION_ID=session-1\n" in state


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
    flush_args: list[tuple[str | None, str | None, bool]] = []

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
    def fake_flush(
        *,
        runner: RecordingRunner,
        ctx: RunContext,
        cwd: str | None = None,
        strict_final_report: bool = False,
    ) -> run_logs.RefreshSkip:
        _ = runner
        order.append("flush-pre")
        flush_args.append((ctx.state_file, cwd, strict_final_report))
        return run_logs.RefreshSkip(skipped=False, reason="")

    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", fake_flush)
    monkeypatch.setattr(
        ship.push,
        "push_branch",
        lambda *_a, **_k: order.append("push") or ship.push.PushResult(remote="origin", attempts=1, status="pushed"),
    )
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
    monkeypatch.setattr(  # also patch the submodule binding used internally
        run_log_flush,
        "flush_logs_post",
        lambda *_a, **_k: order.append("flush-post") or run_logs.RefreshSkip(skipped=False, reason=""),
    )
    monkeypatch.setattr(ship.run_logs, "load_or_recover_manifest", lambda *_a, **_k: object())
    monkeypatch.setattr(ship.run_logs, "write_final_report_comment", lambda *_a, **_k: order.append("comment"))
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: order.append("state"))
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")

    result = ship.run_ship(_ctx(tmp_path), runner=RecordingRunner(), cwd=str(tmp_path))
    assert result.outcome is Outcome.OK
    # The guideline outcome flush runs before PR body composition. Post-ensure
    # remains push-only, so there is no strict post-ensure flush that would
    # re-trigger CI. The live PR URL is refreshed via the API-only "comment".
    assert order == [
        "flush-pre",
        "postbump",
        "flush-pre",
        "pr-body",
        "ensure-pr",
        "comment",
        "push",
        "monitor",
        "merge",
        "postmerge",
        "state",
        "flush-post",
    ]
    assert order.count("flush-pre") == 2
    assert order.count("monitor") == 1
    assert order.count("merge") == 1
    # Both pre-PR flushes are non-strict. The strict post-ensure flush is gone
    # (issue #5217).
    assert flush_args == [(None, str(tmp_path), False), (None, str(tmp_path), False)]
    captured = capsys.readouterr()
    assert "ship.py: pr-prep:" in captured.err
    assert "ship.py: pr-prep:" in captured.err
    assert "ship.py: pr-create:" in captured.err
    assert "ship.py: ci:" not in captured.err
    assert "ship.py: merge" in captured.err
    assert "ship.py: post-merge" in captured.err


def test_straight_merge_post_ensure_committed_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(ship, "_guidelines_gate_before_pr", lambda **_k: ship_guidelines.GuidelinesGateResult())
    monkeypatch.setattr(run_logs, "flush_logs_pre", _REAL_FLUSH_LOGS_PRE)
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", _REAL_FLUSH_LOGS_PRE)
    _ = (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=0\nRUN_ID=run-abc\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")
    _ = (tmp_path / "run-flags.sh").write_text("FORCE_REQUESTED=false\n", encoding="utf-8")
    _ = (tmp_path / "finalize-state.sh").write_text("", encoding="utf-8")
    ctx = _ctx(tmp_path)
    _ = run_logs.init_run(ctx)
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"

    def fake_token_fields(implement_tmpdir: Path, run_id: str) -> dict[str, object]:
        _ = (implement_tmpdir, run_id)
        return {"cost_unavailable": True}

    monkeypatch.setattr(final_report, "_final_report_token_fields", fake_token_fields)
    monkeypatch.setattr(run_logs, "_render_ledger_reports", lambda *_a, **_k: None)
    monkeypatch.setattr(run_logs, "capture_session_transcript", lambda *_a, **_k: None)
    monkeypatch.setattr(
        run_logs,
        "_commit_run",
        lambda *_a, **_k: CommandResult(("git", "commit"), 0, "a" * 40 + "\n", "", 0.0),
    )
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 12, "url": "https://example.test/pr/12", "status": "created"})(),
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
                "result": StepResult(Outcome.NEEDS_USER_INPUT, "ci-fix-exhausted: lint"),
                "action": "wait",
                "goto_rebase": False,
                "failed_run_id": None,
                "transient_rerun_attempted": False,
            },
            )(),
        )

    result = ship.run_ship(
        _ctx(tmp_path, state_file=str(tmp_path / "ship-pr-state.sh")),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    final_summary = (run_dir / "final-summary.md").read_text(encoding="utf-8")
    heading = final_summary.split(":", 1)[-1].split("\n", 1)[0].strip()
    assert heading in {"stalled", "bailed", "bailed-needs-user-input"}
    assert "pr-created" not in heading
    assert manifest["steps_ran"].get("step8") is True
    assert manifest.get("pr_number") == 12


def test_straight_merge_green_ci_single_pre_pr_flush(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(ship, "load_or_prepare_guidelines_note", lambda **_k: ship_guidelines.GuidelinesGateResult(guidelines_status="absent"))
    monkeypatch.setattr(run_logs, "flush_logs_pre", _REAL_FLUSH_LOGS_PRE)
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", _REAL_FLUSH_LOGS_PRE)
    _ = (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=0\nRUN_ID=run-abc\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")
    _ = (tmp_path / "run-flags.sh").write_text("FORCE_REQUESTED=false\n", encoding="utf-8")
    _ = (tmp_path / "finalize-state.sh").write_text("", encoding="utf-8")
    ctx = _ctx(tmp_path)
    _ = run_logs.init_run(ctx)
    flush_calls: list[bool] = []

    def fake_token_fields(implement_tmpdir: Path, run_id: str) -> dict[str, object]:
        _ = (implement_tmpdir, run_id)
        return {"cost_unavailable": True}

    monkeypatch.setattr(final_report, "_final_report_token_fields", fake_token_fields)
    monkeypatch.setattr(run_logs, "_render_ledger_reports", lambda *_a, **_k: None)
    monkeypatch.setattr(run_logs, "capture_session_transcript", lambda *_a, **_k: None)
    monkeypatch.setattr(
        run_logs,
        "_commit_run",
        lambda *_a, **_k: CommandResult(("git", "commit"), 0, "a" * 40 + "\n", "", 0.0),
    )

    real_flush = _REAL_FLUSH_LOGS_PRE

    def capturing_flush(
        *,
        runner: RecordingRunner,
        ctx: RunContext,
        cwd: str | None = None,
        strict_final_report: bool = False,
    ) -> run_logs.RefreshSkip:
        flush_calls.append(strict_final_report)
        return real_flush(runner=runner, ctx=ctx, cwd=cwd, strict_final_report=strict_final_report)

    monkeypatch.setattr(run_logs, "flush_logs_pre", capturing_flush)
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", capturing_flush)
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 12, "url": "https://example.test/pr/12", "status": "created"})(),
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
                "failed_run_id": None,
                "transient_rerun_attempted": False,
            },
        )(),
    )
    monkeypatch.setattr(
        ship.merge,
        "merge_pr",
        lambda *_a, **_k: type("MR", (), {"result": config.MERGE_RESULT_MERGED, "error": ""})(),
    )
    monkeypatch.setattr(
        ship.finalize,
        "postmerge",
        lambda *_a, **_k: type("PM", (), {"outcome": Outcome.OK, "detail": "", "status": "ok"})(),
    )
    monkeypatch.setattr(
        ship.run_logs,
        "flush_logs_post",
        lambda *_a, **_k: run_logs.RefreshSkip(skipped=False, reason=""),
    )
    monkeypatch.setattr(ship.run_logs, "load_or_recover_manifest", lambda *_a, **_k: object())
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(
        _ctx(tmp_path, state_file=str(tmp_path / "ship-pr-state.sh")),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.OK
    # The guideline outcome adds a second non-strict pre-PR flush. Post-ensure
    # remains push-only, so no strict post-ensure flush re-triggers CI.
    assert flush_calls == [False, False]


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



def _prepare_recovered_stalled_log(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    draft: bool = False,
) -> Path:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(run_logs, "flush_logs_pre", _REAL_FLUSH_LOGS_PRE)
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", _REAL_FLUSH_LOGS_PRE)
    _ = (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=0\nRUN_ID=run-abc\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")
    _ = (tmp_path / "run-flags.sh").write_text("FORCE_REQUESTED=false\n", encoding="utf-8")
    _ = (tmp_path / "finalize-state.sh").write_text(
        "STALL_TRACKING=true\nSTALL_STEP=5\nPHASE=stalled\nEXIT_CODE=4\n",
        encoding="utf-8",
    )
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        f"PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nPR_URL=https://example.test/pr/7\n"
        f"REPO=o/r\nMERGE=true\nDRAFT={'true' if draft else 'false'}\nSTALL_TRACKING=false\n",
        encoding="utf-8",
    )
    ctx = _ctx(tmp_path, state_file=str(state_file))
    _ = run_logs.init_run(ctx)
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _ = (run_dir / "final-summary.md").write_text(
        "## /implement run run-abc: stalled\n\n- **Outcome**: stalled\n- **PR**: #7\n",
        encoding="utf-8",
    )

    def fake_token_fields(implement_tmpdir: Path, run_id: str) -> dict[str, object]:
        _ = implement_tmpdir, run_id
        return {"cost_unavailable": True}

    def fake_commit(*_args: object, **_kwargs: object) -> CommandResult:
        return CommandResult(("git", "commit"), 0, "a" * 40 + "\n", "", 0.0)

    monkeypatch.setattr(final_report, "_final_report_token_fields", fake_token_fields)
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", lambda *_a, **_k: None)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", lambda *_a, **_k: None)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "_commit_run", fake_commit)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "_reconcile_terminal_manifest_from_ctx", lambda *_a, **_k: None)  # type: ignore[arg-type]
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: "abc123")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(
        ship_resume.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "existing"})(),
    )
    return state_file


def test_recovered_open_pr_premerge_reconciles_stalled_summary_before_merge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = _prepare_recovered_stalled_log(monkeypatch, tmp_path)
    merge_calls = {"count": 0}

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
                "transient_rerun_attempted": False,
                "failed_run_id": None,
            },
        )(),
    )

    def fake_merge(*_args: object, **_kwargs: object) -> object:
        merge_calls["count"] += 1
        return type("MR", (), {"result": config.MERGE_RESULT_MERGED, "error": ""})()

    monkeypatch.setattr(ship.merge, "merge_pr", fake_merge)
    monkeypatch.setattr(ship, "run_postmerge_phase", lambda *_a, **_k: ship.ShipResult(Outcome.OK))

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert merge_calls["count"] == 1
    text = (tmp_path / "larch-logs" / "implement" / "run-abc" / "final-summary.md").read_text(encoding="utf-8")
    assert ": pr-created" in text
    assert "- **Outcome**: stalled" not in text


def test_recovered_draft_pr_reconciles_stalled_summary_before_ok(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = _prepare_recovered_stalled_log(monkeypatch, tmp_path, draft=True)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    text = (tmp_path / "larch-logs" / "implement" / "run-abc" / "final-summary.md").read_text(encoding="utf-8")
    assert ": pr-created-draft" in text
    assert "- **Outcome**: stalled" not in text


def _init_git_repo(repo: Path) -> None:
    for argv in (
        ["git", "init", "-q"],
        ["git", "checkout", "-q", "-b", "feature"],
        ["git", "config", "user.email", "t@example.com"],
        ["git", "config", "user.name", "t"],
    ):
        _ = subprocess.run(argv, cwd=repo, check=True, capture_output=True)


def test_committed_summary_gate_reads_repo_not_corrected_tmpdir(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    session = tmp_path / "session"
    repo.mkdir()
    session.mkdir()
    _init_git_repo(repo)
    run_dir = repo / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    stalled = "## /implement run run-abc: stalled\n\n- **Outcome**: stalled\n- **PR**: #7\n"
    _ = (run_dir / "final-summary.md").write_text(stalled, encoding="utf-8")
    _ = subprocess.run(["git", "add", "larch-logs"], cwd=repo, check=True, capture_output=True)
    _ = subprocess.run(["git", "commit", "-q", "-m", "stalled log"], cwd=repo, check=True, capture_output=True)

    session_run_dir = session / "larch-logs" / "implement" / "run-abc"
    session_run_dir.mkdir(parents=True)
    corrected = "## /implement run run-abc: pr-created\n\n- **PR**: #7\n"
    _ = (session_run_dir / "final-summary.md").write_text(corrected, encoding="utf-8")

    ctx = make_run_context(
        run_id="run-abc",
        tmpdir=str(session),
        manifest_path=str(session / "manifest.json"),
    )

    assert ship_pr._committed_summary_heading_is_stalled(runner=ProcRunner(), ctx=ctx, cwd=str(repo))


def test_committed_summary_heading_scans_prelude() -> None:
    summary = "Prelude line\n\n## /implement run run-abc: stalled\n\n- **Outcome**: stalled\n"
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("git", "show", "HEAD:larch-logs/implement/run-abc/final-summary.md"),
                0,
                summary,
                "",
                0.0,
            ),
        ],
        strict=True,
    )
    ctx = make_run_context(run_id="run-abc", branch="")

    assert ship_pr._committed_summary_heading_is_stalled(runner=runner, ctx=ctx, cwd="/tmp/repo")


def test_committed_summary_heading_outcome_bullet_without_heading_is_not_stalled() -> None:
    summary = "Prelude line\n\n- **Outcome**: stalled\n"
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("git", "show", "HEAD:larch-logs/implement/run-abc/final-summary.md"),
                0,
                summary,
                "",
                0.0,
            ),
        ],
        strict=True,
    )
    ctx = make_run_context(run_id="run-abc", branch="")

    assert not ship_pr._committed_summary_heading_is_stalled(runner=runner, ctx=ctx, cwd="/tmp/repo")


def test_recovered_stalled_summary_push_failure_blocks_merge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = _prepare_recovered_stalled_log(monkeypatch, tmp_path)
    monkeypatch.setattr(ship, "_flush_guideline_outcome_before_pr", lambda *_a, **_k: None)
    merge_called = False

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
                "transient_rerun_attempted": False,
                "failed_run_id": None,
            },
        )(),
    )
    push_statuses = ["pushed", "failed"]

    def fake_push(*_args: object, **_kwargs: object) -> object:
        return ship.push.PushResult(remote="origin", attempts=1, status=push_statuses.pop(0))

    monkeypatch.setattr(ship.push, "push_branch", fake_push)

    def fake_merge(*_args: object, **_kwargs: object) -> object:
        nonlocal merge_called
        merge_called = True
        return type("MR", (), {"result": config.MERGE_RESULT_MERGED, "error": ""})()

    monkeypatch.setattr(ship.merge, "merge_pr", fake_merge)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert result.detail == "run-log reconciliation push failed: failed"
    assert not merge_called



def test_recovered_stalled_summary_push_exception_blocks_merge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = _prepare_recovered_stalled_log(monkeypatch, tmp_path)
    monkeypatch.setattr(ship, "_flush_guideline_outcome_before_pr", lambda *_a, **_k: None)
    merge_called = False

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
                "transient_rerun_attempted": False,
                "failed_run_id": None,
            },
        )(),
    )
    push_calls = {"count": 0}

    def fake_push(*_args: object, **_kwargs: object) -> object:
        push_calls["count"] += 1
        if push_calls["count"] == 1:
            return ship.push.PushResult(remote="origin", attempts=1, status="pushed")
        raise ShipError("network unavailable")

    def fake_merge(*_args: object, **_kwargs: object) -> object:
        nonlocal merge_called
        merge_called = True
        return type("MR", (), {"result": config.MERGE_RESULT_MERGED, "error": ""})()

    monkeypatch.setattr(ship.push, "push_branch", fake_push)
    monkeypatch.setattr(ship.merge, "merge_pr", fake_merge)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert result.detail == "run-log reconciliation push failed: network unavailable"
    assert not merge_called


def test_post_ensure_fresh_run_is_push_only_no_reflush(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A fresh run is push-only at post-ensure (issue #5217): it never performs the
    second strict final-report flush, so a flush skip that would once have stalled
    the run before the monitor can no longer occur. The single pre-PR flush carries
    the logs and the run proceeds to the monitor and merges.
    """
    strict_flush_called = False
    monitor_called = False

    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 5, "url": "https://example.test/pr/7", "status": "created"})(),
    )
    monkeypatch.setattr(ship.run_logs, "write_final_report_comment", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(ship.merge, "merge_pr", lambda *_a, **_k: type("MR", (), {"result": config.MERGE_RESULT_MERGED, "error": ""})())
    monkeypatch.setattr(ship.finalize, "postmerge", lambda *_a, **_k: type("PM", (), {"outcome": Outcome.OK, "detail": "", "status": "ok"})())
    monkeypatch.setattr(ship.run_logs, "flush_logs_post", lambda *_a, **_k: run_logs.RefreshSkip(skipped=False, reason=""))
    monkeypatch.setattr(ship.run_logs, "load_or_recover_manifest", lambda *_a, **_k: object())

    def fake_flush(
        *_a: object,
        strict_final_report: bool = False,
        **_k: object,
    ) -> run_logs.RefreshSkip:
        nonlocal strict_flush_called
        if strict_final_report:
            # If post-ensure still re-flushed, this critical skip would stall the
            # run before the monitor (the old issue #5186 / #5217 behavior).
            strict_flush_called = True
            return run_logs.RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_COMMIT_FAILED)
        return run_logs.RefreshSkip(skipped=False, reason="")

    def fake_monitor(*_a: object, **_k: object) -> object:
        nonlocal monitor_called
        monitor_called = True
        return type(
            "M",
            (),
            {
                "result": StepResult(Outcome.OK),
                "action": "merge",
                "goto_rebase": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
            },
        )()

    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", fake_flush)
    monkeypatch.setattr(ship.ci_monitor, "monitor", fake_monitor)

    result = ship.run_ship(_ctx(tmp_path), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert monitor_called
    assert not strict_flush_called


def test_post_ensure_push_failure_stalls_before_monitor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monitor_called = False

    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 5, "url": "https://example.test/pr/7", "status": "created"})(),
    )
    monkeypatch.setattr(ship.run_logs, "write_final_report_comment", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", lambda *_a, **_k: run_logs.RefreshSkip(skipped=False, reason=""))
    monkeypatch.setattr(
        ship.push,
        "push_branch",
        lambda *_a, **_k: ship.push.PushResult(remote="origin", attempts=3, status="failed"),
    )

    def fake_monitor(*_a: object, **_k: object) -> object:
        nonlocal monitor_called
        monitor_called = True
        return object()

    monkeypatch.setattr(ship.ci_monitor, "monitor", fake_monitor)

    result = ship.run_ship(_ctx(tmp_path), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert result.detail == "post-ensure-pr push failed: failed"
    assert not monitor_called


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
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: "abc123")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")

    def fake_ensure(*, runner: RecordingRunner, ctx: RunContext, body: str, **_kwargs: object) -> object:  # noqa: ARG001  # pylint: disable=unused-argument
        seen["ensure_branch"] = ctx.branch_name
        return type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "existing"})()

    def fake_monitor(*_args: object, **kwargs: object) -> object:
        seen["monitor"] = (
            kwargs["iteration"],
            kwargs["rebase_count"],
            kwargs["fix_attempts"],
        )
        return type(
            "M",
            (),
            {
                "result": StepResult(Outcome.STALLED, "ci-monitor"),
                "action": "wait",
                "goto_rebase": False,
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
    assert seen == {"ensure_branch": "feat", "monitor": (10, 3, 4)}
    state = state_file.read_text(encoding="utf-8")
    assert "BRANCH_NAME=feat\n" in state
    assert "ITERATION=10\n" in state
    assert "REBASE_COUNT=3\n" in state
    assert "FIX_ATTEMPTS=4\n" in state
    assert "TRANSIENT_RETRIES=1\n" in state


def _no_checks_loop_stubs(
    monkeypatch: pytest.MonkeyPatch,
    *,
    detail: str,
    flush_calls: list[bool],
    push_calls: list[bool],
    snapshot_calls: list[bool],
) -> None:
    """Wire an open-pr resume that bails from the monitor with ``detail``."""
    def recording_flush(*_args: object, **_kwargs: object) -> run_logs.RefreshSkip:
        flush_calls.append(True)
        return run_logs.RefreshSkip(skipped=False, reason="")

    def recording_push(*_args: object, **_kwargs: object) -> ship.push.PushResult:
        push_calls.append(True)
        return ship.push.PushResult(remote="origin", attempts=1, status="pushed")

    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: "h0")
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
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", recording_flush)
    monkeypatch.setattr(ship.push, "push_branch", recording_push)
    # Force a bounded empty-checks grace so a NO_CHECKS bail classifies as the
    # recoverable stall the loop fix targets, independent of git head routing.
    monkeypatch.setattr(
        ship,
        "_empty_checks_params_for_monitor",
        lambda **_k: (config.CI_WAIT_POST_FIX_EMPTY_CHECKS_GRACE_SEC, 0),
    )
    monkeypatch.setattr(
        ship,
        "_publish_post_pr_terminal_snapshot",
        lambda *_a, **_k: snapshot_calls.append(True),
    )
    monkeypatch.setattr(
        ship.ci_monitor,
        "monitor",
        lambda *_a, **_k: type(
            "M",
            (),
            {
                "result": StepResult(Outcome.STALLED, detail),
                "action": "bail",
                "goto_rebase": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
                "ci_fix_rebase_pending": False,
            },
        )(),
    )
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)


def test_open_pr_resume_no_checks_stall_keeps_head_stable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The no-ci-checks-observed loop is broken by holding HEAD steady (#5186).

    On open-pr resume the post-ensure-pr re-flush is skipped, and on a
    no-ci-checks-observed bail the terminal snapshot is skipped. Both sites
    otherwise commit this invocation's own log churn and push it, moving HEAD and
    re-triggering CI on every retry. With both skipped, no flush runs and only the
    idempotent reconcile push is issued, so CI converges on a stable head.
    First-time (fresh) flush is unaffected and is covered by
    test_straight_merge_post_ensure_green_ci_committed_snapshot.
    """
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\n"
        "PR_URL=https://example.test/pr/7\nREPO=o/r\nRUN_ID=run-abc\nMERGE=true\nDRAFT=false\nITERATION=4\n",
        encoding="utf-8",
    )
    flush_calls: list[bool] = []
    push_calls: list[bool] = []
    snapshot_calls: list[bool] = []
    _no_checks_loop_stubs(
        monkeypatch,
        detail=config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED,
        flush_calls=flush_calls,
        push_calls=push_calls,
        snapshot_calls=snapshot_calls,
    )

    result = ship.run_ship(
        _ctx(tmp_path, branch="feat", branch_name="feat", state_file=str(state_file)),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.STALLED
    assert result.detail == config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED
    # One pre-PR guideline-outcome flush runs before ensure_pr. The post-ensure
    # re-flush is skipped on resume, and the terminal snapshot is skipped on the
    # recoverable NO_CHECKS bail, so HEAD advances at most once (outcome sidecar).
    assert flush_calls == [True]
    assert not snapshot_calls
    # Only the idempotent reconcile push is issued.
    assert push_calls == [True]


def test_no_checks_dirty_pr_writes_phase14_reship_flag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\n"
        "PR_URL=https://example.test/pr/7\nMERGE=true\nDRAFT=false\nITERATION=4\n",
        encoding="utf-8",
    )
    flush_calls: list[bool] = []
    push_calls: list[bool] = []
    snapshot_calls: list[bool] = []
    _no_checks_loop_stubs(
        monkeypatch,
        detail=config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED,
        flush_calls=flush_calls,
        push_calls=push_calls,
        snapshot_calls=snapshot_calls,
    )
    monkeypatch.setattr(
        ship.gh,
        "pr_merge_state_read",
        lambda *_a, **_k: CommandResult(
            ("gh", "pr", "view"),
            0,
            '{"mergeStateStatus":"DIRTY","headRefOid":"h0"}',
            "",
            0.01,
        ),
    )

    result = ship.run_ship(
        _ctx(tmp_path, branch="feat", branch_name="feat", state_file=str(state_file)),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.STALLED
    phase14 = tmp_path / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME
    assert phase14.is_file()
    flag_text = phase14.read_text(encoding="utf-8")
    assert f"RESUME_PHASE={config.SHIP_PR_RRR_RESUME_PHASE}\n" in flag_text
    assert "REASON=mergeStateStatus=DIRTY\n" in flag_text


def test_non_no_checks_bail_still_publishes_terminal_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A genuinely terminal bail still publishes the snapshot (guard for #5186).

    The snapshot is only suppressed for the recoverable no-ci-checks-observed
    stall; other terminal bails must still flush and push the final run logs.
    """
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\n"
        "PR_URL=https://example.test/pr/7\nMERGE=true\nDRAFT=false\nITERATION=4\n",
        encoding="utf-8",
    )
    flush_calls: list[bool] = []
    push_calls: list[bool] = []
    snapshot_calls: list[bool] = []
    _no_checks_loop_stubs(
        monkeypatch,
        detail="ci-monitor",
        flush_calls=flush_calls,
        push_calls=push_calls,
        snapshot_calls=snapshot_calls,
    )

    result = ship.run_ship(
        _ctx(tmp_path, branch="feat", branch_name="feat", state_file=str(state_file)),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.STALLED
    # Terminal snapshot still published for a non-NO_CHECKS bail.
    assert snapshot_calls == [True]


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


def test_merged_resume_writes_postmerge_phase_before_postmerge_helper(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nPR_URL=https://example.test/pr/7\n"
        "MERGE=true\nDRAFT=false\nITERATION=4\n",
        encoding="utf-8",
    )
    events: list[str] = []
    original_write = ship._write_ship_state  # pyright: ignore[reportPrivateUsage]
    original_postmerge = ship._ship_postmerge_phase  # pyright: ignore[reportPrivateUsage]

    def observe_write(ctx: RunContext, **kwargs: object) -> None:
        if kwargs.get("phase") == "postmerge":
            events.append("postmerge_write")
        original_write(ctx, **kwargs)  # type: ignore[arg-type]

    def observe_postmerge(*args: object, **kwargs: object) -> ship.ShipResult:
        events.append("postmerge_invoke")
        return original_postmerge(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "MERGED", "head_ref": "stale-head"})(),
    )
    monkeypatch.setattr(ship, "_write_ship_state", observe_write)
    monkeypatch.setattr(ship, "_ship_postmerge_phase", observe_postmerge)
    monkeypatch.setattr(ship, "run_postmerge_phase", lambda *_a, **_k: ship.ShipResult(Outcome.OK, detail="postmerge"))

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert events.index("postmerge_write") < events.index("postmerge_invoke")


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
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: "abc123")
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
            {"result": StepResult(Outcome.OK), "action": "merge", "goto_rebase": False, "transient_rerun_attempted": False, "failed_run_id": None},
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
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: "abc123")
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
    _ = flag.write_text(
        f"RESUME_PHASE={config.SHIP_PR_RRR_RESUME_PHASE}\nREASON=mergeStateStatus=DIRTY\n",
        encoding="utf-8",
    )
    _ = state_file.write_text(
        f"PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=true\nDRAFT=false\n"
        f"RESUME_PHASE={config.SHIP_PR_RRR_RESUME_PHASE}\n"
        f"CALLER_KIND={config.SHIP_PR_PRE_PUSH_CALLER_KIND}\n"
        "CONFLICT_FILES=a.txt\n",
        encoding="utf-8",
    )
    _open_pr_merge_loop_stubs(monkeypatch)
    rebase_calls: list[bool] = []

    def fake_rebase(*_args: object, **_kwargs: object) -> ship.rebase.RebaseResult:
        rebase_calls.append(True)
        return _successful_rebase_result()

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
    _ = flag.write_text(
        f"RESUME_PHASE={config.SHIP_PR_RRR_RESUME_PHASE}\nREASON=mergeStateStatus=DIRTY\n",
        encoding="utf-8",
    )
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

    def fake_rebase(*_args: object, **_kwargs: object) -> ship.rebase.RebaseResult:
        rebase_calls.append(True)
        return _successful_rebase_result()

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


def test_terminal_counter_persistence_keeps_failed_fix_attempts(
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
                "transient_rerun_attempted": False,
                "failed_run_id": "99",
            },
        )(),
    )
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert "FIX_ATTEMPTS=4\n" in state_file.read_text(encoding="utf-8")


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
                "transient_rerun_attempted": True,
                "failed_run_id": None,
            },
        )(),
    )
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.TRANSIENT
    assert "TRANSIENT_RETRIES=3\n" in state_file.read_text(encoding="utf-8")


@pytest.mark.parametrize(("expected_session_id", "expected_outcome"), [("session", Outcome.TRANSIENT), ("", Outcome.STALLED)])
def test_fourth_transient_cap_only_stalls_standalone_runs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    expected_session_id: str,
    expected_outcome: Outcome,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nTRANSIENT_RETRIES=3\nMERGE=true\nDRAFT=false\n",
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
                "transient_rerun_attempted": True,
                "failed_run_id": "77",
            },
        )(),
    )
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(
        _ctx(tmp_path, state_file=str(state_file), expected_session_id=expected_session_id),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is expected_outcome
    assert "TRANSIENT_RETRIES=4\n" in state_file.read_text(encoding="utf-8")


def test_patch_ship_state_keys_preserves_existing_allowed_keys(tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nPR_NUMBER=7\nRESUME_PHASE=ship-pr-rrr-phase14\nOOS_PENDING=true\nUNKNOWN=drop\n",
        encoding="utf-8",
    )

    ship._patch_ship_state_keys(state_file=state_file, patch={"OOS_PENDING": "false"})  # pyright: ignore[reportPrivateUsage]

    state = state_file.read_text(encoding="utf-8")
    assert "PHASE=ci-initial\n" in state
    assert "PR_NUMBER=7\n" in state
    assert "RESUME_PHASE=ship-pr-rrr-phase14\n" in state
    assert "OOS_PENDING=false\n" in state
    assert "UNKNOWN=drop\n" not in state


def test_patch_ship_state_keys_rejects_missing_or_empty_state(tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"

    with pytest.raises(ship.ShipError, match="refusing patch-only ship state write"):
        ship._patch_ship_state_keys(state_file=state_file, patch={"OOS_PENDING": "false"})  # pyright: ignore[reportPrivateUsage]

    _ = state_file.write_text("\n", encoding="utf-8")
    with pytest.raises(ship.ShipError, match="refusing patch-only ship state write"):
        ship._patch_ship_state_keys(state_file=state_file, patch={"OOS_PENDING": "false"})  # pyright: ignore[reportPrivateUsage]


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
    assert seen == [4, 4]
    assert "FIX_ATTEMPTS=4\n" in state_file.read_text(encoding="utf-8")


def test_post_push_reentry_uses_bounded_empty_checks_grace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """After a head-changing CI-fix push, the merge loop re-enters monitor with the
    full poll-based startup deadline so a missing fresh CI run surfaces as a
    recoverable stall instead of polling the full budget (issue #4867). A
    force-pushed / CI-fix head gets the same generous check-registration window as
    a brand-new PR head rather than the shorter 120s grace that caused false
    no-ci-checks-observed stalls (issue #5217).
    """
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nMERGE=true\nDRAFT=false\n",
        encoding="utf-8",
    )
    seen_params: list[tuple[int, int]] = []
    head = {"sha": "h0"}
    results: list[dict[str, object]] = [
        {
            "result": StepResult(Outcome.OK),
            "action": "evaluate_failure",
            "goto_rebase": False,
            "transient_rerun_attempted": False,
            "failed_run_id": "99",
            "ci_fix_rebase_pending": False,
            "advance_head": True,
        },
        {
            "result": StepResult(Outcome.STALLED, config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED),
            "action": "bail",
            "goto_rebase": False,
            "transient_rerun_attempted": False,
            "failed_run_id": None,
            "ci_fix_rebase_pending": False,
        },
    ]

    def fake_rev_parse(*_a: object, **_k: object) -> str:
        return head["sha"]

    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(ship.git, "try_rev_parse", fake_rev_parse)
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
        grace = kwargs.get("empty_checks_grace")
        startup_deadline = kwargs.get("empty_checks_startup_deadline_sec")
        assert isinstance(grace, int)
        assert isinstance(startup_deadline, int)
        seen_params.append((grace, startup_deadline))
        spec = results.pop(0)
        if spec.pop("advance_head", False):
            head["sha"] = "h1"  # the CI-fix push advanced HEAD
        return type("M", (), spec)()

    monkeypatch.setattr(ship.ci_monitor, "monitor", monitor)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert seen_params == [
        (0, config.CI_WAIT_INITIAL_EMPTY_CHECKS_GRACE_SEC),
        (0, config.CI_WAIT_INITIAL_EMPTY_CHECKS_GRACE_SEC),
    ]
    assert _read_state(state_file)["LAST_MONITORED_HEAD"] == "h0"


def test_initial_ci_wait_uses_poll_based_startup_deadline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nMERGE=true\nDRAFT=false\n",
        encoding="utf-8",
    )
    seen_params: list[tuple[int, int]] = []

    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: "h0")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type(
            "PR",
            (),
            {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"},
        )(),
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type(
            "P",
            (),
            {"number": 7, "url": "https://example.test/pr/7", "status": "existing"},
        )(),
    )

    def monitor(*_args: object, **kwargs: object) -> object:
        grace = kwargs.get("empty_checks_grace")
        startup_deadline = kwargs.get("empty_checks_startup_deadline_sec")
        assert isinstance(grace, int)
        assert isinstance(startup_deadline, int)
        seen_params.append((grace, startup_deadline))
        return type(
            "M",
            (),
            {
                "result": StepResult(Outcome.STALLED, config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED),
                "action": "bail",
                "goto_rebase": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
                "ci_fix_rebase_pending": False,
            },
        )()

    monkeypatch.setattr(ship.ci_monitor, "monitor", monitor)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))
    state = _read_state(state_file)

    assert result.outcome is Outcome.STALLED
    assert result.detail == config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED
    assert seen_params == [(0, config.CI_WAIT_INITIAL_EMPTY_CHECKS_GRACE_SEC)]
    assert state["PHASE"] == "stalled"
    assert state["STALL_STEP"] == config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED
    assert state["LAST_MONITORED_HEAD"] == "h0"


def test_initial_startup_deadline_cleared_after_first_monitor_ok(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nMERGE=true\nDRAFT=false\n",
        encoding="utf-8",
    )
    seen_params: list[tuple[int, int]] = []
    results: list[dict[str, object]] = [
        {
            "result": StepResult(Outcome.OK),
            "action": "evaluate_failure",
            "goto_rebase": False,
            "transient_rerun_attempted": False,
            "failed_run_id": "99",
            "ci_fix_rebase_pending": False,
            "advance_head": True,
        },
        {
            "result": StepResult(Outcome.STALLED, config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED),
            "action": "bail",
            "goto_rebase": False,
            "transient_rerun_attempted": False,
            "failed_run_id": None,
            "ci_fix_rebase_pending": False,
        },
    ]

    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: "h0")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type(
            "PR",
            (),
            {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"},
        )(),
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type(
            "P",
            (),
            {"number": 7, "url": "https://example.test/pr/7", "status": "existing"},
        )(),
    )

    def monitor(*_args: object, **kwargs: object) -> object:
        grace = kwargs.get("empty_checks_grace")
        startup_deadline = kwargs.get("empty_checks_startup_deadline_sec")
        assert isinstance(grace, int)
        assert isinstance(startup_deadline, int)
        seen_params.append((grace, startup_deadline))
        return type("M", (), results.pop(0))()

    monkeypatch.setattr(ship.ci_monitor, "monitor", monitor)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert seen_params == [(0, config.CI_WAIT_INITIAL_EMPTY_CHECKS_GRACE_SEC), (0, 0)]


def test_cold_resume_zero_counters_still_gets_initial_startup_deadline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nMERGE=true\nDRAFT=false\n"
        "LAST_MONITORED_HEAD=h0\n",
        encoding="utf-8",
    )
    seen_params: list[tuple[int, int]] = []

    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: "h0")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type(
            "PR",
            (),
            {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"},
        )(),
    )
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type(
            "P",
            (),
            {"number": 7, "url": "https://example.test/pr/7", "status": "existing"},
        )(),
    )

    def monitor(*_args: object, **kwargs: object) -> object:
        grace = kwargs.get("empty_checks_grace")
        startup_deadline = kwargs.get("empty_checks_startup_deadline_sec")
        assert isinstance(grace, int)
        assert isinstance(startup_deadline, int)
        seen_params.append((grace, startup_deadline))
        return type(
            "M",
            (),
            {
                "result": StepResult(Outcome.STALLED, config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED),
                "action": "bail",
                "goto_rebase": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
                "ci_fix_rebase_pending": False,
            },
        )()

    monkeypatch.setattr(ship.ci_monitor, "monitor", monitor)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert seen_params == [(0, config.CI_WAIT_INITIAL_EMPTY_CHECKS_GRACE_SEC)]


def test_post_push_resume_rehydrates_empty_checks_grace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Cold resume after a CI-fix push uses the full poll-based startup deadline (issue #5217)."""
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nMERGE=true\nDRAFT=false\n"
        "FIX_ATTEMPTS=1\nLAST_MONITORED_HEAD=h0\n",
        encoding="utf-8",
    )
    seen_params: list[tuple[int, int]] = []
    head = {"sha": "h1"}

    def fake_rev_parse(*_a: object, **_k: object) -> str:
        return head["sha"]

    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(ship.git, "try_rev_parse", fake_rev_parse)
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
        grace = kwargs.get("empty_checks_grace")
        startup_deadline = kwargs.get("empty_checks_startup_deadline_sec")
        assert isinstance(grace, int)
        assert isinstance(startup_deadline, int)
        seen_params.append((grace, startup_deadline))
        return type(
            "M",
            (),
            {
                "result": StepResult(Outcome.STALLED, config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED),
                "action": "bail",
                "goto_rebase": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
                "ci_fix_rebase_pending": False,
            },
        )()

    monkeypatch.setattr(ship.ci_monitor, "monitor", monitor)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert seen_params == [(0, config.CI_WAIT_INITIAL_EMPTY_CHECKS_GRACE_SEC)]


def test_post_push_resume_missing_last_monitored_head_uses_grace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Cold resume after CI-fix push with FIX_ATTEMPTS but no LAST_MONITORED_HEAD."""
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nMERGE=true\nDRAFT=false\n"
        "FIX_ATTEMPTS=1\n",
        encoding="utf-8",
    )
    seen_params: list[tuple[int, int]] = []
    head = {"sha": "h1"}

    def fake_rev_parse(*_a: object, **_k: object) -> str:
        return head["sha"]

    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(ship.git, "try_rev_parse", fake_rev_parse)
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
        grace = kwargs.get("empty_checks_grace")
        startup_deadline = kwargs.get("empty_checks_startup_deadline_sec")
        assert isinstance(grace, int)
        assert isinstance(startup_deadline, int)
        seen_params.append((grace, startup_deadline))
        return type(
            "M",
            (),
            {
                "result": StepResult(Outcome.STALLED, config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED),
                "action": "bail",
                "goto_rebase": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
                "ci_fix_rebase_pending": False,
            },
        )()

    monkeypatch.setattr(ship.ci_monitor, "monitor", monitor)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert seen_params == [(0, config.CI_WAIT_INITIAL_EMPTY_CHECKS_GRACE_SEC)]


def test_post_push_resume_synced_head_uses_grace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Resume when LAST_MONITORED_HEAD already equals post-fix HEAD still gets the bounded startup deadline (issue #5217)."""
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nMERGE=true\nDRAFT=false\n"
        "FIX_ATTEMPTS=1\nLAST_MONITORED_HEAD=h1\n",
        encoding="utf-8",
    )
    seen_params: list[tuple[int, int]] = []
    head = {"sha": "h1"}

    def fake_rev_parse(*_a: object, **_k: object) -> str:
        return head["sha"]

    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(ship.git, "try_rev_parse", fake_rev_parse)
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
        grace = kwargs.get("empty_checks_grace")
        startup_deadline = kwargs.get("empty_checks_startup_deadline_sec")
        assert isinstance(grace, int)
        assert isinstance(startup_deadline, int)
        seen_params.append((grace, startup_deadline))
        return type(
            "M",
            (),
            {
                "result": StepResult(Outcome.STALLED, config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED),
                "action": "bail",
                "goto_rebase": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
                "ci_fix_rebase_pending": False,
            },
        )()

    monkeypatch.setattr(ship.ci_monitor, "monitor", monitor)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert seen_params == [(0, config.CI_WAIT_INITIAL_EMPTY_CHECKS_GRACE_SEC)]


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


def _force_recovered_reconciliation_post_merge_skip(monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    flush_calls: list[bool] = []

    def fake_committed_summary_heading_is_stalled(**_kwargs: object) -> bool:
        return True

    def fake_live_recovered_outcome(_ctx: RunContext) -> str:
        return "merged"

    def fake_flush_logs_pre(**kwargs: object) -> run_logs.RefreshSkip:
        flush_calls.append(bool(kwargs.get("strict_final_report")))
        return run_logs.RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_POST_MERGE)

    monkeypatch.setattr(
        ship_pr,
        "_committed_summary_heading_is_stalled",
        fake_committed_summary_heading_is_stalled,
    )
    monkeypatch.setattr(ship_pr, "_live_recovered_outcome", fake_live_recovered_outcome)
    monkeypatch.setattr(ship_pr.run_logs, "flush_logs_pre", fake_flush_logs_pre)
    return flush_calls


def _merged_pr_view() -> object:
    return type(
        "PR",
        (),
        {
            "number": 7,
            "url": "https://example.test/pr/7",
            "state": "MERGED",
            "head_ref": "feat",
        },
    )()


def test_done_resume_post_merge_reconciliation_skip_falls_through_to_done(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=done\nBRANCH_NAME=feat\nPR_NUMBER=7\nPR_URL=https://example.test/pr/7\n"
        "REPO=o/r\nMERGE=true\nDRAFT=false\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: _merged_pr_view(),
    )
    monkeypatch.setattr(
        ship.finalize,
        "postmerge",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("postmerge forbidden")),
    )
    flush_calls = _force_recovered_reconciliation_post_merge_skip(monkeypatch)

    result = ship.run_ship(
        _ctx(tmp_path, state_file=str(state_file)),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    state = state_file.read_text(encoding="utf-8")
    assert result.outcome is Outcome.OK
    assert result.detail == "already done"
    assert flush_calls == [True]
    assert "PHASE=done\n" in state
    assert "PHASE=stalled\n" not in state
    assert "STALL_STEP=run-log-reconciliation\n" not in state


def test_merged_resume_post_merge_reconciliation_skip_continues_postmerge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=postmerge\nBRANCH_NAME=feat\nPR_NUMBER=7\nPR_URL=https://example.test/pr/7\n"
        "REPO=o/r\nMERGE=true\nDRAFT=false\nMERGE_RESULT=merged\n",
        encoding="utf-8",
    )
    postmerge_calls: list[bool] = []
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: _merged_pr_view(),
    )
    monkeypatch.setattr(
        ship,
        "run_postmerge_phase",
        lambda *_a, **_k: postmerge_calls.append(True)
        or ship.ShipResult(Outcome.OK, detail="postmerge"),
    )
    flush_calls = _force_recovered_reconciliation_post_merge_skip(monkeypatch)

    result = ship.run_ship(
        _ctx(tmp_path, state_file=str(state_file)),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    state = state_file.read_text(encoding="utf-8")
    assert result.outcome is Outcome.OK
    assert result.detail == "postmerge"
    assert flush_calls == [True]
    assert postmerge_calls == [True]
    assert "PHASE=done\n" in state
    assert "PHASE=stalled\n" not in state
    assert "STALL_STEP=run-log-reconciliation\n" not in state


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


def test_monitor_ok_result_does_not_consume_iteration_or_fix_attempt(
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
    assert "FIX_ATTEMPTS=0\n" in state


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


def test_admin_fallback_ci_not_ready_ignores_review_required_until_ci_settles(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=true\nDRAFT=false\n",
        encoding="utf-8",
    )
    _open_pr_merge_loop_stubs(monkeypatch)
    merge_results = [
        config.MERGE_RESULT_CI_NOT_READY,
        config.MERGE_RESULT_DRIVER_ALREADY_MERGED,
    ]

    def monitor(*_args: object, **_kwargs: object) -> object:
        return type(
            "M",
            (),
            {
                "result": StepResult(Outcome.OK),
                "action": "merge",
                "goto_rebase": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
            },
        )()

    def merge_pr(*_args: object, **_kwargs: object) -> object:
        return type("MR", (), {"result": merge_results.pop(0), "error": "CI checks are not all passing"})()

    def review_decision(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("reviewDecision must not route CI_NOT_READY while admin fallback is enabled")

    monkeypatch.setattr(ship.ci_monitor, "monitor", monitor)
    monkeypatch.setattr(ship.merge, "merge_pr", merge_pr)
    monkeypatch.setattr(ship.gh, "pr_review_decision", review_decision)
    monkeypatch.setattr(
        ship.gh,
        "pr_checks_not_ready_detail",
        lambda *_a, **_k: "blocking checks: lint=pending",
    )
    monkeypatch.setattr(ship, "run_postmerge_phase", lambda *_a, **_k: ship.ShipResult(Outcome.OK))

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert result.needs_user_reason != config.NEEDS_USER_REVIEW_REQUIRED
    assert not merge_results


def test_no_admin_fallback_ci_not_ready_review_required_reports_observed_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=true\n"
        "DRAFT=false\nNO_ADMIN_FALLBACK=true\n",
        encoding="utf-8",
    )
    _open_pr_merge_loop_stubs(monkeypatch)

    def monitor(*_args: object, **_kwargs: object) -> object:
        return type(
            "M",
            (),
            {
                "result": StepResult(Outcome.OK),
                "action": "merge",
                "goto_rebase": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
            },
        )()

    def merge_pr(*_args: object, **_kwargs: object) -> object:
        return type(
            "MR",
            (),
            {"result": config.MERGE_RESULT_CI_NOT_READY, "error": "CI checks are not all passing"},
        )()

    def checks_not_ready_detail(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("review-required CI_NOT_READY should not enter the CI wait handler")

    monkeypatch.setattr(ship.ci_monitor, "monitor", monitor)
    monkeypatch.setattr(ship.merge, "merge_pr", merge_pr)
    monkeypatch.setattr(ship.gh, "pr_review_decision", lambda *_a, **_k: "REVIEW_REQUIRED")
    monkeypatch.setattr(
        ship.gh,
        "pr_merge_state",
        lambda *_a, **_k: ship.gh.MergeState(merge_state_status="UNKNOWN", head_ref_oid="h0"),
    )
    monkeypatch.setattr(ship.gh, "pr_checks_not_ready_detail", checks_not_ready_detail)

    result = ship.run_ship(
        _ctx(tmp_path, state_file=str(state_file), no_admin_fallback=True),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == config.NEEDS_USER_REVIEW_REQUIRED
    assert "mergeStateStatus=UNKNOWN" in (result.detail or "")
    assert "mergeStateStatus=BLOCKED" not in (result.detail or "")


def test_repeated_ci_not_ready_stalls_with_check_detail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=true\nDRAFT=false\n",
        encoding="utf-8",
    )
    _open_pr_merge_loop_stubs(monkeypatch)
    monkeypatch.setattr(config, "SHIP_MERGE_CI_NOT_READY_STALL_THRESHOLD", 2)

    def monitor(*_args: object, **_kwargs: object) -> object:
        return type(
            "M",
            (),
            {
                "result": StepResult(Outcome.OK),
                "action": "merge",
                "goto_rebase": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
            },
        )()

    def merge_pr(*_args: object, **_kwargs: object) -> object:
        return type("MR", (), {"result": config.MERGE_RESULT_CI_NOT_READY, "error": ""})()

    def review_decision(*_args: object, **_kwargs: object) -> str:
        return "APPROVED"

    def not_ready_detail(*_args: object, **_kwargs: object) -> str:
        return "blocking checks: lint=pending"

    monkeypatch.setattr(ship.ci_monitor, "monitor", monitor)
    monkeypatch.setattr(ship.merge, "merge_pr", merge_pr)
    monkeypatch.setattr(ship.gh, "pr_review_decision", review_decision)
    monkeypatch.setattr(ship.gh, "pr_checks_not_ready_detail", not_ready_detail)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    state = state_file.read_text(encoding="utf-8")
    assert result.outcome is Outcome.STALLED
    assert "lint=pending" in (result.detail or "")
    assert "STALL_STEP=merge-ci-not-ready\n" in state
    assert "ITERATION=2\n" in state


def test_race_ci_not_ready_detail_does_not_stall(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=true\nDRAFT=false\n",
        encoding="utf-8",
    )
    _open_pr_merge_loop_stubs(monkeypatch)
    monkeypatch.setattr(config, "SHIP_MERGE_CI_NOT_READY_STALL_THRESHOLD", 2)
    merge_results = [
        config.MERGE_RESULT_CI_NOT_READY,
        config.MERGE_RESULT_CI_NOT_READY,
        config.MERGE_RESULT_DRIVER_ALREADY_MERGED,
    ]

    def monitor(*_args: object, **_kwargs: object) -> object:
        return type(
            "M",
            (),
            {
                "result": StepResult(Outcome.OK),
                "action": "merge",
                "goto_rebase": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
            },
        )()

    def merge_pr(*_args: object, **_kwargs: object) -> object:
        return type("MR", (), {"result": merge_results.pop(0), "error": ""})()

    def review_decision(*_args: object, **_kwargs: object) -> str:
        return "APPROVED"

    def not_ready_detail(*_args: object, **_kwargs: object) -> str:
        return "no fail or pending PR checks remain"

    monkeypatch.setattr(ship.ci_monitor, "monitor", monitor)
    monkeypatch.setattr(ship.merge, "merge_pr", merge_pr)

    def run_postmerge_phase(*_args: object, **_kwargs: object) -> ship.ShipResult:
        return ship.ShipResult(Outcome.OK)

    monkeypatch.setattr(ship.gh, "pr_review_decision", review_decision)
    monkeypatch.setattr(ship.gh, "pr_checks_not_ready_detail", not_ready_detail)
    monkeypatch.setattr(ship, "run_postmerge_phase", run_postmerge_phase)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert not merge_results


def test_changed_ci_not_ready_detail_resets_stall_guard(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nREPO=o/r\nMERGE=true\nDRAFT=false\n",
        encoding="utf-8",
    )
    _open_pr_merge_loop_stubs(monkeypatch)
    monkeypatch.setattr(config, "SHIP_MERGE_CI_NOT_READY_STALL_THRESHOLD", 2)
    merge_results = [
        config.MERGE_RESULT_CI_NOT_READY,
        config.MERGE_RESULT_CI_NOT_READY,
        config.MERGE_RESULT_DRIVER_ALREADY_MERGED,
    ]
    details = ["blocking checks: lint=pending", "blocking checks: unit=pending"]

    def monitor(*_args: object, **_kwargs: object) -> object:
        return type(
            "M",
            (),
            {
                "result": StepResult(Outcome.OK),
                "action": "merge",
                "goto_rebase": False,
                "transient_rerun_attempted": False,
                "failed_run_id": None,
            },
        )()

    def merge_pr(*_args: object, **_kwargs: object) -> object:
        return type("MR", (), {"result": merge_results.pop(0), "error": ""})()

    def review_decision(*_args: object, **_kwargs: object) -> str:
        return "APPROVED"

    def not_ready_detail(*_args: object, **_kwargs: object) -> str:
        return details.pop(0)

    monkeypatch.setattr(ship.ci_monitor, "monitor", monitor)
    monkeypatch.setattr(ship.merge, "merge_pr", merge_pr)

    def run_postmerge_phase(*_args: object, **_kwargs: object) -> ship.ShipResult:
        return ship.ShipResult(Outcome.OK)

    monkeypatch.setattr(ship.gh, "pr_review_decision", review_decision)
    monkeypatch.setattr(ship.gh, "pr_checks_not_ready_detail", not_ready_detail)
    monkeypatch.setattr(ship, "run_postmerge_phase", run_postmerge_phase)

    result = ship.run_ship(_ctx(tmp_path, state_file=str(state_file)), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert not merge_results
    assert not details


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
                "transient_rerun_attempted": False,
                "failed_run_id": None,
            },
        )(),
    )

    def fake_rebase(*_args: object, **_kwargs: object) -> ship.rebase.RebaseResult:
        order.append("rebase")
        return _successful_rebase_result()

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
    ship.emit_result(
        ctx=ctx,
        result=ship.ShipResult(
            Outcome.OK,
            pr_number=2,
            pr_url="u",
            main_health_head_sha="abc123",
            main_health_repair_failed_run_id="44",
            main_health_repair_base_sha="abc123",
            main_health_repair_head="abc123",
            original_branch_forbidden="true",
            main_repair_run_id="44",
            main_repair_head="abc123",
        ),
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["outcome"] == "OK"
    assert payload["pr_number"] == 2
    assert payload["main_health_head_sha"] == "abc123"
    assert payload["main_health_repair_base_sha"] == "abc123"
    assert payload["original_branch_forbidden"] == "true"


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
        ship._breadcrumb(step="checks", detail="Lint&Tests")  # pyright: ignore[reportPrivateUsage]
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

    def observe_postmerge(*, runner: RecordingRunner, ctx: RunContext, **_kwargs: object) -> object:  # noqa: ARG001  # pylint: disable=unused-argument
        assert (Path(ctx.tmpdir) / "post-merge-sentinel").is_file()
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
    result = ship.run_postmerge_phase(runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path))
    assert result.outcome is Outcome.OK


def test_ship_postmerge_push_watch_routes_failure_to_emergency_repair(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    ctx = _ctx(
        tmp_path,
        state_file=str(state_file),
        pr_number=5,
        pr_url="https://example.com/pr/5",
        pr_closed=True,
        merge_result=config.MERGE_RESULT_MERGED,
    )
    _ = (tmp_path / "main-health.env").write_text("MAIN_CI_STATUS=pass\n", encoding="utf-8")

    def fail_if_postmerge_runs(*_args: object, **_kwargs: object) -> ship.ShipResult:
        raise AssertionError("postmerge finalize must wait for merged-SHA push CI")

    monkeypatch.setattr(ship, "run_postmerge_phase", fail_if_postmerge_runs)
    monkeypatch.setattr(
        ship.main_health,
        "wait_main_health",
        lambda *_a, **_k: ship.main_health.MainHealthWaitResult(
            health=ship.main_health.MainHealthStatus(
                status="fail",
                failed_run_id="44",
                head_sha="abc123",
                detail="merged push failed",
            ),
            elapsed_seconds=1,
            attempts=1,
        ),
    )

    result = ship._ship_postmerge_phase(  # pyright: ignore[reportPrivateUsage]
        runner=RecordingRunner(),
        working=ctx,
        cwd=str(tmp_path),
        iteration=1,
        rebase_count=2,
        fix_attempts=3,
        transient_retries=4,
    )

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == config.NEEDS_USER_POSTMERGE_MAIN_CI_FAIL
    assert result.failed_run_id == "44"
    assert result.main_health_head_sha == "abc123"
    assert result.main_health_repair_committed == "false"
    assert result.main_health_repair_base_sha == "abc123"
    assert result.main_repair_run_id == "44"
    assert result.original_branch_forbidden == "true"
    state = _read_state(state_file)
    assert state["PHASE"] == "emergency-repair"
    assert state["ORIGINAL_BRANCH_FORBIDDEN"] == "true"
    assert state["MAIN_REPAIR_RUN_ID"] == "44"
    assert not (tmp_path / "post-merge-sentinel").exists()


def test_ship_postmerge_push_watch_passes_before_finalize(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    ctx = _ctx(
        tmp_path,
        state_file=str(state_file),
        pr_number=5,
        pr_url="https://example.com/pr/5",
        pr_closed=True,
        merge_result=config.MERGE_RESULT_MERGED,
    )
    _ = (tmp_path / "main-health.env").write_text("MAIN_CI_STATUS=pass\n", encoding="utf-8")
    calls: list[str] = []

    def pr_view_field_read(*_args: object, **_kwargs: object) -> CommandResult:
        calls.append("mergeCommit")
        return CommandResult(("gh", "pr", "view", "5", "--repo", "o/r", "--json", "mergeCommit"), 0, '{"mergeCommit":{"oid":"merge-sha"}}', "", 0.01)

    def wait_main_health(*_args: object, **_kwargs: object) -> ship.main_health.MainHealthWaitResult:
        calls.append("watch")
        return ship.main_health.MainHealthWaitResult(
            health=ship.main_health.MainHealthStatus(
                status="pass",
                head_sha="merge-sha",
                detail="merged push passed",
            ),
            elapsed_seconds=1,
            attempts=1,
        )

    def run_postmerge_phase(*_args: object, **_kwargs: object) -> ship.ShipResult:
        calls.append("postmerge")
        return ship.ShipResult(Outcome.OK, detail="done")

    monkeypatch.setattr(ship.gh, "pr_view_field_read", pr_view_field_read)
    monkeypatch.setattr(ship.main_health, "wait_main_health", wait_main_health)
    monkeypatch.setattr(ship, "run_postmerge_phase", run_postmerge_phase)

    result = ship._ship_postmerge_phase(  # pyright: ignore[reportPrivateUsage]
        runner=RecordingRunner(),
        working=ctx,
        cwd=str(tmp_path),
        iteration=0,
        rebase_count=0,
        fix_attempts=0,
        transient_retries=0,
    )

    assert result.outcome is Outcome.OK
    assert calls == ["mergeCommit", "watch", "postmerge"]


def test_ship_postmerge_push_watch_falls_back_to_origin_main_when_merge_commit_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    ctx = _ctx(
        tmp_path,
        state_file=str(state_file),
        pr_number=5,
        pr_url="https://example.com/pr/5",
        pr_closed=True,
        merge_result=config.MERGE_RESULT_MERGED,
    )
    _ = (tmp_path / "main-health.env").write_text("MAIN_CI_STATUS=pass\n", encoding="utf-8")
    calls: list[str] = []

    def fetch(*_args: object, **_kwargs: object) -> CommandResult:
        calls.append("fetch")
        return CommandResult(("git", "fetch", "origin", "main"), 0, "", "", 0.01)

    def try_rev_parse(*args: object, **kwargs: object) -> str:
        ref = str(args[1]) if len(args) > 1 else str(kwargs.get("ref", ""))
        calls.append(ref)
        return "origin-sha" if ref == "origin/main" else ""

    def pr_view_field_read(*_args: object, **_kwargs: object) -> CommandResult:
        calls.append("mergeCommit")
        return CommandResult(("gh", "pr", "view", "5", "--repo", "o/r", "--json", "mergeCommit"), 0, '{"mergeCommit":null}', "", 0.01)

    def wait_main_health(*_args: object, **_kwargs: object) -> ship.main_health.MainHealthWaitResult:
        calls.append("watch")
        return ship.main_health.MainHealthWaitResult(
            health=ship.main_health.MainHealthStatus(
                status="pass",
                head_sha="origin-sha",
                detail="merged push passed",
            ),
            elapsed_seconds=1,
            attempts=1,
        )

    def run_postmerge_phase(*_args: object, **_kwargs: object) -> ship.ShipResult:
        calls.append("postmerge")
        return ship.ShipResult(Outcome.OK, detail="done")

    monkeypatch.setattr(ship.git, "fetch", fetch)
    monkeypatch.setattr(ship.git, "try_rev_parse", try_rev_parse)
    monkeypatch.setattr(ship.gh, "pr_view_field_read", pr_view_field_read)
    monkeypatch.setattr(ship.main_health, "wait_main_health", wait_main_health)
    monkeypatch.setattr(ship, "run_postmerge_phase", run_postmerge_phase)

    result = ship._ship_postmerge_phase(  # pyright: ignore[reportPrivateUsage]
        runner=RecordingRunner(),
        working=ctx,
        cwd=str(tmp_path),
        iteration=0,
        rebase_count=0,
        fix_attempts=0,
        transient_retries=0,
    )

    assert result.outcome is Outcome.OK
    assert calls == ["mergeCommit", "fetch", "origin/main", "watch", "postmerge"]


def test_premerge_main_health_gate_uses_commit_scoped_head_sha(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = (tmp_path / "preflight-tmpdir.env").write_text("PREFLIGHT_TMPDIR=/preflight\n", encoding="utf-8")
    _ = (tmp_path / "main-health.env").write_text("MAIN_CI_STATUS=pass\n", encoding="utf-8")
    ctx = _ctx(
        tmp_path,
        state_file=str(state_file),
        pr_number=5,
        pr_url="https://example.com/pr/5",
        merge_result=config.MERGE_RESULT_MERGED,
    )
    counters = ship.ShipReconciliationCounters(iteration=1, rebase_count=2, fix_attempts=3, transient_retries=4)
    observed: dict[str, str] = {}

    def fetch(*_args: object, **_kwargs: object) -> CommandResult:
        return CommandResult(("git", "fetch", "origin", "main"), 0, "", "", 0.01)

    def try_rev_parse(*args: object, **kwargs: object) -> str:
        ref = str(args[1]) if len(args) > 1 else str(kwargs.get("ref", ""))
        return "base-sha" if ref == "origin/main" else ""

    def read_main_health(*_args: object, **kwargs: object) -> ship.main_health.MainHealthStatus:
        query = kwargs.get("query")
        if query is None:
            query = _args[1]
        query = cast("ship.main_health.MainHealthQuery", query)
        observed["head_sha"] = query.head_sha or ""
        return ship.main_health.MainHealthStatus(status="pass", head_sha=query.head_sha or "", detail="ok")

    monkeypatch.setattr(ship.git, "fetch", fetch)
    monkeypatch.setattr(ship.git, "try_rev_parse", try_rev_parse)
    monkeypatch.setattr(ship.main_health, "read_main_health", read_main_health)

    result = ship._premerge_main_health_gate(  # pyright: ignore[reportPrivateUsage]
        runner=RecordingRunner(),
        working=ctx,
        repo_root=str(tmp_path),
        base_ref="main",
        counters=counters,
    )

    assert result is None
    assert observed["head_sha"] == "base-sha"


def test_main_health_gates_fail_closed_when_sidecar_missing(tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = (tmp_path / "preflight-tmpdir.env").write_text("PREFLIGHT_TMPDIR=/preflight\n", encoding="utf-8")
    ctx = _ctx(
        tmp_path,
        state_file=str(state_file),
        pr_number=5,
        pr_url="https://example.com/pr/5",
        merge_result=config.MERGE_RESULT_MERGED,
    )
    counters = ship.ShipReconciliationCounters(iteration=1, rebase_count=2, fix_attempts=3, transient_retries=4)

    premerge = ship._premerge_main_health_gate(  # pyright: ignore[reportPrivateUsage]
        runner=RecordingRunner(),
        working=ctx,
        repo_root=str(tmp_path),
        base_ref="main",
        counters=counters,
    )
    postmerge = ship._postmerge_main_health_gate(  # pyright: ignore[reportPrivateUsage]
        runner=RecordingRunner(),
        working=ctx.with_(pr_closed=True),
        cwd=str(tmp_path),
        counters=counters,
    )

    assert premerge is not None
    assert premerge.outcome is Outcome.STALLED
    assert "missing main-health.env" in premerge.detail
    assert postmerge is not None
    assert postmerge.outcome is Outcome.STALLED
    assert "missing main-health.env" in postmerge.detail


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
    result = ship.run_postmerge_phase(runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path))
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
from larch.core import logging_util
from larch.core import config
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
    python_dir = Path(__file__).resolve().parents[2]
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
    path = ship._write_ci_fix_detail_log(ctx=ctx, detail=ci_detail)  # pyright: ignore[reportPrivateUsage]
    assert path
    assert Path(path).read_text(encoding="utf-8") == ci_detail


def test_ci_fix_exhausted_terminal_state_sets_bail_reason(tmp_path: Path) -> None:
    """_write_terminal_state for NEEDS_USER_INPUT/ci-fix-exhausted persists BAIL_REASON, BAIL_FAILURE_DETAIL_LOG, STALL_STEP."""
    state_file = tmp_path / "ship-pr-state.sh"
    ci_detail = "ci-fix-exhausted: python-lint\nFAIL test_foo.py\n"
    ctx = _ctx(tmp_path, state_file=str(state_file), final_bail_reason="ci-fix-exhausted")
    detail_log_path = ship._write_ci_fix_detail_log(ctx=ctx, detail=ci_detail)  # pyright: ignore[reportPrivateUsage]

    ship._write_terminal_state(  # pyright: ignore[reportPrivateUsage]
        ctx=ctx,
        result=Outcome.NEEDS_USER_INPUT,
        step="10",
        bail_failure_detail_log=detail_log_path,
    )

    state = state_file.read_text(encoding="utf-8")
    assert "BAIL_REASON=ci-fix-exhausted\n" in state
    assert f"BAIL_FAILURE_DETAIL_LOG={detail_log_path}\n" in state
    assert "STALL_STEP=10\n" in state


def test_ci_fix_exhausted_detail_log_classified_by_stall_recovery(tmp_path: Path) -> None:
    """Stall-recovery classifier on the new envelope yields unrecoverable/none."""
    stall_recovery = Path(__file__).resolve().parents[3] / "python" / "cli.py"

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
        [sys.executable, str(stall_recovery), "stall-recovery", "classify",
         "--implement-tmpdir", str(tmp_path),
         "--in-memory-stall-tracking", "true",
         "--failure-detail-log", str(detail_log)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    out = completed.stdout
    assert "FAILURE_CLASS=unrecoverable" in out, f"unexpected classify output: {out}"
    assert "RESUME_HINT=none" in out, f"unexpected classify output: {out}"


def test_emit_result_prints_before_journal_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    class FailingJournal:
        def __init__(self, *_args: object) -> None:
            pass

        def append(self, *_args: object, **_kwargs: object) -> object:
            raise OSError("journal blocked")

    monkeypatch.setattr(ship.logging_util, "JsonlJournal", FailingJournal)
    ctx = _ctx(tmp_path)
    ship.emit_result(ctx=ctx, result=ship.ShipResult(Outcome.OK, pr_number=1, pr_url="u"))
    captured = capsys.readouterr()
    assert json.loads(captured.out)["outcome"] == "OK"
    assert "journal append skipped" in captured.err


def test_emit_result_skips_journal_on_invalid_tmpdir(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ctx = _ctx(tmp_path, tmpdir="/not/allowed/larch")
    ship.emit_result(ctx=ctx, result=ship.ShipResult(Outcome.STALLED, detail="invalid tmpdir"))
    assert json.loads(capsys.readouterr().out)["outcome"] == "STALLED"
    assert not Path("/not/allowed/larch").exists()


def test_persist_stall_metadata_gap_fill_preserves_custom_key(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, pr_number=2, pr_url="u")
    target = tmp_path / "finalize-state.sh"
    finalize_data = {"CUSTOM_PIN": "keep", "PR_NUMBER": "7"}
    ship.finalize.write_finalize_state_merged(path=target, data=finalize_data)
    ship._persist_stall_metadata_if_needed(ctx=ctx, result=ship.ShipResult(Outcome.STALLED, detail="merge failed"), tmpdir=tmp_path)  # pylint: disable=protected-access
    data = ship.finalize.read_finalize_state(target)
    assert data["CUSTOM_PIN"] == "keep"
    assert data["PR_NUMBER"] == "7"
    assert data["STALL_TRACKING"] == "true"


def test_persist_stall_metadata_uses_state_file_before_ctx(tmp_path: Path) -> None:
    state = tmp_path / "ship-pr-state.sh"
    _ = state.write_text("PR_NUMBER=44\nPR_URL=https://example.invalid/pr/44\n", encoding="utf-8")
    ctx = _ctx(tmp_path, pr_number=None, pr_url="", state_file=str(state))
    ship._persist_stall_metadata_if_needed(ctx=ctx, result=ship.ShipResult(Outcome.STALLED, detail="rebase stalled"), tmpdir=tmp_path)  # pylint: disable=protected-access
    data = ship.finalize.read_finalize_state(tmp_path / "finalize-state.sh")
    assert data["PR_NUMBER"] == "44"
    assert data["PR_URL"] == "https://example.invalid/pr/44"
    assert data["STALL_TRACKING"] == "true"


def test_persist_stall_metadata_treats_zero_pr_number_as_absent(tmp_path: Path) -> None:
    state = tmp_path / "ship-pr-state.sh"
    _ = state.write_text("PR_NUMBER=44\n", encoding="utf-8")
    ctx = _ctx(tmp_path, pr_number=0, state_file=str(state))
    result = ship.ShipResult(Outcome.STALLED, pr_number=0, detail="rebase stalled")
    ship._persist_stall_metadata_if_needed(ctx=ctx, result=result, tmpdir=tmp_path)  # pylint: disable=protected-access
    data = ship.finalize.read_finalize_state(tmp_path / "finalize-state.sh")
    assert data["PR_NUMBER"] == "44"


def test_terminal_finalize_write_emits_success_breadcrumb(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = _ctx(tmp_path, pr_number=7, pr_closed=True)
    ship._write_terminal_finalize_if_terminal(ctx=ctx, result=Outcome.OK, step="")  # pyright: ignore[reportPrivateUsage]

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
        ctx=_ctx(transient_dir),
        result=Outcome.TRANSIENT,
        step="checks",
    )
    ship._write_terminal_finalize_if_terminal(  # pyright: ignore[reportPrivateUsage]
        ctx=_ctx(tmp_path, tmpdir=str(invalid)),
        result=Outcome.OK,
        step="done",
    )

    captured = capsys.readouterr()
    assert "finalize-state-written" not in captured.err
    assert not (transient_dir / "finalize-state.sh").exists()
    assert not (invalid / "finalize-state.sh").exists()


def test_persist_stall_metadata_preserves_existing_tracking(tmp_path: Path) -> None:
    target = tmp_path / "finalize-state.sh"
    ship.finalize.write_finalize_state_merged(path=target, data={"STALL_TRACKING": "true", "STALL_STEP": "existing"})
    ctx = _ctx(tmp_path, stall_step="new")
    ship._persist_stall_metadata_if_needed(ctx=ctx, result=ship.ShipResult(Outcome.STALLED, detail="new"), tmpdir=tmp_path)  # pylint: disable=protected-access
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
    ship.finalize.write_finalize_state_merged(path=target, data={"PR_NUMBER": "88"})
    result = ship.ShipResult(Outcome.STALLED, pr_number=7, detail="post-merge flush skipped: blocked")
    ship._persist_stall_metadata_if_needed(ctx=_ctx(tmp_path, pr_number=7), result=result, tmpdir=tmp_path)  # pylint: disable=protected-access
    data = ship.finalize.read_finalize_state(target)
    assert data["PR_NUMBER"] == "88"
    assert data["STALL_TRACKING"] == "true"


def test_persist_stall_metadata_invalid_tmpdir_is_json_only(tmp_path: Path) -> None:
    invalid = Path("/not/allowed/larch")
    ctx = _ctx(tmp_path, tmpdir=str(invalid))
    ship._persist_stall_metadata_if_needed(ctx=ctx, result=ship.ShipResult(Outcome.STALLED, detail="invalid tmpdir"), tmpdir=invalid)  # pylint: disable=protected-access
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

    result = ship.run_postmerge_phase(runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path))

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


def test_postbump_conflict_routes_to_pre_push_handoff(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    monkeypatch.setattr(
        ship.finalize,
        "postbump_preflight",
        lambda *_a, **_k: ship.finalize.PostbumpPreflight(ok=True),
    )
    monkeypatch.setattr(
        ship.finalize,
        "postbump",
        lambda *_a, **_k: type(
            "R",
            (),
            {
                "outcome": Outcome.STALLED,
                "status": "rebase-failed",
                "detail": "rebase failed; conflicts in: docs/a.md",
                "conflict_files": "docs/a.md",
            },
        )(),
    )
    monkeypatch.setattr(
        ship.run_logs,
        "flush_logs_pre",
        lambda *_a, **_k: type("S", (), {"skipped": False, "reason": ""})(),
    )
    monkeypatch.setattr(
        ship,
        "_write_terminal_finalize_if_terminal",
        lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("terminal finalize should be skipped")
        ),
    )

    result = ship.run_ship(
        _ctx(tmp_path, state_file=str(state_file)),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.STALLED
    state = state_file.read_text(encoding="utf-8")
    assert "PHASE=rebase\n" in state
    assert "RESUME_PHASE=ship-pr-rrr-phase14\n" in state
    assert "CALLER_KIND=ship_pr_pre_push\n" in state
    assert "CONFLICT_FILES=docs/a.md\n" in state
    assert (tmp_path / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME).is_file()


def test_pre_rebase_flush_commit_failed_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # A pre-rebase log flush that skips with reason "commit-failed" must fail
    # closed (STALLED) instead of rebasing + merging on a stale snapshot
    # (issue #4930). Mirrors the post-ensure gate, which already excludes
    # commit-failed via REFRESH_SKIP_POST_ENSURE_PR_OK.
    state_file = tmp_path / "ship-pr-state.sh"
    seen = {"monitored": False}

    def fake_flush(*_a: object, **_k: object) -> run_logs.RefreshSkip:
        # Clean until the merge loop hands control to the rebase branch; the
        # pre-rebase flush is the only one that must surface commit-failed here.
        if seen["monitored"]:
            return run_logs.RefreshSkip(skipped=True, reason="commit-failed")
        return run_logs.RefreshSkip(skipped=False, reason="")

    def fake_monitor(*_a: object, **_k: object) -> object:
        seen["monitored"] = True
        return type(
            "M",
            (),
            {
                "result": StepResult(Outcome.OK),
                "action": "wait",
                "goto_rebase": True,
                "failed_run_id": None,
                "transient_rerun_attempted": False,
            },
        )()

    def fail_rebase(*_a: object, **_k: object) -> object:
        pytest.fail("rebase_and_push reached despite commit-failed pre-rebase flush")

    monkeypatch.setattr(ship.finalize, "postbump_preflight", lambda *_a, **_k: ship.finalize.PostbumpPreflight(ok=True))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", fake_flush)
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda **_k: "body")
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 12, "url": "https://example.test/pr/12", "status": "created"})(),
    )
    monkeypatch.setattr(ship.run_logs, "write_final_report_comment", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(ship.ci_monitor, "monitor", fake_monitor)
    monkeypatch.setattr(ship.rebase, "rebase_and_push", fail_rebase)
    monkeypatch.setattr(ship, "_publish_post_pr_terminal_snapshot", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)

    result = ship.run_ship(
        _ctx(tmp_path, state_file=str(state_file)),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.STALLED
    assert result.detail == "pre-rebase flush skipped: commit-failed"



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



def test_load_or_prepare_guidelines_note_returns_current_durable_note(tmp_path: Path) -> None:
    ship.architectural_guidelines.write_implement_note(
        implement_tmpdir=tmp_path,
        note_text="Consulted note\n",
        head_sha="head",
        metadata={"ASSESSED_HEAD_SHA": "head", "DIFF_FINGERPRINT": ship.architectural_guidelines.diff_fingerprint("diff")},
        base_ref="origin/main",
    )

    result = ship_guidelines.load_or_prepare_guidelines_note(
        implement_tmpdir=str(tmp_path),
        head_sha="head",
        base_ref="origin/main",
    )

    assert result.note == "Consulted note"
    assert result.needs_assessment is False
    assert result.warning_logged is False


def test_load_or_prepare_guidelines_note_requests_compose_assessment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = ship.architectural_guidelines.ComposeMaterializationResult(
        status="assessment-required",
        head_sha="head",
        base_ref="origin/main",
        diff_fingerprint=ship.architectural_guidelines.diff_fingerprint("diff"),
        diff_path=tmp_path / ship.architectural_guidelines.MATERIALIZED_DIFF,
        guidelines_status="present",
    )
    monkeypatch.setattr(
        ship_guidelines.architectural_guidelines,
        "prepare_compose_assessment",
        lambda **_kwargs: prepared,
    )

    result = ship_guidelines.load_or_prepare_guidelines_note(
        implement_tmpdir=str(tmp_path),
        head_sha="head",
        base_ref="origin/main",
    )

    assert result.note == ""
    assert result.needs_assessment is True
    assert result.detail == "architectural-guidelines assessment required before PR body compose"


def test_load_or_prepare_guidelines_note_drops_on_redaction_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ship.architectural_guidelines.write_implement_note(
        implement_tmpdir=tmp_path,
        note_text="Consulted note\n",
        head_sha="head",
        metadata={"ASSESSED_HEAD_SHA": "head", "DIFF_FINGERPRINT": ship.architectural_guidelines.diff_fingerprint("diff")},
        base_ref="origin/main",
    )

    def fail_redact(_note: str) -> str:
        raise ShipError("redaction failed for PR body")

    monkeypatch.setattr(ship.pr_body, "redact_pr_body", fail_redact)

    result = ship_guidelines.load_or_prepare_guidelines_note(
        implement_tmpdir=str(tmp_path),
        head_sha="head",
        base_ref="origin/main",
    )

    assert result.note == ""
    assert result.needs_assessment is False
    assert result.warning_logged is True
    assert result.guidelines_status == "present"
    assert result.reason == ship_guidelines.REASON_NOTE_REDACTION_FAILED


def test_guideline_ship_outcome_sidecar_pinned_and_clean(tmp_path: Path) -> None:
    pinned = ship_guidelines.write_guideline_ship_outcome(
        implement_tmpdir=str(tmp_path),
        result=ship.GuidelinesGateResult(note="Deviation note", guidelines_status="present"),
        head_sha="abc123",
        base_ref="origin/main",
    )
    assert pinned is not None
    assert pinned.outcome == ship_guidelines.OUTCOME_PINNED

    data = json.loads((tmp_path / ship.architectural_guidelines.GUIDELINE_SHIP_OUTCOME_SIDECAR).read_text(encoding="utf-8"))
    assert data["schema_version"] == "1"
    assert data["outcome"] == "pinned"
    assert data["reason"] == ship_guidelines.REASON_NOTE_PINNED
    assert data["guidelines_status"] == "present"

    clean = ship_guidelines.write_guideline_ship_outcome(
        implement_tmpdir=str(tmp_path),
        result=ship.GuidelinesGateResult(guidelines_status="absent"),
        head_sha="abc123",
        base_ref="origin/main",
    )
    assert clean is not None
    assert clean.outcome == ship_guidelines.OUTCOME_CLEAN
    data = json.loads((tmp_path / ship.architectural_guidelines.GUIDELINE_SHIP_OUTCOME_SIDECAR).read_text(encoding="utf-8"))
    assert data["outcome"] == "clean"
    assert data["reason"] == ship_guidelines.REASON_GUIDELINES_ABSENT


def test_guideline_ship_outcome_sidecar_dropped(tmp_path: Path) -> None:
    outcome = ship_guidelines.write_guideline_ship_outcome(
        implement_tmpdir=str(tmp_path),
        result=ship.GuidelinesGateResult(
            guidelines_status="present",
            detail="redaction failed",
            reason=ship_guidelines.REASON_NOTE_REDACTION_FAILED,
        ),
        head_sha="abc123",
        base_ref="origin/main",
    )

    assert outcome is not None
    assert outcome.outcome == ship_guidelines.OUTCOME_DROPPED
    data = json.loads((tmp_path / ship.architectural_guidelines.GUIDELINE_SHIP_OUTCOME_SIDECAR).read_text(encoding="utf-8"))
    assert data["outcome"] == "dropped"
    assert data["reason"] == ship_guidelines.REASON_NOTE_REDACTION_FAILED
    assert data["detail"] == "redaction failed"


def test_guideline_ship_outcome_present_empty_note_classifies_dropped(tmp_path: Path) -> None:
    outcome = ship_guidelines.write_guideline_ship_outcome(
        implement_tmpdir=str(tmp_path),
        result=ship.GuidelinesGateResult(guidelines_status="present"),
        head_sha="abc123",
        base_ref="origin/main",
    )

    assert outcome is not None
    assert outcome.outcome == ship_guidelines.OUTCOME_DROPPED
    assert outcome.guidelines_status == "present"
    data = json.loads((tmp_path / ship.architectural_guidelines.GUIDELINE_SHIP_OUTCOME_SIDECAR).read_text(encoding="utf-8"))
    assert data["outcome"] == "dropped"
    assert data["guidelines_status"] == "present"


def test_invariant_ship_outcome_present_empty_invariants_classifies_clean(tmp_path: Path) -> None:
    outcome = ship_guidelines.write_invariant_ship_outcome(
        implement_tmpdir=str(tmp_path),
        result=ship_guidelines.InvariantsGateResult(
            invariants_status="present",
            assessment_kind="clean",
            reason=ship_guidelines.REASON_INVARIANTS_EMPTY,
        ),
        head_sha="abc123",
        base_ref="origin/main",
    )

    assert outcome is not None
    assert outcome.outcome == ship_guidelines.OUTCOME_CLEAN
    assert outcome.reason == ship_guidelines.REASON_INVARIANTS_EMPTY
    assert outcome.assessment_kind == "clean"
    data = json.loads((tmp_path / ship.architectural_guidelines.INVARIANT_SHIP_OUTCOME_SIDECAR).read_text(encoding="utf-8"))
    assert data["outcome"] == "clean"
    assert data["reason"] == ship_guidelines.REASON_INVARIANTS_EMPTY
    assert data["invariants_status"] == "present"
    assert data["assessment_kind"] == "clean"
    assert ship.architectural_guidelines.validate_invariant_ship_outcome_record(data) is None


def test_guideline_ship_outcome_missing_status_does_not_infer_from_note(tmp_path: Path) -> None:
    outcome = ship_guidelines.write_guideline_ship_outcome(
        implement_tmpdir=str(tmp_path),
        result=ship.GuidelinesGateResult(note="Deviation note"),
        head_sha="abc123",
        base_ref="origin/main",
    )

    assert outcome is not None
    assert outcome.outcome == ship_guidelines.OUTCOME_CLEAN
    assert outcome.reason == ship_guidelines.REASON_GUIDELINES_ABSENT
    assert outcome.guidelines_status == "absent"
    data = json.loads((tmp_path / ship.architectural_guidelines.GUIDELINE_SHIP_OUTCOME_SIDECAR).read_text(encoding="utf-8"))
    assert data["outcome"] == "clean"
    assert data["reason"] == ship_guidelines.REASON_GUIDELINES_ABSENT
    assert data["guidelines_status"] == "absent"


def test_guideline_ship_outcome_blank_head_sha_raises_before_write(tmp_path: Path) -> None:
    with pytest.raises(OSError, match="head_sha is empty"):
        ship_guidelines.write_guideline_ship_outcome(
            implement_tmpdir=str(tmp_path),
            result=ship.GuidelinesGateResult(guidelines_status="absent"),
            head_sha=" \t",
            base_ref="origin/main",
        )

    assert not (tmp_path / ship.architectural_guidelines.GUIDELINE_SHIP_OUTCOME_SIDECAR).exists()


def test_load_or_prepare_guidelines_note_skips_assessment_on_prepare_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = ship.architectural_guidelines.ComposeMaterializationResult(
        status="failed",
        head_sha="head",
        base_ref="origin/main",
        warning="missing remote ref",
    )
    monkeypatch.setattr(
        ship_guidelines.architectural_guidelines,
        "prepare_compose_assessment",
        lambda **_kwargs: prepared,
    )

    result = ship_guidelines.load_or_prepare_guidelines_note(
        implement_tmpdir=str(tmp_path),
        head_sha="head",
        base_ref="origin/main",
    )

    assert result.note == ""
    assert result.needs_assessment is False
    assert result.warning_logged is True


def test_pin_or_invalidate_guidelines_note_clears_retired_artifacts(tmp_path: Path) -> None:
    ship.architectural_guidelines.write_staged_assessment(
        implement_tmpdir=tmp_path,
        assessment_text="note\n",
        assessed_head_sha="old",
        diff_fingerprint_value=ship.architectural_guidelines.diff_fingerprint("diff"),
        base_ref="origin/main",
        diff_text="diff",
    )
    assert ship.architectural_guidelines.persist_dropped_note_notice(tmp_path, notice_text="old marker\n")

    warning_logged = ship_guidelines._pin_or_invalidate_guidelines_note(
        implement_tmpdir=str(tmp_path),
        head_sha="head",
        base_ref="origin/main",
    )

    assert warning_logged is False
    assert not (tmp_path / ship.architectural_guidelines.STAGED_ASSESSMENT).exists()
    assert not (tmp_path / ship.architectural_guidelines.DROPPED_NOTE_ARTIFACT).exists()
    assert not (tmp_path / ship.architectural_guidelines.DURABLE_NOTE).exists()


def test_invalidate_guidelines_note_clears_note_without_drop_notice(tmp_path: Path) -> None:
    ship.architectural_guidelines.write_implement_note(
        implement_tmpdir=tmp_path,
        note_text="note\n",
        head_sha="head",
        metadata={"ASSESSED_HEAD_SHA": "head", "DIFF_FINGERPRINT": ship.architectural_guidelines.diff_fingerprint("diff")},
        base_ref="origin/main",
    )
    assert ship.architectural_guidelines.persist_dropped_note_notice(tmp_path, notice_text="old marker\n")

    warning_logged = ship_guidelines._invalidate_guidelines_note(str(tmp_path))

    assert warning_logged is False
    assert not (tmp_path / ship.architectural_guidelines.DURABLE_NOTE).exists()
    assert ship.architectural_guidelines.read_dropped_note_notice(tmp_path) == ""


def _write_minimal_final_report_state(tmp_path: Path) -> None:
    (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=0\nRUN_ID=run1\n", encoding="utf-8")
    (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")
    (tmp_path / "ship-pr-state.sh").write_text("PR_NUMBER=1\nPR_URL=https://github.com/o/r/pull/1\n", encoding="utf-8")
    (tmp_path / "finalize-state.sh").write_text("", encoding="utf-8")
    (tmp_path / "run-flags.sh").write_text("FORCE_REQUESTED=false\n", encoding="utf-8")


def _stub_final_report_cost_and_assessment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(final_report, "_final_report_token_fields", lambda **_kw: {"cost_unavailable": True})
    monkeypatch.setattr(final_report.exec_issue_detail, "assess_issue_details", lambda *_args, **_kwargs: {})


def test_guidelines_invalidate_removes_note_from_final_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_minimal_final_report_state(tmp_path)
    _stub_final_report_cost_and_assessment(monkeypatch)
    ship.architectural_guidelines.write_implement_note(
        implement_tmpdir=tmp_path,
        note_text="Guideline note\n",
        head_sha="head",
        metadata={"ASSESSED_HEAD_SHA": "head", "DIFF_FINGERPRINT": ship.architectural_guidelines.diff_fingerprint("diff")},
        base_ref="origin/main",
    )

    ship_guidelines._invalidate_guidelines_note(str(tmp_path))
    monkeypatch.setattr(final_report, "_current_head_sha", lambda: "head")
    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)

    assert (rc, err) == (0, "")
    summary = (tmp_path / "summary-final.md").read_text(encoding="utf-8")
    assert "## Architectural guidelines" not in summary
    assert not (tmp_path / ship.architectural_guidelines.DURABLE_NOTE).exists()


def test_guidelines_staged_mismatch_does_not_create_drop_notice_for_final_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_minimal_final_report_state(tmp_path)
    _stub_final_report_cost_and_assessment(monkeypatch)
    ship.architectural_guidelines.write_staged_assessment(
        implement_tmpdir=tmp_path,
        assessment_text="Guideline note\n",
        assessed_head_sha="old",
        diff_fingerprint_value="mismatch",
        base_ref="origin/main",
        diff_text="implementation diff",
    )
    ship_guidelines._invalidate_guidelines_note(str(tmp_path))
    monkeypatch.setattr(final_report, "_current_head_sha", lambda: "head")
    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)

    assert (rc, err) == (0, "")
    assert "## Architectural guidelines" not in (tmp_path / "summary-final.md").read_text(encoding="utf-8")


def _stub_happy_ship_mocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 5, "url": "https://example.test/pr/7", "status": "created"})(),
    )
    monkeypatch.setattr(
        ship.push,
        "push_branch",
        lambda *_a, **_k: ship.push.PushResult(remote="origin", attempts=1, status="pushed"),
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
                "failed_run_id": None,
            },
        )(),
    )
    monkeypatch.setattr(
        ship.merge,
        "merge_pr",
        lambda *_a, **_k: type("MR", (), {"result": config.MERGE_RESULT_MERGED, "error": ""})(),
    )
    monkeypatch.setattr(
        ship.finalize,
        "postmerge",
        lambda *_a, **_k: type("PM", (), {"outcome": Outcome.OK, "detail": "", "status": "ok"})(),
    )
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", lambda *_a, **_k: run_logs.RefreshSkip(skipped=False, reason=""))
    monkeypatch.setattr(ship.run_logs, "flush_logs_post", lambda *_a, **_k: run_logs.RefreshSkip(skipped=False, reason=""))
    monkeypatch.setattr(ship.run_logs, "load_or_recover_manifest", lambda *_a, **_k: object())
    monkeypatch.setattr(ship.run_logs, "write_final_report_comment", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: "head")


def test_fresh_ship_passes_compose_guidelines_note_to_pr_body(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_happy_ship_mocks(monkeypatch)
    order: list[str] = []
    compose_calls: list[dict[str, object]] = []

    def fake_gate(**_kwargs: object) -> ship.GuidelinesGateResult:
        order.append("gate")
        return ship.GuidelinesGateResult(note="Guideline deviation note")

    def fake_compose(**kwargs: object) -> str:
        order.append("compose")
        compose_calls.append(dict(kwargs))
        return "body"

    monkeypatch.setattr(ship, "load_or_prepare_guidelines_note", fake_gate)
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", fake_compose)
    result = ship.run_ship(_ctx(tmp_path), runner=RecordingRunner(), cwd=str(tmp_path))
    assert result.outcome is Outcome.OK
    assert order.index("gate") < order.index("compose")
    assert compose_calls[0].get("architectural_guidelines_note") == "Guideline deviation note"


def test_run_ship_postbump_rebase_writes_compose_note_and_uses_it_in_pr_body(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    def git(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr or completed.stdout
        return completed.stdout.strip()

    (repo / "README.md").write_text("base\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-m", "base")
    (repo / ship.architectural_guidelines.GUIDELINES_FILENAME).write_text(
        "### G-python-1: Keep small\n- Why: minimal change.\n- Deviate when: never\n",
        encoding="utf-8",
    )
    git("branch", "-M", "main")
    git("remote", "add", "origin", str(repo))
    git("remote", "add", "upstream", str(repo))
    head_sha = git("rev-parse", "HEAD")
    git("update-ref", "refs/remotes/origin/main", head_sha)
    git("update-ref", "refs/remotes/upstream/main", head_sha)
    git("switch", "-c", "feature")
    (repo / "README.md").write_text("base\nfeature\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-m", "feature")
    git("switch", "main")
    (repo / "main.txt").write_text("base\nmain advance\n", encoding="utf-8")
    git("add", "main.txt")
    git("commit", "-m", "main advance")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    git("update-ref", "refs/remotes/upstream/main", "HEAD")
    git("switch", "feature")

    compose_calls: list[dict[str, object]] = []
    head_before = git("rev-parse", "HEAD")
    head_after = ""

    def fake_postbump(
        *,
        runner: RecordingRunner,  # noqa: ARG001  # pylint: disable=unused-argument
        ctx: RunContext,
        cwd: str | None = None,
    ) -> ship.finalize.FinalizeResult:
        del ctx, cwd
        nonlocal head_after
        git("rebase", "origin/main")
        head_after = git("rev-parse", "HEAD")
        prepared = ship.architectural_guidelines.prepare_compose_assessment(
            implement_tmpdir=tmp_path,
            repo_root=repo,
            expected_head_sha=head_after,
        )
        assert prepared.status == "assessment-required"
        ship.architectural_guidelines.write_compose_assessment(
            implement_tmpdir=tmp_path,
            assessment_text="Compose assessment",
            repo_root=repo,
        )
        return ship.finalize.FinalizeResult(Outcome.OK, "ok")

    def fake_compose(**kwargs: object) -> str:
        compose_calls.append(dict(kwargs))
        return "body"

    monkeypatch.setattr(ship.finalize, "postbump_preflight", lambda *_a, **_k: ship.finalize.PostbumpPreflight(ok=True))
    monkeypatch.setattr(ship.finalize, "postbump", fake_postbump)
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", lambda *_a, **_k: run_logs.RefreshSkip(skipped=False, reason=""))
    monkeypatch.setattr(ship.run_logs, "write_final_report_comment", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)
    monkeypatch.setattr(ship, "reconcile_committed_stalled_summary_if_recovered", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: git("rev-parse", "HEAD"))
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", fake_compose)
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 5, "url": "https://example.test/pr/7", "status": "created"})(),
    )

    result = ship.run_ship(
        _ctx(tmp_path, merge=False, branch="feature", branch_name="feature", repo="o/r"),
        runner=RecordingRunner(),
        cwd=str(repo),
    )

    assert result.outcome is Outcome.OK
    assert head_before != head_after
    assert compose_calls[0].get("architectural_guidelines_note") == "Compose assessment"


def test_run_ship_merge_loop_rebase_refreshes_guidelines_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    def git(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr or completed.stdout
        return completed.stdout.strip()

    (repo / "README.md").write_text("base\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-m", "base")
    (repo / ship.architectural_guidelines.GUIDELINES_FILENAME).write_text(
        "### G-python-1: Keep small\n- Why: minimal change.\n- Deviate when: never\n",
        encoding="utf-8",
    )
    git("branch", "-M", "main")
    git("remote", "add", "origin", str(repo))
    git("remote", "add", "upstream", str(repo))
    head_sha = git("rev-parse", "HEAD")
    git("update-ref", "refs/remotes/origin/main", head_sha)
    git("update-ref", "refs/remotes/upstream/main", head_sha)
    git("switch", "-c", "feature")
    (repo / "README.md").write_text("base\nfeature\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-m", "feature")
    git("switch", "main")
    (repo / "main.txt").write_text("base\nmain advance\n", encoding="utf-8")
    git("add", "main.txt")
    git("commit", "-m", "main advance")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    git("update-ref", "refs/remotes/upstream/main", "HEAD")
    git("switch", "feature")

    compose_calls: list[dict[str, object]] = []
    head_after_postbump = ""
    head_after_merge_rebase = ""

    def fake_postbump(
        *,
        runner: RecordingRunner,  # noqa: ARG001  # pylint: disable=unused-argument
        ctx: RunContext,
        cwd: str | None = None,
    ) -> ship.finalize.FinalizeResult:
        nonlocal head_after_postbump
        del ctx, cwd
        git("rebase", "origin/main")
        head_after_postbump = git("rev-parse", "HEAD")
        prepared = ship.architectural_guidelines.prepare_compose_assessment(
            implement_tmpdir=tmp_path,
            repo_root=repo,
            expected_head_sha=head_after_postbump,
        )
        assert prepared.status == "assessment-required"
        ship.architectural_guidelines.write_compose_assessment(
            implement_tmpdir=tmp_path,
            assessment_text="Compose assessment",
            repo_root=repo,
        )
        return ship.finalize.FinalizeResult(Outcome.OK, "ok")

    def fake_rebase_and_push(
        *,
        runner: RecordingRunner,  # pylint: disable=unused-argument
        repo: str,
        run_id: str,
        cwd: str,
        tmpdir: str,
        base_remote: str,
        base_ref: str,
        allow_conflict_fix: bool,
        enable_pre_push_handoff: bool,
    ) -> object:
        nonlocal head_after_merge_rebase
        del runner, repo, run_id, cwd, tmpdir, base_remote, base_ref, allow_conflict_fix, enable_pre_push_handoff
        git("rebase", "origin/main")
        head_after_merge_rebase = git("rev-parse", "HEAD")
        return ship.rebase.RebaseResult(
            outcome=Outcome.OK,
            rebased=True,
            pushed=True,
            new_version=None,
            attempts=1,
            detail="",
        )

    def fake_monitor(*_args: object, **_kwargs: object) -> object:
        git("switch", "main")
        (repo / "main-again.txt").write_text("base\nmain advance\nmain again\n", encoding="utf-8")
        git("add", "main-again.txt")
        git("commit", "-m", "main again")
        git("update-ref", "refs/remotes/origin/main", "HEAD")
        git("update-ref", "refs/remotes/upstream/main", "HEAD")
        git("switch", "feature")
        return type(
            "M",
            (),
            {
                "result": StepResult(Outcome.OK),
                "action": "wait",
                "goto_rebase": True,
                "failed_run_id": None,
                "transient_rerun_attempted": False,
                "ci_fix_rebase_pending": False,
            },
        )()

    def fake_compose(**kwargs: object) -> str:
        compose_calls.append(dict(kwargs))
        return "body"

    monkeypatch.setattr(ship.finalize, "postbump_preflight", lambda *_a, **_k: ship.finalize.PostbumpPreflight(ok=True))
    monkeypatch.setattr(ship.finalize, "postbump", fake_postbump)
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", lambda *_a, **_k: run_logs.RefreshSkip(skipped=False, reason=""))
    monkeypatch.setattr(ship.run_logs, "write_final_report_comment", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)
    monkeypatch.setattr(ship, "reconcile_committed_stalled_summary_if_recovered", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: git("rev-parse", "HEAD"))
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", fake_compose)
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 5, "url": "https://example.test/pr/7", "status": "created"})(),
    )
    monkeypatch.setattr(ship.ci_monitor, "monitor", fake_monitor)
    monkeypatch.setattr(ship.rebase, "rebase_and_push", fake_rebase_and_push)
    monkeypatch.setattr(ship, "_post_ensure_flush_and_push", lambda *_a, **_k: None)

    result = ship.run_ship(
        _ctx(tmp_path, merge=True, branch="feature", branch_name="feature", repo="o/r"),
        runner=RecordingRunner(),
        cwd=str(repo),
    )

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == "architectural-guidelines-assessment"
    assert result.detail == "architectural-guidelines assessment required before PR body compose"
    assert head_after_postbump
    assert head_after_merge_rebase
    assert head_after_postbump != head_after_merge_rebase
    assert compose_calls[0].get("architectural_guidelines_note") == "Compose assessment"

def test_guidelines_pin_warning_flushes_before_pr_body(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_happy_ship_mocks(monkeypatch)
    order: list[str] = []

    def fake_gate(**_kwargs: object) -> ship.GuidelinesGateResult:
        order.append("gate")
        return ship.GuidelinesGateResult(note="Guidelines warning", warning_logged=True)

    def fake_flush(*_args: object, **_kwargs: object) -> run_logs.RefreshSkip:
        order.append("flush")
        return run_logs.RefreshSkip(skipped=False, reason="")

    def fake_compose(**_kwargs: object) -> str:
        order.append("compose")
        return "body"

    def fake_ensure(*_args: object, **_kwargs: object) -> object:
        order.append("ensure")
        return type("P", (), {"number": 5, "url": "https://example.test/pr/7", "status": "created"})()

    monkeypatch.setattr(ship, "load_or_prepare_guidelines_note", fake_gate)
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", fake_flush)
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", fake_compose)
    monkeypatch.setattr(ship.pr, "ensure_pr", fake_ensure)

    result = ship.run_ship(_ctx(tmp_path), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    post_gate_flush = order.index("flush", order.index("gate"))
    assert order.index("gate") < post_gate_flush < order.index("compose") < order.index("ensure")


def test_guidelines_pin_warning_refresh_skip_stalls_before_pr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_happy_ship_mocks(monkeypatch)
    ensure_calls = 0
    flush_calls = 0

    def fake_gate(**_kwargs: object) -> ship.GuidelinesGateResult:
        return ship.GuidelinesGateResult(note="Guidelines warning", warning_logged=True)

    def fake_flush(*_args: object, **_kwargs: object) -> run_logs.RefreshSkip:
        nonlocal flush_calls
        flush_calls += 1
        if flush_calls == 1:
            return run_logs.RefreshSkip(skipped=False, reason="")
        return run_logs.RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_COMMIT_FAILED)

    def fake_ensure(*_args: object, **_kwargs: object) -> object:
        nonlocal ensure_calls
        ensure_calls += 1
        return type("P", (), {"number": 5, "url": "https://example.test/pr/7", "status": "created"})()

    monkeypatch.setattr(ship, "load_or_prepare_guidelines_note", fake_gate)
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", fake_flush)
    monkeypatch.setattr(ship.pr, "ensure_pr", fake_ensure)

    result = ship.run_ship(_ctx(tmp_path), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert "architectural-guidelines outcome run-log refresh skipped" in result.detail
    assert ensure_calls == 0


@pytest.mark.parametrize("merge", [False, True])
def test_guidelines_warning_real_flush_commits_before_pr_create(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    merge: bool,
) -> None:
    _stub_happy_ship_mocks(monkeypatch)
    order: list[str] = []

    def fake_gate(**_kwargs: object) -> ship.GuidelinesGateResult:
        order.append("gate")
        return ship.GuidelinesGateResult(note="Guidelines warning", warning_logged=True)

    def fake_flush(**_kwargs: object) -> run_logs.RefreshSkip:
        order.append("flush")
        return run_logs.RefreshSkip(skipped=False, reason="")

    def fake_compose(**_kwargs: object) -> str:
        order.append("compose")
        return "body"

    monkeypatch.setattr(ship, "load_or_prepare_guidelines_note", fake_gate)
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", fake_flush)
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", fake_compose)
    if merge:
        monkeypatch.setattr(ship, "_post_ensure_flush_and_push", lambda *_a, **_k: ship.ShipResult(Outcome.OK, detail="ok"))
    else:
        monkeypatch.setattr(ship, "reconcile_committed_stalled_summary_if_recovered", lambda *_a, **_k: None)

    result = ship.run_ship(_ctx(tmp_path, merge=merge), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert order.index("gate") < order.index("flush", order.index("gate")) < order.index("compose")


def test_guidelines_warning_volatile_only_refresh_uses_matching_committed_outcome(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_happy_ship_mocks(monkeypatch)
    order: list[str] = []
    compose_calls: list[dict[str, object]] = []

    def fake_gate(**_kwargs: object) -> ship.GuidelinesGateResult:
        order.append("gate")
        return ship.GuidelinesGateResult(note="Guidelines warning", guidelines_status="present")

    def fake_flush(*_args: object, **_kwargs: object) -> run_logs.RefreshSkip:
        order.append("flush")
        return run_logs.RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_VOLATILE_ONLY)

    def fake_compose(**kwargs: object) -> str:
        order.append("compose")
        compose_calls.append(dict(kwargs))
        return "body"

    monkeypatch.setattr(ship, "load_or_prepare_guidelines_note", fake_gate)
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", fake_flush)
    monkeypatch.setattr(ship, "_committed_guideline_outcome_matches", lambda **_kwargs: True)
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", fake_compose)

    result = ship.run_ship(_ctx(tmp_path, merge=False), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert order == ["flush", "gate", "flush", "compose"]
    assert compose_calls[0].get("architectural_guidelines_note") == "Guidelines warning"


def test_guidelines_warning_volatile_only_refresh_stalls_without_matching_outcome(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_happy_ship_mocks(monkeypatch)
    order: list[str] = []
    compose_calls: list[dict[str, object]] = []
    ensure_calls = 0

    def fake_gate(**_kwargs: object) -> ship.GuidelinesGateResult:
        order.append("gate")
        return ship.GuidelinesGateResult(note="Guidelines warning", guidelines_status="present")

    def fake_flush(*_args: object, **_kwargs: object) -> run_logs.RefreshSkip:
        order.append("flush")
        return run_logs.RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_VOLATILE_ONLY)

    def fake_compose(**kwargs: object) -> str:
        order.append("compose")
        compose_calls.append(dict(kwargs))
        return "body"

    def fake_ensure_pr(*_args: object, **_kwargs: object) -> object:
        nonlocal ensure_calls
        ensure_calls += 1
        return type("P", (), {"number": 5, "url": "https://example.test/pr/7", "status": "created"})()

    monkeypatch.setattr(ship, "load_or_prepare_guidelines_note", fake_gate)
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", fake_flush)
    monkeypatch.setattr(ship, "_committed_guideline_outcome_matches", lambda **_kwargs: False)
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", fake_compose)
    monkeypatch.setattr(ship.pr, "ensure_pr", fake_ensure_pr)

    result = ship.run_ship(_ctx(tmp_path, merge=False), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.STALLED
    assert ensure_calls == 0
    assert order == ["flush", "gate", "flush"]
    assert not compose_calls


def test_guidelines_warning_no_logs_commit_does_not_stall_before_pr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_happy_ship_mocks(monkeypatch)
    monkeypatch.setattr(ship.finalize, "postbump_preflight", lambda *_a, **_k: ship.finalize.PostbumpPreflight(ok=True))
    monkeypatch.setattr(ship.finalize, "postbump", lambda *_a, **_k: type("R", (), {"outcome": Outcome.OK})())

    def fake_flush(*_args: object, **_kwargs: object) -> run_logs.RefreshSkip:
        return run_logs.RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_NO_LOGS_COMMIT)

    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", fake_flush)
    monkeypatch.setattr(ship, "_pin_and_load_guidelines_note", lambda *_a, **_k: ("Guidelines dropped", True))
    ensure_calls = 0

    def fake_ensure_pr(*_args: object, **_kwargs: object) -> object:
        nonlocal ensure_calls
        ensure_calls += 1
        return type("P", (), {"number": 5, "url": "https://example.test/pr/7", "status": "created"})()

    monkeypatch.setattr(ship.pr, "ensure_pr", fake_ensure_pr)

    result = ship.run_ship(_ctx(tmp_path, no_logs_commit=True, merge=False), runner=RecordingRunner(), cwd=str(tmp_path))

    assert result.outcome is Outcome.OK
    assert ensure_calls == 1


def _prepare_open_pr_resume(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feat\nPR_NUMBER=7\nPR_URL=https://example.test/pr/7\nREPO=o/r\nRUN_ID=run-abc\nISSUE_NUMBER=1\nMERGE=false\nDRAFT=false\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship.git, "current_branch", lambda *_a, **_k: "feat")
    monkeypatch.setattr(
        ship.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feat"})(),
    )
    monkeypatch.setattr(ship.git, "log_subject", lambda *_a, **_k: "Implement driver")
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: "head")
    monkeypatch.setattr(ship.run_logs, "write_final_report_comment", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)
    return state_file


def test_open_pr_resume_guidelines_gate_write_failure_stalls_before_ensure_pr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = _prepare_open_pr_resume(monkeypatch, tmp_path)
    monkeypatch.setattr(
        ship,
        "load_or_prepare_guidelines_note",
        lambda **_kwargs: ship.GuidelinesGateResult(note="Guidelines warning", guidelines_status="present"),
    )
    monkeypatch.setattr(ship, "write_guideline_ship_outcome", lambda **_kwargs: (_ for _ in ()).throw(OSError("boom")))
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("flush_logs_pre must not run")))
    monkeypatch.setattr(ship.pr, "ensure_pr", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("ensure_pr must not run")))

    result = ship.run_ship(
        _ctx(tmp_path, state_file=str(state_file), branch="feat", branch_name="feat"),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.STALLED
    assert "architectural-guidelines outcome sidecar write failed" in result.detail
    assert not (tmp_path / ship.architectural_guidelines.GUIDELINE_SHIP_OUTCOME_SIDECAR).exists()


def test_open_pr_resume_blank_head_sha_stalls_before_ensure_pr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = _prepare_open_pr_resume(monkeypatch, tmp_path)
    monkeypatch.setattr(ship.git, "try_rev_parse", lambda *_a, **_k: "")
    monkeypatch.setattr(
        ship,
        "load_or_prepare_guidelines_note",
        lambda **_kwargs: ship.GuidelinesGateResult(note="Guidelines warning", guidelines_status="present"),
    )
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("flush_logs_pre must not run")))
    monkeypatch.setattr(ship.pr, "ensure_pr", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("ensure_pr must not run")))

    result = ship.run_ship(
        _ctx(tmp_path, state_file=str(state_file), branch="feat", branch_name="feat"),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.STALLED
    assert "architectural-guidelines outcome sidecar write failed" in result.detail
    assert "head_sha is empty" in result.detail
    assert not (tmp_path / ship.architectural_guidelines.GUIDELINE_SHIP_OUTCOME_SIDECAR).exists()


def test_open_pr_resume_clears_stale_guideline_outcome_sidecar_before_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = _prepare_open_pr_resume(monkeypatch, tmp_path)
    stale = tmp_path / ship.architectural_guidelines.GUIDELINE_SHIP_OUTCOME_SIDECAR
    _ = stale.write_text("stale\n", encoding="utf-8")
    order: list[str] = []

    def fake_gate(**_kwargs: object) -> ship.GuidelinesGateResult:
        order.append("gate")
        assert not stale.exists()
        return ship.GuidelinesGateResult(note="Guidelines warning", guidelines_status="present")

    def fake_flush(*_args: object, **_kwargs: object) -> run_logs.RefreshSkip:
        order.append("flush")
        return run_logs.RefreshSkip(skipped=False, reason="")

    def fake_compose(**_kwargs: object) -> str:
        order.append("compose")
        return "body"

    monkeypatch.setattr(ship, "load_or_prepare_guidelines_note", fake_gate)
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", fake_flush)
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", fake_compose)
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "existing"})(),
    )

    result = ship.run_ship(
        _ctx(tmp_path, state_file=str(state_file), branch="feat", branch_name="feat"),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.OK
    assert order == ["gate", "flush", "compose"]
    assert json.loads(stale.read_text(encoding="utf-8"))["outcome"] == "pinned"


def test_open_pr_resume_guidelines_gate_needs_assessment_skips_flush_and_ensure_pr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = _prepare_open_pr_resume(monkeypatch, tmp_path)
    monkeypatch.setattr(
        ship,
        "load_or_prepare_guidelines_note",
        lambda **_kwargs: ship.GuidelinesGateResult(
            needs_assessment=True,
            detail="architectural-guidelines assessment required before PR body compose",
        ),
    )
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("flush_logs_pre must not run")))
    monkeypatch.setattr(ship.pr, "ensure_pr", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("ensure_pr must not run")))

    result = ship.run_ship(
        _ctx(tmp_path, state_file=str(state_file), branch="feat", branch_name="feat"),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == "architectural-guidelines-assessment"
    assert result.detail == "architectural-guidelines assessment required before PR body compose"
    assert not (tmp_path / ship.architectural_guidelines.GUIDELINE_SHIP_OUTCOME_SIDECAR).exists()


def test_open_pr_resume_guidelines_gate_dropped_outcome_stalls_before_compose_and_ensure_pr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = _prepare_open_pr_resume(monkeypatch, tmp_path)
    order: list[str] = []

    def fake_gate(**_kwargs: object) -> ship.GuidelinesGateResult:
        order.append("gate")
        return ship.GuidelinesGateResult(
            note="",
            guidelines_status="present",
            reason=ship_guidelines.REASON_COMPOSE_MATERIALIZATION_FAILED,
        )

    def fake_flush(*_args: object, **_kwargs: object) -> run_logs.RefreshSkip:
        order.append("flush")
        return run_logs.RefreshSkip(skipped=False, reason="")

    monkeypatch.setattr(ship, "load_or_prepare_guidelines_note", fake_gate)
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", fake_flush)
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("compose_pr_body must not run")))
    monkeypatch.setattr(ship.pr, "ensure_pr", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("ensure_pr must not run")))

    result = ship.run_ship(
        _ctx(tmp_path, state_file=str(state_file), branch="feat", branch_name="feat"),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.STALLED
    assert order == ["gate", "flush"]
    outcome = json.loads((tmp_path / ship.architectural_guidelines.GUIDELINE_SHIP_OUTCOME_SIDECAR).read_text(encoding="utf-8"))
    assert outcome["outcome"] == "dropped"
    assert outcome["reason"] == ship_guidelines.REASON_COMPOSE_MATERIALIZATION_FAILED


def test_open_pr_resume_no_logs_commit_keeps_guideline_outcome_sidecar_and_skips_flush(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = _prepare_open_pr_resume(monkeypatch, tmp_path)
    order: list[str] = []

    def fake_gate(**_kwargs: object) -> ship.GuidelinesGateResult:
        order.append("gate")
        return ship.GuidelinesGateResult(note="Guidelines warning", guidelines_status="present")

    def fake_compose(**_kwargs: object) -> str:
        order.append("compose")
        return "body"

    monkeypatch.setattr(ship, "load_or_prepare_guidelines_note", fake_gate)
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("flush_logs_pre must not run")))
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", fake_compose)
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "existing"})(),
    )

    result = ship.run_ship(
        _ctx(tmp_path, state_file=str(state_file), branch="feat", branch_name="feat", no_logs_commit=True),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert result.outcome is Outcome.OK
    assert order == ["gate", "compose"]
    outcome = json.loads((tmp_path / ship.architectural_guidelines.GUIDELINE_SHIP_OUTCOME_SIDECAR).read_text(encoding="utf-8"))
    assert outcome["outcome"] == "pinned"


def test_open_pr_resume_runs_guidelines_gate_before_compose(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = _prepare_open_pr_resume(monkeypatch, tmp_path)
    order: list[str] = []
    compose_calls: list[dict[str, object]] = []

    def fake_gate(**_kwargs: object) -> ship.GuidelinesGateResult:
        order.append("gate")
        return ship.GuidelinesGateResult(note="Resume note")

    def fake_flush(*_args: object, **_kwargs: object) -> run_logs.RefreshSkip:
        order.append("flush")
        return run_logs.RefreshSkip(skipped=False, reason="")

    def fake_compose(**kwargs: object) -> str:
        order.append("compose")
        compose_calls.append(dict(kwargs))
        return "body"

    monkeypatch.setattr(ship, "load_or_prepare_guidelines_note", fake_gate)
    monkeypatch.setattr(ship, "write_guideline_ship_outcome", lambda **_kw: None)
    monkeypatch.setattr(ship, "clear_guideline_ship_outcome_sidecar", lambda **_kw: None)
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", fake_flush)
    monkeypatch.setattr(ship.pr_body, "compose_pr_body", fake_compose)
    monkeypatch.setattr(
        ship.pr,
        "ensure_pr",
        lambda *_a, **_k: type("P", (), {"number": 7, "url": "https://example.test/pr/7", "status": "existing"})(),
    )
    result = ship.run_ship(
        _ctx(tmp_path, state_file=str(state_file), branch="feat", branch_name="feat"),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )
    assert result.outcome is Outcome.OK
    assert order == ["gate", "flush", "compose"]
    assert compose_calls[0].get("architectural_guidelines_note") == "Resume note"


def test_open_pr_resume_requests_reassessment_for_stale_durable_guidelines_note(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    def git(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr or completed.stdout
        return completed.stdout.strip()

    (repo / "README.md").write_text("base\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-m", "base")
    git("branch", "-M", "main")
    git("remote", "add", "origin", str(repo))
    git("remote", "add", "upstream", str(repo))
    head_sha = git("rev-parse", "HEAD")
    git("update-ref", "refs/remotes/origin/main", head_sha)
    git("update-ref", "refs/remotes/upstream/main", head_sha)
    git("switch", "-c", "feature")
    (repo / "README.md").write_text("base\nfeature\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-m", "feature")
    head_sha = git("rev-parse", "HEAD")
    diff_text = ship.architectural_guidelines.materialize_implementation_diff(repo, base_remote="origin", base_ref="main")
    ship.architectural_guidelines.write_implement_note(
        implement_tmpdir=tmp_path,
        note_text="Consulted note\n",
        head_sha=head_sha,
        metadata={
            "ASSESSED_HEAD_SHA": head_sha,
            "DIFF_FINGERPRINT": ship.architectural_guidelines.diff_fingerprint(diff_text),
            "BASE_REF": "origin/main",
        },
        base_ref="origin/main",
    )
    (tmp_path / ship.architectural_guidelines.MATERIALIZED_DIFF).write_text(diff_text, encoding="utf-8")
    tree_sha = git("rev-parse", "HEAD^{tree}")
    moved_main = subprocess.run(
        ["git", "-C", str(repo), "commit-tree", tree_sha, "-p", head_sha, "-m", "main advance"],
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    assert moved_main
    git("update-ref", "refs/remotes/origin/main", moved_main)
    git("update-ref", "refs/remotes/upstream/main", moved_main)
    state_file = tmp_path / "ship-pr-state.sh"
    state_file.write_text(
        "PHASE=ci-initial\nBRANCH_NAME=feature\nPR_NUMBER=7\nPR_URL=https://example.test/pr/7\nREPO=o/r\nMERGE=false\nDRAFT=false\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship_resume.git, "current_branch", lambda *_a, **_k: "feature")
    monkeypatch.setattr(
        ship_resume.gh,
        "pr_view",
        lambda *_a, **_k: type("PR", (), {"number": 7, "url": "https://example.test/pr/7", "state": "OPEN", "head_ref": "feature"})(),
    )
    monkeypatch.setattr(ship.run_logs, "flush_logs_pre", lambda *_a, **_k: run_logs.RefreshSkip(skipped=False, reason=""))
    monkeypatch.setattr(ship.run_logs, "write_final_report_comment", lambda *_a, **_k: None)
    monkeypatch.setattr(ship.finalize, "write_finalize_state", lambda *_a, **_k: None)
    assert ship.architectural_guidelines.note_fingerprint_stale(tmp_path, base_ref="origin/main", repo_root=repo)
    stale_gate = ship.GuidelinesGateResult(
        needs_assessment=True,
        detail="architectural-guidelines assessment required before PR body compose",
    )
    monkeypatch.setattr(ship, "load_or_prepare_guidelines_note", lambda **_kwargs: stale_gate)
    monkeypatch.setattr(ship.pr, "ensure_pr", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("ensure_pr must not run before reassessment")))

    result = ship.run_ship(
        _ctx(tmp_path, state_file=str(state_file), branch="feature", branch_name="feature", merge=False, repo="o/r"),
        runner=RecordingRunner(),
        cwd=str(repo),
    )

    assert result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.needs_user_reason == "architectural-guidelines-assessment"
    assert result.detail == "architectural-guidelines assessment required before PR body compose"


def test_guidelines_assessment_resume_without_pr_number_uses_pre_pr_compose(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    state_file.write_text(
        "PHASE=guidelines-assessment\nBRANCH_NAME=feat\nREPO=o/r\nMERGE=false\nDRAFT=false\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship_resume.git, "current_branch", lambda *_a, **_k: "feat")

    resume = ship_resume._resume_plan(
        ctx=_ctx(tmp_path, state_file=str(state_file), branch="feat", branch_name="feat", repo="o/r"),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert resume.start == "pre-pr-compose"
    assert resume.pr_number is None
    assert resume.pr_url == ""



def test_postmerge_repair_resume_preserves_repair_branch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    state_file.write_text(
        "PHASE=emergency-repair\nBRANCH_NAME=feat\nEMERGENCY_REPAIR_BRANCH=repair/feat\nPR_NUMBER=7\nPR_URL=https://example.test/pr/7\nREPO=o/r\nMERGE=true\nDRAFT=false\nMAIN_REPAIR_RUN_ID=44\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship_resume.git, "current_branch", lambda *_a, **_k: "repair/feat")

    resume = ship_resume._resume_plan(
        ctx=_ctx(tmp_path, state_file=str(state_file), branch="feat", branch_name="feat", repo="o/r"),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert resume.start == "emergency-repair"
    assert resume.branch_name == "repair/feat"
    assert resume.pr_number == 7


def test_postmerge_push_watch_resume_preserves_repair_branch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    state_file.write_text(
        "PHASE=postmerge-push-watch\nBRANCH_NAME=feat\nEMERGENCY_REPAIR_BRANCH=repair/feat\nPR_NUMBER=7\nPR_URL=https://example.test/pr/7\nREPO=o/r\nMERGE=true\nDRAFT=false\nMAIN_REPAIR_RUN_ID=44\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ship_resume.git, "current_branch", lambda *_a, **_k: "repair/feat")

    resume = ship_resume._resume_plan(
        ctx=_ctx(tmp_path, state_file=str(state_file), branch="feat", branch_name="feat", repo="o/r"),
        runner=RecordingRunner(),
        cwd=str(tmp_path),
    )

    assert resume.start == "postmerge-push-watch"
    assert resume.branch_name == "repair/feat"
    assert resume.pr_number == 7


def test_pin_and_load_guidelines_note_logs_redaction_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    diff_text = "implementation diff"
    ship.architectural_guidelines.write_staged_assessment(
        implement_tmpdir=tmp_path,
        assessment_text="note\n",
        assessed_head_sha="old",
        diff_fingerprint_value=ship.architectural_guidelines.diff_fingerprint(diff_text),
        base_ref="origin/main",
        diff_text=diff_text,
    )
    assert ship.architectural_guidelines.pin_note_from_staged(tmp_path, head_sha="head", base_ref="origin/main")

    def fail_redact(_body: str) -> str:
        msg = "redaction failed for PR body"
        raise ShipError(msg)

    monkeypatch.setattr(ship.pr_body, "redact_pr_body", fail_redact)
    assert _pin_guidelines_note_text(implement_tmpdir=str(tmp_path), head_sha="head", base_ref="origin/main") == ""
    issues = (tmp_path / "execution-issues.md").read_text(encoding="utf-8")
    assert "architectural-guidelines note redaction failed" in issues


def test_guidelines_warning_append_failure_warns_stderr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    diff_text = "implementation diff"
    ship.architectural_guidelines.write_staged_assessment(
        implement_tmpdir=tmp_path,
        assessment_text="note\n",
        assessed_head_sha="old",
        diff_fingerprint_value=ship.architectural_guidelines.diff_fingerprint(diff_text),
        base_ref="origin/main",
        diff_text=diff_text,
    )
    assert ship.architectural_guidelines.pin_note_from_staged(tmp_path, head_sha="head", base_ref="origin/main")

    def fail_redact(_body: str) -> str:
        raise ShipError("redaction failed for PR body")

    def fail_append(*_args: object, **_kwargs: object) -> None:
        raise OSError("append failed")

    monkeypatch.setattr(ship.pr_body, "redact_pr_body", fail_redact)
    monkeypatch.setattr(ship.run_logs, "append_execution_issue", fail_append)

    note, warning_logged = ship._pin_and_load_guidelines_note(
        implement_tmpdir=str(tmp_path),
        head_sha="head",
        base_ref="origin/main",
    )

    captured = capsys.readouterr()
    assert note == ""
    assert warning_logged is False
    assert "architectural-guidelines warning append failed: append failed" in captured.err
# pyright: reportUnusedFunction=false
