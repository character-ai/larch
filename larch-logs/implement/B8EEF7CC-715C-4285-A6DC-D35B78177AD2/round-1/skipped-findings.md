### FINDING_10: Finalize bash-parity tests are smoke-only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity.py` does not exercise enough `implement-finalize.sh` subprocess/parity cases, so postbump, postmerge, and teardown behavior can drift from bash unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.



### FINDING_18: Planned finalize unit cases are missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize.py` does not cover several plan-listed edge cases such as postbump gates, verify mismatch, session cleanup guard, and rename branches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.



### FINDING_27: CI loop counters reset across orchestrator reinvocations
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: `iteration`, `rebase_count`, `fix_attempts`, and `transient_retries` are local to each `run_ship()` invocation, so exit-3/exit-6 handbacks reset bash-compatible caps and can allow unbounded work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.



### FINDING_28: Driver lacks ground-truth phase resume/short-circuiting
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: Reinvocation can repeat checks, postbump, log flushing, and PR prep even when a PR already exists or OOS/CI phases were completed, because Python lacks bash-like persisted/ground-truth phase detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.



### FINDING_31: Postmerge manifest recovery does not fail closed like bash
- **Reviewer(s)**: dyn-runlogs-output.txt
- **Severity**: important
- **Concern**: If `manifest.json` is missing mid-run, Python can synthesize a minimal manifest and proceed to `status=done` without bash’s partial recovery marker or report-skip behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlogs-output.txt: Address the concern above.



