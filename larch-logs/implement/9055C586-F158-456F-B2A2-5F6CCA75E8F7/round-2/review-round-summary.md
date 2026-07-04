# Review Round 2

- Mode: `diff`
- 2 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Fail closed when live-leg publication fails
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: Active-leg record publication can fail or be suppressed, leaving a newly launched live leg untracked if the durable JSON record is never written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_2: Handle leader-exited cleanup and escalation
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Cleanup paths that depend on a recorded leader PID can stop too early when the leader exits, either refusing the missing-PID case or returning before escalating surviving descendants.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Track validated child identities or group membership before SIGTERM, then escalate only still-valid children or live members of the recorded pgid even if the leader exited.


