### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ci_monitor.py:monitor
- **Concern**: rebase_then_evaluate routed into the inline fix path with evaluate_failure. Scenario: Bash rebases before run_evaluate_failure (scripts/ship-pr.sh:3547-3549). Under the plan's decoupled-rebase design, fixing while still behind main diverges from bash and from plain rebase handling.
- **Proposed resolution**: Map rebase_then_evaluate to goto_rebase=True, did_fixing=False, OK (same as rebase). Let the Phase-7 driver rebase, then re-enter monitor before any fix dispatch.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:43
- **Concern**: `monitor()` maps every `Decision.action=bail` and several `FixResult` terminals to `StepResult.STALLED` only. Scenario: `ci-decide.sh` `fix-attempts-exhausted` and `run_evaluate_failure` `first-fixer-non-health` are exit-3 paths in `scripts/ship-pr.sh` (`needs_user_bail_reason` / autonomous CI-fix); a Phase-7 driver that only handles `STALLED` will stall instead of exit 3
- **Proposed resolution**: Map `bail` with `bail_reason=fix-attempts-exhausted` to `NEEDS_USER_INPUT`; map `FixResult` `first-fixer-non-health` to `NEEDS_USER_INPUT` (detail token `first-fixer-non-health`, not generic stall); keep timeout/rebase-cap/`NO_CHECKS` bails as `STALLED`; add parity tests in `test_ci_monitor.py`
