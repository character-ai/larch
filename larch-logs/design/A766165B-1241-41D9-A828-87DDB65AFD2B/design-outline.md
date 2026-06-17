## Proposed Design Outline

### Goals
- Fix 7 OOS concerns from the #4533 implement run: cycle routing, delegate timeout, passive CI wait, dead code, test coverage gaps, and conflict-resolution guard.
- Ensure all CI agentic-fix edge cases fail closed or retry correctly rather than burning cycles silently.
- Keep all tests stub-based; no LLM queries in CI.

### Non-goals
- Re-architecting the agentic CI delegate pipeline.
- Replacing all 16 skipped evaluate_failure tests (critical subset only).
- Changing the conflict-resolution.md procedure logic (prose clarification only).

### Approach sketch
- `ci_agentic_fix.py`: guard `first-fixer-non-health` to cycle==1 only; cycle>1 non-health returns `waterfall-failed`.
- `ci_agentic_fix.py`: fail closed with `ci-fix-exhausted` when `_wait_for_ci` returns an error (was: silently reuse stale run_id).
- `ci_monitor.py`: trim `run_ci_fix` to the `ci_fix_rebase_pending=True` push-only body; update affected tests.
- `ci_monitor.py`: extend `_agentic_fix_delegate_timeout_sec` to budget for per-cycle verify time.
- `python/rebase.py`: add forbidden-path guard in `_resolve_conflicts` after each fixer tier.
- Docs: clarify `checkout-ours` prose in `conflict-resolution.md`.
- Tests: add stubbed agentic-delegate tests for critical skipped evaluate_failure paths; add lint-fix waterfall cases.

### Surfaces in scope
- `python/ci_agentic_fix.py`
- `python/ci_monitor.py`
- `python/rebase.py`
- `python/test_ci_monitor.py`
- `python/test_ci_agentic_fix.py`
- `python/test_checks.py`
- `skills/implement/references/conflict-resolution.md`

### Open questions
- None.
