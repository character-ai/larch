# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownLambdaType=false
from __future__ import annotations

import json
import subprocess

import admission


def test_single_line_flattens_newlines() -> None:
    assert admission._single_line(" a\n b\r\n c ") == "a b c"  # pyright: ignore[reportPrivateUsage]


def test_normal_issue_rejects_zero() -> None:
    assert admission._normal_issue("0") is None  # pyright: ignore[reportPrivateUsage]
    assert admission._normal_issue("042") == 42  # pyright: ignore[reportPrivateUsage]


def test_prefix_helpers() -> None:
    assert admission._has_managed_prefix("[IMPLEMENTING] Thing")  # pyright: ignore[reportPrivateUsage]
    assert admission._has_designed_prefix("[DESIGNED] Thing")  # pyright: ignore[reportPrivateUsage]
    assert admission._has_report_prefix("[Audit Report] Thing")  # pyright: ignore[reportPrivateUsage]


def test_preflight_unknown_arg_exits_3(capsys) -> None:
    assert admission.preflight_main(["--bogus"]) == 3
    assert "Unknown option" in capsys.readouterr().err


def test_preflight_without_skip_runs_branch_clean_fetch_and_sync(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(argv, *, env=None):
        _ = env
        calls.append(list(argv))
        if argv[:3] == ["git", "symbolic-ref", "--short"]:
            return subprocess.CompletedProcess(argv, 0, "main\n", "")
        if argv[:3] == ["git", "fetch", "origin"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        if "check-main-sync.sh" in str(argv[0]):
            return subprocess.CompletedProcess(argv, 0, "SYNC_STATUS=ok\n", "")
        if argv[:2] == ["git", "rebase"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:3] == ["git", "status", "--porcelain"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:3] == ["git", "rev-parse", "--git-path"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(admission, "_run", fake_run)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(admission, "_clean_tree", lambda: "true")  # pyright: ignore[reportPrivateUsage]
    assert admission.preflight_main([]) == 0
    assert ["git", "symbolic-ref", "--short", "HEAD"] in calls
    assert any(call[:3] == ["git", "fetch", "origin"] for call in calls)
    assert any(call[:2] == ["git", "rebase"] for call in calls)


def test_gate_missing_gh_returns_admission_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr(admission, "_run", lambda argv, **_kwargs: subprocess.CompletedProcess(argv, 127, "", "missing gh\n"))  # pyright: ignore[reportPrivateUsage]
    assert admission.gate_main(["--issue", "7", "--repo", "owner/repo"]) == 2
    assert "ADMISSION_ERROR=gh issue view failed" in capsys.readouterr().out


def test_gate_gh_failure_does_not_echo_stderr(monkeypatch, capsys) -> None:
    def fake_run(argv, *, env=None):
        _ = env
        if argv[:3] == ["gh", "issue", "view"]:
            return subprocess.CompletedProcess(argv, 1, "", "token ghp_secret\n")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(admission, "_run", fake_run)  # pyright: ignore[reportPrivateUsage]
    assert admission.gate_main(["--issue", "7", "--repo", "owner/repo"]) == 2
    out = capsys.readouterr().out
    assert "ADMISSION_ERROR=gh issue view failed" in out
    assert "ghp_secret" not in out
    assert "token" not in out


def test_gate_resume_still_fails_closed_on_gh_failure(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=7\nRUN_ID=\n", encoding="utf-8")
    monkeypatch.setattr(admission, "_run", lambda argv, **_kwargs: subprocess.CompletedProcess(argv, 1, "", "gh auth token\n"))  # pyright: ignore[reportPrivateUsage]
    assert admission.gate_main(["--issue", "7", "--repo", "owner/repo"]) == 2
    out = capsys.readouterr().out
    assert "ADMISSION_ERROR=gh issue view failed" in out
    assert "auth token" not in out


def test_gate_exit_matrix(monkeypatch, capsys) -> None:
    cases = [
        ({"title": "[IMPLEMENTING] Work", "state": "OPEN", "labels": []}, "", 5, "ADMISSION_RESULT=managed-prefix"),
        ({"title": "Plain work", "state": "OPEN", "labels": [{"name": "audit-report"}]}, "", 6, "ADMISSION_RESULT=audit-report-label"),
        ({"title": "[Audit Report] Work", "state": "OPEN", "labels": []}, "", 7, "ADMISSION_RESULT=report-title"),
        ({"title": "[DESIGNED] Work", "state": "OPEN", "labels": []}, "12,13", 4, "ADMISSION_RESULT=has-blockers"),
        ({"title": "[DESIGNED] Work", "state": "OPEN", "labels": []}, "", 0, "ADMISSION_RESULT=pass"),
    ]
    for payload, blockers, expected_rc, expected_line in cases:
        monkeypatch.setattr(admission, "_gh_issue_view", lambda _issue, _repo, data=payload: (0, json.dumps(data)))  # pyright: ignore[reportPrivateUsage]
        monkeypatch.setattr(admission, "_blockers", lambda _issue, _repo, value=blockers: (0, value))  # pyright: ignore[reportPrivateUsage]
        assert admission.gate_main(["--issue", "7", "--repo", "owner/repo"]) == expected_rc
        assert expected_line in capsys.readouterr().out


def test_gate_blocker_failure_is_fail_open_for_missing_designed_prefix(monkeypatch, capsys) -> None:
    payload = {"title": "Plain work", "state": "OPEN", "labels": []}
    monkeypatch.setattr(admission, "_gh_issue_view", lambda _issue, _repo: (0, json.dumps(payload)))  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(admission, "_blockers", lambda _issue, _repo: (2, ""))  # pyright: ignore[reportPrivateUsage]
    assert admission.gate_main(["--issue", "7", "--repo", "owner/repo"]) == 5
    assert "ADMISSION_RESULT=missing-designed-prefix" in capsys.readouterr().out


def test_fork_env_success(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(admission, "_run", lambda argv, **_kwargs: subprocess.CompletedProcess(argv, 0, "git@github.com:user/fork.git\n", ""))  # pyright: ignore[reportPrivateUsage]

    def fake_remote(remote: str) -> tuple[int, str, str]:
        return (0, "user/fork" if remote == "origin" else "upstream/repo", "")

    monkeypatch.setattr(admission, "_github_remote_repo", fake_remote)  # pyright: ignore[reportPrivateUsage]
    assert admission.fork_env_main(["--tmpdir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert f"CALLER_ENV_PATH={tmp_path / 'caller-env.sh'}" in out
    assert "FORK_REPO=user/fork" in out
    assert "UPSTREAM_REPO=upstream/repo" in out
    assert "FORK_OWNER=user" in out
    assert (tmp_path / "caller-env.sh").read_text(encoding="utf-8") == "REPO=user/fork\n"


def test_fork_env_no_upstream(monkeypatch, capsys) -> None:
    monkeypatch.setattr(admission, "_run", lambda argv, **_kwargs: subprocess.CompletedProcess(argv, 2, "", "missing upstream\n"))  # pyright: ignore[reportPrivateUsage]
    assert admission.fork_env_main([]) == 1
    assert "--forked requires the clone" in capsys.readouterr().err


def test_fork_env_parse_failure(monkeypatch, capsys) -> None:
    monkeypatch.setattr(admission, "_run", lambda argv, **_kwargs: subprocess.CompletedProcess(argv, 0, "ok\n", ""))  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(admission, "_github_remote_repo", lambda _remote: (2, "", "parse failed\n"))  # pyright: ignore[reportPrivateUsage]
    assert admission.fork_env_main([]) == 2
    assert "parse failed" in capsys.readouterr().err


def test_fork_env_caller_env_atomic_failure(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(admission, "_run", lambda argv, **_kwargs: subprocess.CompletedProcess(argv, 0, "ok\n", ""))  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(admission, "_github_remote_repo", lambda remote: (0, "user/fork" if remote == "origin" else "upstream/repo", ""))  # pyright: ignore[reportPrivateUsage]

    def fail_atomic(_path, _text) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(admission, "_atomic_text", fail_atomic)  # pyright: ignore[reportPrivateUsage]
    assert admission.fork_env_main(["--tmpdir", str(tmp_path)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "could not write caller-env.sh" in captured.err
