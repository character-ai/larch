from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "python" / "cli.py"


def test_aggregate_disabled_fast_path_preserves_findings(tmp_path: Path) -> None:
    findings = tmp_path / "findings.md"
    original = "### FINDING_1: keep me\n"
    _ = findings.write_text(original, encoding="utf-8")
    env = os.environ.copy()
    env["LARCH_QUIET_DISABLE"] = "1"
    env["LARCH_AGGREGATOR_DISABLED"] = "1"

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "review",
            "aggregate-findings",
            "--findings-file",
            str(findings),
            "--review-tmpdir",
            str(tmp_path),
            "--codex-present",
            "false",
            "--cursor-present",
            "false",
            "--mode",
            "description",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "AGGREGATED=false" in result.stdout
    assert "REASON=disabled" in result.stdout
    assert findings.read_text(encoding="utf-8") == original
