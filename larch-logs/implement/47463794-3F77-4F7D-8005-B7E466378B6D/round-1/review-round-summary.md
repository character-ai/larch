# Review Round 1

- Mode: `diff`
- 1 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_2: Prompt invariant harness imports missing wrapper attributes
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: `checks.py` no longer exposes prompt helper attributes that `scripts/test-prompt-template-invariants.sh` imports. This raises `AttributeError` and prevents the `make lint` prompt-template check from running.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


