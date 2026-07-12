# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnusedCallResult=false
"""Offline tests for analyze_bugs.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from larch.core.proc import CommandResult
from larch.issue import analyze_bugs
from test_support import RecordingRunner, run_cli

_marker_evidence = analyze_bugs._marker_evidence  # pyright: ignore[reportPrivateUsage]  # direct pure-helper coverage
_bundle_from_mapping = analyze_bugs._bundle_from_mapping  # pyright: ignore[reportPrivateUsage]  # fixture construction
_priority_deep_candidates = analyze_bugs._priority_deep_candidates  # pyright: ignore[reportPrivateUsage]  # routing coverage


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


def test_fetch_filters_bug_prefix_and_uses_paginated_gh_api() -> None:
    page1 = [_issue(number, f"refactor {number}", body="body") for number in range(1, 101)]
    page1[0]["pull_request"] = {"url": "https://github.com/o/r/pull/1"}
    page2 = [_issue(number, f"refactor {number}", state="CLOSED", reason="COMPLETED") for number in range(101, 200)]
    page2.append(_issue(200, "[BUG] newest", state="CLOSED", reason="COMPLETED"))
    runner = RecordingRunner(responses=[_result(json.dumps(page1) + json.dumps(page2))], strict=True)

    selected, _corpus = analyze_bugs.fetch_bug_issues(runner, repo="o/r", count=1)

    assert [issue.number for issue in selected] == [200]
    assert runner.calls == [["gh", "api", "--paginate", "repos/o/r/issues?state=all&per_page=100"]]


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
