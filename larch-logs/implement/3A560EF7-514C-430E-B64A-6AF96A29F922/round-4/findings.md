### FINDING_1: post-monitor wait can precede monitor_rc branching
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Conditional detection only proves a monitor_rc branch exists after capture, not that the first post-monitor wait on the captured PID is inside that branch. A fence can run an unconditional `wait "$PID"` before a decorative monitor_rc conditional, masking monitor failure with the writer exit status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] heredoc body detection rescans each index
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `line_is_heredoc_body_idx` rescans from the start of the fence for every lookup, which can make large fences disproportionately slow and can drift from other heredoc walkers if delimiter behavior changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_3: duplicated heredoc state machine can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The heredoc state machine duplicates inline logic in `scan_fence_buffer_for_anchors`, so future delimiter or strip changes could be applied to only one walker and break heredoc-related guarantees.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: repeated canonical monitor_rc test fixture
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The canonical monitor_rc fixture block is repeated many times, making contract tweaks harder and increasing the chance that a passing fixture is missed during updates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: dead monitor_rc elif branch accepted
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A constant-true conditional head before an `elif` referencing monitor_rc can satisfy the branch check even though the monitor_rc branch is dead at runtime, so waits may be skipped on every path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: init check does not strip trailing shell comments
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The monitor_rc init check does not strip trailing shell comments before matching, so comment text can affect whether an init line is accepted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

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

### FINDING_9: harness does not lint real skills tree
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The test harness can pass while canonical `skills/**` fences regress, because it does not run the linter against the real repository tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: command-substitution bareword monitor_rc false positive
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: A command substitution containing the bare text `monitor_rc`, such as `$(echo monitor_rc)`, can satisfy the branch check without actually reading the captured monitor status variable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] per-anchor lint suppression bypasses monitor_rc checks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: A per-anchor ok comment on the writer line skips all Family B invariants, including the new monitor_rc checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: monitor_rc init accepts nonzero integers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The init regex accepts any integer assignment like `monitor_rc=1`, which can bias the wrapper toward failure-path semantics before the monitor runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: branch exits and writer_rc capture are not verified
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The linter accepts branched waits without verifying writer_rc capture or distinct `exit "$writer_rc"` / `exit "$monitor_rc"` behavior, so monitor failure may still fail to control the wrapper exit code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: lint contract doc conflicts with allowed wait ordering
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The contract doc says wait follows monitor, but the current implementation allows wait before the monitor_rc conditional, which misleads authors fixing incident-class fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] unrelated branch changes bundled
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The branch includes unrelated readability lint and larch-logs commits, which do not affect monitor_rc lint correctness but may be undesirable at merge or review time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] loop condition reachability is not proven
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `while` or `until` constructs mentioning monitor_rc can be accepted without proving the branch is reachable at runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: conditional scan semantics diverge from plan wording
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The implementation requires runtime monitor_rc in the conditional opener through `then`/`do`/`in`, while the plan wording allowed bareword monitor_rc anywhere from keyword line through end of fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_18: monitor_rc contract omits BASH_AUTHORING.md reference
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The new monitor_rc contract text does not include the explicit `BASH_AUTHORING.md` §4 reference required by the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] docs/linting.md changed outside plan file set
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `docs/linting.md` was updated to describe monitor_rc lint behavior but was not listed in the implementation plan file set, creating only PR scope bookkeeping risk if strict file parity is required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
