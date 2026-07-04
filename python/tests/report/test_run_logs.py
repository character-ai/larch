"""Tests for run_logs.py."""

from __future__ import annotations

import contextlib
import json
import subprocess
from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest

from larch.core import config
from larch.report import final_report
from larch.report import run_logs
from larch.report import run_log_commit, run_log_flush
from larch.report.run_log_batch import _rebase_under_tmpdir  # pyright: ignore[reportPrivateUsage]
from larch.report import timing
from larch.report import tokens
from larch.errors import ShipError
from larch.core.proc import CommandResult

from test_support import RecordingRunner as _RecordingRunner, make_run_context

if TYPE_CHECKING:
    from larch.core.run_context import RunContext


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
    assert run_logs.validate_run_id_slug("-abc123")
    assert not run_logs.validate_run_id_slug("../evil")
    assert not run_logs.validate_run_id_slug("a..b")
    assert not run_logs.validate_run_id_slug("bad/slash")
    assert not run_logs.validate_run_id_slug(r"bad\slash")


def test_run_dir_rejects_invalid_run_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="invalid run-id"):
        run_logs._run_dir(log_root=tmp_path / "larch-logs", skill="implement", run_id="../evil")  # pyright: ignore[reportPrivateUsage, reportUnusedCallResult]


@pytest.mark.parametrize(
    "argv",
    [
        ["--run-id", "run-1"],
        ["--run-id=-abc123"],
        ["--run-id", "abc.DEF_123"],
    ],
)
def test_larch_log_validate_run_id_main_valid(
    argv: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = run_logs.larch_log_validate_run_id_main(argv)

    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "VALID=true\n"


@pytest.mark.parametrize(
    "value",
    ["", "../evil", "a..b", "bad/slash", r"bad\slash", "bad space", "bad*char"],
)
def test_larch_log_validate_run_id_main_invalid(
    value: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = run_logs.larch_log_validate_run_id_main([f"--run-id={value}"])

    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "VALID=false\n"


def test_larch_log_validate_run_id_main_missing_arg(capsys: pytest.CaptureFixture[str]) -> None:
    rc = run_logs.larch_log_validate_run_id_main([])

    captured = capsys.readouterr()
    assert rc != 0
    assert captured.out == ""


def test_atomic_write_uses_nofollow(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: dict[str, Any] = {}

    def fake_atomic_write(_path: Path, _content: str, **kwargs: Any) -> None:
        calls.update(kwargs)

    monkeypatch.setattr(run_logs.larch_io, "atomic_write", fake_atomic_write)
    run_logs._atomic_write(path=tmp_path / "manifest.json", content="{}")  # pyright: ignore[reportPrivateUsage]
    assert calls["prefix"] == ".manifest-"
    assert calls["nofollow"] is True


def test_flush_logs_pre_state_file_less_requires_repo_cwd(tmp_path: Path) -> None:
    runner = RecordingRunner()
    skip = run_logs.flush_logs_pre(runner=runner, ctx=_ctx(tmp_path), cwd=None)
    assert skip.skipped
    assert skip.reason == config.REFRESH_SKIP_NO_REPO_CWD


def test_flush_logs_pre_state_file_less_commits_with_repo_cwd(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = RecordingRunner()

    def fake_commit(
        *,
        log_root: Path,
        skill: str = "implement",
        run_id: str = "",
        cwd: str | None = None,
        pre_scrub_violations: int = 0,
    ) -> CommandResult:
        _ = log_root, skill, run_id, pre_scrub_violations
        assert cwd == str(tmp_path)
        runner.git_commits += 1
        return CommandResult(("git", "commit"), 0, "", "", 0.01)

    monkeypatch.setattr(run_logs, "_commit_run", fake_commit)
    monkeypatch.setattr(run_log_flush, "_commit_run", fake_commit)  # type: ignore[arg-type]
    skip = run_logs.flush_logs_pre(runner=runner, ctx=_ctx(tmp_path), cwd=str(tmp_path))
    assert not skip.skipped
    assert runner.git_commits == 1


def test_flush_logs_pre_skips_post_merge(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("MERGE_RESULT=merged\nRUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner()
    skip = run_logs.flush_logs_pre(runner=runner, ctx=_ctx(tmp_path, str(state)))
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
    monkeypatch.setattr(run_log_flush, "_write_final_report", fail_report)  # type: ignore[arg-type]
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
    monkeypatch.setattr(run_log_flush, "_write_manifest", boom)  # type: ignore[arg-type]
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
    assert recovered.manifest.extra == {"recovery_reason": "manifest_lost_mid_run"}
    assert recovered.manifest.reserved["issue_number"] == 123
    manifest_path = tmp_path / "larch-logs" / "implement" / "lost-run" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 2
    assert manifest["run_id"] == "lost-run"
    assert manifest["issue_number"] == 123
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
    assert run_logs.read_durable_flags(state_file=None, ctx=ctx) == run_logs.DurableFlags(
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

    assert run_logs.read_durable_flags(state_file=str(state), ctx=ctx) == run_logs.DurableFlags(
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

    assert run_logs.read_durable_flags(state_file=str(state), ctx=ctx).forked is False


def test_parse_pr_number_state_first_and_ctx_fallback(tmp_path: Path) -> None:
    assert run_logs.parse_pr_number(state_file=None, ctx_pr_number=7) is None
    state = tmp_path / "state.env"
    _ = state.write_text("PR_NUMBER=\n", encoding="utf-8")
    assert run_logs.parse_pr_number(state_file=str(state), ctx_pr_number="8") is None
    _ = state.write_text("PR_NUMBER=0\n", encoding="utf-8")
    assert run_logs.parse_pr_number(state_file=str(state), ctx_pr_number="8") is None
    _ = state.write_text("PR_NUMBER=9\n", encoding="utf-8")
    assert run_logs.parse_pr_number(state_file=str(state), ctx_pr_number=None) == 9


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
        ctx=ctx,
        batch_dir=batch_dir,
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
        ctx=ctx,
        batch_dir=batch_dir,
        step_label="pre-push",
        source_label="test",
    )
    batch = batch_dir / "execution-issues.ndjson"
    assert batch.is_file()
    assert secret not in batch.read_text(encoding="utf-8")


def test_execution_issues_batch_dedupes_repeated_warning_events(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    issue_log = tmp_path / "execution-issues.md"
    _ = issue_log.write_text("### Warnings\n- **Step 7a**: transient warning\n", encoding="utf-8")
    _ = (tmp_path / ".execution-issues-step7a-reached").write_text("", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    batch_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    batch_dir.mkdir(parents=True)

    for _index in range(2):
        run_logs._render_execution_issues_batch(  # pyright: ignore[reportPrivateUsage]
            ctx=ctx,
            batch_dir=batch_dir,
            step_label="pre-push",
            source_label="test",
        )
    _ = issue_log.write_text(
        "### Warnings\n- **Step 7a**: transient warning\n- **Step 8**: new warning\n",
        encoding="utf-8",
    )
    run_logs._render_execution_issues_batch(  # pyright: ignore[reportPrivateUsage]
        ctx=ctx,
        batch_dir=batch_dir,
        step_label="pre-push",
        source_label="test",
    )

    rows = [
        json.loads(line)
        for line in (batch_dir / "execution-issues.ndjson").read_text(encoding="utf-8").splitlines()
    ]
    assert [row["body"].strip() for row in rows] == [
        "- **Step 7a**: transient warning",
        "- **Step 8**: new warning",
    ]


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
        ctx=ctx,
        log_root=tmp_path / "larch-logs",
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
            ctx=ctx,
            log_root=tmp_path / "larch-logs",
            cwd=str(repo),
        )


def test_path_under_repo_rejects_traversal(tmp_path: Path) -> None:
    assert not run_logs.path_under_repo(repo_root=tmp_path, rel_path="../outside")
    assert run_logs.path_under_repo(repo_root=tmp_path, rel_path="docs/plan.md")


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
    skip = run_logs.flush_logs_pre(runner=runner, ctx=_ctx(tmp_path, str(state)))
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
    skip = run_logs.flush_logs_pre(runner=runner, ctx=_ctx(tmp_path, str(state)))
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
    monkeypatch.setattr(run_log_commit, "_REPO_ROOT", repo)
    ctx = _ctx(tmp_path, str(state))
    rel = run_logs._publish_run_tree_to_repo(  # pyright: ignore[reportPrivateUsage]
        ctx=ctx,
        log_root=tmp_path / "larch-logs",
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
        ctx=_ctx(tmp_path, str(state)),
        log_root=tmp_path / "larch-logs",
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
        log_root=log_root,
        skill="implement",
        run_id="run-1",
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
        ctx=_ctx(tmp_path, str(state)),
        log_root=tmp_path / "larch-logs",
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
        *,
        log_root: object,
        skill: object = None,
        run_id: object = None,
        cwd: str | None = None,
        pre_scrub_violations: int = 0,
    ) -> CommandResult:
        _ = log_root, skill, run_id, pre_scrub_violations, cwd
        commits.append(True)
        return CommandResult(
            ("git", "commit"),
            0,
            "a" * 40 + "\n",
            "",
            0.0,
        )

    def noop_write_final_report(**_kw: object) -> None:
        pass

    def noop_capture(**_kw: object) -> None:
        pass

    monkeypatch.setattr(run_logs, "_write_final_report", noop_write_final_report)
    monkeypatch.setattr(run_logs, "capture_session_transcript", noop_capture)
    monkeypatch.setattr(run_logs, "_commit_run", fake_commit)
    monkeypatch.setattr(run_log_flush, "_write_final_report", noop_write_final_report)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", noop_capture)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "_commit_run", fake_commit)  # type: ignore[arg-type]
    runner = RecordingRunner()
    skip = run_logs.flush_logs_pre(runner=runner, ctx=ctx, cwd=str(tmp_path / "repo"))
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
    monkeypatch.setattr(run_log_flush, "update_manifest", fail_update)  # type: ignore[arg-type]
    skip = run_logs.flush_logs_pre(runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path))
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
    skip = run_logs.flush_logs_pre(runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path))
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
    monkeypatch.setattr(run_log_flush, "_write_final_report", noop)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", noop)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", noop)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "_commit_run", noop_commit)  # type: ignore[arg-type]
    skip = run_logs.flush_logs_pre(runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path))
    assert not skip.skipped
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["steps_ran"]["step9a1"] is False


def test_flush_logs_pre_multi_flush_shipping_then_pr_created(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=0\nRUN_ID=run-abc\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")
    _ = (tmp_path / "run-flags.sh").write_text("FORCE_REQUESTED=false\n", encoding="utf-8")
    _ = (tmp_path / "finalize-state.sh").write_text("", encoding="utf-8")
    state = tmp_path / "ship-pr-state.sh"
    _ = state.write_text(
        "RUN_ID=run-abc\nSTALL_TRACKING=false\nMERGE=true\nPR_NUMBER=\nMERGE_RESULT=\nDRAFT=false\n",
        encoding="utf-8",
    )
    ctx = _ctx(tmp_path, str(state))
    _ = run_logs.init_run(ctx)
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"

    monkeypatch.setattr(final_report, "_final_report_token_fields", lambda **_k: {"cost_unavailable": True})  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(run_logs, "_render_ledger_reports", lambda *_a, **_k: None)  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(run_logs, "capture_session_transcript", lambda *_a, **_k: None)  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(
        run_logs,
        "_commit_run",
        lambda *_a, **_k: CommandResult(("git", "commit"), 0, "a" * 40 + "\n", "", 0.0),  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    )
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", lambda *_a, **_k: None)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", lambda *_a, **_k: None)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "_commit_run", lambda *_a, **_k: CommandResult(("git", "commit"), 0, "a" * 40 + "\n", "", 0.0))  # type: ignore[arg-type]

    skip1 = run_logs.flush_logs_pre(runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path))
    assert not skip1.skipped
    final1 = (run_dir / "final-summary.md").read_text(encoding="utf-8")
    heading1 = final1.split("—", 1)[-1].split("\n", 1)[0].strip()
    assert heading1 == "shipping"

    _ = state.write_text(
        "RUN_ID=run-abc\nSTALL_TRACKING=false\nMERGE=true\nPR_NUMBER=12\nPR_URL=https://example.test/pr/12\n"
        "PHASE=ci-initial\nMERGE_RESULT=\nDRAFT=false\n",
        encoding="utf-8",
    )

    skip2 = run_logs.flush_logs_pre(runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path), strict_final_report=True)
    assert not skip2.skipped
    final2 = (run_dir / "final-summary.md").read_text(encoding="utf-8")
    heading2 = final2.split("—", 1)[-1].split("\n", 1)[0].strip()
    assert heading2 == "pr-created"
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == config.MANIFEST_STATUS_IN_PROGRESS
    assert manifest["steps_ran"].get("step8") is True



def test_flush_logs_pre_rewrites_stalled_summary_after_clean_pr_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=0\nRUN_ID=run-abc\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")
    _ = (tmp_path / "run-flags.sh").write_text("FORCE_REQUESTED=false\n", encoding="utf-8")
    state = tmp_path / "ship-pr-state.sh"
    _ = state.write_text(
        "RUN_ID=run-abc\nSTALL_TRACKING=true\nMERGE=true\nPR_NUMBER=\nPHASE=stalled\nMERGE_RESULT=\nDRAFT=false\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "finalize-state.sh").write_text(
        "STALL_TRACKING=true\nSTALL_STEP=5\nPHASE=stalled\nEXIT_CODE=4\n",
        encoding="utf-8",
    )
    ctx = _ctx(tmp_path, str(state))
    _ = run_logs.init_run(ctx)
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"

    def fake_token_fields(implement_tmpdir: Path, run_id: str) -> dict[str, object]:
        _ = implement_tmpdir, run_id
        return {"cost_unavailable": True}

    def fake_commit(*_args: object, **_kwargs: object) -> CommandResult:
        return CommandResult(("git", "commit"), 0, "a" * 40 + "\n", "", 0.0)

    monkeypatch.setattr(final_report, "_final_report_token_fields", fake_token_fields)
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", lambda *_a, **_k: None)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", lambda *_a, **_k: None)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "_commit_run", fake_commit)  # type: ignore[arg-type]

    skip1 = run_logs.flush_logs_pre(runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path), strict_final_report=True)
    assert not skip1.skipped
    stalled_summary = (run_dir / "final-summary.md").read_text(encoding="utf-8")
    assert "— stalled" in stalled_summary
    assert "- **Outcome**: stalled" in stalled_summary

    _ = state.write_text(
        "RUN_ID=run-abc\nSTALL_TRACKING=false\nMERGE=true\nPR_NUMBER=12\nPR_URL=https://example.test/pr/12\n"
        "PHASE=ci-initial\nMERGE_RESULT=\nDRAFT=false\n",
        encoding="utf-8",
    )

    skip2 = run_logs.flush_logs_pre(runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path), strict_final_report=True)

    assert not skip2.skipped
    recovered_summary = (run_dir / "final-summary.md").read_text(encoding="utf-8")
    assert "— pr-created" in recovered_summary
    assert "- **Outcome**: stalled" not in recovered_summary


def test_manifest_only_stalled_summary_reconciliation_updates_heading_and_outcome(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    manifest: dict[str, object] = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": "run-abc",
        "steps_ran": {},
        "status": config.MANIFEST_STATUS_DONE,
        "pr_number": 12,
    }
    _ = (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _ = (run_dir / "final-summary.md").write_text(
        "## /implement run run-abc — stalled\n\n- **Outcome**: stalled\n- **PR**: #12\n",
        encoding="utf-8",
    )

    assert final_report.reconcile_stalled_summary_from_manifest(run_dir)

    text = (run_dir / "final-summary.md").read_text(encoding="utf-8")
    assert "## /implement run run-abc — merged" in text
    assert "- **Outcome**: stalled" not in text


def test_manifest_only_pr_number_without_done_status_keeps_stalled_summary(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    manifest: dict[str, object] = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": "run-abc",
        "steps_ran": {},
        "status": config.MANIFEST_STATUS_IN_PROGRESS,
        "pr_number": 12,
    }
    _ = (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _ = (run_dir / "final-summary.md").write_text(
        "## /implement run run-abc — stalled\n\n- **Outcome**: stalled\n- **PR**: #12\n",
        encoding="utf-8",
    )

    assert not final_report.reconcile_stalled_summary_from_manifest(run_dir)
    assert "- **Outcome**: stalled" in (run_dir / "final-summary.md").read_text(encoding="utf-8")


def test_manifest_only_stalled_summary_skips_rewrite_with_active_bail_reason(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    manifest: dict[str, object] = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": "run-abc",
        "steps_ran": {},
        "status": config.MANIFEST_STATUS_DONE,
        "pr_number": 12,
    }
    _ = (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _ = (run_dir / "final-summary.md").write_text(
        "## /implement run run-abc — stalled\n\n- **Outcome**: stalled\n- **PR**: #12\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "ship-pr-state.sh").write_text("BAIL_REASON=ci-failed\n", encoding="utf-8")

    assert not final_report.reconcile_stalled_summary_from_manifest(run_dir)
    assert "- **Outcome**: stalled" in (run_dir / "final-summary.md").read_text(encoding="utf-8")


def test_flush_logs_pre_retains_reloaded_step8_after_final_report_reconcile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    _ = run_logs.init_run(ctx)
    manifest_path = tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["steps_ran"] = {"step8": False}
    _ = manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    def fake_write_final_report(**_kw: object) -> None:
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        loaded["steps_ran"]["step8"] = True
        _ = manifest_path.write_text(json.dumps(loaded), encoding="utf-8")

    def noop(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(run_logs, "_write_final_report", fake_write_final_report)
    monkeypatch.setattr(run_logs, "capture_session_transcript", noop)
    monkeypatch.setattr(run_logs, "_render_ledger_reports", noop)
    monkeypatch.setattr(run_logs, "_commit_run", lambda *_a, **_k: CommandResult(("git", "commit"), 0, "", "", 0.0))  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "_write_final_report", fake_write_final_report)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", noop)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", noop)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "_commit_run", lambda *_a, **_k: CommandResult(("git", "commit"), 0, "", "", 0.0))  # type: ignore[arg-type]

    skip = run_logs.flush_logs_pre(runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path))

    assert not skip.skipped
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["steps_ran"]["step8"] is True


def test_flush_logs_pre_strict_final_report_error_returns_recovery_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    _ = run_logs.init_run(ctx)

    def fail_report(*_a: object, **_k: object) -> None:
        raise ShipError("reconcile failed")

    monkeypatch.setattr(run_logs, "_write_final_report", fail_report)

    skip = run_logs.flush_logs_pre(runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path), strict_final_report=True)

    assert skip.skipped
    assert skip.reason == run_logs.REFRESH_SKIP_RECOVERY_FAILED


def test_flush_logs_pre_strict_final_report_skips_tracking_upsert(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    _ = run_logs.init_run(ctx)
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    seen: list[bool] = []

    def fake_write_final_report(
        *,
        skip_tracking_upsert: bool = False,
        **_kw: object,
    ) -> None:
        seen.append(skip_tracking_upsert)
        _ = (run_dir / "final-summary.md").write_text("summary\n", encoding="utf-8")

    def noop(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(run_logs, "_write_final_report", fake_write_final_report)
    monkeypatch.setattr(run_logs, "capture_session_transcript", noop)
    monkeypatch.setattr(run_logs, "_render_ledger_reports", noop)
    monkeypatch.setattr(run_logs, "_commit_run", lambda *_a, **_k: CommandResult(("git", "commit"), 0, "", "", 0.0))  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "_write_final_report", fake_write_final_report)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", noop)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", noop)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "_commit_run", lambda *_a, **_k: CommandResult(("git", "commit"), 0, "", "", 0.0))  # type: ignore[arg-type]

    skip = run_logs.flush_logs_pre(runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path), strict_final_report=True)

    assert not skip.skipped
    assert seen == [True, True]


def test_render_token_timing_batches_skips_missing_refresh_json(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    run_logs._render_token_timing_batches(  # pyright: ignore[reportPrivateUsage]
        ctx=ctx,
        log_root=tmp_path / "larch-logs",
    )
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    assert not (tmp_path / "token-report-refresh.json").exists()
    assert not (run_dir / "token-report-refresh.json").exists()


def test_stage_ship_route_handoff_copies_when_present(tmp_path: Path) -> None:
    handoff = tmp_path / ".ship-route-exit-handoff.env"
    _ = handoff.write_text("NEXT_ACTION=ci-fix\nFAILED_RUN_ID=abc123\n", encoding="utf-8")
    ctx = _ctx(tmp_path)
    log_root = tmp_path / "larch-logs"
    run_logs._stage_ship_route_handoff(ctx=ctx, log_root=log_root)  # pyright: ignore[reportPrivateUsage]
    dest = log_root / "implement" / "run-abc" / "ship-route-exit-handoff.env"
    assert dest.is_file()
    assert "NEXT_ACTION=ci-fix" in dest.read_text(encoding="utf-8")


def test_stage_ship_route_handoff_skips_when_absent(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    log_root = tmp_path / "larch-logs"
    run_logs._stage_ship_route_handoff(ctx=ctx, log_root=log_root)  # pyright: ignore[reportPrivateUsage]
    dest = log_root / "implement" / "run-abc" / "ship-route-exit-handoff.env"
    assert not dest.exists()


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
    assert run_logs.read_state_kv(state_file=str(state), key="RUN_ID") == ""


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
    skip = run_logs.flush_logs_pre(runner=runner, ctx=ctx, cwd=None)
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
    monkeypatch.setattr(run_log_commit, "_REPO_ROOT", repo)

    def fail_copy(*_a: object, **_k: object) -> None:
        raise ShipError("copy failed")

    monkeypatch.setattr(run_logs, "_safe_copy_run_tree", fail_copy)
    monkeypatch.setattr(run_log_commit, "_safe_copy_run_tree", fail_copy)  # type: ignore[arg-type]
    ctx = _ctx(tmp_path, str(state))
    with pytest.raises(ShipError, match="copy failed"):
        _ = run_logs._publish_run_tree_to_repo(  # pyright: ignore[reportPrivateUsage]
            ctx=ctx,
            log_root=tmp_path / "larch-logs",
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


def test_commit_run_reports_copy_tree_scrub_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo_on_feature(repo)
    _ = (repo / "README.md").write_text("seed\n", encoding="utf-8")
    _ = subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    _ = subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True, capture_output=True)
    log_root = tmp_path / "larch-logs"
    src = log_root / "implement" / "run-abc"
    src.mkdir(parents=True)
    _ = (src / "artifact.txt").write_text("clean\n", encoding="utf-8")

    def fake_scrub(_directory: Path) -> tuple[int, int]:
        return 2, 1

    monkeypatch.setattr(run_logs, "_scrub_run_tree", fake_scrub)
    monkeypatch.setattr(run_log_commit, "_scrub_run_tree", fake_scrub)  # type: ignore[arg-type]

    result = run_logs._commit_run(  # pyright: ignore[reportPrivateUsage]
        log_root=log_root,
        skill="implement",
        run_id="run-abc",
        cwd=str(repo),
    )

    assert result.returncode == 0, result.stderr
    assert "SECRET_SCRUB_VIOLATIONS=2" in result.stdout


def test_commit_run_reports_pre_scrub_count_without_double_counting_same_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo_on_feature(repo)
    run_dir = repo / "larch-logs" / "design" / "run-abc"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "artifact.txt").write_text("clean\n", encoding="utf-8")
    _ = subprocess.run(["git", "add", "larch-logs"], cwd=repo, check=True, capture_output=True)
    _ = subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True, capture_output=True)

    def fail_scrub(_directory: Path) -> tuple[int, int]:
        raise AssertionError("same-tree run-log commit must not re-scrub")

    monkeypatch.setattr(run_logs, "_scrub_run_tree", fail_scrub)

    result = run_logs._commit_run(  # pyright: ignore[reportPrivateUsage]
        log_root=repo / "larch-logs",
        skill="design",
        run_id="run-abc",
        cwd=str(repo),
        pre_scrub_violations=3,
    )

    assert result.returncode == 0, result.stderr
    assert result.argv == ("true",)
    assert "SECRET_SCRUB_VIOLATIONS=3" in result.stdout


def test_replace_tree_with_backup_refuses_symlink_and_non_directory(tmp_path: Path) -> None:
    staged_for_symlink = tmp_path / "staged-symlink"
    staged_for_symlink.mkdir()
    link_target = tmp_path / "link-target"
    link_target.mkdir()
    symlink_dest = tmp_path / "symlink-dest"
    symlink_dest.symlink_to(link_target, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink destination"):
        run_logs._replace_tree_with_backup(staged=staged_for_symlink, dest=symlink_dest)  # pyright: ignore[reportPrivateUsage]

    staged_for_file = tmp_path / "staged-file"
    staged_for_file.mkdir()
    file_dest = tmp_path / "file-dest"
    _ = file_dest.write_text("not a tree\n", encoding="utf-8")

    with pytest.raises(ValueError, match="non-directory destination"):
        run_logs._replace_tree_with_backup(staged=staged_for_file, dest=file_dest)  # pyright: ignore[reportPrivateUsage]


def test_copy_tree_to_repo_replaces_live_tree_without_rmtree(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    log_root = tmp_path / "larch-logs"
    src = log_root / "implement" / "run-abc"
    src.mkdir(parents=True)
    _ = (src / "artifact.txt").write_text("new\n", encoding="utf-8")
    repo = tmp_path / "repo"
    dest = repo / "larch-logs" / "implement" / "run-abc"
    dest.mkdir(parents=True)
    _ = (dest / "artifact.txt").write_text("old\n", encoding="utf-8")
    original_rmtree = run_logs.shutil.rmtree

    def guarded_rmtree(path: Path | str, *args: Any, **kwargs: Any) -> None:
        assert Path(path) != dest
        original_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(run_logs.shutil, "rmtree", guarded_rmtree)

    rels, copied_dest, violations, scrub_error = run_logs._copy_tree_to_repo(  # pyright: ignore[reportPrivateUsage]
        log_root=log_root,
        repo_root=repo,
        skill="implement",
        run_id="run-abc",
    )

    assert rels == ["larch-logs/implement/run-abc"]
    assert copied_dest == dest
    assert violations == 0
    assert scrub_error is None
    assert (dest / "artifact.txt").read_text(encoding="utf-8") == "new\n"


def test_copy_tree_to_repo_recovers_interrupted_backup(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    src = log_root / "implement" / "run-abc"
    src.mkdir(parents=True)
    _ = (src / "artifact.txt").write_text("new\n", encoding="utf-8")
    repo = tmp_path / "repo"
    backup = repo / "larch-logs" / "implement" / ".run-abc.removing"
    backup.mkdir(parents=True)
    _ = (backup / "artifact.txt").write_text("old\n", encoding="utf-8")
    dest = repo / "larch-logs" / "implement" / "run-abc"

    rels, copied_dest, violations, scrub_error = run_logs._copy_tree_to_repo(  # pyright: ignore[reportPrivateUsage]
        log_root=log_root,
        repo_root=repo,
        skill="implement",
        run_id="run-abc",
    )

    assert rels == ["larch-logs/implement/run-abc"]
    assert copied_dest == dest
    assert violations == 0
    assert scrub_error is None
    assert not backup.exists()
    assert (dest / "artifact.txt").read_text(encoding="utf-8") == "new\n"


def test_commit_run_warns_when_manifest_update_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo_on_feature(repo)
    log_root = tmp_path / "larch-logs"
    manifest = log_root / "implement" / "run-abc" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    _ = manifest.write_text("{}", encoding="utf-8")

    def fail_update(*, path: Path, updates: dict[str, Any]) -> dict[str, Any]:
        _ = path, updates
        raise OSError("manifest unavailable")

    def no_rels(**_kw: object) -> tuple[list[str], Path, int, str | None]:
        return [], repo / "larch-logs" / "implement" / "run-abc", 0, None

    monkeypatch.setattr(run_logs, "_update_manifest_v2", fail_update)
    monkeypatch.setattr(run_logs, "_copy_tree_to_repo", no_rels)
    monkeypatch.setattr(run_log_commit, "_update_manifest_v2", fail_update)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_commit, "_copy_tree_to_repo", no_rels)  # type: ignore[arg-type]

    result = run_logs._commit_run(  # pyright: ignore[reportPrivateUsage]
        log_root=log_root,
        skill="implement",
        run_id="run-abc",
        cwd=str(repo),
    )

    assert result.returncode == 0
    assert "WARN: larch-log commit manifest update failed: manifest unavailable" in capsys.readouterr().err


def test_commit_run_warns_when_breadcrumb_publish_returns_nonzero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo_on_feature(repo)
    log_root = tmp_path / "larch-logs"
    dest = repo / "larch-logs" / "implement" / "run-abc"
    breadcrumb_argv: list[str] = []

    def copied_rels(**_kw: object) -> tuple[list[str], Path, int, str | None]:
        return ["larch-logs/implement/run-abc"], dest, 0, None

    def fail_breadcrumbs(argv: list[str]) -> int:
        breadcrumb_argv.extend(argv)
        return 1

    monkeypatch.setattr(run_logs, "_copy_tree_to_repo", copied_rels)
    monkeypatch.setattr(run_logs, "publish_breadcrumbs_main", fail_breadcrumbs)
    monkeypatch.setattr(run_log_commit, "_copy_tree_to_repo", copied_rels)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_commit, "publish_breadcrumbs_main", fail_breadcrumbs)  # type: ignore[arg-type]

    result = run_logs._commit_run(  # pyright: ignore[reportPrivateUsage]
        log_root=log_root,
        skill="implement",
        run_id="run-abc",
        cwd=str(repo),
    )

    assert result.returncode == 0
    assert breadcrumb_argv == [
        "--source-dir",
        str(tmp_path / "breadcrumbs"),
        "--dest-dir",
        str(dest / "breadcrumbs"),
    ]
    assert "WARN: larch-log commit breadcrumb publish failed: rc=1" in capsys.readouterr().err


def test_commit_run_publishes_breadcrumbs_without_breadcrumbs_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo_on_feature(repo)
    log_root = tmp_path / "larch-logs"
    run_dir = log_root / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "manifest.json").write_text("{}", encoding="utf-8")
    _ = (run_dir / "artifact.txt").write_text("run artifact\n", encoding="utf-8")
    _ = (tmp_path / "larch-quiet-ship.py-123.log").write_text("ship breadcrumb\n", encoding="utf-8")
    for key in ("DESIGN_TMPDIR", "REVIEW_TMPDIR", "RESEARCH_TMPDIR"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))

    result = run_logs._commit_run(  # pyright: ignore[reportPrivateUsage]
        log_root=log_root,
        skill="implement",
        run_id="run-abc",
        cwd=str(repo),
    )

    quiet_log = repo / "larch-logs" / "implement" / "run-abc" / "breadcrumbs" / "quiet.log"
    assert result.returncode == 0
    assert quiet_log.is_file()
    quiet_text = quiet_log.read_text(encoding="utf-8")
    assert "=== larch-quiet-ship.py-123.log ===" in quiet_text
    assert "ship breadcrumb" in quiet_text


def test_larch_log_write_rebases_root_relative_log_root_and_input_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session = tmp_path / "session"
    session.mkdir()
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(session))
    source = session / "token-report.json"
    _ = source.write_text("token report\n", encoding="utf-8")

    rc = run_logs.larch_log_write_main([
        "--log-root",
        "/larch-logs",
        "--skill",
        "implement",
        "--run-id",
        "run-abc",
        "--batch",
        "token-report",
        "--input-file",
        str(source),
    ])

    assert rc == 0
    assert (session / "larch-logs" / "implement" / "run-abc" / "token-report.json").read_text(encoding="utf-8") == "token report\n"


def test_rebase_under_tmpdir_handles_session_local_absolute_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "record.json"
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))

    assert _rebase_under_tmpdir(str(source)) == source


def test_rebase_under_tmpdir_keeps_external_absolute_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = Path("/var/folders/example/T/record.json")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))

    assert _rebase_under_tmpdir(str(source)) == source


def test_rebase_under_tmpdir_prepends_relative_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))

    assert _rebase_under_tmpdir("record.json") == tmp_path / "record.json"


def test_rebase_under_tmpdir_uses_default_leaf_for_empty_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))

    assert _rebase_under_tmpdir("", default_leaf="default.json") == tmp_path / "default.json"


def test_rebase_under_tmpdir_returns_path_without_implement_tmpdir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("IMPLEMENT_TMPDIR", raising=False)

    assert _rebase_under_tmpdir("record.json") == Path("record.json")


def test_checks_digest_sizes_batch_is_append_mode_tsv(tmp_path: Path) -> None:
    assert run_logs._batch_mode("checks-digest-sizes") == "append"  # pyright: ignore[reportPrivateUsage]
    assert run_logs._batch_extension("checks-digest-sizes") == ".tsv"  # pyright: ignore[reportPrivateUsage]
    assert run_logs._batch_sanitizer("checks-digest-sizes") == "none"  # pyright: ignore[reportPrivateUsage]
    record = tmp_path / "row.tsv"
    _ = record.write_text(
        "site\tattempt\tredacted_bytes\tdigest_bytes\tredacted_tokens\tdigest_tokens\tsaved_bytes\tsaved_tokens\tdigest_truncated\n"
        "step6\t1\t100\t20\t25\t5\t80\t20\tfalse\n",
        encoding="utf-8",
    )

    rc = run_logs.larch_log_append_main([
        "--log-root",
        str(tmp_path / "larch-logs"),
        "--skill",
        "implement",
        "--run-id",
        "run-abc",
        "--batch",
        "checks-digest-sizes",
        "--record-file",
        str(record),
    ])

    assert rc == 0
    committed = tmp_path / "larch-logs" / "implement" / "run-abc" / "checks-digest-sizes.tsv"
    assert committed.read_text(encoding="utf-8") == record.read_text(encoding="utf-8")


def test_larch_log_append_rebases_root_relative_log_root_and_record_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session = tmp_path / "session"
    session.mkdir()
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(session))
    record = session / "execution-issue-record.ndjson"
    _ = record.write_text('{"message":"ok"}\n', encoding="utf-8")

    rc = run_logs.larch_log_append_main([
        "--log-root",
        "/larch-logs",
        "--skill",
        "implement",
        "--run-id",
        "run-abc",
        "--batch",
        "execution-issues",
        "--record-file",
        str(record),
    ])

    assert rc == 0
    assert (session / "larch-logs" / "implement" / "run-abc" / "execution-issues.ndjson").read_text(encoding="utf-8") == '{"message":"ok"}\n'


def test_larch_log_flush_warns_when_stage_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.delenv("LARCH_NO_LOGS_COMMIT", raising=False)
    _ = (tmp_path / "session-id").write_text("run-abc\n", encoding="utf-8")

    def fail_stage(*_args: object, **_kwargs: object) -> None:
        raise OSError("stage unavailable")

    monkeypatch.setattr(run_logs, "_stage_pre_commit", fail_stage)
    monkeypatch.setattr(run_log_flush, "_stage_pre_commit", fail_stage)  # type: ignore[arg-type]

    rc = run_logs.larch_log_flush_main([])

    assert rc == 0
    assert "WARN: larch-log flush failed: stage unavailable" in capsys.readouterr().err


def test_larch_log_flush_warns_when_commit_run_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.delenv("LARCH_NO_LOGS_COMMIT", raising=False)
    _ = (tmp_path / "session-id").write_text("run-abc\n", encoding="utf-8")

    def fail_commit(*_args: object, **_kwargs: object) -> CommandResult:
        return CommandResult(
            ("run-log", "commit"),
            1,
            "",
            "refusing to replace symlink destination: /some/path\n",
            0.0,
        )

    monkeypatch.setattr(run_logs, "_stage_pre_commit", lambda *_a, **_k: None)  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(run_logs, "_commit_run", fail_commit)
    monkeypatch.setattr(run_log_flush, "_stage_pre_commit", lambda *_a, **_k: None)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "_commit_run", fail_commit)

    rc = run_logs.larch_log_flush_main([])

    assert rc == 0
    err = capsys.readouterr().err
    assert "WARN: larch-log flush failed: rc=1" in err
    assert "refusing to replace symlink destination: /some/path" in err


def test_larch_log_commit_rejects_bad_pre_scrub_violations(tmp_path: Path) -> None:
    rc = run_logs.larch_log_commit_main(
        [
            "--log-root",
            str(tmp_path / "larch-logs"),
            "--skill",
            "implement",
            "--run-id",
            "run-abc",
            "--pre-scrub-violations",
            "-1",
        ]
    )

    assert rc == 1


def test_write_round_commits_review_threshold_inputs(tmp_path: Path) -> None:
    source = tmp_path / "source-round"
    source.mkdir()
    _ = (source / "collector-results.env").write_text("STATUS=OK\n", encoding="utf-8")
    _ = (source / "review-core-threshold.env").write_text("THRESHOLD_OK=true\n", encoding="utf-8")

    rc = run_logs.larch_log_write_round_main([
        "--log-root",
        str(tmp_path / "larch-logs"),
        "--skill",
        "implement",
        "--run-id",
        "run-abc",
        "--round",
        "1",
        "--source-dir",
        str(source),
    ])

    assert rc == 0
    round_dir = tmp_path / "larch-logs" / "implement" / "run-abc" / "round-1"
    assert (round_dir / "collector-results.env").read_text(encoding="utf-8") == "STATUS=OK\n"
    assert (round_dir / "review-core-threshold.env").read_text(encoding="utf-8") == "THRESHOLD_OK=true\n"



def test_write_round_commits_panel_prompt_sizes(tmp_path: Path) -> None:
    source = tmp_path / "source-round"
    source.mkdir()
    _ = (source / "panel-prompt-sizes.tsv").write_text(
        "site\tphase\tround_num\tslot\tslot_kind\ttool\toutput\tprompt_bytes\tprompt_tokens\tagent_file\tagent_bytes\tagent_tokens\n"
        "review\t\t1\tcorrectness\tspecialist\tcursor\tout.txt\t12\t3\tagents/reviewer-testing.md\t8\t2\n",
        encoding="utf-8",
    )

    rc = run_logs.larch_log_write_round_main([
        "--log-root",
        str(tmp_path / "larch-logs"),
        "--skill",
        "implement",
        "--run-id",
        "run-abc",
        "--round",
        "1",
        "--source-dir",
        str(source),
    ])

    assert rc == 0
    committed = tmp_path / "larch-logs" / "implement" / "run-abc" / "round-1" / "panel-prompt-sizes.tsv"
    assert committed.is_file()
    assert "prompt_bytes" in committed.read_text(encoding="utf-8")

def test_round_artifact_allowlist_includes_degraded_attempt_tallies() -> None:
    assert run_logs._round_artifact_included("voting-tally-degraded-attempt-1.md")  # pyright: ignore[reportPrivateUsage]
    assert run_logs._round_artifact_included("voting-tally-degraded-attempt-2.md")  # pyright: ignore[reportPrivateUsage]
    assert run_logs._round_artifact_included("panel-manifest.ndjson.output-files.dropped-slots")  # pyright: ignore[reportPrivateUsage]
    assert run_logs._round_artifact_included("panel-prompt-sizes.tsv")  # pyright: ignore[reportPrivateUsage]
    assert run_logs._round_artifact_included("dropped-dyn-lint-cursor-straggler-dropped.txt")  # pyright: ignore[reportPrivateUsage]
    assert not run_logs._round_artifact_included("dyn-lint-output.txt")  # pyright: ignore[reportPrivateUsage]


def test_write_round_commits_degraded_attempt_tallies(tmp_path: Path) -> None:
    source = tmp_path / "source-round"
    source.mkdir()
    _ = (source / "collector-results.env").write_text("STATUS=OK\n", encoding="utf-8")
    _ = (source / "voting-tally-degraded-attempt-1.md").write_text("degraded attempt one\n", encoding="utf-8")
    _ = (source / "voting-tally-degraded-attempt-2.md").write_text("degraded attempt two\n", encoding="utf-8")

    rc = run_logs.larch_log_write_round_main([
        "--log-root",
        str(tmp_path / "larch-logs"),
        "--skill",
        "implement",
        "--run-id",
        "run-abc",
        "--round",
        "1",
        "--source-dir",
        str(source),
    ])

    assert rc == 0
    round_dir = tmp_path / "larch-logs" / "implement" / "run-abc" / "round-1"
    assert (round_dir / "collector-results.env").read_text(encoding="utf-8") == "STATUS=OK\n"
    assert (round_dir / "voting-tally-degraded-attempt-1.md").read_text(encoding="utf-8") == "degraded attempt one\n"
    assert (round_dir / "voting-tally-degraded-attempt-2.md").read_text(encoding="utf-8") == "degraded attempt two\n"


def test_write_round_commits_dropped_slot_artifacts_and_redacts(tmp_path: Path) -> None:
    source = tmp_path / "source-round"
    source.mkdir()
    secret = "sk-proj-" + "a" * 48
    _ = (source / "panel-manifest.ndjson.output-files.dropped-slots").write_text(
        "dyn-dyn-lint-escalation\tcursor\tstraggler-dropped\tcut\n",
        encoding="utf-8",
    )
    _ = (source / "dropped-dyn-lint-cursor-straggler-dropped.txt").write_text(
        f"stderr with token {secret}\n",
        encoding="utf-8",
    )
    _ = (source / "dyn-dyn-lint-escalation-output.txt").write_text("raw reviewer output\n", encoding="utf-8")

    rc = run_logs.larch_log_write_round_main([
        "--log-root",
        str(tmp_path / "larch-logs"),
        "--skill",
        "implement",
        "--run-id",
        "run-abc",
        "--round",
        "1",
        "--source-dir",
        str(source),
    ])

    assert rc == 0
    round_dir = tmp_path / "larch-logs" / "implement" / "run-abc" / "round-1"
    assert (round_dir / "panel-manifest.ndjson.output-files.dropped-slots").is_file()
    diag_text = (round_dir / "dropped-dyn-lint-cursor-straggler-dropped.txt").read_text(encoding="utf-8")
    assert secret not in diag_text
    assert not (round_dir / "dyn-dyn-lint-escalation-output.txt").exists()


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


def test_scrub_run_tree_propagates_scrubber_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "findings.md").write_text("plain\n", encoding="utf-8")

    def _boom(_text: str) -> tuple[str, dict[str, int]]:
        raise RuntimeError("scrubber unavailable")

    monkeypatch.setattr(run_logs.redact, "scrub_log_secrets", _boom)
    with pytest.raises(RuntimeError, match="scrubber unavailable"):
        _ = run_logs._scrub_run_tree(run_dir)  # pyright: ignore[reportPrivateUsage]


def test_warn_secret_scrub_remains_warning_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_logs._warn_secret_scrub(violations=2, files_scrubbed=1, directory=tmp_path)  # pyright: ignore[reportPrivateUsage]

    assert "SECRETS DETECTED AND SCRUBBED" in capsys.readouterr().err


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
    monkeypatch.setattr(run_log_commit, "_REPO_ROOT", repo)
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
        runner=runner,
        ctx=_ctx(tmp_path, str(state)),
        log_root=tmp_path / "larch-logs",
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
    monkeypatch.setattr(run_log_flush, "_commit_run", fake_commit)
    skip = run_logs.flush_logs_pre(runner=RecordingRunner(), ctx=_ctx(tmp_path), cwd=str(tmp_path))
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
    monkeypatch.setattr(run_log_commit, "_REPO_ROOT", repo)
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
        runner=runner,
        ctx=_ctx(tmp_path, str(state)),
        log_root=tmp_path / "larch-logs",
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
    monkeypatch.setattr(run_log_commit, "_REPO_ROOT", repo)
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
        runner=runner,
        ctx=_ctx(tmp_path, str(state)),
        log_root=tmp_path / "larch-logs",
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
    monkeypatch.setattr(run_log_commit, "_REPO_ROOT", repo)
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
            runner=runner,
            ctx=_ctx(tmp_path, str(state)),
            log_root=tmp_path / "larch-logs",
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
    monkeypatch.setattr(run_log_commit, "_REPO_ROOT", repo)
    rel = "larch-logs/implement/run-abc"
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "status"), 0, status_stdout, "", 0.01),
            CommandResult(failing_call, 1, "", "failed", 0.01),
        ],
    )
    with pytest.raises(ShipError, match="run-log volatile cleanup failed"):
        _ = run_logs._larch_log_commit(  # pyright: ignore[reportPrivateUsage]
            runner=runner,
            ctx=_ctx(tmp_path, str(state)),
            log_root=tmp_path / "larch-logs",
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
    monkeypatch.setattr(run_log_commit, "_REPO_ROOT", repo)
    rel = "larch-logs/implement/run-abc"

    def fake_scrub(_directory: Path) -> tuple[int, int]:
        return 1, 1

    monkeypatch.setattr(run_logs, "_scrub_run_tree", fake_scrub)
    monkeypatch.setattr(run_log_commit, "_scrub_run_tree", fake_scrub)
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "status"), 0, f" M {rel}/token-report-refresh.json\n", "", 0.01),
            CommandResult(("git", "restore"), 0, "", "", 0.01),
            CommandResult(("git", "status"), 0, "", "", 0.01),
        ],
    )
    result = run_logs._larch_log_commit(  # pyright: ignore[reportPrivateUsage]
        runner=runner,
        ctx=_ctx(tmp_path, str(state)),
        log_root=tmp_path / "larch-logs",
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
    monkeypatch.setattr(run_log_commit, "_REPO_ROOT", repo)
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
        runner=runner,
        ctx=_ctx(tmp_path, str(state)),
        log_root=tmp_path / "larch-logs",
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
    monkeypatch.setattr(run_log_commit, "_REPO_ROOT", repo)
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
        runner=runner,
        ctx=_ctx(tmp_path, str(state)),
        log_root=tmp_path / "larch-logs",
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
    monkeypatch.setattr(run_log_commit, "_REPO_ROOT", repo)
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
        runner=runner,
        ctx=_ctx(tmp_path, str(state)),
        log_root=tmp_path / "larch-logs",
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
    monkeypatch.setattr(run_log_commit, "_REPO_ROOT", repo)
    ctx = _ctx(tmp_path, str(state))
    rel = run_logs._publish_run_tree_to_repo(  # pyright: ignore[reportPrivateUsage]
        ctx=ctx,
        log_root=tmp_path / "larch-logs",
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
            runner=RecordingRunner(),
            ctx=ctx,
            log_root=tmp_path / "larch-logs",
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
        *, batch: str, input_file: Path, **_kw: object
    ) -> tuple[Path, bool, bool]:
        write_batches.append(batch)
        return (input_file, True, False)

    monkeypatch.setattr(run_logs, "_write_batch", fake_write_batch)
    monkeypatch.setattr(run_log_flush, "_write_batch", fake_write_batch)
    ctx = _ctx(tmp_path, str(state))
    runner = RecordingRunner()
    run_logs._render_ledger_reports(runner=runner, ctx=ctx, log_root=tmp_path / "logs")  # pyright: ignore[reportPrivateUsage]

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
        *, batch: str, input_file: Path, **_kw: object
    ) -> tuple[Path, bool, bool]:
        write_batches.append(batch)
        return (input_file, True, False)

    monkeypatch.setattr(run_logs, "_write_batch", fake_write_batch)
    monkeypatch.setattr(run_log_flush, "_write_batch", fake_write_batch)
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
    run_logs._render_ledger_reports(runner=runner, ctx=ctx, log_root=tmp_path / "logs")  # pyright: ignore[reportPrivateUsage]

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
    run_logs._render_ledger_reports(runner=runner, ctx=ctx, log_root=tmp_path / "logs")  # pyright: ignore[reportPrivateUsage]

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
    run_logs._render_ledger_reports(runner=runner, ctx=ctx, log_root=tmp_path / "logs")  # pyright: ignore[reportPrivateUsage]

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


def test_verify_completeness_bailed_heading_with_pr_number_does_not_bail_skip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(run_logs, "_REPO_ROOT", tmp_path)
    run_dir = tmp_path / "larch-logs" / "implement" / "RUN1"
    run_dir.mkdir(parents=True)
    manifest: dict[str, object] = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": "RUN1",
        "steps_ran": {},
        "status": "partial",
        "pr_number": 7,
    }
    _ = (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _ = (run_dir / "final-summary.md").write_text("## /implement run RUN1 — bailed\n", encoding="utf-8")
    tsv = tmp_path / "required.tsv"
    _ = tsv.write_text("relative_path\tcondition\nrun-statistics.md\tstep9a1\n", encoding="utf-8")
    monkeypatch.setenv("LARCH_VERIFY_MANIFEST", str(tsv))

    assert run_logs.verify_completeness_main([str(run_dir)]) == 1
    assert "run-statistics.md" in capsys.readouterr().out


def test_verify_completeness_stalled_heading_with_pr_number_keeps_bail_skip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(run_logs, "_REPO_ROOT", tmp_path)
    run_dir = tmp_path / "larch-logs" / "implement" / "RUN1"
    run_dir.mkdir(parents=True)
    manifest: dict[str, object] = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": "RUN1",
        "steps_ran": {},
        "status": "partial",
        "pr_number": 7,
    }
    _ = (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _ = (run_dir / "final-summary.md").write_text("## /implement run RUN1 — stalled\n", encoding="utf-8")
    tsv = tmp_path / "required.tsv"
    _ = tsv.write_text("relative_path\tcondition\nrun-statistics.md\tstep9a1\n", encoding="utf-8")
    monkeypatch.setenv("LARCH_VERIFY_MANIFEST", str(tsv))

    assert run_logs.verify_completeness_main([str(run_dir)]) == 0
    assert "OK" in capsys.readouterr().out


def test_verify_completeness_bailed_heading_without_pr_number_keeps_bail_skip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(run_logs, "_REPO_ROOT", tmp_path)
    run_dir = tmp_path / "larch-logs" / "implement" / "RUN1"
    run_dir.mkdir(parents=True)
    manifest: dict[str, object] = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": "RUN1",
        "steps_ran": {},
        "status": "partial",
    }
    _ = (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _ = (run_dir / "final-summary.md").write_text("## /implement run RUN1 — bailed\n", encoding="utf-8")
    tsv = tmp_path / "required.tsv"
    _ = tsv.write_text("relative_path\tcondition\nrun-statistics.md\tstep9a1\n", encoding="utf-8")
    monkeypatch.setenv("LARCH_VERIFY_MANIFEST", str(tsv))

    assert run_logs.verify_completeness_main([str(run_dir)]) == 0
    assert "OK" in capsys.readouterr().out


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


def test_capture_transcript_main_defer_commit_no_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """defer_commit=true success path must not append a Warnings entry."""
    transcript = tmp_path / "transcript.jsonl"
    _ = transcript.write_text('{"type":"message"}\n', encoding="utf-8")
    source = tmp_path / "source.txt"
    _ = source.write_text(f"TRANSCRIPT_PATH={transcript}\n", encoding="utf-8")
    log_root = tmp_path / "larch-logs"
    issues_log = tmp_path / "execution-issues.md"
    _ = issues_log.write_text("", encoding="utf-8")

    def _fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        for i, arg in enumerate(args):
            if arg == "--output" and i + 1 < len(args):
                _ = Path(args[i + 1]).write_text('{"type":"stub"}\n', encoding="utf-8")
                break
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        rc = run_logs.capture_transcript_main(
            [
                "--source-file",
                str(source),
                "--log-root",
                str(log_root),
                "--skill",
                "implement",
                "--run-id",
                "RUN1",
                "--no-logs-commit",
                "false",
                "--execution-issues-log",
                str(issues_log),
                "--defer-commit",
                "true",
            ]
        )
    assert rc == 0
    assert "SESSION_TRANSCRIPT_STATUS=captured" in buf.getvalue()
    assert "session transcript was written; commit deferred" not in issues_log.read_text(encoding="utf-8")


def test_capture_transcript_main_preserves_system_tmp_render_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    system_tmp = tmp_path / "system-tmp"
    implement_tmp = tmp_path / "implement-tmp"
    system_tmp.mkdir()
    implement_tmp.mkdir()
    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(implement_tmp))
    monkeypatch.setattr(run_log_flush.tempfile, "tempdir", str(system_tmp))
    transcript = tmp_path / "transcript.jsonl"
    _ = transcript.write_text('{"type":"message"}\n', encoding="utf-8")
    source = tmp_path / "source.txt"
    _ = source.write_text(f"TRANSCRIPT_PATH={transcript}\n", encoding="utf-8")
    log_root = tmp_path / "larch-logs"
    rendered_payload = '{"type":"stub"}\n'

    def _fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        output = Path(args[args.index("--output") + 1])
        assert output.is_relative_to(system_tmp)
        assert not output.is_relative_to(implement_tmp)
        _ = output.write_text(rendered_payload, encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        rc = run_logs.capture_transcript_main(
            [
                "--source-file",
                str(source),
                "--log-root",
                str(log_root),
                "--skill",
                "implement",
                "--run-id",
                "RUN1",
                "--defer-commit",
                "true",
            ]
        )

    captured = buf.getvalue()
    committed = log_root / "implement" / "RUN1" / "session-transcript.jsonl"
    assert rc == 0
    assert "SESSION_TRANSCRIPT_STATUS=captured" in captured
    assert "write-failed" not in captured
    assert committed.read_text(encoding="utf-8") == rendered_payload


def test_init_run_writes_manifest_v2(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    _ = run_logs.init_run(ctx, run_id="run-abc")
    manifest_path = tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == 2
    assert data["skill"] == "implement"


def test_publish_breadcrumbs_noops_source_outside_session_tmpdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = tmp_path / "session"
    outside = tmp_path / "outside"
    (outside / "breadcrumbs").mkdir(parents=True)
    # A quiet log present outside the session tmpdir must NOT be published.
    _ = (outside / "larch-quiet-implement-1.log").write_text("hi\n", encoding="utf-8")
    for key in ("DESIGN_TMPDIR", "REVIEW_TMPDIR", "RESEARCH_TMPDIR"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(session))
    dest = tmp_path / "dest"
    rc = run_logs.publish_breadcrumbs_main(
        ["--source-dir", str(outside / "breadcrumbs"), "--dest-dir", str(dest / "breadcrumbs")]
    )
    assert rc == 0
    assert not (dest / "breadcrumbs").exists()


def test_publish_breadcrumbs_allows_source_under_session_tmpdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = tmp_path / "session"
    (session / "breadcrumbs").mkdir(parents=True)
    _ = (session / "larch-quiet-implement-1.log").write_text("hello\n", encoding="utf-8")
    for key in ("DESIGN_TMPDIR", "REVIEW_TMPDIR", "RESEARCH_TMPDIR"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(session))
    dest = tmp_path / "dest"
    dest.mkdir()
    rc = run_logs.publish_breadcrumbs_main(
        ["--source-dir", str(session / "breadcrumbs"), "--dest-dir", str(dest / "breadcrumbs")]
    )
    assert rc == 0
    assert (dest / "breadcrumbs").is_dir()


def test_publish_breadcrumbs_main_succeeds_without_breadcrumbs_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = tmp_path / "session"
    session.mkdir()
    _ = (session / "larch-quiet-implement-1.log").write_text("hello from quiet log\n", encoding="utf-8")
    for key in ("DESIGN_TMPDIR", "REVIEW_TMPDIR", "RESEARCH_TMPDIR"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(session))
    dest = tmp_path / "dest"

    rc = run_logs.publish_breadcrumbs_main(
        ["--source-dir", str(session / "breadcrumbs"), "--dest-dir", str(dest / "breadcrumbs")]
    )

    quiet_log = dest / "breadcrumbs" / "quiet.log"
    assert rc == 0
    assert quiet_log.is_file()
    quiet_text = quiet_log.read_text(encoding="utf-8")
    assert "=== larch-quiet-implement-1.log ===" in quiet_text
    assert "hello from quiet log" in quiet_text


def test_publish_breadcrumbs_replaces_live_tree_without_rmtree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = tmp_path / "session"
    (session / "breadcrumbs").mkdir(parents=True)
    _ = (session / "larch-quiet-implement-1.log").write_text("hello\n", encoding="utf-8")
    for key in ("DESIGN_TMPDIR", "REVIEW_TMPDIR", "RESEARCH_TMPDIR"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(session))
    dest = tmp_path / "dest" / "breadcrumbs"
    dest.mkdir(parents=True)
    _ = (dest / "quiet.log").write_text("old\n", encoding="utf-8")
    original_rmtree = run_logs.shutil.rmtree

    def guarded_rmtree(path: Path | str, *args: Any, **kwargs: Any) -> None:
        assert Path(path) != dest
        original_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(run_logs.shutil, "rmtree", guarded_rmtree)

    rc = run_logs.publish_breadcrumbs_main(
        ["--source-dir", str(session / "breadcrumbs"), "--dest-dir", str(dest)]
    )

    assert rc == 0
    assert "hello" in (dest / "quiet.log").read_text(encoding="utf-8")


def test_append_failure_sanitizes_diagram_warning_captures(tmp_path: Path) -> None:
    output_file = tmp_path / "architecture-diagram-sanitizer.failure.log"
    _ = output_file.write_text(
        "stderr\nparticipant A as Alice\nA->>B: hi\nsubgraph group\n",
        encoding="utf-8",
    )
    log_path = tmp_path / "execution-issues.md"

    rc = run_logs.append_failure_main(
        [
            "--log",
            str(log_path),
            "--site",
            "design Step 5b.5",
            "--tool",
            "mermaid sanitize",
            "--exit-code",
            "1",
            "--category",
            "Warnings",
            "--output-file",
            str(output_file),
        ]
    )

    assert rc == 0
    text = log_path.read_text(encoding="utf-8")
    assert "participant" not in text
    assert "->>" not in text
    assert "subgraph" not in text
    assert "stderr" in text


def test_manifest_v2_round_trip_preserves_reserved_and_extension_bytes() -> None:
    original = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": "run-1",
        "operator_cwd": "<OPERATOR_CWD>",
        "operator_repo_root": "<REPO_ROOT>",
        "parent_skill": None,
        "issue_number": 42,
        "larch_version": "1.2.3",
        "model_roster": {"main": "model"},
        "effort": "unknown",
        "started_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "attempt": 1,
        "superseded_by": None,
        "stalled_at_step": "5",
        "steps_ran": {"step5": True},
        "flags": {"merge": True},
        "status": "partial",
        "pr_number": 9,
        "extension_key": "kept",
    }

    manifest = run_logs.Manifest.from_json(original)
    rendered = manifest.to_json(existing=original)

    assert rendered == original
    text = json.dumps(rendered, indent=2, sort_keys=True) + "\n"
    assert '"created_at"' not in text
    assert '"version"' not in text
    assert manifest.reserved["stalled_at_step"] == "5"
    assert manifest.extra == {"extension_key": "kept"}


def test_update_manifest_routes_reserved_keys_to_top_level(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    _ = run_logs.init_run(ctx, run_id="run-abc")

    updated = run_logs.update_manifest(ctx, stalled_at_step="7", pr_number=123, custom_extension="yes")

    manifest_path = tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["stalled_at_step"] == "7"
    assert data["pr_number"] == 123
    assert data["custom_extension"] == "yes"
    assert updated.reserved["stalled_at_step"] == "7"
    assert updated.reserved["pr_number"] == 123
    assert updated.extra == {"custom_extension": "yes"}


def test_manifest_v2_registry_keeps_parse_and_emit_filters_distinct() -> None:
    original: dict[str, Any] = {
        "schema_version": 2,
        "status": "partial",
        "skill": "implement",
        "run_id": "run-1",
        "steps_ran": {},
        "started_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "stalled_at_step": "old",
    }

    manifest = run_logs.Manifest.from_json(original)
    assert manifest.extra is None
    promoted = run_logs.Manifest(
        status=manifest.status,
        version=manifest.version,
        run_id=manifest.run_id,
        steps_ran=manifest.steps_ran,
        created_at=manifest.created_at,
        updated_at=manifest.updated_at,
        extra={"stalled_at_step": "new"},
        reserved={},
    ).to_json(existing=original)

    assert promoted["stalled_at_step"] == "new"


def test_synthesize_v2_main_model_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_CODE_MODEL", raising=False)
    monkeypatch.setenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    data = run_logs.Manifest.synthesize_v2(skill="implement", run_id="r").to_json(existing=None)
    assert data["model_roster"]["main"] == "claude-sonnet-4-6"


def test_synthesize_v2_main_model_from_transcript(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_CODE_MODEL", raising=False)
    monkeypatch.delenv("CLAUDE_MODEL", raising=False)
    monkeypatch.setattr(run_logs.tokens, "read_main_model", lambda: "claude-opus-4-8")
    data = run_logs.Manifest.synthesize_v2(skill="design", run_id="r").to_json(existing=None)
    assert data["model_roster"]["main"] == "claude-opus-4-8"


def test_synthesize_v2_main_model_unknown_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_CODE_MODEL", raising=False)
    monkeypatch.delenv("CLAUDE_MODEL", raising=False)
    monkeypatch.setattr(run_logs.tokens, "read_main_model", lambda: "")
    data = run_logs.Manifest.synthesize_v2(skill="implement", run_id="r").to_json(existing=None)
    assert data["model_roster"]["main"] == "unknown"
