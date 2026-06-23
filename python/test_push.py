"""Tests for push.py."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

import config
import git
import push
from errors import ShipError
from proc import CommandResult
from run_context import RunContext

from test_support import RecordingRunner as _RecordingRunner, make_run_context
import phantom
import rebase


@dataclass
class RecordingRunner(_RecordingRunner):
    strict: bool = True


def _push_git_responses(*extra: CommandResult) -> list[CommandResult]:
    return [
        CommandResult(
            ("git", "status", "--porcelain", "--untracked-files=all"),
            0,
            "",
            "",
            0.01,
        ),
        CommandResult(
            ("git", "symbolic-ref", "--short", "HEAD"),
            0,
            "feat/x\n",
            "",
            0.01,
        ),
        *extra,
    ]


def _ctx(**kwargs: object) -> RunContext:
    base = make_run_context(branch="feat/x")
    return base.with_(**kwargs)

def test_assert_clean_worktree_refuses_dirty() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("git", "status", "--porcelain", "--untracked-files=all"),
                0,
                " M file\n",
                "",
                0.01,
            ),
        ],
    )
    with pytest.raises(ShipError, match="uncommitted"):
        push.assert_clean_worktree(runner)


def test_push_branch_retries_then_succeeds() -> None:
    runner = RecordingRunner(
        responses=_push_git_responses(
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 1, "", "fail", 0.01),
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 0, "", "", 0.01),
        ),
    )
    result = push.push_branch(
        runner,
        _ctx(),
        sleeper=lambda _s: None,
    )
    assert result.status == "pushed"
    assert result.attempts == 2


def test_push_branch_fork_uses_origin() -> None:
    runner = RecordingRunner(
        responses=_push_git_responses(
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 0, "", "", 0.01),
        ),
    )
    result = push.push_branch(runner, _ctx(forked=True), sleeper=lambda _s: None)
    assert result.remote == "origin"


def test_push_branch_refuses_detached_head() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("git", "status", "--porcelain", "--untracked-files=all"),
                0,
                "",
                "",
                0.01,
            ),
            CommandResult(("git", "symbolic-ref", "--short", "HEAD"), 1, "", "", 0.01),
        ],
    )
    with pytest.raises(ShipError, match="detached HEAD"):
        _ = push.push_branch(runner, _ctx(), sleeper=lambda _s: None)


def test_push_backs_off_when_stderr_unchanged() -> None:
    runner = RecordingRunner(
        responses=_push_git_responses(
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 1, "", "same error", 0.01),
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 1, "", "same error", 0.01),
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 1, "", "same error", 0.01),
        ),
    )
    sleeps: list[float] = []
    result = push.push_branch(runner, _ctx(), sleeper=sleeps.append)
    assert result.status == "failed"
    assert result.attempts == config.PUSH_MAX_ATTEMPTS
    assert len(sleeps) == config.PUSH_MAX_ATTEMPTS - 1


# CLI contract tests migrated from test_push_cli.py.
def _res(rc: int = 0, stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(("cmd",), rc, stdout, stderr, 0.01)


def test_force_status_map_dirty_worktree(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner(responses=[_res(stdout="feature\n"), _res(stdout=" M file\n")])
    monkeypatch.setattr(push, "proc", runner)
    assert push.force_main([]) == 1
    out = capsys.readouterr().out
    assert "PUSHED=false" in out
    assert "STATUS=dirty_worktree" in out


def test_checkpoint_probe_emits_rebase_outcome_on_skip(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    @dataclass
    class _RebaseResult:
        exit_code: int = 0
        skipped_already_fresh: bool = True
        skipped_already_pushed: bool = False
        conflict_files: str = ""
        rebase_error: str = ""

    @dataclass
    class _ProbeResult:
        dirty: object
        append_warn_error: str = ""

    @dataclass
    class _Dirty:
        status: str = "clean"
        reason: str = ""
        count: int = 0
        paths_file: str = ""

    def _stub_rebase_push(*_args: object, **_kwargs: object) -> _RebaseResult:
        return _RebaseResult()

    monkeypatch.setattr(rebase, "rebase_push", _stub_rebase_push)
    def _stub_probe_with_warn(*_args: object, **_kwargs: object) -> _ProbeResult:
        return _ProbeResult(dirty=_Dirty())

    monkeypatch.setattr(
        phantom,
        "probe_with_warn",
        _stub_probe_with_warn,
    )
    assert push.checkpoint_probe_main(["1.r", "plan"]) == 0
    out = capsys.readouterr().out
    assert "REBASE_OUTCOME=skipped" in out
    assert "SKIPPED_ALREADY_FRESH=true" in out
    assert "CHECKPOINT_NEXT=continue" in out
    assert "PHANTOM_STATUS=clean" in out
    assert "PHANTOM_COUNT=" not in out
    assert "PHANTOM_PATHS_FILE=" not in out


def _stub_clean_phantom(monkeypatch: pytest.MonkeyPatch, calls: list[str] | None = None) -> None:
    @dataclass
    class _ProbeResult:
        dirty: object
        append_warn_error: str = ""

    @dataclass
    class _Dirty:
        status: str = "clean"
        reason: str = ""
        count: int = 0
        paths_file: str = ""

    def _stub_probe_with_warn(*_args: object, **_kwargs: object) -> _ProbeResult:
        if calls is not None:
            calls.append("phantom")
        return _ProbeResult(dirty=_Dirty())

    monkeypatch.setattr(phantom, "probe_with_warn", _stub_probe_with_warn)


def _cr(argv: tuple[str, ...] = ("git",), rc: int = 0) -> CommandResult:
    return CommandResult(argv, rc, "", "", 0.01)


def test_checkpoint_probe_emits_route_continue_on_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(rebase, "rebase_push", lambda *_args, **_kwargs: rebase.RebasePushResult(exit_code=0))  # type: ignore[arg-type]
    _stub_clean_phantom(monkeypatch)
    assert push.checkpoint_probe_main(["1.r", "plan"]) == 0
    out = capsys.readouterr().out
    assert "REBASE_OUTCOME=ok" in out
    assert "ROUTE=continue" in out
    assert "CHECKPOINT_NEXT=continue" in out


def test_checkpoint_probe_emits_route_conflict_without_phantom(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    phantom_calls: list[str] = []
    monkeypatch.setattr(
        rebase,
        "rebase_push",
        lambda *_args, **_kwargs: rebase.RebasePushResult(exit_code=1, conflict_files="src/app.py"),  # type: ignore[arg-type]
    )
    _stub_clean_phantom(monkeypatch, phantom_calls)
    assert push.checkpoint_probe_main(["4.r", "impl"]) == 1
    out = capsys.readouterr().out
    assert "REBASE_OUTCOME=conflict" in out
    assert "CONFLICT_FILES=src/app.py" in out
    assert "ROUTE=conflict" in out
    assert "CHECKPOINT_NEXT=load-routing" in out
    assert not phantom_calls


def test_checkpoint_probe_emits_route_bail_on_rebase_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        rebase,
        "rebase_push",
        lambda *_args, **_kwargs: rebase.RebasePushResult(exit_code=3, rebase_error="bad\nerror"),  # type: ignore[arg-type]
    )
    _stub_clean_phantom(monkeypatch)
    assert push.checkpoint_probe_main(["7.r", "review"]) == 3
    out = capsys.readouterr().out
    assert "REBASE_OUTCOME=failed" in out
    assert "REBASE_ERROR=bad error" in out
    assert "ROUTE=bail" in out
    assert "CHECKPOINT_NEXT=load-routing" in out


def test_checkpoint_probe_emits_load_routing_on_unexpected_rebase_code(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        rebase,
        "rebase_push",
        lambda *_args, **_kwargs: rebase.RebasePushResult(exit_code=9),  # type: ignore[arg-type]
    )
    _stub_clean_phantom(monkeypatch)
    assert push.checkpoint_probe_main(["7.r", "review"]) == 9
    out = capsys.readouterr().out
    assert "REBASE_OUTCOME=failed" in out
    assert "REBASE_ERROR=unexpected-rc-9" in out
    assert "ROUTE=bail" in out
    assert "CHECKPOINT_NEXT=load-routing" in out


def test_checkpoint_probe_forked_target_defaults_to_upstream_main(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def _stub_rebase_push(*_args: object, **kwargs: object) -> rebase.RebasePushResult:
        seen.update(kwargs)
        return rebase.RebasePushResult(exit_code=0, skipped_already_fresh=True)

    monkeypatch.setattr(rebase, "rebase_push", _stub_rebase_push)
    _stub_clean_phantom(monkeypatch)
    assert push.checkpoint_probe_main(["1.r", "plan", "--forked-target", "true"]) == 0
    assert seen["base_remote"] == "upstream"
    assert seen["base_ref"] == "main"


def test_checkpoint_probe_explicit_base_overrides_fork_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def _stub_rebase_push(*_args: object, **kwargs: object) -> rebase.RebasePushResult:
        seen.update(kwargs)
        return rebase.RebasePushResult(exit_code=0, skipped_already_fresh=True)

    monkeypatch.setattr(rebase, "rebase_push", _stub_rebase_push)
    _stub_clean_phantom(monkeypatch)
    assert (
        push.checkpoint_probe_main(
            ["1.r", "plan", "--forked-target", "true", "--base-remote", "origin", "--base-ref", "develop"]
        )
        == 0
    )
    assert seen["base_remote"] == "origin"
    assert seen["base_ref"] == "develop"


def test_checkpoint_probe_resolves_larch_log_only_conflict(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    results = iter([
        rebase.RebasePushResult(exit_code=1, conflict_files="larch-logs/run/log.md"),
        rebase.RebasePushResult(exit_code=0),
    ])
    calls: list[str] = []
    monkeypatch.setattr(rebase, "rebase_push", lambda *_args, **_kwargs: next(results))  # type: ignore[arg-type]
    monkeypatch.setattr(git, "checkout_ours", lambda *_args, **_kwargs: calls.append("checkout") or _cr())  # type: ignore[arg-type]
    monkeypatch.setattr(git, "add", lambda *_args, **_kwargs: calls.append("add") or _cr())  # type: ignore[arg-type]
    _stub_clean_phantom(monkeypatch, calls)
    assert push.checkpoint_probe_main(["4.r", "impl"]) == 0
    out = capsys.readouterr().out
    assert "ROUTE=continue" in out
    assert "CHECKPOINT_NEXT=continue" in out
    assert calls == ["checkout", "add", "phantom"]


def test_checkpoint_probe_resolves_consecutive_larch_log_conflicts(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    results = iter([
        rebase.RebasePushResult(exit_code=1, conflict_files="larch-logs/a.md"),
        rebase.RebasePushResult(exit_code=1, conflict_files="larch-logs/b.md"),
        rebase.RebasePushResult(exit_code=0),
    ])
    calls: list[str] = []
    monkeypatch.setattr(rebase, "rebase_push", lambda *_args, **_kwargs: next(results))  # type: ignore[arg-type]
    monkeypatch.setattr(git, "checkout_ours", lambda *_args, **_kwargs: calls.append("checkout") or _cr())  # type: ignore[arg-type]
    monkeypatch.setattr(git, "add", lambda *_args, **_kwargs: calls.append("add") or _cr())  # type: ignore[arg-type]
    _stub_clean_phantom(monkeypatch, calls)
    assert push.checkpoint_probe_main(["4.r", "impl"]) == 0
    assert "ROUTE=continue" in capsys.readouterr().out
    assert calls == ["checkout", "add", "checkout", "add", "phantom"]


def test_checkpoint_probe_mixed_conflict_resolves_only_larch_logs(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    phantom_calls: list[str] = []
    monkeypatch.setattr(
        rebase,
        "rebase_push",
        lambda *_args, **_kwargs: rebase.RebasePushResult(  # type: ignore[arg-type]
            exit_code=1,
            conflict_files="larch-logs/a.md,src/app.py",
        ),
    )
    monkeypatch.setattr(git, "checkout_ours", lambda *_args, **_kwargs: _cr())  # type: ignore[arg-type]
    monkeypatch.setattr(git, "add", lambda *_args, **_kwargs: _cr())  # type: ignore[arg-type]
    monkeypatch.setattr(git, "try_unmerged_paths", lambda *_args, **_kwargs: ["src/app.py"])  # type: ignore[arg-type]
    _stub_clean_phantom(monkeypatch, phantom_calls)
    assert push.checkpoint_probe_main(["4.r", "impl"]) == 1
    out = capsys.readouterr().out
    assert "CONFLICT_FILES=src/app.py" in out
    assert "ROUTE=conflict" in out
    assert not phantom_calls


def test_checkpoint_probe_trivial_then_nontrivial_continue_conflict(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    results = iter([
        rebase.RebasePushResult(exit_code=1, conflict_files="larch-logs/a.md"),
        rebase.RebasePushResult(exit_code=1, conflict_files="src/app.py"),
    ])
    monkeypatch.setattr(rebase, "rebase_push", lambda *_args, **_kwargs: next(results))  # type: ignore[arg-type]
    monkeypatch.setattr(git, "checkout_ours", lambda *_args, **_kwargs: _cr())  # type: ignore[arg-type]
    monkeypatch.setattr(git, "add", lambda *_args, **_kwargs: _cr())  # type: ignore[arg-type]
    _stub_clean_phantom(monkeypatch, [])
    assert push.checkpoint_probe_main(["4.r", "impl"]) == 1
    assert "CONFLICT_FILES=src/app.py" in capsys.readouterr().out


def test_checkpoint_probe_trivial_continue_failure_routes_bail(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    results = iter([
        rebase.RebasePushResult(exit_code=1, conflict_files="larch-logs/a.md"),
        rebase.RebasePushResult(exit_code=3, rebase_error="continue failed"),
    ])
    monkeypatch.setattr(rebase, "rebase_push", lambda *_args, **_kwargs: next(results))  # type: ignore[arg-type]
    monkeypatch.setattr(git, "checkout_ours", lambda *_args, **_kwargs: _cr())  # type: ignore[arg-type]
    monkeypatch.setattr(git, "add", lambda *_args, **_kwargs: _cr())  # type: ignore[arg-type]
    _stub_clean_phantom(monkeypatch)
    assert push.checkpoint_probe_main(["4.r", "impl"]) == 3
    out = capsys.readouterr().out
    assert "REBASE_ERROR=continue failed" in out
    assert "ROUTE=bail" in out
    assert "CHECKPOINT_NEXT=load-routing" in out


def test_checkpoint_probe_resolve_failure_rederives_conflicts(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        rebase,
        "rebase_push",
        lambda *_args, **_kwargs: rebase.RebasePushResult(exit_code=1, conflict_files="larch-logs/a.md"),  # type: ignore[arg-type]
    )
    monkeypatch.setattr(git, "checkout_ours", lambda *_args, **_kwargs: _cr(rc=1))  # type: ignore[arg-type]
    monkeypatch.setattr(
        git,
        "try_conflict_files",
        lambda *_args, **_kwargs: (  # type: ignore[arg-type]
            git.ConflictFile(path="larch-logs/a.md", stage_1=True, stage_2=True, stage_3=True),
        ),
    )
    monkeypatch.setattr(git, "try_unmerged_paths", lambda *_args, **_kwargs: ["larch-logs/a.md"])  # type: ignore[arg-type]
    _stub_clean_phantom(monkeypatch)
    assert push.checkpoint_probe_main(["4.r", "impl"]) == 1
    assert "CONFLICT_FILES=larch-logs/a.md" in capsys.readouterr().out


def test_checkpoint_probe_empty_conflict_files_skips_trivial_loop(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(rebase, "rebase_push", lambda *_args, **_kwargs: rebase.RebasePushResult(exit_code=1))  # type: ignore[arg-type]
    monkeypatch.setattr(git, "try_unmerged_paths", lambda *_args, **_kwargs: [])  # type: ignore[arg-type]
    monkeypatch.setattr(git, "try_conflict_files", lambda *_args, **_kwargs: ())  # type: ignore[arg-type]
    monkeypatch.setattr(git, "checkout_ours", lambda *_args, **_kwargs: calls.append("checkout") or _cr())  # type: ignore[arg-type]
    _stub_clean_phantom(monkeypatch)
    assert push.checkpoint_probe_main(["4.r", "impl"]) == 1
    out = capsys.readouterr().out
    assert "CONFLICT_FILES=" in out
    assert not calls


def _git(repo: Path, *args: str) -> None:
    _ = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def _hash_object(repo: Path, content: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), "hash-object", "-w", "--stdin"],
        input=content,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def _make_conflict_repo(repo: Path, *paths: str) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "Test")
    _ = (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "init")
    zero = "0" * 40
    for path in paths:
        parent = Path(path).parent
        if str(parent) != path:
            (repo / parent).mkdir(parents=True, exist_ok=True)
        base_blob = _hash_object(repo, f"base {path}\n")
        ours_blob = _hash_object(repo, f"ours {path}\n")
        theirs_blob = _hash_object(repo, f"theirs {path}\n")
        _ = (repo / path).write_text(f"worktree conflict {path}\n", encoding="utf-8")
        index_info = (
            f"0 {zero}\t{path}\n"
            f"100644 {base_blob} 1\t{path}\n"
            f"100644 {ours_blob} 2\t{path}\n"
            f"100644 {theirs_blob} 3\t{path}\n"
        )
        _ = subprocess.run(
            ["git", "-C", str(repo), "update-index", "--index-info"],
            input=index_info,
            capture_output=True,
            text=True,
            check=True,
        )


def _make_case24_rebase_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo24"
    repo.mkdir(parents=True, exist_ok=True)
    path = "larch-logs/implement/run-1/manifest.json"
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "Test")
    _ = (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "init")
    _git(repo, "checkout", "-q", "-b", "feature")
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    _ = (repo / path).write_text("feature manifest\n", encoding="utf-8")
    _git(repo, "add", path)
    _git(repo, "commit", "-q", "-m", "feature log")
    _git(repo, "checkout", "-q", "-B", "main")
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    _ = (repo / path).write_text("main manifest\n", encoding="utf-8")
    _git(repo, "add", path)
    _git(repo, "commit", "-q", "-m", "main log")
    bare = tmp_path / "repo24.git"
    bare.mkdir(parents=True, exist_ok=True)
    _git(bare, "init", "--bare", "-q")
    _git(repo, "remote", "add", "origin", str(bare))
    _git(repo, "push", "-q", "origin", "main")
    _git(repo, "checkout", "-q", "feature")
    return repo


def test_checkpoint_probe_partial_resolve_rederives_remaining_conflict(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo22"
    _make_conflict_repo(
        repo,
        "larch-logs/implement/run-1/one.json",
        "larch-logs/implement/run-1/two.json",
    )
    monkeypatch.chdir(repo)
    monkeypatch.setattr(
        rebase,
        "rebase_push",
        lambda *_args, **_kwargs: rebase.RebasePushResult(  # type: ignore[arg-type]
            exit_code=1,
            conflict_files="larch-logs/implement/run-1/one.json,larch-logs/implement/run-1/two.json",
        ),
    )

    def checkout_ours(_runner: object, path: str, **_kwargs: object) -> CommandResult:
        if path == "larch-logs/implement/run-1/two.json":
            return _cr(rc=42)
        return _cr()

    monkeypatch.setattr(git, "checkout_ours", checkout_ours)  # type: ignore[arg-type]
    monkeypatch.setattr(git, "rm", lambda *_args, **_kwargs: _cr(rc=42))  # type: ignore[arg-type]
    _stub_clean_phantom(monkeypatch)
    assert push.checkpoint_probe_main(["4.r", "impl"]) == 1
    out = capsys.readouterr().out
    assert "CONFLICT_FILES=larch-logs/implement/run-1/two.json" in out
    assert "larch-logs/implement/run-1/one.json,larch-logs/implement/run-1/two.json" not in out


def test_checkpoint_probe_mixed_conflict_real_git_index(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo19"
    _make_conflict_repo(
        repo,
        "larch-logs/implement/run-1/manifest.json",
        "python/stall_recovery.py",
    )
    monkeypatch.chdir(repo)
    continue_calls: list[bool] = []

    def stub_rebase_push(*_args: object, **kwargs: object) -> rebase.RebasePushResult:
        continue_calls.append(bool(kwargs.get("continue_mode")))
        return rebase.RebasePushResult(
            exit_code=1,
            conflict_files="larch-logs/implement/run-1/manifest.json,python/stall_recovery.py",
        )

    monkeypatch.setattr(rebase, "rebase_push", stub_rebase_push)
    phantom_calls: list[str] = []
    _stub_clean_phantom(monkeypatch, phantom_calls)
    assert push.checkpoint_probe_main(["4.r", "impl"]) == 1
    out = capsys.readouterr().out
    assert "CONFLICT_FILES=python/stall_recovery.py" in out
    assert "ROUTE=conflict" in out
    assert not phantom_calls
    assert not any(continue_calls)
    remaining = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    assert remaining == "python/stall_recovery.py"


def test_checkpoint_probe_empty_continue_skip_recovery_real_git(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    repo = _make_case24_rebase_repo(tmp_path)
    monkeypatch.chdir(repo)
    _stub_clean_phantom(monkeypatch)
    assert push.checkpoint_probe_main(["4.r", "impl", "--base-remote", "origin", "--base-ref", "main"]) == 0
    out = capsys.readouterr().out
    assert "ROUTE=continue" in out
    remaining = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    assert remaining == ""
    git_dir = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    rebase_root = repo / git_dir if not Path(git_dir).is_absolute() else Path(git_dir)
    assert not (rebase_root / "rebase-merge").is_dir()
    assert not (rebase_root / "rebase-apply").is_dir()


def test_checkpoint_probe_empty_continue_after_larch_log_uses_skip(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    results = iter([
        rebase.RebasePushResult(exit_code=1, conflict_files="larch-logs/a.md"),
        rebase.RebasePushResult(exit_code=3, rebase_error="nothing to commit"),
        rebase.RebasePushResult(exit_code=0),
    ])
    calls: list[str] = []
    monkeypatch.setattr(rebase, "rebase_push", lambda *_args, **_kwargs: next(results))  # type: ignore[arg-type]
    monkeypatch.setattr(git, "checkout_ours", lambda *_args, **_kwargs: _cr())  # type: ignore[arg-type]
    monkeypatch.setattr(git, "add", lambda *_args, **_kwargs: _cr())  # type: ignore[arg-type]
    monkeypatch.setattr(git, "try_unmerged_paths", lambda *_args, **_kwargs: [])  # type: ignore[arg-type]
    monkeypatch.setattr(git, "try_conflict_files", lambda *_args, **_kwargs: ())  # type: ignore[arg-type]
    monkeypatch.setattr(git, "rebase_skip", lambda *_args, **_kwargs: calls.append("skip") or _cr())  # type: ignore[arg-type]
    _stub_clean_phantom(monkeypatch, calls)
    assert push.checkpoint_probe_main(["4.r", "impl"]) == 0
    assert "ROUTE=continue" in capsys.readouterr().out
    assert calls == ["skip", "phantom"]


def test_checkpoint_probe_skip_after_completed_rebase_returns_continue(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    results = iter([
        rebase.RebasePushResult(exit_code=1, conflict_files="larch-logs/a.md"),
        rebase.RebasePushResult(exit_code=3, rebase_error="nothing to commit"),
    ])
    calls: list[str] = []
    monkeypatch.setattr(rebase, "rebase_push", lambda *_args, **_kwargs: next(results))  # type: ignore[arg-type]
    monkeypatch.setattr(git, "checkout_ours", lambda *_args, **_kwargs: _cr())  # type: ignore[arg-type]
    monkeypatch.setattr(git, "add", lambda *_args, **_kwargs: _cr())  # type: ignore[arg-type]
    monkeypatch.setattr(git, "try_unmerged_paths", lambda *_args, **_kwargs: [])  # type: ignore[arg-type]
    monkeypatch.setattr(git, "try_conflict_files", lambda *_args, **_kwargs: ())  # type: ignore[arg-type]
    monkeypatch.setattr(git, "rebase_skip", lambda *_args, **_kwargs: calls.append("skip") or _cr())  # type: ignore[arg-type]
    monkeypatch.setattr(git, "rebase_in_progress", lambda *_args, **_kwargs: False)  # type: ignore[arg-type]
    _stub_clean_phantom(monkeypatch, calls)
    assert push.checkpoint_probe_main(["4.r", "impl"]) == 0
    assert "ROUTE=continue" in capsys.readouterr().out
    assert calls == ["skip", "phantom"]
    assert "continue" not in calls


def test_branch_push_dedupes_stderr(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner(responses=[_res(stdout="feature\n"), _res(stdout="feature\n"), _res(1, stderr="nope\n"), _res(stdout="feature\n"), _res(1, stderr="nope\n"), _res(stdout="feature\n"), _res(1, stderr="nope\n")])
    monkeypatch.setattr(push, "proc", runner)
    assert push.branch_main([]) == 1
    captured = capsys.readouterr()
    assert "BRANCH=feature" in captured.out
    assert "(repeated 3 times)" in captured.err
    assert "(repeated 3 times)" in captured.err


def test_branch_push_propagates_final_exit_code(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner(
        responses=[
            _res(stdout="feature\n"),
            _res(stdout="feature\n"),
            _res(7, stderr="push failed\n"),
            _res(stdout="feature\n"),
            _res(7, stderr="push failed\n"),
            _res(stdout="feature\n"),
            _res(7, stderr="push failed\n"),
        ],
    )
    monkeypatch.setattr(push, "proc", runner)
    assert push.branch_main([]) == 7
    captured = capsys.readouterr()
    assert "BRANCH=feature" in captured.out


def test_branch_main_unknown_argument_stderr_prefix(capsys: pytest.CaptureFixture[str]) -> None:
    assert push.branch_main(["--bogus"]) == 1
    err = capsys.readouterr().err
    assert "git-push.sh: unknown argument: --bogus" in err


def test_force_main_detached_head_stderr_prefix(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_recovery(*_args: object, **_kwargs: object) -> git.ForcePushResult:
        return git.ForcePushResult(pushed=False, status="detached_head", branch="")

    monkeypatch.setattr(git, "force_push_recovery", fake_recovery)
    assert push.force_main([]) == 2
    err = capsys.readouterr().err
    assert err.strip() == "git-force-push.sh: not on a named branch"
