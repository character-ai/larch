# Review Round 1

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Abandoned `implement-step5-self-review` marker maps to wrong resume hint
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: Abandoned `implement-step5-self-review` marker maps to `RESUME_HINT=step5-review` instead of the self-review checks-commit-route composite. A `/implement --self-review` run whose step5-self-review checks-commit-route is SIGTERM-killed gets `RESUME_HINT=step5-review`; stall recovery re-launches `step-5-review.sh` (external review panel) instead of the self-review checks composite, violating self-review mode and duplicating/skipping work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Emit a step5-self-review-specific resume hint (or branch on marker STEP) that re-invokes checks-commit-route --checks-site step5-self-review --commit-site step5-self-review; document it in stall-recovery.md alongside checks-commit-route-retry.


### FINDING_3: `clear-stall` leaves dead-PID `.bg-wait-active`, blocking Step 18 finalize
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: `clear-stall` does not remove dead-PID `.bg-wait-active` but Step 18 now treats it as a stall layer. After `clear-stall` without a successful checks-commit-route retry, `step-18-gate-finalize` keeps returning `NEXT_ACTION=stall-recovery` and blocks `finalize-done`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Unlink dead-PID checks markers in clear-stall and/or after terminal seeding, or suppress abandoned-marker detection once recovery is terminal.


### FINDING_6: New `checks-commit-route-retry` resume hint not corpus-allowlisted
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: Emits a new resume hint that is not allowlisted by the sensitive-corpus validator. Tier-B report generation can reject the attempts table when this new hint appears, blocking filing on the exact recovery path this change adds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Add checks-commit-route-retry to the allowlisted resume-hint values in _sensitive_value_is_allowlisted and add a regression test for tier-B validation.


