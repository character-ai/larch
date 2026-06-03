### FINDING_1: Driver acceptance matrix coverage is missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-harness-gate-output.txt
- **Severity**: important
- **Concern**: `python/test_ship.py` covers only a small subset of the Phase 7 driver acceptance matrix, leaving draft/forked/repo-unavailable/transient/GOTO-rebase/cap-exhaustion/single-flush and JSON handback regressions unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-harness-gate-output.txt: Address the concern above.



### FINDING_16: CI monitor transient bail path lacks coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The new monitor bail-to-`TRANSIENT` path has no pytest coverage, so transient network bails may regress to `STALLED`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.



### FINDING_17: Run-log post-flush ordering is not tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The planned `flush_logs_post` ordering test is absent, so final reports could be written before manifest `status=done` / `pr_number` without CI detecting it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.



### FINDING_2: Finalize unit and parity coverage is too shallow
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-finalize-parity-output.txt, dyn-harness-gate-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize.py` and `python/test_finalize_bash_parity.py` do not cover the planned postbump gates, teardown/session guards, rename branches, remote-check routing, or true bash parity against `implement-finalize.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-finalize-parity-output.txt, dyn-harness-gate-output.txt: Address the concern above.



### FINDING_22: Python ship lacks resume/short-circuit semantics
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-ship-driver-output.txt
- **Severity**: important
- **Concern**: Re-invoking `python/ship.py` restarts checks/postbump/PR prep instead of resuming from persisted phase or ground truth, causing redundant rebase/push/CI churn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-ship-driver-output.txt: Address the concern above.



### FINDING_28: CI-loop counters are not persisted and diverge from bash
- **Reviewer(s)**: dyn-ship-driver-output.txt, dyn-ci-rebase-output.txt
- **Severity**: important
- **Concern**: `iteration`, `rebase_count`, `fix_attempts`, and `transient_retries` live only in process memory and use different reset/increment rules than bash, so caps can be bypassed across reinvokes or exhausted too early within a run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-driver-output.txt, dyn-ci-rebase-output.txt: Address the concern above.



### FINDING_29: Python JSON lacks a stable phase for transient retry budgeting
- **Reviewer(s)**: dyn-ship-driver-output.txt, dyn-cutover-docs-output.txt
- **Severity**: important
- **Concern**: Step 8+ exit-6 retry accounting still keys off `PHASE` from `ship-pr-state.sh`, but Python does not persist or emit a stable phase, so transient budgets cannot match bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-driver-output.txt, dyn-cutover-docs-output.txt: Address the concern above.



### FINDING_32: Python postmerge cleanup lacks bash local-cleanup parity
- **Reviewer(s)**: dyn-finalize-parity-output.txt
- **Severity**: important
- **Concern**: `finalize.postmerge()` reimplements cleanup without bash’s fetch/retry, orphan larch-log reset, ahead diagnostics, and verify-main behavior, yet can still return `OK` with partial cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-finalize-parity-output.txt: Address the concern above.



