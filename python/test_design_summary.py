"""Unit coverage for /design final-summary helpers, plus CLI-port smoke re-export."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest  # noqa: TC002

import design_summary
import progress_report
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


def _install_final_summary_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    issue_number: str = "42",
) -> list[str]:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("SESSION_ID", "design-run-1")
    monkeypatch.setenv("ISSUE_NUMBER", issue_number)
    upsert_bodies: list[str] = []

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("render", "run-summary"):
            out_file = Path(args[args.index("--output-file") + 1])
            _ = out_file.write_text(
                "## /design run design-run-1 — approved\n\n"
                "- **Outcome**: approved\n"
                "<!-- larch:run-summary v=1 -->\n",
                encoding="utf-8",
            )
        elif args[:2] == ("tracking-issue", "upsert-summary"):
            content_file = Path(args[args.index("--content-file") + 1])
            upsert_bodies.append(content_file.read_text(encoding="utf-8"))
        return subprocess.CompletedProcess(["cli.py", *args], 0, stdout="", stderr="")

    def fake_run_design_failure_report_gate(
        design_tmpdir: Path,
        phase: str,
        outcome: str,
        repo: str,
        issue: str,
        run_id: str,
    ) -> None:
        _ = (design_tmpdir, phase, outcome, repo, issue, run_id)

    monkeypatch.setattr(design_summary, "_run_cli", fake_run_cli)
    monkeypatch.setattr(design_summary, "_run_design_failure_report_gate", fake_run_design_failure_report_gate)
    return upsert_bodies


def _write_design_round_fixture(tmp_path: Path, *, with_timing: bool) -> None:
    round_dir = tmp_path / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    _ = (round_dir / "round-meta.json").write_text(
        '{"tally":{"ACCEPTED_COUNT":"2","REJECTED_COUNT":"1","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"1","OOS_ACCEPTED_COUNT":"1","OOS_REJECTED_COUNT":"1"},"summary":{"panel":{"total_slot_count":1}},"collector":"TOOL=unknown\\nSTATUS=FAILED\\nREVIEWER_FILE=collector-failure-1.txt\\n"}\n',
        encoding="utf-8",
    )
    _ = (round_dir / "panel-manifest.ndjson").write_text(
        '{"slot":"claude-plan-generic","tool":"claude_sub","output":"/t/design/claude-plan-generic-output.txt"}\n',
        encoding="utf-8",
    )
    _ = (tmp_path / "review-findings-full.jsonl").write_text(
        '{"id":"FINDING_D1","outcome":"accepted","reviewer_slots":["claude-plan-generic-output.txt"],"round_num":""}\n'
        '{"id":"FINDING_D2","outcome":"accepted","reviewer_slots":["claude-plan-generic-output.txt"],"round_num":""}\n',
        encoding="utf-8",
    )
    if with_timing:
        _ = (tmp_path / "timing-ledger.tsv").write_text(
            "v1\tround\t1700000000\tdesign\tdesign Step 3 — plan review\t1\t1700000000\t1700000065\t65\t2\t1\t1\t-\n"
            "v1\tvendor\t1700000010\timplement\t-\tclaude\treview\t1700000010\t1700000060\t50\tclaude-plan-generic-output.txt\t0\tcomplete\n",
            encoding="utf-8",
        )


def test_render_final_summary_appends_review_detail_to_stdout_and_upsert(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    upsert_bodies = _install_final_summary_env(tmp_path, monkeypatch)
    _write_design_round_fixture(tmp_path, with_timing=True)

    rc = design_summary.render_final_summary_main(["--outcome", "approved", "--repo", "o/r"])

    assert rc == 0
    body = (tmp_path / "final-summary.md").read_text(encoding="utf-8")
    stdout = capsys.readouterr().out
    assert "## Review Phase Detail" in body
    assert "| 1 | 4 | 2 | 2 | 1 | 1m 05s | — | 1 |" in body
    assert "### Round 1 reviewer timing" in body
    assert "```\n" in body
    assert "## Review Phase Detail" in stdout
    assert upsert_bodies
    assert "## Review Phase Detail" in upsert_bodies[0]


def test_render_final_summary_missing_timing_keeps_table_without_gantt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = _install_final_summary_env(tmp_path, monkeypatch, issue_number="0")
    _write_design_round_fixture(tmp_path, with_timing=False)

    rc = design_summary.render_final_summary_main(["--outcome", "approved"])

    assert rc == 0
    body = (tmp_path / "final-summary.md").read_text(encoding="utf-8")
    assert "## Review Phase Detail" in body
    assert "| 1 | 4 | 2 | 2 | 1 | — | — | 1 |" in body
    assert "### Round 1 reviewer timing" not in body


def test_render_final_summary_redacts_spliced_detail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = _install_final_summary_env(tmp_path, monkeypatch, issue_number="0")
    (tmp_path / "plan-review").mkdir()
    raw_secret = "sk-" + "a" * 32

    def fake_render(*_args: object, **_kwargs: object) -> str:
        return f"## Review Phase Detail\n{raw_secret}\n"

    monkeypatch.setattr(progress_report, "_render_phase_detail_best_effort", fake_render)

    rc = design_summary.render_final_summary_main(["--outcome", "approved"])

    assert rc == 0
    body = (tmp_path / "final-summary.md").read_text(encoding="utf-8")
    assert raw_secret not in body
    assert "<REDACTED-TOKEN>" in body


def test_render_final_summary_swallows_renderer_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = _install_final_summary_env(tmp_path, monkeypatch, issue_number="0")
    (tmp_path / "plan-review").mkdir()

    def fake_render(*_args: object, **_kwargs: object) -> str:
        return ""

    monkeypatch.setattr(progress_report, "_render_phase_detail_best_effort", fake_render)

    rc = design_summary.render_final_summary_main(["--outcome", "approved"])

    assert rc == 0
    body = (tmp_path / "final-summary.md").read_text(encoding="utf-8")
    assert "<!-- larch:run-summary v=1 -->" in body
    assert "## Review Phase Detail" not in body
