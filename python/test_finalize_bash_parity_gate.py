"""Fail-closed guard for finalize bash-parity collection."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def test_finalize_bash_parity_collects_real_tests_when_bash_present() -> None:
    module = Path(__file__).with_name("test_finalize_bash_parity.py")
    if shutil.which("bash") is None:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", str(module)],
            check=False,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0
        assert "skipped" in (result.stdout + result.stderr).lower()
        return
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", str(module)],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0
    collected = result.stdout
    assert "test_postmerge_draft_status_matches_bash_subprocess" in collected
    assert "test_postbump_uses_rebase_without_changelog" in collected
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(module)],
        check=False,
        text=True,
        capture_output=True,
    )
    assert run.returncode == 0
    output = run.stdout + run.stderr
    assert " skipped" not in output
    passed = sum(1 for line in collected.splitlines() if line.startswith("test_"))
    assert passed >= 7
    assert f"{passed} passed" in output
