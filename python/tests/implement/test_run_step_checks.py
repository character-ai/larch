from __future__ import annotations

import types
from pathlib import Path

import pytest

from larch.implement import dispatch_commit_route as route
from test_support import install_larch_bgjob_adapter_capture, make_checks_session


def _session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    return make_checks_session(tmp_path, monkeypatch, bgjob_model=route.bgjob_model)


def test_checks_step_for_site_budgets() -> None:
    assert route._checks_step_for_site("step3") == ("implement-step3-checks", 15600)  # pyright: ignore[reportPrivateUsage]
    assert route._checks_step_for_site("step5-self-review") == (  # pyright: ignore[reportPrivateUsage]
        "implement-checks-step5-self-review",
        14700,
    )
    assert route._checks_step_for_site("step6")[1] == 10800  # pyright: ignore[reportPrivateUsage]


def test_bgjob_spec_uses_parent_pid_when_claude_pid_is_unset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_owner_pids: list[str | None] = []
    monkeypatch.delenv("LARCH_CLAUDE_PID", raising=False)
    monkeypatch.setattr(route.os, "getppid", lambda: 456)
    monkeypatch.setattr(
        route.bgjob_model,
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
        route.bgjob_model,
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


def test_relay_scope_coverage_passes_none_manifest_when_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """claude_fallback / --self-implement runs have no manifest.json by design."""
    impl, repo = _session(tmp_path, monkeypatch)
    _ = (impl / "plan.txt").write_text("plan\n", encoding="utf-8")
    _ = (impl / "step2-baseline.txt").write_text("BASE\n", encoding="utf-8")
    _ = (impl / "repo-root.txt").write_text(f"{repo}\n", encoding="utf-8")
    assert not (impl / "manifest.json").exists()

    seen: list[tuple[str, object]] = []

    def fake_compute(*, tmpdir: Path, manifest_path: object, **_: object) -> object:
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

    def fake_invalidate(*, manifest_path: object, **_: object) -> object:
        seen.append(("invalidate", manifest_path))
        return types.SimpleNamespace(reason="")

    monkeypatch.setattr(route.scope_disposition, "compute_and_write_coverage", fake_compute)
    monkeypatch.setattr(route.scope_disposition, "invalidate_stale_disposition", fake_invalidate)

    assert route._relay_scope_coverage(impl) == 0  # pyright: ignore[reportPrivateUsage]
    assert ("compute", None) in seen
    assert ("invalidate", None) in seen


def test_bgjob_adapter_capture_helper_still_works(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _impl, _repo = _session(tmp_path, monkeypatch)
    captured = install_larch_bgjob_adapter_capture(monkeypatch, route.proc)
    spec = route._bgjob_spec(route.BgjobRequest(  # pyright: ignore[reportPrivateUsage]
        tmpdir=_impl,
        step="implement-step3-checks",
        budget_s=15600,
        verb="step-6-entry",
        public_args=("--site", "step6"),
        merge_result_env=_impl / "bgjob" / "implement-step3-checks.merge.env",
    ))
    assert route._run_adapter(spec) == 0  # pyright: ignore[reportPrivateUsage]
    assert captured
    assert captured[-1][captured[-1].index("--budget-s") + 1] == "15600"
