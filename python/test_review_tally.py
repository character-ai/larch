from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "python" / "cli.py"


def run_review(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["LARCH_QUIET_DISABLE"] = "1"
    return subprocess.run(
        [sys.executable, str(CLI), "review", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_emit_tally_writes_summary_json(tmp_path: Path) -> None:
    tally = tmp_path / "review-tally.env"
    _ = tally.write_text("ACCEPTED_COUNT=0\nREJECTED_COUNT=0\nNEUTRAL_COUNT=0\n", encoding="utf-8")
    accepted = tmp_path / "accepted-findings.md"
    _ = accepted.write_text("", encoding="utf-8")
    oos = tmp_path / "oos.md"
    _ = oos.write_text("", encoding="utf-8")

    result = run_review(
        "emit-tally",
        "--tally-file",
        str(tally),
        "--accepted-findings-file",
        str(accepted),
        "--oos-file",
        str(oos),
        "--review-tmpdir",
        str(tmp_path),
        "--round",
        "1",
        "--mode",
        "description",
    )

    assert result.returncode == 0, result.stderr
    assert "REVIEW_SUMMARY_FILE=" in result.stdout
    assert (tmp_path / "review-summary.json").exists()


def test_log_phase_rejects_unknown_batch(tmp_path: Path) -> None:
    payload = tmp_path / "payload.txt"
    _ = payload.write_text("payload\n", encoding="utf-8")

    result = run_review(
        "log-phase",
        "--run-id",
        "run-1",
        "--batch",
        "unknown",
        "--action",
        "write",
        "--payload-file",
        str(payload),
        "--log-root",
        str(tmp_path / "logs"),
    )

    assert result.returncode == 2
    assert "unregistered review batch" in result.stderr
