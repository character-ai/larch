## Proposed Design Outline

### Goals
- CI **check** failures (test/lint/compile) always attempt a code fix before any retry — never pure rebase+re-bump churn.
- Classify transient (network/infra only) vs deterministic (everything else) before choosing retry-vs-fix, in both Bash and Python.
- Wire the autonomous CI-fix path into the 10/12-max-retries exhaustion path as a budget-gated backstop.

### Non-goals
- Redesigning the vendor-waterfall fixer mechanics — only change *when* it is invoked.
- Flaky-test detection / per-job transience heuristics — CI failures are deterministic by default.
- Changing the green-merge fast path, the behind+pending/pass rebase, or the transient-network terminal exit.

### Approach sketch
- Add one transient-vs-deterministic gate keyed on the existing `is_transient_net_signature` + infra bails; default everything else to deterministic.
- Gate the existing blind `ci-rerun-failed.sh` rerun (`run_evaluate_failure` TRANSIENT_RETRIES<1; Python `evaluate_failure` transient rerun) on that gate — deterministic skips straight to the fixer.
- Keep one rebase-to-main on `rebase_then_evaluate` when behind, but route a persisting deterministic failure to the fixer instead of re-bump+rerun.
- At 10/12-max-retries exhaustion, attempt one budget-gated fix and/or route the stall to the autonomous CI-fix path in `/implement` Step 8+.
- Mirror every change in `python/ci_monitor.py` (+ tests).

### Surfaces in scope
- `scripts/ship-pr.sh` — `run_evaluate_failure`, the CI-watch loop, exhaustion `exit_stall`.
- `scripts/ci-wait.sh` / `scripts/ci-decide.sh` — classification surface, as needed.
- `python/ci_monitor.py` (+ `python/retry.py` if the classifier is shared) and the python tests.
- `skills/implement/SKILL.md` Step 8+ — max-retries → autonomous CI-fix wiring.

### Open questions
- Whether the deterministic/transient gate lives in `ci-decide.sh`/`decide` (decision matrix) or in the caller (`run_evaluate_failure`/`evaluate_failure`) — resolved in the plan.
