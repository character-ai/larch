"""Fail-closed guard for finalize bash-parity collection."""

from __future__ import annotations

import shutil
from pathlib import Path


def test_finalize_bash_parity_module_only_skips_when_bash_absent() -> None:
    text = (Path(__file__).with_name("test_finalize_bash_parity.py")).read_text(
        encoding="utf-8",
    )
    if shutil.which("bash") is None:
        return
    assert 'shutil.which("bash") is None' in text
    assert "script unavailable" not in text
