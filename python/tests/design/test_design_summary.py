"""Unit coverage for /design final-summary helpers, plus CLI-port smoke re-export."""

# pyright: reportUnusedCallResult=false, reportArgumentType=false

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from larch.core import config
from larch.design import design_summary
from larch.design import design_terminal
from larch.report import progress_report
from larch.report import report_tokens_cost
from test_design_cli_ports import test_design_port_registry_entries_are_machine_stdout  # noqa: F401  # pylint: disable=unused-import,import-error  # pyright: ignore[reportUnusedImport]


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


def test_oos_info_counts_file_map_rows(tmp_path: Path) -> None:
    sentinel = tmp_path / "oos-issues-created.md"
    _ = sentinel.write_text(
        "OOS_FILE_MAP\t1\thttps://github.com/example/repo/issues/1\n"
        "https://github.com/example/repo/issues/legacy\n"
        "OOS_FILE_MAP\t2\thttps://github.com/example/repo/issues/2  \n",
        encoding="utf-8",
    )
    assert design_summary._oos_info(tmp_path) == (  # pyright: ignore[reportPrivateUsage]
        2,
        "https://github.com/example/repo/issues/1\nhttps://github.com/example/repo/issues/2",
    )


def test_oos_info_missing_file(tmp_path: Path) -> None:
    assert design_summary._oos_info(tmp_path) == (0, "")  # pyright: ignore[reportPrivateUsage]


def test_oos_info_ignores_malformed_rows(tmp_path: Path) -> None:
    sentinel = tmp_path / "oos-issues-created.md"
    _ = sentinel.write_text(
        "\n"
        "OOS_FILE_MAP\t1\n"
        "OOS_FILE_MAP\t2\t   \n"
        "OOS_FILE_MAP\t3\thttps://github.com/example/repo/issues/3\n"
        "diagnostic OOS_FILE_MAP\t4\thttps://github.com/example/repo/issues/4\n",
        encoding="utf-8",
    )
    assert design_summary._oos_info(tmp_path) == (  # pyright: ignore[reportPrivateUsage]
        1,
        "https://github.com/example/repo/issues/3",
    )


def test_issue_counts_fence_plain_and_boundary_parity(tmp_path: Path) -> None:
    issue_log = tmp_path / "execution-issues.md"
    _ = issue_log.write_text(
        "### Tool Failures\n- exec1\n```\n- fenced ignored\n### Warnings\n- warn1\n",
        encoding="utf-8",
    )
    assert design_summary._issue_counts(tmp_path) == (1, 1)  # pyright: ignore[reportPrivateUsage]


def test_issue_counts_plain_warning_bullet(tmp_path: Path) -> None:
    issue_log = tmp_path / "execution-issues.md"
    _ = issue_log.write_text("### Warnings\n- plain warning\n", encoding="utf-8")
    assert design_summary._issue_counts(tmp_path) == (0, 1)  # pyright: ignore[reportPrivateUsage]


def test_plan_review_line_multiple_rounds(tmp_path: Path) -> None:
    _ = (tmp_path / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=complete\nROUNDS_COMPLETED=2\n", encoding="utf-8",
    )
    assert design_summary._plan_review_line(tmp_path) == "complete (2 rounds)"  # pyright: ignore[reportPrivateUsage]


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


def test_dynamic_archetypes_line_counts_drafter_manifest(tmp_path: Path) -> None:
    _ = (tmp_path / "step2b-drafter-status.txt").write_text("SCOUT_WRITTEN=true\n", encoding="utf-8")
    _ = (tmp_path / "scout-plan-manifest.json").write_text(
        '{"archetypes":[{"name":"dyn-plan","focus_area":"architecture","weight":1,"rationale":"Plan changed.","prompt_body":"Check plan structure."}]}\n',
        encoding="utf-8",
    )
    assert design_summary._dynamic_archetypes_line(tmp_path) == "ok (1)"  # pyright: ignore[reportPrivateUsage]


def test_dynamic_archetypes_line_reports_drafter_absent(tmp_path: Path) -> None:
    _ = (tmp_path / "step2b-drafter-status.txt").write_text("SCOUT_WRITTEN=false\nSCOUT_FAIL_REASON=absent\n", encoding="utf-8")
    assert design_summary._dynamic_archetypes_line(tmp_path) == "static-only, drafter absent"  # pyright: ignore[reportPrivateUsage]


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
                "## /design run design-run-1: approved\n\n"
                "- **Outcome**: ✅ DONE\n"
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

    def no_assess(_category: str, _details: tuple[design_summary.exec_issue_detail.IssueDetail, ...]) -> dict[str, str]:
        return {}

    monkeypatch.setattr(design_summary, "_run_cli", fake_run_cli)
    monkeypatch.setattr(design_summary, "_run_design_failure_report_gate", fake_run_design_failure_report_gate)
    monkeypatch.setattr(design_summary.exec_issue_detail, "assess_issue_details", no_assess)
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


def test_missing_invariant_assessment_warning_prefixes_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upsert_bodies = _install_final_summary_env(tmp_path, monkeypatch)
    (tmp_path / ".missing-invariant-assessment-warning").write_text("", encoding="utf-8")

    rc = design_summary.render_final_summary_main(
        [
            "--outcome",
            "approved",
            "--mode",
            "N/A",
            "--design-tmpdir",
            str(tmp_path),
            "--issue-number",
            "42",
            "--session-id",
            "design-run-1",
        ]
    )

    summary = (tmp_path / "final-summary.md").read_text(encoding="utf-8")
    assert rc == 0
    assert summary.startswith("**⚠ Missing architectural-invariant-assessment.md; Gate C assessment did not persist.**")
    assert upsert_bodies
    assert upsert_bodies[-1].startswith("**⚠ Missing architectural-invariant-assessment.md; Gate C assessment did not persist.**")


def test_missing_invariant_assessment_warning_prefixes_fallback_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("SESSION_ID", "design-run-1")
    (tmp_path / ".missing-invariant-assessment-warning").write_text("", encoding="utf-8")

    def fake_run_cli(*_args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["cli.py"], 1, stdout="", stderr="")

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

    rc = design_summary.render_final_summary_main(
        [
            "--outcome",
            "approved",
            "--mode",
            "N/A",
            "--design-tmpdir",
            str(tmp_path),
            "--issue-number",
            "42",
            "--session-id",
            "design-run-1",
            "--skip-summary-upsert",
        ]
    )

    summary = (tmp_path / "final-summary.md").read_text(encoding="utf-8")
    assert rc == 0
    assert summary.startswith("**⚠ Missing architectural-invariant-assessment.md; Gate C assessment did not persist.**")
    assert "Degraded fallback" in summary


def test_missing_assessment_warnings_prefix_both_once_in_invariant_first_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = _install_final_summary_env(tmp_path, monkeypatch)
    (tmp_path / ".missing-invariant-assessment-warning").write_text("", encoding="utf-8")
    (tmp_path / ".missing-guideline-assessment-warning").write_text("", encoding="utf-8")

    rc = design_summary.render_final_summary_main(
        [
            "--outcome",
            "approved",
            "--mode",
            "N/A",
            "--design-tmpdir",
            str(tmp_path),
            "--issue-number",
            "42",
            "--session-id",
            "design-run-1",
            "--skip-summary-upsert",
        ]
    )

    summary = (tmp_path / "final-summary.md").read_text(encoding="utf-8")
    invariant_warning = "**⚠ Missing architectural-invariant-assessment.md; Gate C assessment did not persist.**"
    guideline_warning = "**⚠ Missing architectural-guideline-assessment.md; Gate C assessment did not persist.**"
    assert rc == 0
    assert summary.index(invariant_warning) < summary.index(guideline_warning)
    assert summary.count(invariant_warning) == 1
    assert summary.count(guideline_warning) == 1


def test_missing_invariant_assessment_symlink_or_missing_marker_is_ignored(
    tmp_path: Path,
) -> None:
    out_file = tmp_path / "final-summary.md"
    out_file.write_text("body\n", encoding="utf-8")
    target = tmp_path / "target"
    target.write_text("", encoding="utf-8")
    (tmp_path / ".missing-invariant-assessment-warning").symlink_to(target)

    design_summary._prefix_missing_assessment_warnings(design_tmpdir=tmp_path, out_file=out_file)  # pyright: ignore[reportPrivateUsage]

    assert out_file.read_text(encoding="utf-8") == "body\n"


def test_missing_guideline_assessment_warning_prefixes_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upsert_bodies = _install_final_summary_env(tmp_path, monkeypatch)
    (tmp_path / ".missing-guideline-assessment-warning").write_text("", encoding="utf-8")

    rc = design_summary.render_final_summary_main(
        [
            "--outcome",
            "approved",
            "--mode",
            "N/A",
            "--design-tmpdir",
            str(tmp_path),
            "--issue-number",
            "42",
            "--session-id",
            "design-run-1",
        ]
    )

    summary = (tmp_path / "final-summary.md").read_text(encoding="utf-8")
    assert rc == 0
    assert summary.startswith("**⚠ Missing architectural-guideline-assessment.md; Gate C assessment did not persist.**")
    assert upsert_bodies
    assert upsert_bodies[-1].startswith("**⚠ Missing architectural-guideline-assessment.md; Gate C assessment did not persist.**")


def test_missing_guideline_assessment_warning_prefixes_fallback_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("SESSION_ID", "design-run-1")
    (tmp_path / ".missing-guideline-assessment-warning").write_text("", encoding="utf-8")

    def fake_run_cli(*_args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["cli.py"], 1, stdout="", stderr="")

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

    rc = design_summary.render_final_summary_main(
        [
            "--outcome",
            "approved",
            "--mode",
            "N/A",
            "--design-tmpdir",
            str(tmp_path),
            "--issue-number",
            "42",
            "--session-id",
            "design-run-1",
            "--skip-summary-upsert",
        ]
    )

    summary = (tmp_path / "final-summary.md").read_text(encoding="utf-8")
    assert rc == 0
    assert summary.startswith("**⚠ Missing architectural-guideline-assessment.md; Gate C assessment did not persist.**")
    assert "Degraded fallback" in summary


def test_guideline_exception_disclosure_prefixes_approved_summary_and_upsert(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upsert_bodies = _install_final_summary_env(tmp_path, monkeypatch)
    (tmp_path / "architectural-guideline-assessment.md").write_text(
        "Deviation on G-Py-4.\n"
        "Exception: pragmatic for this partition piece (author: main-agent, date: 2026-07-13)\n",
        encoding="utf-8",
    )

    rc = design_summary.render_final_summary_main(
        ["--outcome", "approved", "--design-tmpdir", str(tmp_path), "--issue-number", "42", "--session-id", "design-run-1"]
    )

    summary = (tmp_path / "final-summary.md").read_text(encoding="utf-8")
    assert rc == 0
    assert summary.startswith(
        "**Gate C guideline exception recorded:** pragmatic for this partition piece "
        "(author: main-agent, date: 2026-07-13)"
    )
    assert upsert_bodies
    assert upsert_bodies[-1].startswith("**Gate C guideline exception recorded:**")


def test_guideline_exception_disclosure_redacts_secret_rationale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upsert_bodies = _install_final_summary_env(tmp_path, monkeypatch)
    (tmp_path / "architectural-guideline-assessment.md").write_text(
        "Deviation on G-Py-4.\n"
        "Exception: pin token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 for CI (author: main-agent, date: 2026-07-13)\n",
        encoding="utf-8",
    )

    rc = design_summary.render_final_summary_main(
        ["--outcome", "approved", "--design-tmpdir", str(tmp_path), "--issue-number", "42", "--session-id", "design-run-1"]
    )

    summary = (tmp_path / "final-summary.md").read_text(encoding="utf-8")
    assert rc == 0
    assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" not in summary
    assert "<REDACTED-TOKEN>" in summary.splitlines()[0]
    assert upsert_bodies
    assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" not in upsert_bodies[-1]


@pytest.mark.parametrize(
    "note",
    [
        pytest.param("Deviation with no exception block.", id="missing"),
        pytest.param("Exception: see policy elsewhere", id="malformed"),
        pytest.param(
            "Deviation.\n```\nException: fenced (author: main-agent, date: 2026-07-13)\n```",
            id="fenced-only",
        ),
    ],
)
def test_guideline_exception_disclosure_omitted_for_invalid_notes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    note: str,
) -> None:
    _ = _install_final_summary_env(tmp_path, monkeypatch)
    (tmp_path / "architectural-guideline-assessment.md").write_text(note + "\n", encoding="utf-8")

    rc = design_summary.render_final_summary_main(
        ["--outcome", "approved", "--design-tmpdir", str(tmp_path), "--issue-number", "42", "--session-id", "design-run-1"]
    )

    summary = (tmp_path / "final-summary.md").read_text(encoding="utf-8")
    assert rc == 0
    assert "**Gate C guideline exception recorded:**" not in summary


def test_guideline_exception_disclosure_omitted_for_non_approved_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = _install_final_summary_env(tmp_path, monkeypatch)
    (tmp_path / "architectural-guideline-assessment.md").write_text(
        "Deviation on G-Py-4.\n"
        "Exception: pragmatic for this piece (author: main-agent, date: 2026-07-13)\n",
        encoding="utf-8",
    )

    rc = design_summary.render_final_summary_main(
        ["--outcome", "failed-plan-write", "--design-tmpdir", str(tmp_path), "--issue-number", "42", "--session-id", "design-run-1"]
    )

    summary = (tmp_path / "final-summary.md").read_text(encoding="utf-8")
    assert rc == 0
    assert "**Gate C guideline exception recorded:**" not in summary


def test_failure_report_gate_uses_in_process_core(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_core(argv: list[str]) -> tuple[int, list[str]]:
        calls.append(list(argv))
        print("DESIGN_FAILURE_REPORT_DECISION=skip")
        return 0, []

    monkeypatch.setattr(design_terminal, "failure_report_core", fake_core)
    design_summary._run_design_failure_report_gate(design_tmpdir=tmp_path, phase="post", outcome="approved", repo="o/r", issue="42", run_id="run-1")  # pyright: ignore[reportPrivateUsage]
    assert calls
    assert "--outcome" in calls[0]
    assert calls[0][calls[0].index("--outcome") + 1] == "approved"
    assert "DESIGN_FAILURE_REPORT_DECISION=skip" in (tmp_path / "design-failure-report.stdout.log").read_text(encoding="utf-8")
    assert (tmp_path / "design-failure-report.stderr.log").is_file()


def test_render_final_summary_appends_review_detail_to_stdout_and_upsert(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    upsert_bodies = _install_final_summary_env(tmp_path, monkeypatch)
    _write_design_round_fixture(tmp_path, with_timing=True)
    _ = (tmp_path / "execution-issues.md").write_text(
        "### Warnings\n- plan review warning\n",
        encoding="utf-8",
    )

    rc = design_summary.render_final_summary_main(["--outcome", "approved", "--repo", "o/r"])

    assert rc == 0
    body = (tmp_path / "final-summary.md").read_text(encoding="utf-8")
    stdout = capsys.readouterr().out
    assert "<!-- larch:run-summary v=1 -->" in body
    assert "## Review Phase Detail" in body
    assert "## Exec Issues and Warnings" in body
    assert body.index("## Review Phase Detail") < body.index("## Exec Issues and Warnings")
    assert body.index("## Exec Issues and Warnings") < body.index("<!-- larch:run-summary v=1 -->")
    assert "| 1 | 4 | 2 | 1 | 0 | 1m 05s | N/A | 1 |" in body
    assert "### Round 1 reviewer timing" in body
    assert "```\n" in body
    assert "<!-- larch:run-summary v=1 -->" in stdout
    assert "## Review Phase Detail" in stdout
    assert stdout.index("## Review Phase Detail") < stdout.index("## Exec Issues and Warnings")
    assert stdout.index("## Exec Issues and Warnings") < stdout.index("<!-- larch:run-summary v=1 -->")
    assert upsert_bodies
    assert "## Review Phase Detail" in upsert_bodies[0]
    assert upsert_bodies[0].index("## Review Phase Detail") < upsert_bodies[0].index("## Exec Issues and Warnings")
    assert upsert_bodies[0].index("## Exec Issues and Warnings") < upsert_bodies[0].index("<!-- larch:run-summary v=1 -->")


def test_render_final_summary_pre_phase_counts_without_detail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("SESSION_ID", "design-run-1")
    monkeypatch.setenv("ISSUE_NUMBER", "0")
    _ = (tmp_path / "execution-issues.md").write_text(
        "### Tool Failures\n- exec1\n\n### Warnings\n- warn1\n",
        encoding="utf-8",
    )
    render_args: list[tuple[str, ...]] = []

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        render_args.append(args)
        if args[:2] == ("render", "run-summary"):
            out_file = Path(args[args.index("--output-file") + 1])
            _ = out_file.write_text(
                "## /design run design-run-1: approved\n\n"
                f"- **Exec issues**: {args[args.index('--exec-issues') + 1]}\n"
                f"- **Warnings**: {args[args.index('--warnings') + 1]}\n",
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(["cli.py", *args], 0, stdout="", stderr="")

    def fake_gate(**_kw: object) -> None:
        return

    monkeypatch.setattr(design_summary, "_run_cli", fake_run_cli)
    monkeypatch.setattr(design_summary, "_run_design_failure_report_gate", fake_gate)

    rc = design_summary.render_final_summary_main(["--outcome", "approved", "--pre-publish-only"])

    assert rc == 0
    args = next(item for item in render_args if item[:2] == ("render", "run-summary"))
    assert args[args.index("--exec-issues") + 1] == "1"
    assert args[args.index("--warnings") + 1] == "1"
    body = (tmp_path / "final-summary.md").read_text(encoding="utf-8")
    assert "## Exec Issues and Warnings" not in body


def test_render_final_summary_appends_exec_warning_detail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    upsert_bodies = _install_final_summary_env(tmp_path, monkeypatch)
    raw_secret = "sk-" + "c" * 32
    _ = (tmp_path / "execution-issues.md").write_text(
        "### Tool Failures\n"
        "- **step**: failed\n"
        "```text\n- fenced diagnostic hidden\n```\n"
        "### Warnings\n"
        "- **warn**: duplicate\n"
        "- **warn**: duplicate\n"
        f"- **secret**: {raw_secret}\n",
        encoding="utf-8",
    )

    def fake_assess(_category: str, details: tuple[design_summary.exec_issue_detail.IssueDetail, ...]) -> dict[str, str]:
        return {str(index): "Assessment text." for index, _detail in enumerate(details)}

    monkeypatch.setattr(design_summary.exec_issue_detail, "assess_issue_details", fake_assess)

    rc = design_summary.render_final_summary_main(["--outcome", "approved", "--repo", "o/r"])

    assert rc == 0
    body = (tmp_path / "final-summary.md").read_text(encoding="utf-8")
    stdout = capsys.readouterr().out
    assert "<!-- larch:run-summary v=1 -->" in body
    assert "## Exec Issues and Warnings" in body
    assert body.index("## Exec Issues and Warnings") < body.index("<!-- larch:run-summary v=1 -->")
    assert "Exec Issues (1):" in body
    assert "Warnings (3):" in body
    assert "warn: duplicate \u00d72" in body
    assert "Assessment text." in body
    assert "fenced diagnostic hidden" not in body
    assert raw_secret not in body
    assert "<REDACTED-TOKEN>" in body
    assert "## Exec Issues and Warnings" in stdout
    assert stdout.index("## Exec Issues and Warnings") < stdout.index("<!-- larch:run-summary v=1 -->")
    assert upsert_bodies
    assert "Warnings (3):" in upsert_bodies[0]
    assert upsert_bodies[0].index("## Exec Issues and Warnings") < upsert_bodies[0].index("<!-- larch:run-summary v=1 -->")


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
    assert "| 1 | 4 | 2 | 1 | 0 | N/A | N/A | 1 |" in body
    assert "### Round 1 reviewer timing" not in body


def test_render_final_summary_explicit_identity_args_win_over_stale_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stale = tmp_path / "stale"
    explicit = tmp_path / "explicit"
    stale.mkdir()
    explicit.mkdir()
    monkeypatch.setenv("DESIGN_TMPDIR", str(stale))
    monkeypatch.setenv("SESSION_ID", "stale-run")
    monkeypatch.setenv("ISSUE_NUMBER", "1")
    gate_calls: list[tuple[Path, str, str]] = []
    run_summary_args: list[tuple[str, ...]] = []

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        run_summary_args.append(args)
        if args[:2] == ("render", "run-summary"):
            out_file = Path(args[args.index("--output-file") + 1])
            _ = out_file.write_text("summary\n<!-- larch:run-summary v=1 -->\n", encoding="utf-8")
        return subprocess.CompletedProcess(["cli.py", *args], 0, stdout="", stderr="")

    def fake_gate(
        *,
        design_tmpdir: Path,
        phase: str,
        outcome: str,
        repo: str,
        issue: str,
        run_id: str,
    ) -> None:
        _ = phase, outcome, repo
        gate_calls.append((design_tmpdir, issue, run_id))

    monkeypatch.setattr(design_summary, "_run_cli", fake_run_cli)
    monkeypatch.setattr(design_summary, "_run_design_failure_report_gate", fake_gate)

    rc = design_summary.render_final_summary_main([
        "--outcome",
        "approved",
        "--repo",
        "o/r",
        "--design-tmpdir",
        str(explicit),
        "--issue-number",
        "99",
        "--session-id",
        "explicit-run",
    ])

    assert rc == 0
    assert (explicit / "final-summary.md").is_file()
    assert not (stale / "final-summary.md").exists()
    assert gate_calls == [(explicit, "99", "explicit-run")]
    render_args = next(args for args in run_summary_args if args[:2] == ("render", "run-summary"))
    assert render_args[render_args.index("--issue-number") + 1] == "99"
    assert render_args[render_args.index("--run-id") + 1] == "explicit-run"


def test_render_final_summary_empty_identity_argv_does_not_fallback_to_ambient_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = _install_final_summary_env(tmp_path, monkeypatch, issue_number="0")
    monkeypatch.setenv("ISSUE_NUMBER", "999")
    monkeypatch.setenv("SESSION_ID", "stale-run")
    gate_calls: list[tuple[str, str]] = []
    run_summary_args: list[tuple[str, ...]] = []

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        run_summary_args.append(args)
        if args[:2] == ("render", "run-summary"):
            out_file = Path(args[args.index("--output-file") + 1])
            _ = out_file.write_text("summary\n<!-- larch:run-summary v=1 -->\n", encoding="utf-8")
        return subprocess.CompletedProcess(["cli.py", *args], 0, stdout="", stderr="")

    def fake_gate(
        *,
        design_tmpdir: Path,
        phase: str,
        outcome: str,
        repo: str,
        issue: str,
        run_id: str,
    ) -> None:
        _ = design_tmpdir, phase, outcome, repo
        gate_calls.append((issue, run_id))

    monkeypatch.setattr(design_summary, "_run_cli", fake_run_cli)
    monkeypatch.setattr(design_summary, "_run_design_failure_report_gate", fake_gate)

    rc = design_summary.render_final_summary_main([
        "--outcome",
        "approved",
        "--issue-number",
        "",
        "--session-id",
        "",
    ])

    assert rc == 0
    assert gate_calls == [("", "unknown")]
    render_args = next(args for args in run_summary_args if args[:2] == ("render", "run-summary"))
    assert render_args[render_args.index("--run-id") + 1] == "unknown"
    assert render_args[render_args.index("--run-logs-path") + 1] == "N/A"


def test_published_run_logs_path_requires_completed_log_publication(tmp_path: Path) -> None:
    assert design_summary._published_run_logs_path(design_tmpdir=tmp_path, run_id="run-1") == "N/A"  # pyright: ignore[reportPrivateUsage]
    result = tmp_path / ".design-publish-result.env"
    _ = result.write_text("LOG_PUBLISH_COMPLETED=false\n", encoding="utf-8")
    assert design_summary._published_run_logs_path(design_tmpdir=tmp_path, run_id="run-1") == "N/A"  # pyright: ignore[reportPrivateUsage]
    repo = tmp_path / "repo"
    (repo / ".larch").mkdir(parents=True)
    _ = (repo / ".larch" / "config.toml").write_text('[logs]\nuri = "s3://bucket/root"\n', encoding="utf-8")
    _ = (tmp_path / "source-env.sh").write_text(f"REPO_ROOT={repo}\n", encoding="utf-8")
    _ = result.write_text("LOG_PUBLISH_COMPLETED=true\n", encoding="utf-8")
    assert design_summary._published_run_logs_path(design_tmpdir=tmp_path, run_id="run-1") == "provider `s3`, skill `design`, run ID `run-1`"  # pyright: ignore[reportPrivateUsage]


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


def test_render_final_summary_degraded_fallback_includes_issue_count_bullets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("SESSION_ID", "design-run-1")
    monkeypatch.setenv("ISSUE_NUMBER", "0")
    _ = (tmp_path / "execution-issues.md").write_text(
        "### Tool Failures\n- exec1\n\n### Warnings\n- warn1\n- warn2\n",
        encoding="utf-8",
    )

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("render", "run-summary"):
            return subprocess.CompletedProcess(["cli.py", *args], 1, stdout="", stderr="renderer failed")
        return subprocess.CompletedProcess(["cli.py", *args], 0, stdout="", stderr="")

    def fake_gate(**_kw: object) -> None:
        return

    def no_assess(_category: str, _details: tuple[design_summary.exec_issue_detail.IssueDetail, ...]) -> dict[str, str]:
        return {}

    monkeypatch.setattr(design_summary, "_run_cli", fake_run_cli)
    monkeypatch.setattr(design_summary, "_run_design_failure_report_gate", fake_gate)
    monkeypatch.setattr(design_summary.exec_issue_detail, "assess_issue_details", no_assess)

    rc = design_summary.render_final_summary_main(["--outcome", "approved"])

    assert rc == 0
    body = (tmp_path / "final-summary.md").read_text(encoding="utf-8")
    assert "- **Outcome**: ✅ DONE" in body
    assert "- **Exec issues**: 1" in body
    assert "- **Warnings**: 2" in body
    assert "## Exec Issues and Warnings" in body
    assert "Exec Issues (1):" in body
    assert "Warnings (2):" in body


def test_render_final_summary_write_failure_skips_upsert(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upsert_calls: list[tuple[str, ...]] = []
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("SESSION_ID", "design-run-1")
    monkeypatch.setenv("ISSUE_NUMBER", "42")

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("render", "run-summary"):
            out_file = Path(args[args.index("--output-file") + 1])
            _ = out_file.write_text("## summary\n", encoding="utf-8")
            out_file.chmod(0o444)
        elif args[:2] == ("tracking-issue", "upsert-summary"):
            upsert_calls.append(args)
        return subprocess.CompletedProcess(["cli.py", *args], 0, stdout="", stderr="")

    def fake_gate(**_kw: object) -> None:
        return

    monkeypatch.setattr(design_summary, "_run_cli", fake_run_cli)
    monkeypatch.setattr(design_summary, "_run_design_failure_report_gate", fake_gate)

    rc = design_summary.render_final_summary_main(["--outcome", "approved", "--repo", "o/r"])

    assert rc == 1
    assert not upsert_calls


def test_render_final_summary_write_failure_rebuilds_fallback_with_detail_first(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("SESSION_ID", "design-run-1")
    monkeypatch.setenv("ISSUE_NUMBER", "42")
    _ = (tmp_path / "execution-issues.md").write_text(
        "### Warnings\n- warn1\n",
        encoding="utf-8",
    )

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("render", "run-summary"):
            out_file = Path(args[args.index("--output-file") + 1])
            with out_file.open("w", encoding="utf-8") as fh:
                _ = fh.write("## /design run design-run-1: approved\n\n")
                _ = fh.write("- **Outcome**: ✅ DONE\n")
                _ = fh.write("<!-- larch:run-summary v=1 -->\n")
        return subprocess.CompletedProcess(["cli.py", *args], 0, stdout="", stderr="")

    def fake_gate(**_kw: object) -> None:
        return

    def fake_render_design_review_detail(_design_tmpdir: Path) -> str:
        return "## Review Phase Detail\n- recovered review\n"

    original_write_text = Path.write_text
    write_calls = 0

    def flaky_write_text(self: Path, *args: object, **kwargs: object) -> int:
        nonlocal write_calls
        if self == tmp_path / "final-summary.md" and write_calls == 0:
            write_calls += 1
            raise OSError("simulated write failure")
        return original_write_text(self, *args, **kwargs)  # type: ignore[reportArgumentType]

    monkeypatch.setattr(design_summary, "_run_cli", fake_run_cli)
    monkeypatch.setattr(design_summary, "_run_design_failure_report_gate", fake_gate)
    monkeypatch.setattr(design_summary.review_phase_detail, "render_design_review_detail", fake_render_design_review_detail)
    monkeypatch.setattr(design_summary.Path, "write_text", flaky_write_text)

    rc = design_summary.render_final_summary_main(["--outcome", "approved", "--repo", "o/r"])

    assert rc == 1
    assert write_calls == 1
    body = (tmp_path / "final-summary.md").read_text(encoding="utf-8")
    assert body.index("## Review Phase Detail") < body.index("## Exec Issues and Warnings")
    assert body.index("## Exec Issues and Warnings") < body.index("## /design run design-run-1: approved")
    assert body.index("## /design run design-run-1: approved") < body.index("<!-- larch:run-summary v=1 -->")


def test_difficulty_summary_line_prefers_record(tmp_path: Path) -> None:
    _ = (tmp_path / "difficulty-rating.json").write_text(
        '{"predicted_tier":"MODERATE","applied_tier":"HARD","floors_applied":[{"path":"hooks/x"}],"confidence":"medium"}\n',
        encoding="utf-8",
    )

    line = design_summary._difficulty_summary_line(tmp_path)  # pyright: ignore[reportPrivateUsage]

    assert line == "predicted MODERATE; applied HARD; floor raised"


def test_read_token_report_splits_cursor_grok_from_composer(tmp_path: Path) -> None:
    """/design prices cursor grok tokens at grok rates, not composer (issue #7257)."""
    report = {
        "cursor": {"totals": {"total": 6180000}},
        "BUCKETS_cursor": {"input": 150000, "cache_read": 6000000, "output": 30000, "total": 6180000},
        "BUCKETS_cursor_by_model": {
            config.CURSOR_DEFAULT_MODEL: {"input": 100000, "cache_read": 4000000, "output": 20000, "total": 4120000},
            config.CURSOR_GROK_4_5_HIGH_MODEL: {"input": 50000, "cache_read": 2000000, "output": 10000, "total": 2060000},
        },
    }
    _ = (tmp_path / "token-report-final.json").write_text(json.dumps(report), encoding="utf-8")

    buckets = design_summary._read_token_report(tmp_path)  # pyright: ignore[reportPrivateUsage]

    # Composer lane keeps only the composer-2.5 counts; grok routes to its own lane.
    assert (buckets["U_IN"], buckets["U_CR"], buckets["U_OUT"]) == (100000, 4000000, 20000)
    assert (buckets["U_GROK_IN"], buckets["U_GROK_CR"], buckets["U_GROK_OUT"]) == (50000, 2000000, 10000)

    cost_args = design_summary._build_cost_args(buckets)  # pyright: ignore[reportPrivateUsage]
    assert "--cursor-grok-cache-read-tokens" in cost_args
    assert cost_args[cost_args.index("--cursor-grok-cache-read-tokens") + 1] == "2000000"

    # Grok cache read prices at $0.50/M (grok), not $0.45/M (composer): 2M -> $1.00,
    # plus 50k input * $2.00/M + 10k output * $6.00/M = $1.16.
    cost_kv = report_tokens_cost.token_cost_from_args(cost_args)
    assert "CURSOR_GROK_COST=1.16" in cost_kv.splitlines()


def test_render_final_summary_persists_difficulty_record_before_render(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("SESSION_ID", "design-run-1")
    monkeypatch.setenv("ISSUE_NUMBER", "0")
    _ = (tmp_path / "composed-plan.md").write_text(
        "## Plan\nbody\n\ndifficulty: MODERATE\ndiff_lines: 1\n",
        encoding="utf-8",
    )
    calls: list[tuple[str, ...]] = []

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[:2] == ("render", "run-summary"):
            out_file = Path(args[args.index("--output-file") + 1])
            _ = out_file.write_text(
                "## /design run design-run-1: approved\n\n<!-- larch:run-summary v=1 -->\n",
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(["cli.py", *args], 0, stdout="", stderr="")

    monkeypatch.setattr(design_summary, "_run_cli", fake_run_cli)
    def fake_gate(**_kw: object) -> None:
        return None

    monkeypatch.setattr(design_summary, "_run_design_failure_report_gate", fake_gate)

    rc = design_summary.render_final_summary_main(["--outcome", "approved"])

    assert rc == 0
    assert (tmp_path / "difficulty-rating.json").is_file()
    assert any(args[:2] == ("run-log", "write") for args in calls)


def test_final_summary_request_skips_upsert_and_forces_post_phase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_render(argv: list[str]) -> int:
        calls.append(argv)
        _ = (tmp_path / "final-summary.md").write_text("enriched\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)

    ok = design_summary.render_final_summary_for_request(
        design_summary.FinalSummaryRenderRequest(
            design_tmpdir=tmp_path,
            outcome="approved",
            mode="design",
            issue_number="42",
            session_id="RUN1",
            repo="owner/repo",
            upsert_summary_comment=False,
            stdout_log_path=tmp_path / "summary.stdout.log",
        )
    )

    assert ok
    assert calls == [
        [
            "--outcome",
            "approved",
            "--mode",
            "design",
            "--design-tmpdir",
            str(tmp_path),
            "--issue-number",
            "42",
            "--session-id",
            "RUN1",
            "--post-publish-only",
            "--repo",
            "owner/repo",
            "--skip-summary-upsert",
        ]
    ]
    assert "--pre-publish-only" not in calls[0]
    assert (tmp_path / "final-summary.md").read_text(encoding="utf-8") == "enriched\n"


def test_final_summary_request_unlinks_stale_file_on_failed_render(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stale = tmp_path / "final-summary.md"
    _ = stale.write_text("stale\n", encoding="utf-8")

    def fake_render(_argv: list[str]) -> int:
        assert not stale.exists()
        _ = stale.write_text("partial\n", encoding="utf-8")
        return 1

    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)

    ok = design_summary.render_final_summary_for_request(
        design_summary.FinalSummaryRenderRequest(
            design_tmpdir=tmp_path,
            outcome="approved",
            mode="N/A",
            issue_number="0",
            session_id="RUN1",
            repo="",
            upsert_summary_comment=True,
            stdout_log_path=tmp_path / "summary.stdout.log",
        )
    )

    assert not ok
    assert not stale.exists()


def test_render_final_summary_accepts_paused_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("SESSION_ID", "RUN1")
    monkeypatch.setenv("ISSUE_NUMBER", "0")

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("render", "run-summary"):
            out_file = Path(args[args.index("--output-file") + 1])
            _ = out_file.write_text("## paused\n", encoding="utf-8")
        return subprocess.CompletedProcess(["cli.py", *args], 0, stdout="", stderr="")

    def fake_gate(**_kw: object) -> None:
        return

    monkeypatch.setattr(design_summary, "_run_cli", fake_run_cli)
    monkeypatch.setattr(design_summary, "_run_design_failure_report_gate", fake_gate)

    assert design_summary.render_final_summary_main(["--outcome", "paused"]) == 0
