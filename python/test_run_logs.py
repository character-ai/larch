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

    monkeypatch.setattr(run_logs, "_larch_log_commit", fake_commit)
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
    assert manifest["steps_ran"]["pr_number"] == 17


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


def test_token_batch_redaction_truncation_fails_closed(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    pem = "-----BEGIN RSA " + "PRIVATE KEY-----\nMIIB\n"
    _ = (tmp_path / "token-report-refresh.json").write_text(pem, encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    with pytest.raises(ShipError, match="redaction failed"):
        run_logs._render_token_timing_batches(  # pyright: ignore[reportPrivateUsage]
            ctx,
            tmp_path / "larch-logs",
        )


def test_copytree_rejects_symlinks_escaping_run_dir(tmp_path: Path) -> None:
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
        return CommandResult(("true",), 0, "", "", 0.0)

    def noop_write_final_report(_runner: object, _ctx: object) -> None:
        _ = _runner, _ctx

    def noop_capture(_ctx: object, _runner: object, **kwargs: object) -> None:
        _ = _ctx, _runner, kwargs

    monkeypatch.setattr(run_logs, "_write_final_report", noop_write_final_report)
    monkeypatch.setattr(run_logs, "capture_session_transcript", noop_capture)
    monkeypatch.setattr(run_logs, "_larch_log_commit", fake_commit)
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


@pytest.mark.parametrize(
    ("forked", "state_text", "finalize_text", "flags_text", "files", "expected"),
    [
        (True, "RUN_ID=run-abc\n", "", "", (), False),
        (False, "RUN_ID=run-abc\nFORKED_TARGET=true\n", "", "", (), False),
        (
            False,
            "RUN_ID=run-abc\n",
            "DESIGN_ONLY_DONE=true\n",
            "NO_ISSUES=true\n",
            (),
            False,
        ),
        (False, "RUN_ID=run-abc\n", "", "", ("oos-issues.ndjson",), True),
        (False, "RUN_ID=run-abc\n", "", "", ("run-statistics.md",), True),
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
        _ = (run_dir / filename).write_text("x\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state)).with_(forked=forked)
    assert run_logs._step9a1_heuristic(ctx) is expected  # pyright: ignore[reportPrivateUsage]


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

    monkeypatch.setattr(run_logs, "_larch_log_commit", fail_commit)
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
