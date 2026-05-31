Verifying the cited code paths so normalized findings match the implementation.
Two independent correctness gaps in the planned Phase-7 `ci_monitor` / driver mapping: one is `rebase_then_evaluate` routing, the other is bail/`FixResult` → `StepResult` parity with Bash exit 3. They need different fixes and stay as separate findings.

### FINDING_1: rebase_then_evaluate must not enter inline fix before rebase
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `rebase_then_evaluate` is routed into the inline fix path via `evaluate_failure`. In Bash (`scripts/ship-pr.sh:3547-3549`), rebase runs before `run_evaluate_failure`. Under the plan’s decoupled-rebase design, attempting fixes while still behind `main` diverges from Bash and from plain `rebase` handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Map rebase_then_evaluate to goto_rebase=True, did_fixing=False, OK (same as rebase). Let the Phase-7 driver rebase, then re-enter monitor before any fix dispatch.

### FINDING_2: exit-3 bail and FixResult paths must map to NEEDS_USER_INPUT, not STALLED
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `monitor()` maps every `Decision.action=bail` and several `FixResult` terminals to `StepResult.STALLED` only. Bash treats `ci-decide.sh` `fix-attempts-exhausted` and `run_evaluate_failure` `first-fixer-non-health` as exit-3 paths (`needs_user_bail_reason` / autonomous CI-fix in `scripts/ship-pr.sh`). A Phase-7 driver that only handles `STALLED` will stall instead of surfacing exit 3 / `NEEDS_USER_INPUT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Map `bail` with `bail_reason=fix-attempts-exhausted` to `NEEDS_USER_INPUT`; map `FixResult` `first-fixer-non-health` to `NEEDS_USER_INPUT` (detail token `first-fixer-non-health`, not generic stall); keep timeout/rebase-cap/`NO_CHECKS` bails as `STALLED`; add parity tests in `test_ci_monitor.py`
