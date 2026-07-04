# Review Round 2

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: result-env freshness and terminality mismatch
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: Step 3 result-env handling is inconsistent across the wrapper and process-identity code: a stale prior-round env can be accepted before detached-marker validation and route the flow forward too early, a valid current result can be rejected as stale because marker mtime is later, and missing-pid can fall into the long timeout instead of failing after a short grace.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Require numeric PID and successful await; add detached-marker mtime guard to _step3_review_result_env_present
  - From codex-specialist-edge-cases: Require terminal proof tied to the loop before returning success, and fail after a short grace when missing-pid has no valid result
  - From codex-specialist-testing: Base freshness on loop launch or identity epoch and test the result-env mtime between identity and detach marker case.


### FINDING_3: stale .bg-wait-active blocks recovery reads
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: Early-exit reattach and detach paths leave `.bg-wait-active` installed, so a stale hook marker can block orchestrator recovery reads even after the loop has successfully reattached or detached.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Clear .bg-wait-active in cleanup reattach and detach exits; assert in detach harness


