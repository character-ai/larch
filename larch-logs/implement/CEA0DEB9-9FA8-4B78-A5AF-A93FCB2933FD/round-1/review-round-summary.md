# Review Round 1

- Mode: `diff`
- 1 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_4: Timeout retries should not consume the seven-call cap
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-prompt-contract
- **Severity**: important
- **Concern**: Uncapped no-response re-fires are not excluded from the seven-call discussion cap. If timeout retries count, an AFK operator can still hit the cap and proceed with deferred questions, partially defeating the indefinite-wait behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Exempt no-response re-fires from the seven-call decision counter, or add an explicit cap carve-out that timeout retries do not consume branch budget.
  - From cursor-specialist-edge-cases: Exempt no-response re-fires from the seven-call counter; retry current branch without incrementing.
  - From dyn-dyn-prompt-contract: Clarify in rule 6 (or adjacent cap prose) that no-response re-fires retry the current branch and do not advance the seven-call decision counter.


