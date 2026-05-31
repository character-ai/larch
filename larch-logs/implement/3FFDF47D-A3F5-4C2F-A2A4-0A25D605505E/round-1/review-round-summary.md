# Review Round 1

- Mode: `diff`
- 5 accepted, 8 rejected (7 exonerated)

## Accepted Findings

### FINDING_1: plan-size-trigger path must re-run the hard-gate handler before prompting
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Mid-review `LOOP_STATUS=plan-size-trigger` can invoke the hard prompt with stale or missing `check-plan-size` KVs, so Override logging may lack current trigger data and the flow can continue without the full Step 2b.5 contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: flags.md still implies all hard-trigger choices enter Split-path
- **Reviewer(s)**: dyn-flow-control-output.txt
- **Severity**: important
- **Concern**: The `--partition` bullet in `skills/design/references/flags.md` says hard plans show the prompt before entering Split-path automatically, which can mis-route Override as a precursor to decomposition instead of continuing review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flow-control-output.txt: Address the concern above.


### FINDING_13: README hard-gate wording still implies Override enters Split-path
- **Reviewer(s)**: dyn-flow-control-output.txt
- **Severity**: important
- **Concern**: The `/design` README row mentions `Split`/`Override`/`Cancel` but still ends with wording that implies Override leads to the same Split-path rather than continuing plan review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flow-control-output.txt: Address the concern above.


### FINDING_8: plan-review-loop.md sibling docs are missing the soft-advisory three-option breadcrumb
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-doc-sync-output.txt
- **Severity**: important
- **Concern**: `plan-review-loop.sh` was updated for the plan-size soft advisory, but the sibling `.md` does not document the `plan-size-trigger` breadcrumb or the `Split / Override / Cancel` contract required by the plan and script-md sync expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-doc-sync-output.txt: Address the concern above.


### FINDING_9: structure pins do not enforce hard-branch option order or anti-recommendation text
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-flow-control-output.txt
- **Severity**: important
- **Concern**: `test-design-structure.sh` only checks for the Override label/invariant, so CI would still pass if the Step 2b.5 hard prompt reordered `Split / Override / Cancel`, dropped an option, or weakened the advised-against language.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-flow-control-output.txt: Address the concern above.


