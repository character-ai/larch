"""Shared runner for retained review shell façades."""

from __future__ import annotations

import os
from pathlib import Path

import logging_util
import proc

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_LEGACY_DIR = Path(__file__).resolve().parent / "legacy_review_shell"


def run_review_shell(script_name: str, argv: list[str]) -> int:
    """Run a retained review shell façade and relay its contract stream."""
    logging_util.quiet_init(argv0=f"review-{script_name}")
    script = _LEGACY_DIR / script_name
    env = os.environ.copy()
    if not env.get("CLAUDE_PLUGIN_ROOT"):
        env["CLAUDE_PLUGIN_ROOT"] = str(_PLUGIN_ROOT)
    result = proc.run(["bash", str(script), *argv], cwd=str(Path.cwd()), env=env)
    for line in result.stdout.splitlines():
        logging_util.emit(line)
    if result.stderr:
        for line in result.stderr.splitlines():
            logging_util.diagnostic(line)
    return result.returncode
