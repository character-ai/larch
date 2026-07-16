from __future__ import annotations

import types
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from larch.implement import checks_result_identity as identity
from larch.implement import dispatch_commit_route as route
from test_support import capture_start as _capture_spec
from test_support import make_checks_session

if TYPE_CHECKING:
    from larch.bgjob import model


def _session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    return make_checks_session(tmp_path, monkeypatch, bgjob_daemon=route.bgjob_daemon)


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


def test_relay_scope_coverage_passes_none_manifest_when_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """claude_fallback / --self-implement runs have no manifest.json by design.

    The scope relay must pass manifest_path=None when no manifest is present so
    resolve_implement_manifest searches and returns None instead of raising on
    an explicit missing path (issue #7197).
    """
    impl, repo = _session(tmp_path, monkeypatch)
    _ = (impl / "plan.txt").write_text("plan\n", encoding="utf-8")
    _ = (impl / "step2-baseline.txt").write_text("BASE\n", encoding="utf-8")
    _ = (impl / "repo-root.txt").write_text(f"{repo}\n", encoding="utf-8")
    assert not (impl / "manifest.json").exists()

    seen: list[tuple[str, object]] = []

    def fake_compute(
        *, tmpdir: Path, manifest_path: object, **_: object
    ) -> object:
        seen.append(("compute", manifest_path))
        return types.SimpleNamespace(
            total=0,
            touched=0,
            untouched=0,
            untouched_percent=0,
            band="advisory",
            coverage_file=str(tmpdir / "plan-coverage.json"),
            untouched_file="",
            todos_left_count=0,
            todos_file="",
            disposition_required=False,
            plan_fidelity_forced=False,
        )

    def fake_invalidate(
        *, manifest_path: object, **_: object
    ) -> object:
        seen.append(("invalidate", manifest_path))
        return types.SimpleNamespace(reason="")

    monkeypatch.setattr(route.scope_disposition, "compute_and_write_coverage", fake_compute)
    monkeypatch.setattr(route.scope_disposition, "invalidate_stale_disposition", fake_invalidate)

    assert route._relay_scope_coverage(impl) == 0  # pyright: ignore[reportPrivateUsage]
    assert ("compute", None) in seen
    assert ("invalidate", None) in seen


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
