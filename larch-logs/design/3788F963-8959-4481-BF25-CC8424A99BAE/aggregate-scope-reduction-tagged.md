### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:128-145
- **Concern**: [SCOPE-REDUCTION] Hooks-only `_finalize_launch` is a no-op coordinator that adds lambdas without deduplicating launcher tails. Scenario: The proposed helper only iterates caller hooks. Each CI/implement launcher still hand-builds 7-8 closures, so line count and ordering risk stay high while `LauncherPaths` plus `_record_launch_timing` already fix the typo-desync class the issue cites.
- **Proposed resolution**: Prefer minimum-change rollout: land `LauncherPaths`, migrate `run_external_agent` and failure-diag helpers, unify timing via `_record_launch_timing`, and keep sequential epilogue calls. Defer `_finalize_launch` unless a later PR extracts real shared steps beyond `for hook in hooks`.
