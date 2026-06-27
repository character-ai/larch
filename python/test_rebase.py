"""Tests for rebase.py (stub runner + stub launch_fn)."""

from __future__ import annotations

# pyright: reportPrivateUsage=false, reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from larch.core import config
from larch.git import rebase
from larch.agents.agents import LaunchFailure, TierAttempt
from larch.errors import PrePushConflictHandoff, Stalled, TransientNetworkError
from larch.core.proc import CommandResult


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
            runner=runner,
            repo="o/r",
            run_id="run",
            cwd=str(tmp_path),
        )


def test_attempt_cap_stalls() -> None:
    runner = ScriptRunner([])
    with pytest.raises(Stalled, match="attempt cap"):
        _ = rebase.rebase_and_push(
            runner=runner,
            launch_fn=lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
            repo="o/r",
            run_id="run",
            tmpdir="/tmp",
            rebase_attempt=config.REBASE_MAX_ATTEMPTS,
        )


def test_conflict_launch_missing_metadata_uses_wrapper_rc(tmp_path: Path) -> None:
    runner = ScriptRunner(
        [
            ((rebase.agents.sys.executable,), _fail((rebase.agents.sys.executable,), code=7)),
        ],
    )
    launch_fn = rebase.make_conflict_launch_fn(
        runner=runner,
        repo="o/r",
        run_id="run-1",
        output_dir=tmp_path,
    )
    attempt = launch_fn("claude", "conflicted.txt")
    assert attempt.wrapper_rc == 7
    assert attempt.launcher_exit == 7


def test_conflict_launch_captured_launcher_exit_wins_over_wrapper_rc(
    tmp_path: Path,
) -> None:
    runner = ScriptRunner(
        [
            (
                (rebase.agents.sys.executable,),
                _fail(
                    (rebase.agents.sys.executable,),
                    stderr="LAUNCHER_EXIT=1\n",
                    code=5,
                ),
            ),
        ],
    )
    launch_fn = rebase.make_conflict_launch_fn(
        runner=runner,
        repo="o/r",
        run_id="run-1",
        output_dir=tmp_path,
    )
    attempt = launch_fn("claude", "conflicted.txt")
    assert attempt.wrapper_rc == 5
    assert attempt.launcher_exit == 1


def test_conflict_launch_done_sidecar_wins_over_wrapper_success(tmp_path: Path) -> None:
    class DoneRunner(ScriptRunner):
        def run(self, argv: Sequence[str], **_kwargs: object) -> CommandResult:
            output = Path(argv[argv.index("--output") + 1])
            _ = output.write_text("tool output\n", encoding="utf-8")
            _ = output.with_suffix(output.suffix + ".done").write_text("4\n", encoding="utf-8")
            self.calls.append(tuple(argv))
            return _ok(argv)

    launch_fn = rebase.make_conflict_launch_fn(
        runner=DoneRunner([]),
        repo="o/r",
        run_id="run-1",
        output_dir=tmp_path,
    )
    attempt = launch_fn("claude", "conflicted.txt")
    assert attempt.wrapper_rc == 0
    assert attempt.launcher_exit == 4


def test_detached_head_stalls() -> None:
    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _fail(("git", "symbolic-ref", "--short", "HEAD"))),
        ],
    )
    with pytest.raises(Stalled, match="detached"):
        _ = rebase.rebase_and_push(
            runner=runner,
            launch_fn=lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
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
            runner=runner,
            launch_fn=lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
            repo="o/r",
            run_id="run",
            tmpdir=str(tmp_path),
            cwd=str(tmp_path),
        )


def test_already_fresh_skips_rebase(tmp_path: Path) -> None:
    runner = ScriptRunner(_rebase_happy_path_handlers())
    result = rebase.rebase_and_push(
        runner=runner,
        launch_fn=lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
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
        runner=runner,
        launch_fn=lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
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
            runner=runner,
            launch_fn=launch_fn,
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
            runner=runner,
            launch_fn=launch_fn,
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
    with pytest.raises(Stalled, match=r"fixer|first fixer"):
        rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
            runner=runner,
            launch_fn=lambda tier, _csv: TierAttempt(
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


def test_partial_success_waterfall_triggers_handoff(tmp_path: Path) -> None:
    """Winning tier + residual unmerged paths raises PrePushConflictHandoff when enabled."""
    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "README.md\n",
            )),
        ],
    )
    with pytest.raises(PrePushConflictHandoff) as exc_info:
        rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
            runner=runner,
            launch_fn=lambda tier, _csv: TierAttempt(
                tier,
                wrapper_rc=0,
                launcher_exit=0,
                failure=LaunchFailure("none", ""),
            ),
            repo="o/r",
            run_id="run",
            cwd=None,
            tmpdir=str(tmp_path),
            enable_pre_push_handoff=True,
        )
    assert exc_info.value.conflict_files == ("README.md",)
    assert (tmp_path / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME).is_file()


def test_partial_success_waterfall_without_handoff_stalls(tmp_path: Path) -> None:
    """Winning tier + residual unmerged paths raises Stalled when handoff is disabled."""
    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "README.md\n",
            )),
        ],
    )
    with pytest.raises(Stalled, match=r"conflicts|fixer waterfall"):
        rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
            runner=runner,
            launch_fn=lambda tier, _csv: TierAttempt(
                tier,
                wrapper_rc=0,
                launcher_exit=0,
                failure=LaunchFailure("none", ""),
            ),
            repo="o/r",
            run_id="run",
            cwd=None,
            tmpdir=str(tmp_path),
        )
    assert not (tmp_path / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME).exists()


def test_conflict_fixer_forbidden_path_reverts_and_stalls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "README.md\n",
            )),
        ],
    )

    def fake_forbidden_paths(_runner: object, *, cwd: str | None = None) -> tuple[str, ...]:
        _ = cwd
        return (".gitmodules",)

    def fake_revert_forbidden(
        _runner: object,
        *,
        cwd: str | None,
        forbidden: tuple[str, ...],
        baseline_staged: tuple[str, ...] = (),
    ) -> int:
        _ = cwd, forbidden, baseline_staged
        return 1

    monkeypatch.setattr(rebase.coder_delta_guards, "coder_forbidden_paths", fake_forbidden_paths)
    monkeypatch.setattr(rebase.coder_delta_guards, "revert_forbidden_paths", fake_revert_forbidden)

    with pytest.raises(Stalled, match="conflict fixer touched forbidden path"):
        rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
            runner=runner,
            launch_fn=lambda tier, _csv: TierAttempt(
                tier,
                wrapper_rc=0,
                launcher_exit=0,
                failure=LaunchFailure("none", ""),
            ),
            repo="o/r",
            run_id="run",
            cwd=None,
            tmpdir=str(tmp_path),
            enable_pre_push_handoff=True,
        )
    assert ("git", "restore", "--staged", "--", "README.md") in runner.calls
    assert ("git", "checkout", "--merge", "--", "README.md") in runner.calls
    assert not (tmp_path / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME).exists()


def test_conflict_forbidden_snapshot_is_prelaunch_and_not_recomputed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diff_calls = {"n": 0}
    events: list[str] = []

    def unmerged_handler(_argv: tuple[str, ...]) -> CommandResult:
        diff_calls["n"] += 1
        if diff_calls["n"] == 1:
            return _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "README.md\n",
            )
        return _ok(("git", "diff", "--name-only", "--diff-filter=U"), "")

    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), unmerged_handler),
            (("git", "rebase", "--continue"), _ok(("git", "rebase", "--continue"))),
        ],
    )

    def fake_forbidden_paths(_runner: object, *, cwd: str | None = None) -> tuple[str, ...]:
        _ = cwd
        events.append("snapshot")
        return ("frozen-path",)

    def fake_revert_forbidden(
        _runner: object,
        *,
        cwd: str | None,
        forbidden: tuple[str, ...],
        baseline_staged: tuple[str, ...] = (),
    ) -> int:
        _ = cwd, baseline_staged
        events.append(f"revert:{','.join(forbidden)}")
        return 0

    def launch_fn(tier: str, _csv: str) -> TierAttempt:
        events.append(f"launch:{tier}")
        return TierAttempt(tier, 0, 0, LaunchFailure("none", ""))

    monkeypatch.setattr(rebase.coder_delta_guards, "coder_forbidden_paths", fake_forbidden_paths)
    monkeypatch.setattr(rebase.coder_delta_guards, "revert_forbidden_paths", fake_revert_forbidden)

    rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
        runner=runner,
        launch_fn=launch_fn,
        repo="o/r",
        run_id="run",
        cwd=str(tmp_path),
        tmpdir=str(tmp_path),
    )
    assert events == ["snapshot", "launch:claude", "revert:frozen-path"]


@pytest.mark.skip(reason="agentic conflict loop removes bump prepass")
def test_partial_success_waterfall_bump_only_stalls_without_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Winning tier + residual retired version-file conflicts raises Stalled without handoff flag."""
    # pylint: disable=no-member
    monkeypatch.setenv(config.VERSION_ENV_RETIRED, "pkg/version.txt")
    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "pkg/version.txt\n",
            )),
        ],
    )
    with pytest.raises(Stalled, match=r"conflicts|fixer waterfall"):
        rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
            runner=runner,
            launch_fn=lambda tier, _csv: TierAttempt(
                tier,
                wrapper_rc=0,
                launcher_exit=0,
                failure=LaunchFailure("none", ""),
            ),
            repo="o/r",
            run_id="run",
            cwd=str(tmp_path),
            tmpdir=str(tmp_path),
            enable_pre_push_handoff=True,
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
            runner=runner,
            launch_fn=lambda tier, _csv: TierAttempt(
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
            runner=runner,
            launch_fn=lambda tier, _csv: TierAttempt(
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


@pytest.mark.skip(reason="agentic conflict loop removes bump prepass")
def test_bump_only_waterfall_exhaustion_stalls_without_handoff_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # pylint: disable=no-member
    monkeypatch.setenv(config.VERSION_ENV_RETIRED, "pkg/version.txt")
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
            runner=runner,
            launch_fn=lambda tier, _csv: TierAttempt(
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
@pytest.mark.skip(reason="agentic conflict loop removes bump prepass")
def test_bump_path_classes_disable_handoff(path: str) -> None:
    # pylint: disable=no-member
    assert rebase._retired_is_version_path(path)  # pyright: ignore[reportPrivateUsage]
    assert not rebase._retired_conflicts_are_ordinary_only((path,))  # pyright: ignore[reportPrivateUsage]


@pytest.mark.skip(reason="agentic conflict loop removes bump prepass")
def test_larch_version_files_is_canonical_for_bump_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # pylint: disable=no-member
    monkeypatch.setenv(config.VERSION_ENV_RETIRED, "pkg/version.txt")
    monkeypatch.setenv(config.BUMP_ENV_RETIRED, "vendor/not-version.txt")
    assert rebase._retired_is_version_path("pkg/version.txt")  # pyright: ignore[reportPrivateUsage]
    assert not rebase._retired_is_version_path("vendor/not-version.txt")  # pyright: ignore[reportPrivateUsage]
    assert not rebase._retired_conflicts_are_ordinary_only(("pkg/version.txt",))  # pyright: ignore[reportPrivateUsage]


def test_rebase_push_conflict_returns_exit_1(tmp_path: Path) -> None:
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
                "README.md\n",
            )),
        ],
        permissive=False,
    )
    result = rebase.rebase_push(runner, cwd=str(tmp_path))
    assert result.exit_code == 1
    assert result.conflict_files == "README.md"


def test_rebase_push_force_push_same_ref_recovery(tmp_path: Path) -> None:
    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
            (("git", "fetch", "origin", "main", "--quiet"), _ok(("git", "fetch", "origin", "main", "--quiet"))),
            (("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"), _fail(
                ("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"),
            )),
            (("git", "rebase", "origin/main"), _ok(("git", "rebase", "origin/main"))),
            (("git", "config", "--get", "branch.feat.pushRemote"), _ok(("git", "config"), "")),
            (("git", "config", "--get", "branch.feat.remote"), _ok(("git", "config"), "")),
            (("git", "fetch", "origin", "feat", "--quiet"), _ok(("git", "fetch", "origin", "feat", "--quiet"))),
            (("git", "rev-parse", "origin/feat"), _ok(("git", "rev-parse", "origin/feat"), "abc\n")),
            (("git", "ls-remote", "--heads", "origin", "refs/heads/feat"), _ok(
                ("git", "ls-remote", "--heads", "origin", "refs/heads/feat"),
                "",
            )),
            (("git", "push", "--force-with-lease=refs/heads/feat:abc"), _fail(
                ("git", "push", "--force-with-lease=refs/heads/feat:abc"),
            )),
            (("git", "fetch", "origin", "feat", "--quiet"), _ok(("git", "fetch", "origin", "feat", "--quiet"))),
            (("git", "rev-parse", "HEAD"), _ok(("git", "rev-parse", "HEAD"), "abc\n")),
            (("git", "rev-parse", "origin/feat"), _ok(("git", "rev-parse", "origin/feat"), "abc\n")),
        ],
        permissive=False,
    )
    result = rebase.rebase_push(runner, cwd=str(tmp_path))
    assert result.exit_code == 0


def test_rebase_push_retries_transient_fetch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "TRANSIENT_RETRY_BACKOFF_SEC", (0, 0))
    fetch_calls = 0

    def fetch_once_then_ok(argv: tuple[str, ...]) -> CommandResult:
        nonlocal fetch_calls
        fetch_calls += 1
        if fetch_calls == 1:
            return _fail(argv, "fatal: Could not resolve host")
        return _ok(argv)

    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
            (("git", "fetch", "origin", "main", "--quiet"), fetch_once_then_ok),
            (("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"), _ok(
                ("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"),
            )),
        ],
        permissive=False,
    )
    result = rebase.rebase_push(runner, no_push=True, cwd=str(tmp_path))
    assert result.exit_code == 0
    assert fetch_calls == 2


def test_rebase_push_retries_skip_if_pushed_ls_remote(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "TRANSIENT_RETRY_BACKOFF_SEC", (0, 0))
    probe_calls = 0

    def ls_remote_once_then_ok(argv: tuple[str, ...]) -> CommandResult:
        nonlocal probe_calls
        probe_calls += 1
        if probe_calls == 1:
            return _fail(argv, "fatal: Could not resolve host")
        return _ok(argv, "abc\trefs/heads/feat\n")

    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
            (("git", "ls-remote", "--heads", "origin", "refs/heads/feat"), ls_remote_once_then_ok),
        ],
        permissive=False,
    )
    result = rebase.rebase_push(runner, skip_if_pushed=True, no_push=True, cwd=str(tmp_path))
    assert result.exit_code == 0
    assert result.skipped_already_pushed
    assert probe_calls == 2


def test_rebase_push_retries_transient_force_push(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "TRANSIENT_RETRY_BACKOFF_SEC", (0, 0))
    push_calls = 0

    def push_once_then_ok(argv: tuple[str, ...]) -> CommandResult:
        nonlocal push_calls
        push_calls += 1
        if push_calls == 1:
            return _fail(argv, "fatal: Could not resolve host")
        return _ok(argv)

    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(("git", "symbolic-ref", "--short", "HEAD"), "feat\n")),
            (("git", "fetch", "origin", "main", "--quiet"), _ok(("git", "fetch", "origin", "main", "--quiet"))),
            (("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"), _fail(
                ("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"),
            )),
            (("git", "rebase", "origin/main"), _ok(("git", "rebase", "origin/main"))),
            (("git", "config", "--get", "branch.feat.pushRemote"), _ok(("git", "config"), "")),
            (("git", "config", "--get", "branch.feat.remote"), _ok(("git", "config"), "")),
            (("git", "fetch", "origin", "feat", "--quiet"), _ok(("git", "fetch", "origin", "feat", "--quiet"))),
            (("git", "rev-parse", "origin/feat"), _ok(("git", "rev-parse", "origin/feat"), "abc\n")),
            (("git", "push", "--force-with-lease=refs/heads/feat:abc"), push_once_then_ok),
        ],
        permissive=False,
    )
    result = rebase.rebase_push(runner, cwd=str(tmp_path))
    assert result.exit_code == 0
    assert push_calls == 2


def test_rebase_push_invalid_flag_combo_exit_3() -> None:
    runner = ScriptRunner([], permissive=True)
    result = rebase.rebase_push(runner, skip_if_pushed=True, no_push=False)
    assert result.exit_code == 3
    assert "only valid with --no-push" in result.rebase_error


@pytest.mark.skip(reason="agentic conflict loop removes bump prepass")
def test_larch_bump_files_legacy_alias_when_version_files_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # pylint: disable=no-member
    monkeypatch.delenv(config.VERSION_ENV_RETIRED, raising=False)
    monkeypatch.setenv(config.BUMP_ENV_RETIRED, "pkg/legacy-version.txt")
    assert rebase._retired_is_version_path("pkg/legacy-version.txt")  # pyright: ignore[reportPrivateUsage]


@pytest.mark.skip(reason="agentic conflict loop removes bump prepass")
def test_mixed_bump_waterfall_exhaustion_stalls_without_handoff_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # pylint: disable=no-member
    monkeypatch.setenv(config.BUMP_ENV_RETIRED, "pkg/version.txt")
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
            runner=runner,
            launch_fn=lambda tier, _csv: TierAttempt(
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


@pytest.mark.skip(reason="agentic conflict loop removes bump prepass")
def test_changelog_conflict_is_non_bump_for_handoff() -> None:
    # pylint: disable=no-member
    assert not rebase._retired_is_version_path("CHANGELOG.md")  # pyright: ignore[reportPrivateUsage]
    assert rebase._retired_conflicts_are_ordinary_only(("CHANGELOG.md",))  # pyright: ignore[reportPrivateUsage]


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

    with pytest.raises(Stalled, match=r"conflicts|fixer waterfall"):
        rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
            runner=runner,
            launch_fn=lambda tier, _csv: TierAttempt(
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
            runner=runner,
            launch_fn=lambda tier, _csv: TierAttempt(
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
            runner=runner,
            launch_fn=lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
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
            runner=runner,
            launch_fn=lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
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
            runner=runner,
            launch_fn=lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
            repo="o/r",
            run_id="run",
            cwd=None,
        )


def test_make_conflict_launch_fn_argv(tmp_path: Path) -> None:
    out_dir = tmp_path / "launch"
    runner = ScriptRunner([], permissive=True)
    launch_fn = rebase.make_conflict_launch_fn(
        runner=runner,
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
        runner: ScriptRunner,
        tier: str,
        **kwargs: object,
    ) -> CommandResult:
        _ = runner, tier, kwargs
        return CommandResult(("launch",), 0, "LAUNCHER_EXIT=1\n", "", 0.01)

    monkeypatch.setattr(rebase.agents, "launch_tier", _launch_stdout)
    launch_fn = rebase.make_conflict_launch_fn(
        runner=runner,
        repo="owner/repo",
        run_id="run-42",
        output_dir=out_dir,
        cwd=str(tmp_path),
    )
    attempt = launch_fn("cursor", "a.txt")
    assert attempt.launcher_exit == 1


@pytest.mark.parametrize("tier", ["codex", "cursor"])
def test_make_conflict_launch_fn_ingests_external_token_sidecar(
    tier: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_dir = tmp_path / "launch"
    runner = ScriptRunner([], permissive=True)
    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(tmp_path))
    ingest_calls: list[dict[str, object]] = []

    def _launch_stdout(
        runner: ScriptRunner,
        tier: str,
        **kwargs: object,
    ) -> CommandResult:
        _ = runner, kwargs
        return CommandResult(("launch",), 0, f"LAUNCHER_EXIT=0\nTOKEN_RECORD={out_dir / f'{tier}.token-record'}\n", "", 0.01)

    def fake_ingest(_runner: ScriptRunner, **kwargs: object) -> bool:
        ingest_calls.append(kwargs)
        return True

    monkeypatch.setattr(rebase.agents, "launch_tier", _launch_stdout)
    monkeypatch.setattr(rebase.agents, "ingest_launcher_token_sidecar", fake_ingest)
    launch_fn = rebase.make_conflict_launch_fn(
        runner=runner,
        repo="owner/repo",
        run_id="run-42",
        output_dir=out_dir,
        cwd=str(tmp_path),
    )
    attempt = launch_fn(tier, "a.txt")
    assert attempt.launcher_exit == 0
    assert len(ingest_calls) == 1
    assert ingest_calls[0]["tmpdir"] == str(tmp_path)
    assert ingest_calls[0]["implement_tmpdir"] == str(tmp_path)
    assert isinstance(ingest_calls[0]["seen"], set)
    assert ingest_calls[0]["cwd"] == str(tmp_path)
    assert ingest_calls[0]["allow_output_fallback"] is True


def test_make_conflict_launch_fn_clears_stale_fallback_sidecar_before_ingest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_dir = tmp_path / "launch"
    out_dir.mkdir()
    fallback = out_dir / "conflict-cursor.out.token-record"
    _ = fallback.write_text("stale\n", encoding="utf-8")
    runner = ScriptRunner([], permissive=True)
    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(tmp_path))
    freshness_checks: list[bool] = []

    def _launch_stdout(
        runner: ScriptRunner,
        tier: str,
        **kwargs: object,
    ) -> CommandResult:
        _ = runner, tier, kwargs
        freshness_checks.append(not fallback.exists())
        return CommandResult(("launch",), 0, "LAUNCHER_EXIT=0\n", "", 0.01)

    def fake_ingest(_runner: ScriptRunner, **kwargs: object) -> bool:
        assert kwargs["allow_output_fallback"] is True
        freshness_checks.append(not fallback.exists())
        return False

    monkeypatch.setattr(rebase.agents, "launch_tier", _launch_stdout)
    monkeypatch.setattr(rebase.agents, "ingest_launcher_token_sidecar", fake_ingest)
    launch_fn = rebase.make_conflict_launch_fn(
        runner=runner,
        repo="owner/repo",
        run_id="run-42",
        output_dir=out_dir,
        cwd=str(tmp_path),
    )

    attempt = launch_fn("cursor", "a.txt")

    assert attempt.launcher_exit == 0
    assert freshness_checks == [True, True]


def test_make_conflict_launch_fn_ingests_output_fallback_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_dir = tmp_path / "launch"
    runner = ScriptRunner([], permissive=True)
    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(tmp_path))

    def _launch_stdout(
        runner: ScriptRunner,
        tier: str,
        **kwargs: object,
    ) -> CommandResult:
        _ = runner, tier, kwargs
        output = Path(str(kwargs["output"]))
        _ = Path(f"{output}.token-record").write_text(
            "TOOL=cursor\nINPUT=1\nOUTPUT=2\nTOTAL=3\nRAW=cursor_ci_fix\n",
            encoding="utf-8",
        )
        return CommandResult(("launch",), 0, "LAUNCHER_EXIT=0\n", "", 0.01)

    def _ingest_run(
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> CommandResult:
        _ = timeout, cwd, env, check, stdout, stderr
        key = tuple(argv)
        runner.calls.append(key)
        return CommandResult(key, 0, "", "", 0.01)

    monkeypatch.setattr(runner, "run", _ingest_run)
    monkeypatch.setattr(rebase.agents, "launch_tier", _launch_stdout)
    launch_fn = rebase.make_conflict_launch_fn(
        runner=runner,
        repo="owner/repo",
        run_id="run-42",
        output_dir=out_dir,
        cwd=str(tmp_path),
    )

    attempt = launch_fn("cursor", "a.txt")

    assert attempt.launcher_exit == 0
    ingested_inputs = [call[call.index("--input") + 1] for call in runner.calls if "--input" in call]
    assert ingested_inputs == [str(out_dir / "conflict-cursor.out.token-record")] * 2


def test_make_conflict_launch_fn_retries_only_missing_token_sidecar_leg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_dir = tmp_path / "launch"
    sidecar = out_dir / "cursor.token-record"
    sidecar.parent.mkdir(parents=True)
    _ = sidecar.write_text("TOOL=cursor\nINPUT=1\nOUTPUT=2\nTOTAL=3\nRAW=cursor_ci_fix\n", encoding="utf-8")
    runner = ScriptRunner([], permissive=True)
    runner_returncodes = [0, 3, 0]
    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(tmp_path))

    def _launch_stdout(
        runner: ScriptRunner,
        tier: str,
        **kwargs: object,
    ) -> CommandResult:
        _ = runner, tier, kwargs
        return CommandResult(("launch",), 0, f"LAUNCHER_EXIT=0\nTOKEN_RECORD={sidecar}\n", "", 0.01)

    def _ingest_run(
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> CommandResult:
        _ = timeout, cwd, env, check, stdout, stderr
        key = tuple(argv)
        runner.calls.append(key)
        rc = runner_returncodes.pop(0) if runner_returncodes else 0
        return CommandResult(key, rc, "", "", 0.01)

    monkeypatch.setattr(runner, "run", _ingest_run)
    monkeypatch.setattr(rebase.agents, "launch_tier", _launch_stdout)
    launch_fn = rebase.make_conflict_launch_fn(
        runner=runner,
        repo="owner/repo",
        run_id="run-42",
        output_dir=out_dir,
        cwd=str(tmp_path),
    )

    _ = launch_fn("cursor", "a.txt")
    _ = launch_fn("cursor", "a.txt")

    verbs = [call[3] for call in runner.calls]
    assert verbs == ["append-record", "record-vendor-sidecar", "record-vendor-sidecar"]


@pytest.mark.skip(reason="agentic conflict loop removes bump prepass")
def test_retired_prepass_no_retired_checkout_ours_on_vendor() -> None:
    # pylint: disable=no-member
    runner = ScriptRunner(
        [
            (("git", "checkout", "--ours", "--", "vendor/foo.txt"), _fail(
                ("git", "checkout", "--ours", "--", "vendor/foo.txt"),
            )),
        ],
    )
    remaining = rebase._retired_prepass(  # pyright: ignore[reportPrivateUsage]
        runner,
        ["vendor/foo.txt"],
        cwd=None,
    )
    assert remaining == ["vendor/foo.txt"]
    assert not any(c[:3] == ("git", "checkout", "--ours") for c in runner.calls)


@pytest.mark.skip(reason="agentic conflict loop removes bump prepass")
def test_retired_prepass_plugin_json_retired_checkout_ours() -> None:
    # pylint: disable=no-member
    path = config.PLUGIN_JSON_PATH
    runner = ScriptRunner(
        [
            (("git", "checkout", "--ours", "--", path), _ok(("git", "checkout", "--ours", "--", path))),
            (("git", "add", path), _ok(("git", "add", path))),
        ],
    )
    remaining = rebase._retired_prepass(  # pyright: ignore[reportPrivateUsage]
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
        runner=runner,
        launch_fn=launch_fn,
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
        runner=runner,
        launch_fn=launch_fn,
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
            runner=runner,
            launch_fn=lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
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
        runner=runner,
        launch_fn=lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
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
        runner=runner,
        launch_fn=lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
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
        runner=runner,
        launch_fn=lambda _t, _c: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
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


@pytest.mark.skip(reason="agentic conflict loop removes bump prepass")
def test_retired_prepass_version_go_and_go_sum() -> None:
    # pylint: disable=no-member
    for name in ("version.go", "go.sum"):
        runner = ScriptRunner(
            [
                (("git", "checkout", "--ours", "--", name), _ok(
                    ("git", "checkout", "--ours", "--", name),
                )),
                (("git", "add", name), _ok(("git", "add", name))),
            ],
        )
        remaining = rebase._retired_prepass(  # pyright: ignore[reportPrivateUsage]
            runner,
            [name],
            cwd=None,
        )
        assert not remaining
        assert ("git", "checkout", "--ours", "--", name) in runner.calls

def test_sync_local_main_missing_remote_non_main_noops() -> None:
    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(
                ("git", "symbolic-ref", "--short", "HEAD"),
                "feature\n",
            )),
            (("git", "rev-parse", "main"), _ok(("git", "rev-parse", "main"), "local\n")),
            (("git", "rev-parse", "origin/main"), _fail(("git", "rev-parse", "origin/main"))),
        ],
    )
    rebase._sync_local_main(  # pyright: ignore[reportPrivateUsage]
        runner,
        base_remote="origin",
        base_ref="main",
        cwd=None,
    )
    assert not any(call[:3] == ("git", "branch", "-f") for call in runner.calls)


def test_sync_local_main_missing_remote_on_main_stalls() -> None:
    runner = ScriptRunner(
        [
            (("git", "symbolic-ref", "--short", "HEAD"), _ok(
                ("git", "symbolic-ref", "--short", "HEAD"),
                "main\n",
            )),
            (("git", "rev-parse", "main"), _ok(("git", "rev-parse", "main"), "local\n")),
            (("git", "branch", "-f", "main", "origin/main"), _fail(
                ("git", "branch", "-f", "main", "origin/main"),
                "fatal: cannot force update the branch 'main' checked out",
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


def test_failed_tier_skips_blind_staging(tmp_path: Path) -> None:
    conflict_dir = tmp_path / "vendor"
    conflict_dir.mkdir()
    conflict_file = conflict_dir / "foo.txt"
    _ = conflict_file.write_text("<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> branch\n", encoding="utf-8")
    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "vendor/foo.txt\n",
            )),
        ],
    )
    with pytest.raises(Stalled, match=r"fixer|first fixer"):
        rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
            runner=runner,
            launch_fn=lambda tier, _csv: TierAttempt(
                tier,
                wrapper_rc=1,
                launcher_exit=1,
                failure=LaunchFailure("other", "unknown"),
            ),
            repo="o/r",
            run_id="run",
            cwd=str(tmp_path),
            tmpdir=str(tmp_path),
        )
    assert not any(call[:3] == ("git", "add") for call in runner.calls)


def test_success_tier_stages_marker_free_conflict_file(tmp_path: Path) -> None:
    conflict_dir = tmp_path / "vendor"
    conflict_dir.mkdir()
    conflict_file = conflict_dir / "foo.txt"
    _ = conflict_file.write_text("resolved content\n", encoding="utf-8")
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
        runner=runner,
        launch_fn=launch_fn,
        repo="o/r",
        run_id="run",
        cwd=str(tmp_path),
        tmpdir=str(tmp_path),
    )
    assert ("git", "add", "--", "vendor/foo.txt") in runner.calls
    assert ("git", "rebase", "--continue") in runner.calls


def test_effective_failure_class_reads_launcher_capture_envelope(tmp_path: Path) -> None:
    capture = tmp_path / "conflict-claude.fail.log"
    _ = capture.write_text("LAUNCHER_FAILURE_CLASS=health\n", encoding="utf-8")
    attempt = TierAttempt(
        tier="claude",
        wrapper_rc=0,
        launcher_exit=127,
        failure=LaunchFailure("other", "unknown"),
        failure_log=capture,
    )
    assert rebase.agents.effective_failure_class(attempt) == "health"


def test_effective_failure_class_falls_back_without_launcher_kv(tmp_path: Path) -> None:
    capture = tmp_path / "conflict-claude.fail.log"
    _ = capture.write_text("ordinary launcher output\n", encoding="utf-8")
    attempt = TierAttempt(
        tier="claude",
        wrapper_rc=0,
        launcher_exit=1,
        failure=LaunchFailure("other", "parse"),
        failure_log=capture,
    )
    assert rebase.agents.effective_failure_class(attempt) == "health"


def test_conflict_loop_continues_when_log_missing_failure_class_kv(
    tmp_path: Path,
) -> None:
    log_file = tmp_path / "conflict-claude.fail.log"
    _ = log_file.write_text("ordinary launcher output\n", encoding="utf-8")
    launch_calls: list[str] = []
    conflict_dir = tmp_path / "vendor"
    conflict_dir.mkdir()
    _ = (conflict_dir / "foo.txt").write_text("resolved content\n", encoding="utf-8")
    diff_calls = {"n": 0}

    def unmerged_handler(_argv: tuple[str, ...]) -> CommandResult:
        diff_calls["n"] += 1
        if diff_calls["n"] == 1:
            return _ok(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                "vendor/foo.txt\n",
            )
        return _ok(("git", "diff", "--name-only", "--diff-filter=U"), "")

    def launch_fn(tier: str, _csv: str) -> TierAttempt:
        launch_calls.append(tier)
        if tier == config.FIXER_TIER_ORDER[-1]:
            return TierAttempt(
                tier,
                wrapper_rc=0,
                launcher_exit=0,
                failure=LaunchFailure("none", ""),
            )
        return TierAttempt(
            tier,
            wrapper_rc=0,
            launcher_exit=1,
            failure=LaunchFailure("health", "health-probe"),
            failure_log=log_file,
        )

    runner = ScriptRunner(
        [
            (("git", "diff", "--name-only", "--diff-filter=U"), unmerged_handler),
            (("git", "rebase", "--continue"), _ok(("git", "rebase", "--continue"))),
        ],
    )
    rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
        runner=runner,
        launch_fn=launch_fn,
        repo="o/r",
        run_id="run",
        cwd=str(tmp_path),
        tmpdir=str(tmp_path),
    )
    assert launch_calls == list(config.FIXER_TIER_ORDER)


def test_conflict_loop_health_failure_continues_to_next_tier(tmp_path: Path) -> None:
    log_file = tmp_path / "conflict-claude.fail.log"
    _ = log_file.write_text("LAUNCHER_FAILURE_CLASS=health\n", encoding="utf-8")
    launch_calls: list[str] = []

    def launch_fn(tier: str, _csv: str) -> TierAttempt:
        launch_calls.append(tier)
        if tier == config.FIXER_TIER_ORDER[-1]:
            return TierAttempt(
                tier,
                wrapper_rc=0,
                launcher_exit=0,
                failure=LaunchFailure("none", ""),
            )
        return TierAttempt(
            tier,
            wrapper_rc=0,
            launcher_exit=1,
            failure=LaunchFailure("health", "binary-missing"),
            failure_log=log_file,
        )

    conflict_dir = tmp_path / "vendor"
    conflict_dir.mkdir()
    _ = (conflict_dir / "foo.txt").write_text("resolved content\n", encoding="utf-8")
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
    rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
        runner=runner,
        launch_fn=launch_fn,
        repo="o/r",
        run_id="run",
        cwd=str(tmp_path),
        tmpdir=str(tmp_path),
    )
    assert launch_calls == list(config.FIXER_TIER_ORDER)


def test_path_has_conflict_markers_detects_any_marker_line(tmp_path: Path) -> None:
    conflict_file = tmp_path / "partial.txt"
    _ = conflict_file.write_text("resolved top\n=======\nresolved bottom\n", encoding="utf-8")
    assert rebase._path_has_conflict_markers("partial.txt", cwd=str(tmp_path))  # pyright: ignore[reportPrivateUsage]
    _ = conflict_file.write_text("<<<<<<< ours\n", encoding="utf-8")
    assert rebase._path_has_conflict_markers("partial.txt", cwd=str(tmp_path))  # pyright: ignore[reportPrivateUsage]
    _ = conflict_file.write_text("<<<<<<< ours\n=======\n>>>>>>> theirs\n", encoding="utf-8")
    assert rebase._path_has_conflict_markers("partial.txt", cwd=str(tmp_path))  # pyright: ignore[reportPrivateUsage]
    _ = conflict_file.write_text("resolved content\n", encoding="utf-8")
    assert not rebase._path_has_conflict_markers("partial.txt", cwd=str(tmp_path))  # pyright: ignore[reportPrivateUsage]


def test_partial_conflict_markers_are_not_staged(tmp_path: Path) -> None:
    conflict_dir = tmp_path / "vendor"
    conflict_dir.mkdir()
    conflict_file = conflict_dir / "foo.txt"
    _ = conflict_file.write_text("resolved top\n=======\n", encoding="utf-8")
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
            (("git", "add", "vendor/foo.txt"), _ok(("git", "add"), "")),
            (("git", "rebase", "--continue"), _ok(("git", "rebase", "--continue"), "")),
        ],
    )
    with pytest.raises(Stalled):
        rebase._resolve_conflicts(  # pyright: ignore[reportPrivateUsage]
            runner=runner,
            launch_fn=lambda tier, _csv: TierAttempt(tier, 0, 0, LaunchFailure("none", "")),
            repo="o/r",
            run_id="run",
            cwd=str(tmp_path),
            tmpdir=str(tmp_path),
        )
    assert not any(
        call[:2] == ("git", "add") and "vendor/foo.txt" in call
        for call in runner.calls
    )
