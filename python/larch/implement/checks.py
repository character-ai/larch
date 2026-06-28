"""Local relevant-checks runner and lint-fix loop (ship-pr Phase 4).

Local fixer dispatch mirrors ``python/cli.py checks lint-fix`` (#3207): non-zero codex/cursor
launch maps to ``main-agent-required`` with ``failure_reason=dispatch-failed``;
``agents.classify_launch_failure`` is not used on this path (unlike CI fixer).
"""

from __future__ import annotations

# Module references kept at this level so tests can monkeypatch checks.git,
# checks.coder_delta_guards, and checks.external_defaults without targeting sub-modules.
from larch.git import git
from larch.core import coder_delta_guards
from larch.core import external_defaults

from larch.implement.checks_run_relevant import (
    ChecksResult,
    FixOutcome,
    LoopResult,
    normalize_max_iter,
    validate_tmpdir,
    run_relevant_checks,
    check_contains_pins_main,
    checks_run_relevant_main,
)

from larch.implement.checks_lint_fix import (
    run_lint_fix,
    run_check_fix_loop,
    escalate,
    run_checks_phase,
    checks_lint_fix_main,
    checks_repair_loop_main,
)

__all__ = [
    "ChecksResult",
    "FixOutcome",
    "LoopResult",
    "check_contains_pins_main",
    "checks_lint_fix_main",
    "checks_repair_loop_main",
    "checks_run_relevant_main",
    "coder_delta_guards",
    "escalate",
    "external_defaults",
    "git",
    "normalize_max_iter",
    "run_check_fix_loop",
    "run_checks_phase",
    "run_lint_fix",
    "run_relevant_checks",
    "validate_tmpdir",
]
