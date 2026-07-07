"""Tests for Gate C accepted plan-review audit helpers."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

CLI = Path(__file__).resolve().parents[2] / "cli.py"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["LARCH_QUIET_DISABLE"] = "1"
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_snapshot_helper_writes_plan_before_review(tmp_path: Path) -> None:
    _ = (tmp_path / "plan.txt").write_text("initial plan\n", encoding="utf-8")
    result = run_cli("plan-review", "snapshot-pre-review", "--design-tmpdir", str(tmp_path))
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "plan-before-review.txt").read_text(encoding="utf-8") == "initial plan\n"


def test_snapshot_helper_overwrites_later_entry(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    _ = plan.write_text("first\n", encoding="utf-8")
    assert run_cli("plan-review", "snapshot-pre-review", "--design-tmpdir", str(tmp_path)).returncode == 0
    _ = plan.write_text("second\n", encoding="utf-8")
    assert run_cli("plan-review", "snapshot-pre-review", "--design-tmpdir", str(tmp_path)).returncode == 0
    assert (tmp_path / "plan-before-review.txt").read_text(encoding="utf-8") == "second\n"


def test_snapshot_helper_rejects_symlinked_plan(tmp_path: Path) -> None:
    real = tmp_path / "real-plan.txt"
    _ = real.write_text("plan\n", encoding="utf-8")
    (tmp_path / "plan.txt").symlink_to(real)
    result = run_cli("plan-review", "snapshot-pre-review", "--design-tmpdir", str(tmp_path))
    assert result.returncode != 0
    assert not (tmp_path / "plan-before-review.txt").exists()


def test_filter_helper_excludes_one_by_one_skipped_findings(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted-plan-findings-all.md"
    rejected = tmp_path / "rejected-findings.md"
    _ = accepted.write_text(
        "### FINDING_1: Keep\n"
        "- **Concern**: keep this\n"
        "\n"
        "### FINDING_2: Skip\n"
        "- **Concern**: skip this\n"
        "\n",
        encoding="utf-8",
    )
    _ = rejected.write_text(
        "### FINDING_2: Skip\n"
        "- **Concern**: skip this\n"
        "- **Reason not implemented**: rejected by user during one-by-one review\n"
        "\n",
        encoding="utf-8",
    )
    result = run_cli(
        "plan-review",
        "filter-gate-b-skipped",
        "--design-tmpdir",
        str(tmp_path),
        "--accepted",
        str(accepted),
        "--rejected",
        str(rejected),
    )
    assert result.returncode == 0, result.stderr
    assert "FINDING_1" in result.stdout
    assert "FINDING_2" not in result.stdout


def test_filter_helper_passes_through_without_skip_marker(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted-plan-findings-all.md"
    rejected = tmp_path / "rejected-findings.md"
    _ = accepted.write_text("### FINDING_1: Keep\n- **Concern**: keep this\n", encoding="utf-8")
    _ = rejected.write_text("### FINDING_2: Rejected\n- **Concern**: other\n", encoding="utf-8")
    result = run_cli(
        "plan-review",
        "filter-gate-b-skipped",
        "--design-tmpdir",
        str(tmp_path),
        "--accepted",
        str(accepted),
        "--rejected",
        str(rejected),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == accepted.read_text(encoding="utf-8")


def test_persist_helper_writes_clean_note(tmp_path: Path) -> None:
    result = run_cli(
        "plan-review",
        "persist-accepted-audit",
        "--design-tmpdir",
        str(tmp_path),
        "--assessment",
        "clean",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "ACCEPTED_AUDIT_STATUS=ok\n"
    assert (tmp_path / "accepted-plan-findings-audit.md").read_text(encoding="utf-8") == (
        "Accepted plan-review audit: no concerns.\n"
    )


def test_persist_helper_writes_normalized_sidecar_and_overwrites(tmp_path: Path) -> None:
    sidecar = tmp_path / "accepted-plan-findings-audit.input.sidecar"
    audit = tmp_path / "accepted-plan-findings-audit.md"
    _ = audit.write_text("stale\n", encoding="utf-8")
    _ = sidecar.write_text("mild-disagree: note", encoding="utf-8")
    result = run_cli(
        "plan-review",
        "persist-accepted-audit",
        "--design-tmpdir",
        str(tmp_path),
        "--assessment-file",
        str(sidecar),
    )
    assert result.returncode == 0, result.stderr
    assert audit.read_text(encoding="utf-8") == "mild-disagree: note\n"


def test_persist_helper_rejects_missing_sidecar(tmp_path: Path) -> None:
    result = run_cli(
        "plan-review",
        "persist-accepted-audit",
        "--design-tmpdir",
        str(tmp_path),
        "--assessment-file",
        str(tmp_path / "missing.sidecar"),
    )
    assert result.returncode != 0
    assert not (tmp_path / "accepted-plan-findings-audit.md").exists()


def test_persist_helper_rejects_empty_sidecar(tmp_path: Path) -> None:
    sidecar = tmp_path / "empty.sidecar"
    _ = sidecar.write_text("", encoding="utf-8")
    result = run_cli(
        "plan-review",
        "persist-accepted-audit",
        "--design-tmpdir",
        str(tmp_path),
        "--assessment-file",
        str(sidecar),
    )
    assert result.returncode != 0
    assert not (tmp_path / "accepted-plan-findings-audit.md").exists()


def test_persist_helper_rejects_symlink_sidecar(tmp_path: Path) -> None:
    real = tmp_path / "real.sidecar"
    sidecar = tmp_path / "sidecar"
    _ = real.write_text("audit\n", encoding="utf-8")
    sidecar.symlink_to(real)
    result = run_cli(
        "plan-review",
        "persist-accepted-audit",
        "--design-tmpdir",
        str(tmp_path),
        "--assessment-file",
        str(sidecar),
    )
    assert result.returncode != 0
    assert not (tmp_path / "accepted-plan-findings-audit.md").exists()
