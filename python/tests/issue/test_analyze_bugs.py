# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnusedCallResult=false
"""Offline tests for analyze_bugs.py."""

from __future__ import annotations

import json
from pathlib import Path

from larch.core.proc import CommandResult
from larch.issue import analyze_bugs
from test_support import RecordingRunner, run_cli


def _result(stdout: str = "", rc: int = 0, stderr: str = "") -> CommandResult:
    return CommandResult(("cmd",), rc, stdout, stderr, 0.01)


def _issue(number: int, title: str, *, state: str = "CLOSED", reason: str = "COMPLETED", body: str = "body") -> dict[str, object]:
    return {
        "number": number,
        "title": title,
        "state": state,
        "stateReason": reason,
        "body": body,
        "url": f"https://github.com/o/r/issues/{number}",
        "closedAt": "2026-01-01T00:00:00Z",
        "closedByPullRequestsReferences": [],
    }


def test_fetch_filters_bug_prefix_and_keeps_state_all_on_fallback() -> None:
    issues = [
        _issue(1, "not [BUG] later"),
        _issue(2, "[BUG] newest"),
        _issue(3, "[BUG] older"),
    ]
    runner = RecordingRunner(responses=[_result(rc=1, stderr="bad field"), _result(json.dumps(issues))], strict=True)

    selected, _corpus = analyze_bugs.fetch_bug_issues(runner, repo="o/r", count=2)

    assert [issue.number for issue in selected] == [2, 3]
    assert all("--state" in call and "all" in call for call in runner.calls)
    assert "stateReason" in runner.calls[0][-1]
    assert "stateReason" not in runner.calls[1][-1]


def test_plan_block_malformed_forces_needs_deep(tmp_path: Path) -> None:
    body = "before\n<!-- larch:plan:start -->\nno end\n"
    issue = analyze_bugs.IssueRecord(7, "[BUG] malformed", "CLOSED", "COMPLETED", body, "u", "", ())
    runner = RecordingRunner(default=_result(""))

    bundle = analyze_bugs.build_bundle_record(
        runner=runner,
        issue=issue,
        repo="o/r",
        evidence_ref="origin/main",
        run_dir=tmp_path,
        diff_cap=100,
        body_cap=100,
    )

    assert bundle.mechanical_verdict == "NEEDS_DEEP"
    assert "malformed" in bundle.mechanical_reason


def test_exact_fix_reference_newest_wins_and_prefix_collision() -> None:
    output = "badsha\x1fFixes #1234\x1e\ngoodsha\x1fFixes #123\x1e\noldsha\x1fFixes #123\x1e\n"
    runner = RecordingRunner(responses=[_result(output)], strict=True)

    fix = analyze_bugs.find_fix_by_git_log(runner, issue=123, evidence_ref="origin/main")

    assert fix.fix_sha == "goodsha"
    assert runner.calls[0][2] == "origin/main"
    assert "HEAD" not in runner.calls[0]


def test_prefetch_emits_manifest_and_handoff_paths(tmp_path: Path) -> None:
    issues = [_issue(10, "[BUG] fixed")]
    runner = RecordingRunner(
        responses=[
            _result(json.dumps({"nameWithOwner": "o/r"})),
            _result(),
            _result("sha\n"),
            _result(json.dumps(issues)),
            _result("fixsha\x1fFixes #10\x1e"),
            _result("file.py\n"),
            _result("later: touch\n"),
            _result("diff --git a/file.py b/file.py\n"),
            _result(""),
        ],
        strict=True,
    )

    manifest = analyze_bugs.prefetch(runner=runner, count=1, cache_root_arg=str(tmp_path))

    assert manifest.bugs_requested == 1
    assert manifest.bugs_selected == 1
    assert Path(manifest.run_dir, "manifest.json").is_file()
    assert manifest.triage_batch_paths
    assert Path(manifest.deep_queue_path).is_file()


def test_ledger_ingest_rejects_duplicate_and_unknown_verdict(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    manifest = {
        "schema_version": "1",
        "repo": "o/r",
        "issues": [
            {
                "issue_number": 1,
                "title": "[BUG] x",
                "state": "CLOSED",
                "state_reason": "COMPLETED",
                "url": "u",
                "body_path": "b",
                "bundle_path": "bundle",
                "fix_sha": "abc",
                "fix_source": "git-log",
                "touched_files": [],
                "later_history_hash": "h",
                "mechanical_verdict": "",
                "mechanical_reason": "",
                "cache_key": "k1",
            }
        ],
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    batch = run_dir / "triage.jsonl"
    batch.write_text(
        '{"issue":1,"verdict":"FIXED_CLEAR","missing_items":[],"reason":"clear","needs_deep":false}\n'
        '{"issue":1,"verdict":"FIXED_LIKELY","missing_items":[],"reason":"dup","needs_deep":false}\n'
        '{"issue":2,"verdict":"BOGUS","missing_items":[],"reason":"bad","needs_deep":false}\n',
        encoding="utf-8",
    )

    payload = analyze_bugs.ledger_ingest(run_dir=run_dir, ledger_path=tmp_path / "ledger.jsonl", manifest_path=run_dir / "manifest.json", triage_path=batch, deep_path=None)

    assert payload["INGEST_ACCEPTED"] == 1
    assert payload["INGEST_REJECTED"] == 2
    rows = (tmp_path / "ledger.jsonl").read_text(encoding="utf-8")
    assert "FIXED_CLEAR" in rows


def test_deep_queue_priority_cap_and_model_alias(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    issues = []
    for number, cache_key, mechanical in [(1, "k1", "NEEDS_DEEP"), (2, "k2", ""), (3, "k3", "")]:
        issues.append(
            {
                "issue_number": number,
                "title": f"[BUG] {number}",
                "state": "CLOSED",
                "state_reason": "COMPLETED",
                "url": "u",
                "body_path": "b",
                "bundle_path": f"bundle-{number}",
                "fix_sha": "abc",
                "fix_source": "git-log",
                "touched_files": [],
                "later_history_hash": f"h{number}",
                "mechanical_verdict": mechanical,
                "mechanical_reason": mechanical,
                "cache_key": cache_key,
            }
        )
    (run_dir / "manifest.json").write_text(json.dumps({"schema_version": "1", "repo": "o/r", "issues": issues}), encoding="utf-8")
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps({"cache_key": "k2", "issue": 2, "fix_sha": "abc", "later_history_hash": "h2", "triage_verdict": "SUSPECT", "stages_complete": ["triage"]}) + "\n"
        + json.dumps({"cache_key": "k3", "issue": 3, "fix_sha": "abc", "later_history_hash": "h3", "triage_verdict": "FIXED_CLEAR", "stages_complete": ["triage"]}) + "\n",
        encoding="utf-8",
    )

    summary = analyze_bugs.ledger_compute(run_dir=run_dir, ledger_path=ledger, manifest_path=run_dir / "manifest.json", refresh=False, sample=1, deep_max=2, deep_model="fable", batch_size=10)

    assert summary["DEEP_MODEL"] == "claude-fable-5"
    assert summary["DEEP_CAP_TRUNCATED"] == "true"
    queue = [json.loads(line) for line in (run_dir / "deep-queue.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [row["issue"] for row in queue] == [1, 2]


def test_cli_dispatches_analyze_bugs_help() -> None:
    result = run_cli("analyze-bugs", "prefetch", "--help")

    assert result.returncode == 0
    assert "analyze-bugs prefetch" in result.stdout
