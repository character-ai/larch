"""Collection guard for former finalize parity tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_finalize_contract_module_collects_direct_python_tests() -> None:
    module = Path(__file__).with_name("test_finalize_bash_parity.py")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", str(module)],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0
    assert "test_postmerge_skip_decisions_match_former_shell_contract" in result.stdout
    assert "scripts/" not in module.read_text(encoding="utf-8")
