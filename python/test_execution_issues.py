from pathlib import Path

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
