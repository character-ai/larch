# pyright: reportPrivateUsage=false
"""Tests for finalize.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import finalize
import run_logs
from errors import ShipError
from proc import CommandResult
from run_context import RunContext

from test_support import RecordingRunner


def _ctx(tmp_path: Path, **kwargs: object) -> RunContext:
    base = RunContext(
        branch="feat",
        issue="1",
        repo="o/r",
        run_id="run-abc",
        tmpdir=str(tmp_path),
        merge=True,
        draft=False,
        forked=False,
        manifest_path=str(tmp_path / "manifest.json"),
        tool_label="codex",
        no_admin_fallback=False,
        repo_unavailable=False,
        pr_number=7,
        pr_title="Implement thing",
        issue_number="1",
    )
    return base.with_(**kwargs)


def test_title_matches_exact_title() -> None:
    assert finalize._title_matches("Implement thing", "Implement thing", 7)


def test_title_matches_expected_numbered_title() -> None:
    assert finalize._title_matches("Implement thing (#7)", "Implement thing", 7)


def test_title_matches_squash_merge_prefix() -> None:
    assert finalize._title_matches("Implement thing (#7) follow-up", "Implement thing", 7)


def test_title_matches_postmerge_mid_string_suffix() -> None:
    assert finalize._title_matches("Other title (#7) follow-up", "Implement thing", 7)


def test_title_matches_verify_main_plain_prefix() -> None:
    assert finalize._title_matches(
        "Feature follow-up",
        "Feature",
        allow_plain_prefix=True,
        suffix_match="endswith",
    )


def test_title_matches_verify_main_rejects_mid_string_suffix() -> None:
    assert not finalize._title_matches(
        "Other title (#7) follow-up",
        "Different title (#7)",
        allow_plain_prefix=True,
        suffix_match="endswith",
    )


def test_title_matches_verify_main_suffix_at_end() -> None:
    assert finalize._title_matches(
        "Other title (#7)",
        "Different title (#7)",
        allow_plain_prefix=True,
        suffix_match="endswith",
    )


def test_title_matches_avoids_double_number_suffix() -> None:
    assert finalize._title_matches("Title (#7)", "Title (#7)", 7)


def test_title_matches_numbered_expected_rejects_stripped_prefix() -> None:
    assert not finalize._title_matches(
        "Title follow-up",
        "Title (#7)",
        allow_plain_prefix=True,
        suffix_match="endswith",
    )


def test_title_matches_empty_expected_rejected() -> None:
    assert not finalize._title_matches("Anything", "", 7)


def test_postmerge_skips_draft_without_done_manifest(tmp_path: Path) -> None:
    runner = RecordingRunner()
    ctx = _ctx(tmp_path, draft=True)
    _ = run_logs.init_run(ctx)
    result = finalize.postmerge(runner, ctx, cwd=str(tmp_path))
    manifest_path = tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert result.local_cleanup_status == "skipped-draft"
    assert manifest["status"] == "partial"
    assert not any(call[:2] == ["git", "commit"] for call in runner.calls)


def test_postmerge_verifies_main_title(tmp_path: Path) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "checkout", "main"), 0, "", "", 0.01),
            CommandResult(("git", "rev-parse", "origin/main"), 0, "base\n", "", 0.01),
            CommandResult(("git", "fetch", "origin", "main", "--quiet"), 0, "", "", 0.01),
            CommandResult(("git", "rev-list", "--count", "origin/main..HEAD"), 0, "0\n", "", 0.01),
            CommandResult(("git", "pull", "--ff-only", "origin", "main"), 0, "", "", 0.01),
            CommandResult(("git", "check-ref-format", "--branch", "feat"), 0, "", "", 0.01),
            CommandResult(("git", "branch", "-D", "--", "feat"), 0, "", "", 0.01),
            CommandResult(("git", "log", "-1", "--format=%s", "HEAD"), 0, "Implement thing (#7)\n", "", 0.01),
        ],
    )
    result = finalize.postmerge(runner, _ctx(tmp_path), cwd=str(tmp_path))
    assert result.local_cleanup_status == "success"
    assert result.verify_main_status == "verified"
    assert result.branch_deleted is True


def test_postmerge_exposes_branch_delete_failure(tmp_path: Path) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "checkout", "main"), 0, "", "", 0.01),
            CommandResult(("git", "rev-parse", "origin/main"), 0, "base\n", "", 0.01),
            CommandResult(("git", "fetch", "origin", "main", "--quiet"), 0, "", "", 0.01),
            CommandResult(("git", "rev-list", "--count", "origin/main..HEAD"), 0, "0\n", "", 0.01),
            CommandResult(("git", "pull", "--ff-only", "origin", "main"), 0, "", "", 0.01),
            CommandResult(("git", "check-ref-format", "--branch", "feat"), 0, "", "", 0.01),
            CommandResult(("git", "branch", "-D", "--", "feat"), 1, "", "busy", 0.01),
            CommandResult(("git", "log", "-1", "--format=%s", "HEAD"), 0, "Implement thing (#7)\n", "", 0.01),
        ],
    )
    result = finalize.postmerge(runner, _ctx(tmp_path), cwd=str(tmp_path))
    assert result.local_cleanup_status == "success"
    assert result.branch_deleted is False


def test_teardown_stall_preserves_tmpdir_and_writes_manifest(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "issue", "view"), 0, '{"title":"Existing title","state":"OPEN"}\n', "", 0.01),
            CommandResult(("gh", "issue", "edit"), 0, "", "", 0.01),
            CommandResult(("git", "status"), 0, " M file\n", "", 0.01),
            CommandResult(("git", "stash"), 0, "", "", 0.01),
            CommandResult(("git", "stash", "list"), 0, "stash@{0} larch-stalled-1-12\n", "", 0.01),
            CommandResult(("git", "rev-parse", "--git-dir"), 0, ".git\n", "", 0.01),
        ],
    )
    result = finalize.teardown(
        runner,
        _ctx(tmp_path, stall_tracking=True, stall_step="12", no_logs_commit=True),
        cwd=str(tmp_path),
    )
    assert result.status == "stalled-preserved"
    assert tmp_path.exists()
    assert (git_dir / "larch-stalled-run.txt").is_file()
    manifest = json.loads(
        (tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json").read_text(
            encoding="utf-8",
        ),
    )
    assert manifest["stalled_at_step"] == "12"


def test_teardown_log_flush_failure_does_not_skip_stash_or_sentinel(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    def fail_recovery(*_a: object, **_k: object) -> run_logs.ManifestRecovery:
        raise ShipError("lost")

    monkeypatch.setattr(run_logs, "load_or_recover_manifest_checked", fail_recovery)
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "issue", "view"), 0, '{"title":"Existing title","state":"OPEN"}\n', "", 0.01),
            CommandResult(("gh", "issue", "edit"), 0, "", "", 0.01),
            CommandResult(("git", "status"), 0, " M file\n", "", 0.01),
            CommandResult(("git", "stash"), 0, "", "", 0.01),
            CommandResult(("git", "stash", "list"), 0, "stash@{0} larch-stalled-1-12\n", "", 0.01),
            CommandResult(("git", "rev-parse", "--git-dir"), 0, ".git\n", "", 0.01),
        ],
    )
    result = finalize.teardown(
        runner,
        _ctx(tmp_path, stall_tracking=True, stall_step="12", no_logs_commit=True),
        cwd=str(tmp_path),
    )
    assert result.status == "stalled-preserved"
    assert result.sentinel_written is True


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
    result = finalize.postbump(runner, _ctx(tmp_path), cwd=str(tmp_path))
    assert result.status == "ok"
    assert not checkpoint.exists()


def test_postbump_preflight_falls_back_to_target_branch_when_symbolic_ref_empty(tmp_path: Path) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "rev-parse", "--show-toplevel"), 0, f"{tmp_path}\n", "", 0.01),
            CommandResult(("git", "symbolic-ref", "--short", "HEAD"), 0, "\n", "", 0.01),
        ],
    )
    result = finalize.postbump_preflight(runner, _ctx(tmp_path), cwd=str(tmp_path))
    assert result.ok is True
    assert result.branch == "feat"


def test_postbump_exception_uses_bash_status_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail_rebase(*_a: object, **_k: object) -> str:
        raise ShipError("boom")

    monkeypatch.setattr(finalize, "_rebase_no_push", fail_rebase)
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "rev-parse", "--show-toplevel"), 0, f"{tmp_path}\n", "", 0.01),
            CommandResult(("git", "symbolic-ref", "--short", "HEAD"), 0, "feat\n", "", 0.01),
        ],
    )
    result = finalize.postbump(runner, _ctx(tmp_path), cwd=str(tmp_path))
    assert result.status == "rebase-failed"


def test_postbump_rejects_oversized_checkpoint(tmp_path: Path) -> None:
    checkpoint = tmp_path / ".postbump-phase"
    _ = checkpoint.write_bytes(b"x" * 65)
    result = finalize.postbump(RecordingRunner(), _ctx(tmp_path), cwd=str(tmp_path))
    assert result.status == "postbump-state-corrupt"


def test_postmerge_skips_when_pr_not_merged(tmp_path: Path) -> None:
    result = finalize.postmerge(
        RecordingRunner(),
        _ctx(tmp_path, final_bail_reason="blocked"),
        cwd=str(tmp_path),
    )
    assert result.local_cleanup_status == "skipped-bail"
    assert result.verify_main_status == "skipped"


def test_local_cleanup_partial_on_pull_failure(tmp_path: Path) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "checkout", "main"), 0, "", "", 0.01),
            CommandResult(("git", "rev-parse", "origin/main"), 0, "base\n", "", 0.01),
            CommandResult(("git", "fetch", "origin", "main", "--quiet"), 0, "", "", 0.01),
            CommandResult(("git", "rev-list", "--count", "origin/main..HEAD"), 0, "2\n", "", 0.01),
            CommandResult(("git", "log", "origin/main..HEAD", "--format=%s"), 0, "other\n", "", 0.01),
            CommandResult(("git", "diff", "--name-only", "base", "HEAD"), 0, "src/a.py\n", "", 0.01),
            CommandResult(("git", "pull", "--ff-only", "origin", "main"), 1, "", "error", 0.01),
            CommandResult(("git", "rev-list", "--count", "origin/main..HEAD"), 0, "2\n", "", 0.01),
        ],
    )
    result = finalize.postmerge(runner, _ctx(tmp_path), cwd=str(tmp_path))
    assert result.local_cleanup_status == "partial"


def test_local_cleanup_does_not_reset_on_empty_orphan_evidence(tmp_path: Path) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "checkout", "main"), 0, "", "", 0.01),
            CommandResult(("git", "rev-parse", "origin/main"), 0, "base\n", "", 0.01),
            CommandResult(("git", "fetch", "origin", "main", "--quiet"), 0, "", "", 0.01),
            CommandResult(("git", "rev-list", "--count", "origin/main..HEAD"), 0, "1\n", "", 0.01),
            CommandResult(("git", "log", "origin/main..HEAD", "--format=%s"), 0, "", "", 0.01),
            CommandResult(("git", "diff", "--name-only", "base", "HEAD"), 0, "", "", 0.01),
            CommandResult(("git", "pull", "--ff-only", "origin", "main"), 0, "", "", 0.01),
            CommandResult(("git", "check-ref-format", "--branch", "feat"), 0, "", "", 0.01),
            CommandResult(("git", "branch", "-D", "--", "feat"), 0, "", "", 0.01),
            CommandResult(("git", "log", "-1", "--format=%s", "HEAD"), 0, "Implement thing (#7)\n", "", 0.01),
        ],
    )
    result = finalize.postmerge(runner, _ctx(tmp_path), cwd=str(tmp_path))
    assert result.local_cleanup_status == "success"
    assert not any(call[:3] == ["git", "reset", "--hard"] for call in runner.calls)


def test_write_finalize_state_contains_teardown_keys(tmp_path: Path) -> None:
    target = tmp_path / "finalize-state.sh"
    finalize.write_finalize_state(_ctx(tmp_path, pr_closed=True), target)
    text = target.read_text(encoding="utf-8")
    assert "PR_CLOSED=true\n" in text
    assert "NO_LOGS_COMMIT=false\n" in text


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

    assert finalize.kill_session_background_processes(runner, _ctx(tmp_path, tmpdir="")) is False
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

    assert finalize.kill_session_background_processes(runner, _ctx(tmp_path)) is False

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

    assert finalize.kill_session_background_processes(runner, _ctx(tmp_path)) is True

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

    assert finalize.kill_session_background_processes(runner, _ctx(tmp_path)) is True

    assert runner.calls[:5] == [
        ["ps", "-o", "ppid=", "-p", "200"],
        ["ps", "-o", "ppid=", "-p", "100"],
        ["ps", "-o", "ppid=", "-p", "50"],
        ["sh", "-c", "printf '%s %s' $$ ${PPID:-}"],
        ["ps", "-o", "ppid=", "-p", "300"],
    ]
    kill_calls = [call for call in runner.calls if call[:2] == ["kill", "-TERM"]]
    assert kill_calls == [["kill", "-TERM", "999"]]
    assert ["kill", "-TERM", "50"] not in runner.calls


def _no_kill(*_args: object) -> bool:
    pytest.fail("should not kill")


def test_kill_background_processes_main_rejects_missing_design_tmpdir(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(finalize, "kill_session_background_processes", _no_kill)

    rc = finalize.kill_background_processes_main([])

    assert rc == 2
    assert "ERROR=--design-tmpdir is required" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("relative/path", "absolute path"),
        ("/tmp/claude-design-bad\npath", "newline"),
        ("/tmp/claude-design-bad/../other", "'..' segments"),
    ],
)
def test_kill_background_processes_main_rejects_bad_paths(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    value: str,
    expected: str,
) -> None:
    monkeypatch.setattr(finalize, "kill_session_background_processes", _no_kill)

    rc = finalize.kill_background_processes_main(["--design-tmpdir", value])

    assert rc == 2
    assert expected in capsys.readouterr().err


def test_kill_background_processes_main_rejects_allowed_root_non_design_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    non_design = tmp_path / "x"
    non_design.mkdir()
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setattr(finalize, "kill_session_background_processes", _no_kill)

    rc = finalize.kill_background_processes_main(["--design-tmpdir", str(non_design)])

    assert rc == 2
    assert "basename must start with claude-design-" in capsys.readouterr().err


def test_kill_background_processes_main_rejects_design_path_without_marker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design_dir = tmp_path / "claude-design-no-marker"
    design_dir.mkdir()
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setattr(finalize, "kill_session_background_processes", _no_kill)

    rc = finalize.kill_background_processes_main(["--design-tmpdir", str(design_dir)])

    assert rc == 2
    assert "source-env.sh" in capsys.readouterr().err


def test_kill_background_processes_main_rejects_symlinked_design_tmpdir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    victim = tmp_path / "claude-design-victim"
    victim.mkdir()
    _ = (victim / "source-env.sh").write_text("DESIGN_TMPDIR=x\n", encoding="utf-8")
    link = tmp_path / "claude-design-link"
    link.symlink_to(victim)
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setattr(finalize, "kill_session_background_processes", _no_kill)

    rc = finalize.kill_background_processes_main(["--design-tmpdir", str(link)])

    assert rc == 2
    assert "symlink" in capsys.readouterr().err


@pytest.mark.parametrize("killed", [True, False])
def test_kill_background_processes_main_calls_killer_with_design_tmpdir_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    killed: bool,
) -> None:
    design_dir = tmp_path / "claude-design-valid"
    design_dir.mkdir()
    _ = (design_dir / "source-env.sh").write_text("DESIGN_TMPDIR=x\n", encoding="utf-8")
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    seen: dict[str, str] = {}

    def fake_kill(_runner: object, ctx: RunContext) -> bool:
        seen["tmpdir"] = ctx.tmpdir
        return killed

    monkeypatch.setattr(finalize, "kill_session_background_processes", fake_kill)

    rc = finalize.kill_background_processes_main(["--design-tmpdir", str(design_dir)])

    assert rc == 0
    assert seen["tmpdir"] == str(design_dir.resolve())
    assert f"KILLED={str(killed).lower()}" in capsys.readouterr().out


def test_write_finalize_state_merged_preserves_custom_keys(tmp_path: Path) -> None:
    target = tmp_path / "finalize-state.sh"
    finalize.write_finalize_state_merged(target, {"CUSTOM_PIN": "keep", "STALL_TRACKING": "true"})
    data = finalize.read_finalize_state(target)
    assert data["CUSTOM_PIN"] == "keep"
    assert data["STALL_TRACKING"] == "true"


def test_write_finalize_state_merged_bare_values(tmp_path: Path) -> None:
    target = tmp_path / "finalize-state.sh"
    finalize.write_finalize_state_merged(
        target,
        {"PR_TITLE": "Implement feature $(echo unsafe) 'quoted'"},
    )
    text = target.read_text(encoding="utf-8")
    assert text == "PR_TITLE=Implement feature $(echo unsafe) 'quoted'\n"
    assert finalize.read_finalize_state(target)["PR_TITLE"] == "Implement feature $(echo unsafe) 'quoted'"


def test_write_finalize_state_bare_values(tmp_path: Path) -> None:
    target = tmp_path / "finalize-state.sh"
    finalize.write_finalize_state(_ctx(tmp_path, pr_title="Implement feature $(echo unsafe)"), target)
    text = target.read_text(encoding="utf-8")
    assert "PR_TITLE=Implement feature $(echo unsafe)\n" in text
    assert finalize.read_finalize_state(target)["PR_TITLE"] == "Implement feature $(echo unsafe)"


def test_write_finalize_state_merged_rejects_newline_values(tmp_path: Path) -> None:
    target = tmp_path / "finalize-state.sh"
    with pytest.raises(Exception, match="newline"):
        finalize.write_finalize_state_merged(target, {"BAD": "x\ny"})
    with pytest.raises(Exception, match="newline"):
        finalize.write_finalize_state_merged(target, {"BAD": "x\ry"})
