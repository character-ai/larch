from __future__ import annotations

import subprocess
import os
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from larch.implement import checks_result_identity as identity
from larch.implement import dispatch_commit_route as route

if TYPE_CHECKING:
    from larch.bgjob import model


def _capture_spec(captured: list[model.JobSpec]) -> Callable[[model.JobSpec], int]:
    def fake_start(spec: model.JobSpec) -> int:
        captured.append(spec)
        return 0

    return fake_start


def _git(repo: Path, *args: str) -> None:
    _ = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _ = (repo / "tracked").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "tracked")
    _git(repo, "commit", "-m", "base")
    impl = tmp_path / "impl"
    impl.mkdir()
    _ = (impl / "session-env.sh").write_text(f"REPO_ROOT={repo.resolve()}\n", encoding="utf-8")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[3]))
    monkeypatch.setenv("LARCH_CLAUDE_PID", str(os.getpid()))
    monkeypatch.setattr(route.bgjob_daemon, "owner_identity_from_env", lambda _pid: object())  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    return impl, repo.resolve()


def test_step3_composite_preserves_site_budget_and_flags(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _impl, repo = _session(tmp_path, monkeypatch)
    captured: list[model.JobSpec] = []
    monkeypatch.setattr(route.bgjob_adapt, "start_or_reattach", _capture_spec(captured))

    assert route.run_step_checks_main([
        "--site", "step3",
        "--commit-site", "step4",
        "--rebase-checkpoint-4r",
        "--forked-target", "true",
    ]) == 0

    spec = captured[0]
    launch = identity.compute_identity(repo_root=repo)
    assert spec.step == "implement-step3-checks"
    assert spec.budget_s == 15600
    assert spec.initial_merge_rows == tuple(launch.as_rows())
    assert "--commit-site" in spec.command
    assert "--rebase-checkpoint-4r" in spec.command


def test_self_review_uses_distinct_step_and_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = _session(tmp_path, monkeypatch)
    captured: list[model.JobSpec] = []
    monkeypatch.setattr(route.bgjob_adapt, "start_or_reattach", _capture_spec(captured))

    assert route.run_step_checks_main(["--site", "step5-self-review"]) == 0
    assert captured[0].step == "implement-checks-step5-self-review"
    assert captured[0].budget_s == 14700


def test_bgjob_spec_uses_parent_pid_when_claude_pid_is_unset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_owner_pids: list[str | None] = []
    monkeypatch.delenv("LARCH_CLAUDE_PID", raising=False)
    monkeypatch.setattr(route.os, "getppid", lambda: 456)
    monkeypatch.setattr(
        route.bgjob_daemon,
        "owner_identity_from_env",
        lambda pid: captured_owner_pids.append(pid) or object(),  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    )

    _ = route._bgjob_spec(route.BgjobRequest(  # pyright: ignore[reportPrivateUsage]
        tmpdir=tmp_path,
        step="implement-step3-checks",
        budget_s=1,
        verb="run-step-checks",
        public_args=(),
        merge_result_env=tmp_path / "result.env",
    ))

    assert captured_owner_pids == ["456"]


def test_bgjob_spec_propagates_stale_claude_owner_capture_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LARCH_CLAUDE_PID", "stale")
    monkeypatch.setattr(
        route.bgjob_daemon,
        "owner_identity_from_env",
        lambda _pid: (_ for _ in ()).throw(RuntimeError("stale owner")),  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    )

    with pytest.raises(RuntimeError, match="stale owner"):
        _ = route._bgjob_spec(route.BgjobRequest(  # pyright: ignore[reportPrivateUsage]
            tmpdir=tmp_path,
            step="implement-step3-checks",
            budget_s=1,
            verb="run-step-checks",
            public_args=(),
            merge_result_env=tmp_path / "result.env",
        ))


def test_child_requires_complete_launch_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl, _repo = _session(tmp_path, monkeypatch)
    merge = impl / "bgjob" / "implement-step3-checks.merge.env"
    merge.parent.mkdir()

    assert route.run_step_checks_main([
        "--site", "step3",
        "--bgjob-child",
        "--merge-result-env", str(merge),
    ]) == 2
