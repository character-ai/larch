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


CODE_HEADER = (
    "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\t"
    "v2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\t"
    "v3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool\tscope"
)


def _code_row(finding_id: str, result: str, votes: tuple[str, str, str], scope: str = "in_scope") -> str:
    v1, v2, v3 = votes
    return (
        f"{finding_id}\tcodex|cursor\t{result}\t{v1}\ttrue\tmajor\tgood\tfalse\tcodex\t"
        f"{v2}\ttrue\tminor\tgood\tfalse\tcursor\t"
        f"{v3}\ttrue\tminor\tgood\tfalse\tclaude\t{scope}"
    )


def test_render_chart_smoke() -> None:
    assert "Cumulative growth chart" in render_chart.render_chart(["2026-01"], [("A", "Bug", [1])])


def test_analyze_fixture_runs(tmp_path: Path, capsys) -> None:
    fixture = tmp_path / "issues.json"
    fixture.write_text(json.dumps([{"number": 1, "title": "Fix bug", "state": "OPEN", "createdAt": "2026-01-01T00:00:00Z", "body": "", "labels": []}]), encoding="utf-8")
    assert analyze_issues.analyze_main(["--json", str(fixture), "--top-k", "1", "--log-root", str(tmp_path / "missing")]) == 0
    assert "Bug fix" in capsys.readouterr().out


def test_analyze_rich_fixture_pins_categories_duplicates_and_reviewers(tmp_path: Path, capsys) -> None:
    fixture = Path(__file__).with_name("analyze-issues-fixture.json")
    assert analyze_issues.analyze_main(["--json", str(fixture), "--top-k", "3", "--log-root", str(tmp_path / "missing")]) == 0
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


def test_legacy_combined_away_in_body_does_not_dock() -> None:
    issue = {
        "number": 12,
        "state": "CLOSED",
        "body": "Discussion quoted Combined into #99 elsewhere.",
        "comments": [],
        "closedByPullRequestsReferences": [],
    }
    fate = analyze_issues.classify_oos_issue_fate(issue)
    assert fate["bucket"] == "provisional unknown"


def test_html_combined_away_marker_docks() -> None:
    issue = {
        "number": 12,
        "state": "CLOSED",
        "comments": [{"body": "<!-- larch:combined-away source=#1 target=#99 -->"}],
        "closedByPullRequestsReferences": [],
    }
    fate = analyze_issues.classify_oos_issue_fate(issue)
    assert fate["bucket"] == "docked combined-away"
    assert fate["adjusted"] == 0


def test_degraded_comment_fetch_with_bulk_closed(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "implement" / "run-1"
    (run / "round-1").mkdir(parents=True)
    (run / "round-1" / "oos-accepted-review.md").write_text(
        "### OOS_1: item\n- **Reviewer**: codex\n",
        encoding="utf-8",
    )
    (run / "oos-issues.ndjson").write_text(
        json.dumps({"body": "- **Stable ID**: oos-accepted-review:OOS_1\n- **Filed URL**: https://github.com/o/r/issues/10"}) + "\n",
        encoding="utf-8",
    )
    issues = [{"number": 10, "title": "item", "state": "CLOSED", "body": "", "labels": []}]
    filed_issue_details = {10: {"number": 10, "__fetch_failed__": True}}
    _text, stats = analyze_issues.fate_adjusted_oos_scoring(issues, log_root, filed_issue_details=filed_issue_details)
    assert stats["buckets"]["degraded comment fetch"] == 1
    assert stats["buckets"]["provisional unknown"] == 1
    assert stats["totals"]["adjusted"] == 1


def test_cap_rollup_fallback_exact_candidate_match(tmp_path: Path) -> None:
    run = tmp_path / "implement" / "run-1"
    (run / "round-1").mkdir(parents=True)
    (run / "round-1" / "oos-accepted-review.md").write_text(
        "### OOS_1: one\n- **Reviewer**: codex\n\n"
        "### OOS_2: two\n- **Reviewer**: cursor\n",
        encoding="utf-8",
    )
    (run / "oos-issues.ndjson").write_text(
        json.dumps({
            "title": "Aggregated rollup of 2 capped OOS items",
            "body": (
                "- **Stable ID**: oos-accepted-review:OOS_1\n"
                "- **Filed URL**: https://github.com/o/r/issues/10\n"
            ),
        }) + "\n",
        encoding="utf-8",
    )
    rows = analyze_issues._join_implement_run_records(run)
    scored = [row for row in rows if not row.get("bucket")]
    assert len(scored) == 2
    assert {row["reviewer"] for row in scored} == {"codex", "cursor"}


def test_single_url_scores_one_row_not_fan_out(tmp_path: Path) -> None:
    run = tmp_path / "implement" / "run-1"
    (run / "round-1").mkdir(parents=True)
    (run / "round-1" / "oos-accepted-review.md").write_text(
        "### OOS_1: one\n- **Reviewer**: codex\n\n"
        "### OOS_2: two\n- **Reviewer**: cursor\n\n"
        "### OOS_3: three\n- **Reviewer**: claude\n",
        encoding="utf-8",
    )
    (run / "oos-issues.ndjson").write_text(
        json.dumps({
            "body": (
                "- **Stable ID**: oos-accepted-review:OOS_1\n"
                "- **Filed URL**: https://github.com/o/r/issues/10\n"
            ),
        }) + "\n",
        encoding="utf-8",
    )
    rows = analyze_issues._join_implement_run_records(run)
    scored = [row for row in rows if not row.get("bucket")]
    assert len(scored) == 1
    assert scored[0]["reviewer"] == "codex"


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
    assert out.index("## Fate-adjusted OOS Scoring") < out.index("## Ground-truth Voter Calibration")
    assert "No filed OOS run-log evidence found." in out


def test_ground_truth_voter_calibration_decisive_buckets_and_metrics(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "implement" / "run-1"
    round_dir = run / "round-1"
    round_dir.mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({"started_at": "2026-01-01T00:00:00Z"}), encoding="utf-8")
    (round_dir / "findings-classification.tsv").write_text(
        "\n".join(
            [
                CODE_HEADER,
                _code_row("FINDING_1", "rejected", ("YES", "NO", "NO")),
                _code_row("FINDING_2", "accepted", ("YES", "NO", "YES")),
                _code_row("FINDING_3", "accepted", ("YES", "NO", "YES"), "oos"),
                _code_row("FINDING_4", "rejected", ("", "", "")),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (run / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "REJ_CR1_A", "outcome": "rejected", "category": "Bug fix", "prose_body": "### FINDING_1: Parser bug in src/parser.ts\nConcern: bad parser path src/parser.ts"}) + "\n"
        + json.dumps({"id": "FINDING_2", "outcome": "accepted", "category": "Bug fix", "prose_body": "### FINDING_2: Accepted risky behavior in src/app.ts"}) + "\n"
        + json.dumps({"id": "FINDING_3", "outcome": "out_of_scope", "category": "Documentation", "prose_body": "### FINDING_3: OOS stale docs in docs/old-guide.rst"}) + "\n",
        encoding="utf-8",
    )
    (round_dir / "oos-accepted-review.md").write_text(
        "### FINDING_3: OOS stale docs in docs/old-guide.rst\n- **Reviewer**: codex\n",
        encoding="utf-8",
    )
    (run / "oos-issues.ndjson").write_text(
        json.dumps({"body": "- **Stable ID**: oos-accepted-review:FINDING_3\n- **Filed URL**: https://github.com/o/r/issues/12"})
        + "\n",
        encoding="utf-8",
    )
    issues = [
        {
            "number": 10,
            "title": "Fix parser bug in src/parser.ts",
            "state": "OPEN",
            "createdAt": "2026-02-01T00:00:00Z",
            "body": "Fix parser bug in src/parser.ts",
            "labels": [],
        },
        {
            "number": 11,
            "title": "Revert accepted risky behavior in src/app.ts",
            "state": "OPEN",
            "createdAt": "2026-02-02T00:00:00Z",
            "body": "Regression forced revert in src/app.ts",
            "labels": [],
        },
        {"number": 12, "title": "OOS stale docs", "state": "CLOSED", "stateReason": "NOT_PLANNED", "createdAt": "2026-02-03T00:00:00Z", "body": "", "labels": []},
    ]
    text, stats = analyze_issues.ground_truth_voter_calibration(issues, log_root=log_root, filed_issue_details={})
    assert "| rejected_resurfaced | 1 | 1 |" in text
    assert "| accepted_reverted_or_regressed | 1 | 1 |" in text
    assert "| docked closed-unfixed | 1 | 1 |" in text
    assert "- Ineligible rows: 1" in text
    assert "| code-review | codex | 3 | 1 | 2 | 0 | 0.333 | 2 | 0 |" in text
    assert stats["stats"].decisive_rows == 3


def test_ground_truth_design_round_local_disagreement_is_weak(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "design" / "design-run"
    round_dir = run / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "findings-classification.tsv").write_text(
        (
            "finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\t"
            "v2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\t"
            "v3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool\tbody_severity\tscope\n"
            "FINDING_1\tarchitect\taccepted\tYES\ttrue\tmajor\tgood\tfalse\t\tNO\ttrue\tminor\tgood\tfalse\t\tYES\ttrue\tminor\tgood\tfalse\t\tmajor\tin_scope\n"
        ),
        encoding="utf-8",
    )
    (round_dir / "accepted-plan-findings.md").write_text("### FINDING_1: local accepted\n", encoding="utf-8")
    (run / "rejected-findings.md").write_text("### FINDING_1: root rejected\n", encoding="utf-8")
    text, stats = analyze_issues.ground_truth_voter_calibration([], log_root=log_root, filed_issue_details={})
    assert "design round-local/run-root verdict disagreement" in text
    assert "| weak_prose_verdict | 1 | 0 |" in text
    assert stats["stats"].verdict_disagreement == 1


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


def test_legacy_stable_id_extraction_keeps_pre_filed_token_on_same_line() -> None:
    body = "FINDING_1 ... Filed as https://github.com/o/r/issues/10"
    assert analyze_issues._extract_legacy_stable_ids_from_ndjson_body(body) == ["FINDING_1"]


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


def test_cap_rollup_shortfall_keeps_resolved_members(tmp_path: Path) -> None:
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
    scored = [row for row in rows if not row.get("bucket")]
    assert len(scored) == 1
    assert scored[0]["reviewer"] == "codex"
    assert any(row.get("bucket") == "ambiguous rollup expansion" for row in rows)
    issues = [{"number": 10, "title": "one", "state": "OPEN", "body": "", "labels": []}]
    _text, stats = analyze_issues.fate_adjusted_oos_scoring(issues, tmp_path, filed_issue_details={})
    assert stats["totals"] == {"provisional": 1, "adjusted": 1, "docked": 0}
    assert stats["buckets"]["ambiguous rollup expansion"] == 1


def test_cap_rollup_exceeds_expected_returns_ambiguous(tmp_path: Path) -> None:
    run = tmp_path / "implement" / "run-1"
    (run / "round-1").mkdir(parents=True)
    (run / "round-1" / "oos-accepted-review.md").write_text(
        "### OOS_1: one\n- **Reviewer**: codex\n\n"
        "### OOS_2: two\n- **Reviewer**: cursor\n\n"
        "### OOS_3: three\n- **Reviewer**: claude\n",
        encoding="utf-8",
    )
    (run / "oos-issues.ndjson").write_text(
        json.dumps({
            "title": "Aggregated rollup of 2 capped OOS items",
            "body": (
                "- **Stable ID**: oos-accepted-review:OOS_1\n"
                "- **Stable ID**: oos-accepted-review:OOS_2\n"
                "- **Stable ID**: oos-accepted-review:OOS_3\n"
                "- **Filed URL**: https://github.com/o/r/issues/10\n"
            ),
        }) + "\n",
        encoding="utf-8",
    )
    rows = analyze_issues._join_implement_run_records(run)
    assert len(rows) == 1
    assert rows[0]["bucket"] == "ambiguous rollup expansion"


def test_cap_rollup_ambiguous_stable_id_emits_bucket_without_scoring_siblings(tmp_path: Path) -> None:
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
        json.dumps({
            "title": "Aggregated rollup of 2 capped OOS items",
            "body": (
                "- **Stable ID**: oos-accepted-review:OOS_1\n"
                "- **Stable ID**: oos-accepted-review:OOS_2\n"
                "- **Filed URL**: https://github.com/o/r/issues/10\n"
            ),
        }) + "\n",
        encoding="utf-8",
    )
    rows = analyze_issues._join_implement_run_records(run)
    assert any(row.get("bucket") == "ambiguous stable id" for row in rows)
    assert not any(row.get("reviewer") == "cursor" for row in rows if not row.get("bucket"))


def test_incidental_aggregated_rollup_prose_falls_back_to_normal_join(tmp_path: Path) -> None:
    run = tmp_path / "implement" / "run-1"
    (run / "round-1").mkdir(parents=True)
    (run / "round-1" / "oos-accepted-review.md").write_text(
        "### OOS_1: item\n- **Reviewer**: codex\n",
        encoding="utf-8",
    )
    (run / "oos-issues.ndjson").write_text(
        json.dumps({
            "body": (
                "Notes mention Aggregated rollup in prose.\n"
                "- **Filed URL**: https://github.com/o/r/issues/10\n"
            ),
        }) + "\n",
        encoding="utf-8",
    )
    rows = analyze_issues._join_implement_run_records(run)
    assert len(rows) == 1
    assert rows[0].get("bucket") is None
    assert rows[0]["reviewer"] == "unknown"


def test_invalid_label_does_not_dock_closed_issue() -> None:
    issue = {"number": 1, "state": "CLOSED", "body": "", "labels": [{"name": "invalid"}]}
    fate = analyze_issues.classify_oos_issue_fate(issue)
    assert fate["bucket"] == "provisional unknown"
    assert fate["adjusted"] == 1


def test_extract_filed_issue_number_supports_legacy_url_shapes() -> None:
    assert analyze_issues.extract_filed_issue_number_from_text(
        "FINDING_1 ... Filed as https://github.com/character-ai/larch/issues/3025"
    ) == 3025
    assert analyze_issues.extract_filed_issue_number_from_text(
        "**Filed**: https://github.com/o/r/issues/42"
    ) == 42
    assert analyze_issues._record_issue_urls({
        "body": "FINDING_1 ... Filed as https://github.com/o/r/issues/99",
    }) == ["https://github.com/o/r/issues/99"]


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
    out = capsys.readouterr().out
    assert "Fate-adjusted OOS Scoring" in out
    assert "enrichment unavailable: 1" in out
    assert "skipped missing issue: 0" in out


def test_run_main_continues_after_corrupt_issue_dump(monkeypatch, tmp_path: Path, capsys) -> None:
    log_root = tmp_path / "logs"
    monkeypatch.setattr(analyze_issues, "_detect_repo", lambda: "o/r")
    monkeypatch.setattr(analyze_issues, "iter_filed_oos_records", lambda _root: [])
    monkeypatch.setenv("TMPDIR", str(tmp_path))

    def fake_fetch(argv):
        output = Path(list(argv)[list(argv).index("--output") + 1])
        output.write_text("not-json", encoding="utf-8")
        return 0

    monkeypatch.setattr(analyze_issues, "fetch_main", fake_fetch)
    assert analyze_issues.run_main(["--log-root", str(log_root)]) == 0
    assert "Fate-adjusted OOS Scoring" in capsys.readouterr().out


def test_design_oos_duplicate_heading_marks_ambiguous(tmp_path: Path) -> None:
    run = tmp_path / "larch-logs" / "design" / "design-run"
    run.mkdir(parents=True)
    (run / "oos-accepted-design.md").write_text(
        "### OOS_7: first\n- **Reviewer**: architect\n\n"
        "### OOS_7: second\n- **Reviewer**: cursor\n",
        encoding="utf-8",
    )
    (run / "oos-issues-created.md").write_text("OOS_FILE_MAP\t7\thttps://github.com/o/r/issues/77\n", encoding="utf-8")
    rows = analyze_issues.iter_filed_oos_records(tmp_path / "larch-logs")
    assert rows[0]["bucket"] == "ambiguous stable id"


def test_ground_truth_gc_slimmed_run_skips_decisive_scoring(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "implement" / "slim-run"
    round_dir = run / "round-1"
    round_dir.mkdir(parents=True)
    (run / "gc-slimmed").write_text("2026-01-01\n", encoding="utf-8")
    (run / "manifest.json").write_text(json.dumps({"started_at": "2026-01-01T00:00:00Z"}), encoding="utf-8")
    (round_dir / "findings-classification.tsv").write_text(
        "\n".join([CODE_HEADER, _code_row("FINDING_1", "rejected", ("YES", "NO", "NO"))]) + "\n",
        encoding="utf-8",
    )
    (run / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_1", "outcome": "rejected", "prose_body": "### FINDING_1: bug in src/parser.ts"}) + "\n",
        encoding="utf-8",
    )
    issues = [{"number": 10, "title": "Fix parser bug in src/parser.ts", "state": "OPEN", "createdAt": "2026-02-01T00:00:00Z", "body": "parser bug src/parser.ts", "labels": []}]
    text, stats = analyze_issues.ground_truth_voter_calibration(issues, log_root=log_root, filed_issue_details={})
    assert stats["stats"].gc_slimmed_runs == 1
    assert stats["stats"].decisive_rows == 0
    assert stats["stats"].eligible_rows == 0
    assert "| rejected_resurfaced |" not in text


def test_ground_truth_design_jsonl_disagreement_is_weak(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "design" / "design-run"
    round_dir = run / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "findings-classification.tsv").write_text(
        (
            "finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\t"
            "v2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\t"
            "v3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool\tbody_severity\tscope\n"
            "FINDING_1\tarchitect\taccepted\tYES\ttrue\tmajor\tgood\tfalse\t\tNO\ttrue\tminor\tgood\tfalse\t\tYES\ttrue\tminor\tgood\tfalse\t\tmajor\tin_scope\n"
        ),
        encoding="utf-8",
    )
    (round_dir / "accepted-plan-findings.md").write_text("### FINDING_1: accepted in markdown\n", encoding="utf-8")
    (run / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_1", "outcome": "rejected", "prose_body": "### FINDING_1: rejected in jsonl\n"}) + "\n",
        encoding="utf-8",
    )
    text, stats = analyze_issues.ground_truth_voter_calibration([], log_root=log_root, filed_issue_details={})
    assert "design markdown/JSONL verdict disagreement" in text
    assert "| weak_prose_verdict | 1 | 0 |" in text
    assert stats["stats"].decisive_rows == 0


def test_ground_truth_finding_id_word_boundary_avoids_find10(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "implement" / "run-1"
    round_dir = run / "round-1"
    round_dir.mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({"started_at": "2026-01-01T00:00:00Z"}), encoding="utf-8")
    (round_dir / "findings-classification.tsv").write_text(
        "\n".join([CODE_HEADER, _code_row("FINDING_1", "rejected", ("YES", "NO", "NO"))]) + "\n",
        encoding="utf-8",
    )
    (run / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_10", "outcome": "accepted", "prose_body": "### FINDING_10: unrelated accepted finding\n"}) + "\n",
        encoding="utf-8",
    )
    _text, stats = analyze_issues.ground_truth_voter_calibration([], log_root=log_root, filed_issue_details={})
    assert stats["outcomes"][0].row.weak_reason == "missing prose verdict"
    assert stats["stats"].decisive_rows == 0


def test_ground_truth_enrichment_degraded_suppresses_issue_resurfacing(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "implement" / "run-1"
    round_dir = run / "round-1"
    round_dir.mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({"started_at": "2026-01-01T00:00:00Z"}), encoding="utf-8")
    (round_dir / "findings-classification.tsv").write_text(
        "\n".join([CODE_HEADER, _code_row("FINDING_1", "rejected", ("YES", "NO", "NO"))]) + "\n",
        encoding="utf-8",
    )
    (run / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_1", "outcome": "rejected", "category": "Bug fix", "prose_body": "### FINDING_1: Parser bug in src/parser.ts"}) + "\n",
        encoding="utf-8",
    )
    issues = [{"number": 10, "title": "Fix parser bug in src/parser.ts", "state": "OPEN", "createdAt": "2026-02-01T00:00:00Z", "body": "parser bug src/parser.ts", "labels": []}]
    text, stats = analyze_issues.ground_truth_voter_calibration(
        issues, log_root=log_root, filed_issue_details={}, enrichment_degraded="offline",
    )
    assert "| enrichment-degraded-resurfacing | 1 | 0 |" in text
    assert stats["stats"].decisive_rows == 0


def test_ground_truth_oos_tally_disagreement_is_non_decisive(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "implement" / "run-1"
    round_dir = run / "round-1"
    round_dir.mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({"started_at": "2026-01-01T00:00:00Z"}), encoding="utf-8")
    (round_dir / "findings-classification.tsv").write_text(
        "\n".join([CODE_HEADER, _code_row("FINDING_3", "accepted", ("YES", "YES", "YES"), "oos")]) + "\n",
        encoding="utf-8",
    )
    (round_dir / "voting-tally.md").write_text(
        "## Findings\n| Item | YES | NO | JERR | Result |\n| FINDING_3 | 3 | 0 | 0 | rejected |\n",
        encoding="utf-8",
    )
    (run / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_3", "outcome": "out_of_scope", "prose_body": "### FINDING_3: OOS docs\n"}) + "\n",
        encoding="utf-8",
    )
    text, stats = analyze_issues.ground_truth_voter_calibration([], log_root=log_root, filed_issue_details={})
    assert "| weak_oos_panel_verdict | 1 | 0 |" in text
    assert stats["stats"].decisive_rows == 0


def test_ground_truth_not_planned_issue_is_non_decisive_resurfacing(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "implement" / "run-1"
    round_dir = run / "round-1"
    round_dir.mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({"started_at": "2026-01-01T00:00:00Z"}), encoding="utf-8")
    (round_dir / "findings-classification.tsv").write_text(
        "\n".join([CODE_HEADER, _code_row("FINDING_1", "rejected", ("YES", "NO", "NO"))]) + "\n",
        encoding="utf-8",
    )
    (run / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_1", "outcome": "rejected", "category": "Documentation", "prose_body": "### FINDING_1: stale docs in docs/guide.rst"}) + "\n",
        encoding="utf-8",
    )
    issues = [{"number": 10, "title": "stale docs guide", "state": "CLOSED", "stateReason": "NOT_PLANNED", "createdAt": "2026-02-01T00:00:00Z", "body": "stale docs guide", "labels": []}]
    text, stats = analyze_issues.ground_truth_voter_calibration(issues, log_root=log_root, filed_issue_details={})
    assert "| rejected_not_observed | 1 | 0 |" in text
    assert stats["stats"].decisive_rows == 0


def test_ground_truth_oos_prose_weakness_does_not_block_panel_verdict(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "implement" / "run-1"
    round_dir = run / "round-1"
    round_dir.mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({"started_at": "2026-01-01T00:00:00Z"}), encoding="utf-8")
    (round_dir / "findings-classification.tsv").write_text(
        "\n".join([CODE_HEADER, _code_row("FINDING_3", "accepted", ("YES", "YES", "YES"), "oos")]) + "\n",
        encoding="utf-8",
    )
    (round_dir / "voting-tally.md").write_text(
        "## Findings\n| Item | YES | NO | JERR | Result |\n| FINDING_3 | 3 | 0 | 0 | accepted |\n",
        encoding="utf-8",
    )
    (run / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_3", "outcome": "accepted", "prose_body": "### FINDING_3: OOS\n"})
        + "\n"
        + json.dumps({"id": "FINDING_3", "outcome": "rejected", "prose_body": "### FINDING_3: OOS duplicate\n"}),
        encoding="utf-8",
    )
    (round_dir / "oos-accepted-review.md").write_text("### FINDING_3: OOS stale docs\n- **Reviewer**: codex\n", encoding="utf-8")
    (run / "oos-issues.ndjson").write_text(
        json.dumps({"body": "- **Stable ID**: oos-accepted-review:FINDING_3\n- **Filed URL**: https://github.com/o/r/issues/12"}) + "\n",
        encoding="utf-8",
    )
    issues = [{"number": 12, "title": "OOS stale docs", "state": "CLOSED", "stateReason": "NOT_PLANNED", "createdAt": "2026-02-03T00:00:00Z", "body": "", "labels": []}]
    text, stats = analyze_issues.ground_truth_voter_calibration(issues, log_root=log_root, filed_issue_details={})
    assert stats["outcomes"][0].row.oos_panel_verdict == "accepted"
    assert "| docked closed-unfixed | 1 | 1 |" in text
    assert stats["stats"].decisive_rows == 1


def test_ground_truth_multi_round_post_run_issue_resurfacing(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "implement" / "multi-run"
    round1 = run / "round-1"
    round2 = run / "round-2"
    round1.mkdir(parents=True)
    round2.mkdir(parents=True)
    (run / "manifest.json").write_text(
        json.dumps({"started_at": "2026-01-01T00:00:00Z", "ended_at": "2026-01-02T00:00:00Z"}),
        encoding="utf-8",
    )
    (round1 / "findings-classification.tsv").write_text(
        "\n".join([CODE_HEADER, _code_row("FINDING_1", "rejected", ("YES", "NO", "NO"))]) + "\n",
        encoding="utf-8",
    )
    (round2 / "findings-classification.tsv").write_text(
        "\n".join([CODE_HEADER, _code_row("FINDING_2", "accepted", ("YES", "NO", "YES"))]) + "\n",
        encoding="utf-8",
    )
    (round1 / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_1", "outcome": "rejected", "category": "Bug fix", "prose_body": "### FINDING_1: Parser bug in src/parser.ts"}) + "\n",
        encoding="utf-8",
    )
    (round2 / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_2", "outcome": "accepted", "category": "Bug fix", "prose_body": "### FINDING_2: other"}) + "\n",
        encoding="utf-8",
    )
    issues = [{"number": 10, "title": "Fix parser bug in src/parser.ts", "state": "OPEN", "createdAt": "2026-03-01T00:00:00Z", "body": "parser bug src/parser.ts", "labels": []}]
    text, stats = analyze_issues.ground_truth_voter_calibration(issues, log_root=log_root, filed_issue_details={})
    assert "| rejected_resurfaced | 1 | 1 |" in text
    assert stats["stats"].decisive_rows == 1


def test_ground_truth_multi_round_run_root_jsonl_round_isolation(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "implement" / "multi-run"
    round1 = run / "round-1"
    round2 = run / "round-2"
    round1.mkdir(parents=True)
    round2.mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({"started_at": "2026-01-01T00:00:00Z"}), encoding="utf-8")
    (round1 / "findings-classification.tsv").write_text(
        "\n".join([CODE_HEADER, _code_row("FINDING_1", "rejected", ("YES", "NO", "NO"))]) + "\n",
        encoding="utf-8",
    )
    (round2 / "findings-classification.tsv").write_text(
        "\n".join([CODE_HEADER, _code_row("FINDING_1", "accepted", ("YES", "NO", "YES"))]) + "\n",
        encoding="utf-8",
    )
    (run / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_1", "outcome": "rejected", "prose_body": "### FINDING_1: round-1 bug in src/r1.ts"}) + "\n"
        + json.dumps({"id": "FINDING_1", "outcome": "accepted", "prose_body": "### FINDING_1: round-2 bug in src/r2.ts"}) + "\n",
        encoding="utf-8",
    )
    (round1 / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_1", "outcome": "rejected", "prose_body": "### FINDING_1: round-1 bug in src/r1.ts"}) + "\n",
        encoding="utf-8",
    )
    (round2 / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_1", "outcome": "accepted", "prose_body": "### FINDING_1: round-2 bug in src/r2.ts"}) + "\n",
        encoding="utf-8",
    )
    _text, stats = analyze_issues.ground_truth_voter_calibration([], log_root=log_root, filed_issue_details={})
    outcomes = {o.row.round_num: o for o in stats["outcomes"]}
    assert outcomes[1].row.panel_verdict == "rejected"
    assert outcomes[2].row.panel_verdict == "accepted"


def test_ground_truth_multi_round_run_root_jsonl_missing_round_is_ignored(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "implement" / "multi-run"
    round1 = run / "round-1"
    round2 = run / "round-2"
    round1.mkdir(parents=True)
    round2.mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({"started_at": "2026-01-01T00:00:00Z"}), encoding="utf-8")
    (round1 / "findings-classification.tsv").write_text(
        "\n".join([CODE_HEADER, _code_row("FINDING_1", "rejected", ("YES", "NO", "NO"))]) + "\n",
        encoding="utf-8",
    )
    (round2 / "findings-classification.tsv").write_text(
        "\n".join([CODE_HEADER, _code_row("FINDING_1", "accepted", ("YES", "NO", "YES"))]) + "\n",
        encoding="utf-8",
    )
    (run / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_1", "outcome": "rejected", "prose_body": "### FINDING_1: round-1 bug in src/r1.ts"}) + "\n"
        + json.dumps({"id": "FINDING_1", "outcome": "accepted", "prose_body": "### FINDING_1: round-2 bug in src/r2.ts"}) + "\n",
        encoding="utf-8",
    )
    _text, stats = analyze_issues.ground_truth_voter_calibration([], log_root=log_root, filed_issue_details={})
    assert [outcome.row.panel_verdict for outcome in stats["outcomes"]] == ["", ""]
    assert {outcome.reason for outcome in stats["outcomes"]} == {"missing prose verdict"}


def test_ground_truth_standalone_review_requires_record_round_num(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "review" / "review-run"
    run.mkdir(parents=True)
    (run / "review-findings-classification-round-1.tsv").write_text(
        "\n".join([CODE_HEADER, _code_row("FINDING_1", "rejected", ("YES", "NO", "NO"))]) + "\n",
        encoding="utf-8",
    )
    (run / "review-findings-classification-round-2.tsv").write_text(
        "\n".join([CODE_HEADER, _code_row("FINDING_1", "accepted", ("YES", "NO", "YES"))]) + "\n",
        encoding="utf-8",
    )
    (run / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_1", "outcome": "rejected", "prose_body": "### FINDING_1: unscoped stale record"}) + "\n"
        + json.dumps({"id": "FINDING_1", "round_num": 2, "outcome": "accepted", "prose_body": "### FINDING_1: round-2 record"}) + "\n",
        encoding="utf-8",
    )
    _text, stats = analyze_issues.ground_truth_voter_calibration([], log_root=log_root, filed_issue_details={})
    outcomes = {outcome.row.round_num: outcome for outcome in stats["outcomes"]}
    assert outcomes[1].row.panel_verdict == ""
    assert outcomes[2].row.panel_verdict == "accepted"


def test_ground_truth_accepted_finding_resurfacing_without_issue(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run1 = log_root / "implement" / "run-1"
    run2 = log_root / "implement" / "run-2"
    round1 = run1 / "round-1"
    round2 = run2 / "round-1"
    round1.mkdir(parents=True)
    round2.mkdir(parents=True)
    (run1 / "manifest.json").write_text(json.dumps({"started_at": "2026-01-01T00:00:00Z"}), encoding="utf-8")
    (run2 / "manifest.json").write_text(json.dumps({"started_at": "2026-02-01T00:00:00Z"}), encoding="utf-8")
    (round1 / "findings-classification.tsv").write_text(
        "\n".join([CODE_HEADER, _code_row("FINDING_1", "rejected", ("YES", "NO", "NO"))]) + "\n",
        encoding="utf-8",
    )
    (round2 / "findings-classification.tsv").write_text(
        "\n".join([CODE_HEADER, _code_row("FINDING_5", "accepted", ("YES", "NO", "YES"))]) + "\n",
        encoding="utf-8",
    )
    (run1 / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_1", "outcome": "rejected", "category": "Bug fix", "prose_body": "### FINDING_1: shared bug in src/shared.ts"}) + "\n",
        encoding="utf-8",
    )
    (run2 / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_5", "outcome": "accepted", "category": "Bug fix", "prose_body": "### FINDING_5: shared bug in src/shared.ts accepted later"}) + "\n",
        encoding="utf-8",
    )
    text, stats = analyze_issues.ground_truth_voter_calibration([], log_root=log_root, filed_issue_details={})
    assert "| rejected_resurfaced | 1 | 1 |" in text
    assert stats["stats"].decisive_rows == 1
    assert stats["metrics"][("code-review", "cursor")].false_negative_no == 1


def test_ground_truth_rejected_oos_panel_stays_non_decisive(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "implement" / "run-1"
    round_dir = run / "round-1"
    round_dir.mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({"started_at": "2026-01-01T00:00:00Z"}), encoding="utf-8")
    (round_dir / "findings-classification.tsv").write_text(
        "\n".join([CODE_HEADER, _code_row("FINDING_3", "rejected", ("YES", "YES", "YES"), "oos")]) + "\n",
        encoding="utf-8",
    )
    (round_dir / "voting-tally.md").write_text(
        "## Findings\n| Item | YES | NO | JERR | Result |\n| FINDING_3 | 0 | 3 | 0 | rejected |\n",
        encoding="utf-8",
    )
    (run / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_3", "outcome": "out_of_scope", "prose_body": "### FINDING_3: OOS docs\n"}) + "\n",
        encoding="utf-8",
    )
    (round_dir / "oos-accepted-review.md").write_text("### FINDING_3: OOS stale docs\n- **Reviewer**: codex\n", encoding="utf-8")
    (run / "oos-issues.ndjson").write_text(
        json.dumps({"body": "- **Stable ID**: oos-accepted-review:FINDING_3\n- **Filed URL**: https://github.com/o/r/issues/12"}) + "\n",
        encoding="utf-8",
    )
    issues = [{"number": 12, "title": "OOS stale docs", "state": "CLOSED", "stateReason": "NOT_PLANNED", "createdAt": "2026-02-03T00:00:00Z", "body": "", "labels": []}]
    text, stats = analyze_issues.ground_truth_voter_calibration(issues, log_root=log_root, filed_issue_details={})
    assert "| rejected_oos_panel | 1 | 0 |" in text
    assert stats["stats"].decisive_rows == 0


def test_ground_truth_issue_cap_does_not_drop_accepted_finding_evidence(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run1 = log_root / "implement" / "run-1"
    run2 = log_root / "implement" / "run-2"
    round1 = run1 / "round-1"
    round2 = run2 / "round-1"
    round1.mkdir(parents=True)
    round2.mkdir(parents=True)
    (run1 / "manifest.json").write_text(json.dumps({"started_at": "2026-01-01T00:00:00Z"}), encoding="utf-8")
    (run2 / "manifest.json").write_text(json.dumps({"started_at": "2026-02-01T00:00:00Z"}), encoding="utf-8")
    (round1 / "findings-classification.tsv").write_text(
        "\n".join([CODE_HEADER, _code_row("FINDING_1", "rejected", ("YES", "NO", "NO"))]) + "\n",
        encoding="utf-8",
    )
    (round2 / "findings-classification.tsv").write_text(
        "\n".join([CODE_HEADER, _code_row("FINDING_99", "accepted", ("YES", "NO", "YES"))]) + "\n",
        encoding="utf-8",
    )
    (run1 / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_1", "outcome": "rejected", "category": "Bug fix", "prose_body": "### FINDING_1: target bug in src/target.ts"}) + "\n",
        encoding="utf-8",
    )
    (run2 / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_99", "outcome": "accepted", "category": "Bug fix", "prose_body": "### FINDING_99: target bug in src/target.ts resurfaced"}) + "\n",
        encoding="utf-8",
    )
    issues = []
    for idx in range(60):
        issues.append({
            "number": idx + 1,
            "title": f"weak overlap token{idx} misc",
            "state": "OPEN",
            "createdAt": "2026-03-01T00:00:00Z",
            "body": f"weak overlap token{idx} misc",
            "labels": [],
        })
    text, stats = analyze_issues.ground_truth_voter_calibration(issues, log_root=log_root, filed_issue_details={})
    assert "| rejected_resurfaced | 1 | 1 |" in text
    assert stats["stats"].decisive_rows == 1


def test_ground_truth_issue_candidates_are_not_truncated_after_ranking(tmp_path: Path) -> None:
    row = analyze_issues.GroundTruthRow(
        panel_kind="code-review",
        path=tmp_path / "round-1" / "findings-classification.tsv",
        run_dir=tmp_path,
        run_id="run-1",
        round_num=1,
        started_at=analyze_issues.parse_iso("2026-01-01T00:00:00Z"),
        raw_row={"finding_id": "FINDING_1"},
        header=[],
        reviewer_column="reviewer_slots",
        voter_votes=[],
        voters=[],
        is_oos=False,
        panel_verdict="rejected",
        prose_text="target bug in src/target.ts",
        title="target bug",
    )
    issue_evidence = [
        analyze_issues.GroundTruthEvidence(
            source="issue",
            run_id="",
            round_num=0,
            started_at=None,
            created_at=analyze_issues.parse_iso("2026-02-01T00:00:00Z"),
            title=f"target bug filler {idx}",
            text=f"target bug filler {idx}",
            category="Other",
        )
        for idx in range(60)
    ]
    target = analyze_issues.GroundTruthEvidence(
        source="issue",
        run_id="",
        round_num=0,
        started_at=None,
        created_at=analyze_issues.parse_iso("2026-02-01T00:00:00Z"),
        title="target bug in src/target.ts",
        text="target bug in src/target.ts",
        category="Bug fix",
    )
    issue_evidence.append(target)
    candidates = analyze_issues._candidate_evidence_for_row(
        row,
        issue_evidence=issue_evidence,
        accepted_evidence=[],
        accepted_index={},
    )
    assert target in candidates
    assert len([item for item in candidates if item.source == "issue"]) == 61
