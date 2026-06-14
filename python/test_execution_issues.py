from pathlib import Path

import pytest

import execution_issues


def test_write_execution_issues_records_splits_sections(tmp_path: Path) -> None:
    issue_log = tmp_path / "execution-issues.md"
    _ = issue_log.write_text("### Tool Failures\n- one\n\n### Warnings\n- two\n", encoding="utf-8")
    record_file = tmp_path / "records.ndjson"

    count = execution_issues.write_execution_issues_records(issue_log, record_file, "abc", step_label="7a")

    assert count == 2
    text = record_file.read_text(encoding="utf-8")
    assert '"category":"Tool Failures"' in text
    assert '"category":"Warnings"' in text


def test_append_execution_issue_idempotent(tmp_path: Path) -> None:
    log = tmp_path / "execution-issues.md"

    execution_issues.append_execution_issue(log, category="Warnings", entry="- warning")
    execution_issues.append_execution_issue(log, category="Warnings", entry="- warning")

    assert log.read_text(encoding="utf-8").count("- warning") == 1


def test_flush_execution_issues_writes_sentinel_and_clears_log(tmp_path: Path) -> None:
    issue_log = tmp_path / "execution-issues.md"
    _ = issue_log.write_text("### Warnings\n- one\n", encoding="utf-8")
    log_root = tmp_path / "larch-logs"
    run_id = "run-1"

    rc, status, records, _append_log = execution_issues.flush_execution_issues(
        log_root=log_root,
        run_id=run_id,
        issue_log=issue_log,
    )

    assert rc == 0
    assert status in {"ok", "no-records"}
    assert records >= 0
    assert (tmp_path / ".execution-issues-step7a-reached").is_file()
    assert (tmp_path / ".execution-issues-flushed.sha").is_file()


def test_flush_execution_issues_idempotent_when_sentinel_matches(tmp_path: Path) -> None:
    issue_log = tmp_path / "execution-issues.md"
    _ = issue_log.write_text("### Warnings\n- one\n", encoding="utf-8")
    log_root = tmp_path / "larch-logs"
    run_id = "run-2"
    first = execution_issues.flush_execution_issues(log_root=log_root, run_id=run_id, issue_log=issue_log)
    _ = issue_log.write_text("### Warnings\n- one\n", encoding="utf-8")
    second = execution_issues.flush_execution_issues(log_root=log_root, run_id=run_id, issue_log=issue_log)

    assert first[0] == 0
    assert second[0] == 0
    assert second[1] == "already-flushed"
    assert issue_log.read_text(encoding="utf-8") == ""


def test_refresh_execution_issues_skips_when_issue_not_set(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _ = (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=0\nRUN_ID=run-2\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=owner/repo\n", encoding="utf-8")

    rc = execution_issues.refresh_execution_issues_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    out = capsys.readouterr().out
    assert "REFRESHED=true" in out
    assert "REASON=issue-not-set" in out


def test_flush_execution_issues_main_emits_kv_contract(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    issue_log = tmp_path / "execution-issues.md"
    _ = issue_log.write_text("### Warnings\n- one\n", encoding="utf-8")
    log_root = tmp_path / "larch-logs"

    rc = execution_issues.flush_execution_issues_main([
        "--log-root", str(log_root.resolve()),
        "--run-id", "run-3",
        "--issue-log", str(issue_log),
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "FLUSH_STATUS=" in out
    assert "RECORDS=" in out
