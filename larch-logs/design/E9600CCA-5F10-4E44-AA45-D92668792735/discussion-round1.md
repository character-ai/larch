## Decision 1: CI check failures are deterministic by default
- **Question**: How to classify transient vs deterministic before deciding retry-vs-fix?
- **Resolution**: Assume CI **check** failures (test/lint/compile/etc.) are NEVER transient → always attempt a code fix first. Only genuine network/infra failures count as transient and may retry without a code change. The transient set is the existing `is_transient_net_signature` network signatures plus the already-handled infra bails (NO_CHECKS, poll-budget exhausted, ci-status returned no valid output 3x). Everything else = deterministic = fix-first.
- **Source**: user

## Decision 2: Behind + fail — keep one rebase-to-main, then fix
- **Question**: Does fix-first preempt the rebase when the branch is behind main AND CI failed?
- **Resolution**: Keep at most one rebase-to-incorporate-main when behind (a rebase can legitimately clear a stale-main failure and is required before merge), but FORBID the re-bump + blind-rerun churn. A deterministic failure that persists routes to the fixer instead of looping rebase→rebump→rerun.
- **Source**: user

## Decision 3: Scope reaches the max-retries exhaustion path
- **Question**: How far beyond classify + fix-first should scope reach?
- **Resolution**: Also wire the autonomous CI-fix into the 10/12-max-retries exhaustion path — attempt a budget-gated final fix before the terminal stall and/or route the stall to the autonomous CI-fix path in `/implement` Step 8+ (the same path used for Exit 3 `first-fixer-non-health`).
- **Source**: user

## Decision 4: No hard non-goals
- **Question**: What stays off-limits to keep regression risk low?
- **Resolution**: Open to touching the vendor waterfall (`run_ci_fix_vendor`/`run_ci_fix`), the transient-retry helpers (`lib-net.sh`/`retry.py`), and the `ci-decide`/`decide` decision matrix if the cleanest fix needs it. Still prefer the minimal change that satisfies acceptance.
- **Source**: user

## Decision 5: Both Bash and Python implementations updated (hard requirement)
- **Question**: Which implementations must change?
- **Resolution**: Apply the fix to BOTH `scripts/ship-pr.sh` (+ `scripts/ci-wait.sh` / `scripts/ci-decide.sh` as needed) AND the `python/` migration tree (`ci_monitor.py` `evaluate_failure`/`decide`, plus tests). The bug must not reappear when `LARCH_SHIP_PR_IMPL=python` goes live.
- **Source**: issue Acceptance + Python Migration Note

## Decision 6: Preserve fix-attempts budget cap (hard constraint)
- **Question**: How to avoid an unbounded fix loop when fix-first runs more often?
- **Resolution**: The existing fix-attempts cap (`CI_MONITOR_MAX_FIX_ATTEMPTS`=10) and the per-invocation outer waterfall cap (`_max_fix`=3 in Bash / `CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS` in Python) remain. Fix-first must not create an unbounded fix loop; when the fix budget is exhausted the loop stalls (then routes to the autonomous CI-fix path per Decision 3).
- **Source**: codebase

## Decision 7: Out of scope — green-merge fast path, behind+pending/pass rebase, transient-network terminal exit
- **Question**: What stays unchanged?
- **Resolution**: Only the failure-path routing changes. Merge-when-green, the normal up-to-date rebase for behind+pending/pass (not a failure), and the `exit_transient_net` terminal-exit on genuine network signatures are unchanged.
- **Source**: codebase
