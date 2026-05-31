### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:36,40,65,87
- **Concern**: Local re-verify failure returns `local-unfixable` and `evaluate_failure` bails. Scenario: Binding Round 1 Decision 3 requires re-driving the CI vendor waterfall (capped at 3 with backoff) when a fixable job still fails `make` re-verify; `run_ci_fix` instead maps any still-failing fixable job to `local-unfixable`, and `evaluate_failure` bails immediately — one failed lint replay ends the fix loop instead of a second waterfall attempt
- **Proposed resolution**: Return a retriable status from `run_ci_fix` on post-vendor verify failure (e.g. `verify-failed`); let `evaluate_failure` consume outer attempts with backoff and only emit `local-unfixable` for `no-local-equivalent` jobs; add a test that verify failure triggers a second `run_ci_fix` call

