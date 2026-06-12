# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# ruff: noqa: E702, F401
# pylint: skip-file
"""Representative tests for audit run helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import audit_runs
from proc import CommandResult


def test_title_contiguous(capsys):
    assert audit_runs.title_main(["--skill", "implement", "--pr-list", "3,1,2", "--timestamp", "T"]) == 0
    assert capsys.readouterr().out.strip() == "TITLE=[Implement Run Logs Audit T Report] PRs #1-#3"


def test_scan_run_rejects_skill_root(tmp_path: Path, capsys):
    root = Path("larch-logs/implement")
    root.mkdir(parents=True, exist_ok=True)
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\ncache-freshness\tfile\n", encoding="utf-8")
    try:
        assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(root),"--pr","1","--scans-tsv",str(scans)]) == 1
        row = json.loads(capsys.readouterr().out)
        assert row["scan"] == "run-dir-invalid"
    finally:
        # Leave committed log dirs untouched; remove only if empty from this test.
        try:
            root.rmdir(); root.parent.rmdir()
        except OSError:
            pass


def test_scan_run_rejects_cross_skill_absolute_run_dir(tmp_path: Path, capsys):
    run = tmp_path / "larch-logs" / "design" / "run-1"
    run.mkdir(parents=True)
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\ncache-freshness\tfile\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","1","--scans-tsv",str(scans)]) == 1
    row = json.loads(capsys.readouterr().out)
    assert row["scan"] == "run-dir-invalid"


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
    assert "REASON=network down" in out


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
    assert "BODY_FILE_FAILED=true" in capsys.readouterr().out


def test_resolve_prs_reports_issue_list_failure(monkeypatch, capsys):
    runner = AuditRunner({
        ("gh","issue","list","--state","all","--limit","100000","--label","audit-report","--repo","o/r","--json","number,title,createdAt"): cr(("gh",), stderr="auth", rc=1),
    })
    monkeypatch.setattr(audit_runs.proc, "run", runner.run)
    assert audit_runs.resolve_prs_main(["--skill","implement","--repo","o/r"]) == 0
    out = capsys.readouterr().out
    assert "ERROR=gh issue list failed" in out


def test_resolve_prs_reports_issue_view_failure(monkeypatch, capsys):
    prior = json.dumps([{"number": 12, "title": "[Implement Run Logs Audit 2026 Report]", "createdAt": "2026-01-01T00:00:00Z"}])
    runner = AuditRunner({
        ("gh","issue","list","--state","all","--limit","100000","--label","audit-report","--repo","o/r","--json","number,title,createdAt"): cr(("gh",), stdout=prior),
        ("gh","issue","view","12","--repo","o/r","--json","body"): cr(("gh",), stderr="boom", rc=1),
    })
    monkeypatch.setattr(audit_runs.proc, "run", runner.run)
    assert audit_runs.resolve_prs_main(["--skill","implement","--repo","o/r"]) == 0
    assert "ERROR=gh issue view failed for prior audit-report #12" in capsys.readouterr().out


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
