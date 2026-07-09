from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

from larch.calibration import difficulty
from larch.core import config
from larch.core.proc import CommandResult
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


def test_run_log_commit_all_required_artifacts_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir)
    _ = (run_dir / "token-report.json").write_text("{}", encoding="utf-8")
    _ = (run_dir / "session-transcript.jsonl").write_text("{}\n", encoding="utf-8")

    result, copied = _commit_tmp_run(tmp_path, monkeypatch)

    assert result.returncode == 0
    assert copied == ["implement/run-abc"]


def test_run_log_commit_allows_recorded_transcript_omission(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir)
    _ = (run_dir / "token-report.json").write_text("{}", encoding="utf-8")
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
    _write_manifest(run_dir)
    _ = (run_dir / "token-report.json").write_text("{}", encoding="utf-8")

    result, copied = _commit_tmp_run(tmp_path, monkeypatch)

    assert result.returncode == config.RUN_LOG_INCOMPLETE_RC
    assert "session-transcript.jsonl" in result.stderr
    assert not copied


def test_run_log_commit_rejects_session_local_status_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir)
    _ = (run_dir / "token-report.json").write_text("{}", encoding="utf-8")
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


def test_flush_logs_pre_maps_incomplete_commit_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir)
    _ = (run_dir / "token-report.json").write_text("{}", encoding="utf-8")
    ctx = make_run_context(
        run_id="run-abc",
        tmpdir=str(tmp_path),
        manifest_path=str(run_dir / "manifest.json"),
    )
    monkeypatch.setattr(run_log_flush, "_stage_pre_commit", lambda **_kwargs: None)
    _ = _patch_commit_seams(monkeypatch, tmp_path)

    skip = run_log_flush.flush_logs_pre(runner=run_log_flush.proc, ctx=ctx, cwd=str(tmp_path / "repo"))

    assert skip.skipped is True
    assert skip.reason == config.REFRESH_SKIP_RUN_LOG_INCOMPLETE
    assert "session-transcript.jsonl" in skip.error


def test_refresh_run_logs_main_prints_incomplete_reason(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    state = tmp_path / "finalize-state.sh"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    monkeypatch.setattr(
        run_log_flush,
        "flush_logs_pre",
        lambda **_kwargs: RefreshSkip(
            skipped=True,
            reason=config.REFRESH_SKIP_RUN_LOG_INCOMPLETE,
            error="missing transcript",
        ),
    )

    rc = run_log_flush.refresh_run_logs_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    assert "REFRESH_COMMITTED=false REASON=run-log-incomplete ERROR=missing transcript" in capsys.readouterr().out


def test_larch_log_flush_main_returns_incomplete_rc(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir)
    _ = (run_dir / "token-report.json").write_text("{}", encoding="utf-8")
    _ = (tmp_path / "session-id").write_text("run-abc\n", encoding="utf-8")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setattr(run_log_flush, "_stage_pre_commit", lambda **_kwargs: None)
    _ = _patch_commit_seams(monkeypatch, tmp_path)

    rc = run_log_flush.larch_log_flush_main([])

    assert rc == config.RUN_LOG_INCOMPLETE_RC
    assert "session-transcript.jsonl" in capsys.readouterr().err


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
