# pyright: reportUnusedCallResult=false
"""Unit tests for checks result-input identity (I-Stale-1)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from larch.core import config
from larch.implement import checks_result_identity as cri


def _git(repo: Path, *args: str) -> None:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README")
    _git(repo, "commit", "-m", "init")
    return repo.resolve()


def test_compute_identity_deterministic(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    first = cri.compute_identity(repo_root=repo)
    second = cri.compute_identity(repo_root=repo)
    assert first == second
    assert first.fingerprint_schema == config.CHECKS_INPUT_FP_SCHEMA_V1
    assert first.head_sha


def test_identity_changes_after_commit(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    before = cri.compute_identity(repo_root=repo)
    (repo / "README").write_text("changed\n", encoding="utf-8")
    _git(repo, "add", "README")
    _git(repo, "commit", "-m", "change")
    after = cri.compute_identity(repo_root=repo)
    assert after.head_sha != before.head_sha
    assert after.tree_fingerprint != before.tree_fingerprint


def test_identity_changes_after_staged_unstaged_untracked(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    base = cri.compute_identity(repo_root=repo)

    (repo / "README").write_text("unstaged\n", encoding="utf-8")
    unstaged = cri.compute_identity(repo_root=repo)
    assert unstaged.tree_fingerprint != base.tree_fingerprint
    assert unstaged.head_sha == base.head_sha

    _git(repo, "add", "README")
    staged = cri.compute_identity(repo_root=repo)
    assert staged.tree_fingerprint != unstaged.tree_fingerprint
    assert staged.head_sha == base.head_sha

    (repo / "extra.txt").write_text("untracked\n", encoding="utf-8")
    untracked = cri.compute_identity(repo_root=repo)
    assert untracked.tree_fingerprint != staged.tree_fingerprint

    (repo / "extra.txt").write_text("untracked-changed\n", encoding="utf-8")
    untracked_changed = cri.compute_identity(repo_root=repo)
    assert untracked_changed.tree_fingerprint != untracked.tree_fingerprint

    (repo / "extra.txt").unlink()
    deleted = cri.compute_identity(repo_root=repo)
    assert deleted.tree_fingerprint == staged.tree_fingerprint


def test_classify_completed_matching_and_mismatches(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    live = cri.compute_identity(repo_root=repo)
    result = tmp_path / "result.env"
    rows = {
        "STEP": "implement-step3-checks",
        "BGJOB_RC": "0",
        "NEXT_ACTION": "checks-failed",
        **dict(live.as_rows()),
    }
    result.write_text("".join(f"{k}={v}\n" for k, v in rows.items()), encoding="utf-8")
    matching = cri.classify_completed_result(
        result_env=result,
        step="implement-step3-checks",
        live=live,
    )
    assert matching.state == config.CHECKS_RESULT_STATE_MATCHING

    rows["CHECKS_INPUT_HEAD_SHA"] = "deadbeef" * 5
    result.write_text("".join(f"{k}={v}\n" for k, v in rows.items()), encoding="utf-8")
    mismatched = cri.classify_completed_result(
        result_env=result,
        step="implement-step3-checks",
        live=live,
    )
    assert mismatched.state == config.CHECKS_RESULT_STATE_STALE
    assert mismatched.reason == "identity-mismatch"


@pytest.mark.parametrize(
    "action",
    sorted(config.CHECKS_TERMINAL_ACTIONS),
)
def test_classify_accepts_all_terminal_actions(tmp_path: Path, action: str) -> None:
    repo = _init_repo(tmp_path)
    live = cri.compute_identity(repo_root=repo)
    result = tmp_path / "result.env"
    body = "\n".join(
        [
            "STEP=implement-step6-checks",
            "BGJOB_RC=0",
            f"NEXT_ACTION={action}",
            *[f"{k}={v}" for k, v in live.as_rows()],
        ]
    ) + "\n"
    result.write_text(body, encoding="utf-8")
    classified = cri.classify_completed_result(
        result_env=result,
        step="implement-step6-checks",
        live=live,
    )
    assert classified.state == config.CHECKS_RESULT_STATE_MATCHING


def test_classify_unknown_or_missing_action_incomplete(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    live = cri.compute_identity(repo_root=repo)
    result = tmp_path / "result.env"
    base = "\n".join(
        [
            "STEP=implement-step3-checks",
            "BGJOB_RC=0",
            *[f"{k}={v}" for k, v in live.as_rows()],
        ]
    )
    result.write_text(base + "\n", encoding="utf-8")
    missing = cri.classify_completed_result(
        result_env=result,
        step="implement-step3-checks",
        live=live,
    )
    assert missing.state == config.CHECKS_RESULT_STATE_INCOMPLETE
    assert missing.reason == "missing-next-action"

    result.write_text(base + "\nNEXT_ACTION=weird\n", encoding="utf-8")
    unknown = cri.classify_completed_result(
        result_env=result,
        step="implement-step3-checks",
        live=live,
    )
    assert unknown.state == config.CHECKS_RESULT_STATE_INCOMPLETE
    assert unknown.reason == "unsupported-next-action"


def test_classify_symlink_and_legacy_missing_identity(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    live = cri.compute_identity(repo_root=repo)
    real = tmp_path / "real.env"
    real.write_text("STEP=implement-step3-checks\nBGJOB_RC=0\nNEXT_ACTION=continue\n", encoding="utf-8")
    link = tmp_path / "link.env"
    link.symlink_to(real)
    unsafe = cri.classify_completed_result(
        result_env=link,
        step="implement-step3-checks",
        live=live,
    )
    assert unsafe.state == config.CHECKS_RESULT_STATE_UNSAFE

    legacy = cri.classify_completed_result(
        result_env=real,
        step="implement-step3-checks",
        live=live,
    )
    assert legacy.state == config.CHECKS_RESULT_STATE_STALE
    assert legacy.reason == "missing-identity"


def test_validate_repo_root_rejects_symlink_and_non_repo(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    link = tmp_path / "link"
    link.symlink_to(repo)
    with pytest.raises(cri.ChecksIdentityError, match="symlink"):
        cri.validate_repo_root(link)
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(cri.ChecksIdentityError, match="git repository"):
        cri.validate_repo_root(plain)


def test_child_validation_rejects_drift(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    seeded = cri.compute_identity(repo_root=repo)
    (repo / "README").write_text("drift\n", encoding="utf-8")
    with pytest.raises(cri.ChecksIdentityError, match="drifted"):
        cri.validate_child_identity(repo_root=repo, expected=seeded)


def test_integrity_failure_not_reusable(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    live = cri.compute_identity(repo_root=repo)
    result = tmp_path / "result.env"
    rows = dict(cri.integrity_failure_rows(step="implement-step3-checks", reason="pre-checks-identity-mismatch"))
    result.write_text("".join(f"{k}={v}\n" for k, v in rows.items()), encoding="utf-8")
    classified = cri.classify_completed_result(
        result_env=result,
        step="implement-step3-checks",
        live=live,
    )
    assert classified.state == config.CHECKS_RESULT_STATE_INCOMPLETE


def test_resolve_session_repo_root(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    session = tmp_path / "session"
    session.mkdir()
    (session / "session-env.sh").write_text(f"REPO_ROOT={repo}\n", encoding="utf-8")
    assert cri.resolve_session_repo_root(session) == repo


def test_cli_compute_and_classify(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    rc = cri.checks_result_identity_main(["compute", "--repo-root", str(repo)])
    assert rc == 0
    live = cri.compute_identity(repo_root=repo)
    result = tmp_path / "result.env"
    result.write_text(
        "\n".join(
            [
                "STEP=implement-step3-checks",
                "BGJOB_RC=0",
                "NEXT_ACTION=continue",
                *[f"{k}={v}" for k, v in live.as_rows()],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rc = cri.checks_result_identity_main(
        [
            "classify",
            "--repo-root",
            str(repo),
            "--result-env",
            str(result),
            "--step",
            "implement-step3-checks",
        ]
    )
    assert rc == 0
