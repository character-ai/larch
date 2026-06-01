"""Tests for rebase.py (stub runner + stub launch_fn)."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import agents
import config
import rebase
import version_bump
from agents import LaunchFailure, TierAttempt
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
    launch_calls = [c for c in runner.calls if any("launch-cursor-ci.sh" in p for p in c)]
    assert launch_calls
    argv = launch_calls[0]
    assert argv[argv.index("--role") + 1] == config.FIXER_ROLE
    assert argv[argv.index("--conflict-files") + 1] == "a.txt,b.txt"
    assert argv[argv.index("--run-id") + 1] == "run-42"
    assert argv[argv.index("--repo") + 1] == "owner/repo"


def test_rebase_result_uses_apply_result_new_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rebase,
        "_commit_changelog_after_rebump",
        lambda *_a, **_k: None,
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
    ) -> ApplyResult:
        _ = runner, cwd
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
    assert remaining == []
    assert ("git", "checkout", "--ours", "--", path) in runner.calls


def test_waterfall_win_then_rebase_continue(tmp_path: Path) -> None:
    bullets = tmp_path / ".rrr-rebump-bullets.md"
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
        lambda *_a, **_k: None,
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
    ) -> ApplyResult:
        _ = runner, cwd
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
