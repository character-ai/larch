# Review Round 1

- Mode: `diff`
- 1 accepted, 9 rejected (0 neutral)

## Accepted Findings

### FINDING_7: Implement live waits need matching Read policy
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-bg-wait
- **Severity**: minor
- **Concern**: The hook now permits `tasks/*.output` Reads during implement live waits, but the implement skill and anti-polling docs still describe a deny-then-probe path, so an agent can read bytes and act while the child is still running.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Scope Read allow to design markers or update implement SKILL and orchestrator-never to match hook behavior.
  - From dyn-dyn-bg-wait: Either scope the `Read` carve-out to design marker steps only, or update implement NEVER #8 / orchestrator-never #3 and add implement-marker allow tests; drop or rewrite the “denied immediately after” pins if denial is no longer expected.


