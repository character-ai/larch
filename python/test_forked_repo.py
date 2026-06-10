# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Tests for forked repo helper utilities."""

from __future__ import annotations

from typing import Any

import forked_repo
import proc


def _result(argv: list[str], returncode: int = 0, stdout: str = "", stderr: str = "") -> proc.CommandResult:
    return proc.CommandResult(tuple(argv), returncode, stdout, stderr, 0.0)


def test_normalize_github_url_shapes() -> None:
    assert forked_repo.normalize_github_url("git@github.com:Owner/Repo.git") == ("github.com", "owner/repo")
    assert forked_repo.normalize_github_url("https://github.com/Owner/Repo") == ("github.com", "owner/repo")
    assert forked_repo.normalize_github_url("not-a-url") is None


def test_parse_args_requires_owner_repo() -> None:
    try:
        forked_repo.parse_args(["--upstream", "bad", "--fork", "o/r"])
    except forked_repo.SetupError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected SetupError")


def test_rollback_remotes_if_active_restores_snapshot(monkeypatch: Any) -> None:
    snapshot = forked_repo.RemoteSnapshot([("remote.origin.url", "https://github.com/acme/project.git")])
    ctx = forked_repo.SetupContext(snapshot=snapshot, remote_phase_active=True)
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        return _result(argv)

    monkeypatch.setattr(forked_repo.proc, "run", fake_run)
    forked_repo.rollback_remotes_if_active(ctx)
    assert any(call[:4] == ["git", "config", "--add", "remote.origin.url"] for call in calls)


def test_setup_in_verify_failure_rolls_back(monkeypatch: Any, capsys: Any) -> None:
    snapshot = forked_repo.RemoteSnapshot([("remote.origin.url", "https://github.com/acme/project.git")])
    ctx = forked_repo.SetupContext(
        upstream="acme/project",
        fork="me/project",
        snapshot=snapshot,
        remote_phase_active=True,
    )
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        return _result(argv, stdout="origin\n")

    monkeypatch.setattr(forked_repo.proc, "run", fake_run)
    monkeypatch.setenv("LARCH_FORKED_REPO_INJECT_FAILURE", "in-verify")
    try:
        forked_repo.phase_verify(ctx)
    except forked_repo.SetupError:
        forked_repo.rollback_remotes_if_active(ctx)
    else:  # pragma: no cover
        raise AssertionError("expected SetupError")
    err = capsys.readouterr().err
    assert "remote rewrite failed; attempting rollback" in err
    assert any(call[:4] == ["git", "config", "--add", "remote.origin.url"] for call in calls)


def test_setup_submodule_failure_rolls_back_via_setup_main(monkeypatch: Any, capsys: Any) -> None:
    snapshot = forked_repo.RemoteSnapshot([("remote.origin.url", "https://github.com/acme/project.git")])
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        return _result(argv)

    def fake_remotes(ctx: forked_repo.SetupContext) -> None:
        ctx.snapshot = snapshot
        ctx.remote_phase_active = True

    monkeypatch.setattr(forked_repo.proc, "run", fake_run)
    monkeypatch.setattr(forked_repo, "phase_preflight", lambda _ctx: None)
    monkeypatch.setattr(forked_repo, "phase_github", lambda _ctx: None)
    monkeypatch.setattr(forked_repo, "phase_remotes", fake_remotes)
    monkeypatch.setattr(forked_repo, "phase_submodules", lambda _ctx: forked_repo.die("submodule failed"))
    assert forked_repo.setup_main(["--upstream", "acme/project", "--fork", "me/project"]) == 1
    err = capsys.readouterr().err
    assert "remote rewrite failed; attempting rollback" in err
    assert any(call[:4] == ["git", "config", "--add", "remote.origin.url"] for call in calls)


def test_classify_remote_state_origin_upstream_only(monkeypatch: Any) -> None:
    calls: dict[tuple[str, ...], str] = {
        ("git", "remote"): "origin\n",
        ("git", "config", "--get-all", "remote.origin.url"): "https://github.com/acme/project.git\n",
        ("git", "config", "--get-all", "remote.origin.pushurl"): "",
    }

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        key = tuple(argv)
        if key == ("git", "remote"):
            return _result(argv, stdout=calls[key])
        if key[:3] == ("git", "config", "--get-all"):
            return _result(argv, stdout=calls.get(key, ""))
        return _result(argv)

    monkeypatch.setattr(forked_repo.proc, "run", fake_run)
    state = forked_repo.classify_remote_state("acme/project", "me/project", "github.com")
    assert state == "state-origin-upstream-only"
