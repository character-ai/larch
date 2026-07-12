# pyright: reportPrivateUsage=false, reportUnusedCallResult=false
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

from larch.core import proc
from larch.git import gh
from larch.implement import ci_fixer_lane
from larch.implement.ci_fixer_lane import EvidenceState, LaneIdentity

_STEP = "implement-step8-ci-fixer-1-codex-test"
_FINGERPRINT = "c" * 64


def _identity(
    tmp_path: Path,
    *,
    repo_root: Path | None = None,
    starting_head: str = "a" * 40,
    run_id: str = "42",
) -> LaneIdentity:
    handoff = tmp_path / "ci-fixer"
    handoff.mkdir(mode=0o700, exist_ok=True)
    return LaneIdentity(
        mode="ci",
        repo_root=repo_root if repo_root is not None else tmp_path / "repo",
        implement_tmpdir=tmp_path,
        handoff_dir=handoff,
        repo="owner/repo",
        pr=42,
        run_id=run_id,
        tier="codex",
        attempt=1,
        starting_head=starting_head,
        input_fingerprint=_FINGERPRINT,
        step=_STEP,
        result_env=tmp_path / "bgjob" / "x.merge.env",
        invariant_evidence=None,
    )


def _jobs(*names: str) -> tuple[gh.FailedJob, ...]:
    return tuple(gh.FailedJob(name=name, conclusion="failure") for name in names)


def _patch_jobs(monkeypatch: pytest.MonkeyPatch, jobs: tuple[gh.FailedJob, ...], state: str = "ready") -> None:
    def _impl(_runner: object, **_kwargs: object) -> tuple[tuple[gh.FailedJob, ...], str]:
        return jobs, state

    monkeypatch.setattr(ci_fixer_lane.ci_monitor, "read_failed_jobs", _impl)


def test_progress_gate_first_cycle_allows_reship_and_persists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _identity(tmp_path)
    _patch_jobs(monkeypatch, _jobs("python-lint (1)", "python-lint (2)"))

    allow, current = ci_fixer_lane._progress_gate(identity, runner=proc)
    assert allow is True
    assert current is not None
    assert current == frozenset({"python-lint (1)", "python-lint (2)"})
    ci_fixer_lane._persist_signature(identity, current)
    assert ci_fixer_lane._read_prior_signature(identity) == current


def test_progress_gate_repeat_equal_signature_blocks_reship(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _identity(tmp_path)
    ci_fixer_lane._persist_signature(identity, frozenset({"python-lint (1)", "python-lint (2)"}))
    _patch_jobs(monkeypatch, _jobs("python-lint (1)", "python-lint (2)"))

    allow, current = ci_fixer_lane._progress_gate(identity, runner=proc)
    assert allow is False
    assert current == frozenset({"python-lint (1)", "python-lint (2)"})


def test_progress_gate_strict_subset_is_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _identity(tmp_path)
    ci_fixer_lane._persist_signature(
        identity, frozenset({"python-lint (1)", "python-lint (2)", "python-tests (3)"})
    )
    _patch_jobs(monkeypatch, _jobs("python-lint (1)", "python-lint (2)"))

    allow, current = ci_fixer_lane._progress_gate(identity, runner=proc)
    assert allow is True
    assert current == frozenset({"python-lint (1)", "python-lint (2)"})


def test_progress_gate_superset_is_no_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _identity(tmp_path)
    ci_fixer_lane._persist_signature(identity, frozenset({"python-lint (1)"}))
    _patch_jobs(monkeypatch, _jobs("python-lint (1)", "python-tests (2)"))

    allow, _ = ci_fixer_lane._progress_gate(identity, runner=proc)
    assert allow is False


def test_progress_gate_incomparable_is_no_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _identity(tmp_path)
    ci_fixer_lane._persist_signature(identity, frozenset({"python-lint (1)"}))
    _patch_jobs(monkeypatch, _jobs("python-tests (2)"))

    allow, _ = ci_fixer_lane._progress_gate(identity, runner=proc)
    assert allow is False


def test_progress_gate_unavailable_signature_fails_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _identity(tmp_path)
    ci_fixer_lane._persist_signature(identity, frozenset({"python-lint (1)"}))
    _patch_jobs(monkeypatch, (), state="error")

    allow, current = ci_fixer_lane._progress_gate(identity, runner=proc)
    assert allow is True
    assert current is None


def test_progress_gate_read_jobs_exception_fails_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _identity(tmp_path)
    ci_fixer_lane._persist_signature(identity, frozenset({"python-lint (1)"}))

    def _boom(_runner: object, **_kwargs: object) -> tuple[tuple[gh.FailedJob, ...], str]:
        raise OSError("gh unavailable")

    monkeypatch.setattr(ci_fixer_lane.ci_monitor, "read_failed_jobs", _boom)

    allow, current = ci_fixer_lane._progress_gate(identity, runner=proc)
    assert allow is True
    assert current is None


def test_signature_store_roundtrip(tmp_path: Path) -> None:
    identity = _identity(tmp_path)
    assert ci_fixer_lane._read_prior_signature(identity) is None
    signature = frozenset({"python-lint (1)", "python-lint (2)"})
    ci_fixer_lane._persist_signature(identity, signature)
    assert ci_fixer_lane._read_prior_signature(identity) == signature


def test_signature_store_self_heals_on_corruption(tmp_path: Path) -> None:
    identity = _identity(tmp_path)
    ci_fixer_lane._persist_signature(identity, frozenset({"python-lint (1)"}))
    store = ci_fixer_lane._signature_store_path(identity)
    store.write_text("garbage-not-a-signature\n", encoding="utf-8")

    assert ci_fixer_lane._read_prior_signature(identity) is None
    ci_fixer_lane._persist_signature(identity, frozenset({"python-lint (2)"}))
    assert ci_fixer_lane._read_prior_signature(identity) == frozenset({"python-lint (2)"})


def test_signature_store_tampered_digest_returns_none(tmp_path: Path) -> None:
    identity = _identity(tmp_path)
    ci_fixer_lane._persist_signature(identity, frozenset({"python-lint (1)"}))
    store = ci_fixer_lane._signature_store_path(identity)
    store.write_text(f"1\t{'0' * 64}\tpython-lint (1)\n", encoding="utf-8")

    assert ci_fixer_lane._read_prior_signature(identity) is None


def test_signature_store_rejects_symlink(tmp_path: Path) -> None:
    identity = _identity(tmp_path)
    outside = tmp_path.parent / "outside-signature.tsv"
    outside.write_text(f"0\t{'0' * 64}\n", encoding="utf-8")
    store = ci_fixer_lane._signature_store_path(identity)
    store.symlink_to(outside)

    assert ci_fixer_lane._read_prior_signature(identity) is None


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def _seed_repo(repo: Path) -> str:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "fixer-test@example.com")
    _git(repo, "config", "user.name", "fixer-test")
    (repo / "README").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "README")
    _git(repo, "commit", "-q", "-m", "seed")
    return _git(repo, "rev-parse", "HEAD")


def _make_identity(repo: Path, impl: Path, handoff: Path, starting_head: str) -> LaneIdentity:
    return LaneIdentity(
        mode="ci",
        repo_root=repo,
        implement_tmpdir=impl,
        handoff_dir=handoff,
        repo="owner/repo",
        pr=42,
        run_id="42",
        tier="codex",
        attempt=1,
        starting_head=starting_head,
        input_fingerprint=_FINGERPRINT,
        step=_STEP,
        result_env=impl / "bgjob" / "x.merge.env",
        invariant_evidence=None,
    )


def _edit_producing_launcher(repo: Path):
    """A fake launcher that exits clean and leaves an uncommitted working-tree edit."""
    calls = {"n": 0}

    def launch(argv: list[str] | None) -> int:
        assert argv is not None
        output = argv[argv.index("--output") + 1]
        Path(output).with_suffix(Path(output).suffix + ".done").write_text("0\n", encoding="utf-8")
        (repo / "README").write_text(f"fixer attempt {calls['n']}\n", encoding="utf-8")
        calls["n"] += 1
        return 0

    return launch


def test_dispatch_breaks_loop_on_persistent_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    head = _seed_repo(repo)
    impl = tmp_path / "impl"
    impl.mkdir()
    handoff = impl / "ci-fixer"
    handoff.mkdir(mode=0o700)
    (handoff / "distilled-failure.md").write_text(
        "# Distilled CI failure\ncomplexity-baseline FAILED\n", encoding="utf-8"
    )
    evidence = EvidenceState(
        path=handoff / "distilled-failure.md", kind="distilled", digest="d" * 64,
    )
    persistent = _jobs("python-lint (1)", "python-lint (2)")
    _patch_jobs(monkeypatch, persistent)
    launcher = _edit_producing_launcher(repo)

    # Cycle 1: no prior signature -> reship and persist the failing set.
    first = ci_fixer_lane._dispatch(
        _make_identity(repo, impl, handoff, head),
        evidence,
        runner=proc,
        launchers={"codex": launcher},
    )
    assert first.result == "reship"
    assert first.reason == "fixer-produced-uncommitted-change"
    assert first.final_head != head
    assert ci_fixer_lane._read_prior_signature(_make_identity(repo, impl, handoff, head)) == frozenset(
        {"python-lint (1)", "python-lint (2)"}
    )

    # Cycle 2: identical failing set after the reship -> bail instead of reship again.
    second = ci_fixer_lane._dispatch(
        _make_identity(repo, impl, handoff, first.final_head),
        evidence,
        runner=proc,
        launchers={"codex": launcher},
    )
    assert second.result == "operator-bail"
    assert second.reason == "fixer-no-cross-cycle-progress"


def test_dispatch_keeps_reshipping_when_failure_set_shrinks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    head = _seed_repo(repo)
    impl = tmp_path / "impl"
    impl.mkdir()
    handoff = impl / "ci-fixer"
    handoff.mkdir(mode=0o700)
    (handoff / "distilled-failure.md").write_text("# fail\n", encoding="utf-8")
    evidence = EvidenceState(
        path=handoff / "distilled-failure.md", kind="distilled", digest="d" * 64,
    )

    state = {"jobs": _jobs("python-lint (1)", "python-lint (2)", "python-tests (3)")}

    def _read(_runner: object, **_kwargs: object) -> tuple[tuple[gh.FailedJob, ...], str]:
        return state["jobs"], "ready"

    monkeypatch.setattr(ci_fixer_lane.ci_monitor, "read_failed_jobs", _read)
    launcher = _edit_producing_launcher(repo)

    first = ci_fixer_lane._dispatch(
        _make_identity(repo, impl, handoff, head), evidence, runner=proc, launchers={"codex": launcher}
    )
    assert first.result == "reship"

    # The fixer cleared one job: a strict subset is real progress -> reship again.
    state["jobs"] = _jobs("python-lint (1)", "python-lint (2)")
    second = ci_fixer_lane._dispatch(
        _make_identity(repo, impl, handoff, first.final_head),
        evidence,
        runner=proc,
        launchers={"codex": launcher},
    )
    assert second.result == "reship"
    assert ci_fixer_lane._read_prior_signature(
        _make_identity(repo, impl, handoff, first.final_head)
    ) == frozenset({"python-lint (1)", "python-lint (2)"})
