"""Tests for run_logs.py."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import config
import run_logs
from errors import ShipError
from proc import CommandResult
from run_context import RunContext


def _empty_str_lists() -> list[list[str]]:
    return []


def _empty_command_results() -> list[CommandResult]:
    return []


@dataclass
class RecordingRunner:
    calls: list[list[str]] = field(default_factory=_empty_str_lists)
    responses: list[CommandResult] = field(default_factory=_empty_command_results)
    _index: int = 0
    git_commits: int = 0

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
        if argv[:3] == ("git", "commit", "-m"):
            self.git_commits += 1
        if self._index >= len(self.responses):
            return CommandResult(tuple(argv), 0, "", "", 0.01)
        result = self.responses[self._index]
        self._index += 1
        return result


def _ctx(tmp_path: Path, state_file: str | None = None) -> RunContext:
    return RunContext(
        branch="feat",
        issue="1",
        repo="o/r",
        run_id="run-abc",
        tmpdir=str(tmp_path),
        merge=True,
        draft=False,
        forked=False,
        manifest_path=str(tmp_path / "manifest.json"),
        tool_label="cursor",
        no_admin_fallback=False,
        repo_unavailable=False,
        state_file=state_file,
    )


def test_validate_run_id_slug() -> None:
    assert run_logs.validate_run_id_slug("run-1")
    assert not run_logs.validate_run_id_slug("../evil")


def test_flush_logs_pre_skips_missing_state(tmp_path: Path) -> None:
    runner = RecordingRunner()
    skip = run_logs.flush_logs_pre(runner, _ctx(tmp_path))
    assert skip.skipped
    assert skip.reason == config.REFRESH_SKIP_STATE_FILE_MISSING


def test_flush_logs_pre_skips_post_merge(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("MERGE_RESULT=merged\nRUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner()
    skip = run_logs.flush_logs_pre(runner, _ctx(tmp_path, str(state)))
    assert skip.reason == config.REFRESH_SKIP_POST_MERGE


def test_flush_logs_post_no_git_commit(tmp_path: Path) -> None:
    runner = RecordingRunner()
    ctx = _ctx(tmp_path)
    _ = run_logs.init_run(ctx)
    _ = run_logs.flush_logs_post(ctx)
    assert runner.git_commits == 0
    manifest_path = tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == config.MANIFEST_STATUS_DONE


def test_load_or_recover_manifest_from_log_dir(tmp_path: Path) -> None:
    log_dir = tmp_path / "larch-logs" / "implement" / "recovered-run"
    log_dir.mkdir(parents=True)
    ctx = _ctx(tmp_path).with_(run_id="../invalid")
    manifest = run_logs.load_or_recover_manifest(ctx)
    assert manifest.run_id == "recovered-run"


def test_effective_run_id_prefers_state_file(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=state-run\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    assert run_logs.effective_run_id(ctx) == "state-run"


def test_effective_run_id_rejects_unvalidated_ctx_run_id(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path).with_(run_id="../../../outside")
    assert run_logs.effective_run_id(ctx) == ""


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
    assert "Tool Failures" in batch.read_text(encoding="utf-8")


def test_token_batch_redaction_truncation_fails_closed(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIB\n"
    _ = (tmp_path / "token-report-refresh.json").write_text(pem, encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    with pytest.raises(ShipError, match="redaction failed"):
        run_logs._render_token_timing_batches(  # pyright: ignore[reportPrivateUsage]
            ctx,
            tmp_path / "larch-logs",
        )


def test_copytree_preserves_symlinks(tmp_path: Path) -> None:
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
    ctx = _ctx(tmp_path, str(state))
    rel = run_logs._publish_run_tree_to_repo(  # pyright: ignore[reportPrivateUsage]
        ctx,
        tmp_path / "larch-logs",
        cwd=str(repo),
    )
    published = repo / rel / "link.txt"
    assert published.is_symlink()


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


def test_publish_run_tree_copies_run_id_pathspec(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "token-report-refresh.json").write_text("{}", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    ctx = _ctx(tmp_path, str(state))
    rel = run_logs._publish_run_tree_to_repo(  # pyright: ignore[reportPrivateUsage]
        ctx,
        tmp_path / "larch-logs",
        cwd=str(repo),
    )
    assert rel == "larch-logs/implement/run-abc"
    assert (repo / rel / "token-report-refresh.json").is_file()


def test_flush_logs_pre_happy_path_commits(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    _ = run_logs.init_run(ctx)
    runner = RecordingRunner()
    skip = run_logs.flush_logs_pre(runner, ctx, cwd=None)
    assert not skip.skipped
    manifest = json.loads(
        (tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json").read_text(
            encoding="utf-8",
        ),
    )
    assert "step9a1" not in manifest["steps_ran"]
