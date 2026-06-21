# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# pylint: skip-file
"""Smoke tests for analyze issue entrypoints."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import analyze_issues
import render_chart


def test_render_chart_smoke() -> None:
    assert "Cumulative growth chart" in render_chart.render_chart(["2026-01"], [("A", "Bug", [1])])


def test_analyze_fixture_runs(tmp_path: Path, capsys) -> None:
    fixture = tmp_path / "issues.json"
    fixture.write_text(json.dumps([{"number": 1, "title": "Fix bug", "state": "OPEN", "createdAt": "2026-01-01T00:00:00Z", "body": "", "labels": []}]), encoding="utf-8")
    assert analyze_issues.analyze_main(["--json", str(fixture), "--top-k", "1"]) == 0
    assert "Bug fix" in capsys.readouterr().out


def test_analyze_rich_fixture_pins_categories_duplicates_and_reviewers(capsys) -> None:
    fixture = Path(__file__).with_name("analyze-issues-fixture.json")
    assert analyze_issues.analyze_main(["--json", str(fixture), "--top-k", "3"]) == 0
    out = capsys.readouterr().out
    assert "Bug fix: 3 (" in out
    assert "Documentation/contract drift: 2 (" in out
    assert "Other: 1 (" in out
    assert "Auto-spawned share: 1/10" in out
    assert "bug fix: crash in foo" in out
    assert "codex" in out
    assert "YES=2 NO=1" in out


def test_fetch_writes_private_output(monkeypatch, tmp_path: Path) -> None:
    def fake_run(argv, stdout, **_kwargs):
        stdout.write("[]\n")
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    output = tmp_path / "issues.json"
    assert analyze_issues.fetch_main(["--repo", "o/r", "--limit", "10", "--output", str(output)]) == 0
    assert output.stat().st_mode & 0o777 == 0o600


def test_load_issues_duplicate_first_wins_and_warns(tmp_path: Path, capsys) -> None:
    fixture = tmp_path / "issues.json"
    fixture.write_text(json.dumps([
        {"number": "7", "title": "first", "body": "a"},
        {"number": 7, "title": "second", "body": "b"},
    ]), encoding="utf-8")
    issues = analyze_issues.load_issues(str(fixture), lenient=True)
    assert [issue["title"] for issue in issues] == ["first"]
    assert "skipping duplicate parsed number 7" in capsys.readouterr().err


def test_load_issues_skip_threshold_aborts_unless_lenient(tmp_path: Path) -> None:
    fixture = tmp_path / "issues.json"
    fixture.write_text(json.dumps([
        {"number": 1, "title": "valid", "body": ""},
        "bad",
    ]), encoding="utf-8")
    with pytest.raises(SystemExit, match="pass --lenient"):
        analyze_issues.load_issues(str(fixture))
    assert len(analyze_issues.load_issues(str(fixture), lenient=True)) == 1


def test_run_main_forwards_lenient_to_analyzer(monkeypatch, tmp_path: Path) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(analyze_issues, "_detect_repo", lambda: "o/r")
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    def fake_fetch(argv):
        seen["fetch"] = list(argv)
        output = Path(list(argv)[list(argv).index("--output") + 1])
        output.write_text(json.dumps([{"number": 1, "title": "Fix bug", "state": "OPEN", "createdAt": "2026-01-01T00:00:00Z", "body": "", "labels": []}]), encoding="utf-8")
        return 0

    monkeypatch.setattr(analyze_issues, "fetch_main", fake_fetch)
    monkeypatch.setattr(analyze_issues, "iter_filed_oos_records", lambda _root: [])

    assert analyze_issues.run_main(["--lenient"]) == 0
    assert seen["fetch"]


def test_fate_adjusted_open_and_not_planned_from_logs(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "implement" / "run-1"
    (run / "round-1").mkdir(parents=True)
    (run / "round-1" / "oos-accepted-review.md").write_text(
        "### OOS_1: keep\n- **Reviewer(s)**: codex, cursor\n\n"
        "### OOS_2: dock\n- **Reviewer**: claude\n",
        encoding="utf-8",
    )
    (run / "oos-issues.ndjson").write_text(
        json.dumps({"title": "keep", "body": "- **Stable ID**: oos-accepted-review:OOS_1\n- **Filed URL**: https://github.com/o/r/issues/10"}) + "\n"
        + json.dumps({"title": "dock", "body": "- **Stable ID**: oos-accepted-review:OOS_2\n- **Filed URL**: https://github.com/o/r/issues/11"}) + "\n",
        encoding="utf-8",
    )
    issues = [
        {"number": 10, "title": "keep", "state": "OPEN", "body": "", "labels": []},
        {"number": 11, "title": "dock", "state": "CLOSED", "stateReason": "NOT_PLANNED", "body": "", "labels": []},
    ]
    text, stats = analyze_issues.fate_adjusted_oos_scoring(issues, log_root, filed_issue_details={})
    assert "## Fate-adjusted OOS Scoring" in text
    assert "- codex: provisional 1, adjusted 1, docked 0" in text
    assert "- cursor: provisional 1, adjusted 1, docked 0" in text
    assert "- claude: provisional 1, adjusted 0, docked 1" in text
    assert stats["totals"] == {"provisional": 3, "adjusted": 2, "docked": 1}


def test_duplicate_identical_oos_evidence_counts_once(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "implement" / "run-1"
    (run / "round-1").mkdir(parents=True)
    (run / "round-1" / "oos-accepted-review.md").write_text("### OOS_1: keep\n- **Reviewer**: codex\n", encoding="utf-8")
    row = json.dumps({"title": "keep", "body": "- **Stable ID**: oos-accepted-review:OOS_1\n- **Filed URL**: https://github.com/o/r/issues/10"})
    (run / "oos-issues.ndjson").write_text(row + "\n" + row + "\n", encoding="utf-8")
    issues = [{"number": 10, "title": "keep", "state": "OPEN", "body": "", "labels": []}]
    _text, stats = analyze_issues.fate_adjusted_oos_scoring(issues, log_root, filed_issue_details={})
    assert stats["totals"] == {"provisional": 1, "adjusted": 1, "docked": 0}
    assert stats["buckets"]["provisional open"] == 1


def test_combined_away_comment_docks_and_comment_objects_normalize() -> None:
    issue = {
        "number": 12,
        "state": "CLOSED",
        "comments": [{"body": "Combined into #99"}, "extra"],
        "closedByPullRequestsReferences": [],
    }
    assert analyze_issues.issue_comments(issue) == ["Combined into #99", "extra"]
    fate = analyze_issues.classify_oos_issue_fate(issue)
    assert fate["bucket"] == "docked combined-away"
    assert fate["adjusted"] == 0


def test_extract_filed_issue_number_ignores_arbitrary_refs() -> None:
    assert analyze_issues.extract_filed_issue_number_from_text("Finding mentions #4683 only.") is None
    assert analyze_issues.extract_filed_issue_number_from_text("Filed OOS issue #3435") == 3435
    assert analyze_issues.extract_filed_issue_number_from_text("- **Filed URL**: https://github.com/o/r/issues/42") == 42
    assert analyze_issues.extract_filed_issue_number_from_text("| OOS title | #43 | https://github.com/o/r/issues/43 |") == 43


def test_design_oos_file_map_joins_reviewer(tmp_path: Path) -> None:
    run = tmp_path / "larch-logs" / "design" / "design-run"
    run.mkdir(parents=True)
    (run / "oos-accepted-design.md").write_text("### OOS_7: design item\n- **Reviewer**: architect\n", encoding="utf-8")
    (run / "oos-issues-created.md").write_text("OOS_FILE_MAP\t7\thttps://github.com/o/r/issues/77\n", encoding="utf-8")
    rows = analyze_issues.iter_filed_oos_records(tmp_path / "larch-logs")
    assert rows[0]["reviewer"] == "architect"
    assert rows[0]["issue_number"] == 77


def test_run_main_fetches_targeted_details(monkeypatch, tmp_path: Path, capsys) -> None:
    log_root = tmp_path / "logs"
    run = log_root / "implement" / "run-1"
    (run / "round-1").mkdir(parents=True)
    (run / "round-1" / "oos-accepted-review.md").write_text("### OOS_1: item\n- **Reviewer**: codex\n", encoding="utf-8")
    (run / "oos-issues.ndjson").write_text(json.dumps({"body": "- **Stable ID**: oos-accepted-review:OOS_1\n- **Filed URL**: https://github.com/o/r/issues/9"}) + "\n", encoding="utf-8")
    monkeypatch.setenv("TMPDIR", str(tmp_path))

    def fake_fetch(argv):
        output = Path(list(argv)[list(argv).index("--output") + 1])
        output.write_text(json.dumps([]), encoding="utf-8")
        return 0

    seen: dict[str, object] = {}
    monkeypatch.setattr(analyze_issues, "fetch_main", fake_fetch)
    def fake_details(repo, numbers):
        seen["fetch"] = (repo, numbers)
        return {9: {"number": 9, "state": "CLOSED", "closedByPullRequestsReferences": [{"number": 1}]}}

    monkeypatch.setattr(analyze_issues, "_fetch_filed_oos_issue_details", fake_details)
    assert analyze_issues.run_main(["--repo", "o/r", "--log-root", str(log_root)]) == 0
    assert seen["fetch"] == ("o/r", {9})
    assert "kept by PR: 1" in capsys.readouterr().out


def test_main_appends_fate_section_after_reviewer_tables(tmp_path: Path, capsys) -> None:
    fixture = tmp_path / "issues.json"
    fixture.write_text(json.dumps([{"number": 1, "title": "Fix bug", "state": "OPEN", "createdAt": "2026-01-01T00:00:00Z", "body": "", "labels": []}]), encoding="utf-8")
    assert analyze_issues.analyze_main(["--json", str(fixture), "--log-root", str(tmp_path / "missing")]) == 0
    out = capsys.readouterr().out
    assert out.index("## Reviewer/Persona Tables") < out.index("## Fate-adjusted OOS Scoring")
    assert "No filed OOS run-log evidence found." in out


def test_fetch_main_retries_without_optional_fields(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(argv, stdout, **_kwargs):
        calls.append(list(argv))
        if "stateReason" in argv[-1]:
            return subprocess.CompletedProcess(argv, 1)
        stdout.write(json.dumps([{"number": 1, "title": "t"}]))
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    output = tmp_path / "issues.json"
    assert analyze_issues.fetch_main(["--repo", "o/r", "--limit", "10", "--output", str(output)]) == 0
    assert len(calls) == 2
    assert "stateReason" in calls[0][-1]
    assert "stateReason" not in calls[1][-1]
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload[0]["_larch_degraded_fields"] == ["stateReason", "url"]


def test_legacy_stable_id_extraction_ignores_pre_filed_tokens() -> None:
    body = (
        "Finding mentions OOS_5 and #4683 in prose.\n"
        "- **Filed URL**: https://github.com/o/r/issues/42\n"
    )
    assert analyze_issues._extract_legacy_stable_ids_from_ndjson_body(body) == []


def test_main_agent_stable_id_joins_review_block(tmp_path: Path) -> None:
    run = tmp_path / "implement" / "run-1"
    (run / "round-1").mkdir(parents=True)
    (run / "round-1" / "oos-accepted-review.md").write_text(
        "### OOS_1: item\n- **Reviewer**: codex\n",
        encoding="utf-8",
    )
    (run / "oos-issues.ndjson").write_text(
        json.dumps({"body": "- **Stable ID**: oos-accepted-main-agent:OOS_1\n- **Filed URL**: https://github.com/o/r/issues/10"}) + "\n",
        encoding="utf-8",
    )
    rows = analyze_issues._join_implement_run_records(run)
    assert rows[0]["reviewer"] == "codex"


def test_cap_rollup_ambiguous_expansion_scores_no_partial_members(tmp_path: Path) -> None:
    run = tmp_path / "implement" / "run-1"
    (run / "round-1").mkdir(parents=True)
    review_md = run / "round-1" / "oos-accepted-review.md"
    review_md.write_text(
        "### OOS_1: one\n- **Reviewer**: codex\n\n"
        + "".join(f"### OOS_{idx}: extra {idx}\n- **Reviewer**: r{idx}\n\n" for idx in range(2, 9)),
        encoding="utf-8",
    )
    (run / "oos-issues.ndjson").write_text(
        json.dumps({
            "title": "Aggregated rollup of 3 capped OOS items",
            "body": (
                "- **Stable ID**: oos-accepted-review:OOS_1\n"
                "- **Filed URL**: https://github.com/o/r/issues/10\n"
            ),
        }) + "\n",
        encoding="utf-8",
    )
    rows = analyze_issues._join_implement_run_records(run)
    assert len(rows) == 1
    assert rows[0]["bucket"] == "ambiguous rollup expansion"
    issues = [{"number": 10, "title": "one", "state": "OPEN", "body": "", "labels": []}]
    _text, stats = analyze_issues.fate_adjusted_oos_scoring(issues, tmp_path, filed_issue_details={})
    assert stats["totals"] == {"provisional": 0, "adjusted": 0, "docked": 0}
    assert stats["buckets"]["ambiguous rollup expansion"] == 1


def test_stable_id_collision_marks_ambiguous(tmp_path: Path) -> None:
    run = tmp_path / "implement" / "run-1"
    (run / "round-1").mkdir(parents=True)
    (run / "round-1" / "oos-accepted-review.md").write_text(
        "### OOS_1: first\n- **Reviewer**: codex\n",
        encoding="utf-8",
    )
    (run / "round-2").mkdir(parents=True)
    (run / "round-2" / "oos-accepted-review.md").write_text(
        "### OOS_1: second\n- **Reviewer**: cursor\n",
        encoding="utf-8",
    )
    (run / "oos-issues.ndjson").write_text(
        json.dumps({"body": "- **Stable ID**: oos-accepted-review:OOS_1\n- **Filed URL**: https://github.com/o/r/issues/10"}) + "\n",
        encoding="utf-8",
    )
    rows = analyze_issues._join_implement_run_records(run)
    assert len(rows) == 1
    assert rows[0]["bucket"] == "ambiguous stable id"


def test_merged_issue_index_clears_degraded_state_reason_from_sidecar() -> None:
    issues = [{"number": 1, "title": "t", "state": "CLOSED", "_larch_degraded_fields": ["stateReason"]}]
    details = {1: {"stateReason": "NOT_PLANNED"}}
    index = analyze_issues._merged_issue_index(issues, details)
    assert "stateReason" not in (index[1].get("_larch_degraded_fields") or [])
    fate = analyze_issues.classify_oos_issue_fate(index[1])
    assert fate["bucket"] == "docked closed-unfixed"


def test_design_oos_bare_url_recovery_requires_filed_shapes(tmp_path: Path) -> None:
    run = tmp_path / "design" / "run-1"
    run.mkdir(parents=True)
    (run / "oos-issues-created.md").write_text(
        "See https://github.com/o/r/issues/99 for notes\n"
        "- **Filed URL**: https://github.com/o/r/issues/42\n",
        encoding="utf-8",
    )
    rows = analyze_issues._parse_oos_issues_created(run / "oos-issues-created.md", accepted_design_path=None)
    assert len(rows) == 1
    assert rows[0]["issue_number"] == 42


def test_run_main_fetches_targeted_details_after_bulk_failure(monkeypatch, tmp_path: Path, capsys) -> None:
    log_root = tmp_path / "logs"
    run = log_root / "implement" / "run-1"
    (run / "round-1").mkdir(parents=True)
    (run / "round-1" / "oos-accepted-review.md").write_text("### OOS_1: item\n- **Reviewer**: codex\n", encoding="utf-8")
    (run / "oos-issues.ndjson").write_text(json.dumps({"body": "- **Stable ID**: oos-accepted-review:OOS_1\n- **Filed URL**: https://github.com/o/r/issues/9"}) + "\n", encoding="utf-8")
    monkeypatch.setenv("TMPDIR", str(tmp_path))

    def fake_fetch(_argv):
        return 1

    seen: dict[str, object] = {}
    monkeypatch.setattr(analyze_issues, "fetch_main", fake_fetch)

    def fake_details(repo, numbers):
        seen["fetch"] = (repo, numbers)
        return {9: {"number": 9, "state": "CLOSED", "closedByPullRequestsReferences": [{"number": 1}]}}

    monkeypatch.setattr(analyze_issues, "_fetch_filed_oos_issue_details", fake_details)
    assert analyze_issues.run_main(["--repo", "o/r", "--log-root", str(log_root)]) == 0
    assert seen["fetch"] == ("o/r", {9})
    assert "kept by PR: 1" in capsys.readouterr().out


def test_run_main_offline_without_repo(monkeypatch, tmp_path: Path, capsys) -> None:
    log_root = tmp_path / "logs"
    run = log_root / "implement" / "run-1"
    (run / "round-1").mkdir(parents=True)
    (run / "round-1" / "oos-accepted-review.md").write_text("### OOS_1: item\n- **Reviewer**: codex\n", encoding="utf-8")
    (run / "oos-issues.ndjson").write_text(json.dumps({"body": "- **Stable ID**: oos-accepted-review:OOS_1\n- **Filed URL**: https://github.com/o/r/issues/9"}) + "\n", encoding="utf-8")
    monkeypatch.setattr(analyze_issues, "_detect_repo", lambda: "")
    assert analyze_issues.run_main(["--log-root", str(log_root)]) == 0
    assert "Fate-adjusted OOS Scoring" in capsys.readouterr().out
