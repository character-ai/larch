# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownLambdaType=false
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from larch.state import admission


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
        if argv[:4] == [sys.executable, str(admission._PY_CLI), "git", "check-main-sync"]:  # pyright: ignore[reportPrivateUsage]
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


def test_preflight_dirty_tree_exits_before_fetch(monkeypatch, capsys) -> None:
    calls: list[list[str]] = []

    def fake_run(argv, *, env=None):
        _ = env
        calls.append(list(argv))
        if argv[:3] == ["git", "symbolic-ref", "--short"]:
            return subprocess.CompletedProcess(argv, 0, "main\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(admission, "_run", fake_run)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(admission, "_clean_tree", lambda: "false")  # pyright: ignore[reportPrivateUsage]
    assert admission.preflight_main([]) == 2
    assert "Working tree is not clean" in capsys.readouterr().out
    assert not any(call[:3] == ["git", "fetch", "origin"] for call in calls)


def test_preflight_skip_branch_skips_sync_and_rebase_but_fetches(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(argv, *, env=None):
        _ = env
        calls.append(list(argv))
        if argv[:3] == ["git", "fetch", "origin"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:3] == ["git", "status", "--porcelain"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:3] == ["git", "rev-parse", "--git-path"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(admission, "_run", fake_run)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(admission, "_clean_tree", lambda: "true")  # pyright: ignore[reportPrivateUsage]
    assert admission.preflight_main(["--skip-branch-check"]) == 0
    assert any(call[:3] == ["git", "fetch", "origin"] for call in calls)
    assert not any(call[:3] == ["git", "symbolic-ref", "--short"] for call in calls)
    assert not any(
        call[:4] == [sys.executable, str(admission._PY_CLI), "git", "check-main-sync"] for call in calls  # pyright: ignore[reportPrivateUsage]
    )
    assert not any(call[:2] == ["git", "rebase"] for call in calls)


def test_preflight_retries_transient_fetch_once(monkeypatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(admission, "_transient_retry_sleeper", lambda _seconds: None)  # pyright: ignore[reportPrivateUsage]

    def fake_run(argv, *, env=None):
        _ = env
        calls.append(list(argv))
        if argv[:3] == ["git", "symbolic-ref", "--short"]:
            return subprocess.CompletedProcess(argv, 0, "main\n", "")
        if argv[:3] == ["git", "fetch", "origin"]:
            fetch_count = sum(1 for call in calls if call[:3] == ["git", "fetch", "origin"])
            if fetch_count == 1:
                return subprocess.CompletedProcess(argv, 128, "", "fatal: unable to access: HTTP 502\n")
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:4] == [sys.executable, str(admission._PY_CLI), "git", "check-main-sync"]:  # pyright: ignore[reportPrivateUsage]
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
    assert sum(1 for call in calls if call[:3] == ["git", "fetch", "origin"]) == 2


def test_preflight_non_transient_fetch_failure_not_retried(monkeypatch, capsys) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(admission, "_transient_retry_sleeper", lambda _seconds: None)  # pyright: ignore[reportPrivateUsage]

    def fake_run(argv, *, env=None):
        _ = env
        calls.append(list(argv))
        if argv[:3] == ["git", "symbolic-ref", "--short"]:
            return subprocess.CompletedProcess(argv, 0, "main\n", "")
        if argv[:3] == ["git", "fetch", "origin"]:
            return subprocess.CompletedProcess(argv, 128, "", "fatal: couldn't find remote ref main\n")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(admission, "_run", fake_run)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(admission, "_clean_tree", lambda: "true")  # pyright: ignore[reportPrivateUsage]
    assert admission.preflight_main([]) == 3
    assert "git fetch origin main failed" in capsys.readouterr().out
    assert sum(1 for call in calls if call[:3] == ["git", "fetch", "origin"]) == 1


def test_preflight_skip_clean_preserves_stalled_marker_when_status_dirty(monkeypatch, tmp_path) -> None:
    marker = tmp_path / "larch-stalled-run.txt"
    marker.write_text("stalled\n", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(argv, *, env=None):
        _ = env
        calls.append(list(argv))
        if argv[:3] == ["git", "symbolic-ref", "--short"]:
            return subprocess.CompletedProcess(argv, 0, "main\n", "")
        if argv[:3] == ["git", "fetch", "origin"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:4] == [sys.executable, str(admission._PY_CLI), "git", "check-main-sync"]:  # pyright: ignore[reportPrivateUsage]
            return subprocess.CompletedProcess(argv, 0, "SYNC_STATUS=ok\n", "")
        if argv[:3] == ["git", "status", "--porcelain"]:
            return subprocess.CompletedProcess(argv, 0, " M kept.txt\n", "")
        if argv[:3] == ["git", "rev-parse", "--git-path"]:
            return subprocess.CompletedProcess(argv, 0, str(marker) + "\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(admission, "_run", fake_run)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(admission, "_clean_tree", lambda: (_ for _ in ()).throw(AssertionError("clean check should be skipped")))  # pyright: ignore[reportPrivateUsage]
    assert admission.preflight_main(["--skip-clean-check"]) == 0
    assert marker.exists()
    assert not any(call[:3] == ["git", "rev-parse", "--git-path"] for call in calls)
    assert not any(call[:2] == ["git", "rebase"] for call in calls)


def test_preflight_skip_clean_clears_stalled_marker_when_status_clean(monkeypatch, tmp_path) -> None:
    marker = tmp_path / "larch-stalled-run.txt"
    marker.write_text("stalled\n", encoding="utf-8")

    def fake_run(argv, *, env=None):
        _ = env
        if argv[:3] == ["git", "symbolic-ref", "--short"]:
            return subprocess.CompletedProcess(argv, 0, "main\n", "")
        if argv[:3] == ["git", "fetch", "origin"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:4] == [sys.executable, str(admission._PY_CLI), "git", "check-main-sync"]:  # pyright: ignore[reportPrivateUsage]
            return subprocess.CompletedProcess(argv, 0, "SYNC_STATUS=ok\n", "")
        if argv[:3] == ["git", "status", "--porcelain"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:3] == ["git", "rev-parse", "--git-path"]:
            return subprocess.CompletedProcess(argv, 0, str(marker) + "\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(admission, "_run", fake_run)  # pyright: ignore[reportPrivateUsage]
    assert admission.preflight_main(["--skip-clean-check"]) == 0
    assert not marker.exists()


def test_preflight_rebase_failure_aborts(monkeypatch, capsys) -> None:
    calls: list[list[str]] = []

    def fake_run(argv, *, env=None):
        _ = env
        calls.append(list(argv))
        if argv[:3] == ["git", "symbolic-ref", "--short"]:
            return subprocess.CompletedProcess(argv, 0, "main\n", "")
        if argv[:3] == ["git", "fetch", "origin"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:4] == [sys.executable, str(admission._PY_CLI), "git", "check-main-sync"]:  # pyright: ignore[reportPrivateUsage]
            return subprocess.CompletedProcess(argv, 0, "SYNC_STATUS=ok\n", "")
        if argv[:3] == ["git", "rebase", "origin/main"]:
            return subprocess.CompletedProcess(argv, 1, "", "conflict\n")
        if argv[:3] == ["git", "status", "--porcelain"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(admission, "_run", fake_run)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(admission, "_clean_tree", lambda: "true")  # pyright: ignore[reportPrivateUsage]
    assert admission.preflight_main([]) == 3
    assert "git rebase origin/main failed" in capsys.readouterr().out
    assert ["git", "rebase", "--abort"] in calls


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


def test_gh_issue_view_retries_once(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(argv, *, env=None):
        _ = env
        calls.append(list(argv))
        if len(calls) == 1:
            return subprocess.CompletedProcess(argv, 1, "", "temporary\n")
        return subprocess.CompletedProcess(argv, 0, '{"title":"ok"}\n', "")

    monkeypatch.setattr(admission, "_run", fake_run)  # pyright: ignore[reportPrivateUsage]
    rc, raw = admission._gh_issue_view(issue=7, repo="owner/repo")  # pyright: ignore[reportPrivateUsage]
    assert rc == 0
    assert raw == '{"title":"ok"}\n'
    assert calls == [
        ["gh", "issue", "view", "7", "--repo", "owner/repo", "--json", "title,state,labels"],
        ["gh", "issue", "view", "7", "--repo", "owner/repo", "--json", "title,state,labels"],
    ]


@pytest.mark.parametrize(
    ("payload", "blockers", "expected_rc", "expected_line"),
    [
        ({"title": "[IMPLEMENTING] Work", "state": "OPEN", "labels": []}, "", 0, "RESUME=true"),
        ({"title": "[IMPLEMENTING] Work", "state": "OPEN", "labels": []}, "12", 4, "ADMISSION_RESULT=has-blockers"),
        ({"title": "[Audit Report] Work", "state": "OPEN", "labels": []}, "", 7, "ADMISSION_RESULT=report-title"),
    ],
)
def test_gate_resume_matrix(tmp_path, monkeypatch, capsys, payload, blockers: str, expected_rc: int, expected_line: str) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setenv("RUN_ID", "R1")
    (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=7\nRUN_ID=R1\n", encoding="utf-8")
    monkeypatch.setattr(admission, "_gh_issue_view", lambda issue, repo: (0, json.dumps(payload)))  # pyright: ignore[reportPrivateUsage]  # noqa: ARG005
    monkeypatch.setattr(admission, "_blockers", lambda issue, repo: (0, blockers))  # pyright: ignore[reportPrivateUsage]  # noqa: ARG005
    assert admission.gate_main(["--issue", "7", "--repo", "owner/repo"]) == expected_rc
    out = capsys.readouterr().out
    assert expected_line in out
    assert "ADMISSION_RESULT=managed-prefix" not in out


def test_gate_resume_run_id_mismatch_uses_normal_admission(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setenv("RUN_ID", "R2")
    (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=7\nRUN_ID=R1\n", encoding="utf-8")
    payload = {"title": "[IMPLEMENTING] Work", "state": "OPEN", "labels": []}
    monkeypatch.setattr(admission, "_gh_issue_view", lambda issue, repo: (0, json.dumps(payload)))  # pyright: ignore[reportPrivateUsage]  # noqa: ARG005
    monkeypatch.setattr(admission, "_blockers", lambda issue, repo: (0, ""))  # pyright: ignore[reportPrivateUsage]  # noqa: ARG005
    assert admission.gate_main(["--issue", "7", "--repo", "owner/repo"]) == 5
    out = capsys.readouterr().out
    assert "ADMISSION_RESULT=managed-prefix" in out
    assert "RESUME=true" not in out


def test_gate_exit_matrix(monkeypatch, capsys) -> None:
    cases = [
        ({"title": "[IMPLEMENTING] Work", "state": "OPEN", "labels": []}, "", 5, "ADMISSION_RESULT=managed-prefix"),
        ({"title": "Plain work", "state": "OPEN", "labels": [{"name": "audit-report"}]}, "", 6, "ADMISSION_RESULT=audit-report-label"),
        ({"title": "[Audit Report] Work", "state": "OPEN", "labels": []}, "", 7, "ADMISSION_RESULT=report-title"),
        ({"title": "[DESIGNED] Work", "state": "OPEN", "labels": []}, "12,13", 4, "ADMISSION_RESULT=has-blockers"),
        ({"title": "[DESIGNED] Work", "state": "OPEN", "labels": []}, "", 0, "ADMISSION_RESULT=pass"),
    ]
    for payload, blockers, expected_rc, expected_line in cases:
        monkeypatch.setattr(admission, "_gh_issue_view", lambda issue, repo, data=payload: (0, json.dumps(data)))  # pyright: ignore[reportPrivateUsage]  # noqa: ARG005
        monkeypatch.setattr(admission, "_blockers", lambda issue, repo, value=blockers: (0, value))  # pyright: ignore[reportPrivateUsage]  # noqa: ARG005
        assert admission.gate_main(["--issue", "7", "--repo", "owner/repo"]) == expected_rc
        assert expected_line in capsys.readouterr().out


def test_gate_blocker_failure_fails_closed(monkeypatch, capsys) -> None:
    payload = {"title": "Plain work", "state": "OPEN", "labels": []}
    monkeypatch.setattr(admission, "_gh_issue_view", lambda issue, repo: (0, json.dumps(payload)))  # pyright: ignore[reportPrivateUsage]  # noqa: ARG005
    monkeypatch.setattr(admission, "_blockers", lambda issue, repo: (2, ""))  # pyright: ignore[reportPrivateUsage]  # noqa: ARG005
    assert admission.gate_main(["--issue", "7", "--repo", "owner/repo"]) == 2
    out = capsys.readouterr().out
    assert "ADMISSION_ERROR=blocker check failed (exit 2)" in out
    assert "ADMISSION_RESULT=missing-designed-prefix" not in out


def test_gate_resume_blocker_failure_fails_closed(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setenv("RUN_ID", "R1")
    (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=7\nRUN_ID=R1\n", encoding="utf-8")
    payload = {"title": "[IMPLEMENTING] Work", "state": "OPEN", "labels": []}
    monkeypatch.setattr(admission, "_gh_issue_view", lambda issue, repo: (0, json.dumps(payload)))  # pyright: ignore[reportPrivateUsage]  # noqa: ARG005
    monkeypatch.setattr(admission, "_blockers", lambda issue, repo: (2, ""))  # pyright: ignore[reportPrivateUsage]  # noqa: ARG005
    assert admission.gate_main(["--issue", "7", "--repo", "owner/repo"]) == 2
    out = capsys.readouterr().out
    assert "ADMISSION_ERROR=blocker check failed (exit 2)" in out
    assert "RESUME=true" not in out


def test_fork_env_success(tmp_path, monkeypatch, capsys) -> None:
    gh_calls: list[list[str]] = []

    def fake_run(argv, **_kwargs):  # pyright: ignore[reportMissingParameterType, reportUnknownParameterType]
        if argv[:3] == ["git", "remote", "get-url"]:
            return subprocess.CompletedProcess(argv, 0, "https://github.com/upstream/repo.git\n", "")
        if len(argv) >= 4 and list(argv[-3:]) == ["gh", "remote-repo", "origin"]:
            gh_calls.append(list(argv))
            return subprocess.CompletedProcess(argv, 0, "user/fork\n", "")
        if len(argv) >= 4 and list(argv[-3:]) == ["gh", "remote-repo", "upstream"]:
            gh_calls.append(list(argv))
            return subprocess.CompletedProcess(argv, 0, "upstream/repo\n", "")
        return subprocess.CompletedProcess(argv, 1, "", "unexpected\n")

    monkeypatch.setattr(admission, "_run", fake_run)  # pyright: ignore[reportPrivateUsage]
    assert admission.fork_env_main(["--tmpdir", str(tmp_path)]) == 0
    expected_argv = [sys.executable, str(admission._PY_CLI), "gh", "remote-repo"]  # pyright: ignore[reportPrivateUsage]
    assert gh_calls == [
        [*expected_argv, "origin"],
        [*expected_argv, "upstream"],
    ]
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
    def fake_run(argv, **_kwargs):  # pyright: ignore[reportMissingParameterType, reportUnknownParameterType]
        if argv[:3] == ["git", "remote", "get-url"]:
            return subprocess.CompletedProcess(argv, 0, "https://github.com/upstream/repo.git\n", "")
        if len(argv) >= 4 and list(argv[-3:]) == ["gh", "remote-repo", "origin"]:
            return subprocess.CompletedProcess(argv, 2, "", "parse failed\n")
        return subprocess.CompletedProcess(argv, 1, "", "unexpected\n")

    monkeypatch.setattr(admission, "_run", fake_run)  # pyright: ignore[reportPrivateUsage]
    assert admission.fork_env_main([]) == 2
    assert "parse failed" in capsys.readouterr().err


def test_fork_env_caller_env_atomic_failure(tmp_path, monkeypatch, capsys) -> None:
    def fake_run(argv, **_kwargs):  # pyright: ignore[reportMissingParameterType, reportUnknownParameterType]
        if argv[:3] == ["git", "remote", "get-url"]:
            return subprocess.CompletedProcess(argv, 0, "https://github.com/upstream/repo.git\n", "")
        if len(argv) >= 4 and list(argv[-3:]) == ["gh", "remote-repo", "origin"]:
            return subprocess.CompletedProcess(argv, 0, "user/fork\n", "")
        if len(argv) >= 4 and list(argv[-3:]) == ["gh", "remote-repo", "upstream"]:
            return subprocess.CompletedProcess(argv, 0, "upstream/repo\n", "")
        return subprocess.CompletedProcess(argv, 1, "", "unexpected\n")

    monkeypatch.setattr(admission, "_run", fake_run)  # pyright: ignore[reportPrivateUsage]

    def fail_atomic(**_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(admission, "_atomic_text", fail_atomic)  # pyright: ignore[reportPrivateUsage]
    assert admission.fork_env_main(["--tmpdir", str(tmp_path)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "could not write caller-env.sh" in captured.err


# ---------------------------------------------------------------------------
# _blockers unit tests — these test _blockers in isolation (not via mocked
# _blockers) so that a regression to "return 0, ''" on subprocess failure
# would be caught here rather than only at the gate_main level.
# ---------------------------------------------------------------------------


def test_blockers_subprocess_failure_propagates_rc(monkeypatch) -> None:
    monkeypatch.setattr(admission, "_run", lambda argv, **_: subprocess.CompletedProcess(argv, 1, "", "import error\n"))  # pyright: ignore[reportPrivateUsage]
    rc, blockers = admission._blockers(issue=7, repo="owner/repo")  # pyright: ignore[reportPrivateUsage]
    assert rc == 1
    assert blockers == ""


def test_blockers_subprocess_success_with_blockers_line(monkeypatch) -> None:
    monkeypatch.setattr(admission, "_run", lambda argv, **_: subprocess.CompletedProcess(argv, 0, "BLOCKERS=12 34\n", ""))  # pyright: ignore[reportPrivateUsage]
    rc, blockers = admission._blockers(issue=7, repo="owner/repo")  # pyright: ignore[reportPrivateUsage]
    assert rc == 0
    assert blockers == "12 34"


def test_blockers_subprocess_success_no_blockers_line_is_fail_open(monkeypatch) -> None:
    # D3: subprocess exits 0 but emits no BLOCKERS= line (e.g. degraded GitHub API
    # inside the subprocess) → treat as no blockers found (fail-open posture).
    monkeypatch.setattr(admission, "_run", lambda argv, **_: subprocess.CompletedProcess(argv, 0, "OTHER=value\n", ""))  # pyright: ignore[reportPrivateUsage]
    rc, blockers = admission._blockers(issue=7, repo="owner/repo")  # pyright: ignore[reportPrivateUsage]
    assert rc == 0
    assert blockers == ""


def test_gate_blocker_subprocess_failure_fails_closed_e2e(monkeypatch, capsys) -> None:
    # End-to-end: _run is mocked directly (not _blockers) so the full call chain
    # from gate_main → _blockers → _run is exercised.  A regression to
    # "return 0, ''" inside _blockers would cause gate_main to emit
    # ADMISSION_RESULT=missing-designed-prefix instead of ADMISSION_ERROR.
    payload = {"title": "[DESIGNED] Work", "state": "OPEN", "labels": []}

    def fake_run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if argv[:3] == ["gh", "issue", "view"]:
            return subprocess.CompletedProcess(argv, 0, json.dumps(payload), "")
        return subprocess.CompletedProcess(argv, 1, "", "fake subprocess failure\n")

    monkeypatch.setattr(admission, "_run", fake_run)  # pyright: ignore[reportPrivateUsage]
    assert admission.gate_main(["--issue", "7", "--repo", "owner/repo"]) == 2
    out = capsys.readouterr().out
    assert "ADMISSION_ERROR=" in out
    assert "ADMISSION_RESULT=pass" not in out
    assert "ADMISSION_RESULT=missing-designed-prefix" not in out
