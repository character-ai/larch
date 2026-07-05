# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# ruff: noqa: E702
# pylint: skip-file
"""Representative tests for audit run helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from larch.core import architectural_guidelines as ag
from larch.core import config
from larch.issue import audit_runs
from larch.core.proc import CommandResult

import pytest


def test_title_contiguous(capsys):
    assert audit_runs.title_main(["--skill", "implement", "--pr-list", "3,1,2", "--timestamp", "T"]) == 0
    assert capsys.readouterr().out.strip() == "TITLE=[Implement Run Logs Audit T Report] PRs #1-#3"


def test_title_single_pr(capsys):
    assert audit_runs.title_main(["--skill", "implement", "--pr-list", "42", "--timestamp", "T"]) == 0
    assert capsys.readouterr().out.strip() == "TITLE=[Implement Run Logs Audit T Report] PRs #42"


def test_title_noncontiguous_compact(capsys):
    assert audit_runs.title_main(["--skill", "implement", "--pr-list", "1,2,5,6", "--timestamp", "T"]) == 0
    assert capsys.readouterr().out.strip() == "TITLE=[Implement Run Logs Audit T Report] PRs #1-#6 (4 total)"


def test_title_noncontiguous_stays_under_256_chars(capsys):
    pr_list = ",".join(str(n) for n in range(5000, 5000 + 2276, 2))
    assert audit_runs.title_main(["--skill", "implement", "--pr-list", pr_list, "--timestamp", "2026-06-28T10:00-07:00"]) == 0
    out = capsys.readouterr().out.strip()
    title_val = out.removeprefix("TITLE=")
    assert len(title_val) <= 256


def test_title_design_noncontiguous_compact(capsys):
    assert audit_runs.title_main(["--skill", "design", "--pr-list", "10,20,30", "--timestamp", "T"]) == 0
    assert capsys.readouterr().out.strip() == "TITLE=[Design Run Logs Audit T Report] PRs #10-#30 (3 total)"


def test_design_run_id_extraction_requires_strict_uuid_title():
    title = "chore(larch-logs): design run 12345678-1234-1234-1234-123456789ABC"
    assert audit_runs.match_design_run_log_pr_title(title)
    assert audit_runs.extract_design_run_log_pr_id(title) == "12345678-1234-1234-1234-123456789ABC"
    loose = "chore(larch-logs): design run 12345678-extra"
    assert not audit_runs.match_design_run_log_pr_title(loose)
    assert audit_runs.extract_design_run_log_pr_id(loose) == ""


def test_pacific_timestamp_main_emits_pacific_source(capsys):
    assert audit_runs.pacific_timestamp_main([]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["PACIFIC_TIMESTAMP_SOURCE"] == "tz_america_los_angeles"
    assert re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}-0[78]:00", out["PACIFIC_TIMESTAMP"])


def test_pacific_timestamp_main_utc_fallback(monkeypatch, capsys):
    def missing_zone(_name):
        raise audit_runs.ZoneInfoNotFoundError("missing tzdata")

    monkeypatch.setattr(audit_runs, "ZoneInfo", missing_zone)
    assert audit_runs.pacific_timestamp_main([]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["PACIFIC_TIMESTAMP_SOURCE"] == "utc_fallback"
    assert re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}Z", out["PACIFIC_TIMESTAMP"])


def test_pacific_timestamp_main_rejects_unknown_argv(capsys):
    assert audit_runs.pacific_timestamp_main(["--bogus"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unexpected argument" in captured.err


def test_scan_run_rejects_skill_root(tmp_path: Path, capsys):
    root = tmp_path / "larch-logs" / "implement"
    root.mkdir(parents=True, exist_ok=True)
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\ncache-freshness\tfile\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(root),"--pr","1","--scans-tsv",str(scans)]) == 1
    row = json.loads(capsys.readouterr().out)
    assert row["scan"] == "run-dir-invalid"


def test_scan_run_error_rows_for_missing_inputs(tmp_path: Path, capsys):
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\ncache-freshness\tfile\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(tmp_path / "missing"),"--pr","1","--scans-tsv",str(scans)]) == 1
    row = json.loads(capsys.readouterr().out)
    assert row["scan"] == "run-dir-missing"
    run = tmp_path / "run"
    run.mkdir()
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","1","--scans-tsv",str(tmp_path / "missing.tsv")]) == 1
    row = json.loads(capsys.readouterr().out)
    assert row["scan"] == "scans-registry"
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","abc","--scans-tsv",str(scans)]) == 1
    row = json.loads(capsys.readouterr().out)
    assert row["scan"] == "audit-scan-run-args"


def test_scan_run_rejects_cross_skill_absolute_run_dir(tmp_path: Path, capsys):
    run = tmp_path / "larch-logs" / "design" / "run-1"
    run.mkdir(parents=True)
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\ncache-freshness\tfile\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","1","--scans-tsv",str(scans)]) == 1
    row = json.loads(capsys.readouterr().out)
    assert row["scan"] == "run-dir-invalid"


def _scan_design_guideline(tmp_path: Path, run: Path, capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    scans = tmp_path / "scans-design.tsv"
    scans.write_text(
        "name\ttype\tpattern\texpected_outcome\tseverity\n"
        "guideline-assessment\tfile\tarchitectural-guideline-assessment.md\tcommitted Gate C guideline assessment present and non-empty when file exists\tlow\n",
        encoding="utf-8",
    )
    assert audit_runs.scan_run_main(["--skill", "design", "--run-dir", str(run), "--pr", "7", "--scans-tsv", str(scans)]) == 0
    return json.loads(capsys.readouterr().out.splitlines()[0])


def test_scan_run_design_guideline_assessment_missing_is_informational(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = tmp_path / "run"
    run.mkdir()

    row = _scan_design_guideline(tmp_path, run, capsys)

    assert row["scan"] == "guideline-assessment"
    assert row["result"] == "informational"


def test_scan_run_design_guideline_assessment_classifies_clean_and_deviation(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    clean_run = tmp_path / "clean"
    clean_run.mkdir()
    (clean_run / ag.DESIGN_ASSESSMENT).write_text(ag.CLEAN_PRESENTATION_NOTE + "\n", encoding="utf-8")

    clean_row = _scan_design_guideline(tmp_path, clean_run, capsys)

    assert clean_row["result"] == "pass"
    assert clean_row["assessment_kind"] == "clean"

    deviation_run = tmp_path / "deviation"
    deviation_run.mkdir()
    (deviation_run / ag.DESIGN_ASSESSMENT).write_text("Deviation approved.\n", encoding="utf-8")

    deviation_row = _scan_design_guideline(tmp_path, deviation_run, capsys)

    assert deviation_row["result"] == "pass"
    assert deviation_row["assessment_kind"] == "deviation"


def test_scan_run_design_guideline_assessment_empty_or_nonregular_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    empty_run = tmp_path / "empty"
    empty_run.mkdir()
    (empty_run / ag.DESIGN_ASSESSMENT).write_text(" \n", encoding="utf-8")

    empty_row = _scan_design_guideline(tmp_path, empty_run, capsys)

    assert empty_row["result"] == "fail"

    symlink_run = tmp_path / "symlink"
    symlink_run.mkdir()
    target = tmp_path / "target.md"
    target.write_text("Deviation\n", encoding="utf-8")
    (symlink_run / ag.DESIGN_ASSESSMENT).symlink_to(target)

    symlink_row = _scan_design_guideline(tmp_path, symlink_run, capsys)

    assert symlink_row["result"] == "fail"


def test_scan_run_design_guideline_assessment_unreadable_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = tmp_path / "unreadable"
    run.mkdir()
    assessment = run / ag.DESIGN_ASSESSMENT
    assessment.write_text("Deviation\n", encoding="utf-8")
    assessment.chmod(0o000)

    try:
        row = _scan_design_guideline(tmp_path, run, capsys)
    finally:
        assessment.chmod(0o600)

    assert row["result"] == "fail"
    assert "unreadable" in str(row.get("detail", ""))


def test_scan_run_dispatches_guideline_assessment_from_design_registry(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "manifest.json").write_text('{"larch_version":"1.2.3"}\n', encoding="utf-8")
    (run / ag.DESIGN_ASSESSMENT).write_text(ag.CLEAN_PRESENTATION_NOTE + "\n", encoding="utf-8")
    scans = tmp_path / "scans-design.tsv"
    scans.write_text(
        "name\ttype\tpattern\texpected_outcome\tseverity\n"
        "cache-freshness\tmanifest-field\tmanifest.json::larch_version < latest\trun plugin matches or lags current (informational when behind)\tlow\n"
        "guideline-assessment\tfile\tarchitectural-guideline-assessment.md\tcommitted Gate C guideline assessment present and non-empty when file exists\tlow\n",
        encoding="utf-8",
    )

    assert audit_runs.scan_run_main(["--skill", "design", "--run-dir", str(run), "--pr", "7", "--scans-tsv", str(scans), "--current-version", "1.2.3"]) == 0
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]

    assert any(row["scan"] == "cache-freshness" for row in rows)
    row = next(row for row in rows if row["scan"] == "guideline-assessment")
    assert row["result"] == "pass"
    assert row["assessment_kind"] == "clean"


def test_scan_run_codex_round1_adherence_skips_unexpected_round_dir(tmp_path: Path, capsys):
    run = tmp_path / "run"
    weird = run / "round-final"
    weird.mkdir(parents=True)
    (weird / "panel-manifest.ndjson").write_text('{"tool":"codex"}\n', encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\ncodex-round1-adherence\tjsonl-field\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["scan"] == "codex-round1-adherence"
    assert row["result"] == "pass"


def _scan_codex_round_adherence(tmp_path: Path, run: Path, capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\ncodex-round1-adherence\tjsonl-field\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill", "implement", "--run-dir", str(run), "--pr", "7", "--scans-tsv", str(scans)]) == 0
    return json.loads(capsys.readouterr().out.splitlines()[0])


def _scan_guideline_outcome(tmp_path: Path, run: Path, capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\nguideline-ship-outcome\tnamed-handler\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill", "implement", "--run-dir", str(run), "--pr", "7", "--scans-tsv", str(scans)]) == 0
    return json.loads(capsys.readouterr().out.splitlines()[0])


def _write_guideline_outcome(
    run: Path,
    *,
    outcome: str = "pinned",
    reason: str = "note-pinned",
    **overrides: object,
) -> None:
    assessment_kind = "deviation"
    if outcome == "clean":
        assessment_kind = "clean" if reason == "clean-note" else ""
    elif outcome == "dropped":
        assessment_kind = ""
    payload = {
        "schema_version": "1",
        "phase": "implement",
        "step": "8",
        "outcome": outcome,
        "reason": reason,
        "detail": "",
        "guidelines_status": "present",
        "head_sha": "abc123",
        "base_ref": "origin/main",
        "assessment_kind": assessment_kind,
    } | overrides
    (run / ag.GUIDELINE_SHIP_OUTCOME_SIDECAR).write_text(json.dumps(payload), encoding="utf-8")


def test_guideline_ship_outcome_scan_missing_cutover_and_valid(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "manifest.json").write_text(
        json.dumps({"larch_version": config.GUIDELINE_SHIP_OUTCOME_MIN_LARCH_VERSION, "steps_ran": {"step8": True}}),
        encoding="utf-8",
    )
    (run / "final-summary.md").write_text("summary\n", encoding="utf-8")

    row = _scan_guideline_outcome(tmp_path, run, capsys)
    assert row["result"] == "fail"
    assert "missing" in str(row["detail"])

    _write_guideline_outcome(run, outcome="dropped", reason="note-redaction-failed")
    row = _scan_guideline_outcome(tmp_path, run, capsys)
    assert row["result"] == "pass"
    assert row["outcome"] == "dropped"
    assert row["reason"] == "note-redaction-failed"


@pytest.mark.parametrize(
    ("manifest", "expected_result"),
    [
        ({"larch_version": config.GUIDELINE_SHIP_OUTCOME_MIN_LARCH_VERSION, "steps_ran": {"step8": True}}, "pass"),
        ({"larch_version": config.GUIDELINE_SHIP_OUTCOME_MIN_LARCH_VERSION, "steps_ran": {"step8": False}}, "informational"),
    ],
)
def test_guideline_ship_outcome_scan_step8_parity(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    manifest: dict[str, object],
    expected_result: str,
) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "manifest.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    (run / "final-summary.md").write_text("summary\n", encoding="utf-8")
    _write_guideline_outcome(run, outcome="clean", reason="clean-note")

    row = _scan_guideline_outcome(tmp_path, run, capsys)

    assert row["result"] == expected_result


def test_guideline_ship_outcome_scan_legacy_and_malformed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "manifest.json").write_text('{"larch_version":"0.1.0","steps_ran":{"step8":true}}\n', encoding="utf-8")
    (run / "final-summary.md").write_text("summary\n", encoding="utf-8")
    row = _scan_guideline_outcome(tmp_path, run, capsys)
    assert row["result"] == "informational"

    (run / "manifest.json").write_text(
        json.dumps({"larch_version": config.GUIDELINE_SHIP_OUTCOME_MIN_LARCH_VERSION, "steps_ran": {"step8": True}}),
        encoding="utf-8",
    )
    (run / ag.GUIDELINE_SHIP_OUTCOME_SIDECAR).write_text(
        '{"schema_version":"1","phase":"implement","step":"8","outcome":"pinned","reason":"bogus","detail":"","guidelines_status":"present","base_ref":"origin/main","assessment_kind":"deviation"}\n',
        encoding="utf-8",
    )
    row = _scan_guideline_outcome(tmp_path, run, capsys)
    assert row["result"] == "fail"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"phase": "design"}, "phase must be implement"),
        ({"step": "7"}, "step must be 8"),
        ({"base_ref": ""}, "base_ref is empty"),
        ({"outcome": "dropped", "reason": "note-pinned"}, "fields are inconsistent for dropped guidelines"),
    ],
)
def test_guideline_ship_outcome_scan_rejects_schema_mismatches(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    overrides: dict[str, object],
    message: str,
) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "manifest.json").write_text(
        json.dumps({"larch_version": config.GUIDELINE_SHIP_OUTCOME_MIN_LARCH_VERSION, "steps_ran": {"step8": True}}),
        encoding="utf-8",
    )
    (run / "final-summary.md").write_text("summary\n", encoding="utf-8")
    _write_guideline_outcome(run, **overrides)

    row = _scan_guideline_outcome(tmp_path, run, capsys)

    assert row["result"] == "fail"
    assert message in str(row["detail"])


def test_scan_codex_round1_adherence_allows_round_two_generic_and_specialist(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    run = tmp_path / "run"
    round2 = run / "round-2"
    round2.mkdir(parents=True)
    (round2 / "panel-manifest.ndjson").write_text(
        json.dumps({"slot": "generalist", "tool": "codex"}) + "\n"
        + json.dumps({"slot": "testing", "tool": "codex"}) + "\n",
        encoding="utf-8",
    )

    row = _scan_codex_round_adherence(tmp_path, run, capsys)

    assert row["scan"] == "codex-round1-adherence"
    assert row["result"] == "pass"


def test_scan_codex_round1_adherence_allows_round_two_generic_only(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    run = tmp_path / "run"
    round2 = run / "round-2"
    round2.mkdir(parents=True)
    (round2 / "panel-manifest.ndjson").write_text(json.dumps({"slot": "generalist", "tool": "codex"}) + "\n", encoding="utf-8")

    row = _scan_codex_round_adherence(tmp_path, run, capsys)

    assert row["result"] == "pass"


def test_scan_codex_round1_adherence_allows_round_three_specialist_codex(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    run = tmp_path / "run"
    round3 = run / "round-3"
    round3.mkdir(parents=True)
    (round3 / "panel-manifest.ndjson").write_text(
        json.dumps({"slot": "testing", "tool": "codex"}) + "\n"
        + json.dumps({"slot": "dyn-api-codex", "tool": "codex"}) + "\n",
        encoding="utf-8",
    )

    row = _scan_codex_round_adherence(tmp_path, run, capsys)

    assert row["result"] == "pass"


def test_scan_codex_round1_adherence_fails_round_three_generic_codex(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    run = tmp_path / "run"
    round3 = run / "round-3"
    round3.mkdir(parents=True)
    (round3 / "panel-manifest.ndjson").write_text(
        json.dumps({"slot": "generalist", "tool": "codex"}) + "\n"
        + json.dumps({"slot": "codex-plan-generic", "tool": "codex"}) + "\n",
        encoding="utf-8",
    )

    row = _scan_codex_round_adherence(tmp_path, run, capsys)

    assert row["result"] == "fail"
    assert row["rounds_with_generic_codex"] == [3]
    assert row["violations"] == [{"round": 3, "slot": "generalist"}, {"round": 3, "slot": "codex-plan-generic"}]


def test_scan_codex_round1_adherence_fails_round_four_generic_codex(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    run = tmp_path / "run"
    round4 = run / "round-4"
    round4.mkdir(parents=True)
    (round4 / "panel-manifest.ndjson").write_text(json.dumps({"slot": "generalist", "tool": "codex"}) + "\n", encoding="utf-8")

    row = _scan_codex_round_adherence(tmp_path, run, capsys)

    assert row["result"] == "fail"
    assert row["rounds_with_generic_codex"] == [4]


def test_oos_silent_drop_no_git_fallback(tmp_path: Path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    (run / "oos-accepted-main-agent.md").write_text("### OOS_1: thing\n- **Focus area**: correctness\n", encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\noos-silent-drop\tfile\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans)]) == 0
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    row = next(r for r in rows if r["scan"] == "oos-silent-drop")
    assert row["result"] == "fail"
    assert row["inline_triage_hits"] == 0


def test_oos_silent_drop_counts_enterprise_gh_host_urls(tmp_path: Path, monkeypatch, capsys):
    run = tmp_path / "run"
    run.mkdir()
    (run / "oos-accepted-main-agent.md").write_text("### OOS_1: thing\n- **Focus area**: correctness\n", encoding="utf-8")
    (run / "oos-issues-created.md").write_text("https://github.enterprise.test/o/r/issues/12\n", encoding="utf-8")
    monkeypatch.setenv("GH_HOST", "github.enterprise.test")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\noos-silent-drop\tfile\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "pass"
    assert row["issue_urls"] == 1


def test_oos_silent_drop_accepts_oos_header_whitespace(tmp_path: Path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    (run / "oos-accepted-main-agent.md").write_text("### \tOOS_1: thing\n- **Focus area**: correctness\n", encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\noos-silent-drop\tfile\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "fail"
    assert row["non_security_oos_blocks"] == 1


def test_oos_silent_drop_security_hardening_focus_area_is_excluded(tmp_path: Path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    (run / "oos-accepted-main-agent.md").write_text("### OOS_1: private\n- **focus-area**: security-hardening\n", encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\noos-silent-drop\tfile\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "skip"


def test_compute_counters_legacy_alias(tmp_path: Path, capsys):
    d = tmp_path / "scans"; d.mkdir()
    (d / "scan-results-1.ndjson").write_text('{"scan":"ns-retry-sidecars","result":"skip"}\n', encoding="utf-8")
    prior = tmp_path / "prior.md"
    prior.write_text("---\nns_retries_cursor_specialist_launches: 4\n---\n", encoding="utf-8")
    assert audit_runs.compute_counters_main(["--scan-results-dir", str(d), "--prior-frontmatter", str(prior)]) == 0
    out = dict(line.split("=",1) for line in capsys.readouterr().out.splitlines())
    assert out["NS_RETRIES_CURSOR_SPECIALIST"] == "4"
    assert out["NS_RETRIES_SKIPPED_RUNS"] == "1"


def test_compute_counters_reads_only_top_frontmatter(tmp_path: Path, capsys):
    d = tmp_path / "scans"; d.mkdir()
    (d / "scan-results-1.ndjson").write_text('{"scan":"changelog-rebase-conflicts","count":1}\n', encoding="utf-8")
    prior = tmp_path / "prior.md"
    prior.write_text("---\nchangelog_rebase_conflicts: 2\n---\n\nExample:\nchangelog_rebase_conflicts: 99\n", encoding="utf-8")
    assert audit_runs.compute_counters_main(["--scan-results-dir", str(d), "--prior-frontmatter", str(prior)]) == 0
    out = dict(line.split("=",1) for line in capsys.readouterr().out.splitlines())
    assert out["CHANGELOG_REBASE_CONFLICTS"] == "3"
    assert out["CHANGELOG_DELTA"] == "1"


def test_compute_counters_treats_malformed_numbers_as_zero(tmp_path: Path, capsys):
    d = tmp_path / "scans"; d.mkdir()
    (d / "scan-results-1.ndjson").write_text(
        '{"scan":"exon-misclassification","count":"bad"}\n'
        '{"scan":"oos-category-mangle","count":[]}\n'
        '{"scan":"category-stats","canonical":"nope","oos_blank":{}}\n'
        '{"scan":"ns-retry-sidecars","result":"fail","count":"x"}\n'
        '{"scan":"changelog-rebase-conflicts","count":"nan"}\n',
        encoding="utf-8",
    )
    assert audit_runs.compute_counters_main(["--scan-results-dir", str(d)]) == 0
    out = dict(line.split("=",1) for line in capsys.readouterr().out.splitlines())
    assert out["EXON_DELTA"] == "0"
    assert out["OOS_MANGLED_DELTA"] == "0"
    assert out["OOS_CLEAN_DELTA"] == "0"
    assert out["NS_RETRIES_DELTA"] == "0"
    assert out["CHANGELOG_DELTA"] == "0"


def test_compute_counters_reports_guideline_outcome_counts(tmp_path: Path, capsys):
    d = tmp_path / "scans"; d.mkdir()
    (d / "scan-results-1.ndjson").write_text(
        '{"scan":"guideline-ship-outcome","result":"pass","outcome":"pinned"}\n'
        '{"scan":"guideline-ship-outcome","result":"pass","outcome":"clean"}\n'
        '{"scan":"guideline-ship-outcome","result":"pass","outcome":"dropped"}\n',
        encoding="utf-8",
    )
    assert audit_runs.compute_counters_main(["--scan-results-dir", str(d)]) == 0
    out = dict(line.split("=",1) for line in capsys.readouterr().out.splitlines())
    assert out["GUIDELINE_OUTCOME_RUNS"] == "3"
    assert out["GUIDELINE_OUTCOME_PINNED"] == "1"
    assert out["GUIDELINE_OUTCOME_CLEAN"] == "1"
    assert out["GUIDELINE_OUTCOME_DROPPED"] == "1"
    assert out["GUIDELINE_DROP_RATE_BPS"] == "3333"


class AuditRunner:
    def __init__(self, responses: dict[tuple[str, ...], CommandResult]):
        self.responses = responses

    def run(self, argv, **_kwargs):
        key = tuple(argv)
        if key not in self.responses:
            raise AssertionError(f"unexpected argv: {argv}")
        return self.responses[key]


def cr(argv: tuple[str, ...], stdout: str = "", stderr: str = "", rc: int = 0) -> CommandResult:
    return CommandResult(argv, rc, stdout, stderr, 0.01)


def test_close_priors_reports_transport_failure_before_json_parse(monkeypatch, capsys):
    runner = AuditRunner({
        ("gh","issue","list","--state","open","--limit","100000","--label","audit-report","--repo","o/r","--json","number,title"): cr(("gh",), stdout="not json", stderr="network down", rc=1),
    })
    monkeypatch.setattr(audit_runs.proc, "run", runner.run)
    assert audit_runs.close_priors_main(["--skill","implement","--new-issue-number","9","--repo","o/r"]) == 1
    out = capsys.readouterr().out
    assert "ISSUE_LIST_FAILED=true" in out
    assert "REASON=gh issue list failed" in out


def test_close_priors_reports_malformed_success_json(monkeypatch, capsys):
    runner = AuditRunner({
        ("gh","issue","list","--state","open","--limit","100000","--label","audit-report","--repo","o/r","--json","number,title"): cr(("gh",), stdout="not json", rc=0),
    })
    monkeypatch.setattr(audit_runs.proc, "run", runner.run)
    assert audit_runs.close_priors_main(["--skill","implement","--new-issue-number","9","--repo","o/r"]) == 1
    assert "ISSUE_LIST_FAILED=true" in capsys.readouterr().out


def test_close_priors_body_file_failure_fallback(monkeypatch, capsys):
    runner = AuditRunner({
        ("gh","issue","list","--state","open","--limit","100000","--label","audit-report","--repo","o/r","--json","number,title"): cr(("gh",), stdout="[]"),
    })
    monkeypatch.setattr(audit_runs.proc, "run", runner.run)
    def fail_named_temp(*_args, **_kwargs):
        raise OSError("no temp")
    monkeypatch.setattr(audit_runs.tempfile, "NamedTemporaryFile", fail_named_temp)
    assert audit_runs.close_priors_main(["--skill","implement","--new-issue-number","9","--repo","o/r"]) == 1
    out = capsys.readouterr().out
    assert "BODY_FILE_FAILED=true" in out
    assert "REASON=mktemp failed" in out


def test_close_priors_reports_partial_success(monkeypatch, capsys):
    prior = json.dumps([
        {"number": 7, "title": "[Implement Run Logs Audit 2026 Report] old"},
        {"number": 8, "title": "[Implement Run Logs Audit 2026 Report] older"},
    ])
    class PartialCloseRunner:
        def run(self, argv, **_kwargs):
            if argv[:3] == ["gh","issue","list"]:
                return cr(("gh",), stdout=prior)
            if argv[:4] == ["gh","issue","comment","7"]:
                return cr(("gh",))
            if argv[:4] == ["gh","issue","close","7"]:
                return cr(("gh",))
            if argv[:4] == ["gh","issue","comment","8"]:
                return cr(("gh",), stderr="boom", rc=1)
            raise AssertionError(f"unexpected argv: {argv}")
    monkeypatch.setattr(audit_runs.proc, "run", PartialCloseRunner().run)
    assert audit_runs.close_priors_main(["--skill","implement","--new-issue-number","9","--repo","o/r"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert "CLOSED_NUMBER=7" in out
    assert any(line.startswith("CLOSE_FAILED=8\tREASON=gh issue comment failed") for line in out)


def test_resolve_prs_reports_issue_list_failure(monkeypatch, capsys):
    runner = AuditRunner({
        ("gh","issue","list","--state","all","--limit","100000","--label","audit-report","--repo","o/r","--json","number,title,createdAt"): cr(("gh",), stderr="auth", rc=1),
    })
    monkeypatch.setattr(audit_runs.proc, "run", runner.run)
    assert audit_runs.resolve_prs_main(["--skill","implement","--repo","o/r"]) == 0
    out = capsys.readouterr().out
    assert "ERROR=gh issue list failed" in out


def test_resolve_prs_stdout_key_order_on_error(monkeypatch, capsys):
    runner = AuditRunner({
        ("gh","issue","list","--state","all","--limit","100000","--label","audit-report","--repo","o/r","--json","number,title,createdAt"): cr(("gh",), stderr="auth", rc=1),
    })
    monkeypatch.setattr(audit_runs.proc, "run", runner.run)
    assert audit_runs.resolve_prs_main(["--skill","implement","--repo","o/r"]) == 0
    keys = [line.split("=", 1)[0] for line in capsys.readouterr().out.splitlines()]
    assert keys == ["IMPLICIT_SINCE_LAST_AUDIT", "PRIOR_REPORT_NUMBER", "PR_LIST", "PR_COUNT", "RESOLVED_ECHO", "ERROR"]


def test_resolve_prs_unknown_argv_exits_one_stderr_only(capsys):
    assert audit_runs.resolve_prs_main(["--skill","implement","--bogus"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unrecognized arguments: --bogus" in captured.err


def test_resolve_prs_reports_issue_view_failure(monkeypatch, capsys):
    prior = json.dumps([{"number": 12, "title": "[Implement Run Logs Audit 2026 Report]", "createdAt": "2026-01-01T00:00:00Z"}])
    runner = AuditRunner({
        ("gh","issue","list","--state","all","--limit","100000","--label","audit-report","--repo","o/r","--json","number,title,createdAt"): cr(("gh",), stdout=prior),
        ("gh","issue","view","12","--repo","o/r","--json","body"): cr(("gh",), stderr="boom", rc=1),
    })
    monkeypatch.setattr(audit_runs.proc, "run", runner.run)
    assert audit_runs.resolve_prs_main(["--skill","implement","--repo","o/r"]) == 0
    assert "ERROR=gh issue view failed for prior audit-report #12" in capsys.readouterr().out


def test_resolve_prs_ignores_audited_range_outside_frontmatter(monkeypatch, capsys):
    prior = json.dumps([{"number": 12, "title": "[Implement Run Logs Audit 2026 Report]", "createdAt": "2026-01-01T00:00:00Z"}])
    body = json.dumps({"body": "---\ntitle: report\n---\n\n```yaml\naudited_pr_range:\n  last: 99\n```\n"})
    runner = AuditRunner({
        ("gh","issue","list","--state","all","--limit","100000","--label","audit-report","--repo","o/r","--json","number,title,createdAt"): cr(("gh",), stdout=prior),
        ("gh","issue","view","12","--repo","o/r","--json","body"): cr(("gh",), stdout=body),
    })
    monkeypatch.setattr(audit_runs.proc, "run", runner.run)
    assert audit_runs.resolve_prs_main(["--skill","implement","--repo","o/r"]) == 0
    assert "malformed or missing frontmatter" in capsys.readouterr().out


def test_preflight_blocks_stale_local_main_and_redacts_remote(monkeypatch, capsys):
    responses = {
        ("git","fetch","origin","main"): cr(("git",)),
        ("git","branch","--show-current"): cr(("git",), stdout="feature\n"),
        ("git","rev-parse","--verify","main^{commit}"): cr(("git",), stdout="aaa\n"),
        ("git","rev-parse","--verify","origin/main^{commit}"): cr(("git",), stdout="bbb\n"),
    }
    monkeypatch.setattr(audit_runs.proc, "run", AuditRunner(responses).run)
    assert audit_runs.preflight_main(["--skill","implement","--repo","o/r"]) == 0
    out = capsys.readouterr().out
    assert "PREFLIGHT_OK=false" in out
    assert "local main is stale" in out


def test_preflight_redacts_remote_url_identity_failure(monkeypatch, capsys):
    responses = {
        ("git","fetch","origin","main"): cr(("git",)),
        ("git","branch","--show-current"): cr(("git",), stdout="feature\n"),
        ("git","rev-parse","--verify","main^{commit}"): cr(("git",), stdout="aaa\n"),
        ("git","rev-parse","--verify","origin/main^{commit}"): cr(("git",), stdout="aaa\n"),
        ("git","status","--porcelain"): cr(("git",), stdout=""),
        ("git","config","--get","remote.origin.url"): cr(("git",), stdout="https://ghp_secret123@not-github.invalid/o/r.git\n"),
        ("gh","repo","view","o/r","--json","url"): cr(("gh",), stdout='{"url":""}\n'),
        ("gh","issue","list","--state","all","--label","audit-report","--repo","o/r","--json","number,createdAt","--limit","50"): cr(("gh",), stdout="[]\n"),
    }
    monkeypatch.setattr(audit_runs.proc, "run", AuditRunner(responses).run)
    assert audit_runs.preflight_main(["--skill","implement","--repo","o/r"]) == 0
    out = capsys.readouterr().out
    assert "ghp_secret123" not in out
    assert "<redacted>@" in out


def test_preflight_missing_repo_uses_default_kv(monkeypatch, capsys):
    calls: list[list[str]] = []
    def run(argv, **_kwargs):
        calls.append(list(argv))
        if argv[:3] == ["git","fetch","origin"]:
            return cr(("git",))
        if argv[:3] == ["git","branch","--show-current"]:
            return cr(("git",), stdout="feature\n")
        if argv[:3] == ["git","rev-parse","--verify"]:
            return cr(("git",), stdout="abc\n")
        if argv[:2] == ["git","status"]:
            return cr(("git",), stdout="")
        if argv[:3] == ["git","config","--get"]:
            return cr(("git",), stdout="https://github.com/character-ai/larch.git\n")
        if argv[:3] == ["gh","repo","view"]:
            return cr(("gh",), stdout='{"url":"https://github.com/character-ai/larch"}\n')
        if argv[:3] == ["gh","issue","list"]:
            return cr(("gh",), stdout="[]")
        raise AssertionError(f"unexpected argv: {argv}")
    monkeypatch.setattr(audit_runs.proc, "run", run)
    assert audit_runs.preflight_main(["--skill","implement"]) == 0
    assert "PREFLIGHT_OK=true" in capsys.readouterr().out
    assert any(call[:3] == ["gh","repo","view"] and call[3] == "character-ai/larch" for call in calls)


def test_preflight_allow_concurrent_skips_recent_audit_probe(monkeypatch, capsys):
    responses = {
        ("git","fetch","origin","main"): cr(("git",)),
        ("git","branch","--show-current"): cr(("git",), stdout="feature\n"),
        ("git","rev-parse","--verify","main^{commit}"): cr(("git",), stdout="aaa\n"),
        ("git","rev-parse","--verify","origin/main^{commit}"): cr(("git",), stdout="aaa\n"),
        ("git","status","--porcelain"): cr(("git",), stdout=""),
        ("git","config","--get","remote.origin.url"): cr(("git",), stdout="https://github.com/o/r.git\n"),
        ("gh","repo","view","o/r","--json","url"): cr(("gh",), stdout='{"url":"https://github.com/o/r"}\n'),
    }
    runner = AuditRunner(responses)
    monkeypatch.setattr(audit_runs.proc, "run", runner.run)
    assert audit_runs.preflight_main(["--skill","implement","--repo","o/r","--allow-concurrent"]) == 0
    assert "PREFLIGHT_OK=true" in capsys.readouterr().out


def test_map_runs_matches_parent_issue_number_exactly(monkeypatch, tmp_path: Path, capsys):
    root = tmp_path / "larch-logs" / "implement"
    wrong = root / "wrong"
    right = root / "right"
    wrong.mkdir(parents=True)
    right.mkdir()
    (wrong / "parent-issue.md").write_text("ISSUE_NUMBER=123\n", encoding="utf-8")
    (wrong / "manifest.json").write_text('{"started_at":"2026-01-02T00:00:00+00:00","larch_version":"9.9.9"}\n', encoding="utf-8")
    (right / "parent-issue.md").write_text("ISSUE_NUMBER=12\n", encoding="utf-8")
    (right / "manifest.json").write_text('{"started_at":"2026-01-01T00:00:00+00:00","larch_version":"1.2.3"}\n', encoding="utf-8")
    runner = AuditRunner({
        ("gh","pr","view","5","--repo","o/r","--json","body"): cr(("gh",), stdout='{"body":"Closes #12"}\n'),
    })
    monkeypatch.setattr(audit_runs.proc, "run", runner.run)
    assert audit_runs.map_runs_main(["--skill","implement","--pr-list","5","--repo","o/r","--log-root",str(root)]) == 0
    assert capsys.readouterr().out.splitlines()[0] == "5\tright\t2026-01-01T00:00:00+00:00\t1.2.3\t12"


def test_map_runs_reports_tied_parent_issue_candidates(monkeypatch, tmp_path: Path, capsys):
    root = tmp_path / "larch-logs" / "implement"
    for name in ("a", "b"):
        run = root / name
        run.mkdir(parents=True)
        (run / "parent-issue.md").write_text("ISSUE_NUMBER=12\n", encoding="utf-8")
        (run / "manifest.json").write_text('{"started_at":"2026-01-01T00:00:00+00:00","larch_version":"1.2.3"}\n', encoding="utf-8")
    runner = AuditRunner({
        ("gh","pr","view","5","--repo","o/r","--json","body"): cr(("gh",), stdout='{"body":"Closes #12"}\n'),
    })
    monkeypatch.setattr(audit_runs.proc, "run", runner.run)
    assert audit_runs.map_runs_main(["--skill","implement","--pr-list","5","--repo","o/r","--log-root",str(root)]) == 0
    captured = capsys.readouterr()
    assert "MAP_PARENT_ISSUE_AMBIGUOUS=true" in captured.err
    assert captured.out.splitlines()[0] == "5\t\t\t\t12"


def test_map_runs_reports_pr_view_failure(monkeypatch, tmp_path: Path, capsys):
    root = tmp_path / "larch-logs" / "implement"
    root.mkdir(parents=True)
    runner = AuditRunner({
        ("gh","pr","view","5","--repo","o/r","--json","body"): cr(("gh",), stderr="auth", rc=1),
    })
    monkeypatch.setattr(audit_runs.proc, "run", runner.run)
    assert audit_runs.map_runs_main(["--skill","implement","--pr-list","5","--repo","o/r","--log-root",str(root)]) == 0
    captured = capsys.readouterr()
    assert "MAP_GH_PR_VIEW_FAILED=true" in captured.err
    assert captured.out.splitlines()[0] == "5\t\t\t\t"


def test_map_runs_does_not_use_manifest_fallback_after_pr_body_failure(monkeypatch, tmp_path: Path, capsys):
    root = tmp_path / "larch-logs" / "implement"
    run = root / "stale"
    run.mkdir(parents=True)
    (run / "manifest.json").write_text('{"pr_number":"5","started_at":"2026-01-01T00:00:00+00:00","larch_version":"1.2.3","closes_issue":"12"}\n', encoding="utf-8")
    runner = AuditRunner({
        ("gh","pr","view","5","--repo","o/r","--json","body"): cr(("gh",), stderr="auth", rc=1),
    })
    monkeypatch.setattr(audit_runs.proc, "run", runner.run)
    assert audit_runs.map_runs_main(["--skill","implement","--pr-list","5","--repo","o/r","--log-root",str(root)]) == 0
    captured = capsys.readouterr()
    assert "MAP_GH_PR_VIEW_FAILED=true" in captured.err
    assert captured.out.splitlines()[0] == "5\t\t\t\t"


def test_scan_run_counts_non_string_categories_as_mangled(tmp_path: Path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    rows = [
        {"id":"FINDING_1","outcome":"accepted","phase":"plan-review","category":7},
        {"id":"FINDING_2","outcome":"accepted","phase":"plan-review","category":True},
        {"id":"FINDING_3","outcome":"accepted","phase":"plan-review","category":"correctness"},
    ]
    (run / "review-findings-full.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\noos-category-mangle\tjsonl-field\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans)]) == 0
    out = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    mangle = next(row for row in out if row["scan"] == "oos-category-mangle")
    stats = next(row for row in out if row["scan"] == "category-stats")
    assert mangle["count"] == 2
    assert stats["mangled"] == 2


def test_scan_run_treats_array_and_object_categories_as_blank(tmp_path: Path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    rows = [
        {"id":"FINDING_1","outcome":"accepted","phase":"plan-review","category":["correctness"]},
        {"id":"OOS_1","outcome":"accepted","phase":"plan-review","category":{"name":"correctness"}},
    ]
    (run / "review-findings-full.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\noos-category-mangle\tjsonl-field\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans)]) == 0
    out = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    mangle = next(row for row in out if row["scan"] == "oos-category-mangle")
    stats = next(row for row in out if row["scan"] == "category-stats")
    assert mangle["count"] == 0
    assert stats["blank"] == 2
    assert stats["oos_blank"] == 1


def test_scan_codex_generalist_waste_fails_slow_no_issues(tmp_path: Path, capsys):
    run = tmp_path / "run"
    round1 = run / "round-1"
    round1.mkdir(parents=True)
    (round1 / "round-meta.json").write_text(json.dumps({
        "reviewer_signals": [{"output_basename": "codex-generalist-output.txt", "result_kind": "NO_ISSUES_FOUND"}],
        "wrapper_logs": {"codex": "✓ codex agent: completed (exit code 0, 121s elapsed, output 12 bytes)\n"},
    }), encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\ncodex-generalist-waste\tjson\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "fail"
    assert row["elapsed_seconds"] == 121


def test_scan_codex_generalist_waste_passes_no_issues_too_thin(tmp_path: Path, capsys):
    run = tmp_path / "run"
    round1 = run / "round-1"
    round1.mkdir(parents=True)
    (round1 / "round-meta.json").write_text(json.dumps({
        "reviewer_signals": [{"output_basename": "codex-generalist-output.txt", "result_kind": "NO_ISSUES_FOUND_TOO_THIN"}],
        "wrapper_logs": {"codex": "121s elapsed\n"},
    }), encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\ncodex-generalist-waste\tjson\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "pass"
    assert row["elapsed_seconds"] == 121


def test_scan_codex_generalist_waste_uses_timing_report_fallback(tmp_path: Path, capsys):
    run = tmp_path / "run"
    round1 = run / "round-1"
    round1.mkdir(parents=True)
    (round1 / "round-meta.json").write_text(json.dumps({
        "reviewer_signals": [{"output_basename": "codex-generalist-output.txt", "result_kind": "NO_ISSUES_FOUND"}],
    }), encoding="utf-8")
    (run / "timing-report.json").write_text(json.dumps({
        "vendor_task_averages": [
            {"vendor": "codex", "task_kind": "codex-review-generic", "max_seconds": 121},
        ],
    }), encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\ncodex-generalist-waste\tjson\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "fail"
    assert row["elapsed_seconds"] == 121


def test_scan_codex_generalist_waste_uses_timing_report_steps_fallback(tmp_path: Path, capsys):
    run = tmp_path / "run"
    round1 = run / "round-1"
    round1.mkdir(parents=True)
    (round1 / "round-meta.json").write_text(json.dumps({
        "reviewer_signals": [{"output_basename": "codex-generalist-output.txt", "result_kind": "NO_ISSUES_FOUND"}],
    }), encoding="utf-8")
    (run / "timing-report.json").write_text(json.dumps({
        "steps": [
            {"vendor": "codex", "task_kind": "codex-review-generic", "duration_seconds": 122},
        ],
    }), encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\ncodex-generalist-waste\tjson\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "fail"
    assert row["elapsed_seconds"] == 122


def test_scan_codex_generalist_waste_uses_timing_report_per_step_fallback(tmp_path: Path, capsys):
    run = tmp_path / "run"
    round1 = run / "round-1"
    round1.mkdir(parents=True)
    (round1 / "round-meta.json").write_text(json.dumps({
        "reviewer_signals": [{"output_basename": "codex-generalist-output.txt", "result_kind": "NO_ISSUES_FOUND"}],
    }), encoding="utf-8")
    (run / "timing-report.json").write_text(json.dumps({
        "per_step": [
            {"skill": "implement", "step": "Step 5 — code review", "duration_seconds": 123},
        ],
    }), encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\ncodex-generalist-waste\tjson\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "fail"
    assert row["elapsed_seconds"] == 123


def test_scan_ns_retry_sidecars_legacy_fallback_without_reviewer_signals(tmp_path: Path, capsys):
    run = tmp_path / "run"
    round1 = run / "round-1"
    round1.mkdir(parents=True)
    (round1 / "codex-generalist-output-ns-retry.txt").write_text("retry\n", encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\nns-retry-sidecars\tfile\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "fail"
    assert row["count"] == 1
    assert row["reasons"] == {"UNKNOWN": 1}
    assert row["detail"] == "legacy sidecar fallback (reviewer_signals unavailable)"


def test_scan_run_malformed_review_findings_category_stats_is_partial(tmp_path: Path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    good = json.dumps({"id":"FINDING_1","outcome":"accepted","phase":"plan-review","category":"not-canonical"})
    (run / "review-findings-full.jsonl").write_text(f"{good}\n{{not json\n", encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\noos-category-mangle\tjsonl-field\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans)]) == 0
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    stats = next(row for row in rows if row["scan"] == "category-stats")
    assert stats["partial_data"] is True
    assert stats["partial_reason"] == "malformed_review_findings_jsonl"
    assert stats["detail"] == "jq failed (category-stats): parse error"
    assert stats["mangled"] == 0


def _scan_category_stats(run: Path, scans: Path, capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    assert audit_runs.scan_run_main(["--skill", "implement", "--run-dir", str(run), "--pr", "7", "--scans-tsv", str(scans)]) == 0
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    return next(row for row in rows if row["scan"] == "category-stats")


def test_scan_run_empty_review_findings_self_review_tally_populates_blank_stats(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "review-findings-full.jsonl").write_text("", encoding="utf-8")
    (run / "code-review-tally.json").write_text(
        '{"mode":"self-review","accepted_count":2,"rejected_count":1}\n',
        encoding="utf-8",
    )
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\noos-category-mangle\tjsonl-field\n", encoding="utf-8")

    stats = _scan_category_stats(run, scans, capsys)

    assert stats["partial_data"] is False
    assert stats["blank"] == 3
    assert stats["canonical"] == 0
    assert stats["mangled"] == 0


def test_scan_run_absent_review_findings_self_review_tally_populates_blank_stats(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "code-review-tally.json").write_text(
        '{"mode":"self-review","accepted_count":"bad","rejected_count":2}\n',
        encoding="utf-8",
    )
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\noos-category-mangle\tjsonl-field\n", encoding="utf-8")

    stats = _scan_category_stats(run, scans, capsys)

    assert stats["partial_data"] is False
    assert stats["blank"] == 2
    assert stats["canonical"] == 0
    assert stats["mangled"] == 0


def test_self_review_tally_rows_preserve_audit_output_shape(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "code-review-tally.json").write_text(
        '{"mode":"self-review","accepted_count":"bad","rejected_count":2}\n',
        encoding="utf-8",
    )

    rows = audit_runs._self_review_tally_rows(run)

    assert rows == [
        {
            "id": "SELF_REVIEW_REJECTED_1",
            "source": "committed-self-review-tally",
            "phase": "code-review",
            "outcome": "rejected",
            "category": "",
            "severity": "(none)",
            "body_severity": "",
            "focus_area": "",
        },
        {
            "id": "SELF_REVIEW_REJECTED_2",
            "source": "committed-self-review-tally",
            "phase": "code-review",
            "outcome": "rejected",
            "category": "",
            "severity": "(none)",
            "body_severity": "",
            "focus_area": "",
        },
    ]


def test_scan_run_outcome_less_review_findings_uses_self_review_tally(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run = tmp_path / "run"
    run.mkdir()
    lines = [
        json.dumps({"id": "FINDING_1", "phase": "retroactive-backfill", "outcome": "accepted"}),
        json.dumps({"id": "FINDING_2", "phase": "code-review"}),
    ]
    (run / "review-findings-full.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (run / "code-review-tally.json").write_text(
        '{"mode":"self-review","accepted_count":2,"rejected_count":1}\n',
        encoding="utf-8",
    )
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\noos-category-mangle\tjsonl-field\n", encoding="utf-8")

    stats = _scan_category_stats(run, scans, capsys)

    assert stats["partial_data"] is False
    assert stats["blank"] == 3
    assert stats["canonical"] == 0
    assert stats["mangled"] == 0


def test_scan_run_malformed_review_findings_does_not_use_self_review_tally(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "review-findings-full.jsonl").write_text("{not json\n", encoding="utf-8")
    (run / "code-review-tally.json").write_text(
        '{"mode":"self-review","accepted_count":2,"rejected_count":1}\n',
        encoding="utf-8",
    )
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\noos-category-mangle\tjsonl-field\n", encoding="utf-8")

    stats = _scan_category_stats(run, scans, capsys)

    assert stats["partial_data"] is True
    assert stats["partial_reason"] == "malformed_review_findings_jsonl"
    assert stats["blank"] == 0


def test_oos_silent_drop_malformed_oos_issues_ndjson_reports_error(tmp_path: Path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    (run / "oos-accepted-main-agent.md").write_text("### OOS_1: thing\n- **Focus area**: correctness\n", encoding="utf-8")
    (run / "oos-issues.ndjson").write_text("{not json\n", encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\noos-silent-drop\tfile\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "error"
    assert row["detail"] == "jq parse failure while reading oos-issues.ndjson for rejected-OOS markers"


def test_scan_required_bail_and_step9a1_gating(tmp_path: Path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    (run / "manifest.json").write_text('{"steps_ran":{}}\n', encoding="utf-8")
    (run / "final-summary.md").write_text("Run bailed\n", encoding="utf-8")
    required = tmp_path / "required.tsv"
    required.write_text("relative_path\tcondition\nrun-statistics.md\tstep9a1\n", encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\nrequired-file-presence\tfile\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans),"--required-files-tsv",str(required)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "pass"

    (run / "manifest.json").write_text('{"steps_ran":{"step8":true}}\n', encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans),"--required-files-tsv",str(required)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "pass"


def test_scan_required_bailed_heading_with_pr_evidence_reports_missing(tmp_path: Path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    (run / "manifest.json").write_text('{"steps_ran":{},"pr_number":7}\n', encoding="utf-8")
    (run / "final-summary.md").write_text("## /implement run run: bailed\n", encoding="utf-8")
    required = tmp_path / "required.tsv"
    required.write_text("relative_path\tcondition\nrun-statistics.md\tstep9a1\n", encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\nrequired-file-presence\tfile\n", encoding="utf-8")

    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans),"--required-files-tsv",str(required)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "fail"
    assert row["missing"] == ["run-statistics.md"]


def test_scan_required_corrupt_manifest_does_not_bail_skip(tmp_path: Path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    (run / "manifest.json").write_text("{not json\n", encoding="utf-8")
    (run / "final-summary.md").write_text("Run bailed\n", encoding="utf-8")
    required = tmp_path / "required.tsv"
    required.write_text("relative_path\tcondition\nrun-statistics.md\tstep9a1\n", encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\nrequired-file-presence\tfile\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans),"--required-files-tsv",str(required)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "fail"
    assert row["missing"] == ["run-statistics.md"]


def test_scan_required_non_dict_steps_ran_does_not_bail_skip(tmp_path: Path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    (run / "manifest.json").write_text('{"steps_ran":[]}\n', encoding="utf-8")
    (run / "final-summary.md").write_text("Run bailed\n", encoding="utf-8")
    required = tmp_path / "required.tsv"
    required.write_text("relative_path\tcondition\nrun-statistics.md\tstep9a1\n", encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\nrequired-file-presence\tfile\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans),"--required-files-tsv",str(required)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "fail"
    assert row["missing"] == ["run-statistics.md"]


def test_scan_required_non_bail_incomplete_and_explicit_step9a1_false(tmp_path: Path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    required = tmp_path / "required.tsv"
    required.write_text("relative_path\tcondition\nrun-statistics.md\tstep9a1\n", encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\nrequired-file-presence\tfile\n", encoding="utf-8")
    (run / "manifest.json").write_text('{"steps_ran":{}}\n', encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans),"--required-files-tsv",str(required)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "fail"
    assert row["missing"] == ["run-statistics.md"]
    (run / "manifest.json").write_text('{"steps_ran":{"step9a1":false}}\n', encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans),"--required-files-tsv",str(required)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "pass"



def test_scan_required_step9a1_ignores_provisional_ndjson(tmp_path: Path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    required = tmp_path / "required.tsv"
    required.write_text("relative_path\tcondition\nrun-statistics.md\tstep9a1\n", encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\nrequired-file-presence\tfile\n", encoding="utf-8")
    (run / "manifest.json").write_text('{"steps_ran":{}}\n', encoding="utf-8")
    (run / "oos-issues.ndjson").write_text('{"phase":"implement"}\n', encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans),"--required-files-tsv",str(required)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "fail"
    assert row["missing"] == ["run-statistics.md"]
    (run / "run-statistics.md").write_text("Run run: 0 OOS issue(s) filed.\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans),"--required-files-tsv",str(required)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "pass"


def test_scan_required_stale_step9a1_true_without_stats_fails(tmp_path: Path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    required = tmp_path / "required.tsv"
    required.write_text("relative_path\tcondition\nrun-statistics.md\tstep9a1\n", encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\nrequired-file-presence\tfile\n", encoding="utf-8")
    (run / "manifest.json").write_text('{"steps_ran":{"step9a1":true}}\n', encoding="utf-8")
    (run / "oos-issues.ndjson").write_text('{"phase":"implement"}\n', encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans),"--required-files-tsv",str(required)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[0])
    assert row["result"] == "fail"
    assert row["missing"] == ["run-statistics.md"]


def test_scan_cross_cutting_emits_self_deploying_gap_alias(tmp_path: Path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    (run / "manifest.json").write_text('{"pr_number":"8","started_at":"2026-01-01T00:00:00Z"}\n', encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\ncache-freshness\tfile\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans)]) == 0
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    row = next(r for r in rows if r["scan"] == "cross-cutting")
    assert row["manifest_pr_number_mismatch_with_audited_pr"] is True
    assert row["self_deploying_gap"] is True
# pyright: reportOperatorIssue=false
