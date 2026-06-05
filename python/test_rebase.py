"""Tests for rebase.py (stub runner + stub launch_fn)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import config
import rebase
from agents import LaunchFailure, TierAttempt
from errors import PrePushConflictHandoff, Stalled, TransientNetworkError
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


def _rebase_happy_path_handlers(
    *,
    base_remote: str = "origin",
    base_ref: str = "main",
) -> list[
    tuple[
        tuple[str, ...],
        CommandResult | Exception | Callable[[tuple[str, ...]], CommandResult],
    ]
]:
    base_target = f"{base_remote}/{base_ref}"
    return [
        (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
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
        (("git", "status", "--porcelain"), _ok(("git", "status", "--porcelain"))),
        (("git", "fetch", "origin", "feat", "--quiet"), _ok(("git", "fetch", "origin", "feat", "--quiet"))),
        (("git", "push", "--force-with-lease", "origin", "feat"), _ok(
            ("git", "push", "--force-with-lease", "origin", "feat"),
        )),
    ]


def test_missing_conflict_launch_dir_stalls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(config.ENV_IMPLEMENT_TMPDIR, raising=False)
    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
        ],
    )
    with pytest.raises(Stalled, match="conflict launch"):
        _ = rebase.rebase_and_push(
            runner,
            repo="o/r",
            run_id="run",
            cwd=str(tmp_path),
        )


def test_attempt_cap_stalls() -> None:
    runner = ScriptRunner([])
    with pytest.raises(Stalled, match="attempt cap"):
        _ = rebase.rebase_and_push(
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
        _ = rebase.rebase_and_push(
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
            (("git", "fetch", "origin", "main", "--quiet"), _fail(
                ("git", "fetch", "origin", "main", "--quiet"),
                "network/auth issue\n",
            )),
            (("git", "rebase", "--abort"), _ok(("git", "rebase", "--abort"))),
        ],
    )
    with pytest.raises(TransientNetworkError):
        _ = rebase.rebase_and_push(
            runner,
            lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
            repo="o/r",
            run_id="run",
            tmpdir=str(tmp_path),
            cwd=str(tmp_path),
        )


def test_already_fresh_skips_rebase(tmp_path: Path) -> None:
    runner = ScriptRunner(_rebase_happy_path_handlers())
    result = rebase.rebase_and_push(
        runner,
        lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
        repo="o/r",
        run_id="run",
        tmpdir=str(tmp_path),
        cwd=str(tmp_path),
    )
    assert result.rebased is False
    assert result.pushed is True
    assert result.new_version is None
    assert not any(c[:3] == ("git", "rebase", "origin/main") for c in runner.calls)


def test_fresh_branch_force_pushes(tmp_path: Path) -> None:
    runner = ScriptRunner(_rebase_happy_path_handlers())
    result = rebase.rebase_and_push(
        runner,
        lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
        repo="o/r",
        run_id="run",
        tmpdir=str(tmp_path),
        cwd=str(tmp_path),
    )
    assert result.new_version is None
    assert result.pushed is True
    assert ("git", "push", "--force-with-lease", "origin", "feat") in runner.calls


def test_waterfall_exhaustion_pre_push_handoff(tmp_path: Path) -> None:
    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
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

    with pytest.raises(PrePushConflictHandoff) as exc_info:
        _ = rebase.rebase_and_push(
            runner,
            launch_fn,
            repo="o/r",
            run_id="run",
            tmpdir=str(tmp_path),
            cwd=str(tmp_path),
            enable_pre_push_handoff=True,
        )
    err = exc_info.value
    assert err.conflict_files == ("vendor/foo.txt",)
    assert err.resume_phase == config.SHIP_PR_RRR_RESUME_PHASE
    assert err.caller_kind == config.SHIP_PR_PRE_PUSH_CALLER_KIND
    assert err.conflict_csv == "vendor/foo.txt"
    assert (tmp_path / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME).is_file()


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


def test_launch_fn_receives_conflict_csv_and_handoff_flag(tmp_path: Path) -> None:
    seen: list[tuple[str, str]] = []

    def launch_fn(tier: str, csv: str) -> TierAttempt:
        seen.append((tier, csv))
        return TierAttempt(tier, 0, 1, LaunchFailure("other", "unknown"))

    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "vendor/x.txt\n",
            )),
        ],
    )
    with pytest.raises(PrePushConflictHandoff) as exc_info:
        rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
            runner,
            launch_fn,
            repo="o/r",
            run_id="run",
            cwd=None,
            tmpdir=str(tmp_path),
            enable_pre_push_handoff=True,
        )
    assert seen
    assert seen[0][1] == "vendor/x.txt"
    assert exc_info.value.conflict_files == ("vendor/x.txt",)
    assert (tmp_path / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME).is_file()


def test_waterfall_exhaustion_without_handoff_enabled_stalls_without_flag(
    tmp_path: Path,
) -> None:
    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "vendor/x.txt\n",
            )),
        ],
    )
    with pytest.raises(Stalled, match="fixer waterfall"):
        rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
            runner,
            lambda tier, _csv: TierAttempt(
                tier,
                wrapper_rc=0,
                launcher_exit=1,
                failure=LaunchFailure("other", "unknown"),
            ),
            repo="o/r",
            run_id="run",
            cwd=None,
            tmpdir=str(tmp_path),
        )
    assert not (tmp_path / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME).exists()


def test_handoff_uses_implement_tmpdir_env_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(tmp_path))
    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "vendor/x.txt\n",
            )),
        ],
    )
    with pytest.raises(PrePushConflictHandoff):
        rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
            runner,
            lambda tier, _csv: TierAttempt(
                tier,
                wrapper_rc=0,
                launcher_exit=1,
                failure=LaunchFailure("other", "unknown"),
            ),
            repo="o/r",
            run_id="run",
            cwd=None,
            tmpdir=None,
            enable_pre_push_handoff=True,
        )
    assert (tmp_path / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME).is_file()


def test_handoff_without_tmpdir_configuration_stalls_without_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(config.ENV_IMPLEMENT_TMPDIR, raising=False)
    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "vendor/x.txt\n",
            )),
        ],
    )
    with pytest.raises(Stalled, match="handoff flag tmpdir"):
        rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
            runner,
            lambda tier, _csv: TierAttempt(
                tier,
                wrapper_rc=0,
                launcher_exit=1,
                failure=LaunchFailure("other", "unknown"),
            ),
            repo="o/r",
            run_id="run",
            cwd=None,
            tmpdir=None,
            enable_pre_push_handoff=True,
        )


def test_bump_only_waterfall_exhaustion_stalls_without_handoff_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(config.ENV_LARCH_VERSION_FILES, "pkg/version.txt")
    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "pkg/version.txt\n",
            )),
        ],
    )

    with pytest.raises(Stalled, match="fixer waterfall"):
        rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
            runner,
            lambda tier, _csv: TierAttempt(
                tier,
                wrapper_rc=0,
                launcher_exit=1,
                failure=LaunchFailure("other", "unknown"),
            ),
            repo="o/r",
            run_id="run",
            cwd=str(tmp_path),
            tmpdir=str(tmp_path),
            enable_pre_push_handoff=True,
        )
    assert not (tmp_path / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME).exists()


@pytest.mark.parametrize(
    "path",
    [
        config.PLUGIN_JSON_PATH,
        "nested/.claude-plugin/plugin.json",
        "version.go",
        "go.sum",
    ],
)
def test_bump_path_classes_disable_handoff(path: str) -> None:
    assert rebase._is_bump_path(path)  # pyright: ignore[reportPrivateUsage]
    assert not rebase._conflicts_are_non_bump_only((path,))  # pyright: ignore[reportPrivateUsage]


def test_larch_version_files_is_canonical_for_bump_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(config.ENV_LARCH_VERSION_FILES, "pkg/version.txt")
    monkeypatch.setenv(config.ENV_LARCH_BUMP_FILES, "vendor/not-version.txt")
    assert rebase._is_bump_path("pkg/version.txt")  # pyright: ignore[reportPrivateUsage]
    assert not rebase._is_bump_path("vendor/not-version.txt")  # pyright: ignore[reportPrivateUsage]
    assert not rebase._conflicts_are_non_bump_only(("pkg/version.txt",))  # pyright: ignore[reportPrivateUsage]


def test_larch_bump_files_legacy_alias_when_version_files_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(config.ENV_LARCH_VERSION_FILES, raising=False)
    monkeypatch.setenv(config.ENV_LARCH_BUMP_FILES, "pkg/legacy-version.txt")
    assert rebase._is_bump_path("pkg/legacy-version.txt")  # pyright: ignore[reportPrivateUsage]


def test_mixed_bump_waterfall_exhaustion_stalls_without_handoff_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(config.ENV_LARCH_BUMP_FILES, "pkg/version.txt")
    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "vendor/foo.txt\npkg/version.txt\n",
            )),
        ],
    )

    with pytest.raises(Stalled, match="fixer waterfall"):
        rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
            runner,
            lambda tier, _csv: TierAttempt(
                tier,
                wrapper_rc=0,
                launcher_exit=1,
                failure=LaunchFailure("other", "unknown"),
            ),
            repo="o/r",
            run_id="run",
            cwd=str(tmp_path),
            tmpdir=str(tmp_path),
            enable_pre_push_handoff=True,
        )
    assert not (tmp_path / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME).exists()


def test_changelog_conflict_is_non_bump_for_handoff() -> None:
    assert not rebase._is_bump_path("CHANGELOG.md")  # pyright: ignore[reportPrivateUsage]
    assert rebase._conflicts_are_non_bump_only(("CHANGELOG.md",))  # pyright: ignore[reportPrivateUsage]


def test_waterfall_win_with_remaining_conflicts_stalls_without_handoff_flag(
    tmp_path: Path,
) -> None:
    diff_calls = {"n": 0}

    def unmerged_handler(_argv: tuple[str, ...]) -> CommandResult:
        diff_calls["n"] += 1
        return _ok(
            ("git", "diff", "--name-only", "--diff-filter=U"),
            "vendor/foo.txt\n",
        )

    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), unmerged_handler),
        ],
    )

    with pytest.raises(Stalled, match="conflicts remain"):
        rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
            runner,
            lambda tier, _csv: TierAttempt(
                tier,
                wrapper_rc=0,
                launcher_exit=0,
                failure=LaunchFailure("none", ""),
            ),
            repo="o/r",
            run_id="run",
            cwd=str(tmp_path),
            tmpdir=str(tmp_path),
        )
    assert diff_calls["n"] >= 2
    assert not (tmp_path / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME).exists()


def test_unresolvable_handoff_dir_stalls_without_handoff_tokens(tmp_path: Path) -> None:
    missing_tmpdir = tmp_path / "missing"
    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "vendor/foo.txt\n",
            )),
        ],
    )

    with pytest.raises(Stalled, match="cannot write"):
        rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
            runner,
            lambda tier, _csv: TierAttempt(
                tier,
                wrapper_rc=0,
                launcher_exit=1,
                failure=LaunchFailure("other", "unknown"),
            ),
            repo="o/r",
            run_id="run",
            cwd=str(tmp_path),
            tmpdir=str(missing_tmpdir),
            enable_pre_push_handoff=True,
        )
    assert not (
        missing_tmpdir / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME
    ).exists()


def test_non_conflict_rebase_aborts_and_stalls(tmp_path: Path) -> None:
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
        _ = rebase.rebase_and_push(
            runner,
            lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
            repo="o/r",
            run_id="run",
            tmpdir=str(tmp_path),
            cwd=str(tmp_path),
        )
    assert ("git", "rebase", "--abort") in runner.calls


def test_fetch_non_transient_stalls_and_aborts_active_rebase(tmp_path: Path) -> None:
    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
            (("git", "fetch", "origin", "main", "--quiet"), _fail(
                ("git", "fetch", "origin", "main", "--quiet"),
                "repository not found\n",
            )),
        ],
    )
    with pytest.raises(Stalled, match="fetch failed"):
        _ = rebase.rebase_and_push(
            runner,
            lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
            repo="o/r",
            run_id="run",
            tmpdir=str(tmp_path),
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
        tmpdir=str(tmp_path),
        enable_pre_push_handoff=True,
    )
    assert ("git", "rebase", "--continue") in runner.calls
    assert not (tmp_path / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME).exists()


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


def test_defer_push_skips_force_push(tmp_path: Path) -> None:
    runner = ScriptRunner(_rebase_happy_path_handlers())
    result = rebase.rebase_and_push(
        runner,
        lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
        repo="o/r",
        run_id="run",
        tmpdir=str(tmp_path),
        cwd=str(tmp_path),
        defer_push=True,
    )
    assert result.pushed is False
    assert result.new_version is None
    assert not any(
        c[:3] == ("git", "push", "--force-with-lease") for c in runner.calls
    )


def test_rebase_uses_custom_base_remote(tmp_path: Path) -> None:
    runner = ScriptRunner(
        _rebase_happy_path_handlers(base_remote="upstream", base_ref="main"),
    )
    result = rebase.rebase_and_push(
        runner,
        lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
        repo="o/r",
        run_id="run",
        tmpdir=str(tmp_path),
        cwd=str(tmp_path),
        base_remote="upstream",
        base_ref="main",
    )
    assert result.new_version is None
    assert ("git", "fetch", "upstream", "main", "--quiet") in runner.calls
    assert not any(
        c[:4] == ("git", "fetch", "origin", "main") for c in runner.calls
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
