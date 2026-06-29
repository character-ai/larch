# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# pylint: skip-file
"""Tests for combine issue filtering."""

from __future__ import annotations

import json

from larch.git import gh
from pathlib import Path

from larch.issue import combine_issues
from larch.core.proc import CommandResult


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


def test_apply_rejects_malformed_source_issues_before_create(monkeypatch, tmp_path: Path, capsys):
    class CountingRunner:
        def __init__(self):
            self.calls: list[list[str]] = []

        def run(self, argv, **_kwargs):
            self.calls.append(list(argv))
            return CommandResult(tuple(argv), 0, "https://github.com/o/r/issues/99\n", "", 0.01)

    body = tmp_path / "body.md"
    body.write_text("Combined body\n", encoding="utf-8")
    runner = CountingRunner()
    monkeypatch.setattr(combine_issues.proc, "run", runner.run)
    assert combine_issues.apply_main([
        "--repo", "o/r",
        "--title", "T",
        "--body-file", str(body),
        "--source-issues", "1,nope",
        "--defer-close",
    ]) == 1
    assert "ERROR=--source-issues values must be positive integers" in capsys.readouterr().err
    assert not any(call[:3] == ["gh", "issue", "create"] for call in runner.calls)


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


def test_apply_close_warning_redacts_failed_close_stderr(monkeypatch, tmp_path: Path, capsys):
    class CloseFailRunner:
        def run(self, argv, **_kwargs):
            if argv[:3] == ["gh", "issue", "create"]:
                return CommandResult(tuple(argv), 0, "https://github.com/o/r/issues/99\n", "", 0.01)
            if argv[:3] == ["gh", "issue", "close"]:
                return CommandResult(tuple(argv), 1, "", "failed with ghp_abcdefghijklmnopqrstuvwxyz0123456789", 0.01)
            return CommandResult(tuple(argv), 0, '{"nameWithOwner":"o/r"}', "", 0.01)

    body = tmp_path / "body.md"
    body.write_text("Combined body\n", encoding="utf-8")
    monkeypatch.setattr(combine_issues.proc, "run", CloseFailRunner().run)
    monkeypatch.setattr(combine_issues.time, "sleep", lambda _seconds: None)
    assert combine_issues.apply_main(["--repo", "o/r", "--title", "T", "--body-file", str(body), "--source-issues", "1"]) == 0
    captured = capsys.readouterr()
    assert "WARNING=Failed to close #1:" in captured.err
    assert "ghp_abcdefghijklmnopqrstuvwxyz0123456789" not in captured.err
    assert "CLOSED_ISSUES=0" in captured.out



def _write_json(path: Path, data: object) -> str:
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


class GhReadRunner:
    def __init__(self):
        self.calls: list[list[str]] = []

    def run(self, argv, **_kwargs):
        self.calls.append(list(argv))
        return CommandResult(tuple(argv), 0, "[]", "", 0.01)


def test_issue_blocking_read_pins_native_endpoint_argv():
    runner = GhReadRunner()
    result = gh.issue_blocking_read(runner, "7", repo="o/r")
    assert result.returncode == 0
    assert runner.calls == [["gh", "api", "repos/o/r/issues/7/dependencies/blocking", "--paginate"]]


def test_fetch_deps_reads_both_directions_and_marks_blocking_failure(monkeypatch, capsys):
    def blocked_by(_runner, issue, *, repo, _cwd=None):
        assert repo == "o/r"
        if issue == "1":
            return CommandResult(("gh",), 0, '[{"number":"3"},{"number":3},{"number":"x"},{"id":1}]', "", 0.01)
        return CommandResult(("gh",), 0, "[]", "", 0.01)

    def blocking(_runner, issue, *, repo, _cwd=None):
        assert repo == "o/r"
        if issue == "2":
            return CommandResult(("gh",), 1, "", "HTTP 404 Not Found", 0.01)
        return CommandResult(("gh",), 0, '[{"number":4}]', "", 0.01)

    monkeypatch.setattr(combine_issues.gh, "issue_blocked_by_read", blocked_by)
    monkeypatch.setattr(combine_issues.gh, "issue_blocking_read", blocking)
    assert combine_issues.fetch_deps_main(["--repo", "o/r", "--issues", "1,2"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["issues"]["1"] == {"blocked_by": [3], "blocking": [4], "read_ok": True}
    assert payload["issues"]["2"]["read_ok"] is False
    assert payload["failed_issue_reads"] == [{"source_issue": 2, "direction": "blocking", "error": "HTTP 404 Not Found"}]
    assert payload["warnings"][0]["code"] == "blocking_endpoint_unavailable"


def test_plan_inherited_remaps_dedupes_self_edges_and_classifies(tmp_path: Path, capsys):
    deps = _write_json(tmp_path / "deps.json", {
        "status": "ok",
        "issues": {
            "1": {"blocked_by": [1, 2, 5], "blocking": [6], "read_ok": True},
            "2": {"blocked_by": [1], "blocking": [], "read_ok": True},
        },
        "warnings": [],
    })
    source_map = _write_json(tmp_path / "source-map.json", {"1": 100, "2": 200})
    open_issues = _write_json(tmp_path / "open.json", {"status": "ok", "issues": [
        {"number": 5, "title": "normal blocker", "state": "open"},
        {"number": 6, "title": "normal client", "state": "open"},
    ]})
    combined = _write_json(tmp_path / "combined.json", [
        {"number": 100, "title": "[OOS] one", "source_issues": [1]},
        {"number": 200, "title": "[OOS] two", "source_issues": [2]},
    ])
    assert combine_issues.plan_inherited_main([
        "--deps-file", deps,
        "--source-to-combined-file", source_map,
        "--open-issues-file", open_issues,
        "--combined-issues-file", combined,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    safe_edges = {tuple(row["edge"]) for row in payload["safe_edges"]}
    exception_edges = {tuple(row["edge"]) for row in payload["exception_edges"]}
    assert (100, 5) in safe_edges
    assert (100, 200) in safe_edges
    assert (200, 100) in safe_edges
    assert (6, 100) in exception_edges
    assert payload["self_edges_skipped"] == 1
    assert payload["edge_provenance"]["6:100"] == [1]


def test_plan_inherited_expands_split_source_hosts(tmp_path: Path, capsys):
    deps = _write_json(tmp_path / "deps.json", {
        "status": "ok",
        "issues": {"1": {"blocked_by": [5], "blocking": [6], "read_ok": True}},
        "warnings": [],
    })
    source_map = _write_json(tmp_path / "source-map.json", {"1": [100, 101]})
    open_issues = _write_json(tmp_path / "open.json", {"status": "ok", "issues": [
        {"number": 5, "title": "normal blocker", "state": "open"},
        {"number": 6, "title": "normal client", "state": "open"},
    ]})
    combined = _write_json(tmp_path / "combined.json", [
        {"number": 100, "title": "[OOS] one", "source_issues": [1]},
        {"number": 101, "title": "[OOS] two", "source_issues": [1]},
    ])
    assert combine_issues.plan_inherited_main([
        "--deps-file", deps,
        "--source-to-combined-file", source_map,
        "--open-issues-file", open_issues,
        "--combined-issues-file", combined,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    safe_edges = {tuple(row["edge"]) for row in payload["safe_edges"]}
    exception_edges = {tuple(row["edge"]) for row in payload["exception_edges"]}
    assert safe_edges == {(100, 5), (101, 5)}
    assert exception_edges == {(6, 100), (6, 101)}


def test_plan_inherited_uses_refreshed_open_title_for_combined_oos(tmp_path: Path, capsys):
    deps = _write_json(tmp_path / "deps.json", {
        "status": "ok",
        "issues": {"1": {"blocked_by": [], "blocking": [5], "read_ok": True}},
        "warnings": [],
    })
    source_map = _write_json(tmp_path / "source-map.json", {"1": 100})
    open_issues = _write_json(tmp_path / "open.json", {"issues": [
        {"number": 5, "title": "normal", "state": "open"},
        {"number": 100, "title": "[OOS] live title", "state": "open"},
    ]})
    combined = _write_json(tmp_path / "combined.json", [{"number": 100, "title": "stale snapshot", "source_issues": [1]}])
    assert combine_issues.plan_inherited_main([
        "--deps-file", deps,
        "--source-to-combined-file", source_map,
        "--open-issues-file", open_issues,
        "--combined-issues-file", combined,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["safe_edges"] == []
    assert [row["edge"] for row in payload["exception_edges"]] == [[5, 100]]
    assert payload["exception_edges"][0]["blocker_title"] == "[OOS] live title"


def test_plan_inherited_unknown_metadata_blocks_source_until_refresh(tmp_path: Path, capsys):
    deps = _write_json(tmp_path / "deps.json", {"issues": {"1": {"blocked_by": [9], "blocking": [], "read_ok": True}}})
    source_map = _write_json(tmp_path / "source-map.json", {"1": 100})
    open_issues = _write_json(tmp_path / "open.json", {"issues": []})
    combined = _write_json(tmp_path / "combined.json", [{"number": 100, "title": "[OOS] one", "source_issues": [1]}])
    assert combine_issues.plan_inherited_main([
        "--deps-file", deps,
        "--source-to-combined-file", source_map,
        "--open-issues-file", open_issues,
        "--combined-issues-file", combined,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [row["edge"] for row in payload["unknown_edges"]] == [[100, 9]]
    assert payload["per_source_initial_eligibility"]["1"]["eligible"] is False


def test_plan_inherited_closed_blocker_with_repo_is_satisfied(monkeypatch, tmp_path: Path, capsys):
    deps = _write_json(tmp_path / "deps.json", {
        "status": "ok",
        "issues": {"1": {"blocked_by": [9], "blocking": [], "read_ok": True}},
    })
    source_map = _write_json(tmp_path / "source-map.json", {"1": 100})
    open_issues = _write_json(tmp_path / "open.json", {"status": "ok", "issues": []})
    combined = _write_json(tmp_path / "combined.json", [{"number": 100, "title": "[OOS] one", "source_issues": [1]}])
    calls = []

    def view(_runner, issue, field, *, repo, cwd=None):
        calls.append((issue, field, repo, cwd))
        return CommandResult(("gh",), 0, json.dumps({"number": 9, "state": "CLOSED", "title": "[DONE] done"}), "", 0.01)

    monkeypatch.setattr(combine_issues.gh, "issue_view_field_read", view)
    assert combine_issues.plan_inherited_main([
        "--repo", "o/r",
        "--deps-file", deps,
        "--source-to-combined-file", source_map,
        "--open-issues-file", open_issues,
        "--combined-issues-file", combined,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert calls == [("9", "number,state,title", "o/r", None)]
    assert [row["edge"] for row in payload["satisfied_edges"]] == [[100, 9]]
    assert payload["satisfied_edges"][0]["blocker_title"] == "[DONE] done"
    assert payload["safe_edges"] == []
    assert payload["exception_edges"] == []
    assert payload["unknown_edges"] == []
    assert payload["per_source_initial_eligibility"]["1"]["eligible"] is True


def test_plan_inherited_closed_blocker_metadata_is_not_unknown():
    meta = {
        100: {"number": 100, "title": "[OOS] combined", "state": "OPEN"},
        9: {"number": 9, "title": "[DONE] done", "state": "CLOSED"},
    }
    assert combine_issues._classify_edge(edge=(100, 9), meta=meta, combined_oos={100}) == (
        "satisfied",
        "blocker issue already closed (dependency satisfied)",
    )


def test_plan_inherited_without_repo_does_not_enrich_missing_blocker(monkeypatch, tmp_path: Path, capsys):
    deps = _write_json(tmp_path / "deps.json", {"issues": {"1": {"blocked_by": [9], "blocking": [], "read_ok": True}}})
    source_map = _write_json(tmp_path / "source-map.json", {"1": 100})
    open_issues = _write_json(tmp_path / "open.json", {"issues": []})
    combined = _write_json(tmp_path / "combined.json", [{"number": 100, "title": "[OOS] one", "source_issues": [1]}])

    def view(*_args, **_kwargs):
        raise AssertionError("blocker enrichment should require --repo")

    monkeypatch.setattr(combine_issues.gh, "issue_view_field_read", view)
    assert combine_issues.plan_inherited_main([
        "--deps-file", deps,
        "--source-to-combined-file", source_map,
        "--open-issues-file", open_issues,
        "--combined-issues-file", combined,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [row["edge"] for row in payload["unknown_edges"]] == [[100, 9]]
    assert payload["satisfied_edges"] == []
    assert payload["per_source_initial_eligibility"]["1"]["eligible"] is False


def test_plan_inherited_failed_blocker_lookup_stays_unknown_and_warns(monkeypatch, tmp_path: Path, capsys):
    deps = _write_json(tmp_path / "deps.json", {"issues": {"1": {"blocked_by": [9], "blocking": [], "read_ok": True}}})
    source_map = _write_json(tmp_path / "source-map.json", {"1": 100})
    open_issues = _write_json(tmp_path / "open.json", {"issues": []})
    combined = _write_json(tmp_path / "combined.json", [{"number": 100, "title": "[OOS] one", "source_issues": [1]}])

    def view(_runner, issue, field, *, repo, cwd=None):
        assert (issue, field, repo, cwd) == ("9", "number,state,title", "o/r", None)
        return CommandResult(("gh",), 1, "", "failed with ghp_abcdefghijklmnopqrstuvwxyz0123456789", 0.01)

    monkeypatch.setattr(combine_issues.gh, "issue_view_field_read", view)
    assert combine_issues.plan_inherited_main([
        "--repo", "o/r",
        "--deps-file", deps,
        "--source-to-combined-file", source_map,
        "--open-issues-file", open_issues,
        "--combined-issues-file", combined,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [row["edge"] for row in payload["unknown_edges"]] == [[100, 9]]
    assert payload["per_source_initial_eligibility"]["1"]["eligible"] is False
    assert payload["warnings"][0]["code"] == "blocker_state_read_failed"
    assert "ghp_abcdefghijklmnopqrstuvwxyz0123456789" not in json.dumps(payload["warnings"])


def test_plan_inherited_open_blocker_enriched_with_repo_classifies_safe(monkeypatch, tmp_path: Path, capsys):
    deps = _write_json(tmp_path / "deps.json", {"issues": {"1": {"blocked_by": [9], "blocking": [], "read_ok": True}}})
    source_map = _write_json(tmp_path / "source-map.json", {"1": 100})
    open_issues = _write_json(tmp_path / "open.json", {"issues": []})
    combined = _write_json(tmp_path / "combined.json", [{"number": 100, "title": "[OOS] one", "source_issues": [1]}])

    def view(_runner, issue, field, *, repo, cwd=None):
        assert (issue, field, repo, cwd) == ("9", "number,state,title", "o/r", None)
        return CommandResult(("gh",), 0, json.dumps({"number": 9, "state": "OPEN", "title": "ready blocker"}), "", 0.01)

    monkeypatch.setattr(combine_issues.gh, "issue_view_field_read", view)
    assert combine_issues.plan_inherited_main([
        "--repo", "o/r",
        "--deps-file", deps,
        "--source-to-combined-file", source_map,
        "--open-issues-file", open_issues,
        "--combined-issues-file", combined,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [row["edge"] for row in payload["safe_edges"]] == [[100, 9]]
    assert payload["unknown_edges"] == []
    assert payload["satisfied_edges"] == []


def test_plan_inherited_refresh_reclassifies_unknown_edge_and_allows_close(tmp_path: Path, capsys):
    deps = _write_json(tmp_path / "deps.json", {"issues": {"1": {"blocked_by": [9], "blocking": [], "read_ok": True}}})
    source_map = _write_json(tmp_path / "source-map.json", {"1": 100})
    combined = _write_json(tmp_path / "combined.json", [{"number": 100, "title": "[OOS] one", "source_issues": [1]}])
    first_open = _write_json(tmp_path / "open-first.json", {"issues": []})
    assert combine_issues.plan_inherited_main([
        "--deps-file", deps,
        "--source-to-combined-file", source_map,
        "--open-issues-file", first_open,
        "--combined-issues-file", combined,
    ]) == 0
    first = json.loads(capsys.readouterr().out)
    assert [row["edge"] for row in first["unknown_edges"]] == [[100, 9]]

    refreshed_open = _write_json(tmp_path / "open-refreshed.json", {"issues": [
        {"number": 9, "title": "ready blocker", "state": "open"},
    ]})
    assert combine_issues.plan_inherited_main([
        "--deps-file", deps,
        "--source-to-combined-file", source_map,
        "--open-issues-file", refreshed_open,
        "--combined-issues-file", combined,
    ]) == 0
    refreshed = json.loads(capsys.readouterr().out)
    assert [row["edge"] for row in refreshed["safe_edges"]] == [[100, 9]]
    assert refreshed["unknown_edges"] == []

    plan = _write_json(tmp_path / "plan.json", refreshed)
    writes = _write_json(tmp_path / "writes.json", {"write_results": [
        {"edge": [100, 9], "phase": "inherited_reclassified_safe", "status": "written", "source_issues": [1]},
    ]})
    decisions = _write_json(tmp_path / "decisions.json", {"decisions": []})
    blocked = _write_json(tmp_path / "blocked.json", {"blocked_sources": []})
    assert combine_issues.close_eligible_main([
        "--inherited-plan-file", plan,
        "--write-results-file", writes,
        "--exception-decisions-file", decisions,
        "--source-to-combined-file", source_map,
        "--blocked-sources-file", blocked,
    ]) == 0
    close_payload = json.loads(capsys.readouterr().out)
    assert close_payload["eligible_by_combined"] == {"100": [1]}


def test_close_eligible_uses_write_decision_and_blocked_source_schemas(tmp_path: Path, capsys):
    plan = _write_json(tmp_path / "plan.json", {
        "status": "ok",
        "safe_edges": [{"edge": [100, 5], "source_issues": [1]}],
        "exception_edges": [{"edge": [6, 100], "source_issues": [1]}],
        "unknown_edges": [{"edge": [200, 9], "source_issues": [2]}],
        "per_source_initial_eligibility": {
            "1": {"eligible": True, "reasons": []},
            "2": {"eligible": False, "reasons": ["dependency_read_failed"]},
            "3": {"eligible": True, "reasons": []},
        },
    })
    writes = _write_json(tmp_path / "writes.json", {"write_results": [
        {"edge": [100, 5], "client_issue": 100, "blocker_issue": 5, "phase": "inherited_safe", "status": "written", "source_issues": [1]},
    ]})
    decisions = _write_json(tmp_path / "decisions.json", {"decisions": [
        {"edge": [6, 100], "decision": "rejected", "phase": "inherited_exception", "source_issues": [1], "reason": "operator rejected"},
    ]})
    source_map = _write_json(tmp_path / "source-map.json", {"1": 100, "2": 200, "3": 300})
    blocked = _write_json(tmp_path / "blocked.json", {"blocked_sources": [{"source_issue": 3, "reason": "blocked item remains"}]})
    assert combine_issues.close_eligible_main([
        "--inherited-plan-file", plan,
        "--write-results-file", writes,
        "--exception-decisions-file", decisions,
        "--source-to-combined-file", source_map,
        "--blocked-sources-file", blocked,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["eligible_by_combined"] == {"100": [1]}
    assert payload["ineligible_sources"] == [2, 3]
    assert "blocked item remains" in payload["reasons"]["3"]


def test_close_eligible_ignores_satisfied_edges(tmp_path: Path, capsys):
    plan = _write_json(tmp_path / "plan.json", {
        "status": "ok",
        "safe_edges": [],
        "exception_edges": [],
        "satisfied_edges": [{"edge": [100, 9], "source_issues": [1]}],
        "unknown_edges": [],
        "per_source_initial_eligibility": {"1": {"eligible": True, "reasons": []}},
    })
    writes = _write_json(tmp_path / "writes.json", {"write_results": []})
    decisions = _write_json(tmp_path / "decisions.json", {"decisions": []})
    source_map = _write_json(tmp_path / "source-map.json", {"1": 100})
    blocked = _write_json(tmp_path / "blocked.json", {"blocked_sources": []})
    assert combine_issues.close_eligible_main([
        "--inherited-plan-file", plan,
        "--write-results-file", writes,
        "--exception-decisions-file", decisions,
        "--source-to-combined-file", source_map,
        "--blocked-sources-file", blocked,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["eligible_by_combined"] == {"100": [1]}
    assert payload["ineligible_sources"] == []
    assert payload["reasons"]["1"] == []


def test_close_eligible_ignores_retried_safe_write_failure(tmp_path: Path, capsys):
    plan = _write_json(tmp_path / "plan.json", {
        "status": "ok",
        "safe_edges": [{"edge": [100, 5], "source_issues": [1]}],
        "exception_edges": [],
        "unknown_edges": [],
        "per_source_initial_eligibility": {"1": {"eligible": True, "reasons": []}},
    })
    writes = _write_json(tmp_path / "writes.json", {"write_results": [
        {"edge": [100, 5], "phase": "inherited_safe", "status": "failed", "source_issues": [1]},
        {"edge": [100, 5], "phase": "inherited_safe", "status": "written", "source_issues": [1]},
    ]})
    decisions = _write_json(tmp_path / "decisions.json", {"decisions": []})
    source_map = _write_json(tmp_path / "source-map.json", {"1": 100})
    blocked = _write_json(tmp_path / "blocked.json", {"blocked_sources": []})
    assert combine_issues.close_eligible_main([
        "--inherited-plan-file", plan,
        "--write-results-file", writes,
        "--exception-decisions-file", decisions,
        "--source-to-combined-file", source_map,
        "--blocked-sources-file", blocked,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["eligible_by_combined"] == {"100": [1]}
    assert payload["ineligible_sources"] == []


def test_close_eligible_ignores_later_safe_write_failure_after_success(tmp_path: Path, capsys):
    plan = _write_json(tmp_path / "plan.json", {
        "status": "ok",
        "safe_edges": [{"edge": [100, 5], "source_issues": [1]}],
        "exception_edges": [],
        "unknown_edges": [],
        "per_source_initial_eligibility": {"1": {"eligible": True, "reasons": []}},
    })
    writes = _write_json(tmp_path / "writes.json", {"write_results": [
        {"edge": [100, 5], "phase": "inherited_safe", "status": "written", "source_issues": [1]},
        {"edge": [100, 5], "phase": "inherited_safe", "status": "failed", "source_issues": [1]},
    ]})
    decisions = _write_json(tmp_path / "decisions.json", {"decisions": []})
    source_map = _write_json(tmp_path / "source-map.json", {"1": 100})
    blocked = _write_json(tmp_path / "blocked.json", {"blocked_sources": []})
    assert combine_issues.close_eligible_main([
        "--inherited-plan-file", plan,
        "--write-results-file", writes,
        "--exception-decisions-file", decisions,
        "--source-to-combined-file", source_map,
        "--blocked-sources-file", blocked,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["eligible_by_combined"] == {"100": [1]}
    assert payload["ineligible_sources"] == []


def test_close_eligible_marks_multi_host_sources_ineligible(tmp_path: Path, capsys):
    plan = _write_json(tmp_path / "plan.json", {
        "status": "ok",
        "safe_edges": [],
        "exception_edges": [],
        "unknown_edges": [],
        "per_source_initial_eligibility": {"1": {"eligible": True, "reasons": []}},
    })
    writes = _write_json(tmp_path / "writes.json", {"write_results": []})
    decisions = _write_json(tmp_path / "decisions.json", {"decisions": []})
    source_map = _write_json(tmp_path / "source-map.json", {"1": [100, 101]})
    blocked = _write_json(tmp_path / "blocked.json", {"blocked_sources": []})
    assert combine_issues.close_eligible_main([
        "--inherited-plan-file", plan,
        "--write-results-file", writes,
        "--exception-decisions-file", decisions,
        "--source-to-combined-file", source_map,
        "--blocked-sources-file", blocked,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["eligible_by_combined"] == {}
    assert payload["ineligible_sources"] == [1]
    assert payload["reasons"]["1"] == ["multi_combined_host_closure_unsupported"]


def test_close_eligible_fails_closed_for_missing_failed_and_unresolved_edges(tmp_path: Path, capsys):
    plan = _write_json(tmp_path / "plan.json", {
        "status": "ok",
        "safe_edges": [
            {"edge": [100, 5], "source_issues": [1]},
            {"edge": [200, 7], "source_issues": [2]},
        ],
        "exception_edges": [{"edge": [8, 300], "source_issues": [3]}],
        "unknown_edges": [],
        "per_source_initial_eligibility": {
            "1": {"eligible": True, "reasons": []},
            "2": {"eligible": True, "reasons": []},
            "3": {"eligible": True, "reasons": []},
        },
    })
    writes = _write_json(tmp_path / "writes.json", {"write_results": [
        {"edge": [100, 5], "phase": "inherited_safe", "status": "failed", "source_issues": [1]},
    ]})
    decisions = _write_json(tmp_path / "decisions.json", {"decisions": [
        {"edge": [8, 300], "decision": "unresolved", "phase": "inherited_exception", "source_issues": [3], "reason": "operator cancelled"},
    ]})
    source_map = _write_json(tmp_path / "source-map.json", {"1": 100, "2": 200, "3": 300})
    blocked = _write_json(tmp_path / "blocked.json", {"blocked_sources": []})
    assert combine_issues.close_eligible_main([
        "--inherited-plan-file", plan,
        "--write-results-file", writes,
        "--exception-decisions-file", decisions,
        "--source-to-combined-file", source_map,
        "--blocked-sources-file", blocked,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["eligible_by_combined"] == {}
    assert payload["ineligible_sources"] == [1, 2, 3]
    assert "inherited_safe_write_missing_or_failed:100:5" in payload["reasons"]["1"]
    assert "inherited_safe_write_missing_or_failed:200:7" in payload["reasons"]["2"]
    assert "inherited_exception_unresolved:8:300" in payload["reasons"]["3"]


def test_close_eligible_allows_approved_exception_with_successful_write(tmp_path: Path, capsys):
    plan = _write_json(tmp_path / "plan.json", {
        "status": "ok",
        "safe_edges": [],
        "exception_edges": [{"edge": [6, 100], "source_issues": [1]}],
        "unknown_edges": [],
        "per_source_initial_eligibility": {"1": {"eligible": True, "reasons": []}},
    })
    writes = _write_json(tmp_path / "writes.json", {"write_results": [
        {"edge": [6, 100], "phase": "inherited_exception", "status": "written", "source_issues": [1]},
    ]})
    decisions = _write_json(tmp_path / "decisions.json", {"decisions": [
        {"edge": [6, 100], "decision": "approved", "phase": "inherited_exception", "source_issues": [1], "reason": "operator approved"},
    ]})
    source_map = _write_json(tmp_path / "source-map.json", {"1": 100})
    blocked = _write_json(tmp_path / "blocked.json", {"blocked_sources": []})
    assert combine_issues.close_eligible_main([
        "--inherited-plan-file", plan,
        "--write-results-file", writes,
        "--exception-decisions-file", decisions,
        "--source-to-combined-file", source_map,
        "--blocked-sources-file", blocked,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["eligible_by_combined"] == {"100": [1]}
    assert payload["ineligible_sources"] == []


def test_close_eligible_blocks_approved_exception_with_failed_write(tmp_path: Path, capsys):
    plan = _write_json(tmp_path / "plan.json", {
        "status": "ok",
        "safe_edges": [],
        "exception_edges": [{"edge": [6, 100], "source_issues": [1]}],
        "unknown_edges": [],
        "per_source_initial_eligibility": {"1": {"eligible": True, "reasons": []}},
    })
    writes = _write_json(tmp_path / "writes.json", {"write_results": [
        {"edge": [6, 100], "phase": "inherited_exception", "status": "failed", "source_issues": [1]},
    ]})
    decisions = _write_json(tmp_path / "decisions.json", {"decisions": [
        {"edge": [6, 100], "decision": "approved", "phase": "inherited_exception", "source_issues": [1], "reason": "operator approved"},
    ]})
    source_map = _write_json(tmp_path / "source-map.json", {"1": 100})
    blocked = _write_json(tmp_path / "blocked.json", {"blocked_sources": []})
    assert combine_issues.close_eligible_main([
        "--inherited-plan-file", plan,
        "--write-results-file", writes,
        "--exception-decisions-file", decisions,
        "--source-to-combined-file", source_map,
        "--blocked-sources-file", blocked,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["eligible_by_combined"] == {}
    assert payload["ineligible_sources"] == [1]
    assert "inherited_exception_write_failed:6:100" in payload["reasons"]["1"]


def test_close_eligible_requires_ok_plan_status_and_initial_coverage(tmp_path: Path, capsys):
    writes = _write_json(tmp_path / "writes.json", {"write_results": []})
    decisions = _write_json(tmp_path / "decisions.json", {"decisions": []})
    source_map = _write_json(tmp_path / "source-map.json", {"1": 100, "2": 200})
    blocked = _write_json(tmp_path / "blocked.json", {"blocked_sources": []})

    failed_plan = _write_json(tmp_path / "failed-plan.json", {
        "status": "failed",
        "safe_edges": [],
        "exception_edges": [],
        "unknown_edges": [],
        "per_source_initial_eligibility": {
            "1": {"eligible": True, "reasons": []},
            "2": {"eligible": True, "reasons": []},
        },
    })
    assert combine_issues.close_eligible_main([
        "--inherited-plan-file", failed_plan,
        "--write-results-file", writes,
        "--exception-decisions-file", decisions,
        "--source-to-combined-file", source_map,
        "--blocked-sources-file", blocked,
    ]) == 1
    assert "status must be 'ok'" in capsys.readouterr().err

    truncated_plan = _write_json(tmp_path / "truncated-plan.json", {
        "status": "ok",
        "safe_edges": [],
        "exception_edges": [],
        "unknown_edges": [],
        "per_source_initial_eligibility": {"1": {"eligible": True, "reasons": []}},
    })
    assert combine_issues.close_eligible_main([
        "--inherited-plan-file", truncated_plan,
        "--write-results-file", writes,
        "--exception-decisions-file", decisions,
        "--source-to-combined-file", source_map,
        "--blocked-sources-file", blocked,
    ]) == 1
    assert "missing per_source_initial_eligibility for source issues: 2" in capsys.readouterr().err


def test_apply_defer_close_creates_without_closing(monkeypatch, tmp_path: Path, capsys):
    body = tmp_path / "body.md"
    body.write_text("Combined body\n", encoding="utf-8")
    runner = ApplyRunner()
    monkeypatch.setattr(combine_issues.proc, "run", runner.run)
    assert combine_issues.apply_main([
        "--repo", "o/r",
        "--title", "T",
        "--body-file", str(body),
        "--source-issues", "1,2",
        "--defer-close",
    ]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["COMBINED_ISSUE"] == "99"
    assert out["SOURCE_ISSUES"] == "1,2"
    assert out["SOURCE_TO_COMBINED_JSON_FRAGMENT"] == '{"1":99,"2":99}'
    assert out["CLOSING_DEFERRED"] == "true"
    assert out["CLOSED_ISSUES"] == "0"
    assert not any(call[:3] == ["gh", "issue", "close"] for call in runner.calls)


def test_merge_source_to_combined_fragments_promotes_sorted_unique_arrays():
    merged = combine_issues._merge_source_to_combined_fragment(accumulated={}, fragment={"1": 99, "2": 101})
    assert merged == {"1": 99, "2": 101}
    merged = combine_issues._merge_source_to_combined_fragment(accumulated=merged, fragment={"1": 100})
    assert merged == {"1": [99, 100], "2": 101}
    merged = combine_issues._merge_source_to_combined_fragment(accumulated=merged, fragment={"1": [100, 99], "2": 101})
    assert merged == {"1": [99, 100], "2": 101}


def test_close_sources_reuses_close_comment_and_counts(monkeypatch, capsys):
    runner = ApplyRunner()
    monkeypatch.setattr(combine_issues.proc, "run", runner.run)
    monkeypatch.setattr(combine_issues, "_source_close_skip_reason", lambda **_kw: None)
    monkeypatch.setattr(combine_issues.time, "sleep", lambda _seconds: None)
    assert combine_issues.close_sources_main(["--repo", "o/r", "--combined-issue", "99", "--source-issues", "1,2"]) == 0
    out = capsys.readouterr().out
    assert "CLOSED_ISSUES=2" in out
    assert "PARTIAL=false" in out
    close_calls = [call for call in runner.calls if call[:3] == ["gh", "issue", "close"]]
    assert close_calls[0][:7] == ["gh", "issue", "close", "1", "--repo", "o/r", "--comment"]
    assert "Combined into #99" in close_calls[0][7]
    assert "larch:combined-away source=#1 target=#99" in close_calls[0][7]
    assert len(close_calls) == 3


def test_close_sources_skips_sources_that_became_busy(monkeypatch, capsys):
    class RefreshRunner:
        def __init__(self):
            self.calls: list[list[str]] = []

        def run(self, argv, **_kwargs):
            self.calls.append(list(argv))
            if argv[:3] == ["gh", "issue", "view"]:
                issue = argv[3]
                title = "[IMPLEMENTING] busy" if issue == "1" else "ready"
                return CommandResult(tuple(argv), 0, json.dumps({"title": title, "state": "OPEN"}), "", 0.01)
            if argv[:3] == ["gh", "issue", "close"]:
                return CommandResult(tuple(argv), 0, "", "", 0.01)
            return CommandResult(tuple(argv), 0, '{"nameWithOwner":"o/r"}', "", 0.01)

    runner = RefreshRunner()
    monkeypatch.setattr(combine_issues.proc, "run", runner.run)
    assert combine_issues.close_sources_main(["--repo", "o/r", "--combined-issue", "99", "--source-issues", "1,2"]) == 0
    captured = capsys.readouterr()
    assert "CLOSED_ISSUES=1" in captured.out
    assert "PARTIAL=true" in captured.out
    assert "Skipped #1: source issue has busy title prefix" in captured.err
    close_calls = [call for call in runner.calls if call[:3] == ["gh", "issue", "close"]]
    assert len(close_calls) == 1
    assert close_calls[0][:7] == ["gh", "issue", "close", "2", "--repo", "o/r", "--comment"]
    assert "Combined into #99" in close_calls[0][7]
    assert "larch:combined-away source=#2 target=#99" in close_calls[0][7]


def test_close_sources_warning_redacts_failed_close_stderr(monkeypatch, capsys):
    class CloseSourcesFailRunner:
        def run(self, argv, **_kwargs):
            if argv[:3] == ["gh", "issue", "close"]:
                return CommandResult(tuple(argv), 1, "", "failed with ghp_abcdefghijklmnopqrstuvwxyz0123456789", 0.01)
            return CommandResult(tuple(argv), 0, '{"nameWithOwner":"o/r"}', "", 0.01)

    monkeypatch.setattr(combine_issues.proc, "run", CloseSourcesFailRunner().run)
    monkeypatch.setattr(combine_issues, "_source_close_skip_reason", lambda **_kw: None)
    monkeypatch.setattr(combine_issues.time, "sleep", lambda _seconds: None)
    assert combine_issues.close_sources_main(["--repo", "o/r", "--combined-issue", "99", "--source-issues", "1"]) == 0
    captured = capsys.readouterr()
    assert "WARNING=Failed to close #1:" in captured.err
    assert "ghp_abcdefghijklmnopqrstuvwxyz0123456789" not in captured.err
    assert "CLOSED_ISSUES=0" in captured.out
    assert "PARTIAL=true" in captured.out


def test_close_stale_rejects_invalid_reason_before_close(monkeypatch, capsys):
    calls = []

    def run(argv, **_kwargs):
        calls.append(list(argv))
        return CommandResult(tuple(argv), 0, "", "", 0.01)

    monkeypatch.setattr(combine_issues.proc, "run", run)
    assert combine_issues.close_stale_main(["--repo", "o/r", "--issues", "1", "--reason", "stale"]) == 1
    assert "ERROR=--reason must be one of: completed, not planned" in capsys.readouterr().err
    assert not any(call[:3] == ["gh", "issue", "close"] for call in calls)


def test_close_stale_rejects_missing_comment_file_before_close(monkeypatch, tmp_path: Path, capsys):
    calls = []

    def run(argv, **_kwargs):
        calls.append(list(argv))
        return CommandResult(tuple(argv), 0, "", "", 0.01)

    monkeypatch.setattr(combine_issues.proc, "run", run)
    missing = tmp_path / "missing.md"
    assert combine_issues.close_stale_main([
        "--repo", "o/r",
        "--issues", "1",
        "--reason", "not planned",
        "--comment-file", str(missing),
    ]) == 1
    assert "ERROR=Missing or unreadable --comment-file" in capsys.readouterr().err
    assert not any(call[:3] == ["gh", "issue", "close"] for call in calls)


def test_close_stale_dry_run_does_not_close(monkeypatch, capsys):
    calls = []

    def run(argv, **_kwargs):
        calls.append(list(argv))
        return CommandResult(tuple(argv), 0, "", "", 0.01)

    monkeypatch.setattr(combine_issues.proc, "run", run)
    assert combine_issues.close_stale_main([
        "--repo", "o/r",
        "--issues", "1,2",
        "--reason", "not planned",
        "--dry-run",
    ]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out == ["DRY_RUN=true", "WOULD_CLOSE=1,2", "CLOSED_ISSUES=0", "PARTIAL=false"]
    assert not any(call[:3] == ["gh", "issue", "close"] for call in calls)


def test_close_stale_live_success_with_comment(monkeypatch, tmp_path: Path, capsys):
    calls = []

    def run(argv, **_kwargs):
        calls.append(list(argv))
        if argv[:3] == ["gh", "issue", "close"]:
            return CommandResult(tuple(argv), 0, "", "", 0.01)
        return CommandResult(tuple(argv), 0, '{"nameWithOwner":"o/r"}', "", 0.01)

    comment = tmp_path / "comment.md"
    comment.write_text("Stale discard summary\n", encoding="utf-8")
    monkeypatch.setattr(combine_issues.proc, "run", run)
    monkeypatch.setattr(combine_issues, "_source_close_skip_reason", lambda **_kw: None)
    assert combine_issues.close_stale_main([
        "--repo", "o/r",
        "--issues", "1",
        "--reason", "not planned",
        "--comment-file", str(comment),
    ]) == 0
    captured = capsys.readouterr()
    assert "CLOSED_ISSUES=1" in captured.out
    assert "PARTIAL=false" in captured.out
    assert calls == [["gh", "issue", "close", "1", "--repo", "o/r", "--reason", "not planned", "--comment", "Stale discard summary\n"]]


def test_close_stale_skip_path_sets_partial(monkeypatch, capsys):
    calls = []

    def run(argv, **_kwargs):
        calls.append(list(argv))
        return CommandResult(tuple(argv), 0, "", "", 0.01)

    def skip(*, repo, source):
        _ = repo
        return "source issue is not open (CLOSED)" if source == 1 else None

    monkeypatch.setattr(combine_issues.proc, "run", run)
    monkeypatch.setattr(combine_issues, "_source_close_skip_reason", skip)
    assert combine_issues.close_stale_main(["--repo", "o/r", "--issues", "1,2", "--reason", "completed"]) == 0
    captured = capsys.readouterr()
    assert "CLOSED_ISSUES=1" in captured.out
    assert "PARTIAL=true" in captured.out
    assert "WARNING=Skipped #1: source issue is not open (CLOSED)" in captured.err
    assert calls == [["gh", "issue", "close", "2", "--repo", "o/r", "--reason", "completed"]]


def test_close_stale_warning_redacts_failed_close_stderr(monkeypatch, capsys):
    class CloseStaleFailRunner:
        def run(self, argv, **_kwargs):
            if argv[:3] == ["gh", "issue", "close"]:
                return CommandResult(tuple(argv), 1, "", "failed with ghp_abcdefghijklmnopqrstuvwxyz0123456789", 0.01)
            return CommandResult(tuple(argv), 0, '{"nameWithOwner":"o/r"}', "", 0.01)

    monkeypatch.setattr(combine_issues.proc, "run", CloseStaleFailRunner().run)
    monkeypatch.setattr(combine_issues, "_source_close_skip_reason", lambda **_kw: None)
    assert combine_issues.close_stale_main(["--repo", "o/r", "--issues", "1", "--reason", "not planned"]) == 0
    captured = capsys.readouterr()
    assert "WARNING=Failed to close #1:" in captured.err
    assert "ghp_abcdefghijklmnopqrstuvwxyz0123456789" not in captured.err
    assert "CLOSED_ISSUES=0" in captured.out
    assert "PARTIAL=true" in captured.out


def test_list_open_uses_paginated_api_and_filters_pulls_and_closed(monkeypatch, capsys):
    class OpenRunner:
        def __init__(self):
            self.calls = []
        def run(self, argv, **_kwargs):
            self.calls.append(list(argv))
            rows1 = [
                {"number": 1, "title": "open", "state": "open", "body": "b", "labels": []},
                {"number": 2, "title": "pr", "state": "open", "pull_request": {}},
            ]
            rows2 = [
                {"number": 3, "title": "research archival", "state": "open"},
                {"number": 4, "title": "closed", "state": "closed"},
            ]
            return CommandResult(tuple(argv), 0, json.dumps(rows1) + json.dumps(rows2), "", 0.01)
    runner = OpenRunner()
    monkeypatch.setattr(combine_issues.proc, "run", runner.run)
    assert combine_issues.list_open_main(["--repo", "o/r"]) == 0
    assert runner.calls == [["gh", "api", "--paginate", "repos/o/r/issues?state=open&per_page=100"]]
    payload = json.loads(capsys.readouterr().out)
    assert [row["number"] for row in payload["issues"]] == [1, 3]


def test_list_open_fails_closed_on_gh_or_json_errors(monkeypatch, capsys):
    class FailingOpenRunner:
        def run(self, argv, **_kwargs):
            return CommandResult(tuple(argv), 1, "", "network down", 0.01)

    monkeypatch.setattr(combine_issues.proc, "run", FailingOpenRunner().run)
    assert combine_issues.list_open_main(["--repo", "o/r"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "failed"
    assert payload["warnings"][0]["code"] == "gh_api_failed"

    class InvalidJsonRunner:
        def run(self, argv, **_kwargs):
            return CommandResult(tuple(argv), 0, "not json", "", 0.01)

    monkeypatch.setattr(combine_issues.proc, "run", InvalidJsonRunner().run)
    assert combine_issues.list_open_main(["--repo", "o/r"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "failed"
    assert payload["warnings"][0]["code"] == "json_invalid"


def test_prose_audit_remaps_sources_parses_blocks_and_dedupes_existing(monkeypatch, tmp_path: Path, capsys):
    open_issues = _write_json(tmp_path / "open.json", {"issues": [
        {"number": 100, "title": "[OOS] combined", "state": "open", "body": ""},
        {"number": 5, "title": "open client", "state": "open", "body": ""},
        {"number": 6, "title": "open blocker", "state": "open", "body": ""},
    ]})
    existing = _write_json(tmp_path / "existing.json", [[100, 5]])
    source_map = _write_json(tmp_path / "source-map.json", {"77": 100})

    def view(_runner, issue, field, *, repo, cwd=None):
        assert repo == "o/r"
        assert field == "title,body,state"
        assert cwd is None
        bodies = {
            "100": "Blocked by #5\nBlocks #6\nBlocked by #77",
            "5": "Blocked by #100",
            "6": "No numeric blockers here",
        }
        return CommandResult(("gh",), 0, json.dumps({"title": "t", "body": bodies.get(issue, ""), "state": "OPEN"}), "", 0.01)

    def comments(_runner, issue, *, repo, cwd=None):
        assert repo == "o/r"
        assert cwd is None
        if issue == "6":
            return CommandResult(("gh",), 0, json.dumps([{"id": 500, "body": "Blocks #100"}]), "", 0.01)
        return CommandResult(("gh",), 0, "[]", "", 0.01)

    monkeypatch.setattr(combine_issues.gh, "issue_view_field_read", view)
    monkeypatch.setattr(combine_issues.gh, "issue_comments_list_read", comments)
    assert combine_issues.prose_audit_main([
        "--repo", "o/r",
        "--combined-issues", "100",
        "--open-issues-file", open_issues,
        "--existing-edges-file", existing,
        "--source-to-combined-file", source_map,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    edges = {tuple(row["edge"]) for row in payload["candidates"]}
    assert (100, 5) not in edges
    assert edges == {(6, 100), (5, 100), (100, 6)}
    assert any(row.get("evidence_comment_id") == 500 for row in payload["candidates"])


def test_prose_audit_keeps_combined_endpoints_missing_from_open_metadata(monkeypatch, tmp_path: Path, capsys):
    open_issues = _write_json(tmp_path / "open.json", {"issues": [
        {"number": 5, "title": "open client", "state": "open", "body": ""},
    ]})
    existing = _write_json(tmp_path / "existing.json", [])
    source_map = _write_json(tmp_path / "source-map.json", {})

    def view(_runner, issue, field, *, repo, cwd=None):
        assert repo == "o/r"
        assert field == "title,body,state"
        assert cwd is None
        bodies = {
            "100": "Blocked by #5",
            "5": "Blocked by #100",
        }
        return CommandResult(("gh",), 0, json.dumps({"title": "t", "body": bodies.get(issue, ""), "state": "OPEN"}), "", 0.01)

    monkeypatch.setattr(combine_issues.gh, "issue_view_field_read", view)
    monkeypatch.setattr(combine_issues.gh, "issue_comments_list_read", lambda *_args, **_kwargs: CommandResult(("gh",), 0, "[]", "", 0.01))
    assert combine_issues.prose_audit_main([
        "--repo", "o/r",
        "--combined-issues", "100",
        "--open-issues-file", open_issues,
        "--existing-edges-file", existing,
        "--source-to-combined-file", source_map,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert {tuple(row["edge"]) for row in payload["candidates"]} == {(5, 100), (100, 5)}


def test_prose_audit_blocks_parser_ignores_examples_negation_and_code(monkeypatch, tmp_path: Path, capsys):
    open_issues = _write_json(tmp_path / "open.json", {"issues": [
        {"number": 100, "title": "[OOS] combined", "state": "open", "body": ""},
        {"number": 6, "title": "open blocker", "state": "open", "body": ""},
    ]})
    existing = _write_json(tmp_path / "existing.json", [])
    source_map = _write_json(tmp_path / "source-map.json", {})

    def view(_runner, issue, field, *, repo, cwd=None):
        assert repo == "o/r"
        assert field == "title,body,state"
        assert cwd is None
        if issue == "100":
            body = (
                "Inline `Blocks #6` example\n"
                "Example: Blocks #6\n"
                "This does not block #6\n"
                "not Blocking #6\n"
                "```\n"
                "Blocks #6\n"
                "```"
            )
        else:
            body = ""
        return CommandResult(("gh",), 0, json.dumps({"title": "t", "body": body, "state": "OPEN"}), "", 0.01)

    monkeypatch.setattr(combine_issues.gh, "issue_view_field_read", view)
    monkeypatch.setattr(combine_issues.gh, "issue_comments_list_read", lambda *_args, **_kwargs: CommandResult(("gh",), 0, "[]", "", 0.01))
    assert combine_issues.prose_audit_main([
        "--repo", "o/r",
        "--combined-issues", "100",
        "--open-issues-file", open_issues,
        "--existing-edges-file", existing,
        "--source-to-combined-file", source_map,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["candidates"] == []


def test_prose_audit_fails_closed_on_comment_read_error(monkeypatch, tmp_path: Path, capsys):
    open_issues = _write_json(tmp_path / "open.json", {"status": "ok", "issues": [
        {"number": 100, "title": "[OOS] combined", "state": "open", "body": ""},
    ]})
    existing = _write_json(tmp_path / "existing.json", [])
    source_map = _write_json(tmp_path / "source-map.json", {})

    monkeypatch.setattr(
        combine_issues.gh,
        "issue_view_field_read",
        lambda *_args, **_kwargs: CommandResult(("gh",), 0, json.dumps({"title": "t", "body": "", "state": "OPEN"}), "", 0.01),
    )
    monkeypatch.setattr(
        combine_issues.gh,
        "issue_comments_list_read",
        lambda *_args, **_kwargs: CommandResult(("gh",), 1, "", "network down", 0.01),
    )
    assert combine_issues.prose_audit_main([
        "--repo", "o/r",
        "--combined-issues", "100",
        "--open-issues-file", open_issues,
        "--existing-edges-file", existing,
        "--source-to-combined-file", source_map,
    ]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "failed"
    assert payload["warnings"][0]["code"] == "comments_read_failed"


def test_prose_audit_drops_edges_for_closed_refreshed_issue(monkeypatch, tmp_path: Path, capsys):
    open_issues = _write_json(tmp_path / "open.json", {"status": "ok", "issues": [
        {"number": 5, "title": "stale open", "state": "open", "body": ""},
    ]})
    existing = _write_json(tmp_path / "existing.json", [])
    source_map = _write_json(tmp_path / "source-map.json", {})

    def view(_runner, issue, field, *, repo, cwd=None):
        assert repo == "o/r"
        assert field == "title,body,state"
        assert cwd is None
        state = "CLOSED" if issue == "5" else "OPEN"
        body = "Blocked by #100" if issue == "5" else "Blocked by #5"
        return CommandResult(("gh",), 0, json.dumps({"title": "t", "body": body, "state": state}), "", 0.01)

    monkeypatch.setattr(combine_issues.gh, "issue_view_field_read", view)
    monkeypatch.setattr(combine_issues.gh, "issue_comments_list_read", lambda *_args, **_kwargs: CommandResult(("gh",), 0, "[]", "", 0.01))
    assert combine_issues.prose_audit_main([
        "--repo", "o/r",
        "--combined-issues", "100",
        "--open-issues-file", open_issues,
        "--existing-edges-file", existing,
        "--source-to-combined-file", source_map,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["candidates"] == []


def test_plan_audit_splits_tier1_safe_exceptions_and_tier2(tmp_path: Path, capsys):
    prose = _write_json(tmp_path / "prose.json", {"candidates": [
        {"edge": [100, 5], "source_kind": "tier1_prose", "confidence": "explicit", "reason": "combined blocked by open"},
        {"edge": [5, 100], "source_kind": "tier1_prose", "confidence": "explicit", "reason": "open blocked by oos"},
    ]})
    tier2 = _write_json(tmp_path / "tier2.json", {"candidates": [
        {"edge": [100, 6], "source_kind": "tier2_semantic", "confidence": "medium", "reason": "semantic dependency"},
    ]})
    existing = _write_json(tmp_path / "existing.json", [])
    decided = _write_json(tmp_path / "decided.json", {"decisions": []})
    open_issues = _write_json(tmp_path / "open.json", {"issues": [
        {"number": 5, "title": "normal", "state": "open"},
        {"number": 6, "title": "normal two", "state": "open"},
    ]})
    combined = _write_json(tmp_path / "combined.json", [{"number": 100, "title": "[OOS] combined", "source_issues": [1]}])
    assert combine_issues.plan_audit_main([
        "--prose-candidates-file", prose,
        "--tier2-candidates-file", tier2,
        "--existing-edges-file", existing,
        "--decided-edges-file", decided,
        "--open-issues-file", open_issues,
        "--combined-issues-file", combined,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [row["edge"] for row in payload["auto_write_edges"]] == [[100, 5]]
    approval_edges = {tuple(row["edge"]) for row in payload["approval_required_edges"]}
    assert approval_edges == {(5, 100), (100, 6)}


def test_plan_audit_uses_refreshed_open_title_for_combined_oos(tmp_path: Path, capsys):
    prose = _write_json(tmp_path / "prose.json", {"candidates": [
        {"edge": [5, 100], "source_kind": "tier1_prose", "confidence": "explicit", "reason": "open blocked by oos"},
    ]})
    tier2 = _write_json(tmp_path / "tier2.json", {"candidates": []})
    existing = _write_json(tmp_path / "existing.json", [])
    decided = _write_json(tmp_path / "decided.json", {"decisions": []})
    open_issues = _write_json(tmp_path / "open.json", {"issues": [
        {"number": 5, "title": "normal", "state": "open"},
        {"number": 100, "title": "[OOS] live title", "state": "open"},
    ]})
    combined = _write_json(tmp_path / "combined.json", [{"number": 100, "title": "stale snapshot", "source_issues": [1]}])
    assert combine_issues.plan_audit_main([
        "--prose-candidates-file", prose,
        "--tier2-candidates-file", tier2,
        "--existing-edges-file", existing,
        "--decided-edges-file", decided,
        "--open-issues-file", open_issues,
        "--combined-issues-file", combined,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["auto_write_edges"] == []
    assert [row["edge"] for row in payload["approval_required_edges"]] == [[5, 100]]
    assert payload["approval_required_edges"][0]["blocker_issue"] == 100


def test_plan_audit_retries_approved_edge_absent_from_existing(tmp_path: Path, capsys):
    prose = _write_json(tmp_path / "prose.json", {"candidates": [
        {"edge": [100, 5], "source_kind": "tier1_prose", "confidence": "explicit", "reason": "combined blocked by open"},
    ]})
    tier2 = _write_json(tmp_path / "tier2.json", {"candidates": []})
    existing = _write_json(tmp_path / "existing.json", [])
    decided = _write_json(tmp_path / "decided.json", {"decisions": [
        {"edge": [100, 5], "decision": "approved"},
    ]})
    open_issues = _write_json(tmp_path / "open.json", {"status": "ok", "issues": [
        {"number": 5, "title": "normal", "state": "open"},
    ]})
    combined = _write_json(tmp_path / "combined.json", [{"number": 100, "title": "[OOS] combined", "source_issues": [1]}])
    assert combine_issues.plan_audit_main([
        "--prose-candidates-file", prose,
        "--tier2-candidates-file", tier2,
        "--existing-edges-file", existing,
        "--decided-edges-file", decided,
        "--open-issues-file", open_issues,
        "--combined-issues-file", combined,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [row["edge"] for row in payload["auto_write_edges"]] == [[100, 5]]
    assert payload["duplicate_edges_skipped"] == 0


def test_plan_audit_rejects_malformed_tier2_source_kind(tmp_path: Path, capsys):
    prose = _write_json(tmp_path / "prose.json", {"candidates": []})
    tier2 = _write_json(tmp_path / "tier2.json", {"candidates": [
        {"edge": [100, 6], "confidence": "medium", "reason": "semantic dependency"},
    ]})
    existing = _write_json(tmp_path / "existing.json", [])
    decided = _write_json(tmp_path / "decided.json", {"decisions": []})
    open_issues = _write_json(tmp_path / "open.json", {"issues": [
        {"number": 6, "title": "normal", "state": "open"},
    ]})
    combined = _write_json(tmp_path / "combined.json", [{"number": 100, "title": "[OOS] combined", "source_issues": [1]}])
    assert combine_issues.plan_audit_main([
        "--prose-candidates-file", prose,
        "--tier2-candidates-file", tier2,
        "--existing-edges-file", existing,
        "--decided-edges-file", decided,
        "--open-issues-file", open_issues,
        "--combined-issues-file", combined,
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["auto_write_edges"] == []
    assert payload["approval_required_edges"] == []
    assert [row["edge"] for row in payload["policy_rejected_edges"]] == [[100, 6]]
    assert payload["policy_rejected_edges"][0]["policy_reason"] == "tier2 candidate must declare source_kind=tier2_semantic"
