# Review Round 2

- Mode: `diff`
- 2 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: non-atomic Scenario 5 reap preconditions
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: major
- **Concern**: Scenario 5’s precondition checks and `reap_main` are not atomic, so a fast unlink can satisfy the assertions without ever calling `terminate_validated_process_group`; the test may pass without exercising the intended no-signal termination branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


### FINDING_6: command substitution keeps long-lived bgjob starts attached
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Long-lived bgjob starts are still captured through command substitution, so the harness can block until daemon EOF instead of exercising owner-death, timeout, or external-kill paths. That can let the child exit normally before the intended background lifecycle is tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
