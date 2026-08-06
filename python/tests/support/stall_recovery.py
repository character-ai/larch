"""Test doubles for Rust-owned stall-recovery subprocess boundaries."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from larch import io as larch_io

_ROOT = Path(__file__).resolve().parents[3]
_REFERENCE = _ROOT / "fixtures" / "rust-parity" / "stall_recovery_reference.py"
_SUBPROCESS_RUN = subprocess.run


def frozen_normalized_outcome(
    _runner: object,
    *,
    implement_tmpdir: str,
    in_memory_stall_tracking: str = "",
) -> dict[str, str]:
    """Run the frozen pre-cutover normalizer as a Python-unit-test double."""
    argv = [
        sys.executable,
        str(_REFERENCE),
        "normalize-outcome",
        "--implement-tmpdir",
        implement_tmpdir,
    ]
    if in_memory_stall_tracking:
        argv.extend(["--in-memory-stall-tracking", in_memory_stall_tracking])
    result = _SUBPROCESS_RUN(argv, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(result.stderr or "frozen outcome normalizer failed")
    return larch_io.parse_kv(result.stdout, skip_empty_key=True)
