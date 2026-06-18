"""Collection guard for former finalize parity tests."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from pytest_sharding import ENV_SHARD_COUNT, ENV_SHARD_ID


def _subprocess_env() -> dict[str, str]:
    """Drop CI shard assignment so nested pytest collects the full module."""
    env = os.environ.copy()
    _ = env.pop(ENV_SHARD_ID, None)
    _ = env.pop(ENV_SHARD_COUNT, None)
    return env


def test_finalize_contract_module_collects_direct_python_tests() -> None:
    module = Path(__file__).with_name("test_finalize_bash_parity.py")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", str(module)],
        check=False,
        text=True,
        capture_output=True,
        env=_subprocess_env(),
    )
    assert result.returncode == 0
    assert "test_postmerge_skip_decisions_match_former_shell_contract" in result.stdout
    assert "scripts/" not in module.read_text(encoding="utf-8")
