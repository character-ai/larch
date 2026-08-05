from __future__ import annotations

from pathlib import Path

import pytest

from larch.implement import checks_result_identity as identity
from larch.implement import dispatch_commit_route as route
from test_support import (
    assert_larch_bgjob_adapter_request,
    install_larch_bgjob_adapter_capture,
    make_checks_session,
)


def _session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    return make_checks_session(tmp_path, monkeypatch, bgjob_daemon=route.bgjob_daemon)


def test_parent_seeds_identity_and_forwards_child_arguments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _impl, repo = _session(tmp_path, monkeypatch)
    captured = install_larch_bgjob_adapter_capture(monkeypatch, route.proc)

    assert route.step6_entry_main(["--forked-target", "true"]) == 0

    launch = identity.compute_identity(repo_root=repo)
    command = captured[-1]
    assert_larch_bgjob_adapter_request(
        command,
        step="implement-step6-checks",
        initial_merge_rows=launch.as_rows(),
    )
    assert command[-8:] == (
        "--repo-root", str(repo),
        "--launch-head", launch.head_sha,
        "--launch-fp", launch.tree_fingerprint,
        "--launch-schema", launch.fingerprint_schema,
    )


def test_child_precheck_drift_publishes_integrity_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl, repo = _session(tmp_path, monkeypatch)
    launch = identity.compute_identity(repo_root=repo)
    _ = (repo / "tracked").write_text("drift\n", encoding="utf-8")
    merge = impl / "bgjob" / "implement-step6-checks.merge.env"
    merge.parent.mkdir()

    rc = route.step6_entry_main([
        "--bgjob-child",
        "--merge-result-env", str(merge),
        "--repo-root", str(repo),
        "--launch-head", launch.head_sha,
        "--launch-fp", launch.tree_fingerprint,
        "--launch-schema", launch.fingerprint_schema,
    ])

    assert rc == 1
    assert "NEXT_ACTION=identity-integrity-failed" in merge.read_text(encoding="utf-8")


def test_matching_completed_result_is_reused_without_seed_rewrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl, repo = _session(tmp_path, monkeypatch)
    launch = identity.compute_identity(repo_root=repo)
    bgjob = impl / "bgjob"
    bgjob.mkdir()
    result = bgjob / "implement-step6-checks.result.env"
    rows = [
        ("STEP", "implement-step6-checks"),
        ("BGJOB_RC", "0"),
        ("NEXT_ACTION", "skip-to-7a"),
        *launch.as_rows(),
    ]
    _ = result.write_text("".join(f"{key}={value}\n" for key, value in rows), encoding="utf-8")
    _ = install_larch_bgjob_adapter_capture(monkeypatch, route.proc)

    assert route.step6_entry_main([]) == 0
    assert result.is_file()


def test_stale_completed_result_is_cleared_before_parent_relaunch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl, repo = _session(tmp_path, monkeypatch)
    prior = identity.compute_identity(repo_root=repo)
    bgjob = impl / "bgjob"
    bgjob.mkdir()
    result = bgjob / "implement-step6-checks.result.env"
    merge = bgjob / "implement-step6-checks.merge.env"
    rows = [
        ("STEP", "implement-step6-checks"),
        ("BGJOB_RC", "0"),
        ("NEXT_ACTION", "skip-to-7a"),
        *prior.as_rows(),
    ]
    _ = result.write_text("".join(f"{key}={value}\n" for key, value in rows), encoding="utf-8")
    _ = merge.write_text("stale\n", encoding="utf-8")
    _ = (repo / "tracked").write_text("drift\n", encoding="utf-8")
    captured = install_larch_bgjob_adapter_capture(monkeypatch, route.proc)

    assert route.step6_entry_main([]) == 0
    assert not result.exists()
    assert captured[-1][captured[-1].index("--step") + 1] == "implement-step6-checks"


def test_live_step6_job_reattaches_only_when_its_seed_matches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl, repo = _session(tmp_path, monkeypatch)
    launch = identity.compute_identity(repo_root=repo)
    merge = impl / "bgjob" / "implement-step6-checks.merge.env"
    merge.parent.mkdir()
    _ = merge.write_text("".join(f"{key}={value}\n" for key, value in launch.as_rows()), encoding="utf-8")
    monkeypatch.setattr(route, "_live_registry_entry", lambda **_kwargs: object())  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]

    route._prepare_checks_rejoin(  # pyright: ignore[reportPrivateUsage]
        tmpdir=impl,
        step="implement-step6-checks",
        merge_env=merge,
        identity=launch,
    )

    _ = merge.write_text("CHECKS_INPUT_HEAD_SHA=stale\n", encoding="utf-8")
    with pytest.raises(ValueError, match="live checks job identity mismatch"):
        route._prepare_checks_rejoin(  # pyright: ignore[reportPrivateUsage]
            tmpdir=impl,
            step="implement-step6-checks",
            merge_env=merge,
            identity=launch,
        )


def test_step6_refuses_an_unsafe_completed_result_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl, _repo = _session(tmp_path, monkeypatch)
    result = impl / "bgjob" / "implement-step6-checks.result.env"
    result.parent.mkdir()
    result.mkdir()

    assert route.step6_entry_main([]) == 2
    assert result.is_dir()


def test_step6_child_success_publishes_output_and_identity_together(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl, repo = _session(tmp_path, monkeypatch)
    launch = identity.compute_identity(repo_root=repo)
    merge = impl / "bgjob" / "implement-step6-checks.merge.env"
    merge.parent.mkdir()
    monkeypatch.setattr(route, "_step6_entry_worker", lambda _args, _tmpdir: print("NEXT_ACTION=skip-to-7a") or 0)  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]

    assert route.step6_entry_main([
        "--bgjob-child",
        "--merge-result-env", str(merge),
        "--repo-root", str(repo),
        "--launch-head", launch.head_sha,
        "--launch-fp", launch.tree_fingerprint,
        "--launch-schema", launch.fingerprint_schema,
    ]) == 0

    rows = dict(line.split("=", 1) for line in merge.read_text(encoding="utf-8").splitlines())
    assert rows["NEXT_ACTION"] == "skip-to-7a"
    assert rows["CHECKS_INPUT_HEAD_SHA"] == launch.head_sha
