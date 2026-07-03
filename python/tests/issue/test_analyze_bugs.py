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


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


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
    assert any("stateReason" in arg for arg in runner.calls[0])
    assert not any("stateReason" in arg for arg in runner.calls[1])


def test_fetch_bug_issues_pages_until_count_met() -> None:
    page1 = [_issue(number, f"refactor {number}") for number in range(1, 101)]
    page2 = [_issue(number, f"refactor {number}") for number in range(101, 200)]
    page2.append(_issue(200, "[BUG] newest"))
    runner = RecordingRunner(responses=[_result(json.dumps(page1)), _result(json.dumps(page2))], strict=True)

    selected, _corpus = analyze_bugs.fetch_bug_issues(runner, repo="o/r", count=1)

    assert [issue.number for issue in selected] == [200]
    assert runner.calls[0][-2:] == ["--page", "1"]
    assert runner.calls[1][-2:] == ["--page", "2"]


def test_cache_key_changes_with_state_and_state_reason() -> None:
    base = analyze_bugs._cache_key(issue_number=1, fix_sha="sha", later_history_hash="later", state="OPEN", state_reason="COMPLETED")  # pyright: ignore[reportPrivateUsage]
    changed_state = analyze_bugs._cache_key(issue_number=1, fix_sha="sha", later_history_hash="later", state="CLOSED", state_reason="COMPLETED")  # pyright: ignore[reportPrivateUsage]
    changed_reason = analyze_bugs._cache_key(issue_number=1, fix_sha="sha", later_history_hash="later", state="OPEN", state_reason="NOT_PLANNED")  # pyright: ignore[reportPrivateUsage]

    assert base != changed_state
    assert base != changed_reason


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


def test_build_bundle_record_rejects_unreadable_git_fix_sha(tmp_path: Path) -> None:
    issue = analyze_bugs.IssueRecord(7, "[BUG] git fix", "CLOSED", "COMPLETED", "body", "u", "", ())
    runner = RecordingRunner(
        responses=[
            _result("deadbeef\x1fFixes #7\x1e"),
            _result(rc=1, stderr="fatal: Not a valid object name deadbeef"),
        ],
        strict=True,
    )

    bundle = analyze_bugs.build_bundle_record(
        runner=runner,
        issue=issue,
        repo="o/r",
        evidence_ref="origin/main",
        run_dir=tmp_path,
        diff_cap=100,
        body_cap=100,
    )

    assert bundle.fix_sha == ""
    assert bundle.mechanical_verdict == "NEEDS_DEEP"
    assert "Not a valid object name" in bundle.mechanical_reason


def test_build_bundle_record_rejects_unreadable_pr_fix_sha(tmp_path: Path) -> None:
    issue = analyze_bugs.IssueRecord(
        7,
        "[BUG] pr fix",
        "CLOSED",
        "COMPLETED",
        "body",
        "u",
        "",
        ({"number": 9, "url": "https://github.com/o/r/pull/9"},),
    )
    runner = RecordingRunner(
        responses=[
            _result(""),
            _result(json.dumps({"mergeCommit": {"oid": "deadbeef"}})),
            _result(rc=1, stderr="fatal: Not a valid object name deadbeef"),
        ],
        strict=True,
    )

    bundle = analyze_bugs.build_bundle_record(
        runner=runner,
        issue=issue,
        repo="o/r",
        evidence_ref="origin/main",
        run_dir=tmp_path,
        diff_cap=100,
        body_cap=100,
    )

    assert bundle.fix_sha == ""
    assert bundle.mechanical_verdict == "NEEDS_DEEP"
    assert "Not a valid object name" in bundle.mechanical_reason


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
    manifest: dict[str, object] = {
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


def test_ledger_compute_keeps_no_fix_deep_candidates_pending(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    body_path = run_dir / "issue-1-body.md"
    bundle_path = run_dir / "issue-1-bundle.md"
    _write_json(
        run_dir / "manifest.json",
        {
            "schema_version": "1",
            "repo": "o/r",
            "run_id": "run-1",
            "run_dir": str(run_dir),
            "evidence_ref": "origin/main",
            "bugs_requested": 1,
            "bugs_selected": 1,
            "generated_at": 1,
            "ledger_path": str(tmp_path / "ledger.jsonl"),
            "triage_batch_paths": [],
            "deep_queue_path": str(run_dir / "deep-queue.jsonl"),
            "issues": [
                {
                    "issue_number": 1,
                    "title": "[BUG] no fix",
                    "state": "CLOSED",
                    "state_reason": "COMPLETED",
                    "url": "u",
                    "body_path": str(body_path),
                    "bundle_path": str(bundle_path),
                    "fix_sha": "",
                    "fix_source": "git-log",
                    "touched_files": [],
                    "later_history_hash": "later",
                    "mechanical_verdict": "NEEDS_DEEP",
                    "mechanical_reason": "closed issue has no traceable unique fix commit",
                    "cache_key": "cache-key",
                    "sampled": False,
                }
            ],
        },
    )
    _ = body_path.write_text("body\n", encoding="utf-8")
    _ = bundle_path.write_text("bundle\n", encoding="utf-8")
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps(
            {
                "cache_key": "cache-key",
                "issue": 1,
                "fix_sha": "",
                "later_history_hash": "later",
                "triage_verdict": "",
                "triage_reason": "",
                "triage_missing_items": [],
                "triage_needs_deep": False,
                "deep_verdict": "CONFIRMED_FIXED",
                "deep_reason": "stale deep verdict",
                "sampled": False,
                "stages_complete": ["deep"],
                "updated_at": 1,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = analyze_bugs.ledger_compute(run_dir=run_dir, ledger_path=ledger, manifest_path=run_dir / "manifest.json", refresh=False, sample=0, deep_max=10, deep_model="sonnet", batch_size=10)

    assert summary["DEEP_PENDING"] == 1
    queue = [json.loads(line) for line in (run_dir / "deep-queue.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    assert [row["issue"] for row in queue] == [1]


def test_load_ledger_quarantines_corrupt_lines(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps({"cache_key": "ok", "issue": 1, "fix_sha": "", "later_history_hash": "", "stages_complete": []}) + "\n"
        + "not-json\n"
        + "[]\n",
        encoding="utf-8",
    )

    records, corrupt_count = analyze_bugs.load_ledger(ledger)

    assert list(records) == ["ok"]
    assert corrupt_count == 2
    assert list(tmp_path.glob("ledger.jsonl.corrupt-*"))


def test_render_report_overrides_stale_deep_and_writes_follow_up(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    body1 = run_dir / "issue-1-body.md"
    body2 = run_dir / "issue-2-body.md"
    bundle1 = run_dir / "issue-1-bundle.md"
    bundle2 = run_dir / "issue-2-bundle.md"
    for path, text in ((body1, "body 1\n"), (body2, "body 2\n"), (bundle1, "bundle 1\n"), (bundle2, "bundle 2\n")):
        _ = path.write_text(text, encoding="utf-8")
    key1 = "cache-1"
    key2 = "cache-2"
    _write_json(
        run_dir / "manifest.json",
        {
            "schema_version": "1",
            "repo": "o/r",
            "run_id": "run-1",
            "run_dir": str(run_dir),
            "evidence_ref": "origin/main",
            "bugs_requested": 2,
            "bugs_selected": 2,
            "generated_at": 1,
            "ledger_path": str(tmp_path / "ledger.jsonl"),
            "triage_batch_paths": [],
            "deep_queue_path": str(run_dir / "deep-queue.jsonl"),
            "issues": [
                {
                    "issue_number": 1,
                    "title": "[BUG] open stale",
                    "state": "OPEN",
                    "state_reason": "",
                    "url": "https://github.com/o/r/issues/1",
                    "body_path": str(body1),
                    "bundle_path": str(bundle1),
                    "fix_sha": "",
                    "fix_source": "git-log",
                    "touched_files": [],
                    "later_history_hash": "later-1",
                    "mechanical_verdict": "NOT_FIXED",
                    "mechanical_reason": "issue is still open",
                    "cache_key": key1,
                    "sampled": False,
                },
                {
                    "issue_number": 2,
                    "title": "[BUG] truncated stale",
                    "state": "CLOSED",
                    "state_reason": "COMPLETED",
                    "url": "https://github.com/o/r/issues/2",
                    "body_path": str(body2),
                    "bundle_path": str(bundle2),
                    "fix_sha": "sha2",
                    "fix_source": "git-log",
                    "touched_files": [],
                    "later_history_hash": "later-2",
                    "mechanical_verdict": "",
                    "mechanical_reason": "",
                    "cache_key": key2,
                    "sampled": False,
                },
            ],
        },
    )
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps({"cache_key": key1, "issue": 1, "fix_sha": "", "later_history_hash": "later-1", "deep_verdict": "CONFIRMED_FIXED", "deep_reason": "stale", "stages_complete": ["deep"], "sampled": False}) + "\n"
        + json.dumps({"cache_key": key2, "issue": 2, "fix_sha": "sha2", "later_history_hash": "later-2", "deep_verdict": "FIXED_CLEAR", "deep_reason": "clear", "stages_complete": ["deep"], "sampled": False}) + "\n",
        encoding="utf-8",
    )
    _write_json(run_dir / "ledger-summary.json", {"DEEP_TRUNCATED_ISSUES": [2], "DEEP_RATE_MODEL": "claude-sonnet-4.5", "DEEP_MODEL": "claude-sonnet-4.5"})

    report = analyze_bugs.render_report(manifest_path=run_dir / "manifest.json", ledger_path=ledger, run_dir=run_dir)

    assert "NOT_FIXED" in report
    assert "deep cap truncated this candidate" in report
    assert "ANALYZE_BUGS_COST_ESTIMATE=" in report
    assert (run_dir / "report.md").read_text(encoding="utf-8") == report
    follow_up = (run_dir / "follow-up-issue.md").read_text(encoding="utf-8")
    assert "# Analyze-bugs follow-up" in follow_up
    assert "#1: NOT_FIXED" in follow_up


def test_cli_dispatches_analyze_bugs_help() -> None:
    result = run_cli("analyze-bugs", "prefetch", "--help")

    assert result.returncode == 0
    assert "analyze-bugs prefetch" in result.stdout
