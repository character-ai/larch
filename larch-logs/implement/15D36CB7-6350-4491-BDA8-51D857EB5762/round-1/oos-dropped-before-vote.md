### OOS_1: [OUT_OF_SCOPE] Large-diff scope rule no longer forbids exhaustive per-file review
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The large-diff guidance no longer explicitly says not to attempt exhaustive per-file review. On very large PRs, reviewers may drift back into noisy file-by-file nit review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Calibration examples lost some formatting and meta-calibration cues
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The calibration example block now has delimiter and wording drift. That is minor, but it weakens the output-shape cues that the examples were meant to preserve.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Logic-errors checklist dropped the boolean-conditions cue
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The compressed Logic errors bullet no longer explicitly names boolean conditions. That may slightly under-weight standalone boolean-logic bugs that are not inversion or operator mistakes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Calibration example formatting drift in direct consumers
- **Reviewer(s)**: dyn-dyn-prompt-contracts
- **Severity**: nit
- **Concern**: Calibration Example A now uses hyphens instead of em dashes and drops the synthetic-labeling detail. That mainly affects direct consumers of `agents/code-reviewer.md`, not aggregation validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-prompt-contracts: Address the concern above.

