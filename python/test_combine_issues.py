# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# pylint: skip-file
"""Tests for combine issue filtering."""

from __future__ import annotations

import json
from pathlib import Path

import combine_issues
from proc import CommandResult


class Runner:
    def __init__(self, stdout: str):
        self.stdout = stdout
    def run(self, argv, **_kwargs):
        if argv[:3] == ["gh", "issue", "list"]:
            return CommandResult(tuple(argv), 0, self.stdout, "", 0.01)
        return CommandResult(tuple(argv), 0, '{"nameWithOwner":"o/r"}', "", 0.01)


def test_fetch_filters_busy_titles(monkeypatch, capsys):
    issues = [
        {"number":1,"title":"[IMPLEMENTING] busy"},
        {"number":2,"title":"[DESIGNED] keep"},
        {"number":3,"title":"normal"},
        {"number":4,"title":"[IN PROGRESS] legacy"},
        {"number":5,"title":"[LOCKED] not now"},
        {"number":6,"title":"[LOCKED]Do not combine"},
    ]
    monkeypatch.setattr(combine_issues.proc, "run", Runner(json.dumps(issues)).run)
    assert combine_issues.fetch_main(["--repo", "o/r"]) == 0
    out = dict(line.split("=",1) for line in capsys.readouterr().out.splitlines())
    assert out["COUNT"] == "2"
    issues_file = Path(out["ISSUES_FILE"])
    try:
        assert issues_file.stat().st_mode & 0o777 == 0o600
        kept = json.loads(issues_file.read_text(encoding="utf-8"))
        assert [issue["number"] for issue in kept] == [2, 3]
    finally:
        issues_file.unlink(missing_ok=True)


def test_fetch_oos_only(monkeypatch, capsys):
    issues = [{"number":1,"title":"[OOS] one"},{"number":2,"title":"not"}]
    monkeypatch.setattr(combine_issues.proc, "run", Runner(json.dumps(issues)).run)
    assert combine_issues.fetch_main(["--repo", "o/r", "--oos"]) == 0
    out = dict(line.split("=",1) for line in capsys.readouterr().out.splitlines())
    assert out["COUNT"] == "1"


def test_fetch_rejects_non_list_json(monkeypatch, capsys):
    monkeypatch.setattr(combine_issues.proc, "run", Runner('{"message":"api error"}').run)
    assert combine_issues.fetch_main(["--repo", "o/r"]) == 1
    assert "ERROR=Failed to fetch issues from o/r" in capsys.readouterr().err


def test_apply_dry_run_wire(tmp_path: Path, capsys):
    body = tmp_path / "body.md"
    body.write_text("Combined body\n", encoding="utf-8")
    assert combine_issues.apply_main(["--repo", "o/r", "--title", "T", "--body-file", str(body), "--source-issues", "1,2", "--dry-run"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert "DRY_RUN=true" in out
    assert "WOULD_CREATE=T" in out
    assert "WOULD_CLOSE=2 issues: 1,2" in out


def test_apply_rejects_empty_source_issue_list(tmp_path: Path, capsys):
    body = tmp_path / "body.md"
    body.write_text("Combined body\n", encoding="utf-8")
    assert combine_issues.apply_main(["--repo", "o/r", "--title", "T", "--body-file", str(body), "--source-issues", " , "]) == 1
    assert "ERROR=No source issues provided" in capsys.readouterr().err


class ApplyRunner:
    def __init__(self):
        self.calls: list[list[str]] = []

    def run(self, argv, **_kwargs):
        self.calls.append(list(argv))
        if argv[:3] == ["gh", "issue", "create"]:
            return CommandResult(tuple(argv), 0, "https://github.com/o/r/issues/99\n", "", 0.01)
        if argv[:3] == ["gh", "issue", "close"] and argv[3] == "1" and sum(c[:4] == ["gh", "issue", "close", "1"] for c in self.calls) == 1:
            return CommandResult(tuple(argv), 1, "", "temporary error", 0.01)
        if argv[:3] == ["gh", "issue", "close"]:
            return CommandResult(tuple(argv), 0, "", "", 0.01)
        return CommandResult(tuple(argv), 0, '{"nameWithOwner":"o/r"}', "", 0.01)


class FailingCreateRunner:
    def __init__(self, result: CommandResult):
        self.result = result

    def run(self, argv, **_kwargs):
        if argv[:3] == ["gh", "issue", "create"]:
            return self.result
        return CommandResult(tuple(argv), 0, '{"nameWithOwner":"o/r"}', "", 0.01)


def test_apply_create_failure_withholds_gh_output(monkeypatch, tmp_path: Path, capsys):
    body = tmp_path / "body.md"
    body.write_text("Combined body with secret-token\n", encoding="utf-8")
    runner = FailingCreateRunner(CommandResult(("gh",), 1, "stdout secret-token", "stderr secret-token", 0.01))
    monkeypatch.setattr(combine_issues.proc, "run", runner.run)
    assert combine_issues.apply_main(["--repo", "o/r", "--title", "T", "--body-file", str(body), "--source-issues", "1"]) == 1
    err = capsys.readouterr().err
    assert "output withheld" in err
    assert "secret-token" not in err


def test_apply_create_parse_failure_withholds_gh_output(monkeypatch, tmp_path: Path, capsys):
    body = tmp_path / "body.md"
    body.write_text("Combined body\n", encoding="utf-8")
    runner = FailingCreateRunner(CommandResult(("gh",), 0, "created secret-token but no url", "", 0.01))
    monkeypatch.setattr(combine_issues.proc, "run", runner.run)
    assert combine_issues.apply_main(["--repo", "o/r", "--title", "T", "--body-file", str(body), "--source-issues", "1"]) == 1
    err = capsys.readouterr().err
    assert "output withheld" in err
    assert "secret-token" not in err


def test_apply_create_and_close_wire_retries(monkeypatch, tmp_path: Path, capsys):
    body = tmp_path / "body.md"
    body.write_text("Combined body\n", encoding="utf-8")
    runner = ApplyRunner()
    monkeypatch.setattr(combine_issues.proc, "run", runner.run)
    monkeypatch.setattr(combine_issues.time, "sleep", lambda _seconds: None)
    assert combine_issues.apply_main(["--repo", "o/r", "--title", "T", "--body-file", str(body), "--source-issues", "1,2"]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["DRY_RUN"] == "false"
    assert out["COMBINED_ISSUE"] == "99"
    assert out["CLOSED_ISSUES"] == "2"
    assert sum(c[:4] == ["gh", "issue", "close", "1"] for c in runner.calls) == 2
