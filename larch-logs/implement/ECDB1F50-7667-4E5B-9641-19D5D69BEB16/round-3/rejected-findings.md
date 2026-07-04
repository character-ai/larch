### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Reattach failure misclassifies dead-vs-live loop state
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: important
- **Concern**: The reattach path does not consistently distinguish a dead detached loop from a still-live one: some failures exit instead of re-dispatching the same entry, while others clear detach state in ways that can permit duplicate concurrent reviews or retry churn after freshness mismatches or PID reuse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: On reattach failure after state cleanup, fall through to fresh dispatch when identity proves the detached loop is gone; fail closed without second dispatch when a live loop is still validated
  - From codex-specialist-correctness: Clear detached state and fall through to the existing fresh plan-review run path, or update the plan/docs to specify fail-closed behavior.
  - From cursor-specialist-edge-cases: On reattach failure, tear down via teardown-loop-identity when the PID is still live, or fail closed and preserve detach state until identity validation confirms the loop is gone before allowing fresh dispatch.
  - From codex-specialist-edge-cases: Check fresh result env before breaking on any validation mismatch, or avoid clearing detached state when freshness cannot be ruled out.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

