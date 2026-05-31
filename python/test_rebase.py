"""Tests for rebase.py (stub runner + stub launch_fn)."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import config
import rebase
import version_bump
from agents import LaunchFailure, TierAttempt
from version_bump import BumpClassification
from errors import NeedsUserInput, Stalled, TransientNetworkError
from proc import CommandResult


def _empty_argv_log() -> list[tuple[str, ...]]:
    return []


@dataclass
class ScriptRunner:
    """Runner that matches argv by prefix; defaults to success when permissive."""

    handlers: list[tuple[tuple[str, ...], CommandResult | Exception]]
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
