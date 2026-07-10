# Review Round 1

- Mode: `diff`
- 5 accepted, 4 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Stale post-apply pipeline references
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-load-closure
- **Severity**: major
- **Concern**: `skills/design/SKILL.md` still points Step 3.5 to `approval-gates.md` §Shared post-apply pipeline, but that section now exists only in `approval-gates-gate-b.md`. The stale references can cause the orchestrator to miss step-10 continuation, marker, and idempotency rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-load-closure: Address the concern above.


### FINDING_2: Missing failure-slice reads before failed-path staging
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-load-closure
- **Severity**: major
- **Concern**: Several clarify, Split-path, and Step 3 terminal branches stage or export `failed-*` outcomes before an adjacent mandatory read of `finalize-step5-failures.md`. This can bypass failure-reporting, terminal-state, and automatic-error-staging instructions, including the distinct `failed-judge-panel` wording path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-load-closure: Address the concern above.


### FINDING_3: Missing Gate A default-path negative harness pin
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-load-closure
- **Severity**: major
- **Concern**: The structure harness verifies positive Gate A loading but does not assert that `approval-gates-gate-a.md` is absent from the default path outside the Step 1e re-entry block. A future edit could reintroduce eager Gate A loading while CI remains green and token savings regress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-load-closure: Address the concern above.


### FINDING_6: Heatmap fixtures do not cover split reference paths
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The heatmap fixtures and assertions still primarily use monolithic `approval-gates.md` references, leaving Gate B/C, runtime, and failure-slice paths untested for normalization, attribution, default-path exclusion, and reporting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_11: Split-path failed-judge-panel wording is ambiguous
- **Reviewer(s)**: dyn-dyn-load-closure
- **Severity**: major
- **Concern**: The `failed-judge-panel` Split-path says to run Final summary “through Read/cache” rather than explicitly running the Final summary block. Unlike sibling paths, this wording can omit the failure-slice contract and automatic error staging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-load-closure: Address the concern above.
