"""Tests for run_logs.py."""

from __future__ import annotations

import contextlib
import json
import subprocess
from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import cast

import pytest

import config
import run_logs
import timing
import tokens
from errors import ShipError
from proc import CommandResult
from run_context import RunContext

from test_support import RecordingRunner as _RecordingRunner, make_run_context


class RecordingRunner(_RecordingRunner):
    git_commits: int = 0

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
        if tuple(argv[:3]) == ("git", "commit", "-m"):
            self.git_commits += 1
        return super().run(
            argv,
            timeout=timeout,
            cwd=cwd,
            env=env,
            check=check,
            stdout=stdout,
            stderr=stderr,
        )


def _ctx(tmp_path: Path, state_file: str | None = None) -> RunContext:
    return make_run_context(
        run_id="run-abc",
        tmpdir=str(tmp_path),
        manifest_path=str(tmp_path / "manifest.json"),
        state_file=state_file,
    )


def test_validate_run_id_slug() -> None:
    assert run_logs.validate_run_id_slug("run-1")
    assert not run_logs.validate_run_id_slug("../evil")


def test_flush_logs_pre_state_file_less_requires_repo_cwd(tmp_path: Path) -> None:
    runner = RecordingRunner()
    skip = run_logs.flush_logs_pre(runner, _ctx(tmp_path), cwd=None)
    assert skip.skipped
    assert skip.reason == config.REFRESH_SKIP_NO_REPO_CWD


def test_flush_logs_pre_state_file_less_commits_with_repo_cwd(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = RecordingRunner()

    def fake_commit(
        _runner: RecordingRunner,
        _ctx_obj: RunContext,
        _log_root: Path,
        *,
        cwd: str | None = None,
    ) -> CommandResult:
        assert cwd == str(tmp_path)
        runner.git_commits += 1
        return CommandResult(("git", "commit"), 0, "", "", 0.01)

    monkeypatch.setattr(run_logs, "_commit_run", fake_commit)
    skip = run_logs.flush_logs_pre(runner, _ctx(tmp_path), cwd=str(tmp_path))
    assert not skip.skipped
    assert runner.git_commits == 1


def test_flush_logs_pre_skips_post_merge(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("MERGE_RESULT=merged\nRUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner()
    skip = run_logs.flush_logs_pre(runner, _ctx(tmp_path, str(state)))
    assert skip.reason == config.REFRESH_SKIP_POST_MERGE


def test_flush_logs_post_no_git_commit(tmp_path: Path) -> None:
    runner = RecordingRunner()
    ctx = _ctx(tmp_path).with_(pr_number=17)
    _ = run_logs.init_run(ctx)
    _ = run_logs.flush_logs_post(ctx, merge_result=config.MERGE_RESULT_MERGED)
    assert runner.git_commits == 0
    manifest_path = tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == config.MANIFEST_STATUS_DONE
    assert manifest["pr_number"] == 17
    assert "pr_number" not in manifest["steps_ran"]


def test_flush_logs_post_does_not_write_done_manifest_before_reports(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ctx = _ctx(tmp_path).with_(pr_number=17)
    _ = run_logs.init_run(ctx)

    def fail_report(*_a: object, **_k: object) -> None:
        raise ShipError("write-final-report failed")

    monkeypatch.setattr(run_logs, "_write_final_report", fail_report)
    skip = run_logs.flush_logs_post(
        ctx,
        merge_result=config.MERGE_RESULT_MERGED,
        runner=RecordingRunner(),
    )
    manifest_path = tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert skip.skipped is True
    assert manifest["status"] == config.MANIFEST_STATUS_PARTIAL
    assert "pr_number" not in manifest


def test_flush_logs_post_manifest_write_oserror_returns_recovery_skip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ctx = _ctx(tmp_path)
    _ = run_logs.init_run(ctx)

    def boom(*_a: object, **_k: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(run_logs, "_write_manifest", boom)
    skip = run_logs.flush_logs_post(ctx, merge_result=config.MERGE_RESULT_MERGED)
    assert skip.skipped is True
    assert skip.reason == run_logs.REFRESH_SKIP_RECOVERY_FAILED


def test_flush_logs_post_leaves_partial_on_failed_merge(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    _ = run_logs.init_run(ctx)
    _ = run_logs.flush_logs_post(ctx, merge_result=config.MERGE_RESULT_ERROR)
    manifest_path = tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == config.MANIFEST_STATUS_PARTIAL


def test_load_or_recover_manifest_from_log_dir(tmp_path: Path) -> None:
    log_dir = tmp_path / "larch-logs" / "implement" / "recovered-run"
    log_dir.mkdir(parents=True)
    ctx = _ctx(tmp_path).with_(run_id="../invalid")
    manifest = run_logs.load_or_recover_manifest(ctx)
    assert manifest.run_id == ""


def test_load_or_recover_manifest_absent_run_dir_tags_partial(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=lost-run\nISSUE_NUMBER=123\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    recovered = run_logs.load_or_recover_manifest_checked(ctx)
    assert recovered.recovery_ok
    assert recovered.manifest.status == config.MANIFEST_STATUS_PARTIAL
    assert recovered.manifest.extra == {
        "recovery_reason": "manifest_lost_mid_run",
        "issue_number": 123,
    }
    manifest_path = tmp_path / "larch-logs" / "implement" / "lost-run" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 2
    assert manifest["run_id"] == "lost-run"
    assert manifest["steps_ran"] == {}
    assert manifest["issue_number"] == 123


def test_effective_run_id_prefers_state_file(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=state-run\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    assert run_logs.effective_run_id(ctx) == "state-run"


def test_effective_run_id_rejects_unvalidated_ctx_run_id(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path).with_(run_id="../../../outside")
    assert run_logs.effective_run_id(ctx) == ""


def test_read_resume_counters_absent_and_corrupt_values(tmp_path: Path) -> None:
    assert run_logs.read_resume_counters(None) == run_logs.ResumeCounters(0, 0, 0, 0)
    state = tmp_path / "state.env"
    _ = state.write_text(
        "ITERATION=10\nREBASE_COUNT=bad\nFIX_ATTEMPTS=\nTRANSIENT_RETRIES=3\n",
        encoding="utf-8",
    )

    assert run_logs.read_resume_counters(str(state)) == run_logs.ResumeCounters(10, 0, 0, 3)


def test_read_durable_flags_state_first_and_forked_target_implies_forked(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path).with_(repo_unavailable=False, forked=False, forked_target=False, merge=True, draft=False)
    assert run_logs.read_durable_flags(None, ctx) == run_logs.DurableFlags(
        repo_unavailable=False,
        forked_target=False,
        forked=False,
        merge=True,
        draft=False,
    )
    state = tmp_path / "state.env"
    _ = state.write_text(
        "REPO_UNAVAILABLE=true\nFORKED_TARGET=true\nMERGE=false\nDRAFT=maybe\n",
        encoding="utf-8",
    )

    assert run_logs.read_durable_flags(str(state), ctx) == run_logs.DurableFlags(
        repo_unavailable=True,
        forked_target=True,
        forked=True,
        merge=False,
        draft=False,
    )


def test_read_durable_flags_persisted_false_overrides_stale_ctx_forked(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path).with_(forked=True, forked_target=True)
    state = tmp_path / "state.env"
    _ = state.write_text("FORKED_TARGET=false\n", encoding="utf-8")

    assert run_logs.read_durable_flags(str(state), ctx).forked is False


def test_parse_pr_number_state_first_and_ctx_fallback(tmp_path: Path) -> None:
    assert run_logs.parse_pr_number(None, 7) is None
    state = tmp_path / "state.env"
    _ = state.write_text("PR_NUMBER=\n", encoding="utf-8")
    assert run_logs.parse_pr_number(str(state), "8") is None
    _ = state.write_text("PR_NUMBER=0\n", encoding="utf-8")
    assert run_logs.parse_pr_number(str(state), "8") is None
    _ = state.write_text("PR_NUMBER=9\n", encoding="utf-8")
    assert run_logs.parse_pr_number(str(state), None) == 9


def test_manifest_status_read_only_uses_effective_run_id_path(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=state-run\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state)).with_(run_id="ctx-run")
    assert run_logs.manifest_status(ctx) == ""
    manifest = tmp_path / "larch-logs" / "implement" / "state-run" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    _ = manifest.write_text('{"status":"done"}', encoding="utf-8")
    assert run_logs.manifest_status(ctx) == "done"
    manifest = tmp_path / "larch-logs" / "implement" / "ctx-run" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    _ = manifest.write_text('{"status":"done"}', encoding="utf-8")
    assert run_logs.manifest_status(ctx) == "done"
    _ = (tmp_path / "larch-logs" / "implement" / "state-run" / "manifest.json").write_text("{", encoding="utf-8")
    assert run_logs.manifest_status(ctx) == ""


def test_execution_issues_batch_from_markdown(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    _ = (tmp_path / "execution-issues.md").write_text(
        "### Tool Failures\nline one\n",
        encoding="utf-8",
    )
    _ = (tmp_path / ".execution-issues-step7a-reached").write_text("", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    batch_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    batch_dir.mkdir(parents=True)
    run_logs._render_execution_issues_batch(  # pyright: ignore[reportPrivateUsage]
        ctx,
        batch_dir,
        step_label="pre-push",
        source_label="test",
    )
    batch = batch_dir / "execution-issues.ndjson"
    assert batch.is_file()
    text = batch.read_text(encoding="utf-8")
    assert "Tool Failures" in text
    assert "-----BEGIN" not in text


def test_execution_issues_batch_redacts_pem(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    secret = "ghp_" + "abcdefghijklmnopqrstuvwxyz1234567890ABCD"
    _ = (tmp_path / "execution-issues.md").write_text(
        f"### Tool Failures\n{secret}\n",
        encoding="utf-8",
    )
    _ = (tmp_path / ".execution-issues-step7a-reached").write_text("", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    batch_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    batch_dir.mkdir(parents=True)
    run_logs._render_execution_issues_batch(  # pyright: ignore[reportPrivateUsage]
        ctx,
        batch_dir,
        step_label="pre-push",
        source_label="test",
    )
    batch = batch_dir / "execution-issues.ndjson"
    assert batch.is_file()
    assert secret not in batch.read_text(encoding="utf-8")


def test_load_or_recover_manifest_invalid_json(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "execution-issues.ndjson").write_text("{}\n", encoding="utf-8")
    _ = (run_dir / "manifest.json").write_text("{not-json", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    manifest = run_logs.load_or_recover_manifest(ctx)
    assert manifest.run_id == "run-abc"
    assert manifest.steps_ran.get("recovered") is True


def test_token_batch_refresh_json_not_written_to_batch_dir(tmp_path: Path) -> None:
    # Refresh JSON files are volatile in-loop snapshots and must NOT be copied
    # into the committed run tree (issue #3708 Phase 1).  This test verifies
    # the PEM-containing edge case: even with bad content in the refresh file,
    # nothing is written to batch_dir under the refresh basename.
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    pem = "-----BEGIN RSA " + "PRIVATE KEY-----\nMIIB\n"
    _ = (tmp_path / "token-report-refresh.json").write_text(pem, encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    run_logs._render_token_timing_batches(  # pyright: ignore[reportPrivateUsage]
        ctx,
        tmp_path / "larch-logs",
    )
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    assert not (run_dir / "token-report-refresh.json").exists()


def test_copytree_rejects_symlinks_escaping_run_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    secret = tmp_path / "secret.txt"
    _ = secret.write_text("secret", encoding="utf-8")
    link = run_dir / "link.txt"
    link.symlink_to(secret)
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(run_logs, "_REPO_ROOT", repo)
    ctx = _ctx(tmp_path, str(state))
    with pytest.raises(ShipError, match="refusing symlink"):
        _ = run_logs._publish_run_tree_to_repo(  # pyright: ignore[reportPrivateUsage]
            ctx,
            tmp_path / "larch-logs",
            cwd=str(repo),
        )


def test_path_under_repo_rejects_traversal(tmp_path: Path) -> None:
    assert not run_logs.path_under_repo(tmp_path, "../outside")
    assert run_logs.path_under_repo(tmp_path, "docs/plan.md")


@pytest.mark.parametrize(
    "merge_result",
    ["merged", "admin_merged", "already_merged"],
)
def test_flush_logs_pre_skips_post_merge_matrix(
    tmp_path: Path,
    merge_result: str,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text(f"MERGE_RESULT={merge_result}\nRUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner()
    skip = run_logs.flush_logs_pre(runner, _ctx(tmp_path, str(state)))
    assert skip.reason == config.REFRESH_SKIP_POST_MERGE


@pytest.mark.parametrize(
    ("line", "reason"),
    [
        ("RUN_ID=run-abc\nNO_LOGS_COMMIT=true\n", config.REFRESH_SKIP_NO_LOGS_COMMIT),
        ("", config.REFRESH_SKIP_NO_RUN_ID),
        ("RUN_ID=../bad\n", config.REFRESH_SKIP_INVALID_RUN_ID),
    ],
)
def test_flush_logs_pre_skip_reason_tokens(
    tmp_path: Path,
    line: str,
    reason: str,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text(line, encoding="utf-8")
    runner = RecordingRunner()
    skip = run_logs.flush_logs_pre(runner, _ctx(tmp_path, str(state)))
    assert skip.skipped
    assert skip.reason == reason


def test_publish_run_tree_copies_run_id_pathspec(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "token-report-refresh.json").write_text("{}", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(run_logs, "_REPO_ROOT", repo)
    ctx = _ctx(tmp_path, str(state))
    rel = run_logs._publish_run_tree_to_repo(  # pyright: ignore[reportPrivateUsage]
        ctx,
        tmp_path / "larch-logs",
        cwd=str(repo),
    )
    assert rel == "larch-logs/implement/run-abc"
    assert (repo / rel / "token-report-refresh.json").is_file()


def test_is_placeholder_run_id_matches_non_unique_labels() -> None:
    assert run_logs.is_placeholder_run_id("run-1")
    assert run_logs.is_placeholder_run_id("run-2")
    assert run_logs.is_placeholder_run_id("run-10")
    # Unique run-ids (UUIDs, tmpdir basenames, the "run-abc" test label) are kept.
    assert not run_logs.is_placeholder_run_id("run-abc")
    assert not run_logs.is_placeholder_run_id("9F1C2D3E-1234-5678-9ABC-DEF012345678")
    assert not run_logs.is_placeholder_run_id("larch-implement-AbC123")
    assert not run_logs.is_placeholder_run_id("run")
    assert not run_logs.is_placeholder_run_id("")


def test_publish_run_tree_refuses_placeholder_run_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # A non-unique placeholder run-id (run-1) must never be copied into the repo
    # (issue #4397) — the shared path collides across concurrent runs and clones.
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-1\n", encoding="utf-8")
    run_dir = tmp_path / "larch-logs" / "implement" / "run-1"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "token-report-refresh.json").write_text("{}", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(run_logs, "_REPO_ROOT", repo)
    rel = run_logs._publish_run_tree_to_repo(  # pyright: ignore[reportPrivateUsage]
        _ctx(tmp_path, str(state)),
        tmp_path / "larch-logs",
        cwd=str(repo),
    )
    assert rel == ""
    assert not (repo / "larch-logs" / "implement" / "run-1").exists()


def _init_git_repo_on_feature(repo: Path) -> None:
    for argv in (
        ["git", "init", "-q"],
        ["git", "checkout", "-q", "-b", "feature"],
        ["git", "config", "user.email", "t@example.com"],
        ["git", "config", "user.name", "t"],
    ):
        _ = subprocess.run(argv, cwd=repo, check=True, capture_output=True)


def test_commit_run_refuses_placeholder_run_id(tmp_path: Path) -> None:
    # `run-log commit` (the design + implement repo-commit chokepoint) must
    # no-op for a placeholder run-id rather than commit a shared directory.
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo_on_feature(repo)
    log_root = tmp_path / "larch-logs"
    src = log_root / "implement" / "run-1"
    src.mkdir(parents=True)
    _ = (src / "manifest.json").write_text("{}", encoding="utf-8")
    result = run_logs._commit_run(  # pyright: ignore[reportPrivateUsage]
        log_root,
        "implement",
        "run-1",
        cwd=str(repo),
    )
    assert result.returncode == 0
    assert not (repo / "larch-logs" / "implement" / "run-1").exists()


def test_refresh_only_sidecars_not_written_to_batch_dir(tmp_path: Path) -> None:
    # Refresh JSON files must NOT be written to batch_dir (issue #3708 Phase 1).
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    _ = (tmp_path / "token-report-refresh.json").write_text("{}", encoding="utf-8")
    _ = (tmp_path / "timing-report-refresh.json").write_text("{}", encoding="utf-8")
    run_logs._render_token_timing_batches(  # pyright: ignore[reportPrivateUsage]
        _ctx(tmp_path, str(state)),
        tmp_path / "larch-logs",
    )
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    assert not (run_dir / "token-report-refresh.json").exists()
    assert not (run_dir / "timing-report-refresh.json").exists()


def test_flush_logs_pre_happy_path_commits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    _ = run_logs.init_run(ctx)
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _ = (run_dir / "token-report-refresh.json").write_text("{}", encoding="utf-8")
    commits: list[bool] = []

    def fake_commit(
        _runner: object,
        _ctx: object,
        _log_root: object,
        *,
        cwd: str | None = None,
    ) -> CommandResult:
        _ = cwd
        commits.append(True)
        return CommandResult(
            ("git", "commit"),
            0,
            "a" * 40 + "\n",
            "",
            0.0,
        )

    def noop_write_final_report(_runner: object, _ctx: object) -> None:
        _ = _runner, _ctx

    def noop_capture(_ctx: object, _runner: object, **kwargs: object) -> None:
        _ = _ctx, _runner, kwargs

    monkeypatch.setattr(run_logs, "_write_final_report", noop_write_final_report)
    monkeypatch.setattr(run_logs, "capture_session_transcript", noop_capture)
    monkeypatch.setattr(run_logs, "_commit_run", fake_commit)
    runner = RecordingRunner()
    skip = run_logs.flush_logs_pre(runner, ctx, cwd=str(tmp_path / "repo"))
    assert not skip.skipped
    assert commits == [True]
    manifest = json.loads(
        (tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json").read_text(
            encoding="utf-8",
        ),
    )
    assert "step9a1" not in manifest["steps_ran"]


def test_flush_logs_pre_update_manifest_failure_returns_recovery_skip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    _ = run_logs.init_run(ctx)

    def fail_update(*_a: object, **_k: object) -> run_logs.Manifest:
        raise ShipError("manifest recovery failed")

    monkeypatch.setattr(run_logs, "update_manifest", fail_update)
    skip = run_logs.flush_logs_pre(RecordingRunner(), ctx, cwd=str(tmp_path))
    assert skip.skipped is True
    assert skip.reason == run_logs.REFRESH_SKIP_RECOVERY_FAILED


def test_flush_logs_pre_commit_exception_returns_commit_skip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    _ = run_logs.init_run(ctx)

    def fail_commit(*_a: object, **_k: object) -> CommandResult:
        raise ShipError("commit failed")

    def noop(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(run_logs, "_commit_run", fail_commit)
    monkeypatch.setattr(run_logs, "_write_final_report", noop)
    monkeypatch.setattr(run_logs, "capture_session_transcript", noop)
    monkeypatch.setattr(run_logs, "_render_ledger_reports", noop)
    skip = run_logs.flush_logs_pre(RecordingRunner(), ctx, cwd=str(tmp_path))
    assert skip.skipped is True
    assert skip.reason == config.REFRESH_SKIP_COMMIT_FAILED


@pytest.mark.parametrize(
    ("forked", "state_text", "finalize_text", "flags_text", "files", "expected"),
    [
        (True, "RUN_ID=run-abc\n", "", "", ("run-statistics.md",), True),
        (False, "RUN_ID=run-abc\nFORKED_TARGET=true\n", "", "", ("run-statistics.md",), True),
        (
            False,
            "RUN_ID=run-abc\n",
            "DESIGN_ONLY_DONE=true\n",
            "NO_ISSUES=true\n",
            (),
            False,
        ),
        (False, "RUN_ID=run-abc\n", "", "", ("oos-issues.ndjson",), False),
        (False, "RUN_ID=run-abc\n", "", "", ("run-statistics.md",), True),
        (False, "RUN_ID=run-abc\n", "", "", ("oos-issues.ndjson", "run-statistics.md"), True),
        (False, "RUN_ID=run-abc\n", "", "", (), None),
    ],
)
def test_step9a1_heuristic_matrix(
    tmp_path: Path,
    forked: bool,
    state_text: str,
    finalize_text: str,
    flags_text: str,
    files: tuple[str, ...],
    expected: bool | None,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text(state_text, encoding="utf-8")
    if finalize_text:
        _ = (tmp_path / "finalize-state.sh").write_text(finalize_text, encoding="utf-8")
    if flags_text:
        _ = (tmp_path / "run-flags.sh").write_text(flags_text, encoding="utf-8")
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    for filename in files:
        if filename == "run-statistics.md":
            _ = (run_dir / filename).write_text("Run run-abc: 0 OOS issue(s) filed.\n", encoding="utf-8")
        elif filename == "oos-issues.ndjson":
            _ = (run_dir / filename).write_text('{"phase":"implement"}\n', encoding="utf-8")
        else:
            _ = (run_dir / filename).write_text("x\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state)).with_(forked=forked)
    assert run_logs._step9a1_heuristic(ctx) is expected  # pyright: ignore[reportPrivateUsage]



def test_step9a1_heuristic_manifest_explicit_values(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "oos-issues.ndjson").write_text('{"phase":"implement"}\n', encoding="utf-8")
    _ = (run_dir / "manifest.json").write_text('{"steps_ran":{"step9a1":false}}\n', encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    assert run_logs._step9a1_heuristic(ctx) is False  # pyright: ignore[reportPrivateUsage]
    _ = (run_dir / "manifest.json").write_text('{"steps_ran":{"step9a1":true}}\n', encoding="utf-8")
    assert run_logs._step9a1_heuristic(ctx) is False  # pyright: ignore[reportPrivateUsage]


def test_flush_logs_pre_downgrades_stale_step9a1_true_with_ndjson_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    _ = run_logs.init_run(ctx)
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _ = (run_dir / "oos-issues.ndjson").write_text('{"phase":"implement"}\n', encoding="utf-8")
    manifest_path = run_dir / "manifest.json"
    _ = manifest_path.write_text(
        json.dumps({"status": "partial", "version": "1", "run_id": "run-abc", "steps_ran": {"step9a1": True}}),
        encoding="utf-8",
    )

    def noop(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(run_logs, "_write_final_report", noop)
    monkeypatch.setattr(run_logs, "capture_session_transcript", noop)
    monkeypatch.setattr(run_logs, "_render_ledger_reports", noop)
    def noop_commit(*_args: object, **_kwargs: object) -> CommandResult:
        return CommandResult(("",), 0, "", "", 0.0)

    monkeypatch.setattr(run_logs, "_commit_run", noop_commit)
    skip = run_logs.flush_logs_pre(RecordingRunner(), ctx, cwd=str(tmp_path))
    assert not skip.skipped
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["steps_ran"]["step9a1"] is False


def test_render_token_timing_batches_skips_missing_refresh_json(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    run_logs._render_token_timing_batches(  # pyright: ignore[reportPrivateUsage]
        ctx,
        tmp_path / "larch-logs",
    )
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    assert not (tmp_path / "token-report-refresh.json").exists()
    assert not (run_dir / "token-report-refresh.json").exists()


def test_update_manifest_ignores_unknown_keys(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    _ = run_logs.init_run(ctx)
    manifest = run_logs.update_manifest(ctx, version="9", updated_at="now")
    assert manifest.version == "9"
    assert manifest.updated_at == "now"
    assert "version" not in manifest.steps_ran


def test_read_state_kv_unreadable_file_returns_empty(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_bytes(b"\xff\xfe")
    assert run_logs.read_state_kv(str(state), "RUN_ID") == ""


def test_flush_logs_pre_skips_commit_without_repo_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    _ = run_logs.init_run(ctx)

    def fail_commit(*_a: object, **_k: object) -> CommandResult:
        msg = "commit should not run without repo cwd"
        raise AssertionError(msg)

    def noop(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(run_logs, "_commit_run", fail_commit)
    monkeypatch.setattr(run_logs, "_write_final_report", noop)
    monkeypatch.setattr(run_logs, "capture_session_transcript", noop)
    monkeypatch.setattr(run_logs, "_render_ledger_reports", noop)
    runner = RecordingRunner()
    skip = run_logs.flush_logs_pre(runner, ctx, cwd=None)
    assert skip.skipped
    assert skip.reason == config.REFRESH_SKIP_NO_REPO_CWD


def test_load_or_recover_manifest_prefers_ctx_run_id(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs" / "implement"
    old = log_root / "run-old"
    new = log_root / "run-abc"
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    _ = (old / "manifest.json").write_text(
        json.dumps({"status": "partial", "version": "1", "run_id": "run-old", "steps_ran": {}}),
        encoding="utf-8",
    )
    _ = (new / "manifest.json").write_text(
        json.dumps({"status": "partial", "version": "1", "run_id": "run-abc", "steps_ran": {}}),
        encoding="utf-8",
    )
    ctx = _ctx(tmp_path, state_file=None)
    manifest = run_logs.load_or_recover_manifest(ctx)
    assert manifest.run_id == "run-abc"


def test_load_or_recover_manifest_fails_closed_without_valid_run_id(
    tmp_path: Path,
) -> None:
    newest = tmp_path / "larch-logs" / "implement" / "run-new"
    newest.mkdir(parents=True)
    _ = (newest / "manifest.json").write_text(
        json.dumps(
            {"status": "partial", "version": "1", "run_id": "run-new", "steps_ran": {}},
        ),
        encoding="utf-8",
    )
    ctx = _ctx(tmp_path).with_(run_id="../bad")
    manifest = run_logs.load_or_recover_manifest(ctx)
    assert manifest.run_id == ""
    assert not manifest.steps_ran


def test_publish_run_tree_preserves_existing_dest_when_copy_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    src = tmp_path / "larch-logs" / "implement" / "run-abc"
    src.mkdir(parents=True)
    _ = (src / "new.txt").write_text("new\n", encoding="utf-8")
    repo = tmp_path / "repo"
    dest = repo / "larch-logs" / "implement" / "run-abc"
    dest.mkdir(parents=True)
    _ = (dest / "old.txt").write_text("old\n", encoding="utf-8")
    monkeypatch.setattr(run_logs, "_REPO_ROOT", repo)

    def fail_copy(*_a: object, **_k: object) -> None:
        raise ShipError("copy failed")

    monkeypatch.setattr(run_logs, "_safe_copy_run_tree", fail_copy)
    ctx = _ctx(tmp_path, str(state))
    with pytest.raises(ShipError, match="copy failed"):
        _ = run_logs._publish_run_tree_to_repo(  # pyright: ignore[reportPrivateUsage]
            ctx,
            tmp_path / "larch-logs",
            cwd=str(repo),
        )
    assert (dest / "old.txt").read_text(encoding="utf-8") == "old\n"


def test_scrub_run_tree_redacts_cursor_key(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    sub = run_dir / "round-1"
    sub.mkdir(parents=True)
    secret = (
        "cursor --api-key crsr_1620abcdefghijklmnopqrstuvwxyz0123456789 --workspace /x\n"
    )
    _ = (sub / "findings.md").write_text(secret, encoding="utf-8")
    _ = (run_dir / "clean.md").write_text("clean prose\n", encoding="utf-8")
    violations, files_scrubbed = run_logs._scrub_run_tree(  # pyright: ignore[reportPrivateUsage]
        run_dir,
    )
    assert violations == 1
    assert files_scrubbed == 1
    assert "crsr_1620" not in (sub / "findings.md").read_text(encoding="utf-8")
    assert (run_dir / "clean.md").read_text(encoding="utf-8") == "clean prose\n"


def test_scrub_run_tree_fail_closed_on_residual(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _ = (run_dir / "f.md").write_text(
        "crsr_1620abcdefghijklmnopqrstuvwxyz0123456789\n",
        encoding="utf-8",
    )

    def _never_scrubs(text: str) -> tuple[str, dict[str, int]]:
        return text, {"cursor-api-key": 1}

    monkeypatch.setattr(run_logs.redact, "scrub_log_secrets", _never_scrubs)
    with pytest.raises(ShipError, match="secret survived scrubbing"):
        _ = run_logs._scrub_run_tree(run_dir)  # pyright: ignore[reportPrivateUsage]


def test_larch_log_commit_skips_volatile_refresh_only_and_cleans(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    src = tmp_path / "larch-logs" / "implement" / "run-abc"
    src.mkdir(parents=True)
    _ = (src / "token-report-refresh.json").write_text("{}", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(run_logs, "_REPO_ROOT", repo)
    rel = "larch-logs/implement/run-abc"
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("git", "status"),
                0,
                f"?? {rel}/token-report-refresh.json\n",
                "",
                0.01,
            ),
            CommandResult(("git", "clean"), 0, "", "", 0.01),
            CommandResult(("git", "status"), 0, "", "", 0.01),
        ],
    )
    result = run_logs._larch_log_commit(  # pyright: ignore[reportPrivateUsage]
        runner,
        _ctx(tmp_path, str(state)),
        tmp_path / "larch-logs",
        cwd=str(repo),
    )
    assert result.returncode == 0
    assert result.argv == ("larch-log-volatile-only",)
    assert runner.git_commits == 0
    assert ["git", "clean", "-fd", "--", f"{rel}/token-report-refresh.json"] in runner.calls


def test_flush_logs_pre_reports_volatile_only_skip_reason(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_commit(*_a: object, **_k: object) -> CommandResult:
        return CommandResult(("larch-log-volatile-only",), 0, "", "", 0.01)

    monkeypatch.setattr(run_logs, "_commit_run", fake_commit)
    skip = run_logs.flush_logs_pre(RecordingRunner(), _ctx(tmp_path), cwd=str(tmp_path))
    assert skip.skipped
    assert skip.reason == config.REFRESH_SKIP_VOLATILE_ONLY


def test_larch_log_commit_commits_canonical_token_report_delta(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    src = tmp_path / "larch-logs" / "implement" / "run-abc"
    src.mkdir(parents=True)
    _ = (src / "token-report.json").write_text("{}", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(run_logs, "_REPO_ROOT", repo)
    rel = "larch-logs/implement/run-abc"
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "status"), 0, f" M {rel}/token-report.json\n", "", 0.01),
            CommandResult(("git", "add"), 0, "", "", 0.01),
            CommandResult(("git", "diff"), 1, "", "", 0.01),
            CommandResult(("git", "commit", "-m"), 0, "", "", 0.01),
        ],
    )
    result = run_logs._larch_log_commit(  # pyright: ignore[reportPrivateUsage]
        runner,
        _ctx(tmp_path, str(state)),
        tmp_path / "larch-logs",
        cwd=str(repo),
    )
    assert result.returncode == 0
    assert any(call[:3] == ["git", "commit", "-m"] for call in runner.calls)


def test_larch_log_commit_commits_mixed_volatile_and_canonical_deltas(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    src = tmp_path / "larch-logs" / "implement" / "run-abc"
    src.mkdir(parents=True)
    _ = (src / "token-report-refresh.json").write_text("{}", encoding="utf-8")
    _ = (src / "token-report.ndjson").write_text("{}\n", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(run_logs, "_REPO_ROOT", repo)
    rel = "larch-logs/implement/run-abc"
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("git", "status"),
                0,
                f" M {rel}/token-report-refresh.json\n M {rel}/token-report.ndjson\n",
                "",
                0.01,
            ),
            CommandResult(("git", "add"), 0, "", "", 0.01),
            CommandResult(("git", "diff"), 1, "", "", 0.01),
            CommandResult(("git", "commit", "-m"), 0, "", "", 0.01),
        ],
    )
    result = run_logs._larch_log_commit(  # pyright: ignore[reportPrivateUsage]
        runner,
        _ctx(tmp_path, str(state)),
        tmp_path / "larch-logs",
        cwd=str(repo),
    )
    assert result.returncode == 0
    assert result.argv != ("larch-log-volatile-only",)
    assert any(call[:3] == ["git", "commit", "-m"] for call in runner.calls)


def test_larch_log_commit_volatile_cleanup_fails_closed_on_dirty_repo(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    src = tmp_path / "larch-logs" / "implement" / "run-abc"
    src.mkdir(parents=True)
    _ = (src / "timing-report-refresh.json").write_text("{}", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(run_logs, "_REPO_ROOT", repo)
    rel = "larch-logs/implement/run-abc"
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "status"), 0, f"?? {rel}/timing-report-refresh.json\n", "", 0.01),
            CommandResult(("git", "clean"), 0, "", "", 0.01),
            CommandResult(("git", "status"), 0, " M README.md\n", "", 0.01),
        ],
    )
    with pytest.raises(ShipError, match="dirty porcelain"):
        _ = run_logs._larch_log_commit(  # pyright: ignore[reportPrivateUsage]
            runner,
            _ctx(tmp_path, str(state)),
            tmp_path / "larch-logs",
            cwd=str(repo),
        )


@pytest.mark.parametrize(
    ("failing_call", "status_stdout"),
    [
        (
            ("git", "reset"),
            "A  larch-logs/implement/run-abc/token-report-refresh.json\n",
        ),
        (
            ("git", "restore"),
            " M larch-logs/implement/run-abc/token-report-refresh.json\n",
        ),
        (
            ("git", "clean"),
            "?? larch-logs/implement/run-abc/token-report-refresh.json\n",
        ),
    ],
)
def test_larch_log_commit_volatile_cleanup_git_failures_fail_closed(
    failing_call: tuple[str, str],
    status_stdout: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    src = tmp_path / "larch-logs" / "implement" / "run-abc"
    src.mkdir(parents=True)
    _ = (src / "token-report-refresh.json").write_text("{}", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(run_logs, "_REPO_ROOT", repo)
    rel = "larch-logs/implement/run-abc"
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "status"), 0, status_stdout, "", 0.01),
            CommandResult(failing_call, 1, "", "failed", 0.01),
        ],
    )
    with pytest.raises(ShipError, match="run-log volatile cleanup failed"):
        _ = run_logs._larch_log_commit(  # pyright: ignore[reportPrivateUsage]
            runner,
            _ctx(tmp_path, str(state)),
            tmp_path / "larch-logs",
            cwd=str(repo),
        )
    assert all(call != ["git", "clean", "-fd", "--", rel] for call in runner.calls)


def test_larch_log_commit_scrubbed_volatile_sidecar_skips_commit_and_cleans(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    src = tmp_path / "larch-logs" / "implement" / "run-abc"
    src.mkdir(parents=True)
    _ = (src / "token-report-refresh.json").write_text("secret", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(run_logs, "_REPO_ROOT", repo)
    rel = "larch-logs/implement/run-abc"

    def fake_scrub(_directory: Path) -> tuple[int, int]:
        return 1, 1

    monkeypatch.setattr(run_logs, "_scrub_run_tree", fake_scrub)
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "status"), 0, f" M {rel}/token-report-refresh.json\n", "", 0.01),
            CommandResult(("git", "restore"), 0, "", "", 0.01),
            CommandResult(("git", "status"), 0, "", "", 0.01),
        ],
    )
    result = run_logs._larch_log_commit(  # pyright: ignore[reportPrivateUsage]
        runner,
        _ctx(tmp_path, str(state)),
        tmp_path / "larch-logs",
        cwd=str(repo),
    )
    assert result.returncode == 0
    assert result.argv == ("larch-log-volatile-only",)
    assert not any(call[:3] == ["git", "commit", "-m"] for call in runner.calls)
    assert ["git", "restore", "--worktree", "--staged", "--source=HEAD", "--", f"{rel}/token-report-refresh.json"] in runner.calls


def test_larch_log_commit_volatile_session_transcript_refresh_skips_commit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    src = tmp_path / "larch-logs" / "implement" / "run-abc"
    src.mkdir(parents=True)
    _ = (src / "session-transcript-refresh.txt").write_text("transcript", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(run_logs, "_REPO_ROOT", repo)
    rel = "larch-logs/implement/run-abc"
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("git", "status"),
                0,
                f"?? {rel}/session-transcript-refresh.txt\n",
                "",
                0.01,
            ),
            CommandResult(("git", "clean"), 0, "", "", 0.01),
            CommandResult(("git", "status"), 0, "", "", 0.01),
        ],
    )
    result = run_logs._larch_log_commit(  # pyright: ignore[reportPrivateUsage]
        runner,
        _ctx(tmp_path, str(state)),
        tmp_path / "larch-logs",
        cwd=str(repo),
    )
    assert result.argv == ("larch-log-volatile-only",)
    assert ["git", "clean", "-fd", "--", f"{rel}/session-transcript-refresh.txt"] in runner.calls


def test_larch_log_commit_volatile_cleanup_restores_am_porcelain(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    src = tmp_path / "larch-logs" / "implement" / "run-abc"
    src.mkdir(parents=True)
    _ = (src / "token-report-refresh.json").write_text("{}", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(run_logs, "_REPO_ROOT", repo)
    rel = "larch-logs/implement/run-abc"
    path = f"{rel}/token-report-refresh.json"
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "status"), 0, f"AM {path}\n", "", 0.01),
            CommandResult(("git", "reset", "HEAD"), 0, "", "", 0.01),
            CommandResult(("git", "restore"), 0, "", "", 0.01),
            CommandResult(("git", "status"), 0, "", "", 0.01),
        ],
    )
    result = run_logs._larch_log_commit(  # pyright: ignore[reportPrivateUsage]
        runner,
        _ctx(tmp_path, str(state)),
        tmp_path / "larch-logs",
        cwd=str(repo),
    )
    assert result.argv == ("larch-log-volatile-only",)
    reset_call = ["git", "reset", "HEAD", "--", rel]
    restore_call = ["git", "restore", "--worktree", "--staged", "--source=HEAD", "--", path]
    assert reset_call in runner.calls
    assert restore_call in runner.calls
    assert runner.calls.index(reset_call) < runner.calls.index(restore_call)


def test_larch_log_commit_volatile_cleanup_resets_staged_before_restore(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    src = tmp_path / "larch-logs" / "implement" / "run-abc"
    src.mkdir(parents=True)
    _ = (src / "timing-report-refresh.json").write_text("{}", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(run_logs, "_REPO_ROOT", repo)
    rel = "larch-logs/implement/run-abc"
    path = f"{rel}/timing-report-refresh.json"
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "status"), 0, f"A  {path}\n", "", 0.01),
            CommandResult(("git", "reset", "HEAD"), 0, "", "", 0.01),
            CommandResult(("git", "restore"), 0, "", "", 0.01),
            CommandResult(("git", "status"), 0, "", "", 0.01),
        ],
    )
    result = run_logs._larch_log_commit(  # pyright: ignore[reportPrivateUsage]
        runner,
        _ctx(tmp_path, str(state)),
        tmp_path / "larch-logs",
        cwd=str(repo),
    )
    assert result.argv == ("larch-log-volatile-only",)
    reset_call = ["git", "reset", "HEAD", "--", rel]
    restore_call = ["git", "restore", "--worktree", "--staged", "--source=HEAD", "--", path]
    assert reset_call in runner.calls
    assert restore_call in runner.calls
    assert runner.calls.index(reset_call) < runner.calls.index(restore_call)


def test_publish_run_tree_uses_repo_root_not_cwd_subdir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Regression: copy destination uses _REPO_ROOT regardless of caller CWD."""
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    src = tmp_path / "larch-logs" / "implement" / "run-abc"
    src.mkdir(parents=True)
    _ = (src / "manifest.json").write_text("{}", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    subdir = repo / "python"
    subdir.mkdir()
    monkeypatch.setattr(run_logs, "_REPO_ROOT", repo)
    ctx = _ctx(tmp_path, str(state))
    rel = run_logs._publish_run_tree_to_repo(  # pyright: ignore[reportPrivateUsage]
        ctx,
        tmp_path / "larch-logs",
        cwd=str(subdir),  # CWD is a repo subdirectory, not the root
    )
    assert rel == "larch-logs/implement/run-abc"
    # Copy must land under repo root, not under the subdirectory CWD.
    assert (repo / rel / "manifest.json").is_file(), "copy must land under repo root"
    assert not (subdir / rel).exists(), "copy must NOT land under subdir CWD"


def test_larch_log_commit_rejects_cwd_outside_repo_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Guard: raise ShipError when caller CWD is not the repo root."""
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    src = tmp_path / "larch-logs" / "implement" / "run-abc"
    src.mkdir(parents=True)
    _ = (src / "manifest.json").write_text("{}", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    subdir = repo / "python"
    subdir.mkdir()
    monkeypatch.setattr(run_logs, "_REPO_ROOT", repo)
    ctx = _ctx(tmp_path, str(state))
    with pytest.raises(ShipError, match="repo root"):
        _ = run_logs._larch_log_commit(  # pyright: ignore[reportPrivateUsage]
            RecordingRunner(),
            ctx,
            tmp_path / "larch-logs",
            cwd=str(subdir),
        )


def test_render_ledger_reports_uses_direct_renderers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    _ = (tmp_path / "timing-ledger.tsv").write_text(
        "v1\tmark\t1\timplement\tStep 0\t-\t-\t-\t-\t-\t-\t-\t-\n",
        encoding="utf-8",
    )
    captured: dict[str, str] = {}

    def capture_env(env: object) -> None:
        if isinstance(env, Mapping):
            env_map = cast("Mapping[object, object]", env)
            captured.update(
                {key: value for key, value in env_map.items() if isinstance(key, str) and isinstance(value, str)}
            )

    def fake_token_report(**kwargs: object) -> dict[str, object]:
        capture_env(kwargs.get("env"))
        return {"claude": {}}

    def fake_render_json(_self: timing.TimingReport, *, env: object = None, **_: object) -> dict[str, object]:
        capture_env(env)
        return {"per_step": []}

    def fake_resolve_timing_ledger_path(**_: object) -> Path:
        return tmp_path / "timing-ledger.tsv"

    monkeypatch.setattr(tokens, "token_report", fake_token_report)
    monkeypatch.setattr(timing.TimingReport, "render_json", fake_render_json)
    monkeypatch.setattr(timing, "resolve_timing_ledger_path", fake_resolve_timing_ledger_path)
    write_batches: list[str] = []

    def fake_write_batch(
        _log_root: Path, _skill: str, _run_id: str, batch: str, input_file: Path
    ) -> tuple[Path, bool, bool]:
        write_batches.append(batch)
        return (input_file, True, False)

    monkeypatch.setattr(run_logs, "_write_batch", fake_write_batch)
    ctx = _ctx(tmp_path, str(state))
    runner = RecordingRunner()
    run_logs._render_ledger_reports(runner, ctx, tmp_path / "logs")  # pyright: ignore[reportPrivateUsage]

    assert (tmp_path / "token-report-refresh.json").is_file()
    assert (tmp_path / "timing-report-refresh.json").is_file()
    assert captured.get("LARCH_TIMING_SKILL") == "implement"
    assert "DESIGN_TMPDIR" not in captured
    assert "token-report" in write_batches
    assert "timing-report" in write_batches


def _ledger_report_fixture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[RecordingRunner, RunContext, list[str]]:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    _ = (tmp_path / "timing-ledger.tsv").write_text(
        "v1\tmark\t1\timplement\tStep 0\t-\t-\t-\t-\t-\t-\t-\t-\n",
        encoding="utf-8",
    )
    _ledger_path = tmp_path / "timing-ledger.tsv"
    monkeypatch.setattr(timing, "resolve_timing_ledger_path", lambda **_kw: _ledger_path)  # type: ignore[arg-type]
    write_batches: list[str] = []

    def fake_write_batch(
        _log_root: Path, _skill: str, _run_id: str, batch: str, input_file: Path
    ) -> tuple[Path, bool, bool]:
        write_batches.append(batch)
        return (input_file, True, False)

    monkeypatch.setattr(run_logs, "_write_batch", fake_write_batch)
    return RecordingRunner(), _ctx(tmp_path, str(state)), write_batches


def test_render_ledger_reports_timing_succeeds_when_token_report_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner, ctx, write_batches = _ledger_report_fixture(monkeypatch, tmp_path)

    def raise_token_report(**_kwargs: object) -> dict[str, object]:
        msg = "token renderer failed"
        raise RuntimeError(msg)

    monkeypatch.setattr(tokens, "token_report", raise_token_report)
    run_logs._render_ledger_reports(runner, ctx, tmp_path / "logs")  # pyright: ignore[reportPrivateUsage]

    assert not (tmp_path / "token-report-refresh.json").exists()
    assert (tmp_path / "timing-report-refresh.json").is_file()
    assert "token-report" not in write_batches
    assert "timing-report" in write_batches


def test_render_ledger_reports_token_succeeds_when_timing_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner, ctx, write_batches = _ledger_report_fixture(monkeypatch, tmp_path)

    def fake_token_report(**_kwargs: object) -> dict[str, object]:
        return {"claude": {}}

    def raise_render_json(_self: timing.TimingReport, **_: object) -> dict[str, object]:  # type: ignore[misc]
        raise RuntimeError("timing renderer failed")

    monkeypatch.setattr(tokens, "token_report", fake_token_report)
    monkeypatch.setattr(timing.TimingReport, "render_json", raise_render_json)
    run_logs._render_ledger_reports(runner, ctx, tmp_path / "logs")  # pyright: ignore[reportPrivateUsage]

    assert (tmp_path / "token-report-refresh.json").is_file()
    assert not (tmp_path / "timing-report-refresh.json").exists()
    assert "token-report" in write_batches
    assert "timing-report" not in write_batches


def test_render_ledger_reports_writes_empty_timing_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner, ctx, _write_batches = _ledger_report_fixture(monkeypatch, tmp_path)

    def fake_token_report(**_kwargs: object) -> dict[str, object]:
        return {"claude": {}}

    def empty_render_json(_self: timing.TimingReport, **_: object) -> dict[str, object]:  # type: ignore[misc]
        return {}

    monkeypatch.setattr(tokens, "token_report", fake_token_report)
    monkeypatch.setattr(timing.TimingReport, "render_json", empty_render_json)
    run_logs._render_ledger_reports(runner, ctx, tmp_path / "logs")  # pyright: ignore[reportPrivateUsage]

    timing_path = tmp_path / "timing-report-refresh.json"
    assert timing_path.is_file()
    assert json.loads(timing_path.read_text(encoding="utf-8")) == {}


def test_report_subprocess_env_pins_implement_and_clears_design_tmpdir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    design_tmp = tmp_path / "design"
    design_tmp.mkdir()
    _ = (design_tmp / "run-params.json").write_text(json.dumps({}), encoding="utf-8")
    monkeypatch.setenv("LARCH_TIMING_SKILL", "design")
    monkeypatch.setenv("DESIGN_TMPDIR", str(design_tmp))
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    env = run_logs._report_subprocess_env(_ctx(tmp_path, str(state)))  # pyright: ignore[reportPrivateUsage]
    assert env["LARCH_TIMING_SKILL"] == "implement"
    assert "DESIGN_TMPDIR" not in env


def test_verify_completeness_reports_missing_required_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(run_logs, "_REPO_ROOT", tmp_path)
    run_dir = tmp_path / "larch-logs" / "implement" / "RUN1"
    run_dir.mkdir(parents=True)
    manifest = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": "RUN1",
        "steps_ran": {"step7a": True},
        "status": "partial",
    }
    _ = (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _ = (run_dir / "token-report.json").write_text("{}", encoding="utf-8")
    tsv = tmp_path / "required.tsv"
    _ = tsv.write_text("relative_path\tcondition\nfinal-summary.md\talways\n", encoding="utf-8")
    monkeypatch.setenv("LARCH_VERIFY_MANIFEST", str(tsv))
    assert run_logs.verify_completeness_main([str(run_dir)]) == 1


def test_verify_completeness_ok_when_required_file_present(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(run_logs, "_REPO_ROOT", tmp_path)
    run_dir = tmp_path / "larch-logs" / "implement" / "RUN1"
    run_dir.mkdir(parents=True)
    manifest = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": "RUN1",
        "steps_ran": {"step8": True},
        "status": "partial",
    }
    _ = (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _ = (run_dir / "final-summary.md").write_text("# done\n", encoding="utf-8")
    tsv = tmp_path / "required.tsv"
    _ = tsv.write_text("relative_path\tcondition\nfinal-summary.md\tstep8\n", encoding="utf-8")
    monkeypatch.setenv("LARCH_VERIFY_MANIFEST", str(tsv))
    assert run_logs.verify_completeness_main([str(run_dir)]) == 0


def test_verify_completeness_stale_step9a1_true_without_stats_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(run_logs, "_REPO_ROOT", tmp_path)
    run_dir = tmp_path / "larch-logs" / "implement" / "RUN1"
    run_dir.mkdir(parents=True)
    manifest = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": "RUN1",
        "steps_ran": {"step9a1": True},
        "status": "partial",
    }
    _ = (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _ = (run_dir / "oos-issues.ndjson").write_text('{"phase":"implement"}\n', encoding="utf-8")
    tsv = tmp_path / "required.tsv"
    _ = tsv.write_text("relative_path\tcondition\nrun-statistics.md\tstep9a1\n", encoding="utf-8")
    monkeypatch.setenv("LARCH_VERIFY_MANIFEST", str(tsv))
    assert run_logs.verify_completeness_main([str(run_dir)]) == 1
    assert "run-statistics.md" in capsys.readouterr().out


def test_refresh_run_logs_main_skips_without_state_file(tmp_path: Path) -> None:
    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        rc = run_logs.refresh_run_logs_main(["--implement-tmpdir", str(tmp_path)])
    assert rc == 0
    assert f"REFRESH_SKIPPED=true REASON={config.REFRESH_SKIP_STATE_FILE_MISSING}" in buf.getvalue()


def test_capture_transcript_main_missing_source(tmp_path: Path) -> None:
    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        rc = run_logs.capture_transcript_main(
            [
                "--source-file",
                str(tmp_path / "missing.txt"),
                "--log-root",
                str(tmp_path / "larch-logs"),
                "--skill",
                "implement",
                "--run-id",
                "RUN1",
                "--no-logs-commit",
                "true",
            ],
        )
    assert rc == 0
    assert "SESSION_TRANSCRIPT_STATUS=source-file-missing" in buf.getvalue()


def test_init_run_writes_manifest_v2(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    _ = run_logs.init_run(ctx, run_id="run-abc")
    manifest_path = tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == 2
    assert data["skill"] == "implement"
