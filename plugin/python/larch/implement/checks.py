"""Re-exports for the relevant-checks runner and repair loop (ship-pr Phase 4).

The lint-fix engine and ``checks fixer-evidence`` are owned by Rust (#8625). The
still-Python repair loop dispatches the Rust ``checks lint-fix`` verb through
``scripts/larch.sh`` and rebuilds its outcome; this module only re-exports the
loop, runner, and shared types for tests and callers.
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
    run_contains_pins_scan,
)

from larch.implement.checks_lint_fix import (
    run_lint_fix,
    run_check_fix_loop,
    escalate,
    checks_repair_loop_main,
)

__all__ = [
    "ChecksResult",
    "FixOutcome",
    "LoopResult",
    "checks_repair_loop_main",
    "coder_delta_guards",
    "escalate",
    "external_defaults",
    "git",
    "normalize_max_iter",
    "run_check_fix_loop",
    "run_contains_pins_scan",
    "run_lint_fix",
    "run_relevant_checks",
    "validate_tmpdir",
]
