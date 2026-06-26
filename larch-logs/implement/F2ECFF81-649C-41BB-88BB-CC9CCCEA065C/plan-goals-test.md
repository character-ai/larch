## Goal
Implement issue #5440: [IMPLEMENTING] checks lint-fix: per-tool timeout 300s + 600s total budget + timeout→main-agent-required routing.

## Implementation Plan
## Problem

`run_lint_fix` in `python/checks.py` blocked a full /implement run for ~3 hours because:

1. `_RUN_EXTERNAL_TIMEOUT = 1800` — each external tool (claude, codex, cursor) gets 30 minutes. With three tools in the waterfall, worst case is 90 minutes of blocked wall time before lint-fix gives up.
2. The claude subprocess (`claude -p`) timed out at exit 124 after 30 minutes without producing any output, yet the checks log that triggered lint-fix may have been a transient or already-resolved failure.
3. Timeout paths can reach `status="failed"` (exit 1 from `checks_lint_fix_main`), which `review_and_fix.py` maps to the `lint-fix-failed` stall reason — stalling the entire run rather than handing off to main Claude.

## Fix plan

Three changes in `python/checks.py`:

**1. Reduce `_RUN_EXTERNAL_TIMEOUT` from 1800 → 300** (line 46)

A lint fix is a narrow, targeted task. If claude/codex/cursor has not produced output in 5 minutes, it is hung. 300s per tool.

**2. Add a 600s total budget cap to `run_lint_fix`**

Start a wall-clock timer at entry to `run_lint_fix`. After each tool attempt (regardless of outcome), check elapsed time. If `elapsed >= 600s`, short-circuit the loop and return `FixOutcome(status="main-agent-required", failure_reason="lint-fix-budget-exceeded", ...)` without trying further tiers. This bounds worst-case to 10 minutes regardless of tool count.

Add constants alongside the existing one:

```python
_RUN_EXTERNAL_TIMEOUT: Final = 300
_LINT_FIX_TOTAL_BUDGET_SECONDS: Final = 600
```

**3. Ensure timeout exit (124) always routes to `main-agent-required`, never `failed`**

Currently, when all tiers are exhausted without success, `run_lint_fix` returns `main-agent-required` with `failure_reason="dispatch-failed"` (exit 0 from `checks_lint_fix_main`). But the run that prompted this issue hit `lint-fix-failed` (exit 1), meaning some timeout path reached the `status="failed"` branch instead. Audit the exit-124 handling in `_run_claude`, `_run_codex`, `_run_cursor` and ensure a timed-out tier always falls through to the next tier (or to the budget-exceeded path), never to a `failed` return.

## Acceptance

- `_RUN_EXTERNAL_TIMEOUT = 300` in `checks.py`
- `_LINT_FIX_TOTAL_BUDGET_SECONDS = 600` in `checks.py`, enforced in `run_lint_fix`
- A simulated all-tools-timeout in `python/test_checks.py` exits with `LINT_FIX_STATUS=main-agent-required`, not `LINT_FIX_STATUS=failed`
- `make py-test` passes

## Test plan
(no test plan section in plan-file)
