# ruff: noqa: TC002,FLY002,FBT003
# pyright: reportUnusedCallResult=false, reportArgumentType=false
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import rejected_analysis as ra
import voting


def _started() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_implement_fixture(root: Path, *, run_id: str = "RUN-1", finding_id: str = "FINDING_1", json_id: str = "REJ_CR1_1", concern: str = "Missing required check", path: str = "python/foo.py:12", vote1: str = "YES", vote2: str = "NO", severity1: str = "major", scope: str = "") -> Path:
    run = root / "larch-logs" / "implement" / run_id
    round_dir = run / "round-1"
    round_dir.mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({"started_at": _started(), "skill": "implement"}), encoding="utf-8")
    (round_dir / "review-findings-full.jsonl").write_text(
        json.dumps(
            {
                "id": json_id,
                "phase": "code-review",
                "outcome": "rejected",
                "round_num": "1",
                "reviewer_slots": ["cursor-specialist"],
                "prose_body": f"### {finding_id}: {concern}\n- **Location**: {path}\n- **Concern**: {concern}\n",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    header = voting.CODE_REVIEW_FINDINGS_CLASSIFICATION_HEADER
    row = "\t".join(
        [
            finding_id,
            "cursor-specialist",
            "rejected",
            vote1,
            "true",
            severity1,
            "good",
            "false",
            "cursor-validity",
            vote2,
            "true",
            "minor",
            "good",
            "false",
            "codex-plan-fidelity",
            "NO",
            "true",
            "minor",
            "good",
            "false",
            "codex-pragmatism",
            scope,
        ]
    )
    (round_dir / "findings-classification.tsv").write_text(header + "\n" + row + "\n", encoding="utf-8")
    return run


def test_extractors_and_hash_are_stable_without_filesystem_probe(tmp_path: Path) -> None:
    prose = """### FINDING_7:   Missing   required check
- **File**: `python/foo.py:12-14`
- **Location**: `docs/other.md:9`
- **Concern**: Missing   required check
"""
    row = {"file": "", "location": ""}
    assert ra.extract_concern(prose, row) == "Missing required check"
    assert ra.extract_target_path(prose, row, tmp_path) == "python/foo.py"
    assert ra.extract_line_hint(prose, row, "python/foo.py") == "12"
    finding = ra.RejectedFinding(
        finding_hash="",
        concern_hash="",
        source_skill="implement",
        run_id="RUN-A",
        round_num="1",
        canonical_finding_id="FINDING_7",
        synthetic_id="REJ_CR1_7",
        reviewer_slots=("reviewer",),
        dissenting_slots=("v1",),
        file_path="python/foo.py",
        line_hint="12",
        concern="Missing required check",
        prose_body=prose,
        classification_row={},
        vote_split=ra.VoteSplit(1, 2, ("v1",), ("v2", "v3"), True),
        started_at=_started(),
    )
    first = ra.compute_finding_hash(finding)
    (tmp_path / "python").mkdir()
    (tmp_path / "python" / "foo.py").write_text("print('x')\n", encoding="utf-8")
    changed_metadata = ra.RejectedFinding(**{**finding.__dict__, "run_id": "RUN-B", "round_num": "3", "canonical_finding_id": "FINDING_99", "synthetic_id": "REJ_CR3_99", "line_hint": "14"})
    assert ra.compute_finding_hash(changed_metadata) == first


def test_prepare_keeps_one_yes_and_ledgers_zero_yes_oos_and_duplicates(tmp_path: Path) -> None:
    _write_implement_fixture(tmp_path, run_id="RUN-A", finding_id="FINDING_1", json_id="REJ_CR1_1", concern="Missing required check", path="python/foo.py:12")
    _write_implement_fixture(tmp_path, run_id="RUN-B", finding_id="FINDING_2", json_id="REJ_CR1_2", concern="Zero yes concern", path="python/bar.py:5", vote1="NO", vote2="NO")
    _write_implement_fixture(tmp_path, run_id="RUN-C", finding_id="OOS_1", json_id="OOS_1", concern="Deferred concern", path="python/oos.py:1", scope="oos")
    _write_implement_fixture(tmp_path, run_id="RUN-D", finding_id="FINDING_3", json_id="REJ_CR1_3", concern="Missing required check", path="python/foo.py:12", severity1="minor")
    result = ra.prepare(days=7, log_root=tmp_path / "larch-logs", work_dir=tmp_path / "work", repo_root=tmp_path, open_issues=[])
    assert result.verify_count == 1
    prompt = Path(result.candidates[0].prompt_path).read_text(encoding="utf-8")
    assert "Return one JSON object only" in prompt
    assert "python/foo.py" in prompt
    pending = result.ledger_pending_file.read_text(encoding="utf-8")
    assert "dismissed:zero-yes" in pending
    assert "dismissed:oos-deferred" in pending
    assert "dismissed:near-duplicate" in pending


def test_prepare_scans_review_layout_and_excludes_security(tmp_path: Path) -> None:
    run = tmp_path / "larch-logs" / "review" / "REV-1"
    run.mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({"started_at": _started()}), encoding="utf-8")
    (run / "review-findings.ndjson").write_text(
        json.dumps(
            {
                "id": "REJ_CR1_4",
                "phase": "code-review",
                "outcome": "rejected",
                "prose_body": "### FINDING_4: Credential exposure\n- **File**: python/secret.py:3\n- **Concern**: credential exposure leaks a token\n",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    header = voting.CODE_REVIEW_FINDINGS_CLASSIFICATION_HEADER
    row = "\t".join(["FINDING_4", "reviewer", "rejected", "YES", "true", "major", "good", "false", "cursor", "NO", "true", "minor", "good", "false", "codex", "NO", "true", "minor", "good", "false", "claude", ""])
    (run / "review-findings-classification-round-1.tsv").write_text(header + "\n" + row + "\n", encoding="utf-8")
    result = ra.prepare(days=7, log_root=tmp_path / "larch-logs", work_dir=tmp_path / "work", repo_root=tmp_path, open_issues=[])
    assert result.verify_count == 0
    assert "dismissed:security-sensitive" in result.ledger_pending_file.read_text(encoding="utf-8")


def test_ingest_finalize_and_record_confirmed_and_launch_failed_retryable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_implement_fixture(tmp_path)
    prep = ra.prepare(days=7, log_root=tmp_path / "larch-logs", work_dir=tmp_path / "work", repo_root=tmp_path, open_issues=[])
    candidate = prep.candidates[0]
    output = tmp_path / "work" / "verdict-C1.txt"
    output.write_text(json.dumps({"status": "confirmed", "current_location": "python/foo.py:13", "evidence": "Current code still omits the check."}), encoding="utf-8")
    Path(str(output) + ".dirty-tree").write_text("STATUS=clean\n", encoding="utf-8")
    result = ra.ingest_verdict(work_dir=prep.work_dir, candidate_id=candidate.candidate_id, output=output, launcher_exit=0)
    assert result.status == "ingested"
    final = ra.finalize(work_dir=prep.work_dir)
    assert final.confirmed_count == 1
    assert "Dissenting voter(s):" in final.issue_batch_file.read_text(encoding="utf-8")
    issue_stdout = tmp_path / "work" / "issue.stdout.txt"
    issue_stdout.write_text("ISSUES_CREATED=1\nISSUES_FAILED=0\nISSUES_DEDUPLICATED=0\nISSUE_1_NUMBER=123\nISSUE_1_URL=https://example.invalid/123\n", encoding="utf-8")
    record = ra.record(work_dir=prep.work_dir, issue_output=issue_stdout, issue_verified=True, repo_root=tmp_path)
    assert record.rc == 0
    ledger = (tmp_path / ra.LEDGER_PATH).read_text(encoding="utf-8")
    assert "filed-as" in ledger
    assert "123" in ledger


def test_ingest_status_launch_failed_is_not_ledgers_as_verification_failed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_implement_fixture(tmp_path)
    prep = ra.prepare(days=7, log_root=tmp_path / "larch-logs", work_dir=tmp_path / "work", repo_root=tmp_path, open_issues=[])
    candidate = prep.candidates[0]
    result = ra.ingest_verdict(work_dir=prep.work_dir, candidate_id=candidate.candidate_id, output=tmp_path / "missing.txt", launcher_exit=1)
    assert result.status == "launch-failed"
    final = ra.finalize(work_dir=prep.work_dir)
    assert final.launch_failures == 1
    record = ra.record(work_dir=prep.work_dir, launch_failures=1, repo_root=tmp_path)
    assert record.rc == 1
    ledger = (tmp_path / ra.LEDGER_PATH).read_text(encoding="utf-8")
    assert candidate.finding_hash not in ledger
    assert "dismissed:verification-failed" not in ledger


def test_record_partial_issue_failure_commits_safe_rows_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_implement_fixture(tmp_path, run_id="RUN-Z", finding_id="FINDING_9", json_id="REJ_CR1_9", concern="Zero yes", path="python/z.py:1", vote1="NO", vote2="NO")
    prep = ra.prepare(days=7, log_root=tmp_path / "larch-logs", work_dir=tmp_path / "work", repo_root=tmp_path, open_issues=[])
    final = ra.finalize(work_dir=prep.work_dir)
    assert final.confirmed_count == 0
    record = ra.record(work_dir=prep.work_dir, issue_verified=False, issues_failed=1, repo_root=tmp_path)
    assert record.rc == 1
    ledger = (tmp_path / ra.LEDGER_PATH).read_text(encoding="utf-8")
    assert "dismissed:zero-yes" in ledger
