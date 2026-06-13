from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "python" / "cli.py"


def test_compose_findings_empty_inputs_writes_jsonl(tmp_path: Path) -> None:
    impl = tmp_path / "impl"
    _ = impl.mkdir()
    output = tmp_path / "review-findings-full.jsonl"
    env = os.environ.copy()
    env["LARCH_QUIET_DISABLE"] = "1"

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "review",
            "compose-findings",
            "--implement-tmpdir",
            str(impl),
            "--issue",
            "0",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "COMPOSED=true" in result.stdout
    assert "MODE=jsonl" in result.stdout
    assert output.exists()
