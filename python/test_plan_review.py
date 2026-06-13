from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import plan_review

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "python" / "cli.py"


def run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged["CLAUDE_PLUGIN_ROOT"] = str(ROOT)
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        env=merged,
        text=True,
        capture_output=True,
        check=False,
    )


def test_emit_plan_persists_diff_lines(tmp_path: Path) -> None:
    _ = (tmp_path / "plan.txt").write_text("## Plan\n\ndiff_lines: 42\n", encoding="utf-8")
    proc = run_cli("plan-review", "emit", "--design-tmpdir", str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    assert "EMIT_PLAN_STATUS=ok" in proc.stdout
    assert (tmp_path / "diff-lines.txt").read_text(encoding="utf-8") == "42\n"


def test_emit_plan_missing_diff_lines_fails(tmp_path: Path) -> None:
    _ = (tmp_path / "plan.txt").write_text("## Plan\n", encoding="utf-8")
    proc = run_cli("plan-review", "emit", "--design-tmpdir", str(tmp_path))
    assert proc.returncode == 1
    assert "EMIT_PLAN_STATUS=missing-diff-lines" in proc.stdout


def test_finalize_plan_creates_empty_artifacts_and_rejects_symlink(tmp_path: Path) -> None:
    _ = (tmp_path / "plan.txt").write_text("plan\n", encoding="utf-8")
    _ = (tmp_path / "diff-lines.txt").write_text("1\n", encoding="utf-8")
    proc = run_cli("plan-review", "finalize", "--design-tmpdir", str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    assert "FINALIZE_PLAN_STATUS=ok" in proc.stdout
    assert (tmp_path / "voting-tally.md").exists()

    (tmp_path / "voting-tally.md").unlink()
    _ = (tmp_path / "target").write_text("x", encoding="utf-8")
    (tmp_path / "voting-tally.md").symlink_to(tmp_path / "target")
    proc = run_cli("plan-review", "finalize", "--design-tmpdir", str(tmp_path))
    assert proc.returncode == 1
    assert "FINALIZE_PLAN_STATUS=invalid-artifact" in proc.stdout


def test_preview_large_plan_threshold_and_header(tmp_path: Path) -> None:
    body = "# Title\n" + "\n".join(f"## Section {i}" for i in range(3)) + "\n"
    _ = (tmp_path / "plan.txt").write_text(body, encoding="utf-8")
    proc = run_cli(
        "plan-review",
        "preview",
        "--design-tmpdir",
        str(tmp_path),
        "--variant",
        "step3",
        env={"LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD": "1"},
    )
    assert proc.returncode == 0
    assert "## Plan Candidate for Review" in proc.stdout
    assert "The plan is very large" in proc.stdout


def test_step3_state_non_numeric_round_count_falls_back_to_zero(tmp_path: Path) -> None:
    (tmp_path / ".step3-reentry").touch()
    _ = (tmp_path / "review-round-count.txt").write_text("not-a-number\n", encoding="utf-8")
    proc = run_cli(
        "plan-review",
        "step3-state",
        "--design-tmpdir",
        str(tmp_path),
        "--direct-review-entry",
    )
    assert proc.returncode == 0, proc.stderr
    assert "STEP3_STATE=direct-review-entry" in proc.stdout


def test_round_artifact_allowlist_and_drift_baseline(tmp_path: Path) -> None:
    assert plan_review.round_artifact_included("round-summary.env")
    assert not plan_review.round_artifact_included("debug.txt")
    assert plan_review.round_revise_artifact_excluded("codex-output.txt")
    assert plan_review.drift_baseline_write_once(tmp_path, "10", "20") == 0
    assert (tmp_path / "drift-baseline.env").read_text(encoding="utf-8") == (
        "BASELINE_PLAN_LINES=10\nBASELINE_DIFF_LINES=20\n"
    )
    assert plan_review.drift_baseline_write_once(tmp_path, "99", "99") == 0
    assert "99" not in (tmp_path / "drift-baseline.env").read_text(encoding="utf-8")


def test_record_report_evidence_writes_escalation_ledger(tmp_path: Path) -> None:
    proc = run_cli(
        "plan-review",
        "run",
        "--design-tmpdir",
        str(tmp_path),
        "--record-report-evidence",
        "tally-error",
    )
    assert proc.returncode == 0, proc.stderr
    ledger = tmp_path / "design-failure-escalation-ledger.tsv"
    assert ledger.exists()
    text = ledger.read_text(encoding="utf-8")
    assert "trigger=tally-error" in text
    assert "phase=validation" in text
