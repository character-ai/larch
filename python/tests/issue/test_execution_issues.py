import json
from pathlib import Path

import pytest

from larch.issue import execution_issues


def test_append_execution_issue_idempotent(tmp_path: Path) -> None:
    log = tmp_path / "execution-issues.md"

    execution_issues.append_execution_issue(log, category="Warnings", entry="- warning")
    execution_issues.append_execution_issue(log, category="Warnings", entry="- warning")

    assert log.read_text(encoding="utf-8").count("- warning") == 1


def test_append_execution_issue_inserts_inside_existing_section(tmp_path: Path) -> None:
    log = tmp_path / "execution-issues.md"
    _ = log.write_text("### Tool Failures\n- old\n### Warnings\n- warn\n", encoding="utf-8")

    execution_issues.append_execution_issue(log, category="Tool Failures", entry="- new")
    execution_issues.append_execution_issue(log, category="Tool Failures", entry="- new")

    text = log.read_text(encoding="utf-8")
    assert text.index("- new") < text.index("### Warnings")
    assert text.count("- new") == 1


def test_append_execution_issue_rejects_symlink_log(tmp_path: Path) -> None:
    log = tmp_path / "execution-issues.md"
    target = tmp_path / "target.md"
    _ = target.write_text("", encoding="utf-8")
    log.symlink_to(target)

    with pytest.raises(OSError, match="non-regular log file"):
        execution_issues.append_execution_issue(log, category="Warnings", entry="- warning")


def test_resolve_execution_issue_removes_only_the_matching_live_entry(tmp_path: Path) -> None:
    log = tmp_path / "execution-issues.md"
    _ = log.write_text("### Tool Failures\n- one\n- two\n", encoding="utf-8")

    assert execution_issues.resolve_execution_issue(log, entry="- one") is True
    assert execution_issues.resolve_execution_issue(log, entry="- absent") is False
    assert log.read_text(encoding="utf-8") == "### Tool Failures\n- two\n"


def test_execution_issue_resolution_record_uses_the_entry_identity() -> None:
    record = json.loads(execution_issues.execution_issue_resolution_record(
        category="Tool Failures", entry="- transient", resolution="recovered",
    ))

    assert record["event"] == "resolved"
    assert record["issue_ids"] == [
        execution_issues.execution_issue_id(category="Tool Failures", body="- transient")
    ]


