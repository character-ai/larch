"""Python CLI entrypoint for /design post-plan emission.

Ports skills/design/scripts/design-postplan-emit.sh.
Reads BASELINE_PLAN_LINES and BASELINE_DIFF_LINES from drift-baseline.env
to compute the DRIFT_TRIGGER_FIRED advisory for plan-size drift detection.

Implements `design postplan-emit --design-tmpdir PATH [--snapshot-original]
[--with-plan-size]` with the merged-mode exit codes:
  0  ok
  1  merged failure (plan-size rc 2/3 or other error)
  2  reserved
 10  validator defects
 11  pause-save (merged: exit without in-driver pause-save)
 12  hard size trigger
 13  partition size trigger
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from collections.abc import Sequence


# Drift-detection keys read from drift-baseline.env
_KEY_BASELINE_PLAN_LINES = "BASELINE_PLAN_LINES"
_KEY_BASELINE_DIFF_LINES = "BASELINE_DIFF_LINES"
# Emitted when current plan exceeds the baseline by the drift multiple
_KEY_DRIFT_TRIGGER_FIRED = "DRIFT_TRIGGER_FIRED"


def _plugin_root() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[1]


def postplan_emit_main(argv: Sequence[str]) -> int:
    argv = list(argv)
    root = _plugin_root()
    result = subprocess.run(
        [sys.executable, str(root / "python" / "cli.py"), "plan-review", "emit", *argv],
        check=False,
    )
    return int(result.returncode)
