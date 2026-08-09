# pyright: reportPrivateUsage=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportUnknownVariableType=false
# pylint: disable=no-member
"""Tests for finalize.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from larch.state import finalize
from larch.errors import ShipError
from larch.core.proc import CommandResult, Runner
from larch.core.run_context import RunContext

from test_support import RecordingRunner, make_run_context

if TYPE_CHECKING:
    from larch.core.run_context import RunContext


def _ctx(tmp_path: Path, **kwargs: object) -> RunContext:
    base = make_run_context(
        run_id="run-abc",
        tmpdir=str(tmp_path),
        manifest_path=str(tmp_path / "manifest.json"),
        tool_label="codex",
        pr_number=7,
        pr_title="Implement thing",
        issue_number="1",
    )
    return base.with_(**kwargs)


def _write_partial_manifest(tmp_path: Path) -> Path:
    path = tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(
        '{"schema_version":2,"status":"partial","run_id":"run-abc","steps_ran":{}}\n',
        encoding="utf-8",
    )
    return path


def test_title_matches_exact_title() -> None:
    assert finalize._title_matches(actual="Implement thing", expected="Implement thing", pr_number=7)


def test_title_matches_expected_numbered_title() -> None:
    assert finalize._title_matches(actual="Implement thing (#7)", expected="Implement thing", pr_number=7)


def test_title_matches_squash_merge_prefix() -> None:
    assert finalize._title_matches(actual="Implement thing (#7) follow-up", expected="Implement thing", pr_number=7)


def test_title_matches_postmerge_mid_string_suffix() -> None:
    assert finalize._title_matches(actual="Other title (#7) follow-up", expected="Implement thing", pr_number=7)


def test_title_matches_verify_main_plain_prefix() -> None:
    assert finalize._title_matches(
        actual="Feature follow-up",
        expected="Feature",
        allow_plain_prefix=True,
        suffix_match="endswith",
    )


def test_title_matches_verify_main_rejects_mid_string_suffix() -> None:
    assert not finalize._title_matches(
        actual="Other title (#7) follow-up",
        expected="Different title (#7)",
        allow_plain_prefix=True,
        suffix_match="endswith",
    )


def test_title_matches_verify_main_suffix_at_end() -> None:
    assert finalize._title_matches(
        actual="Other title (#7)",
        expected="Different title (#7)",
        allow_plain_prefix=True,
        suffix_match="endswith",
    )


def test_title_matches_avoids_double_number_suffix() -> None:
    assert finalize._title_matches(actual="Title (#7)", expected="Title (#7)", pr_number=7)


def test_title_matches_numbered_expected_rejects_stripped_prefix() -> None:
    assert not finalize._title_matches(
        actual="Title follow-up",
        expected="Title (#7)",
        allow_plain_prefix=True,
        suffix_match="endswith",
    )


def test_title_matches_empty_expected_rejected() -> None:
    assert not finalize._title_matches(actual="Anything", expected="", pr_number=7)


@pytest.mark.parametrize(
    "payload",
    ["", "{}", '{"title":"","state":"OPEN"}', '{"title":null,"state":"OPEN"}', "[]"],
)
def test_rename_issue_fails_without_a_valid_issue_title(tmp_path: Path, payload: str) -> None:
    runner = RecordingRunner(
        responses=[CommandResult(("gh", "issue", "view"), 0, payload, "", 0.01)],
    )

    status = finalize._rename_issue(runner=runner, ctx=_ctx(tmp_path), state="done", cwd=str(tmp_path))

    assert status == "failed"
    assert not any(call[1:3] == ["issue", "edit"] for call in runner.calls)


def test_postmerge_skips_draft_without_done_manifest(tmp_path: Path) -> None:
    runner = RecordingRunner()
    ctx = _ctx(tmp_path, draft=True)
    manifest_path = _write_partial_manifest(tmp_path)
    result = finalize.postmerge(runner=runner, ctx=ctx, cwd=str(tmp_path))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert result.local_cleanup_status == "skipped-draft"
    assert manifest["status"] == "partial"
    assert not any(call[:2] == ["git", "commit"] for call in runner.calls)


def test_postmerge_verifies_main_title(tmp_path: Path) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "checkout", "main"), 0, "", "", 0.01),
            CommandResult(("git", "fetch", "origin", "main", "--quiet"), 0, "", "", 0.01),
            CommandResult(("git", "pull", "--ff-only", "origin", "main"), 0, "", "", 0.01),
            CommandResult(("git", "check-ref-format", "--branch", "feat"), 0, "", "", 0.01),
            CommandResult(("git", "show-ref", "--verify", "--quiet", "refs/heads/feat"), 0, "", "", 0.01),
            CommandResult(("git", "branch", "-D", "--", "feat"), 0, "", "", 0.01),
            CommandResult(("git", "log", "-1", "--format=%s", "HEAD"), 0, "Implement thing (#7)\n", "", 0.01),
        ],
    )
    result = finalize.postmerge(runner=runner, ctx=_ctx(tmp_path), cwd=str(tmp_path))
    assert result.local_cleanup_status == "success"
    assert result.verify_main_status == "verified"
    assert result.branch_deleted is True


def test_postmerge_stalls_when_local_branch_delete_fails(tmp_path: Path) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "checkout", "main"), 0, "", "", 0.01),
            CommandResult(("git", "fetch", "origin", "main", "--quiet"), 0, "", "", 0.01),
            CommandResult(("git", "pull", "--ff-only", "origin", "main"), 0, "", "", 0.01),
            CommandResult(("git", "check-ref-format", "--branch", "feat"), 0, "", "", 0.01),
            CommandResult(("git", "show-ref", "--verify", "--quiet", "refs/heads/feat"), 0, "", "", 0.01),
            CommandResult(("git", "branch", "-D", "--", "feat"), 1, "", "busy", 0.01),
        ],
    )
    result = finalize.postmerge(runner=runner, ctx=_ctx(tmp_path), cwd=str(tmp_path))
    assert result.outcome is finalize.Outcome.STALLED
    assert result.status == "local-cleanup-failed"
    assert result.local_cleanup_status == "partial"
    assert result.branch_deleted is False


def test_teardown_stall_preserves_tmpdir_without_recreating_log_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    monkeypatch.setattr(finalize.rust_runtime, "progress_deactivate", lambda *_args, **_kwargs: True)
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "issue", "view"), 0, '{"title":"Existing title","state":"OPEN"}\n', "", 0.01),
            CommandResult(("gh", "issue", "edit"), 0, "", "", 0.01),
            CommandResult(("gh", "issue", "view"), 0, '{"url":"https://github.com/o/r/issues/1"}\n', "", 0.01),
            CommandResult(("git", "status"), 0, " M file\n", "", 0.01),
            CommandResult(("git", "stash"), 0, "", "", 0.01),
            CommandResult(("git", "stash", "list"), 0, "stash@{0} larch-stalled-1-12\n", "", 0.01),
            CommandResult(("git", "rev-parse", "--git-dir"), 0, ".git\n", "", 0.01),
        ],
    )
    result = finalize.teardown(
        runner=runner,
        ctx=_ctx(tmp_path, stall_tracking=True, stall_step="12", no_logs_commit=True),
        cwd=str(tmp_path),
    )
    assert result.status == "stalled-preserved"
    assert tmp_path.exists()
    assert (git_dir / "larch-stalled-run.txt").is_file()
    assert not (tmp_path / "larch-logs").exists()


def test_teardown_does_not_create_run_log_staging(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(finalize, "_cleanup_target_ok", lambda **_kwargs: False)
    monkeypatch.setattr(finalize.bgjob_registry, "has_live_entry", lambda **_kwargs: False)
    monkeypatch.setattr(finalize.rust_runtime, "progress_deactivate", lambda *_args, **_kwargs: True)

    result = finalize.teardown(
        runner=RecordingRunner(),
        ctx=_ctx(tmp_path, done_rename_applied=True, no_logs_commit=True, repo_unavailable=True),
        cwd=str(tmp_path),
    )

    assert result.status == "cleanup-skipped"
    assert not (tmp_path / "larch-logs").exists()


def test_postbump_clears_unknown_legacy_checkpoint(tmp_path: Path) -> None:
    checkpoint = tmp_path / ".postbump-phase"
    _ = checkpoint.write_text("not-a-valid-checkpoint", encoding="utf-8")
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "rev-parse", "--show-toplevel"), 0, f"{tmp_path}\n", "", 0.01),
            CommandResult(("git", "symbolic-ref", "--short", "HEAD"), 0, "feat\n", "", 0.01),
            CommandResult(("git", "fetch", "origin", "main", "--quiet"), 0, "", "", 0.01),
            CommandResult(("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"), 0, "", "", 0.01),
            CommandResult(("git", "ls-remote", "--exit-code", "--heads", "origin", "feat"), 2, "", "", 0.01),
        ],
    )
    result = finalize.postbump(runner=runner, ctx=_ctx(tmp_path), cwd=str(tmp_path))
    assert result.status == "ok"
    assert not checkpoint.exists()


def test_postbump_preflight_falls_back_to_target_branch_when_symbolic_ref_empty(tmp_path: Path) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "rev-parse", "--show-toplevel"), 0, f"{tmp_path}\n", "", 0.01),
            CommandResult(("git", "symbolic-ref", "--short", "HEAD"), 0, "\n", "", 0.01),
        ],
    )
    result = finalize.postbump_preflight(runner=runner, ctx=_ctx(tmp_path), cwd=str(tmp_path))
    assert result.ok is True
    assert result.branch == "feat"


def test_postbump_exception_uses_bash_status_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail_rebase(*_a: object, **_k: object) -> finalize.RebaseNoPushResult:
        raise ShipError("boom")

    monkeypatch.setattr(finalize, "_rebase_no_push", fail_rebase)
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "rev-parse", "--show-toplevel"), 0, f"{tmp_path}\n", "", 0.01),
            CommandResult(("git", "symbolic-ref", "--short", "HEAD"), 0, "feat\n", "", 0.01),
        ],
    )
    result = finalize.postbump(runner=runner, ctx=_ctx(tmp_path), cwd=str(tmp_path))
    assert result.status == "rebase-failed"


def test_rebase_no_push_aborts_and_reports_conflict_files_on_stall(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    rebase_calls: list[str] = []

    def fake_retry_fetch(**_kwargs: object) -> bool:
        return True

    def fake_is_ancestor(*_args: object, **_kwargs: object) -> bool:
        return False

    def fake_rebase(_runner: object, onto: str, **_kwargs: object) -> CommandResult:
        rebase_calls.append(onto)
        return CommandResult(("git", "rebase", onto), 0 if onto == "--abort" else 1, "", "", 0.01)

    def fake_unmerged(*_args: object, **_kwargs: object) -> list[str]:
        return ["docs/some-guide.md"]

    def fake_in_progress(*_args: object, **_kwargs: object) -> bool:
        return True

    monkeypatch.setattr(finalize, "_retry_fetch", fake_retry_fetch)
    monkeypatch.setattr(finalize.git, "is_ancestor", fake_is_ancestor)
    monkeypatch.setattr(finalize.git, "rebase", fake_rebase)
    monkeypatch.setattr(finalize.git, "try_unmerged_paths", fake_unmerged)
    monkeypatch.setattr(finalize.git, "rebase_in_progress", fake_in_progress)

    result = finalize._rebase_no_push(RecordingRunner(), base_remote="origin", cwd=str(tmp_path))
    assert result.status == "failed"
    assert result.conflict_files == ("docs/some-guide.md",)
    assert rebase_calls == ["origin/main", "--abort"]


def test_postbump_surfaces_conflict_files_on_rebase_failed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def stub_rebase(*_a: object, **_k: object) -> finalize.RebaseNoPushResult:
        return finalize.RebaseNoPushResult(
            "failed",
            conflict_files=("python/skill-closure-baseline.json",),
        )

    monkeypatch.setattr(finalize, "_rebase_no_push", stub_rebase)
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "rev-parse", "--show-toplevel"), 0, f"{tmp_path}\n", "", 0.01),
            CommandResult(("git", "symbolic-ref", "--short", "HEAD"), 0, "feat\n", "", 0.01),
        ],
    )
    result = finalize.postbump(runner=runner, ctx=_ctx(tmp_path), cwd=str(tmp_path))
    assert result.status == "rebase-failed"
    assert result.conflict_files == "python/skill-closure-baseline.json"
    assert "python/skill-closure-baseline.json" in result.detail


def test_postbump_rejects_oversized_checkpoint(tmp_path: Path) -> None:
    checkpoint = tmp_path / ".postbump-phase"
    _ = checkpoint.write_bytes(b"x" * 65)
    result = finalize.postbump(runner=RecordingRunner(), ctx=_ctx(tmp_path), cwd=str(tmp_path))
    assert result.status == "postbump-state-corrupt"


def test_postmerge_skips_when_pr_not_merged(tmp_path: Path) -> None:
    result = finalize.postmerge(
        runner=RecordingRunner(),
        ctx=_ctx(tmp_path, final_bail_reason="blocked"),
        cwd=str(tmp_path),
    )
    assert result.local_cleanup_status == "skipped-bail"
    assert result.verify_main_status == "skipped"


def test_local_cleanup_partial_on_pull_failure(tmp_path: Path) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "checkout", "main"), 0, "", "", 0.01),
            CommandResult(("git", "fetch", "origin", "main", "--quiet"), 0, "", "", 0.01),
            CommandResult(("git", "pull", "--ff-only", "origin", "main"), 1, "", "error", 0.01),
            CommandResult(("git", "rev-list", "--count", "origin/main..HEAD"), 0, "2\n", "", 0.01),
        ],
    )
    result = finalize.postmerge(runner=runner, ctx=_ctx(tmp_path), cwd=str(tmp_path))
    assert result.local_cleanup_status == "partial"


def test_local_cleanup_does_not_reset_on_empty_orphan_evidence(tmp_path: Path) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "checkout", "main"), 0, "", "", 0.01),
            CommandResult(("git", "fetch", "origin", "main", "--quiet"), 0, "", "", 0.01),
            CommandResult(("git", "pull", "--ff-only", "origin", "main"), 0, "", "", 0.01),
            CommandResult(("git", "check-ref-format", "--branch", "feat"), 0, "", "", 0.01),
            CommandResult(("git", "show-ref", "--verify", "--quiet", "refs/heads/feat"), 0, "", "", 0.01),
            CommandResult(("git", "branch", "-D", "--", "feat"), 0, "", "", 0.01),
            CommandResult(("git", "log", "-1", "--format=%s", "HEAD"), 0, "Implement thing (#7)\n", "", 0.01),
        ],
    )
    result = finalize.postmerge(runner=runner, ctx=_ctx(tmp_path), cwd=str(tmp_path))
    assert result.local_cleanup_status == "success"
    assert not any(call[:3] == ["git", "reset", "--hard"] for call in runner.calls)


def test_write_finalize_state_contains_teardown_keys(tmp_path: Path) -> None:
    target = tmp_path / "finalize-state.sh"
    finalize.write_finalize_state(ctx=_ctx(tmp_path, pr_closed=True), path=target)
    text = target.read_text(encoding="utf-8")
    assert "PR_CLOSED=true\n" in text
    assert "NO_LOGS_COMMIT=false\n" in text


def test_implement_finalize_teardown_emits_issue_url_and_subcommand(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state = tmp_path / "finalize-state.sh"
    finalize.write_finalize_state(
        ctx=_ctx(tmp_path, issue_number="12", repo="o/r", repo_unavailable=False, no_logs_commit=True),
        path=state,
    )
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))

    def fake_issue_info(runner: object, *, issue: str, field: str, repo: str | None) -> str:
        _ = (runner, issue, field, repo)
        return "https://github.com/o/r/issues/12"

    def fake_kill_session_background_processes(*, runner: object, ctx: RunContext) -> bool:
        _ = (runner, ctx)
        return False

    monkeypatch.setattr(finalize.rust_runtime, "issue_info", fake_issue_info)
    monkeypatch.setattr(finalize, "kill_session_background_processes", fake_kill_session_background_processes)
    rc = finalize.implement_finalize_teardown_main([
        "--state-file", str(state),
        "--implement-tmpdir", str(tmp_path),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ISSUE_URL=https://github.com/o/r/issues/12" in out
    assert "FINALIZE_SUBCOMMAND=teardown" in out


def test_cache_sessions_root_honors_absolute_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    assert finalize.cache_sessions_root() == tmp_path / "xdg" / "larch" / "sessions"


def test_cache_sessions_root_ignores_empty_or_relative_xdg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", "relative")
    assert finalize.cache_sessions_root() == Path.home() / ".cache" / "larch" / "sessions"
    monkeypatch.setenv("XDG_CACHE_HOME", "")
    assert finalize.cache_sessions_root() == Path.home() / ".cache" / "larch" / "sessions"


def test_kill_session_background_processes_returns_false_without_tmpdir(tmp_path: Path) -> None:
    runner = RecordingRunner(strict=True)

    assert finalize.kill_session_background_processes(runner=runner, ctx=_ctx(tmp_path, tmpdir="")) is False
    assert not runner.calls


def test_kill_session_background_processes_returns_false_when_no_processes_match(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(finalize.os, "getpid", lambda: 200)
    monkeypatch.setattr(finalize.os, "getppid", lambda: 100)
    runner = RecordingRunner(
        strict=True,
        responses=[
            CommandResult(("ps", "-o", "ppid=", "-p", "200"), 0, "100\n", "", 0.01),
            CommandResult(("ps", "-o", "ppid=", "-p", "100"), 0, "50\n", "", 0.01),
            CommandResult(("ps", "-o", "ppid=", "-p", "50"), 0, "1\n", "", 0.01),
            CommandResult(("sh", "-c", "printf '%s %s' $$ ${PPID:-}"), 0, "300 100", "", 0.01),
            CommandResult(("ps", "-o", "ppid=", "-p", "300"), 0, "\n", "", 0.01),
            CommandResult(("sh", "-c", "process-list"), 0, "", "", 0.01),
        ],
    )

    assert finalize.kill_session_background_processes(runner=runner, ctx=_ctx(tmp_path)) is False

    assert not any(call[:2] == ["kill", "-TERM"] for call in runner.calls)


def test_kill_session_background_processes_tolerates_tmpdir_resolve_oserror(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(finalize.os, "getpid", lambda: 200)
    monkeypatch.setattr(finalize.os, "getppid", lambda: 100)

    class FailingPath:
        def __init__(self, _value: str) -> None:
            pass

        def resolve(self, *, strict: bool = False) -> object:
            _ = strict
            raise OSError("resolve failed")

    monkeypatch.setattr(finalize, "Path", FailingPath)
    runner = RecordingRunner(
        strict=True,
        responses=[
            CommandResult(("ps", "-o", "ppid=", "-p", "200"), 0, "100\n", "", 0.01),
            CommandResult(("ps", "-o", "ppid=", "-p", "100"), 0, "50\n", "", 0.01),
            CommandResult(("ps", "-o", "ppid=", "-p", "50"), 0, "1\n", "", 0.01),
            CommandResult(("sh", "-c", "printf '%s %s' $$ ${PPID:-}"), 0, "300 100", "", 0.01),
            CommandResult(("ps", "-o", "ppid=", "-p", "300"), 0, "\n", "", 0.01),
            CommandResult(("sh", "-c", "process-list"), 0, "999\n", "", 0.01),
            CommandResult(("kill", "-TERM", "999"), 0, "", "", 0.01),
        ],
    )

    assert finalize.kill_session_background_processes(runner=runner, ctx=_ctx(tmp_path)) is True

    kill_calls = [call for call in runner.calls if call[:2] == ["kill", "-TERM"]]
    assert kill_calls == [["kill", "-TERM", "999"]]


def test_kill_session_background_processes_skips_live_python_ancestors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(finalize.os, "getpid", lambda: 200)
    monkeypatch.setattr(finalize.os, "getppid", lambda: 100)
    runner = RecordingRunner(
        strict=True,
        responses=[
            CommandResult(("ps", "-o", "ppid=", "-p", "200"), 0, "100\n", "", 0.01),
            CommandResult(("ps", "-o", "ppid=", "-p", "100"), 0, "50\n", "", 0.01),
            CommandResult(("ps", "-o", "ppid=", "-p", "50"), 0, "1\n", "", 0.01),
            CommandResult(("sh", "-c", "printf '%s %s' $$ ${PPID:-}"), 0, "300 100", "", 0.01),
            CommandResult(("ps", "-o", "ppid=", "-p", "300"), 0, "\n", "", 0.01),
            CommandResult(
                ("sh", "-c", "process-list"),
                0,
                "50\n999\n",
                "",
                0.01,
            ),
            CommandResult(("kill", "-TERM", "999"), 0, "", "", 0.01),
        ],
    )

    assert finalize.kill_session_background_processes(runner=runner, ctx=_ctx(tmp_path)) is True

    assert runner.calls[:5] == [
        ["ps", "-o", "ppid=", "-p", "200"],
        ["ps", "-o", "ppid=", "-p", "100"],
        ["ps", "-o", "ppid=", "-p", "50"],
        ["sh", "-c", "printf '%s %s' $$ ${PPID:-}"],
        ["ps", "-o", "ppid=", "-p", "300"],
    ]
    log_text = (tmp_path / finalize.config.FINALIZE_KILL_LOG_FILE).read_text(encoding="utf-8")
    assert '"pid": 999' in log_text
    assert '"signal": "SIGTERM"' in log_text
    kill_calls = [call for call in runner.calls if call[:2] == ["kill", "-TERM"]]
    assert kill_calls == [["kill", "-TERM", "999"]]
    assert ["kill", "-TERM", "50"] not in runner.calls









def test_write_finalize_state_merged_preserves_custom_keys(tmp_path: Path) -> None:
    target = tmp_path / "finalize-state.sh"
    finalize.write_finalize_state_merged(path=target, data={"CUSTOM_PIN": "keep", "STALL_TRACKING": "true"})
    data = finalize.read_finalize_state(target)
    assert data["CUSTOM_PIN"] == "keep"
    assert data["STALL_TRACKING"] == "true"


def test_write_finalize_state_merged_bare_values(tmp_path: Path) -> None:
    target = tmp_path / "finalize-state.sh"
    finalize.write_finalize_state_merged(
        path=target,
        data={"PR_TITLE": "Implement feature $(echo unsafe) 'quoted'"},
    )
    text = target.read_text(encoding="utf-8")
    assert text == "PR_TITLE=Implement feature $(echo unsafe) 'quoted'\n"
    assert finalize.read_finalize_state(target)["PR_TITLE"] == "Implement feature $(echo unsafe) 'quoted'"


def test_write_finalize_state_bare_values(tmp_path: Path) -> None:
    target = tmp_path / "finalize-state.sh"
    finalize.write_finalize_state(ctx=_ctx(tmp_path, pr_title="Implement feature $(echo unsafe)"), path=target)
    text = target.read_text(encoding="utf-8")
    assert "PR_TITLE=Implement feature $(echo unsafe)\n" in text
    assert finalize.read_finalize_state(target)["PR_TITLE"] == "Implement feature $(echo unsafe)"


def test_write_finalize_state_merged_rejects_newline_values(tmp_path: Path) -> None:
    target = tmp_path / "finalize-state.sh"
    with pytest.raises(Exception, match="newline"):
        finalize.write_finalize_state_merged(path=target, data={"BAD": "x\ny"})
    with pytest.raises(Exception, match="newline"):
        finalize.write_finalize_state_merged(path=target, data={"BAD": "x\ry"})


def test_cleanup_main_removes_implement_tmpdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    _ = monkeypatch.setattr(finalize, "_cleanup_target_ok", lambda **_kw: True)  # type: ignore[arg-type]
    rc = finalize.cleanup_main(["--implement-tmpdir", str(tmp_path)])
    assert rc == 0
    assert not tmp_path.exists()
    assert "CLEANED=true" in capsys.readouterr().out


def test_implement_finalize_rejects_unknown_arg(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = tmp_path / "finalize-state.sh"
    finalize.write_finalize_state(ctx=_ctx(tmp_path, no_logs_commit=True), path=state)
    rc = finalize.implement_finalize_teardown_main([
        "--state-file", str(state),
        "--implement-tmpdir", str(tmp_path),
        "--bogus",
    ])
    assert rc == 2
    assert "unrecognized arguments" in capsys.readouterr().err


def test_implement_finalize_requires_phase_specific_bail_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = tmp_path / "finalize-state.sh"
    finalize.write_finalize_state(ctx=_ctx(tmp_path), path=state)
    rc = finalize.implement_finalize_postmerge_main(["--state-file", str(state)])
    assert rc == 2
    assert "final-bail-reason-file" in capsys.readouterr().err


def test_implement_finalize_rejects_missing_required_state_key(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = tmp_path / "finalize-state.sh"
    finalize.write_finalize_state(ctx=_ctx(tmp_path), path=state)
    text = state.read_text(encoding="utf-8").replace("MERGE=true\n", "")
    state.write_text(text, encoding="utf-8")
    rc = finalize.implement_finalize_teardown_main([
        "--state-file", str(state),
        "--implement-tmpdir", str(tmp_path),
    ])
    assert rc == 2
    assert "state-file missing required key: MERGE" in capsys.readouterr().err


def test_implement_finalize_rejects_malformed_bool(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = tmp_path / "finalize-state.sh"
    finalize.write_finalize_state(ctx=_ctx(tmp_path), path=state)
    state.write_text(state.read_text(encoding="utf-8").replace("DRAFT=false", "DRAFT=maybe"), encoding="utf-8")
    rc = finalize.implement_finalize_teardown_main([
        "--state-file", str(state),
        "--implement-tmpdir", str(tmp_path),
    ])
    assert rc == 2
    assert "state-file key DRAFT must be true or false" in capsys.readouterr().err


def test_implement_finalize_rejects_duplicate_state_key(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = tmp_path / "finalize-state.sh"
    finalize.write_finalize_state(ctx=_ctx(tmp_path), path=state)
    state.write_text(state.read_text(encoding="utf-8") + "DRAFT=true\n", encoding="utf-8")

    rc = finalize.implement_finalize_teardown_main([
        "--state-file", str(state),
        "--implement-tmpdir", str(tmp_path),
    ])

    assert rc == 2
    assert "duplicate state-file key: DRAFT" in capsys.readouterr().err


def test_implement_finalize_postbump_rejects_invalid_new_version(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state = tmp_path / "finalize-state.sh"
    state.write_text(
        "BRANCH_NAME=feat\n"
        "ISSUE_NUMBER=1\n"
        "PR_TITLE=Implement thing\n"
        "REPO=o/r\n"
        "REPO_UNAVAILABLE=false\n"
        "FORKED_TARGET=false\n"
        "BUMP_TYPE=PATCH\n"
        "NEW_VERSION=not-a-version\n",
        encoding="utf-8",
    )
    rc = finalize.implement_finalize_postbump_main([
        "--state-file", str(state),
        "--implement-tmpdir", str(tmp_path),
    ])
    assert rc == 2
    assert "NEW_VERSION must be semver" in capsys.readouterr().err


def _cleanup_ctx(**overrides: object) -> RunContext:
    return make_run_context(
        expected_session_id="session-ok",
        expected_tmpdir_basename_prefix="claude-implement-larch5-",
        **overrides,
    )


def test_cleanup_target_ok_happy_path(tmp_path: Path) -> None:
    target = tmp_path / "claude-implement-larch5-happy"
    target.mkdir()
    _ = (target / "session-id").write_text("session-ok\n", encoding="utf-8")
    assert finalize._cleanup_target_ok(ctx=_cleanup_ctx(), tmpdir=target, cwd=str(tmp_path))


def test_cleanup_target_ok_prefix_mismatch_session_match(tmp_path: Path) -> None:
    target = tmp_path / "claude-implement-foreign"
    target.mkdir()
    _ = (target / "session-id").write_text("session-ok\n", encoding="utf-8")
    assert finalize._cleanup_target_ok(ctx=_cleanup_ctx(), tmpdir=target, cwd=str(tmp_path))


def test_cleanup_target_ok_session_id_mismatch(tmp_path: Path) -> None:
    target = tmp_path / "claude-implement-larch5-sessionbad"
    target.mkdir()
    _ = (target / "session-id").write_text("wrong-session-id\n", encoding="utf-8")
    assert not finalize._cleanup_target_ok(ctx=_cleanup_ctx(), tmpdir=target, cwd=str(tmp_path))


def test_cleanup_target_ok_missing_session_id(tmp_path: Path) -> None:
    target = tmp_path / "claude-implement-larch5-missingid"
    target.mkdir()
    assert not finalize._cleanup_target_ok(ctx=_cleanup_ctx(), tmpdir=target, cwd=str(tmp_path))


def test_cleanup_target_ok_legacy_basename_only(tmp_path: Path) -> None:
    target = tmp_path / "claude-implement-larch5-legacy"
    target.mkdir()
    ctx = make_run_context(
        expected_session_id="",
        expected_tmpdir_basename_prefix="claude-implement-larch5-",
    )
    assert finalize._cleanup_target_ok(ctx=ctx, tmpdir=target, cwd=str(tmp_path))


def test_implement_finalize_teardown_rejects_disallowed_state_file_root(
    capsys: pytest.CaptureFixture[str],
) -> None:
    state = Path(__file__).resolve().parent / "disallowed-finalize-state.sh"
    state.write_text("BRANCH_NAME=feat\n", encoding="utf-8")
    try:
        rc = finalize.implement_finalize_teardown_main([
            "--state-file", str(state),
            "--implement-tmpdir", "/tmp/claude-implement-larch5-test",
        ])
        assert rc == 2
        assert "state-file must be under" in capsys.readouterr().err
    finally:
        state.unlink(missing_ok=True)


def test_implement_finalize_teardown_rejects_disallowed_implement_tmpdir(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state = tmp_path / "finalize-state.sh"
    finalize.write_finalize_state(ctx=_ctx(tmp_path), path=state)
    repo_root = Path(__file__).resolve().parents[3]
    rc = finalize.implement_finalize_teardown_main([
        "--state-file", str(state),
        "--implement-tmpdir", str(repo_root),
    ])
    assert rc == 2
    assert "implement-tmpdir must be under" in capsys.readouterr().err


def test_implement_finalize_teardown_rejects_state_file_outside_tmpdir(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session_dir = tmp_path / "session"
    other_dir = tmp_path / "other"
    session_dir.mkdir()
    other_dir.mkdir()
    state = other_dir / "finalize-state.sh"
    finalize.write_finalize_state(ctx=_ctx(other_dir), path=state)
    rc = finalize.implement_finalize_teardown_main([
        "--state-file", str(state),
        "--implement-tmpdir", str(session_dir),
    ])
    assert rc == 2
    assert "state-file must live under --implement-tmpdir" in capsys.readouterr().err


def test_implement_finalize_postbump_rejects_state_file_outside_tmpdir(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session_dir = tmp_path / "session"
    other_dir = tmp_path / "other"
    session_dir.mkdir()
    other_dir.mkdir()
    state = other_dir / "finalize-state.sh"
    state.write_text(
        "BRANCH_NAME=feat\n"
        "ISSUE_NUMBER=1\n"
        "PR_TITLE=Implement thing\n"
        "REPO=o/r\n"
        "REPO_UNAVAILABLE=false\n"
        "FORKED_TARGET=false\n"
        "BUMP_TYPE=NONE\n"
        "NEW_VERSION=\n",
        encoding="utf-8",
    )
    rc = finalize.implement_finalize_postbump_main([
        "--state-file", str(state),
        "--implement-tmpdir", str(session_dir),
    ])
    assert rc == 2
    assert "state-file must live under --implement-tmpdir" in capsys.readouterr().err


def test_implement_finalize_accepts_cache_root_state_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    session_dir = finalize.cache_sessions_root() / "claude-implement-repo-abc"
    session_dir.mkdir(parents=True)
    state = session_dir / "finalize-state.sh"
    finalize.write_finalize_state(ctx=_ctx(session_dir, no_logs_commit=True), path=state)

    def fake_kill_session_background_processes(*, runner: object, ctx: RunContext) -> bool:
        _ = (runner, ctx)
        return False

    monkeypatch.setattr(finalize, "kill_session_background_processes", fake_kill_session_background_processes)
    rc = finalize.implement_finalize_teardown_main([
        "--state-file", str(state),
        "--implement-tmpdir", str(session_dir),
    ])
    assert rc == 0
    assert "FINALIZE_SUBCOMMAND=teardown" in capsys.readouterr().out


def test_teardown_deactivates_run_before_tmpdir_removal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Teardown calls the Rust deactivation seam with the effective run ID."""
    runner = RecordingRunner()
    ctx = _ctx(tmp_path, pr_number=3, done_rename_applied=True)
    _ = _write_partial_manifest(tmp_path)

    deactivate_calls: list[tuple[str, str]] = []

    def fake_deactivate(
        _runner: object,
        *,
        repo_root: str,
        run_id: str,
        cwd: str | None = None,
    ) -> bool:
        _ = cwd
        deactivate_calls.append((repo_root, run_id))
        return True

    monkeypatch.setattr(finalize.rust_runtime, "progress_deactivate", fake_deactivate)

    def fake_kill(*, runner: Runner, ctx: RunContext) -> bool:  # noqa: ARG001  # pylint: disable=unused-argument
        return True

    monkeypatch.setattr(finalize, "kill_session_background_processes", fake_kill)

    result = finalize.teardown(runner=runner, ctx=ctx, cwd=str(tmp_path))
    assert result.outcome.name == "OK"
    assert len(deactivate_calls) == 1
    assert deactivate_calls[0][1] == "run-abc"


def test_teardown_uses_persisted_repo_root_outside_clone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    ctx = _ctx(tmp_path, pr_number=3, done_rename_applied=True)
    (tmp_path / "session-env.sh").write_text(f"REPO_ROOT={repo}\nLARCH_RUN_ID=run-abc\n", encoding="utf-8")
    deactivate_calls: list[tuple[str, str]] = []

    monkeypatch.setattr(finalize, "kill_session_background_processes", lambda **_kwargs: True)
    monkeypatch.setattr(finalize.bgjob_registry, "has_live_entry", lambda **_kwargs: False)

    def fake_deactivate(
        _runner: object,
        *,
        repo_root: str,
        run_id: str,
        cwd: str | None = None,
    ) -> bool:
        _ = cwd
        deactivate_calls.append((repo_root, run_id))
        return True

    monkeypatch.setattr(
        finalize.rust_runtime,
        "progress_deactivate",
        fake_deactivate,
    )

    _ = finalize.teardown(runner=RecordingRunner(), ctx=ctx, cwd=str(outside))

    assert deactivate_calls == [(str(repo.resolve()), "run-abc")]


_STALE_LIVE = "coverage artifact does not match live repository inputs"


def _stub_teardown_side_effects(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    crumbs: list[str] = []

    class _Writer:
        def emit(self, message: str, *, quiet: bool = True) -> None:  # pylint: disable=unused-argument  # test stub matches interface; quiet not exercised here
            crumbs.append(message)

    (tmp_path / "session-env.sh").write_text(
        f"REPO_ROOT={tmp_path}\nLARCH_RUN_ID=run-abc\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(finalize.logging_util, "BreadcrumbWriter", _Writer)
    monkeypatch.setattr(finalize, "kill_session_background_processes", lambda **_kwargs: True)
    monkeypatch.setattr(finalize, "_cleanup_target_ok", lambda **_kwargs: False)
    monkeypatch.setattr(finalize.bgjob_registry, "has_live_entry", lambda **_kwargs: False)
    monkeypatch.setattr(finalize.rust_runtime, "issue_info", lambda *_a, **_k: "")
    monkeypatch.setattr(finalize.rust_runtime, "progress_deactivate", lambda *_a, **_k: True)
    return crumbs


def test_teardown_stale_live_coverage_renames_done_when_not_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    crumbs = _stub_teardown_side_effects(monkeypatch, tmp_path)
    rename_calls: list[str] = []

    def boom(*_a: object, **_k: object) -> str:
        raise ShipError(_STALE_LIVE)

    monkeypatch.setattr(finalize.scope_disposition, "disposition_link_kind", boom)
    monkeypatch.setattr(
        finalize.scope_disposition,
        "load_coverage",
        lambda _tmpdir: object(),
    )
    monkeypatch.setattr(
        finalize.scope_disposition,
        "load_disposition",
        lambda _tmpdir, *, coverage=None: None,  # noqa: ARG005
    )
    monkeypatch.setattr(
        finalize,
        "_rename_issue",
        lambda **kwargs: rename_calls.append(str(kwargs["state"])) or "ok",
    )
    (tmp_path / "post-merge-sentinel").write_text("", encoding="utf-8")

    result = finalize.teardown(
        runner=RecordingRunner(),
        ctx=_ctx(tmp_path, pr_number=3, done_rename_applied=False, no_logs_commit=True),
        cwd=str(tmp_path),
    )

    assert result.outcome.name == "OK"
    assert result.rename_branch == "B"
    assert rename_calls == ["done"]
    assert any("live coverage no longer matches" in c for c in crumbs)
    assert any("validated persisted disposition" in c for c in crumbs)


def test_teardown_stale_live_coverage_skips_done_rename_for_proceed_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    crumbs = _stub_teardown_side_effects(monkeypatch, tmp_path)
    rename_calls: list[str] = []

    def boom(*_a: object, **_k: object) -> str:
        raise ShipError(_STALE_LIVE)

    class _Partial:
        disposition = "proceed-partial"

    monkeypatch.setattr(finalize.scope_disposition, "disposition_link_kind", boom)
    monkeypatch.setattr(
        finalize.scope_disposition,
        "load_coverage",
        lambda _tmpdir: object(),
    )
    monkeypatch.setattr(
        finalize.scope_disposition,
        "load_disposition",
        lambda _tmpdir, *, coverage=None: _Partial(),  # noqa: ARG005
    )
    monkeypatch.setattr(
        finalize,
        "_rename_issue",
        lambda **kwargs: rename_calls.append(str(kwargs["state"])) or "ok",
    )
    (tmp_path / "post-merge-sentinel").write_text("", encoding="utf-8")

    result = finalize.teardown(
        runner=RecordingRunner(),
        ctx=_ctx(tmp_path, pr_number=3, done_rename_applied=False, no_logs_commit=True),
        cwd=str(tmp_path),
    )

    assert result.outcome.name == "OK"
    assert result.rename_branch == "C"
    assert not rename_calls
    assert any("validated persisted disposition" in c for c in crumbs)


def test_teardown_stale_live_coverage_missing_persisted_coverage_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = _stub_teardown_side_effects(monkeypatch, tmp_path)
    rename_calls: list[str] = []

    def boom(*_a: object, **_k: object) -> str:
        raise ShipError(_STALE_LIVE)

    monkeypatch.setattr(finalize.scope_disposition, "disposition_link_kind", boom)
    monkeypatch.setattr(finalize.scope_disposition, "load_coverage", lambda _tmpdir: None)
    monkeypatch.setattr(
        finalize,
        "_rename_issue",
        lambda **kwargs: rename_calls.append(str(kwargs["state"])) or "ok",
    )
    (tmp_path / "post-merge-sentinel").write_text("", encoding="utf-8")

    with pytest.raises(ShipError, match=_STALE_LIVE):
        _ = finalize.teardown(
            runner=RecordingRunner(),
            ctx=_ctx(tmp_path, pr_number=3, done_rename_applied=False, no_logs_commit=True),
            cwd=str(tmp_path),
        )

    assert not rename_calls


def test_teardown_stale_live_coverage_before_post_merge_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = _stub_teardown_side_effects(monkeypatch, tmp_path)
    rename_calls: list[str] = []

    def boom(*_a: object, **_k: object) -> str:
        raise ShipError(_STALE_LIVE)

    monkeypatch.setattr(finalize.scope_disposition, "disposition_link_kind", boom)
    monkeypatch.setattr(
        finalize,
        "_rename_issue",
        lambda **kwargs: rename_calls.append(str(kwargs["state"])) or "ok",
    )

    with pytest.raises(ShipError, match=_STALE_LIVE):
        _ = finalize.teardown(
            runner=RecordingRunner(),
            ctx=_ctx(tmp_path, pr_number=3, done_rename_applied=False, no_logs_commit=True),
            cwd=str(tmp_path),
        )

    assert not rename_calls


def test_teardown_stale_live_coverage_invalid_persisted_disposition_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = _stub_teardown_side_effects(monkeypatch, tmp_path)
    rename_calls: list[str] = []

    def boom(*_a: object, **_k: object) -> str:
        raise ShipError(_STALE_LIVE)

    monkeypatch.setattr(finalize.scope_disposition, "disposition_link_kind", boom)
    monkeypatch.setattr(finalize.scope_disposition, "load_coverage", lambda _tmpdir: object())
    monkeypatch.setattr(
        finalize.scope_disposition,
        "load_disposition",
        lambda _tmpdir, *, coverage=None: (
            _ := coverage,  # type: ignore[reportUnknownVariableType]
            (_ for _ in ()).throw(ShipError("invalid persisted disposition")),
        )[1],
    )
    monkeypatch.setattr(
        finalize,
        "_rename_issue",
        lambda **kwargs: rename_calls.append(str(kwargs["state"])) or "ok",
    )
    (tmp_path / "post-merge-sentinel").write_text("", encoding="utf-8")

    with pytest.raises(ShipError, match="invalid persisted disposition"):
        _ = finalize.teardown(
            runner=RecordingRunner(),
            ctx=_ctx(tmp_path, pr_number=3, done_rename_applied=False, no_logs_commit=True),
            cwd=str(tmp_path),
        )

    assert not rename_calls


def test_teardown_non_mismatch_disposition_ship_error_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = _stub_teardown_side_effects(monkeypatch, tmp_path)
    rename_calls: list[str] = []

    def boom(*_a: object, **_k: object) -> str:
        raise ShipError("scope disposition has invalid disposition")

    monkeypatch.setattr(finalize.scope_disposition, "disposition_link_kind", boom)
    monkeypatch.setattr(
        finalize,
        "_rename_issue",
        lambda **kwargs: rename_calls.append(str(kwargs["state"])) or "ok",
    )

    with pytest.raises(ShipError, match="invalid disposition"):
        _ = finalize.teardown(
            runner=RecordingRunner(),
            ctx=_ctx(tmp_path, pr_number=3, done_rename_applied=False, no_logs_commit=True),
            cwd=str(tmp_path),
        )

    assert not rename_calls


def test_teardown_successful_part_of_skips_done_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = _stub_teardown_side_effects(monkeypatch, tmp_path)
    rename_calls: list[str] = []

    monkeypatch.setattr(
        finalize.scope_disposition,
        "disposition_link_kind",
        lambda *_a, **_k: "part-of",
    )
    monkeypatch.setattr(
        finalize,
        "_rename_issue",
        lambda **kwargs: rename_calls.append(str(kwargs["state"])) or "ok",
    )

    result = finalize.teardown(
        runner=RecordingRunner(),
        ctx=_ctx(tmp_path, pr_number=3, done_rename_applied=False, no_logs_commit=True),
        cwd=str(tmp_path),
    )

    assert result.outcome.name == "OK"
    assert result.rename_branch == "C"
    assert not rename_calls
