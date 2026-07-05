"""Unit coverage for /design final-summary helpers, plus CLI-port smoke re-export."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest  # noqa: TC002

from larch.design import design_summary
from larch.design import design_lifecycle
from larch.report import progress_report
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


def test_failure_report_gate_uses_in_process_core(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_core(argv: list[str]) -> tuple[int, list[str]]:
        calls.append(list(argv))
        print("DESIGN_FAILURE_REPORT_DECISION=skip")
        return 0, []

    monkeypatch.setattr(design_lifecycle, "failure_report_core", fake_core)
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

    rc = design_summary.render_final_summary_main(["--outcome", "approved", "--repo", "o/r"])

    assert rc == 0
    body = (tmp_path / "final-summary.md").read_text(encoding="utf-8")
    stdout = capsys.readouterr().out
    assert "## Review Phase Detail" in body
    assert "| 1 | 4 | 2 | 1 | 0 | 1m 05s | N/A | 1 |" in body
    assert "### Round 1 reviewer timing" in body
    assert "```\n" in body
    assert "## Review Phase Detail" in stdout
    assert upsert_bodies
    assert "## Review Phase Detail" in upsert_bodies[0]


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
    assert "## Exec Issues and Warnings" in body
    assert "Exec Issues (1):" in body
    assert "Warnings (3):" in body
    assert "warn: duplicate \u00d72" in body
    assert "Assessment text." in body
    assert "fenced diagnostic hidden" not in body
    assert raw_secret not in body
    assert "<REDACTED-TOKEN>" in body
    assert "## Exec Issues and Warnings" in stdout
    assert upsert_bodies
    assert "Warnings (3):" in upsert_bodies[0]


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
    assert "| 1 | 4 | 2 | 2 | 1 | N/A | N/A | 1 |" in body
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


def test_difficulty_summary_line_prefers_record(tmp_path: Path) -> None:
    _ = (tmp_path / "difficulty-rating.json").write_text(
        '{"predicted_tier":"MODERATE","applied_tier":"HARD","floors_applied":[{"path":"hooks/x"}],"confidence":"medium"}\n',
        encoding="utf-8",
    )

    line = design_summary._difficulty_summary_line(tmp_path)  # pyright: ignore[reportPrivateUsage]

    assert line == "predicted MODERATE; applied HARD; floor raised"


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
