# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownLambdaType=false
from __future__ import annotations

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
