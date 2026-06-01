"""Tests for rebase.py (stub runner + stub launch_fn)."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import changelog
import config
import rebase
import version_bump
from agents import LaunchFailure, TierAttempt
from bump_worktree import DropResult
from changelog import ChangelogError
from version_bump import ApplyResult, BumpClassification
from errors import NeedsUserInput, Stalled, TransientNetworkError
from proc import CommandResult


def _empty_argv_log() -> list[tuple[str, ...]]:
    return []


@dataclass
class ScriptRunner:
    """Runner that matches argv by prefix; defaults to success when permissive."""

    handlers: list[
        tuple[
            tuple[str, ...],
            CommandResult | Exception | Callable[[tuple[str, ...]], CommandResult],
        ]
    ]
    calls: list[tuple[str, ...]] = field(default_factory=_empty_argv_log)
    permissive: bool = True

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
        key = tuple(argv)
        self.calls.append(key)
        for pattern, result in self.handlers:
            if len(key) >= len(pattern) and key[: len(pattern)] == pattern:
                if isinstance(result, Exception):
                    raise result
                if callable(result):
                    return result(key)
                return result
        if self.permissive:
            return _ok(key)
        msg = f"unexpected argv: {argv}"
        raise AssertionError(msg)


def _ok(argv: Sequence[str], stdout: str = "") -> CommandResult:
    return CommandResult(tuple(argv), 0, stdout, "", 0.01)


def _fail(argv: Sequence[str], stderr: str = "error", code: int = 1) -> CommandResult:
    return CommandResult(tuple(argv), code, "", stderr, 0.01)


def _noop_commit_changelog_after_rebump(
    runner: ScriptRunner,
    new_version: str,
    old_version: str,
    bullets_path: Path,
    *,
    cwd: str | None,
) -> None:
    _ = runner, new_version, old_version, bullets_path, cwd


def test_rebump_bullets_path_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.ENV_IMPLEMENT_TMPDIR, raising=False)
    assert rebase._rebump_bullets_path("/tmp/x", None) == Path(  # pyright: ignore[reportPrivateUsage]
        "/tmp/x/.rrr-rebump-bullets.md",
    )
    assert rebase._rebump_bullets_path(None, "/explicit.md") == Path(  # pyright: ignore[reportPrivateUsage]
        "/explicit.md",
    )
    assert rebase._rebump_bullets_path(None, None) is None  # pyright: ignore[reportPrivateUsage]


def test_missing_bullets_path_stalls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(config.ENV_IMPLEMENT_TMPDIR, raising=False)
    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
        ],
    )
    with pytest.raises(Stalled, match="bullets path"):
        _ = rebase.rebase_and_rebump(
            runner,
            lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
            repo="o/r",
            run_id="run",
            cwd=str(tmp_path),
        )


def test_attempt_cap_stalls() -> None:
    runner = ScriptRunner([])
    with pytest.raises(Stalled, match="attempt cap"):
        _ = rebase.rebase_and_rebump(
            runner,
            lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
            repo="o/r",
            run_id="run",
            tmpdir="/tmp",
            rebase_attempt=config.REBASE_MAX_ATTEMPTS,
        )


def test_detached_head_stalls() -> None:
    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _fail(("git", "symbolic-ref", "--short", "HEAD"))),
        ],
    )
    with pytest.raises(Stalled, match="detached"):
        _ = rebase.rebase_and_rebump(
            runner,
            lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
            repo="o/r",
            run_id="run",
            tmpdir="/tmp",
        )


def test_fetch_transient_raises(tmp_path: Path) -> None:
    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
            (("git", "status", "--porcelain"), _ok(("git", "status", "--porcelain"))),
            (("git", "log", "-1", "--format=%s"), _ok(("git", "log", "-1", "--format=%s"), "other\n")),
            (("git", "fetch", "origin", "main", "--quiet"), _fail(
                ("git", "fetch", "origin", "main", "--quiet"),
                "network/auth issue\n",
            )),
            (("git", "rebase", "--abort"), _ok(("git", "rebase", "--abort"))),
        ],
    )
    with pytest.raises(TransientNetworkError):
        _ = rebase.rebase_and_rebump(
            runner,
            lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
            repo="o/r",
            run_id="run",
            tmpdir=str(tmp_path),
            cwd=str(tmp_path),
        )


def _patch_none_classify(monkeypatch: pytest.MonkeyPatch) -> None:
    def _none(runner: ScriptRunner, *, cwd: str | None = None) -> BumpClassification:
        _ = runner, cwd
        return BumpClassification(
            current_version="1.0.0",
            new_version="1.0.0",
            bump_type="NONE",
            major_reasons=(),
            minor_reasons=(),
            reasoning="",
        )

    monkeypatch.setattr(version_bump, "classify_bump", _none)


def _write_classify_repo(tmp_path: Path) -> None:
    plugin = tmp_path / config.PLUGIN_JSON_PATH
    _ = plugin.parent.mkdir(parents=True, exist_ok=True)
    _ = plugin.write_text('{"version": "1.0.0"}\n', encoding="utf-8")
    skill = tmp_path / "skills" / "x" / "SKILL.md"
    _ = skill.parent.mkdir(parents=True, exist_ok=True)
    _ = skill.write_text("---\nname: x\n---\nbody\n", encoding="utf-8")


def test_already_fresh_skips_rebase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_classify_repo(tmp_path)
    _patch_none_classify(monkeypatch)
    bullets = tmp_path / ".rrr-rebump-bullets.md"
    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
            (("git", "status", "--porcelain"), _ok(("git", "status", "--porcelain"))),
            (("git", "log", "-1", "--format=%s"), _ok(("git", "log", "-1", "--format=%s"), "feat: work\n")),
            (("git", "fetch", "origin", "main", "--quiet"), _ok(("git", "fetch", "origin", "main", "--quiet"))),
            (("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"), _ok(
                ("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"),
            )),
            (("git", "rev-parse", "main"), _fail(("git", "rev-parse", "main"))),
            (("git", "rev-parse", "HEAD"), _ok(("git", "rev-parse", "HEAD"), "deadbeef\n")),
            (("git", "merge-base", "main", "HEAD"), _fail(("git", "merge-base", "main", "HEAD"))),
            (("git", "merge-base", "origin/main", "HEAD"), _ok(
                ("git", "merge-base", "origin/main", "HEAD"),
                "base\n",
            )),
            (("git", "diff", "--name-only", "base", "HEAD"), _ok(
                ("git", "diff", "--name-only", "base", "HEAD"),
                "",
            )),
            (("git", "show", f"origin/main:{config.PLUGIN_JSON_PATH}"), _ok(
                ("git", "show", f"origin/main:{config.PLUGIN_JSON_PATH}"),
                json.dumps({"version": "1.0.0"}),
            )),
            (("git", "status", "--porcelain", "--untracked-files=no"), _ok(
                ("git", "status", "--porcelain", "--untracked-files=no"),
            )),
            (("git", "fetch", "origin", "feat", "--quiet"), _ok(("git", "fetch", "origin", "feat", "--quiet"))),
            (("git", "push", "--force-with-lease", "origin", "feat"), _ok(
                ("git", "push", "--force-with-lease", "origin", "feat"),
            )),
        ],
    )
    result = rebase.rebase_and_rebump(
        runner,
        lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
        repo="o/r",
        run_id="run",
        tmpdir=str(tmp_path),
        bullets_path=bullets,
        cwd=str(tmp_path),
    )
    assert result.rebased is False
    assert result.pushed is True
    assert result.new_version is None
    assert not any(c[:3] == ("git", "rebase", "origin/main") for c in runner.calls)


def test_bump_none_still_force_pushes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_classify_repo(tmp_path)
    _patch_none_classify(monkeypatch)
    bullets = tmp_path / ".rrr-rebump-bullets.md"
    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
            (("git", "status", "--porcelain"), _ok(("git", "status", "--porcelain"))),
            (("git", "log", "-1", "--format=%s"), _ok(("git", "log", "-1", "--format=%s"), "feat: work\n")),
            (("git", "fetch", "origin", "main", "--quiet"), _ok(("git", "fetch", "origin", "main", "--quiet"))),
            (("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"), _ok(
                ("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"),
            )),
            (("git", "rev-parse", "main"), _fail(("git", "rev-parse", "main"))),
            (("git", "merge-base", "main", "HEAD"), _fail(("git", "merge-base", "main", "HEAD"))),
            (("git", "merge-base", "origin/main", "HEAD"), _ok(
                ("git", "merge-base", "origin/main", "HEAD"),
                "base\n",
            )),
            (("git", "status", "--porcelain", "--untracked-files=all"), _ok(
                ("git", "status", "--porcelain", "--untracked-files=all"),
            )),
            (("git", "fetch", "origin", "feat", "--quiet"), _ok(("git", "fetch", "origin", "feat", "--quiet"))),
            (("git", "push", "--force-with-lease", "origin", "feat"), _ok(
                ("git", "push", "--force-with-lease", "origin", "feat"),
            )),
        ],
    )
    result = rebase.rebase_and_rebump(
        runner,
        lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
        repo="o/r",
        run_id="run",
        tmpdir=str(tmp_path),
        bullets_path=bullets,
        cwd=str(tmp_path),
    )
    assert result.new_version is None
    assert result.pushed is True
    assert not any("apply" in " ".join(c) for c in runner.calls if c[0] != "git")


def test_waterfall_exhaustion_needs_user_input(tmp_path: Path) -> None:
    bullets = tmp_path / ".rrr-rebump-bullets.md"
    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
            (("git", "status", "--porcelain"), _ok(("git", "status", "--porcelain"))),
            (("git", "log", "-1", "--format=%s"), _ok(("git", "log", "-1", "--format=%s"), "work\n")),
            (("git", "fetch", "origin", "main", "--quiet"), _ok(("git", "fetch", "origin", "main", "--quiet"))),
            (("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"), _fail(
                ("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"),
            )),
            (("git", "rebase", "origin/main"), _fail(("git", "rebase", "origin/main"))),
            (("git", "diff", "--name-only", "--diff-filter=U"), _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "vendor/foo.txt\n",
            )),
        ],
    )

    def launch_fn(tier: str, conflict_csv: str) -> TierAttempt:
        assert tier in config.FIXER_TIER_ORDER
        assert conflict_csv == "vendor/foo.txt"
        return TierAttempt(
            tier=tier,
            wrapper_rc=0,
            launcher_exit=1,
            failure=LaunchFailure("other", "unknown"),
        )

    with pytest.raises(NeedsUserInput):
        _ = rebase.rebase_and_rebump(
            runner,
            launch_fn,
            repo="o/r",
            run_id="run",
            tmpdir=str(tmp_path),
            bullets_path=bullets,
            cwd=str(tmp_path),
        )


def test_is_empty_or_already_applied_error() -> None:
    assert rebase._is_empty_or_already_applied_rebase_error(  # pyright: ignore[reportPrivateUsage]
        "nothing to commit",
    )
    assert rebase._is_empty_or_already_applied_rebase_error("No changes")  # pyright: ignore[reportPrivateUsage]
    assert not rebase._is_empty_or_already_applied_rebase_error(  # pyright: ignore[reportPrivateUsage]
        "pre-commit hook failed",
    )


def test_force_push_oid_and_retry(tmp_path: Path) -> None:
    sleeps: list[float] = []
    runner = ScriptRunner(
        [
            (("git", "status", "--porcelain"), _ok(("git", "status", "--porcelain"))),
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
            (("git", "fetch", "origin", "feat", "--quiet"), _ok(("git", "fetch", "origin", "feat", "--quiet"))),
            (
                ("git", "push", "--force-with-lease=refs/heads/feat:abc", "origin"),
                _fail(("git", "push", "--force-with-lease=refs/heads/feat:abc", "origin")),
            ),
            (("git", "fetch", "origin", "feat", "--quiet"), _ok(("git", "fetch", "origin", "feat", "--quiet"))),
            (("git", "rev-parse", "HEAD"), _ok(("git", "rev-parse", "HEAD"), "deadbeef\n")),
            (("git", "rev-parse", "origin/feat"), _ok(("git", "rev-parse", "origin/feat"), "deadbeef\n")),
        ],
        permissive=False,
    )
    result = rebase._force_push_branch(  # pyright: ignore[reportPrivateUsage]
        runner,
        cwd=str(tmp_path),
        sleep_fn=sleeps.append,
        expected_remote_oid="abc",
    )
    assert result.returncode == 0
    assert not sleeps


def test_launch_fn_receives_conflict_csv() -> None:
    seen: list[tuple[str, str]] = []

    def launch_fn(tier: str, csv: str) -> TierAttempt:
        seen.append((tier, csv))
        return TierAttempt(tier, 0, 0, LaunchFailure("none", ""))

    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "vendor/x.txt\n",
            )),
        ],
    )
    with pytest.raises(NeedsUserInput):
        rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
            runner,
            launch_fn,
            repo="o/r",
            run_id="run",
            cwd=None,
        )
    assert seen
    assert seen[0][1] == "vendor/x.txt"


def test_non_conflict_rebase_aborts_and_stalls(tmp_path: Path) -> None:
    bullets = tmp_path / ".rrr-rebump-bullets.md"
    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
            (("git", "fetch", "origin", "main", "--quiet"), _ok(("git", "fetch", "origin", "main", "--quiet"))),
            (("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"), _fail(
                ("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"),
            )),
            (("git", "rebase", "origin/main"), _fail(("git", "rebase", "origin/main"), "fatal")),
            (("git", "diff", "--name-only", "--diff-filter=U"), _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "",
            )),
            (("git", "rebase", "--abort"), _ok(("git", "rebase", "--abort"))),
        ],
    )
    with pytest.raises(Stalled, match="rebase failed"):
        _ = rebase.rebase_and_rebump(
            runner,
            lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
            repo="o/r",
            run_id="run",
            tmpdir=str(tmp_path),
            bullets_path=bullets,
            cwd=str(tmp_path),
        )
    assert ("git", "rebase", "--abort") in runner.calls


def test_invalid_old_version_skips_staging(tmp_path: Path) -> None:
    bullets = tmp_path / ".rrr-rebump-bullets.md"
    runner = ScriptRunner([])
    rebase._stage_rebump_bullets(  # pyright: ignore[reportPrivateUsage]
        runner,
        old_version="not-semver",
        bullets_path=bullets,
        cwd=str(tmp_path),
    )
    assert not bullets.exists()
    assert not any("drop" in " ".join(c) for c in runner.calls)


def test_fetch_non_transient_aborts_and_stalls(tmp_path: Path) -> None:
    bullets = tmp_path / ".rrr-rebump-bullets.md"
    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
            (("git", "status", "--porcelain"), _ok(("git", "status", "--porcelain"))),
            (("git", "log", "-1", "--format=%s"), _ok(("git", "log", "-1", "--format=%s"), "work\n")),
            (("git", "fetch", "origin", "main", "--quiet"), _fail(
                ("git", "fetch", "origin", "main", "--quiet"),
                "repository not found\n",
            )),
            (("git", "rebase", "--abort"), _ok(("git", "rebase", "--abort"))),
        ],
    )
    with pytest.raises(Stalled, match="fetch failed"):
        _ = rebase.rebase_and_rebump(
            runner,
            lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
            repo="o/r",
            run_id="run",
            tmpdir=str(tmp_path),
            bullets_path=bullets,
            cwd=str(tmp_path),
        )
    assert ("git", "rebase", "--abort") in runner.calls


def test_unmerged_diff_failure_stalls_in_resolve_conflicts() -> None:
    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), _fail(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "fatal: index corrupt",
            )),
        ],
    )
    with pytest.raises(Stalled, match="diff-filter=U"):
        rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
            runner,
            lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
            repo="o/r",
            run_id="run",
            cwd=None,
        )


def test_make_conflict_launch_fn_argv(tmp_path: Path) -> None:
    out_dir = tmp_path / "launch"
    runner = ScriptRunner([], permissive=True)
    launch_fn = rebase.make_conflict_launch_fn(
        runner,
        repo="owner/repo",
        run_id="run-42",
        output_dir=out_dir,
        cwd=str(tmp_path),
    )
    attempt = launch_fn("cursor", "a.txt,b.txt")
    assert attempt.launcher_exit == 0


def test_make_conflict_launch_fn_reads_launcher_exit_from_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_dir = tmp_path / "launch"
    runner = ScriptRunner([], permissive=True)

    def _launch_stdout(
        _runner: ScriptRunner,
        tier: str,
        **kwargs: object,
    ) -> CommandResult:
        _ = _runner, tier, kwargs
        return CommandResult(("launch",), 0, "LAUNCHER_EXIT=1\n", "", 0.01)

    monkeypatch.setattr(rebase.agents, "launch_tier", _launch_stdout)
    launch_fn = rebase.make_conflict_launch_fn(
        runner,
        repo="owner/repo",
        run_id="run-42",
        output_dir=out_dir,
        cwd=str(tmp_path),
    )
    attempt = launch_fn("cursor", "a.txt")
    assert attempt.launcher_exit == 1


def test_rebase_result_uses_apply_result_new_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rebase,
        "_commit_changelog_after_rebump",
        _noop_commit_changelog_after_rebump,
    )
    _write_classify_repo(tmp_path)
    bullets = tmp_path / ".rrr-rebump-bullets.md"

    def _patch(runner: ScriptRunner, *, cwd: str | None = None) -> BumpClassification:
        _ = runner, cwd
        return BumpClassification(
            current_version="1.0.0",
            new_version="1.0.1",
            bump_type="PATCH",
            major_reasons=(),
            minor_reasons=(),
            reasoning="",
        )

    def _apply(
        runner: ScriptRunner,
        new_version: str,
        *,
        cwd: str | None = None,
        base_remote: str = "origin",
        base_ref: str = "main",
    ) -> ApplyResult:
        _ = runner, new_version, cwd, base_remote, base_ref
        return ApplyResult(applied=True, new_version="2.0.0", commit_sha="abc")

    monkeypatch.setattr(version_bump, "classify_bump", _patch)
    monkeypatch.setattr(version_bump, "apply_bump", _apply)
    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
            (("git", "status", "--porcelain"), _ok(("git", "status", "--porcelain"))),
            (("git", "log", "-1", "--format=%s"), _ok(("git", "log", "-1", "--format=%s"), "work\n")),
            (("git", "fetch", "origin", "main", "--quiet"), _ok(("git", "fetch", "origin", "main", "--quiet"))),
            (("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"), _ok(
                ("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"),
            )),
            (("git", "rev-parse", "main"), _fail(("git", "rev-parse", "main"))),
            (("git", "merge-base", "main", "HEAD"), _fail(("git", "merge-base", "main", "HEAD"))),
            (("git", "merge-base", "origin/main", "HEAD"), _ok(
                ("git", "merge-base", "origin/main", "HEAD"),
                "base\n",
            )),
            (("git", "show", f"origin/main:{config.PLUGIN_JSON_PATH}"), _ok(
                ("git", "show", f"origin/main:{config.PLUGIN_JSON_PATH}"),
                json.dumps({"version": "1.0.0"}),
            )),
            (("git", "status", "--porcelain", "--untracked-files=no"), _ok(
                ("git", "status", "--porcelain", "--untracked-files=no"),
            )),
            (("git", "fetch", "origin", "feat", "--quiet"), _ok(("git", "fetch", "origin", "feat", "--quiet"))),
            (("git", "push", "--force-with-lease", "origin", "feat"), _ok(
                ("git", "push", "--force-with-lease", "origin", "feat"),
            )),
        ],
    )
    result = rebase.rebase_and_rebump(
        runner,
        lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
        repo="o/r",
        run_id="run",
        tmpdir=str(tmp_path),
        bullets_path=bullets,
        cwd=str(tmp_path),
    )
    assert result.new_version == "2.0.0"


def test_deterministic_prepass_no_checkout_ours_on_vendor() -> None:
    runner = ScriptRunner(
        [
            (("git", "checkout", "--ours", "--", "vendor/foo.txt"), _fail(
                ("git", "checkout", "--ours", "--", "vendor/foo.txt"),
            )),
        ],
    )
    remaining = rebase._deterministic_prepass(  # pyright: ignore[reportPrivateUsage]
        runner,
        ["vendor/foo.txt"],
        cwd=None,
    )
    assert remaining == ["vendor/foo.txt"]
    assert not any(c[:3] == ("git", "checkout", "--ours") for c in runner.calls)


def test_deterministic_prepass_plugin_json_checkout_ours() -> None:
    path = config.PLUGIN_JSON_PATH
    runner = ScriptRunner(
        [
            (("git", "checkout", "--ours", "--", path), _ok(("git", "checkout", "--ours", "--", path))),
            (("git", "add", path), _ok(("git", "add", path))),
        ],
    )
    remaining = rebase._deterministic_prepass(  # pyright: ignore[reportPrivateUsage]
        runner,
        [path],
        cwd=None,
    )
    assert not remaining
    assert ("git", "checkout", "--ours", "--", path) in runner.calls


def test_waterfall_win_then_rebase_continue(tmp_path: Path) -> None:
    diff_calls = {"n": 0}

    def unmerged_handler(_argv: tuple[str, ...]) -> CommandResult:
        diff_calls["n"] += 1
        if diff_calls["n"] == 1:
            return _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "vendor/foo.txt\n",
            )
        return _ok(("git", "diff", "--name-only", "--diff-filter=U"), "")

    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), unmerged_handler),
            (("git", "rebase", "--continue"), _ok(("git", "rebase", "--continue"))),
        ],
    )

    def launch_fn(tier: str, conflict_csv: str) -> TierAttempt:
        assert conflict_csv == "vendor/foo.txt"
        return TierAttempt(tier, 0, 0, LaunchFailure("none", ""))

    rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
        runner,
        launch_fn,
        repo="o/r",
        run_id="run",
        cwd=str(tmp_path),
    )
    assert ("git", "rebase", "--continue") in runner.calls


def test_continue_with_unmerged_reloops_without_skip() -> None:
    continue_calls = {"n": 0}
    diff_calls = {"n": 0}

    def continue_handler(_argv: tuple[str, ...]) -> CommandResult:
        continue_calls["n"] += 1
        if continue_calls["n"] == 1:
            return _fail(("git", "rebase", "--continue"), "still conflicted")
        return _ok(("git", "rebase", "--continue"))

    def diff_handler(_argv: tuple[str, ...]) -> CommandResult:
        diff_calls["n"] += 1
        if diff_calls["n"] in (1, 3, 4):
            return _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "vendor/a.txt\n",
            )
        return _ok(("git", "diff", "--name-only", "--diff-filter=U"), "")

    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), diff_handler),
            (("git", "rebase", "--continue"), continue_handler),
        ],
    )
    launch_calls: list[str] = []

    def launch_fn(tier: str, conflict_csv: str) -> TierAttempt:
        launch_calls.append(conflict_csv)
        return TierAttempt(tier, 0, 0, LaunchFailure("none", ""))

    rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
        runner,
        launch_fn,
        repo="o/r",
        run_id="run",
        cwd=None,
    )
    assert len(launch_calls) == 2
    assert not any(c[:3] == ("git", "rebase", "--skip") for c in runner.calls)


def test_hook_failure_continue_aborts_and_stalls() -> None:
    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "",
            )),
            (("git", "rebase", "--continue"), _fail(
                ("git", "rebase", "--continue"),
                "pre-commit hook failed",
            )),
            (("git", "rebase", "--abort"), _ok(("git", "rebase", "--abort"))),
        ],
    )
    with pytest.raises(Stalled, match="continue failed"):
        rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
            runner,
            lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
            repo="o/r",
            run_id="run",
            cwd=None,
        )
    assert ("git", "rebase", "--abort") in runner.calls
    assert not any(c[:3] == ("git", "rebase", "--skip") for c in runner.calls)


def test_empty_commit_continue_skips_then_continues() -> None:
    continue_calls = {"n": 0}

    def continue_handler(_argv: tuple[str, ...]) -> CommandResult:
        continue_calls["n"] += 1
        if continue_calls["n"] == 1:
            return _fail(("git", "rebase", "--continue"), "nothing to commit")
        return _ok(("git", "rebase", "--continue"))

    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "",
            )),
            (("git", "rebase", "--continue"), continue_handler),
            (("git", "rebase", "--skip"), _ok(("git", "rebase", "--skip"))),
        ],
    )
    rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
        runner,
        lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
        repo="o/r",
        run_id="run",
        cwd=None,
    )
    assert ("git", "rebase", "--skip") in runner.calls


def test_force_push_plain_lease_single_retry(tmp_path: Path) -> None:
    sleeps: list[float] = []
    push_calls = {"n": 0}

    def push_handler(argv: tuple[str, ...]) -> CommandResult:
        push_calls["n"] += 1
        if push_calls["n"] == 1:
            return _fail(argv)
        return _ok(argv)

    runner = ScriptRunner(
        [
            (("git", "status", "--porcelain"), _ok(("git", "status", "--porcelain"))),
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
            (("git", "fetch", "origin", "feat", "--quiet"), _ok(("git", "fetch", "origin", "feat", "--quiet"))),
            (("git", "push", "--force-with-lease", "origin", "feat"), push_handler),
            (("git", "rev-parse", "HEAD"), _ok(("git", "rev-parse", "HEAD"), "aaa\n")),
            (("git", "rev-parse", "origin/feat"), _ok(("git", "rev-parse", "origin/feat"), "bbb\n")),
        ],
        permissive=False,
    )
    result = rebase._force_push_branch(  # pyright: ignore[reportPrivateUsage]
        runner,
        cwd=str(tmp_path),
        sleep_fn=sleeps.append,
    )
    assert result.returncode == 0
    assert sleeps == [5.0]
    assert push_calls["n"] == 2


def test_version_regression_guard_recomputes_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rebase,
        "_commit_changelog_after_rebump",
        _noop_commit_changelog_after_rebump,
    )
    _write_classify_repo(tmp_path)
    bullets = tmp_path / ".rrr-rebump-bullets.md"
    applied_versions: list[str] = []

    def _patch(runner: ScriptRunner, *, cwd: str | None = None) -> BumpClassification:
        _ = runner, cwd
        return BumpClassification(
            current_version="2.0.0",
            new_version="1.5.0",
            bump_type="PATCH",
            major_reasons=(),
            minor_reasons=(),
            reasoning="",
        )

    def _apply(
        runner: ScriptRunner,
        new_version: str,
        *,
        cwd: str | None = None,
        base_remote: str = "origin",
        base_ref: str = "main",
    ) -> ApplyResult:
        _ = runner, cwd, base_remote, base_ref
        applied_versions.append(new_version)
        return ApplyResult(applied=True, new_version=new_version, commit_sha="sha")

    monkeypatch.setattr(version_bump, "classify_bump", _patch)
    monkeypatch.setattr(version_bump, "apply_bump", _apply)
    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
            (("git", "status", "--porcelain"), _ok(("git", "status", "--porcelain"))),
            (("git", "log", "-1", "--format=%s"), _ok(("git", "log", "-1", "--format=%s"), "work\n")),
            (("git", "fetch", "origin", "main", "--quiet"), _ok(("git", "fetch", "origin", "main", "--quiet"))),
            (("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"), _ok(
                ("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"),
            )),
            (("git", "rev-parse", "main"), _fail(("git", "rev-parse", "main"))),
            (("git", "merge-base", "main", "HEAD"), _fail(("git", "merge-base", "main", "HEAD"))),
            (("git", "merge-base", "origin/main", "HEAD"), _ok(
                ("git", "merge-base", "origin/main", "HEAD"),
                "base\n",
            )),
            (("git", "show", f"origin/main:{config.PLUGIN_JSON_PATH}"), _ok(
                ("git", "show", f"origin/main:{config.PLUGIN_JSON_PATH}"),
                json.dumps({"version": "2.0.0"}),
            )),
            (("git", "status", "--porcelain", "--untracked-files=no"), _ok(
                ("git", "status", "--porcelain", "--untracked-files=no"),
            )),
            (("git", "fetch", "origin", "feat", "--quiet"), _ok(("git", "fetch", "origin", "feat", "--quiet"))),
            (("git", "push", "--force-with-lease", "origin", "feat"), _ok(
                ("git", "push", "--force-with-lease", "origin", "feat"),
            )),
        ],
    )
    result = rebase.rebase_and_rebump(
        runner,
        lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
        repo="o/r",
        run_id="run",
        tmpdir=str(tmp_path),
        bullets_path=bullets,
        cwd=str(tmp_path),
    )
    assert applied_versions == ["2.0.1"]
    assert result.new_version == "2.0.1"


def _rebump_happy_path_handlers(
    *,
    base_remote: str = "origin",
    base_ref: str = "main",
    base_version: str = "1.0.0",
) -> list[
    tuple[
        tuple[str, ...],
        CommandResult | Exception | Callable[[tuple[str, ...]], CommandResult],
    ]
]:
    base_target = f"{base_remote}/{base_ref}"
    return [
        (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
        (("git", "status", "--porcelain"), _ok(("git", "status", "--porcelain"))),
        (("git", "log", "-1", "--format=%s"), _ok(("git", "log", "-1", "--format=%s"), "work\n")),
        (("git", "fetch", base_remote, base_ref, "--quiet"), _ok(
            ("git", "fetch", base_remote, base_ref, "--quiet"),
        )),
        (("git", "merge-base", "--is-ancestor", base_target, "HEAD"), _ok(
            ("git", "merge-base", "--is-ancestor", base_target, "HEAD"),
        )),
        (("git", "rev-parse", "main"), _fail(("git", "rev-parse", "main"))),
        (("git", "merge-base", "main", "HEAD"), _fail(("git", "merge-base", "main", "HEAD"))),
        (("git", "merge-base", base_target, "HEAD"), _ok(
            ("git", "merge-base", base_target, "HEAD"),
            "base\n",
        )),
        (("git", "show", f"{base_target}:{config.PLUGIN_JSON_PATH}"), _ok(
            ("git", "show", f"{base_target}:{config.PLUGIN_JSON_PATH}"),
            json.dumps({"version": base_version}),
        )),
        (("git", "status", "--porcelain", "--untracked-files=no"), _ok(
            ("git", "status", "--porcelain", "--untracked-files=no"),
        )),
        (("git", "fetch", "origin", "feat", "--quiet"), _ok(("git", "fetch", "origin", "feat", "--quiet"))),
        (("git", "push", "--force-with-lease", "origin", "feat"), _ok(
            ("git", "push", "--force-with-lease", "origin", "feat"),
        )),
    ]


def test_defer_push_skips_force_push(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rebase,
        "_commit_changelog_after_rebump",
        _noop_commit_changelog_after_rebump,
    )
    _write_classify_repo(tmp_path)
    bullets = tmp_path / ".rrr-rebump-bullets.md"

    def _patch(runner: ScriptRunner, *, cwd: str | None = None) -> BumpClassification:
        _ = runner, cwd
        return BumpClassification(
            current_version="1.0.0",
            new_version="1.0.1",
            bump_type="PATCH",
            major_reasons=(),
            minor_reasons=(),
            reasoning="",
        )

    def _apply(
        runner: ScriptRunner,
        new_version: str,
        *,
        cwd: str | None = None,
        base_remote: str = "origin",
        base_ref: str = "main",
    ) -> ApplyResult:
        _ = runner, new_version, cwd, base_remote, base_ref
        return ApplyResult(applied=True, new_version="1.0.1", commit_sha="abc")

    monkeypatch.setattr(version_bump, "classify_bump", _patch)
    monkeypatch.setattr(version_bump, "apply_bump", _apply)
    runner = ScriptRunner(_rebump_happy_path_handlers())
    result = rebase.rebase_and_rebump(
        runner,
        lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
        repo="o/r",
        run_id="run",
        tmpdir=str(tmp_path),
        bullets_path=bullets,
        cwd=str(tmp_path),
        defer_push=True,
    )
    assert result.pushed is False
    assert result.new_version == "1.0.1"
    assert not any(
        c[:3] == ("git", "push", "--force-with-lease") for c in runner.calls
    )


def test_has_bump_false_skips_rebump(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_classify_repo(tmp_path)
    bullets = tmp_path / ".rrr-rebump-bullets.md"

    def _forbidden_classify(runner: ScriptRunner, *, cwd: str | None = None) -> BumpClassification:
        _ = runner, cwd
        msg = "classify_bump must not run when has_bump=False"
        raise AssertionError(msg)

    def _forbidden_apply(
        runner: ScriptRunner,
        new_version: str,
        *,
        cwd: str | None = None,
        base_remote: str = "origin",
        base_ref: str = "main",
    ) -> ApplyResult:
        _ = runner, new_version, cwd, base_remote, base_ref
        msg = "apply_bump must not run when has_bump=False"
        raise AssertionError(msg)

    monkeypatch.setattr(version_bump, "classify_bump", _forbidden_classify)
    monkeypatch.setattr(version_bump, "apply_bump", _forbidden_apply)
    runner = ScriptRunner(_rebump_happy_path_handlers())
    result = rebase.rebase_and_rebump(
        runner,
        lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
        repo="o/r",
        run_id="run",
        tmpdir=str(tmp_path),
        bullets_path=bullets,
        cwd=str(tmp_path),
        has_bump=False,
    )
    assert result.new_version is None
    assert result.pushed is True
    assert ("git", "push", "--force-with-lease", "origin", "feat") in runner.calls


def test_has_bump_false_and_defer_push_skips_rebump_and_push(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_classify_repo(tmp_path)
    bullets = tmp_path / ".rrr-rebump-bullets.md"

    def _forbidden_classify(runner: ScriptRunner, *, cwd: str | None = None) -> BumpClassification:
        _ = runner, cwd
        msg = "classify_bump must not run when has_bump=False"
        raise AssertionError(msg)

    def _forbidden_apply(
        runner: ScriptRunner,
        new_version: str,
        *,
        cwd: str | None = None,
        base_remote: str = "origin",
        base_ref: str = "main",
    ) -> ApplyResult:
        _ = runner, new_version, cwd, base_remote, base_ref
        msg = "apply_bump must not run when has_bump=False"
        raise AssertionError(msg)

    monkeypatch.setattr(version_bump, "classify_bump", _forbidden_classify)
    monkeypatch.setattr(version_bump, "apply_bump", _forbidden_apply)
    runner = ScriptRunner(_rebump_happy_path_handlers())
    result = rebase.rebase_and_rebump(
        runner,
        lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
        repo="o/r",
        run_id="run",
        tmpdir=str(tmp_path),
        bullets_path=bullets,
        cwd=str(tmp_path),
        has_bump=False,
        defer_push=True,
    )
    assert result.new_version is None
    assert result.pushed is False
    assert not any(
        c[:3] == ("git", "push", "--force-with-lease") for c in runner.calls
    )


def test_apply_bump_receives_base(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """apply_bump guard uses rebase base_remote/base_ref; classify_bump is mocked."""
    monkeypatch.setattr(
        rebase,
        "_commit_changelog_after_rebump",
        _noop_commit_changelog_after_rebump,
    )
    _write_classify_repo(tmp_path)
    bullets = tmp_path / ".rrr-rebump-bullets.md"

    def _patch(runner: ScriptRunner, *, cwd: str | None = None) -> BumpClassification:
        _ = runner, cwd
        return BumpClassification(
            current_version="1.0.0",
            new_version="1.0.1",
            bump_type="PATCH",
            major_reasons=(),
            minor_reasons=(),
            reasoning="",
        )

    monkeypatch.setattr(version_bump, "classify_bump", _patch)
    runner = ScriptRunner(
        [
            *_rebump_happy_path_handlers(
                base_remote="upstream",
                base_ref="main",
                base_version="1.0.0",
            ),
            (("git", "add", config.PLUGIN_JSON_PATH), _ok(("git", "add", config.PLUGIN_JSON_PATH))),
            (("git", "commit", "-m", "Bump version to 1.0.1"), _ok(
                ("git", "commit", "-m", "Bump version to 1.0.1"),
            )),
            (("git", "rev-parse", "HEAD"), _ok(("git", "rev-parse", "HEAD"), "deadbeef\n")),
            (("git", "reset", "HEAD", config.PLUGIN_JSON_PATH), _ok(
                ("git", "reset", "HEAD", config.PLUGIN_JSON_PATH),
            )),
        ],
    )
    result = rebase.rebase_and_rebump(
        runner,
        lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
        repo="o/r",
        run_id="run",
        tmpdir=str(tmp_path),
        bullets_path=bullets,
        cwd=str(tmp_path),
        base_remote="upstream",
        base_ref="main",
    )
    assert result.new_version == "1.0.1"
    assert ("git", "fetch", "upstream", "main", "--quiet") in runner.calls
    assert (
        "git",
        "show",
        f"upstream/main:{config.PLUGIN_JSON_PATH}",
    ) in runner.calls
    assert not any(
        c[:4] == ("git", "fetch", "origin", "main") for c in runner.calls
    )
    assert not any(
        len(c) >= 3
        and c[0] == "git"
        and c[1] == "show"
        and c[2] == f"origin/main:{config.PLUGIN_JSON_PATH}"
        for c in runner.calls
    )


def test_sync_local_main_on_main_stalls() -> None:
    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(
                ("git", "symbolic-ref", "--short", "HEAD"),
                "main\n",
            )),
        ],
    )
    with pytest.raises(Stalled, match="refusing to update local 'main'"):
        rebase._sync_local_main(  # pyright: ignore[reportPrivateUsage]
            runner,
            base_remote="origin",
            base_ref="main",
            cwd=None,
        )


def test_deterministic_prepass_version_go_and_go_sum() -> None:
    for name in ("version.go", "go.sum"):
        runner = ScriptRunner(
            [
                (("git", "checkout", "--ours", "--", name), _ok(
                    ("git", "checkout", "--ours", "--", name),
                )),
                (("git", "add", name), _ok(("git", "add", name))),
            ],
        )
        remaining = rebase._deterministic_prepass(  # pyright: ignore[reportPrivateUsage]
            runner,
            [name],
            cwd=None,
        )
        assert not remaining
        assert ("git", "checkout", "--ours", "--", name) in runner.calls


def test_drop_bump_stages_bullets_and_calls_drop_changelog(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_classify_repo(tmp_path)
    cl = tmp_path / config.CHANGELOG_DEFAULT_PATH
    _ = cl.write_text(
        "## [1.0.0] - 2020-01-01\n\n- item\n",
        encoding="utf-8",
    )
    bullets = tmp_path / ".rrr-rebump-bullets.md"
    drop_changelog_versions: list[str] = []

    def _drop_bump(
        runner: ScriptRunner,
        **unused: object,
    ) -> DropResult:
        del unused
        _ = runner
        return DropResult(dropped=True, old_sha="bumpsha")

    def _drop_changelog(
        runner: ScriptRunner,
        version: str,
        *,
        max_depth: int = 0,  # pylint: disable=unused-argument
        cwd: str | None = None,
    ) -> DropResult:
        _ = runner, max_depth, cwd
        drop_changelog_versions.append(version)
        return DropResult(dropped=True, old_sha="clsha")

    monkeypatch.setattr(version_bump, "drop_bump_commit", _drop_bump)
    monkeypatch.setattr(changelog, "drop_changelog_commit", _drop_changelog)
    _patch_none_classify(monkeypatch)
    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(
                ("git", "symbolic-ref", "--short", "HEAD"),
                "feat\n",
            )),
            (("git", "status", "--porcelain"), _ok(("git", "status", "--porcelain"))),
            (("git", "log", "-1", "--format=%s", "bumpsha"), _ok(
                ("git", "log", "-1", "--format=%s", "bumpsha"),
                "Bump version to 1.0.0\n",
            )),
            (("git", "fetch", "origin", "main", "--quiet"), _ok(
                ("git", "fetch", "origin", "main", "--quiet",
            ))),
            (("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"), _ok(
                ("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"),
            )),
            (("git", "rev-parse", "main"), _fail(("git", "rev-parse", "main"))),
            (("git", "merge-base", "main", "HEAD"), _fail(("git", "merge-base", "main", "HEAD"))),
            (("git", "merge-base", "origin/main", "HEAD"), _ok(
                ("git", "merge-base", "origin/main", "HEAD"),
                "base\n",
            )),
            (("git", "status", "--porcelain", "--untracked-files=no"), _ok(
                ("git", "status", "--porcelain", "--untracked-files=no"),
            )),
            (("git", "fetch", "origin", "feat", "--quiet"), _ok(
                ("git", "fetch", "origin", "feat", "--quiet",
            ))),
            (("git", "push", "--force-with-lease", "origin", "feat"), _ok(
                ("git", "push", "--force-with-lease", "origin", "feat"),
            )),
        ],
    )
    _ = rebase.rebase_and_rebump(
        runner,
        lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
        repo="o/r",
        run_id="run",
        tmpdir=str(tmp_path),
        bullets_path=bullets,
        cwd=str(tmp_path),
    )
    assert drop_changelog_versions == ["1.0.0"]
    assert "- item" in bullets.read_text(encoding="utf-8")


def test_guarded_drop_changelog_refusal_stalls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_classify_repo(tmp_path)
    cl = tmp_path / config.CHANGELOG_DEFAULT_PATH
    _ = cl.write_text("## [1.0.0] - 2020-01-01\n\n- item\n", encoding="utf-8")
    bullets = tmp_path / ".rrr-rebump-bullets.md"

    def _refuse_drop(
        _runner: ScriptRunner,
        _version: str,
        *,
        max_depth: int = 0,  # pylint: disable=unused-argument
        cwd: str | None = None,
    ) -> DropResult:
        _ = _runner, _version, max_depth, cwd
        return DropResult(dropped=False, error="dirty worktree")

    monkeypatch.setattr(changelog, "drop_changelog_commit", _refuse_drop)
    runner = ScriptRunner([])
    with pytest.raises(Stalled, match="drop-changelog-commit"):
        rebase._stage_rebump_bullets(  # pyright: ignore[reportPrivateUsage]
            runner,
            old_version="1.0.0",
            bullets_path=bullets,
            cwd=str(tmp_path),
        )


def test_commit_changelog_after_rebump_duplicate_heading_stalls(
    tmp_path: Path,
) -> None:
    cl = tmp_path / config.CHANGELOG_DEFAULT_PATH
    _ = cl.write_text(
        "## [1.1.0] - 2020-01-01\n\n## [1.1.0] - 2020-02-01\n",
        encoding="utf-8",
    )
    bullets = tmp_path / "bullets.md"
    _ = bullets.write_text("- new\n", encoding="utf-8")
    runner = ScriptRunner([])
    with pytest.raises(Stalled, match=r"1\.1\.0"):
        rebase._commit_changelog_after_rebump(  # pyright: ignore[reportPrivateUsage]
            runner,
            "1.1.0",
            "1.0.0",
            bullets,
            cwd=str(tmp_path),
        )
    assert not bullets.exists()


def test_commit_changelog_after_rebump_changelog_error_stalls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cl = tmp_path / config.CHANGELOG_DEFAULT_PATH
    _ = cl.write_text("## [1.0.0] - 2020-01-01\n", encoding="utf-8")
    bullets = tmp_path / "bullets.md"
    _ = bullets.write_text("- new\n", encoding="utf-8")

    def _write_raises(*_args: object, **_kwargs: object) -> str:
        raise ChangelogError("no anchor found for changelog entry", code=3)

    monkeypatch.setattr(changelog, "write_changelog_entry", _write_raises)
    runner = ScriptRunner([])
    with pytest.raises(Stalled, match="no anchor"):
        rebase._commit_changelog_after_rebump(  # pyright: ignore[reportPrivateUsage]
            runner,
            "1.1.0",
            "1.0.0",
            bullets,
            cwd=str(tmp_path),
        )
    assert not bullets.exists()


def test_changelog_ready_after_rebump_short_circuits_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cl = tmp_path / config.CHANGELOG_DEFAULT_PATH
    _ = cl.write_text("## [1.1.0] - 2020-01-01\n", encoding="utf-8")
    bullets = tmp_path / "bullets.md"
    commit_called = {"n": 0}

    def _commit(*_args: object, **_kwargs: object) -> changelog.CommitResult:
        commit_called["n"] += 1
        return changelog.CommitResult(committed=False, error="not committed")

    monkeypatch.setattr(changelog, "commit_changelog", _commit)
    runner = ScriptRunner(
        [
            (("git", "status", "--porcelain", "--untracked-files=no"), _ok(
                ("git", "status", "--porcelain", "--untracked-files=no"),
            )),
        ],
    )
    rebase._commit_changelog_after_rebump(  # pyright: ignore[reportPrivateUsage]
        runner,
        "1.1.0",
        "1.0.0",
        bullets,
        cwd=str(tmp_path),
    )
    assert commit_called["n"] == 1
