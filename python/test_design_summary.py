"""Unit coverage for /design final-summary helpers, plus CLI-port smoke re-export."""

from __future__ import annotations

from pathlib import Path

import design_summary
from test_design_cli_ports import test_design_port_registry_entries_are_machine_stdout  # noqa: F401  # pylint: disable=unused-import  # pyright: ignore[reportUnusedImport]


def test_issue_counts_counts_h3_warnings(tmp_path: Path) -> None:
    issue_log = tmp_path / "execution-issues.md"
    _ = issue_log.write_text("### Warnings\n- **Step 2b.5**: plan-size check failed\n", encoding="utf-8")
    assert design_summary._issue_counts(tmp_path) == (0, 1)  # pyright: ignore[reportPrivateUsage]


def test_issue_counts_splits_exec_and_warnings(tmp_path: Path) -> None:
    issue_log = tmp_path / "execution-issues.md"
    _ = issue_log.write_text(
        "### Tool Failures\n- **gh**: timeout\n\n### Warnings\n- **lint**: drift\n",
        encoding="utf-8",
    )
    assert design_summary._issue_counts(tmp_path) == (1, 1)  # pyright: ignore[reportPrivateUsage]


def test_issue_counts_ignores_other_sections(tmp_path: Path) -> None:
    issue_log = tmp_path / "execution-issues.md"
    _ = issue_log.write_text("### Q/A\n- **q1**: answered\n", encoding="utf-8")
    assert design_summary._issue_counts(tmp_path) == (0, 0)  # pyright: ignore[reportPrivateUsage]


def test_issue_counts_missing_file(tmp_path: Path) -> None:
    assert design_summary._issue_counts(tmp_path) == (0, 0)  # pyright: ignore[reportPrivateUsage]


def test_plan_review_line_multiple_rounds(tmp_path: Path) -> None:
    _ = (tmp_path / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=complete\nROUNDS_COMPLETED=5\n", encoding="utf-8",
    )
    assert design_summary._plan_review_line(tmp_path) == "complete (5 rounds)"  # pyright: ignore[reportPrivateUsage]


def test_plan_review_line_single_round(tmp_path: Path) -> None:
    _ = (tmp_path / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=complete\nROUNDS_COMPLETED=1\n", encoding="utf-8",
    )
    assert design_summary._plan_review_line(tmp_path) == "complete (1 round)"  # pyright: ignore[reportPrivateUsage]


def test_plan_review_line_status_without_rounds(tmp_path: Path) -> None:
    _ = (tmp_path / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=panel-skipped\n", encoding="utf-8",
    )
    assert design_summary._plan_review_line(tmp_path) == "panel-skipped"  # pyright: ignore[reportPrivateUsage]


def test_plan_review_line_missing_env_is_na(tmp_path: Path) -> None:
    assert design_summary._plan_review_line(tmp_path) == "N/A"  # pyright: ignore[reportPrivateUsage]
