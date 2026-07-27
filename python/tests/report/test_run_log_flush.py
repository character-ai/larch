from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from larch.calibration import difficulty
from larch.core import config
from larch.core.proc import CommandResult
from larch.errors import ShipError
from larch.report import run_log_commit
from larch.report import run_log_flush
from larch.report.run_log_manifest import RefreshSkip

from test_support import make_run_context


def _write_manifest(run_dir: Path, *, skill: str = "implement", steps_ran: dict[str, object] | None = None) -> None:
    payload: dict[str, object] = {
        "schema_version": 2,
        "skill": skill,
        "run_id": run_dir.name,
        "steps_ran": steps_ran or {},
        "status": "partial",
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    _ = (run_dir / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_terminal_artifacts(run_dir: Path) -> None:
    _ = (run_dir / "final-summary.md").write_text("# Final\n", encoding="utf-8")
    _ = (run_dir / "token-report.json").write_text("{}", encoding="utf-8")
    _ = (run_dir / "timing-report.json").write_text("{}", encoding="utf-8")
    _ = (run_dir / "execution-issues.ndjson").write_text("", encoding="utf-8")


def _patch_commit_seams(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _ = subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    copied: list[str] = []
    monkeypatch.setattr(run_log_commit, "_publish_breadcrumbs_with_warning", lambda **_kwargs: None)

    def fake_git_stdout(argv: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        _ = cwd
        if argv[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return subprocess.CompletedProcess(argv, 0, "feature\n", "")
        if argv[:3] == ["git", "symbolic-ref", "--short"]:
            return subprocess.CompletedProcess(argv, 0, "origin/main\n", "")
        if argv[:3] == ["git", "status", "--porcelain"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        raise AssertionError(f"unexpected git argv: {argv}")

    def fake_copy_tree_to_repo(
        *,
        log_root: Path,
        repo_root: Path,
        skill: str,
        run_id: str,
    ) -> tuple[list[str], Path, int, str | None]:
        _ = log_root
        copied.append(f"{skill}/{run_id}")
        return [f"larch-logs/{skill}/{run_id}"], repo_root / "larch-logs" / skill / run_id, 0, None

    monkeypatch.setattr(run_log_commit, "_git_stdout", fake_git_stdout)
    monkeypatch.setattr(run_log_commit, "_copy_tree_to_repo", fake_copy_tree_to_repo)
    return copied


def _commit_tmp_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, run_id: str = "run-abc") -> tuple[CommandResult, list[str]]:
    copied = _patch_commit_seams(monkeypatch, tmp_path)
    result = run_log_commit._commit_run(  # pyright: ignore[reportPrivateUsage]
        log_root=tmp_path / "larch-logs",
        skill="implement",
        run_id=run_id,
        cwd=str(tmp_path / "repo"),
    )
    return result, copied


def test_refresh_difficulty_record_merges_resolution_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = tmp_path / "implement" / "run-1"
    run_dir.mkdir(parents=True)
    record_path = run_dir / difficulty.DIFFICULTY_RECORD_BASENAME
    existing = difficulty.build_record(
        rater="implement",
        rater_tool="claude",
        rater_model="unknown",
        implement_rating=difficulty.validate_rating_object(
            {"predicted_tier": "TRIVIAL", "confidence": "high", "rationale": "bootstrap"}
        ),
        override_tier="HARD",
        audit_upgrade="true",
        escalations=(
            {"round": 2, "from_tier": "MODERATE", "to_tier": "HARD", "trigger": "bulk-skip"},
        ),
        panel_tier="HARD",
        round_cap=2,
        codex_model_role="default",
        audit_evaluated=True,
        escalated_round=True,
    )
    difficulty.write_record(record_path, existing)

    monkeypatch.setattr(run_log_flush, "effective_run_id", lambda _ctx: "run-1")
    monkeypatch.setattr(run_log_flush, "_write_batch", lambda **_kwargs: None)

    def fake_run(argv: list[str], *, cwd: str | None = None, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if argv[:3] == ["git", "diff", "--name-only"]:
            assert cwd == str(tmp_path)
            return subprocess.CompletedProcess(argv, 0, "hooks/pre-tool-use.sh\n", "")
        raise AssertionError(f"unexpected command: {argv}")

    monkeypatch.setattr(run_log_flush.proc, "run", fake_run)

    run_log_flush._refresh_difficulty_record(ctx=object(), log_root=tmp_path, cwd=str(tmp_path))  # pyright: ignore[reportPrivateUsage]
    data = json.loads(record_path.read_text(encoding="utf-8"))

    assert data["override_source"] == "operator"
    assert data["panel_tier"] == "HARD"
    assert data["round_cap"] == 2
    assert data["codex_model_role"] == "default"
    assert data["audit_evaluated"] is True
    assert data["escalated_round"] is True
    assert data["escalations"][0]["round"] == 2


def test_prepare_terminal_snapshot_orders_complete_final_refresh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "run-abc"
    run_dir = tmp_path / "larch-logs" / "implement" / run_id
    run_dir.mkdir(parents=True)
    ctx = make_run_context(run_id=run_id, tmpdir=str(tmp_path), manifest_path=str(run_dir / "manifest.json"))
    events: list[str] = []
    updates: list[dict[str, object]] = []
    recovery = SimpleNamespace(recovery_ok=True, manifest=SimpleNamespace(steps_ran={}))

    def write_final_report(**_kwargs: object) -> None:
        events.append("final-report")
        _ = (run_dir / "final-summary.md").write_text("# Final\n", encoding="utf-8")

    def render_ledgers(**_kwargs: object) -> None:
        events.append("token-timing-ledgers")
        _ = (run_dir / "token-report.json").write_text("{}\n", encoding="utf-8")
        _ = (run_dir / "timing-report.json").write_text("{}\n", encoding="utf-8")

    def capture(**_kwargs: object) -> run_log_flush.TranscriptCaptureResult:
        events.append("transcript")
        path = run_dir / "session-transcript.jsonl"
        _ = path.write_text("{}\n", encoding="utf-8")
        return run_log_flush.TranscriptCaptureResult(status="captured", path=path, source_configured=True)

    def flush_issues(**_kwargs: object) -> None:
        events.append("execution-issues")
        _ = (run_dir / "execution-issues.ndjson").write_text("", encoding="utf-8")

    monkeypatch.setattr(run_log_flush, "_load_refresh_session_env", lambda _tmpdir: None)
    monkeypatch.setattr(run_log_flush, "_refresh_context", lambda **_kwargs: ctx)
    monkeypatch.setattr(run_log_flush, "load_or_recover_manifest_checked", lambda _ctx: recovery)
    monkeypatch.setattr(run_log_flush, "_refresh_difficulty_record", lambda **_kwargs: events.append("difficulty"))
    monkeypatch.setattr(run_log_flush, "_write_final_report", write_final_report)
    monkeypatch.setattr(
        run_log_flush, "_reconcile_stalled_summary_backstop", lambda **_kwargs: events.append("stalled-summary")
    )
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", render_ledgers)
    monkeypatch.setattr(
        run_log_flush, "_render_token_timing_batches", lambda **_kwargs: events.append("derived-token-timing")
    )
    monkeypatch.setattr(run_log_flush, "_stage_vendor_failure_diagnostics", lambda **_kwargs: events.append("vendor"))
    monkeypatch.setattr(run_log_flush, "_stage_invariant_ship_outcome", lambda **_kwargs: events.append("invariant"))
    monkeypatch.setattr(run_log_flush, "_stage_guideline_ship_outcome", lambda **_kwargs: events.append("guideline"))
    monkeypatch.setattr(run_log_flush, "_stage_ship_route_handoff", lambda **_kwargs: events.append("ship-handoff"))
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", capture)
    monkeypatch.setattr(run_log_flush, "_terminal_execution_issues_flush", flush_issues)
    monkeypatch.setattr(
        run_log_flush, "_reconcile_terminal_manifest_from_ctx", lambda _ctx: events.append("manifest-reconcile")
    )
    monkeypatch.setattr(run_log_flush, "update_manifest", lambda _ctx, **kwargs: updates.append(kwargs))

    result = run_log_flush.prepare_terminal_snapshot(
        runner=object(),  # type: ignore[arg-type]
        tmpdir=tmp_path,
        run_id=run_id,
    )

    assert result.ok is True
    assert result.transcript_status == "captured"
    assert events == [
        "difficulty",
        "final-report",
        "stalled-summary",
        "token-timing-ledgers",
        "derived-token-timing",
        "vendor",
        "invariant",
        "guideline",
        "ship-handoff",
        "transcript",
        "execution-issues",
        "final-report",
        "manifest-reconcile",
    ]
    assert updates == [{"steps_ran": {"step18": True}}]


def test_prepare_terminal_snapshot_failure_preserves_staging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_id = "run-abc"
    run_dir = tmp_path / "larch-logs" / "implement" / run_id
    run_dir.mkdir(parents=True)
    prior = run_dir / "session-transcript.jsonl"
    _ = prior.write_text('{"prior":true}\n', encoding="utf-8")
    ctx = make_run_context(run_id=run_id, tmpdir=str(tmp_path), manifest_path=str(run_dir / "manifest.json"))
    recovery = SimpleNamespace(recovery_ok=True, manifest=SimpleNamespace(steps_ran={}))
    recorded: list[str] = []

    monkeypatch.setattr(run_log_flush, "_load_refresh_session_env", lambda _tmpdir: None)
    monkeypatch.setattr(run_log_flush, "_refresh_context", lambda **_kwargs: ctx)
    monkeypatch.setattr(run_log_flush, "load_or_recover_manifest_checked", lambda _ctx: recovery)
    monkeypatch.setattr(run_log_flush, "_refresh_difficulty_record", lambda **_kwargs: None)
    monkeypatch.setattr(run_log_flush, "_write_final_report", lambda **_kwargs: None)
    monkeypatch.setattr(run_log_flush, "_reconcile_stalled_summary_backstop", lambda **_kwargs: None)
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", lambda **_kwargs: None)
    monkeypatch.setattr(run_log_flush, "_render_token_timing_batches", lambda **_kwargs: None)
    monkeypatch.setattr(run_log_flush, "_stage_vendor_failure_diagnostics", lambda **_kwargs: None)
    monkeypatch.setattr(run_log_flush, "_stage_invariant_ship_outcome", lambda **_kwargs: None)
    monkeypatch.setattr(run_log_flush, "_stage_guideline_ship_outcome", lambda **_kwargs: None)
    monkeypatch.setattr(run_log_flush, "_stage_ship_route_handoff", lambda **_kwargs: None)
    monkeypatch.setattr(
        run_log_flush,
        "capture_session_transcript",
        lambda **_kwargs: run_log_flush.TranscriptCaptureResult(
            status="source-file-missing", path=prior, source_configured=True
        ),
    )
    monkeypatch.setattr(
        run_log_flush, "_record_terminal_snapshot_failure", lambda *, message, **_kwargs: recorded.append(message)
    )

    result = run_log_flush.prepare_terminal_snapshot(
        runner=object(),  # type: ignore[arg-type]
        tmpdir=tmp_path,
        run_id=run_id,
    )

    assert result.ok is False
    assert result.transcript_status == "source-file-missing"
    assert recorded == [
        "terminal transcript refresh failed: status=source-file-missing; "
        "the prior staged transcript was retained when available"
    ]
    assert prior.read_text(encoding="utf-8") == '{"prior":true}\n'


def test_unconfigured_terminal_transcript_requires_artifact_or_recorded_waiver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "run-abc"
    ctx = make_run_context(run_id=run_id, tmpdir=str(tmp_path), manifest_path="")
    monkeypatch.delenv("LARCH_CLAUDE_SOURCE_FILE", raising=False)
    monkeypatch.setattr(
        run_log_flush,
        "_capture_transcript_append_warning",
        lambda **_kwargs: False,
    )

    result = run_log_flush.capture_session_transcript(ctx=ctx, runner=object())  # type: ignore[arg-type]

    assert result.status == "source-not-configured"
    assert result.artifact_present is False
    assert result.omission_recorded is False
    assert result.ok is False


def test_run_log_commit_all_required_artifacts_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir, steps_ran={"step18": True})
    _write_terminal_artifacts(run_dir)
    _ = (run_dir / "session-transcript.jsonl").write_text("{}\n", encoding="utf-8")

    result, copied = _commit_tmp_run(tmp_path, monkeypatch)

    assert result.returncode == 0
    assert copied == ["implement/run-abc"]


def test_run_log_commit_allows_recorded_transcript_omission(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir, steps_ran={"step18": True})
    _write_terminal_artifacts(run_dir)
    body = "- **Step 7a: session-transcript status=write-failed:** source file disappeared"
    _ = (run_dir / "execution-issues.ndjson").write_text(
        json.dumps({"category": "Warnings", "body": body}) + "\n",
        encoding="utf-8",
    )

    result, copied = _commit_tmp_run(tmp_path, monkeypatch)

    assert result.returncode == 0
    assert copied == ["implement/run-abc"]


def test_run_log_commit_fails_silent_transcript_omission(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir, steps_ran={"step18": True})
    _write_terminal_artifacts(run_dir)

    result, copied = _commit_tmp_run(tmp_path, monkeypatch)

    assert result.returncode == config.RUN_LOG_INCOMPLETE_RC
    assert "session-transcript.jsonl" in result.stderr
    assert not copied


def test_run_log_commit_rejects_session_local_status_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir, steps_ran={"step18": True})
    _write_terminal_artifacts(run_dir)
    _ = (tmp_path / "execution-issues.md").write_text(
        "### Warnings\n- **Step 7a: session-transcript status=write-failed:** source file disappeared\n",
        encoding="utf-8",
    )

    result, copied = _commit_tmp_run(tmp_path, monkeypatch)

    assert result.returncode == config.RUN_LOG_INCOMPLETE_RC
    assert "session-transcript.jsonl" in result.stderr
    assert not copied


def test_run_log_commit_code_review_tally_requires_full_findings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir)
    _ = (run_dir / "code-review-tally.json").write_text("{}", encoding="utf-8")

    result, copied = _commit_tmp_run(tmp_path, monkeypatch)

    assert result.returncode == config.RUN_LOG_INCOMPLETE_RC
    assert "review-findings-full.jsonl" in result.stderr
    assert not copied


def test_run_log_commit_step7a_without_code_review_does_not_require_full_findings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir)
    _ = (run_dir / "token-report.json").write_text("{}", encoding="utf-8")
    _ = (run_dir / "session-transcript.jsonl").write_text("{}\n", encoding="utf-8")

    result, copied = _commit_tmp_run(tmp_path, monkeypatch)

    assert result.returncode == 0
    assert copied == ["implement/run-abc"]


def test_preterminal_outcome_label_check_rejects_terminal_labels() -> None:
    for label in ("stalled", "bailed", "bailed-needs-user-input"):
        with pytest.raises(ShipError, match="pre-terminal"):
            run_log_flush._check_preterminal_outcome_label(label)  # pyright: ignore[reportPrivateUsage]

    for label in ("shipping", "in-progress", "pr-created"):
        run_log_flush._check_preterminal_outcome_label(label)  # pyright: ignore[reportPrivateUsage]


def test_parse_preterminal_outcome_label_targets_run_heading() -> None:
    assert (
        run_log_flush._parse_preterminal_outcome_label(  # pyright: ignore[reportPrivateUsage]
            "# Prelude\n\n## /implement final summary: stalled\n",
        )
        == "stalled"
    )
    assert (
        run_log_flush._parse_preterminal_outcome_label(  # pyright: ignore[reportPrivateUsage]
            "## /implement final summary — bailed-needs-user-input\n",
        )
        == "bailed-needs-user-input"
    )
    assert (
        run_log_flush._parse_preterminal_outcome_label(  # pyright: ignore[reportPrivateUsage]
            "## Architectural notes: stalled\n\n## /implement final summary: shipping\n",
        )
        == "shipping"
    )
    assert (
        run_log_flush._parse_preterminal_outcome_label(  # pyright: ignore[reportPrivateUsage]
            "## /implement final summary\n\n## /implement final summary: stalled\n",
        )
        == "stalled"
    )


def test_refresh_logs_checkpoint_stages_preterminal_forbidden_label_without_publishing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir)
    _ = (run_dir / "final-summary.md").write_text("## /implement final summary: stalled\n", encoding="utf-8")
    ctx = make_run_context(
        run_id="run-abc",
        tmpdir=str(tmp_path),
        manifest_path=str(run_dir / "manifest.json"),
    )
    monkeypatch.setattr(run_log_flush, "_stage_local_checkpoint", lambda **_kwargs: None)

    def fail_commit(**_kwargs: object) -> CommandResult:
        raise AssertionError("mutable refresh must not publish through Git")

    monkeypatch.setattr(run_log_flush, "_commit_run", fail_commit, raising=False)

    skip = run_log_flush.refresh_logs_checkpoint(runner=run_log_flush.proc, ctx=ctx, cwd=str(tmp_path))

    assert skip.skipped is False


def test_refresh_logs_checkpoint_stages_neutral_preterminal_label_without_publishing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir)
    _ = (run_dir / "final-summary.md").write_text("## /implement final summary: shipping\n", encoding="utf-8")
    ctx = make_run_context(
        run_id="run-abc",
        tmpdir=str(tmp_path),
        manifest_path=str(run_dir / "manifest.json"),
    )
    commits: list[str] = []
    monkeypatch.setattr(run_log_flush, "_stage_local_checkpoint", lambda **_kwargs: None)

    def fake_commit(**_kwargs: object) -> CommandResult:
        commits.append("commit")
        return CommandResult(("git", "commit"), 0, "a" * 40 + "\n", "", 0.0)

    monkeypatch.setattr(run_log_flush, "_commit_run", fake_commit, raising=False)

    skip = run_log_flush.refresh_logs_checkpoint(runner=run_log_flush.proc, ctx=ctx, cwd=str(tmp_path))

    assert skip.skipped is False
    assert not commits


def test_refresh_logs_checkpoint_keeps_incomplete_tree_mutable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir)
    _ = (run_dir / "token-report.json").write_text("{}", encoding="utf-8")
    ctx = make_run_context(
        run_id="run-abc",
        tmpdir=str(tmp_path),
        manifest_path=str(run_dir / "manifest.json"),
    )
    monkeypatch.setattr(run_log_flush, "_stage_local_checkpoint", lambda **_kwargs: None)
    _ = _patch_commit_seams(monkeypatch, tmp_path)

    skip = run_log_flush.refresh_logs_checkpoint(runner=run_log_flush.proc, ctx=ctx, cwd=str(tmp_path / "repo"))

    assert skip.skipped is False


def test_refresh_run_logs_main_prints_incomplete_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    state = tmp_path / "finalize-state.sh"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    monkeypatch.setattr(
        run_log_flush,
        "refresh_logs_checkpoint",
        lambda **_kwargs: RefreshSkip(
            skipped=True, reason=config.REFRESH_SKIP_RUN_LOG_INCOMPLETE, error="missing transcript"
        ),
    )

    rc = run_log_flush.refresh_run_logs_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    assert "REFRESH_COMMITTED=false REASON=run-log-incomplete ERROR=missing transcript" in capsys.readouterr().out


def test_run_log_checkpoint_main_keeps_incomplete_tree_mutable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir)
    _ = (run_dir / "token-report.json").write_text("{}", encoding="utf-8")
    _ = (tmp_path / "session-id").write_text("run-abc\n", encoding="utf-8")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setattr(run_log_flush, "_stage_local_checkpoint", lambda **_kwargs: None)
    _ = _patch_commit_seams(monkeypatch, tmp_path)

    rc = run_log_flush.run_log_checkpoint_main([])

    assert rc == 0
    assert capsys.readouterr().err == ""


def test_run_log_checkpoint_main_stages_preterminal_forbidden_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir)
    _ = (run_dir / "final-summary.md").write_text("## /implement final summary: bailed\n", encoding="utf-8")
    _ = (tmp_path / "session-id").write_text("run-abc\n", encoding="utf-8")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setattr(run_log_flush, "_stage_local_checkpoint", lambda **_kwargs: None)

    def fail_commit(**_kwargs: object) -> CommandResult:
        raise AssertionError("pre-terminal guard should skip commit")

    monkeypatch.setattr(run_log_flush, "_commit_run", fail_commit, raising=False)

    rc = run_log_flush.run_log_checkpoint_main([])

    assert rc == 0
    assert capsys.readouterr().err == ""


def test_run_log_commit_missing_run_dir_preserves_noop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    copied = _patch_commit_seams(monkeypatch, tmp_path)

    def fake_copy_tree_to_repo(
        *,
        log_root: Path,
        repo_root: Path,
        skill: str,
        run_id: str,
    ) -> tuple[list[str], Path, int, str | None]:
        _ = log_root, skill, run_id
        copied.append("copy-called")
        return [], repo_root / "larch-logs" / "implement" / "run-abc", 0, None

    monkeypatch.setattr(run_log_commit, "_copy_tree_to_repo", fake_copy_tree_to_repo)

    result = run_log_commit._commit_run(  # pyright: ignore[reportPrivateUsage]
        log_root=tmp_path / "larch-logs",
        skill="implement",
        run_id="run-abc",
        cwd=str(tmp_path / "repo"),
    )

    assert result.returncode == 0
    assert result.returncode != config.RUN_LOG_INCOMPLETE_RC
    assert copied == ["copy-called"]


# pyright: reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportArgumentType=false
