### FINDING_1: post-monitor wait can precede monitor_rc branching
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Conditional detection only proves a monitor_rc branch exists after capture, not that the first post-monitor wait on the captured PID is inside that branch. A fence can run an unconditional `wait "$PID"` before a decorative monitor_rc conditional, masking monitor failure with the writer exit status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: monitor_rc init accepts nonzero integers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The init regex accepts any integer assignment like `monitor_rc=1`, which can bias the wrapper toward failure-path semantics before the monitor runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: lint contract doc conflicts with allowed wait ordering
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The contract doc says wait follows monitor, but the current implementation allows wait before the monitor_rc conditional, which misleads authors fixing incident-class fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_5: dead monitor_rc elif branch accepted
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A constant-true conditional head before an `elif` referencing monitor_rc can satisfy the branch check even though the monitor_rc branch is dead at runtime, so waits may be skipped on every path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: harness contract doc omits monitor_rc cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-lint-foreground-markers.md` still documents cases only through 53 and does not describe new monitor_rc cases 54-66, so future harness edits may omit those regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_8: missing negative fixture for non-literal monitor_rc init
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The harness lacks a regression fixture showing that variable initialization such as `monitor_rc=$?` or `monitor_rc=$other` is rejected where the plan expects literal init.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


