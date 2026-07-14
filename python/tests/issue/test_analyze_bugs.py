# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnusedCallResult=false
"""Offline tests for analyze_bugs.py."""

# pyright: reportOperatorIssue=false

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import cast

import pytest

from larch.core.proc import CommandResult, ProcRunner
from larch.issue import analyze_bugs
from larch.lint import lint_agent_tool_contract as latc
from test_support import RecordingRunner, run_cli

_marker_evidence = analyze_bugs._marker_evidence  # pyright: ignore[reportPrivateUsage]  # direct pure-helper coverage
_bundle_from_mapping = analyze_bugs._bundle_from_mapping  # pyright: ignore[reportPrivateUsage]  # fixture construction
_priority_deep_candidates = analyze_bugs._priority_deep_candidates  # pyright: ignore[reportPrivateUsage]  # routing coverage
_parse_finder_finding = analyze_bugs._parse_finder_finding  # pyright: ignore[reportPrivateUsage]  # strict finder contract coverage
_parse_finder_row = analyze_bugs._parse_finder_row  # pyright: ignore[reportPrivateUsage]  # strict finder contract coverage
_parse_refuter_result = analyze_bugs._parse_refuter_result  # pyright: ignore[reportPrivateUsage]  # strict refuter contract coverage


EVIDENCE_TOKEN = "token-123"


def _result(stdout: str = "", rc: int = 0, stderr: str = "") -> CommandResult:
    return CommandResult(("cmd",), rc, stdout, stderr, 0.01)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _write_bundle(path: Path, *, proof: str = EVIDENCE_TOKEN) -> None:
    path.write_text(f"# Bundle\nevidence_token: {proof}\n\nbody\n", encoding="utf-8")


def _triage_row(issue: int, verdict: str = "FIXED_CLEAR", *, proof: str = EVIDENCE_TOKEN, reason: str = "clear", needs_deep: bool = False) -> str:
    return json.dumps(
        {
            "issue": issue,
            "verdict": verdict,
            "missing_items": [],
            "reason": reason,
            "needs_deep": needs_deep,
            "evidence_token": proof,
        },
        sort_keys=True,
    ) + "\n"


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


def _single_manifest(run_dir: Path, *, issue: int = 1, cache_key: str = "k1", bundle_path: Path | None = None, mechanical: str = "") -> dict[str, object]:
    resolved_bundle_path = bundle_path or (run_dir / f"issue-{issue}-bundle.md")
    return {
        "schema_version": "1",
        "repo": "o/r",
        "run_id": "run-1",
        "run_dir": str(run_dir),
        "evidence_ref": "origin/main",
        "bugs_requested": 1,
        "bugs_selected": 1,
        "generated_at": 1,
        "ledger_path": str(run_dir / "ledger.jsonl"),
        "triage_batch_paths": [],
        "deep_queue_path": str(run_dir / "deep-queue.jsonl"),
        "issues": [
            {
                "issue_number": issue,
                "title": f"[BUG] {issue}",
                "state": "CLOSED",
                "state_reason": "COMPLETED",
                "url": f"https://github.com/o/r/issues/{issue}",
                "body_path": str(run_dir / f"issue-{issue}-body.md"),
                "bundle_path": str(resolved_bundle_path),
                "fix_sha": "sha",
                "fix_source": "git-log",
                "touched_files": [],
                "later_history_hash": "later",
                "mechanical_verdict": mechanical,
                "mechanical_reason": mechanical,
                "cache_key": cache_key,
                "sampled": False,
            }
        ],
    }


def _single_manifest_issue(run_dir: Path, *, issue: int = 1, cache_key: str = "k1", mechanical: str = "") -> dict[str, object]:
    raw_issues = _single_manifest(run_dir, issue=issue, cache_key=cache_key, mechanical=mechanical)["issues"]
    if not isinstance(raw_issues, list) or not raw_issues:
        raise AssertionError("helper manifest lacks issue rows")
    return cast("dict[str, object]", raw_issues[0])


def test_fetch_filters_bug_prefix_and_uses_issue_list_read() -> None:
    issues = [_issue(number, f"refactor {number}", body="body") for number in range(1, 5)]
    issues.append(_issue(200, "[BUG] newest", state="CLOSED", reason="COMPLETED"))
    runner = RecordingRunner(responses=[_result(json.dumps(issues))], strict=True)

    selected, _corpus = analyze_bugs.fetch_bug_issues(runner, repo="o/r", count=1)

    assert [issue.number for issue in selected] == [200]
    assert runner.calls[0][:4] == ["gh", "issue", "list", "--repo"]  # lint-gh-argv-literal: ok fixture assertion
    assert "--limit" in runner.calls[0]
    assert runner.calls[0][runner.calls[0].index("--limit") + 1] == "100000"
    assert "closedByPullRequestsReferences" in runner.calls[0][runner.calls[0].index("--json") + 1]


def test_fetch_translates_ship_error_to_analyze_bugs_error() -> None:
    runner = RecordingRunner(responses=[_result(rc=1, stderr="auth boom")], strict=True)
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="gh issue list failed"):
        analyze_bugs.fetch_bug_issues(runner, repo="o/r", count=1)


def test_fetch_normalizes_lifecycle_prefixes_and_bug_case() -> None:
    issues: list[dict[str, object]] = [
        _issue(1, "[DONE] [BUG] fixed"),
        _issue(2, "[Bug] terminal report"),
        _issue(3, "[DONE] [Bug] fixed mixed case"),
        _issue(4, "note mentions [BUG] later"),
        _issue(5, "[DONE] note mentions [BUG] later"),
        _issue(6, "[DESIGNED] [BUG] designed"),
        _issue(7, "[IMPLEMENTING] [BUG] implementing"),
        _issue(8, "[STALLED] [Bug] stalled mixed case"),
    ]
    runner: RecordingRunner = RecordingRunner(responses=[_result(json.dumps(issues))], strict=True)

    selected: list[analyze_bugs.IssueRecord]
    selected, _corpus = analyze_bugs.fetch_bug_issues(runner, repo="o/r", count=10)

    assert [issue.number for issue in selected] == [1, 2, 3, 6, 7, 8]


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


def test_build_bundle_record_rejects_pr_fix_sha_outside_evidence_ref(tmp_path: Path) -> None:
    issue = analyze_bugs.IssueRecord(
        7,
        "[BUG] pr fix",
        "CLOSED",
        "COMPLETED",
        "body",
        "u",
        "",
        (),
    )
    runner = RecordingRunner(
        responses=[
            _result(""),
            _result(json.dumps({"closedByPullRequestsReferences": [{"number": 9, "url": "https://github.com/o/r/pull/9"}]})),
            _result(json.dumps({"mergeCommit": {"oid": "deadbeef"}})),
            _result(),
            _result(rc=1, stderr="fatal: Not a valid merge base"),
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
    assert "Not a valid merge base" in bundle.mechanical_reason
    assert ["git", "merge-base", "--is-ancestor", "deadbeef", "origin/main"] in runner.calls


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
            _result("o/r\n"),
            _result(),
            _result("sha\n"),
            _result(json.dumps(issues)),
            _result("fixsha\x1fFixes #10\x1e"),
            _result(),
            _result(),
            _result("file.py\n"),
            _result("1767225600\n"),
            _result("10\t2\tfile.py\n"),
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
    manifest_text = Path(manifest.run_dir, "manifest.json").read_text(encoding="utf-8")
    bundle_text = Path(manifest.issues[0].bundle_path).read_text(encoding="utf-8")
    triage_batch_text = Path(manifest.triage_batch_paths[0]).read_text(encoding="utf-8")
    token = analyze_bugs._extract_evidence_token(bundle_text)  # pyright: ignore[reportPrivateUsage]
    assert token
    assert f"evidence_token: {token}" in bundle_text
    assert token not in manifest_text
    assert token not in triage_batch_text
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
                "bundle_path": str(run_dir / "bundle.md"),
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
    _write_bundle(run_dir / "bundle.md")
    batch = run_dir / "triage.jsonl"
    batch.write_text(
        _triage_row(1, "FIXED_CLEAR")
        + _triage_row(1, "FIXED_LIKELY", reason="dup")
        + _triage_row(2, "BOGUS", reason="bad"),
        encoding="utf-8",
    )

    payload = analyze_bugs.ledger_ingest(run_dir=run_dir, ledger_path=tmp_path / "ledger.jsonl", manifest_path=run_dir / "manifest.json", triage_path=batch, deep_path=None)

    assert payload["INGEST_ACCEPTED"] == 1
    assert payload["INGEST_REJECTED"] == 2
    rows = (tmp_path / "ledger.jsonl").read_text(encoding="utf-8")
    assert "FIXED_CLEAR" in rows


def test_ledger_ingest_rejects_issue_not_in_active_batch(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    manifest: dict[str, object] = {
        "schema_version": "1",
        "repo": "o/r",
        "issues": [
            {
                "issue_number": 1,
                "title": "[BUG] a",
                "state": "CLOSED",
                "state_reason": "COMPLETED",
                "url": "u1",
                "body_path": "b1",
                "bundle_path": "bundle-1",
                "fix_sha": "abc",
                "fix_source": "git-log",
                "touched_files": [],
                "later_history_hash": "h1",
                "mechanical_verdict": "",
                "mechanical_reason": "",
                "cache_key": "k1",
            },
            {
                "issue_number": 2,
                "title": "[BUG] b",
                "state": "CLOSED",
                "state_reason": "COMPLETED",
                "url": "u2",
                "body_path": "b2",
                "bundle_path": "bundle-2",
                "fix_sha": "def",
                "fix_source": "git-log",
                "touched_files": [],
                "later_history_hash": "h2",
                "mechanical_verdict": "",
                "mechanical_reason": "",
                "cache_key": "k2",
            },
        ],
    }
    _write_json(run_dir / "manifest.json", manifest)
    (run_dir / "triage-pending-1.jsonl").write_text(
        json.dumps({"issue": 1, "cache_key": "k1", "bundle_path": "bundle-1"}) + "\n",
        encoding="utf-8",
    )
    batch = run_dir / "triage.jsonl"
    batch.write_text(_triage_row(2, reason="off-task"), encoding="utf-8")

    payload = analyze_bugs.ledger_ingest(run_dir=run_dir, ledger_path=tmp_path / "ledger.jsonl", manifest_path=run_dir / "manifest.json", triage_path=batch, deep_path=None)

    assert payload["INGEST_ACCEPTED"] == 0
    assert payload["INGEST_REJECTED"] == 1
    assert not (tmp_path / "ledger.jsonl").exists()


def test_ledger_ingest_refresh_triage_clears_stale_deep_verdict(tmp_path: Path) -> None:
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
                    "title": "[BUG] stale deep",
                    "state": "CLOSED",
                    "state_reason": "COMPLETED",
                    "url": "u",
                    "body_path": str(body_path),
                    "bundle_path": str(bundle_path),
                    "fix_sha": "sha1",
                    "fix_source": "git-log",
                    "touched_files": [],
                    "later_history_hash": "later",
                    "mechanical_verdict": "",
                    "mechanical_reason": "",
                    "cache_key": "cache-key",
                    "sampled": False,
                }
            ],
        },
    )
    _ = body_path.write_text("body\n", encoding="utf-8")
    _write_bundle(bundle_path)
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps(
            {
                "cache_key": "cache-key",
                "issue": 1,
                "fix_sha": "sha1",
                "later_history_hash": "later",
                "triage_verdict": "FIXED_CLEAR",
                "triage_reason": "old triage",
                "triage_missing_items": [],
                "triage_needs_deep": False,
                "triage_evidence_verified": True,
                "deep_verdict": "CONFIRMED_FIXED",
                "deep_reason": "stale deep verdict",
                "sampled": False,
                "stages_complete": ["deep", "triage"],
                "updated_at": 1,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    batch = run_dir / "triage.jsonl"
    batch.write_text(_triage_row(1, reason="refresh"), encoding="utf-8")

    payload = analyze_bugs.ledger_ingest(run_dir=run_dir, ledger_path=ledger, manifest_path=run_dir / "manifest.json", triage_path=batch, deep_path=None)

    assert payload["INGEST_ACCEPTED"] == 1
    updated = json.loads(ledger.read_text(encoding="utf-8").splitlines()[-1])
    assert updated["deep_verdict"] == ""
    assert updated["deep_reason"] == ""
    assert updated["triage_evidence_verified"] is True
    assert "deep" not in updated["stages_complete"]


def test_ledger_ingest_skips_missing_deep_ingest_file(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _write_json(
        run_dir / "manifest.json",
        {
            "schema_version": "1",
            "repo": "o/r",
            "run_id": "run-1",
            "run_dir": str(run_dir),
            "evidence_ref": "origin/main",
            "bugs_requested": 0,
            "bugs_selected": 0,
            "generated_at": 1,
            "ledger_path": str(tmp_path / "ledger.jsonl"),
            "triage_batch_paths": [],
            "deep_queue_path": str(run_dir / "deep-queue.jsonl"),
            "issues": [],
        },
    )
    ledger = tmp_path / "ledger.jsonl"

    payload = analyze_bugs.ledger_ingest(run_dir=run_dir, ledger_path=ledger, manifest_path=run_dir / "manifest.json", triage_path=None, deep_path=run_dir / "missing-deep.jsonl")

    assert payload["INGEST_STAGE"] == "deep"
    assert payload["INGEST_ACCEPTED"] == 0
    assert payload["INGEST_REJECTED"] == 0
    assert not ledger.exists()


def test_deep_queue_priority_cap_and_model_alias(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    issues = []
    for number, cache_key, mechanical in [(1, "k1", "NEEDS_DEEP"), (2, "k2", ""), (3, "k3", ""), (4, "k4", ""), (5, "k5", "")]:
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
        + json.dumps({"cache_key": "k3", "issue": 3, "fix_sha": "abc", "later_history_hash": "h3", "triage_verdict": "FIXED_CLEAR", "stages_complete": ["triage"]}) + "\n"
        + json.dumps({"cache_key": "k4", "issue": 4, "fix_sha": "abc", "later_history_hash": "h4", "triage_verdict": "SUSPECT", "triage_evidence_verified": True, "stages_complete": ["triage"]}) + "\n"
        + json.dumps({"cache_key": "k5", "issue": 5, "fix_sha": "abc", "later_history_hash": "h5", "triage_verdict": "FIXED_CLEAR", "triage_evidence_verified": True, "stages_complete": ["triage"]}) + "\n",
        encoding="utf-8",
    )

    summary = analyze_bugs.ledger_compute(run_dir=run_dir, ledger_path=ledger, manifest_path=run_dir / "manifest.json", refresh=False, sample=1, deep_max=2, deep_model="fable", batch_size=10)

    assert summary["DEEP_MODEL"] == "claude-fable-5"
    assert summary["DEEP_CAP_TRUNCATED"] == "true"
    queue = [json.loads(line) for line in (run_dir / "deep-queue.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [row["issue"] for row in queue] == [1, 4]


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


def test_render_report_prefers_deep_verdict_over_mechanical_verdict(tmp_path: Path) -> None:
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

    assert "CONFIRMED_FIXED" in report
    assert "deep cap truncated this candidate" in report
    assert "ANALYZE_BUGS_COST_ESTIMATE=" in report
    assert (run_dir / "report.md").read_text(encoding="utf-8") == report
    assert not (run_dir / "follow-up-issue.md").exists()


def test_render_report_surfaces_deep_verdict_after_mechanical_needs_deep(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    body = run_dir / "issue-1-body.md"
    bundle = run_dir / "issue-1-bundle.md"
    _ = body.write_text("body\n", encoding="utf-8")
    _ = bundle.write_text("bundle\n", encoding="utf-8")
    cache_key = "cache-1"
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
                    "title": "[BUG] deep verified",
                    "state": "CLOSED",
                    "state_reason": "COMPLETED",
                    "url": "https://github.com/o/r/issues/1",
                    "body_path": str(body),
                    "bundle_path": str(bundle),
                    "fix_sha": "sha1",
                    "fix_source": "git-log",
                    "touched_files": [],
                    "later_history_hash": "later-1",
                    "mechanical_verdict": "NEEDS_DEEP",
                    "mechanical_reason": "no exact Fixes reference",
                    "cache_key": cache_key,
                    "sampled": False,
                }
            ],
        },
    )
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps(
            {
                "cache_key": cache_key,
                "issue": 1,
                "fix_sha": "sha1",
                "later_history_hash": "later-1",
                "deep_verdict": "CONFIRMED_FIXED",
                "deep_reason": "deep verifier found the fix",
                "stages_complete": ["deep"],
                "sampled": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = analyze_bugs.render_report(manifest_path=run_dir / "manifest.json", ledger_path=ledger, run_dir=run_dir)

    assert "| Confirmed or likely fixed | 1 |" in report
    assert "| Needs deep | 0 |" in report
    assert "| [#1](https://github.com/o/r/issues/1) | sha1 | DEEP | CONFIRMED_FIXED | deep verifier found the fix |  |" in report
    assert "no exact Fixes reference" not in report


def test_extract_evidence_token_accepts_only_canonical_near_top_line() -> None:
    assert analyze_bugs._extract_evidence_token("# Bundle\nevidence_token: abc123\n") == "abc123"  # pyright: ignore[reportPrivateUsage]
    assert analyze_bugs._extract_evidence_token("evidence_token: \n") is None  # pyright: ignore[reportPrivateUsage]
    assert analyze_bugs._extract_evidence_token(" evidence_token: abc123\n") is None  # pyright: ignore[reportPrivateUsage]
    assert analyze_bugs._extract_evidence_token("evidence_token: abc123 extra\n") is None  # pyright: ignore[reportPrivateUsage]
    assert analyze_bugs._extract_evidence_token("\n".join(["x"] * 20 + ["evidence_token: late"])) is None  # pyright: ignore[reportPrivateUsage]


def test_ledger_ingest_accepts_correct_evidence_token(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    bundle_path = run_dir / "issue-1-bundle.md"
    _write_bundle(bundle_path)
    _write_json(run_dir / "manifest.json", _single_manifest(run_dir, bundle_path=bundle_path))
    batch = run_dir / "triage.jsonl"
    batch.write_text(_triage_row(1), encoding="utf-8")
    ledger = tmp_path / "ledger.jsonl"

    payload = analyze_bugs.ledger_ingest(run_dir=run_dir, ledger_path=ledger, manifest_path=run_dir / "manifest.json", triage_path=batch, deep_path=None)

    assert payload["INGEST_ACCEPTED"] == 1
    row = json.loads(ledger.read_text(encoding="utf-8"))
    assert row["triage_evidence_verified"] is True


def test_ledger_ingest_rejects_missing_wrong_and_unreadable_evidence_tokens(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    bundle_path = run_dir / "issue-1-bundle.md"
    _write_bundle(bundle_path)
    _write_json(run_dir / "manifest.json", _single_manifest(run_dir, bundle_path=bundle_path))
    ledger = tmp_path / "ledger.jsonl"

    missing_token = run_dir / "missing-token.jsonl"
    missing_token.write_text('{"issue":1,"verdict":"FIXED_CLEAR","missing_items":[],"reason":"clear","needs_deep":false}\n', encoding="utf-8")
    wrong_token = run_dir / "wrong-token.jsonl"
    wrong_token.write_text(_triage_row(1, proof="wrong-token"), encoding="utf-8")

    payload_missing = analyze_bugs.ledger_ingest(run_dir=run_dir, ledger_path=ledger, manifest_path=run_dir / "manifest.json", triage_path=missing_token, deep_path=None)
    payload_wrong = analyze_bugs.ledger_ingest(run_dir=run_dir, ledger_path=ledger, manifest_path=run_dir / "manifest.json", triage_path=wrong_token, deep_path=None)

    assert payload_missing["INGEST_ACCEPTED"] == 0
    assert payload_wrong["INGEST_ACCEPTED"] == 0

    bundle_path.write_text("# Bundle without token\n", encoding="utf-8")
    no_bundle_token = run_dir / "no-bundle-token.jsonl"
    no_bundle_token.write_text(_triage_row(1), encoding="utf-8")
    payload_no_bundle_token = analyze_bugs.ledger_ingest(run_dir=run_dir, ledger_path=ledger, manifest_path=run_dir / "manifest.json", triage_path=no_bundle_token, deep_path=None)
    assert payload_no_bundle_token["INGEST_ACCEPTED"] == 0

    bundle_path.unlink()
    missing_bundle = run_dir / "missing-bundle.jsonl"
    missing_bundle.write_text(_triage_row(1), encoding="utf-8")
    payload_missing_bundle = analyze_bugs.ledger_ingest(run_dir=run_dir, ledger_path=ledger, manifest_path=run_dir / "manifest.json", triage_path=missing_bundle, deep_path=None)
    assert payload_missing_bundle["INGEST_ACCEPTED"] == 0
    assert not ledger.exists()


def test_ledger_ingest_rejects_unexpected_triage_keys(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    bundle_path = run_dir / "issue-1-bundle.md"
    _write_bundle(bundle_path)
    _write_json(run_dir / "manifest.json", _single_manifest(run_dir, bundle_path=bundle_path))
    batch = run_dir / "triage.jsonl"
    row = json.loads(_triage_row(1))
    row["extra"] = "field"
    batch.write_text(json.dumps(row) + "\n", encoding="utf-8")

    payload = analyze_bugs.ledger_ingest(run_dir=run_dir, ledger_path=tmp_path / "ledger.jsonl", manifest_path=run_dir / "manifest.json", triage_path=batch, deep_path=None)

    assert payload["INGEST_ACCEPTED"] == 0
    assert payload["INGEST_REJECTED"] == 1


def test_legacy_unverified_triage_requeues_and_does_not_drive_report_or_deep(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    issues: list[dict[str, object]] = [
        _single_manifest_issue(run_dir, issue=1, cache_key="k1"),
        _single_manifest_issue(run_dir, issue=2, cache_key="k2", mechanical="NEEDS_DEEP"),
    ]
    _write_json(run_dir / "manifest.json", {"schema_version": "1", "repo": "o/r", "issues": issues})
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps({"cache_key": "k1", "issue": 1, "fix_sha": "sha", "later_history_hash": "later", "triage_verdict": "FIXED_CLEAR", "stages_complete": ["triage"]}) + "\n"
        + json.dumps({"cache_key": "k2", "issue": 2, "fix_sha": "sha", "later_history_hash": "later", "triage_verdict": "SUSPECT", "stages_complete": ["triage"]}) + "\n",
        encoding="utf-8",
    )

    summary = analyze_bugs.ledger_compute(run_dir=run_dir, ledger_path=ledger, manifest_path=run_dir / "manifest.json", refresh=False, sample=1, deep_max=10, deep_model="sonnet", batch_size=10)
    report = analyze_bugs.render_report(manifest_path=run_dir / "manifest.json", ledger_path=ledger, run_dir=run_dir)

    assert summary["TRIAGE_PENDING"] == 1
    triage_pending = [json.loads(line) for line in (run_dir / "triage-pending-1.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [row["issue"] for row in triage_pending] == [1]
    deep_queue = [json.loads(line) for line in (run_dir / "deep-queue.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [row["issue"] for row in deep_queue] == [2]
    assert "FIXED_CLEAR" not in report
    assert "not yet triaged" in report


def test_bug_fix_triage_agent_grants_read_tool() -> None:
    agent = (Path(__file__).resolve().parents[3] / ".claude/agents/bug-fix-triage.md").read_text(encoding="utf-8")

    assert "tools: [Read]" in agent
    assert "tools: []" not in agent


def test_cli_dispatches_analyze_bugs_help() -> None:
    result = run_cli("analyze-bugs", "prefetch", "--help")

    assert result.returncode == 0
    assert "analyze-bugs prefetch" in result.stdout


@pytest.mark.parametrize("flag", ["--sweep", "--sweep-max=1"])
def test_prefetch_rejects_sweep_only_flags(flag: str) -> None:
    result = run_cli("analyze-bugs", "prefetch", flag)

    assert result.returncode != 0
    assert "unrecognized arguments" in result.stderr


def _analytics_bundle(run_dir: Path, *, issue: int, cache_key: str, files: list[str], fix_time: int, added_lines: int = 10, markers: list[int] | None = None, mechanical: str = "") -> dict[str, object]:
    row = _single_manifest_issue(run_dir, issue=issue, cache_key=cache_key, mechanical=mechanical)
    row["fix_sha"] = f"sha-{issue}"
    row["touched_files"] = files
    row["fix_time"] = fix_time
    row["added_lines"] = added_lines
    row["zones"] = sorted({analyze_bugs.zone_for_path(path) for path in files})
    row["marker_references"] = markers or []
    row["marker_fingerprint"] = f"fingerprint-{issue}"
    row["baseline_extended"] = any(path.startswith("python/") and path.endswith("-baseline.json") for path in files)
    return row


def test_zone_mapping_table() -> None:
    cases = {
        "python/larch/issue/analyze_bugs.py": "python/larch/issue",
        "skills/implement/SKILL.md": "skills/implement",
        "scripts/check.sh": "scripts",
        "docs/linting.md": "docs",
        "python/complexity-baseline.json": "python/complexity-baseline.json",
        "README.md": "README.md",
    }

    assert {path: analyze_bugs.zone_for_path(path) for path in cases} == cases


def test_marker_evidence_requires_phrase_and_reference() -> None:
    references, fingerprint = _marker_evidence("[BUG] Regression from #12", "body")
    no_phrase, _ = _marker_evidence("[BUG] follow-up #12", "body")
    no_reference, _ = _marker_evidence("[BUG] residual failure", "body")

    assert references == (12,)
    assert len(fingerprint) == 64
    assert not no_phrase
    assert not no_reference


def test_analytics_detects_churn_chronic_chains_and_baseline(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "200"
    run_dir.mkdir(parents=True)
    now = 2_000_000
    issues = [
        _analytics_bundle(run_dir, issue=1, cache_key="k1", files=["python/larch/issue/shared.py", "python/complexity-baseline.json"], fix_time=now - 100, markers=[9]),
        _analytics_bundle(run_dir, issue=2, cache_key="k2", files=["python/larch/issue/shared.py"], fix_time=now - 200),
        _analytics_bundle(run_dir, issue=3, cache_key="k3", files=["python/larch/issue/shared.py"], fix_time=now - 300),
    ]
    manifest = {"schema_version": "1", "repo": "o/r", "run_id": "200", "generated_at": now, "issues": issues}
    ledger = tmp_path / "ledger.jsonl"

    view = analyze_bugs.build_analytics_view(
        manifest=manifest,
        bundles=[_bundle_from_mapping(row) for row in issues],
        ledger_path=ledger,
    )

    assert analyze_bugs.ChainEdge(1, 9, "marker") in view.chain_edges
    assert analyze_bugs.ChainEdge(1, 2, "file_intersection") in view.chain_edges
    assert analyze_bugs.ChainEdge(2, 3, "file_intersection") in view.chain_edges
    assert view.churned_files == ("python/larch/issue/shared.py",)
    assert view.chronic_zones[0].zone == "python/larch/issue"
    assert view.chronic_zones[0].issues == (1, 2, 3)
    assert view.baseline_issues == (1,)


def test_risk_routing_priority_and_verified_triage_gate(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    now = 2_000_000
    raw = _analytics_bundle(
        run_dir,
        issue=1,
        cache_key="k1",
        files=["python/larch/issue/a.py", "scripts/a.sh"],
        fix_time=now - 100,
        added_lines=500,
        markers=[2],
    )
    bundle = _bundle_from_mapping(raw)
    verified = analyze_bugs.LedgerRecord(
        cache_key="k1",
        issue=1,
        fix_sha="sha-1",
        later_history_hash="later",
        triage_verdict="FIXED_CLEAR",
        triage_evidence_verified=True,
        stages_complete=("triage",),
    )
    view = analyze_bugs.build_analytics_view(manifest={"generated_at": now}, bundles=[bundle], ledger_path=tmp_path / "ledger.jsonl")

    candidates = _priority_deep_candidates(bundles=[bundle], ledger={"k1": verified}, sample=0, refresh=False, analytics=view)
    blocked = _priority_deep_candidates(
        bundles=[bundle],
        ledger={"k1": analyze_bugs.LedgerRecord(cache_key="k1", issue=1, fix_sha="sha-1", later_history_hash="later", triage_verdict="FIXED_CLEAR", stages_complete=("triage",))},
        sample=0,
        refresh=False,
        analytics=view,
    )

    assert candidates[0]["source"] == "chain-linked"
    assert not blocked


def test_report_renders_analytics_and_stable_delta(tmp_path: Path, monkeypatch: object) -> None:
    runs = tmp_path / "runs"
    prior_dir = runs / "100"
    run_dir = runs / "200"
    prior_dir.mkdir(parents=True)
    run_dir.mkdir()
    now = 2_000_000
    prior = analyze_bugs.RunSnapshot("1", "o/r", "100", now - 1000, (1,), (1,), (), (), analyze_bugs.VERIFIED_PREDICATE_VERSION)
    _write_json(prior_dir / "run-state.json", cast("dict[str, object]", analyze_bugs.asdict(prior)))
    issues = [
        _analytics_bundle(run_dir, issue=1, cache_key="k1", files=["python/larch/issue/shared.py", "python/complexity-baseline.json"], fix_time=now - 100, markers=[9], mechanical="NOT_FIXED"),
        _analytics_bundle(run_dir, issue=2, cache_key="k2", files=["python/larch/issue/shared.py"], fix_time=now - 200, mechanical="WONTFIX"),
        _analytics_bundle(run_dir, issue=3, cache_key="k3", files=["python/larch/issue/shared.py"], fix_time=now - 300, mechanical="NOT_FIXED"),
    ]
    manifest: dict[str, object] = {
        "schema_version": "1", "repo": "o/r", "run_id": "200", "run_dir": str(run_dir), "evidence_ref": "origin/main",
        "bugs_requested": 3, "bugs_selected": 3, "generated_at": now, "ledger_path": str(tmp_path / "ledger.jsonl"),
        "triage_batch_paths": [], "deep_queue_path": str(run_dir / "deep-queue.jsonl"), "issues": issues,
    }
    _write_json(run_dir / "manifest.json", manifest)
    monkeypatch.setattr(analyze_bugs, "_runner", RecordingRunner)  # type: ignore[attr-defined]  # test seam

    report = analyze_bugs.render_report(manifest_path=run_dir / "manifest.json", ledger_path=tmp_path / "ledger.jsonl", run_dir=run_dir)

    assert "| Issue | Fix | Tier | Verdict |" in report
    assert "## Chronic zones" in report
    assert "## Fix chains" in report
    assert "## Baseline-extending fixes" in report
    assert "## Since last run" in report
    assert "Newly selected: #2, #3" in report
    assert "Suggestion: run /learn-from-bugs scoped to python/larch/issue." in report
    assert report.rstrip().splitlines()[-1].startswith("ANALYZE_BUGS_COST_ESTIMATE=")


def test_file_intersection_excludes_exact_fourteen_day_boundary(tmp_path: Path) -> None:
    now = 2_000_000
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    issues = [
        _analytics_bundle(run_dir, issue=1, cache_key="k1", files=["shared.py"], fix_time=now),
        _analytics_bundle(run_dir, issue=2, cache_key="k2", files=["shared.py"], fix_time=now - (14 * analyze_bugs.DAY_SECONDS)),
    ]

    view = analyze_bugs.build_analytics_view(
        manifest={"generated_at": now},
        bundles=[_bundle_from_mapping(row) for row in issues],
        ledger_path=tmp_path / "ledger.jsonl",
    )

    assert not any(edge.detector_kind == "file_intersection" for edge in view.chain_edges)


def test_hydrates_undated_historical_fix_before_window_filter(tmp_path: Path) -> None:
    now = 2_000_000
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps({"cache_key": "historic", "issue": 2, "fix_sha": "sha-2", "later_history_hash": "", "fix_time": 0, "updated_at": 1}) + "\n",
        encoding="utf-8",
    )
    runner = RecordingRunner(responses=[_result("python/a.py\n"), _result(str(now - 100)), _result("4\t0\tpython/a.py\n")], strict=True)

    view = analyze_bugs.build_analytics_view(manifest={"generated_at": now}, bundles=[], ledger_path=ledger, runner=runner)

    assert [record.issue for record in view.records] == [2]
    assert view.hydrated_records[0].fix_time == now - 100


def test_hydration_repairs_partial_metadata_and_marker_backfill_keeps_it(tmp_path: Path) -> None:
    now = 2_000_000
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps({"cache_key": "historic", "issue": 2, "fix_sha": "sha-2", "later_history_hash": "", "fix_time": now - 100, "added_lines": 0, "touched_files": [], "updated_at": 1, "metadata_version": 1}) + "\n",
        encoding="utf-8",
    )
    runner = RecordingRunner(
        responses=[_result("python/a.py\n"), _result(str(now - 100)), _result("4\t0\tpython/a.py\n"), _result(json.dumps({"title": "[BUG] residual after #1", "body": "body"}))],
        strict=True,
    )

    view = analyze_bugs.build_analytics_view(manifest={"generated_at": now, "repo": "o/r"}, bundles=[], ledger_path=ledger, runner=runner)

    assert view.hydrated_records[0].touched_files == ("python/a.py",)
    assert view.hydrated_records[0].added_lines == 4
    assert view.hydrated_records[0].marker_references == (1,)


def test_external_marker_reference_does_not_make_zone_chronic(tmp_path: Path) -> None:
    now = 2_000_000
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    bundles = [
        _bundle_from_mapping(_analytics_bundle(run_dir, issue=1, cache_key="k1", files=["python/a.py"], fix_time=now - 100, markers=[9])),
        _bundle_from_mapping(_analytics_bundle(run_dir, issue=2, cache_key="k2", files=["python/b.py"], fix_time=now - 200, markers=[9])),
    ]

    view = analyze_bugs.build_analytics_view(manifest={"generated_at": now}, bundles=bundles, ledger_path=tmp_path / "ledger.jsonl")

    assert not view.chronic_zones


def test_historical_marker_backfill_is_deferred_until_report_success(tmp_path: Path, monkeypatch: object) -> None:
    runs = tmp_path / "runs"
    run_dir = runs / "200"
    run_dir.mkdir(parents=True)
    now = 2_000_000
    manifest = _single_manifest(run_dir, issue=1, cache_key="active", mechanical="WONTFIX")
    manifest["generated_at"] = now
    manifest["run_id"] = "200"
    manifest["run_dir"] = str(run_dir)
    manifest["ledger_path"] = str(tmp_path / "ledger.jsonl")
    issues = cast("list[dict[str, object]]", manifest["issues"])
    issues[0]["fix_sha"] = ""
    _write_json(run_dir / "manifest.json", manifest)
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps({"cache_key": "historic", "issue": 2, "fix_sha": "", "later_history_hash": "", "fix_time": now - 100, "updated_at": 1}) + "\n",
        encoding="utf-8",
    )
    runner = RecordingRunner(responses=[_result(json.dumps({"title": "[BUG] residual after #1", "body": "body"}))], strict=True)
    monkeypatch.setattr(analyze_bugs, "_runner", lambda: runner)  # type: ignore[attr-defined]  # typed runner factory

    report = analyze_bugs.render_report(manifest_path=run_dir / "manifest.json", ledger_path=ledger, run_dir=run_dir)
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]

    assert "| #2 | #1 | marker |" in report
    assert rows[-1]["marker_references"] == [1]
    assert rows[-1]["marker_fingerprint"]


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    merged = {
        **os.environ,
        "GIT_AUTHOR_NAME": "sweep-test",
        "GIT_AUTHOR_EMAIL": "sweep@example.com",
        "GIT_COMMITTER_NAME": "sweep-test",
        "GIT_COMMITTER_EMAIL": "sweep@example.com",
    }
    if env:
        merged.update(env)
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env=merged,
    )
    return result.stdout.strip()


def _init_sweep_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "sweep@example.com")
    _git(repo, "config", "user.name", "sweep-test")
    return repo


def _commit_file(repo: Path, relative: str, content: str, message: str, *, when: int | None = None) -> str:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    _git(repo, "add", "--", relative)
    env: dict[str, str] = {}
    if when is not None:
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(when)) + " +0000"
        env["GIT_AUTHOR_DATE"] = stamp
        env["GIT_COMMITTER_DATE"] = stamp
    _git(repo, "commit", "-q", "-m", message, env=env or None)
    return _git(repo, "rev-parse", "HEAD")


def _merge_branch(repo: Path, branch: str, message: str, *, when: int | None = None) -> str:
    env: dict[str, str] = {}
    if when is not None:
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(when)) + " +0000"
        env["GIT_AUTHOR_DATE"] = stamp
        env["GIT_COMMITTER_DATE"] = stamp
    _git(repo, "merge", "--no-ff", "-q", "-m", message, branch, env=env or None)
    return _git(repo, "rev-parse", "HEAD")


def _set_origin_main(repo: Path, sha: str | None = None) -> str:
    tip = sha or _git(repo, "rev-parse", "HEAD")
    _git(repo, "update-ref", "refs/remotes/origin/main", tip)
    return tip


def _ledger_row(
    *,
    issue: int,
    cache_key: str,
    files: list[str],
    fix_time: int,
    fix_sha: str = "a" * 40,
    added_lines: int = 10,
) -> str:
    zones = sorted({analyze_bugs.zone_for_path(path) for path in files})
    return json.dumps(
        {
            "cache_key": cache_key,
            "issue": issue,
            "fix_sha": fix_sha,
            "later_history_hash": "later",
            "triage_verdict": "FIXED_CLEAR",
            "triage_reason": "ok",
            "triage_missing_items": [],
            "triage_needs_deep": False,
            "triage_evidence_verified": True,
            "deep_verdict": "",
            "deep_reason": "",
            "sampled": False,
            "stages_complete": ["triage"],
            "updated_at": fix_time,
            "touched_files": files,
            "fix_time": fix_time,
            "added_lines": added_lines,
            "marker_references": [],
            "marker_fingerprint": "",
            "zones": zones,
            "baseline_extended": False,
            "metadata_version": analyze_bugs.ANALYTICS_METADATA_VERSION,
        },
        sort_keys=True,
    )


def _write_chronic_ledger(path: Path, *, now: int) -> None:
    # Three bugs in python/larch/issue within the 14-day analytics window.
    rows = [
        _ledger_row(issue=11, cache_key="c1", files=["python/larch/issue/shared.py"], fix_time=now - 100, fix_sha="1" * 40),
        _ledger_row(issue=12, cache_key="c2", files=["python/larch/issue/shared.py"], fix_time=now - 200, fix_sha="2" * 40),
        _ledger_row(issue=13, cache_key="c3", files=["python/larch/issue/shared.py"], fix_time=now - 300, fix_sha="3" * 40),
    ]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_sweep_state_round_trip_and_absent_default(tmp_path: Path) -> None:
    path = tmp_path / "sweep-state.json"
    assert analyze_bugs.load_sweep_state(path) is None

    state = analyze_bugs.SweepState(
        last_sweep_sha="a" * 40,
        last_sweep_at="2026-07-13T12:00:00Z",
        schema_version=analyze_bugs.SWEEP_SCHEMA_VERSION,
        pending_shas=("b" * 40, "c" * 40),
    )
    analyze_bugs.write_sweep_state(path, state)
    loaded = analyze_bugs.load_sweep_state(path)
    assert loaded == state
    assert oct(path.stat().st_mode & 0o777) in {"0o600", "0o400"}


def test_sweep_state_round_trips_pending_frontier_over_1000_shas(tmp_path: Path) -> None:
    path = tmp_path / "sweep-state.json"
    pending = tuple(f"{index:040x}" for index in range(1_001))
    state = analyze_bugs.SweepState(
        last_sweep_sha="a" * 40,
        last_sweep_at="2026-07-13T12:00:00Z",
        schema_version=analyze_bugs.SWEEP_SCHEMA_VERSION,
        pending_shas=pending,
    )

    analyze_bugs.write_sweep_state(path, state)

    assert analyze_bugs.load_sweep_state(path) == state


def test_sweep_state_rejects_malformed_schema_and_pending(tmp_path: Path) -> None:
    path = tmp_path / "sweep-state.json"
    _write_json(
        path,
        {
            "last_sweep_sha": "a" * 40,
            "last_sweep_at": "2026-07-13T12:00:00Z",
            "schema_version": 99,
            "pending_shas": [],
        },
    )
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="unsupported sweep state schema"):
        analyze_bugs.load_sweep_state(path)

    _write_json(
        path,
        {
            "last_sweep_sha": "not-a-sha",
            "last_sweep_at": "2026-07-13T12:00:00Z",
            "schema_version": 1,
            "pending_shas": [],
        },
    )
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="full 40-character"):
        analyze_bugs.load_sweep_state(path)

    _write_json(
        path,
        {
            "last_sweep_sha": "a" * 40,
            "last_sweep_at": "2026-07-13T12:00:00Z",
            "schema_version": 1,
            "pending_shas": ["b" * 40, "b" * 40],
        },
    )
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="duplicate pending"):
        analyze_bugs.load_sweep_state(path)

    _write_json(
        path,
        {
            "last_sweep_sha": "a" * 40,
            "last_sweep_at": "yesterday",
            "schema_version": 1,
            "pending_shas": [],
        },
    )
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="ISO-8601"):
        analyze_bugs.load_sweep_state(path)


def test_sweep_enumeration_selects_merges_only_and_excludes_flush_release_and_logs_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_sweep_repo(tmp_path)
    monkeypatch.chdir(repo)
    base = _commit_file(repo, "python/larch/issue/a.py", "A = 1\n", "seed", when=1_700_000_000)
    _set_origin_main(repo, base)

    flush = _commit_file(repo, "larch-logs/run/x.md", "log\n", "chore(larch-logs): flush", when=1_700_000_100)
    release = _commit_file(repo, "VERSION", "1.0.0\n", "Release v1.0.0", when=1_700_000_200)
    logs_only = _commit_file(repo, "larch-logs/other.md", "more\n", "docs: logs only", when=1_700_000_300)
    direct = _commit_file(repo, "python/larch/issue/a.py", "A = 2\n", "fix: direct main commit", when=1_700_000_400)
    _git(repo, "checkout", "-q", "-b", "real-one")
    _commit_file(repo, "python/larch/issue/a.py", "A = 3\n", "fix: real one", when=1_700_000_500)
    _git(repo, "checkout", "-q", "main")
    _git(repo, "merge", "--no-ff", "-q", "-m", "Merge real one", "real-one")
    real_one = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "-b", "real-two")
    _commit_file(repo, "python/larch/core/b.py", "B = 1\n", "fix: real two", when=1_700_000_600)
    _git(repo, "checkout", "-q", "main")
    _git(repo, "merge", "--no-ff", "-q", "-m", "Merge real two", "real-two")
    real_two = _git(repo, "rev-parse", "HEAD")
    tip = _set_origin_main(repo)

    run_dir = tmp_path / "run"
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("", encoding="utf-8")
    analyze_bugs.write_sweep_state(
        analyze_bugs.sweep_state_path(ledger),
        analyze_bugs.SweepState(
            last_sweep_sha=base,
            last_sweep_at="2026-01-01T00:00:00Z",
            schema_version=1,
            pending_shas=(),
        ),
    )

    result = analyze_bugs.sweep_enumeration(
        runner=ProcRunner(),
        ledger_path=ledger,
        run_dir=run_dir,
        repo="o/r",
        sweep_max=20,
        pinned_tip=tip,
    )

    selected = {commit.merge_sha for commit in result.selected}
    assert selected == {real_one, real_two}
    assert flush not in selected
    assert release not in selected
    assert logs_only not in selected
    assert direct not in selected
    assert result.skipped_count == 0


def test_sweep_enumeration_first_run_window_and_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_sweep_repo(tmp_path)
    monkeypatch.chdir(repo)
    old = _commit_file(repo, "python/old.py", "X = 1\n", "old commit", when=1_000_000_000)
    _git(repo, "checkout", "-q", "-b", "recent")
    _commit_file(repo, "python/new.py", "Y = 1\n", "recent commit", when=1_800_000_000)
    _git(repo, "checkout", "-q", "main")
    recent = _merge_branch(repo, "recent", "Merge recent", when=1_800_000_000)
    tip = _set_origin_main(repo)
    run_dir = tmp_path / "run"
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("", encoding="utf-8")

    result = analyze_bugs.sweep_enumeration(
        runner=ProcRunner(),
        ledger_path=ledger,
        run_dir=run_dir,
        repo="o/r",
        sweep_max=20,
        pinned_tip=tip,
        now=1_800_000_000 + 3_600,
    )
    assert [commit.merge_sha for commit in result.selected] == [recent]
    assert old not in {commit.merge_sha for commit in result.selected}

    # Far enough after the tip that the 48-hour first-run window is empty.
    empty = analyze_bugs.sweep_enumeration(
        runner=ProcRunner(),
        ledger_path=ledger,
        run_dir=run_dir,
        repo="o/r",
        sweep_max=20,
        pinned_tip=tip,
        now=1_800_000_000 + analyze_bugs.SWEEP_INITIAL_WINDOW_SECONDS + 10,
    )
    assert not empty.selected
    assert not empty.pending_shas
    assert empty.skipped_count == 0


def test_sweep_enumeration_reachability_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_sweep_repo(tmp_path)
    monkeypatch.chdir(repo)
    tip = _commit_file(repo, "python/a.py", "A = 1\n", "tip", when=1_700_000_000)
    _set_origin_main(repo, tip)
    other = tmp_path / "other"
    other.mkdir()
    _git(other, "init", "-q", "-b", "main")
    _git(other, "config", "user.email", "sweep@example.com")
    _git(other, "config", "user.name", "sweep-test")
    foreign = _commit_file(other, "x.py", "1\n", "foreign", when=1_700_000_100)

    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("", encoding="utf-8")
    analyze_bugs.write_sweep_state(
        analyze_bugs.sweep_state_path(ledger),
        analyze_bugs.SweepState(
            last_sweep_sha=foreign,
            last_sweep_at="2026-01-01T00:00:00Z",
            schema_version=1,
            pending_shas=(),
        ),
    )
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match=r"last_sweep_sha .* not reachable"):
        analyze_bugs.sweep_enumeration(
            runner=ProcRunner(),
            ledger_path=ledger,
            run_dir=tmp_path / "run",
            repo="o/r",
            sweep_max=20,
            pinned_tip=tip,
        )

    analyze_bugs.write_sweep_state(
        analyze_bugs.sweep_state_path(ledger),
        analyze_bugs.SweepState(
            last_sweep_sha=tip,
            last_sweep_at="2026-01-01T00:00:00Z",
            schema_version=1,
            pending_shas=(foreign,),
        ),
    )
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match=r"pending SHA .* not reachable"):
        analyze_bugs.sweep_enumeration(
            runner=ProcRunner(),
            ledger_path=ledger,
            run_dir=tmp_path / "run",
            repo="o/r",
            sweep_max=20,
            pinned_tip=tip,
        )


def test_sweep_first_parent_merge_evidence_and_symbols(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_sweep_repo(tmp_path)
    monkeypatch.chdir(repo)
    _commit_file(repo, "python/larch/issue/mod.py", "VALUE = 1\n\ndef helper():\n    return VALUE\n", "base", when=1_700_000_000)
    _git(repo, "checkout", "-q", "-b", "feature")
    _commit_file(
        repo,
        "python/larch/issue/mod.py",
        "VALUE = 2\n\ndef helper():\n    return VALUE\n\ndef planted():\n    return VALUE\n",
        "feature change",
        when=1_700_000_100,
    )
    _git(repo, "checkout", "-q", "main")
    mainline = _commit_file(repo, "python/larch/issue/consumer.py", "from python.larch.issue.mod import planted\n", "mainline consumer", when=1_700_000_150)
    _git(repo, "merge", "--no-ff", "-q", "-m", "Merge feature into main", "feature")
    merge_sha = _git(repo, "rev-parse", "HEAD")
    tip = _set_origin_main(repo)
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("", encoding="utf-8")
    analyze_bugs.write_sweep_state(
        analyze_bugs.sweep_state_path(ledger),
        analyze_bugs.SweepState(last_sweep_sha=mainline, last_sweep_at="2026-01-01T00:00:00Z", schema_version=1, pending_shas=()),
    )

    result = analyze_bugs.sweep_prepare(
        runner=ProcRunner(),
        run_dir=tmp_path / "run",
        ledger_path=ledger,
        repo="o/r",
        sweep_max=20,
        pinned_tip=tip,
    )
    assert result["SELECTED_COUNT"] == 1
    selected = json.loads(Path(str(result["SELECTED_MERGE_MANIFEST"])).read_text(encoding="utf-8"))
    row = selected["selected"][0]
    assert row["merge_sha"] == merge_sha
    assert row["base_sha"] == mainline
    assert "python/larch/issue/mod.py" in row["touched_paths"]
    assert "python/larch/issue/consumer.py" not in row["touched_paths"]
    bundle_text = Path(row["bundle_path"]).read_text(encoding="utf-8")
    assert "def planted" in bundle_text
    assert "planted" in bundle_text
    assert "changed_symbols: planted" in bundle_text or "planted" in bundle_text


def test_sweep_chronic_priority_cap_and_pending_frontier(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_sweep_repo(tmp_path)
    monkeypatch.chdir(repo)
    now = int(time.time())
    base = _commit_file(repo, "README.md", "root\n", "seed", when=now - 1_000)
    # Non-chronic but large diff.
    big = "Z = '" + ("x" * 4000) + "'\n"
    _git(repo, "checkout", "-q", "-b", "non-chronic")
    _commit_file(repo, "docs/guide.md", big, "docs: large non-chronic", when=now - 300)
    _git(repo, "checkout", "-q", "main")
    non_chronic = _merge_branch(repo, "non-chronic", "Merge non-chronic", when=now - 300)
    # Chronic zone, smaller diff.
    _git(repo, "checkout", "-q", "-b", "chronic")
    _commit_file(repo, "python/larch/issue/shared.py", "SHARED = 1\n", "fix: chronic small", when=now - 200)
    _git(repo, "checkout", "-q", "main")
    chronic = _merge_branch(repo, "chronic", "Merge chronic", when=now - 200)
    _git(repo, "checkout", "-q", "-b", "later")
    _commit_file(repo, "scripts/tool.sh", "echo hi\n", "scripts: later", when=now - 100)
    _git(repo, "checkout", "-q", "main")
    later = _merge_branch(repo, "later", "Merge later", when=now - 100)
    tip = _set_origin_main(repo)

    ledger = tmp_path / "ledger.jsonl"
    _write_chronic_ledger(ledger, now=now)
    analyze_bugs.write_sweep_state(
        analyze_bugs.sweep_state_path(ledger),
        analyze_bugs.SweepState(last_sweep_sha=base, last_sweep_at="2026-01-01T00:00:00Z", schema_version=1, pending_shas=()),
    )

    run1 = tmp_path / "run1"
    capped = analyze_bugs.sweep_prepare(
        runner=ProcRunner(),
        run_dir=run1,
        ledger_path=ledger,
        repo="o/r",
        sweep_max=1,
        pinned_tip=tip,
        now=now,
    )
    assert capped["SELECTED_COUNT"] == 1
    assert capped["SKIPPED_COUNT"] == 2
    assert capped["COVERAGE_INCOMPLETE"] == "true"
    assert set(cast("tuple[str, ...]", capped["PENDING_SHAS"])) == {non_chronic, later}
    selected = json.loads(Path(str(capped["SELECTED_MERGE_MANIFEST"])).read_text(encoding="utf-8"))
    assert selected["selected"][0]["merge_sha"] == chronic
    assert selected["selected"][0]["is_chronic"] is True
    # Prepare must not mutate durable sweep state.
    durable = analyze_bugs.load_sweep_state(analyze_bugs.sweep_state_path(ledger))
    assert durable is not None
    assert not durable.pending_shas
    assert durable.last_sweep_sha == base

    (run1 / analyze_bugs.SWEEP_FINDER_RAW_NAME).write_text(
        _finder_jsonl([{"merge_sha": chronic, "findings": []}]), encoding="utf-8"
    )
    analyze_bugs.sweep_ingest_finder(run_dir=run1)
    analyze_bugs.sweep_ingest_refuter(run_dir=run1)
    _write_json(run1 / "manifest.json", _single_manifest(run1, mechanical="WONTFIX"))
    _write_bundle(run1 / "issue-1-bundle.md")
    monkeypatch.setattr(analyze_bugs, "_runner", ProcRunner)
    analyze_bugs.render_report(manifest_path=run1 / "manifest.json", ledger_path=ledger, run_dir=run1)

    committed = analyze_bugs.load_sweep_state(analyze_bugs.sweep_state_path(ledger))
    assert committed is not None
    assert committed.last_sweep_sha == tip
    assert committed.pending_shas == (non_chronic, later)

    _commit_file(repo, "README.md", "root2\n", "chore: tiny readme", when=now + 50)
    new_tip = _set_origin_main(repo)
    resumed = analyze_bugs.sweep_prepare(
        runner=ProcRunner(),
        ledger_path=ledger,
        run_dir=tmp_path / "run2",
        repo="o/r",
        sweep_max=1,
        pinned_tip=new_tip,
        now=now + 100,
    )
    resumed_manifest = json.loads(Path(str(resumed["SELECTED_MERGE_MANIFEST"])).read_text(encoding="utf-8"))
    assert resumed_manifest["selected"][0]["merge_sha"] == non_chronic
    assert later in cast("tuple[str, ...]", resumed["PENDING_SHAS"])
    assert cast("int", resumed["SKIPPED_COUNT"]) >= 1


def test_sweep_prepare_cli_fence_and_help(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_sweep_repo(tmp_path)
    monkeypatch.chdir(repo)
    base = _commit_file(repo, "python/a.py", "A = 1\n", "seed", when=1_700_000_000)
    _commit_file(repo, "python/a.py", "A = 2\n", "change", when=1_700_000_100)
    tip = _set_origin_main(repo)
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("", encoding="utf-8")
    analyze_bugs.write_sweep_state(
        analyze_bugs.sweep_state_path(ledger),
        analyze_bugs.SweepState(last_sweep_sha=base, last_sweep_at="2026-01-01T00:00:00Z", schema_version=1, pending_shas=()),
    )
    run_dir = tmp_path / "run"
    monkeypatch.setattr(analyze_bugs, "_runner", ProcRunner)
    monkeypatch.setattr(analyze_bugs, "resolve_repo", lambda _runner, explicit="": explicit or "o/r")  # pyright: ignore[reportUnknownLambdaType]  # test stub

    rc = analyze_bugs.sweep_main(
        ["prepare", "--run-dir", str(run_dir), "--ledger-path", str(ledger), "--repo", "o/r", "--sweep-max", "20"]
    )
    assert rc == 0
    assert (run_dir / analyze_bugs.SWEEP_SELECTED_MANIFEST_NAME).is_file()
    assert (run_dir / analyze_bugs.SWEEP_BUNDLE_MANIFEST_NAME).is_file()
    help_result = run_cli("analyze-bugs", "sweep", "--help")
    assert help_result.returncode == 0
    assert "prepare" in help_result.stdout

    # Invalid state fails closed.
    analyze_bugs.write_sweep_state(
        analyze_bugs.sweep_state_path(ledger),
        analyze_bugs.SweepState(last_sweep_sha="f" * 40, last_sweep_at="2026-01-01T00:00:00Z", schema_version=1, pending_shas=()),
    )
    # Force an unreachable watermark by writing a valid-looking but foreign SHA after replacing tip pin.
    foreign_repo = tmp_path / "foreign"
    foreign_repo.mkdir()
    _git(foreign_repo, "init", "-q", "-b", "main")
    _git(foreign_repo, "config", "user.email", "sweep@example.com")
    _git(foreign_repo, "config", "user.name", "sweep-test")
    foreign = _commit_file(foreign_repo, "z.py", "1\n", "foreign", when=1_700_000_200)
    bad_state = analyze_bugs.SweepState(last_sweep_sha=foreign, last_sweep_at="2026-01-01T00:00:00Z", schema_version=1, pending_shas=())
    analyze_bugs.write_sweep_state(analyze_bugs.sweep_state_path(ledger), bad_state)
    rc_bad = analyze_bugs.sweep_main(
        ["prepare", "--run-dir", str(tmp_path / "run-bad"), "--ledger-path", str(ledger), "--repo", "o/r"]
    )
    assert rc_bad == 1
    assert tip


def test_non_sweep_verbs_do_not_touch_sweep_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    ledger = tmp_path / "ledger.jsonl"
    state_path = analyze_bugs.sweep_state_path(ledger)
    assert not state_path.exists()
    manifest = _single_manifest(run_dir, issue=1, cache_key="k1", mechanical="WONTFIX")
    manifest["ledger_path"] = str(ledger)
    _write_json(run_dir / "manifest.json", manifest)
    _write_bundle(run_dir / "issue-1-bundle.md")
    monkeypatch.setattr(analyze_bugs, "_runner", lambda: RecordingRunner(default=_result("")))

    summary = analyze_bugs.ledger_compute(
        run_dir=run_dir,
        ledger_path=ledger,
        manifest_path=run_dir / "manifest.json",
        refresh=False,
        sample=0,
        deep_max=0,
        deep_model="sonnet",
        batch_size=10,
    )
    assert "TRIAGE_BATCH_PATHS" in summary or "DEEP_QUEUE_PATH" in summary or summary
    assert not state_path.exists()

    report = analyze_bugs.render_report(manifest_path=run_dir / "manifest.json", ledger_path=ledger, run_dir=run_dir)
    assert "Analyze Bugs Report" in report
    assert not state_path.exists()


# ---------------------------------------------------------------------------
# Sweep report/state integration (issue #7208, piece 3).
# ---------------------------------------------------------------------------


def _write_validated_sweep_artifact(
    run_dir: Path,
    *,
    pending: tuple[str, ...] = (),
    skipped: int = 0,
    candidate: bool = True,
) -> None:
    selected = _sweep_selected_manifest(
        run_dir,
        pending=pending,
        skipped=skipped,
        coverage_incomplete=bool(pending),
    )
    bundle_path = run_dir / f"sweep-{SWEEP_SHA_A}-bundle.md"
    bundle_path.write_text("# Sweep evidence\n" + ("x" * 40) + "\n", encoding="utf-8")
    (run_dir / analyze_bugs.SWEEP_REFUTER_QUEUE_NAME).write_text(
        json.dumps(
            {
                "merge_sha": SWEEP_SHA_A,
                "finding_index": 0,
                "file": "python/example.py",
                "symbol": "example",
                "description": "wrong field remains in a consumer",
                "severity": "high",
                "confidence": "medium",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(run_dir / analyze_bugs.SWEEP_SELECTED_MANIFEST_NAME, selected)
    _write_json(
        run_dir / analyze_bugs.SWEEP_VALIDATED_NAME,
        {
            "pinned_tip": SWEEP_TIP,
            "selected_manifest_path": str(run_dir / analyze_bugs.SWEEP_SELECTED_MANIFEST_NAME),
            "selected_count": 1,
            "skipped_count": skipped,
            "pending_shas": list(pending),
            "coverage_incomplete": bool(pending),
            "candidates": [
                {
                    "merge_sha": SWEEP_SHA_A,
                    "file": "python/example.py",
                    "symbol": "example",
                    "description": "wrong field remains in a consumer",
                    "severity": "high",
                    "confidence": "medium",
                }
            ]
            if candidate
            else [],
        },
    )


def test_render_report_merges_sweep_and_commits_pending_state_last(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    ledger = tmp_path / "ledger.jsonl"
    manifest = _single_manifest(run_dir, mechanical="NOT_FIXED")
    _write_json(run_dir / "manifest.json", manifest)
    _write_bundle(run_dir / "issue-1-bundle.md")
    _write_validated_sweep_artifact(run_dir, pending=(SWEEP_SHA_B,), skipped=1)
    analyze_bugs.write_sweep_state(
        analyze_bugs.sweep_state_path(ledger),
        analyze_bugs.SweepState(SWEEP_SHA_C, "2026-01-01T00:00:00Z", 1, ()),
    )
    monkeypatch.setattr(analyze_bugs, "_runner", lambda: RecordingRunner(default=_result(SWEEP_TIP + "\n")))

    report = analyze_bugs.render_report(manifest_path=run_dir / "manifest.json", ledger_path=ledger, run_dir=run_dir)

    assert "## Sweep candidates" in report
    assert "python/example.py" in report
    assert "Sweep selected merges: 1" in report
    assert "Sweep skipped merges: 1" in report
    assert "Sweep pending frontier: 1" in report
    assert "Sweep coverage incomplete" in report
    assert "ANALYZE_BUGS_SWEEP_COST_ESTIMATE=$" in report
    followup = (run_dir / "follow-up-issue.md").read_text(encoding="utf-8")
    assert "#1: NOT_FIXED" in followup
    assert "Sweep candidates:" in followup
    state = analyze_bugs.load_sweep_state(analyze_bugs.sweep_state_path(ledger))
    assert state is not None
    assert state.last_sweep_sha == SWEEP_TIP
    assert state.pending_shas == (SWEEP_SHA_B,)
    assert (run_dir / "report.md").is_file()
    assert (run_dir / "follow-up-issue.md").is_file()


def test_sweep_report_failure_leaves_existing_state_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    ledger = tmp_path / "ledger.jsonl"
    _write_json(run_dir / "manifest.json", _single_manifest(run_dir, mechanical="WONTFIX"))
    _write_bundle(run_dir / "issue-1-bundle.md")
    _write_validated_sweep_artifact(run_dir, pending=(SWEEP_SHA_B,), skipped=1)
    state_path = analyze_bugs.sweep_state_path(ledger)
    analyze_bugs.write_sweep_state(
        state_path,
        analyze_bugs.SweepState(SWEEP_SHA_C, "2026-01-01T00:00:00Z", 1, ()),
    )
    before = state_path.read_text(encoding="utf-8")
    original_write = analyze_bugs._atomic_write_text  # pyright: ignore[reportPrivateUsage]  # report-write failure seam

    def fail_report(path: Path, text: str, *, mode: int = 0o600) -> None:
        if path.name == "report.md":
            raise OSError("simulated report write failure")
        original_write(path, text, mode=mode)

    monkeypatch.setattr(analyze_bugs, "_atomic_write_text", fail_report)
    monkeypatch.setattr(analyze_bugs, "_runner", lambda: RecordingRunner(default=_result(SWEEP_TIP + "\n")))

    with pytest.raises(OSError, match="simulated report"):
        analyze_bugs.render_report(manifest_path=run_dir / "manifest.json", ledger_path=ledger, run_dir=run_dir)
    assert state_path.read_text(encoding="utf-8") == before


def test_sweep_only_survivor_creates_followup_body(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    ledger = tmp_path / "ledger.jsonl"
    _write_json(run_dir / "manifest.json", _single_manifest(run_dir, mechanical="WONTFIX"))
    _write_bundle(run_dir / "issue-1-bundle.md")
    _write_validated_sweep_artifact(run_dir)
    monkeypatch.setattr(analyze_bugs, "_runner", lambda: RecordingRunner(default=_result(SWEEP_TIP + "\n")))

    report = analyze_bugs.render_report(manifest_path=run_dir / "manifest.json", ledger_path=ledger, run_dir=run_dir)

    followup = run_dir / "follow-up-issue.md"
    assert followup.is_file()
    assert "Sweep candidates:" in followup.read_text(encoding="utf-8")
    assert f"Follow-up body file: {followup}" in report


def test_sweep_report_rejects_stale_tip_or_manifest_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    ledger = tmp_path / "ledger.jsonl"
    _write_json(run_dir / "manifest.json", _single_manifest(run_dir, mechanical="WONTFIX"))
    _write_bundle(run_dir / "issue-1-bundle.md")
    _write_validated_sweep_artifact(run_dir)
    monkeypatch.setattr(analyze_bugs, "_runner", lambda: RecordingRunner(default=_result(SWEEP_SHA_B + "\n")))

    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="stale"):
        analyze_bugs.render_report(manifest_path=run_dir / "manifest.json", ledger_path=ledger, run_dir=run_dir)

    artifact_path = run_dir / analyze_bugs.SWEEP_VALIDATED_NAME
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["selected_manifest_path"] = str(tmp_path / "foreign.json")
    _write_json(artifact_path, artifact)
    monkeypatch.setattr(analyze_bugs, "_runner", lambda: RecordingRunner(default=_result(SWEEP_TIP + "\n")))
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="foreign selected manifest"):
        analyze_bugs.render_report(manifest_path=run_dir / "manifest.json", ledger_path=ledger, run_dir=run_dir)


# ---------------------------------------------------------------------------
# Sweep ingest-finder / ingest-refuter contract tests (issue #7207, piece 2).
# ---------------------------------------------------------------------------

SWEEP_TIP = "f" * 40
SWEEP_SHA_A = "a" * 40
SWEEP_SHA_B = "b" * 40
SWEEP_SHA_C = "c" * 40


def _sweep_selected_manifest(
    run_dir: Path,
    *,
    pinned_tip: str = SWEEP_TIP,
    shas: tuple[str, ...] = (SWEEP_SHA_A,),
    pending: tuple[str, ...] = (),
    skipped: int = 0,
    coverage_incomplete: bool = False,
) -> dict[str, object]:
    return {
        "pinned_tip": pinned_tip,
        "selected_count": len(shas),
        "skipped_count": skipped,
        "coverage_incomplete": coverage_incomplete,
        "pending_shas": list(pending),
        "selected": [
            {
                "merge_sha": sha,
                "base_sha": "0" * 40,
                "subject": f"merge {sha[:7]}",
                "diff_size": 1,
                "is_chronic": False,
                "chronic_zones": [],
                "touched_paths": [],
                "bundle_path": str(run_dir / f"sweep-{sha}-bundle.md"),
            }
            for sha in shas
        ],
    }


def _prepare_sweep_run(
    run_dir: Path,
    *,
    shas: tuple[str, ...] = (SWEEP_SHA_A,),
    pending: tuple[str, ...] = (),
    skipped: int = 0,
    coverage_incomplete: bool = False,
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        run_dir / analyze_bugs.SWEEP_SELECTED_MANIFEST_NAME,
        _sweep_selected_manifest(
            run_dir,
            shas=shas,
            pending=pending,
            skipped=skipped,
            coverage_incomplete=coverage_incomplete,
        ),
    )


def _finding(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "file": "python/larch/issue/mod.py",
        "symbol": "helper",
        "description": "wrong dict key",
        "severity": "high",
        "confidence": "medium",
    }
    base.update(overrides)
    return base


def _finder_jsonl(rows: list[dict[str, object]]) -> str:
    return "".join(json.dumps(dict(row), sort_keys=True) + "\n" for row in rows)


def _parse_kv(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            out[key] = value
    return out


def _run_ingest(subphase: str, run_dir: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, dict[str, str], str]:
    rc = analyze_bugs.sweep_main([subphase, "--run-dir", str(run_dir)])
    captured = capsys.readouterr()
    return rc, _parse_kv(captured.out), captured.err


def _refuter_setup(run_dir: Path, *, findings: int = 1) -> None:
    _prepare_sweep_run(run_dir, shas=(SWEEP_SHA_A,))
    finding_rows = [_finding(symbol=f"symbol_{i}") for i in range(findings)]
    (run_dir / analyze_bugs.SWEEP_FINDER_RAW_NAME).write_text(
        _finder_jsonl([{"merge_sha": SWEEP_SHA_A, "findings": finding_rows}]), encoding="utf-8"
    )
    analyze_bugs.sweep_ingest_finder(run_dir=run_dir)


def test_finder_finding_parser_strict() -> None:
    parsed = _parse_finder_finding(_finding())
    assert isinstance(parsed, analyze_bugs.SweepFinding)
    assert parsed.file == "python/larch/issue/mod.py"
    assert parsed.severity == "high"
    assert isinstance(_parse_finder_finding(_finding(extra="x")), str)
    assert isinstance(_parse_finder_finding(_finding(severity="blocker")), str)
    assert isinstance(_parse_finder_finding(_finding(confidence="maybe")), str)
    assert isinstance(_parse_finder_finding(_finding(file="/abs/x.py")), str)
    assert isinstance(_parse_finder_finding(_finding(file="../escape.py")), str)
    assert isinstance(_parse_finder_finding(_finding(file="")), str)
    normalized = _parse_finder_finding(_finding(description="  a\x07b  "))
    assert isinstance(normalized, analyze_bugs.SweepFinding)
    assert normalized.description == "ab"


def test_finder_row_parser_strict() -> None:
    empty = _parse_finder_row({"merge_sha": SWEEP_SHA_A, "findings": []})
    assert isinstance(empty, analyze_bugs.SweepFinderRow)
    assert empty.findings == ()
    populated = _parse_finder_row({"merge_sha": SWEEP_SHA_A, "findings": [_finding()]})
    assert isinstance(populated, analyze_bugs.SweepFinderRow)
    assert len(populated.findings) == 1
    assert isinstance(_parse_finder_row({"merge_sha": SWEEP_SHA_A}), str)
    assert isinstance(_parse_finder_row({"merge_sha": "short", "findings": []}), str)
    assert isinstance(_parse_finder_row({"merge_sha": SWEEP_SHA_A, "findings": {}}), str)
    over = {"merge_sha": SWEEP_SHA_A, "findings": [_finding() for _ in range(analyze_bugs.SWEEP_FINDINGS_PER_MERGE_CAP + 1)]}
    assert isinstance(_parse_finder_row(over), str)


def test_refuter_result_parser_strict() -> None:
    valid = _parse_refuter_result({"merge_sha": SWEEP_SHA_A, "finding_index": 0, "verdict": "survives"})
    assert isinstance(valid, analyze_bugs.SweepRefutationResult)
    assert isinstance(_parse_refuter_result({"merge_sha": SWEEP_SHA_A, "finding_index": 0, "verdict": "nope"}), str)
    assert isinstance(_parse_refuter_result({"merge_sha": SWEEP_SHA_A, "finding_index": 0}), str)
    assert isinstance(_parse_refuter_result({"merge_sha": SWEEP_SHA_A, "finding_index": -1, "verdict": "refuted"}), str)
    assert isinstance(_parse_refuter_result({"merge_sha": SWEEP_SHA_A, "finding_index": True, "verdict": "refuted"}), str)
    assert isinstance(_parse_refuter_result({"merge_sha": "short", "finding_index": 0, "verdict": "refuted"}), str)


def test_ingest_finder_happy_path_writes_deterministic_queue(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _prepare_sweep_run(run_dir, shas=(SWEEP_SHA_A,))
    (run_dir / analyze_bugs.SWEEP_FINDER_RAW_NAME).write_text(
        _finder_jsonl(
            [{"merge_sha": SWEEP_SHA_A, "findings": [_finding(symbol="first"), _finding(symbol="second", description="d2")]}]
        ),
        encoding="utf-8",
    )
    payload = analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
    assert payload["INGEST_ACCEPTED"] == 1
    assert payload["REFUTER_QUEUE_COUNT"] == 2
    assert payload["PINNED_TIP"] == SWEEP_TIP
    assert str(payload["SELECTED_MERGE_MANIFEST"]).endswith(analyze_bugs.SWEEP_SELECTED_MANIFEST_NAME)
    queue_lines = (run_dir / analyze_bugs.SWEEP_REFUTER_QUEUE_NAME).read_text(encoding="utf-8").splitlines()
    assert len(queue_lines) == 2
    rows = [json.loads(line) for line in queue_lines]
    assert [row["finding_index"] for row in rows] == [0, 1]
    assert {row["merge_sha"] for row in rows} == {SWEEP_SHA_A}
    assert set(rows[0]) == {"merge_sha", "finding_index", "file", "symbol", "description", "severity", "confidence"}
    assert rows[0]["symbol"] == "first"


def test_ingest_finder_rejects_invalid_output(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    finder = run_dir / analyze_bugs.SWEEP_FINDER_RAW_NAME
    queue = run_dir / analyze_bugs.SWEEP_REFUTER_QUEUE_NAME
    _prepare_sweep_run(run_dir, shas=(SWEEP_SHA_A,))
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="missing"):
        analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
    finder.write_text("\n   \n", encoding="utf-8")
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="empty"):
        analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
    finder.write_text(json.dumps({"merge_sha": SWEEP_SHA_A, "findings": [], "extra": 1}) + "\n", encoding="utf-8")
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="unexpected or missing"):
        analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
    finder.write_text(_finder_jsonl([{"merge_sha": SWEEP_SHA_A, "findings": [_finding(severity="blocker")]}]), encoding="utf-8")
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="severity"):
        analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
    finder.write_text(_finder_jsonl([{"merge_sha": SWEEP_SHA_A, "findings": []}, {"merge_sha": SWEEP_SHA_A, "findings": []}]), encoding="utf-8")
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="duplicate"):
        analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
    finder.write_text(_finder_jsonl([{"merge_sha": SWEEP_SHA_C, "findings": []}]), encoding="utf-8")
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="foreign"):
        analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
    finder.write_text(_finder_jsonl([{"merge_sha": SWEEP_SHA_A, "findings": [_finding(file="/abs/x.py")]}]), encoding="utf-8")
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="repository-relative"):
        analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
    _prepare_sweep_run(run_dir, shas=(SWEEP_SHA_A, SWEEP_SHA_B))
    finder.write_text(_finder_jsonl([{"merge_sha": SWEEP_SHA_A, "findings": []}]), encoding="utf-8")
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="missing selected"):
        analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
    assert not queue.exists()


def test_ingest_refuter_keeps_survivors_and_writes_validated_artifact(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _prepare_sweep_run(run_dir, shas=(SWEEP_SHA_A,), skipped=2, pending=(SWEEP_SHA_B,), coverage_incomplete=True)
    (run_dir / analyze_bugs.SWEEP_FINDER_RAW_NAME).write_text(
        _finder_jsonl([{"merge_sha": SWEEP_SHA_A, "findings": [_finding(symbol="a"), _finding(symbol="b", description="d2")]}]),
        encoding="utf-8",
    )
    analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
    (run_dir / analyze_bugs.SWEEP_REFUTER_RAW_NAME).write_text(
        "".join(
            json.dumps(row) + "\n"
            for row in [
                {"merge_sha": SWEEP_SHA_A, "finding_index": 0, "verdict": "survives"},
                {"merge_sha": SWEEP_SHA_A, "finding_index": 1, "verdict": "refuted"},
            ]
        ),
        encoding="utf-8",
    )
    payload = analyze_bugs.sweep_ingest_refuter(run_dir=run_dir)
    assert payload["CANDIDATE_COUNT"] == 1
    assert payload["REFUTED_COUNT"] == 1
    assert payload["REFUTER_QUEUE_COUNT"] == 2
    assert payload["PINNED_TIP"] == SWEEP_TIP
    validated = json.loads((run_dir / analyze_bugs.SWEEP_VALIDATED_NAME).read_text(encoding="utf-8"))
    assert validated["pinned_tip"] == SWEEP_TIP
    assert validated["selected_count"] == 1
    assert validated["skipped_count"] == 2
    assert validated["coverage_incomplete"] is True
    assert tuple(validated["pending_shas"]) == (SWEEP_SHA_B,)
    assert len(validated["candidates"]) == 1
    assert validated["candidates"][0]["symbol"] == "a"


def test_ingest_refuter_rejects_invalid_output(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    raw = run_dir / analyze_bugs.SWEEP_REFUTER_RAW_NAME
    validated = run_dir / analyze_bugs.SWEEP_VALIDATED_NAME

    _refuter_setup(run_dir, findings=1)
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="missing"):
        analyze_bugs.sweep_ingest_refuter(run_dir=run_dir)
    raw.write_text("\n", encoding="utf-8")
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="empty"):
        analyze_bugs.sweep_ingest_refuter(run_dir=run_dir)
    raw.write_text(json.dumps({"merge_sha": SWEEP_SHA_A, "finding_index": 0, "verdict": "survives", "reason": "x"}) + "\n", encoding="utf-8")
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="unexpected or missing"):
        analyze_bugs.sweep_ingest_refuter(run_dir=run_dir)
    raw.write_text(json.dumps({"merge_sha": SWEEP_SHA_A, "finding_index": 0, "verdict": "maybe"}) + "\n", encoding="utf-8")
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="unknown"):
        analyze_bugs.sweep_ingest_refuter(run_dir=run_dir)
    raw.write_text(
        "".join(
            json.dumps(row) + "\n"
            for row in [
                {"merge_sha": SWEEP_SHA_A, "finding_index": 0, "verdict": "survives"},
                {"merge_sha": SWEEP_SHA_A, "finding_index": 0, "verdict": "refuted"},
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="duplicate"):
        analyze_bugs.sweep_ingest_refuter(run_dir=run_dir)
    raw.write_text(json.dumps({"merge_sha": SWEEP_SHA_A, "finding_index": 9, "verdict": "survives"}) + "\n", encoding="utf-8")
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="foreign"):
        analyze_bugs.sweep_ingest_refuter(run_dir=run_dir)

    _refuter_setup(run_dir, findings=2)
    raw.write_text(json.dumps({"merge_sha": SWEEP_SHA_A, "finding_index": 0, "verdict": "survives"}) + "\n", encoding="utf-8")
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="missing 1 queued"):
        analyze_bugs.sweep_ingest_refuter(run_dir=run_dir)
    assert not validated.exists()


def test_refuter_queue_order_is_deterministic(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _prepare_sweep_run(run_dir, shas=(SWEEP_SHA_A, SWEEP_SHA_B))
    # Finder rows deliberately out of manifest order; the queue must follow manifest order.
    (run_dir / analyze_bugs.SWEEP_FINDER_RAW_NAME).write_text(
        _finder_jsonl(
            [
                {"merge_sha": SWEEP_SHA_B, "findings": [_finding(symbol="b0"), _finding(symbol="b1")]},
                {"merge_sha": SWEEP_SHA_A, "findings": [_finding(symbol="a0")]},
            ]
        ),
        encoding="utf-8",
    )
    analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
    rows = [json.loads(line) for line in (run_dir / analyze_bugs.SWEEP_REFUTER_QUEUE_NAME).read_text(encoding="utf-8").splitlines()]
    assert [row["merge_sha"] for row in rows] == [SWEEP_SHA_A, SWEEP_SHA_B, SWEEP_SHA_B]
    assert [row["finding_index"] for row in rows] == [0, 0, 1]


def test_ingest_zero_selected_merges_completes_without_finder_file(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _prepare_sweep_run(run_dir, shas=())
    payload = analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
    assert payload["INGEST_ACCEPTED"] == 0
    assert payload["REFUTER_QUEUE_COUNT"] == 0
    queue = run_dir / analyze_bugs.SWEEP_REFUTER_QUEUE_NAME
    assert queue.is_file()
    assert queue.read_text(encoding="utf-8") == ""
    rpayload = analyze_bugs.sweep_ingest_refuter(run_dir=run_dir)
    assert rpayload["CANDIDATE_COUNT"] == 0
    validated = json.loads((run_dir / analyze_bugs.SWEEP_VALIDATED_NAME).read_text(encoding="utf-8"))
    assert validated["candidates"] == []
    assert validated["pinned_tip"] == SWEEP_TIP


def test_ingest_empty_findings_for_all_merges_bypasses_refuter_file(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _prepare_sweep_run(run_dir, shas=(SWEEP_SHA_A, SWEEP_SHA_B))
    (run_dir / analyze_bugs.SWEEP_FINDER_RAW_NAME).write_text(
        _finder_jsonl([{"merge_sha": SWEEP_SHA_A, "findings": []}, {"merge_sha": SWEEP_SHA_B, "findings": []}]),
        encoding="utf-8",
    )
    payload = analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
    assert payload["INGEST_ACCEPTED"] == 2
    assert payload["REFUTER_QUEUE_COUNT"] == 0
    assert (run_dir / analyze_bugs.SWEEP_REFUTER_QUEUE_NAME).read_text(encoding="utf-8") == ""
    rpayload = analyze_bugs.sweep_ingest_refuter(run_dir=run_dir)
    assert rpayload["CANDIDATE_COUNT"] == 0
    assert (run_dir / analyze_bugs.SWEEP_VALIDATED_NAME).is_file()


def test_absent_or_empty_raw_files_fail_when_work_dispatched(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _prepare_sweep_run(run_dir, shas=(SWEEP_SHA_A,))
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="missing"):
        analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
    (run_dir / analyze_bugs.SWEEP_FINDER_RAW_NAME).write_text("\n", encoding="utf-8")
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="empty"):
        analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
    (run_dir / analyze_bugs.SWEEP_FINDER_RAW_NAME).write_text(
        _finder_jsonl([{"merge_sha": SWEEP_SHA_A, "findings": [_finding()]}]), encoding="utf-8"
    )
    analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="missing"):
        analyze_bugs.sweep_ingest_refuter(run_dir=run_dir)
    (run_dir / analyze_bugs.SWEEP_REFUTER_RAW_NAME).write_text("\n", encoding="utf-8")
    with pytest.raises(analyze_bugs.AnalyzeBugsError, match="empty"):
        analyze_bugs.sweep_ingest_refuter(run_dir=run_dir)


def test_zero_findings_distinct_from_failed_output(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _prepare_sweep_run(run_dir, shas=(SWEEP_SHA_A,))
    (run_dir / analyze_bugs.SWEEP_FINDER_RAW_NAME).write_text(
        _finder_jsonl([{"merge_sha": SWEEP_SHA_A, "findings": []}]), encoding="utf-8"
    )
    ok_payload = analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
    assert ok_payload["INGEST_ACCEPTED"] == 1
    assert ok_payload["REFUTER_QUEUE_COUNT"] == 0
    (run_dir / analyze_bugs.SWEEP_FINDER_RAW_NAME).unlink()
    with pytest.raises(analyze_bugs.AnalyzeBugsError):
        analyze_bugs.sweep_ingest_finder(run_dir=run_dir)


def test_sweep_ingest_failures_leave_durable_state_unchanged(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _prepare_sweep_run(run_dir, shas=(SWEEP_SHA_A, SWEEP_SHA_B))
    ledger = tmp_path / "ledger.jsonl"
    state_path = analyze_bugs.sweep_state_path(ledger)
    analyze_bugs.write_sweep_state(
        state_path,
        analyze_bugs.SweepState(
            last_sweep_sha=SWEEP_TIP,
            last_sweep_at="2026-01-01T00:00:00Z",
            schema_version=1,
            pending_shas=(SWEEP_SHA_B,),
        ),
    )
    before = state_path.read_text(encoding="utf-8")
    finder_raw = run_dir / analyze_bugs.SWEEP_FINDER_RAW_NAME
    queue_path = run_dir / analyze_bugs.SWEEP_REFUTER_QUEUE_NAME
    validated_path = run_dir / analyze_bugs.SWEEP_VALIDATED_NAME
    failure_cases: dict[str, str | None] = {
        "missing": None,
        "empty": "\n",
        "foreign": _finder_jsonl([{"merge_sha": SWEEP_SHA_C, "findings": []}]),
        "malformed": "{not json}\n",
        "incomplete": _finder_jsonl([{"merge_sha": SWEEP_SHA_A, "findings": []}]),
        "bad_enum": _finder_jsonl([{"merge_sha": SWEEP_SHA_A, "findings": [_finding(severity="blocker")]}]),
    }
    for content in failure_cases.values():
        if content is None:
            finder_raw.unlink(missing_ok=True)
        else:
            finder_raw.write_text(content, encoding="utf-8")
        queue_path.unlink(missing_ok=True)
        validated_path.unlink(missing_ok=True)
        with pytest.raises(analyze_bugs.AnalyzeBugsError):
            analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
        assert state_path.read_text(encoding="utf-8") == before
        assert not queue_path.exists()
        assert not validated_path.exists()

    # Refuter failures with queued findings present likewise leave durable state untouched.
    _prepare_sweep_run(run_dir, shas=(SWEEP_SHA_A,))
    finder_raw.write_text(
        _finder_jsonl([{"merge_sha": SWEEP_SHA_A, "findings": [_finding()]}]), encoding="utf-8"
    )
    analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
    refuter_raw = run_dir / analyze_bugs.SWEEP_REFUTER_RAW_NAME
    for content in (None, "\n", json.dumps({"merge_sha": SWEEP_SHA_A, "finding_index": 9, "verdict": "survives"}) + "\n"):
        if content is None:
            refuter_raw.unlink(missing_ok=True)
        else:
            refuter_raw.write_text(content, encoding="utf-8")
        validated_path.unlink(missing_ok=True)
        with pytest.raises(analyze_bugs.AnalyzeBugsError):
            analyze_bugs.sweep_ingest_refuter(run_dir=run_dir)
        assert state_path.read_text(encoding="utf-8") == before
        assert not validated_path.exists()


def test_ingest_finder_cli_fence_emits_kvs_and_nonzero_on_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run_dir = tmp_path / "run"
    _prepare_sweep_run(run_dir, shas=(SWEEP_SHA_A,))
    (run_dir / analyze_bugs.SWEEP_FINDER_RAW_NAME).write_text(
        _finder_jsonl([{"merge_sha": SWEEP_SHA_A, "findings": [_finding(), _finding(symbol="other")]}]),
        encoding="utf-8",
    )
    rc, kvs, err = _run_ingest("ingest-finder", run_dir, capsys)
    assert rc == 0
    assert err == ""
    assert kvs["INGEST_ACCEPTED"] == "1"
    assert kvs["REFUTER_QUEUE_COUNT"] == "2"
    assert kvs["PINNED_TIP"] == SWEEP_TIP
    assert Path(kvs["REFUTER_QUEUE_PATH"]).is_file()
    # A failed finder ingest returns non-zero and leaves no queue for the refuter to consume.
    (run_dir / analyze_bugs.SWEEP_FINDER_RAW_NAME).unlink()
    queue_path = run_dir / analyze_bugs.SWEEP_REFUTER_QUEUE_NAME
    queue_path.unlink(missing_ok=True)
    rc2, _kvs2, err2 = _run_ingest("ingest-finder", run_dir, capsys)
    assert rc2 == 1
    assert "ERROR:" in err2
    assert not queue_path.exists()
    rc3, _kvs3, _err3 = _run_ingest("ingest-refuter", run_dir, capsys)
    assert rc3 == 1


def test_ingest_refuter_cli_fence_emits_kvs_and_nonzero_on_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run_dir = tmp_path / "run"
    _refuter_setup(run_dir, findings=1)
    (run_dir / analyze_bugs.SWEEP_REFUTER_RAW_NAME).write_text(
        json.dumps({"merge_sha": SWEEP_SHA_A, "finding_index": 0, "verdict": "survives"}) + "\n", encoding="utf-8"
    )
    rc, kvs, err = _run_ingest("ingest-refuter", run_dir, capsys)
    assert rc == 0
    assert err == ""
    assert kvs["CANDIDATE_COUNT"] == "1"
    assert kvs["REFUTED_COUNT"] == "0"
    assert kvs["PINNED_TIP"] == SWEEP_TIP
    assert Path(kvs["SWEEP_VALIDATED_PATH"]).is_file()
    (run_dir / analyze_bugs.SWEEP_REFUTER_RAW_NAME).write_text(
        json.dumps({"merge_sha": SWEEP_SHA_A, "finding_index": 0, "verdict": "bogus"}) + "\n", encoding="utf-8"
    )
    rc2, _kvs2, err2 = _run_ingest("ingest-refuter", run_dir, capsys)
    assert rc2 == 1
    assert "ERROR:" in err2


def test_sweep_golden_transcript_wrong_key_survives(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _prepare_sweep_run(run_dir, shas=(SWEEP_SHA_A,))
    # Bundle plants a wrong-consumer-dict-key defect for the finder contract to catch.
    (run_dir / f"sweep-{SWEEP_SHA_A}-bundle.md").write_text(
        "# Sweep evidence bundle\n\n"
        "## First-parent diff\n```diff\n+rename: correct_key\n```\n\n"
        "## Consumers\n- python/larch/issue/consumer.py:5: value = registry['wrong_key']\n",
        encoding="utf-8",
    )
    (run_dir / analyze_bugs.SWEEP_FINDER_RAW_NAME).write_text(
        _finder_jsonl(
            [
                {
                    "merge_sha": SWEEP_SHA_A,
                    "findings": [
                        _finding(
                            file="python/larch/issue/consumer.py",
                            symbol="Consumer.lookup",
                            description="reads registry['wrong_key'] after the rename to correct_key",
                        )
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    finder_payload = analyze_bugs.sweep_ingest_finder(run_dir=run_dir)
    assert finder_payload["REFUTER_QUEUE_COUNT"] == 1
    assert "wrong_key" in (run_dir / analyze_bugs.SWEEP_REFUTER_QUEUE_NAME).read_text(encoding="utf-8")
    (run_dir / analyze_bugs.SWEEP_REFUTER_RAW_NAME).write_text(
        json.dumps({"merge_sha": SWEEP_SHA_A, "finding_index": 0, "verdict": "survives"}) + "\n", encoding="utf-8"
    )
    refuter_payload = analyze_bugs.sweep_ingest_refuter(run_dir=run_dir)
    assert refuter_payload["CANDIDATE_COUNT"] == 1
    validated = json.loads((run_dir / analyze_bugs.SWEEP_VALIDATED_NAME).read_text(encoding="utf-8"))
    candidate = validated["candidates"][0]
    assert candidate["file"] == "python/larch/issue/consumer.py"
    assert candidate["symbol"] == "Consumer.lookup"
    assert "wrong_key" in candidate["description"]


def test_sweep_bug_finder_agent_contract_pinned() -> None:
    root = Path(__file__).resolve().parents[3]
    agent_path = root / ".claude" / "agents" / "sweep-bug-finder.md"
    text = agent_path.read_text(encoding="utf-8")
    frontmatter = latc.extract_frontmatter(text)
    assert frontmatter is not None
    declaration = latc.parse_tools_declaration(frontmatter.text)
    assert declaration is not None
    assert declaration.explicit_list
    assert set(declaration.tools) == {"Read", "Grep", "Glob"}
    assert "model: sonnet" in frontmatter.text
    body = frontmatter.body
    # Strict finder and refuter JSONL schemas are pinned verbatim.
    assert '"merge_sha"' in body
    assert '"findings"' in body
    assert '"finding_index"' in body
    assert '"verdict"' in body
    assert '"survives|refuted"' in body
    assert '"high|medium|low"' in body
    # Read requirement, adversarial finder language, queue-row-only refuter handoff.
    assert latc.first_read_intent_line(body, body_start_line=frontmatter.body_start_line) is not None
    assert "planted" in body.lower()
    assert "disprove" in body.lower()
    assert "REFUTER_QUEUE_PATH" in body
    assert "exactly one" in body
    # Unreadable-evidence fail-closed fallback and the live lint stays clean.
    assert latc.has_fail_closed_language(body)
    assert not latc.scan_file(agent_path, root=root)
