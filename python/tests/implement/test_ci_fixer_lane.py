# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnusedCallResult=false, reportPrivateUsage=false
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

from larch.core import proc
from larch.git import gh
from larch.implement import ci_fixer_lane, ci_monitor
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


def _no_fixable(_jobs: tuple[gh.FailedJob, ...]) -> ci_monitor.ClassifiedJobs:
    return ci_monitor.ClassifiedJobs(0, (), (), ())


# --- _edit_verdict: signature-gate path (no locally-reproducible failing jobs) ---


def test_edit_verdict_first_cycle_allows_reship_and_persists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _identity(tmp_path)
    monkeypatch.setattr(ci_fixer_lane.ci_monitor, "classify_failed_jobs", _no_fixable)
    jobs = _jobs("deploy-aws (1)", "deploy-gcp (1)")  # not in CI_FIXABLE_JOBS

    should_reship, signature, reason = ci_fixer_lane._edit_verdict(
        identity, runner=proc, jobs=jobs
    )
    assert should_reship is True
    assert signature is not None
    assert signature == frozenset({"deploy-aws (1)", "deploy-gcp (1)"})
    assert reason == ""
    ci_fixer_lane._persist_signature(identity, signature)
    assert ci_fixer_lane._read_prior_signature(identity) == signature


def test_edit_verdict_repeat_equal_signature_blocks_reship(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _identity(tmp_path)
    ci_fixer_lane._persist_signature(identity, frozenset({"deploy-aws (1)", "deploy-gcp (1)"}))
    monkeypatch.setattr(ci_fixer_lane.ci_monitor, "classify_failed_jobs", _no_fixable)

    should_reship, signature, reason = ci_fixer_lane._edit_verdict(
        identity, runner=proc, jobs=_jobs("deploy-aws (1)", "deploy-gcp (1)")
    )
    assert should_reship is False
    assert signature is None
    assert reason == "fixer-no-cross-cycle-progress"


def test_edit_verdict_strict_subset_is_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _identity(tmp_path)
    ci_fixer_lane._persist_signature(
        identity, frozenset({"deploy-aws (1)", "deploy-gcp (1)", "deploy-azure (1)"})
    )
    monkeypatch.setattr(ci_fixer_lane.ci_monitor, "classify_failed_jobs", _no_fixable)

    should_reship, signature, _ = ci_fixer_lane._edit_verdict(
        identity, runner=proc, jobs=_jobs("deploy-aws (1)", "deploy-gcp (1)")
    )
    assert should_reship is True
    assert signature == frozenset({"deploy-aws (1)", "deploy-gcp (1)"})


def test_edit_verdict_superset_is_no_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _identity(tmp_path)
    ci_fixer_lane._persist_signature(identity, frozenset({"deploy-aws (1)"}))
    monkeypatch.setattr(ci_fixer_lane.ci_monitor, "classify_failed_jobs", _no_fixable)

    should_reship, _, _ = ci_fixer_lane._edit_verdict(
        identity, runner=proc, jobs=_jobs("deploy-aws (1)", "deploy-gcp (1)")
    )
    assert should_reship is False


def test_edit_verdict_jobs_unavailable_fails_open(
    tmp_path: Path,
) -> None:
    identity = _identity(tmp_path)
    ci_fixer_lane._persist_signature(identity, frozenset({"deploy-aws (1)"}))

    should_reship, signature, reason = ci_fixer_lane._edit_verdict(
        identity, runner=proc, jobs=None
    )
    assert should_reship is True
    assert signature is None
    assert reason == ""


# --- _edit_verdict / _locally_validates: local re-validation path ---


def _fixable_classify(_jobs: tuple[gh.FailedJob, ...]) -> ci_monitor.ClassifiedJobs:
    row = ci_monitor.JobClass(name="python-lint", shard="1", klass="fixable")
    return ci_monitor.ClassifiedJobs(1, (row,), (row,), ())


def test_locally_validates_none_when_no_fixable_jobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ci_fixer_lane.ci_monitor, "classify_failed_jobs", _no_fixable)
    assert ci_fixer_lane._locally_validates(
        proc, _jobs("deploy-aws (1)"), cwd=str(tmp_path)
    ) is None


def test_locally_validates_true_when_all_fixable_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ci_fixer_lane.ci_monitor, "classify_failed_jobs", _fixable_classify)
    monkeypatch.setattr(
        ci_fixer_lane.ci_monitor, "verify_job_locally",
        lambda **_kwargs: True,
    )
    assert ci_fixer_lane._locally_validates(
        proc, _jobs("python-lint (1)"), cwd=str(tmp_path)
    ) is True


def test_locally_validates_false_when_a_fixable_job_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ci_fixer_lane.ci_monitor, "classify_failed_jobs", _fixable_classify)
    monkeypatch.setattr(
        ci_fixer_lane.ci_monitor, "verify_job_locally",
        lambda **_kwargs: False,
    )
    assert ci_fixer_lane._locally_validates(
        proc, _jobs("python-lint (1)"), cwd=str(tmp_path)
    ) is False


def test_edit_verdict_local_validation_pass_reships(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _identity(tmp_path)
    monkeypatch.setattr(ci_fixer_lane.ci_monitor, "classify_failed_jobs", _fixable_classify)
    monkeypatch.setattr(ci_fixer_lane.ci_monitor, "verify_job_locally", lambda **_kwargs: True)

    should_reship, signature, reason = ci_fixer_lane._edit_verdict(
        identity, runner=proc, jobs=_jobs("python-lint (1)")
    )
    assert should_reship is True
    assert signature == frozenset({"python-lint (1)"})
    assert reason == ""


def test_edit_verdict_local_validation_fail_advances_tier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _identity(tmp_path)
    monkeypatch.setattr(ci_fixer_lane.ci_monitor, "classify_failed_jobs", _fixable_classify)
    monkeypatch.setattr(ci_fixer_lane.ci_monitor, "verify_job_locally", lambda **_kwargs: False)

    should_reship, signature, reason = ci_fixer_lane._edit_verdict(
        identity, runner=proc, jobs=_jobs("python-lint (1)")
    )
    assert should_reship is False
    assert signature is None
    assert reason == "fixer-edit-fails-local-validation"


# --- signature store ---


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


# --- _reset_fixer_delta ---


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


def test_reset_fixer_delta_restores_modified_and_removes_created(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    head = _seed_repo(repo)
    impl = tmp_path / "impl"
    impl.mkdir()
    handoff = impl / "ci-fixer"
    handoff.mkdir(mode=0o700)
    identity = LaneIdentity(
        mode="ci", repo_root=repo, implement_tmpdir=impl, handoff_dir=handoff,
        repo="owner/repo", pr=42, run_id="42", tier="codex", attempt=1,
        starting_head=head, input_fingerprint=_FINGERPRINT, step=_STEP,
        result_env=impl / "bgjob" / "x.merge.env", invariant_evidence=None,
    )
    # Fixer modified a tracked file and created a new file.
    (repo / "README").write_text("fixer changed this\n", encoding="utf-8")
    (repo / "newfile.txt").write_text("fixer created this\n", encoding="utf-8")
    delta = ci_fixer_lane._salvage_delta(identity, runner=proc, baseline={})
    assert sorted(delta) == ["README", "newfile.txt"]

    ci_fixer_lane._reset_fixer_delta(identity, runner=proc, delta=delta)

    assert (repo / "README").read_text(encoding="utf-8") == "seed\n"
    assert not (repo / "newfile.txt").exists()
    assert _git(repo, "status", "--porcelain") == ""


# --- _dispatch integration ---


def _make_identity(repo: Path, impl: Path, handoff: Path, starting_head: str) -> LaneIdentity:
    return LaneIdentity(
        mode="ci", repo_root=repo, implement_tmpdir=impl, handoff_dir=handoff,
        repo="owner/repo", pr=42, run_id="42", tier="codex", attempt=1,
        starting_head=starting_head, input_fingerprint=_FINGERPRINT, step=_STEP,
        result_env=impl / "bgjob" / "x.merge.env", invariant_evidence=None,
    )


def _edit_producing_launcher(repo: Path):
    calls = {"n": 0}

    def launch(argv: list[str] | None) -> int:
        assert argv is not None
        output = argv[argv.index("--output") + 1]
        Path(output).with_suffix(Path(output).suffix + ".done").write_text("0\n", encoding="utf-8")
        (repo / "README").write_text(f"fixer attempt {calls['n']}\n", encoding="utf-8")
        calls["n"] += 1
        return 0

    return launch


def _setup_dispatch_fixture(tmp_path: Path):
    repo = tmp_path / "repo"
    head = _seed_repo(repo)
    impl = tmp_path / "impl"
    impl.mkdir()
    handoff = impl / "ci-fixer"
    handoff.mkdir(mode=0o700)
    (handoff / "distilled-failure.md").write_text("# Distilled CI failure\n", encoding="utf-8")
    evidence = EvidenceState(
        path=handoff / "distilled-failure.md", kind="distilled", digest="d" * 64,
    )
    return repo, head, impl, handoff, evidence


def test_dispatch_local_validation_fail_resets_and_advances(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, head, impl, handoff, evidence = _setup_dispatch_fixture(tmp_path)
    monkeypatch.setattr(
        ci_fixer_lane.ci_monitor, "read_failed_jobs",
        lambda *_args, **_kwargs: (_jobs("python-lint (1)"), "ready"),
    )
    monkeypatch.setattr(ci_fixer_lane.ci_monitor, "classify_failed_jobs", _fixable_classify)
    monkeypatch.setattr(ci_fixer_lane.ci_monitor, "verify_job_locally", lambda **_kwargs: False)
    launcher = _edit_producing_launcher(repo)

    result = ci_fixer_lane._dispatch(
        _make_identity(repo, impl, handoff, head), evidence, runner=proc,
        launchers={"codex": launcher},
    )
    assert result.result == "retry-next-tool"
    assert result.reason == "fixer-edit-fails-local-validation"
    assert result.final_head == head
    # The fixer's non-fixing edit was reset; the tree is clean again.
    assert _git(repo, "status", "--porcelain") == ""
    assert (repo / "README").read_text(encoding="utf-8") == "seed\n"


def test_dispatch_local_validation_pass_reships(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, head, impl, handoff, evidence = _setup_dispatch_fixture(tmp_path)
    monkeypatch.setattr(
        ci_fixer_lane.ci_monitor, "read_failed_jobs",
        lambda *_args, **_kwargs: (_jobs("python-lint (1)"), "ready"),
    )
    monkeypatch.setattr(ci_fixer_lane.ci_monitor, "classify_failed_jobs", _fixable_classify)
    monkeypatch.setattr(ci_fixer_lane.ci_monitor, "verify_job_locally", lambda **_kwargs: True)
    launcher = _edit_producing_launcher(repo)

    result = ci_fixer_lane._dispatch(
        _make_identity(repo, impl, handoff, head), evidence, runner=proc,
        launchers={"codex": launcher},
    )
    assert result.result == "reship"
    assert result.reason == "fixer-produced-uncommitted-change"
    assert ci_fixer_lane._read_prior_signature(_make_identity(repo, impl, handoff, head)) == frozenset(
        {"python-lint (1)"}
    )


def test_dispatch_signature_no_progress_resets_and_advances(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, head, impl, handoff, evidence = _setup_dispatch_fixture(tmp_path)
    # A non-locally-reproducible failing job so the signature gate is used.
    monkeypatch.setattr(
        ci_fixer_lane.ci_monitor, "read_failed_jobs",
        lambda *_args, **_kwargs: (_jobs("deploy-aws (1)", "deploy-gcp (1)"), "ready"),
    )
    monkeypatch.setattr(ci_fixer_lane.ci_monitor, "classify_failed_jobs", _no_fixable)
    # Prior reship already recorded this exact failing set: no progress.
    ci_fixer_lane._persist_signature(
        _make_identity(repo, impl, handoff, head),
        frozenset({"deploy-aws (1)", "deploy-gcp (1)"}),
    )
    launcher = _edit_producing_launcher(repo)

    result = ci_fixer_lane._dispatch(
        _make_identity(repo, impl, handoff, head), evidence, runner=proc,
        launchers={"codex": launcher},
    )
    assert result.result == "retry-next-tool"
    assert result.reason == "fixer-no-cross-cycle-progress"
    assert _git(repo, "status", "--porcelain") == ""
