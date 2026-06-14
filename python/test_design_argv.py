"""Tests for the Python /design argv CLI bridge."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


CLI = Path(__file__).with_name("cli.py")


def test_design_parse_argv_cli_writes_sourceable_output(tmp_path: Path) -> None:
    output = tmp_path / "argv.env"
    result = subprocess.run(
        [sys.executable, str(CLI), "design", "parse-argv", "--output", str(output), "--brainstorm", "123"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    text = output.read_text(encoding="utf-8")
    assert "brainstorm_requested='true'" in text
    assert "POSITIONAL_KIND='issue'" in text
    assert "POSITIONAL_VALUE='123'" in text
