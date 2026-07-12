from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from larch.implement import checks_result_identity as identity
from larch.implement import dispatch_commit_route as route

if TYPE_CHECKING:
    import pytest

    from larch.bgjob import model


def _capture_spec(captured: list[model.JobSpec]) -> Callable[[model.JobSpec], int]:
    def fake_start(spec: model.JobSpec) -> int:
        captured.append(spec)
        return 0

    return fake_start


def _start_ok(_spec: model.JobSpec) -> int:
    return 0


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
    monkeypatch.delenv("LARCH_CLAUDE_PID", raising=False)
    return impl, repo.resolve()


def test_parent_seeds_identity_and_forwards_child_arguments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _impl, repo = _session(tmp_path, monkeypatch)
    captured: list[model.JobSpec] = []
    monkeypatch.setattr(route.bgjob_adapt, "start_or_reattach", _capture_spec(captured))

    assert route.step6_entry_main(["--forked-target", "true"]) == 0

    launch = identity.compute_identity(repo_root=repo)
    spec = captured[0]
    assert spec.step == "implement-step6-checks"
    assert spec.initial_merge_rows == tuple(launch.as_rows())
    assert spec.command[-8:] == (
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
    monkeypatch.setattr(route.bgjob_adapt, "start_or_reattach", _start_ok)

    assert route.step6_entry_main([]) == 0
    assert result.is_file()
