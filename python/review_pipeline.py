"""Review pipeline CLI entry points.

The C1b review pipeline now has Python-owned CLI verbs. The functions below
preserve the shipped contracts by executing the legacy shell implementations
from a private location while callers cut over to ``python/cli.py review ...``.
"""

from __future__ import annotations

import os
from pathlib import Path

import logging_util
import proc

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_LEGACY_DIR = Path(__file__).resolve().parent / "legacy_review_shell"


def run_legacy(script_name: str, argv: list[str]) -> int:
    logging_util.quiet_init(argv0=f"review-{script_name}")
    script = _LEGACY_DIR / script_name
    env = os.environ.copy()
    if not env.get("CLAUDE_PLUGIN_ROOT"):
        env["CLAUDE_PLUGIN_ROOT"] = str(_PLUGIN_ROOT)
    result = proc.run(["bash", str(script), *argv], cwd=str(_PLUGIN_ROOT), env=env)
    for line in result.stdout.splitlines():
        logging_util.emit(line)
    if result.stdout and not result.stdout.endswith("\n"):
        # splitlines() already emitted the unterminated tail. Keep parity by not
        # adding a second blank line.
        pass
    if result.stderr:
        for line in result.stderr.splitlines():
            logging_util.diagnostic(line)
    return result.returncode


def gather_context(argv: list[str]) -> int:
    return run_legacy("gather-context.sh", argv)


def dispatch_panel(argv: list[str]) -> int:
    return run_legacy("dispatch-panel.sh", argv)


def collect_findings(argv: list[str]) -> int:
    return run_legacy("collect-findings.sh", argv)


def check_reviewer_failure_threshold(argv: list[str]) -> int:
    return run_legacy("check-reviewer-failure-threshold.sh", argv)


def review_core(argv: list[str]) -> int:
    return run_legacy("review-core.sh", argv)


def gather_context_main(argv: list[str]) -> int:
    return gather_context(argv)


def dispatch_panel_main(argv: list[str]) -> int:
    return dispatch_panel(argv)


def collect_findings_main(argv: list[str]) -> int:
    return collect_findings(argv)


def check_reviewer_failure_threshold_main(argv: list[str]) -> int:
    return check_reviewer_failure_threshold(argv)


def review_core_main(argv: list[str]) -> int:
    return review_core(argv)
