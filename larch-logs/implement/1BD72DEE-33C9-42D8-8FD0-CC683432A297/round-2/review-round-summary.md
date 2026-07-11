# Review Round 2

- Mode: `diff`
- 3 accepted, 7 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Recovery-time missing persisted coverage is not tested
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: The negative teardown test omits the post-merge sentinel, so recovery never runs and `load_coverage()` returning `None` is not exercised. A regression in the recovery branch could therefore ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_2: Final-report recovery can accept missing persisted coverage
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-testing
- **Severity**: major
- **Concern**: After a stale-live mismatch, final-report recovery can receive `None` from `load_coverage()` and suppress the optional summary line instead of failing closed. This permits report generation without validated persisted evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_3: Stale-live recovery is not restricted to post-merge rendering
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: The stale-live coverage recovery path is available to the pre-push strict final-report flow as well as post-merge rendering. An inline CI-fix can therefore cause a pre-merge stale mismatch to be suppressed without verified post-merge state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
